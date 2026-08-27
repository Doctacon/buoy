"""Private DuckDB-v1 persistence for sanitized local telemetry traces.

This module is deliberately independent from retrieval instrumentation.  It
accepts only the typed, already-sanitized rows produced by
``telemetry_envelope`` and owns the verified DuckDB write boundary.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import os
from pathlib import Path
import stat
from typing import TYPE_CHECKING, Callable, Iterator, Literal, Protocol

import duckdb

from buoy_search.telemetry.queue import (
    QueueLockTimeout,
    UnreadablePathError,
    UnsafePathError,
    UnsupportedPlatformError,
    database_write_lock,
    fsync_directory,
    open_private_directory_at,
    open_private_file_at,
    open_verified_directory,
    safe_link_at,
    safe_rmdir_at,
    safe_unlink_at,
    scan_fixed_private_inventory,
    stat_private_entry_at,
    verify_private_file_fd,
)

if TYPE_CHECKING:
    from buoy_search.telemetry.envelope import TraceRows
    from buoy_search.telemetry.queue import TelemetryPaths


TELEMETRY_SCHEMA_VERSION = 2
DATABASE_BASENAME = "telemetry.duckdb"
DATABASE_WAL_BASENAME = "telemetry.duckdb.wal"
DATABASE_INIT_DIRECTORY = "database-init-v1"
DATABASE_MIGRATION_DIRECTORY = "database-migrate-v2"
DATABASE_BACKUP_BASENAME = "telemetry-v1-backup.duckdb"
_INITIALIZATION_SCRATCH_NAMES = frozenset(
    {DATABASE_BASENAME, DATABASE_WAL_BASENAME}
)
_MIGRATION_SCRATCH_NAMES = frozenset(
    {
        DATABASE_BASENAME,
        DATABASE_WAL_BASENAME,
        DATABASE_BACKUP_BASENAME,
    }
)
DATABASE_INIT_MAX_BYTES = 16_777_216
MIGRATION_BATCH_SIZE = 128

StoreOutcome = Literal["committed", "replayed", "conflict"]

_SAFE_DUCKDB_CONFIG = {
    "enable_external_access": "false",
    "autoinstall_known_extensions": "false",
    "autoload_known_extensions": "false",
    "allow_community_extensions": "false",
}


class TelemetryStoreError(RuntimeError):
    """Base class whose messages are bounded and safe to classify."""


class StoreBusyError(TelemetryStoreError):
    """The dedicated telemetry database lock was not acquired in time."""


class StoreIncompatibleError(TelemetryStoreError):
    """The database is valid DuckDB but not the exact governed v1 schema."""


class StoreUnsafeError(TelemetryStoreError):
    """A fixed telemetry path failed its ownership/type/link boundary."""


class StoreUnreadableError(TelemetryStoreError):
    """DuckDB or the local filesystem could not read a governed store."""


class StoreTerminalAbsentError(StoreUnreadableError):
    """The read-only recovery probe found no trace terminal state."""


class StoreWriteError(TelemetryStoreError):
    """A governed trace could not be committed to a compatible store."""


class StoreUpgradeRequiredError(TelemetryStoreError):
    """A valid version-2 trace is pending behind an exact version-1 store."""


@dataclass(frozen=True)
class StoreSnapshot:
    """Verified content-free facts for the writer's durable state file."""

    schema_version: int
    persisted_runs_snapshot: int
    database_device: int
    database_inode: int
    database_bytes: int


@dataclass(frozen=True)
class StoreAppendResult:
    """One store outcome, verified snapshot, and durability degradation."""

    outcome: StoreOutcome
    snapshot: StoreSnapshot
    durability_degraded: bool = False


@dataclass(frozen=True)
class StoreMigrationResult:
    """Content-free counts from one exact version-1 to version-2 migration."""

    runs: int
    spans: int
    events: int
    backup_present: bool
    durability_degraded: bool = False


@dataclass(frozen=True)
class StoreReconcileResult:
    """Verified exact-v2 facts after already-current scratch recovery."""

    snapshot: StoreSnapshot
    backup_present: bool
    scratch_recovered: bool = False
    durability_degraded: bool = False


@dataclass(frozen=True)
class _V1ContentIdentity:
    counts: tuple[int, int, int]
    sha256: str


@dataclass(frozen=True)
class _V2ContentIdentity:
    counts: tuple[int, int, int, int]
    sha256: str


class _RowsLike(Protocol):
    run: tuple[object, ...]
    spans: tuple[tuple[object, ...], ...]
    events: tuple[tuple[object, ...], ...]


_V1_TABLE_LAYOUTS: dict[
    str,
    tuple[tuple[str, str, bool, bool], ...],
] = {
    "telemetry_metadata": (
        ("singleton", "BOOLEAN", True, True),
        ("schema_version", "INTEGER", True, False),
        ("created_at", "TIMESTAMP", True, False),
        ("runs_view_sha256", "VARCHAR", True, False),
        ("stage_view_sha256", "VARCHAR", True, False),
    ),
    "trace_runs": (
        ("trace_id", "VARCHAR", True, True),
        ("root_span_id", "VARCHAR", True, False),
        ("started_at", "TIMESTAMP", True, False),
        ("ended_at", "TIMESTAMP", True, False),
        ("duration_ms", "DOUBLE", True, False),
        ("retrieval_mode", "VARCHAR", True, False),
        ("outcome", "VARCHAR", True, False),
        ("hit_count", "INTEGER", True, False),
        ("namespace_count", "INTEGER", True, False),
        ("initial_fanout", "INTEGER", True, False),
        ("final_fanout", "INTEGER", True, False),
        ("failure_count", "INTEGER", True, False),
        ("incomplete", "BOOLEAN", True, False),
        ("widened", "BOOLEAN", True, False),
        ("fallback_reason", "VARCHAR", False, False),
        ("evidence_status", "VARCHAR", False, False),
        ("embedding_model", "VARCHAR", True, False),
        ("embedding_precision", "VARCHAR", True, False),
        ("top_k", "INTEGER", True, False),
        ("candidates", "INTEGER", True, False),
        ("buoy_version", "VARCHAR", True, False),
        ("observation_schema_version", "INTEGER", True, False),
    ),
    "spans": (
        ("trace_id", "VARCHAR", True, True),
        ("span_id", "VARCHAR", True, True),
        ("parent_span_id", "VARCHAR", False, False),
        ("name", "VARCHAR", True, False),
        ("started_at", "TIMESTAMP", True, False),
        ("ended_at", "TIMESTAMP", True, False),
        ("duration_ms", "DOUBLE", True, False),
        ("status_code", "VARCHAR", True, False),
        ("attributes", "JSON", True, False),
    ),
    "span_events": (
        ("trace_id", "VARCHAR", True, True),
        ("span_id", "VARCHAR", True, True),
        ("event_index", "INTEGER", True, True),
        ("name", "VARCHAR", True, False),
        ("occurred_at", "TIMESTAMP", True, False),
        ("attributes", "JSON", True, False),
    ),
}

_V1_VIEW_LAYOUTS: dict[str, tuple[tuple[str, str], ...]] = {
    "retrieval_runs_v1": tuple(
        (name, column_type)
        for name, column_type, _not_null, _primary_key in _V1_TABLE_LAYOUTS[
            "trace_runs"
        ]
    ),
    "retrieval_stage_latency_v1": (
        ("trace_id", "VARCHAR"),
        ("retrieval_started_at", "TIMESTAMP"),
        ("retrieval_mode", "VARCHAR"),
        ("outcome", "VARCHAR"),
        ("span_id", "VARCHAR"),
        ("parent_span_id", "VARCHAR"),
        ("stage", "VARCHAR"),
        ("started_at", "TIMESTAMP"),
        ("ended_at", "TIMESTAMP"),
        ("duration_ms", "DOUBLE"),
        ("status_code", "VARCHAR"),
        ("attributes", "JSON"),
    ),
}

_V1_TABLES_DDL = """
    CREATE TABLE telemetry_metadata (
        singleton BOOLEAN PRIMARY KEY CHECK (singleton),
        schema_version INTEGER NOT NULL,
        created_at TIMESTAMP NOT NULL,
        runs_view_sha256 VARCHAR NOT NULL,
        stage_view_sha256 VARCHAR NOT NULL
    );
    CREATE TABLE trace_runs (
        trace_id VARCHAR PRIMARY KEY,
        root_span_id VARCHAR NOT NULL,
        started_at TIMESTAMP NOT NULL,
        ended_at TIMESTAMP NOT NULL,
        duration_ms DOUBLE NOT NULL CHECK (duration_ms >= 0),
        retrieval_mode VARCHAR NOT NULL,
        outcome VARCHAR NOT NULL,
        hit_count INTEGER NOT NULL CHECK (hit_count >= 0),
        namespace_count INTEGER NOT NULL CHECK (namespace_count >= 0),
        initial_fanout INTEGER NOT NULL CHECK (initial_fanout >= 0),
        final_fanout INTEGER NOT NULL CHECK (final_fanout >= 0),
        failure_count INTEGER NOT NULL CHECK (failure_count >= 0),
        incomplete BOOLEAN NOT NULL,
        widened BOOLEAN NOT NULL,
        fallback_reason VARCHAR,
        evidence_status VARCHAR,
        embedding_model VARCHAR NOT NULL,
        embedding_precision VARCHAR NOT NULL,
        top_k INTEGER NOT NULL CHECK (top_k >= 0),
        candidates INTEGER NOT NULL CHECK (candidates >= 0),
        buoy_version VARCHAR NOT NULL,
        observation_schema_version INTEGER NOT NULL
    );
    CREATE TABLE spans (
        trace_id VARCHAR NOT NULL,
        span_id VARCHAR NOT NULL,
        parent_span_id VARCHAR,
        name VARCHAR NOT NULL,
        started_at TIMESTAMP NOT NULL,
        ended_at TIMESTAMP NOT NULL,
        duration_ms DOUBLE NOT NULL CHECK (duration_ms >= 0),
        status_code VARCHAR NOT NULL,
        attributes JSON NOT NULL,
        PRIMARY KEY (trace_id, span_id)
    );
    CREATE TABLE span_events (
        trace_id VARCHAR NOT NULL,
        span_id VARCHAR NOT NULL,
        event_index INTEGER NOT NULL CHECK (event_index >= 0),
        name VARCHAR NOT NULL,
        occurred_at TIMESTAMP NOT NULL,
        attributes JSON NOT NULL,
        PRIMARY KEY (trace_id, span_id, event_index)
    );
"""

_RUNS_VIEW_DDL = """
    CREATE VIEW retrieval_runs_v1 AS
        SELECT *
        FROM trace_runs
        WHERE observation_schema_version = 1;
"""

_STAGE_VIEW_DDL = """
    CREATE VIEW retrieval_stage_latency_v1 AS
        SELECT
            runs.trace_id,
            runs.started_at AS retrieval_started_at,
            runs.retrieval_mode,
            runs.outcome,
            spans.span_id,
            spans.parent_span_id,
            spans.name AS stage,
            spans.started_at,
            spans.ended_at,
            spans.duration_ms,
            spans.status_code,
            spans.attributes
        FROM retrieval_runs_v1 AS runs
        JOIN spans USING (trace_id)
        WHERE spans.name <> 'buoy.retrieve';
"""

_V2_COMMAND_LAYOUT = (
    ("trace_id", "VARCHAR", True, True),
    ("root_span_id", "VARCHAR", True, False),
    ("started_at", "TIMESTAMP", True, False),
    ("ended_at", "TIMESTAMP", True, False),
    ("command_duration_ms", "DOUBLE", True, False),
    ("execution_mode", "VARCHAR", True, False),
    ("retrieval_mode", "VARCHAR", True, False),
    ("outcome", "VARCHAR", True, False),
    ("exit_code", "INTEGER", True, False),
    ("error_type", "VARCHAR", False, False),
    ("pipeline_present", "BOOLEAN", True, False),
    ("buoy_version", "VARCHAR", True, False),
    ("observation_schema_version", "INTEGER", True, False),
)
_V2_OPERATION_LAYOUT = (
    ("trace_id", "VARCHAR", True, True),
    ("span_id", "VARCHAR", True, False),
    ("started_at", "TIMESTAMP", True, False),
    ("ended_at", "TIMESTAMP", True, False),
    ("pipeline_duration_ms", "DOUBLE", True, False),
    ("outcome", "VARCHAR", True, False),
    ("hit_count", "INTEGER", True, False),
    ("namespace_count", "INTEGER", True, False),
    ("initial_fanout", "INTEGER", True, False),
    ("final_fanout", "INTEGER", True, False),
    ("failure_count", "INTEGER", True, False),
    ("incomplete", "BOOLEAN", True, False),
    ("widened", "BOOLEAN", True, False),
    ("fallback_reason", "VARCHAR", False, False),
    ("evidence_status", "VARCHAR", False, False),
    ("embedding_model", "VARCHAR", True, False),
    ("embedding_precision", "VARCHAR", True, False),
    ("top_k", "INTEGER", True, False),
    ("candidates", "INTEGER", True, False),
    ("buoy_version", "VARCHAR", True, False),
    ("observation_schema_version", "INTEGER", True, False),
)
_V2_TABLE_LAYOUTS = {
    **{
        key: value
        for key, value in _V1_TABLE_LAYOUTS.items()
        if key != "telemetry_metadata"
    },
    "telemetry_metadata": (
        *_V1_TABLE_LAYOUTS["telemetry_metadata"],
        ("command_runs_view_sha256", "VARCHAR", True, False),
        ("command_stage_view_sha256", "VARCHAR", True, False),
    ),
    "retrieve_command_runs": _V2_COMMAND_LAYOUT,
    "retrieval_operations": _V2_OPERATION_LAYOUT,
}
_V2_VIEW_LAYOUTS = {
    **_V1_VIEW_LAYOUTS,
    "retrieval_command_runs_v2": (
        ("trace_id", "VARCHAR"),
        ("root_span_id", "VARCHAR"),
        ("started_at", "TIMESTAMP"),
        ("ended_at", "TIMESTAMP"),
        ("command_duration_ms", "DOUBLE"),
        ("execution_mode", "VARCHAR"),
        ("retrieval_mode", "VARCHAR"),
        ("command_outcome", "VARCHAR"),
        ("exit_code", "INTEGER"),
        ("command_error_type", "VARCHAR"),
        ("pipeline_span_id", "VARCHAR"),
        ("pipeline_started_at", "TIMESTAMP"),
        ("pipeline_ended_at", "TIMESTAMP"),
        ("pipeline_duration_ms", "DOUBLE"),
        ("retrieval_outcome", "VARCHAR"),
        ("hit_count", "INTEGER"),
        ("namespace_count", "INTEGER"),
        ("initial_fanout", "INTEGER"),
        ("final_fanout", "INTEGER"),
        ("failure_count", "INTEGER"),
        ("incomplete", "BOOLEAN"),
        ("widened", "BOOLEAN"),
        ("fallback_reason", "VARCHAR"),
        ("evidence_status", "VARCHAR"),
        ("embedding_model", "VARCHAR"),
        ("embedding_precision", "VARCHAR"),
        ("top_k", "INTEGER"),
        ("candidates", "INTEGER"),
        ("buoy_version", "VARCHAR"),
        ("observation_schema_version", "INTEGER"),
    ),
    "retrieval_stage_latency_v2": (
        ("trace_id", "VARCHAR"),
        ("command_started_at", "TIMESTAMP"),
        ("execution_mode", "VARCHAR"),
        ("retrieval_mode", "VARCHAR"),
        ("command_outcome", "VARCHAR"),
        ("span_id", "VARCHAR"),
        ("parent_span_id", "VARCHAR"),
        ("stage", "VARCHAR"),
        ("started_at", "TIMESTAMP"),
        ("ended_at", "TIMESTAMP"),
        ("duration_ms", "DOUBLE"),
        ("status_code", "VARCHAR"),
        ("attributes", "JSON"),
    ),
}

_V2_TABLES_DDL = """
    CREATE TABLE retrieve_command_runs (
        trace_id VARCHAR PRIMARY KEY,
        root_span_id VARCHAR NOT NULL,
        started_at TIMESTAMP NOT NULL,
        ended_at TIMESTAMP NOT NULL,
        command_duration_ms DOUBLE NOT NULL CHECK (command_duration_ms >= 0),
        execution_mode VARCHAR NOT NULL,
        retrieval_mode VARCHAR NOT NULL,
        outcome VARCHAR NOT NULL,
        exit_code INTEGER NOT NULL CHECK (exit_code >= 0 AND exit_code <= 255),
        error_type VARCHAR,
        pipeline_present BOOLEAN NOT NULL,
        buoy_version VARCHAR NOT NULL,
        observation_schema_version INTEGER NOT NULL
    );
    CREATE TABLE retrieval_operations (
        trace_id VARCHAR PRIMARY KEY,
        span_id VARCHAR NOT NULL,
        started_at TIMESTAMP NOT NULL,
        ended_at TIMESTAMP NOT NULL,
        pipeline_duration_ms DOUBLE NOT NULL CHECK (pipeline_duration_ms >= 0),
        outcome VARCHAR NOT NULL,
        hit_count INTEGER NOT NULL CHECK (hit_count >= 0),
        namespace_count INTEGER NOT NULL CHECK (namespace_count >= 0),
        initial_fanout INTEGER NOT NULL CHECK (initial_fanout >= 0),
        final_fanout INTEGER NOT NULL CHECK (final_fanout >= 0),
        failure_count INTEGER NOT NULL CHECK (failure_count >= 0),
        incomplete BOOLEAN NOT NULL,
        widened BOOLEAN NOT NULL,
        fallback_reason VARCHAR,
        evidence_status VARCHAR,
        embedding_model VARCHAR NOT NULL,
        embedding_precision VARCHAR NOT NULL,
        top_k INTEGER NOT NULL CHECK (top_k >= 0),
        candidates INTEGER NOT NULL CHECK (candidates >= 0),
        buoy_version VARCHAR NOT NULL,
        observation_schema_version INTEGER NOT NULL
    );
"""
_V2_COMMAND_VIEW_DDL = """
    CREATE VIEW retrieval_command_runs_v2 AS
        SELECT
            command.trace_id,
            command.root_span_id,
            command.started_at,
            command.ended_at,
            command.command_duration_ms,
            command.execution_mode,
            command.retrieval_mode,
            command.outcome AS command_outcome,
            command.exit_code,
            command.error_type AS command_error_type,
            operation.span_id AS pipeline_span_id,
            operation.started_at AS pipeline_started_at,
            operation.ended_at AS pipeline_ended_at,
            operation.pipeline_duration_ms,
            operation.outcome AS retrieval_outcome,
            operation.hit_count,
            operation.namespace_count,
            operation.initial_fanout,
            operation.final_fanout,
            operation.failure_count,
            operation.incomplete,
            operation.widened,
            operation.fallback_reason,
            operation.evidence_status,
            operation.embedding_model,
            operation.embedding_precision,
            operation.top_k,
            operation.candidates,
            command.buoy_version,
            command.observation_schema_version
        FROM retrieve_command_runs AS command
        LEFT JOIN retrieval_operations AS operation USING (trace_id);
"""
_V2_STAGE_VIEW_DDL = """
    CREATE VIEW retrieval_stage_latency_v2 AS
        SELECT
            command.trace_id,
            command.started_at AS command_started_at,
            command.execution_mode,
            command.retrieval_mode,
            command.outcome AS command_outcome,
            spans.span_id,
            spans.parent_span_id,
            spans.name AS stage,
            spans.started_at,
            spans.ended_at,
            spans.duration_ms,
            spans.status_code,
            spans.attributes
        FROM retrieve_command_runs AS command
        JOIN spans USING (trace_id)
        WHERE spans.span_id <> command.root_span_id;
"""


def append_trace(paths: TelemetryPaths, rows: TraceRows) -> StoreAppendResult:
    """Commit one exact trace graph, replay it idempotently, or flag conflict.

    The caller supplies only fixed canonical paths and already-validated rows.
    This function owns the bounded database lock and never changes an existing
    incompatible or conflicting store.
    """

    _validate_fixed_paths(paths)
    try:
        with database_write_lock(paths, timeout_ms=250):
            return _append_trace_locked(paths, rows)
    except TelemetryStoreError:
        raise
    except QueueLockTimeout as exc:
        raise StoreBusyError("telemetry store is busy") from exc
    except (UnsafePathError, UnsupportedPlatformError, ValueError) as exc:
        raise StoreUnsafeError("telemetry store path is unsafe") from exc
    except (UnreadablePathError, FileNotFoundError, OSError) as exc:
        raise StoreUnreadableError("telemetry store is unreadable") from exc
    except Exception as exc:
        raise StoreWriteError("telemetry store operation failed") from exc


def inspect_trace_terminal(
    paths: TelemetryPaths,
    rows: TraceRows,
) -> StoreAppendResult:
    """Prove an existing exact replay or conflict without mutating DuckDB."""

    _validate_fixed_paths(paths)
    try:
        with database_write_lock(paths, timeout_ms=250):
            return _inspect_trace_terminal_locked(paths, rows)
    except TelemetryStoreError:
        raise
    except QueueLockTimeout as exc:
        raise StoreBusyError("telemetry store is busy") from exc
    except (UnsafePathError, UnsupportedPlatformError, ValueError) as exc:
        raise StoreUnsafeError("telemetry store path is unsafe") from exc
    except (UnreadablePathError, FileNotFoundError, OSError) as exc:
        raise StoreUnreadableError("telemetry store is unreadable") from exc
    except Exception as exc:
        raise StoreUnreadableError("telemetry store is unreadable") from exc


def _append_trace_locked(
    paths: TelemetryPaths,
    rows: _RowsLike,
) -> StoreAppendResult:
    try:
        root_fd = open_verified_directory(paths.directory)
    except (ValueError, OSError) as exc:
        raise StoreUnsafeError("telemetry store path is unsafe") from exc
    try:
        durability_degraded = _recover_initialization_scratch(root_fd)
        backup_present = _validate_append_auxiliary_paths(root_fd)
        database_stat = _optional_private_stat(
            root_fd,
            DATABASE_BASENAME,
            kind="file",
        )
        wal_stat = _optional_private_stat(
            root_fd,
            DATABASE_WAL_BASENAME,
            kind="file",
            max_bytes=DATABASE_INIT_MAX_BYTES,
        )
        if database_stat is None:
            if wal_stat is not None or backup_present:
                raise StoreUnsafeError("telemetry store path is unsafe")
            result = _initialize_database_atomically(paths, root_fd, rows)
            return _with_degradation(result, durability_degraded)
        _verify_final_database_fd(root_fd)
        if wal_stat is not None:
            durability_degraded |= _recover_final_wal(paths, root_fd)
        result = _append_existing(
            paths,
            root_fd,
            rows,
            backup_present=backup_present,
        )
        return _with_degradation(result, durability_degraded)
    except TelemetryStoreError:
        raise
    except ValueError as exc:
        raise StoreUnsafeError("telemetry store path is unsafe") from exc
    except duckdb.Error as exc:
        raise StoreUnreadableError("telemetry store is unreadable") from exc
    except OSError as exc:
        raise StoreUnreadableError("telemetry store is unreadable") from exc
    finally:
        os.close(root_fd)


def _with_degradation(
    result: StoreAppendResult,
    durability_degraded: bool,
) -> StoreAppendResult:
    if not durability_degraded or result.durability_degraded:
        return result
    return StoreAppendResult(
        outcome=result.outcome,
        snapshot=result.snapshot,
        durability_degraded=True,
    )


def _inspect_trace_terminal_locked(
    paths: TelemetryPaths,
    rows: _RowsLike,
) -> StoreAppendResult:
    root_fd = open_verified_directory(paths.directory)
    try:
        backup_present = _validate_append_auxiliary_paths(root_fd)
        if (
            _optional_private_stat(
                root_fd,
                DATABASE_INIT_DIRECTORY,
                kind="directory",
            )
            is not None
        ):
            raise StoreUnsafeError("telemetry initialization path is unsafe")
        database_stat = _optional_private_stat(
            root_fd,
            DATABASE_BASENAME,
            kind="file",
        )
        if database_stat is None:
            raise StoreTerminalAbsentError("telemetry terminal state is absent")
        if (
            _optional_private_stat(
                root_fd,
                DATABASE_WAL_BASENAME,
                kind="file",
                max_bytes=DATABASE_INIT_MAX_BYTES,
            )
            is not None
        ):
            raise StoreUnreadableError("telemetry terminal state is unproven")
        _verify_final_database_fd(root_fd)
        try:
            with _verified_connection(
                paths.database_path,
                root_fd,
                DATABASE_BASENAME,
                read_only=True,
            ) as connection:
                schema_version = _validate_schema(connection)
                if backup_present:
                    if schema_version != 2:
                        raise StoreIncompatibleError(
                            "telemetry retained backup is incompatible"
                        )
                    v1_identity = _validate_existing_content(
                        connection, schema_version
                    )
                    if _validate_retained_backup(paths, root_fd) != v1_identity:
                        raise StoreIncompatibleError(
                            "telemetry retained backup history differs"
                        )
                else:
                    _validate_existing_content(connection, schema_version)
                existing = _read_trace_graph(connection, _trace_id(rows))
                if not any(existing):
                    raise StoreTerminalAbsentError(
                        "telemetry terminal state is absent"
                    )
                outcome: StoreOutcome = (
                    "replayed" if existing == _row_graph(rows) else "conflict"
                )
                persisted_runs = _persisted_run_count(connection)
        except StoreUnsafeError:
            raise
        except StoreUnreadableError:
            raise
        except ValueError as exc:
            raise StoreIncompatibleError(
                "telemetry store schema is incompatible"
            ) from exc
        except duckdb.Error as exc:
            _raise_connection_error(exc)
        final_stat = _verify_final_database_fd(root_fd)
        _require_path_matches_stat(paths.database_path, final_stat)
        return StoreAppendResult(
            outcome=outcome,
            snapshot=_store_snapshot(
                persisted_runs, final_stat, schema_version=schema_version
            ),
        )
    finally:
        os.close(root_fd)


def _validate_fixed_paths(paths: TelemetryPaths) -> None:
    directory = Path(paths.directory)
    expected = {
        "database_path": directory / DATABASE_BASENAME,
        "database_wal_path": directory / DATABASE_WAL_BASENAME,
        "lock_path": directory / "write.lock",
        "database_init_directory": directory / DATABASE_INIT_DIRECTORY,
        "init_database_path": (
            directory / DATABASE_INIT_DIRECTORY / DATABASE_BASENAME
        ),
        "init_wal_path": (
            directory / DATABASE_INIT_DIRECTORY / DATABASE_WAL_BASENAME
        ),
        "migration_directory": directory / DATABASE_MIGRATION_DIRECTORY,
        "migration_database_path": (
            directory / DATABASE_MIGRATION_DIRECTORY / DATABASE_BASENAME
        ),
        "migration_wal_path": (
            directory / DATABASE_MIGRATION_DIRECTORY / DATABASE_WAL_BASENAME
        ),
        "migration_backup_candidate_path": (
            directory / DATABASE_MIGRATION_DIRECTORY / DATABASE_BACKUP_BASENAME
        ),
        "backup_database_path": directory / DATABASE_BACKUP_BASENAME,
    }
    for field, expected_path in expected.items():
        if Path(getattr(paths, field)) != expected_path:
            raise StoreUnsafeError("telemetry store path is unsafe")


def _validate_append_auxiliary_paths(root_fd: int) -> bool:
    if _optional_private_stat(
        root_fd,
        DATABASE_MIGRATION_DIRECTORY,
        kind="directory",
    ) is not None:
        raise StoreUnsafeError("telemetry migration path is unresolved")
    return (
        _optional_private_stat(
            root_fd,
            DATABASE_BACKUP_BASENAME,
            kind="file",
        )
        is not None
    )


def _optional_private_stat(
    parent_fd: int,
    name: str,
    *,
    kind: Literal["file", "directory"],
    max_bytes: int | None = None,
    allowed_nlinks: tuple[int, ...] = (1,),
) -> os.stat_result | None:
    try:
        return stat_private_entry_at(
            parent_fd,
            name,
            kind=kind,
            max_bytes=max_bytes,
            allowed_nlinks=allowed_nlinks,
        )
    except FileNotFoundError:
        return None


def _verify_final_database_fd(root_fd: int) -> os.stat_result:
    descriptor = open_private_file_at(
        root_fd,
        DATABASE_BASENAME,
        flags=os.O_RDONLY,
        allowed_nlinks=(1,),
    )
    try:
        return verify_private_file_fd(descriptor, allowed_nlinks=(1,))
    finally:
        os.close(descriptor)


def _recover_initialization_scratch(root_fd: int) -> bool:
    scratch_stat = _optional_private_stat(
        root_fd,
        DATABASE_INIT_DIRECTORY,
        kind="directory",
    )
    if scratch_stat is None:
        return False
    del scratch_stat
    scratch_fd = open_private_directory_at(
        root_fd,
        DATABASE_INIT_DIRECTORY,
        create=False,
    )
    try:
        scan_fixed_private_inventory(
            scratch_fd,
            allowed_names=_INITIALIZATION_SCRATCH_NAMES,
        )
        scratch_database = _optional_private_stat(
            scratch_fd,
            DATABASE_BASENAME,
            kind="file",
            max_bytes=DATABASE_INIT_MAX_BYTES,
            allowed_nlinks=(1, 2),
        )
        scratch_wal = _optional_private_stat(
            scratch_fd,
            DATABASE_WAL_BASENAME,
            kind="file",
            max_bytes=DATABASE_INIT_MAX_BYTES,
        )
        final_database = _optional_private_stat(
            root_fd,
            DATABASE_BASENAME,
            kind="file",
            allowed_nlinks=(1, 2),
        )
        if scratch_database is not None:
            if (
                final_database is not None
                and scratch_database.st_dev == final_database.st_dev
                and scratch_database.st_ino == final_database.st_ino
            ):
                if (
                    scratch_database.st_nlink != 2
                    or final_database.st_nlink != 2
                ):
                    raise StoreUnsafeError(
                        "telemetry initialization path is unsafe"
                    )
                safe_unlink_at(
                    scratch_fd,
                    DATABASE_BASENAME,
                    allowed_nlinks=(2,),
                )
            else:
                if scratch_database.st_nlink != 1:
                    raise StoreUnsafeError(
                        "telemetry initialization path is unsafe"
                    )
                safe_unlink_at(scratch_fd, DATABASE_BASENAME)
        if scratch_wal is not None:
            safe_unlink_at(scratch_fd, DATABASE_WAL_BASENAME)
        durability_degraded = not fsync_directory(scratch_fd)
    finally:
        os.close(scratch_fd)
    safe_rmdir_at(root_fd, DATABASE_INIT_DIRECTORY)
    durability_degraded |= not fsync_directory(root_fd)
    return durability_degraded


def _initialize_database_atomically(
    paths: TelemetryPaths,
    root_fd: int,
    rows: _RowsLike,
) -> StoreAppendResult:
    scratch_fd = open_private_directory_at(
        root_fd,
        DATABASE_INIT_DIRECTORY,
        create=True,
    )
    linked = False
    durability_degraded = False
    try:
        # Reserve the fixed name with the governed creation primitive before
        # handing the absent path to DuckDB's necessarily path-only API.
        database_fd = open_private_file_at(
            scratch_fd,
            DATABASE_BASENAME,
            flags=os.O_CREAT | os.O_EXCL | os.O_RDWR,
            max_bytes=DATABASE_INIT_MAX_BYTES,
        )
        os.close(database_fd)
        safe_unlink_at(scratch_fd, DATABASE_BASENAME)
        try:
            with _connect_database(paths.init_database_path) as connection:
                # DuckDB creates through a path-only API.  Once it has created
                # the fixed file, establish ownership/type/link/mode before
                # allowing schema or row work to proceed.
                created_fd = open_private_file_at(
                    scratch_fd,
                    DATABASE_BASENAME,
                    flags=os.O_RDONLY,
                    max_bytes=DATABASE_INIT_MAX_BYTES,
                )
                try:
                    created_stat = verify_private_file_fd(
                        created_fd,
                        max_bytes=DATABASE_INIT_MAX_BYTES,
                    )
                    _require_path_matches_stat(
                        paths.init_database_path,
                        created_stat,
                    )
                finally:
                    os.close(created_fd)
                _insert_trace_transaction(connection, rows, initialize=True)
        except duckdb.Error as exc:
            raise StoreWriteError("telemetry store write failed") from exc
        durability_degraded |= _require_wal_absent_after_close(
            scratch_fd,
            DATABASE_WAL_BASENAME,
        )
        scratch_database = _verify_scratch_database(scratch_fd)
        _require_path_matches_stat(paths.init_database_path, scratch_database)
        try:
            with _verified_connection(
                paths.init_database_path,
                scratch_fd,
                DATABASE_BASENAME,
                read_only=True,
                max_bytes=DATABASE_INIT_MAX_BYTES,
            ) as connection:
                _validate_schema(connection)
                if _read_trace_graph(connection, _trace_id(rows)) != _row_graph(
                    rows
                ):
                    raise StoreIncompatibleError(
                        "telemetry store trace graph is incompatible"
                    )
                persisted_runs = _persisted_run_count(connection)
        except StoreIncompatibleError:
            raise
        except (duckdb.Error, ValueError) as exc:
            raise StoreWriteError("telemetry store verification failed") from exc
        safe_link_at(
            scratch_fd,
            DATABASE_BASENAME,
            root_fd,
            DATABASE_BASENAME,
        )
        linked = True
        durability_degraded |= not fsync_directory(root_fd)
        safe_unlink_at(
            scratch_fd,
            DATABASE_BASENAME,
            allowed_nlinks=(2,),
        )
        durability_degraded |= not fsync_directory(scratch_fd)
        os.close(scratch_fd)
        scratch_fd = -1
        safe_rmdir_at(root_fd, DATABASE_INIT_DIRECTORY)
        durability_degraded |= not fsync_directory(root_fd)
        final_stat = _verify_final_database_fd(root_fd)
        _require_path_matches_stat(paths.database_path, final_stat)
        return StoreAppendResult(
            outcome="committed",
            snapshot=_store_snapshot(persisted_runs, final_stat),
            durability_degraded=durability_degraded,
        )
    except TelemetryStoreError:
        raise
    except (ValueError, PermissionError) as exc:
        raise StoreUnsafeError("telemetry initialization path is unsafe") from exc
    except OSError as exc:
        if linked:
            raise StoreWriteError("telemetry store acknowledgement failed") from exc
        raise StoreWriteError("telemetry store initialization failed") from exc
    finally:
        if scratch_fd >= 0:
            os.close(scratch_fd)


def _verify_scratch_database(scratch_fd: int) -> os.stat_result:
    descriptor = open_private_file_at(
        scratch_fd,
        DATABASE_BASENAME,
        flags=os.O_RDONLY,
        max_bytes=DATABASE_INIT_MAX_BYTES,
    )
    try:
        observed = verify_private_file_fd(
            descriptor,
            max_bytes=DATABASE_INIT_MAX_BYTES,
        )
        os.fsync(descriptor)
        return observed
    finally:
        os.close(descriptor)


def _recover_final_wal(paths: TelemetryPaths, root_fd: int) -> bool:
    _verify_final_database_fd(root_fd)
    try:
        with _verified_connection(
            paths.database_path,
            root_fd,
            DATABASE_BASENAME,
            read_only=False,
        ):
            pass
    except duckdb.Error as exc:
        _raise_connection_error(
            exc,
            unreadable_message="telemetry store recovery failed",
        )
    durability_degraded = not fsync_directory(root_fd)
    durability_degraded |= _require_wal_absent_after_close(
        root_fd,
        DATABASE_WAL_BASENAME,
    )
    return durability_degraded


def _require_wal_absent_after_close(parent_fd: int, wal_name: str) -> bool:
    wal_stat = _optional_private_stat(
        parent_fd,
        wal_name,
        kind="file",
        max_bytes=DATABASE_INIT_MAX_BYTES,
    )
    if wal_stat is None:
        return False
    if wal_stat.st_size != 0:
        raise StoreUnreadableError("telemetry store recovery is incomplete")
    safe_unlink_at(parent_fd, wal_name)
    return not fsync_directory(parent_fd)


def _append_existing(
    paths: TelemetryPaths,
    root_fd: int,
    rows: _RowsLike,
    *,
    backup_present: bool,
) -> StoreAppendResult:
    try:
        with _verified_connection(
            paths.database_path,
            root_fd,
            DATABASE_BASENAME,
            read_only=False,
        ) as connection:
            try:
                schema_version = _validate_schema(connection)
            except ValueError as exc:
                raise StoreIncompatibleError(
                    "telemetry store schema is incompatible"
                ) from exc
            v1_identity = _validate_existing_content(
                connection, schema_version
            )
            if backup_present:
                if schema_version != 2:
                    raise StoreIncompatibleError(
                        "telemetry retained backup is incompatible"
                    )
                if _validate_retained_backup(paths, root_fd) != v1_identity:
                    raise StoreIncompatibleError(
                        "telemetry retained backup history differs"
                    )
            result = _validate_and_insert_or_classify_transaction(
                connection,
                rows,
            )
            schema_version = _validate_schema(connection)
            persisted_runs = _persisted_run_count(connection)
    except StoreUnsafeError:
        raise
    except StoreIncompatibleError as exc:
        if (
            _optional_private_stat(
                root_fd,
                DATABASE_WAL_BASENAME,
                kind="file",
                max_bytes=DATABASE_INIT_MAX_BYTES,
            )
            is not None
        ):
            raise StoreUnreadableError(
                "telemetry store validation left recovery state"
            ) from exc
        _verify_final_database_fd(root_fd)
        raise
    except StoreUnreadableError:
        raise
    except StoreWriteError:
        raise
    except duckdb.Error as exc:
        _raise_connection_error(exc)
    durability_degraded = _require_wal_absent_after_close(
        root_fd,
        DATABASE_WAL_BASENAME,
    )
    final_stat = _verify_final_database_fd(root_fd)
    _require_path_matches_stat(paths.database_path, final_stat)
    return StoreAppendResult(
        outcome=result,
        snapshot=_store_snapshot(
            persisted_runs, final_stat, schema_version=schema_version
        ),
        durability_degraded=durability_degraded,
    )


def _validate_retained_backup(
    paths: TelemetryPaths,
    root_fd: int,
    *,
    allowed_nlinks: tuple[int, ...] = (1,),
) -> _V1ContentIdentity:
    try:
        with _verified_connection(
            paths.backup_database_path,
            root_fd,
            DATABASE_BACKUP_BASENAME,
            read_only=True,
            allowed_nlinks=allowed_nlinks,
        ) as backup:
            _validate_schema(backup, expected_version=1)
            return _validate_existing_content(backup, 1)
    except (duckdb.Error, ValueError) as exc:
        raise StoreIncompatibleError(
            "telemetry retained backup is incompatible"
        ) from exc


def _persisted_run_count(connection: duckdb.DuckDBPyConnection) -> int:
    table_names = {
        str(row[0])
        for row in connection.execute(
            """
            SELECT table_name FROM system.duckdb_tables()
            WHERE database_name = system.current_database()
              AND schema_name = 'main'
            """
        ).fetchall()
    }
    statement = "SELECT count(*) FROM trace_runs"
    if "retrieve_command_runs" in table_names:
        statement += " UNION ALL SELECT count(*) FROM retrieve_command_runs"
    values = connection.execute(statement).fetchall()
    counts = [row[0] for row in values]
    if any(type(value) is not int or value < 0 for value in counts):
        raise ValueError("telemetry DuckDB run count is incompatible")
    return sum(counts)


def _store_snapshot(
    persisted_runs: int,
    database_stat: os.stat_result,
    *,
    schema_version: int = TELEMETRY_SCHEMA_VERSION,
) -> StoreSnapshot:
    return StoreSnapshot(
        schema_version=schema_version,
        persisted_runs_snapshot=persisted_runs,
        database_device=database_stat.st_dev,
        database_inode=database_stat.st_ino,
        database_bytes=database_stat.st_size,
    )


@contextmanager
def _verified_connection(
    path: Path | str,
    parent_fd: int,
    basename: str,
    *,
    read_only: bool,
    max_bytes: int | None = None,
    allowed_nlinks: tuple[int, ...] = (1,),
) -> Iterator[duckdb.DuckDBPyConnection]:
    before = stat_private_entry_at(
        parent_fd,
        basename,
        kind="file",
        max_bytes=max_bytes,
        allowed_nlinks=allowed_nlinks,
    )
    _require_path_matches_stat(path, before)
    connection = _connect_database(path, read_only=read_only)
    try:
        yield connection
    finally:
        try:
            connection.close()
        finally:
            after = stat_private_entry_at(
                parent_fd,
                basename,
                kind="file",
                max_bytes=max_bytes,
                allowed_nlinks=allowed_nlinks,
            )
            _require_path_matches_stat(path, after)
            if (before.st_dev, before.st_ino) != (
                after.st_dev,
                after.st_ino,
            ):
                raise StoreUnsafeError(
                    "telemetry store path changed during open"
                )


def _require_path_matches_stat(
    path: Path | str,
    expected: os.stat_result,
) -> None:
    observed = os.stat(path, follow_symlinks=False)
    if (
        not stat.S_ISREG(observed.st_mode)
        or observed.st_uid != os.geteuid()
        or (observed.st_dev, observed.st_ino)
        != (expected.st_dev, expected.st_ino)
    ):
        raise StoreUnsafeError("telemetry store path changed during open")


def _connect_database(
    path: Path | str,
    *,
    read_only: bool = False,
) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(
        str(path),
        read_only=read_only,
        config=_SAFE_DUCKDB_CONFIG,
    )


def _raise_connection_error(
    error: duckdb.Error,
    *,
    unreadable_message: str = "telemetry store is unreadable",
) -> None:
    message = str(error)
    if (
        isinstance(error, duckdb.IOException)
        and "Could not set lock on file" in message
        and "Conflicting lock is held" in message
    ):
        raise StoreBusyError("telemetry store is busy") from error
    raise StoreUnreadableError(unreadable_message) from error


def _insert_trace_transaction(
    connection: duckdb.DuckDBPyConnection,
    rows: _RowsLike,
    *,
    initialize: bool,
) -> None:
    connection.execute("BEGIN TRANSACTION")
    try:
        if initialize:
            _initialize_schema_v2(connection)
        _insert_trace_rows(connection, rows)
    except Exception:
        try:
            connection.execute("ROLLBACK")
        except Exception:
            pass
        raise
    else:
        connection.execute("COMMIT")


def _validate_and_insert_or_classify_transaction(
    connection: duckdb.DuckDBPyConnection,
    rows: _RowsLike,
) -> StoreOutcome:
    connection.execute("BEGIN TRANSACTION")
    try:
        try:
            schema_version = _validate_schema(connection)
        except ValueError as exc:
            raise StoreIncompatibleError(
                "telemetry store schema is incompatible"
            ) from exc
        except duckdb.Error as exc:
            raise StoreUnreadableError(
                "telemetry store is unreadable"
            ) from exc
        if _is_v2_rows(rows) and schema_version == 1:
            raise StoreUpgradeRequiredError("telemetry store upgrade required")
        trace_id = _trace_id(rows)
        try:
            existing = _read_trace_graph(connection, trace_id)
            if any(existing):
                result: StoreOutcome = (
                    "replayed" if existing == _row_graph(rows) else "conflict"
                )
            else:
                _insert_trace_rows(connection, rows)
                result = "committed"
            connection.execute("COMMIT")
        except TelemetryStoreError:
            raise
        except Exception as exc:
            raise StoreWriteError("telemetry store write failed") from exc
    except Exception:
        try:
            connection.execute("ROLLBACK")
        except Exception:
            pass
        raise
    return result


def _is_v2_rows(rows: _RowsLike) -> bool:
    return hasattr(rows, "command")


def _trace_id(rows: _RowsLike) -> str:
    source = getattr(rows, "command", None)
    if source is None:
        source = rows.run
    return str(source[0])


def _insert_trace_rows(
    connection: duckdb.DuckDBPyConnection,
    rows: _RowsLike,
) -> None:
    if _is_v2_rows(rows):
        connection.execute(
            "INSERT INTO retrieve_command_runs VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            getattr(rows, "command"),
        )
        operation = getattr(rows, "retrieval_operation")
        if operation is not None:
            connection.execute(
                "INSERT INTO retrieval_operations VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                operation,
            )
    else:
        connection.execute(
            """
            INSERT INTO trace_runs VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            rows.run,
        )
    connection.executemany(
        "INSERT INTO spans VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows.spans,
    )
    if rows.events:
        connection.executemany(
            "INSERT INTO span_events VALUES (?, ?, ?, ?, ?, ?)",
            rows.events,
        )


def _row_graph(rows: _RowsLike) -> tuple[tuple[tuple[object, ...], ...], ...]:
    if _is_v2_rows(rows):
        operation = getattr(rows, "retrieval_operation")
        return (
            (tuple(getattr(rows, "command")),),
            (() if operation is None else (tuple(operation),)),
            tuple(rows.spans),
            tuple(rows.events),
        )
    return ((tuple(rows.run),), (), tuple(rows.spans), tuple(rows.events))


def _read_trace_graph(
    connection: duckdb.DuckDBPyConnection,
    trace_id: str,
) -> tuple[tuple[tuple[object, ...], ...], ...]:
    table_names = {
        str(row[0])
        for row in connection.execute(
            """
            SELECT table_name FROM system.duckdb_tables()
            WHERE database_name = system.current_database()
              AND schema_name = 'main'
            """
        ).fetchall()
    }
    commands: tuple[tuple[object, ...], ...] = ()
    operations: tuple[tuple[object, ...], ...] = ()
    if "retrieve_command_runs" in table_names:
        commands = tuple(
            tuple(row)
            for row in connection.execute(
                "SELECT * FROM retrieve_command_runs WHERE trace_id = ?",
                (trace_id,),
            ).fetchall()
        )
        operations = tuple(
            tuple(row)
            for row in connection.execute(
                "SELECT * FROM retrieval_operations WHERE trace_id = ?",
                (trace_id,),
            ).fetchall()
        )
    runs = tuple(
        tuple(row)
        for row in connection.execute(
            "SELECT * FROM trace_runs WHERE trace_id = ?",
            (trace_id,),
        ).fetchall()
    )
    spans = tuple(
        tuple(row)
        for row in connection.execute(
            """
            SELECT * FROM spans
            WHERE trace_id = ?
            ORDER BY started_at, span_id
            """,
            (trace_id,),
        ).fetchall()
    )
    events = tuple(
        tuple(row)
        for row in connection.execute(
            """
            SELECT * FROM span_events
            WHERE trace_id = ?
            ORDER BY event_index
            """,
            (trace_id,),
        ).fetchall()
    )
    if commands:
        return commands, operations, spans, events
    return runs, (), spans, events


def _create_v1_schema_objects(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute(_V1_TABLES_DDL)
    connection.execute(_RUNS_VIEW_DDL)
    connection.execute(_STAGE_VIEW_DDL)


def _add_v2_data_objects(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute(_V2_TABLES_DDL)
    connection.execute(_V2_COMMAND_VIEW_DDL)
    connection.execute(_V2_STAGE_VIEW_DDL)


def _add_v2_schema_objects(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute(
        "ALTER TABLE telemetry_metadata "
        "ADD COLUMN command_runs_view_sha256 VARCHAR"
    )
    connection.execute(
        "ALTER TABLE telemetry_metadata "
        "ADD COLUMN command_stage_view_sha256 VARCHAR"
    )
    _add_v2_data_objects(connection)


def _initialize_schema_v1(connection: duckdb.DuckDBPyConnection) -> None:
    _create_v1_schema_objects(connection)
    digests = _view_sql_digests(connection, version=1)
    if digests != _expected_view_sql_digests(1):
        raise ValueError("telemetry DuckDB views are incompatible")
    connection.execute(
        """
        INSERT INTO telemetry_metadata VALUES (
            true, 1, current_timestamp AT TIME ZONE 'UTC', ?, ?
        )
        """,
        (
            digests["retrieval_runs_v1"],
            digests["retrieval_stage_latency_v1"],
        ),
    )


def _set_v2_metadata_not_null(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute(
        "ALTER TABLE telemetry_metadata ALTER COLUMN "
        "command_runs_view_sha256 SET NOT NULL"
    )
    connection.execute(
        "ALTER TABLE telemetry_metadata ALTER COLUMN "
        "command_stage_view_sha256 SET NOT NULL"
    )


def _initialize_schema_v2(connection: duckdb.DuckDBPyConnection) -> None:
    _create_v1_schema_objects(connection)
    _add_v2_schema_objects(connection)
    _set_v2_metadata_not_null(connection)
    digests = _view_sql_digests(connection, version=2)
    if digests != _expected_view_sql_digests(2):
        raise ValueError("telemetry DuckDB views are incompatible")
    connection.execute(
        """
        INSERT INTO telemetry_metadata VALUES (
            true, 2, current_timestamp AT TIME ZONE 'UTC', ?, ?, ?, ?
        )
        """,
        (
            digests["retrieval_runs_v1"],
            digests["retrieval_stage_latency_v1"],
            digests["retrieval_command_runs_v2"],
            digests["retrieval_stage_latency_v2"],
        ),
    )


# Retained internal seam used by the established store transaction tests.
_initialize_schema = _initialize_schema_v2


def _validate_schema(
    connection: duckdb.DuckDBPyConnection,
    expected_version: int | None = None,
) -> int:
    current_database = str(
        connection.execute("SELECT system.current_database()").fetchone()[0]
    )
    attached = connection.execute(
        """
        SELECT database_name
        FROM system.duckdb_databases()
        WHERE NOT internal AND database_name <> ?
        LIMIT 1
        """,
        (current_database,),
    ).fetchall()
    user_schemas = connection.execute(
        """
        SELECT schema_name
        FROM system.duckdb_schemas()
        WHERE database_name = ? AND schema_name <> 'main'
        LIMIT 1
        """,
        (current_database,),
    ).fetchall()
    if attached or user_schemas:
        raise ValueError("telemetry DuckDB database inventory is incompatible")
    user_functions = connection.execute(
        """
        SELECT function_name
        FROM system.duckdb_functions()
        WHERE database_name = system.current_database()
        LIMIT 1
        """
    ).fetchall()
    sequences = connection.execute(
        """
        SELECT sequence_name
        FROM system.duckdb_sequences()
        WHERE database_name = system.current_database()
        LIMIT 1
        """
    ).fetchall()
    custom_types = connection.execute(
        """
        SELECT type_name
        FROM system.duckdb_types()
        WHERE database_name = system.current_database() AND NOT internal
        LIMIT 1
        """
    ).fetchall()
    ungoverned_metadata = connection.execute(
        """
        SELECT object_name FROM (
            SELECT database_name AS object_name
            FROM system.duckdb_databases()
            WHERE database_name = system.current_database()
              AND (
                  comment IS NOT NULL
                  OR map_keys(tags) <> ['storage_version']
                  OR coalesce(cardinality(options), 0) <> 0
              )
            UNION ALL
            SELECT schema_name
            FROM system.duckdb_schemas()
            WHERE database_name = system.current_database()
              AND (comment IS NOT NULL OR coalesce(cardinality(tags), 0) <> 0)
            UNION ALL
            SELECT table_name
            FROM system.duckdb_tables()
            WHERE database_name = system.current_database() AND NOT internal
              AND (comment IS NOT NULL OR coalesce(cardinality(tags), 0) <> 0)
            UNION ALL
            SELECT view_name
            FROM system.duckdb_views()
            WHERE database_name = system.current_database() AND NOT internal
              AND (comment IS NOT NULL OR coalesce(cardinality(tags), 0) <> 0)
            UNION ALL
            SELECT table_name || '.' || column_name
            FROM system.duckdb_columns()
            WHERE database_name = system.current_database()
              AND schema_name = 'main' AND NOT internal
              AND (
                  comment IS NOT NULL OR column_default IS NOT NULL
              )
        ) AS inventory
        LIMIT 1
        """
    ).fetchall()
    if user_functions or sequences or custom_types or ungoverned_metadata:
        raise ValueError("telemetry DuckDB user objects are incompatible")
    table_names = {
        str(name)
        for (name,) in connection.execute(
            """
            SELECT table_name
            FROM system.duckdb_tables()
            WHERE database_name = system.current_database()
              AND schema_name = 'main'
            LIMIT 8
            """
        ).fetchall()
    }
    view_names = {
        str(name)
        for (name,) in connection.execute(
            """
            SELECT view_name
            FROM system.duckdb_views()
            WHERE database_name = system.current_database()
              AND schema_name = 'main'
              AND NOT internal
            LIMIT 5
            """
        ).fetchall()
    }
    if table_names == set(_V1_TABLE_LAYOUTS) and view_names == set(_V1_VIEW_LAYOUTS):
        version = 1
        table_layouts = _V1_TABLE_LAYOUTS
        view_layouts = _V1_VIEW_LAYOUTS
    elif table_names == set(_V2_TABLE_LAYOUTS) and view_names == set(_V2_VIEW_LAYOUTS):
        version = 2
        table_layouts = _V2_TABLE_LAYOUTS
        view_layouts = _V2_VIEW_LAYOUTS
    else:
        raise ValueError("telemetry DuckDB schema objects are incompatible")
    if expected_version is not None and version != expected_version:
        raise ValueError("telemetry DuckDB schema version is incompatible")
    for table_name, expected_layout in table_layouts.items():
        actual_layout = tuple(
            (str(row[1]), str(row[2]), bool(row[3]), bool(row[5]))
            for row in connection.execute(
                f"SELECT * FROM system.pragma_table_info('{table_name}') "
                f"LIMIT {len(expected_layout) + 1}"
            ).fetchall()
        )
        if actual_layout != expected_layout:
            raise ValueError(
                f"telemetry DuckDB table {table_name!r} is incompatible"
            )
    for view_name, expected_layout in view_layouts.items():
        actual_layout = tuple(
            (str(name), str(column_type), bool(is_nullable))
            for name, column_type, is_nullable in connection.execute(
                """
                SELECT column_name, data_type, is_nullable
                FROM system.duckdb_columns()
                WHERE database_name = system.current_database()
                  AND schema_name = 'main'
                  AND table_name = ?
                ORDER BY column_index
                LIMIT ?
                """,
                (view_name, len(expected_layout) + 1),
            ).fetchall()
        )
        expected_view_layout = tuple(
            (name, column_type, True)
            for name, column_type in expected_layout
        )
        if actual_layout != expected_view_layout:
            raise ValueError(
                f"telemetry DuckDB view {view_name!r} is incompatible"
            )
    if _constraint_inventory(connection) != _expected_constraint_inventory(version):
        raise ValueError("telemetry DuckDB constraints are incompatible")
    indexes = connection.execute(
        """
        SELECT index_name FROM system.duckdb_indexes()
        WHERE database_name = system.current_database()
          AND schema_name = 'main'
        LIMIT 1
        """
    ).fetchall()
    if indexes:
        raise ValueError("telemetry DuckDB indexes are incompatible")
    digests = _view_sql_digests(connection, version=version)
    expected_digests = _expected_view_sql_digests(version)
    if digests != expected_digests:
        raise ValueError("telemetry DuckDB views are incompatible")
    if version == 1:
        metadata = connection.execute(
            """
            SELECT singleton, schema_version,
                   runs_view_sha256, stage_view_sha256
            FROM telemetry_metadata
            """
        ).fetchall()
        expected_metadata = [
            (
                True,
                1,
                expected_digests["retrieval_runs_v1"],
                expected_digests["retrieval_stage_latency_v1"],
            )
        ]
    else:
        metadata = connection.execute(
            """
            SELECT singleton, schema_version,
                   runs_view_sha256, stage_view_sha256,
                   command_runs_view_sha256, command_stage_view_sha256
            FROM telemetry_metadata
            """
        ).fetchall()
        expected_metadata = [
            (
                True,
                2,
                expected_digests["retrieval_runs_v1"],
                expected_digests["retrieval_stage_latency_v1"],
                expected_digests["retrieval_command_runs_v2"],
                expected_digests["retrieval_stage_latency_v2"],
            )
        ]
    if metadata != expected_metadata:
        raise ValueError("telemetry DuckDB schema version is incompatible")
    return version


def _constraint_inventory(
    connection: duckdb.DuckDBPyConnection,
) -> tuple[tuple[object, ...], ...]:
    rows = [
        tuple(row)
        for row in connection.execute(
            """
            SELECT table_name, constraint_type, constraint_text,
                   expression, constraint_column_names
            FROM system.duckdb_constraints()
            WHERE database_name = system.current_database()
              AND schema_name = 'main'
            LIMIT 257
            """
        ).fetchall()
    ]
    return tuple(sorted(rows, key=repr))


@lru_cache(maxsize=2)
def _expected_constraint_inventory(version: int) -> tuple[tuple[object, ...], ...]:
    with _connect_database(":memory:") as connection:
        if version == 1:
            _create_v1_schema_objects(connection)
        elif version == 2:
            _create_v1_schema_objects(connection)
            _add_v2_schema_objects(connection)
            _set_v2_metadata_not_null(connection)
        else:
            raise ValueError("unsupported telemetry schema version")
        return _constraint_inventory(connection)


def _view_sql_digests(
    connection: duckdb.DuckDBPyConnection,
    *,
    version: int | None = None,
) -> dict[str, str]:
    selected_version = version
    if selected_version is None:
        count = connection.execute(
            """
            SELECT count(*) FROM system.duckdb_views()
            WHERE database_name = system.current_database()
              AND schema_name = 'main' AND NOT internal
              AND view_name IN (
                  'retrieval_command_runs_v2',
                  'retrieval_stage_latency_v2'
              )
            """
        ).fetchone()
        selected_version = 2 if count and count[0] == 2 else 1
    names = (
        ("retrieval_runs_v1", "retrieval_stage_latency_v1")
        if selected_version == 1
        else tuple(_V2_VIEW_LAYOUTS)
    )
    placeholders = ", ".join("?" for _ in names)
    rows = connection.execute(
        f"""
        SELECT view_name, sql
        FROM system.duckdb_views()
        WHERE database_name = system.current_database()
          AND schema_name = 'main'
          AND view_name IN ({placeholders})
        """,
        names,
    ).fetchall()
    if len(rows) != len(names):
        raise ValueError("telemetry DuckDB views are incompatible")
    return {
        str(name): hashlib.sha256(str(sql).encode("utf-8")).hexdigest()
        for name, sql in rows
    }


@lru_cache(maxsize=2)
def _expected_view_sql_digests(version: int = 2) -> dict[str, str]:
    with _connect_database(":memory:") as connection:
        _create_v1_schema_objects(connection)
        if version == 2:
            _add_v2_schema_objects(connection)
            _set_v2_metadata_not_null(connection)
        elif version != 1:
            raise ValueError("unsupported telemetry schema version")
        return _view_sql_digests(connection, version=version)


def _upgrade_schema_v1_to_v2(connection: duckdb.DuckDBPyConnection) -> None:
    _validate_schema(connection, expected_version=1)
    connection.execute("BEGIN TRANSACTION")
    try:
        _add_v2_data_objects(connection)
        digests = _expected_view_sql_digests(2)
        connection.execute(
            """
            CREATE TABLE telemetry_metadata_v2 (
                singleton BOOLEAN PRIMARY KEY CHECK (singleton),
                schema_version INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL,
                runs_view_sha256 VARCHAR NOT NULL,
                stage_view_sha256 VARCHAR NOT NULL,
                command_runs_view_sha256 VARCHAR NOT NULL,
                command_stage_view_sha256 VARCHAR NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO telemetry_metadata_v2 VALUES (
                true, 2, current_timestamp AT TIME ZONE 'UTC', ?, ?, ?, ?
            )
            """,
            (
                digests["retrieval_runs_v1"],
                digests["retrieval_stage_latency_v1"],
                digests["retrieval_command_runs_v2"],
                digests["retrieval_stage_latency_v2"],
            ),
        )
        connection.execute("DROP TABLE telemetry_metadata")
        connection.execute(
            "ALTER TABLE telemetry_metadata_v2 RENAME TO telemetry_metadata"
        )
        _validate_schema(connection, expected_version=2)
    except Exception:
        try:
            connection.execute("ROLLBACK")
        except Exception:
            pass
        raise
    connection.execute("COMMIT")


def inspect_store_schema_version(paths: TelemetryPaths) -> int | None:
    """Return an exact governed schema version without mutating the store."""

    _validate_fixed_paths(paths)
    try:
        with database_write_lock(paths, timeout_ms=250):
            root_fd = open_verified_directory(paths.directory, repair_mode=False)
            try:
                database = _optional_private_stat(
                    root_fd, DATABASE_BASENAME, kind="file"
                )
                if database is None:
                    return None
                if _optional_private_stat(
                    root_fd,
                    DATABASE_WAL_BASENAME,
                    kind="file",
                    max_bytes=DATABASE_INIT_MAX_BYTES,
                ) is not None:
                    raise StoreUnsafeError("telemetry store path is unsafe")
                _verify_final_database_fd(root_fd)
                with _verified_connection(
                    paths.database_path,
                    root_fd,
                    DATABASE_BASENAME,
                    read_only=True,
                ) as connection:
                    version = _validate_schema(connection)
                    _validate_existing_content(connection, version)
                    return version
            finally:
                os.close(root_fd)
    except QueueLockTimeout as exc:
        raise StoreBusyError("telemetry store is busy") from exc
    except TelemetryStoreError:
        raise
    except (UnsafePathError, ValueError) as exc:
        raise StoreUnsafeError("telemetry store path is unsafe") from exc
    except (duckdb.Error, OSError) as exc:
        raise StoreUnreadableError("telemetry store is unreadable") from exc


def migrate_store_v1_to_v2(
    paths: TelemetryPaths,
    *,
    fault_hook: Callable[[str], None] | None = None,
) -> StoreMigrationResult:
    """Back up and atomically migrate one exact closed version-1 store."""

    _validate_fixed_paths(paths)
    hook = fault_hook or (lambda _phase: None)
    try:
        with database_write_lock(paths, timeout_ms=250):
            return _migrate_store_locked(paths, hook)
    except QueueLockTimeout as exc:
        raise StoreBusyError("telemetry store is busy") from exc
    except TelemetryStoreError:
        raise
    except (UnsafePathError, ValueError, PermissionError) as exc:
        raise StoreUnsafeError("telemetry migration path is unsafe") from exc
    except duckdb.Error as exc:
        raise StoreUnreadableError("telemetry store is unreadable") from exc
    except OSError as exc:
        raise StoreWriteError("telemetry store migration failed") from exc


def _migrate_store_locked(
    paths: TelemetryPaths,
    hook: Callable[[str], None],
) -> StoreMigrationResult:
    root_fd = open_verified_directory(paths.directory)
    scratch_fd = -1
    published = False
    durability_degraded = False
    try:
        if _optional_private_stat(
            root_fd,
            DATABASE_WAL_BASENAME,
            kind="file",
            max_bytes=DATABASE_INIT_MAX_BYTES,
        ) is not None:
            raise StoreUnsafeError("telemetry store path is unsafe")
        source_stat = _verify_final_database_fd(root_fd)
        with _verified_connection(
            paths.database_path,
            root_fd,
            DATABASE_BASENAME,
            read_only=True,
        ) as source:
            _validate_schema(source, expected_version=1)
            source_identity = _validate_existing_content(source, 1)
        hook("validated_source")

        scratch_fd = _prepare_migration_scratch(root_fd)
        hook("scratch_created")
        source_hash = _copy_private_file(
            root_fd,
            DATABASE_BASENAME,
            scratch_fd,
            DATABASE_BASENAME,
        )
        hook("scratch_copied")
        backup_candidate_hash = _copy_private_file(
            root_fd,
            DATABASE_BASENAME,
            scratch_fd,
            DATABASE_BACKUP_BASENAME,
            chunk_hook=lambda: hook("backup_copy_midpoint"),
        )
        hook("backup_candidate_copied")
        if backup_candidate_hash != source_hash:
            raise StoreWriteError("telemetry migration backup copy failed")
        with _verified_connection(
            paths.migration_backup_candidate_path,
            scratch_fd,
            DATABASE_BACKUP_BASENAME,
            read_only=True,
        ) as backup_candidate:
            _validate_schema(backup_candidate, expected_version=1)
            if _validate_existing_content(backup_candidate, 1) != source_identity:
                raise StoreIncompatibleError(
                    "telemetry migration backup candidate is incompatible"
                )
        hook("backup_candidate_validated")

        scratch_stat = stat_private_entry_at(
            scratch_fd, DATABASE_BASENAME, kind="file"
        )
        if scratch_stat.st_size != source_stat.st_size:
            raise StoreWriteError("telemetry migration copy failed")
        with _verified_connection(
            paths.migration_database_path,
            scratch_fd,
            DATABASE_BASENAME,
            read_only=False,
        ) as scratch:
            _upgrade_schema_v1_to_v2(scratch)
        hook("transaction_committed")
        durability_degraded |= _require_wal_absent_after_close(
            scratch_fd, DATABASE_WAL_BASENAME
        )
        with _verified_connection(
            paths.migration_database_path,
            scratch_fd,
            DATABASE_BASENAME,
            read_only=True,
        ) as scratch:
            _validate_schema(scratch, expected_version=2)
            if _validate_existing_content(scratch, 2) != source_identity:
                raise StoreIncompatibleError(
                    "telemetry migration values are incompatible"
                )
        hook("scratch_validated")

        backup = _optional_private_stat(
            root_fd,
            DATABASE_BACKUP_BASENAME,
            kind="file",
        )
        if backup is None:
            safe_link_at(
                scratch_fd,
                DATABASE_BACKUP_BASENAME,
                root_fd,
                DATABASE_BACKUP_BASENAME,
            )
            durability_degraded |= not fsync_directory(root_fd)
            safe_unlink_at(
                scratch_fd,
                DATABASE_BACKUP_BASENAME,
                allowed_nlinks=(2,),
            )
            durability_degraded |= not fsync_directory(scratch_fd)
        else:
            if backup.st_size != source_stat.st_size:
                raise StoreIncompatibleError(
                    "telemetry migration backup is incompatible"
                )
            if _hash_private_file(root_fd, DATABASE_BACKUP_BASENAME) != source_hash:
                raise StoreIncompatibleError(
                    "telemetry migration backup is incompatible"
                )
            safe_unlink_at(scratch_fd, DATABASE_BACKUP_BASENAME)
            durability_degraded |= not fsync_directory(scratch_fd)
        hook("backup_published")
        hook("backup_created")
        with _verified_connection(
            paths.backup_database_path,
            root_fd,
            DATABASE_BACKUP_BASENAME,
            read_only=True,
        ) as backup_connection:
            _validate_schema(backup_connection, expected_version=1)
            if _validate_existing_content(backup_connection, 1) != source_identity:
                raise StoreIncompatibleError(
                    "telemetry migration backup is incompatible"
                )
        hook("backup_validated")
        hook("backup_fsynced")

        current = _verify_final_database_fd(root_fd)
        if (current.st_dev, current.st_ino, current.st_size) != (
            source_stat.st_dev,
            source_stat.st_ino,
            source_stat.st_size,
        ):
            raise StoreUnsafeError("telemetry store changed during migration")
        os.rename(
            DATABASE_BASENAME,
            DATABASE_BASENAME,
            src_dir_fd=scratch_fd,
            dst_dir_fd=root_fd,
        )
        published = True
        hook("canonical_published")
        durability_degraded |= not fsync_directory(root_fd)
        hook("directory_fsynced")
        final_stat = _verify_final_database_fd(root_fd)
        _require_path_matches_stat(paths.database_path, final_stat)
        with _verified_connection(
            paths.database_path,
            root_fd,
            DATABASE_BASENAME,
            read_only=True,
        ) as final:
            _validate_schema(final, expected_version=2)
            if _validate_existing_content(final, 2) != source_identity:
                raise StoreIncompatibleError(
                    "telemetry migrated store is incompatible"
                )
        os.close(scratch_fd)
        scratch_fd = -1
        safe_rmdir_at(root_fd, DATABASE_MIGRATION_DIRECTORY)
        durability_degraded |= not fsync_directory(root_fd)
        hook("state_publication_ready")
        return StoreMigrationResult(
            runs=source_identity.counts[0],
            spans=source_identity.counts[1],
            events=source_identity.counts[2],
            backup_present=True,
            durability_degraded=durability_degraded,
        )
    except Exception:
        if not published and scratch_fd >= 0:
            _remove_safe_migration_scratch(root_fd, scratch_fd)
            scratch_fd = -1
        raise
    finally:
        if scratch_fd >= 0:
            os.close(scratch_fd)
        os.close(root_fd)


def migration_backup_matches_v1_source(paths: TelemetryPaths) -> bool:
    """Prove an immutable final backup is the exact current canonical v1 source."""

    _validate_fixed_paths(paths)
    try:
        with database_write_lock(paths, timeout_ms=250):
            root_fd = open_verified_directory(paths.directory)
            try:
                backup_stat = _optional_private_stat(
                    root_fd,
                    DATABASE_BACKUP_BASENAME,
                    kind="file",
                    allowed_nlinks=(1, 2),
                )
                if backup_stat is None:
                    return False
                source_stat = _verify_final_database_fd(root_fd)
                with _verified_connection(
                    paths.database_path,
                    root_fd,
                    DATABASE_BASENAME,
                    read_only=True,
                ) as source:
                    _validate_schema(source, expected_version=1)
                    source_identity = _validate_existing_content(source, 1)
                backup_identity = _validate_retained_backup(
                    paths,
                    root_fd,
                    allowed_nlinks=(backup_stat.st_nlink,),
                )
                if (
                    backup_stat.st_size != source_stat.st_size
                    or backup_identity != source_identity
                    or _hash_private_file(
                        root_fd,
                        DATABASE_BACKUP_BASENAME,
                        allowed_nlinks=(backup_stat.st_nlink,),
                    )
                    != _hash_private_file(root_fd, DATABASE_BASENAME)
                ):
                    raise StoreIncompatibleError(
                        "telemetry migration backup is incompatible"
                    )
                if backup_stat.st_nlink == 2:
                    scratch_fd = _prepare_migration_scratch(root_fd)
                    os.close(scratch_fd)
                return True
            finally:
                os.close(root_fd)
    except QueueLockTimeout as exc:
        raise StoreBusyError("telemetry store is busy") from exc
    except TelemetryStoreError:
        raise
    except (UnsafePathError, ValueError, PermissionError) as exc:
        raise StoreUnsafeError("telemetry migration backup is unsafe") from exc
    except duckdb.Error as exc:
        raise StoreUnreadableError("telemetry store is unreadable") from exc
    except OSError as exc:
        raise StoreWriteError("telemetry backup validation failed") from exc


def recover_prepublication_migration_scratch(paths: TelemetryPaths) -> bool:
    """Remove only recognized scratch after re-proving canonical exact v1."""

    _validate_fixed_paths(paths)
    try:
        with database_write_lock(paths, timeout_ms=250):
            root_fd = open_verified_directory(paths.directory)
            try:
                if _optional_private_stat(
                    root_fd,
                    DATABASE_MIGRATION_DIRECTORY,
                    kind="directory",
                ) is None:
                    return False
                with _verified_connection(
                    paths.database_path,
                    root_fd,
                    DATABASE_BASENAME,
                    read_only=True,
                ) as connection:
                    _validate_schema(connection, expected_version=1)
                    _validate_existing_content(connection, 1)
                scratch_fd = _prepare_migration_scratch(root_fd)
                os.close(scratch_fd)
                safe_rmdir_at(root_fd, DATABASE_MIGRATION_DIRECTORY)
                fsync_directory(root_fd)
                return True
            finally:
                os.close(root_fd)
    except QueueLockTimeout as exc:
        raise StoreBusyError("telemetry store is busy") from exc
    except TelemetryStoreError:
        raise
    except (UnsafePathError, ValueError, PermissionError) as exc:
        raise StoreUnsafeError("telemetry migration path is unsafe") from exc
    except duckdb.Error as exc:
        raise StoreUnreadableError("telemetry store is unreadable") from exc
    except OSError as exc:
        raise StoreWriteError("telemetry scratch recovery failed") from exc


def reconcile_already_current_store(paths: TelemetryPaths) -> StoreReconcileResult:
    """Validate exact v2/backup and clean only empty post-publication scratch."""

    _validate_fixed_paths(paths)
    try:
        with database_write_lock(paths, timeout_ms=250):
            root_fd = open_verified_directory(paths.directory)
            try:
                scratch_present = False
                try:
                    scratch_fd = open_private_directory_at(
                        root_fd,
                        DATABASE_MIGRATION_DIRECTORY,
                        create=False,
                    )
                except FileNotFoundError:
                    scratch_fd = -1
                if scratch_fd >= 0:
                    scratch_present = True
                    try:
                        names = scan_fixed_private_inventory(
                            scratch_fd,
                            allowed_names=_MIGRATION_SCRATCH_NAMES,
                        )
                        if names:
                            raise StoreUnsafeError(
                                "telemetry migration path is unresolved"
                            )
                    finally:
                        os.close(scratch_fd)
                if _optional_private_stat(
                    root_fd,
                    DATABASE_WAL_BASENAME,
                    kind="file",
                    max_bytes=DATABASE_INIT_MAX_BYTES,
                ) is not None:
                    raise StoreUnsafeError("telemetry store path is unsafe")
                backup_present = _optional_private_stat(
                    root_fd,
                    DATABASE_BACKUP_BASENAME,
                    kind="file",
                ) is not None
                with _verified_connection(
                    paths.database_path,
                    root_fd,
                    DATABASE_BASENAME,
                    read_only=True,
                ) as connection:
                    _validate_schema(connection, expected_version=2)
                    v1_identity = _validate_existing_content(connection, 2)
                    persisted_runs = _persisted_run_count(connection)
                if backup_present and (
                    _validate_retained_backup(paths, root_fd) != v1_identity
                ):
                    raise StoreIncompatibleError(
                        "telemetry retained backup history differs"
                    )
                durability_degraded = False
                if scratch_present:
                    safe_rmdir_at(root_fd, DATABASE_MIGRATION_DIRECTORY)
                    durability_degraded = not fsync_directory(root_fd)
                final_stat = _verify_final_database_fd(root_fd)
                return StoreReconcileResult(
                    snapshot=_store_snapshot(
                        persisted_runs,
                        final_stat,
                        schema_version=2,
                    ),
                    backup_present=backup_present,
                    scratch_recovered=scratch_present,
                    durability_degraded=durability_degraded,
                )
            finally:
                os.close(root_fd)
    except QueueLockTimeout as exc:
        raise StoreBusyError("telemetry store is busy") from exc
    except TelemetryStoreError:
        raise
    except (UnsafePathError, ValueError, PermissionError) as exc:
        raise StoreUnsafeError("telemetry migration path is unsafe") from exc
    except duckdb.Error as exc:
        raise StoreUnreadableError("telemetry store is unreadable") from exc
    except OSError as exc:
        raise StoreWriteError("telemetry store reconciliation failed") from exc


def _prepare_migration_scratch(root_fd: int) -> int:
    try:
        scratch_fd = open_private_directory_at(
            root_fd, DATABASE_MIGRATION_DIRECTORY, create=False
        )
    except FileNotFoundError:
        return open_private_directory_at(
            root_fd, DATABASE_MIGRATION_DIRECTORY, create=True
        )
    try:
        names = scan_fixed_private_inventory(
            scratch_fd,
            allowed_names=_MIGRATION_SCRATCH_NAMES,
        )
    except UnsafePathError:
        os.close(scratch_fd)
        raise StoreUnsafeError("telemetry migration path is unsafe") from None
    for name in sorted(names):
        observed = stat_private_entry_at(
            scratch_fd,
            name,
            kind="file",
            allowed_nlinks=(1, 2) if name == DATABASE_BACKUP_BASENAME else (1,),
        )
        if name == DATABASE_BACKUP_BASENAME and observed.st_nlink == 2:
            final = stat_private_entry_at(
                root_fd,
                DATABASE_BACKUP_BASENAME,
                kind="file",
                allowed_nlinks=(2,),
            )
            if (observed.st_dev, observed.st_ino) != (final.st_dev, final.st_ino):
                os.close(scratch_fd)
                raise StoreUnsafeError("telemetry backup publication is unsafe")
            safe_unlink_at(
                scratch_fd,
                name,
                allowed_nlinks=(2,),
            )
        else:
            safe_unlink_at(scratch_fd, name)
    fsync_directory(scratch_fd)
    return scratch_fd


def _remove_safe_migration_scratch(root_fd: int, scratch_fd: int) -> None:
    try:
        try:
            names = scan_fixed_private_inventory(
                scratch_fd,
                allowed_names=_MIGRATION_SCRATCH_NAMES,
            )
        except UnsafePathError:
            os.close(scratch_fd)
            return
        for name in sorted(names):
            stat_private_entry_at(
                scratch_fd, name, kind="file", allowed_nlinks=(1,)
            )
            safe_unlink_at(scratch_fd, name)
        fsync_directory(scratch_fd)
        os.close(scratch_fd)
        safe_rmdir_at(root_fd, DATABASE_MIGRATION_DIRECTORY)
        fsync_directory(root_fd)
    except Exception:
        try:
            os.close(scratch_fd)
        except OSError:
            pass


def _copy_private_file(
    source_parent_fd: int,
    source_name: str,
    destination_parent_fd: int,
    destination_name: str,
    *,
    chunk_hook: Callable[[], None] | None = None,
) -> str:
    source = open_private_file_at(
        source_parent_fd, source_name, flags=os.O_RDONLY
    )
    try:
        source_stat = verify_private_file_fd(source)
        destination = open_private_file_at(
            destination_parent_fd,
            destination_name,
            flags=os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        )
        digest = hashlib.sha256()
        written = 0
        hook_called = False
        try:
            while True:
                chunk = os.read(source, 1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                view = memoryview(chunk)
                while view:
                    count = os.write(destination, view)
                    if count <= 0:
                        raise OSError("short telemetry migration write")
                    written += count
                    view = view[count:]
                if chunk_hook is not None and not hook_called:
                    hook_called = True
                    chunk_hook()
            os.fchmod(destination, 0o600)
            os.fsync(destination)
            observed = verify_private_file_fd(destination)
            if written != source_stat.st_size or observed.st_size != written:
                raise StoreWriteError("telemetry migration copy failed")
        finally:
            os.close(destination)
        return digest.hexdigest()
    finally:
        os.close(source)


def _hash_private_file(
    parent_fd: int,
    name: str,
    *,
    allowed_nlinks: tuple[int, ...] = (1,),
) -> str:
    descriptor = open_private_file_at(
        parent_fd,
        name,
        flags=os.O_RDONLY,
        allowed_nlinks=allowed_nlinks,
    )
    digest = hashlib.sha256()
    try:
        before = verify_private_file_fd(
            descriptor, allowed_nlinks=allowed_nlinks
        )
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        after = verify_private_file_fd(
            descriptor, allowed_nlinks=allowed_nlinks
        )
        if (before.st_dev, before.st_ino, before.st_size) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
        ):
            raise StoreUnsafeError("telemetry backup changed while hashing")
        return digest.hexdigest()
    finally:
        os.close(descriptor)


def _v1_counts(connection: duckdb.DuckDBPyConnection) -> tuple[int, int, int]:
    statements = (
        "SELECT count(*) FROM trace_runs",
        """SELECT count(*) FROM spans
           WHERE trace_id IN (SELECT trace_id FROM trace_runs)""",
        """SELECT count(*) FROM span_events
           WHERE trace_id IN (SELECT trace_id FROM trace_runs)""",
    )
    return tuple(
        int(connection.execute(statement).fetchone()[0])
        for statement in statements
    )


def _validate_existing_content(
    connection: duckdb.DuckDBPyConnection,
    schema_version: int,
) -> _V1ContentIdentity:
    v1_identity = _validate_v1_content(connection)
    total_spans = int(connection.execute("SELECT count(*) FROM spans").fetchone()[0])
    total_events = int(
        connection.execute("SELECT count(*) FROM span_events").fetchone()[0]
    )
    if schema_version == 1:
        if (
            v1_identity.counts[1] != total_spans
            or v1_identity.counts[2] != total_events
        ):
            raise ValueError("telemetry v1 graph inventory is incompatible")
        return v1_identity
    if schema_version != 2:
        raise ValueError("telemetry content schema version is incompatible")
    v2_identity = _validate_v2_content(connection)
    if (
        v1_identity.counts[1] + v2_identity.counts[2] != total_spans
        or v1_identity.counts[2] + v2_identity.counts[3] != total_events
    ):
        raise ValueError("telemetry shared graph inventory is incompatible")
    return v1_identity


def _validate_v1_content(
    connection: duckdb.DuckDBPyConnection,
) -> _V1ContentIdentity:
    """Stream exact v1 traces in bounded batches through the canonical validator."""

    from buoy_search.telemetry.envelope import TraceRows, encode_trace_envelope_v1

    _preflight_v1_scalar_lengths(connection)
    physical_counts = _v1_counts(connection)
    digest = hashlib.sha256()
    observed_runs = 0
    observed_spans = 0
    observed_events = 0
    after_trace_id = ""
    while True:
        trace_ids = [
            str(row[0])
            for row in connection.execute(
                """
                SELECT trace_id
                FROM trace_runs
                WHERE trace_id > ?
                ORDER BY trace_id
                LIMIT ?
                """,
                (after_trace_id, MIGRATION_BATCH_SIZE),
            ).fetchall()
        ]
        if not trace_ids:
            break
        for trace_id in trace_ids:
            counts = connection.execute(
                """
                SELECT
                    (SELECT count(*) FROM spans WHERE trace_id = ?),
                    (SELECT count(*) FROM span_events WHERE trace_id = ?)
                """,
                (trace_id, trace_id),
            ).fetchone()
            if counts is None or not (1 <= counts[0] <= 256) or not (0 <= counts[1] <= 1):
                raise ValueError("telemetry v1 trace cardinality is incompatible")
            run_rows = connection.execute(
                "SELECT * FROM trace_runs WHERE trace_id = ?",
                (trace_id,),
            ).fetchall()
            span_rows = connection.execute(
                """
                SELECT * FROM spans
                WHERE trace_id = ?
                ORDER BY started_at, span_id
                """,
                (trace_id,),
            ).fetchall()
            event_rows = connection.execute(
                """
                SELECT * FROM span_events
                WHERE trace_id = ?
                ORDER BY event_index
                """,
                (trace_id,),
            ).fetchall()
            if len(run_rows) != 1:
                raise ValueError("telemetry v1 run cardinality is incompatible")
            rows = TraceRows(
                run=tuple(run_rows[0]),
                spans=tuple(tuple(row) for row in span_rows),
                events=tuple(tuple(row) for row in event_rows),
            )
            payload = encode_trace_envelope_v1(rows)
            digest.update(len(payload).to_bytes(8, "big"))
            digest.update(payload)
            observed_runs += 1
            observed_spans += len(span_rows)
            observed_events += len(event_rows)
        after_trace_id = trace_ids[-1]
    observed_counts = (observed_runs, observed_spans, observed_events)
    if observed_counts != physical_counts:
        raise ValueError("telemetry v1 graph inventory is incompatible")
    return _V1ContentIdentity(observed_counts, digest.hexdigest())


def _validate_v2_content(
    connection: duckdb.DuckDBPyConnection,
) -> _V2ContentIdentity:
    """Stream exact v2 traces through the canonical graph/privacy validator."""

    from buoy_search.telemetry.envelope import (
        CommandTraceRows,
        encode_trace_envelope_v2,
    )

    _preflight_v2_scalar_lengths(connection)
    physical_counts = tuple(
        int(connection.execute(statement).fetchone()[0])
        for statement in (
            "SELECT count(*) FROM retrieve_command_runs",
            "SELECT count(*) FROM retrieval_operations",
            """SELECT count(*) FROM spans WHERE trace_id IN
               (SELECT trace_id FROM retrieve_command_runs)""",
            """SELECT count(*) FROM span_events WHERE trace_id IN
               (SELECT trace_id FROM retrieve_command_runs)""",
        )
    )
    digest = hashlib.sha256()
    observed = [0, 0, 0, 0]
    after_trace_id = ""
    while True:
        trace_ids = [
            str(row[0])
            for row in connection.execute(
                """
                SELECT trace_id FROM retrieve_command_runs
                WHERE trace_id > ? ORDER BY trace_id LIMIT ?
                """,
                (after_trace_id, MIGRATION_BATCH_SIZE),
            ).fetchall()
        ]
        if not trace_ids:
            break
        for trace_id in trace_ids:
            counts = connection.execute(
                """
                SELECT
                    (SELECT count(*) FROM retrieval_operations WHERE trace_id = ?),
                    (SELECT count(*) FROM spans WHERE trace_id = ?),
                    (SELECT count(*) FROM span_events WHERE trace_id = ?)
                """,
                (trace_id, trace_id, trace_id),
            ).fetchone()
            if counts is None or not (
                0 <= counts[0] <= 1
                and 1 <= counts[1] <= 256
                and 0 <= counts[2] <= 1
            ):
                raise ValueError("telemetry v2 trace cardinality is incompatible")
            command_rows = connection.execute(
                "SELECT * FROM retrieve_command_runs WHERE trace_id = ?",
                (trace_id,),
            ).fetchall()
            operation_rows = connection.execute(
                "SELECT * FROM retrieval_operations WHERE trace_id = ?",
                (trace_id,),
            ).fetchall()
            span_rows = connection.execute(
                """SELECT * FROM spans WHERE trace_id = ?
                   ORDER BY started_at, span_id""",
                (trace_id,),
            ).fetchall()
            event_rows = connection.execute(
                """SELECT * FROM span_events WHERE trace_id = ?
                   ORDER BY event_index""",
                (trace_id,),
            ).fetchall()
            if len(command_rows) != 1:
                raise ValueError("telemetry v2 command cardinality is incompatible")
            rows = CommandTraceRows(
                command=tuple(command_rows[0]),
                retrieval_operation=(
                    tuple(operation_rows[0]) if operation_rows else None
                ),
                spans=tuple(tuple(row) for row in span_rows),
                events=tuple(tuple(row) for row in event_rows),
            )
            payload = encode_trace_envelope_v2(rows)
            digest.update(len(payload).to_bytes(8, "big"))
            digest.update(payload)
            observed[0] += 1
            observed[1] += len(operation_rows)
            observed[2] += len(span_rows)
            observed[3] += len(event_rows)
        after_trace_id = trace_ids[-1]
    observed_counts = tuple(observed)
    if observed_counts != physical_counts:
        raise ValueError("telemetry v2 graph inventory is incompatible")
    return _V2ContentIdentity(observed_counts, digest.hexdigest())


def _preflight_v2_scalar_lengths(
    connection: duckdb.DuckDBPyConnection,
) -> None:
    _preflight_scalar_lengths(
        connection,
        ("retrieve_command_runs", "retrieval_operations", "spans", "span_events"),
        _V2_TABLE_LAYOUTS,
    )


def _preflight_v1_scalar_lengths(
    connection: duckdb.DuckDBPyConnection,
) -> None:
    _preflight_scalar_lengths(
        connection,
        ("trace_runs", "spans", "span_events"),
        _V1_TABLE_LAYOUTS,
    )


def _preflight_scalar_lengths(
    connection: duckdb.DuckDBPyConnection,
    table_names: tuple[str, ...],
    layouts: dict[str, tuple[tuple[str, str, bool, bool], ...]],
) -> None:
    for table_name in table_names:
        columns = [name for name, _type, _nullable, _key in layouts[table_name]]
        expressions = ", ".join(
            f'max(octet_length(encode(CAST("{column}" AS VARCHAR))))'
            for column in columns
        )
        maxima = connection.execute(
            f'SELECT {expressions} FROM "{table_name}"'
        ).fetchone()
        if maxima is None:
            raise ValueError("telemetry scalar preflight failed")
        if any(
            value is not None and (value < 0 or value > 65_536)
            for value in maxima
        ):
            raise ValueError("telemetry scalar value is oversized")
