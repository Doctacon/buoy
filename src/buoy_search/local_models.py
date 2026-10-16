"""Offline-only construction helpers for Buoy's local inference models.

This module intentionally imports no model framework at import time.  Runtime
configuration is applied before ``torch`` or ``sentence_transformers`` is
imported by a loader.
"""

from __future__ import annotations

import os
import sys
from typing import Any

BGE_MODEL = "BAAI/bge-small-en-v1.5"
BGE_REVISION = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"
DEFAULT_MODEL_THREADS = 4

_OFFLINE_ENVIRONMENT = {
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
    "HF_HUB_DISABLE_TELEMETRY": "1",
    "HF_HUB_DISABLE_IMPLICIT_TOKEN": "1",
    "DO_NOT_TRACK": "1",
    "TOKENIZERS_PARALLELISM": "false",
}


class LocalModelError(RuntimeError):
    """A pinned local model could not be configured or loaded from cache."""


def configure_local_runtime() -> None:
    """Force offline, non-telemetric model-library behavior in this process."""

    # Assign rather than setdefault: an inherited ``0`` must not weaken the
    # offline contract of a Buoy model load.
    os.environ.update(_OFFLINE_ENVIRONMENT)


def resolved_device() -> str:
    """Return the explicitly selected local model device (CPU by default)."""

    device = os.environ.get("BUOY_DEVICE", "cpu").strip()
    if not device:
        raise LocalModelError("BUOY_DEVICE must be a non-empty device name")
    return device


def model_thread_count() -> int:
    """Return the validated torch thread limit (four by default)."""

    raw_value = os.environ.get("BUOY_MODEL_THREADS", str(DEFAULT_MODEL_THREADS))
    try:
        threads = int(raw_value, 10)
    except (TypeError, ValueError) as exc:
        raise LocalModelError("BUOY_MODEL_THREADS must be a positive integer") from exc
    if threads <= 0 or str(threads) != raw_value.strip():
        raise LocalModelError("BUOY_MODEL_THREADS must be a positive integer")
    return threads


def configure_torch_threads() -> None:
    """Apply the bounded thread count if torch has been loaded by a model library."""

    configure_local_runtime()
    threads = model_thread_count()
    torch = sys.modules.get("torch")
    if torch is not None:
        torch.set_num_threads(threads)  # type: ignore[attr-defined]


def _pinned_revision(model_name: str, revision: str | None) -> str:
    if model_name == BGE_MODEL:
        if revision is not None and revision != BGE_REVISION:
            raise LocalModelError(
                f"{BGE_MODEL} must use pinned revision {BGE_REVISION}"
            )
        return BGE_REVISION
    if revision is None:
        raise LocalModelError(f"local model {model_name!r} requires an exact revision")
    return revision


def load_sentence_transformer(
    model_name: str,
    revision: str | None = None,
) -> Any:
    """Load an exact cached SentenceTransformer without any network fallback."""

    pinned_revision = _pinned_revision(model_name, revision)
    configure_local_runtime()
    device = resolved_device()
    # Validate before importing model dependencies, then apply after
    # sentence-transformers has imported torch.
    model_thread_count()

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:  # pragma: no cover - dependency install failure.
        raise LocalModelError(
            "sentence-transformers is required for local embeddings; run `uv sync` first"
        ) from exc

    configure_torch_threads()
    try:
        from buoy_search.model_progress import suppress_model_progress_bars

        with suppress_model_progress_bars():
            return SentenceTransformer(
                model_name,
                revision=pinned_revision,
                local_files_only=True,
                trust_remote_code=False,
                device=device,
                model_kwargs={"use_safetensors": True},
            )
    except Exception as exc:
        raise LocalModelError(
            f"pinned model {model_name}@{pinned_revision} is not available in the "
            "local Hugging Face cache; on an online machine run "
            "`python scripts/prepare_local_models.py --download` and copy that "
            "cache to this host (automatic downloads are disabled)"
        ) from exc
