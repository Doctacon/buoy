"""Local applied-state backend for generic site RAG indexing.

This module manages only local JSON state. It does not read credentials, load
embedding models, or call turbopuffer. The state store is the incremental diff
baseline for future plan/apply commands.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Literal

from turbo_search.crawler import validate_base_url
from turbo_search.plan_artifacts import stable_json_dumps

APPLIED_STATE_SCHEMA_VERSION = 1
DEFAULT_STATE_ROOT = Path(".turbo-search")
ROW_STATUS_ACTIVE = "active"
ROW_STATUS_RETAINED_STALE = "retained_stale"
ROW_STATUS_DELETED = "deleted"
VALID_ROW_STATUSES = {ROW_STATUS_ACTIVE, ROW_STATUS_RETAINED_STALE, ROW_STATUS_DELETED}

RowStatus = Literal["active", "retained_stale", "deleted"]
JsonObject = dict[str, Any]


class AppliedStateError(ValueError):
    """Raised when local applied state is invalid or incompatible."""


@dataclass(frozen=True)
class AppliedStateRow:
    """One row tracked by the local applied-state ledger."""

    row_id: str
    canonical_url: str
    page_hash: str
    chunk_hash: str
    embedding_text_hash: str
    plan_id: str
    applied_at: str
    status: RowStatus = ROW_STATUS_ACTIVE


@dataclass(frozen=True)
class AppliedState:
    """Local state for one site/namespace pair.

    ``first_apply`` is runtime metadata only. It is true when no state file was
    present and is intentionally omitted from persisted JSON.
    """

    schema_version: int
    site_id: str
    namespace: str
    base_url: str
    updated_at: str
    last_plan_id: str
    last_apply_id: str
    rows: list[AppliedStateRow] = field(default_factory=list)
    first_apply: bool = False


@dataclass(frozen=True)
class AppliedStatePaths:
    """Resolved local state paths for one site/namespace."""

    state_dir: Path
    history_dir: Path
    last_applied_path: Path

    def history_path(self, apply_id: str) -> Path:
        return self.history_dir / f"{safe_state_filename(apply_id)}.json"


def applied_state_paths(
    *,
    site_id: str,
    namespace: str,
    state_root: Path = DEFAULT_STATE_ROOT,
) -> AppliedStatePaths:
    """Return default local applied-state paths for a site/namespace."""

    safe_site_id = safe_state_component(site_id, label="site_id")
    safe_namespace = safe_state_component(namespace, label="namespace")
    state_dir = Path(state_root) / "state" / safe_site_id / safe_namespace
    return AppliedStatePaths(
        state_dir=state_dir,
        history_dir=state_dir / "history",
        last_applied_path=state_dir / "last-applied.json",
    )


def load_applied_state(
    *,
    site_id: str,
    namespace: str,
    base_url: str,
    state_root: Path = DEFAULT_STATE_ROOT,
) -> AppliedState:
    """Load local state or return an explicit first-apply empty state."""

    normalized_base_url = validate_base_url(base_url)
    paths = applied_state_paths(site_id=site_id, namespace=namespace, state_root=state_root)
    if not paths.last_applied_path.exists():
        return AppliedState(
            schema_version=APPLIED_STATE_SCHEMA_VERSION,
            site_id=site_id,
            namespace=namespace,
            base_url=normalized_base_url,
            updated_at="",
            last_plan_id="",
            last_apply_id="",
            rows=[],
            first_apply=True,
        )

    raw = json.loads(paths.last_applied_path.read_text(encoding="utf-8"))
    state = applied_state_from_json(raw)
    validate_applied_state(
        state,
        expected_site_id=site_id,
        expected_namespace=namespace,
        expected_base_url=normalized_base_url,
    )
    return AppliedState(
        schema_version=state.schema_version,
        site_id=state.site_id,
        namespace=state.namespace,
        base_url=state.base_url,
        updated_at=state.updated_at,
        last_plan_id=state.last_plan_id,
        last_apply_id=state.last_apply_id,
        rows=state.rows,
        first_apply=False,
    )


def save_applied_state(
    state: AppliedState,
    *,
    state_root: Path = DEFAULT_STATE_ROOT,
) -> AppliedStatePaths:
    """Persist local state history and atomically update ``last-applied.json``.

    History and last-applied writes are separate files. ``last-applied.json`` is
    replaced only after JSON serialization succeeds and the target directory is
    prepared. Callers should invoke this only after the corresponding live apply
    operations have succeeded.
    """

    validate_applied_state(
        state,
        expected_site_id=state.site_id,
        expected_namespace=state.namespace,
        expected_base_url=state.base_url,
    )
    if not state.last_apply_id:
        raise AppliedStateError("applied state last_apply_id is required before saving")

    paths = applied_state_paths(site_id=state.site_id, namespace=state.namespace, state_root=state_root)
    paths.history_dir.mkdir(parents=True, exist_ok=True)
    payload = applied_state_to_json(state)
    _atomic_write_json(paths.history_path(state.last_apply_id), payload)
    _atomic_write_json(paths.last_applied_path, payload)
    return paths


def build_applied_state(
    *,
    site_id: str,
    namespace: str,
    base_url: str,
    last_plan_id: str,
    last_apply_id: str,
    rows: list[AppliedStateRow],
    updated_at: str | None = None,
) -> AppliedState:
    """Construct an applied state with normalized URL and timestamp defaults."""

    return AppliedState(
        schema_version=APPLIED_STATE_SCHEMA_VERSION,
        site_id=site_id,
        namespace=namespace,
        base_url=validate_base_url(base_url),
        updated_at=updated_at or datetime.now(timezone.utc).isoformat(),
        last_plan_id=last_plan_id,
        last_apply_id=last_apply_id,
        rows=rows,
        first_apply=False,
    )


def applied_state_to_json(state: AppliedState) -> JsonObject:
    """Return the persisted JSON representation of applied state."""

    payload = asdict(state)
    payload.pop("first_apply", None)
    return normalize_state_json(payload)


def applied_state_from_json(payload: JsonObject) -> AppliedState:
    """Parse local state JSON into typed state objects."""

    if not isinstance(payload, dict):
        raise AppliedStateError("applied state must be a JSON object")
    rows_payload = payload.get("rows", [])
    if not isinstance(rows_payload, list):
        raise AppliedStateError("applied state rows must be a list")
    rows = [applied_state_row_from_json(row, index=index) for index, row in enumerate(rows_payload)]
    try:
        return AppliedState(
            schema_version=int(payload["schema_version"]),
            site_id=str(payload["site_id"]),
            namespace=str(payload["namespace"]),
            base_url=validate_base_url(str(payload["base_url"])),
            updated_at=str(payload.get("updated_at", "")),
            last_plan_id=str(payload.get("last_plan_id", "")),
            last_apply_id=str(payload.get("last_apply_id", "")),
            rows=rows,
            first_apply=False,
        )
    except KeyError as exc:
        raise AppliedStateError(f"applied state missing required field: {exc.args[0]}") from exc
    except (TypeError, ValueError) as exc:
        raise AppliedStateError(f"applied state is invalid: {exc}") from exc


def applied_state_row_from_json(payload: Any, *, index: int) -> AppliedStateRow:
    if not isinstance(payload, dict):
        raise AppliedStateError(f"applied state row {index} must be a JSON object")
    try:
        status = str(payload.get("status", ROW_STATUS_ACTIVE))
        if status not in VALID_ROW_STATUSES:
            raise AppliedStateError(
                f"applied state row {index} has invalid status {status!r}; "
                f"expected one of {sorted(VALID_ROW_STATUSES)}"
            )
        return AppliedStateRow(
            row_id=str(payload["row_id"]),
            canonical_url=str(payload["canonical_url"]),
            page_hash=str(payload["page_hash"]),
            chunk_hash=str(payload["chunk_hash"]),
            embedding_text_hash=str(payload["embedding_text_hash"]),
            plan_id=str(payload["plan_id"]),
            applied_at=str(payload["applied_at"]),
            status=status,  # type: ignore[arg-type]
        )
    except KeyError as exc:
        raise AppliedStateError(f"applied state row {index} missing required field: {exc.args[0]}") from exc


def validate_applied_state(
    state: AppliedState,
    *,
    expected_site_id: str,
    expected_namespace: str,
    expected_base_url: str,
) -> None:
    """Validate schema and compatibility for loaded/saved state."""

    if state.schema_version != APPLIED_STATE_SCHEMA_VERSION:
        raise AppliedStateError(
            f"unsupported applied state schema_version {state.schema_version}; "
            f"expected {APPLIED_STATE_SCHEMA_VERSION}"
        )
    if state.site_id != expected_site_id:
        raise AppliedStateError(
            f"applied state site_id mismatch: expected {expected_site_id!r}, found {state.site_id!r}"
        )
    if state.namespace != expected_namespace:
        raise AppliedStateError(
            f"applied state namespace mismatch: expected {expected_namespace!r}, found {state.namespace!r}"
        )
    normalized_expected_base_url = validate_base_url(expected_base_url)
    if validate_base_url(state.base_url) != normalized_expected_base_url:
        raise AppliedStateError(
            f"applied state base_url mismatch: expected {normalized_expected_base_url!r}, found {state.base_url!r}"
        )
    for index, row in enumerate(state.rows):
        if row.status not in VALID_ROW_STATUSES:
            raise AppliedStateError(
                f"applied state row {index} has invalid status {row.status!r}; "
                f"expected one of {sorted(VALID_ROW_STATUSES)}"
            )
        for field_name in (
            "row_id",
            "canonical_url",
            "page_hash",
            "chunk_hash",
            "embedding_text_hash",
            "plan_id",
            "applied_at",
        ):
            if not getattr(row, field_name):
                raise AppliedStateError(f"applied state row {index} has empty {field_name}")


def normalize_state_json(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): normalize_state_json(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [normalize_state_json(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def safe_state_component(value: str, *, label: str) -> str:
    """Validate one path component used by local state paths."""

    if not value or value in {".", ".."}:
        raise ValueError(f"{label} must be a non-empty path component")
    if Path(value).is_absolute() or "/" in value or "\\" in value:
        raise ValueError(f"{label} must not contain path separators")
    return value


def safe_state_filename(value: str) -> str:
    """Return a safe filename stem for an apply ID."""

    return safe_state_component(value, label="apply_id").replace(":", "-")


def _atomic_write_json(path: Path, payload: JsonObject) -> None:
    """Write JSON to a temp file in the same directory, then replace target."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temp_path.write_text(stable_json_dumps(payload, indent=2) + "\n", encoding="utf-8")
    try:
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()
