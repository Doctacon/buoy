from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from contextvars import ContextVar
from datetime import datetime, timedelta
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import textwrap
import unittest
from unittest.mock import Mock, patch

from opentelemetry import propagate, trace as otel_trace

from buoy_search import telemetry as telemetry_module
from buoy_search.config import RuntimeConfig
from buoy_search.retriever import (
    EvidenceRouteContext,
    HybridRetriever,
    MultiNamespaceRetriever,
    ProviderCallError,
    RetrievalOptions,
)
from buoy_search.telemetry import (
    QUERY_EMBED_SPAN_NAME,
    WIDENED_EVENT_NAME,
    copied_context_callable,
    local_telemetry_enabled,
    retrieval_trace,
    telemetry_span,
)
from buoy_search.telemetry_envelope import (
    TraceRows,
    decode_trace_envelope_v1,
)
from buoy_search.telemetry_queue import PublicationResult, telemetry_paths


class RecordingEmbedder:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def encode(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        return [[0.1, 0.2, 0.3]]


class StaticNamespace:
    def __init__(
        self,
        rows: list[dict[str, object]] | None = None,
        *,
        barrier: threading.Barrier | None = None,
        error: BaseException | None = None,
    ) -> None:
        self._rows = list(rows or [])
        self._barrier = barrier
        self._error = error
        self.calls = 0

    def multi_query(self, **_kwargs: object) -> dict[str, object]:
        self.calls += 1
        if self._barrier is not None:
            self._barrier.wait(timeout=5)
        if self._error is not None:
            raise self._error
        return {"rows": list(self._rows)}


class FixedReranker:
    def score(self, _query: str, passages: list[str]) -> list[float]:
        return [float(len(passages) - index) for index in range(len(passages))]


class AmbientInspectingNamespace(StaticNamespace):
    def __init__(self, rows: list[dict[str, object]]) -> None:
        super().__init__(rows)
        self.ambient_span_is_valid: bool | None = None
        self.injected_carrier: dict[str, str] | None = None

    def multi_query(self, **kwargs: object) -> dict[str, object]:
        self.ambient_span_is_valid = (
            otel_trace.get_current_span().get_span_context().is_valid
        )
        carrier: dict[str, str] = {}
        propagate.inject(carrier)
        self.injected_carrier = carrier
        return super().multi_query(**kwargs)


class CollectDecision:
    status = "unassessed"
    is_weak = None

    def to_dict(self) -> dict[str, object]:
        return {"status": self.status}


class CollectAssessor:
    mode = "collect"

    def assess(self, **_kwargs: object) -> CollectDecision:
        return CollectDecision()


def _row(
    row_id: str,
    *,
    title: str = "Title",
    url: str = "https://example.test/page",
    content: str = "Useful content",
    path: str = "docs/page.md",
) -> dict[str, object]:
    return {
        "id": row_id,
        "attributes": {
            "title": title,
            "url": url,
            "section_path": "Section",
            "content": content,
            "path": path,
            "repo_path": path,
            "tags": ["documentation"],
        },
    }


class LocalRetrievalTelemetryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.home = Path(self._temporary.name)
        self._home_patch = patch(
            "buoy_search.local_paths.Path.home",
            return_value=self.home,
        )
        self._environment_patch = patch.dict(os.environ, {}, clear=True)
        self._home_patch.start()
        self._environment_patch.start()

    def tearDown(self) -> None:
        self._environment_patch.stop()
        self._home_patch.stop()
        self._temporary.cleanup()

    def enable_telemetry(self) -> None:
        os.environ["BUOY_TELEMETRY"] = "local"

    @contextmanager
    def capture_envelopes(self) -> Iterator[tuple[list[bytes], Mock]]:
        captured: list[bytes] = []

        def publish(payload: bytes, *, paths: object) -> PublicationResult:
            del paths
            captured.append(payload)
            return PublicationResult(
                published=True,
                source_name="v1-00000000000000000000000000000001.json",
                reason="published",
            )

        with (
            patch.object(
                telemetry_module,
                "publish_envelope",
                side_effect=publish,
            ),
            patch.object(telemetry_module, "request_writer_start") as start,
        ):
            yield captured, start

    def single_retriever(
        self,
        namespace: StaticNamespace | None = None,
        *,
        config: RuntimeConfig | None = None,
    ) -> HybridRetriever:
        return HybridRetriever(
            namespace=namespace or StaticNamespace([_row("one")]),
            embedder=RecordingEmbedder(),
            config=config or RuntimeConfig(namespace="test-namespace"),
        )

    def multi_retriever(
        self,
        namespaces: list[StaticNamespace],
        *,
        namespace_names: list[str] | None = None,
    ) -> MultiNamespaceRetriever:
        names = namespace_names or [
            f"test-namespace-{index}" for index in range(len(namespaces))
        ]
        embedder = RecordingEmbedder()
        retrievers = [
            HybridRetriever(
                namespace=namespace,
                embedder=embedder,
                config=RuntimeConfig(namespace=name),
            )
            for namespace, name in zip(namespaces, names, strict=True)
        ]
        return MultiNamespaceRetriever(
            retrievers=retrievers,
            embedder=embedder,
            reranker_loader=FixedReranker,
        )

    @staticmethod
    def options(count: int = 1) -> list[RetrievalOptions]:
        return [
            RetrievalOptions(
                top_k=3,
                candidates=12,
                ranking_mode="chunk",
                ranking_profile="none",
            )
            for _ in range(count)
        ]

    def test_disabled_and_global_otel_disable_create_no_telemetry_files(self) -> None:
        for value in ("local", "LOCAL", " local", "local "):
            with self.subTest(buoy_value=value):
                self.assertTrue(
                    local_telemetry_enabled({"BUOY_TELEMETRY": value})
                )
        for value in ("", "true"):
            with self.subTest(disabled_buoy_value=value):
                self.assertFalse(
                    local_telemetry_enabled({"BUOY_TELEMETRY": value})
                )
        self.assertFalse(
            local_telemetry_enabled(
                {"BUOY_TELEMETRY": "local", "OTEL_SDK_DISABLED": "TRUE"}
            )
        )
        variants = (
            {},
            {"BUOY_TELEMETRY": "true"},
            {"BUOY_TELEMETRY": "local", "OTEL_SDK_DISABLED": "true"},
        )
        for environment in variants:
            with self.subTest(environment=environment):
                os.environ.clear()
                os.environ.update(environment)
                result = self.single_retriever().retrieve(
                    "query",
                    self.options()[0],
                )
                self.assertEqual([hit.id for hit in result.hits], ["one"])
                self.assertFalse(local_telemetry_enabled())
                self.assertFalse((self.home / ".buoy").exists())

    def test_opt_in_publishes_one_canonical_useful_trace_envelope(self) -> None:
        self.enable_telemetry()

        with patch.object(
            telemetry_module,
            "request_writer_start",
        ) as start:
            result = self.single_retriever().retrieve(
                "  useful query  ",
                self.options()[0],
            )

        self.assertEqual(result.query, "useful query")
        paths = telemetry_paths()
        ready = list(paths.ready_directory.iterdir())
        self.assertEqual(len(ready), 1)
        rows = decode_trace_envelope_v1(ready[0].read_bytes())
        start.assert_called_once_with(paths=paths)
        self.assertFalse(paths.database_path.exists())
        self.assertEqual(
            rows.run[5:14],
            (
                "explicit_single",
                "success",
                1,
                1,
                1,
                1,
                0,
                False,
                False,
            ),
        )
        self.assertEqual(
            rows.run[16:20],
            ("BAAI/bge-small-en-v1.5", "float32", 3, 12),
        )
        self.assertEqual(rows.run[21], 1)
        self.assertGreaterEqual(rows.run[4], 0.0)
        self.assertEqual(
            {span[3] for span in rows.spans},
            {"buoy.retrieve", "buoy.query.embed", "buoy.namespace.query"},
        )
        self.assertTrue(
            all(span[7] == "OK" and span[6] >= 0 for span in rows.spans)
        )
        self.assertEqual(
            sum(span[3] != "buoy.retrieve" for span in rows.spans),
            2,
        )

    def test_privacy_allowlist_drops_queries_content_locations_ids_and_errors(
        self,
    ) -> None:
        self.enable_telemetry()
        query_secret = "QUERY_SENTINEL_40f2ad"
        namespace_secret = "NAMESPACE_SENTINEL_7a1fd8"
        model_secret = "MODEL_PATH_SENTINEL_911bd2"
        precision_secret = "PRECISION_SENTINEL_04262c"
        content_secret = "CONTENT_SENTINEL_f4eb80"
        url_secret = "URL_SENTINEL_1a830d"
        path_secret = "PATH_SENTINEL_06ac77"
        id_secret = "ID_SENTINEL_86ee3f"
        raw_error_secret = "RAW_PROVIDER_ERROR_SENTINEL_f85024"
        injected_secret = "INJECTED_ATTRIBUTE_SENTINEL_f4a6c3"
        credential_secret = "CREDENTIAL_SENTINEL_3859f1"
        command_arg_secret = "COMMAND_ARG_SENTINEL_aec48d"
        os.environ["TURBOPUFFER_API_KEY"] = credential_secret
        config = RuntimeConfig(
            namespace=namespace_secret,
            embedding_model=model_secret,
            embedding_precision=precision_secret,
        )
        retriever = self.single_retriever(
            StaticNamespace(
                [
                    _row(
                        id_secret,
                        title=content_secret,
                        url=f"https://example.test/{url_secret}",
                        content=content_secret,
                        path=f"private/{path_secret}.md",
                    )
                ]
            ),
            config=config,
        )

        with self.capture_envelopes() as (captured, start):
            with patch.object(sys, "argv", ["buoy", command_arg_secret]):
                result = retriever.retrieve(query_secret, self.options()[0])
            self.assertEqual(result.hits[0].id, id_secret)
            with self.assertRaises(ProviderCallError):
                self.single_retriever(
                    StaticNamespace(error=RuntimeError(raw_error_secret)),
                    config=config,
                ).retrieve(query_secret, self.options()[0])

            with retrieval_trace(
                mode="explicit_single",
                embedding_model=model_secret,
                embedding_precision=precision_secret,
                top_k=1,
                candidates=1,
                namespace_count=1,
                initial_fanout=1,
                routing_selection_reason=injected_secret,
            ) as root_span:
                root_span.set_attribute("private.query", injected_secret)
                root_span.set_attribute(
                    "buoy.retrieval.mode",
                    injected_secret,
                )
                root_span.add_event(
                    f"private.{injected_secret}",
                    {"private.query": injected_secret},
                )
                root_span.set_attributes(
                    {
                        "buoy.retrieval.outcome": "success",
                        "buoy.retrieval.hit_count": 0,
                    }
                )
                root_span.mark_ok()

        self.assertEqual(len(captured), 3)
        self.assertEqual(start.call_count, 3)
        decoded: list[TraceRows] = [
            decode_trace_envelope_v1(payload) for payload in captured
        ]
        encoded = b"".join(captured).decode("ascii")
        custom_labels = {(rows.run[16], rows.run[17]) for rows in decoded}
        for sentinel in (
            query_secret,
            namespace_secret,
            model_secret,
            precision_secret,
            content_secret,
            url_secret,
            path_secret,
            id_secret,
            raw_error_secret,
            injected_secret,
            credential_secret,
            command_arg_secret,
        ):
            with self.subTest(sentinel=sentinel):
                self.assertNotIn(sentinel, encoded)
        self.assertEqual(custom_labels, {("custom", "custom")})

    def test_parallel_namespace_spans_keep_the_retrieval_root_parent(self) -> None:
        self.enable_telemetry()
        barrier = threading.Barrier(2)
        retriever = self.multi_retriever(
            [
                StaticNamespace(
                    [
                        _row(
                            "one",
                            url="https://example.test/one",
                            content="First content",
                            path="docs/one.md",
                        )
                    ],
                    barrier=barrier,
                ),
                StaticNamespace(
                    [
                        _row(
                            "two",
                            url="https://example.test/two",
                            content="Second content",
                            path="docs/two.md",
                        )
                    ],
                    barrier=barrier,
                ),
            ]
        )

        with self.capture_envelopes() as (captured, start):
            result = retriever.retrieve("parallel query", self.options(2))

        self.assertEqual(len(result.hits), 2)
        self.assertEqual(len(captured), 1)
        start.assert_called_once()
        rows = decode_trace_envelope_v1(captured[0])
        trace_id, root_span_id = rows.run[:2]
        namespace_spans = [
            span for span in rows.spans if span[3] == "buoy.namespace.query"
        ]
        self.assertEqual(len(namespace_spans), 2)
        self.assertEqual({row[0] for row in namespace_spans}, {trace_id})
        self.assertEqual({row[2] for row in namespace_spans}, {root_span_id})
        self.assertEqual(len({row[1] for row in namespace_spans}), 2)
        self.assertEqual(
            {json.loads(row[8])["buoy.route.rank"] for row in namespace_spans},
            {1, 2},
        )

    def test_private_trace_never_becomes_ambient_provider_context(self) -> None:
        self.enable_telemetry()
        namespace = AmbientInspectingNamespace([_row("one")])

        with self.capture_envelopes() as (captured, start):
            result = self.single_retriever(namespace).retrieve(
                "context query",
                self.options()[0],
            )

        self.assertEqual([hit.id for hit in result.hits], ["one"])
        self.assertFalse(namespace.ambient_span_is_valid)
        self.assertIsNotNone(namespace.injected_carrier)
        assert namespace.injected_carrier is not None
        self.assertNotIn("traceparent", namespace.injected_carrier)
        self.assertEqual(len(captured), 1)
        start.assert_called_once()
        rows = decode_trace_envelope_v1(captured[0])
        self.assertEqual(rows.run[6], "success")

    def test_executor_wrapper_never_copies_unrelated_contextvars(self) -> None:
        unrelated: ContextVar[str] = ContextVar(
            "test_unrelated_context",
            default="worker-default",
        )
        caller_token = unrelated.set("caller-secret")
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                disabled_value = executor.submit(
                    copied_context_callable(unrelated.get)
                ).result(timeout=5)
            self.assertEqual(disabled_value, "worker-default")

            self.enable_telemetry()
            with self.capture_envelopes() as (captured, start):
                with retrieval_trace(
                    mode="explicit_single",
                    embedding_model="BAAI/bge-small-en-v1.5",
                    embedding_precision="float32",
                    top_k=1,
                    candidates=1,
                    namespace_count=1,
                    initial_fanout=1,
                ) as root_span:

                    def observe_worker_context() -> tuple[str, bool]:
                        observed = unrelated.get()
                        with telemetry_span(
                            QUERY_EMBED_SPAN_NAME
                        ) as child_span:
                            enabled = child_span.enabled
                            child_span.mark_ok()
                        return observed, enabled

                    with ThreadPoolExecutor(max_workers=1) as executor:
                        enabled_value, child_enabled = executor.submit(
                            copied_context_callable(observe_worker_context)
                        ).result(timeout=5)
                    root_span.set_attributes(
                        {
                            "buoy.retrieval.outcome": "success",
                            "buoy.retrieval.hit_count": 0,
                        }
                    )
                    root_span.mark_ok()
        finally:
            unrelated.reset(caller_token)

        self.assertEqual(enabled_value, "worker-default")
        self.assertTrue(child_enabled)
        self.assertEqual(len(captured), 1)
        start.assert_called_once()
        rows = decode_trace_envelope_v1(captured[0])
        self.assertEqual(
            sum(span[3] == QUERY_EMBED_SPAN_NAME for span in rows.spans),
            1,
        )

    def test_invalid_otel_environment_cannot_break_import_or_retrieval(self) -> None:
        script = textwrap.dedent(
            """
            import os
            import buoy_search.telemetry as telemetry
            from buoy_search.config import RuntimeConfig
            from buoy_search.retriever import HybridRetriever, RetrievalOptions
            from buoy_search.telemetry_queue import PublicationResult

            captured = []

            def publish(payload, *, paths):
                del paths
                captured.append(payload)
                return PublicationResult(
                    published=True,
                    source_name="v1-00000000000000000000000000000001.json",
                    reason="published",
                )

            telemetry.publish_envelope = publish
            telemetry.request_writer_start = lambda *, paths: None
            expected_published = int(
                os.environ.pop("BUOY_TEST_EXPECTED_PUBLISHED")
            )

            class Embedder:
                def encode(self, _texts):
                    return [[0.1, 0.2, 0.3]]

            class Namespace:
                def multi_query(self, **_kwargs):
                    return {
                        "rows": [
                            {
                                "id": "one",
                                "attributes": {
                                    "title": "Title",
                                    "url": "https://example.test/one",
                                    "content": "Content",
                                },
                            }
                        ]
                    }

            result = HybridRetriever(
                namespace=Namespace(),
                embedder=Embedder(),
                config=RuntimeConfig(namespace="test"),
            ).retrieve(
                "query",
                RetrievalOptions(ranking_mode="chunk", ranking_profile="none"),
            )
            assert [hit.id for hit in result.hits] == ["one"]
            assert len(captured) == expected_published
            """
        )
        environment = dict(os.environ)
        environment.update(
            {
                "HOME": str(self.home),
                "BUOY_TELEMETRY": "local",
                "OTEL_SDK_DISABLED": "not-a-boolean",
                "OTEL_TRACES_SAMPLER": "not-a-sampler",
                "OTEL_ATTRIBUTE_COUNT_LIMIT": "not-an-integer",
                "OTEL_SPAN_EVENT_COUNT_LIMIT": "also-not-an-integer",
                "BUOY_TEST_EXPECTED_PUBLISHED": "1",
            }
        )

        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=Path(__file__).resolve().parents[1],
            env=environment,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

        self.assertEqual(
            completed.returncode,
            0,
            msg=f"stdout={completed.stdout!r} stderr={completed.stderr!r}",
        )
        self.assertEqual(completed.stdout, "")
        self.assertEqual(completed.stderr, "")
        self.assertFalse((self.home / ".buoy").exists())

        sdk_failure_home = self.home / "sdk-import-failure"
        sdk_failure_environment = dict(environment)
        sdk_failure_environment.update(
            {
                "HOME": str(sdk_failure_home),
                "OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT": "not-an-integer",
                "BUOY_TEST_EXPECTED_PUBLISHED": "0",
            }
        )
        sdk_failure = subprocess.run(
            [sys.executable, "-c", script],
            cwd=Path(__file__).resolve().parents[1],
            env=sdk_failure_environment,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(
            sdk_failure.returncode,
            0,
            msg=(
                f"stdout={sdk_failure.stdout!r} "
                f"stderr={sdk_failure.stderr!r}"
            ),
        )
        self.assertEqual(sdk_failure.stdout, "")
        self.assertEqual(sdk_failure.stderr, "")
        self.assertFalse((sdk_failure_home / ".buoy").exists())

    def test_controlled_nanosecond_clock_becomes_naive_utc_microseconds(
        self,
    ) -> None:
        self.enable_telemetry()
        controlled_time_ns = 1_704_067_200_123_456_789
        expected_utc_timestamp = datetime(1970, 1, 1) + timedelta(
            microseconds=controlled_time_ns // 1_000
        )

        with (
            self.capture_envelopes() as (captured, start),
            patch.object(
                telemetry_module,
                "_time_ns",
                return_value=controlled_time_ns,
            ),
        ):
            result = self.single_retriever().retrieve(
                "time query",
                self.options()[0],
            )

        self.assertEqual([hit.id for hit in result.hits], ["one"])
        self.assertEqual(len(captured), 1)
        start.assert_called_once()
        rows = decode_trace_envelope_v1(captured[0])
        self.assertEqual(rows.run[2], expected_utc_timestamp)
        self.assertEqual(rows.run[3], expected_utc_timestamp)
        self.assertIsNone(rows.run[2].tzinfo)
        self.assertEqual(
            {(span[4], span[5]) for span in rows.spans},
            {(expected_utc_timestamp, expected_utc_timestamp)},
        )

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks are unavailable")
    def test_symlinked_telemetry_directory_is_rejected_without_side_effects(
        self,
    ) -> None:
        baseline = self.single_retriever().retrieve(
            "same query",
            self.options()[0],
        ).to_dict()
        buoy_home = self.home / ".buoy"
        buoy_home.mkdir(mode=0o700)
        redirected = self.home / "redirected"
        redirected.mkdir(mode=0o700)
        telemetry_directory = buoy_home / "telemetry"
        try:
            telemetry_directory.symlink_to(redirected, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"could not create test symlink: {exc}")
        self.enable_telemetry()
        stdout = StringIO()
        stderr = StringIO()

        with (
            patch.object(telemetry_module, "request_writer_start") as start,
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            observed = (
                self.single_retriever()
                .retrieve("same query", self.options()[0])
                .to_dict()
            )

        self.assertEqual(observed, baseline)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")
        self.assertTrue(telemetry_directory.is_symlink())
        self.assertEqual(list(redirected.iterdir()), [])
        start.assert_not_called()

    def test_one_success_one_failure_records_partial_outcome(self) -> None:
        self.enable_telemetry()
        retriever = self.multi_retriever(
            [
                StaticNamespace([_row("success")]),
                StaticNamespace(error=RuntimeError("private provider detail")),
            ]
        )

        with self.capture_envelopes() as (captured, start):
            result = retriever.retrieve("partial query", self.options(2))

        self.assertEqual([hit.id for hit in result.hits], ["success"])
        self.assertTrue(result.incomplete)
        self.assertEqual(len(result.failures), 1)
        self.assertEqual(len(captured), 1)
        start.assert_called_once()
        rows = decode_trace_envelope_v1(captured[0])
        run = (
            rows.run[6],
            rows.run[7],
            rows.run[11],
            rows.run[12],
            rows.run[10],
        )
        namespace_attributes = [
            json.loads(span[8])
            for span in rows.spans
            if span[3] == "buoy.namespace.query"
        ]
        self.assertEqual(run, ("partial", 1, 1, True, 2))
        self.assertEqual(
            {
                attributes["buoy.namespace.status"]
                for attributes in namespace_attributes
            },
            {"ok", "failed"},
        )

    def test_automatic_singleton_records_evidence_mode_and_status(self) -> None:
        self.enable_telemetry()
        retriever = self.multi_retriever(
            [StaticNamespace([_row("supported")])]
        )

        with self.capture_envelopes() as (captured, start):
            result = retriever.retrieve(
                "automatic query",
                self.options(),
                evidence_assessor=CollectAssessor(),
                evidence_route_context=EvidenceRouteContext(
                    selection_reason="high_confidence_semantic",
                    semantic_score=0.9,
                    semantic_margin=0.2,
                ),
            )

        self.assertEqual([hit.id for hit in result.hits], ["supported"])
        self.assertEqual(result.evidence["mode"], "collect")
        self.assertEqual(result.evidence["status"], "unassessed")
        self.assertEqual(len(captured), 1)
        start.assert_called_once()
        rows = decode_trace_envelope_v1(captured[0])
        run = (rows.run[5], rows.run[6], rows.run[15], rows.run[8])
        evidence_attributes = [
            span[8]
            for span in rows.spans
            if span[3] == "buoy.evidence.assess"
        ]
        self.assertEqual(run, ("automatic", "success", "unassessed", 1))
        self.assertEqual(len(evidence_attributes), 1)
        self.assertEqual(
            json.loads(evidence_attributes[0]),
            {
                "buoy.evidence.mode": "collect",
                "buoy.evidence.status": "unassessed",
            },
        )

    def test_empty_top_route_records_widening_event_and_final_fanout(self) -> None:
        self.enable_telemetry()
        first = StaticNamespace()
        second = StaticNamespace([_row("fallback-hit")])
        retriever = self.multi_retriever([first, second])

        with self.capture_envelopes() as (captured, start):
            result = retriever.retrieve(
                "fallback query",
                self.options(2),
                initial_fanout=1,
            )

        self.assertEqual([hit.id for hit in result.hits], ["fallback-hit"])
        self.assertTrue(result.fallback.widened)
        self.assertEqual(result.fallback.reason, "empty_top1")
        self.assertEqual(first.calls, 1)
        self.assertEqual(second.calls, 1)
        self.assertEqual(len(captured), 1)
        start.assert_called_once()
        rows = decode_trace_envelope_v1(captured[0])
        run = (
            rows.run[6],
            rows.run[7],
            rows.run[9],
            rows.run[10],
            rows.run[11],
            rows.run[12],
            rows.run[13],
            rows.run[14],
        )
        self.assertEqual(
            run,
            ("success", 1, 1, 2, 0, False, True, "empty_top1"),
        )
        self.assertEqual(len(rows.events), 1)
        event = rows.events[0]
        self.assertEqual(event[3], WIDENED_EVENT_NAME)
        self.assertEqual(
            json.loads(event[5]),
            {
                "buoy.retrieval.fallback_reason": "empty_top1",
                "buoy.retrieval.final_fanout": 2,
                "buoy.retrieval.initial_fanout": 1,
            },
        )

    def test_all_provider_failure_preserves_exception_and_records_redacted_error(
        self,
    ) -> None:
        raw_error = "RAW_FAILURE_DETAIL_SENTINEL_dfe958"
        options = self.options(2)
        disabled = self.multi_retriever(
            [
                StaticNamespace(error=RuntimeError(raw_error)),
                StaticNamespace(error=RuntimeError(raw_error)),
            ]
        )
        with self.assertRaises(ProviderCallError) as disabled_error:
            disabled.retrieve("failing query", options)

        self.enable_telemetry()
        enabled = self.multi_retriever(
            [
                StaticNamespace(error=RuntimeError(raw_error)),
                StaticNamespace(error=RuntimeError(raw_error)),
            ]
        )
        with self.capture_envelopes() as (captured, start):
            with self.assertRaises(ProviderCallError) as enabled_error:
                enabled.retrieve("failing query", options)

        self.assertEqual(str(enabled_error.exception), str(disabled_error.exception))
        self.assertNotIn(raw_error, str(enabled_error.exception))
        self.assertEqual(len(captured), 1)
        start.assert_called_once()
        rows = decode_trace_envelope_v1(captured[0])
        run = (rows.run[6], rows.run[11], rows.run[12], rows.run[7])
        attributes = [span[8] for span in rows.spans]
        self.assertEqual(run, ("error", 2, True, 0))
        self.assertNotIn(raw_error, json.dumps(attributes))
        self.assertTrue(
            any(
                json.loads(value).get("buoy.error.type") == "provider_call_error"
                for value in attributes
            )
        )

    def test_sink_failure_does_not_change_retrieval_result(self) -> None:
        baseline = self.single_retriever().retrieve(
            "same query",
            self.options()[0],
        ).to_dict()
        self.enable_telemetry()

        stdout = StringIO()
        stderr = StringIO()
        with (
            patch.object(
                telemetry_module,
                "publish_envelope",
                side_effect=RuntimeError("sink unavailable"),
            ),
            patch.object(telemetry_module, "request_writer_start") as start,
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            observed = (
                self.single_retriever()
                .retrieve("same query", self.options()[0])
                .to_dict()
            )

        self.assertEqual(observed, baseline)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")
        start.assert_not_called()
        self.assertFalse((self.home / ".buoy").exists())

    def test_queue_lock_drop_does_not_change_retrieval_result(self) -> None:
        baseline = self.single_retriever().retrieve(
            "same query",
            self.options()[0],
        ).to_dict()
        self.enable_telemetry()

        stdout = StringIO()
        stderr = StringIO()
        dropped = PublicationResult(
            published=False,
            source_name=None,
            reason="queue_lock_timeout",
        )
        with (
            patch.object(
                telemetry_module,
                "publish_envelope",
                return_value=dropped,
            ),
            patch.object(telemetry_module, "request_writer_start") as start,
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            observed = (
                self.single_retriever()
                .retrieve("same query", self.options()[0])
                .to_dict()
            )

        self.assertEqual(observed, baseline)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")
        start.assert_not_called()
        self.assertFalse((self.home / ".buoy").exists())


if __name__ == "__main__":
    unittest.main()
