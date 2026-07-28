"""Compact local DuckDB applied state for generic site RAG indexing.

The state store does not read credentials, load embedding models, or call
Turbopuffer. It is the local incremental-diff baseline for future plan/apply
commands.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
import os
from pathlib import Path
import stat
import sys
from typing import Iterator, Literal

import duckdb
import portalocker

from buoy_search.source_url import validate_base_url

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


@dataclass(frozen=True)
class AppliedStateSummary:
    """Constant-size metadata and status counts for inventory surfaces."""

    schema_version: int
    site_id: str
    namespace: str
    base_url: str
    updated_at: str
    last_plan_id: str
    last_apply_id: str
    active_rows: int
    retained_stale_rows: int
    deleted_rows: int
    total_rows: int


def applied_state_paths(
    *,
    site_id: str,
    namespace: str,
    state_root: Path = DEFAULT_STATE_ROOT,
) -> AppliedStatePaths:
    """Return local DuckDB paths for one state ledger."""

    safe_site_id = safe_state_component(site_id, label="site_id")
    safe_namespace = safe_state_component(namespace, label="namespace")
    state_dir = Path(state_root) / "state" / safe_site_id / safe_namespace
    return AppliedStatePaths(
        state_dir=state_dir,
        database_path=state_dir / "state.duckdb",
        lock_path=state_dir / "apply.lock",
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
    """Load current DuckDB state or return a first-apply empty state."""

    normalized_base_url = validate_base_url(base_url)
    paths = applied_state_paths(site_id=site_id, namespace=namespace, state_root=state_root)
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


def load_applied_state_summary(
    *,
    database_path: Path,
    state_root: Path = DEFAULT_STATE_ROOT,
) -> AppliedStateSummary:
    """Inspect one state database without materializing its applied rows."""

    database_path = Path(database_path)
    state_root = Path(state_root)
    with _bind_summary_database(
        database_path=database_path, state_root=state_root
    ) as binding:
        try:
            with duckdb.connect(str(database_path), read_only=True) as connection:
                _validate_database_schema(connection)
                metadata_rows = connection.execute(
                    """
                    SELECT schema_version, site_id, namespace, base_url, updated_at,
                           last_plan_id, last_apply_id
                    FROM state_metadata
                    """
                ).fetchall()
                if len(metadata_rows) != 1:
                    raise AppliedStateError(
                        "DuckDB applied state must contain exactly one metadata row"
                    )
                metadata = metadata_rows[0]
                counts = connection.execute(
                    """
                    SELECT count(*) FILTER (WHERE status = 'active'),
                           count(*) FILTER (WHERE status = 'retained_stale'),
                           count(*) FILTER (WHERE status = 'deleted'),
                           count(*)
                    FROM applied_rows
                    """
                ).fetchone()
                if counts is None or len(counts) != 4:
                    raise AppliedStateError("DuckDB applied-state counts are invalid")
        except duckdb.Error as exc:
            raise AppliedStateError(
                f"could not load DuckDB applied-state summary: {exc}"
            ) from exc

        _assert_summary_database_identity(binding)
        schema_version = int(metadata[0])
        metadata_site_id = str(metadata[1])
        metadata_namespace = str(metadata[2])
        normalized_base_url = validate_base_url(str(metadata[3]))
        if metadata_site_id != binding.site_id or metadata_namespace != binding.namespace:
            raise AppliedStateError("applied state path does not match its identity")
        expected_path = applied_state_paths(
            site_id=metadata_site_id,
            namespace=metadata_namespace,
            state_root=state_root,
        ).database_path.absolute()
        if database_path.absolute() != expected_path:
            raise AppliedStateError("applied state path does not match its identity")
        summary = AppliedStateSummary(
            schema_version=schema_version,
            site_id=metadata_site_id,
            namespace=metadata_namespace,
            base_url=normalized_base_url,
            updated_at=str(metadata[4]),
            last_plan_id=str(metadata[5]),
            last_apply_id=str(metadata[6]),
            active_rows=int(counts[0]),
            retained_stale_rows=int(counts[1]),
            deleted_rows=int(counts[2]),
            total_rows=int(counts[3]),
        )
        validate_applied_state(
            AppliedState(
                schema_version=summary.schema_version,
                site_id=summary.site_id,
                namespace=summary.namespace,
                base_url=summary.base_url,
                updated_at=summary.updated_at,
                last_plan_id=summary.last_plan_id,
                last_apply_id=summary.last_apply_id,
            ),
            expected_site_id=binding.site_id,
            expected_namespace=binding.namespace,
            expected_base_url=normalized_base_url,
        )
        if min(
            summary.active_rows,
            summary.retained_stale_rows,
            summary.deleted_rows,
            summary.total_rows,
        ) < 0 or (
            summary.active_rows
            + summary.retained_stale_rows
            + summary.deleted_rows
            != summary.total_rows
        ):
            raise AppliedStateError(
                "applied state contains an unknown status or contradictory row counts"
            )
        return summary


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


def safe_state_component(value: str, *, label: str) -> str:
    """Validate one path component used by local state paths."""

    if not value or value in {".", ".."}:
        raise ValueError(f"{label} must be a non-empty path component")
    if Path(value).is_absolute() or "/" in value or "\\" in value:
        raise ValueError(f"{label} must not contain path separators")
    return value


@dataclass(frozen=True)
class _SummaryBoundPath:
    path: Path
    descriptor: int
    identity: tuple[int, int, int, int, int]
    directory: bool


@dataclass(frozen=True)
class _SummaryDatabaseBinding:
    site_id: str
    namespace: str
    paths: tuple[_SummaryBoundPath, ...]


@contextmanager
def _bind_summary_database(
    *, database_path: Path, state_root: Path
) -> Iterator[_SummaryDatabaseBinding]:
    """Hold the database and each parent entry across pathname-based inspection."""

    root = state_root.absolute()
    database = database_path.absolute()
    try:
        relative = database.relative_to(root)
    except ValueError as exc:
        raise AppliedStateError("applied state escapes its configured root") from exc
    if (
        len(relative.parts) != 4
        or relative.parts[0] != "state"
        or relative.parts[3] != "state.duckdb"
    ):
        raise AppliedStateError("applied state path does not match its identity")
    site_id = safe_state_component(relative.parts[1], label="site_id")
    namespace = safe_state_component(relative.parts[2], label="namespace")

    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    file_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    opened: list[_SummaryBoundPath] = []
    try:
        root_parent = root.parent
        parent_descriptor = os.open(root_parent, directory_flags)
        opened.append(_summary_bound_path(root_parent, parent_descriptor, directory=True))
        parent = parent_descriptor
        components = (
            (root, root.name or "."),
            (root / "state", "state"),
            (root / "state" / site_id, site_id),
            (root / "state" / site_id / namespace, namespace),
        )
        for path, name in components:
            descriptor = os.open(name, directory_flags, dir_fd=parent)
            bound = _summary_bound_path(path, descriptor, directory=True)
            opened.append(bound)
            parent = descriptor
        try:
            database_descriptor = os.open("state.duckdb", file_flags, dir_fd=parent)
        except OSError as exc:
            raise AppliedStateError(
                "applied state must be a regular no-follow file"
            ) from exc
        opened.append(
            _summary_bound_path(database, database_descriptor, directory=False)
        )
        binding = _SummaryDatabaseBinding(site_id, namespace, tuple(opened))
        _assert_summary_database_identity(binding)
        yield binding
    except AppliedStateError:
        raise
    except OSError as exc:
        raise AppliedStateError("applied state contains an unsafe no-follow path") from exc
    finally:
        active_error = sys.exc_info()[0] is not None
        close_error: OSError | None = None
        for item in reversed(opened):
            try:
                os.close(item.descriptor)
            except OSError as exc:
                close_error = close_error or exc
        if close_error is not None and not active_error:
            raise AppliedStateError("could not close applied-state summary descriptors") from close_error


def _summary_bound_path(
    path: Path, descriptor: int, *, directory: bool
) -> _SummaryBoundPath:
    metadata = os.fstat(descriptor)
    expected_kind = stat.S_ISDIR if directory else stat.S_ISREG
    if not expected_kind(metadata.st_mode):
        os.close(descriptor)
        raise AppliedStateError(
            "applied-state path contains an unsafe directory"
            if directory
            else "applied state must be a regular no-follow file"
        )
    return _SummaryBoundPath(
        path=path,
        descriptor=descriptor,
        identity=_summary_mutation_identity(metadata),
        directory=directory,
    )


def _summary_mutation_identity(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _assert_summary_database_identity(binding: _SummaryDatabaseBinding) -> None:
    for item in binding.paths:
        opened = os.fstat(item.descriptor)
        current = item.path.lstat()
        expected_kind = stat.S_ISDIR if item.directory else stat.S_ISREG
        if (
            not expected_kind(opened.st_mode)
            or not expected_kind(current.st_mode)
            or stat.S_ISLNK(current.st_mode)
            or _summary_mutation_identity(opened) != item.identity
            or _summary_mutation_identity(current) != item.identity
        ):
            raise AppliedStateError("applied state changed during summary inspection")


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
