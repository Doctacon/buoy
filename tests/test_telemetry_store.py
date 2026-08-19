from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timedelta
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import duckdb

from buoy_search.telemetry_envelope import TraceRows
from buoy_search.telemetry_queue import QueueLockTimeout, telemetry_paths
from buoy_search import telemetry_store


_SAFE_CONFIG = {
    "enable_external_access": "false",
    "autoinstall_known_extensions": "false",
    "autoload_known_extensions": "false",
    "allow_community_extensions": "false",
}


def _trace_rows(number: int = 1) -> TraceRows:
    trace_id = f"{number:032x}"
    root_span_id = f"{number * 2:016x}"
    child_span_id = f"{number * 2 + 1:016x}"
    started_at = datetime(2024, 1, 1, 12, 0) + timedelta(seconds=number)
    ended_at = started_at + timedelta(milliseconds=5)
    return TraceRows(
        run=(
            trace_id,
            root_span_id,
            started_at,
            ended_at,
            5.0,
            "explicit_single",
            "success",
            1,
            1,
            1,
            1,
            0,
            False,
            False,
            None,
            None,
            "custom",
            "custom",
            10,
            10,
            "0+test",
            1,
        ),
        spans=(
            (
                trace_id,
                root_span_id,
                None,
                "buoy.retrieve",
                started_at,
                ended_at,
                5.0,
                "OK",
                '{"buoy.observation.schema_version":1}',
            ),
            (
                trace_id,
                child_span_id,
                root_span_id,
                "buoy.query.embed",
                started_at + timedelta(milliseconds=1),
                started_at + timedelta(milliseconds=2),
                1.0,
                "OK",
                '{"buoy.embedding.model":"custom"}',
            ),
        ),
        events=(
            (
                trace_id,
                root_span_id,
                0,
                "retrieval.widened",
                started_at + timedelta(milliseconds=3),
                '{"buoy.retrieval.final_fanout":1}',
            ),
        ),
    )


class TelemetryStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name) / "telemetry"
        self.paths = telemetry_paths(self.root)

    def _connect(self, *, read_only: bool = False) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(
            str(self.paths.database_path),
            read_only=read_only,
            config=_SAFE_CONFIG,
        )

    def _counts(self) -> tuple[int, int, int]:
        with self._connect(read_only=True) as connection:
            return tuple(
                connection.execute(f"SELECT count(*) FROM {table}").fetchone()[
                    0
                ]
                for table in ("trace_runs", "spans", "span_events")
            )

    def test_first_commit_publishes_complete_private_v1_store(self) -> None:
        rows = _trace_rows()

        result = telemetry_store.append_trace(self.paths, rows)

        self.assertEqual(result.outcome, "committed")
        self.assertFalse(result.durability_degraded)
        database_stat = self.paths.database_path.stat()
        self.assertEqual(
            result.snapshot,
            telemetry_store.StoreSnapshot(
                schema_version=1,
                persisted_runs_snapshot=1,
                database_device=database_stat.st_dev,
                database_inode=database_stat.st_ino,
                database_bytes=database_stat.st_size,
            ),
        )
        self.assertEqual(stat.S_IMODE(database_stat.st_mode), 0o600)
        self.assertEqual(database_stat.st_nlink, 1)
        self.assertFalse(self.paths.database_wal_path.exists())
        self.assertFalse(self.paths.database_init_directory.exists())
        self.assertEqual(
            {path.name for path in self.root.iterdir()},
            {"telemetry.duckdb", "write.lock"},
        )
        with self._connect(read_only=True) as connection:
            metadata = connection.execute(
                "SELECT schema_version, created_at FROM telemetry_metadata"
            ).fetchone()
            self.assertIsNotNone(metadata)
            assert metadata is not None
            self.assertEqual(metadata[0], 1)
            self.assertIsNone(metadata[1].tzinfo)
            self.assertEqual(
                connection.execute(
                    "SELECT count(*) FROM retrieval_runs_v1"
                ).fetchone(),
                (1,),
            )
            self.assertEqual(
                connection.execute(
                    "SELECT count(*) FROM retrieval_stage_latency_v1"
                ).fetchone(),
                (1,),
            )
            self.assertEqual(
                telemetry_store._read_trace_graph(
                    connection,
                    str(rows.run[0]),
                ),
                telemetry_store._row_graph(rows),
            )

    def test_exact_replay_and_second_trace_are_idempotent(self) -> None:
        first = _trace_rows(1)
        second = _trace_rows(2)

        self.assertEqual(
            telemetry_store.append_trace(self.paths, first).outcome,
            "committed",
        )
        self.assertEqual(
            telemetry_store.append_trace(self.paths, first).outcome,
            "replayed",
        )
        self.assertEqual(self._counts(), (1, 2, 1))
        self.assertEqual(
            telemetry_store.append_trace(self.paths, second).outcome,
            "committed",
        )
        self.assertEqual(self._counts(), (2, 4, 2))

    def test_any_run_span_or_event_graph_difference_is_a_conflict(self) -> None:
        rows = _trace_rows()
        telemetry_store.append_trace(self.paths, rows)
        changed_run = list(rows.run)
        changed_run[7] = 2
        changed_span = list(rows.spans[1])
        changed_span[8] = '{"buoy.embedding.model":"different"}'
        changed_event = list(rows.events[0])
        changed_event[5] = '{"buoy.retrieval.final_fanout":2}'
        extra_span = (
            str(rows.run[0]),
            "f" * 16,
            str(rows.run[1]),
            "buoy.rerank",
            rows.run[2],
            rows.run[3],
            5.0,
            "OK",
            "{}",
        )
        variants = (
            replace(rows, run=tuple(changed_run)),
            replace(
                rows,
                spans=(rows.spans[0], tuple(changed_span)),
            ),
            replace(rows, events=(tuple(changed_event),)),
            replace(rows, spans=rows.spans[:1]),
            replace(rows, spans=(*rows.spans, extra_span)),
            replace(rows, events=()),
        )

        for variant in variants:
            with self.subTest(variant=variant):
                self.assertEqual(
                    telemetry_store.append_trace(self.paths, variant).outcome,
                    "conflict",
                )
                self.assertEqual(self._counts(), (1, 2, 1))
        with self._connect(read_only=True) as connection:
            self.assertEqual(
                telemetry_store._read_trace_graph(
                    connection,
                    str(rows.run[0]),
                ),
                telemetry_store._row_graph(rows),
            )

    def test_orphaned_existing_graph_conflicts_without_mutation(self) -> None:
        rows = _trace_rows()
        telemetry_store.append_trace(self.paths, rows)
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM trace_runs WHERE trace_id = ?",
                (rows.run[0],),
            )

        result = telemetry_store.append_trace(self.paths, rows)

        self.assertEqual(result.outcome, "conflict")
        self.assertEqual(self._counts(), (0, 2, 1))

    def test_terminal_inspection_proves_replay_or_conflict_without_write(
        self,
    ) -> None:
        rows = _trace_rows()
        telemetry_store.append_trace(self.paths, rows)
        changed = list(rows.run)
        changed[7] = 2

        replay = telemetry_store.inspect_trace_terminal(self.paths, rows)
        conflict = telemetry_store.inspect_trace_terminal(
            self.paths,
            replace(rows, run=tuple(changed)),
        )

        self.assertEqual(replay.outcome, "replayed")
        self.assertEqual(conflict.outcome, "conflict")
        self.assertEqual(replay.snapshot.persisted_runs_snapshot, 1)
        self.assertEqual(conflict.snapshot, replay.snapshot)
        self.assertFalse(replay.durability_degraded)
        self.assertEqual(self._counts(), (1, 2, 1))

    def test_terminal_inspection_rejects_an_absent_trace(self) -> None:
        telemetry_store.append_trace(self.paths, _trace_rows(1))

        with self.assertRaises(telemetry_store.StoreUnreadableError):
            telemetry_store.inspect_trace_terminal(
                self.paths,
                _trace_rows(2),
            )

        self.assertEqual(self._counts(), (1, 2, 1))

    def test_schema_version_mismatch_blocks_without_mutation(self) -> None:
        telemetry_store.append_trace(self.paths, _trace_rows(1))
        with self._connect() as connection:
            connection.execute(
                "UPDATE telemetry_metadata SET schema_version = 2"
            )
        before = self.paths.database_path.read_bytes()

        with self.assertRaises(telemetry_store.StoreIncompatibleError):
            telemetry_store.append_trace(self.paths, _trace_rows(2))

        self.assertEqual(self._counts(), (1, 2, 1))
        self.assertEqual(self.paths.database_path.read_bytes(), before)
        self.assertFalse(self.paths.database_wal_path.exists())

    def test_existing_append_validates_and_writes_on_one_connection(self) -> None:
        telemetry_store.append_trace(self.paths, _trace_rows(1))
        original_connect = telemetry_store._connect_database

        with patch.object(
            telemetry_store,
            "_connect_database",
            wraps=original_connect,
        ) as connect_database:
            result = telemetry_store.append_trace(
                self.paths,
                _trace_rows(2),
            )

        self.assertEqual(result.outcome, "committed")
        self.assertEqual(connect_database.call_count, 1)
        self.assertFalse(connect_database.call_args.kwargs["read_only"])
        self.assertEqual(self._counts(), (2, 4, 2))

    def test_counterfeit_view_digest_cannot_authorize_append(self) -> None:
        telemetry_store.append_trace(self.paths, _trace_rows(1))
        with self._connect() as connection:
            connection.execute("DROP VIEW retrieval_stage_latency_v1")
            connection.execute("DROP VIEW retrieval_runs_v1")
            connection.execute(
                """
                CREATE VIEW retrieval_runs_v1 AS
                    SELECT * FROM trace_runs WHERE false
                """
            )
            connection.execute(telemetry_store._STAGE_VIEW_DDL)
            counterfeit = telemetry_store._view_sql_digests(connection)
            connection.execute(
                """
                UPDATE telemetry_metadata
                SET runs_view_sha256 = ?, stage_view_sha256 = ?
                """,
                (
                    counterfeit["retrieval_runs_v1"],
                    counterfeit["retrieval_stage_latency_v1"],
                ),
            )

        with self.assertRaises(telemetry_store.StoreIncompatibleError):
            telemetry_store.append_trace(self.paths, _trace_rows(2))

        self.assertEqual(self._counts(), (1, 2, 1))

    def test_qualified_catalog_validation_ignores_shadow_macros(self) -> None:
        telemetry_store.append_trace(self.paths, _trace_rows(1))
        shadow_macros = (
            "CREATE MACRO current_database() "
            "AS error('shadow current_database invoked')",
            "CREATE MACRO duckdb_tables() AS TABLE "
            "SELECT error('shadow duckdb_tables invoked') AS poisoned",
            "CREATE MACRO duckdb_views() AS TABLE "
            "SELECT error('shadow duckdb_views invoked') AS poisoned",
            "CREATE MACRO duckdb_columns() AS TABLE "
            "SELECT error('shadow duckdb_columns invoked') AS poisoned",
            "CREATE MACRO pragma_table_info(name) AS TABLE "
            "SELECT error('shadow pragma_table_info invoked') AS poisoned",
        )
        with self._connect() as connection:
            for statement in shadow_macros:
                connection.execute(statement)

        result = telemetry_store.append_trace(self.paths, _trace_rows(2))

        self.assertEqual(result.outcome, "committed")
        self.assertEqual(self._counts(), (2, 4, 2))

    def test_external_file_view_is_rejected_without_binding_removed_path(
        self,
    ) -> None:
        telemetry_store.append_trace(self.paths, _trace_rows(1))
        external_path = self.root / "REMOVED_EXTERNAL_SENTINEL.parquet"
        escaped_external_path = str(external_path).replace("'", "''")
        with duckdb.connect(str(self.paths.database_path)) as connection:
            connection.execute(
                f"COPY trace_runs TO '{escaped_external_path}' (FORMAT PARQUET)"
            )
            connection.execute("DROP VIEW retrieval_stage_latency_v1")
            connection.execute("DROP VIEW retrieval_runs_v1")
            connection.execute(
                f"""
                CREATE VIEW retrieval_runs_v1 AS
                    SELECT * FROM read_parquet('{escaped_external_path}')
                """
            )
            connection.execute(telemetry_store._STAGE_VIEW_DDL)
        external_path.unlink()
        before = self.paths.database_path.read_bytes()

        with self.assertRaises(
            telemetry_store.StoreIncompatibleError
        ) as raised:
            telemetry_store.append_trace(self.paths, _trace_rows(2))

        message = str(raised.exception)
        self.assertNotIn(str(external_path), message)
        self.assertNotIn("I/O", message)
        self.assertNotIn("IO Error", message)
        self.assertEqual(self.paths.database_path.read_bytes(), before)

    def test_failed_first_transaction_never_publishes_final_database(self) -> None:
        with patch.object(
            telemetry_store,
            "_insert_trace_transaction",
            side_effect=RuntimeError("private injected detail"),
        ):
            with self.assertRaises(telemetry_store.StoreWriteError) as raised:
                telemetry_store.append_trace(self.paths, _trace_rows())

        self.assertEqual(str(raised.exception), "telemetry store operation failed")
        self.assertFalse(self.paths.database_path.exists())
        self.assertTrue(self.paths.database_init_directory.is_dir())
        self.assertEqual(
            telemetry_store.append_trace(self.paths, _trace_rows()).outcome,
            "committed",
        )

    def test_private_prepublication_scratch_is_removed_and_rebuilt(self) -> None:
        self.root.mkdir(mode=0o700)
        self.paths.database_init_directory.mkdir(mode=0o700)
        self.paths.init_database_path.write_bytes(b"incomplete")
        self.paths.init_database_path.chmod(0o600)
        self.paths.init_wal_path.write_bytes(b"incomplete wal")
        self.paths.init_wal_path.chmod(0o600)

        result = telemetry_store.append_trace(self.paths, _trace_rows())

        self.assertEqual(result.outcome, "committed")
        self.assertFalse(self.paths.database_init_directory.exists())
        self.assertEqual(self._counts(), (1, 2, 1))

    def test_unknown_scratch_entry_blocks_and_is_preserved(self) -> None:
        self.root.mkdir(mode=0o700)
        self.paths.database_init_directory.mkdir(mode=0o700)
        unknown = self.paths.database_init_directory / "unknown"
        unknown.write_bytes(b"do not delete")
        unknown.chmod(0o600)

        with self.assertRaises(telemetry_store.StoreUnsafeError):
            telemetry_store.append_trace(self.paths, _trace_rows())

        self.assertEqual(unknown.read_bytes(), b"do not delete")
        self.assertFalse(self.paths.database_path.exists())

    def test_same_inode_publication_crash_recovers_to_exact_replay(self) -> None:
        rows = _trace_rows()
        telemetry_store.append_trace(self.paths, rows)
        self.paths.database_init_directory.mkdir(mode=0o700)
        os.link(self.paths.database_path, self.paths.init_database_path)
        self.assertEqual(self.paths.database_path.stat().st_nlink, 2)

        result = telemetry_store.append_trace(self.paths, rows)

        self.assertEqual(result.outcome, "replayed")
        self.assertFalse(self.paths.database_init_directory.exists())
        self.assertEqual(self.paths.database_path.stat().st_nlink, 1)
        self.assertEqual(self._counts(), (1, 2, 1))

    def test_symlinked_and_oversized_final_wals_fail_closed(self) -> None:
        for sidecar in ("symlink", "oversized"):
            with self.subTest(sidecar=sidecar), tempfile.TemporaryDirectory() as raw:
                root = Path(raw) / "telemetry"
                paths = telemetry_paths(root)
                telemetry_store.append_trace(paths, _trace_rows(1))
                if sidecar == "symlink":
                    sentinel = Path(raw) / "sentinel"
                    sentinel.write_bytes(b"private sentinel")
                    paths.database_wal_path.symlink_to(sentinel)
                else:
                    paths.database_wal_path.touch(mode=0o600)
                    paths.database_wal_path.chmod(0o600)
                    with paths.database_wal_path.open("r+b") as stream:
                        stream.truncate(
                            telemetry_store.DATABASE_INIT_MAX_BYTES + 1
                        )

                with self.assertRaises(telemetry_store.StoreUnsafeError):
                    telemetry_store.append_trace(paths, _trace_rows(2))

                with duckdb.connect(
                    str(paths.database_path),
                    read_only=True,
                    config=_SAFE_CONFIG,
                ) as connection:
                    self.assertEqual(
                        connection.execute(
                            "SELECT count(*) FROM trace_runs"
                        ).fetchone(),
                        (1,),
                    )
                if sidecar == "symlink":
                    self.assertEqual(sentinel.read_bytes(), b"private sentinel")

    def test_real_crash_left_wal_is_rolled_back_before_append(self) -> None:
        telemetry_store.append_trace(self.paths, _trace_rows(1))
        script = """
import duckdb
import os
import sys
os.umask(0o077)
connection = duckdb.connect(sys.argv[1], config={
    'enable_external_access': 'false',
    'autoinstall_known_extensions': 'false',
    'autoload_known_extensions': 'false',
    'allow_community_extensions': 'false',
})
connection.execute('BEGIN TRANSACTION')
connection.execute(
    "UPDATE telemetry_metadata "
    "SET created_at = created_at + INTERVAL '1 microsecond'"
)
connection.execute('COMMIT')
os._exit(0)
"""

        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                script,
                str(self.paths.database_path),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(self.paths.database_wal_path.is_file())
        self.assertGreater(self.paths.database_wal_path.stat().st_size, 0)
        result = telemetry_store.append_trace(self.paths, _trace_rows(2))
        self.assertEqual(result.outcome, "committed")
        self.assertFalse(self.paths.database_wal_path.exists())
        self.assertEqual(self._counts(), (2, 4, 2))

    def test_mid_insert_failure_rolls_back_complete_trace(self) -> None:
        rows = _trace_rows()
        duplicate_rows = replace(rows, spans=(rows.spans[0], rows.spans[0]))
        with duckdb.connect(":memory:", config=_SAFE_CONFIG) as connection:
            telemetry_store._initialize_schema(connection)

            with self.assertRaises(duckdb.ConstraintException):
                telemetry_store._insert_trace_transaction(
                    connection,
                    duplicate_rows,
                    initialize=False,
                )

            self.assertEqual(
                tuple(
                    connection.execute(
                        f"SELECT count(*) FROM {table}"
                    ).fetchone()[0]
                    for table in ("trace_runs", "spans", "span_events")
                ),
                (0, 0, 0),
            )

    def test_naive_utc_timestamps_are_timezone_independent(self) -> None:
        rows = _trace_rows()
        original_connect = telemetry_store._connect_database

        def non_utc_connect(
            path: Path | str,
            *,
            read_only: bool = False,
        ) -> duckdb.DuckDBPyConnection:
            connection = original_connect(path, read_only=read_only)
            connection.execute("SET TimeZone = 'Pacific/Honolulu'")
            return connection

        with patch.object(
            telemetry_store,
            "_connect_database",
            side_effect=non_utc_connect,
        ):
            telemetry_store.append_trace(self.paths, rows)

        with self._connect(read_only=True) as connection:
            connection.execute("SET TimeZone = 'Pacific/Honolulu'")
            observed = connection.execute(
                "SELECT started_at, ended_at FROM trace_runs"
            ).fetchone()
        self.assertEqual(observed, (rows.run[2], rows.run[3]))

    def test_directory_fsync_degradation_is_returned_after_commit(self) -> None:
        with patch.object(
            telemetry_store,
            "fsync_directory",
            return_value=False,
        ):
            result = telemetry_store.append_trace(self.paths, _trace_rows())

        self.assertEqual(result.outcome, "committed")
        self.assertTrue(result.durability_degraded)
        self.assertEqual(self._counts(), (1, 2, 1))

    def test_lock_timeout_has_one_bounded_store_error(self) -> None:
        @contextmanager
        def busy_lock(*_args: object, **_kwargs: object):
            raise QueueLockTimeout("private lock detail")
            yield

        with patch.object(
            telemetry_store,
            "database_write_lock",
            side_effect=busy_lock,
        ):
            with self.assertRaises(telemetry_store.StoreBusyError) as raised:
                telemetry_store.append_trace(self.paths, _trace_rows())

        self.assertEqual(str(raised.exception), "telemetry store is busy")

    def test_external_read_only_holder_is_classified_as_busy(self) -> None:
        telemetry_store.append_trace(self.paths, _trace_rows(1))
        environment = os.environ.copy()
        environment["BUOY_TEST_DATABASE"] = str(self.paths.database_path)
        holder = subprocess.Popen(
            [
                sys.executable,
                "-c",
                (
                    "import duckdb, os, sys; "
                    "connection = duckdb.connect("
                    "os.environ['BUOY_TEST_DATABASE'], read_only=True); "
                    "print('ready', flush=True); "
                    "sys.stdin.read(1); "
                    "connection.close()"
                ),
            ],
            env=environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.addCleanup(lambda: holder.poll() is None and holder.kill())
        assert holder.stdout is not None
        self.assertEqual(holder.stdout.readline().strip(), "ready")

        with self.assertRaises(telemetry_store.StoreBusyError) as raised:
            telemetry_store.append_trace(self.paths, _trace_rows(2))

        self.assertEqual(str(raised.exception), "telemetry store is busy")
        output, errors = holder.communicate("\n", timeout=10)
        self.assertEqual(holder.returncode, 0, (output, errors))
        self.assertEqual(
            telemetry_store.append_trace(self.paths, _trace_rows(2)).outcome,
            "committed",
        )
        self.assertEqual(self._counts(), (2, 4, 2))

    def test_malformed_database_is_unreadable_not_incompatible(self) -> None:
        self.root.mkdir(mode=0o700)
        self.paths.database_path.write_bytes(b"not a DuckDB database")
        self.paths.database_path.chmod(0o600)

        with self.assertRaises(telemetry_store.StoreUnreadableError):
            telemetry_store.append_trace(self.paths, _trace_rows())

        self.assertEqual(
            self.paths.database_path.read_bytes(),
            b"not a DuckDB database",
        )

    def test_fixed_path_substitution_is_rejected_before_creation(self) -> None:
        substituted = replace(
            self.paths,
            database_path=self.root / "different.duckdb",
        )

        with self.assertRaises(telemetry_store.StoreUnsafeError):
            telemetry_store.append_trace(substituted, _trace_rows())

        self.assertFalse(self.root.exists())

    def test_database_inode_replacement_while_open_is_detected(self) -> None:
        telemetry_store.append_trace(self.paths, _trace_rows(1))
        replacement = Path(self.temporary_directory.name) / "replacement.duckdb"
        shutil.copy2(self.paths.database_path, replacement)
        replacement.chmod(0o600)
        original_connect = telemetry_store._connect_database
        replaced = False

        def replacing_connect(
            path: Path | str,
            *,
            read_only: bool = False,
        ) -> duckdb.DuckDBPyConnection:
            nonlocal replaced
            connection = original_connect(path, read_only=read_only)
            if Path(path) == self.paths.database_path and not replaced:
                os.replace(replacement, self.paths.database_path)
                replaced = True
            return connection

        with patch.object(
            telemetry_store,
            "_connect_database",
            side_effect=replacing_connect,
        ):
            with self.assertRaises(telemetry_store.StoreUnsafeError):
                telemetry_store.append_trace(self.paths, _trace_rows(2))

        self.assertTrue(replaced)
        self.assertEqual(self._counts(), (1, 2, 1))


if __name__ == "__main__":
    unittest.main()
