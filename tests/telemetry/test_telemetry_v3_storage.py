from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import tempfile
from collections.abc import Callable
from typing import Sequence
import unittest
from unittest.mock import patch

import duckdb

from buoy_search.telemetry import producer
from buoy_search.telemetry import store
from buoy_search.telemetry import writer as telemetry_writer
from buoy_search.telemetry.envelope import (
    EVIDENCE_SPAN_NAME,
    NAMESPACE_QUERY_SPAN_NAME,
    QUERY_EMBED_SPAN_NAME,
    RERANK_SPAN_NAME,
    CommandTraceRowsV3,
    command_trace_rows_from_spans_v3,
    encode_trace_envelope_v1,
    encode_trace_envelope_v2,
    encode_trace_envelope_v3,
)
from buoy_search.retrieval import _provider_invocation_receipt as provider_receipt
from buoy_search.telemetry.producer import (
    inference_request,
    retrieval_trace,
    retrieve_command_trace,
    safe_time_ns,
    telemetry_span,
)
from buoy_search.telemetry.queue import (
    TerminalReceipt,
    claim_ready_names,
    publish_envelope,
    publish_terminal_receipt,
    read_terminal_receipt,
    scan_queue_read_only,
    telemetry_paths,
    telemetry_paths_v2,
    telemetry_paths_v3,
)
from buoy_search.telemetry.writer import run_writer, telemetry_flush, telemetry_migrate, telemetry_status
from tests.telemetry.test_telemetry_v2_storage import (
    _create_v1_store,
    _replace_v1_trace,
    _rows,
    _v1_rows,
)

_SAFE_CONFIG = {
    "enable_external_access": "false",
    "autoinstall_known_extensions": "false",
    "autoload_known_extensions": "false",
    "allow_community_extensions": "false",
}


def _expand_valid_v2_store_above_initialization_limit(
    database_path: Path,
) -> None:
    target_size = store.DATABASE_INIT_MAX_BYTES + 4_194_304
    with database_path.open("r+b") as stream:
        stream.truncate(target_size)
        stream.flush()
        os.fsync(stream.fileno())
    with store._connect_database(database_path, read_only=True) as connection:
        store._validate_schema(connection, expected_version=2)
        store._validate_v1_content(connection)
        store._validate_v2_content(connection)


def _preview_v3_rows() -> CommandTraceRowsV3:
    captured: list[tuple[object, ...]] = []

    def capture(
        spans: Sequence[object],
        *,
        root_span_id: int | None,
        schema_version: int,
        provider_accounting: tuple[object, ...] | None,
    ) -> None:
        captured.append((tuple(spans), root_span_id, schema_version, provider_accounting))

    started = safe_time_ns()
    assert started is not None
    with patch.dict(os.environ, {"BUOY_TELEMETRY": "local"}), patch.object(
        producer, "_persist_command_trace_best_effort", side_effect=capture
    ):
        with retrieve_command_trace(
            started_at_ns=started,
            bootstrap_ended_at_ns=started,
            execution_mode="preview",
            retrieval_mode="explicit_single",
            inference_policy="compatibility_in_process",
            _schema_version=3,
        ) as command:
            with command.stage("buoy.retrieve.prepare"):
                pass
            with command.stage("buoy.output.render"):
                pass
            command.finish(0)
    spans, root_span_id, schema_version, accounting = captured[0]
    assert schema_version == 3 and isinstance(root_span_id, int) and isinstance(accounting, tuple)
    return command_trace_rows_from_spans_v3(
        spans,  # type: ignore[arg-type]
        root_span_id=root_span_id,
        provider_accounting=accounting,
    )


def _captured_v3_rows(
    *,
    execution_mode: str,
    retrieval_mode: str,
    inference_policy: str,
    body: Callable[[object], None],
) -> CommandTraceRowsV3:
    captured: list[tuple[object, ...]] = []

    def capture(
        spans: Sequence[object],
        *,
        root_span_id: int | None,
        schema_version: int,
        provider_accounting: tuple[object, ...] | None,
    ) -> None:
        captured.append((tuple(spans), root_span_id, schema_version, provider_accounting))

    started = safe_time_ns()
    assert started is not None
    with patch.dict(os.environ, {"BUOY_TELEMETRY": "local"}), patch.object(
        producer, "_persist_command_trace_best_effort", side_effect=capture
    ):
        with retrieve_command_trace(
            started_at_ns=started,
            bootstrap_ended_at_ns=started,
            execution_mode=execution_mode,  # type: ignore[arg-type]
            retrieval_mode=retrieval_mode,  # type: ignore[arg-type]
            inference_policy=inference_policy,  # type: ignore[arg-type]
            _schema_version=3,
        ) as command:
            body(command)
    spans, root_span_id, schema_version, accounting = captured[0]
    assert schema_version == 3 and isinstance(root_span_id, int)
    assert isinstance(accounting, tuple)
    return command_trace_rows_from_spans_v3(
        spans,  # type: ignore[arg-type]
        root_span_id=root_span_id,
        provider_accounting=accounting,
    )


def _live_v3_rows_with_inference() -> CommandTraceRowsV3:
    captured: list[tuple[object, ...]] = []

    def capture(spans: Sequence[object], *, root_span_id: int | None, schema_version: int, provider_accounting: tuple[object, ...] | None) -> None:
        captured.append((tuple(spans), root_span_id, schema_version, provider_accounting))

    started = safe_time_ns(); assert started is not None
    with patch.dict(os.environ, {"BUOY_TELEMETRY": "local"}), patch.object(producer, "_persist_command_trace_best_effort", side_effect=capture):
        with retrieve_command_trace(
            started_at_ns=started, bootstrap_ended_at_ns=started,
            execution_mode="live", retrieval_mode="explicit_single",
            inference_policy="compatibility_in_process", _schema_version=3,
        ) as command:
            with command.stage("buoy.retrieve.prepare"):
                pass
            with retrieval_trace(
                mode="explicit_single", embedding_model="BAAI/bge-small-en-v1.5",
                embedding_precision="float32", top_k=5, candidates=10,
                namespace_count=1, initial_fanout=1,
            ) as pipeline:
                with telemetry_span("buoy.query.embed") as embed:
                    with inference_request(operation="encode", backend="in_process", role="primary", item_count=1):
                        pass
                    embed.mark_ok()
                with telemetry_span("buoy.namespace.query", {"buoy.route.rank": 1}) as namespace:
                    with provider_receipt._content_operation(1) as operation:
                        operation._invoke("server_rrf", "initial", lambda: object())
                    namespace.set_attributes({"buoy.namespace.status": "ok", "buoy.namespace.hit_count": 1})
                    namespace.mark_ok()
                pipeline.set_attributes({"buoy.retrieval.outcome": "success", "buoy.retrieval.hit_count": 1, "buoy.retrieval.final_fanout": 1})
                pipeline.mark_ok()
            with command.stage("buoy.output.render"):
                pass
            command.finish(0)
    spans, root_span_id, schema_version, accounting = captured[0]
    assert schema_version == 3 and isinstance(root_span_id, int) and isinstance(accounting, tuple)
    return command_trace_rows_from_spans_v3(spans, root_span_id=root_span_id, provider_accounting=accounting)  # type: ignore[arg-type]


def _finish_live_explicit(
    command: object,
    *,
    inference: Callable[[], None] | None = None,
) -> None:
    with command.stage("buoy.retrieve.prepare"):  # type: ignore[attr-defined]
        pass
    with retrieval_trace(
        mode="explicit_single",
        embedding_model="BAAI/bge-small-en-v1.5",
        embedding_precision="float32",
        top_k=5,
        candidates=10,
        namespace_count=1,
        initial_fanout=1,
    ) as pipeline:
        with telemetry_span(QUERY_EMBED_SPAN_NAME) as embed:
            if inference is not None:
                inference()
            embed.mark_ok()
        with telemetry_span(
            NAMESPACE_QUERY_SPAN_NAME, {"buoy.route.rank": 1}
        ) as namespace:
            with provider_receipt._content_operation(1) as operation:
                operation._invoke("server_rrf", "initial", lambda: object())
            namespace.set_attributes(
                {"buoy.namespace.status": "ok", "buoy.namespace.hit_count": 1}
            )
            namespace.mark_ok()
        pipeline.set_attributes(
            {
                "buoy.retrieval.outcome": "success",
                "buoy.retrieval.hit_count": 1,
                "buoy.retrieval.final_fanout": 1,
            }
        )
        pipeline.mark_ok()
    with command.stage("buoy.output.render"):  # type: ignore[attr-defined]
        pass
    command.finish(0)  # type: ignore[attr-defined]


def _finish_automatic(
    command: object,
    *,
    include_content: bool,
) -> None:
    with command.stage("buoy.retrieve.prepare"):  # type: ignore[attr-defined]
        with command.stage("buoy.routing.model"):  # type: ignore[attr-defined]
            pass
        with command.stage("buoy.routing.catalog"):  # type: ignore[attr-defined]
            observer = provider_receipt._active_catalog_observer()
            assert observer is not None
            with observer._operation() as catalog:
                catalog._invoke("namespace_list_page", lambda: object())
                catalog._invoke("metadata", lambda: object())
                catalog._invoke("card_query_page", lambda: object())
                catalog._invoke("card_query_page", lambda: object())
                catalog._invoke("namespace_list_page", lambda: object())
        with command.stage("buoy.routing.model"):  # type: ignore[attr-defined]
            pass
        with command.stage("buoy.routing.select"):  # type: ignore[attr-defined]
            pass
    if include_content:
        with retrieval_trace(
            mode="automatic",
            embedding_model="BAAI/bge-small-en-v1.5",
            embedding_precision="float32",
            top_k=5,
            candidates=10,
            namespace_count=2,
            initial_fanout=1,
        ) as pipeline:
            with telemetry_span(QUERY_EMBED_SPAN_NAME) as embed:
                embed.mark_ok()
            with telemetry_span(
                NAMESPACE_QUERY_SPAN_NAME, {"buoy.route.rank": 1}
            ) as namespace:
                with provider_receipt._content_operation(1) as operation:
                    operation._invoke("server_rrf", "initial", lambda: object())
                namespace.set_attributes(
                    {"buoy.namespace.status": "ok", "buoy.namespace.hit_count": 1}
                )
                namespace.mark_ok()
            with telemetry_span(EVIDENCE_SPAN_NAME) as evidence:
                evidence.set_attributes(
                    {
                        "buoy.evidence.mode": "active",
                        "buoy.evidence.status": "supported",
                        "buoy.evidence.candidates_scored": 1,
                        "buoy.evidence.top_score": 1.0,
                        "buoy.evidence.second_score": 0.0,
                        "buoy.evidence.score_gap": 1.0,
                    }
                )
                evidence.mark_ok()
            with telemetry_span(RERANK_SPAN_NAME) as rerank:
                rerank.set_attributes(
                    {
                        "buoy.rerank.applied": True,
                        "buoy.rerank.candidates_before_dedupe": 1,
                        "buoy.rerank.candidates_after_dedupe": 1,
                        "buoy.reranker.model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
                        "buoy.reranker.revision": "a" * 40,
                    }
                )
                rerank.mark_ok()
            pipeline.set_attributes(
                {
                    "buoy.retrieval.outcome": "success",
                    "buoy.retrieval.hit_count": 1,
                    "buoy.retrieval.final_fanout": 1,
                    "buoy.evidence.status": "supported",
                }
            )
            pipeline.mark_ok()
    with command.stage("buoy.output.render"):  # type: ignore[attr-defined]
        pass
    command.finish(0)  # type: ignore[attr-defined]


class TelemetryV3StorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "telemetry"
        self.v1 = telemetry_paths(self.root)
        self.v2 = telemetry_paths_v2(self.root)
        self.v3 = telemetry_paths_v3(self.root)

    def test_shared_capacity_counts_all_three_inboxes(self) -> None:
        from buoy_search.telemetry import queue as telemetry_queue
        with patch.object(telemetry_queue, "PUBLISHED_MAX_ENTRIES", 2):
            self.assertTrue(publish_envelope(b"{}", paths=self.v1).published)
            self.assertTrue(publish_envelope(b"{}", paths=self.v2).published)
            blocked = publish_envelope(b"{}", paths=self.v3)
        self.assertFalse(blocked.published)
        self.assertEqual(blocked.reason, "queue_full")
        self.assertEqual(scan_queue_read_only(self.v3).ready, 0)

    def test_default_command_publication_switches_atomically_to_v3(self) -> None:
        payloads: list[bytes] = []
        published_paths: list[object] = []

        def publish(payload: bytes, *, paths: object) -> object:
            payloads.append(payload)
            published_paths.append(paths)
            from buoy_search.telemetry.queue import PublicationResult
            return PublicationResult(True, "v3-" + "0" * 32 + ".json", "published")

        started = safe_time_ns()
        assert started is not None
        with patch.dict(os.environ, {"BUOY_TELEMETRY": "local"}), patch.object(
            producer, "publish_envelope", side_effect=publish
        ), patch.object(producer, "request_writer_start") as writer_start:
            with retrieve_command_trace(
                started_at_ns=started,
                bootstrap_ended_at_ns=started,
                execution_mode="preview",
                retrieval_mode="explicit_single",
                inference_policy="compatibility_in_process",
            ) as command:
                with command.stage("buoy.retrieve.prepare"):
                    pass
                with command.stage("buoy.output.render"):
                    pass
                command.finish(0)
        self.assertEqual(len(payloads), 1)
        value = json.loads(payloads[0])
        self.assertEqual((value["envelope_schema_version"], value["observation_schema_version"]), (3, 3))
        self.assertEqual(value["provider_accounting"]["status"], "complete")
        self.assertEqual(getattr(published_paths[0], "queue_version"), 3)
        writer_start.assert_called_once()

    def test_v3_has_distinct_paths_names_and_aggregate_status(self) -> None:
        self.assertEqual(self.v3.queue_version, 3)
        self.assertEqual(self.v3.inbox_directory.name, "inbox-v3")
        self.assertEqual(self.v3.migration_directory.name, "database-migrate-v3")
        self.assertEqual(self.v3.backup_database_path.name, "telemetry-v2-backup.duckdb")
        publication = publish_envelope(encode_trace_envelope_v3(_preview_v3_rows()), paths=self.v3)
        self.assertTrue(publication.published)
        assert publication.source_name is not None
        self.assertTrue(publication.source_name.startswith("v3-"))
        status = telemetry_status(paths=self.v1, environment={})
        self.assertEqual(status["schema_version"], 3)
        self.assertEqual(status["queue"]["v3_ready"], 1)  # type: ignore[index]
        self.assertEqual(status["queue"]["v1_ready"], 0)  # type: ignore[index]
        self.assertEqual(status["queue"]["v2_ready"], 0)  # type: ignore[index]

    def test_status_reconciles_each_unaccounted_v3_terminal_receipt(self) -> None:
        payload = encode_trace_envelope_v3(_preview_v3_rows())
        for kind, reason, counter in (
            ("rejected", "invalid_value", "rejected"),
            ("conflict", "trace_conflict", "conflicts"),
            ("replayed", None, "replays"),
        ):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as raw:
                paths = telemetry_paths_v3(Path(raw) / "telemetry")
                publication = publish_envelope(payload, paths=paths)
                assert publication.source_name is not None
                self.assertEqual(
                    claim_ready_names(paths, (publication.source_name,)),
                    (publication.source_name,),
                )
                publish_terminal_receipt(
                    paths,
                    TerminalReceipt(
                        schema_version=3,
                        kind=kind,  # type: ignore[arg-type]
                        source_name=publication.source_name,
                        envelope_sha256=hashlib.sha256(payload).hexdigest(),
                        digest_complete=True,
                        envelope_bytes=len(payload),
                        recorded_at_unix_ms=1,
                        reason=reason,
                    ),
                )
                facts = telemetry_status(
                    paths=telemetry_paths(paths.directory), environment={}
                )
                self.assertEqual(facts["accounting"][counter], 1)  # type: ignore[index]
                self.assertFalse(facts["accounting"]["incomplete"])  # type: ignore[index]

    def test_status_marks_malformed_unaccounted_v3_receipt_incomplete(self) -> None:
        publication = publish_envelope(
            encode_trace_envelope_v3(_preview_v3_rows()), paths=self.v3
        )
        assert publication.source_name is not None
        self.v3.receipts_directory.mkdir(mode=0o700, exist_ok=True)
        receipt_name = "r3-" + publication.source_name[3:]
        (self.v3.receipts_directory / receipt_name).write_bytes(b"{}")
        (self.v3.receipts_directory / receipt_name).chmod(0o600)
        facts = telemetry_status(paths=self.v1, environment={})
        self.assertTrue(facts["accounting"]["incomplete"])  # type: ignore[index]
        self.assertEqual(facts["overall"], "blocked")

    def test_fresh_v3_store_normalizes_atomic_rows_and_truthful_null_catalog(self) -> None:
        rows = _preview_v3_rows()
        result = store.append_trace(self.v3, rows)
        self.assertEqual((result.outcome, result.snapshot.schema_version), ("committed", 3))
        with duckdb.connect(str(self.v3.database_path), read_only=True, config=_SAFE_CONFIG) as connection:
            self.assertEqual(store._validate_schema(connection), 3)
            self.assertEqual(connection.execute("SELECT status,unit FROM retrieve_provider_accounting_v3").fetchone(), ("complete", "provider_client_invocation"))
            catalog = connection.execute("SELECT outcome,invocation_count FROM retrieve_provider_catalog_v3").fetchone()
            self.assertEqual(catalog, (None, 0))
            summary = connection.execute("SELECT content_invocation_count,catalog_outcome,catalog_invocation_count FROM retrieval_provider_summary_v3").fetchone()
            self.assertEqual(summary, (0, None, 0))
            command = connection.execute("SELECT observation_schema_version,inference_policy FROM retrieve_command_runs_v3").fetchone()
            self.assertEqual(command, (3, "compatibility_in_process"))
            self.assertEqual(connection.execute("SELECT count(*) FROM retrieve_command_runs").fetchone(), (0,))
        self.assertEqual(store.inspect_trace_terminal(self.v3, rows).outcome, "replayed")

    def test_inference_and_provider_rows_drive_stable_aggregates(self) -> None:
        rows = _live_v3_rows_with_inference()
        store.append_trace(self.v3, rows)
        with duckdb.connect(str(self.v3.database_path), read_only=True, config=_SAFE_CONFIG) as connection:
            inference = connection.execute(
                "SELECT operation,backend,role,item_count,worker_state,outcome,error_type FROM retrieval_inference_requests_v3"
            ).fetchone()
            self.assertEqual(inference, ("encode", "in_process", "primary", 1, None, "success", None))
            command = connection.execute(
                "SELECT in_process_encode_requests,worker_encode_requests,fallback_requests FROM retrieval_command_runs_v3"
            ).fetchone()
            self.assertEqual(command, (1, 0, 0))
            provider = connection.execute(
                "SELECT content_logical_operation_count,content_invocation_count,server_rrf_count FROM retrieval_provider_summary_v3"
            ).fetchone()
            self.assertEqual(provider, (1, 1, 1))

    def test_exact_ordered_v3_views_cover_required_command_shapes(self) -> None:
        def preview(command: object) -> None:
            with command.stage("buoy.retrieve.prepare"):  # type: ignore[attr-defined]
                pass
            with command.stage("buoy.output.render"):  # type: ignore[attr-defined]
                pass
            command.finish(0)  # type: ignore[attr-defined]

        def pre_pipeline_failure(command: object) -> None:
            try:
                with command.stage("buoy.retrieve.prepare"):  # type: ignore[attr-defined]
                    raise RuntimeError("private pre-pipeline detail")
            except RuntimeError:
                pass
            command.finish(1, error_type="model_error")  # type: ignore[attr-defined]

        def live_failure(command: object) -> None:
            with command.stage("buoy.retrieve.prepare"):  # type: ignore[attr-defined]
                pass
            try:
                with retrieval_trace(
                    mode="explicit_single",
                    embedding_model="BAAI/bge-small-en-v1.5",
                    embedding_precision="float32",
                    top_k=5,
                    candidates=10,
                    namespace_count=1,
                    initial_fanout=1,
                ):
                    with telemetry_span(QUERY_EMBED_SPAN_NAME) as embed:
                        embed.mark_ok()
                    raise RuntimeError("private pipeline detail")
            except RuntimeError:
                pass
            with command.stage("buoy.output.render"):  # type: ignore[attr-defined]
                pass
            command.finish(2, error_type="provider_error")  # type: ignore[attr-defined]

        def worker_lifecycle() -> None:
            with inference_request(
                operation="encode",
                backend="worker",
                role="primary",
                item_count=1,
            ) as request:
                request.observe_worker_state("spawned")
            with inference_request(
                operation="encode",
                backend="worker",
                role="primary",
                item_count=1,
            ) as request:
                request.observe_worker_state("reused")

        def worker_fallback() -> None:
            try:
                with inference_request(
                    operation="encode",
                    backend="worker",
                    role="primary",
                    item_count=1,
                ) as request:
                    request.observe_worker_state("reused")
                    raise RuntimeError("private worker detail")
            except RuntimeError:
                pass
            with inference_request(
                operation="encode",
                backend="in_process",
                role="fallback",
                item_count=1,
            ):
                pass

        cases = {
            "preview": _captured_v3_rows(
                execution_mode="preview",
                retrieval_mode="explicit_single",
                inference_policy="compatibility_in_process",
                body=preview,
            ),
            "pre_pipeline_failure": _captured_v3_rows(
                execution_mode="live",
                retrieval_mode="explicit_single",
                inference_policy="compatibility_in_process",
                body=pre_pipeline_failure,
            ),
            "live_success": _captured_v3_rows(
                execution_mode="live",
                retrieval_mode="explicit_single",
                inference_policy="compatibility_in_process",
                body=lambda command: _finish_live_explicit(command),
            ),
            "live_failure": _captured_v3_rows(
                execution_mode="live",
                retrieval_mode="explicit_single",
                inference_policy="compatibility_in_process",
                body=live_failure,
            ),
            "worker_spawn_reuse": _captured_v3_rows(
                execution_mode="live",
                retrieval_mode="explicit_single",
                inference_policy="worker_preferred",
                body=lambda command: _finish_live_explicit(
                    command, inference=worker_lifecycle
                ),
            ),
            "fallback": _captured_v3_rows(
                execution_mode="live",
                retrieval_mode="explicit_single",
                inference_policy="worker_preferred",
                body=lambda command: _finish_live_explicit(
                    command, inference=worker_fallback
                ),
            ),
            "catalog_only": _captured_v3_rows(
                execution_mode="preview",
                retrieval_mode="automatic",
                inference_policy="compatibility_in_process",
                body=lambda command: _finish_automatic(
                    command, include_content=False
                ),
            ),
            "content_only": _live_v3_rows_with_inference(),
            "automatic_combined": _captured_v3_rows(
                execution_mode="live",
                retrieval_mode="automatic",
                inference_policy="compatibility_in_process",
                body=lambda command: _finish_automatic(
                    command, include_content=True
                ),
            ),
        }
        for rows in cases.values():
            self.assertEqual(store.append_trace(self.v3, rows).outcome, "committed")

        expected = {
            "preview": ("preview", "explicit_single", "success", False, 0, 0, 0, 0, 0, None, 0),
            "pre_pipeline_failure": ("live", "explicit_single", "error", False, 0, 0, 0, 0, 0, None, 0),
            "live_success": ("live", "explicit_single", "success", True, 0, 0, 0, 1, 1, None, 0),
            "live_failure": ("live", "explicit_single", "error", True, 0, 0, 0, 0, 0, None, 0),
            "worker_spawn_reuse": ("live", "explicit_single", "success", True, 2, 1, 1, 1, 1, None, 0),
            "fallback": ("live", "explicit_single", "success", True, 1, 0, 1, 1, 1, None, 0),
            "catalog_only": ("preview", "automatic", "success", False, 0, 0, 0, 0, 0, "success", 5),
            "content_only": ("live", "explicit_single", "success", True, 0, 0, 0, 1, 1, None, 0),
            "automatic_combined": ("live", "automatic", "success", True, 0, 0, 0, 1, 1, "success", 5),
        }
        with duckdb.connect(
            str(self.v3.database_path), read_only=True, config=_SAFE_CONFIG
        ) as connection:
            for view_name in store._V3_VIEW_LAYOUTS:
                if not view_name.endswith("_v3"):
                    continue
                columns = tuple(
                    item[0]
                    for item in connection.execute(
                        f"SELECT * FROM {view_name} LIMIT 0"
                    ).description
                )
                self.assertEqual(
                    columns,
                    tuple(name for name, _kind in store._V3_VIEW_LAYOUTS[view_name]),
                )
            for case_name, rows in cases.items():
                trace_id = str(rows.command[0])
                command_values = connection.execute(
                    """SELECT execution_mode,retrieval_mode,command_outcome,
                              pipeline_span_id IS NOT NULL,
                              worker_encode_requests,worker_spawned_requests,
                              worker_reused_requests
                       FROM retrieval_command_runs_v3 WHERE trace_id=?""",
                    (trace_id,),
                ).fetchone()
                provider_values = connection.execute(
                    """SELECT content_logical_operation_count,
                              content_invocation_count,catalog_outcome,
                              catalog_invocation_count
                       FROM retrieval_provider_summary_v3 WHERE trace_id=?""",
                    (trace_id,),
                ).fetchone()
                assert command_values is not None and provider_values is not None
                observed = (*command_values, *provider_values)
                self.assertEqual(observed, expected[case_name], case_name)
                inference_rows = connection.execute(
                    """SELECT operation,backend,role,worker_state,outcome,error_type
                       FROM retrieval_inference_requests_v3 WHERE trace_id=?
                       ORDER BY started_at,span_id""",
                    (trace_id,),
                ).fetchall()
                if case_name == "worker_spawn_reuse":
                    self.assertEqual(
                        [row[3] for row in inference_rows], ["spawned", "reused"]
                    )
                if case_name == "fallback":
                    self.assertEqual(
                        [(row[1], row[2], row[4]) for row in inference_rows],
                        [
                            ("worker", "primary", "error"),
                            ("in_process", "fallback", "success"),
                        ],
                    )
                invocation_rows = connection.execute(
                    """SELECT route_rank,attempt_index,request_form,trigger,outcome,error_category
                       FROM retrieval_provider_content_invocations_v3
                       WHERE trace_id=? ORDER BY route_rank,attempt_index""",
                    (trace_id,),
                ).fetchall()
                self.assertEqual(
                    len(invocation_rows),
                    1 if case_name in {"live_success", "worker_spawn_reuse", "fallback", "content_only", "automatic_combined"} else 0,
                    case_name,
                )

    def test_unavailable_provider_accounting_has_only_status_row(self) -> None:
        from dataclasses import replace
        original = _preview_v3_rows()
        rows = replace(
            original,
            provider_accounting=("unavailable", "provider_client_invocation", None, None),
        )
        store.append_trace(self.v3, rows)
        with duckdb.connect(str(self.v3.database_path), read_only=True, config=_SAFE_CONFIG) as connection:
            self.assertEqual(connection.execute("SELECT status FROM retrieve_provider_accounting_v3").fetchone(), ("unavailable",))
            self.assertEqual(connection.execute("SELECT count(*) FROM retrieve_provider_catalog_v3").fetchone(), (0,))
            summary = connection.execute("SELECT content_invocation_count,catalog_outcome FROM retrieval_provider_summary_v3").fetchone()
            self.assertEqual(summary, (None, None))

    def test_writer_drains_all_three_inboxes_into_one_v3_store(self) -> None:
        self.assertTrue(publish_envelope(encode_trace_envelope_v1(_v1_rows()), paths=self.v1).published)
        self.assertTrue(publish_envelope(encode_trace_envelope_v2(_rows()), paths=self.v2).published)
        self.assertTrue(publish_envelope(encode_trace_envelope_v3(_preview_v3_rows()), paths=self.v3).published)
        with patch("buoy_search.telemetry.writer.IDLE_EXIT_SECONDS", 0):
            self.assertEqual(run_writer(self.v1), 0)
        for paths in (self.v1, self.v2, self.v3):
            snapshot = scan_queue_read_only(paths)
            self.assertEqual((snapshot.ready, snapshot.claimed, snapshot.receipts), (0, 0, 1))
        with duckdb.connect(str(self.v1.database_path), read_only=True, config=_SAFE_CONFIG) as connection:
            self.assertEqual(store._validate_schema(connection), 3)
            self.assertEqual(connection.execute("SELECT count(*) FROM trace_runs").fetchone(), (1,))
            self.assertEqual(connection.execute("SELECT count(*) FROM retrieve_command_runs").fetchone(), (1,))
            self.assertEqual(connection.execute("SELECT count(*) FROM retrieve_command_runs_v3").fetchone(), (1,))

    def test_exact_v2_to_v3_migration_preserves_history_views_and_both_backups(self) -> None:
        self.root.mkdir(mode=0o700)
        _create_v1_store(self.v1.database_path)
        store.migrate_store_v1_to_v2(self.v1)
        store.append_trace(self.v2, _rows())
        with duckdb.connect(str(self.v2.database_path), read_only=True, config=_SAFE_CONFIG) as before:
            old_v1 = before.execute("SELECT * FROM retrieval_runs_v1 ORDER BY trace_id").fetchall()
            old_v2 = before.execute("SELECT * FROM retrieval_command_runs_v2 ORDER BY trace_id").fetchall()
            old_digests = store._view_sql_digests(before, version=2)
        migrated = store.migrate_store_v2_to_v3(self.v3)
        self.assertTrue(migrated.backup_present)
        self.assertTrue(self.v1.backup_database_path.is_file())
        self.assertTrue(self.v3.backup_database_path.is_file())
        with duckdb.connect(str(self.v3.database_path), read_only=True, config=_SAFE_CONFIG) as after:
            self.assertEqual(store._validate_schema(after), 3)
            self.assertEqual(after.execute("SELECT * FROM retrieval_runs_v1 ORDER BY trace_id").fetchall(), old_v1)
            self.assertEqual(after.execute("SELECT * FROM retrieval_command_runs_v2 ORDER BY trace_id").fetchall(), old_v2)
            self.assertEqual({name: store._view_sql_digests(after, version=3)[name] for name in old_digests}, old_digests)
        facts = telemetry_migrate(paths=self.v1)
        self.assertEqual(facts["outcome"], "already_current")
        self.assertEqual((facts["source_schema_version"], facts["target_schema_version"]), (3, 3))

    def test_v3_pending_behind_v2_is_blocked_without_mutation(self) -> None:
        self.root.mkdir(mode=0o700)
        _create_v1_store(self.v1.database_path)
        first = telemetry_migrate(paths=self.v1)
        self.assertEqual((first["source_schema_version"], first["target_schema_version"]), (1, 2))
        before = self.v1.database_path.read_bytes()
        publication = publish_envelope(encode_trace_envelope_v3(_preview_v3_rows()), paths=self.v3)
        self.assertTrue(publication.published)
        status = telemetry_status(paths=self.v1, environment={})
        self.assertEqual(status["store"]["state"], "upgrade_required")  # type: ignore[index]
        self.assertEqual(status["overall"], "blocked")
        self.assertEqual(telemetry_flush(timeout=0, paths=self.v1)["outcome"], "blocked")
        self.assertEqual(self.v1.database_path.read_bytes(), before)
        self.assertEqual(scan_queue_read_only(self.v3).ready, 1)

    def test_global_cross_version_trace_conflict_never_partially_inserts(self) -> None:
        from dataclasses import replace
        legacy = _rows()
        self.assertEqual(store.append_trace(self.v3, legacy).outcome, "committed")
        candidate = _preview_v3_rows()
        trace_id = str(legacy.command[0])
        conflicting = replace(
            candidate,
            command=(trace_id, *candidate.command[1:]),
            retrieval_operation=(
                None if candidate.retrieval_operation is None
                else (trace_id, *candidate.retrieval_operation[1:])
            ),
            spans=tuple((trace_id, *span[1:]) for span in candidate.spans),
            events=tuple((trace_id, *event[1:]) for event in candidate.events),
        )
        self.assertEqual(store.append_trace(self.v3, conflicting).outcome, "conflict")
        with duckdb.connect(str(self.v3.database_path), read_only=True, config=_SAFE_CONFIG) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM retrieve_command_runs").fetchone(), (1,))
            self.assertEqual(connection.execute("SELECT count(*) FROM retrieve_command_runs_v3").fetchone(), (0,))
            self.assertEqual(connection.execute("SELECT count(*) FROM retrieve_provider_accounting_v3").fetchone(), (0,))

    def test_v2_to_v3_accepts_immutable_v1_backup_as_history_subset(self) -> None:
        self.root.mkdir(mode=0o700)
        _create_v1_store(self.v1.database_path)
        first = _v1_rows()
        store.append_trace(self.v1, first)
        store.migrate_store_v1_to_v2(self.v1)
        backup = self.v1.backup_database_path.read_bytes()
        later = _replace_v1_trace(first, 42)
        self.assertEqual(store.append_trace(self.v2, later).outcome, "committed")
        store.migrate_store_v2_to_v3(self.v3)
        self.assertEqual(self.v1.backup_database_path.read_bytes(), backup)
        with duckdb.connect(
            str(self.v3.database_path), read_only=True, config=_SAFE_CONFIG
        ) as connection:
            self.assertEqual(
                connection.execute("SELECT count(*) FROM trace_runs").fetchone(),
                (2,),
            )

    def test_backup_published_retry_finishes_v3_before_late_v1_v2_drain(self) -> None:
        self.root.mkdir(mode=0o700)
        _create_v1_store(self.v1.database_path)
        store.migrate_store_v1_to_v2(self.v1)

        class Crash(BaseException):
            pass

        with self.assertRaises(Crash):
            store.migrate_store_v2_to_v3(
                self.v3,
                fault_hook=lambda phase: (_ for _ in ()).throw(Crash())
                if phase == "backup_published"
                else None,
            )
        self.assertEqual(store.inspect_store_schema_version(self.v3), 2)
        self.assertTrue(self.v3.backup_database_path.is_file())
        self.assertTrue(
            publish_envelope(
                encode_trace_envelope_v1(_v1_rows()), paths=self.v1
            ).published
        )
        self.assertTrue(
            publish_envelope(encode_trace_envelope_v2(_rows()), paths=self.v2).published
        )

        migrated = telemetry_migrate(paths=self.v1)
        self.assertEqual(
            (migrated["source_schema_version"], migrated["target_schema_version"]),
            (2, 3),
        )
        self.assertEqual(scan_queue_read_only(self.v1).ready, 1)
        self.assertEqual(scan_queue_read_only(self.v2).ready, 1)
        with duckdb.connect(
            str(self.v3.database_path), read_only=True, config=_SAFE_CONFIG
        ) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM trace_runs").fetchone(), (0,))
            self.assertEqual(connection.execute("SELECT count(*) FROM retrieve_command_runs").fetchone(), (0,))

        def start_writer(**_kwargs: object) -> None:
            with patch.object(telemetry_writer, "IDLE_EXIT_SECONDS", 0):
                run_writer(self.v1)

        with patch.object(
            telemetry_writer, "request_writer_start", side_effect=start_writer
        ):
            flushed = telemetry_flush(timeout=5, paths=self.v1)
        self.assertEqual(flushed["outcome"], "flushed")
        with duckdb.connect(
            str(self.v3.database_path), read_only=True, config=_SAFE_CONFIG
        ) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM trace_runs").fetchone(), (1,))
            self.assertEqual(connection.execute("SELECT count(*) FROM retrieve_command_runs").fetchone(), (1,))

    def test_v2_to_v3_blocks_on_nonterminal_drain_then_recovers_once(self) -> None:
        for fault in ("receipt_publication", "acknowledgement"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as raw:
                v1 = telemetry_paths(Path(raw) / "telemetry")
                v2 = telemetry_paths_v2(v1.directory)
                v3 = telemetry_paths_v3(v1.directory)
                v1.directory.mkdir(mode=0o700)
                _create_v1_store(v1.database_path)
                store.migrate_store_v1_to_v2(v1)
                payload = encode_trace_envelope_v2(_rows())
                publication = publish_envelope(payload, paths=v2)
                assert publication.source_name is not None
                target = (
                    "publish_terminal_receipt"
                    if fault == "receipt_publication"
                    else "acknowledge_claim"
                )
                fault_kwargs = (
                    {
                        "side_effect": telemetry_writer.TelemetryQueueError(
                            "injected terminal drain failure"
                        )
                    }
                    if fault == "receipt_publication"
                    else {"return_value": False}
                )
                with patch.object(telemetry_writer, target, **fault_kwargs):
                    blocked = telemetry_migrate(paths=v1)

                self.assertEqual(blocked["outcome"], "blocked")
                self.assertEqual(store.inspect_store_schema_version(v3), 2)
                blocked_queue = scan_queue_read_only(v2)
                self.assertEqual(
                    (blocked_queue.ready, blocked_queue.claimed), (0, 1)
                )
                with duckdb.connect(
                    str(v1.database_path), read_only=True, config=_SAFE_CONFIG
                ) as connection:
                    self.assertEqual(
                        connection.execute(
                            "SELECT count(*) FROM retrieve_command_runs"
                        ).fetchone(),
                        (1,),
                    )
                    self.assertEqual(
                        connection.execute(
                            "SELECT count(*) FROM system.duckdb_tables() "
                            "WHERE table_name='retrieve_command_runs_v3'"
                        ).fetchone(),
                        (0,),
                    )

                migrated = telemetry_migrate(paths=v1)
                self.assertEqual(migrated["outcome"], "migrated")
                self.assertEqual(store.inspect_store_schema_version(v3), 3)
                final_queue = scan_queue_read_only(v2)
                self.assertEqual(
                    (final_queue.ready, final_queue.claimed, final_queue.receipts),
                    (0, 0, 1),
                )
                receipt = read_terminal_receipt(
                    publication.source_name, paths=v2
                )
                assert receipt is not None
                self.assertEqual(
                    receipt.kind,
                    "replayed" if fault == "receipt_publication" else "committed",
                )
                with duckdb.connect(
                    str(v1.database_path), read_only=True, config=_SAFE_CONFIG
                ) as connection:
                    self.assertEqual(
                        connection.execute(
                            "SELECT count(*) FROM retrieve_command_runs"
                        ).fetchone(),
                        (1,),
                    )
                    self.assertEqual(
                        connection.execute(
                            "SELECT count(*) FROM retrieve_command_runs_v3"
                        ).fetchone(),
                        (0,),
                    )
                status = telemetry_status(paths=v1, environment={})
                self.assertEqual(status["accounting"]["conflicts"], 0)  # type: ignore[index]
                self.assertEqual(
                    status["accounting"]["replays"],  # type: ignore[index]
                    1 if fault == "receipt_publication" else 0,
                )
                self.assertFalse(status["accounting"]["incomplete"])  # type: ignore[index]

    def test_hostile_v3_normalized_cardinality_is_rejected_before_materialization(self) -> None:
        rows = _live_v3_rows_with_inference()
        store.append_trace(self.v3, rows)
        with duckdb.connect(str(self.v3.database_path), config=_SAFE_CONFIG) as connection:
            original = connection.execute(
                "SELECT * FROM retrieve_inference_requests_v3 LIMIT 1"
            ).fetchone()
            assert original is not None
            additions = []
            for number in range(1, 257):
                values = list(original)
                values[1] = f"{number:016x}"
                additions.append(tuple(values))
            connection.executemany(
                "INSERT INTO retrieve_inference_requests_v3 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                additions,
            )
        with patch.object(
            store,
            "_read_trace_graph",
            side_effect=AssertionError("hostile rows were materialized"),
        ) as read_graph, self.assertRaises(store.TelemetryStoreError):
            store.reconcile_already_current_store_v3(self.v3)
        read_graph.assert_not_called()

    def test_normalized_materialization_uses_exact_inference_provider_limits(self) -> None:
        store.append_trace(self.v3, _live_v3_rows_with_inference())
        observed: list[tuple[str, int]] = []
        real_fetch = store._fetch_limited

        def capture_limit(
            connection: duckdb.DuckDBPyConnection,
            statement: str,
            parameters: tuple[object, ...],
            *,
            maximum: int,
        ) -> tuple[tuple[object, ...], ...]:
            observed.append((statement, maximum))
            return real_fetch(
                connection, statement, parameters, maximum=maximum
            )

        with patch.object(store, "_fetch_limited", side_effect=capture_limit):
            store.reconcile_already_current_store_v3(self.v3)
        expected = {
            "retrieve_inference_requests_v3": 256,
            "retrieve_provider_accounting_v3": 1,
            "retrieve_provider_content_operations_v3": 3,
            "retrieve_provider_content_invocations_v3": 18,
            "retrieve_provider_catalog_v3": 1,
        }
        for table_name, maximum in expected.items():
            self.assertTrue(
                any(table_name in statement and limit == maximum for statement, limit in observed),
                (table_name, observed),
            )
        self.assertTrue(
            any(
                "retrieve_provider_content_invocations_v3" in statement
                and limit == 6
                for statement, limit in observed
            )
        )

    def test_valid_migration_v3_candidates_above_initialization_limit_retry(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw) / "base"
            base_paths = telemetry_paths(base)
            base_paths.directory.mkdir(mode=0o700)
            _create_v1_store(base_paths.database_path)
            store.migrate_store_v1_to_v2(base_paths)
            _expand_valid_v2_store_above_initialization_limit(
                base_paths.database_path
            )
            self.assertGreater(
                base_paths.database_path.stat().st_size,
                store.DATABASE_INIT_MAX_BYTES,
            )

            class Crash(BaseException):
                pass

            for phase in ("scratch_validated", "backup_published"):
                with self.subTest(phase=phase):
                    root = Path(raw) / phase
                    shutil.copytree(base, root)
                    v1 = telemetry_paths(root)
                    v3 = telemetry_paths_v3(root)
                    with self.assertRaises(Crash):
                        store.migrate_store_v2_to_v3(
                            v3,
                            fault_hook=lambda observed, selected=phase: (
                                (_ for _ in ()).throw(Crash())
                                if observed == selected
                                else None
                            ),
                        )
                    self.assertEqual(store.inspect_store_schema_version(v3), 2)
                    self.assertNotEqual(
                        telemetry_status(paths=v1, environment={})["store"]["state"],  # type: ignore[index]
                        "unsafe",
                    )
                    self.assertGreater(
                        v3.migration_database_path.stat().st_size,
                        store.DATABASE_INIT_MAX_BYTES,
                    )
                    if phase == "scratch_validated":
                        self.assertGreater(
                            v3.migration_backup_candidate_path.stat().st_size,
                            store.DATABASE_INIT_MAX_BYTES,
                        )
                        store.migrate_store_v2_to_v3(v3)
                    else:
                        self.assertGreater(
                            v3.backup_database_path.stat().st_size,
                            store.DATABASE_INIT_MAX_BYTES,
                        )
                        self.assertEqual(
                            telemetry_migrate(paths=v1)["outcome"], "migrated"
                        )
                    self.assertEqual(store.inspect_store_schema_version(v3), 3)
                    self.assertGreater(
                        v3.backup_database_path.stat().st_size,
                        store.DATABASE_INIT_MAX_BYTES,
                    )
                    with duckdb.connect(
                        str(v3.database_path),
                        read_only=True,
                        config=_SAFE_CONFIG,
                    ) as connection:
                        self.assertEqual(store._validate_schema(connection), 3)
                        self.assertEqual(
                            connection.execute(
                                "SELECT count(*) FROM retrieve_command_runs"
                            ).fetchone(),
                            (0,),
                        )

    def test_oversized_migration_v3_wal_blocks_without_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            v1 = telemetry_paths(Path(raw) / "telemetry")
            v3 = telemetry_paths_v3(v1.directory)
            v1.directory.mkdir(mode=0o700)
            _create_v1_store(v1.database_path)
            store.migrate_store_v1_to_v2(v1)
            v3.migration_directory.mkdir(mode=0o700)
            hostile = v3.migration_wal_path
            with hostile.open("wb") as stream:
                stream.truncate(telemetry_writer.DATABASE_WAL_MAX_BYTES + 1)
            hostile.chmod(0o600)
            status = telemetry_status(paths=v1, environment={})
            self.assertEqual(status["store"]["state"], "unsafe")  # type: ignore[index]
            self.assertEqual(telemetry_migrate(paths=v1)["outcome"], "blocked")
            self.assertTrue(hostile.is_file())
            self.assertEqual(
                hostile.stat().st_size,
                telemetry_writer.DATABASE_WAL_MAX_BYTES + 1,
            )

    def test_v3_migration_artifacts_and_management_are_private_and_network_free(self) -> None:
        sentinels = (
            b"PRIVATE_QUERY_V3_SENTINEL",
            b"PRIVATE_NAMESPACE_V3_SENTINEL",
            b"PRIVATE_CREDENTIAL_V3_SENTINEL",
            b"PRIVATE_PATH_V3_SENTINEL",
            b"PRIVATE_ERROR_V3_SENTINEL",
        )
        self.root.mkdir(mode=0o700)
        _create_v1_store(self.v1.database_path)
        store.append_trace(self.v1, _v1_rows())
        store.migrate_store_v1_to_v2(self.v1)
        store.append_trace(self.v2, _rows())
        captured: list[bytes] = []

        class Crash(BaseException):
            pass

        def capture_after_backup(phase: str) -> None:
            if phase != "backup_published":
                return
            for path in self.root.rglob("*"):
                if path.is_file():
                    captured.append(path.read_bytes())
            raise Crash

        with patch.dict(
            os.environ,
            {
                "PRIVATE_QUERY": sentinels[0].decode(),
                "PRIVATE_NAMESPACE": sentinels[1].decode(),
                "TURBOPUFFER_API_KEY": sentinels[2].decode(),
                "PRIVATE_PATH": sentinels[3].decode(),
                "PRIVATE_ERROR": sentinels[4].decode(),
            },
            clear=True,
        ), self.assertRaises(Crash):
            store.migrate_store_v2_to_v3(
                self.v3, fault_hook=capture_after_backup
            )
        self.assertTrue(self.v3.backup_database_path.is_file())
        self.assertTrue(self.v3.migration_directory.is_dir())

        def network_forbidden(*_args: object, **_kwargs: object) -> object:
            raise AssertionError("telemetry management attempted network access")

        outputs: list[bytes] = []
        with patch.object(socket, "socket", side_effect=network_forbidden), patch.object(
            socket, "create_connection", side_effect=network_forbidden
        ), patch.object(socket, "getaddrinfo", side_effect=network_forbidden):
            outputs.append(
                json.dumps(
                    telemetry_status(paths=self.v1, environment={}), sort_keys=True
                ).encode()
            )
            outputs.append(json.dumps(telemetry_migrate(paths=self.v1), sort_keys=True).encode())
            outputs.append(json.dumps(telemetry_flush(timeout=0, paths=self.v1), sort_keys=True).encode())
        self.assertEqual(store.inspect_store_schema_version(self.v3), 3)
        for path in self.root.rglob("*"):
            if path.is_file():
                captured.append(path.read_bytes())
        captured.extend(outputs)
        for sentinel in sentinels:
            for artifact in captured:
                self.assertNotIn(sentinel, artifact)

    def test_hostile_preexisting_v2_backup_blocks_without_changing_source(self) -> None:
        self.root.mkdir(mode=0o700)
        _create_v1_store(self.v1.database_path)
        store.migrate_store_v1_to_v2(self.v1)
        before = self.v1.database_path.read_bytes()
        self.v3.backup_database_path.write_bytes(b"PRIVATE_HOSTILE_V2_BACKUP")
        self.v3.backup_database_path.chmod(0o600)
        with self.assertRaises(store.StoreIncompatibleError):
            store.migrate_store_v2_to_v3(self.v3)
        self.assertEqual(store.inspect_store_schema_version(self.v3), 2)
        self.assertEqual(self.v1.database_path.read_bytes(), before)
        self.assertFalse(self.v3.migration_directory.exists())

    def test_v2_to_v3_postpublication_fault_reconciles_without_recopy(self) -> None:
        self.root.mkdir(mode=0o700)
        _create_v1_store(self.v1.database_path)
        store.migrate_store_v1_to_v2(self.v1)

        class Crash(BaseException):
            pass

        with self.assertRaises(Crash):
            store.migrate_store_v2_to_v3(
                self.v3,
                fault_hook=lambda observed: (_ for _ in ()).throw(Crash()) if observed == "canonical_published" else None,
            )
        self.assertEqual(store.inspect_store_schema_version(self.v3), 3)
        self.assertTrue(self.v3.migration_directory.is_dir())
        facts = telemetry_migrate(paths=self.v1)
        self.assertEqual(facts["outcome"], "already_current")
        self.assertFalse(self.v3.migration_directory.exists())
        self.assertTrue(self.v3.backup_database_path.is_file())

    def test_v2_to_v3_prepublication_faults_leave_v2_and_retry(self) -> None:
        phases = ("validated_source", "scratch_created", "backup_candidate_copied", "transaction_committed", "scratch_validated", "backup_published")
        for phase in phases:
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as raw:
                v1 = telemetry_paths(Path(raw) / "telemetry")
                v3 = telemetry_paths_v3(v1.directory)
                v1.directory.mkdir(mode=0o700)
                _create_v1_store(v1.database_path)
                store.migrate_store_v1_to_v2(v1)

                class Crash(BaseException):
                    pass

                with self.assertRaises(Crash):
                    store.migrate_store_v2_to_v3(
                        v3,
                        fault_hook=lambda observed, selected=phase: (_ for _ in ()).throw(Crash()) if observed == selected else None,
                    )
                self.assertEqual(store.inspect_store_schema_version(v3), 2)
                self.assertFalse(v3.database_wal_path.exists())
                store.migrate_store_v2_to_v3(v3)
                self.assertEqual(store.inspect_store_schema_version(v3), 3)


if __name__ == "__main__":
    unittest.main()
