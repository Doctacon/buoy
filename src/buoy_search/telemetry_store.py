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
from typing import TYPE_CHECKING, Iterator, Literal, Protocol

import duckdb

from buoy_search.telemetry_queue import (
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
    stat_private_entry_at,
    verify_private_file_fd,
)

if TYPE_CHECKING:
    from buoy_search.telemetry_envelope import TraceRows
    from buoy_search.telemetry_queue import TelemetryPaths


TELEMETRY_SCHEMA_VERSION = 1
DATABASE_BASENAME = "telemetry.duckdb"
DATABASE_WAL_BASENAME = "telemetry.duckdb.wal"
DATABASE_INIT_DIRECTORY = "database-init-v1"
DATABASE_INIT_MAX_BYTES = 16_777_216

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


class _RowsLike(Protocol):
    run: tuple[object, ...]
    spans: tuple[tuple[object, ...], ...]
    events: tuple[tuple[object, ...], ...]


_TABLE_LAYOUTS: dict[
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

_VIEW_LAYOUTS: dict[str, tuple[tuple[str, str], ...]] = {
    "retrieval_runs_v1": tuple(
        (name, column_type)
        for name, column_type, _not_null, _primary_key in _TABLE_LAYOUTS[
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

_TABLES_DDL = """
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
            if wal_stat is not None:
                raise StoreUnsafeError("telemetry store path is unsafe")
            result = _initialize_database_atomically(paths, root_fd, rows)
            return _with_degradation(result, durability_degraded)
        _verify_final_database_fd(root_fd)
        if wal_stat is not None:
            durability_degraded |= _recover_final_wal(paths, root_fd)
        result = _append_existing(paths, root_fd, rows)
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
                _validate_schema(connection)
                existing = _read_trace_graph(connection, str(rows.run[0]))
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
            snapshot=_store_snapshot(persisted_runs, final_stat),
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
    }
    for field, expected_path in expected.items():
        if Path(getattr(paths, field)) != expected_path:
            raise StoreUnsafeError("telemetry store path is unsafe")


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
        entries = set(os.listdir(scratch_fd))
        allowed = {DATABASE_BASENAME, DATABASE_WAL_BASENAME}
        if not entries <= allowed:
            raise StoreUnsafeError("telemetry initialization path is unsafe")
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
                if _read_trace_graph(connection, str(rows.run[0])) != _row_graph(
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
) -> StoreAppendResult:
    try:
        with _verified_connection(
            paths.database_path,
            root_fd,
            DATABASE_BASENAME,
            read_only=False,
        ) as connection:
            result = _validate_and_insert_or_classify_transaction(
                connection,
                rows,
            )
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
        snapshot=_store_snapshot(persisted_runs, final_stat),
        durability_degraded=durability_degraded,
    )


def _persisted_run_count(connection: duckdb.DuckDBPyConnection) -> int:
    row = connection.execute("SELECT count(*) FROM trace_runs").fetchone()
    if row is None or type(row[0]) is not int or row[0] < 0:
        raise ValueError("telemetry DuckDB run count is incompatible")
    return row[0]


def _store_snapshot(
    persisted_runs: int,
    database_stat: os.stat_result,
) -> StoreSnapshot:
    return StoreSnapshot(
        schema_version=TELEMETRY_SCHEMA_VERSION,
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
) -> Iterator[duckdb.DuckDBPyConnection]:
    before = stat_private_entry_at(
        parent_fd,
        basename,
        kind="file",
        max_bytes=max_bytes,
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
            _initialize_schema(connection)
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
            _validate_schema(connection)
        except ValueError as exc:
            raise StoreIncompatibleError(
                "telemetry store schema is incompatible"
            ) from exc
        except duckdb.Error as exc:
            raise StoreUnreadableError(
                "telemetry store is unreadable"
            ) from exc
        trace_id = str(rows.run[0])
        try:
            existing = _read_trace_graph(connection, trace_id)
            if any(existing):
                result: StoreOutcome = (
                    "replayed"
                    if existing == _row_graph(rows)
                    else "conflict"
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


def _insert_trace_rows(
    connection: duckdb.DuckDBPyConnection,
    rows: _RowsLike,
) -> None:
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


def _row_graph(
    rows: _RowsLike,
) -> tuple[
    tuple[tuple[object, ...], ...],
    tuple[tuple[object, ...], ...],
    tuple[tuple[object, ...], ...],
]:
    return ((tuple(rows.run),), tuple(rows.spans), tuple(rows.events))


def _read_trace_graph(
    connection: duckdb.DuckDBPyConnection,
    trace_id: str,
) -> tuple[
    tuple[tuple[object, ...], ...],
    tuple[tuple[object, ...], ...],
    tuple[tuple[object, ...], ...],
]:
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
            SELECT *
            FROM spans
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
            SELECT *
            FROM span_events
            WHERE trace_id = ?
            ORDER BY event_index
            """,
            (trace_id,),
        ).fetchall()
    )
    return runs, spans, events


def _create_schema_objects(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute(_TABLES_DDL)
    connection.execute(_RUNS_VIEW_DDL)
    connection.execute(_STAGE_VIEW_DDL)


def _initialize_schema(connection: duckdb.DuckDBPyConnection) -> None:
    _create_schema_objects(connection)
    view_digests = _view_sql_digests(connection)
    expected_digests = _expected_view_sql_digests()
    if view_digests != expected_digests:
        raise ValueError("telemetry DuckDB views are incompatible")
    connection.execute(
        """
        INSERT INTO telemetry_metadata VALUES (
            true,
            1,
            current_timestamp AT TIME ZONE 'UTC',
            ?,
            ?
        )
        """,
        (
            expected_digests["retrieval_runs_v1"],
            expected_digests["retrieval_stage_latency_v1"],
        ),
    )


def _validate_schema(connection: duckdb.DuckDBPyConnection) -> None:
    table_names = {
        str(name)
        for (name,) in connection.execute(
            """
            SELECT table_name
            FROM system.duckdb_tables()
            WHERE database_name = system.current_database()
              AND schema_name = 'main'
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
            """
        ).fetchall()
    }
    if table_names != set(_TABLE_LAYOUTS) or view_names != set(_VIEW_LAYOUTS):
        raise ValueError("telemetry DuckDB schema objects are incompatible")
    for table_name, expected_layout in _TABLE_LAYOUTS.items():
        actual_layout = tuple(
            (str(row[1]), str(row[2]), bool(row[3]), bool(row[5]))
            for row in connection.execute(
                f"SELECT * FROM system.pragma_table_info('{table_name}')"
            ).fetchall()
        )
        if actual_layout != expected_layout:
            raise ValueError(
                f"telemetry DuckDB table {table_name!r} is incompatible"
            )
    for view_name, expected_layout in _VIEW_LAYOUTS.items():
        actual_layout = tuple(
            (str(name), str(column_type))
            for name, column_type in connection.execute(
                """
                SELECT column_name, data_type
                FROM system.duckdb_columns()
                WHERE database_name = system.current_database()
                  AND schema_name = 'main'
                  AND table_name = ?
                ORDER BY column_index
                """,
                (view_name,),
            ).fetchall()
        )
        if actual_layout != expected_layout:
            raise ValueError(
                f"telemetry DuckDB view {view_name!r} is incompatible"
            )
    metadata = connection.execute(
        """
        SELECT
            singleton,
            schema_version,
            runs_view_sha256,
            stage_view_sha256
        FROM telemetry_metadata
        """
    ).fetchall()
    view_digests = _view_sql_digests(connection)
    expected_digests = _expected_view_sql_digests()
    if view_digests != expected_digests:
        raise ValueError("telemetry DuckDB views are incompatible")
    expected_metadata = [
        (
            True,
            TELEMETRY_SCHEMA_VERSION,
            expected_digests["retrieval_runs_v1"],
            expected_digests["retrieval_stage_latency_v1"],
        )
    ]
    if metadata != expected_metadata:
        raise ValueError("telemetry DuckDB schema version is incompatible")


def _view_sql_digests(
    connection: duckdb.DuckDBPyConnection,
) -> dict[str, str]:
    rows = connection.execute(
        """
        SELECT view_name, sql
        FROM system.duckdb_views()
        WHERE database_name = system.current_database()
          AND schema_name = 'main'
          AND view_name IN (
              'retrieval_runs_v1',
              'retrieval_stage_latency_v1'
          )
        """
    ).fetchall()
    if len(rows) != len(_VIEW_LAYOUTS):
        raise ValueError("telemetry DuckDB views are incompatible")
    return {
        str(name): hashlib.sha256(str(sql).encode("utf-8")).hexdigest()
        for name, sql in rows
    }


@lru_cache(maxsize=1)
def _expected_view_sql_digests() -> dict[str, str]:
    with _connect_database(":memory:") as connection:
        _create_schema_objects(connection)
        return _view_sql_digests(connection)
