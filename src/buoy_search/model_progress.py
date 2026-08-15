"""Shared suppression for third-party model loading progress bars."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import sys


@contextmanager
def suppress_model_progress_bars() -> Iterator[None]:
    """Hide third-party model bars while restoring the caller's prior state."""

    transformers_logging = sys.modules.get("transformers.utils.logging")
    if transformers_logging is None:
        transformers_utils = sys.modules.get("transformers.utils")
        transformers_logging = getattr(transformers_utils, "logging", None)
    transformers_progress_was_enabled = False
    try:
        transformers_progress_was_enabled = bool(
            transformers_logging is not None
            and transformers_logging.is_progress_bar_enabled()
        )
        if transformers_logging is not None:
            transformers_logging.disable_progress_bar()
    except Exception:
        # Progress is presentation-only; incompatibility must not break work.
        transformers_logging = None

    huggingface_utils = sys.modules.get("huggingface_hub.utils")
    huggingface_progress_was_enabled = False
    try:
        huggingface_progress_was_enabled = bool(
            huggingface_utils is not None
            and not huggingface_utils.are_progress_bars_disabled()
        )
        if huggingface_utils is not None:
            huggingface_utils.disable_progress_bars()
    except Exception:
        # Progress is presentation-only; incompatibility must not break work.
        huggingface_utils = None

    try:
        yield
    finally:
        try:
            if huggingface_utils is not None and huggingface_progress_was_enabled:
                huggingface_utils.enable_progress_bars()
        except Exception:
            pass
        try:
            if transformers_logging is not None and transformers_progress_was_enabled:
                transformers_logging.enable_progress_bar()
        except Exception:
            pass
