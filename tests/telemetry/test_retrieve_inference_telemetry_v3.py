from __future__ import annotations

from contextlib import ExitStack, contextmanager
from datetime import datetime, timedelta
from io import StringIO
import json
import os
from typing import Callable, Iterator, Sequence
import unittest
from unittest.mock import patch

from buoy_search.cli.main import (
    _CommandEmbeddingWorkerSession,
    _InProcessEmbeddingFallbackError,
    _prepare_default_embedding_worker,
)
from buoy_search.config import RuntimeConfig
from buoy_search.retrieval import _provider_invocation_receipt as receipt
from buoy_search.retrieval.embedding_worker import EmbeddingWorkerError
from buoy_search.retrieval.evidence import OWNER_AUTHORIZED_ACTIVE_CALIBRATION
from buoy_search.retrieval.retriever import (
    CalibratedEvidenceAssessor,
    EvidenceRouteContext,
    SearchHit,
)
from buoy_search.telemetry import producer
from buoy_search.telemetry.envelope import (
    CommandTraceRowsV3,
    TraceEnvelopeError,
    V2_COMMAND_ROOT_SPAN_NAME,
    V2_PIPELINE_SPAN_NAME,
    V3_INFERENCE_SPAN_NAME,
    command_trace_rows_from_spans_v3,
    decode_trace_envelope_v3,
    encode_trace_envelope_v3,
)
from buoy_search.telemetry.producer import (
    EVIDENCE_SPAN_NAME,
    NAMESPACE_QUERY_SPAN_NAME,
    QUERY_EMBED_SPAN_NAME,
    RERANK_SPAN_NAME,
    instrument_in_process_embedder,
    instrument_in_process_reranker,
    retrieval_trace,
    retrieve_command_trace,
    safe_time_ns,
    telemetry_span,
)
from tests.telemetry.test_telemetry_v2_storage import _canonical, _rows


_PROVIDER_UNAVAILABLE = (
    "unavailable",
    "provider_client_invocation",
    None,
    None,
)


class _Embedder:
    def encode(self, _texts: Sequence[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3]]


class _Reranker:
    def __init__(self, *, error: BaseException | None = None) -> None:
        self.error = error
        self.calls: list[tuple[str, list[str]]] = []

    def score(self, query: str, passages: Sequence[str]) -> list[float]:
        self.calls.append((query, list(passages)))
        if self.error is not None:
            raise self.error
        return [float(index) for index, _passage in enumerate(passages)]


def _v3_rows_with_inference() -> CommandTraceRowsV3:
    v2 = _rows()
    command = list(v2.command)
    command[-1] = 3
    command.append("compatibility_in_process")
    operation = list(v2.retrieval_operation or ())
    operation[-1] = 3
    spans: list[tuple[object, ...]] = []
    embed = next(span for span in v2.spans if span[3] == QUERY_EMBED_SPAN_NAME)
    for span in v2.spans:
        values = list(span)
        attributes = json.loads(str(values[8]))
        if values[3] in {V2_COMMAND_ROOT_SPAN_NAME, V2_PIPELINE_SPAN_NAME}:
            attributes["buoy.observation.schema_version"] = 3
        if values[3] == V2_COMMAND_ROOT_SPAN_NAME:
            attributes["buoy.inference.policy"] = "compatibility_in_process"
        values[8] = _canonical(attributes)
        spans.append(tuple(values))
    inference = (
        embed[0],
        "9" * 16,
        embed[1],
        V3_INFERENCE_SPAN_NAME,
        embed[4] + timedelta(microseconds=100),
        embed[4] + timedelta(microseconds=900),
        0.8,
        "OK",
        _canonical(
            {
                "buoy.inference.backend": "in_process",
                "buoy.inference.item_count": 1,
                "buoy.inference.operation": "encode",
                "buoy.inference.outcome": "success",
                "buoy.inference.role": "primary",
            }
        ),
    )
    spans.append(inference)
    spans.sort(key=lambda row: (row[4], row[1]))
    return CommandTraceRowsV3(
        tuple(command),
        tuple(operation),
        _PROVIDER_UNAVAILABLE,
        tuple(spans),
        v2.events,
    )


def _v3_worker_fallback_value() -> dict[str, object]:
    value = json.loads(encode_trace_envelope_v3(_v3_rows_with_inference()))
    value["command"].update(
        {
            "inference_policy": "worker_preferred",
            "retrieval_mode": "automatic",
        }
    )
    root = next(
        span for span in value["spans"] if span["name"] == V2_COMMAND_ROOT_SPAN_NAME
    )
    root["attributes"].update(
        {
            "buoy.inference.policy": "worker_preferred",
            "buoy.retrieval.mode": "automatic",
        }
    )
    pipeline = next(
        span for span in value["spans"] if span["name"] == V2_PIPELINE_SPAN_NAME
    )
    pipeline["attributes"]["buoy.retrieval.mode"] = "automatic"
    prepare = next(
        span for span in value["spans"] if span["name"] == "buoy.retrieve.prepare"
    )
    trace_id = root["trace_id"]

    def routing_stage(
        span_id: str,
        name: str,
        start_offset_us: int,
        end_offset_us: int,
    ) -> dict[str, object]:
        return {
            "trace_id": trace_id,
            "span_id": span_id,
            "parent_span_id": prepare["span_id"],
            "name": name,
            "started_at_unix_us": root["started_at_unix_us"] + start_offset_us,
            "ended_at_unix_us": root["started_at_unix_us"] + end_offset_us,
            "duration_ms": (end_offset_us - start_offset_us) / 1_000,
            "status_code": "OK",
            "attributes": {},
        }

    route_select = routing_stage("c" * 16, "buoy.routing.select", 1_550, 1_990)
    value["spans"].extend(
        (
            routing_stage("d" * 16, "buoy.routing.model", 1_100, 1_200),
            routing_stage("e" * 16, "buoy.routing.catalog", 1_250, 1_350),
            routing_stage("f" * 16, "buoy.routing.model", 1_400, 1_500),
            route_select,
            {
                "trace_id": trace_id,
                "span_id": "1" * 16,
                "parent_span_id": pipeline["span_id"],
                "name": RERANK_SPAN_NAME,
                "started_at_unix_us": root["started_at_unix_us"] + 7_100,
                "ended_at_unix_us": root["started_at_unix_us"] + 7_400,
                "duration_ms": 0.3,
                "status_code": "OK",
                "attributes": {},
            },
            {
                "trace_id": trace_id,
                "span_id": "01" * 8,
                "parent_span_id": pipeline["span_id"],
                "name": EVIDENCE_SPAN_NAME,
                "started_at_unix_us": root["started_at_unix_us"] + 7_500,
                "ended_at_unix_us": root["started_at_unix_us"] + 7_700,
                "duration_ms": 0.2,
                "status_code": "UNSET",
                "attributes": {},
            },
        )
    )

    fallback = next(
        span for span in value["spans"] if span["name"] == V3_INFERENCE_SPAN_NAME
    )
    fallback.update(
        {
            "parent_span_id": route_select["span_id"],
            "started_at_unix_us": root["started_at_unix_us"] + 1_750,
            "ended_at_unix_us": root["started_at_unix_us"] + 1_850,
            "duration_ms": 0.1,
        }
    )
    fallback["attributes"]["buoy.inference.role"] = "fallback"
    worker = json.loads(json.dumps(fallback))
    worker.update(
        {
            "span_id": "a" * 16,
            "started_at_unix_us": root["started_at_unix_us"] + 1_600,
            "ended_at_unix_us": root["started_at_unix_us"] + 1_700,
            "duration_ms": 0.1,
            "status_code": "ERROR",
        }
    )
    worker["attributes"].update(
        {
            "buoy.inference.backend": "worker",
            "buoy.inference.error_type": "busy_timeout",
            "buoy.inference.outcome": "error",
            "buoy.inference.role": "primary",
            "buoy.inference.worker_state": "unknown",
        }
    )
    value["spans"].append(worker)
    value["spans"].sort(
        key=lambda span: (span["started_at_unix_us"], span["span_id"])
    )
    return value


class RetrieveInferenceEnvelopeV3Tests(unittest.TestCase):
    def test_exact_v3_round_trip_preserves_v2_and_inference_graph(self) -> None:
        rows = _v3_rows_with_inference()
        payload = encode_trace_envelope_v3(rows)

        self.assertEqual(decode_trace_envelope_v3(payload), rows)
        value = json.loads(payload)
        self.assertEqual(value["envelope_schema_version"], 3)
        self.assertEqual(value["command"]["inference_policy"], "compatibility_in_process")
        self.assertEqual(value["provider_accounting"]["status"], "unavailable")
        inference = next(
            span for span in value["spans"] if span["name"] == V3_INFERENCE_SPAN_NAME
        )
        self.assertEqual(inference["attributes"]["buoy.inference.item_count"], 1)

    def test_decoder_rejects_invalid_inference_state_parent_and_fallback(self) -> None:
        base = json.loads(encode_trace_envelope_v3(_v3_rows_with_inference()))
        inference = next(
            span for span in base["spans"] if span["name"] == V3_INFERENCE_SPAN_NAME
        )

        invalid_state = json.loads(json.dumps(base))
        selected = next(
            span
            for span in invalid_state["spans"]
            if span["name"] == V3_INFERENCE_SPAN_NAME
        )
        selected["attributes"].update(
            {
                "buoy.inference.backend": "worker",
                "buoy.inference.worker_state": "unknown",
            }
        )
        with self.assertRaises(TraceEnvelopeError):
            decode_trace_envelope_v3(_canonical(invalid_state).encode())

        invalid_parent = json.loads(json.dumps(base))
        namespace = next(
            span
            for span in invalid_parent["spans"]
            if span["name"] == NAMESPACE_QUERY_SPAN_NAME
        )
        selected = next(
            span
            for span in invalid_parent["spans"]
            if span["name"] == V3_INFERENCE_SPAN_NAME
        )
        selected["parent_span_id"] = namespace["span_id"]
        with self.assertRaises(TraceEnvelopeError):
            decode_trace_envelope_v3(_canonical(invalid_parent).encode())

        invalid_fallback = json.loads(json.dumps(base))
        selected = next(
            span
            for span in invalid_fallback["spans"]
            if span["name"] == V3_INFERENCE_SPAN_NAME
        )
        selected["attributes"]["buoy.inference.role"] = "fallback"
        invalid_fallback["command"]["inference_policy"] = "worker_preferred"
        root = next(
            span
            for span in invalid_fallback["spans"]
            if span["name"] == V2_COMMAND_ROOT_SPAN_NAME
        )
        root["attributes"]["buoy.inference.policy"] = "worker_preferred"
        with self.assertRaises(TraceEnvelopeError):
            decode_trace_envelope_v3(_canonical(invalid_fallback).encode())

    def test_decoder_rejects_prohibited_inference_attribute(self) -> None:
        value = json.loads(encode_trace_envelope_v3(_v3_rows_with_inference()))
        inference = next(
            span for span in value["spans"] if span["name"] == V3_INFERENCE_SPAN_NAME
        )
        inference["attributes"]["query"] = "private-query"
        with self.assertRaises(TraceEnvelopeError) as raised:
            decode_trace_envelope_v3(_canonical(value).encode())
        self.assertNotIn("private-query", str(raised.exception))

    def test_decoder_enforces_item_bounds_and_command_policy_identity(self) -> None:
        for operation, count in (("encode", 0), ("encode", 17), ("score", 109)):
            with self.subTest(operation=operation, count=count):
                value = json.loads(
                    encode_trace_envelope_v3(_v3_rows_with_inference())
                )
                inference = next(
                    span
                    for span in value["spans"]
                    if span["name"] == V3_INFERENCE_SPAN_NAME
                )
                inference["attributes"]["buoy.inference.operation"] = operation
                inference["attributes"]["buoy.inference.item_count"] = count
                with self.assertRaises(TraceEnvelopeError):
                    decode_trace_envelope_v3(_canonical(value).encode())

        value = json.loads(encode_trace_envelope_v3(_v3_rows_with_inference()))
        value["command"]["inference_policy"] = "forced_in_process"
        with self.assertRaises(TraceEnvelopeError):
            decode_trace_envelope_v3(_canonical(value).encode())

    def test_decoder_rejects_malformed_first_fallback_pair(self) -> None:
        mutations = ("parent", "operation", "item_count", "not_immediate")
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                # First prove the altered span is independently valid under
                # generic parent/operation/timing rules in a legal position.
                witness = _v3_worker_fallback_value()
                witness_requests = [
                    span
                    for span in witness["spans"]
                    if span["name"] == V3_INFERENCE_SPAN_NAME
                ]
                witness_worker, witness_fallback = witness_requests
                altered = json.loads(json.dumps(witness_fallback))
                altered["span_id"] = "03" * 8
                if mutation == "parent":
                    query_embed = next(
                        span
                        for span in witness["spans"]
                        if span["name"] == QUERY_EMBED_SPAN_NAME
                    )
                    altered.update(
                        {
                            "parent_span_id": query_embed["span_id"],
                            "started_at_unix_us": (
                                query_embed["started_at_unix_us"] + 150
                            ),
                            "ended_at_unix_us": (
                                query_embed["started_at_unix_us"] + 250
                            ),
                            "duration_ms": 0.1,
                        }
                    )
                elif mutation == "operation":
                    altered.update(
                        {
                            "started_at_unix_us": (
                                witness_fallback["ended_at_unix_us"] + 10
                            ),
                            "ended_at_unix_us": (
                                witness_fallback["ended_at_unix_us"] + 30
                            ),
                            "duration_ms": 0.02,
                        }
                    )
                    altered["attributes"]["buoy.inference.operation"] = "score"
                elif mutation == "item_count":
                    altered.update(
                        {
                            "started_at_unix_us": (
                                witness_fallback["ended_at_unix_us"] + 10
                            ),
                            "ended_at_unix_us": (
                                witness_fallback["ended_at_unix_us"] + 30
                            ),
                            "duration_ms": 0.02,
                        }
                    )
                    altered["attributes"]["buoy.inference.item_count"] = 2
                else:
                    altered.update(
                        {
                            "started_at_unix_us": (
                                witness_worker["started_at_unix_us"] - 40
                            ),
                            "ended_at_unix_us": (
                                witness_worker["started_at_unix_us"] - 10
                            ),
                            "duration_ms": 0.03,
                            "status_code": "OK",
                        }
                    )
                    altered["attributes"].update(
                        {
                            "buoy.inference.backend": "worker",
                            "buoy.inference.outcome": "success",
                            "buoy.inference.role": "primary",
                            "buoy.inference.worker_state": "reused",
                        }
                    )
                    altered["attributes"].pop(
                        "buoy.inference.error_type", None
                    )
                witness["spans"].append(altered)
                witness["spans"].sort(
                    key=lambda span: (
                        span["started_at_unix_us"],
                        span["span_id"],
                    )
                )
                decode_trace_envelope_v3(_canonical(witness).encode())

                value = _v3_worker_fallback_value()
                requests = [
                    span
                    for span in value["spans"]
                    if span["name"] == V3_INFERENCE_SPAN_NAME
                ]
                worker, fallback = requests
                if mutation == "parent":
                    query_embed = next(
                        span
                        for span in value["spans"]
                        if span["name"] == QUERY_EMBED_SPAN_NAME
                    )
                    fallback.update(
                        {
                            "parent_span_id": query_embed["span_id"],
                            "started_at_unix_us": (
                                query_embed["started_at_unix_us"] + 150
                            ),
                            "ended_at_unix_us": (
                                query_embed["started_at_unix_us"] + 250
                            ),
                            "duration_ms": 0.1,
                        }
                    )
                elif mutation == "operation":
                    # Route selection is independently valid for encode and score.
                    fallback["attributes"]["buoy.inference.operation"] = "score"
                elif mutation == "item_count":
                    fallback["attributes"]["buoy.inference.item_count"] = 2
                else:
                    intervening = json.loads(json.dumps(fallback))
                    intervening.update(
                        {
                            "span_id": "02" * 8,
                            "started_at_unix_us": worker["ended_at_unix_us"] + 10,
                            "ended_at_unix_us": worker["ended_at_unix_us"] + 40,
                            "duration_ms": 0.03,
                            "status_code": "OK",
                        }
                    )
                    intervening["attributes"].update(
                        {
                            "buoy.inference.backend": "worker",
                            "buoy.inference.outcome": "success",
                            "buoy.inference.role": "primary",
                            "buoy.inference.worker_state": "reused",
                        }
                    )
                    intervening["attributes"].pop(
                        "buoy.inference.error_type", None
                    )
                    value["spans"].append(intervening)
                    value["spans"].sort(
                        key=lambda span: (
                            span["started_at_unix_us"],
                            span["span_id"],
                        )
                    )
                with self.assertRaises(TraceEnvelopeError):
                    decode_trace_envelope_v3(_canonical(value).encode())

    def test_decoder_accepts_latched_later_fallback_with_new_logical_shape(self) -> None:
        value = _v3_worker_fallback_value()
        first = [
            span
            for span in value["spans"]
            if span["name"] == V3_INFERENCE_SPAN_NAME
        ][-1]
        later = json.loads(json.dumps(first))
        later["span_id"] = "b" * 16
        later["started_at_unix_us"] = first["ended_at_unix_us"] + 20
        later["ended_at_unix_us"] = later["started_at_unix_us"] + 100
        later["duration_ms"] = 0.1
        later["attributes"]["buoy.inference.item_count"] = 3
        value["spans"].append(later)
        value["spans"].sort(
            key=lambda span: (span["started_at_unix_us"], span["span_id"])
        )

        decoded = decode_trace_envelope_v3(_canonical(value).encode())

        self.assertEqual(
            len([span for span in decoded.spans if span[3] == V3_INFERENCE_SPAN_NAME]),
            3,
        )


class RetrieveInferencePolicyV3Tests(unittest.TestCase):
    def test_policy_matrix_is_content_free_and_preserves_non_v3_dry_run_path(self) -> None:
        policies: list[str] = []
        with patch(
            "buoy_search.cli.main.EMBEDDING_WORKER_CAPABILITY_FACTORY",
            return_value=True,
        ) as capability:
            session = _prepare_default_embedding_worker(
                RuntimeConfig(),
                activate=False,
                disabled=False,
                policy_callback=policies.append,
            )
        self.assertIsNone(session)
        self.assertEqual(policies, ["worker_preferred"])
        capability.assert_called_once_with()

        policies.clear()
        with patch(
            "buoy_search.cli.main.EMBEDDING_WORKER_CAPABILITY_FACTORY",
            side_effect=AssertionError("disabled policy must short-circuit"),
        ):
            session = _prepare_default_embedding_worker(
                RuntimeConfig(),
                activate=False,
                disabled=True,
                policy_callback=policies.append,
            )
        self.assertIsNone(session)
        self.assertEqual(policies, ["forced_in_process"])

        policies.clear()
        with patch(
            "buoy_search.cli.main.EMBEDDING_WORKER_CAPABILITY_FACTORY",
            side_effect=AssertionError("custom model must short-circuit"),
        ):
            session = _prepare_default_embedding_worker(
                RuntimeConfig(embedding_model="private-custom-model"),
                activate=True,
                disabled=False,
                policy_callback=policies.append,
            )
        self.assertIsNone(session)
        self.assertEqual(policies, ["compatibility_in_process"])

        with patch(
            "buoy_search.cli.main.EMBEDDING_WORKER_CAPABILITY_FACTORY",
            side_effect=AssertionError("production v2 dry-run path changed"),
        ):
            self.assertIsNone(
                _prepare_default_embedding_worker(
                    RuntimeConfig(),
                    activate=False,
                    disabled=False,
                )
            )

    def test_late_identity_and_capability_failures_downgrade_policy(self) -> None:
        from buoy_search.retrieval import embedding_worker

        policies: list[str] = []
        with patch(
            "buoy_search.cli.main.EMBEDDING_WORKER_CAPABILITY_FACTORY",
            return_value=True,
        ), patch.object(embedding_worker, "SCHEMA_VERSION", 99):
            session = _prepare_default_embedding_worker(
                RuntimeConfig(),
                activate=True,
                disabled=False,
                policy_callback=policies.append,
            )
        self.assertIsNone(session)
        self.assertEqual(
            policies,
            ["worker_preferred", "compatibility_in_process"],
        )

        policies.clear()
        with patch(
            "buoy_search.cli.main.EMBEDDING_WORKER_CAPABILITY_FACTORY",
            return_value=True,
        ), patch.object(
            embedding_worker,
            "_require_capability",
            side_effect=RuntimeError("private late failure"),
        ):
            session = _prepare_default_embedding_worker(
                RuntimeConfig(),
                activate=True,
                disabled=False,
                policy_callback=policies.append,
            )
        self.assertIsNone(session)
        self.assertEqual(
            policies,
            ["worker_preferred", "compatibility_in_process"],
        )

    def test_preview_policy_has_no_identity_import_or_process_side_effect(self) -> None:
        policies: list[str] = []
        with patch(
            "buoy_search.cli.main.EMBEDDING_WORKER_CAPABILITY_FACTORY",
            return_value=True,
        ), patch(
            "buoy_search.retrieval.embedding_worker._require_capability",
            side_effect=AssertionError("preview forced late capability work"),
        ), patch(
            "buoy_search.retrieval.embedding_worker._spawn_worker",
            side_effect=AssertionError("preview spawned a process"),
        ):
            session = _prepare_default_embedding_worker(
                RuntimeConfig(),
                activate=False,
                disabled=False,
                policy_callback=policies.append,
            )
        self.assertIsNone(session)
        self.assertEqual(policies, ["worker_preferred"])


class RetrieveInferenceProducerV3Tests(unittest.TestCase):
    @contextmanager
    def _trace(
        self,
        *,
        policy: str,
        retrieval_mode: str = "explicit_single",
    ) -> Iterator[tuple[object, list[tuple[object, ...]]]]:
        captured: list[tuple[object, ...]] = []

        def capture(
            spans: Sequence[object],
            *,
            root_span_id: int | None,
            schema_version: int,
            provider_accounting: tuple[object, ...] | None,
        ) -> None:
            captured.append(
                (tuple(spans), root_span_id, schema_version, provider_accounting)
            )

        started = safe_time_ns()
        assert started is not None
        class MissingReceiptHandle:
            def receipt(self) -> None:
                return None

        @contextmanager
        def missing_receipt_scope() -> Iterator[MissingReceiptHandle]:
            yield MissingReceiptHandle()

        with patch.dict(os.environ, {"BUOY_TELEMETRY": "local"}), patch.object(
            producer,
            "_persist_command_trace_best_effort",
            side_effect=capture,
        ), patch.object(
            receipt,
            "_provider_invocation_receipt_scope",
            missing_receipt_scope,
        ):
            with retrieve_command_trace(
                started_at_ns=started,
                bootstrap_ended_at_ns=started,
                execution_mode="live",
                retrieval_mode=retrieval_mode,
                inference_policy=policy,
                _schema_version=3,
            ) as command:
                yield command, captured
        self.assertEqual(len(captured), 1)

    def _complete_explicit_trace(
        self,
        command: object,
        encode: Callable[[], list[list[float]]],
    ) -> list[list[float]]:
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
            with telemetry_span(QUERY_EMBED_SPAN_NAME) as embed_span:
                vectors = encode()
                embed_span.mark_ok()
            with telemetry_span(
                NAMESPACE_QUERY_SPAN_NAME,
                {"buoy.route.rank": 1},
            ) as namespace_span:
                namespace_span.set_attributes(
                    {
                        "buoy.namespace.status": "ok",
                        "buoy.namespace.hit_count": 1,
                    }
                )
                namespace_span.mark_ok()
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
        return vectors

    def _rows_from_capture(
        self,
        captured: list[tuple[object, ...]],
    ) -> CommandTraceRowsV3:
        spans, root_span_id, schema_version, provider_accounting = captured[0]
        self.assertEqual(schema_version, 3)
        self.assertIsInstance(root_span_id, int)
        self.assertIsInstance(provider_accounting, tuple)
        return command_trace_rows_from_spans_v3(
            spans,  # type: ignore[arg-type]
            root_span_id=root_span_id,  # type: ignore[arg-type]
            provider_accounting=provider_accounting,  # type: ignore[arg-type]
        )

    def test_in_process_request_is_nested_under_query_embedding(self) -> None:
        with self._trace(policy="compatibility_in_process") as (command, captured):
            embedder = instrument_in_process_embedder(_Embedder())
            vectors = self._complete_explicit_trace(
                command,
                lambda: embedder.encode(["private-query"]),
            )
        rows = self._rows_from_capture(captured)

        self.assertEqual(vectors, [[0.1, 0.2, 0.3]])
        inference = next(span for span in rows.spans if span[3] == V3_INFERENCE_SPAN_NAME)
        embed = next(span for span in rows.spans if span[3] == QUERY_EMBED_SPAN_NAME)
        self.assertEqual(inference[2], embed[1])
        self.assertNotIn("private-query", encode_trace_envelope_v3(rows).decode())

    def test_worker_failure_and_fallback_are_two_sibling_requests(self) -> None:
        warnings: list[str] = []

        def failed_worker(
            _texts: Sequence[str],
            observer: Callable[[str], None],
        ) -> list[list[float]]:
            observer("unknown")
            raise EmbeddingWorkerError("busy_timeout")

        with self._trace(policy="worker_preferred") as (command, captured):
            session = _CommandEmbeddingWorkerSession(
                lambda _texts: (_ for _ in ()).throw(
                    AssertionError("diagnostic callback required")
                ),
                warning_callback=warnings.append,
                encode_with_lifecycle=failed_worker,
            )
            embedder = session.embedder("retrieval", _Embedder)
            vectors = self._complete_explicit_trace(
                command,
                lambda: embedder.encode(["private-query"]),
            )
        rows = self._rows_from_capture(captured)

        self.assertEqual(vectors, [[0.1, 0.2, 0.3]])
        self.assertEqual(len(warnings), 1)
        requests = [span for span in rows.spans if span[3] == V3_INFERENCE_SPAN_NAME]
        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0][2], requests[1][2])
        attributes = [json.loads(str(span[8])) for span in requests]
        self.assertEqual(
            [(item["buoy.inference.backend"], item["buoy.inference.outcome"]) for item in attributes],
            [("worker", "error"), ("in_process", "success")],
        )
        payload = encode_trace_envelope_v3(rows).decode()
        self.assertNotIn("private-query", payload)
        self.assertNotIn("diagnostic callback required", payload)

    def test_fake_clock_excludes_fallback_factory_from_request_timing(self) -> None:
        ticks = iter(range(1_000_000_000, 2_000_000_000, 1_000_000))
        factory_at: list[int] = []
        backend_at: list[int] = []

        class TimedEmbedder:
            def encode(self, _texts: Sequence[str]) -> list[list[float]]:
                observed = safe_time_ns()
                assert observed is not None
                backend_at.append(observed)
                return [[1.0]]

        def factory() -> TimedEmbedder:
            observed = safe_time_ns()
            assert observed is not None
            factory_at.append(observed)
            return TimedEmbedder()

        def failed_worker(
            _texts: Sequence[str],
            observer: Callable[[str], None],
        ) -> list[list[float]]:
            observer("unknown")
            raise EmbeddingWorkerError("busy_timeout")

        with patch.object(producer, "_time_ns", side_effect=lambda: next(ticks)):
            with self._trace(policy="worker_preferred") as (command, captured):
                session = _CommandEmbeddingWorkerSession(
                    lambda _texts: [],
                    warning_callback=lambda _message: None,
                    encode_with_lifecycle=failed_worker,
                )
                embedder = session.embedder("timed", factory)
                self._complete_explicit_trace(
                    command,
                    lambda: embedder.encode(["timed-query"]),
                )
        rows = self._rows_from_capture(captured)
        fallback = [
            span
            for span in rows.spans
            if span[3] == V3_INFERENCE_SPAN_NAME
            and json.loads(str(span[8]))["buoy.inference.backend"] == "in_process"
        ][0]
        epoch = datetime(1970, 1, 1)
        fallback_start_us = int((fallback[4] - epoch).total_seconds() * 1_000_000)
        fallback_end_us = int((fallback[5] - epoch).total_seconds() * 1_000_000)

        self.assertLess(factory_at[0] // 1_000, fallback_start_us)
        self.assertLessEqual(fallback_start_us, backend_at[0] // 1_000)
        self.assertLessEqual(backend_at[0] // 1_000, fallback_end_us)

    def test_parent_matrix_and_evidence_score_reuse(self) -> None:
        reranker = _Reranker()
        hit = SearchHit(id="hit", title="title", content="fresh passage")
        route_context = EvidenceRouteContext(
            selection_reason="ambiguous_semantic",
            semantic_score=0.3,
            semantic_margin=0.1,
        )
        reused_loader_calls = 0

        def forbidden_reused_loader() -> _Reranker:
            nonlocal reused_loader_calls
            reused_loader_calls += 1
            raise AssertionError("existing evidence scores loaded a reranker")

        with self._trace(
            policy="compatibility_in_process",
            retrieval_mode="automatic",
        ) as (command, captured):
            with command.stage("buoy.retrieve.prepare"):  # type: ignore[attr-defined]
                with command.stage("buoy.routing.model"):  # type: ignore[attr-defined]
                    pass
                with command.stage("buoy.routing.catalog"):  # type: ignore[attr-defined]
                    pass
                with command.stage("buoy.routing.model"):  # type: ignore[attr-defined]
                    pass
                with command.stage("buoy.routing.select"):  # type: ignore[attr-defined]
                    instrument_in_process_embedder(_Embedder()).encode(
                        ["route query"]
                    )
                    instrument_in_process_reranker(reranker).score(
                        "route query", ["route passage"]
                    )
            with retrieval_trace(
                mode="automatic",
                embedding_model="BAAI/bge-small-en-v1.5",
                embedding_precision="float32",
                top_k=5,
                candidates=10,
                namespace_count=1,
                initial_fanout=1,
            ) as pipeline:
                with telemetry_span(QUERY_EMBED_SPAN_NAME) as span:
                    instrument_in_process_embedder(_Embedder()).encode(["query"])
                    span.mark_ok()
                with telemetry_span(
                    NAMESPACE_QUERY_SPAN_NAME,
                    {"buoy.route.rank": 1},
                ) as span:
                    span.set_attributes(
                        {
                            "buoy.namespace.status": "ok",
                            "buoy.namespace.hit_count": 1,
                        }
                    )
                    span.mark_ok()
                with telemetry_span(RERANK_SPAN_NAME) as span:
                    instrument_in_process_reranker(reranker).score(
                        "query", ["result passage"]
                    )
                    span.mark_ok()
                with telemetry_span(EVIDENCE_SPAN_NAME):
                    reused = CalibratedEvidenceAssessor(
                        OWNER_AUTHORIZED_ACTIVE_CALIBRATION,
                        reranker_loader=forbidden_reused_loader,
                    )
                    reused.assess(
                        query="query",
                        hits=[hit],
                        existing_scores=[0.5],
                        route_context=route_context,
                        namespace_failure_count=0,
                        widening_triggered_by_weak_evidence=False,
                    )
                    fresh = CalibratedEvidenceAssessor(
                        OWNER_AUTHORIZED_ACTIVE_CALIBRATION,
                        reranker_loader=lambda: instrument_in_process_reranker(
                            reranker
                        ),
                    )
                    fresh.assess(
                        query="query",
                        hits=[hit],
                        existing_scores=None,
                        route_context=route_context,
                        namespace_failure_count=0,
                        widening_triggered_by_weak_evidence=False,
                    )
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
        rows = self._rows_from_capture(captured)
        by_id = {span[1]: span[3] for span in rows.spans}
        requests = [span for span in rows.spans if span[3] == V3_INFERENCE_SPAN_NAME]
        parent_names = [by_id[span[2]] for span in requests]

        self.assertEqual(reused_loader_calls, 0)
        self.assertEqual(parent_names.count("buoy.routing.select"), 2)
        self.assertEqual(parent_names.count(QUERY_EMBED_SPAN_NAME), 1)
        self.assertEqual(parent_names.count(RERANK_SPAN_NAME), 1)
        self.assertEqual(parent_names.count(EVIDENCE_SPAN_NAME), 1)

    def test_worker_and_fallback_double_failure_records_two_errors(self) -> None:
        warnings: list[str] = []
        fallback_error = RuntimeError("private fallback score frame")

        def failed_worker(
            _texts: Sequence[str],
            observer: Callable[[str], None],
        ) -> list[list[float]]:
            observer("unknown")
            raise EmbeddingWorkerError("encoding_failure")

        class FailedFallback:
            def encode(self, _texts: Sequence[str]) -> list[list[float]]:
                raise fallback_error

        with self._trace(policy="worker_preferred") as (command, captured):
            with command.stage("buoy.retrieve.prepare"):  # type: ignore[attr-defined]
                pass
            with self.assertRaises(_InProcessEmbeddingFallbackError):
                with retrieval_trace(
                    mode="explicit_single",
                    embedding_model="BAAI/bge-small-en-v1.5",
                    embedding_precision="float32",
                    top_k=5,
                    candidates=10,
                    namespace_count=1,
                    initial_fanout=1,
                ):
                    with telemetry_span(QUERY_EMBED_SPAN_NAME):
                        session = _CommandEmbeddingWorkerSession(
                            lambda _texts: [],
                            warning_callback=warnings.append,
                            encode_with_lifecycle=failed_worker,
                        )
                        session.embedder("failed", FailedFallback).encode(["query"])
            command.finish(1, error_type="model_error")  # type: ignore[attr-defined]
        rows = self._rows_from_capture(captured)
        attributes = [
            json.loads(str(span[8]))
            for span in rows.spans
            if span[3] == V3_INFERENCE_SPAN_NAME
        ]

        self.assertEqual(len(warnings), 1)
        self.assertEqual(len(attributes), 2)
        self.assertEqual(
            [item["buoy.inference.outcome"] for item in attributes],
            ["error", "error"],
        )
        self.assertEqual(
            [item["buoy.inference.error_type"] for item in attributes],
            ["encoding_failure", "encoding_failure"],
        )

    def test_disabled_path_installs_no_lifecycle_callback_or_adapter(self) -> None:
        base_calls: list[list[str]] = []

        def base(texts: Sequence[str]) -> list[list[float]]:
            base_calls.append(list(texts))
            return [[1.0]]

        session = _CommandEmbeddingWorkerSession(
            base,
            warning_callback=lambda _message: None,
            encode_with_lifecycle=lambda _texts, _observer: (_ for _ in ()).throw(
                AssertionError("disabled telemetry installed lifecycle callback")
            ),
        )
        embedder = _Embedder()

        self.assertIs(instrument_in_process_embedder(embedder), embedder)
        with patch(
            "buoy_search.cli.main.inference_request",
            side_effect=AssertionError("disabled telemetry created a context"),
        ):
            result = session.embedder("disabled", _Embedder).encode(["query"])
        self.assertEqual(result, [[1.0]])
        self.assertEqual(base_calls, [["query"]])
        self.assertIsNone(producer._ACTIVE_SESSION.get())
        self.assertIsNone(producer._ACTIVE_SPAN.get())

    def test_session_telemetry_fault_matrix_preserves_exact_behavior(self) -> None:
        class InjectedTelemetryFault(BaseException):
            pass

        def run_scenario(scenario: str, *, inject_fault: bool) -> dict[str, object]:
            calls = {"base": 0, "worker": 0, "factory": 0, "fallback": 0}
            lifecycle: list[str] = []
            warnings: list[str] = []
            events: list[str] = []
            warning_output = StringIO()
            worker_result = [[object()]]
            fallback_result = [[object()]]
            worker_error = EmbeddingWorkerError("busy_timeout")
            fallback_error = _InProcessEmbeddingFallbackError(
                "bounded fallback failure"
            )

            def base_worker(_texts: Sequence[str]) -> list[list[float]]:
                calls["base"] += 1
                raise AssertionError("lifecycle-aware worker seam was bypassed")

            def lifecycle_worker(
                _texts: Sequence[str],
                observer: Callable[[str], None],
            ) -> list[list[float]]:
                calls["worker"] += 1
                events.append("worker")
                state = "reused" if scenario == "worker_success" else "unknown"
                lifecycle.append(state)
                try:
                    observer(state)
                except BaseException:
                    # The real worker client owns this exact fault-isolation seam.
                    pass
                if scenario == "worker_success":
                    return worker_result
                raise worker_error

            class Fallback:
                def encode(self, _texts: Sequence[str]) -> list[list[float]]:
                    calls["fallback"] += 1
                    events.append("fallback")
                    if scenario == "double_failure":
                        raise fallback_error
                    return fallback_result

            def fallback_factory() -> Fallback:
                calls["factory"] += 1
                events.append("factory")
                return Fallback()

            def warn(message: str) -> None:
                warnings.append(message)
                print(message, file=warning_output)

            result: object | None = None
            raised: BaseException | None = None
            with ExitStack() as stack:
                if inject_fault:
                    fault = InjectedTelemetryFault("private telemetry fault")
                    for method in (
                        "observe_worker_state",
                        "mark_success",
                        "mark_error",
                    ):
                        stack.enter_context(
                            patch.object(
                                producer.InferenceRequestTelemetry,
                                method,
                                side_effect=fault,
                            )
                        )
                with self._trace(policy="worker_preferred") as (command, _captured):
                    session = _CommandEmbeddingWorkerSession(
                        base_worker,
                        warning_callback=warn,
                        encode_with_lifecycle=lifecycle_worker,
                    )
                    embedder = session.embedder("matrix", fallback_factory)
                    if scenario == "double_failure":
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
                                with telemetry_span(QUERY_EMBED_SPAN_NAME):
                                    embedder.encode(["query"])
                        except BaseException as exc:
                            raised = exc
                        command.finish(1, error_type="model_error")  # type: ignore[attr-defined]
                    else:
                        result = self._complete_explicit_trace(
                            command,
                            lambda: embedder.encode(["query"]),
                        )
            return {
                "calls": calls,
                "lifecycle": lifecycle,
                "warnings": warnings,
                "warning_output": warning_output.getvalue(),
                "events": events,
                "result": result,
                "expected_result": (
                    worker_result
                    if scenario == "worker_success"
                    else fallback_result
                ),
                "raised": raised,
                "expected_error": fallback_error,
            }

        expected = {
            "worker_success": {
                "calls": {"base": 0, "worker": 1, "factory": 0, "fallback": 0},
                "lifecycle": ["reused"],
                "events": ["worker"],
                "warning_count": 0,
            },
            "fallback_success": {
                "calls": {"base": 0, "worker": 1, "factory": 1, "fallback": 1},
                "lifecycle": ["unknown"],
                "events": ["worker", "factory", "fallback"],
                "warning_count": 1,
            },
            "double_failure": {
                "calls": {"base": 0, "worker": 1, "factory": 1, "fallback": 1},
                "lifecycle": ["unknown"],
                "events": ["worker", "factory", "fallback"],
                "warning_count": 1,
            },
        }
        for scenario, contract in expected.items():
            with self.subTest(scenario=scenario):
                enabled = run_scenario(scenario, inject_fault=False)
                faulted = run_scenario(scenario, inject_fault=True)
                for observed in (enabled, faulted):
                    self.assertEqual(observed["calls"], contract["calls"])
                    self.assertEqual(observed["lifecycle"], contract["lifecycle"])
                    self.assertEqual(observed["events"], contract["events"])
                    self.assertEqual(
                        len(observed["warnings"]), contract["warning_count"]
                    )
                    if scenario == "double_failure":
                        self.assertIs(
                            observed["raised"], observed["expected_error"]
                        )
                        self.assertIsNone(observed["result"])
                    else:
                        self.assertIs(
                            observed["result"], observed["expected_result"]
                        )
                        self.assertIsNone(observed["raised"])
                self.assertEqual(faulted["calls"], enabled["calls"])
                self.assertEqual(faulted["lifecycle"], enabled["lifecycle"])
                self.assertEqual(faulted["warnings"], enabled["warnings"])
                self.assertEqual(faulted["warning_output"], enabled["warning_output"])
                self.assertEqual(faulted["events"], enabled["events"])

    def test_full_prohibited_sentinel_matrix_is_absent(self) -> None:
        sentinels = {
            "query": "SENTINEL_QUERY_TEXT",
            "passage": "SENTINEL_PASSAGE_TEXT",
            "vector": "12345.67891",
            "score": "98765.43219",
            "pid": "SENTINEL_WORKER_PID",
            "path": "SENTINEL_SOCKET_PATH",
            "model": "SENTINEL_CUSTOM_MODEL",
            "credential": "SENTINEL_PROVIDER_CREDENTIAL",
            "provider": "SENTINEL_PROVIDER_RESPONSE",
            "exception": "SENTINEL_RAW_EXCEPTION",
            "context": "SENTINEL_AMBIENT_CONTEXT",
            "frame": "SENTINEL_WORKER_FRAME",
        }

        class PrivacyEmbedder:
            def encode(self, _texts: Sequence[str]) -> list[list[float]]:
                return [[12345.67891]]

        class PrivacyReranker:
            def score(self, _query: str, passages: Sequence[str]) -> list[float]:
                self.assert_passages = list(passages)
                return [98765.43219]

        def failed_worker(
            _texts: Sequence[str],
            observer: Callable[[str], None],
        ) -> list[list[float]]:
            observer("unknown")
            raw = RuntimeError("|".join(sentinels.values()))
            raise EmbeddingWorkerError("busy_timeout") from raw

        with patch.dict(
            os.environ,
            {
                "TURBOPUFFER_API_KEY": sentinels["credential"],
                "AMBIENT_TRACE_CONTEXT": sentinels["context"],
            },
        ):
            with self._trace(
                policy="worker_preferred",
                retrieval_mode="explicit_multi",
            ) as (command, captured):
                with command.stage("buoy.retrieve.prepare"):  # type: ignore[attr-defined]
                    pass
                with retrieval_trace(
                    mode="explicit_multi",
                    embedding_model=sentinels["model"],
                    embedding_precision="float32",
                    top_k=5,
                    candidates=10,
                    namespace_count=1,
                    initial_fanout=1,
                ) as pipeline:
                    session = _CommandEmbeddingWorkerSession(
                        lambda _texts: [],
                        warning_callback=lambda _message: None,
                        encode_with_lifecycle=failed_worker,
                    )
                    with telemetry_span(QUERY_EMBED_SPAN_NAME) as span:
                        session.embedder("privacy", PrivacyEmbedder).encode(
                            [sentinels["query"]]
                        )
                        span.mark_ok()
                    with telemetry_span(
                        NAMESPACE_QUERY_SPAN_NAME,
                        {"buoy.route.rank": 1},
                    ) as span:
                        span.set_attributes(
                            {
                                "buoy.namespace.status": "ok",
                                "buoy.namespace.hit_count": 1,
                            }
                        )
                        span.mark_ok()
                    with telemetry_span(RERANK_SPAN_NAME) as span:
                        session.reranker(PrivacyReranker).score(
                            sentinels["query"],
                            [sentinels["passage"]],
                        )
                        span.mark_ok()
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
        payload = encode_trace_envelope_v3(
            self._rows_from_capture(captured)
        ).decode()

        for name, sentinel in sentinels.items():
            with self.subTest(name=name):
                self.assertNotIn(sentinel, payload)


if __name__ == "__main__":
    unittest.main()
