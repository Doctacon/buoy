from __future__ import annotations

import asyncio
from concurrent.futures import CancelledError as FuturesCancelledError
from contextlib import redirect_stderr, redirect_stdout
from contextvars import ContextVar
from dataclasses import dataclass
from io import StringIO
import json
import threading
import unittest
from unittest.mock import patch

import buoy_search.retrieval._provider_invocation_receipt as receipt
from buoy_search.cli.main import main
from buoy_search.config import RuntimeConfig
from buoy_search.retrieval.retriever import (
    EvidenceRouteContext,
    HybridRetriever,
    MultiNamespaceRetriever,
    ProviderCallError,
    RetrievalOptions,
    _invoke_content_expression,
    run_multi_query,
)


PRIVATE_QUERY = "QUERY_PRIVATE_SENTINEL"
PRIVATE_NAMESPACE = "NAMESPACE_PRIVATE_SENTINEL"
PRIVATE_CONTENT = "CONTENT_PRIVATE_SENTINEL"
PRIVATE_PATH = "PATH_PRIVATE_SENTINEL"
PRIVATE_ERROR = "ERROR_PRIVATE_SENTINEL"


def response(row_id: str = "row") -> dict[str, object]:
    return {
        "rows": [
            {
                "id": row_id,
                "attributes": {
                    "title": PRIVATE_CONTENT,
                    "content": PRIVATE_CONTENT,
                    "path": PRIVATE_PATH,
                },
            }
        ]
    }


class Embedder:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def encode(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        return [[0.1, 0.2, 0.3]]


class Reranker:
    def score(self, _query: str, passages: list[str]) -> list[float]:
        return [float(len(passages) - index) for index in range(len(passages))]


class ScriptedNamespace:
    def __init__(
        self,
        script: list[object],
        *,
        barrier: threading.Barrier | None = None,
        unrelated: ContextVar[str] | None = None,
    ) -> None:
        self.script = list(script)
        self.calls: list[dict[str, object]] = []
        self.barrier = barrier
        self.unrelated = unrelated
        self.unrelated_values: list[str] = []
        self._lock = threading.Lock()

    def multi_query(self, **kwargs: object) -> object:
        with self._lock:
            self.calls.append(dict(kwargs))
            if self.unrelated is not None:
                self.unrelated_values.append(self.unrelated.get())
            if self.barrier is not None and len(self.calls) == 1:
                barrier = self.barrier
            else:
                barrier = None
            if not self.script:
                raise AssertionError("script exhausted")
            item = self.script.pop(0)
        if barrier is not None:
            barrier.wait(timeout=5)
        if isinstance(item, BaseException):
            raise item
        return item


class LocalSignatureNamespace:
    def __init__(self) -> None:
        self.body_calls = 0
        self.queries: object | None = None

    def multi_query(self, *, queries: object) -> object:
        self.body_calls += 1
        self.queries = queries
        return response()


class FixedExceptionNamespace:
    def __init__(self, exc: BaseException) -> None:
        self.exc = exc
        self.calls: list[dict[str, object]] = []

    def multi_query(self, **kwargs: object) -> object:
        self.calls.append(dict(kwargs))
        raise self.exc


@dataclass(frozen=True)
class Decision:
    status: str = "sufficient_evidence"
    is_weak: bool | None = False

    def to_dict(self) -> dict[str, object]:
        return {"status": self.status, "reason": "test", "model": "test"}


class Assessor:
    mode = "collect"

    def __init__(self) -> None:
        self.calls = 0

    def assess(self, **_kwargs: object) -> Decision:
        self.calls += 1
        return Decision()


ROUTE_CONTEXT = EvidenceRouteContext(
    selection_reason="high_confidence_semantic",
    semantic_score=0.9,
    semantic_margin=0.2,
)


def single(namespace: object, *, namespace_name: str = PRIVATE_NAMESPACE) -> HybridRetriever:
    return HybridRetriever(
        namespace=namespace,
        embedder=Embedder(),
        config=RuntimeConfig(namespace=namespace_name),
    )


def multi(namespaces: list[object]) -> MultiNamespaceRetriever:
    embedder = Embedder()
    retrievers = [
        HybridRetriever(
            namespace=namespace,
            embedder=embedder,
            config=RuntimeConfig(namespace=f"{PRIVATE_NAMESPACE}-{index}"),
        )
        for index, namespace in enumerate(namespaces, start=1)
    ]
    return MultiNamespaceRetriever(
        retrievers=retrievers,
        embedder=embedder,
        reranker_loader=Reranker,
    )


def payload(handle: object) -> dict[str, object]:
    data = handle.receipt()  # type: ignore[attr-defined]
    if data is None:
        raise AssertionError("receipt unexpectedly unavailable")
    return json.loads(data)


def operations(handle: object) -> list[dict[str, object]]:
    return payload(handle)["content"]["operations"]  # type: ignore[index,return-value]


def schema_error(attribute: str) -> RuntimeError:
    return RuntimeError(f'attribute "{attribute}" not found in schema: {PRIVATE_ERROR}')


UNSUPPORTED = "multi_query() got an unexpected keyword argument 'rerank_by'"


class ContentAttemptGrammarTests(unittest.TestCase):
    def test_exact_one_through_six_attempt_grammar(self) -> None:
        scripts = {
            1: [response()],
            2: [TypeError(UNSUPPORTED), response()],
            3: [schema_error("tags"), TypeError(UNSUPPORTED), response()],
            4: [
                TypeError(UNSUPPORTED),
                schema_error("tags"),
                TypeError(UNSUPPORTED),
                response(),
            ],
            5: [
                schema_error("tags"),
                TypeError(UNSUPPORTED),
                schema_error("repo_path"),
                TypeError(UNSUPPORTED),
                response(),
            ],
            6: [
                TypeError(UNSUPPORTED),
                schema_error("tags"),
                TypeError(UNSUPPORTED),
                schema_error("repo_path"),
                TypeError(UNSUPPORTED),
                response(),
            ],
        }
        for count, script in scripts.items():
            with self.subTest(count=count):
                namespace = ScriptedNamespace(script)
                with receipt._provider_invocation_receipt_scope() as handle:
                    result = single(namespace).retrieve(
                        PRIVATE_QUERY, RetrievalOptions(top_k=1, candidates=2)
                    )
                operation = operations(handle)[0]
                attempts = operation["attempts"]
                self.assertEqual(result.hits[0].id, "row")
                self.assertEqual(operation["route_rank"], 1)
                self.assertEqual(operation["outcome"], "success")
                self.assertEqual(len(attempts), count)
                self.assertEqual(
                    [item["attempt_index"] for item in attempts],
                    list(range(1, count + 1)),
                )
                for index, (attempt, call) in enumerate(
                    zip(attempts, namespace.calls, strict=True)
                ):
                    expected_form = (
                        "server_rrf" if "rerank_by" in call else "client_rrf"
                    )
                    self.assertEqual(attempt["request_form"], expected_form)
                    self.assertEqual(
                        call.get("rerank_by"),
                        ("RRF",) if expected_form == "server_rrf" else None,
                    )
                    self.assertEqual(len(call["queries"]), 2)
                    if index == 0:
                        self.assertEqual(attempt["trigger"], "initial")
                    elif expected_form == "client_rrf":
                        self.assertEqual(
                            attempt["trigger"], "server_rrf_unsupported"
                        )
                    else:
                        self.assertEqual(
                            attempt["trigger"], "optional_schema_compatibility"
                        )
                self.assertEqual(attempts[-1]["outcome"], "success")
                self.assertIsNone(attempts[-1]["error_category"])

    def test_one_and_two_optional_removals_without_client_fallback(self) -> None:
        for missing in (("tags",), ("tags", "repo_path")):
            with self.subTest(missing=missing):
                namespace = ScriptedNamespace(
                    [*(schema_error(attribute) for attribute in missing), response()]
                )
                with receipt._provider_invocation_receipt_scope() as handle:
                    single(namespace).retrieve(PRIVATE_QUERY, RetrievalOptions())
                attempts = operations(handle)[0]["attempts"]
                self.assertEqual(len(attempts), len(missing) + 1)
                self.assertEqual(
                    [item["request_form"] for item in attempts],
                    ["server_rrf"] * (len(missing) + 1),
                )
                self.assertEqual(attempts[0]["trigger"], "initial")
                self.assertEqual(
                    [item["trigger"] for item in attempts[1:]],
                    ["optional_schema_compatibility"] * len(missing),
                )

    def test_local_signature_rejection_counts_before_method_body_then_falls_back(self) -> None:
        namespace = LocalSignatureNamespace()
        queries = [{"private": object()}]
        with receipt._provider_invocation_receipt_scope() as handle:
            with receipt._content_operation(1) as observer:
                returned, fusion = run_multi_query(
                    namespace,
                    queries,
                    _content_observer=observer,
                )
        attempts = operations(handle)[0]["attempts"]
        self.assertEqual(returned["rows"][0]["attributes"]["content"], PRIVATE_CONTENT)
        self.assertEqual(fusion, "client_rrf")
        self.assertEqual(namespace.body_calls, 1)
        self.assertIs(namespace.queries, queries)
        self.assertEqual(
            [(item["request_form"], item["outcome"]) for item in attempts],
            [("server_rrf", "error"), ("client_rrf", "success")],
        )
        self.assertEqual(attempts[0]["error_category"], "unexpected_error")

    def test_unrelated_error_adds_no_retry_and_post_response_error_adds_no_attempt(self) -> None:
        unrelated = ScriptedNamespace([RuntimeError(f"unrelated {PRIVATE_ERROR}")])
        with receipt._provider_invocation_receipt_scope() as unrelated_handle:
            with self.assertRaises(ProviderCallError):
                single(unrelated).retrieve(PRIVATE_QUERY, RetrievalOptions())
        unrelated_operation = operations(unrelated_handle)[0]
        self.assertEqual(len(unrelated.calls), 1)
        self.assertEqual(len(unrelated_operation["attempts"]), 1)
        self.assertEqual(unrelated_operation["attempts"][0]["outcome"], "error")
        self.assertEqual(unrelated_operation["outcome"], "error")

        malformed = ScriptedNamespace(
            [{"rows": [{"id": "bad", "attributes": {"tags": "bad"}}]}]
        )
        with receipt._provider_invocation_receipt_scope() as malformed_handle:
            with self.assertRaises(ProviderCallError):
                single(malformed).retrieve(PRIVATE_QUERY, RetrievalOptions())
        malformed_operation = operations(malformed_handle)[0]
        self.assertEqual(len(malformed.calls), 1)
        self.assertEqual(malformed_operation["attempts"][0]["outcome"], "success")
        self.assertEqual(malformed_operation["outcome"], "error")

        interruption = KeyboardInterrupt(PRIVATE_ERROR)

        class InterruptingResponse:
            @property
            def rows(self) -> object:
                raise interruption

        interrupted = ScriptedNamespace([InterruptingResponse()])
        caught = None
        with receipt._provider_invocation_receipt_scope() as interrupted_handle:
            try:
                single(interrupted).retrieve(PRIVATE_QUERY, RetrievalOptions())
            except KeyboardInterrupt as raised:
                caught = raised
        interrupted_operation = operations(interrupted_handle)[0]
        self.assertIs(caught, interruption)
        self.assertEqual(len(interrupted.calls), 1)
        self.assertEqual(interrupted_operation["attempts"][0]["outcome"], "success")
        self.assertEqual(interrupted_operation["outcome"], "interrupted")

    def test_governed_expression_without_operation_runs_once_and_invalidates_only_receipt(
        self,
    ) -> None:
        marker = object()
        namespace = ScriptedNamespace([marker])
        queries = [{"query": object()}]
        with receipt._provider_invocation_receipt_scope() as handle:
            returned, fusion = run_multi_query(namespace, queries)
        self.assertIs(returned, marker)
        self.assertEqual(fusion, "server_rrf")
        self.assertEqual(len(namespace.calls), 1)
        self.assertIs(namespace.calls[0]["queries"], queries)
        self.assertIsNone(handle.receipt())

    def test_positional_server_and_keyword_client_observer_callbacks(self) -> None:
        calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

        class Observer:
            def _invoke(self, *args: object, **kwargs: object) -> object:
                calls.append((args, kwargs))
                callback = args[2] if args else kwargs["callback"]
                return callback()  # type: ignore[operator]

        marker = object()
        observer = Observer()
        self.assertIs(
            _invoke_content_expression(
                observer,
                request_form="server_rrf",
                trigger="initial",
                callback=lambda: marker,
            ),
            marker,
        )
        self.assertIs(
            _invoke_content_expression(
                observer,
                request_form="client_rrf",
                trigger="server_rrf_unsupported",
                callback=lambda: marker,
            ),
            marker,
        )
        self.assertEqual(calls[0][0][:2], ("server_rrf", "initial"))
        self.assertEqual(calls[0][1], {})
        self.assertEqual(calls[1][0], ())
        self.assertEqual(
            set(calls[1][1]), {"request_form", "trigger", "callback"}
        )

    def test_receipt_bytes_exclude_all_content_and_error_sentinels(self) -> None:
        namespace = ScriptedNamespace(
            [schema_error("tags"), response("PRIVATE_PROVIDER_SENTINEL")]
        )
        with receipt._provider_invocation_receipt_scope() as handle:
            single(namespace).retrieve(PRIVATE_QUERY, RetrievalOptions())
        data = handle.receipt()
        self.assertIsNotNone(data)
        for sentinel in (
            PRIVATE_QUERY,
            PRIVATE_NAMESPACE,
            PRIVATE_CONTENT,
            PRIVATE_PATH,
            PRIVATE_ERROR,
            "PRIVATE_PROVIDER_SENTINEL",
            "tags",
            "rerank_by",
        ):
            self.assertNotIn(sentinel.encode(), data)  # type: ignore[operator]


class ContentExceptionIdentityTests(unittest.TestCase):
    class CustomControlFlow(BaseException):
        pass

    def test_all_cancellation_control_flow_and_error_objects_are_identical(self) -> None:
        cases: list[tuple[BaseException, str]] = [
            (asyncio.CancelledError(PRIVATE_ERROR), "interrupted"),
            (FuturesCancelledError(PRIVATE_ERROR), "interrupted"),
            (KeyboardInterrupt(PRIVATE_ERROR), "interrupted"),
            (SystemExit(PRIVATE_ERROR), "interrupted"),
            (GeneratorExit(PRIVATE_ERROR), "interrupted"),
            (self.CustomControlFlow(PRIVATE_ERROR), "interrupted"),
            (ValueError(PRIVATE_ERROR), "error"),
            (RuntimeError(PRIVATE_ERROR), "error"),
            (TypeError(PRIVATE_ERROR), "error"),
        ]
        for exc, expected in cases:
            with self.subTest(exc=type(exc).__name__):
                namespace = FixedExceptionNamespace(exc)
                caught = None
                with receipt._provider_invocation_receipt_scope() as handle:
                    try:
                        with receipt._content_operation(1) as observer:
                            run_multi_query(
                                namespace,
                                [],
                                _content_observer=observer,
                            )
                    except BaseException as raised:
                        caught = raised
                self.assertIs(caught, exc)
                self.assertEqual(len(namespace.calls), 1)
                operation = operations(handle)[0]
                self.assertEqual(operation["outcome"], expected)
                self.assertEqual(operation["attempts"][0]["outcome"], expected)

    def test_transformed_futures_cancellation_keeps_external_behavior_and_receipt_authority(
        self,
    ) -> None:
        baseline_exc = FuturesCancelledError(PRIVATE_ERROR)
        baseline = None
        try:
            single(FixedExceptionNamespace(baseline_exc)).retrieve(
                PRIVATE_QUERY, RetrievalOptions()
            )
        except ProviderCallError as raised:
            baseline = raised

        exc = FuturesCancelledError(PRIVATE_ERROR)
        namespace = FixedExceptionNamespace(exc)
        caught = None
        with receipt._provider_invocation_receipt_scope() as handle:
            try:
                single(namespace).retrieve(PRIVATE_QUERY, RetrievalOptions())
            except ProviderCallError as raised:
                caught = raised
        self.assertIsNotNone(baseline)
        self.assertIsNotNone(caught)
        assert baseline is not None
        assert caught is not None
        self.assertIs(type(caught), type(baseline))
        self.assertEqual(str(caught), str(baseline))
        self.assertIn("Provider error: CancelledError", str(caught))
        self.assertNotIn(PRIVATE_ERROR, str(caught))
        self.assertIsNone(caught.__cause__)
        self.assertEqual(caught.__suppress_context__, baseline.__suppress_context__)
        self.assertIs(caught.__context__, exc)
        self.assertIs(baseline.__context__, baseline_exc)
        operation = operations(handle)[0]
        self.assertEqual(operation["outcome"], "interrupted")
        self.assertEqual(operation["attempts"][0]["outcome"], "interrupted")
        self.assertEqual(len(namespace.calls), 1)


class ContentRouteAndFanoutTests(unittest.TestCase):
    def test_explicit_single_is_route_one(self) -> None:
        namespace = ScriptedNamespace([response()])
        with receipt._provider_invocation_receipt_scope() as handle:
            result = single(namespace).retrieve(PRIVATE_QUERY, RetrievalOptions())
        self.assertEqual(result.hits[0].id, "row")
        self.assertEqual([item["route_rank"] for item in operations(handle)], [1])

    def test_cli_explicit_multi_two_and_three_routes(self) -> None:
        for fanout in (2, 3):
            with self.subTest(fanout=fanout):
                retriever = multi(
                    [ScriptedNamespace([response(str(index))]) for index in range(fanout)]
                )
                argv = ["retrieve", PRIVATE_QUERY, "--json"]
                for index in range(fanout):
                    argv.extend(["--namespace", f"site-{index}-v1"])
                with receipt._provider_invocation_receipt_scope() as handle, patch(
                    "buoy_search.cli.main.MultiNamespaceRetriever.from_configs",
                    return_value=retriever,
                ), redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                    exit_code = main(argv)
                self.assertEqual(exit_code, 0)
                self.assertEqual(
                    [item["route_rank"] for item in operations(handle)],
                    list(range(1, fanout + 1)),
                )

    def test_three_concurrent_routes_serialize_atomically_with_eighteen_attempts(self) -> None:
        barrier = threading.Barrier(3)
        script = [
            TypeError(UNSUPPORTED),
            schema_error("tags"),
            TypeError(UNSUPPORTED),
            schema_error("repo_path"),
            TypeError(UNSUPPORTED),
            response(),
        ]
        namespaces = [
            ScriptedNamespace(list(script), barrier=barrier) for _ in range(3)
        ]
        unrelated = ContextVar("content-private-unrelated", default="worker-default")
        token = unrelated.set("AMBIENT_PRIVATE_SENTINEL")
        for namespace in namespaces:
            namespace.unrelated = unrelated
        try:
            with receipt._provider_invocation_receipt_scope() as handle:
                result = multi(namespaces).retrieve(
                    PRIVATE_QUERY, [RetrievalOptions()] * 3
                )
        finally:
            unrelated.reset(token)
        content = payload(handle)["content"]
        self.assertEqual(content["logical_operation_count"], 3)
        self.assertEqual(content["invocation_count"], 18)
        self.assertEqual(
            [item["route_rank"] for item in content["operations"]], [1, 2, 3]
        )
        self.assertTrue(all(len(item["attempts"]) == 6 for item in content["operations"]))
        self.assertEqual(len(result.namespace_results), 3)
        self.assertEqual(
            [value for namespace in namespaces for value in namespace.unrelated_values],
            ["worker-default"] * 18,
        )
        self.assertNotIn(b"AMBIENT_PRIVATE_SENTINEL", handle.receipt())

    def test_automatic_top_one_stop_and_empty_widening_reach_exact_routes(self) -> None:
        assessor = Assessor()
        top_one_namespaces = [
            ScriptedNamespace([response("one")]),
            ScriptedNamespace([response("two")]),
            ScriptedNamespace([response("three")]),
        ]
        with receipt._provider_invocation_receipt_scope() as top_one_handle:
            top_one = multi(top_one_namespaces).retrieve(
                PRIVATE_QUERY,
                [RetrievalOptions()] * 3,
                initial_fanout=1,
                evidence_assessor=assessor,
                evidence_route_context=ROUTE_CONTEXT,
            )
        self.assertFalse(top_one.fallback.widened)
        self.assertEqual([item["route_rank"] for item in operations(top_one_handle)], [1])
        self.assertEqual([len(item.calls) for item in top_one_namespaces], [1, 0, 0])

        widening_namespaces = [
            ScriptedNamespace([{"rows": []}]),
            ScriptedNamespace([response("two")]),
            ScriptedNamespace([response("three")]),
        ]
        with receipt._provider_invocation_receipt_scope() as widening_handle:
            widened = multi(widening_namespaces).retrieve(
                PRIVATE_QUERY,
                [RetrievalOptions()] * 3,
                initial_fanout=1,
                evidence_assessor=Assessor(),
                evidence_route_context=ROUTE_CONTEXT,
            )
        self.assertTrue(widened.fallback.widened)
        self.assertEqual(
            [item["route_rank"] for item in operations(widening_handle)], [1, 2, 3]
        )
        self.assertEqual([len(item.calls) for item in widening_namespaces], [1, 1, 1])

    def test_failed_top_one_widens_without_repeating_route_one(self) -> None:
        namespaces = [
            ScriptedNamespace([RuntimeError(PRIVATE_ERROR)]),
            ScriptedNamespace([response("two")]),
            ScriptedNamespace([response("three")]),
        ]
        with receipt._provider_invocation_receipt_scope() as handle:
            result = multi(namespaces).retrieve(
                PRIVATE_QUERY,
                [RetrievalOptions()] * 3,
                initial_fanout=1,
            )
        self.assertTrue(result.fallback.widened)
        self.assertEqual(result.fallback.reason, "failed_top1")
        self.assertEqual([len(item.calls) for item in namespaces], [1, 1, 1])
        self.assertEqual(
            [item["outcome"] for item in operations(handle)],
            ["error", "success", "success"],
        )

    def test_partial_and_all_failures_preserve_reached_route_outcomes(self) -> None:
        partial_namespaces = [
            ScriptedNamespace([response("one")]),
            ScriptedNamespace([RuntimeError(PRIVATE_ERROR)]),
            ScriptedNamespace([response("three")]),
        ]
        with receipt._provider_invocation_receipt_scope() as partial_handle:
            partial = multi(partial_namespaces).retrieve(
                PRIVATE_QUERY, [RetrievalOptions()] * 3
            )
        self.assertTrue(partial.incomplete)
        self.assertEqual(
            [item["outcome"] for item in operations(partial_handle)],
            ["success", "error", "success"],
        )

        all_namespaces = [
            ScriptedNamespace([RuntimeError(PRIVATE_ERROR)]) for _ in range(3)
        ]
        with receipt._provider_invocation_receipt_scope() as all_handle:
            with self.assertRaises(ProviderCallError):
                multi(all_namespaces).retrieve(
                    PRIVATE_QUERY, [RetrievalOptions()] * 3
                )
        self.assertEqual(
            [item["outcome"] for item in operations(all_handle)],
            ["error", "error", "error"],
        )

    def test_missing_reranker_stops_before_first_or_later_calls(self) -> None:
        def missing() -> Reranker:
            raise RuntimeError("reranker unavailable")

        before_namespaces = [
            ScriptedNamespace([response("one")]),
            ScriptedNamespace([response("two")]),
        ]
        before = multi(before_namespaces)
        before._reranker_loader = missing
        with receipt._provider_invocation_receipt_scope() as before_handle:
            with self.assertRaisesRegex(RuntimeError, "reranker unavailable"):
                before.retrieve(PRIVATE_QUERY, [RetrievalOptions()] * 2)
        self.assertEqual(operations(before_handle), [])
        self.assertEqual([len(item.calls) for item in before_namespaces], [0, 0])

        later_namespaces = [
            ScriptedNamespace([{"rows": []}]),
            ScriptedNamespace([response("two")]),
            ScriptedNamespace([response("three")]),
        ]
        later = multi(later_namespaces)
        later._reranker_loader = missing
        with receipt._provider_invocation_receipt_scope() as later_handle:
            with self.assertRaisesRegex(RuntimeError, "reranker unavailable"):
                later.retrieve(
                    PRIVATE_QUERY,
                    [RetrievalOptions()] * 3,
                    initial_fanout=1,
                )
        self.assertEqual([item["route_rank"] for item in operations(later_handle)], [1])
        self.assertEqual([len(item.calls) for item in later_namespaces], [1, 0, 0])

    def test_zero_attempt_pre_call_error_is_begun_and_terminal(self) -> None:
        exc = ValueError("pre-call")
        namespace = ScriptedNamespace([response()])
        caught = None
        with receipt._provider_invocation_receipt_scope() as handle:
            try:
                with patch(
                    "buoy_search.retrieval.retriever.build_multi_query_subqueries",
                    side_effect=exc,
                ):
                    single(namespace).retrieve(PRIVATE_QUERY, RetrievalOptions())
            except ValueError as raised:
                caught = raised
        operation = operations(handle)[0]
        self.assertIs(caught, exc)
        self.assertEqual(operation["outcome"], "error")
        self.assertEqual(operation["attempts"], [])
        self.assertEqual(namespace.calls, [])


class ContentFaultIsolationTests(unittest.TestCase):
    def assert_success_call(self, namespace: ScriptedNamespace, result: object) -> None:
        self.assertEqual(result.hits[0].id, "row")  # type: ignore[attr-defined]
        self.assertEqual(len(namespace.calls), 1)
        self.assertEqual(namespace.calls[0]["rerank_by"], ("RRF",))
        self.assertEqual(len(namespace.calls[0]["queries"]), 2)

    def test_disabled_and_every_ledger_observer_fault_are_call_equivalent(self) -> None:
        baseline_namespace = ScriptedNamespace([response()])
        baseline = single(baseline_namespace).retrieve(
            PRIVATE_QUERY, RetrievalOptions(top_k=1, candidates=2)
        )
        self.assert_success_call(baseline_namespace, baseline)
        baseline_calls = baseline_namespace.calls

        for method in (
            "_begin_content",
            "_begin_content_attempt",
            "_complete_content_attempt",
            "_complete_content",
        ):
            with self.subTest(method=method):
                namespace = ScriptedNamespace([response()])
                with receipt._provider_invocation_receipt_scope() as handle:
                    ledger = receipt._active_ledger()
                    assert ledger is not None
                    with patch.object(
                        ledger, method, side_effect=RuntimeError("observer fault")
                    ):
                        result = single(namespace).retrieve(
                            PRIVATE_QUERY,
                            RetrievalOptions(top_k=1, candidates=2),
                        )
                self.assert_success_call(namespace, result)
                self.assertEqual(namespace.calls, baseline_calls)
                self.assertEqual(result.to_dict(), baseline.to_dict())
                self.assertIsNone(handle.receipt())

    def test_observer_access_fault_runs_exact_expression_once(self) -> None:
        class BrokenObserver:
            @property
            def _invoke(self) -> object:
                raise RuntimeError("observer access fault")

        marker = object()
        calls = 0

        def callback() -> object:
            nonlocal calls
            calls += 1
            return marker

        with receipt._provider_invocation_receipt_scope() as handle:
            with receipt._content_operation(1):
                returned = _invoke_content_expression(
                    BrokenObserver(),
                    request_form="server_rrf",
                    trigger="initial",
                    callback=callback,
                )
        self.assertIs(returned, marker)
        self.assertEqual(calls, 1)
        self.assertIsNone(handle.receipt())

    def test_submission_failure_preserves_exception_identity_and_makes_receipt_unknown(
        self,
    ) -> None:
        exc = RuntimeError("submission fault")
        namespace = ScriptedNamespace([response()])
        caught = None
        with receipt._provider_invocation_receipt_scope() as handle:
            try:
                with patch(
                    "buoy_search.retrieval.retriever.ThreadPoolExecutor.submit",
                    side_effect=exc,
                ):
                    multi([namespace]).retrieve(PRIVATE_QUERY, [RetrievalOptions()])
            except RuntimeError as raised:
                caught = raised
        self.assertIs(caught, exc)
        self.assertEqual(namespace.calls, [])
        self.assertIsNone(handle.receipt())

    def test_worker_lease_registration_claim_and_release_faults_are_call_equivalent(
        self,
    ) -> None:
        for method in ("_register_lease", "_claim_lease", "_release_lease"):
            with self.subTest(method=method):
                namespace = ScriptedNamespace([response()])
                with receipt._provider_invocation_receipt_scope() as handle:
                    ledger = receipt._active_ledger()
                    assert ledger is not None
                    with patch.object(
                        ledger, method, side_effect=RuntimeError("lease fault")
                    ):
                        result = multi([namespace]).retrieve(
                            PRIVATE_QUERY, [RetrievalOptions()]
                        )
                self.assert_success_call(namespace, result)
                self.assertIsNone(handle.receipt())

    def test_worker_bind_and_reset_faults_are_call_equivalent(self) -> None:
        original_context = receipt._ACTIVE_LEDGER

        class FaultContext:
            def __init__(self, *, fail: str) -> None:
                self.fail = fail

            def get(self) -> object:
                return original_context.get()

            def set(self, value: object) -> object:
                if (
                    self.fail == "set"
                    and threading.current_thread() is not threading.main_thread()
                ):
                    raise RuntimeError("bind fault")
                return original_context.set(value)  # type: ignore[arg-type]

            def reset(self, token: object) -> None:
                if (
                    self.fail == "reset"
                    and threading.current_thread() is not threading.main_thread()
                ):
                    raise RuntimeError("reset fault")
                original_context.reset(token)  # type: ignore[arg-type]

        for failure in ("set", "reset"):
            with self.subTest(failure=failure):
                namespace = ScriptedNamespace([response()])
                with receipt._provider_invocation_receipt_scope() as handle:
                    with patch.object(
                        receipt, "_ACTIVE_LEDGER", FaultContext(fail=failure)
                    ):
                        result = multi([namespace]).retrieve(
                            PRIVATE_QUERY, [RetrievalOptions()]
                        )
                self.assert_success_call(namespace, result)
                self.assertIsNone(handle.receipt())

    def test_worker_exception_identity_survives_receipt_propagation(self) -> None:
        exc = KeyboardInterrupt(PRIVATE_ERROR)
        namespace = FixedExceptionNamespace(exc)
        caught = None
        with receipt._provider_invocation_receipt_scope() as handle:
            try:
                multi([namespace]).retrieve(PRIVATE_QUERY, [RetrievalOptions()])
            except KeyboardInterrupt as raised:
                caught = raised
        self.assertIs(caught, exc)
        self.assertEqual(len(namespace.calls), 1)
        operation = operations(handle)[0]
        self.assertEqual(operation["outcome"], "interrupted")
        self.assertEqual(operation["attempts"][0]["outcome"], "interrupted")


if __name__ == "__main__":
    unittest.main()
