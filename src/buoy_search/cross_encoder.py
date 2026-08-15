"""Pinned local cross-encoder used for bounded cross-namespace reranking."""

from __future__ import annotations

from functools import lru_cache
import math
from typing import Protocol, Sequence

from buoy_search.model_progress import suppress_model_progress_bars

CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
CROSS_ENCODER_REVISION = "c5ee24cb16019beea0893ab7796b1df96625c6b8"
CROSS_ENCODER_MAX_LENGTH = 512
CROSS_ENCODER_BATCH_SIZE = 8


class CrossEncoderRerankerError(RuntimeError):
    """The exact local reranker could not be loaded or produced invalid scores."""


class CrossEncoderReranker(Protocol):
    """Minimal query/passage scoring seam used by retrieval orchestration."""

    def score(self, query: str, passages: Sequence[str]) -> list[float]:
        """Return one finite relevance score per passage."""


class _PinnedMiniLMReranker:
    def __init__(self) -> None:
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:  # pragma: no cover - depends on optional install.
            raise CrossEncoderRerankerError(
                "sentence-transformers is required for cross-namespace reranking; "
                "run `uv sync` first"
            ) from exc

        try:
            with suppress_model_progress_bars():
                self._model = CrossEncoder(
                    CROSS_ENCODER_MODEL,
                    revision=CROSS_ENCODER_REVISION,
                    local_files_only=True,
                    trust_remote_code=False,
                    device="cpu",
                    max_length=CROSS_ENCODER_MAX_LENGTH,
                    model_kwargs={"use_safetensors": True},
                )
        except Exception as exc:
            raise CrossEncoderRerankerError(
                f"pinned reranker {CROSS_ENCODER_MODEL}@{CROSS_ENCODER_REVISION} "
                "is not cached locally; cache that exact revision and retry "
                "(downloads and substitutions are disabled)"
            ) from exc

    def score(self, query: str, passages: Sequence[str]) -> list[float]:
        pairs = [(query, passage) for passage in passages]
        if not pairs:
            return []
        try:
            raw_scores = self._model.predict(
                pairs,
                batch_size=CROSS_ENCODER_BATCH_SIZE,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
        except Exception as exc:
            raise CrossEncoderRerankerError(
                "pinned cross-namespace reranker inference failed"
            ) from exc

        values = raw_scores.tolist() if hasattr(raw_scores, "tolist") else raw_scores
        if not isinstance(values, Sequence) or isinstance(values, (str, bytes, bytearray)):
            raise CrossEncoderRerankerError(
                "pinned cross-namespace reranker returned an invalid score sequence"
            )
        if len(values) != len(passages):
            raise CrossEncoderRerankerError(
                "pinned cross-namespace reranker returned the wrong number of scores"
            )
        scores: list[float] = []
        for value in values:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise CrossEncoderRerankerError(
                    "pinned cross-namespace reranker returned a non-numeric score"
                )
            score = float(value)
            if not math.isfinite(score):
                raise CrossEncoderRerankerError(
                    "pinned cross-namespace reranker returned a non-finite score"
                )
            scores.append(score)
        return scores


@lru_cache(maxsize=1)
def load_cross_encoder_reranker() -> CrossEncoderReranker:
    """Load one exact cached MiniLM revision; never download or substitute it."""

    return _PinnedMiniLMReranker()
