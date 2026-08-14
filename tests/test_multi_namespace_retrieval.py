from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import os
import sys
import threading
from types import ModuleType
import unittest
from unittest.mock import patch

from buoy_search.cli import main
from buoy_search.config import RuntimeConfig
from buoy_search.cross_encoder import (
    CROSS_ENCODER_MAX_LENGTH,
    CROSS_ENCODER_MODEL,
    CROSS_ENCODER_REVISION,
    load_cross_encoder_reranker,
)
from buoy_search.retriever import (
    HybridRetriever,
    MultiNamespaceRetriever,
    ProviderCallError,
    RetrievalOptions,
    SearchHit,
    rerank_dedupe_key,
)
from buoy_search.routing import RoutedRetrievalResult


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
                        "tags": [self.name, row_id],
                    },
                }
                for row_id in self.ids
            ]
        }


class EmptyNamespace:
    def __init__(self, name: str, order: list[str]) -> None:
        self.name = name
        self.order = order

    def multi_query(self, **_kwargs: object) -> dict[str, object]:
        self.order.append(self.name)
        return {"rows": []}


class BarrierNamespace(RankedNamespace):
    def __init__(
        self,
        name: str,
        ids: list[str],
        order: list[str],
        barrier: threading.Barrier,
    ) -> None:
        super().__init__(name, ids, order)
        self.barrier = barrier

    def multi_query(self, **kwargs: object) -> dict[str, object]:
        self.barrier.wait(timeout=3)
        return super().multi_query(**kwargs)


class FixedReranker:
    def __init__(self, scores: list[float] | None = None) -> None:
        self.scores = scores
        self.calls: list[tuple[str, list[str]]] = []

    def score(self, query: str, passages: list[str]) -> list[float]:
        self.calls.append((query, list(passages)))
        if self.scores is None:
            return [0.0] * len(passages)
        return list(self.scores)


class FakeRoutingSelection:
    def to_dict(self) -> dict[str, object]:
        return {"active": True, "strategy": "hybrid_rrf"}


class FailingNamespace:
    def __init__(self, name: str, order: list[str]) -> None:
        self.name = name
        self.order = order

    def multi_query(self, **_kwargs: object) -> dict[str, object]:
        self.order.append(self.name)
        raise RuntimeError("service unavailable")


class MultiNamespaceRetrieverTests(unittest.TestCase):
    def make_retriever(
        self,
        namespaces: list[object],
        embedder: RecordingEmbedder,
        *,
        reranker: FixedReranker | None = None,
        loader: object | None = None,
    ) -> MultiNamespaceRetriever:
        configs = [RuntimeConfig(namespace=f"namespace-{index}") for index in range(len(namespaces))]
        retrievers = [
            HybridRetriever(namespace=namespace, embedder=embedder, config=config)
            for namespace, config in zip(namespaces, configs, strict=True)
        ]
        if loader is None:
            loader = lambda: reranker or FixedReranker()
        return MultiNamespaceRetriever(
            retrievers=retrievers,
            embedder=embedder,
            reranker_loader=loader,  # type: ignore[arg-type]
        )

    def test_embeds_once_queries_concurrently_and_fuses_equal_ce_scores(self) -> None:
        order: list[str] = []
        embedder = RecordingEmbedder()
        reranker = FixedReranker()
        barrier = threading.Barrier(3)
        retriever = self.make_retriever(
            [
                BarrierNamespace("first", ["first-1", "first-2"], order, barrier),
                BarrierNamespace("second", ["second-1", "second-2"], order, barrier),
                BarrierNamespace("third", ["third-1", "third-2"], order, barrier),
            ],
            embedder,
            reranker=reranker,
        )

        result = retriever.retrieve(
            "  shared query  ",
            [
                RetrievalOptions(top_k=5, candidates=10, ranking_mode="chunk", ranking_profile="none"),
                RetrievalOptions(top_k=5, candidates=10, ranking_mode="chunk", ranking_profile="none"),
                RetrievalOptions(top_k=5, candidates=10, ranking_mode="chunk", ranking_profile="none"),
            ],
        )

        self.assertEqual(embedder.calls, [["shared query"]])
        self.assertCountEqual(order, ["first", "second", "third"])
        self.assertEqual(
            [(hit.namespace, hit.id) for hit in result.hits],
            [
                ("namespace-0", "first-1"),
                ("namespace-1", "second-1"),
                ("namespace-0", "first-2"),
                ("namespace-2", "third-1"),
                ("namespace-1", "second-2"),
            ],
        )
        payload = result.to_dict()
        self.assertNotIn("namespace", payload)
        self.assertEqual(
            payload["namespaces"],
            ["namespace-0", "namespace-1", "namespace-2"],
        )
        self.assertEqual(
            payload["fusion"], "cross_namespace_equal_weight_ordinal_rrf"
        )
        self.assertEqual(
            payload["routing"],
            {
                "active": False,
                "mode": "explicit",
                "selected_namespaces": [
                    "namespace-0",
                    "namespace-1",
                    "namespace-2",
                ],
                "initial_fanout": 3,
                "max_fanout": 3,
            },
        )
        self.assertTrue(payload["reranking"]["applied"])
        self.assertEqual(
            payload["reranking"]["method"], "equal_weight_ordinal_rrf"
        )
        self.assertEqual(payload["reranking"]["rrf_k"], 60)
        self.assertEqual(
            payload["reranking"]["components"],
            ["cross_encoder_rank", "namespace_rank"],
        )
        self.assertEqual(payload["hits"][0]["namespace"], "namespace-0")
        self.assertEqual(payload["hits"][0]["tags"], ["first", "first-1"])
        cross_namespace = payload["hits"][0]["score_info"]["cross_namespace"]
        self.assertEqual(cross_namespace["route_rank"], 1)
        self.assertEqual(cross_namespace["namespace_rank"], 1)
        self.assertEqual(cross_namespace["cross_encoder_rank"], 1)
        self.assertEqual(cross_namespace["cross_encoder_score"], 0.0)
        self.assertEqual(cross_namespace["reranker_score"], 0.0)
        self.assertEqual(
            cross_namespace["fusion_score"],
            cross_namespace["cross_encoder_rrf_score"]
            + cross_namespace["namespace_rrf_score"],
        )
        self.assertEqual(len(reranker.calls), 1)

        routed_payload = RoutedRetrievalResult(
            result=result,
            routing=FakeRoutingSelection(),  # type: ignore[arg-type]
        ).to_dict()
        self.assertEqual(routed_payload["hits"][0]["tags"], ["first", "first-1"])
        self.assertEqual(routed_payload["hits"][0]["namespace"], "namespace-0")
        self.assertEqual(routed_payload["routing"]["strategy"], "hybrid_rrf")

    def test_fusion_retains_a_strong_local_hit_over_a_slightly_better_ce_hit(self) -> None:
        order: list[str] = []
        retriever = self.make_retriever(
            [
                RankedNamespace("first", ["local-first"], order),
                RankedNamespace("second", ["ce-first", "ce-second"], order),
            ],
            RecordingEmbedder(),
            # Candidate input order is local-first, ce-first, ce-second. The
            # cross encoder prefers both second-namespace hits, but equal-weight
            # ordinal RRF lets the other namespace's local #1 beat its local #2.
            reranker=FixedReranker([0.8, 1.0, 0.9]),
        )

        result = retriever.retrieve(
            "query", [RetrievalOptions(top_k=3), RetrievalOptions(top_k=3)]
        )

        self.assertEqual(
            [hit.id for hit in result.hits],
            ["ce-first", "local-first", "ce-second"],
        )
        retained = result.hits[1].score_info["cross_namespace"]
        displaced = result.hits[2].score_info["cross_namespace"]
        self.assertEqual(retained["cross_encoder_rank"], 3)
        self.assertEqual(retained["namespace_rank"], 1)
        self.assertEqual(displaced["cross_encoder_rank"], 2)
        self.assertEqual(displaced["namespace_rank"], 2)
        self.assertGreater(retained["fusion_score"], displaced["fusion_score"])

    def test_cross_encoder_rank_orders_candidates_with_equal_local_rank(self) -> None:
        order: list[str] = []
        retriever = self.make_retriever(
            [
                RankedNamespace("first", ["weaker"], order),
                RankedNamespace("second", ["stronger"], order),
            ],
            RecordingEmbedder(),
            reranker=FixedReranker([0.1, 0.9]),
        )

        result = retriever.retrieve(
            "query", [RetrievalOptions(top_k=2), RetrievalOptions(top_k=2)]
        )

        self.assertEqual([hit.id for hit in result.hits], ["stronger", "weaker"])
        self.assertEqual(
            result.hits[0].score_info["cross_namespace"]["namespace_rank"], 1
        )
        self.assertEqual(
            result.hits[0].score_info["cross_namespace"]["cross_encoder_rank"], 1
        )

    def test_equal_fusion_scores_break_by_cross_encoder_rank(self) -> None:
        order: list[str] = []
        retriever = self.make_retriever(
            [
                RankedNamespace("first", ["local-one", "ce-one"], order),
                RankedNamespace("second", ["ce-two"], order),
            ],
            RecordingEmbedder(),
            # ce-one is CE #1 / local #2 and ce-two is CE #2 / local #1,
            # producing the same fused score. CE rank is the first tie-breaker.
            reranker=FixedReranker([0.1, 0.9, 0.8]),
        )

        result = retriever.retrieve(
            "query", [RetrievalOptions(top_k=3), RetrievalOptions(top_k=3)]
        )

        self.assertEqual(result.hits[0].id, "ce-one")
        self.assertEqual(result.hits[1].id, "ce-two")
        first_info = result.hits[0].score_info["cross_namespace"]
        second_info = result.hits[1].score_info["cross_namespace"]
        self.assertEqual(first_info["fusion_score"], second_info["fusion_score"])
        self.assertEqual(first_info["cross_encoder_rank"], 1)
        self.assertEqual(second_info["cross_encoder_rank"], 2)

    def test_top_k_represents_every_nonempty_namespace_when_space_allows(self) -> None:
        order: list[str] = []
        retriever = self.make_retriever(
            [
                RankedNamespace(
                    "dominant",
                    [f"dominant-{index}" for index in range(1, 9)],
                    order,
                ),
                RankedNamespace("minority", ["minority-1", "minority-2"], order),
            ],
            RecordingEmbedder(),
            # The minority candidate is last by both CE and fused rank, so the
            # coverage policy must replace the dominant namespace's worst hit.
            # minority-2 has the better cross-encoder/fused position inside
            # its corpus, but namespace coverage intentionally preserves the
            # existing hybrid retriever's local #1, minority-1.
            reranker=FixedReranker(
                [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, -1.0, 0.0]
            ),
        )

        result = retriever.retrieve(
            "query", [RetrievalOptions(top_k=3), RetrievalOptions(top_k=3)]
        )

        self.assertEqual(
            [hit.namespace for hit in result.hits],
            ["namespace-0", "namespace-0", "namespace-1"],
        )
        self.assertEqual(result.hits[-1].id, "minority-1")
        self.assertTrue(
            result.hits[-1].score_info["cross_namespace"][
                "namespace_coverage_promoted"
            ]
        )
        coverage = result.to_dict()["reranking"]["namespace_coverage"]
        self.assertEqual(coverage["promoted_namespaces"], ["namespace-1"])
        self.assertTrue(coverage["possible"])
        self.assertTrue(coverage["applied"])

    def test_namespace_coverage_is_reported_impossible_when_top_k_is_too_small(self) -> None:
        order: list[str] = []
        retriever = self.make_retriever(
            [
                RankedNamespace("first", ["first"], order),
                RankedNamespace("second", ["second"], order),
                RankedNamespace("third", ["third"], order),
            ],
            RecordingEmbedder(),
            reranker=FixedReranker([0.9, 0.8, 0.7]),
        )

        result = retriever.retrieve(
            "query",
            [
                RetrievalOptions(top_k=2),
                RetrievalOptions(top_k=2),
                RetrievalOptions(top_k=2),
            ],
        )

        self.assertEqual([hit.id for hit in result.hits], ["first", "second"])
        coverage = result.to_dict()["reranking"]["namespace_coverage"]
        self.assertFalse(coverage["possible"])
        self.assertFalse(coverage["applied"])
        self.assertEqual(coverage["required_namespaces"], [
            "namespace-0", "namespace-1", "namespace-2"
        ])

    def test_namespace_coverage_keeps_a_shared_duplicate_when_promoting_another_namespace(self) -> None:
        order: list[str] = []

        class SharedNamespace(RankedNamespace):
            def multi_query(self, **kwargs: object) -> dict[str, object]:
                payload = super().multi_query(**kwargs)
                for row in payload["rows"]:
                    if row["id"] == "shared":
                        row["attributes"].update(
                            {
                                "url": "https://example.com/shared",
                                "section_path": "Shared",
                                "content": "shared content",
                            }
                        )
                return payload

        retriever = self.make_retriever(
            [
                SharedNamespace("first", ["a1", "a2", "shared"], order),
                SharedNamespace("second", ["shared"], order),
                RankedNamespace("third", ["c1", "c2", "c3"], order),
            ],
            RecordingEmbedder(),
            # Pure fusion selects A, A, (A+B). C's local #1 is promoted;
            # the donor must be the second A-only hit, not the sole B member.
            reranker=FixedReranker([1.0, 0.9, 0.8, 0.1, 0.2, 0.3]),
        )

        result = retriever.retrieve(
            "query",
            [
                RetrievalOptions(top_k=3),
                RetrievalOptions(top_k=3),
                RetrievalOptions(top_k=3),
            ],
        )

        self.assertEqual([hit.id for hit in result.hits], ["a1", "shared", "c1"])
        self.assertEqual(
            result.hits[1].score_info["cross_namespace"]["duplicate_namespaces"],
            ["namespace-0", "namespace-1"],
        )
        self.assertTrue(
            result.hits[2].score_info["cross_namespace"][
                "namespace_coverage_promoted"
            ]
        )
        coverage = result.to_dict()["reranking"]["namespace_coverage"]
        self.assertTrue(coverage["possible"])
        self.assertEqual(coverage["promoted_namespaces"], ["namespace-2"])

    def test_successful_top1_does_not_load_or_query_fallbacks(self) -> None:
        order: list[str] = []
        embedder = RecordingEmbedder()
        loader_calls: list[bool] = []

        def forbidden_loader() -> FixedReranker:
            loader_calls.append(True)
            raise AssertionError("single route loaded reranker")

        retriever = self.make_retriever(
            [
                RankedNamespace("first", ["one"], order),
                FailingNamespace("second", order),
                FailingNamespace("third", order),
            ],
            embedder,
            loader=forbidden_loader,
        )

        result = retriever.retrieve(
            "query",
            [RetrievalOptions(), RetrievalOptions(), RetrievalOptions()],
            initial_fanout=1,
        )

        self.assertEqual(embedder.calls, [["query"]])
        self.assertEqual(order, ["first"])
        self.assertEqual(loader_calls, [])
        self.assertEqual(result.namespaces, ["namespace-0"])
        self.assertFalse(result.reranking.applied)
        self.assertIsNone(result.reranking.method)
        self.assertEqual(result.fusion, "single_namespace")
        self.assertFalse(result.fallback.widened)
        self.assertEqual(result.hits[0].namespace, "namespace-0")
        self.assertEqual(
            result.hits[0].score_info["cross_namespace"],
            {"route_rank": 1, "namespace_rank": 1},
        )

    def test_successful_top1_preserves_requested_top_k_above_rerank_cap(self) -> None:
        order: list[str] = []

        def forbidden_loader() -> FixedReranker:
            raise AssertionError("single route loaded reranker")

        retriever = self.make_retriever(
            [
                RankedNamespace(
                    "first", [f"row-{index}" for index in range(12)], order
                ),
                FailingNamespace("second", order),
            ],
            RecordingEmbedder(),
            loader=forbidden_loader,
        )

        result = retriever.retrieve(
            "query",
            [
                RetrievalOptions(
                    top_k=12, ranking_mode="chunk", ranking_profile="none"
                ),
                RetrievalOptions(
                    top_k=12, ranking_mode="chunk", ranking_profile="none"
                ),
            ],
            initial_fanout=1,
        )

        self.assertEqual(len(result.hits), 12)
        self.assertEqual(order, ["first"])

    def test_empty_top1_widens_once_and_reranks_fallbacks(self) -> None:
        order: list[str] = []
        embedder = RecordingEmbedder()
        reranker = FixedReranker([0.1, 0.9])
        retriever = self.make_retriever(
            [
                EmptyNamespace("first", order),
                RankedNamespace("second", ["two"], order),
                RankedNamespace("third", ["three"], order),
            ],
            embedder,
            reranker=reranker,
        )

        result = retriever.retrieve(
            "query",
            [RetrievalOptions(), RetrievalOptions(), RetrievalOptions()],
            initial_fanout=1,
        )

        self.assertEqual(embedder.calls, [["query"]])
        self.assertEqual(order.count("first"), 1)
        self.assertCountEqual(order, ["first", "second", "third"])
        self.assertEqual([hit.id for hit in result.hits], ["three", "two"])
        self.assertEqual(result.fallback.reason, "empty_top1")
        self.assertEqual(result.fallback.added_namespaces, ("namespace-1", "namespace-2"))
        self.assertFalse(result.incomplete)

    def test_failed_top1_preserves_fallback_successes_and_redacts_failure(self) -> None:
        order: list[str] = []
        embedder = RecordingEmbedder()
        retriever = self.make_retriever(
            [
                FailingNamespace("first", order),
                RankedNamespace("second", ["two"], order),
                EmptyNamespace("third", order),
            ],
            embedder,
            reranker=FixedReranker(),
        )

        result = retriever.retrieve(
            "query",
            [RetrievalOptions(), RetrievalOptions(), RetrievalOptions()],
            initial_fanout=1,
        )
        payload = result.to_dict()

        self.assertTrue(result.incomplete)
        self.assertEqual(result.fallback.reason, "failed_top1")
        self.assertEqual([hit.id for hit in result.hits], ["two"])
        self.assertEqual(payload["namespace_failures"][0]["namespace"], "namespace-0")
        self.assertNotIn("service unavailable", json.dumps(payload))
        self.assertFalse(result.reranking.applied)

    def test_ambiguous_route_reranks_two_successes_and_reports_one_partial_failure(self) -> None:
        order: list[str] = []
        reranker = FixedReranker([0.1, 0.9])
        retriever = self.make_retriever(
            [
                RankedNamespace("first", ["one"], order),
                FailingNamespace("second", order),
                RankedNamespace("third", ["three"], order),
            ],
            RecordingEmbedder(),
            reranker=reranker,
        )

        result = retriever.retrieve(
            "query",
            [RetrievalOptions(), RetrievalOptions(), RetrievalOptions()],
        )

        self.assertEqual([hit.id for hit in result.hits], ["three", "one"])
        self.assertTrue(result.reranking.applied)
        self.assertTrue(result.incomplete)
        self.assertEqual(
            [failure.namespace for failure in result.failures], ["namespace-1"]
        )
        self.assertEqual(
            [entry["namespace"] for entry in result.to_dict()["namespace_results"]],
            ["namespace-0", "namespace-2"],
        )

    def test_missing_reranker_fails_before_multi_content_queries(self) -> None:
        order: list[str] = []

        def missing_loader() -> FixedReranker:
            raise RuntimeError("exact model is unavailable")

        retriever = self.make_retriever(
            [
                RankedNamespace("first", ["one"], order),
                RankedNamespace("second", ["two"], order),
            ],
            RecordingEmbedder(),
            loader=missing_loader,
        )

        with self.assertRaisesRegex(RuntimeError, "exact model is unavailable"):
            retriever.retrieve(
                "query", [RetrievalOptions(), RetrievalOptions()]
            )
        self.assertEqual(order, [])

    def test_missing_reranker_after_empty_top1_prevents_fallback_queries(self) -> None:
        order: list[str] = []

        def missing_loader() -> FixedReranker:
            raise RuntimeError("exact model is unavailable")

        retriever = self.make_retriever(
            [
                EmptyNamespace("first", order),
                RankedNamespace("second", ["two"], order),
                RankedNamespace("third", ["three"], order),
            ],
            RecordingEmbedder(),
            loader=missing_loader,
        )

        with self.assertRaisesRegex(RuntimeError, "exact model is unavailable"):
            retriever.retrieve(
                "query",
                [RetrievalOptions(), RetrievalOptions(), RetrievalOptions()],
                initial_fanout=1,
            )
        self.assertEqual(order, ["first"])

    def test_all_provider_failures_are_fatal_and_attributed_without_details(self) -> None:
        order: list[str] = []
        embedder = RecordingEmbedder()
        retriever = self.make_retriever(
            [
                FailingNamespace("first", order),
                FailingNamespace("second", order),
                FailingNamespace("third", order),
            ],
            embedder,
            reranker=FixedReranker(),
        )

        with self.assertRaises(ProviderCallError) as raised:
            retriever.retrieve(
                "query",
                [RetrievalOptions(), RetrievalOptions(), RetrievalOptions()],
            )

        message = str(raised.exception)
        self.assertIn("namespace-0", message)
        self.assertIn("namespace-2", message)
        self.assertNotIn("service unavailable", message)
        self.assertEqual(embedder.calls, [["query"]])

    def test_candidate_pool_is_eight_each_deduplicated_and_globally_bounded(self) -> None:
        order: list[str] = []
        embedder = RecordingEmbedder()

        class DuplicateNamespace(RankedNamespace):
            def multi_query(self, **kwargs: object) -> dict[str, object]:
                payload = super().multi_query(**kwargs)
                first = payload["rows"][0]["attributes"]
                first.update(
                    {
                        "url": "https://example.com/shared#fragment",
                        "section_path": "Shared Section",
                        "content": "identical content",
                    }
                )
                return payload

        reranker = FixedReranker()
        retriever = self.make_retriever(
            [
                DuplicateNamespace("first", [f"first-{index}" for index in range(12)], order),
                DuplicateNamespace("second", [f"second-{index}" for index in range(12)], order),
                DuplicateNamespace("third", [f"third-{index}" for index in range(12)], order),
            ],
            embedder,
            reranker=reranker,
        )

        result = retriever.retrieve(
            "query",
            [
                RetrievalOptions(top_k=5, ranking_mode="chunk", ranking_profile="none"),
                RetrievalOptions(top_k=5, ranking_mode="chunk", ranking_profile="none"),
                RetrievalOptions(top_k=5, ranking_mode="chunk", ranking_profile="none"),
            ],
        )

        self.assertEqual(result.reranking.candidates_before_dedupe, 24)
        self.assertEqual(result.reranking.candidates_after_dedupe, 22)
        self.assertEqual(len(reranker.calls[0][1]), 22)
        self.assertEqual(len(result.hits), 5)
        shared = next(hit for hit in result.hits if hit.url.startswith("https://example.com/shared"))
        self.assertEqual(
            shared.score_info["cross_namespace"]["duplicate_namespaces"],
            ["namespace-0", "namespace-1", "namespace-2"],
        )

    def test_invalid_reranker_scores_fail_instead_of_falling_back_to_route_order(self) -> None:
        for scores in ([0.5], [0.5, float("nan")]):
            with self.subTest(scores=scores):
                order: list[str] = []
                retriever = self.make_retriever(
                    [
                        RankedNamespace("first", ["one"], order),
                        RankedNamespace("second", ["two"], order),
                    ],
                    RecordingEmbedder(),
                    reranker=FixedReranker(list(scores)),
                )
                with self.assertRaisesRegex(
                    RuntimeError, "wrong number|non-finite"
                ):
                    retriever.retrieve(
                        "query", [RetrievalOptions(), RetrievalOptions()]
                    )

    def test_dedupe_uses_canonical_url_but_namespace_qualifies_relative_paths(self) -> None:
        shared = {
            "section_path": " Shared   Section ",
            "content": "exact content",
        }
        url_one = SearchHit(
            id="one",
            namespace="namespace-0",
            url="https://EXAMPLE.com/docs/#one",
            **shared,
        )
        url_two = SearchHit(
            id="two",
            namespace="namespace-1",
            url="https://example.com/docs#two",
            section_path="shared section",
            content="exact content",
        )
        other_url = SearchHit(
            id="three",
            namespace="namespace-1",
            url="https://example.com/other",
            **shared,
        )
        repo_one = SearchHit(
            id="four",
            namespace="namespace-0",
            repo_path="README.md",
            **shared,
        )
        repo_two = SearchHit(
            id="five",
            namespace="namespace-1",
            repo_path="README.md",
            **shared,
        )

        self.assertEqual(rerank_dedupe_key(url_one), rerank_dedupe_key(url_two))
        self.assertNotEqual(rerank_dedupe_key(url_one), rerank_dedupe_key(other_url))
        self.assertNotEqual(rerank_dedupe_key(repo_one), rerank_dedupe_key(repo_two))


class CrossEncoderLoaderTests(unittest.TestCase):
    def tearDown(self) -> None:
        load_cross_encoder_reranker.cache_clear()

    def test_loader_is_lazy_cached_and_pins_local_safetensors_cpu_contract(self) -> None:
        module = ModuleType("sentence_transformers")
        init_calls: list[tuple[str, dict[str, object]]] = []
        predict_calls: list[tuple[list[tuple[str, str]], dict[str, object]]] = []

        class FakeCrossEncoder:
            def __init__(self, model: str, **kwargs: object) -> None:
                init_calls.append((model, kwargs))

            def predict(
                self, pairs: list[tuple[str, str]], **kwargs: object
            ) -> list[float]:
                predict_calls.append((pairs, kwargs))
                return [0.25] * len(pairs)

        module.CrossEncoder = FakeCrossEncoder  # type: ignore[attr-defined]
        load_cross_encoder_reranker.cache_clear()
        with patch.dict(sys.modules, {"sentence_transformers": module}):
            first = load_cross_encoder_reranker()
            second = load_cross_encoder_reranker()
            scores = first.score("query", ["one", "two"])

        self.assertIs(first, second)
        self.assertEqual(len(init_calls), 1)
        model, kwargs = init_calls[0]
        self.assertEqual(model, CROSS_ENCODER_MODEL)
        self.assertEqual(kwargs["revision"], CROSS_ENCODER_REVISION)
        self.assertTrue(kwargs["local_files_only"])
        self.assertFalse(kwargs["trust_remote_code"])
        self.assertEqual(kwargs["device"], "cpu")
        self.assertEqual(kwargs["max_length"], CROSS_ENCODER_MAX_LENGTH)
        self.assertEqual(kwargs["model_kwargs"], {"use_safetensors": True})
        self.assertEqual(scores, [0.25, 0.25])
        self.assertEqual(predict_calls[0][1]["batch_size"], 8)
        self.assertFalse(predict_calls[0][1]["show_progress_bar"])


class MultiNamespaceCliTests(unittest.TestCase):
    def test_missing_cli_namespace_enters_auto_mode_and_key_failure_precedes_client(self) -> None:
        with patch.dict(os.environ, {}, clear=True), patch(
            "buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY",
            side_effect=AssertionError("client constructed without key"),
        ):
            stdout = StringIO()
            stderr = StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                result = main(["retrieve", "query", "--json"])
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
        self.assertEqual(
            payload["reranking"]["method"], "equal_weight_ordinal_rrf"
        )
        self.assertEqual(payload["reranking"]["rrf_k"], 60)
        self.assertEqual(
            payload["reranking"]["components"],
            ["cross_encoder_rank", "namespace_rank"],
        )

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
                    "--dry-run",
                ]
            )

        self.assertEqual(result, 0)
        self.assertIn("namespaces: site-one-v1, site-two-v1", stdout.getvalue())
        self.assertIn("explicit multi-namespace retrieval plan", stdout.getvalue().lower())
        self.assertIn(
            "ranking[site-one-v1]: mode=page; profile=none; pool=20; aggregation=max",
            stdout.getvalue(),
        )
        self.assertIn(
            "ranking[site-two-v1]: mode=page; profile=none; pool=20; aggregation=max",
            stdout.getvalue(),
        )
        self.assertNotIn("mode=None", stdout.getvalue())

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
                    "--json",
                ]
            )

        self.assertEqual(result, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("Retrieval failed", stderr.getvalue())
        self.assertIn("service unavailable", stderr.getvalue())

    def test_plain_and_compatibility_live_explicit_outputs_are_identical(self) -> None:
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
                            "tags": ["library", "guide"],
                            "score_info": {},
                            "namespace": "site-one-v1",
                        },
                        {
                            "id": "row-two",
                            "title": "Two",
                            "url": "https://two.example/",
                            "content": "two",
                            "tags": [],
                            "score_info": {},
                            "namespace": "site-two-v1",
                        },
                    ],
                }

        class SuccessfulMultiRetriever:
            def __init__(self) -> None:
                self.calls: list[tuple[str, object]] = []

            def retrieve(self, query: str, options: object) -> TextResult:
                self.calls.append((query, options))
                return TextResult()

        retriever = SuccessfulMultiRetriever()
        stdout = StringIO()
        stderr = StringIO()
        with patch(
            "buoy_search.cli.MultiNamespaceRetriever.from_configs",
            return_value=retriever,
        ), redirect_stdout(stdout), redirect_stderr(stderr):
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

        self.assertEqual(result, 0, stderr.getvalue())
        self.assertEqual(len(retriever.calls), 1)
        output = stdout.getvalue()
        self.assertIn("Corpus: site-one-v1", output)
        self.assertIn("Corpus: site-two-v1", output)
        self.assertIn("Tags: library, guide", output)
        self.assertEqual(output.count("Tags:"), 1)

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
                    "--json",
                ]
            )

        self.assertEqual(result, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(captured_namespaces, ["site-one-v1", "site-two-v1"])
        self.assertIn("site-two-v1", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
