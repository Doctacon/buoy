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

from buoy_search import telemetry_store, telemetry_writer
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
    QueueSnapshot,
    WriterState,
    publish_envelope,
    read_terminal_receipt,
    read_writer_state,
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
        "buoy.retrieval.mode": "explicit_single",
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
    path.parent.mkdir(mode=0o700, exist_ok=True)
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


def _replace_v1_trace(rows: TraceRows, number: int) -> TraceRows:
    trace_id = f"{number:032x}"
    root_span_id = f"{(number % (2**64 - 1)) + 1:016x}"
    run = list(rows.run)
    run[0] = trace_id
    run[1] = root_span_id
    spans = []
    for span in rows.spans:
        changed = list(span)
        changed[0] = trace_id
        changed[1] = root_span_id
        changed[2] = None
        spans.append(tuple(changed))
    return TraceRows(tuple(run), tuple(spans), rows.events)


def _insert_v1_rows(path: Path, rows: tuple[TraceRows, ...]) -> None:
    with duckdb.connect(str(path), config=_SAFE_CONFIG) as connection:
        for trace in rows:
            telemetry_store._insert_trace_rows(connection, trace)


def _widened_v2_object() -> dict[str, object]:
    value = json.loads(encode_trace_envelope_v2(_rows()))
    operation = value["retrieval_operation"]
    assert isinstance(operation, dict)
    operation.update(
        {
            "namespace_count": 2,
            "final_fanout": 2,
            "widened": True,
            "fallback_reason": "weak_top1",
        }
    )
    pipeline = value["spans"][1]
    pipeline["attributes"].update(
        {
            "buoy.retrieval.namespace_count": 2,
            "buoy.retrieval.final_fanout": 2,
            "buoy.retrieval.widened": True,
            "buoy.retrieval.fallback_reason": "weak_top1",
        }
    )
    value["events"] = [
        {
            "trace_id": value["command"]["trace_id"],
            "span_id": pipeline["span_id"],
            "event_index": 0,
            "name": "retrieval.widened",
            "occurred_at_unix_us": pipeline["started_at_unix_us"] + 1_000,
            "attributes": {
                "buoy.retrieval.initial_fanout": 1,
                "buoy.retrieval.final_fanout": 2,
                "buoy.retrieval.fallback_reason": "weak_top1",
            },
        }
    ]
    return value


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

    def test_comprehensive_shape_value_graph_privacy_matrix_is_rejected(self) -> None:
        original = json.loads(encode_trace_envelope_v2(_rows()))
        cases: list[tuple[str, dict[str, object], str]] = []

        def changed(name: str) -> dict[str, object]:
            value = deepcopy(original)
            cases.append((name, value, "invalid_graph"))
            return value

        unknown = deepcopy(original)
        unknown["query"] = "PRIVATE_QUERY_SENTINEL"
        cases.append(("unknown top key", unknown, "invalid_shape"))
        wrong_version = deepcopy(original)
        wrong_version["envelope_schema_version"] = 1
        cases.append(
            ("wrong version", wrong_version, "unsupported_envelope_version")
        )
        hostile = deepcopy(original)
        hostile["spans"][0]["attributes"]["process.command_args"] = (
            "PRIVATE_ARGV_SENTINEL"
        )
        cases.append(("prohibited root value", hostile, "invalid_shape"))

        changed("summary duration")["retrieval_operation"][
            "pipeline_duration_ms"
        ] = 5.0
        changed("root id mismatch")["command"]["root_span_id"] = "4" * 16
        duplicate = changed("duplicate span id")
        duplicate["spans"][1]["span_id"] = duplicate["spans"][0]["span_id"]
        changed("missing parent")["spans"][1]["parent_span_id"] = "5" * 16
        cycle = changed("cycle")
        cycle["spans"][1]["parent_span_id"] = cycle["spans"][1]["span_id"]
        changed("span ordering")["spans"].reverse()
        changed("child outside root")["spans"][1]["ended_at_unix_us"] = (
            original["command"]["ended_at_unix_us"] + 1
        )
        changed("summary mismatch")["retrieval_operation"]["hit_count"] = 0
        changed("root status mismatch")["spans"][0]["status_code"] = "ERROR"
        changed("pipeline status mismatch")["spans"][1]["status_code"] = "ERROR"
        changed("pipeline mode mismatch")["spans"][1]["attributes"][
            "buoy.retrieval.mode"
        ] = "automatic"
        no_pipeline = changed("live success without pipeline")
        no_pipeline["command"]["pipeline_present"] = False
        no_pipeline["spans"][0]["attributes"][
            "buoy.retrieval.pipeline_present"
        ] = False
        no_pipeline["retrieval_operation"] = None
        no_pipeline["spans"] = no_pipeline["spans"][:1]
        pipeline_error = changed("pipeline error without category")
        pipeline_error["retrieval_operation"]["outcome"] = "error"
        pipeline_error["spans"][1]["attributes"][
            "buoy.retrieval.outcome"
        ] = "error"
        pipeline_error["spans"][1]["status_code"] = "ERROR"

        widened_null = _widened_v2_object()
        widened_null["retrieval_operation"]["fallback_reason"] = None
        widened_null["spans"][1]["attributes"].pop(
            "buoy.retrieval.fallback_reason"
        )
        cases.append(("widened null fallback", widened_null, "invalid_graph"))
        wrong_owner = _widened_v2_object()
        wrong_owner["events"][0]["span_id"] = wrong_owner["command"][
            "root_span_id"
        ]
        cases.append(("event wrong owner", wrong_owner, "invalid_graph"))
        outside_pipeline = _widened_v2_object()
        outside_pipeline["events"][0]["occurred_at_unix_us"] = (
            outside_pipeline["command"]["started_at_unix_us"] + 1
        )
        cases.append(("event outside pipeline", outside_pipeline, "invalid_graph"))

        for name, value, reason in cases:
            with self.subTest(name=name):
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
        with patch.object(telemetry_writer, "DRAIN_DEADLINE_SECONDS", 0):
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
        state = self.v1.writer_state_path.read_bytes()
        again = telemetry_migrate_command(json_output=True, paths=self.v1)
        self.assertEqual(json.loads(again.output)["outcome"], "already_current")
        self.assertEqual(self.v1.backup_database_path.read_bytes(), backup)
        self.assertEqual(self.v1.writer_state_path.read_bytes(), state)

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


class ReviewRepairTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "telemetry"
        self.v1 = telemetry_paths(self.root)
        self.v2 = telemetry_paths_v2(self.root)

    def _write_v1_state(self) -> None:
        observed = self.v1.database_path.stat()
        write_writer_state(
            WriterState(
                phase="stopped",
                store_state="compatible",
                store_schema_version=1,
                persisted_runs_snapshot=1,
                database_device=observed.st_dev,
                database_inode=observed.st_ino,
                database_bytes=observed.st_size,
            ),
            paths=self.v1,
        )

    def test_mid_backup_copy_crash_never_publishes_partial_and_retry_succeeds(self) -> None:
        _create_v1_store(self.v1.database_path)
        _insert_v1_rows(self.v1.database_path, (_v1_rows(),))

        class InjectedCrash(BaseException):
            pass

        def crash(phase: str) -> None:
            if phase == "backup_copy_midpoint":
                raise InjectedCrash

        with self.assertRaises(InjectedCrash):
            telemetry_store.migrate_store_v1_to_v2(
                self.v1, fault_hook=crash
            )
        self.assertFalse(self.v1.backup_database_path.exists())
        self.assertTrue(self.v1.migration_backup_candidate_path.exists())
        self.assertEqual(
            telemetry_store.inspect_store_schema_version(self.v1), 1
        )

        queued = _replace_v1_trace(_v1_rows(), 2)
        publish_envelope(encode_trace_envelope_v1(queued), paths=self.v1)
        repaired = telemetry_migrate_command(json_output=True, paths=self.v1)
        self.assertEqual(repaired.exit_code, 0)
        repaired_facts = json.loads(repaired.output)
        self.assertEqual(repaired_facts["outcome"], "migrated")
        self.assertEqual(repaired_facts["migrated_v1_runs"], 2)
        self.assertFalse(self.v1.migration_directory.exists())
        self.assertEqual(
            telemetry_store.inspect_store_schema_version(self.v1), 2
        )

    def test_backup_link_publication_crash_is_recognized_and_retry_safe(self) -> None:
        _create_v1_store(self.v1.database_path)

        class InjectedCrash(BaseException):
            pass

        original_unlink = telemetry_store.safe_unlink_at

        def crash_candidate_unlink(
            parent_fd: int,
            name: str,
            **kwargs: object,
        ) -> None:
            if name == telemetry_store.DATABASE_BACKUP_BASENAME:
                raise InjectedCrash
            original_unlink(parent_fd, name, **kwargs)

        with patch.object(
            telemetry_store,
            "safe_unlink_at",
            side_effect=crash_candidate_unlink,
        ), self.assertRaises(InjectedCrash):
            telemetry_store.migrate_store_v1_to_v2(self.v1)
        candidate = self.v1.migration_backup_candidate_path.stat()
        final = self.v1.backup_database_path.stat()
        self.assertEqual((candidate.st_dev, candidate.st_ino), (final.st_dev, final.st_ino))
        self.assertEqual(candidate.st_nlink, 2)
        repaired = telemetry_migrate_command(json_output=True, paths=self.v1)
        self.assertEqual(repaired.exit_code, 0)
        self.assertEqual(json.loads(repaired.output)["outcome"], "migrated")
        self.assertEqual(self.v1.backup_database_path.stat().st_nlink, 1)

    def test_post_publication_retry_recovers_scratch_state_append_and_flush(self) -> None:
        _create_v1_store(self.v1.database_path)

        def crash(phase: str) -> None:
            if phase == "canonical_published":
                raise RuntimeError("PRIVATE_POST_PUBLICATION_SENTINEL")

        with self.assertRaises(RuntimeError):
            telemetry_store.migrate_store_v1_to_v2(
                self.v1, fault_hook=crash
            )
        self.assertTrue(self.v1.migration_directory.is_dir())
        self.assertEqual(
            telemetry_status(paths=self.v1, environment={})["store"]["state"],
            "present_unverified",
        )
        with self.assertRaises(telemetry_store.StoreUnsafeError):
            telemetry_store.append_trace(self.v2, _rows())

        retried = telemetry_migrate_command(json_output=True, paths=self.v1)
        self.assertEqual(retried.exit_code, 0)
        self.assertEqual(json.loads(retried.output)["outcome"], "already_current")
        self.assertFalse(self.v1.migration_directory.exists())
        self.assertEqual(
            telemetry_store.append_trace(self.v2, _rows()).outcome,
            "committed",
        )
        later = _replace_trace(_rows(), "7")
        publish_envelope(encode_trace_envelope_v2(later), paths=self.v2)

        def start_writer(**_kwargs: object) -> None:
            with patch.object(telemetry_writer, "IDLE_EXIT_SECONDS", 0):
                run_writer(self.v1)

        with patch.object(
            telemetry_writer, "request_writer_start", side_effect=start_writer
        ):
            flushed = telemetry_flush(timeout=5, paths=self.v1)
        self.assertEqual(flushed["outcome"], "flushed")

    def test_semantically_hostile_v1_store_blocks_before_backup_or_mutation(self) -> None:
        sentinel = "PRIVATE_RAW_ERROR_CONTENT_SENTINEL"
        _create_v1_store(self.v1.database_path)
        _insert_v1_rows(self.v1.database_path, (_v1_rows(),))
        with duckdb.connect(
            str(self.v1.database_path), config=_SAFE_CONFIG
        ) as connection:
            connection.execute(
                "UPDATE spans SET attributes = ?",
                (_canonical({"content": sentinel}),),
            )
        before = self.v1.database_path.read_bytes()
        result = telemetry_migrate_command(json_output=True, paths=self.v1)
        self.assertEqual(result.exit_code, 2)
        self.assertEqual(json.loads(result.output)["outcome"], "blocked")
        self.assertNotIn(sentinel, result.output)
        self.assertEqual(self.v1.database_path.read_bytes(), before)
        self.assertFalse(self.v1.backup_database_path.exists())
        self.assertFalse(self.v1.migration_directory.exists())

    def test_streaming_validation_crosses_one_hundred_twenty_eight_traces(self) -> None:
        self.assertEqual(telemetry_store.MIGRATION_BATCH_SIZE, 128)
        _create_v1_store(self.v1.database_path)
        traces = tuple(
            _replace_v1_trace(_v1_rows(), number)
            for number in range(1, 130)
        )
        _insert_v1_rows(self.v1.database_path, traces)
        migrated = telemetry_store.migrate_store_v1_to_v2(self.v1)
        self.assertEqual(migrated.runs, 129)
        self.assertEqual(migrated.spans, 129)

    def test_unknown_user_schema_blocks_append_and_migration(self) -> None:
        telemetry_store.append_trace(self.v2, _rows())
        with duckdb.connect(
            str(self.v2.database_path), config=_SAFE_CONFIG
        ) as connection:
            connection.execute("CREATE SCHEMA hidden")
            connection.execute("CREATE TABLE hidden.secret(value INTEGER)")
        with self.assertRaises(telemetry_store.StoreIncompatibleError):
            telemetry_store.append_trace(
                self.v2, _replace_trace(_rows(), "8")
            )

        with tempfile.TemporaryDirectory() as raw:
            paths = telemetry_paths(Path(raw) / "telemetry")
            _create_v1_store(paths.database_path)
            with duckdb.connect(
                str(paths.database_path), config=_SAFE_CONFIG
            ) as connection:
                connection.execute("CREATE SCHEMA hidden")
                connection.execute("CREATE TABLE hidden.secret(value INTEGER)")
            result = telemetry_migrate_command(json_output=True, paths=paths)
            self.assertEqual(result.exit_code, 2)
            self.assertFalse(paths.backup_database_path.exists())

    def test_same_and_cross_version_replay_conflict_are_global_and_atomic(self) -> None:
        v1 = _v1_rows()
        self.assertEqual(telemetry_store.append_trace(self.v1, v1).outcome, "committed")
        self.assertEqual(telemetry_store.append_trace(self.v1, v1).outcome, "replayed")
        changed_run = list(v1.run)
        changed_run[7] = 2
        changed_root = list(v1.spans[0])
        changed_attributes = json.loads(changed_root[8])
        changed_attributes["buoy.retrieval.hit_count"] = 2
        changed_root[8] = _canonical(changed_attributes)
        v1_conflict = TraceRows(
            tuple(changed_run), (tuple(changed_root),), v1.events
        )
        encode_trace_envelope_v1(v1_conflict)
        self.assertEqual(
            telemetry_store.append_trace(
                self.v1,
                v1_conflict,
            ).outcome,
            "conflict",
        )
        v2 = _rows()
        self.assertEqual(telemetry_store.append_trace(self.v2, v2).outcome, "committed")
        self.assertEqual(telemetry_store.append_trace(self.v2, v2).outcome, "replayed")
        changed_command = list(v2.command)
        changed_command[6] = "automatic"
        changed_root = list(v2.spans[0])
        root_attributes = json.loads(changed_root[8])
        root_attributes["buoy.retrieval.mode"] = "automatic"
        changed_root[8] = _canonical(root_attributes)
        changed_pipeline = list(v2.spans[1])
        pipeline_attributes = json.loads(changed_pipeline[8])
        pipeline_attributes["buoy.retrieval.mode"] = "automatic"
        changed_pipeline[8] = _canonical(pipeline_attributes)
        v2_conflict = CommandTraceRows(
            tuple(changed_command),
            v2.retrieval_operation,
            (tuple(changed_root), tuple(changed_pipeline)),
            v2.events,
        )
        encode_trace_envelope_v2(v2_conflict)
        self.assertEqual(
            telemetry_store.append_trace(self.v2, v2_conflict).outcome,
            "conflict",
        )
        cross_v2 = _replace_trace(_rows(), "a")
        encode_trace_envelope_v2(cross_v2)
        self.assertEqual(
            telemetry_store.append_trace(self.v2, cross_v2).outcome,
            "conflict",
        )

        with tempfile.TemporaryDirectory() as raw:
            paths = telemetry_paths(Path(raw) / "telemetry")
            telemetry_store.append_trace(paths, _rows())
            cross_v1 = _replace_v1_trace(_v1_rows(), int("1" * 32, 16))
            encode_trace_envelope_v1(cross_v1)
            self.assertEqual(
                telemetry_store.append_trace(paths, cross_v1).outcome,
                "conflict",
            )

    def test_writer_receipts_classify_replay_and_cross_version_conflict(self) -> None:
        v1 = _v1_rows()
        telemetry_store.append_trace(self.v1, v1)
        replay = publish_envelope(encode_trace_envelope_v1(v1), paths=self.v1)
        cross = _replace_trace(_rows(), "a")
        conflict = publish_envelope(
            encode_trace_envelope_v2(cross), paths=self.v2
        )
        with patch.object(telemetry_writer, "IDLE_EXIT_SECONDS", 0):
            run_writer(self.v1)
        replay_receipt = read_terminal_receipt(
            str(replay.source_name), paths=self.v1
        )
        conflict_receipt = read_terminal_receipt(
            str(conflict.source_name), paths=self.v2
        )
        self.assertEqual(replay_receipt.kind, "replayed")
        self.assertEqual(conflict_receipt.kind, "conflict")
        self.assertEqual(conflict_receipt.reason, "trace_conflict")

    def test_v1_flush_snapshot_ignores_later_blocking_v2_publication(self) -> None:
        _create_v1_store(self.v1.database_path)
        self._write_v1_state()
        publish_envelope(encode_trace_envelope_v1(_v1_rows()), paths=self.v1)

        def start_writer(**_kwargs: object) -> None:
            publish_envelope(encode_trace_envelope_v2(_rows()), paths=self.v2)
            with patch.object(telemetry_writer, "IDLE_EXIT_SECONDS", 0):
                run_writer(self.v1)

        with patch.object(
            telemetry_writer, "request_writer_start", side_effect=start_writer
        ):
            result = telemetry_flush(timeout=5, paths=self.v1)
        self.assertEqual(result["outcome"], "flushed")
        self.assertEqual(scan_queue_read_only(self.v2).ready, 1)

    def test_migration_preflight_blocks_hostile_inboxes_before_duckdb(self) -> None:
        for queue_version in (1, 2):
            with self.subTest(queue_version=queue_version), tempfile.TemporaryDirectory() as raw:
                paths = telemetry_paths(Path(raw) / "telemetry")
                _create_v1_store(paths.database_path)
                queue_paths = telemetry_paths(
                    paths.directory, queue_version=queue_version
                )
                queue_paths.ready_directory.mkdir(parents=True, mode=0o700)
                for child in ("tmp", "claimed", "receipts"):
                    (queue_paths.inbox_directory / child).mkdir(mode=0o700)
                hostile = queue_paths.ready_directory / "PRIVATE_UNKNOWN"
                hostile.write_bytes(b"PRIVATE_RAW_ERROR")
                hostile.chmod(0o600)
                with patch.object(
                    telemetry_store,
                    "_connect_database",
                    side_effect=AssertionError("DuckDB opened before preflight"),
                ):
                    result = telemetry_migrate_command(
                        json_output=True, paths=paths
                    )
                self.assertEqual(result.exit_code, 2)

    def test_backup_and_scratch_preflight_block_before_duckdb(self) -> None:
        for hostile_kind in ("backup_symlink", "scratch_unknown"):
            with self.subTest(hostile_kind=hostile_kind), tempfile.TemporaryDirectory() as raw:
                paths = telemetry_paths(Path(raw) / "telemetry")
                _create_v1_store(paths.database_path)
                if hostile_kind == "backup_symlink":
                    target = Path(raw) / "PRIVATE_TARGET"
                    target.write_bytes(b"PRIVATE")
                    paths.backup_database_path.symlink_to(target)
                else:
                    paths.migration_directory.mkdir(mode=0o700)
                    unknown = paths.migration_directory / "PRIVATE_UNKNOWN"
                    unknown.write_bytes(b"PRIVATE")
                    unknown.chmod(0o600)
                with patch.object(
                    telemetry_store,
                    "_connect_database",
                    side_effect=AssertionError("DuckDB opened before preflight"),
                ):
                    result = telemetry_migrate_command(
                        json_output=True, paths=paths
                    )
                self.assertEqual(result.exit_code, 2)

    def test_final_state_failure_is_exact_blocked_and_retry_reconciles(self) -> None:
        _create_v1_store(self.v1.database_path)
        original = telemetry_writer.write_writer_state

        def fail_final(state: WriterState, *, paths: object) -> bool:
            if state.store_schema_version == 2:
                raise OSError("PRIVATE_STATE_FAILURE_SENTINEL")
            return original(state, paths=paths)

        with patch.object(
            telemetry_writer, "write_writer_state", side_effect=fail_final
        ):
            result = telemetry_migrate_command(json_output=True, paths=self.v1)
        value = json.loads(result.output)
        self.assertEqual(result.exit_code, 2)
        self.assertEqual(value["outcome"], "blocked")
        self.assertEqual(value["target_schema_version"], 2)
        self.assertEqual(value["migrated_v1_runs"], 0)
        self.assertTrue(value["backup_present"])
        self.assertNotIn("PRIVATE_STATE_FAILURE_SENTINEL", result.output)
        self.assertEqual(
            telemetry_store.inspect_store_schema_version(self.v1), 2
        )
        retried = telemetry_migrate_command(json_output=True, paths=self.v1)
        self.assertEqual(retried.exit_code, 0)
        self.assertEqual(json.loads(retried.output)["outcome"], "already_current")
        self.assertEqual(read_writer_state(self.v1).store_schema_version, 2)

    def test_append_allows_exact_backup_and_rejects_hostile_backup_or_scratch(self) -> None:
        telemetry_store.append_trace(self.v2, _rows())
        with tempfile.TemporaryDirectory() as raw:
            backup_source = Path(raw) / "backup.duckdb"
            _create_v1_store(backup_source)
            self.v1.backup_database_path.write_bytes(backup_source.read_bytes())
            self.v1.backup_database_path.chmod(0o600)
        self.assertEqual(
            telemetry_store.append_trace(
                self.v2, _replace_trace(_rows(), "9")
            ).outcome,
            "committed",
        )
        self.v1.backup_database_path.write_bytes(b"PRIVATE_HOSTILE_BACKUP")
        self.v1.backup_database_path.chmod(0o600)
        with self.assertRaises(telemetry_store.StoreIncompatibleError):
            telemetry_store.append_trace(
                self.v2, _replace_trace(_rows(), "b")
            )
        self.v1.backup_database_path.unlink()
        self.v1.migration_directory.mkdir(mode=0o700)
        with self.assertRaises(telemetry_store.StoreUnsafeError):
            telemetry_store.append_trace(
                self.v2, _replace_trace(_rows(), "c")
            )

    def test_status_uses_aggregate_split_capacity_boundaries(self) -> None:
        cases = (
            (
                QueueSnapshot(present=True, ready=2, pending_bytes=2),
                QueueSnapshot(present=True, ready=2, pending_bytes=2),
                {"PUBLISHED_MAX_ENTRIES": 4, "PUBLISHED_MAX_BYTES": 100},
            ),
            (
                QueueSnapshot(present=True, ready=1, pending_bytes=5),
                QueueSnapshot(present=True, ready=1, pending_bytes=5),
                {"PUBLISHED_MAX_ENTRIES": 100, "PUBLISHED_MAX_BYTES": 10},
            ),
        )
        for queue_v1, queue_v2, limits in cases:
            with self.subTest(limits=limits), patch.object(
                telemetry_writer,
                "scan_queue_read_only",
                side_effect=(queue_v1, queue_v2),
            ), patch.multiple(telemetry_writer, **limits):
                status = telemetry_status(paths=self.v1, environment={})
            self.assertTrue(status["queue"]["capacity_full"])

    def test_migrate_text_and_json_have_exact_fact_parity(self) -> None:
        json_result = telemetry_migrate_command(json_output=True, paths=self.v1)
        text_result = telemetry_migrate_command(json_output=False, paths=self.v1)
        facts = json.loads(json_result.output)
        rendered = {
            item.split("=", 1)[0]: item.split("=", 1)[1]
            for item in text_result.output.removeprefix("Telemetry migrate: ").split()
        }
        self.assertEqual(set(rendered), set(facts))
        for key, value in facts.items():
            expected = (
                "null"
                if value is None
                else "true"
                if value is True
                else "false"
                if value is False
                else str(value)
            )
            if key != "elapsed_ms":
                self.assertEqual(rendered[key], expected)

    def test_stateless_and_mismatched_state_remain_present_unverified(self) -> None:
        _create_v1_store(self.v1.database_path)
        self.assertEqual(
            telemetry_status(paths=self.v1, environment={})["store"]["state"],
            "present_unverified",
        )
        observed = self.v1.database_path.stat()
        write_writer_state(
            WriterState(
                phase="stopped",
                store_state="compatible",
                store_schema_version=1,
                persisted_runs_snapshot=0,
                database_device=observed.st_dev,
                database_inode=observed.st_ino + 1,
                database_bytes=observed.st_size,
            ),
            paths=self.v1,
        )
        self.assertEqual(
            telemetry_status(paths=self.v1, environment={})["store"]["state"],
            "present_unverified",
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
