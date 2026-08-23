from __future__ import annotations

from contextlib import ExitStack, redirect_stderr, redirect_stdout
from contextvars import ContextVar
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import duckdb
from opentelemetry import baggage
from opentelemetry import context as otel_context
from opentelemetry import trace as otel_trace
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags

from buoy_search import telemetry, telemetry_store, telemetry_writer
from buoy_search.cli import main
from buoy_search.catalog import CatalogError
from buoy_search.config import RuntimeConfig, RuntimeConfigError
from buoy_search.entrypoint import main as entrypoint_main
from buoy_search.remote_catalog import RemoteCatalogError
from buoy_search.routing import AutomaticRoutingError
from buoy_search.retriever import (
    EvidenceRouteContext,
    HybridRetriever,
    MultiNamespaceRetriever,
    ProviderCallError,
    RetrievalOptions,
)
from buoy_search.telemetry import (
    EVIDENCE_SPAN_NAME,
    NAMESPACE_QUERY_SPAN_NAME,
    QUERY_EMBED_SPAN_NAME,
    RERANK_SPAN_NAME,
    retrieval_trace,
    telemetry_span,
)
from buoy_search.telemetry_envelope import (
    V2_PIPELINE_SPAN_NAME,
    decode_trace_envelope_v1,
    decode_trace_envelope_v2,
)
from buoy_search.telemetry_queue import (
    PublicationResult,
    scan_queue_read_only,
    telemetry_paths,
    telemetry_paths_v2,
)


class _Embedder:
    def encode(self, _texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3]]


class _Namespace:
    def __init__(self, *, error: BaseException | None = None) -> None:
        self.error = error
        self.calls = 0

    def multi_query(self, **_kwargs: object) -> dict[str, object]:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return {
            "rows": [
                {
                    "id": "private-row",
                    "attributes": {
                        "title": "Title",
                        "url": "https://example.test/",
                        "content": "Content",
                    },
                }
            ]
        }


class _InspectingNamespace(_Namespace):
    def __init__(
        self,
        *,
        unrelated: ContextVar[str],
        observations: list[tuple[str, bool]],
        error: BaseException | None = None,
    ) -> None:
        super().__init__(error=error)
        self._unrelated = unrelated
        self._observations = observations

    def multi_query(self, **kwargs: object) -> dict[str, object]:
        self._observations.append(
            (
                self._unrelated.get(),
                otel_trace.get_current_span().get_span_context().is_valid,
            )
        )
        return super().multi_query(**kwargs)


class _BrokenStream:
    def __init__(self, failure: OSError) -> None:
        self.failure = failure
        self.calls = 0

    def write(self, _value: str) -> int:
        self.calls += 1
        raise self.failure

    def flush(self) -> None:
        return None


class _FakeRouting:
    def __init__(self, namespace_count: int = 1) -> None:
        self.initial_fanout = 1
        self.selection_reason = "high_confidence_semantic"
        self.semantic_margin = 0.2
        self.selected_cards = [
            SimpleNamespace(
                namespace=f"site-auto-{index}-v1",
                region="gcp-us-central1",
                embedding_model="BAAI/bge-small-en-v1.5",
                embedding_precision="float32",
                ranking_mode="page",
                ranking_profile="none",
                ranking_pool=20,
                ranking_aggregation="max",
            )
            for index in range(1, namespace_count + 1)
        ]
        self.entries = [SimpleNamespace(semantic_score=0.9)]

    def to_dict(self) -> dict[str, object]:
        return {
            "active": True,
            "strategy": "title_alias_then_semantic",
            "catalog_namespace": "buoy-routing-catalog-v3",
            "region": "gcp-us-central1",
            "snapshot_revision": 1,
            "credentials_required": True,
            "read_only_api_calls_occurred": True,
            "content_retrieval_occurred": False,
            "routing_model": "BAAI/bge-small-en-v1.5",
            "routing_model_revision": "0" * 40,
            "requested_limit": 3,
            "initial_fanout": 1,
            "selection_reason": self.selection_reason,
            "high_confidence": True,
            "semantic_confidence_floor": 0.0,
            "semantic_margin_floor": 0.0,
            "semantic_margin": self.semantic_margin,
            "selected": [],
        }


class _EvidenceDecision:
    def __init__(self, status: str, is_weak: bool) -> None:
        self.status = status
        self.is_weak = is_weak

    def to_dict(self) -> dict[str, object]:
        return {"status": self.status}


class _SequenceEvidenceAssessor:
    mode = "active"

    def __init__(self) -> None:
        self._decisions = [
            _EvidenceDecision("no_relevant_evidence", True),
            _EvidenceDecision("supported", False),
        ]
        self.calls: list[dict[str, object]] = []

    def assess(self, **kwargs: object) -> _EvidenceDecision:
        self.calls.append(dict(kwargs))
        return self._decisions.pop(0)


class _OrdinalReranker:
    def __init__(self) -> None:
        self.calls = 0

    def score(self, _query: str, passages: list[str]) -> list[float]:
        self.calls += 1
        return [float(len(passages) - index) for index in range(len(passages))]


class _AutomaticRetriever:
    def __init__(
        self,
        *,
        failure: bool = False,
        mode: str = "automatic",
    ) -> None:
        self.failure = failure
        self.mode = mode
        self.calls = 0

    def retrieve(self, _query: str, _options: object, **_kwargs: object) -> object:
        self.calls += 1
        with retrieval_trace(
            mode=self.mode,
            embedding_model="BAAI/bge-small-en-v1.5",
            embedding_precision="float32",
            top_k=5,
            candidates=200,
            namespace_count=1,
            initial_fanout=1,
            routing_selection_reason="high_confidence_semantic",
            routing_semantic_score=0.9,
            routing_semantic_margin=0.2,
        ) as pipeline:
            with telemetry_span(QUERY_EMBED_SPAN_NAME) as child:
                child.mark_ok()
            pipeline.set_attribute("buoy.retrieval.final_fanout", 1)
            with telemetry_span(
                NAMESPACE_QUERY_SPAN_NAME,
                {"buoy.route.rank": 1},
            ) as child:
                child.set_attributes(
                    {
                        "buoy.namespace.status": "ok",
                        "buoy.namespace.hit_count": 1,
                    }
                )
                child.mark_ok()
            if self.failure:
                raise ProviderCallError("sanitized provider failure")
            if self.mode != "explicit_single":
                with telemetry_span(RERANK_SPAN_NAME) as child:
                    child.mark_ok()
            if self.mode == "automatic":
                with telemetry_span(
                    EVIDENCE_SPAN_NAME,
                    {
                        "buoy.evidence.mode": "active",
                        "buoy.evidence.status": "supported",
                    },
                ):
                    pass
            pipeline.set_attributes(
                {
                    "buoy.retrieval.outcome": "success",
                    "buoy.retrieval.hit_count": 1,
                    "buoy.retrieval.final_fanout": 1,
                }
            )
            pipeline.mark_ok()
        return SimpleNamespace(
            to_dict=lambda: {
                "dry_run": False,
                "namespaces": ["site-auto-v1"],
                "hits": [],
            }
        )


class RetrieveCommandTelemetryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.home_patch = patch(
            "buoy_search.local_paths.Path.home", return_value=self.home
        )
        self.home_patch.start()
        self.env_patch = patch.dict(
            os.environ, {"BUOY_TELEMETRY": "local"}, clear=True
        )
        self.env_patch.start()
        self.payloads: list[bytes] = []

        def publish(payload: bytes, *, paths: object) -> PublicationResult:
            del paths
            self.payloads.append(payload)
            return PublicationResult(
                True,
                f"v2-{'0' * 32}.json",
                "published",
            )

        self.publish_patch = patch.object(
            telemetry, "publish_envelope", side_effect=publish
        )
        self.start_patch = patch.object(telemetry, "request_writer_start")
        self.start = self.start_patch.start()
        self.publish_patch.start()

    def tearDown(self) -> None:
        self.publish_patch.stop()
        self.start_patch.stop()
        self.env_patch.stop()
        self.home_patch.stop()
        self.temp.cleanup()

    def _rows(self):
        self.assertEqual(len(self.payloads), 1)
        return decode_trace_envelope_v2(self.payloads[0])

    def _assert_exact_graph(
        self,
        rows,
        *,
        pipeline: bool,
        automatic: bool = False,
        namespace_minimum: int = 0,
    ) -> None:
        by_name: dict[str, list[tuple[object, ...]]] = {}
        by_id = {}
        for span in rows.spans:
            by_name.setdefault(span[3], []).append(span)
            by_id[span[1]] = span
        self.assertEqual(len(by_name["buoy.retrieve.command"]), 1)
        root = by_name["buoy.retrieve.command"][0]
        self.assertIsNone(root[2])
        self.assertEqual(root[1], rows.command[1])
        for required in (
            "buoy.cli.bootstrap",
            "buoy.retrieve.prepare",
            "buoy.output.render",
        ):
            self.assertEqual(len(by_name[required]), 1)
            self.assertEqual(by_name[required][0][2], root[1])
        bootstrap = by_name["buoy.cli.bootstrap"][0]
        prepare = by_name["buoy.retrieve.prepare"][0]
        render = by_name["buoy.output.render"][0]
        self.assertEqual(bootstrap[4], root[4])
        self.assertLessEqual(bootstrap[5], prepare[4])
        self.assertLessEqual(prepare[5], render[4])
        self.assertEqual(len(by_name.get(V2_PIPELINE_SPAN_NAME, [])), int(pipeline))
        retrieval_names = {
            "buoy.query.embed",
            "buoy.namespace.query",
            "buoy.rerank",
            "buoy.evidence.assess",
        }
        retrieval_spans = [
            span for span in rows.spans if span[3] in retrieval_names
        ]
        if pipeline:
            pipeline_span = by_name[V2_PIPELINE_SPAN_NAME][0]
            self.assertEqual(pipeline_span[2], root[1])
            self.assertLessEqual(prepare[5], pipeline_span[4])
            self.assertLessEqual(pipeline_span[5], render[4])
            self.assertEqual(len(by_name.get("buoy.query.embed", [])), 1)
            self.assertGreaterEqual(
                len(by_name.get("buoy.namespace.query", [])), namespace_minimum
            )
            for span in retrieval_spans:
                cursor = span
                while cursor[2] != pipeline_span[1]:
                    cursor = by_id[cursor[2]]
                self.assertEqual(cursor[2], pipeline_span[1])
        else:
            self.assertEqual(retrieval_spans, [])
        routing_names = {
            "buoy.routing.catalog",
            "buoy.routing.model",
            "buoy.routing.select",
        }
        routing_spans = [span for span in rows.spans if span[3] in routing_names]
        if automatic:
            self.assertEqual(len(by_name.get("buoy.routing.catalog", [])), 1)
            self.assertEqual(len(by_name.get("buoy.routing.select", [])), 1)
            self.assertGreaterEqual(len(by_name.get("buoy.routing.model", [])), 1)
            for span in routing_spans:
                cursor = span
                while cursor[2] != prepare[1]:
                    cursor = by_id[cursor[2]]
                self.assertEqual(cursor[2], prepare[1])
                if pipeline:
                    self.assertLessEqual(span[5], pipeline_span[4])
                self.assertLessEqual(span[5], render[4])
        else:
            self.assertEqual(routing_spans, [])
        self.assertEqual(
            list(rows.spans), sorted(rows.spans, key=lambda span: (span[4], span[1]))
        )

    @staticmethod
    def _single_retriever(*, error: BaseException | None = None) -> HybridRetriever:
        return HybridRetriever(
            namespace=_Namespace(error=error),
            embedder=_Embedder(),
            config=RuntimeConfig(namespace="site-private-v1"),
        )

    def _automatic_patches(self, retriever: object | None = None):
        snapshot = SimpleNamespace(
            eligible_cards=[object()],
            missing_card_ids=(),
            stale_target_ids=(),
            disabled_ids=(),
            incompatible_ids=(),
            snapshot_revision=1,
            counts=SimpleNamespace(
                listed_total=2,
                control_plane_count=1,
                content_live_count=1,
                card_count=1,
                stale_target_count=0,
                missing_card_count=0,
                disabled_count=0,
                incompatible_count=0,
                eligible_count=1,
            ),
            metrics=SimpleNamespace(
                namespace_list_pages=1,
                metadata_requests=1,
                card_query_pages=1,
                billing=(),
            ),
        )
        calibration = SimpleNamespace(
            mode="collect",
            model="cross-encoder/ms-marco-MiniLM-L-6-v2",
            model_revision="0" * 40,
            calibration_id="test",
            calibration_revision="test",
            feature_contract="test",
            threshold=None,
        )
        patches = [
            patch("buoy_search.cli.ROUTING_CONFIDENCE_FACTORY", return_value=SimpleNamespace(mode="collect")),
            patch("buoy_search.cli.load_evidence_calibration", return_value=calibration),
            patch("buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY", return_value=object()),
            patch("buoy_search.cli.read_remote_catalog", return_value=snapshot),
            patch("buoy_search.cli.require_eligible", side_effect=lambda value: value),
            patch("buoy_search.cli.ROUTING_EMBEDDER_FACTORY", return_value=object()),
            patch("buoy_search.cli.hybrid_route", return_value=_FakeRouting()),
        ]
        if retriever is not None:
            patches.append(
                patch(
                    "buoy_search.cli.MultiNamespaceRetriever.from_configs",
                    return_value=retriever,
                )
            )
        return patches

    def test_explicit_single_and_multi_live_emit_one_nested_v2_pipeline(self) -> None:
        for namespaces in (("site-one-v1",), ("site-one-v1", "site-two-v1")):
            with self.subTest(namespaces=namespaces):
                self.payloads.clear()
                retriever = (
                    self._single_retriever()
                    if len(namespaces) == 1
                    else _AutomaticRetriever(mode="explicit_multi")
                )
                target = (
                    "buoy_search.cli.HybridRetriever.from_config"
                    if len(namespaces) == 1
                    else "buoy_search.cli.MultiNamespaceRetriever.from_configs"
                )
                args = ["retrieve", "private query", "--json"]
                for namespace in namespaces:
                    args += ["--namespace", namespace]
                with patch(target, return_value=retriever), redirect_stdout(StringIO()):
                    self.assertEqual(main(args), 0)
                rows = self._rows()
                self.assertEqual(rows.command[5], "live")
                self.assertEqual(
                    rows.command[6],
                    "explicit_single" if len(namespaces) == 1 else "explicit_multi",
                )
                self.assertTrue(rows.command[10])
                self.assertIsNotNone(rows.retrieval_operation)
                self._assert_exact_graph(rows, pipeline=True, namespace_minimum=1)
                self.assertEqual(self.start.call_count, len(namespaces))

    def test_explicit_preview_aliases_emit_command_without_pipeline(self) -> None:
        for alias in ("--dry-run", "--plan"):
            for namespaces in (
                ("site-one-v1",),
                ("site-one-v1", "site-two-v1"),
            ):
                with self.subTest(alias=alias, namespaces=namespaces):
                    self.payloads.clear()
                    args = ["retrieve", "private query", alias, "--json"]
                    for namespace in namespaces:
                        args.extend(("--namespace", namespace))
                    with redirect_stdout(StringIO()):
                        self.assertEqual(main(args), 0)
                    rows = self._rows()
                    self.assertEqual(
                        rows.command[5:8],
                        (
                            "preview",
                            "explicit_single" if len(namespaces) == 1 else "explicit_multi",
                            "success",
                        ),
                    )
                    self.assertIsNone(rows.retrieval_operation)
                    self._assert_exact_graph(rows, pipeline=False)

    def test_automatic_preview_and_live_have_governed_routing_stages(self) -> None:
        os.environ["TURBOPUFFER_API_KEY"] = "private-key"
        for preview in (True, False):
            with self.subTest(preview=preview):
                self.payloads.clear()
                retriever = _AutomaticRetriever()
                patches = self._automatic_patches(None if preview else retriever)
                started = [item.start() for item in patches]
                try:
                    args = ["retrieve", "private query", "--json"]
                    if preview:
                        args.append("--dry-run")
                    with redirect_stdout(StringIO()):
                        self.assertEqual(main(args), 0)
                finally:
                    for item in reversed(patches):
                        item.stop()
                rows = self._rows()
                names = [row[3] for row in rows.spans]
                self.assertEqual(rows.command[6], "automatic")
                self.assertIn("buoy.routing.catalog", names)
                self.assertIn("buoy.routing.model", names)
                self.assertIn("buoy.routing.select", names)
                self.assertEqual(V2_PIPELINE_SPAN_NAME in names, not preview)
                self.assertEqual(rows.retrieval_operation is not None, not preview)
                self._assert_exact_graph(
                    rows,
                    pipeline=not preview,
                    automatic=True,
                    namespace_minimum=0 if preview else 1,
                )
                for routing_call in started[:7]:
                    self.assertEqual(routing_call.call_count, 1)
                self.assertEqual(retriever.calls, 0 if preview else 1)
                evidence = [
                    span for span in rows.spans if span[3] == EVIDENCE_SPAN_NAME
                ]
                self.assertEqual(len(evidence), 0 if preview else 1)
                if evidence:
                    self.assertEqual(evidence[0][7], "UNSET")

    def test_automatic_pipeline_and_render_errors_keep_completed_routing(self) -> None:
        os.environ["TURBOPUFFER_API_KEY"] = "private-key"
        cases = (
            ("pipeline", _AutomaticRetriever(failure=True), None),
            ("render", _AutomaticRetriever(), OSError("private render failure")),
        )
        for name, retriever, render_failure in cases:
            with self.subTest(name=name):
                self.payloads.clear()
                with ExitStack() as stack:
                    for item in self._automatic_patches(retriever):
                        stack.enter_context(item)
                    if render_failure is not None:
                        stack.enter_context(
                            patch(
                                "buoy_search.cli._print_json",
                                side_effect=render_failure,
                            )
                        )
                        raised = self.assertRaises(OSError)
                    else:
                        stack.enter_context(redirect_stderr(StringIO()))
                        raised = None
                    if raised is None:
                        self.assertEqual(main(["retrieve", "query", "--json"]), 2)
                    else:
                        with raised:
                            main(["retrieve", "query", "--json"])
                rows = self._rows()
                self.assertEqual(rows.command[6:8], ("automatic", "error"))
                self.assertIsNotNone(rows.retrieval_operation)
                routing = [
                    span
                    for span in rows.spans
                    if span[3]
                    in {
                        "buoy.routing.catalog",
                        "buoy.routing.model",
                        "buoy.routing.select",
                    }
                ]
                self.assertTrue(routing)
                self.assertTrue(all(span[7] == "OK" for span in routing))
                self._assert_exact_graph(
                    rows, pipeline=True, automatic=True, namespace_minimum=1
                )
                if name == "pipeline":
                    self.assertEqual(rows.retrieval_operation[5], "error")
                else:
                    self.assertEqual(rows.retrieval_operation[5], "success")
                    self.assertEqual(rows.command[9], "render_error")

    def test_automatic_weak_evidence_widening_publishes_truthful_v2_graph(self) -> None:
        os.environ["TURBOPUFFER_API_KEY"] = "private-key"
        namespaces = [_Namespace() for _ in range(3)]
        embedder = _Embedder()
        reranker = _OrdinalReranker()
        retriever = MultiNamespaceRetriever(
            retrievers=[
                HybridRetriever(
                    namespace=namespace,
                    embedder=embedder,
                    config=RuntimeConfig(namespace=f"site-auto-{index}-v1"),
                )
                for index, namespace in enumerate(namespaces, start=1)
            ],
            embedder=embedder,
            reranker_loader=lambda: reranker,
        )
        assessor = _SequenceEvidenceAssessor()
        patches = self._automatic_patches(retriever)
        patches[6] = patch(
            "buoy_search.cli.hybrid_route", return_value=_FakeRouting(3)
        )
        with ExitStack() as stack:
            for item in patches:
                stack.enter_context(item)
            stack.enter_context(
                patch(
                    "buoy_search.cli.CalibratedEvidenceAssessor",
                    return_value=assessor,
                )
            )
            stack.enter_context(redirect_stdout(StringIO()))
            self.assertEqual(main(["retrieve", "private query", "--json"]), 0)

        rows = self._rows()
        operation = rows.retrieval_operation
        self.assertIsNotNone(operation)
        assert operation is not None
        self.assertEqual(operation[7:10], (3, 1, 3))
        self.assertTrue(operation[12])
        self.assertEqual(operation[13], "weak_top1")
        names = [span[3] for span in rows.spans]
        self.assertEqual(names.count(NAMESPACE_QUERY_SPAN_NAME), 3)
        self.assertEqual(names.count(RERANK_SPAN_NAME), 1)
        self.assertEqual(names.count(EVIDENCE_SPAN_NAME), 2)
        namespace_ranks = sorted(
            json.loads(span[8])["buoy.route.rank"]
            for span in rows.spans
            if span[3] == NAMESPACE_QUERY_SPAN_NAME
        )
        self.assertEqual(namespace_ranks, [1, 2, 3])
        self.assertEqual(len(rows.events), 1)
        self.assertEqual(rows.events[0][3], "retrieval.widened")
        self.assertEqual(len(assessor.calls), 2)
        self.assertIsInstance(
            assessor.calls[0]["route_context"], EvidenceRouteContext
        )
        self.assertEqual([namespace.calls for namespace in namespaces], [1, 1, 1])
        self.assertEqual(reranker.calls, 1)
        self._assert_exact_graph(
            rows, pipeline=True, automatic=True, namespace_minimum=3
        )

    def test_configuration_and_pipeline_failures_keep_output_and_categories(self) -> None:
        stderr = StringIO()
        with redirect_stderr(stderr):
            self.assertEqual(main(["retrieve", "query", "--json"]), 2)
        rows = self._rows()
        self.assertIn("TURBOPUFFER_API_KEY", stderr.getvalue())
        self.assertEqual(rows.command[7:11], ("error", 2, "configuration_error", False))
        names = [span[3] for span in rows.spans]
        self.assertEqual(names.count("buoy.cli.bootstrap"), 1)
        self.assertEqual(names.count("buoy.retrieve.prepare"), 1)
        self.assertEqual(names.count("buoy.output.render"), 1)
        self.assertEqual(names.count("buoy.routing.model"), 1)
        self.assertNotIn(V2_PIPELINE_SPAN_NAME, names)

        self.payloads.clear()
        os.environ["TURBOPUFFER_API_KEY"] = "private-key"
        retriever = self._single_retriever(error=RuntimeError("raw-private-error"))
        stderr = StringIO()
        with patch(
            "buoy_search.cli.HybridRetriever.from_config", return_value=retriever
        ), redirect_stderr(stderr):
            self.assertEqual(
                main(
                    [
                        "retrieve",
                        "query",
                        "--namespace",
                        "site-one-v1",
                        "--json",
                    ]
                ),
                2,
            )
        rows = self._rows()
        self.assertEqual(rows.command[7:10], ("error", 2, "provider_call_error"))
        self.assertTrue(rows.command[10])
        self.assertEqual(rows.retrieval_operation[5], "error")
        self._assert_exact_graph(rows, pipeline=True, namespace_minimum=1)
        self.assertNotIn("raw-private-error", self.payloads[0].decode("ascii"))

    def test_render_and_unexpected_exceptions_reraise_identity_with_exit_one(self) -> None:
        escaped = OSError("private-render-error")
        with patch(
            "buoy_search.cli._print_json", side_effect=escaped
        ), self.assertRaises(OSError) as raised:
            main(
                [
                    "retrieve",
                    "query",
                    "--namespace",
                    "site-one-v1",
                    "--dry-run",
                    "--json",
                ]
            )
        self.assertIs(raised.exception, escaped)
        rows = self._rows()
        self.assertEqual(rows.command[7:10], ("error", 1, "render_error"))
        self.assertNotIn("private-render-error", self.payloads[0].decode("ascii"))

        self.payloads.clear()
        escaped = LookupError("private-unexpected-error")
        with patch(
            "buoy_search.cli.resolve_retrieval_namespaces", side_effect=escaped
        ), self.assertRaises(LookupError) as raised:
            main(["retrieve", "query", "--namespace", "site-one-v1"])
        self.assertIs(raised.exception, escaped)
        rows = self._rows()
        self.assertEqual(rows.command[7:10], ("error", 1, "unexpected_error"))
        self.assertNotIn("buoy.output.render", [span[3] for span in rows.spans])

    def test_runtime_config_broken_stderr_is_identical_enabled_and_disabled(self) -> None:
        args = ["retrieve", "query", "--namespace", "site-one-v1"]
        config_failure = RuntimeConfigError("PRIVATE_CONFIG_SENTINEL")
        observations = []
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                self.payloads.clear()
                stream_failure = OSError("PRIVATE_STREAM_SENTINEL")
                stream = _BrokenStream(stream_failure)
                environment = {"BUOY_TELEMETRY": "local"} if enabled else {}
                with patch.dict(os.environ, environment, clear=True), patch(
                    "buoy_search.cli.resolve_retrieval_namespaces",
                    side_effect=config_failure,
                ), redirect_stderr(stream):
                    result = main(args)
                observations.append((result, stream.calls))
                self.assertEqual(result, 2)
                self.assertEqual(stream.calls, 1)
                if enabled:
                    rows = self._rows()
                    self.assertEqual(rows.command[7:9], ("error", 2))
                    self.assertEqual(rows.command[9], "render_error")
                    render = next(
                        span for span in rows.spans if span[3] == "buoy.output.render"
                    )
                    self.assertEqual(render[7], "ERROR")
                    self.assertNotIn("PRIVATE", self.payloads[0].decode("ascii"))
                else:
                    self.assertEqual(self.payloads, [])
        self.assertEqual(observations, [(2, 1), (2, 1)])

    def test_disabled_and_sink_failures_preserve_command_result(self) -> None:
        self.env_patch.stop()
        self.env_patch = patch.dict(os.environ, {}, clear=True)
        self.env_patch.start()
        with patch.object(telemetry, "publish_envelope") as publish, redirect_stdout(StringIO()):
            result = main(
                [
                    "retrieve",
                    "query",
                    "--namespace",
                    "site-one-v1",
                    "--dry-run",
                    "--json",
                ]
            )
        self.assertEqual(result, 0)
        publish.assert_not_called()
        self.assertFalse((self.home / ".buoy").exists())

        os.environ["BUOY_TELEMETRY"] = "local"
        with patch.object(
            telemetry, "encode_trace_envelope_v2", side_effect=RuntimeError("sink")
        ), redirect_stdout(StringIO()):
            self.assertEqual(
                main(
                    [
                        "retrieve",
                        "query",
                        "--namespace",
                        "site-one-v1",
                        "--dry-run",
                        "--json",
                    ]
                ),
                0,
            )

    def test_direct_retriever_stays_v1_and_command_context_is_ambient_isolated(self) -> None:
        self.payloads.clear()
        unrelated: ContextVar[str] = ContextVar("private", default="default")
        token = unrelated.set("context-secret")
        try:
            result = self._single_retriever().retrieve(
                "query",
                RetrievalOptions(ranking_mode="chunk", ranking_profile="none"),
            )
        finally:
            unrelated.reset(token)
        self.assertEqual([hit.id for hit in result.hits], ["private-row"])
        self.assertEqual(len(self.payloads), 1)
        rows = decode_trace_envelope_v1(self.payloads[0])
        self.assertEqual(rows.run[21], 1)
        self.assertNotIn("context-secret", self.payloads[0].decode("ascii"))
        self.assertFalse(otel_trace.get_current_span().get_span_context().is_valid)

    def test_enabled_disabled_explicit_preview_output_equivalence(self) -> None:
        args = [
            "retrieve",
            "equivalence query",
            "--namespace",
            "site-equivalence-v1",
            "--dry-run",
            "--json",
        ]
        enabled_stdout = StringIO()
        with redirect_stdout(enabled_stdout):
            self.assertEqual(main(args), 0)
        self._rows()

        self.payloads.clear()
        disabled_stdout = StringIO()
        with patch.dict(os.environ, {}, clear=True), redirect_stdout(disabled_stdout):
            self.assertEqual(main(args), 0)
        self.assertEqual(enabled_stdout.getvalue(), disabled_stdout.getvalue())
        self.assertEqual(self.payloads, [])

    def test_real_entrypoint_queue_writer_store_and_worker_privacy_boundary(self) -> None:
        sentinels = {
            "query": "QUERY_SENTINEL_PRIVATE",
            "argv": "ARGV_EXECUTABLE_SENTINEL_PRIVATE",
            "namespace_one": "site-privacy-sentinel-one-v1",
            "namespace_two": "site-privacy-sentinel-two-v1",
            "path": "PATH_SENTINEL_PRIVATE",
            "content": "CONTENT_SENTINEL_PRIVATE",
            "credential": "CREDENTIAL_SENTINEL_PRIVATE",
            "error": "ERROR_SENTINEL_PRIVATE",
            "stack": "STACK_SENTINEL_PRIVATE",
            "resource": "RESOURCE_SENTINEL_PRIVATE",
            "baggage": "BAGGAGE_SENTINEL_PRIVATE",
            "unrelated": "CONTEXT_SENTINEL_PRIVATE",
            "trace": "1234567890abcdef1234567890abcdef",
        }
        observations: list[tuple[str, bool]] = []
        unrelated: ContextVar[str] = ContextVar(
            "privacy_unrelated", default="worker-default"
        )

        class ContentNamespace(_InspectingNamespace):
            def multi_query(self, **kwargs: object) -> dict[str, object]:
                result = super().multi_query(**kwargs)
                result["rows"][0]["attributes"].update(
                    {
                        "content": sentinels["content"],
                        "url": f"file:///{sentinels['path']}",
                    }
                )
                return result

        namespaces = [
            ContentNamespace(unrelated=unrelated, observations=observations),
            ContentNamespace(unrelated=unrelated, observations=observations),
        ]
        retrievers = [
            HybridRetriever(
                namespace=namespace,
                embedder=_Embedder(),
                config=RuntimeConfig(namespace=name),
            )
            for namespace, name in zip(
                namespaces,
                (sentinels["namespace_one"], sentinels["namespace_two"]),
                strict=True,
            )
        ]
        multi = MultiNamespaceRetriever(
            retrievers=retrievers,
            embedder=_Embedder(),
            reranker_loader=_OrdinalReranker,
        )

        self.publish_patch.stop()
        os.environ.update(
            {
                "BUOY_TELEMETRY": "local",
                "TURBOPUFFER_API_KEY": sentinels["credential"],
                "OTEL_RESOURCE_ATTRIBUTES": f"private={sentinels['resource']}",
            }
        )
        unrelated_token = unrelated.set(sentinels["unrelated"])
        ambient = baggage.set_baggage("private", sentinels["baggage"])
        ambient = otel_trace.set_span_in_context(
            NonRecordingSpan(
                SpanContext(
                    trace_id=int(sentinels["trace"], 16),
                    span_id=int("1234567890abcdef", 16),
                    is_remote=True,
                    trace_flags=TraceFlags(TraceFlags.SAMPLED),
                    trace_state=otel_trace.DEFAULT_TRACE_STATE,
                )
            ),
            ambient,
        )
        ambient_token = otel_context.attach(ambient)
        argv = [
            sentinels["argv"],
            "retrieve",
            sentinels["query"],
            "--namespace",
            sentinels["namespace_one"],
            "--namespace",
            sentinels["namespace_two"],
            "--json",
        ]
        try:
            with patch.object(sys, "argv", argv), patch(
                "buoy_search.cli.MultiNamespaceRetriever.from_configs",
                return_value=multi,
            ), redirect_stdout(StringIO()):
                self.assertEqual(entrypoint_main(), 0)
        finally:
            otel_context.detach(ambient_token)
            unrelated.reset(unrelated_token)

        self.assertEqual(len(observations), 2)
        self.assertEqual(observations, [("worker-default", False)] * 2)
        paths_v1 = telemetry_paths()
        paths_v2 = telemetry_paths_v2(paths_v1.directory)
        prohibited_text = tuple(sentinels.values())
        for sentinel in prohibited_text:
            self.assertNotIn(sentinel, str(paths_v1.directory))
        observed_relative_names: set[str] = set()

        def capture_relative_names() -> None:
            for path in paths_v1.directory.rglob("*"):
                relative = path.relative_to(paths_v1.directory)
                observed_relative_names.add(relative.as_posix())
                observed_relative_names.update(relative.parts)

        self.assertEqual(scan_queue_read_only(paths_v2).ready, 1)
        capture_relative_names()
        ready_payloads = [path.read_bytes() for path in paths_v2.ready_directory.iterdir()]
        rows = decode_trace_envelope_v2(ready_payloads[0])
        self.assertEqual(
            len([span for span in rows.spans if span[3] == "buoy.namespace.query"]),
            2,
        )

        error = RuntimeError(sentinels["error"])
        error.add_note(sentinels["stack"])
        failing_namespaces = [
            _InspectingNamespace(
                unrelated=unrelated,
                observations=observations,
                error=error,
            )
            for _ in range(2)
        ]
        failing_multi = MultiNamespaceRetriever(
            retrievers=[
                HybridRetriever(
                    namespace=namespace,
                    embedder=_Embedder(),
                    config=RuntimeConfig(namespace=name),
                )
                for namespace, name in zip(
                    failing_namespaces,
                    (sentinels["namespace_one"], sentinels["namespace_two"]),
                    strict=True,
                )
            ],
            embedder=_Embedder(),
            reranker_loader=_OrdinalReranker,
        )
        with patch.object(sys, "argv", argv), patch(
            "buoy_search.cli.MultiNamespaceRetriever.from_configs",
            return_value=failing_multi,
        ), redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            self.assertEqual(entrypoint_main(), 2)
        self.assertEqual(scan_queue_read_only(paths_v2).ready, 2)
        capture_relative_names()

        prohibited = tuple(value.encode("ascii") for value in sentinels.values())
        for path in paths_v2.ready_directory.iterdir():
            payload = path.read_bytes()
            for sentinel in prohibited:
                self.assertNotIn(sentinel, payload, path)

        with patch("buoy_search.telemetry_writer.IDLE_EXIT_SECONDS", 0):
            self.assertEqual(telemetry_writer.run_writer(paths_v1), 0)
        status_bytes = json.dumps(
            telemetry_writer.telemetry_status(paths=paths_v1, environment={}),
            sort_keys=True,
        ).encode()
        migrate_bytes = telemetry_writer.telemetry_migrate_command(
            json_output=True, paths=paths_v1
        ).output.encode()
        artifact_bytes = [status_bytes, migrate_bytes]
        capture_relative_names()
        for path in paths_v1.directory.rglob("*"):
            if path.is_file():
                artifact_bytes.append(path.read_bytes())
        with duckdb.connect(
            str(paths_v1.database_path),
            read_only=True,
            config=telemetry_store._SAFE_DUCKDB_CONFIG,
        ) as connection:
            database_values = []
            for table in (
                "telemetry_metadata",
                "retrieve_command_runs",
                "retrieval_operations",
                "spans",
                "span_events",
            ):
                database_values.extend(connection.execute(f"SELECT * FROM {table}").fetchall())
        artifact_bytes.append(repr(database_values).encode("ascii"))
        for sentinel_text, sentinel in zip(
            prohibited_text, prohibited, strict=True
        ):
            for relative_name in observed_relative_names:
                self.assertNotIn(sentinel_text, relative_name)
            for artifact in artifact_bytes:
                self.assertNotIn(sentinel, artifact)

    def test_pre_pipeline_model_catalog_and_routing_categories(self) -> None:
        os.environ["TURBOPUFFER_API_KEY"] = "private-key"
        cases = (
            (
                "model_error",
                [
                    patch(
                        "buoy_search.cli.ROUTING_CONFIDENCE_FACTORY",
                        side_effect=ValueError("private model detail"),
                    )
                ],
            ),
            (
                "catalog_error",
                [
                    patch(
                        "buoy_search.cli.ROUTING_CONFIDENCE_FACTORY",
                        return_value=SimpleNamespace(mode="collect"),
                    ),
                    patch(
                        "buoy_search.cli.load_evidence_calibration",
                        return_value=SimpleNamespace(mode="collect"),
                    ),
                    patch(
                        "buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY",
                        side_effect=RuntimeError("private catalog detail"),
                    ),
                ],
            ),
        )
        for category, patches in cases:
            with self.subTest(category=category):
                self.payloads.clear()
                with ExitStack() as stack:
                    for item in patches:
                        stack.enter_context(item)
                    with redirect_stderr(StringIO()):
                        self.assertEqual(main(["retrieve", "query", "--json"]), 2)
                rows = self._rows()
                self.assertEqual(rows.command[9], category)
                self.assertIsNone(rows.retrieval_operation)

        self.payloads.clear()
        patches = self._automatic_patches()
        patches[-1] = patch(
            "buoy_search.cli.hybrid_route",
            side_effect=ValueError("private routing detail"),
        )
        for item in patches:
            item.start()
        try:
            with redirect_stderr(StringIO()):
                self.assertEqual(main(["retrieve", "query", "--json"]), 2)
        finally:
            for item in reversed(patches):
                item.stop()
        rows = self._rows()
        self.assertEqual(rows.command[9], "routing_error")
        self.assertIsNone(rows.retrieval_operation)

    def test_catalog_and_routing_exception_classes_preserve_order_and_output(self) -> None:
        os.environ["TURBOPUFFER_API_KEY"] = "private-key"

        def run_catalog(exc: BaseException, enabled: bool):
            calls: list[str] = []
            stderr = StringIO()
            environment = {
                "TURBOPUFFER_API_KEY": "private-key",
                **({"BUOY_TELEMETRY": "local"} if enabled else {}),
            }
            with patch.dict(os.environ, environment, clear=True), patch(
                "buoy_search.cli.ROUTING_CONFIDENCE_FACTORY",
                side_effect=lambda: calls.append("confidence")
                or SimpleNamespace(mode="collect"),
            ), patch(
                "buoy_search.cli.load_evidence_calibration",
                side_effect=lambda: calls.append("evidence")
                or SimpleNamespace(mode="collect"),
            ), patch(
                "buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY",
                side_effect=lambda **_kwargs: calls.append("catalog") or (_ for _ in ()).throw(exc),
            ), patch(
                "buoy_search.cli.ROUTING_EMBEDDER_FACTORY",
                side_effect=lambda: calls.append("embedder") or object(),
            ), redirect_stderr(stderr):
                result = main(["retrieve", "query", "--json"])
            return result, stderr.getvalue(), calls

        for exception_type in (RemoteCatalogError, CatalogError, RuntimeError, ValueError):
            with self.subTest(stage="catalog", exception=exception_type.__name__):
                self.payloads.clear()
                enabled = run_catalog(exception_type("safe catalog failure"), True)
                self.payloads.clear()
                disabled = run_catalog(exception_type("safe catalog failure"), False)
                self.assertEqual(enabled, disabled)
                self.assertEqual(enabled[0], 2)
                self.assertEqual(enabled[2], ["confidence", "evidence", "catalog"])

        def run_routing(exc: BaseException, enabled: bool):
            calls: list[str] = []
            retriever = _AutomaticRetriever()
            patches = self._automatic_patches(retriever)
            patches[-2] = patch(
                "buoy_search.cli.hybrid_route",
                side_effect=lambda *_args, **_kwargs: calls.append("route")
                or (_ for _ in ()).throw(exc),
            )
            environment = {
                "TURBOPUFFER_API_KEY": "private-key",
                **({"BUOY_TELEMETRY": "local"} if enabled else {}),
            }
            stderr = StringIO()
            with patch.dict(os.environ, environment, clear=True), ExitStack() as stack:
                for item in patches:
                    stack.enter_context(item)
                stack.enter_context(redirect_stderr(stderr))
                result = main(["retrieve", "query", "--json"])
            return result, stderr.getvalue(), calls, retriever.calls

        for exception_type in (AutomaticRoutingError, RuntimeError, ValueError):
            with self.subTest(stage="routing", exception=exception_type.__name__):
                self.payloads.clear()
                enabled = run_routing(exception_type("safe routing failure"), True)
                self.payloads.clear()
                disabled = run_routing(exception_type("safe routing failure"), False)
                self.assertEqual(enabled, disabled)
                self.assertEqual(enabled, (2, "Automatic routing failed: safe routing failure\n", ["route"], 0))

    def test_private_provider_span_export_context_and_sink_failures_are_isolated(self) -> None:
        args = [
            "retrieve",
            "query",
            "--namespace",
            "site-one-v1",
            "--dry-run",
            "--json",
        ]
        baseline = StringIO()
        with redirect_stdout(baseline):
            self.assertEqual(main(args), 0)
        baseline_output = baseline.getvalue()

        class BrokenContext:
            def get(self):
                return None

            def set(self, _value):
                raise RuntimeError("PRIVATE_CONTEXT_FAILURE")

            def reset(self, _token):
                raise RuntimeError("PRIVATE_CONTEXT_FAILURE")

        cases = (
            (
                "provider",
                patch(
                    "opentelemetry.sdk.trace.TracerProvider.__init__",
                    side_effect=RuntimeError("PRIVATE_PROVIDER_FAILURE"),
                ),
            ),
            (
                "tracer_start",
                patch(
                    "opentelemetry.sdk.trace.Tracer.start_span",
                    side_effect=RuntimeError("PRIVATE_TRACER_FAILURE"),
                ),
            ),
            (
                "span_attribute",
                patch(
                    "opentelemetry.sdk.trace._Span.set_attribute",
                    side_effect=RuntimeError("PRIVATE_ATTRIBUTE_FAILURE"),
                ),
            ),
            (
                "span_status",
                patch(
                    "opentelemetry.sdk.trace._Span.set_status",
                    side_effect=RuntimeError("PRIVATE_STATUS_FAILURE"),
                ),
            ),
            (
                "span_end",
                patch(
                    "opentelemetry.sdk.trace._Span.end",
                    side_effect=RuntimeError("PRIVATE_END_FAILURE"),
                ),
            ),
            (
                "exporter",
                patch.object(
                    telemetry._BufferingSpanExporter,
                    "export",
                    side_effect=RuntimeError("PRIVATE_EXPORT_FAILURE"),
                ),
            ),
            (
                "context",
                patch.object(telemetry, "_ACTIVE_SESSION", BrokenContext()),
            ),
            (
                "envelope",
                patch.object(
                    telemetry,
                    "encode_trace_envelope_v2",
                    side_effect=RuntimeError("PRIVATE_ENVELOPE_FAILURE"),
                ),
            ),
            (
                "publication",
                patch.object(
                    telemetry,
                    "publish_envelope",
                    side_effect=RuntimeError("PRIVATE_PUBLICATION_FAILURE"),
                ),
            ),
            (
                "writer",
                patch.object(
                    telemetry,
                    "request_writer_start",
                    side_effect=RuntimeError("PRIVATE_WRITER_FAILURE"),
                ),
            ),
        )
        for name, failure_patch in cases:
            with self.subTest(name=name):
                self.payloads.clear()
                stdout = StringIO()
                stderr = StringIO()
                with failure_patch, redirect_stdout(stdout), redirect_stderr(stderr):
                    self.assertEqual(main(args), 0)
                self.assertEqual(stdout.getvalue(), baseline_output)
                self.assertEqual(stderr.getvalue(), "")
                self.assertNotIn("PRIVATE", stdout.getvalue())

    def test_clock_session_publication_and_writer_failures_are_isolated(self) -> None:
        args = [
            "retrieve",
            "query",
            "--namespace",
            "site-one-v1",
            "--dry-run",
            "--json",
        ]
        for target, failure in (
            ("_time_ns", RuntimeError("clock")),
            ("_new_trace_session", RuntimeError("session")),
        ):
            with self.subTest(target=target):
                self.payloads.clear()
                with patch.object(telemetry, target, side_effect=failure), redirect_stdout(StringIO()):
                    self.assertEqual(main(args), 0)
                self.assertEqual(self.payloads, [])

        for target in ("publish_envelope", "request_writer_start"):
            with self.subTest(target=target):
                self.payloads.clear()
                with patch.object(
                    telemetry, target, side_effect=RuntimeError(target)
                ), redirect_stdout(StringIO()):
                    self.assertEqual(main(args), 0)

    def test_entrypoint_timestamp_and_fake_clock_boundaries_are_exact(self) -> None:
        self.payloads.clear()
        base = 1_700_000_000_000_000_000
        ticks = iter(base + offset * 1_000_000 for offset in range(1, 13))
        retriever = self._single_retriever()
        with patch.object(telemetry, "_time_ns", side_effect=lambda: next(ticks)), patch(
            "buoy_search.cli.HybridRetriever.from_config", return_value=retriever
        ), redirect_stdout(StringIO()):
            self.assertEqual(
                main(
                    [
                        "retrieve",
                        "query",
                        "--namespace",
                        "site-one-v1",
                        "--json",
                    ],
                    entry_started_at_ns=base,
                ),
                0,
            )
        rows = self._rows()
        self._assert_exact_graph(rows, pipeline=True, namespace_minimum=1)
        self.assertEqual(rows.command[4], 12.0)
        self.assertIsNotNone(rows.retrieval_operation)
        assert rows.retrieval_operation is not None
        self.assertEqual(rows.retrieval_operation[4], 5.0)
        root_start = rows.command[2]
        expected = {
            "buoy.retrieve.command": (0.0, 12.0),
            "buoy.cli.bootstrap": (0.0, 1.0),
            "buoy.retrieve.prepare": (2.0, 3.0),
            V2_PIPELINE_SPAN_NAME: (4.0, 9.0),
            "buoy.query.embed": (5.0, 6.0),
            "buoy.namespace.query": (7.0, 8.0),
            "buoy.output.render": (10.0, 11.0),
        }
        for span in rows.spans:
            start_ms = (span[4] - root_start).total_seconds() * 1000
            end_ms = (span[5] - root_start).total_seconds() * 1000
            self.assertEqual((start_ms, end_ms), expected[span[3]])

    def test_controlled_initialization_routing_and_render_delays_skip_pipeline(self) -> None:
        def explicit_duration(*, initialize_ms: int = 0, render_ms: int = 0):
            self.payloads.clear()
            now = [1_700_000_000_000_000_000]
            retriever = self._single_retriever()

            def construct(*_args: object, **_kwargs: object):
                now[0] += initialize_ms * 1_000_000
                return retriever

            def render(_value: object):
                now[0] += render_ms * 1_000_000

            with patch.object(telemetry, "_time_ns", side_effect=lambda: now[0]), patch(
                "buoy_search.cli.HybridRetriever.from_config", side_effect=construct
            ), patch("buoy_search.cli._print_json", side_effect=render):
                self.assertEqual(
                    main(
                        [
                            "retrieve",
                            "query",
                            "--namespace",
                            "site-one-v1",
                            "--json",
                        ],
                        entry_started_at_ns=now[0],
                    ),
                    0,
                )
            return self._rows()

        baseline = explicit_duration()
        initialized = explicit_duration(initialize_ms=17)
        rendered = explicit_duration(render_ms=23)
        self.assertEqual(initialized.command[4] - baseline.command[4], 17.0)
        self.assertEqual(rendered.command[4] - baseline.command[4], 23.0)
        self.assertEqual(
            initialized.retrieval_operation[4], baseline.retrieval_operation[4]
        )
        self.assertEqual(rendered.retrieval_operation[4], baseline.retrieval_operation[4])

        def automatic_duration(route_ms: int):
            self.payloads.clear()
            os.environ["TURBOPUFFER_API_KEY"] = "private-key"
            now = [1_700_000_000_000_000_000]
            retriever = _AutomaticRetriever()
            patches = self._automatic_patches(retriever)
            patches[-2] = patch(
                "buoy_search.cli.hybrid_route",
                side_effect=lambda *_args, **_kwargs: (
                    now.__setitem__(0, now[0] + route_ms * 1_000_000) or _FakeRouting()
                ),
            )
            with ExitStack() as stack:
                stack.enter_context(
                    patch.object(telemetry, "_time_ns", side_effect=lambda: now[0])
                )
                for item in patches:
                    stack.enter_context(item)
                stack.enter_context(redirect_stdout(StringIO()))
                self.assertEqual(
                    main(
                        ["retrieve", "query", "--json"],
                        entry_started_at_ns=now[0],
                    ),
                    0,
                )
            return self._rows()

        automatic_baseline = automatic_duration(0)
        routed = automatic_duration(19)
        self.assertEqual(routed.command[4] - automatic_baseline.command[4], 19.0)
        self.assertEqual(
            routed.retrieval_operation[4], automatic_baseline.retrieval_operation[4]
        )

    def test_controlled_subprocess_probe_attributes_pre_pipeline_and_render_delay(self) -> None:
        probe = Path(__file__).parent / "fixtures" / "retrieve_command_timing_probe.py"
        injected_delay_ms = 500
        observations: dict[str, dict[int, dict[str, object]]] = {}
        for stage in ("initialize", "routing", "render"):
            observations[stage] = {}
            for delay_ms in (0, injected_delay_ms):
                completed = subprocess.run(
                    [
                        sys.executable,
                        str(probe),
                        "--stage",
                        stage,
                        "--delay-ms",
                        str(delay_ms),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    env={
                        "PYTHONPATH": str(Path(__file__).parents[1] / "src"),
                        "BUOY_TELEMETRY": "local",
                    },
                    timeout=30,
                )
                self.assertEqual(completed.stderr, "")
                observations[stage][delay_ms] = json.loads(completed.stdout)
        for stage, pair in observations.items():
            baseline = pair[0]
            delayed = pair[injected_delay_ms]
            for observation in (baseline, delayed):
                self.assertEqual(observation["exit_code"], 0)
                self.assertEqual(observation["stage"], stage)
                if stage == "routing":
                    self.assertTrue(observation["routing_before_pipeline"])
                    self.assertEqual(
                        set(observation["routing_stages"]),
                        {
                            "buoy.routing.catalog",
                            "buoy.routing.model",
                            "buoy.routing.select",
                        },
                    )
                else:
                    self.assertFalse(observation["routing_before_pipeline"])
                    self.assertEqual(observation["routing_stages"], [])
            command_delta = (
                float(delayed["command_duration_ms"])
                - float(baseline["command_duration_ms"])
            )
            pipeline_delta = abs(
                float(delayed["pipeline_duration_ms"])
                - float(baseline["pipeline_duration_ms"])
            )
            self.assertGreaterEqual(command_delta, injected_delay_ms * 0.75)
            self.assertLessEqual(command_delta, injected_delay_ms * 1.5)
            self.assertLessEqual(pipeline_delta, 25.0)


if __name__ == "__main__":
    unittest.main()
