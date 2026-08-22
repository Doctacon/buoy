from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

import duckdb

from buoy_search import telemetry_queue, telemetry_store, telemetry_writer
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
    TerminalReceipt,
    WriterState,
    claim_ready_names,
    publish_envelope,
    publish_terminal_receipt,
    read_terminal_receipt,
    read_writer_state,
    reconcile_writer_receipts_shared,
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
_BOOTSTRAP = "4" * 16
_PREPARE = "5" * 16
_EMBED = "6" * 16
_NAMESPACE = "7" * 16
_RENDER = "8" * 16
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
    bootstrap = (
        _TRACE,
        _BOOTSTRAP,
        _ROOT,
        "buoy.cli.bootstrap",
        _START,
        _START + timedelta(milliseconds=1),
        1.0,
        "OK",
        "{}",
    )
    prepare = (
        _TRACE,
        _PREPARE,
        _ROOT,
        "buoy.retrieve.prepare",
        _START + timedelta(milliseconds=1),
        _START + timedelta(milliseconds=2),
        1.0,
        "OK" if outcome == "success" or pipeline else "ERROR",
        "{}" if outcome == "success" or pipeline else _canonical(
            {"buoy.error.type": "configuration_error"}
        ),
    )
    render = (
        _TRACE,
        _RENDER,
        _ROOT,
        "buoy.output.render",
        _START + timedelta(milliseconds=8),
        _START + timedelta(milliseconds=9),
        1.0,
        "OK",
        "{}",
    )
    if not pipeline:
        return CommandTraceRows(command, None, (root, bootstrap, prepare, render), ())
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
    embed = (
        _TRACE,
        _EMBED,
        _PIPELINE,
        "buoy.query.embed",
        _START + timedelta(milliseconds=3),
        _START + timedelta(milliseconds=4),
        1.0,
        "OK",
        "{}",
    )
    namespace = (
        _TRACE,
        _NAMESPACE,
        _PIPELINE,
        "buoy.namespace.query",
        _START + timedelta(milliseconds=4),
        _START + timedelta(milliseconds=7),
        3.0,
        "OK",
        _canonical(
            {
                "buoy.namespace.hit_count": 1,
                "buoy.namespace.status": "ok",
                "buoy.route.rank": 1,
            }
        ),
    )
    return CommandTraceRows(
        command,
        operation,
        (root, bootstrap, prepare, pipeline_span, embed, namespace, render),
        (),
    )


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


def _publish_claimed_receipt(
    paths: telemetry_queue.TelemetryPaths,
    payload: bytes,
    *,
    recorded_at_unix_ms: int,
) -> tuple[str, telemetry_queue.ReceiptPublicationResult]:
    publication = publish_envelope(payload, paths=paths)
    assert publication.source_name is not None
    claimed = claim_ready_names(paths, (publication.source_name,))
    assert claimed == (publication.source_name,)
    result = publish_terminal_receipt(
        paths,
        TerminalReceipt(
            schema_version=paths.queue_version,
            kind="committed",
            source_name=publication.source_name,
            envelope_sha256=hashlib.sha256(payload).hexdigest(),
            digest_complete=True,
            envelope_bytes=len(payload),
            recorded_at_unix_ms=recorded_at_unix_ms,
            reason=None,
        ),
    )
    return publication.source_name, result


def _write_receipt_temporary(
    paths: telemetry_queue.TelemetryPaths,
    receipt: TerminalReceipt,
) -> str:
    name = telemetry_queue.receipt_temp_name_for_source(receipt.source_name)
    payload = telemetry_queue._canonical_json_bytes(
        telemetry_queue._receipt_object(receipt),
        maximum=telemetry_queue.RECEIPT_MAX_FILE_BYTES,
    )
    target = paths.receipts_directory / name
    target.write_bytes(payload)
    target.chmod(0o600)
    return name


def _json_span(value: dict[str, object], name: str) -> dict[str, object]:
    spans = value["spans"]
    assert isinstance(spans, list)
    return next(span for span in spans if span["name"] == name)


def _row_span(rows: CommandTraceRows, name: str) -> tuple[object, ...]:
    return next(span for span in rows.spans if span[3] == name)


def _automatic_v2_object() -> dict[str, object]:
    value = json.loads(encode_trace_envelope_v2(_rows()))
    value["command"]["retrieval_mode"] = "automatic"
    value["command"]["execution_mode"] = "live"
    value["spans"][0]["attributes"]["buoy.retrieval.mode"] = "automatic"
    pipeline = _json_span(value, V2_PIPELINE_SPAN_NAME)
    pipeline["attributes"]["buoy.retrieval.mode"] = "automatic"
    prepare = _json_span(value, "buoy.retrieve.prepare")
    start = prepare["started_at_unix_us"]
    routing_spans = [
        {
            "trace_id": value["command"]["trace_id"],
            "span_id": "c" * 16,
            "parent_span_id": prepare["span_id"],
            "name": "buoy.routing.model",
            "started_at_unix_us": start,
            "ended_at_unix_us": start + 100,
            "duration_ms": 0.1,
            "status_code": "OK",
            "attributes": {},
        },
        {
            "trace_id": value["command"]["trace_id"],
            "span_id": "9" * 16,
            "parent_span_id": prepare["span_id"],
            "name": "buoy.routing.catalog",
            "started_at_unix_us": start + 100,
            "ended_at_unix_us": start + 200,
            "duration_ms": 0.1,
            "status_code": "OK",
            "attributes": {},
        },
        {
            "trace_id": value["command"]["trace_id"],
            "span_id": "a" * 16,
            "parent_span_id": prepare["span_id"],
            "name": "buoy.routing.model",
            "started_at_unix_us": start + 200,
            "ended_at_unix_us": start + 300,
            "duration_ms": 0.1,
            "status_code": "OK",
            "attributes": {},
        },
        {
            "trace_id": value["command"]["trace_id"],
            "span_id": "b" * 16,
            "parent_span_id": prepare["span_id"],
            "name": "buoy.routing.select",
            "started_at_unix_us": start + 300,
            "ended_at_unix_us": start + 400,
            "duration_ms": 0.1,
            "status_code": "OK",
            "attributes": {},
        },
    ]
    value["spans"].extend(routing_spans)
    value["spans"].sort(
        key=lambda span: (span["started_at_unix_us"], span["span_id"])
    )
    return value


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
    pipeline = _json_span(value, V2_PIPELINE_SPAN_NAME)
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
        _json_span(duplicate, "buoy.cli.bootstrap")["span_id"] = duplicate[
            "spans"
        ][0]["span_id"]
        _json_span(changed("missing parent"), "buoy.cli.bootstrap")[
            "parent_span_id"
        ] = "9" * 16
        cycle = changed("cycle")
        bootstrap = _json_span(cycle, "buoy.cli.bootstrap")
        bootstrap["parent_span_id"] = bootstrap["span_id"]
        changed("span ordering")["spans"].reverse()
        outside = changed("child outside root")
        _json_span(outside, "buoy.cli.bootstrap")["ended_at_unix_us"] = (
            original["command"]["ended_at_unix_us"] + 1
        )
        changed("summary mismatch")["retrieval_operation"]["hit_count"] = 0
        changed("root status mismatch")["spans"][0]["status_code"] = "ERROR"
        _json_span(changed("pipeline status mismatch"), V2_PIPELINE_SPAN_NAME)[
            "status_code"
        ] = "ERROR"
        _json_span(changed("pipeline mode mismatch"), V2_PIPELINE_SPAN_NAME)[
            "attributes"
        ]["buoy.retrieval.mode"] = "automatic"
        no_pipeline = changed("live success without pipeline")
        no_pipeline["command"]["pipeline_present"] = False
        no_pipeline["spans"][0]["attributes"][
            "buoy.retrieval.pipeline_present"
        ] = False
        no_pipeline["retrieval_operation"] = None
        no_pipeline["spans"] = [
            span
            for span in no_pipeline["spans"]
            if span["name"]
            not in {
                V2_PIPELINE_SPAN_NAME,
                "buoy.query.embed",
                "buoy.namespace.query",
            }
        ]
        pipeline_error = changed("pipeline error without category")
        pipeline_error["retrieval_operation"]["outcome"] = "error"
        pipeline_span = _json_span(pipeline_error, V2_PIPELINE_SPAN_NAME)
        pipeline_span["attributes"]["buoy.retrieval.outcome"] = "error"
        pipeline_span["status_code"] = "ERROR"

        widened_null = _widened_v2_object()
        widened_null["retrieval_operation"]["fallback_reason"] = None
        _json_span(widened_null, V2_PIPELINE_SPAN_NAME)["attributes"].pop(
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

    def test_mode_outcome_cardinality_parentage_and_order_are_independent(self) -> None:
        valid = json.loads(encode_trace_envelope_v2(_rows()))
        automatic = _automatic_v2_object()
        decode_trace_envelope_v2(
            json.dumps(automatic, sort_keys=True, separators=(",", ":")).encode()
        )
        escaping = json.loads(
            encode_trace_envelope_v2(_rows(outcome="error", pipeline=False))
        )
        escaping["command"]["exit_code"] = 1
        escaping["spans"][0]["attributes"]["buoy.command.exit_code"] = 1
        escaping["spans"] = [
            span for span in escaping["spans"] if span["name"] != "buoy.output.render"
        ]
        decode_trace_envelope_v2(
            json.dumps(escaping, sort_keys=True, separators=(",", ":")).encode()
        )

        cases: list[tuple[str, dict[str, object]]] = []

        def without(name: str, span_name: str) -> None:
            value = deepcopy(valid)
            value["spans"] = [
                span for span in value["spans"] if span["name"] != span_name
            ]
            cases.append((name, value))

        without("missing bootstrap", "buoy.cli.bootstrap")
        without("missing prepare", "buoy.retrieve.prepare")
        without("missing returned render", "buoy.output.render")
        without("missing live embed", "buoy.query.embed")
        without("missing successful namespace", "buoy.namespace.query")

        duplicate = deepcopy(valid)
        duplicate_bootstrap = deepcopy(_json_span(duplicate, "buoy.cli.bootstrap"))
        duplicate_bootstrap["span_id"] = "c" * 16
        duplicate["spans"].append(duplicate_bootstrap)
        duplicate["spans"].sort(
            key=lambda span: (span["started_at_unix_us"], span["span_id"])
        )
        cases.append(("duplicate bootstrap", duplicate))

        duplicate_embed = deepcopy(valid)
        second_embed = deepcopy(_json_span(duplicate_embed, "buoy.query.embed"))
        second_embed["span_id"] = "d" * 16
        duplicate_embed["spans"].append(second_embed)
        duplicate_embed["spans"].sort(
            key=lambda span: (span["started_at_unix_us"], span["span_id"])
        )
        cases.append(("duplicate embed", duplicate_embed))

        misparented = deepcopy(valid)
        _json_span(misparented, V2_PIPELINE_SPAN_NAME)["parent_span_id"] = _json_span(
            misparented, "buoy.retrieve.prepare"
        )["span_id"]
        cases.append(("misparented pipeline", misparented))

        reordered = deepcopy(valid)
        render = _json_span(reordered, "buoy.output.render")
        render["started_at_unix_us"] = (
            _json_span(reordered, "buoy.retrieve.prepare")["started_at_unix_us"] + 100
        )
        render["ended_at_unix_us"] = render["started_at_unix_us"] + 100
        render["duration_ms"] = 0.1
        reordered["spans"].sort(
            key=lambda span: (span["started_at_unix_us"], span["span_id"])
        )
        cases.append(("render before pipeline", reordered))

        explicit_routing = deepcopy(automatic)
        explicit_routing["command"]["retrieval_mode"] = "explicit_single"
        explicit_routing["spans"][0]["attributes"][
            "buoy.retrieval.mode"
        ] = "explicit_single"
        _json_span(explicit_routing, V2_PIPELINE_SPAN_NAME)["attributes"][
            "buoy.retrieval.mode"
        ] = "explicit_single"
        cases.append(("explicit routing stages", explicit_routing))

        for span_name in (
            "buoy.routing.catalog",
            "buoy.routing.model",
            "buoy.routing.select",
        ):
            missing = deepcopy(automatic)
            missing["spans"] = [
                span for span in missing["spans"] if span["name"] != span_name
            ]
            cases.append((f"automatic missing {span_name}", missing))

        duplicate_catalog = deepcopy(automatic)
        catalog = deepcopy(_json_span(duplicate_catalog, "buoy.routing.catalog"))
        catalog["span_id"] = "d" * 16
        duplicate_catalog["spans"].append(catalog)
        duplicate_catalog["spans"].sort(
            key=lambda span: (span["started_at_unix_us"], span["span_id"])
        )
        cases.append(("automatic duplicate catalog", duplicate_catalog))

        bad_order = deepcopy(automatic)
        catalog = _json_span(bad_order, "buoy.routing.catalog")
        selection = _json_span(bad_order, "buoy.routing.select")
        catalog["started_at_unix_us"] = selection["ended_at_unix_us"]
        catalog["ended_at_unix_us"] = catalog["started_at_unix_us"] + 100
        catalog["duration_ms"] = 0.1
        bad_order["spans"].sort(
            key=lambda span: (span["started_at_unix_us"], span["span_id"])
        )
        cases.append(("automatic catalog after select", bad_order))

        error_zero = json.loads(
            encode_trace_envelope_v2(_rows(outcome="error", pipeline=False))
        )
        error_zero["command"]["exit_code"] = 0
        error_zero["spans"][0]["attributes"]["buoy.command.exit_code"] = 0
        cases.append(("error outcome with zero exit", error_zero))

        escaping_render_ok = deepcopy(escaping)
        render = deepcopy(_json_span(valid, "buoy.output.render"))
        escaping_render_ok["spans"].append(render)
        escaping_render_ok["spans"].sort(
            key=lambda span: (span["started_at_unix_us"], span["span_id"])
        )
        cases.append(("escaping exception with successful render", escaping_render_ok))

        for name, value in cases:
            with self.subTest(name=name):
                with self.assertRaises(TraceEnvelopeError) as raised:
                    decode_trace_envelope_v2(
                        json.dumps(
                            value, sort_keys=True, separators=(",", ":")
                        ).encode()
                    )
                self.assertEqual(raised.exception.reason, "invalid_graph")


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

    def test_writer_rejects_impossible_v2_graphs_before_database_mutation(self) -> None:
        invalid_graph = json.loads(encode_trace_envelope_v2(_rows()))
        invalid_graph["spans"] = [
            span
            for span in invalid_graph["spans"]
            if span["name"] != "buoy.query.embed"
        ]
        error_zero = json.loads(
            encode_trace_envelope_v2(_rows(outcome="error", pipeline=False))
        )
        error_zero["command"]["exit_code"] = 0
        error_zero["spans"][0]["attributes"]["buoy.command.exit_code"] = 0
        publications = []
        for value in (invalid_graph, error_zero):
            publications.append(
                publish_envelope(
                    json.dumps(value, sort_keys=True, separators=(",", ":")).encode(),
                    paths=self.v2,
                )
            )
        valid = publish_envelope(encode_trace_envelope_v2(_rows()), paths=self.v2)
        with patch("buoy_search.telemetry_writer.IDLE_EXIT_SECONDS", 0):
            self.assertEqual(run_writer(self.v1), 0)
        receipts = [
            read_terminal_receipt(result.source_name, paths=self.v2)
            for result in (*publications, valid)
        ]
        self.assertEqual(
            [(receipt.kind, receipt.reason) for receipt in receipts],
            [("rejected", "invalid_graph"), ("rejected", "invalid_graph"), ("committed", None)],
        )
        with duckdb.connect(
            str(self.v2.database_path), read_only=True, config=_SAFE_CONFIG
        ) as connection:
            self.assertEqual(
                connection.execute("SELECT count(*) FROM retrieve_command_runs").fetchone(),
                (1,),
            )

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
                (12,),
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
            "backup_candidate_copied",
            "backup_candidate_validated",
            "transaction_committed",
            "scratch_validated",
            "backup_published",
            "backup_validated",
            "backup_fsynced",
            "canonical_published",
            "directory_fsynced",
            "state_publication_ready",
        )
        for phase in phases:
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as raw:
                paths = telemetry_paths(Path(raw) / "telemetry")
                _create_v1_store(paths.database_path)

                class InjectedCrash(BaseException):
                    pass

                def fail(
                    observed: str,
                    selected_phase: str = phase,
                ) -> None:
                    if observed == selected_phase:
                        raise InjectedCrash

                with self.assertRaises(InjectedCrash):
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
                retried = telemetry_migrate_command(
                    json_output=True, paths=paths
                )
                self.assertEqual(retried.exit_code, 0)
                self.assertIn(
                    json.loads(retried.output)["outcome"],
                    {"migrated", "already_current"},
                )
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
        changed_command[6] = "explicit_multi"
        changed_spans = []
        for span in v2.spans:
            changed_span = list(span)
            if span[3] in {V2_COMMAND_ROOT_SPAN_NAME, V2_PIPELINE_SPAN_NAME}:
                attributes = json.loads(changed_span[8])
                attributes["buoy.retrieval.mode"] = "explicit_multi"
                changed_span[8] = _canonical(attributes)
            changed_spans.append(tuple(changed_span))
        v2_conflict = CommandTraceRows(
            tuple(changed_command),
            v2.retrieval_operation,
            tuple(changed_spans),
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


    def test_backup_published_retry_skips_later_v1_then_flushes_once(self) -> None:
        _create_v1_store(self.v1.database_path)
        source = _v1_rows()
        _insert_v1_rows(self.v1.database_path, (source,))

        class InjectedCrash(BaseException):
            pass

        def crash(phase: str) -> None:
            if phase == "backup_published":
                raise InjectedCrash

        with self.assertRaises(InjectedCrash):
            telemetry_store.migrate_store_v1_to_v2(
                self.v1, fault_hook=crash
            )
        backup = self.v1.backup_database_path.read_bytes()
        later = _replace_v1_trace(source, 2)
        published = publish_envelope(
            encode_trace_envelope_v1(later), paths=self.v1
        )
        migrated = telemetry_migrate_command(json_output=True, paths=self.v1)
        facts = json.loads(migrated.output)
        self.assertEqual((migrated.exit_code, facts["outcome"]), (0, "migrated"))
        self.assertEqual(facts["migrated_v1_runs"], 1)
        self.assertEqual(scan_queue_read_only(self.v1).ready, 1)
        self.assertEqual(self.v1.backup_database_path.read_bytes(), backup)

        def start_writer(**_kwargs: object) -> None:
            with patch.object(telemetry_writer, "IDLE_EXIT_SECONDS", 0):
                run_writer(self.v1)

        with patch.object(
            telemetry_writer, "request_writer_start", side_effect=start_writer
        ):
            flushed = telemetry_flush(timeout=5, paths=self.v1)
        self.assertEqual(flushed["outcome"], "flushed")
        assert published.source_name is not None
        self.assertEqual(
            read_terminal_receipt(
                published.source_name, paths=self.v1
            ).kind,
            "committed",
        )
        with duckdb.connect(
            str(self.v1.database_path), read_only=True, config=_SAFE_CONFIG
        ) as connection:
            self.assertEqual(
                connection.execute("SELECT count(*) FROM trace_runs").fetchone()[0],
                2,
            )
        with patch.object(
            telemetry_writer, "request_writer_start", side_effect=start_writer
        ):
            self.assertEqual(
                telemetry_flush(timeout=1, paths=self.v1)["outcome"], "empty"
            )
        self.assertEqual(self.v1.backup_database_path.read_bytes(), backup)

    def test_incomplete_migration_scans_block_before_store_import(self) -> None:
        _create_v1_store(self.v1.database_path)
        for incomplete_version in (1, 2):
            with self.subTest(queue_version=incomplete_version):
                calls = 0

                def scan(paths: telemetry_queue.TelemetryPaths) -> QueueSnapshot:
                    nonlocal calls
                    calls += 1
                    return QueueSnapshot(
                        present=True,
                        scan_incomplete=paths.queue_version == incomplete_version,
                    )

                with patch.object(
                    telemetry_writer, "scan_queue_read_only", side_effect=scan
                ), patch.object(
                    telemetry_writer,
                    "_load_store_module",
                    side_effect=AssertionError("store imported"),
                ) as load:
                    result = telemetry_migrate_command(
                        json_output=True, paths=self.v1
                    )
                self.assertEqual(result.exit_code, 2)
                self.assertEqual(calls, 2)
                load.assert_not_called()

        calls = 0

        def post_lock_scan(paths: telemetry_queue.TelemetryPaths) -> QueueSnapshot:
            nonlocal calls
            calls += 1
            return QueueSnapshot(
                present=True,
                scan_incomplete=calls == 3 and paths.queue_version == 1,
            )

        with patch.object(
            telemetry_writer,
            "scan_queue_read_only",
            side_effect=post_lock_scan,
        ), patch.object(
            telemetry_writer,
            "_load_store_module",
            side_effect=AssertionError("store imported"),
        ) as load:
            result = telemetry_migrate_command(
                json_output=True, paths=self.v1
            )
        self.assertEqual(result.exit_code, 2)
        self.assertEqual(calls, 4)
        load.assert_not_called()

    def test_exact_object_inventory_rejects_all_user_metadata_v1_and_v2(self) -> None:
        mutations = {
            "macro": "CREATE MACRO current_database() AS 'shadow'",
            "sequence": "CREATE SEQUENCE unexpected_sequence",
            "type": "CREATE TYPE unexpected_type AS ENUM ('x')",
            "default": (
                "ALTER TABLE trace_runs ALTER COLUMN outcome "
                "SET DEFAULT 'success'"
            ),
            "comment": "COMMENT ON TABLE trace_runs IS 'private comment'",
        }
        for version in (1, 2):
            for name, statement in mutations.items():
                with self.subTest(version=version, mutation=name), tempfile.TemporaryDirectory() as raw:
                    paths = telemetry_paths(Path(raw) / "telemetry")
                    if version == 1:
                        _create_v1_store(paths.database_path)
                    else:
                        telemetry_store.append_trace(
                            telemetry_paths_v2(paths.directory), _rows()
                        )
                    with duckdb.connect(
                        str(paths.database_path), config=_SAFE_CONFIG
                    ) as connection:
                        connection.execute(statement)
                    with self.assertRaises(telemetry_store.StoreUnsafeError):
                        telemetry_store.inspect_store_schema_version(paths)

    def test_exact_v2_content_privacy_and_graph_edits_block(self) -> None:
        sentinel = "PRIVATE_EDITED_V2_SENTINEL"
        mutations = {
            "privacy": (
                "UPDATE spans SET attributes = ? WHERE parent_span_id IS NULL",
                (_canonical({"private": sentinel}),),
            ),
            "oversized_scalar": (
                "UPDATE spans SET attributes = ? WHERE parent_span_id IS NULL",
                (_canonical({"private": "x" * 65_537}),),
            ),
            "graph": (
                "UPDATE spans SET parent_span_id = ? WHERE parent_span_id IS NULL",
                ("f" * 16,),
            ),
        }
        for name, (statement, parameters) in mutations.items():
            with self.subTest(mutation=name), tempfile.TemporaryDirectory() as raw:
                paths = telemetry_paths(Path(raw) / "telemetry")
                v2 = telemetry_paths_v2(paths.directory)
                telemetry_store.append_trace(v2, _rows())
                with duckdb.connect(
                    str(paths.database_path), config=_SAFE_CONFIG
                ) as connection:
                    connection.execute(statement, parameters)
                with self.assertRaises(telemetry_store.StoreUnsafeError):
                    telemetry_store.inspect_store_schema_version(paths)
                result = telemetry_migrate_command(
                    json_output=True, paths=paths
                )
                self.assertEqual(result.exit_code, 2)
                self.assertNotIn(sentinel, result.output)

        with tempfile.TemporaryDirectory() as raw:
            paths = telemetry_paths(Path(raw) / "telemetry")
            v2 = telemetry_paths_v2(paths.directory)
            telemetry_store.append_trace(v2, _rows())
            with duckdb.connect(
                str(paths.database_path), config=_SAFE_CONFIG
            ) as connection:
                connection.execute(
                    """
                    INSERT INTO spans
                    SELECT trace_id, lpad(to_hex(i), 16, '0'), root_span_id,
                           'buoy.retrieve.pipeline', started_at, ended_at,
                           command_duration_ms, 'OK', '{}'
                    FROM retrieve_command_runs, range(1, 257) AS values(i)
                    """
                )
            with self.assertRaises(telemetry_store.StoreUnsafeError):
                telemetry_store.inspect_store_schema_version(paths)

    def test_retained_backup_must_be_valid_and_match_canonical_v1_history(self) -> None:
        sentinel = "PRIVATE_BACKUP_CONTENT_SENTINEL"
        mutations = {
            "privacy": (
                "UPDATE spans SET attributes = ?",
                (_canonical({"private": sentinel}),),
            ),
            "graph": (
                "UPDATE spans SET parent_span_id = ?",
                ("f" * 16,),
            ),
            "different_valid_history": (None, ()),
        }
        for name, (statement, parameters) in mutations.items():
            with self.subTest(mutation=name), tempfile.TemporaryDirectory() as raw:
                paths = telemetry_paths(Path(raw) / "telemetry")
                v2 = telemetry_paths_v2(paths.directory)
                _create_v1_store(paths.database_path)
                _insert_v1_rows(paths.database_path, (_v1_rows(),))
                telemetry_store.migrate_store_v1_to_v2(paths)
                with duckdb.connect(
                    str(paths.backup_database_path), config=_SAFE_CONFIG
                ) as connection:
                    if statement is not None:
                        connection.execute(statement, parameters)
                    else:
                        connection.execute(
                            "UPDATE spans SET trace_id = ?",
                            ("c" * 32,),
                        )
                        connection.execute(
                            "UPDATE trace_runs SET trace_id = ?",
                            ("c" * 32,),
                        )
                with self.assertRaises(telemetry_store.StoreIncompatibleError):
                    telemetry_store.append_trace(v2, _rows())
                with self.assertRaises(telemetry_store.StoreIncompatibleError):
                    telemetry_store.reconcile_already_current_store(paths)
                self.assertNotIn(
                    sentinel,
                    telemetry_migrate_command(
                        json_output=True, paths=paths
                    ).output,
                )

    def test_orphan_auxiliary_store_state_is_blocked_and_nonmutating(self) -> None:
        cases = ("backup", "migration", "initialization", "hostile_backup")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as raw:
                paths = telemetry_paths(Path(raw) / "telemetry")
                paths.directory.mkdir(mode=0o700)
                if case == "backup":
                    paths.backup_database_path.write_bytes(b"safe")
                    paths.backup_database_path.chmod(0o600)
                elif case == "migration":
                    paths.migration_directory.mkdir(mode=0o700)
                elif case == "initialization":
                    paths.database_init_directory.mkdir(mode=0o700)
                else:
                    target = Path(raw) / "target"
                    target.write_bytes(b"untouched")
                    paths.backup_database_path.symlink_to(target)
                before = sorted(
                    (item.relative_to(paths.directory).as_posix(), item.is_symlink())
                    for item in paths.directory.rglob("*")
                )
                result = telemetry_migrate_command(
                    json_output=True, paths=paths
                )
                facts = json.loads(result.output)
                self.assertEqual((result.exit_code, facts["outcome"]), (2, "blocked"))
                self.assertEqual(facts["backup_present"], case == "backup")
                after = sorted(
                    (item.relative_to(paths.directory).as_posix(), item.is_symlink())
                    for item in paths.directory.rglob("*")
                )
                self.assertEqual(after, before)

    def test_receipt_capacity_rotation_and_reconciliation_are_shared(self) -> None:
        now_ms = int(time.time() * 1_000)
        first, _ = _publish_claimed_receipt(
            self.v1, encode_trace_envelope_v1(_v1_rows()), recorded_at_unix_ms=now_ms
        )
        second, _ = _publish_claimed_receipt(
            self.v2, encode_trace_envelope_v2(_rows()), recorded_at_unix_ms=now_ms
        )
        third_rows = _replace_v1_trace(_v1_rows(), 3)
        third_publication = publish_envelope(
            encode_trace_envelope_v1(third_rows), paths=self.v1
        )
        assert third_publication.source_name is not None
        claim_ready_names(self.v1, (third_publication.source_name,))
        third_receipt = TerminalReceipt(
            schema_version=1,
            kind="committed",
            source_name=third_publication.source_name,
            envelope_sha256=hashlib.sha256(
                encode_trace_envelope_v1(third_rows)
            ).hexdigest(),
            digest_complete=True,
            envelope_bytes=len(encode_trace_envelope_v1(third_rows)),
            recorded_at_unix_ms=now_ms,
            reason=None,
        )
        with patch.object(telemetry_queue, "RECEIPT_MAX_ENTRIES", 2):
            with self.assertRaises(telemetry_queue.TelemetryQueueError):
                publish_terminal_receipt(self.v1, third_receipt)
            first_path = self.v1.receipts_directory / telemetry_queue.receipt_name_for_source(first)
            old_ns = (now_ms - 122_000) * 1_000_000
            os.utime(first_path, ns=(old_ns, old_ns))
            published = publish_terminal_receipt(self.v1, third_receipt)
            self.assertIn(
                telemetry_queue.receipt_name_for_source(first),
                published.rotated_names,
            )
            state = reconcile_writer_receipts_shared(
                WriterState(
                    accounted_receipts=tuple(
                        sorted(
                            (
                                telemetry_queue.receipt_name_for_source(first),
                                telemetry_queue.receipt_name_for_source(second),
                            )
                        )
                    )
                ),
                paths=(self.v1, self.v2),
            )
            self.assertEqual(len(state.accounted_receipts), 2)
            self.assertEqual(state.receipts_rotated, 1)

    def test_shared_receipt_byte_and_temporary_boundaries(self) -> None:
        now_ms = int(time.time() * 1_000)
        _publish_claimed_receipt(
            self.v1, encode_trace_envelope_v1(_v1_rows()), recorded_at_unix_ms=now_ms
        )
        _publish_claimed_receipt(
            self.v2, encode_trace_envelope_v2(_rows()), recorded_at_unix_ms=now_ms
        )
        existing_bytes = sum(
            item.stat().st_size
            for directory in (
                self.v1.receipts_directory,
                self.v2.receipts_directory,
            )
            for item in directory.iterdir()
        )
        later = _replace_trace(_rows(), "8")
        source = publish_envelope(
            encode_trace_envelope_v2(later), paths=self.v2
        ).source_name
        assert source is not None
        claim_ready_names(self.v2, (source,))
        receipt = TerminalReceipt(
            2,
            "committed",
            source,
            hashlib.sha256(encode_trace_envelope_v2(later)).hexdigest(),
            True,
            len(encode_trace_envelope_v2(later)),
            now_ms,
            None,
        )
        with patch.object(telemetry_queue, "RECEIPT_MAX_ENTRIES", 10), patch.object(
            telemetry_queue, "RECEIPT_MAX_BYTES", existing_bytes
        ), self.assertRaises(telemetry_queue.TelemetryQueueError):
            publish_terminal_receipt(self.v2, receipt)

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "telemetry"
            v1 = telemetry_paths(root)
            v2 = telemetry_paths_v2(root)
            p1 = publish_envelope(encode_trace_envelope_v1(_v1_rows()), paths=v1)
            p2 = publish_envelope(encode_trace_envelope_v2(_rows()), paths=v2)
            assert p1.source_name and p2.source_name
            claim_ready_names(v1, (p1.source_name,))
            for paths, name in ((v1, "r1-" + "a" * 32 + ".part"), (v2, "r2-" + "b" * 32 + ".part")):
                path = paths.receipts_directory / name
                path.write_bytes(b"x")
                path.chmod(0o600)
            receipt = TerminalReceipt(
                1,
                "committed",
                p1.source_name,
                hashlib.sha256(encode_trace_envelope_v1(_v1_rows())).hexdigest(),
                True,
                len(encode_trace_envelope_v1(_v1_rows())),
                now_ms,
                None,
            )
            with patch.object(telemetry_queue, "RECEIPT_MAX_ENTRIES", 2), self.assertRaises(
                telemetry_queue.TelemetryQueueError
            ):
                publish_terminal_receipt(v1, receipt)


    def test_receipt_recovery_uses_trusted_time_for_split_capacity(self) -> None:
        def setup_case(raw: str) -> tuple[
            telemetry_queue.TelemetryPaths,
            telemetry_queue.TelemetryPaths,
            str,
            str,
            str,
        ]:
            v1 = telemetry_paths(Path(raw) / "telemetry")
            v2 = telemetry_paths_v2(v1.directory)
            now_ms = int(time.time() * 1_000)
            first, _ = _publish_claimed_receipt(
                v1,
                encode_trace_envelope_v1(_v1_rows()),
                recorded_at_unix_ms=now_ms,
            )
            second, _ = _publish_claimed_receipt(
                v2,
                encode_trace_envelope_v2(_rows()),
                recorded_at_unix_ms=now_ms,
            )
            later = _replace_v1_trace(_v1_rows(), 9)
            publication = publish_envelope(
                encode_trace_envelope_v1(later), paths=v1
            )
            assert publication.source_name is not None
            claim_ready_names(v1, (publication.source_name,))
            return v1, v2, first, second, publication.source_name

        with tempfile.TemporaryDirectory() as raw:
            v1, v2, first, second, source = setup_case(raw)
            future = TerminalReceipt(
                1,
                "committed",
                source,
                hashlib.sha256(
                    encode_trace_envelope_v1(_replace_v1_trace(_v1_rows(), 9))
                ).hexdigest(),
                True,
                len(encode_trace_envelope_v1(_replace_v1_trace(_v1_rows(), 9))),
                telemetry_queue.COUNTER_MAX,
                None,
            )
            temporary = _write_receipt_temporary(v1, future)
            total_bytes = sum(
                item.stat().st_size
                for directory in (v1.receipts_directory, v2.receipts_directory)
                for item in directory.iterdir()
                if item.suffix == ".json"
            )
            with patch.object(telemetry_queue, "RECEIPT_MAX_ENTRIES", 2), patch.object(
                telemetry_queue, "RECEIPT_MAX_BYTES", total_bytes
            ), self.assertRaises(telemetry_queue.TelemetryQueueError):
                telemetry_queue.resolve_receipt_temporary(
                    v1,
                    temporary,
                    terminal_condition_proven=True,
                )
            self.assertIsNotNone(read_terminal_receipt(first, paths=v1))
            self.assertIsNotNone(read_terminal_receipt(second, paths=v2))
            self.assertTrue((v1.receipts_directory / temporary).exists())

        with tempfile.TemporaryDirectory() as raw:
            v1, v2, first, second, source = setup_case(raw)
            first_name = telemetry_queue.receipt_name_for_source(first)
            second_name = telemetry_queue.receipt_name_for_source(second)
            old_ns = time.time_ns() - 122 * 1_000_000_000
            for paths, name in (
                (v1, first_name),
                (v2, second_name),
            ):
                os.utime(
                    paths.receipts_directory / name,
                    ns=(old_ns, old_ns),
                )
            ancient = TerminalReceipt(
                1,
                "committed",
                source,
                hashlib.sha256(
                    encode_trace_envelope_v1(_replace_v1_trace(_v1_rows(), 9))
                ).hexdigest(),
                True,
                len(encode_trace_envelope_v1(_replace_v1_trace(_v1_rows(), 9))),
                0,
                None,
            )
            temporary = _write_receipt_temporary(v1, ancient)
            total_bytes = sum(
                item.stat().st_size
                for directory in (v1.receipts_directory, v2.receipts_directory)
                for item in directory.iterdir()
                if item.suffix == ".json"
            )
            with patch.object(telemetry_queue, "RECEIPT_MAX_ENTRIES", 2), patch.object(
                telemetry_queue, "RECEIPT_MAX_BYTES", total_bytes
            ):
                self.assertTrue(
                    telemetry_queue.resolve_receipt_temporary(
                        v1,
                        temporary,
                        terminal_condition_proven=True,
                    )
                )
            self.assertFalse((v1.receipts_directory / first_name).exists())
            self.assertTrue((v2.receipts_directory / second_name).exists())
            self.assertIsNotNone(read_terminal_receipt(second, paths=v2))
            self.assertIsNotNone(read_terminal_receipt(source, paths=v1))

    def test_writer_lifecycle_blocks_every_incomplete_scan_phase(self) -> None:
        phases = {"startup": 1, "recovery": 2, "main": 4, "final_idle": 5}
        for version in (1, 2):
            for phase, incomplete_call in phases.items():
                with self.subTest(version=version, phase=phase), tempfile.TemporaryDirectory() as raw:
                    v1 = telemetry_paths(Path(raw) / "telemetry")
                    target = v1 if version == 1 else telemetry_paths_v2(v1.directory)
                    payload = (
                        encode_trace_envelope_v1(_v1_rows())
                        if version == 1
                        else encode_trace_envelope_v2(_rows())
                    )
                    publication = publish_envelope(payload, paths=target)
                    assert publication.source_name is not None
                    if phase == "recovery":
                        claim_ready_names(target, (publication.source_name,))
                    elif phase == "final_idle":
                        target.ready_directory.joinpath(
                            publication.source_name
                        ).unlink()
                    real_scan = telemetry_writer.scan_queue_read_only
                    target_calls = 0

                    def scan(paths: telemetry_queue.TelemetryPaths) -> QueueSnapshot:
                        nonlocal target_calls
                        if paths.queue_version == version:
                            target_calls += 1
                            if target_calls == incomplete_call:
                                return QueueSnapshot(
                                    present=True,
                                    scan_incomplete=True,
                                )
                        return real_scan(paths)

                    with patch.object(
                        telemetry_writer,
                        "scan_queue_read_only",
                        side_effect=scan,
                    ), patch.object(telemetry_writer, "IDLE_EXIT_SECONDS", 0):
                        self.assertEqual(
                            run_writer(v1),
                            0 if phase == "final_idle" else 1,
                        )
                    state = read_writer_state(v1)
                    assert state is not None
                    self.assertEqual((state.phase, state.reason), ("blocked", "queue_unsafe"))
                    self.assertNotEqual(state.phase, "stopped")
                    if phase != "final_idle":
                        snapshot = scan_queue_read_only(target)
                        self.assertEqual(snapshot.ready + snapshot.claimed, 1)
                    start = telemetry_queue.request_writer_start(paths=v1)
                    self.assertTrue(start.suppressed)

    def test_large_hostile_scratch_inventory_is_bounded_and_nonmutating(self) -> None:
        for operation in ("status", "migrate", "reconcile", "prepare", "cleanup"):
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as raw:
                paths = telemetry_paths(Path(raw) / "telemetry")
                paths.directory.mkdir(mode=0o700)
                paths.migration_directory.mkdir(mode=0o700)
                for index in range(512):
                    entry = paths.migration_directory / f"hostile-{index:04d}"
                    entry.write_bytes(b"PRIVATE_SCRATCH_SENTINEL")
                    entry.chmod(0o600)
                before = tuple(sorted(item.name for item in paths.migration_directory.iterdir()))
                with patch.object(
                    telemetry_store,
                    "_connect_database",
                    side_effect=AssertionError("DuckDB opened"),
                ) as connect:
                    if operation == "status":
                        result = telemetry_status(paths=paths, environment={})
                        self.assertEqual(result["overall"], "blocked")
                    elif operation == "migrate":
                        with patch.object(
                            telemetry_writer,
                            "_load_store_module",
                            side_effect=AssertionError("store imported"),
                        ) as load:
                            result = telemetry_migrate_command(
                                json_output=True, paths=paths
                            )
                            self.assertEqual(result.exit_code, 2)
                            self.assertNotIn("PRIVATE_SCRATCH_SENTINEL", result.output)
                            load.assert_not_called()
                    elif operation == "reconcile":
                        with self.assertRaises(telemetry_store.StoreUnsafeError):
                            telemetry_store.reconcile_already_current_store(paths)
                    else:
                        root_fd = telemetry_queue.open_verified_directory(
                            paths.directory
                        )
                        try:
                            if operation == "prepare":
                                with self.assertRaises(telemetry_store.StoreUnsafeError):
                                    telemetry_store._prepare_migration_scratch(root_fd)
                            else:
                                scratch_fd = telemetry_queue.open_private_directory_at(
                                    root_fd,
                                    telemetry_store.DATABASE_MIGRATION_DIRECTORY,
                                    create=False,
                                )
                                telemetry_store._remove_safe_migration_scratch(
                                    root_fd, scratch_fd
                                )
                        finally:
                            os.close(root_fd)
                    connect.assert_not_called()
                after = tuple(sorted(item.name for item in paths.migration_directory.iterdir()))
                self.assertEqual(after, before)

    def test_final_pending_v2_snapshot_is_queue_lock_linearized(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            paths = telemetry_paths(Path(raw) / "telemetry")
            v2 = telemetry_paths_v2(paths.directory)
            _create_v1_store(paths.database_path)
            self.assertEqual(
                telemetry_migrate_command(
                    json_output=True, paths=paths
                ).exit_code,
                0,
            )

            producer_before_rename = threading.Event()
            release_producer = threading.Event()
            snapshot_lock_contended = threading.Event()
            snapshot_lock_acquired = threading.Event()
            final_scan_started = threading.Event()
            order: list[str] = []
            producer_results: list[telemetry_queue.PublicationResult] = []
            migration_results: list[telemetry_writer.CommandResult] = []
            thread_errors: list[BaseException] = []
            real_require_name = telemetry_queue._require_open_name_matches_fd
            real_queue_lock = telemetry_writer.queue_lock
            real_rename = telemetry_queue.os.rename
            real_scan = telemetry_writer.scan_queue_read_only
            assert telemetry_queue.fcntl is not None
            real_flock = telemetry_queue.fcntl.flock
            exclusive_nonblocking = (
                telemetry_queue.fcntl.LOCK_EX | telemetry_queue.fcntl.LOCK_NB
            )

            def pause_before_ready_rename(
                parent_fd: int,
                name: str,
                descriptor: int,
            ) -> None:
                real_require_name(parent_fd, name, descriptor)
                if name.startswith("v2-") and name.endswith(".part"):
                    order.append("producer_holds_queue_lock_before_rename")
                    producer_before_rename.set()
                    if not release_producer.wait(5):
                        raise AssertionError("producer release timed out")

            def observe_rename(
                source: str,
                destination: str,
                *args: object,
                **kwargs: object,
            ) -> None:
                real_rename(source, destination, *args, **kwargs)
                if (
                    threading.current_thread().name == "paused-v2-producer"
                    and source.startswith("v2-")
                    and source.endswith(".part")
                    and destination.endswith(".json")
                ):
                    order.append("producer_ready_rename")

            def observe_flock(descriptor: int, operation: int) -> None:
                try:
                    real_flock(descriptor, operation)
                except BlockingIOError:
                    if (
                        threading.current_thread().name
                        == "migration-final-snapshot"
                        and operation == exclusive_nonblocking
                    ):
                        order.append("snapshot_queue_lock_contended")
                        snapshot_lock_contended.set()
                    raise

            @contextmanager
            def observe_final_queue_lock(
                selected: telemetry_queue.TelemetryPaths,
                *args: object,
                **kwargs: object,
            ) -> object:
                with real_queue_lock(selected, *args, **kwargs) as descriptor:
                    order.append("snapshot_queue_lock_acquired")
                    snapshot_lock_acquired.set()
                    yield descriptor

            def observe_scan(
                selected: telemetry_queue.TelemetryPaths,
            ) -> QueueSnapshot:
                if (
                    threading.current_thread().name
                    == "migration-final-snapshot"
                    and snapshot_lock_contended.is_set()
                ):
                    order.append("final_v2_scan")
                    final_scan_started.set()
                return real_scan(selected)

            def run_producer() -> None:
                try:
                    producer_results.append(
                        publish_envelope(
                            encode_trace_envelope_v2(_rows()), paths=v2
                        )
                    )
                except BaseException as exc:
                    thread_errors.append(exc)

            def run_migration() -> None:
                try:
                    migration_results.append(
                        telemetry_migrate_command(
                            json_output=True, paths=paths
                        )
                    )
                except BaseException as exc:
                    thread_errors.append(exc)

            producer = threading.Thread(
                target=run_producer,
                name="paused-v2-producer",
                daemon=True,
            )
            migration = threading.Thread(
                target=run_migration,
                name="migration-final-snapshot",
                daemon=True,
            )
            rename_mock = Mock(side_effect=observe_rename)
            supported_dir_fd = set(telemetry_queue.os.supports_dir_fd)
            supported_dir_fd.add(rename_mock)
            migration_started = False
            try:
                with patch.object(
                    telemetry_queue,
                    "_require_open_name_matches_fd",
                    side_effect=pause_before_ready_rename,
                ), patch.object(
                    telemetry_queue.os,
                    "rename",
                    rename_mock,
                ), patch.object(
                    telemetry_queue.os,
                    "supports_dir_fd",
                    supported_dir_fd,
                ), patch.object(
                    telemetry_queue.fcntl,
                    "flock",
                    side_effect=observe_flock,
                ), patch.object(
                    telemetry_writer,
                    "queue_lock",
                    side_effect=observe_final_queue_lock,
                ), patch.object(
                    telemetry_writer,
                    "scan_queue_read_only",
                    side_effect=observe_scan,
                ):
                    producer.start()
                    self.assertTrue(
                        producer_before_rename.wait(5),
                        thread_errors or producer_results,
                    )
                    migration.start()
                    migration_started = True
                    self.assertTrue(snapshot_lock_contended.wait(5))
                    self.assertFalse(snapshot_lock_acquired.is_set())
                    self.assertFalse(final_scan_started.is_set())
                    release_producer.set()
                    producer.join(5)
                    migration.join(5)
            finally:
                release_producer.set()
                producer.join(5)
                if migration_started:
                    migration.join(5)

            self.assertFalse(producer.is_alive())
            self.assertFalse(migration.is_alive())
            self.assertEqual(thread_errors, [])
            self.assertEqual(len(producer_results), 1)
            self.assertTrue(producer_results[0].published)
            self.assertEqual(len(migration_results), 1)
            migration_facts = json.loads(migration_results[0].output)
            self.assertEqual(
                (migration_results[0].exit_code, migration_facts["outcome"]),
                (0, "already_current"),
            )
            self.assertEqual(migration_facts["pending_v2"], 1)
            self.assertLess(
                order.index("snapshot_queue_lock_contended"),
                order.index("producer_ready_rename"),
            )
            self.assertLess(
                order.index("producer_ready_rename"),
                order.index("snapshot_queue_lock_acquired"),
            )
            self.assertLess(
                order.index("snapshot_queue_lock_acquired"),
                order.index("final_v2_scan"),
            )

    def test_final_pending_v2_snapshot_blocks_on_timeout_or_incomplete(self) -> None:
        for failure in ("timeout", "incomplete"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as raw:
                paths = telemetry_paths(Path(raw) / "telemetry")
                _create_v1_store(paths.database_path)
                real_scan = telemetry_writer.scan_queue_read_only
                v2_calls = 0

                def incomplete_final(
                    selected: telemetry_queue.TelemetryPaths,
                ) -> QueueSnapshot:
                    nonlocal v2_calls
                    result = real_scan(selected)
                    if selected.queue_version == 2:
                        v2_calls += 1
                        if v2_calls == 3:
                            return QueueSnapshot(
                                present=result.present,
                                scan_incomplete=True,
                            )
                    return result

                @contextmanager
                def timeout_lock(*args: object, **kwargs: object) -> object:
                    raise telemetry_queue.QueueLockTimeout("busy")
                    yield

                if failure == "timeout":
                    patches = patch.object(
                        telemetry_writer,
                        "queue_lock",
                        side_effect=timeout_lock,
                    )
                else:
                    patches = patch.object(
                        telemetry_writer,
                        "scan_queue_read_only",
                        side_effect=incomplete_final,
                    )
                with patches:
                    result = telemetry_migrate_command(
                        json_output=True, paths=paths
                    )
                self.assertEqual(
                    (result.exit_code, json.loads(result.output)["outcome"]),
                    (2, "blocked"),
                )

    def test_publication_after_final_snapshot_release_is_outside_fact(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            paths = telemetry_paths(Path(raw) / "telemetry")
            v2 = telemetry_paths_v2(paths.directory)
            _create_v1_store(paths.database_path)
            real_queue_lock = telemetry_writer.queue_lock
            publication: list[telemetry_queue.PublicationResult] = []

            @contextmanager
            def publish_after_release(
                selected: telemetry_queue.TelemetryPaths,
                *args: object,
                **kwargs: object,
            ) -> object:
                with real_queue_lock(selected, *args, **kwargs) as descriptor:
                    yield descriptor
                publication.append(
                    publish_envelope(
                        encode_trace_envelope_v2(_rows()), paths=v2
                    )
                )

            with patch.object(
                telemetry_writer,
                "queue_lock",
                side_effect=publish_after_release,
            ):
                result = telemetry_migrate_command(
                    json_output=True, paths=paths
                )
            facts = json.loads(result.output)
            self.assertEqual(
                (result.exit_code, facts["outcome"], facts["pending_v2"]),
                (0, "migrated", 0),
            )
            self.assertEqual(len(publication), 1)
            self.assertTrue(publication[0].published)
            self.assertEqual(scan_queue_read_only(v2).ready, 1)

    def test_writer_state_publication_no_cleanup_crashes_reconcile(self) -> None:
        phases = ("temporary_durable", "renamed", "directory_synced")
        sentinel = b"PRIVATE_STATE_CRASH_SENTINEL"
        for phase in phases:
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as raw:
                paths = telemetry_paths(Path(raw) / "telemetry")
                _create_v1_store(paths.database_path)

                class InjectedCrash(BaseException):
                    pass

                calls = 0

                def crash(observed: str) -> None:
                    nonlocal calls
                    if observed == phase:
                        calls += 1
                        if calls == 2:
                            raise InjectedCrash(sentinel.decode())

                with patch.object(
                    telemetry_queue,
                    "_writer_state_fault_hook",
                    crash,
                ), self.assertRaises(InjectedCrash):
                    telemetry_writer.telemetry_migrate(paths=paths)
                self.assertEqual(
                    telemetry_store.inspect_store_schema_version(paths), 2
                )
                self.assertTrue(paths.backup_database_path.is_file())
                for item in paths.directory.rglob("*"):
                    if item.is_file() and not item.is_symlink():
                        self.assertNotIn(sentinel, item.read_bytes())
                retried = telemetry_migrate_command(
                    json_output=True, paths=paths
                )
                self.assertEqual(
                    (retried.exit_code, json.loads(retried.output)["outcome"]),
                    (0, "already_current"),
                )
                self.assertFalse(paths.writer_state_temp_path.exists())

        with tempfile.TemporaryDirectory() as raw:
            paths = telemetry_paths(Path(raw) / "telemetry")
            _create_v1_store(paths.database_path)
            calls = 0

            def fail(observed: str) -> None:
                nonlocal calls
                if observed == "temporary_durable":
                    calls += 1
                    if calls == 2:
                        raise OSError("PRIVATE_STATE_FAILURE_SENTINEL")

            with patch.object(
                telemetry_queue,
                "_writer_state_fault_hook",
                fail,
            ):
                blocked = telemetry_migrate_command(
                    json_output=True, paths=paths
                )
            facts = json.loads(blocked.output)
            self.assertEqual((blocked.exit_code, facts["outcome"]), (2, "blocked"))
            self.assertEqual(
                (facts["source_schema_version"], facts["target_schema_version"]),
                (1, 2),
            )
            self.assertTrue(facts["backup_present"])
            self.assertNotIn("PRIVATE_STATE_FAILURE_SENTINEL", blocked.output)
            retried = telemetry_migrate_command(
                json_output=True, paths=paths
            )
            self.assertEqual(
                (retried.exit_code, json.loads(retried.output)["outcome"]),
                (0, "already_current"),
            )


def _replace_trace(rows: CommandTraceRows, digit: str) -> CommandTraceRows:
    trace = digit * 32
    ids = {
        span[1]: digit * 15 + f"{index + 1:x}"
        for index, span in enumerate(rows.spans)
    }
    command = list(rows.command)
    command[0] = trace
    command[1] = ids[rows.command[1]]
    operation = None
    if rows.retrieval_operation is not None:
        changed_operation = list(rows.retrieval_operation)
        changed_operation[0] = trace
        changed_operation[1] = ids[rows.retrieval_operation[1]]
        operation = tuple(changed_operation)
    spans = []
    for span in rows.spans:
        changed = list(span)
        changed[0] = trace
        changed[1] = ids[span[1]]
        changed[2] = None if span[2] is None else ids[span[2]]
        spans.append(tuple(changed))
    events = []
    for event in rows.events:
        changed_event = list(event)
        changed_event[0] = trace
        changed_event[1] = ids[event[1]]
        events.append(tuple(changed_event))
    return CommandTraceRows(tuple(command), operation, tuple(spans), tuple(events))


if __name__ == "__main__":
    unittest.main()
