from __future__ import annotations

from contextlib import ExitStack, redirect_stderr, redirect_stdout
from contextvars import ContextVar
from io import StringIO
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from opentelemetry import trace as otel_trace

from buoy_search import telemetry
from buoy_search.cli import main
from buoy_search.config import RuntimeConfig
from buoy_search.retriever import (
    HybridRetriever,
    ProviderCallError,
    RetrievalOptions,
)
from buoy_search.telemetry import (
    NAMESPACE_QUERY_SPAN_NAME,
    QUERY_EMBED_SPAN_NAME,
    retrieval_trace,
    telemetry_span,
)
from buoy_search.telemetry_envelope import (
    V2_PIPELINE_SPAN_NAME,
    decode_trace_envelope_v1,
    decode_trace_envelope_v2,
)
from buoy_search.telemetry_queue import PublicationResult


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


class _FakeRouting:
    def __init__(self) -> None:
        self.initial_fanout = 1
        self.selection_reason = "high_confidence_semantic"
        self.semantic_margin = 0.2
        self.selected_cards = [
            SimpleNamespace(
                namespace="site-auto-v1",
                region="gcp-us-central1",
                embedding_model="BAAI/bge-small-en-v1.5",
                embedding_precision="float32",
                ranking_mode="page",
                ranking_profile="none",
                ranking_pool=20,
                ranking_aggregation="max",
            )
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
                stages = [row[3] for row in rows.spans]
                self.assertIn(V2_PIPELINE_SPAN_NAME, stages)
                self.assertIn("buoy.query.embed", stages)
                self.assertIn("buoy.namespace.query", stages)
                self.assertEqual(self.start.call_count, len(namespaces))

    def test_explicit_preview_aliases_emit_command_without_pipeline(self) -> None:
        for alias in ("--dry-run", "--plan"):
            with self.subTest(alias=alias):
                self.payloads.clear()
                with redirect_stdout(StringIO()):
                    self.assertEqual(
                        main(
                            [
                                "retrieve",
                                "private query",
                                "--namespace",
                                "site-one-v1",
                                alias,
                                "--json",
                            ]
                        ),
                        0,
                    )
                rows = self._rows()
                self.assertEqual(rows.command[5:8], ("preview", "explicit_single", "success"))
                self.assertIsNone(rows.retrieval_operation)
                self.assertNotIn(V2_PIPELINE_SPAN_NAME, [row[3] for row in rows.spans])

    def test_automatic_preview_and_live_have_governed_routing_stages(self) -> None:
        os.environ["TURBOPUFFER_API_KEY"] = "private-key"
        for preview in (True, False):
            with self.subTest(preview=preview):
                self.payloads.clear()
                retriever = _AutomaticRetriever()
                patches = self._automatic_patches(None if preview else retriever)
                for item in patches:
                    item.start()
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

    def test_configuration_and_pipeline_failures_keep_output_and_categories(self) -> None:
        stderr = StringIO()
        with redirect_stderr(stderr):
            self.assertEqual(main(["retrieve", "query", "--json"]), 2)
        rows = self._rows()
        self.assertIn("TURBOPUFFER_API_KEY", stderr.getvalue())
        self.assertEqual(rows.command[7:11], ("error", 2, "configuration_error", False))

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

    def test_v2_privacy_sentinels_and_enabled_disabled_output_equivalence(self) -> None:
        query = "QUERY_SENTINEL_PRIVATE"
        namespace = "site-sentinel-private-v1"
        credential = "CREDENTIAL_SENTINEL_PRIVATE"
        argv_secret = "ARGV_SENTINEL_PRIVATE"
        context_secret = "CONTEXT_SENTINEL_PRIVATE"
        os.environ["TURBOPUFFER_API_KEY"] = credential
        unrelated: ContextVar[str] = ContextVar("unrelated", default="default")
        token = unrelated.set(context_secret)
        enabled_stdout = StringIO()
        try:
            with patch.object(
                os, "environ", dict(os.environ)
            ), patch.object(
                __import__("sys"), "argv", ["buoy", argv_secret]
            ), redirect_stdout(enabled_stdout):
                self.assertEqual(
                    main(
                        [
                            "retrieve",
                            query,
                            "--namespace",
                            namespace,
                            "--dry-run",
                            "--json",
                        ]
                    ),
                    0,
                )
        finally:
            unrelated.reset(token)
        payload = self.payloads[0].decode("ascii")
        for sentinel in (query, namespace, credential, argv_secret, context_secret):
            self.assertNotIn(sentinel, payload)

        self.payloads.clear()
        disabled_stdout = StringIO()
        with patch.dict(os.environ, {}, clear=True), redirect_stdout(disabled_stdout):
            self.assertEqual(
                main(
                    [
                        "retrieve",
                        query,
                        "--namespace",
                        namespace,
                        "--dry-run",
                        "--json",
                    ]
                ),
                0,
            )
        self.assertEqual(enabled_stdout.getvalue(), disabled_stdout.getvalue())
        self.assertEqual(self.payloads, [])

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

    def test_entrypoint_timestamp_and_fake_clock_enclose_pipeline(self) -> None:
        self.payloads.clear()
        ticks = iter(range(1_700_000_000_000_000_000, 1_700_000_000_000_100_000, 1_000))
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
                    entry_started_at_ns=1_700_000_000_000_000_000,
                ),
                0,
            )
        rows = self._rows()
        self.assertIsNotNone(rows.retrieval_operation)
        assert rows.retrieval_operation is not None
        self.assertLessEqual(rows.command[2], rows.retrieval_operation[2])
        self.assertLessEqual(rows.retrieval_operation[3], rows.command[3])
        self.assertGreaterEqual(rows.command[4], rows.retrieval_operation[4])


if __name__ == "__main__":
    unittest.main()
