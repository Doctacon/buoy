from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

import duckdb

from buoy_search import telemetry_store
from buoy_search.telemetry_envelope import (
    CommandTraceRows,
    TraceEnvelopeError,
    TraceRows,
    V2_COMMAND_ROOT_SPAN_NAME,
    V2_PIPELINE_SPAN_NAME,
    decode_trace_envelope_v2,
    encode_trace_envelope_v1,
    encode_trace_envelope_v2,
)
from buoy_search.telemetry_queue import (
    WriterState,
    publish_envelope,
    scan_queue_read_only,
    telemetry_paths,
    telemetry_paths_v2,
    write_writer_state,
    writer_lifetime_lock,
)
from buoy_search.telemetry_writer import (
    run_writer,
    telemetry_flush,
    telemetry_migrate_command,
    telemetry_status,
)


_START = datetime(2026, 8, 20, 12, 0, 0)
_TRACE = "1" * 32
_ROOT = "2" * 16
_PIPELINE = "3" * 16
_SAFE_CONFIG = telemetry_store._SAFE_DUCKDB_CONFIG


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _rows(
    *,
    execution_mode: str = "live",
    outcome: str = "success",
    pipeline: bool = True,
) -> CommandTraceRows:
    error_type = None if outcome == "success" else "configuration_error"
    exit_code = 0 if outcome == "success" else 2
    command = (
        _TRACE,
        _ROOT,
        _START,
        _START + timedelta(milliseconds=10),
        10.0,
        execution_mode,
        "explicit_single",
        outcome,
        exit_code,
        error_type,
        pipeline,
        "0.6.2",
        2,
    )
    root_attributes: dict[str, object] = {
        "buoy.observation.schema_version": 2,
        "buoy.version": "0.6.2",
        "buoy.command.name": "retrieve",
        "buoy.command.execution_mode": execution_mode,
        "buoy.retrieval.mode": "explicit_single",
        "buoy.command.outcome": outcome,
        "buoy.command.exit_code": exit_code,
        "buoy.retrieval.pipeline_present": pipeline,
    }
    if error_type is not None:
        root_attributes["buoy.error.type"] = error_type
    root = (
        _TRACE,
        _ROOT,
        None,
        V2_COMMAND_ROOT_SPAN_NAME,
        _START,
        _START + timedelta(milliseconds=10),
        10.0,
        "OK" if outcome == "success" else "ERROR",
        _canonical(root_attributes),
    )
    if not pipeline:
        return CommandTraceRows(command, None, (root,), ())
    operation = (
        _TRACE,
        _PIPELINE,
        _START + timedelta(milliseconds=2),
        _START + timedelta(milliseconds=8),
        6.0,
        "success",
        1,
        1,
        1,
        1,
        0,
        False,
        False,
        None,
        "supported",
        "custom",
        "float32",
        5,
        10,
        "0.6.2",
        2,
    )
    pipeline_attributes = {
        "buoy.observation.schema_version": 2,
        "buoy.version": "0.6.2",
        "buoy.retrieval.outcome": "success",
        "buoy.retrieval.hit_count": 1,
        "buoy.retrieval.namespace_count": 1,
        "buoy.retrieval.initial_fanout": 1,
        "buoy.retrieval.final_fanout": 1,
        "buoy.retrieval.failure_count": 0,
        "buoy.retrieval.incomplete": False,
        "buoy.retrieval.widened": False,
        "buoy.evidence.status": "supported",
        "buoy.embedding.model": "custom",
        "buoy.embedding.precision": "float32",
        "buoy.retrieval.top_k": 5,
        "buoy.retrieval.candidates": 10,
    }
    pipeline_span = (
        _TRACE,
        _PIPELINE,
        _ROOT,
        V2_PIPELINE_SPAN_NAME,
        _START + timedelta(milliseconds=2),
        _START + timedelta(milliseconds=8),
        6.0,
        "OK",
        _canonical(pipeline_attributes),
    )
    return CommandTraceRows(command, operation, (root, pipeline_span), ())


def _create_v1_store(path: Path) -> None:
    path.parent.mkdir(mode=0o700)
    with duckdb.connect(str(path), config=_SAFE_CONFIG) as connection:
        telemetry_store._initialize_schema_v1(connection)
    path.chmod(0o600)


def _v1_rows() -> TraceRows:
    attributes = {
        "buoy.observation.schema_version": 1,
        "buoy.version": "0.6.2",
        "buoy.retrieval.mode": "explicit_single",
        "buoy.retrieval.outcome": "success",
        "buoy.retrieval.hit_count": 1,
        "buoy.retrieval.namespace_count": 1,
        "buoy.retrieval.initial_fanout": 1,
        "buoy.retrieval.final_fanout": 1,
        "buoy.retrieval.failure_count": 0,
        "buoy.retrieval.incomplete": False,
        "buoy.retrieval.widened": False,
        "buoy.embedding.model": "custom",
        "buoy.embedding.precision": "float32",
        "buoy.retrieval.top_k": 5,
        "buoy.retrieval.candidates": 10,
    }
    run = (
        "a" * 32,
        "b" * 16,
        _START,
        _START + timedelta(milliseconds=5),
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
        "float32",
        5,
        10,
        "0.6.2",
        1,
    )
    root = (
        run[0],
        run[1],
        None,
        "buoy.retrieve",
        run[2],
        run[3],
        run[4],
        "OK",
        _canonical(attributes),
    )
    return TraceRows(run, (root,), ())


class Version2EnvelopeTests(unittest.TestCase):
    def test_live_preview_and_pre_pipeline_error_round_trip_canonically(self) -> None:
        fixtures = (
            _rows(),
            _rows(execution_mode="preview", pipeline=False),
            _rows(outcome="error", pipeline=False),
        )
        for rows in fixtures:
            with self.subTest(command=rows.command[5:8]):
                payload = encode_trace_envelope_v2(rows)
                self.assertEqual(decode_trace_envelope_v2(payload), rows)
                self.assertEqual(
                    payload,
                    json.dumps(
                        json.loads(payload),
                        ensure_ascii=True,
                        allow_nan=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode(),
                )

    def test_shape_value_graph_and_privacy_forgery_are_rejected(self) -> None:
        original = json.loads(encode_trace_envelope_v2(_rows()))
        mutations = []
        unknown = deepcopy(original)
        unknown["query"] = "PRIVATE_QUERY_SENTINEL"
        mutations.append((unknown, "invalid_shape"))
        wrong_version = deepcopy(original)
        wrong_version["envelope_schema_version"] = 1
        mutations.append((wrong_version, "unsupported_envelope_version"))
        mismatch = deepcopy(original)
        mismatch["retrieval_operation"]["pipeline_duration_ms"] = 5.0
        mutations.append((mismatch, "invalid_graph"))
        hostile_attribute = deepcopy(original)
        hostile_attribute["spans"][0]["attributes"]["process.command_args"] = (
            "PRIVATE_ARGV_SENTINEL"
        )
        mutations.append((hostile_attribute, "invalid_shape"))
        for value, reason in mutations:
            with self.subTest(reason=reason):
                payload = json.dumps(
                    value, sort_keys=True, separators=(",", ":")
                ).encode()
                with self.assertRaises(TraceEnvelopeError) as raised:
                    decode_trace_envelope_v2(payload)
                self.assertEqual(raised.exception.reason, reason)
                self.assertNotIn("PRIVATE", str(raised.exception))


class Version2QueueStoreMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "telemetry"
        self.v1 = telemetry_paths(self.root)
        self.v2 = telemetry_paths_v2(self.root)

    def test_exact_byte_privacy_sentinel_never_reaches_terminal_artifacts(self) -> None:
        sentinel = b"PRIVATE_QUERY_PATH_CREDENTIAL_SENTINEL"
        forged = json.loads(encode_trace_envelope_v2(_rows()))
        forged["spans"][0]["attributes"]["query.text"] = sentinel.decode()
        payload = json.dumps(
            forged, sort_keys=True, separators=(",", ":")
        ).encode()
        self.assertIn(sentinel, payload)
        self.assertTrue(publish_envelope(payload, paths=self.v2).published)
        with patch("buoy_search.telemetry_writer.IDLE_EXIT_SECONDS", 0):
            self.assertEqual(run_writer(self.v1), 0)
        status_output = json.dumps(
            telemetry_status(paths=self.v1, environment={}), sort_keys=True
        ).encode()
        migrate_output = telemetry_migrate_command(
            json_output=True, paths=self.v1
        ).output.encode()
        self.assertNotIn(sentinel, status_output)
        self.assertNotIn(sentinel, migrate_output)
        for path in self.root.rglob("*"):
            if path.is_file():
                self.assertNotIn(sentinel, path.read_bytes(), path)

    def test_separate_queue_and_exact_v2_views_persist_all_fixture_modes(self) -> None:
        payload = encode_trace_envelope_v2(_rows())
        published = publish_envelope(payload, paths=self.v2)
        self.assertTrue(published.published)
        self.assertTrue(published.source_name.startswith("v2-"))
        self.assertFalse(self.v1.inbox_directory.exists())
        self.assertEqual(scan_queue_read_only(self.v2).ready, 1)

        fixtures = (
            _rows(),
            _replace_trace(_rows(execution_mode="preview", pipeline=False), "4"),
            _replace_trace(_rows(outcome="error", pipeline=False), "5"),
        )
        for rows in fixtures:
            self.assertEqual(
                telemetry_store.append_trace(self.v2, rows).outcome,
                "committed",
            )
        with duckdb.connect(
            str(self.v2.database_path), read_only=True, config=_SAFE_CONFIG
        ) as connection:
            self.assertEqual(telemetry_store._validate_schema(connection), 2)
            self.assertEqual(
                tuple(row[0] for row in connection.execute(
                    "SELECT pipeline_duration_ms FROM retrieval_command_runs_v2 "
                    "ORDER BY trace_id"
                ).fetchall()),
                (6.0, None, None),
            )
            self.assertEqual(
                connection.execute(
                    "SELECT count(*) FROM retrieval_stage_latency_v2"
                ).fetchone(),
                (1,),
            )
            self.assertEqual(
                connection.execute(
                    "SELECT count(*) FROM retrieval_runs_v1"
                ).fetchone(),
                (0,),
            )
        with duckdb.connect(
            str(self.v2.database_path), config=_SAFE_CONFIG
        ) as connection:
            connection.execute("CREATE MACRO hostile_v2() AS 1")
        with self.assertRaises(telemetry_store.StoreIncompatibleError):
            telemetry_store.append_trace(
                self.v2,
                _replace_trace(_rows(), "6"),
            )

    def test_status_and_flush_leave_v2_pending_behind_exact_v1(self) -> None:
        _create_v1_store(self.v1.database_path)
        observed = self.v1.database_path.stat()
        write_writer_state(
            WriterState(
                phase="stopped",
                store_state="compatible",
                store_schema_version=1,
                persisted_runs_snapshot=0,
                database_device=observed.st_dev,
                database_inode=observed.st_ino,
                database_bytes=observed.st_size,
            ),
            paths=self.v1,
        )
        status = telemetry_status(paths=self.v1, environment={})
        self.assertEqual(status["store"]["state"], "upgrade_required")
        self.assertEqual(status["overall"], "degraded")
        publish_envelope(encode_trace_envelope_v2(_rows()), paths=self.v2)
        before = self.v2.ready_directory.iterdir()
        before_names = sorted(path.name for path in before)
        status = telemetry_status(paths=self.v1, environment={})
        self.assertEqual(status["overall"], "blocked")
        self.assertEqual(status["queue"]["v2_ready"], 1)
        result = telemetry_flush(timeout=0, paths=self.v1)
        self.assertEqual(result["outcome"], "blocked")
        self.assertEqual(
            sorted(path.name for path in self.v2.ready_directory.iterdir()),
            before_names,
        )

    def test_dual_writer_drains_v1_and_leaves_v2_recoverable_until_upgrade(self) -> None:
        _create_v1_store(self.v1.database_path)
        publish_envelope(encode_trace_envelope_v1(_v1_rows()), paths=self.v1)
        publish_envelope(encode_trace_envelope_v2(_rows()), paths=self.v2)
        with patch("buoy_search.telemetry_writer.IDLE_EXIT_SECONDS", 0):
            self.assertEqual(run_writer(self.v1), 0)
        self.assertEqual(scan_queue_read_only(self.v1).ready, 0)
        self.assertEqual(scan_queue_read_only(self.v2).ready, 1)
        self.assertEqual(scan_queue_read_only(self.v2).claimed, 0)
        with duckdb.connect(
            str(self.v1.database_path), read_only=True, config=_SAFE_CONFIG
        ) as connection:
            self.assertEqual(telemetry_store._validate_schema(connection), 1)
            self.assertEqual(
                connection.execute("SELECT count(*) FROM trace_runs").fetchone(),
                (1,),
            )

    def test_migration_drains_v1_snapshot_into_backup_and_v2_store(self) -> None:
        _create_v1_store(self.v1.database_path)
        publish_envelope(encode_trace_envelope_v1(_v1_rows()), paths=self.v1)
        result = telemetry_migrate_command(json_output=True, paths=self.v1)
        self.assertEqual(result.exit_code, 0)
        value = json.loads(result.output)
        self.assertEqual(value["outcome"], "migrated")
        self.assertEqual(value["migrated_v1_runs"], 1)
        for database in (
            self.v1.database_path,
            self.v1.backup_database_path,
        ):
            with duckdb.connect(
                str(database), read_only=True, config=_SAFE_CONFIG
            ) as connection:
                self.assertEqual(
                    connection.execute(
                        "SELECT count(*) FROM retrieval_runs_v1"
                    ).fetchone(),
                    (1,),
                )

    def test_status_flush_producer_writer_and_migrate_are_network_inert(self) -> None:
        payload = encode_trace_envelope_v2(_rows())
        forbidden_modules = {
            "buoy_search.cli": None,
            "buoy_search.retriever": None,
            "buoy_search.routing": None,
        }
        with (
            patch.object(
                socket, "socket", side_effect=AssertionError("network")
            ),
            patch.object(
                socket, "getaddrinfo", side_effect=AssertionError("dns")
            ),
            patch.dict("sys.modules", forbidden_modules),
            patch(
                "buoy_search.telemetry_writer.request_writer_start",
                return_value=None,
            ),
        ):
            self.assertTrue(publish_envelope(payload, paths=self.v2).published)
            telemetry_status(paths=self.v1, environment={})
            self.assertEqual(
                telemetry_flush(timeout=0, paths=self.v1)["outcome"],
                "timeout",
            )
            with patch("buoy_search.telemetry_writer.IDLE_EXIT_SECONDS", 0):
                self.assertEqual(run_writer(self.v1), 0)
            self.assertEqual(
                json.loads(
                    telemetry_migrate_command(
                        json_output=True, paths=self.v1
                    ).output
                )["outcome"],
                "already_current",
            )

    def test_migrate_absent_busy_and_mismatching_backup_outcomes(self) -> None:
        absent = telemetry_migrate_command(json_output=True, paths=self.v1)
        self.assertEqual(absent.exit_code, 0)
        self.assertEqual(json.loads(absent.output)["outcome"], "absent")
        self.assertFalse(self.root.exists())

        _create_v1_store(self.v1.database_path)
        with writer_lifetime_lock(self.v1, timeout_ms=0):
            busy = telemetry_migrate_command(json_output=True, paths=self.v1)
        self.assertEqual(busy.exit_code, 1)
        self.assertEqual(json.loads(busy.output)["outcome"], "busy")

        self.v1.backup_database_path.write_bytes(b"different history")
        self.v1.backup_database_path.chmod(0o600)
        before = self.v1.database_path.read_bytes()
        blocked = telemetry_migrate_command(json_output=True, paths=self.v1)
        self.assertEqual(blocked.exit_code, 2)
        self.assertEqual(json.loads(blocked.output)["outcome"], "blocked")
        self.assertEqual(self.v1.database_path.read_bytes(), before)
        self.assertEqual(
            self.v1.backup_database_path.read_bytes(), b"different history"
        )

    def test_migrate_is_backed_up_atomic_idempotent_and_network_inert(self) -> None:
        _create_v1_store(self.v1.database_path)
        sentinel = b"PRIVATE_MIGRATION_OUTPUT_SENTINEL"
        with patch.object(socket, "socket", side_effect=AssertionError("network")), patch.object(
            socket, "getaddrinfo", side_effect=AssertionError("dns")
        ):
            result = telemetry_migrate_command(json_output=True, paths=self.v1)
        self.assertEqual(result.exit_code, 0)
        value = json.loads(result.output)
        self.assertEqual(value["outcome"], "migrated")
        self.assertNotIn(sentinel, result.output.encode())
        self.assertEqual(
            telemetry_store.inspect_store_schema_version(self.v1), 2
        )
        with duckdb.connect(
            str(self.v1.backup_database_path),
            read_only=True,
            config=_SAFE_CONFIG,
        ) as backup_connection:
            self.assertEqual(
                telemetry_store._validate_schema(backup_connection), 1
            )
        backup = self.v1.backup_database_path.read_bytes()
        again = telemetry_migrate_command(json_output=True, paths=self.v1)
        self.assertEqual(json.loads(again.output)["outcome"], "already_current")
        self.assertEqual(self.v1.backup_database_path.read_bytes(), backup)

    def test_every_migration_fault_keeps_one_provable_canonical_version(self) -> None:
        phases = (
            "validated_source",
            "scratch_created",
            "scratch_copied",
            "transaction_committed",
            "scratch_validated",
            "backup_created",
            "backup_fsynced",
            "canonical_published",
            "directory_fsynced",
            "state_publication_ready",
        )
        for phase in phases:
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as raw:
                paths = telemetry_paths(Path(raw) / "telemetry")
                _create_v1_store(paths.database_path)

                def fail(
                    observed: str,
                    selected_phase: str = phase,
                ) -> None:
                    if observed == selected_phase:
                        raise RuntimeError("PRIVATE_FAULT_SENTINEL")

                with self.assertRaises(RuntimeError):
                    telemetry_store.migrate_store_v1_to_v2(
                        paths, fault_hook=fail
                    )
                version = telemetry_store.inspect_store_schema_version(paths)
                expected = 2 if phase in {
                    "canonical_published",
                    "directory_fsynced",
                    "state_publication_ready",
                } else 1
                self.assertEqual(version, expected)
                self.assertFalse(paths.database_wal_path.exists())
                if phase == "backup_created":
                    retried = telemetry_store.migrate_store_v1_to_v2(paths)
                    self.assertTrue(retried.backup_present)
                    self.assertEqual(
                        telemetry_store.inspect_store_schema_version(paths), 2
                    )


def _replace_trace(rows: CommandTraceRows, digit: str) -> CommandTraceRows:
    trace = digit * 32
    root = digit * 15 + "1"
    pipeline = digit * 15 + "2"
    command = list(rows.command)
    command[0] = trace
    command[1] = root
    operation = None
    if rows.retrieval_operation is not None:
        changed_operation = list(rows.retrieval_operation)
        changed_operation[0] = trace
        changed_operation[1] = pipeline
        operation = tuple(changed_operation)
    spans = []
    for index, span in enumerate(rows.spans):
        changed = list(span)
        changed[0] = trace
        changed[1] = root if index == 0 else pipeline
        changed[2] = None if index == 0 else root
        spans.append(tuple(changed))
    return CommandTraceRows(tuple(command), operation, tuple(spans), rows.events)


if __name__ == "__main__":
    unittest.main()
