from __future__ import annotations

import ast
import asyncio
from concurrent.futures import CancelledError as FuturesCancelledError, ThreadPoolExecutor
from contextlib import ExitStack, contextmanager, redirect_stderr, redirect_stdout
from contextvars import ContextVar
from io import StringIO
import json
import os
from pathlib import Path
from types import SimpleNamespace
import threading
import unittest
from unittest.mock import patch

import buoy_search
import buoy_search._provider_invocation_receipt as receipt
from buoy_search import cli
from buoy_search.telemetry import CommandTelemetry
from tests.test_provider_invocation_receipt_catalog import (
    REGION,
    FakeClient,
    make_card,
    make_client,
)
from tests.test_provider_invocation_receipt_content import (
    PRIVATE_CONTENT,
    PRIVATE_ERROR,
    PRIVATE_NAMESPACE,
    PRIVATE_PATH,
    PRIVATE_QUERY,
    Reranker,
    ScriptedNamespace,
    multi,
    response,
)


API_KEY = "tpuf_INTEGRATION_PRIVATE_CREDENTIAL"


class CollectDecision:
    status = "unassessed"
    is_weak = None

    def to_dict(self) -> dict[str, object]:
        return {"mode": "collect", "status": self.status, "reason": "test"}


class CollectAssessor:
    mode = "collect"

    def assess(self, **_kwargs: object) -> CollectDecision:
        return CollectDecision()


EVIDENCE_CALIBRATION = SimpleNamespace(
    mode="collect",
    model="fixed-private-model",
    model_revision="0" * 40,
    calibration_id="fixed",
    calibration_revision="fixed",
    feature_contract="fixed",
    threshold=None,
)


class FakeRouting:
    def __init__(self, cards: list[object], *, initial_fanout: int) -> None:
        self.selected_cards = cards
        self.initial_fanout = initial_fanout
        self.selection_reason = "high_confidence_semantic"
        self.semantic_margin = 0.25
        self.entries = [SimpleNamespace(semantic_score=0.9)]

    def to_dict(self) -> dict[str, object]:
        return {
            "active": True,
            "strategy": "title_alias_then_semantic",
            "catalog_namespace": "buoy-routing-catalog-v3",
            "region": REGION,
            "snapshot_revision": "fixed",
            "credentials_required": True,
            "read_only_api_calls_occurred": True,
            "content_retrieval_occurred": False,
            "routing_model": "fixed",
            "routing_model_revision": "0" * 40,
            "requested_limit": 3,
            "initial_fanout": self.initial_fanout,
            "selection_reason": self.selection_reason,
            "high_confidence": True,
            "semantic_confidence_floor": 0.0,
            "semantic_margin_floor": 0.0,
            "semantic_margin": self.semantic_margin,
            "selected_cards": [],
        }


@contextmanager
def automatic_runtime(
    client: object,
    *,
    retriever: object | None,
    fanout: int,
):
    def route(_query: str, cards: object, **_kwargs: object) -> FakeRouting:
        return FakeRouting(list(cards), initial_fanout=fanout)  # type: ignore[arg-type]

    with ExitStack() as stack:
        stack.enter_context(patch.object(os, "environ", {"TURBOPUFFER_API_KEY": API_KEY}))
        stack.enter_context(
            patch("buoy_search.cli.ROUTING_CONFIDENCE_FACTORY", return_value=SimpleNamespace(mode="collect"))
        )
        stack.enter_context(
            patch("buoy_search.cli.load_evidence_calibration", return_value=EVIDENCE_CALIBRATION)
        )
        stack.enter_context(
            patch("buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY", return_value=client)
        )
        stack.enter_context(
            patch("buoy_search.cli.ROUTING_EMBEDDER_FACTORY", return_value=object())
        )
        stack.enter_context(patch("buoy_search.cli.hybrid_route", side_effect=route))
        stack.enter_context(
            patch("buoy_search.cli.CalibratedEvidenceAssessor", return_value=CollectAssessor())
        )
        if retriever is None:
            stack.enter_context(
                patch(
                    "buoy_search.cli.MultiNamespaceRetriever.from_configs",
                    side_effect=AssertionError("preview constructed content retriever"),
                )
            )
        else:
            stack.enter_context(
                patch(
                    "buoy_search.cli.MultiNamespaceRetriever.from_configs",
                    return_value=retriever,
                )
            )
        yield


def run_automatic(
    client: object,
    *,
    retriever: object | None,
    fanout: int,
    preview: bool,
) -> tuple[int, str, str]:
    argv = ["retrieve", PRIVATE_QUERY, "--json"]
    if preview:
        argv.append("--dry-run")
    stdout = StringIO()
    stderr = StringIO()
    with automatic_runtime(client, retriever=retriever, fanout=fanout), redirect_stdout(
        stdout
    ), redirect_stderr(stderr):
        result = cli.main(argv)
    return result, stdout.getvalue(), stderr.getvalue()


def decoded(handle: object) -> dict[str, object]:
    data = handle.receipt()  # type: ignore[attr-defined]
    if data is None:
        raise AssertionError("receipt unexpectedly unavailable")
    receipt._decode_receipt(data)
    return json.loads(data)


class AutomaticReceiptIntegrationTests(unittest.TestCase):
    def test_automatic_preview_is_catalog_only_and_explicit_live_catalog_is_null(self) -> None:
        card = make_card("site-preview-v1")
        client, resource, _trace = make_client(cards=[card])
        with receipt._provider_invocation_receipt_scope() as automatic_handle:
            result, stdout, stderr = run_automatic(
                client, retriever=None, fanout=1, preview=True
            )
        automatic = decoded(automatic_handle)
        self.assertEqual((result, stderr), (0, ""))
        self.assertTrue(json.loads(stdout)["dry_run"])
        self.assertEqual(len(resource.query_calls), 2)
        self.assertEqual(automatic["catalog"]["outcome"], "success")  # type: ignore[index]
        self.assertEqual(automatic["catalog"]["invocation_count"], 5)  # type: ignore[index]
        self.assertEqual(automatic["content"]["logical_operation_count"], 0)  # type: ignore[index]
        self.assertEqual(automatic["content"]["invocation_count"], 0)  # type: ignore[index]

        namespace = ScriptedNamespace([response("explicit")])
        with receipt._provider_invocation_receipt_scope() as explicit_handle, patch(
            "buoy_search.cli.HybridRetriever.from_config",
            return_value=multi([namespace])._retrievers[0],
        ), patch.object(os, "environ", {}), redirect_stdout(StringIO()), redirect_stderr(
            StringIO()
        ):
            explicit_result = cli.main(
                [
                    "retrieve",
                    PRIVATE_QUERY,
                    "--namespace",
                    "site-explicit-v1",
                    "--json",
                ]
            )
        explicit = decoded(explicit_handle)
        self.assertEqual(explicit_result, 0)
        self.assertIsNone(explicit["catalog"]["outcome"])  # type: ignore[index]
        self.assertEqual(explicit["catalog"]["invocation_count"], 0)  # type: ignore[index]
        self.assertEqual(explicit["content"]["logical_operation_count"], 1)  # type: ignore[index]
        self.assertEqual(explicit["content"]["invocation_count"], 1)  # type: ignore[index]

    def test_explicit_preview_constructs_no_retriever_or_provider_and_records_zero(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        with receipt._provider_invocation_receipt_scope() as handle, patch(
            "buoy_search.cli.HybridRetriever.from_config",
            side_effect=AssertionError("explicit preview constructed retriever"),
        ) as single_retriever, patch(
            "buoy_search.cli.MultiNamespaceRetriever.from_configs",
            side_effect=AssertionError("explicit preview constructed multi retriever"),
        ) as multi_retriever, patch(
            "buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY",
            side_effect=AssertionError("explicit preview constructed provider client"),
        ) as provider, patch.object(os, "environ", {}), redirect_stdout(
            stdout
        ), redirect_stderr(stderr):
            result = cli.main(
                [
                    "retrieve",
                    PRIVATE_QUERY,
                    "--namespace",
                    "site-explicit-preview-v1",
                    "--dry-run",
                    "--json",
                ]
            )

        payload = decoded(handle)
        preview = json.loads(stdout.getvalue())
        self.assertEqual((result, stderr.getvalue()), (0, ""))
        self.assertEqual(
            {
                key: preview[key]
                for key in (
                    "command",
                    "dry_run",
                    "plan",
                    "credentials_required",
                    "turbopuffer_api_calls",
                    "api_calls_occurred",
                    "query",
                    "namespace",
                    "content_retrieval_occurred",
                )
            },
            {
                "command": "retrieve",
                "dry_run": True,
                "plan": True,
                "credentials_required": False,
                "turbopuffer_api_calls": False,
                "api_calls_occurred": False,
                "query": PRIVATE_QUERY,
                "namespace": "site-explicit-preview-v1",
                "content_retrieval_occurred": False,
            },
        )
        single_retriever.assert_not_called()
        multi_retriever.assert_not_called()
        provider.assert_not_called()
        self.assertEqual(
            payload["catalog"],
            {
                "outcome": None,
                "invocation_count": 0,
                "namespace_list_page": {
                    "success": 0,
                    "error": 0,
                    "interrupted": 0,
                },
                "metadata": {"success": 0, "error": 0, "interrupted": 0},
                "card_query_page": {
                    "success": 0,
                    "error": 0,
                    "interrupted": 0,
                },
            },
        )
        self.assertEqual(
            payload["content"],
            {
                "logical_operation_count": 0,
                "invocation_count": 0,
                "operations": [],
            },
        )

    def test_automatic_live_keeps_catalog_and_concurrent_worker_content_separate(self) -> None:
        barrier = threading.Barrier(3)
        cards = [make_card(f"site-live-{index}-v1") for index in range(1, 4)]
        client, _resource, _trace = make_client(cards=cards)
        unrelated = ContextVar("receipt-integration-private", default="worker-default")
        token = unrelated.set("AMBIENT_CONTEXT_PRIVATE_SENTINEL")
        namespaces = [
            ScriptedNamespace(
                [response(f"route-{index}")], barrier=barrier, unrelated=unrelated
            )
            for index in range(1, 4)
        ]
        try:
            with receipt._provider_invocation_receipt_scope() as outer:
                with receipt._provider_invocation_receipt_scope() as inner:
                    result, _stdout, stderr = run_automatic(
                        client,
                        retriever=multi(namespaces),
                        fanout=3,
                        preview=False,
                    )
                self.assertIsNone(inner.receipt())
        finally:
            unrelated.reset(token)
        payload = decoded(outer)
        self.assertEqual((result, stderr), (0, ""))
        self.assertEqual(payload["catalog"]["invocation_count"], 5)  # type: ignore[index]
        self.assertEqual(payload["catalog"]["outcome"], "success")  # type: ignore[index]
        self.assertEqual(payload["content"]["logical_operation_count"], 3)  # type: ignore[index]
        self.assertEqual(payload["content"]["invocation_count"], 3)  # type: ignore[index]
        self.assertEqual(
            [operation["route_rank"] for operation in payload["content"]["operations"]],  # type: ignore[index]
            [1, 2, 3],
        )
        self.assertEqual(
            [value for namespace in namespaces for value in namespace.unrelated_values],
            ["worker-default"] * 3,
        )
        self.assertNotIn(b"AMBIENT_CONTEXT_PRIVATE_SENTINEL", outer.receipt())

    def test_pre_call_partial_and_all_failure_receipts_are_terminal(self) -> None:
        client_failure = RuntimeError("CLIENT_FACTORY_PRIVATE_SENTINEL")
        unused_client, _resource, _trace = make_client(
            cards=[make_card("site-unused-v1")]
        )
        with receipt._provider_invocation_receipt_scope() as catalog_pre_handle:
            with automatic_runtime(
                unused_client, retriever=None, fanout=1
            ), patch(
                "buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY",
                side_effect=client_failure,
            ), redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                catalog_pre_result = cli.main(
                    ["retrieve", PRIVATE_QUERY, "--dry-run", "--json"]
                )
        catalog_pre = decoded(catalog_pre_handle)
        self.assertEqual(catalog_pre_result, 2)
        self.assertIsNone(catalog_pre["catalog"]["outcome"])  # type: ignore[index]
        self.assertEqual(catalog_pre["catalog"]["invocation_count"], 0)  # type: ignore[index]
        self.assertEqual(catalog_pre["content"]["invocation_count"], 0)  # type: ignore[index]

        pre_client, _resource, _trace = make_client(
            cards=[make_card("site-pre-call-v1")]
        )
        exact = ValueError("PRE_CALL_PRIVATE_SENTINEL")
        caught = None
        with receipt._provider_invocation_receipt_scope() as pre_handle, patch(
            "buoy_search.retriever.build_multi_query_subqueries", side_effect=exact
        ):
            try:
                run_automatic(
                    pre_client,
                    retriever=multi([ScriptedNamespace([response()])]),
                    fanout=1,
                    preview=False,
                )
            except ValueError as raised:
                caught = raised
        self.assertIs(caught, exact)
        pre = decoded(pre_handle)
        self.assertEqual(pre["catalog"]["outcome"], "success")  # type: ignore[index]
        self.assertEqual(pre["content"]["operations"][0]["outcome"], "error")  # type: ignore[index]
        self.assertEqual(pre["content"]["operations"][0]["attempts"], [])  # type: ignore[index]

        cases = (
            (
                "partial",
                [ScriptedNamespace([response("ok")]), ScriptedNamespace([RuntimeError(PRIVATE_ERROR)])],
                0,
                ["success", "error"],
            ),
            (
                "all",
                [ScriptedNamespace([RuntimeError(PRIVATE_ERROR)]) for _ in range(2)],
                2,
                ["error", "error"],
            ),
        )
        for name, namespaces, expected_exit, expected_outcomes in cases:
            with self.subTest(name=name):
                cards = [
                    make_card(f"site-{name}-{index}-v1")
                    for index in range(1, len(namespaces) + 1)
                ]
                client, _resource, _trace = make_client(cards=cards)
                with receipt._provider_invocation_receipt_scope() as handle:
                    result, _stdout, _stderr = run_automatic(
                        client,
                        retriever=multi(namespaces),
                        fanout=len(namespaces),
                        preview=False,
                    )
                payload = decoded(handle)
                self.assertEqual(result, expected_exit)
                self.assertEqual(payload["catalog"]["outcome"], "success")  # type: ignore[index]
                self.assertEqual(
                    [item["outcome"] for item in payload["content"]["operations"]],  # type: ignore[index]
                    expected_outcomes,
                )

    def test_automatic_content_cancellation_and_control_flow_handoff_matrix(self) -> None:
        class CustomControlFlow(BaseException):
            pass

        cases: list[tuple[BaseException, str, bool]] = [
            (asyncio.CancelledError(PRIVATE_ERROR), "interrupted", True),
            (FuturesCancelledError(PRIVATE_ERROR), "interrupted", False),
            (KeyboardInterrupt(PRIVATE_ERROR), "interrupted", True),
            (SystemExit(PRIVATE_ERROR), "interrupted", True),
            (GeneratorExit(PRIVATE_ERROR), "interrupted", True),
            (CustomControlFlow(PRIVATE_ERROR), "interrupted", True),
            (ValueError(PRIVATE_ERROR), "error", False),
            (RuntimeError(PRIVATE_ERROR), "error", False),
            (Exception(PRIVATE_ERROR), "error", False),
        ]
        for exc, expected_outcome, escapes in cases:
            with self.subTest(exc=type(exc).__name__):
                client, _resource, _trace = make_client(
                    cards=[make_card("site-control-v1")]
                )
                caught = None
                result = None
                with receipt._provider_invocation_receipt_scope() as handle:
                    try:
                        result, _stdout, _stderr = run_automatic(
                            client,
                            retriever=multi([ScriptedNamespace([exc])]),
                            fanout=1,
                            preview=False,
                        )
                    except BaseException as raised:
                        caught = raised
                payload = decoded(handle)
                operation = payload["content"]["operations"][0]  # type: ignore[index]
                self.assertEqual(operation["outcome"], expected_outcome)
                self.assertEqual(operation["attempts"][0]["outcome"], expected_outcome)
                if escapes:
                    self.assertIs(caught, exc)
                    self.assertIsNone(result)
                else:
                    self.assertIsNone(caught)
                    self.assertEqual(result, 2)

    def test_independent_concurrent_automatic_preview_scopes_do_not_cross_account(self) -> None:
        cards = [make_card("site-concurrent-v1")]
        clients: list[FakeClient] = []
        clients_lock = threading.Lock()

        def client_factory(**_kwargs: object) -> FakeClient:
            client, _resource, _trace = make_client(cards=cards)
            with clients_lock:
                clients.append(client)
            return client

        def route(_query: str, values: object, **_kwargs: object) -> FakeRouting:
            return FakeRouting(list(values), initial_fanout=1)  # type: ignore[arg-type]

        args = cli.build_parser().parse_args(
            ["retrieve", PRIVATE_QUERY, "--dry-run", "--json"]
        )
        receipts: list[bytes | None] = []
        statuses: list[int] = []
        barrier = threading.Barrier(2)

        def run() -> None:
            with receipt._provider_invocation_receipt_scope() as handle:
                barrier.wait(timeout=5)
                statuses.append(cli._run_retrieve(args, CommandTelemetry()))
            receipts.append(handle.receipt())

        with ExitStack() as stack:
            stack.enter_context(
                patch.object(os, "environ", {"TURBOPUFFER_API_KEY": API_KEY})
            )
            stack.enter_context(
                patch("buoy_search.cli.ROUTING_CONFIDENCE_FACTORY", return_value=SimpleNamespace(mode="collect"))
            )
            stack.enter_context(
                patch("buoy_search.cli.load_evidence_calibration", return_value=EVIDENCE_CALIBRATION)
            )
            stack.enter_context(
                patch("buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY", side_effect=client_factory)
            )
            stack.enter_context(
                patch("buoy_search.cli.ROUTING_EMBEDDER_FACTORY", return_value=object())
            )
            stack.enter_context(patch("buoy_search.cli.hybrid_route", side_effect=route))
            stack.enter_context(patch("buoy_search.cli._render_retrieve"))
            with ThreadPoolExecutor(max_workers=2) as executor:
                list(executor.map(lambda _index: run(), range(2)))

        self.assertEqual(sorted(statuses), [0, 0])
        self.assertEqual(len(clients), 2)
        self.assertEqual(len(receipts), 2)
        for data in receipts:
            self.assertIsNotNone(data)
            payload = json.loads(data)  # type: ignore[arg-type]
            self.assertEqual(payload["catalog"]["invocation_count"], 5)
            self.assertEqual(payload["content"]["invocation_count"], 0)

    def test_observer_faults_preserve_automatic_result_and_make_receipt_unknown(self) -> None:
        def execute(*, fault: str | None) -> tuple[int, str, str, bytes | None]:
            client, _resource, _trace = make_client(
                cards=[make_card("site-fault-v1")]
            )
            namespace = ScriptedNamespace([response("same")])
            with receipt._provider_invocation_receipt_scope() as handle:
                ledger = receipt._active_ledger()
                assert ledger is not None
                with ExitStack() as stack:
                    if fault == "catalog-constructor":
                        stack.enter_context(
                            patch.object(
                                receipt,
                                "_CatalogObserver",
                                side_effect=RuntimeError("observer fault"),
                            )
                        )
                    elif fault == "content-registration":
                        stack.enter_context(
                            patch.object(
                                ledger,
                                "_begin_content_attempt",
                                side_effect=RuntimeError("observer fault"),
                            )
                        )
                    result = run_automatic(
                        client,
                        retriever=multi([namespace]),
                        fanout=1,
                        preview=False,
                    )
            return (*result, handle.receipt())

        baseline = execute(fault=None)
        self.assertIsNotNone(baseline[3])
        for fault in ("catalog-constructor", "content-registration"):
            with self.subTest(fault=fault):
                observed = execute(fault=fault)
                self.assertEqual(observed[:3], baseline[:3])
                self.assertIsNone(observed[3])

    def test_canonical_bytes_and_diagnostics_exclude_strict_privacy_sentinels(self) -> None:
        client, _resource, _trace = make_client(
            cards=[make_card("site-privacy-v1")]
        )
        with receipt._provider_invocation_receipt_scope() as handle:
            result, _stdout, _stderr = run_automatic(
                client,
                retriever=multi([ScriptedNamespace([response("private-id")])]),
                fanout=1,
                preview=False,
            )
        self.assertEqual(result, 0)
        data = handle.receipt()
        self.assertIsNotNone(data)
        sentinels = (
            PRIVATE_QUERY,
            "ARGV_PRIVATE_SENTINEL",
            "EXECUTABLE_PRIVATE_SENTINEL",
            PRIVATE_NAMESPACE,
            "site-privacy-v1",
            "PROVIDER_PRIVATE_SENTINEL",
            "CARD_PRIVATE_SENTINEL",
            PRIVATE_CONTENT,
            PRIVATE_PATH,
            API_KEY,
            "https://private.example/",
            "PAYLOAD_PRIVATE_SENTINEL",
            "BILLING_PRIVATE_SENTINEL",
            PRIVATE_ERROR,
            "STACK_PRIVATE_SENTINEL",
            "TIMESTAMP_PRIVATE_SENTINEL",
            "TRACE_ID_PRIVATE_SENTINEL",
            "AMBIENT_CONTEXT_PRIVATE_SENTINEL",
        )
        for sentinel in sentinels:
            self.assertNotIn(sentinel.encode(), data)  # type: ignore[operator]
            invalid = json.loads(data)  # type: ignore[arg-type]
            invalid["private"] = sentinel
            with self.assertRaises(receipt._ReceiptValidationError) as raised:
                receipt._parse_receipt_value(invalid)
            self.assertEqual(
                str(raised.exception), "provider invocation receipt is invalid"
            )
            self.assertNotIn(sentinel, str(raised.exception))


class ReceiptIntegrationAuditTests(unittest.TestCase):
    def test_only_automatic_cli_production_caller_passes_private_observer(self) -> None:
        root = Path(__file__).resolve().parents[1]
        expected = {
            "scripts/evaluate_multi_corpus_retrieval.py": 1,
            "scripts/evaluate_routing_quality.py": 1,
            "src/buoy_search/apply.py": 2,
            "src/buoy_search/catalog_cli.py": 9,
            "src/buoy_search/cli.py": 1,
        }
        observed: dict[str, int] = {}
        observer_callers: list[str] = []
        for base in (root / "src", root / "scripts"):
            for path in sorted(base.rglob("*.py")):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                calls = [
                    node
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "read_remote_catalog"
                ]
                if not calls:
                    continue
                relative = str(path.relative_to(root))
                observed[relative] = len(calls)
                for call in calls:
                    if any(
                        keyword.arg == "_invocation_observer"
                        for keyword in call.keywords
                    ):
                        observer_callers.append(relative)
        self.assertEqual(observed, expected)
        self.assertEqual(observer_callers, ["src/buoy_search/cli.py"])

    def test_no_public_cli_environment_persistence_or_telemetry_v2_drift(self) -> None:
        root = Path(__file__).resolve().parents[1]
        parser = cli.build_parser()
        option_strings = {
            option
            for action in parser._actions
            for option in action.option_strings
        }
        for action in parser._actions:
            choices = getattr(action, "choices", None)
            if isinstance(choices, dict):
                for child in choices.values():
                    option_strings.update(
                        option
                        for child_action in child._actions
                        for option in child_action.option_strings
                    )
        self.assertFalse(
            any("receipt" in option or "provider-invocation" in option for option in option_strings)
        )
        self.assertNotIn("provider_invocation", buoy_search.__all__)
        self.assertFalse(hasattr(buoy_search, "provider_invocation_receipt_scope"))
        self.assertEqual(receipt.__all__, ())

        core_source = (root / "src/buoy_search/_provider_invocation_receipt.py").read_text(
            encoding="utf-8"
        )
        for prohibited in (
            "os.environ",
            "argparse",
            "open(",
            "Path(",
            "duckdb",
            "telemetry",
            "requests",
            "urllib",
        ):
            self.assertNotIn(prohibited, core_source)
        cli_source = (root / "src/buoy_search/cli.py").read_text(encoding="utf-8")
        self.assertNotIn("_provider_invocation_receipt_scope", cli_source)
        self.assertEqual(cli_source.count("_invocation_observer"), 1)

        telemetry_paths = (
            "src/buoy_search/telemetry.py",
            "src/buoy_search/telemetry_envelope.py",
            "src/buoy_search/telemetry_queue.py",
            "src/buoy_search/telemetry_store.py",
            "src/buoy_search/telemetry_writer.py",
        )
        for relative in telemetry_paths:
            source = (root / relative).read_text(encoding="utf-8")
            with self.subTest(relative=relative):
                self.assertNotIn("provider_client_invocation", source)
                self.assertNotIn("provider_invocation_receipt", source)


if __name__ == "__main__":
    unittest.main()
