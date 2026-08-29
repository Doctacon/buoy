from __future__ import annotations

from contextlib import contextmanager
import json
import os
from typing import Callable, Iterator, Sequence
import unittest
from unittest.mock import patch

from buoy_search.retrieval import _provider_invocation_receipt as receipt
from buoy_search.telemetry import producer
from buoy_search.telemetry.envelope import (
    CommandTraceRowsV3,
    TraceEnvelopeError,
    command_trace_rows_from_spans_v3,
    decode_trace_envelope_v3,
    encode_trace_envelope_v3,
    provider_accounting_from_receipt,
)
from buoy_search.telemetry.producer import (
    EVIDENCE_SPAN_NAME,
    NAMESPACE_QUERY_SPAN_NAME,
    QUERY_EMBED_SPAN_NAME,
    RERANK_SPAN_NAME,
    retrieval_trace,
    retrieve_command_trace,
    safe_time_ns,
    telemetry_span,
)


class RetrieveProviderTelemetryV3Tests(unittest.TestCase):
    @contextmanager
    def _trace(
        self,
        *,
        retrieval_mode: str = "explicit_single",
        execution_mode: str = "preview",
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
        with patch.dict(os.environ, {"BUOY_TELEMETRY": "local"}), patch.object(
            producer,
            "_persist_command_trace_best_effort",
            side_effect=capture,
        ):
            with retrieve_command_trace(
                started_at_ns=started,
                bootstrap_ended_at_ns=started,
                execution_mode=execution_mode,
                retrieval_mode=retrieval_mode,
                inference_policy="compatibility_in_process",
                _schema_version=3,
            ) as command:
                yield command, captured
        self.assertEqual(len(captured), 1)

    def _finish_preview(self, command: object, *, automatic: bool = False) -> None:
        with command.stage("buoy.retrieve.prepare"):  # type: ignore[attr-defined]
            if automatic:
                with command.stage("buoy.routing.model"):  # type: ignore[attr-defined]
                    pass
                with command.stage("buoy.routing.catalog"):  # type: ignore[attr-defined]
                    pass
                with command.stage("buoy.routing.model"):  # type: ignore[attr-defined]
                    pass
                with command.stage("buoy.routing.select"):  # type: ignore[attr-defined]
                    pass
        with command.stage("buoy.output.render"):  # type: ignore[attr-defined]
            pass
        command.finish(0)  # type: ignore[attr-defined]

    def _finish_live_explicit(
        self,
        command: object,
        provider_call: Callable[[], None],
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
                embed.mark_ok()
            with telemetry_span(
                NAMESPACE_QUERY_SPAN_NAME,
                {"buoy.route.rank": 1},
            ) as namespace:
                provider_call()
                namespace.set_attributes(
                    {
                        "buoy.namespace.status": "ok",
                        "buoy.namespace.hit_count": 1,
                    }
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

    def _finish_live_multi(
        self,
        command: object,
        provider_call: Callable[[int], None],
    ) -> None:
        with command.stage("buoy.retrieve.prepare"):  # type: ignore[attr-defined]
            pass
        with retrieval_trace(
            mode="explicit_multi",
            embedding_model="BAAI/bge-small-en-v1.5",
            embedding_precision="float32",
            top_k=5,
            candidates=10,
            namespace_count=2,
            initial_fanout=2,
        ) as pipeline:
            with telemetry_span(QUERY_EMBED_SPAN_NAME) as embed:
                embed.mark_ok()
            for route_rank in (1, 2):
                with telemetry_span(
                    NAMESPACE_QUERY_SPAN_NAME,
                    {"buoy.route.rank": route_rank},
                ) as namespace:
                    provider_call(route_rank)
                    namespace.set_attributes(
                        {
                            "buoy.namespace.status": "ok",
                            "buoy.namespace.hit_count": 1,
                        }
                    )
                    namespace.mark_ok()
            with telemetry_span(RERANK_SPAN_NAME) as rerank:
                rerank.set_attributes(
                    {
                        "buoy.rerank.applied": True,
                        "buoy.rerank.candidates_before_dedupe": 2,
                        "buoy.rerank.candidates_after_dedupe": 2,
                        "buoy.reranker.model": (
                            "cross-encoder/ms-marco-MiniLM-L-6-v2"
                        ),
                        "buoy.reranker.revision": "a" * 40,
                    }
                )
                rerank.mark_ok()
            pipeline.set_attributes(
                {
                    "buoy.retrieval.outcome": "success",
                    "buoy.retrieval.hit_count": 2,
                    "buoy.retrieval.final_fanout": 2,
                }
            )
            pipeline.mark_ok()
        with command.stage("buoy.output.render"):  # type: ignore[attr-defined]
            pass
        command.finish(0)  # type: ignore[attr-defined]

    def _finish_live_automatic(self, command: object) -> None:
        with command.stage("buoy.retrieve.prepare"):  # type: ignore[attr-defined]
            with command.stage("buoy.routing.model"):  # type: ignore[attr-defined]
                pass
            with command.stage("buoy.routing.catalog"):  # type: ignore[attr-defined]
                observer = receipt._active_catalog_observer()
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
                NAMESPACE_QUERY_SPAN_NAME,
                {"buoy.route.rank": 1},
            ) as namespace:
                with receipt._content_operation(1) as provider:
                    provider._invoke("server_rrf", "initial", lambda: object())
                namespace.set_attributes(
                    {
                        "buoy.namespace.status": "ok",
                        "buoy.namespace.hit_count": 1,
                    }
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
                        "buoy.reranker.model": (
                            "cross-encoder/ms-marco-MiniLM-L-6-v2"
                        ),
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

    def _finish_automatic_prepare_error(
        self,
        command: object,
        *,
        enter_catalog: bool,
    ) -> None:
        try:
            with command.stage("buoy.retrieve.prepare"):  # type: ignore[attr-defined]
                with command.stage("buoy.routing.model"):  # type: ignore[attr-defined]
                    if not enter_catalog:
                        raise RuntimeError("model setup failed")
                with command.stage("buoy.routing.catalog"):  # type: ignore[attr-defined]
                    raise RuntimeError("catalog setup failed")
        except RuntimeError:
            pass
        command.finish(  # type: ignore[attr-defined]
            1,
            error_type="catalog_error" if enter_catalog else "model_error",
        )

    def _rows(self, captured: list[tuple[object, ...]]) -> CommandTraceRowsV3:
        spans, root_span_id, schema_version, provider_accounting = captured[0]
        self.assertEqual(schema_version, 3)
        self.assertIsInstance(root_span_id, int)
        self.assertIsInstance(provider_accounting, tuple)
        return command_trace_rows_from_spans_v3(
            spans,  # type: ignore[arg-type]
            root_span_id=root_span_id,  # type: ignore[arg-type]
            provider_accounting=provider_accounting,  # type: ignore[arg-type]
        )

    def test_explicit_preview_records_authoritative_zero_not_unavailable(self) -> None:
        with patch.object(
            receipt,
            "_provider_invocation_receipt_scope",
            wraps=receipt._provider_invocation_receipt_scope,
        ) as scope:
            with self._trace() as (command, captured):
                self._finish_preview(command)
        rows = self._rows(captured)
        payload = encode_trace_envelope_v3(rows)
        value = json.loads(payload)

        self.assertEqual(scope.call_count, 1)
        self.assertEqual(value["provider_accounting"]["status"], "complete")
        self.assertEqual(
            value["provider_accounting"]["content"],
            {"logical_operation_count": 0, "invocation_count": 0, "operations": []},
        )
        self.assertEqual(value["provider_accounting"]["catalog"]["outcome"], None)
        self.assertEqual(value["provider_accounting"]["catalog"]["invocation_count"], 0)
        self.assertEqual(decode_trace_envelope_v3(payload), rows)

    def test_content_attempts_preserve_fallback_and_outcomes(self) -> None:
        def provider_call() -> None:
            with receipt._content_operation(1) as operation:
                def unsupported() -> object:
                    raise TypeError("private signature detail")

                with self.assertRaises(TypeError):
                    operation._invoke("server_rrf", "initial", unsupported)
                self.assertEqual(
                    operation._invoke(
                        "client_rrf",
                        "server_rrf_unsupported",
                        lambda: "content",
                    ),
                    "content",
                )

        with self._trace(execution_mode="live") as (command, captured):
            self._finish_live_explicit(command, provider_call)
        content = self._rows(captured).provider_accounting[2]
        self.assertIsInstance(content, dict)
        assert isinstance(content, dict)

        self.assertEqual(content["logical_operation_count"], 1)
        self.assertEqual(content["invocation_count"], 2)
        operation = content["operations"][0]
        self.assertEqual(operation["route_rank"], 1)
        self.assertEqual(
            [attempt["request_form"] for attempt in operation["attempts"]],
            ["server_rrf", "client_rrf"],
        )
        self.assertEqual(
            [attempt["outcome"] for attempt in operation["attempts"]],
            ["error", "success"],
        )

    def test_minimum_catalog_read_records_five_separate_attempts(self) -> None:
        with self._trace(retrieval_mode="automatic") as (command, captured):
            observer = receipt._active_catalog_observer()
            self.assertIsNotNone(observer)
            assert observer is not None
            with observer._operation() as operation:
                operation._invoke("namespace_list_page", lambda: object())
                operation._invoke("metadata", lambda: object())
                operation._invoke("card_query_page", lambda: object())
                operation._invoke("card_query_page", lambda: object())
                operation._invoke("namespace_list_page", lambda: object())
            self._finish_preview(command, automatic=True)
        catalog = self._rows(captured).provider_accounting[3]
        self.assertIsInstance(catalog, dict)
        assert isinstance(catalog, dict)

        self.assertEqual(catalog["outcome"], "success")
        self.assertEqual(catalog["invocation_count"], 5)
        self.assertEqual(catalog["namespace_list_page"]["success"], 2)
        self.assertEqual(catalog["metadata"]["success"], 1)
        self.assertEqual(catalog["card_query_page"]["success"], 2)

    def test_mapper_accepts_content_rounds_and_catalog_upper_boundaries(self) -> None:
        attempts = []
        for round_index in range(3):
            attempts.extend(
                [
                    {
                        "attempt_index": len(attempts) + 1,
                        "request_form": "server_rrf",
                        "trigger": (
                            "initial"
                            if round_index == 0
                            else "optional_schema_compatibility"
                        ),
                        "outcome": "error",
                        "error_category": "unexpected_error",
                    },
                    {
                        "attempt_index": len(attempts) + 2,
                        "request_form": "client_rrf",
                        "trigger": "server_rrf_unsupported",
                        "outcome": "error",
                        "error_category": "runtime_error",
                    },
                ]
            )
        content = {
            "logical_operation_count": 1,
            "invocation_count": 6,
            "operations": [
                {
                    "route_rank": 1,
                    "outcome": "error",
                    "attempts": attempts,
                }
            ],
        }
        complete_catalog = {
            "outcome": "success",
            "invocation_count": 40_001,
            "namespace_list_page": {
                "success": 20_000,
                "error": 0,
                "interrupted": 0,
            },
            "metadata": {"success": 1, "error": 0, "interrupted": 0},
            "card_query_page": {
                "success": 20_000,
                "error": 0,
                "interrupted": 0,
            },
        }
        terminal_catalog = json.loads(json.dumps(complete_catalog))
        terminal_catalog["outcome"] = "error"
        terminal_catalog["invocation_count"] = 40_002
        terminal_catalog["namespace_list_page"]["success"] = 20_001

        def encoded(catalog: object) -> bytes:
            return json.dumps(
                {
                    "receipt_schema_version": 1,
                    "unit": "provider_client_invocation",
                    "content": content,
                    "catalog": catalog,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode()

        complete = provider_accounting_from_receipt(encoded(complete_catalog))
        terminal = provider_accounting_from_receipt(encoded(terminal_catalog))
        self.assertEqual(complete[0], "complete")
        self.assertEqual(terminal[0], "complete")
        self.assertEqual(complete[2]["invocation_count"], 6)  # type: ignore[index]
        self.assertEqual(complete[3]["invocation_count"], 40_001)  # type: ignore[index]
        self.assertEqual(terminal[3]["invocation_count"], 40_002)  # type: ignore[index]

        invalid_success = json.loads(json.dumps(terminal_catalog))
        invalid_success["outcome"] = "success"
        self.assertEqual(
            provider_accounting_from_receipt(encoded(invalid_success))[0],
            "unavailable",
        )

    def test_missing_or_invalid_receipt_is_unavailable_never_zero(self) -> None:
        unavailable = (
            "unavailable",
            "provider_client_invocation",
            None,
            None,
        )
        invalid_values = (
            None,
            b"{}",
            b'{"catalog":null,"content":null,"receipt_schema_version":1,"unit":"wrong"}',
            (
                b'{"catalog":null,"content":null,"receipt_schema_version":true,'
                b'"unit":"provider_client_invocation"}'
            ),
            (
                b'{"catalog":null,"catalog":null,"content":null,'
                b'"receipt_schema_version":1,"unit":"provider_client_invocation"}'
            ),
        )
        for value in invalid_values:
            with self.subTest(value=value):
                self.assertEqual(provider_accounting_from_receipt(value), unavailable)

        class MissingHandle:
            def receipt(self) -> None:
                return None

        @contextmanager
        def missing_scope() -> Iterator[MissingHandle]:
            yield MissingHandle()

        with patch.object(receipt, "_provider_invocation_receipt_scope", missing_scope):
            with self._trace() as (command, captured):
                self._finish_preview(command)
        self.assertEqual(self._rows(captured).provider_accounting, unavailable)

    def test_disabled_and_v2_commands_do_not_enter_receipt_scope(self) -> None:
        started = safe_time_ns()
        assert started is not None
        with patch.object(
            receipt,
            "_provider_invocation_receipt_scope",
            side_effect=AssertionError("disabled/v2 command entered receipt scope"),
        ) as scope:
            with patch.dict(os.environ, {}, clear=True):
                with retrieve_command_trace(
                    started_at_ns=started,
                    bootstrap_ended_at_ns=started,
                    execution_mode="preview",
                    retrieval_mode="explicit_single",
                    _schema_version=3,
                ) as command:
                    self.assertFalse(command.enabled)
            with patch.dict(os.environ, {"BUOY_TELEMETRY": "local"}), patch.object(
                producer, "_persist_command_trace_best_effort"
            ):
                with retrieve_command_trace(
                    started_at_ns=started,
                    bootstrap_ended_at_ns=started,
                    execution_mode="preview",
                    retrieval_mode="explicit_single",
                    _schema_version=2,
                ) as command:
                    self._finish_preview(command)
            with patch.dict(os.environ, {"BUOY_TELEMETRY": "local"}), patch.object(
                producer, "_persist_trace_best_effort"
            ):
                with retrieval_trace(
                    mode="explicit_single",
                    embedding_model="BAAI/bge-small-en-v1.5",
                    embedding_precision="float32",
                    top_k=5,
                    candidates=10,
                    namespace_count=1,
                    initial_fanout=1,
                ) as operation:
                    operation.set_attributes(
                        {
                            "buoy.retrieval.outcome": "success",
                            "buoy.retrieval.final_fanout": 1,
                        }
                    )
                    operation.mark_ok()
        self.assertEqual(scope.call_count, 0)

    def test_command_exception_identity_survives_receipt_sealing(self) -> None:
        failure = RuntimeError("private command failure")
        captured: list[tuple[object, ...]] | None = None
        with self.assertRaises(RuntimeError) as raised:
            with self._trace() as (_command, observed):
                captured = observed
                with receipt._content_operation(1) as operation:
                    operation._invoke("server_rrf", "initial", lambda: object())
                raise failure
        self.assertIs(raised.exception, failure)
        self.assertIsNotNone(captured)
        assert captured is not None
        provider = captured[0][3]
        self.assertIsInstance(provider, tuple)
        assert isinstance(provider, tuple)
        self.assertEqual(provider[0], "complete")
        self.assertEqual(provider[2]["invocation_count"], 1)  # type: ignore[index]

    def test_nested_canary_remains_authoritative_and_v3_is_unavailable(self) -> None:
        with receipt._provider_invocation_receipt_scope() as outer:
            with self._trace() as (command, captured):
                with receipt._content_operation(1) as operation:
                    operation._invoke("server_rrf", "initial", lambda: object())
                self._finish_preview(command)
        outer_bytes = outer.receipt()
        self.assertIsNotNone(outer_bytes)
        self.assertEqual(self._rows(captured).provider_accounting[0], "unavailable")
        outer_provider = provider_accounting_from_receipt(outer_bytes)
        self.assertEqual(outer_provider[0], "complete")
        self.assertEqual(outer_provider[2]["invocation_count"], 1)  # type: ignore[index]

    def test_decoder_rejects_content_route_and_fanout_contradictions(self) -> None:
        def one_provider_call() -> None:
            with receipt._content_operation(1) as operation:
                operation._invoke("server_rrf", "initial", lambda: object())

        with self._trace(execution_mode="live") as (command, captured):
            self._finish_live_explicit(command, one_provider_call)
        single = json.loads(encode_trace_envelope_v3(self._rows(captured)))

        def ranked_provider_call(route_rank: int) -> None:
            with receipt._content_operation(route_rank) as operation:
                operation._invoke("server_rrf", "initial", lambda: object())

        with self._trace(
            retrieval_mode="explicit_multi",
            execution_mode="live",
        ) as (command, captured):
            self._finish_live_multi(command, ranked_provider_call)
        multi = json.loads(encode_trace_envelope_v3(self._rows(captured)))

        with self._trace(
            retrieval_mode="automatic",
            execution_mode="live",
        ) as (command, captured):
            self._finish_live_automatic(command)
        automatic = json.loads(encode_trace_envelope_v3(self._rows(captured)))

        extra_single_route = json.loads(json.dumps(single))
        extra_operation = json.loads(
            json.dumps(extra_single_route["provider_accounting"]["content"]["operations"][0])
        )
        extra_operation["route_rank"] = 2
        extra_single_route["provider_accounting"]["content"]["operations"].append(
            extra_operation
        )
        extra_single_route["provider_accounting"]["content"].update(
            {"logical_operation_count": 2, "invocation_count": 2}
        )

        partial_multi = json.loads(json.dumps(multi))
        partial_multi["retrieval_operation"].update(
            {
                "outcome": "partial",
                "hit_count": 1,
                "failure_count": 1,
                "incomplete": True,
            }
        )
        for span in partial_multi["spans"]:
            if span["name"] == "buoy.retrieve.pipeline":
                span["attributes"].update(
                    {
                        "buoy.retrieval.outcome": "partial",
                        "buoy.retrieval.hit_count": 1,
                        "buoy.retrieval.failure_count": 1,
                        "buoy.retrieval.incomplete": True,
                    }
                )
            if (
                span["name"] == NAMESPACE_QUERY_SPAN_NAME
                and span["attributes"].get("buoy.route.rank") == 2
            ):
                span["status_code"] = "ERROR"
                span["attributes"] = {
                    "buoy.route.rank": 2,
                    "buoy.namespace.status": "failed",
                    "buoy.error.type": "provider_call_error",
                }
        failed_provider = partial_multi["provider_accounting"]["content"][
            "operations"
        ][1]
        failed_provider["outcome"] = "error"
        failed_provider["attempts"][0].update(
            {"outcome": "error", "error_category": "runtime_error"}
        )
        decode_trace_envelope_v3(
            json.dumps(
                partial_multi,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        )
        post_provider_failure = json.loads(json.dumps(partial_multi))
        post_provider_operation = post_provider_failure["provider_accounting"][
            "content"
        ]["operations"][1]
        post_provider_operation["outcome"] = "success"
        post_provider_operation["attempts"][0].update(
            {"outcome": "success", "error_category": None}
        )
        decode_trace_envelope_v3(
            json.dumps(
                post_provider_failure,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        )

        missing_multi_route = json.loads(json.dumps(multi))
        missing_multi_route["provider_accounting"]["content"]["operations"].pop()
        missing_multi_route["provider_accounting"]["content"].update(
            {"logical_operation_count": 1, "invocation_count": 1}
        )

        missing_automatic_route = json.loads(json.dumps(automatic))
        missing_automatic_route["provider_accounting"]["content"] = {
            "logical_operation_count": 0,
            "invocation_count": 0,
            "operations": [],
        }

        terminal_mismatch = json.loads(json.dumps(single))
        provider_operation = terminal_mismatch["provider_accounting"]["content"][
            "operations"
        ][0]
        provider_operation["outcome"] = "error"
        provider_operation["attempts"][0].update(
            {"outcome": "error", "error_category": "runtime_error"}
        )

        for label, mutation in (
            ("explicit_single", extra_single_route),
            ("explicit_multi", missing_multi_route),
            ("automatic", missing_automatic_route),
            ("terminal_outcome", terminal_mismatch),
        ):
            with self.subTest(label=label), self.assertRaises(TraceEnvelopeError):
                decode_trace_envelope_v3(
                    json.dumps(
                        mutation,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode()
                )

    def test_catalog_reach_requires_an_actual_automatic_catalog_span(self) -> None:
        with self._trace(retrieval_mode="automatic") as (command, captured):
            self._finish_automatic_prepare_error(command, enter_catalog=False)
        failed_before_catalog = json.loads(
            encode_trace_envelope_v3(self._rows(captured))
        )
        self.assertIsNone(
            failed_before_catalog["provider_accounting"]["catalog"]["outcome"]
        )

        contradiction = json.loads(json.dumps(failed_before_catalog))
        contradiction["provider_accounting"]["catalog"] = {
            "outcome": "success",
            "invocation_count": 1,
            "namespace_list_page": {
                "success": 1,
                "error": 0,
                "interrupted": 0,
            },
            "metadata": {"success": 0, "error": 0, "interrupted": 0},
            "card_query_page": {"success": 0, "error": 0, "interrupted": 0},
        }
        with self.assertRaises(TraceEnvelopeError):
            decode_trace_envelope_v3(
                json.dumps(
                    contradiction,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            )

        with self._trace(retrieval_mode="automatic") as (command, captured):
            self._finish_automatic_prepare_error(command, enter_catalog=True)
        failed_in_catalog = encode_trace_envelope_v3(self._rows(captured))
        self.assertEqual(
            json.loads(failed_in_catalog)["provider_accounting"]["catalog"][
                "invocation_count"
            ],
            0,
        )
        decode_trace_envelope_v3(failed_in_catalog)

    def test_decoder_rejects_provider_shape_count_order_and_boolean_mutations(self) -> None:
        with self._trace(retrieval_mode="automatic") as (command, captured):
            observer = receipt._active_catalog_observer()
            assert observer is not None
            with observer._operation() as operation:
                operation._invoke("namespace_list_page", lambda: object())
                operation._invoke("metadata", lambda: object())
                operation._invoke("card_query_page", lambda: object())
                operation._invoke("card_query_page", lambda: object())
                operation._invoke("namespace_list_page", lambda: object())
            self._finish_preview(command, automatic=True)
        base = json.loads(encode_trace_envelope_v3(self._rows(captured)))

        mutations = []
        unknown = json.loads(json.dumps(base))
        unknown["provider_accounting"]["extra"] = 1
        mutations.append(unknown)
        bool_count = json.loads(json.dumps(base))
        bool_count["provider_accounting"]["catalog"]["invocation_count"] = True
        mutations.append(bool_count)
        mismatch = json.loads(json.dumps(base))
        mismatch["provider_accounting"]["catalog"]["invocation_count"] = 6
        mutations.append(mismatch)
        impossible_order = json.loads(json.dumps(base))
        impossible_order["provider_accounting"]["catalog"][
            "namespace_list_page"
        ]["success"] = 10_001
        impossible_order["provider_accounting"]["catalog"]["card_query_page"]["success"] = 1
        impossible_order["provider_accounting"]["catalog"]["invocation_count"] = 10_003
        mutations.append(impossible_order)
        overflow = json.loads(json.dumps(base))
        overflow["provider_accounting"]["catalog"]["invocation_count"] = 40_003
        mutations.append(overflow)
        mixed_terminal = json.loads(json.dumps(base))
        mixed_terminal["provider_accounting"]["catalog"]["outcome"] = "error"
        mixed_terminal["provider_accounting"]["catalog"]["metadata"] = {
            "success": 0,
            "error": 1,
            "interrupted": 0,
        }
        mixed_terminal["provider_accounting"]["catalog"]["card_query_page"] = {
            "success": 0,
            "error": 1,
            "interrupted": 0,
        }
        mixed_terminal["provider_accounting"]["catalog"]["invocation_count"] = 4
        mutations.append(mixed_terminal)
        preview_content = json.loads(json.dumps(base))
        missing_automatic_catalog = json.loads(json.dumps(base))
        missing_automatic_catalog["provider_accounting"]["catalog"] = {
            "outcome": None,
            "invocation_count": 0,
            "namespace_list_page": {"success": 0, "error": 0, "interrupted": 0},
            "metadata": {"success": 0, "error": 0, "interrupted": 0},
            "card_query_page": {"success": 0, "error": 0, "interrupted": 0},
        }
        mutations.append(missing_automatic_catalog)
        preview_content["provider_accounting"]["content"] = {
            "logical_operation_count": 1,
            "invocation_count": 1,
            "operations": [
                {
                    "route_rank": 1,
                    "outcome": "success",
                    "attempts": [
                        {
                            "attempt_index": 1,
                            "request_form": "server_rrf",
                            "trigger": "initial",
                            "outcome": "success",
                            "error_category": None,
                        }
                    ],
                }
            ],
        }
        mutations.append(preview_content)

        for mutation in mutations:
            with self.subTest(provider=mutation["provider_accounting"]):
                payload = json.dumps(
                    mutation,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
                with self.assertRaises(TraceEnvelopeError):
                    decode_trace_envelope_v3(payload)

    def test_governed_callback_privacy_inputs_are_absent_from_v3_bytes(self) -> None:
        sentinels = {
            name: f"private-{name}-sentinel"
            for name in (
                "query",
                "provider-response",
                "raw-error",
                "cursor",
                "header",
                "credential",
                "ambient-context",
            )
        }
        observed: dict[str, object] = {}

        class FakeProvider:
            def query(
                self,
                *,
                query: str,
                cursor: str,
                headers: dict[str, str],
                credential: str,
                fail: bool,
            ) -> dict[str, str]:
                observed.update(
                    {
                        "query": query,
                        "cursor": cursor,
                        "header": headers["x-private"],
                        "credential": credential,
                        "ambient": os.environ["PRIVATE_PROVIDER_CONTEXT"],
                    }
                )
                if fail:
                    raise TypeError(sentinels["raw-error"])
                return {"body": sentinels["provider-response"]}

        fake = FakeProvider()

        def invoke_fake(*, fail: bool) -> dict[str, str]:
            return fake.query(
                query=sentinels["query"],
                cursor=sentinels["cursor"],
                headers={"x-private": sentinels["header"]},
                credential=sentinels["credential"],
                fail=fail,
            )

        def provider_call() -> None:
            with receipt._content_operation(1) as operation:
                with self.assertRaises(TypeError) as raised:
                    operation._invoke(
                        "server_rrf",
                        "initial",
                        lambda: invoke_fake(fail=True),
                    )
                self.assertEqual(str(raised.exception), sentinels["raw-error"])
                response = operation._invoke(
                    "client_rrf",
                    "server_rrf_unsupported",
                    lambda: invoke_fake(fail=False),
                )
                self.assertEqual(response["body"], sentinels["provider-response"])

        with patch.dict(
            os.environ,
            {"PRIVATE_PROVIDER_CONTEXT": sentinels["ambient-context"]},
        ):
            with self._trace(execution_mode="live") as (command, captured):
                self._finish_live_explicit(command, provider_call)
        self.assertEqual(
            observed,
            {
                "query": sentinels["query"],
                "cursor": sentinels["cursor"],
                "header": sentinels["header"],
                "credential": sentinels["credential"],
                "ambient": sentinels["ambient-context"],
            },
        )
        payload = encode_trace_envelope_v3(self._rows(captured))

        self.assertIn(b"provider_client_invocation", payload)
        for name, sentinel in sentinels.items():
            with self.subTest(name=name):
                self.assertNotIn(sentinel.encode(), payload)


if __name__ == "__main__":
    unittest.main()
