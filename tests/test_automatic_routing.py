from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
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


def make_card(
    namespace: str,
    *,
    title: str | None = None,
    summary: str = "Routing test source.",
    aliases: list[str] | None = None,
    vector: list[float] | None = None,
    enabled: bool = True,
    embedding_precision: str = "float32",
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
        self.assertEqual(payload["evidence"]["mode"], "collect")
        self.assertEqual(
            payload["evidence"]["status"], "requires_content_retrieval"
        )
        self.assertIsNone(payload["evidence"]["threshold"])
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
                    "evidence": {"mode": "collect", "status": "unassessed"},
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
        self.assertEqual(json.loads(stdout)["evidence"]["status"], "unassessed")
        self.assertIsInstance(
            captured["evidence_assessor"], CalibratedEvidenceAssessor
        )
        route_context = captured["evidence_route_context"]
        self.assertIsInstance(route_context, EvidenceRouteContext)
        self.assertEqual(route_context.selection_reason, "unique_title_or_alias")

    def test_plain_collect_mode_does_not_pay_for_discarded_evidence_scores(self) -> None:
        cards = [
            make_card("dagster", title="Dagster", vector=cosine_vector(0.5)),
            make_card("tpuf", title="Turbopuffer", vector=cosine_vector(0.9)),
            make_card("thistle", title="Thistle", vector=cosine_vector(0.2)),
        ]
        catalog_snapshot = snapshot(cards)
        captured: dict[str, object] = {}

        class FakeRetriever:
            def retrieve(self, _query, _options, **kwargs):  # noqa: ANN001
                captured.update(kwargs)
                return object()

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
            side_effect=AssertionError("collect assessor loaded for plain output"),
        ), patch("buoy_search.cli.print_retrieval_text"):
            result, stdout, stderr = run_cli(
                ["retrieve", "Dagster assets"],
                env={"TURBOPUFFER_API_KEY": self.API_KEY},
            )

        self.assertEqual((result, stdout, stderr), (0, "", ""))
        self.assertEqual(captured, {"initial_fanout": 1})

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


if __name__ == "__main__":
    unittest.main()
