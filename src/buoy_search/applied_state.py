"""Compact local DuckDB applied state for generic site RAG indexing.

The state store does not read credentials, load embedding models, or call
Turbopuffer. It is the local incremental-diff baseline for future plan/apply
commands.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Iterator, Literal
from uuid import uuid4

import duckdb
import portalocker

from buoy_search.crawler import validate_base_url

APPLIED_STATE_SCHEMA_VERSION = 1
DUCKDB_STATE_SCHEMA_VERSION = 1
DEFAULT_STATE_ROOT = Path(".buoy")
LEGACY_STATE_ROOT = Path(".turbo-search")
LEGACY_STATE_ROOT_WARNING = (
    "Warning: using legacy state root .turbo-search in place; pass --state-root explicitly "
    "to choose a root. No state was migrated."
)
ROW_STATUS_ACTIVE = "active"
ROW_STATUS_RETAINED_STALE = "retained_stale"
ROW_STATUS_DELETED = "deleted"
VALID_ROW_STATUSES = {ROW_STATUS_ACTIVE, ROW_STATUS_RETAINED_STALE, ROW_STATUS_DELETED}

RowStatus = Literal["active", "retained_stale", "deleted"]
JsonObject = dict[str, Any]


class AppliedStateError(ValueError):
    """Raised when local applied state is invalid or incompatible."""


def resolve_state_root(explicit_state_root: Path | None) -> tuple[Path, str | None]:
    """Resolve Buoy's implicit state root without moving or copying state."""

    if explicit_state_root is not None:
        return Path(explicit_state_root), None

    current_exists = DEFAULT_STATE_ROOT.exists()
    legacy_exists = LEGACY_STATE_ROOT.exists()
    if current_exists and legacy_exists:
        raise AppliedStateError(
            "both implicit state roots exist: .buoy and .turbo-search; "
            "pass --state-root explicitly to choose one"
        )
    if legacy_exists:
        return LEGACY_STATE_ROOT, LEGACY_STATE_ROOT_WARNING
    return DEFAULT_STATE_ROOT, None


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
class ApplyRunSummary:
    """Small durable record of one successful approved apply."""

    apply_id: str
    plan_id: str
    applied_at: str
    rows_upserted: int
    rows_deleted: int
    retained_stale_rows: int


@dataclass(frozen=True)
class AppliedState:
    """Local state for one site/namespace pair.

    ``first_apply`` is runtime metadata only. It is true when the local
    database has no active state and is intentionally not persisted as a
    database field.
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
    """Resolved storage locations for one site/namespace."""

    state_dir: Path
    database_path: Path
    lock_path: Path
    legacy_state_path: Path
    legacy_archive_path: Path


def applied_state_paths(
    *,
    site_id: str,
    namespace: str,
    state_root: Path = DEFAULT_STATE_ROOT,
) -> AppliedStatePaths:
    """Return local DuckDB and legacy-cleanup paths for one state ledger."""

    safe_site_id = safe_state_component(site_id, label="site_id")
    safe_namespace = safe_state_component(namespace, label="namespace")
    state_dir = Path(state_root) / "state" / safe_site_id / safe_namespace
    return AppliedStatePaths(
        state_dir=state_dir,
        database_path=state_dir / "state.duckdb",
        lock_path=state_dir / "apply.lock",
        legacy_state_path=state_dir / "last-applied.json",
        legacy_archive_path=state_dir / "legacy-json" / "last-applied.json",
    )


@contextmanager
def acquire_namespace_apply_lock(
    *,
    site_id: str,
    namespace: str,
    state_root: Path = DEFAULT_STATE_ROOT,
) -> Iterator[None]:
    """Fail fast when an approved apply already owns this namespace."""

    paths = applied_state_paths(site_id=site_id, namespace=namespace, state_root=state_root)
    paths.state_dir.mkdir(parents=True, exist_ok=True)
    try:
        with portalocker.Lock(
            str(paths.lock_path),
            mode="a+",
            timeout=0,
            fail_when_locked=True,
        ):
            yield
    except portalocker.exceptions.LockException as exc:
        raise AppliedStateError(
            f"approved apply is already in progress for namespace {namespace!r}; retry after it finishes"
        ) from exc


def load_applied_state(
    *,
    site_id: str,
    namespace: str,
    base_url: str,
    state_root: Path = DEFAULT_STATE_ROOT,
) -> AppliedState:
    """Load current DuckDB state or return a first-apply empty state.

    A legacy JSON ledger is deleted and replaced with an intentionally empty
    database. It is not imported because it may describe remote rows that no
    longer exist.
    """

    normalized_base_url = validate_base_url(base_url)
    paths = applied_state_paths(site_id=site_id, namespace=namespace, state_root=state_root)
    _migrate_legacy_state(paths)
    if not paths.database_path.exists():
        return _first_apply_state(site_id=site_id, namespace=namespace, base_url=normalized_base_url)

    try:
        with duckdb.connect(str(paths.database_path), read_only=True) as connection:
            _validate_database_schema(connection)
            metadata_rows = connection.execute(
                """
                SELECT schema_version, site_id, namespace, base_url, updated_at, last_plan_id, last_apply_id
                FROM state_metadata
                """
            ).fetchall()
            row_count = int(connection.execute("SELECT count(*) FROM applied_rows").fetchone()[0])
            if not metadata_rows:
                if row_count:
                    raise AppliedStateError("DuckDB applied rows exist without state metadata")
                return _first_apply_state(site_id=site_id, namespace=namespace, base_url=normalized_base_url)
            if len(metadata_rows) != 1:
                if row_count:
                    raise AppliedStateError("DuckDB applied rows exist without exactly one metadata row")
                raise AppliedStateError("DuckDB applied state must contain exactly one metadata row")
            metadata = metadata_rows[0]
            state = AppliedState(
                schema_version=int(metadata[0]),
                site_id=str(metadata[1]),
                namespace=str(metadata[2]),
                base_url=validate_base_url(str(metadata[3])),
                updated_at=str(metadata[4]),
                last_plan_id=str(metadata[5]),
                last_apply_id=str(metadata[6]),
                rows=[
                    AppliedStateRow(
                        row_id=str(row_id),
                        canonical_url=str(canonical_url),
                        page_hash=str(page_hash),
                        chunk_hash=str(chunk_hash),
                        embedding_text_hash=str(embedding_text_hash),
                        plan_id=str(plan_id),
                        applied_at=str(applied_at),
                        status=str(status),  # type: ignore[arg-type]
                    )
                    for row_id, canonical_url, page_hash, chunk_hash, embedding_text_hash, plan_id, applied_at, status in connection.execute(
                        """
                        SELECT row_id, canonical_url, page_hash, chunk_hash, embedding_text_hash,
                               plan_id, applied_at, status
                        FROM applied_rows
                        ORDER BY canonical_url, row_id
                        """
                    ).fetchall()
                ],
                first_apply=False,
            )
    except duckdb.Error as exc:
        raise AppliedStateError(f"could not load DuckDB applied state: {exc}") from exc

    validate_applied_state(
        state,
        expected_site_id=site_id,
        expected_namespace=namespace,
        expected_base_url=normalized_base_url,
    )
    return state


def save_applied_state(
    state: AppliedState,
    *,
    state_root: Path = DEFAULT_STATE_ROOT,
    apply_run: ApplyRunSummary | None = None,
) -> AppliedStatePaths:
    """Atomically replace current rows and optionally append one apply summary.

    Callers must invoke this only after the corresponding remote work has
    succeeded. The later apply-integration ticket supplies exact run counts;
    the store deliberately does not invent them.
    """

    validate_applied_state(
        state,
        expected_site_id=state.site_id,
        expected_namespace=state.namespace,
        expected_base_url=state.base_url,
    )
    if not state.last_apply_id:
        raise AppliedStateError("applied state last_apply_id is required before saving")
    if apply_run is not None:
        _validate_apply_run(apply_run, state=state)

    paths = applied_state_paths(site_id=state.site_id, namespace=state.namespace, state_root=state_root)
    _migrate_legacy_state(paths)
    paths.state_dir.mkdir(parents=True, exist_ok=True)
    try:
        with duckdb.connect(str(paths.database_path)) as connection:
            _initialize_schema(connection)
            connection.execute("BEGIN TRANSACTION")
            try:
                connection.execute("DELETE FROM applied_rows")
                if state.rows:
                    connection.executemany(
                        """
                        INSERT INTO applied_rows (
                            row_id, canonical_url, page_hash, chunk_hash, embedding_text_hash,
                            plan_id, applied_at, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        [
                            (
                                row.row_id,
                                row.canonical_url,
                                row.page_hash,
                                row.chunk_hash,
                                row.embedding_text_hash,
                                row.plan_id,
                                row.applied_at,
                                row.status,
                            )
                            for row in state.rows
                        ],
                    )
                connection.execute("DELETE FROM state_metadata")
                connection.execute(
                    """
                    INSERT INTO state_metadata (
                        schema_version, site_id, namespace, base_url, updated_at, last_plan_id, last_apply_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        APPLIED_STATE_SCHEMA_VERSION,
                        state.site_id,
                        state.namespace,
                        state.base_url,
                        state.updated_at,
                        state.last_plan_id,
                        state.last_apply_id,
                    ],
                )
                if apply_run is not None:
                    connection.execute(
                        """
                        INSERT INTO apply_runs (
                            apply_id, plan_id, applied_at, rows_upserted, rows_deleted, retained_stale_rows
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        [
                            apply_run.apply_id,
                            apply_run.plan_id,
                            apply_run.applied_at,
                            apply_run.rows_upserted,
                            apply_run.rows_deleted,
                            apply_run.retained_stale_rows,
                        ],
                    )
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise
    except duckdb.Error as exc:
        raise AppliedStateError(f"could not save DuckDB applied state: {exc}") from exc
    return paths


def load_apply_run_summaries(
    *,
    site_id: str,
    namespace: str,
    state_root: Path = DEFAULT_STATE_ROOT,
) -> list[ApplyRunSummary]:
    """Return retained compact apply summaries oldest first."""

    paths = applied_state_paths(site_id=site_id, namespace=namespace, state_root=state_root)
    if not paths.database_path.exists():
        return []
    try:
        with duckdb.connect(str(paths.database_path), read_only=True) as connection:
            return [
                ApplyRunSummary(
                    apply_id=str(apply_id),
                    plan_id=str(plan_id),
                    applied_at=str(applied_at),
                    rows_upserted=int(rows_upserted),
                    rows_deleted=int(rows_deleted),
                    retained_stale_rows=int(retained_stale_rows),
                )
                for apply_id, plan_id, applied_at, rows_upserted, rows_deleted, retained_stale_rows in connection.execute(
                    """
                    SELECT apply_id, plan_id, applied_at, rows_upserted, rows_deleted, retained_stale_rows
                    FROM apply_runs
                    ORDER BY applied_at, apply_id
                    """
                ).fetchall()
            ]
    except duckdb.Error as exc:
        raise AppliedStateError(f"could not load DuckDB apply summaries: {exc}") from exc


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
    """Serialize legacy JSON state for archive fixtures and compatibility tests."""

    payload = asdict(state)
    payload.pop("first_apply", None)
    return normalize_state_json(payload)


def applied_state_from_json(payload: JsonObject) -> AppliedState:
    """Parse a legacy JSON state payload without activating it."""

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


def _first_apply_state(*, site_id: str, namespace: str, base_url: str) -> AppliedState:
    return AppliedState(
        schema_version=APPLIED_STATE_SCHEMA_VERSION,
        site_id=site_id,
        namespace=namespace,
        base_url=base_url,
        updated_at="",
        last_plan_id="",
        last_apply_id="",
        rows=[],
        first_apply=True,
    )


def _migrate_legacy_state(paths: AppliedStatePaths) -> None:
    """Delete legacy JSON only after installing an empty valid database."""

    _delete_legacy_archive(paths)
    if paths.database_path.exists():
        if paths.legacy_state_path.exists():
            paths.legacy_state_path.unlink()
        return
    if not paths.legacy_state_path.exists():
        return
    paths.state_dir.mkdir(parents=True, exist_ok=True)
    _initialize_empty_database(paths)
    paths.legacy_state_path.unlink()


def _initialize_empty_database(paths: AppliedStatePaths) -> None:
    """Atomically install a valid empty DuckDB ledger without risking legacy state."""

    temporary_path = paths.database_path.with_name(f".{paths.database_path.name}.tmp-{uuid4().hex}")
    try:
        with duckdb.connect(str(temporary_path)) as connection:
            _initialize_schema(connection)
        os.replace(temporary_path, paths.database_path)
    except (duckdb.Error, OSError) as exc:
        raise AppliedStateError(f"could not initialize DuckDB applied state: {exc}") from exc
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _delete_legacy_archive(paths: AppliedStatePaths) -> None:
    """Remove a legacy directory left by the superseded migration."""

    if paths.legacy_archive_path.is_file():
        paths.legacy_archive_path.unlink()
    archive_dir = paths.legacy_archive_path.parent
    if archive_dir.is_symlink():
        archive_dir.unlink()
    elif archive_dir.is_dir() and not any(archive_dir.iterdir()):
        archive_dir.rmdir()


def _initialize_schema(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS state_schema (
            schema_version INTEGER PRIMARY KEY
        )
        """
    )
    connection.execute("INSERT OR IGNORE INTO state_schema VALUES (?)", [DUCKDB_STATE_SCHEMA_VERSION])
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS state_metadata (
            schema_version INTEGER NOT NULL,
            site_id VARCHAR NOT NULL,
            namespace VARCHAR NOT NULL,
            base_url VARCHAR NOT NULL,
            updated_at VARCHAR NOT NULL,
            last_plan_id VARCHAR NOT NULL,
            last_apply_id VARCHAR NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS applied_rows (
            row_id VARCHAR PRIMARY KEY,
            canonical_url VARCHAR NOT NULL,
            page_hash VARCHAR NOT NULL,
            chunk_hash VARCHAR NOT NULL,
            embedding_text_hash VARCHAR NOT NULL,
            plan_id VARCHAR NOT NULL,
            applied_at VARCHAR NOT NULL,
            status VARCHAR NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS apply_runs (
            apply_id VARCHAR PRIMARY KEY,
            plan_id VARCHAR NOT NULL,
            applied_at VARCHAR NOT NULL,
            rows_upserted BIGINT NOT NULL,
            rows_deleted BIGINT NOT NULL,
            retained_stale_rows BIGINT NOT NULL
        )
        """
    )


def _validate_database_schema(connection: duckdb.DuckDBPyConnection) -> None:
    rows = connection.execute("SELECT schema_version FROM state_schema").fetchall()
    if rows != [(DUCKDB_STATE_SCHEMA_VERSION,)]:
        raise AppliedStateError(
            f"unsupported DuckDB applied state schema version: {rows!r}; "
            f"expected {DUCKDB_STATE_SCHEMA_VERSION}"
        )


def _validate_apply_run(apply_run: ApplyRunSummary, *, state: AppliedState) -> None:
    if not apply_run.apply_id:
        raise AppliedStateError("apply run apply_id is required")
    if apply_run.plan_id != state.last_plan_id:
        raise AppliedStateError("apply run plan_id must match applied state last_plan_id")
    if apply_run.apply_id != state.last_apply_id:
        raise AppliedStateError("apply run apply_id must match applied state last_apply_id")
    if apply_run.applied_at != state.updated_at:
        raise AppliedStateError("apply run applied_at must match applied state updated_at")
    for field_name in ("rows_upserted", "rows_deleted", "retained_stale_rows"):
        if getattr(apply_run, field_name) < 0:
            raise AppliedStateError(f"apply run {field_name} must be non-negative")
