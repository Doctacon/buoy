from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import os
import unittest
from unittest.mock import patch

from buoy_search.cli import main
from buoy_search.config import RuntimeConfig
from buoy_search.retriever import (
    RRF_K,
    HybridRetriever,
    MultiNamespaceRetriever,
    RetrievalOptions,
)


class RecordingEmbedder:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def encode(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        return [[0.1, 0.2, 0.3]]


class RankedNamespace:
    def __init__(self, name: str, ids: list[str], order: list[str]) -> None:
        self.name = name
        self.ids = ids
        self.order = order

    def multi_query(self, **_kwargs: object) -> dict[str, object]:
        self.order.append(self.name)
        return {
            "rows": [
                {
                    "id": row_id,
                    "attributes": {
                        "title": f"{self.name} {row_id}",
                        "url": f"https://example.com/{self.name}/{row_id}",
                        "content": f"content {row_id}",
                    },
                }
                for row_id in self.ids
            ]
        }


class FailingNamespace:
    def __init__(self, name: str, order: list[str]) -> None:
        self.name = name
        self.order = order

    def multi_query(self, **_kwargs: object) -> dict[str, object]:
        self.order.append(self.name)
        raise RuntimeError("service unavailable")


class MultiNamespaceRetrieverTests(unittest.TestCase):
    def make_retriever(self, namespaces: list[object], embedder: RecordingEmbedder) -> MultiNamespaceRetriever:
        configs = [RuntimeConfig(namespace=f"namespace-{index}") for index in range(len(namespaces))]
        retrievers = [
            HybridRetriever(namespace=namespace, embedder=embedder, config=config)
            for namespace, config in zip(namespaces, configs, strict=True)
        ]
        return MultiNamespaceRetriever(retrievers=retrievers, embedder=embedder)

    def test_embeds_once_queries_in_order_and_rrf_ties_use_namespace_order(self) -> None:
        order: list[str] = []
        embedder = RecordingEmbedder()
        retriever = self.make_retriever(
            [
                RankedNamespace("first", ["shared", "first-2"], order),
                RankedNamespace("second", ["shared", "second-2"], order),
            ],
            embedder,
        )

        result = retriever.retrieve(
            "  shared query  ",
            [
                RetrievalOptions(top_k=4, candidates=10, ranking_mode="chunk", ranking_profile="none"),
                RetrievalOptions(top_k=4, candidates=10, ranking_mode="chunk", ranking_profile="none"),
            ],
        )

        self.assertEqual(embedder.calls, [["shared query"]])
        self.assertEqual(order, ["first", "second"])
        self.assertEqual(
            [(hit.namespace, hit.id) for hit in result.hits],
            [
                ("namespace-0", "shared"),
                ("namespace-1", "shared"),
                ("namespace-0", "first-2"),
                ("namespace-1", "second-2"),
            ],
        )
        payload = result.to_dict()
        self.assertNotIn("namespace", payload)
        self.assertEqual(payload["namespaces"], ["namespace-0", "namespace-1"])
        self.assertEqual(payload["fusion"], "cross_namespace_rrf")
        self.assertEqual(payload["hits"][0]["namespace"], "namespace-0")
        self.assertEqual(payload["hits"][1]["namespace"], "namespace-1")
        self.assertIn("cross_namespace_rrf_score", payload["hits"][0]["score_info"])
        self.assertEqual(RRF_K, 60)
        self.assertAlmostEqual(
            payload["hits"][0]["score_info"]["cross_namespace_rrf_score"],
            1.0 / (RRF_K + 1),
        )

    def test_namespace_failure_aborts_with_attribution_after_one_embedding(self) -> None:
        order: list[str] = []
        embedder = RecordingEmbedder()
        retriever = self.make_retriever(
            [RankedNamespace("first", ["one"], order), FailingNamespace("second", order)],
            embedder,
        )

        with self.assertRaisesRegex(RuntimeError, "namespace-1"):
            retriever.retrieve(
                "query",
                [RetrievalOptions(), RetrievalOptions()],
            )

        self.assertEqual(embedder.calls, [["query"]])
        self.assertEqual(order, ["first", "second"])


class MultiNamespaceCliTests(unittest.TestCase):
    def test_missing_cli_namespace_enters_auto_mode_and_key_failure_precedes_client(self) -> None:
        for extra in ([], ["--live"]):
            with self.subTest(extra=extra), patch.dict(os.environ, {}, clear=True), patch(
                "buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY",
                side_effect=AssertionError("client constructed without key"),
            ):
                stdout = StringIO()
                stderr = StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    result = main(["retrieve", "query", *extra, "--json"])
            self.assertEqual(result, 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("TURBOPUFFER_API_KEY", stderr.getvalue())

    def test_duplicate_cli_namespace_fails_before_config(self) -> None:
        with patch("buoy_search.cli.config_from_args", side_effect=AssertionError("config loaded")):
            stdout = StringIO()
            stderr = StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                result = main(
                    [
                        "retrieve",
                        "query",
                        "--namespace",
                        "site-repeat-v1",
                        "--namespace",
                        "site-repeat-v1",
                        "--live",
                    ]
                )

        self.assertEqual(result, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("must not repeat namespace ID 'site-repeat-v1'", stderr.getvalue())

    def test_environment_namespace_is_ignored_and_does_not_bypass_auto_credentials(self) -> None:
        with patch.dict(os.environ, {"TURBOPUFFER_NAMESPACE": "site-env-v1"}, clear=True), patch(
            "buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY",
            side_effect=AssertionError("client constructed without key"),
        ):
            stdout, stderr = StringIO(), StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                result = main(["retrieve", " query ", "--dry-run", "--json"])

        self.assertEqual(result, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("TURBOPUFFER_API_KEY", stderr.getvalue())
        self.assertNotIn("site-env-v1", stderr.getvalue())

    def test_repeated_cli_namespaces_replace_environment_and_preserve_order(self) -> None:
        with patch.dict(os.environ, {"TURBOPUFFER_NAMESPACE": "site-env-v1"}, clear=True):
            stdout = StringIO()
            with redirect_stdout(stdout):
                result = main(
                    [
                        "retrieve",
                        "query",
                        "--namespace",
                        "github-first-v1",
                        "--namespace",
                        "site-second-v1",
                        "--dry-run",
                        "--json",
                    ]
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(payload["namespaces"], ["github-first-v1", "site-second-v1"])
        self.assertNotIn("namespace", payload)
        self.assertEqual(
            [plan["namespace"] for plan in payload["namespace_plans"]],
            ["github-first-v1", "site-second-v1"],
        )
        self.assertEqual(payload["namespace_plans"][0]["ranking_mode"], "file")
        self.assertEqual(payload["namespace_plans"][1]["ranking_mode"], "page")

    def test_multi_dry_run_text_names_selected_namespaces(self) -> None:
        stdout = StringIO()
        with redirect_stdout(stdout):
            result = main(
                [
                    "retrieve",
                    "query",
                    "--namespace",
                    "site-one-v1",
                    "--namespace",
                    "site-two-v1",
                ]
            )

        self.assertEqual(result, 0)
        self.assertIn("namespaces: site-one-v1, site-two-v1", stdout.getvalue())
        self.assertIn("ranking site-one-v1", stdout.getvalue())
        self.assertIn("ranking site-two-v1", stdout.getvalue())

    def test_blank_query_fails_before_config(self) -> None:
        with patch("buoy_search.cli.config_from_args", side_effect=AssertionError("config loaded")):
            stdout = StringIO()
            stderr = StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                result = main(["retrieve", "   ", "--namespace", "site-one-v1", "--json"])
        self.assertEqual(result, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("non-empty query", stderr.getvalue())

    def test_single_live_namespace_failure_names_selected_namespace(self) -> None:
        class FailingSingleRetriever:
            def retrieve(self, _query: str, _options: object) -> object:
                raise RuntimeError("service unavailable")

        stdout = StringIO()
        stderr = StringIO()
        with patch(
            "buoy_search.cli.HybridRetriever.from_config",
            return_value=FailingSingleRetriever(),
        ), redirect_stdout(stdout), redirect_stderr(stderr):
            result = main(
                [
                    "retrieve",
                    "query",
                    "--namespace",
                    "site-only-v1",
                    "--live",
                    "--json",
                ]
            )

        self.assertEqual(result, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("Retrieval failed for namespace 'site-only-v1'", stderr.getvalue())
        self.assertIn("service unavailable", stderr.getvalue())

    def test_multi_live_text_attributes_each_hit_namespace(self) -> None:
        class TextResult:
            def to_dict(self) -> dict[str, object]:
                return {
                    "dry_run": False,
                    "namespaces": ["site-one-v1", "site-two-v1"],
                    "fusion": "cross_namespace_rrf",
                    "embedding_precision": "float32",
                    "hits": [
                        {
                            "id": "row-one",
                            "title": "One",
                            "url": "https://one.example/",
                            "content": "one",
                            "score_info": {},
                            "namespace": "site-one-v1",
                        },
                        {
                            "id": "row-two",
                            "title": "Two",
                            "url": "https://two.example/",
                            "content": "two",
                            "score_info": {},
                            "namespace": "site-two-v1",
                        },
                    ],
                }

        class SuccessfulMultiRetriever:
            def retrieve(self, _query: str, _options: object) -> TextResult:
                return TextResult()

        stdout = StringIO()
        stderr = StringIO()
        with patch(
            "buoy_search.cli.MultiNamespaceRetriever.from_configs",
            return_value=SuccessfulMultiRetriever(),
        ), redirect_stdout(stdout), redirect_stderr(stderr):
            result = main(
                [
                    "retrieve",
                    "query",
                    "--namespace",
                    "site-one-v1",
                    "--namespace",
                    "site-two-v1",
                    "--live",
                ]
            )

        self.assertEqual(result, 0, stderr.getvalue())
        self.assertIn("Namespace: site-one-v1", stdout.getvalue())
        self.assertIn("Namespace: site-two-v1", stdout.getvalue())

    def test_live_namespace_failure_prints_no_partial_payload(self) -> None:
        class FailingMultiRetriever:
            def retrieve(self, _query: str, _options: object) -> object:
                raise RuntimeError("Retrieval failed for namespace 'site-two-v1': unavailable")

        captured_namespaces: list[str] = []

        def fake_from_configs(configs: object) -> FailingMultiRetriever:
            captured_namespaces.extend(config.namespace for config in configs)
            return FailingMultiRetriever()

        stdout = StringIO()
        stderr = StringIO()
        with patch(
            "buoy_search.cli.MultiNamespaceRetriever.from_configs",
            side_effect=fake_from_configs,
        ), redirect_stdout(stdout), redirect_stderr(stderr):
            result = main(
                [
                    "retrieve",
                    "query",
                    "--namespace",
                    "site-one-v1",
                    "--namespace",
                    "site-two-v1",
                    "--live",
                    "--json",
                ]
            )

        self.assertEqual(result, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(captured_namespaces, ["site-one-v1", "site-two-v1"])
        self.assertIn("site-two-v1", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
