from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import math
import os
from pathlib import Path
from types import SimpleNamespace
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
from buoy_search.cli import build_parser, main
from buoy_search.config import RuntimeConfig
from buoy_search.remote_catalog import REMOTE_CATALOG_NAMESPACE
from buoy_search.retriever import RRF_K
from buoy_search.routing import (
    AutomaticRoutingError,
    eligible_catalog_cards,
    hybrid_route,
    lexical_route,
    semantic_route,
)
from tests.test_remote_catalog import FakeClient, NamespacePage, QueryResource


def unit_vector(index: int = 0) -> list[float]:
    vector = [0.0] * ROUTING_DIMENSIONS
    vector[index] = 1.0
    return vector


class CredentialReadSentinel(dict[str, str]):
    def get(self, key: str, default=None):  # noqa: ANN001 - dict-compatible sentinel.
        if key == "TURBOPUFFER_API_KEY":
            raise AssertionError("TURBOPUFFER_API_KEY was read")
        return super().get(key, default)

    def __getitem__(self, key: str) -> str:
        if key == "TURBOPUFFER_API_KEY":
            raise AssertionError("TURBOPUFFER_API_KEY was read")
        return super().__getitem__(key)

    def __contains__(self, key: object) -> bool:
        if key == "TURBOPUFFER_API_KEY":
            raise AssertionError("TURBOPUFFER_API_KEY was read")
        return super().__contains__(key)


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
    tags: list[str] | None = None,
    vector: list[float] | None = None,
    enabled: bool = True,
    region: str = "gcp-us-central1",
    embedding_model: str = ROUTING_MODEL,
    embedding_precision: str = "float32",
    ranking_mode: str = "page",
    ranking_profile: str = "none",
    ranking_pool: int = 20,
    ranking_aggregation: str = "max",
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
            tags=list(tags or []),
            semantic_origin="manual",
            region=region,
            embedding_model=embedding_model,
            embedding_precision=embedding_precision,
            plan_schema_version=1,
            ranking_mode=ranking_mode,
            ranking_profile=ranking_profile,
            ranking_pool=ranking_pool,
            ranking_aggregation=ranking_aggregation,
        ),
        embedder=FixedEmbedder(vector),
        now="2026-07-18T12:00:00+00:00",
    )


def run_cli(
    args: list[str],
    *,
    env: dict[str, str] | None = None,
    environment: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    stdout = StringIO()
    stderr = StringIO()
    environ = environment if environment is not None else (env or {})
    with patch.object(os, "environ", environ), redirect_stdout(stdout), redirect_stderr(stderr):
        result = main(args)
    return result, stdout.getvalue(), stderr.getvalue()


class RoutingAlgorithmTests(unittest.TestCase):
    def test_eligibility_gates_disabled_and_runtime_incompatible_cards_before_scoring(self) -> None:
        eligible = make_card("eligible", title="ordinary", vector=unit_vector(1))
        canaries = [
            make_card("disabled", title="strong canary", vector=unit_vector(), enabled=False),
            make_card("wrong-region", title="strong canary", vector=unit_vector(), region="aws-us-east-1"),
            make_card("wrong-model", title="strong canary", vector=unit_vector(), embedding_model="other/model"),
            make_card("wrong-precision", title="strong canary", vector=unit_vector(), embedding_precision="float16"),
        ]
        document = type("Document", (), {"cards": [eligible, *canaries]})()
        result = eligible_catalog_cards(document, config=RuntimeConfig())

        self.assertEqual([card.namespace for card in result.cards], ["eligible"])
        self.assertEqual(
            result.exclusion_counts,
            {"disabled": 1, "region": 1, "embedding_model": 1, "embedding_precision": 1},
        )
        selection = hybrid_route(
            "strong canary",
            result.cards,
            embedder=FixedEmbedder(unit_vector(1)),
            route_top_k=3,
            catalog_path=Path("catalog.json"),
            catalog_revision="revision",
            exclusion_counts=result.exclusion_counts,
        )
        self.assertEqual([entry.namespace for entry in selection.entries], ["eligible"])

    def test_lexical_normalization_phrase_frequency_descriptor_dedup_and_ties(self) -> None:
        first = make_card(
            "a-namespace",
            title="Data_Vault",
            aliases=["Alpha Beta", "Vault"],
            tags=["Python"],
        )
        second = make_card("b-namespace", title="alpha beta", tags=["data vault"])
        unmatched = make_card("c-namespace", title="Bet")

        ranking = lexical_route(
            "ＤＡＴＡ vault data vault; alpha-beta alpha beta; pythonic PYTHON",
            [second, unmatched, first],
        )

        self.assertEqual(
            [(card.namespace, count, tokens) for card, count, tokens in ranking],
            [("a-namespace", 4, 6), ("b-namespace", 2, 4)],
        )
        self.assertNotIn("c-namespace", [card.namespace for card, _count, _tokens in ranking])

    def test_semantic_uses_prefixed_query_persisted_vectors_cosine_and_namespace_ties(self) -> None:
        embedder = FixedEmbedder(unit_vector(0))
        cards = [
            make_card("z-zero", vector=unit_vector(1)),
            make_card("b-tie", vector=unit_vector(0)),
            make_card("a-tie", vector=unit_vector(0)),
        ]
        ranking = semantic_route("  routing question  ", cards, embedder=embedder)

        self.assertEqual(embedder.calls, [[f"{ROUTING_QUERY_PREFIX}routing question"]])
        self.assertEqual([card.namespace for card, _score in ranking], ["a-tie", "b-tie", "z-zero"])
        self.assertEqual([score for _card, score in ranking], [1.0, 1.0, 0.0])

    def test_semantic_rejects_invalid_or_nonfinite_query_vectors(self) -> None:
        card = make_card("card")
        for vector, message in (
            ([1.0], "exactly 384"),
            ([0.0] * ROUTING_DIMENSIONS, "normalized"),
            ([math.nan] + [0.0] * (ROUTING_DIMENSIONS - 1), "finite"),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(AutomaticRoutingError, message):
                semantic_route("query", [card], embedder=FixedEmbedder(vector))

    def test_hybrid_equal_rrf_one_list_membership_ties_and_pre_retrieval_truncation(self) -> None:
        self.assertEqual(RRF_K, 60)
        cards = [
            make_card("a-semantic", title="unmatched a", vector=unit_vector()),
            make_card("b-lexical", title="chosen phrase", vector=unit_vector(1)),
            make_card("c-semantic", title="unmatched c", vector=unit_vector()),
        ]
        selection = hybrid_route(
            "chosen phrase",
            cards,
            embedder=FixedEmbedder(unit_vector()),
            route_top_k=2,
            catalog_path=Path("catalog.json"),
            catalog_revision="revision",
            exclusion_counts={},
        )

        self.assertEqual([entry.namespace for entry in selection.entries], ["b-lexical", "a-semantic"])
        self.assertEqual(selection.entries[0].lexical_rank, 1)
        self.assertAlmostEqual(
            selection.entries[0].hybrid_score,
            1 / (RRF_K + 1) + 1 / (RRF_K + 3),
        )
        self.assertIsNone(selection.entries[1].lexical_rank)
        self.assertAlmostEqual(selection.entries[1].hybrid_score, 1 / (RRF_K + 1))
        self.assertEqual(len(selection.selected_cards), 2)
        payload = selection.to_dict()
        self.assertNotIn("vector", json.dumps(payload))
        self.assertEqual(payload["strategy"], "hybrid_rrf")


class AutomaticRoutingCliTests(unittest.TestCase):
    API_KEY = "tpuf_test-routing-secret"

    def automatic_fixture(self) -> tuple[FakeClient, QueryResource, FixedEmbedder]:
        cards = [
            make_card("a-semantic", title="alpha", vector=unit_vector()),
            make_card("b-lexical", title="chosen phrase", vector=unit_vector(1)),
            make_card("c-semantic", title="charlie", vector=unit_vector()),
            make_card("d-semantic", title="delta", vector=unit_vector()),
            make_card("disabled", enabled=False),
            make_card("incompatible", embedding_precision="float16"),
            make_card("stale"),
        ]
        live = [
            REMOTE_CATALOG_NAMESPACE,
            "a-semantic",
            "b-lexical",
            "c-semantic",
            "d-semantic",
            "disabled",
            "incompatible",
            "missing",
        ]
        resource = QueryResource(cards)
        client = FakeClient([NamespacePage(live), NamespacePage(live)], resource)
        return client, resource, FixedEmbedder(unit_vector())

    def run_automatic(
        self,
        args: list[str],
        *,
        client: object,
        embedder: FixedEmbedder | None = None,
    ) -> tuple[int, str, str]:
        with patch(
            "buoy_search.remote_catalog.create_client",
            side_effect=AssertionError("real SDK/network client used"),
        ), patch(
            "buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY", return_value=client
        ), patch(
            "buoy_search.cli.load_routing_embedder", return_value=embedder or FixedEmbedder()
        ):
            return run_cli(args, env={"TURBOPUFFER_API_KEY": self.API_KEY})

    def test_all_automatic_modes_require_key_before_client_and_ignore_environment_namespace(self) -> None:
        for extra in ([], ["--auto-route"], ["--live"], ["--dry-run"], ["--plan"]):
            with self.subTest(extra=extra), patch(
                "buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY",
                side_effect=AssertionError("client constructed without key"),
            ), patch(
                "buoy_search.remote_catalog.create_client",
                side_effect=AssertionError("real SDK/network client used"),
            ):
                result, stdout, stderr = run_cli(
                    ["retrieve", "query", *extra, "--json"],
                    env={"TURBOPUFFER_NAMESPACE": "must-be-ignored"},
                )
            self.assertEqual((result, stdout), (2, ""))
            self.assertIn("TURBOPUFFER_API_KEY", stderr)
            self.assertNotIn("must-be-ignored", stderr)

    def test_explicit_preview_aliases_bypass_key_client_remote_and_route_model(self) -> None:
        payloads = []
        for preview_flag in ("--dry-run", "--plan"):
            environment = CredentialReadSentinel({"TURBOPUFFER_NAMESPACE": "ignored"})
            with self.subTest(preview_flag=preview_flag), patch(
                "buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY",
                side_effect=AssertionError("remote client constructed"),
            ), patch(
                "buoy_search.cli.read_remote_catalog", side_effect=AssertionError("remote catalog read")
            ), patch(
                "buoy_search.cli.load_routing_embedder", side_effect=AssertionError("route model loaded")
            ), patch(
                "buoy_search.remote_catalog.create_client",
                side_effect=AssertionError("real SDK/network client used"),
            ):
                result, stdout, stderr = run_cli(
                    [
                        "retrieve", "query", "--namespace", "explicit-one",
                        "--namespace", "explicit-two", preview_flag, "--json",
                    ],
                    environment=environment,
                )
            self.assertEqual((result, stderr), (0, ""))
            payloads.append(json.loads(stdout))
        self.assertEqual(payloads[0], payloads[1])
        payload = payloads[0]
        self.assertEqual(payload["namespaces"], ["explicit-one", "explicit-two"])
        self.assertFalse(payload["credentials_required"])
        self.assertFalse(payload["turbopuffer_api_calls"])
        self.assertFalse(payload["api_calls_occurred"])
        self.assertNotIn("routing", payload)

    def test_preview_aliases_and_auto_route_are_identical_and_parser_limit_is_bounded(self) -> None:
        payloads = []
        for extra in (["--dry-run"], ["--plan"], ["--auto-route", "--dry-run"]):
            client, _resource, embedder = self.automatic_fixture()
            result, stdout, stderr = self.run_automatic(
                ["retrieve", "chosen phrase", *extra, "--json"],
                client=client,
                embedder=embedder,
            )
            self.assertEqual((result, stderr), (0, ""))
            payloads.append(json.loads(stdout))
        self.assertEqual(payloads, [payloads[0]] * len(payloads))

        parser = build_parser()
        for value in ("0", "11"):
            with self.subTest(value=value), redirect_stderr(StringIO()), self.assertRaises(SystemExit):
                parser.parse_args(["retrieve", "query", "--route-top-k", value])
        self.assertEqual(
            parser.parse_args(["retrieve", "query", "--route-top-k", "10"]).route_top_k,
            10,
        )

    def test_preview_performs_two_stable_list_and_strong_card_passes_then_routes_top_three(self) -> None:
        client, resource, embedder = self.automatic_fixture()
        before_cards = list(resource.cards)
        with patch(
            "buoy_search.cli.MultiNamespaceRetriever.from_configs",
            side_effect=AssertionError("content retriever constructed during preview"),
        ):
            result, stdout, stderr = self.run_automatic(
                ["retrieve", "chosen phrase", "--dry-run", "--json"], client=client, embedder=embedder
            )
        self.assertEqual((result, stderr), (0, ""))
        payload = json.loads(stdout)
        routing = payload["routing"]
        self.assertEqual(client.namespaces_calls, [{"page_size": 1000}] * 2)
        self.assertEqual(client.namespace_calls, [REMOTE_CATALOG_NAMESPACE])
        self.assertEqual(resource.metadata_calls, 1)
        self.assertEqual(len(resource.query_calls), 2)
        for call in resource.query_calls:
            self.assertEqual(call["consistency"], {"level": "strong"})
            self.assertEqual(call["rank_by"], ("id", "asc"))
            self.assertNotIn("filters", call)
        self.assertEqual(resource.cards, before_cards)
        self.assertEqual(embedder.calls, [[f"{ROUTING_QUERY_PREFIX}chosen phrase"]])
        self.assertEqual(payload["namespaces"], ["b-lexical", "a-semantic", "c-semantic"])
        self.assertEqual(
            [entry["namespace"] for entry in routing["selected_cards"]],
            payload["namespaces"],
        )
        self.assertEqual(routing["requested_limit"], 3)
        self.assertEqual(routing["catalog_namespace"], REMOTE_CATALOG_NAMESPACE)
        self.assertTrue(payload["credentials_required"])
        self.assertTrue(payload["turbopuffer_api_calls"])
        self.assertTrue(payload["api_calls_occurred"])
        self.assertTrue(routing["credentials_required"])
        self.assertTrue(routing["read_only_api_calls_occurred"])
        self.assertFalse(payload["content_retrieval_occurred"])
        self.assertFalse(routing["content_retrieval_occurred"])
        self.assertEqual(
            routing["remote_counts"],
            {
                "listed_total": 8,
                "control_plane_count": 1,
                "content_live_count": 7,
                "card_count": 7,
                "stale_target_count": 1,
                "missing_card_count": 1,
                "disabled_count": 1,
                "incompatible_count": 1,
                "eligible_count": 4,
            },
        )
        self.assertEqual(
            routing["exclusion_counts"],
            {"disabled": 1, "incompatible": 1, "missing_card": 1, "stale_target": 1},
        )
        self.assertEqual(
            routing["read_metrics"],
            {
                "namespace_list_pages": 2,
                "metadata_requests": 1,
                "card_query_pages": 2,
                "billing": [
                    {"billable_logical_bytes_queried": 123},
                    {"billable_logical_bytes_queried": 123},
                ],
            },
        )
        self.assertEqual(routing["selected_cards"][0]["lexical_rank"], 1)
        self.assertEqual(routing["selected_cards"][1]["semantic_rank"], 1)
        self.assertNotIn('"vector": [', stdout)
        self.assertNotIn("vector_hash", stdout)
        self.assertNotIn("tpuf_", stdout)

    def test_preview_text_reports_authenticated_reads_and_no_content_retrieval(self) -> None:
        client, _resource, embedder = self.automatic_fixture()
        result, stdout, stderr = self.run_automatic(
            ["retrieve", "chosen phrase", "--dry-run"], client=client, embedder=embedder
        )

        self.assertEqual((result, stderr), (0, ""))
        self.assertIn("credentials required", stdout)
        self.assertIn("read-only namespace-list/catalog-query API calls occurred", stdout)
        self.assertIn("no content retrieval", stdout)
        self.assertNotIn("no credentials or turbopuffer API calls", stdout)

    def test_plain_and_compatibility_live_route_identically_and_fail_all_or_nothing(self) -> None:
        live_payload = {
            "command": "retrieve",
            "dry_run": False,
            "credentials_required": True,
            "turbopuffer_api_calls": True,
            "api_calls_occurred": True,
            "content_retrieval_occurred": True,
            "query": "chosen phrase",
            "region": "gcp-us-central1",
            "namespaces": ["b-lexical", "a-semantic", "c-semantic"],
            "embedding_model": ROUTING_MODEL,
            "embedding_precision": "float32",
            "top_k": 5,
            "candidates": 200,
            "fusion": "cross_namespace_rrf",
            "namespace_results": [],
            "hits": [],
        }
        outputs = []
        for extra in ([], ["--live"]):
            calls = []
            retriever = SimpleNamespace(
                retrieve=lambda query, options: (
                    calls.append((query, options)),
                    SimpleNamespace(to_dict=lambda: live_payload),
                )[1]
            )
            client, resource, embedder = self.automatic_fixture()
            with self.subTest(extra=extra), patch(
                "buoy_search.cli.MultiNamespaceRetriever.from_configs", return_value=retriever
            ) as from_configs:
                result, stdout, stderr = self.run_automatic(
                    ["retrieve", "chosen phrase", *extra, "--json"],
                    client=client,
                    embedder=embedder,
                )
            self.assertEqual((result, stderr), (0, ""))
            self.assertEqual(client.namespaces_calls, [{"page_size": 1000}] * 2)
            self.assertEqual(client.namespace_calls, [REMOTE_CATALOG_NAMESPACE])
            self.assertEqual(resource.metadata_calls, 1)
            self.assertEqual(len(resource.query_calls), 2)
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][0], "chosen phrase")
            configs = from_configs.call_args.args[0]
            self.assertEqual(
                [config.namespace for config in configs],
                ["b-lexical", "a-semantic", "c-semantic"],
            )
            outputs.append(stdout)
        self.assertEqual(outputs[0], outputs[1])
        payload = json.loads(outputs[0])
        self.assertTrue(payload["content_retrieval_occurred"])
        self.assertTrue(payload["routing"]["content_retrieval_occurred"])

        failing = SimpleNamespace(
            retrieve=lambda _query, _options: (_ for _ in ()).throw(RuntimeError("boom"))
        )
        client, _resource, embedder = self.automatic_fixture()
        with patch("buoy_search.cli.MultiNamespaceRetriever.from_configs", return_value=failing):
            result, stdout, stderr = self.run_automatic(
                ["retrieve", "chosen phrase", "--json"],
                client=client,
                embedder=embedder,
            )
        self.assertEqual((result, stdout), (2, ""))
        self.assertIn("Namespace retrieval failed", stderr)
        self.assertNotIn("content_retrieval_occurred", stderr)

    def test_live_preview_conflicts_and_whitespace_fail_before_config_credentials_or_api(self) -> None:
        for preview_flag in ("--dry-run", "--plan"):
            with self.subTest(preview_flag=preview_flag), patch(
                "buoy_search.cli.config_from_args", side_effect=AssertionError("config loaded")
            ):
                result, stdout, stderr = run_cli(
                    [
                        "retrieve", "   ", "--live", preview_flag,
                        "--auto-route", "--namespace", "explicit", "--json",
                    ],
                    environment=CredentialReadSentinel(),
                )
            self.assertEqual((result, stdout), (2, ""))
            self.assertIn("Choose either --live or --dry-run/--plan", stderr)

        with patch(
            "buoy_search.cli.config_from_args", side_effect=AssertionError("config loaded")
        ), patch(
            "buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY",
            side_effect=AssertionError("remote client constructed"),
        ):
            result, stdout, stderr = run_cli(
                ["retrieve", "   ", "--json"], environment=CredentialReadSentinel()
            )
        self.assertEqual((result, stdout), (2, ""))
        self.assertIn("non-empty query", stderr)

    def test_explicit_automatic_options_conflict_before_namespace_or_query_validation(self) -> None:
        cases = (
            (["--auto-route"], "--auto-route and --namespace are mutually exclusive"),
            (["--route-top-k", "2"], "--route-top-k is valid only for automatic retrieval"),
        )
        for extra, expected in cases:
            with self.subTest(extra=extra), patch(
                "buoy_search.cli.config_from_args", side_effect=AssertionError("config loaded")
            ):
                result, stdout, stderr = run_cli(
                    ["retrieve", "   ", "--namespace", "   ", *extra, "--json"],
                    environment=CredentialReadSentinel(),
                )
            self.assertEqual((result, stdout), (2, ""))
            self.assertIn(expected, stderr)

    def test_zero_eligible_snapshot_fails_actionably_before_model_or_content(self) -> None:
        live = [REMOTE_CATALOG_NAMESPACE, "missing"]
        client = FakeClient([NamespacePage(live), NamespacePage(live)], QueryResource([]))
        with patch(
            "buoy_search.cli.load_routing_embedder",
            side_effect=AssertionError("route model loaded with zero eligible cards"),
        ), patch(
            "buoy_search.cli.MultiNamespaceRetriever.from_configs",
            side_effect=AssertionError("content retriever constructed"),
        ), patch(
            "buoy_search.remote_catalog.create_client",
            side_effect=AssertionError("real SDK/network client used"),
        ), patch("buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY", return_value=client):
            result, stdout, stderr = run_cli(
                ["retrieve", "query", "--json"],
                env={"TURBOPUFFER_API_KEY": self.API_KEY},
            )
        self.assertEqual((result, stdout), (2, ""))
        self.assertIn("no eligible live remote namespace cards", stderr)
        self.assertIn("buoy catalog list --all", stderr)

    def test_unstable_lists_unstable_cards_and_provider_failures_are_redacted(self) -> None:
        card = make_card("stable")
        cases: list[tuple[object, str]] = [
            (
                FakeClient(
                    [
                        NamespacePage([REMOTE_CATALOG_NAMESPACE, card.namespace]),
                        NamespacePage([REMOTE_CATALOG_NAMESPACE, card.namespace, "new"]),
                    ],
                    QueryResource([card]),
                ),
                "namespace listing changed",
            ),
            (
                FakeClient(
                    [
                        NamespacePage([REMOTE_CATALOG_NAMESPACE, card.namespace]),
                        NamespacePage([REMOTE_CATALOG_NAMESPACE, card.namespace]),
                    ],
                    QueryResource([card], second_pass_cards=[make_card("stable", title="changed")]),
                ),
                "catalog changed between",
            ),
        ]

        class ProviderFailureClient:
            def namespaces(self, **_kwargs: object) -> object:
                raise RuntimeError(f"429 Authorization=Bearer {self_secret}")

        class ProviderCardFailureResource(QueryResource):
            def query(self, **_kwargs: object) -> object:
                raise RuntimeError(f"timeout api_key={self_secret}")

        self_secret = self.API_KEY
        cases.extend(
            [
                (ProviderFailureClient(), "namespace listing failed"),
                (
                    FakeClient(
                        [NamespacePage([REMOTE_CATALOG_NAMESPACE, card.namespace])],
                        ProviderCardFailureResource([card]),
                    ),
                    "card page query failed",
                ),
            ]
        )
        for client, expected in cases:
            with self.subTest(expected=expected), patch(
                "buoy_search.cli.load_routing_embedder",
                side_effect=AssertionError("model loaded after unstable remote read"),
            ):
                result, stdout, stderr = self.run_automatic(
                    ["retrieve", "query", "--json"], client=client
                )
            self.assertEqual((result, stdout), (2, ""))
            self.assertIn(expected, stderr)
            self.assertNotIn(self.API_KEY, stderr)
            self.assertNotIn("Authorization", stderr)


if __name__ == "__main__":
    unittest.main()
