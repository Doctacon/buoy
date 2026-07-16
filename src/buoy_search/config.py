"""Runtime configuration helpers for the Buoy CLI.

This module intentionally does not read secrets. Live commands read turbopuffer
credentials at the call site only after explicit user approval.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import os
import sys

DEFAULT_REGION = "gcp-us-central1"
DEFAULT_NAMESPACE = "site-scrapling-readthedocs-io-v1"
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_EMBEDDING_PRECISION = "float32"
EMBEDDING_PRECISIONS = ("float32", "float16")
EMBEDDING_MODEL_ENV = "BUOY_EMBEDDING_MODEL"
LEGACY_EMBEDDING_MODEL_ENV = "TURBO_SEARCH_EMBEDDING_MODEL"
EMBEDDING_PRECISION_ENV = "BUOY_EMBEDDING_PRECISION"
LEGACY_EMBEDDING_PRECISION_ENV = "TURBO_SEARCH_EMBEDDING_PRECISION"


class RuntimeConfigError(ValueError):
    """Raised when non-secret runtime configuration is contradictory."""


def _stderr_warning(message: str) -> None:
    try:
        print(message, file=sys.stderr)
    except OSError:
        # Configuration warnings are advisory and must not alter command behavior.
        pass


@dataclass(frozen=True)
class RuntimeConfig:
    """Non-secret runtime defaults for local and live commands."""

    region: str = DEFAULT_REGION
    namespace: str = DEFAULT_NAMESPACE
    embedding_model: str = DEFAULT_EMBEDDING_MODEL
    embedding_precision: str = DEFAULT_EMBEDDING_PRECISION


def load_config(*, warning_callback: Callable[[str], None] | None = None) -> RuntimeConfig:
    """Load non-secret runtime configuration from environment defaults.

    Deliberately excludes TURBOPUFFER_API_KEY so help and dry-run commands can be
    used safely without credentials. Buoy retains the old branded embedding
    variables through 0.3 as bounded compatibility fallbacks scheduled for
    removal in 0.4.
    """

    current_model = os.environ.get(EMBEDDING_MODEL_ENV)
    legacy_model = os.environ.get(LEGACY_EMBEDDING_MODEL_ENV)
    if current_model is not None and legacy_model is not None and current_model != legacy_model:
        raise RuntimeConfigError(
            f"conflicting {EMBEDDING_MODEL_ENV} and {LEGACY_EMBEDDING_MODEL_ENV} values; "
            f"unset one or make them identical"
        )
    if current_model is not None:
        embedding_model = current_model
    elif legacy_model is not None:
        embedding_model = legacy_model
        (warning_callback or _stderr_warning)(
            f"Warning: {LEGACY_EMBEDDING_MODEL_ENV} is deprecated; use {EMBEDDING_MODEL_ENV}. "
            "It will be removed in 0.4."
        )
    else:
        embedding_model = DEFAULT_EMBEDDING_MODEL

    current_precision = os.environ.get(EMBEDDING_PRECISION_ENV)
    legacy_precision = os.environ.get(LEGACY_EMBEDDING_PRECISION_ENV)
    if current_precision is not None and legacy_precision is not None and current_precision != legacy_precision:
        raise RuntimeConfigError(
            f"conflicting {EMBEDDING_PRECISION_ENV} and {LEGACY_EMBEDDING_PRECISION_ENV} values; "
            "unset one or make them identical"
        )
    if current_precision is not None:
        embedding_precision = current_precision
    elif legacy_precision is not None:
        embedding_precision = legacy_precision
        (warning_callback or _stderr_warning)(
            f"Warning: {LEGACY_EMBEDDING_PRECISION_ENV} is deprecated; use {EMBEDDING_PRECISION_ENV}. "
            "It will be removed in 0.4."
        )
    else:
        embedding_precision = DEFAULT_EMBEDDING_PRECISION
    if embedding_precision not in EMBEDDING_PRECISIONS:
        raise RuntimeConfigError(
            f"embedding precision must be one of: {', '.join(EMBEDDING_PRECISIONS)}"
        )

    return RuntimeConfig(
        region=os.environ.get("TURBOPUFFER_REGION", DEFAULT_REGION),
        namespace=os.environ.get("TURBOPUFFER_NAMESPACE", DEFAULT_NAMESPACE),
        embedding_model=embedding_model,
        embedding_precision=embedding_precision,
    )
