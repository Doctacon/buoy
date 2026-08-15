from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from io import StringIO
import json
import math
import os
import unittest
from unittest.mock import patch

from buoy_search.catalog import (
    ROUTING_DIMENSIONS,
    ROUTING_MODEL,
    ROUTING_QUERY_PREFIX,
    CardFields,
    NamespaceCard,
    prepare_card,
    vector_hash,
)
from buoy_search.cli import main
from buoy_search.evidence import EvidenceCalibrationError
from buoy_search.retriever import CalibratedEvidenceAssessor, EvidenceRouteContext
from buoy_search.remote_catalog import (
    CompatibilityContract,
    REMOTE_CATALOG_NAMESPACE,
    classify_remote_catalog,
)
from buoy_search.routing import (
    AutomaticRoutingError,
    hybrid_route,
    named_route,
    prototype_route,
    prototype_route_scores,
    semantic_route,
)


def unit_vector(index: int = 0) -> list[float]:
    vector = [0.0] * ROUTING_DIMENSIONS
    vector[index] = 1.0
    return vector


def cosine_vector(score: float) -> list[float]:
    vector = [0.0] * ROUTING_DIMENSIONS
    vector[0] = score
    vector[1] = math.sqrt(1.0 - score * score)
    return vector


class FixedEmbedder:
    def __init__(self, vector: list[float] | None = None) -> None:
        self.vector = list(vector or unit_vector())
        self.calls: list[list[str]] = []

    def encode(self, texts):  # noqa: ANN001 - protocol test double.
        self.calls.append(list(texts))
        return [list(self.vector) for _ in texts]


class FixedReranker:
    def __init__(self, scores: list[float]) -> None:
        self.scores = list(scores)
        self.calls: list[tuple[str, list[str]]] = []

    def score(self, query: str, passages):  # noqa: ANN001 - protocol test double.
        values = list(passages)
        self.calls.append((query, values))
        if len(values) != len(self.scores):
            raise AssertionError(
                f"expected {len(self.scores)} passages, received {len(values)}"
            )
        return list(self.scores)


def make_card(
    namespace: str,
    *,
    title: str | None = None,
    summary: str = "Routing test source.",
    aliases: list[str] | None = None,
    vector: list[float] | None = None,
    enabled: bool = True,
    embedding_precision: str = "float32",
    routing_examples: list[str] | None = None,
) -> NamespaceCard:
    return prepare_card(
        CardFields(
            namespace=namespace,
            enabled=enabled,
            source_kind="website",
            source_uri=f"https://{namespace}.example/docs",
            site_id=f"site-{namespace}",
            title=title or namespace,
            summary=summary,
            aliases=list(aliases or []),
            tags=["website"],
            semantic_origin="manual",
            region="gcp-us-central1",
            embedding_model=ROUTING_MODEL,
            embedding_precision=embedding_precision,
            plan_schema_version=2,
            ranking_mode="page",
            ranking_profile="none",
            ranking_pool=20,
            ranking_aggregation="max",
            routing_examples=list(routing_examples or []),
        ),
        embedder=FixedEmbedder(vector),
        now="2026-08-13T12:00:00+00:00",
    )


def snapshot(
    cards: list[NamespaceCard],
    *,
    extra_live: tuple[str, ...] = (),
):
    live = [REMOTE_CATALOG_NAMESPACE, *(card.namespace for card in cards), *extra_live]
    return classify_remote_catalog(
        live_namespace_ids=live,
        cards=cards,
        compatibility=CompatibilityContract(
            region="gcp-us-central1",
            embedding_model=ROUTING_MODEL,
            embedding_precision="float32",
        ),
    )


def run_cli(args: list[str], *, env: dict[str, str] | None = None) -> tuple[int, str, str]:
    stdout = StringIO()
    stderr = StringIO()
    with patch.object(os, "environ", env or {}), redirect_stdout(stdout), redirect_stderr(stderr):
        result = main(args)
    return result, stdout.getvalue(), stderr.getvalue()


class RoutingAlgorithmTests(unittest.TestCase):
    def test_title_and_alias_matching_never_uses_summary_or_tags_for_shortcut(self) -> None:
        cards = [
            make_card("dagster", title="Dagster", aliases=["dagster.io"]),
            make_card("other", title="Other", summary="Dagster website"),
        ]
        self.assertEqual(
            [card.namespace for card in named_route("How does dagster.io work?", cards)],
            ["dagster"],
        )
        self.assertEqual(named_route("website", cards), [])

    def test_simple_domain_title_matches_its_product_name_without_card_mutation(self) -> None:
        cards = [
            make_card("tpuf", title="turbopuffer.com", aliases=[]),
            make_card("other", title="Other"),
        ]
        self.assertEqual(
            [card.namespace for card in named_route("How does Turbopuffer work?", cards)],
            ["tpuf"],
        )
        self.assertEqual(
            [card.namespace for card in named_route("Read turbopuffer.com docs", cards)],
            ["tpuf"],
        )

    def test_unique_named_route_selects_one_with_bounded_fallback_candidates(self) -> None:
        cards = [
            make_card("dagster", title="Dagster", vector=cosine_vector(0.2)),
            make_card("tpuf", title="Turbopuffer", vector=cosine_vector(0.9)),
            make_card("thistle", title="Thistle", vector=cosine_vector(0.5)),
        ]
        selection = hybrid_route(
            "How does Dagster model assets?",
            cards,
            embedder=FixedEmbedder(),
            route_top_k=3,
        )
        self.assertEqual(selection.initial_fanout, 1)
        self.assertEqual(selection.selection_reason, "unique_title_or_alias")
        self.assertEqual(selection.selected_cards[0].namespace, "dagster")
        self.assertEqual(len(selection.selected_cards), 3)
        self.assertTrue(selection.entries[0].exact_name_match)

    def test_two_named_corpora_select_exactly_those_two(self) -> None:
        cards = [
            make_card("dagster", title="Dagster"),
            make_card("tpuf", title="Turbopuffer"),
            make_card("thistle", title="Thistle"),
        ]
        selection = hybrid_route(
            "Compare Turbopuffer and Dagster",
            cards,
            embedder=FixedEmbedder(),
            route_top_k=3,
        )
        self.assertEqual(
            {card.namespace for card in selection.selected_cards},
            {"dagster", "tpuf"},
        )
        self.assertEqual(selection.initial_fanout, 2)
        self.assertEqual(selection.selection_reason, "multiple_named_corpora")

    def test_three_named_corpora_select_exactly_those_three(self) -> None:
        cards = [
            make_card("dagster", title="Dagster"),
            make_card("tpuf", title="Turbopuffer"),
            make_card("thistle", title="Thistle"),
            make_card("oscilar", title="Oscilar"),
        ]
        selection = hybrid_route(
            "Compare Turbopuffer, Dagster, and Thistle",
            cards,
            embedder=FixedEmbedder(),
            route_top_k=3,
        )
        self.assertEqual(
            {card.namespace for card in selection.selected_cards},
            {"dagster", "tpuf", "thistle"},
        )
        self.assertEqual(selection.initial_fanout, 3)

    def test_more_than_three_named_corpora_fail_closed(self) -> None:
        cards = [
            make_card("dagster", title="Dagster"),
            make_card("tpuf", title="Turbopuffer"),
            make_card("thistle", title="Thistle"),
            make_card("oscilar", title="Oscilar"),
        ]
        with self.assertRaisesRegex(
            AutomaticRoutingError, "query names 4 corpora"
        ):
            hybrid_route(
                "Compare Turbopuffer, Dagster, Thistle, and Oscilar",
                cards,
                embedder=FixedEmbedder(),
                route_top_k=3,
            )

    def test_semantic_threshold_and_margin_choose_one_or_three(self) -> None:
        confident_cards = [
            make_card("first", vector=cosine_vector(0.80)),
            make_card("second", vector=cosine_vector(0.70)),
            make_card("third", vector=cosine_vector(0.20)),
        ]
        confident = hybrid_route(
            "descriptor free question",
            confident_cards,
            embedder=FixedEmbedder(),
            route_top_k=3,
        )
        self.assertTrue(confident.high_confidence)
        self.assertEqual(confident.initial_fanout, 1)
        self.assertEqual(confident.selection_reason, "high_confidence_semantic")

        ambiguous_cards = [
            make_card("first", vector=cosine_vector(0.80)),
            make_card("second", vector=cosine_vector(0.77)),
            make_card("third", vector=cosine_vector(0.20)),
        ]
        ambiguous = hybrid_route(
            "descriptor free question",
            ambiguous_cards,
            embedder=FixedEmbedder(),
            route_top_k=3,
        )
        self.assertFalse(ambiguous.high_confidence)
        self.assertEqual(ambiguous.initial_fanout, 3)
        self.assertEqual(ambiguous.selection_reason, "ambiguous_semantic")

    def test_semantic_query_is_prefixed_and_invalid_vectors_fail(self) -> None:
        embedder = FixedEmbedder()
        card = make_card("one")
        semantic_route(" routing question ", [card], embedder=embedder)
        self.assertEqual(embedder.calls, [[f"{ROUTING_QUERY_PREFIX}routing question"]])
        with self.assertRaisesRegex(AutomaticRoutingError, "exactly 384"):
            semantic_route("query", [card], embedder=FixedEmbedder([1.0]))

    def test_prototype_route_uses_one_embedding_and_max_example_score(self) -> None:
        cards = [
            make_card(
                "alpha",
                vector=cosine_vector(0.9),
                routing_examples=["Which API returns namespace schema metadata?"],
            ),
            make_card("beta", vector=cosine_vector(0.8)),
        ]
        embedder = FixedEmbedder()
        reranker = FixedReranker([-5.0, 8.0, 7.0])
        collect = prototype_route(
            "How can I inspect schema metadata?",
            cards,
            embedder=embedder,
            reranker_loader=lambda: reranker,
            route_top_k=3,
        )
        self.assertEqual(len(embedder.calls), 1)
        self.assertEqual(
            embedder.calls,
            [[f"{ROUTING_QUERY_PREFIX}How can I inspect schema metadata?"]],
        )
        self.assertEqual(len(reranker.calls), 1)
        self.assertEqual([card.namespace for card in collect.selected_cards], ["alpha", "beta"])
        self.assertEqual(collect.initial_fanout, 2)
        self.assertFalse(collect.high_confidence)
        self.assertEqual(collect.entries[0].winning_prototype_kind, "example")
        self.assertEqual(collect.entries[0].winning_prototype_index, 0)
        self.assertNotIn(
            "Which API returns",
            json.dumps(collect.to_dict()),
        )
        self.assertFalse(collect.to_dict()["active"])
        self.assertEqual(
            collect.to_dict()["confidence_artifact"]["mode"], "collect"
        )

    def test_prototype_shortlist_is_exact_and_bounded_to_twelve(self) -> None:
        cards = [make_card(f"card-{index:02d}") for index in range(13)]
        reranker = FixedReranker([float(index) for index in range(12)])
        scores = prototype_route_scores(
            "descriptor-free question",
            cards,
            embedder=FixedEmbedder(),
            reranker=reranker,
        )
        self.assertEqual(len(scores), 12)
        self.assertNotIn("card-12", {item.card.namespace for item in scores})
        self.assertEqual(len(reranker.calls[0][1]), 12)

    def test_prototype_stage_one_is_isolated_from_legacy_base_vectors(self) -> None:
        first_axis = unit_vector(0)
        second_axis = unit_vector(1)
        base_first = make_card(
            "base-first",
            vector=first_axis,
            routing_examples=["Base-first prototype example"],
        )
        prototype_first = make_card(
            "prototype-first",
            vector=second_axis,
            routing_examples=["Prototype-first example"],
        )
        base_first = replace(
            base_first,
            routing_prototype_vector=second_axis,
            routing_prototype_vector_hash=vector_hash(second_axis),
        )
        prototype_first = replace(
            prototype_first,
            routing_prototype_vector=first_axis,
            routing_prototype_vector_hash=vector_hash(first_axis),
        )
        cards = [base_first, prototype_first]

        legacy = semantic_route(
            "descriptor-free query",
            cards,
            embedder=FixedEmbedder(first_axis),
        )
        candidate = prototype_route_scores(
            "descriptor-free query",
            cards,
            embedder=FixedEmbedder(first_axis),
            reranker=FixedReranker([1.0, 1.0, 1.0, 1.0]),
        )
        hybrid = hybrid_route(
            "descriptor-free query",
            cards,
            embedder=FixedEmbedder(first_axis),
            route_top_k=3,
        )

        self.assertEqual(legacy[0][0].namespace, "base-first")
        self.assertEqual(hybrid.selected_cards[0].namespace, "base-first")
        self.assertEqual(candidate[0].card.namespace, "prototype-first")
        self.assertEqual(candidate[0].shortlist_rank, 1)

    def test_thousand_card_catalog_keeps_one_embedding_and_twelve_local_scores(self) -> None:
        cards = [make_card(f"card-{index:04d}") for index in range(1000)]
        embedder = FixedEmbedder()
        reranker = FixedReranker([0.0] * 12)

        scores = prototype_route_scores(
            "descriptor-free scale question",
            list(reversed(cards)),
            embedder=embedder,
            reranker=reranker,
        )

        self.assertEqual(len(embedder.calls), 1)
        self.assertEqual(len(reranker.calls), 1)
        self.assertEqual(len(reranker.calls[0][1]), 12)
        self.assertEqual(
            [item.card.namespace for item in scores],
            [f"card-{index:04d}" for index in range(12)],
        )

    def test_named_quality_observation_prepends_exact_card_to_bounded_shortlist(self) -> None:
        cards = [make_card(f"card-{index:02d}") for index in range(12)]
        cards.append(make_card("zz-named", title="Named Product"))
        scores = prototype_route_scores(
            "How does Named Product work?",
            cards,
            embedder=FixedEmbedder(),
            reranker=FixedReranker([0.0] * 12),
            include_exact_names=True,
        )
        named = next(item for item in scores if item.card.namespace == "zz-named")
        self.assertEqual(named.shortlist_rank, 1)
        self.assertEqual(len(scores), 12)

    def test_prototype_scoring_enforces_the_exact_108_passage_bound(self) -> None:
        examples = [f"Capability example {index}" for index in range(8)]
        cards = [
            make_card(f"card-{index:02d}", routing_examples=examples)
            for index in range(12)
        ]
        reranker = FixedReranker([0.0] * 108)
        prototype_route_scores(
            "bounded question",
            cards,
            embedder=FixedEmbedder(),
            reranker=reranker,
        )
        self.assertEqual(len(reranker.calls[0][1]), 108)

        invalid = replace(
            cards[0],
            routing_examples=[f"Too many {index}" for index in range(9)],
        )
        embedder = FixedEmbedder()
        with self.assertRaisesRegex(AutomaticRoutingError, "at most 8"):
            prototype_route_scores(
                "question",
                [invalid],
                embedder=embedder,
                reranker=FixedReranker([]),
            )
        self.assertEqual(embedder.calls, [])

        overlong = replace(cards[0], routing_examples=["q" * 513])
        with self.assertRaisesRegex(AutomaticRoutingError, "examples are invalid"):
            prototype_route_scores(
                "question",
                [overlong],
                embedder=FixedEmbedder(),
                reranker=FixedReranker([]),
            )

        stale = replace(
            cards[0],
            routing_prototype_vector_hash="0" * 64,
        )
        stale_embedder = FixedEmbedder()
        with self.assertRaisesRegex(AutomaticRoutingError, "projection is stale"):
            prototype_route_scores(
                "question",
                [stale],
                embedder=stale_embedder,
                reranker=FixedReranker([]),
            )
        self.assertEqual(stale_embedder.calls, [])

    def test_named_prototype_route_preserves_shortcut_and_skips_reranker(self) -> None:
        class FailingReranker:
            def score(self, _query, _passages):  # noqa: ANN001
                raise AssertionError("named route loaded reranker")

        embedder = FixedEmbedder()
        selection = prototype_route(
            "How does Dagster model assets?",
            [
                make_card("dagster", title="Dagster"),
                make_card("other", title="Other"),
            ],
            embedder=embedder,
            reranker_loader=lambda: FailingReranker(),
            route_top_k=3,
        )
        self.assertEqual(len(embedder.calls), 1)
        self.assertEqual(selection.initial_fanout, 1)
        self.assertEqual(selection.selection_reason, "unique_title_or_alias")
        self.assertEqual(selection.selected_cards[0].namespace, "dagster")

    def test_named_prototype_route_does_not_construct_reranker(self) -> None:
        selection = prototype_route(
            "How does Dagster model assets?",
            [make_card("dagster", title="Dagster"), make_card("other")],
            embedder=FixedEmbedder(),
            reranker_loader=lambda: (_ for _ in ()).throw(
                AssertionError("named route constructed reranker")
            ),
            route_top_k=3,
        )
        self.assertEqual(selection.selection_reason, "unique_title_or_alias")

    def test_prototype_reranker_failure_is_redacted(self) -> None:
        secret = "routing-prototype-secret"

        class LeakyReranker:
            def score(self, _query, _passages):  # noqa: ANN001
                raise RuntimeError(f"Bearer {secret}")

        with self.assertRaisesRegex(
            AutomaticRoutingError, "routing shortlist reranking failed"
        ) as raised:
            prototype_route_scores(
                "query",
                [make_card("one")],
                embedder=FixedEmbedder(),
                reranker=LeakyReranker(),
            )
        self.assertNotIn(secret, str(raised.exception))

    def test_prototype_reranker_loader_failure_is_redacted(self) -> None:
        secret = "routing-loader-secret"

        with self.assertRaisesRegex(
            AutomaticRoutingError, "routing shortlist reranker loading failed"
        ) as raised:
            prototype_route(
                "descriptor-free query",
                [make_card("one")],
                embedder=FixedEmbedder(),
                reranker_loader=lambda: (_ for _ in ()).throw(
                    RuntimeError(f"Bearer {secret}")
                ),
                route_top_k=3,
            )
        self.assertNotIn(secret, str(raised.exception))

    def test_empty_prototype_cards_fail_before_model_work(self) -> None:
        embedder = FixedEmbedder()
        reranker = FixedReranker([])
        with self.assertRaisesRegex(AutomaticRoutingError, "at least one eligible"):
            prototype_route_scores(
                "query",
                [],
                embedder=embedder,
                reranker=reranker,
            )
        self.assertEqual(embedder.calls, [])
        self.assertEqual(reranker.calls, [])

    def test_base_and_card_score_ties_keep_frozen_order_and_null_index(self) -> None:
        cards = [
            make_card("alpha", routing_examples=["Example"]),
            make_card("beta"),
        ]
        scores = prototype_route_scores(
            "query",
            cards,
            embedder=FixedEmbedder(),
            reranker=FixedReranker([2.0, 2.0, 2.0]),
        )
        self.assertEqual([item.card.namespace for item in scores], ["alpha", "beta"])
        self.assertEqual(scores[0].winning_prototype_kind, "card")
        selection = prototype_route(
            "query",
            cards,
            embedder=FixedEmbedder(),
            reranker_loader=lambda: FixedReranker([2.0, 2.0, 2.0]),
            route_top_k=3,
        )
        first = selection.to_dict()["selected_cards"][0]
        self.assertIn("winning_prototype_index", first)
        self.assertIsNone(first["winning_prototype_index"])

    def test_malformed_prototype_score_sequence_fails_safely(self) -> None:
        class InvalidReranker:
            def score(self, _query, _passages):  # noqa: ANN001
                return object()

        with self.assertRaisesRegex(AutomaticRoutingError, "invalid score sequence"):
            prototype_route_scores(
                "query",
                [make_card("one")],
                embedder=FixedEmbedder(),
                reranker=InvalidReranker(),
            )

    def test_prototype_embedder_failure_is_redacted(self) -> None:
        secret = "routing-embedder-secret"

        class LeakyEmbedder:
            def encode(self, _texts):  # noqa: ANN001
                raise RuntimeError(f"Bearer {secret}")

        with self.assertRaisesRegex(
            AutomaticRoutingError, "routing query embedding failed"
        ) as raised:
            prototype_route_scores(
                "query",
                [make_card("one")],
                embedder=LeakyEmbedder(),
                reranker=FixedReranker([1.0]),
            )
        self.assertNotIn(secret, str(raised.exception))


class AutomaticRoutingCliTests(unittest.TestCase):
    API_KEY = "tpuf_test-routing-secret"

    def _run_preview(self, query: str, cards: list[NamespaceCard], *, extra_live=()):
        catalog_snapshot = snapshot(cards, extra_live=extra_live)
        with patch(
            "buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY", return_value=object()
        ), patch(
            "buoy_search.cli.read_remote_catalog", return_value=catalog_snapshot
        ), patch(
            "buoy_search.cli.ROUTING_EMBEDDER_FACTORY", return_value=FixedEmbedder()
        ):
            return run_cli(
                ["retrieve", query, "--plan", "--json"],
                env={"TURBOPUFFER_API_KEY": self.API_KEY},
            )

    def test_automatic_preview_reports_route_without_querying_content(self) -> None:
        cards = [
            make_card("dagster", title="Dagster", vector=cosine_vector(0.5)),
            make_card("tpuf", title="Turbopuffer", vector=cosine_vector(0.9)),
            make_card("thistle", title="Thistle", vector=cosine_vector(0.2)),
        ]
        result, stdout, stderr = self._run_preview("Dagster assets", cards)
        payload = json.loads(stdout)
        self.assertEqual((result, stderr), (0, ""))
        self.assertTrue(payload["dry_run"])
        self.assertTrue(payload["credentials_required"])
        self.assertTrue(payload["turbopuffer_api_calls"])
        self.assertFalse(payload["content_retrieval_occurred"])
        self.assertEqual(payload["routing"]["selection_reason"], "unique_title_or_alias")
        self.assertEqual(payload["routing"]["initial_fanout"], 1)
        self.assertEqual(payload["initial_fanout"], 1)
        self.assertEqual(payload["namespaces"][0], "dagster")
        self.assertEqual(payload["evidence"]["mode"], "active")
        self.assertEqual(
            payload["evidence"]["status"], "requires_content_retrieval"
        )
        self.assertEqual(payload["evidence"]["threshold"], -8.0)
        self.assertEqual(
            payload["evidence"]["enforcement_scope"],
            "automatic_live_retrieval",
        )
        self.assertNotIn("vector", json.dumps(payload["routing"]["selected_cards"]))

    def test_automatic_live_wires_governed_evidence_assessment(self) -> None:
        cards = [
            make_card("dagster", title="Dagster", vector=cosine_vector(0.5)),
            make_card("tpuf", title="Turbopuffer", vector=cosine_vector(0.9)),
            make_card("thistle", title="Thistle", vector=cosine_vector(0.2)),
        ]
        catalog_snapshot = snapshot(cards)
        captured: dict[str, object] = {}

        class FakeResult:
            def to_dict(self) -> dict[str, object]:
                return {
                    "command": "retrieve",
                    "dry_run": False,
                    "content_retrieval_occurred": True,
                    "namespaces": ["dagster"],
                    "hits": [],
                    "evidence": {"mode": "active", "status": "supported"},
                }

        class FakeRetriever:
            def retrieve(self, _query, _options, **kwargs):  # noqa: ANN001
                captured.update(kwargs)
                return FakeResult()

        with patch(
            "buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY", return_value=object()
        ), patch(
            "buoy_search.cli.read_remote_catalog", return_value=catalog_snapshot
        ), patch(
            "buoy_search.cli.ROUTING_EMBEDDER_FACTORY", return_value=FixedEmbedder()
        ), patch(
            "buoy_search.cli.MultiNamespaceRetriever.from_configs",
            return_value=FakeRetriever(),
        ):
            result, stdout, stderr = run_cli(
                ["retrieve", "Dagster assets", "--json"],
                env={"TURBOPUFFER_API_KEY": self.API_KEY},
            )

        self.assertEqual((result, stderr), (0, ""))
        self.assertEqual(json.loads(stdout)["evidence"]["status"], "supported")
        self.assertIsInstance(
            captured["evidence_assessor"], CalibratedEvidenceAssessor
        )
        route_context = captured["evidence_route_context"]
        self.assertIsInstance(route_context, EvidenceRouteContext)
        self.assertEqual(route_context.selection_reason, "unique_title_or_alias")

    def test_plain_automatic_retrieval_wires_active_evidence_assessment(self) -> None:
        cards = [
            make_card("dagster", title="Dagster", vector=cosine_vector(0.5)),
            make_card("tpuf", title="Turbopuffer", vector=cosine_vector(0.9)),
            make_card("thistle", title="Thistle", vector=cosine_vector(0.2)),
        ]
        catalog_snapshot = snapshot(cards)
        captured: dict[str, object] = {}
        assessor = object()

        class FakeResult:
            def to_dict(self) -> dict[str, object]:
                return {
                    "command": "retrieve",
                    "dry_run": False,
                    "content_retrieval_occurred": True,
                    "namespaces": ["dagster"],
                    "embedding_precision": "float32",
                    "fusion": "cross_namespace_equal_weight_ordinal_rrf",
                    "hits": [
                        {
                            "id": "dagster-hit",
                            "title": "Dagster assets",
                            "url": "https://docs.dagster.io/guides/build/assets",
                            "content": "Assets model persistent objects.",
                        }
                    ],
                    "evidence": {"mode": "active", "status": "supported"},
                }

        class FakeRetriever:
            def retrieve(self, _query, _options, **kwargs):  # noqa: ANN001
                captured.update(kwargs)
                return FakeResult()

        with patch(
            "buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY", return_value=object()
        ), patch(
            "buoy_search.cli.read_remote_catalog", return_value=catalog_snapshot
        ), patch(
            "buoy_search.cli.ROUTING_EMBEDDER_FACTORY", return_value=FixedEmbedder()
        ), patch(
            "buoy_search.cli.MultiNamespaceRetriever.from_configs",
            return_value=FakeRetriever(),
        ), patch(
            "buoy_search.cli.CalibratedEvidenceAssessor",
            return_value=assessor,
        ):
            result, stdout, stderr = run_cli(
                ["retrieve", "Dagster assets"],
                env={"TURBOPUFFER_API_KEY": self.API_KEY},
            )

        self.assertEqual((result, stderr), (0, ""))
        self.assertEqual(
            stdout,
            "Found 1 passage.\n\n"
            "1. Dagster assets\n"
            "   https://docs.dagster.io/guides/build/assets\n"
            "   Assets model persistent objects.\n",
        )
        self.assertIs(captured["evidence_assessor"], assessor)
        self.assertIsInstance(
            captured["evidence_route_context"], EvidenceRouteContext
        )
        self.assertEqual(captured["initial_fanout"], 1)

    def test_catalog_resource_failure_cannot_leak_credentials(self) -> None:
        secret = "tpuf_AUTO_RESOURCE_SECRET"

        class LeakyProviderError(Exception):
            pass

        class ResourceExplodingClient:
            def namespaces(self, **_kwargs: object) -> object:
                return [
                    {"id": REMOTE_CATALOG_NAMESPACE},
                    {"id": "site-example-v1"},
                ]

            def namespace(self, _namespace: str) -> object:
                raise LeakyProviderError(f"Bearer {secret}")

        with patch(
            "buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY",
            return_value=ResourceExplodingClient(),
        ), patch(
            "buoy_search.cli.ROUTING_EMBEDDER_FACTORY",
            side_effect=AssertionError("routing model loaded after catalog failure"),
        ):
            result, stdout, stderr = run_cli(
                ["retrieve", "routing question", "--plan", "--json"],
                env={"TURBOPUFFER_API_KEY": secret},
            )

        self.assertEqual((result, stdout), (2, ""))
        self.assertIn("namespace resource acquisition", stderr)
        self.assertIn("LeakyProviderError", stderr)
        self.assertNotIn(secret, stderr)
        self.assertNotIn("Bearer", stderr)

    def test_missing_or_incompatible_live_card_fails_before_route_model(self) -> None:
        cards = [
            make_card("eligible"),
            make_card("incompatible", embedding_precision="float16"),
        ]
        catalog_snapshot = snapshot(cards, extra_live=("missing",))
        with patch(
            "buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY", return_value=object()
        ), patch(
            "buoy_search.cli.read_remote_catalog", return_value=catalog_snapshot
        ), patch(
            "buoy_search.cli.ROUTING_EMBEDDER_FACTORY",
            side_effect=AssertionError("route model loaded"),
        ):
            result, stdout, stderr = run_cli(
                ["retrieve", "query", "--plan", "--json"],
                env={"TURBOPUFFER_API_KEY": self.API_KEY},
            )
        self.assertEqual((result, stdout), (2, ""))
        self.assertIn("missing cards", stderr)
        self.assertIn("incompatible cards", stderr)

    def test_invalid_evidence_artifact_fails_before_provider_work(self) -> None:
        with patch(
            "buoy_search.cli.load_evidence_calibration",
            side_effect=EvidenceCalibrationError("artifact is incompatible"),
        ), patch(
            "buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY",
            side_effect=AssertionError("catalog client constructed"),
        ):
            result, stdout, stderr = run_cli(
                ["retrieve", "query", "--plan", "--json"],
                env={"TURBOPUFFER_API_KEY": self.API_KEY},
            )

        self.assertEqual((result, stdout), (2, ""))
        self.assertIn("Automatic evidence assessment failed", stderr)
        self.assertIn("artifact is incompatible", stderr)

    def test_disabled_and_stale_cards_are_covered_but_excluded(self) -> None:
        eligible = make_card("eligible", vector=unit_vector())
        disabled = make_card("disabled", enabled=False, vector=unit_vector())
        stale = make_card("stale", vector=unit_vector())
        catalog_snapshot = classify_remote_catalog(
            live_namespace_ids=(REMOTE_CATALOG_NAMESPACE, "eligible", "disabled"),
            cards=(eligible, disabled, stale),
            compatibility=CompatibilityContract(
                region="gcp-us-central1",
                embedding_model=ROUTING_MODEL,
                embedding_precision="float32",
            ),
        )
        with patch(
            "buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY", return_value=object()
        ), patch(
            "buoy_search.cli.read_remote_catalog", return_value=catalog_snapshot
        ), patch(
            "buoy_search.cli.ROUTING_EMBEDDER_FACTORY", return_value=FixedEmbedder()
        ):
            result, stdout, stderr = run_cli(
                ["retrieve", "query", "--plan", "--json"],
                env={"TURBOPUFFER_API_KEY": self.API_KEY},
            )
        payload = json.loads(stdout)
        self.assertEqual((result, stderr), (0, ""))
        self.assertEqual(payload["namespaces"], ["eligible"])
        self.assertEqual(payload["routing"]["exclusion_counts"], {"disabled": 1, "stale_target": 1})
        self.assertEqual(
            payload["routing"]["exclusion_ids"],
            {"disabled": ["disabled"], "stale_target": ["stale"]},
        )

    def test_removed_route_top_k_is_rejected_before_provider_work(self) -> None:
        with patch(
            "buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY",
            side_effect=AssertionError("catalog client constructed"),
        ):
            stdout = StringIO()
            stderr = StringIO()
            with patch.object(
                os, "environ", {"TURBOPUFFER_API_KEY": self.API_KEY}
            ), redirect_stdout(stdout), redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as raised:
                    main(
                        [
                            "retrieve",
                            "query",
                            "--route-top-k",
                            "1",
                            "--plan",
                            "--json",
                        ]
                    )
        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("unrecognized arguments: --route-top-k 1", stderr.getvalue())

    def test_missing_key_fails_before_client_even_if_ambient_namespace_is_set(self) -> None:
        with patch(
            "buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY",
            side_effect=AssertionError("client constructed"),
        ):
            result, stdout, stderr = run_cli(
                ["retrieve", "query", "--json"],
                env={"TURBOPUFFER_NAMESPACE": "must-be-ignored"},
            )
        self.assertEqual((result, stdout), (2, ""))
        self.assertIn("TURBOPUFFER_API_KEY", stderr)

    def test_explicit_preview_bypasses_credentials_catalog_and_route_model(self) -> None:
        with patch(
            "buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY",
            side_effect=AssertionError("catalog client constructed"),
        ), patch(
            "buoy_search.cli.ROUTING_EMBEDDER_FACTORY",
            side_effect=AssertionError("route model loaded"),
        ), patch(
            "buoy_search.cli.load_evidence_calibration",
            side_effect=AssertionError("evidence calibration loaded"),
        ):
            result, stdout, stderr = run_cli(
                [
                    "retrieve",
                    "query",
                    "--namespace",
                    "site-one-v1",
                    "--namespace",
                    "site-two-v1",
                    "--plan",
                    "--json",
                ]
            )
        payload = json.loads(stdout)
        self.assertEqual((result, stderr), (0, ""))
        self.assertEqual(payload["routing"]["mode"], "explicit")
        self.assertFalse(payload["routing"]["active"])
        self.assertFalse(payload["credentials_required"])
        self.assertFalse(payload["turbopuffer_api_calls"])
        self.assertNotIn("evidence", payload)

    def test_explicit_live_single_and_multi_bypass_active_evidence_gate(self) -> None:
        class FakeResult:
            def to_dict(self) -> dict[str, object]:
                return {
                    "command": "retrieve",
                    "dry_run": False,
                    "hits": [],
                }

        class FakeRetriever:
            def retrieve(self, _query, _options, **kwargs):  # noqa: ANN001
                self.assert_no_automatic_kwargs(kwargs)
                return FakeResult()

            @staticmethod
            def assert_no_automatic_kwargs(kwargs: dict[str, object]) -> None:
                if kwargs:
                    raise AssertionError(
                        "explicit retrieval received automatic evidence arguments"
                    )

        with patch(
            "buoy_search.cli.load_evidence_calibration",
            side_effect=AssertionError("evidence calibration loaded"),
        ), patch(
            "buoy_search.cli.HybridRetriever.from_config",
            return_value=FakeRetriever(),
        ), patch(
            "buoy_search.cli.MultiNamespaceRetriever.from_configs",
            return_value=FakeRetriever(),
        ):
            for namespaces in (
                ["site-one-v1"],
                ["site-one-v1", "site-two-v1"],
            ):
                with self.subTest(namespaces=namespaces):
                    args = ["retrieve", "query", "--json"]
                    for namespace in namespaces:
                        args.extend(["--namespace", namespace])
                    result, stdout, stderr = run_cli(args)
                    self.assertEqual((result, stderr), (0, ""))
                    self.assertEqual(json.loads(stdout)["hits"], [])


if __name__ == "__main__":
    unittest.main()
