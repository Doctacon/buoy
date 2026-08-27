"""Exact offline token-budget subdivision for repository treatment source ranges."""

from __future__ import annotations

from collections.abc import Callable
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
import os
from pathlib import Path
from typing import Any, Protocol

from buoy_search.indexing.repo_syntax_chunking import SourceRange

TOKENIZER_MODEL = "BAAI/bge-small-en-v1.5"
TOKENIZER_REVISION = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"
TOKENIZER_IMPLEMENTATION = "transformers.models.bert.tokenization_bert.BertTokenizer"
TOKENIZER_FILES_SHA256 = "9c7beccadaa552c323907a895ad9ab188d8b75763022403f72c5d91085334f3b"
TRANSFORMERS_VERSION = "5.12.1"
MAX_EMBEDDING_TOKENS = 512
TOKENIZER_FILES = (
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.txt",
)


class TreatmentTokenBudgetError(RuntimeError):
    """Raised when exact treatment token compatibility cannot be guaranteed."""


class UnsplittableSourceLine(TreatmentTokenBudgetError):
    """One complete rendered physical source line exceeds the token maximum."""

    def __init__(self, line: int, token_count: int) -> None:
        super().__init__("one complete rendered physical source line exceeds the token maximum")
        self.line = line
        self.token_count = token_count


class Tokenizer(Protocol):
    model_max_length: int

    def __call__(self, text: str, **kwargs: object) -> dict[str, Any]: ...


def bundled_tokenizer_snapshot() -> Path:
    """Return the immutable tokenizer-only snapshot shipped for offline planning."""

    return (
        Path(__file__).resolve().parent.parent
        / "data"
        / "bge-small-en-v1.5"
        / TOKENIZER_REVISION
    )


def load_pinned_tokenizer(snapshot: Path | None = None) -> Tokenizer:
    """Load and verify only the exact tokenizer; never construct a model or use a network."""

    for name in (
        "HF_HUB_OFFLINE",
        "TRANSFORMERS_OFFLINE",
        "HF_HUB_DISABLE_IMPLICIT_TOKEN",
        "HF_HUB_DISABLE_TELEMETRY",
    ):
        os.environ[name] = "1"
    try:
        installed_version = version("transformers")
    except PackageNotFoundError as exc:
        raise TreatmentTokenBudgetError(
            f"pinned tokenizer package mismatch: transformers=={TRANSFORMERS_VERSION} required"
        ) from exc
    if installed_version != TRANSFORMERS_VERSION:
        raise TreatmentTokenBudgetError(
            f"pinned tokenizer package mismatch: transformers=={TRANSFORMERS_VERSION} required"
        )

    resolved = (snapshot or bundled_tokenizer_snapshot()).expanduser().resolve(strict=True)
    if resolved.name != TOKENIZER_REVISION:
        raise TreatmentTokenBudgetError("pinned tokenizer revision mismatch")
    if tokenizer_files_identity(resolved) != TOKENIZER_FILES_SHA256:
        raise TreatmentTokenBudgetError("pinned tokenizer file-set identity mismatch")

    from transformers import BertTokenizer
    from transformers.utils import logging as transformers_logging

    transformers_logging.set_verbosity_error()
    tokenizer = BertTokenizer.from_pretrained(
        resolved,
        local_files_only=True,
        revision=TOKENIZER_REVISION,
    )
    implementation = f"{type(tokenizer).__module__}.{type(tokenizer).__name__}"
    if implementation != TOKENIZER_IMPLEMENTATION:
        raise TreatmentTokenBudgetError("pinned tokenizer implementation mismatch")
    if tokenizer.model_max_length != MAX_EMBEDDING_TOKENS:
        raise TreatmentTokenBudgetError("pinned tokenizer model maximum mismatch")
    return tokenizer


def tokenizer_files_identity(snapshot: Path) -> str:
    files: list[dict[str, object]] = []
    try:
        entries = tuple(sorted(snapshot.iterdir(), key=lambda entry: entry.name))
    except OSError as exc:
        raise TreatmentTokenBudgetError("pinned tokenizer file set is missing") from exc
    if tuple(entry.name for entry in entries) != TOKENIZER_FILES or any(
        entry.is_symlink() or not entry.is_file() for entry in entries
    ):
        raise TreatmentTokenBudgetError("pinned tokenizer file-set identity mismatch")
    try:
        for path in entries:
            payload = path.read_bytes()
            files.append(
                {
                    "path": path.name,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "size_bytes": len(payload),
                }
            )
    except OSError as exc:
        raise TreatmentTokenBudgetError("pinned tokenizer file set is missing") from exc
    canonical = json.dumps(files, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def exact_token_count(tokenizer: Tokenizer, embedding_text: str) -> int:
    """Count a complete final embedding payload with the pinned call options."""

    encoded = tokenizer(
        embedding_text,
        add_special_tokens=True,
        truncation=False,
        padding=False,
        return_length=True,
    )
    lengths = encoded.get("length")
    if not isinstance(lengths, list) or len(lengths) != 1:
        raise TreatmentTokenBudgetError("pinned tokenizer returned an invalid exact length")
    token_count = lengths[0]
    if not isinstance(token_count, int) or isinstance(token_count, bool) or token_count < 0:
        raise TreatmentTokenBudgetError("pinned tokenizer returned an invalid exact length")
    return token_count


def exhaustive_maximal_subdivision(
    parent: SourceRange,
    render_embedding_text: Callable[[SourceRange], str],
    count_tokens: Callable[[str], int],
) -> tuple[SourceRange, ...]:
    """Choose every farthest feasible physical-line prefix without crossing ``parent``."""

    if parent.end < parent.start:
        raise TreatmentTokenBudgetError("source subdivision parent is empty")
    children: list[SourceRange] = []
    cursor = parent.start
    while cursor <= parent.end:
        feasible: list[int] = []
        one_line_count: int | None = None
        for end in range(cursor, parent.end + 1):
            candidate = SourceRange(cursor, end, parent.breadcrumbs)
            token_count = count_tokens(render_embedding_text(candidate))
            if end == cursor:
                one_line_count = token_count
            if token_count <= MAX_EMBEDDING_TOKENS:
                feasible.append(end)
        if not feasible:
            assert one_line_count is not None
            raise UnsplittableSourceLine(cursor, one_line_count)
        end = max(feasible)
        children.append(SourceRange(cursor, end, parent.breadcrumbs))
        cursor = end + 1

    expected = parent.start
    for child in children:
        if (
            child.start != expected
            or child.end < child.start
            or child.end > parent.end
            or child.breadcrumbs != parent.breadcrumbs
        ):
            raise TreatmentTokenBudgetError("source subdivision violated parent coverage")
        expected = child.end + 1
    if expected != parent.end + 1:
        raise TreatmentTokenBudgetError("source subdivision violated parent coverage")
    return tuple(children)
