"""Runtime configuration helpers for the Buoy CLI.

This module intentionally does not read secrets. Live commands read turbopuffer
credentials at the call site only after explicit user approval.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import os

DEFAULT_REGION = "gcp-us-central1"
DEFAULT_NAMESPACE = "site-scrapling-readthedocs-io-v1"
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_EMBEDDING_PRECISION = "float32"
EMBEDDING_PRECISIONS = ("float32", "float16")
EMBEDDING_MODEL_ENV = "BUOY_EMBEDDING_MODEL"
REMOVED_EMBEDDING_MODEL_ENV = "TURBO_SEARCH_EMBEDDING_MODEL"
EMBEDDING_PRECISION_ENV = "BUOY_EMBEDDING_PRECISION"
REMOVED_EMBEDDING_PRECISION_ENV = "TURBO_SEARCH_EMBEDDING_PRECISION"
REMOVED_EMBEDDING_ENV_MAPPINGS = (
    (REMOVED_EMBEDDING_MODEL_ENV, EMBEDDING_MODEL_ENV),
    (REMOVED_EMBEDDING_PRECISION_ENV, EMBEDDING_PRECISION_ENV),
)


class RuntimeConfigError(ValueError):
    """Raised when non-secret runtime configuration is contradictory."""


def removed_embedding_environment_error(
    environment: Mapping[str, str] | None = None,
) -> str | None:
    """Return the value-redacted Buoy 0.4 diagnostic for removed variables."""

    source = os.environ if environment is None else environment
    present = [f"{old} -> {new}" for old, new in REMOVED_EMBEDDING_ENV_MAPPINGS if old in source]
    if not present:
        return None
    noun = "variable is" if len(present) == 1 else "variables are"
    return f"Removed environment {noun} not supported in Buoy 0.4.0: {'; '.join(present)}"


@dataclass(frozen=True)
class RuntimeConfig:
    """Non-secret runtime defaults for local and live commands."""

    region: str = DEFAULT_REGION
    namespace: str = DEFAULT_NAMESPACE
    embedding_model: str = DEFAULT_EMBEDDING_MODEL
    embedding_precision: str = DEFAULT_EMBEDDING_PRECISION


def load_config(
    *,
    warning_callback: Callable[[str], None] | None = None,
    ignore_environment_namespace: bool = False,
) -> RuntimeConfig:
    """Load non-secret runtime configuration from environment defaults.

    Deliberately excludes TURBOPUFFER_API_KEY so help and dry-run commands can be
    used safely without credentials. Removed branded embedding variables are
    rejected by CLI entry points before dispatch and never become configuration.
    """

    # Retain the keyword for source compatibility; removal emits no warnings.
    del warning_callback

    embedding_model = os.environ.get(EMBEDDING_MODEL_ENV, DEFAULT_EMBEDDING_MODEL)
    embedding_precision = os.environ.get(EMBEDDING_PRECISION_ENV, DEFAULT_EMBEDDING_PRECISION)
    if embedding_precision not in EMBEDDING_PRECISIONS:
        raise RuntimeConfigError(
            f"embedding precision must be one of: {', '.join(EMBEDDING_PRECISIONS)}"
        )

    return RuntimeConfig(
        region=os.environ.get("TURBOPUFFER_REGION", DEFAULT_REGION),
        namespace=(
            DEFAULT_NAMESPACE
            if ignore_environment_namespace
            else os.environ.get("TURBOPUFFER_NAMESPACE", DEFAULT_NAMESPACE)
        ),
        embedding_model=embedding_model,
        embedding_precision=embedding_precision,
    )
