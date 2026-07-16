from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import math
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from buoy_search.catalog import (
    ROUTING_DIMENSIONS,
    ROUTING_MODEL,
    ROUTING_QUERY_PREFIX,
    CardFields,
    NamespaceCard,
    prepare_card,
    save_catalog,
)
from buoy_search.cli import build_parser, main
from buoy_search.config import RuntimeConfig
from buoy_search.retriever import RRF_K
from buoy_search.routing import (
    AutomaticRoutingError,
    eligible_catalog_cards,
    hybrid_route,
    lexical_route,
    semantic_route,
)


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
        now="2026-07-15T12:00:00+00:00",
    )


def write_catalog(path: Path, cards: list[NamespaceCard]) -> None:
    save_catalog(path, cards, now="2026-07-15T13:00:00+00:00")


def run_cli(args: list[str], *, env: dict[str, str] | None = None) -> tuple[int, str, str]:
    stdout = StringIO()
    stderr = StringIO()
    with patch.dict(os.environ, env or {}, clear=True), redirect_stdout(stdout), redirect_stderr(stderr):
        result = main(args)
    return result, stdout.getvalue(), stderr.getvalue()


def run_cli_with_environment(
    args: list[str], environment: dict[str, str]
) -> tuple[int, str, str]:
    stdout = StringIO()
    stderr = StringIO()
    with patch.object(os, "environ", environment), redirect_stdout(stdout), redirect_stderr(stderr):
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
    def test_activation_conflicts_and_route_only_flags_fail_before_config_catalog_or_model(self) -> None:
        sentinels = {
            "buoy_search.cli.config_from_args": patch(
                "buoy_search.cli.config_from_args", side_effect=AssertionError("config loaded")
            ),
            "buoy_search.cli.load_catalog": patch(
                "buoy_search.cli.load_catalog", side_effect=AssertionError("catalog loaded")
            ),
            "buoy_search.cli.load_routing_embedder": patch(
                "buoy_search.cli.load_routing_embedder", side_effect=AssertionError("model loaded")
            ),
        }
        for args, expected in (
            (["retrieve", "query", "--auto-route", "--namespace", "explicit"], "mutually exclusive"),
            (["retrieve", "query", "--route-top-k", "2", "--namespace", "explicit"], "valid only"),
            (["retrieve", "query", "--catalog", "catalog.json", "--namespace", "explicit"], "valid only"),
        ):
            with self.subTest(args=args):
                with sentinels["buoy_search.cli.config_from_args"], sentinels["buoy_search.cli.load_catalog"], sentinels["buoy_search.cli.load_routing_embedder"]:
                    result, stdout, stderr = run_cli(args)
                self.assertEqual(result, 2)
                self.assertEqual(stdout, "")
                self.assertIn(expected, stderr)
                sentinels = {
                    "buoy_search.cli.config_from_args": patch("buoy_search.cli.config_from_args", side_effect=AssertionError("config loaded")),
                    "buoy_search.cli.load_catalog": patch("buoy_search.cli.load_catalog", side_effect=AssertionError("catalog loaded")),
                    "buoy_search.cli.load_routing_embedder": patch("buoy_search.cli.load_routing_embedder", side_effect=AssertionError("model loaded")),
                }

    def test_explicit_namespace_error_precedes_empty_query_while_auto_route_validates_query(self) -> None:
        with patch("buoy_search.cli.config_from_args", side_effect=AssertionError("config loaded")):
            result, stdout, stderr = run_cli(["retrieve", "   ", "--json"])
        self.assertEqual(result, 2)
        self.assertEqual(stdout, "")
        self.assertIn("--namespace or TURBOPUFFER_NAMESPACE", stderr)
        self.assertNotIn("non-empty query", stderr)

        with patch("buoy_search.cli.load_catalog", side_effect=AssertionError("catalog loaded")):
            result, stdout, stderr = run_cli(["retrieve", "   ", "--auto-route", "--json"])
        self.assertEqual(result, 2)
        self.assertEqual(stdout, "")
        self.assertIn("non-empty query", stderr)

    def test_route_top_k_parser_bounds_are_one_through_ten(self) -> None:
        parser = build_parser()
        for value in ("0", "11"):
            with self.subTest(value=value), redirect_stderr(StringIO()), self.assertRaises(SystemExit):
                parser.parse_args(["retrieve", "query", "--auto-route", "--route-top-k", value])
        args = parser.parse_args(["retrieve", "query", "--auto-route", "--route-top-k", "10"])
        self.assertEqual(args.route_top_k, 10)

    def test_catalog_cli_path_overrides_environment_and_empty_values_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cli_path = root / "cli.json"
            env_path = root / "env.json"
            write_catalog(cli_path, [make_card("cli-card", title="route me")])
            write_catalog(env_path, [make_card("env-card", title="route me")])
            with patch("buoy_search.cli.load_routing_embedder", return_value=FixedEmbedder()):
                result, stdout, stderr = run_cli(
                    ["retrieve", "route me", "--auto-route", "--catalog", str(cli_path), "--json"],
                    env={"BUOY_CATALOG_PATH": str(env_path)},
                )
            self.assertEqual((result, stderr), (0, ""))
            payload = json.loads(stdout)
            self.assertEqual(payload["routing"]["catalog_path"], str(cli_path))
            self.assertEqual(payload["namespaces"], ["cli-card"])

            result, stdout, stderr = run_cli(
                ["retrieve", "query", "--auto-route", "--catalog", "", "--json"]
            )
            self.assertEqual(result, 2)
            self.assertEqual(stdout, "")
            self.assertIn("non-whitespace", stderr)
            result, stdout, stderr = run_cli(
                ["retrieve", "query", "--auto-route", "--json"],
                env={"BUOY_CATALOG_PATH": "   "},
            )
            self.assertEqual(result, 2)
            self.assertEqual(stdout, "")
            self.assertIn("BUOY_CATALOG_PATH", stderr)

    def test_environment_namespace_is_replaced_with_stderr_warning_and_clean_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            write_catalog(path, [make_card("routed", title="route me")])
            with patch("buoy_search.cli.load_routing_embedder", return_value=FixedEmbedder()):
                result, stdout, stderr = run_cli(
                    ["retrieve", "route me", "--auto-route", "--catalog", str(path), "--json"],
                    env={"TURBOPUFFER_NAMESPACE": "ignored-explicit"},
                )
            self.assertEqual(result, 0)
            self.assertEqual(json.loads(stdout)["namespaces"], ["routed"])
            self.assertIn("replaces TURBOPUFFER_NAMESPACE", stderr)
            self.assertNotIn("Warning", stdout)

    def test_explicit_retrieval_never_loads_catalog_or_route_model(self) -> None:
        with patch("buoy_search.cli.load_catalog", side_effect=AssertionError("catalog loaded")), patch(
            "buoy_search.cli.load_routing_embedder", side_effect=AssertionError("model loaded")
        ):
            result, stdout, stderr = run_cli(
                ["retrieve", "query", "--namespace", "explicit", "--json"],
                env={"BUOY_CATALOG_PATH": "corrupt.json"},
            )
        self.assertEqual((result, stderr), (0, ""))
        payload = json.loads(stdout)
        self.assertEqual(payload["namespace"], "explicit")
        self.assertNotIn("routing", payload)

    def test_dry_preview_defaults_top_three_is_local_nonmutating_and_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            cards = [
                make_card(f"card-{index}", title=f"topic {index}", vector=unit_vector(index))
                for index in range(4)
            ]
            write_catalog(path, cards)
            before = path.read_bytes()
            route_embedder = FixedEmbedder(unit_vector())
            environment = CredentialReadSentinel({"TURBOPUFFER_API_KEY": "must-not-be-read"})
            stdout = StringIO()
            stderr = StringIO()
            with patch.object(os, "environ", environment), patch(
                "buoy_search.cli.load_routing_embedder", return_value=route_embedder
            ), patch(
                "buoy_search.cli.MultiNamespaceRetriever.from_configs",
                side_effect=AssertionError("live retriever constructed"),
            ), patch(
                "buoy_search.cli.list_namespace_ids", side_effect=AssertionError("remote discovery")
            ), redirect_stdout(stdout), redirect_stderr(stderr):
                result = main(
                    ["retrieve", "topic", "--auto-route", "--catalog", str(path), "--json"]
                )
            stdout = stdout.getvalue()
            stderr = stderr.getvalue()
            self.assertEqual((result, stderr), (0, ""))
            payload = json.loads(stdout)
            self.assertTrue(payload["dry_run"])
            self.assertFalse(payload["credentials_required"])
            self.assertFalse(payload["turbopuffer_api_calls"])
            self.assertEqual(len(payload["namespaces"]), 3)
            self.assertEqual(payload["routing"]["requested_limit"], 3)
            self.assertEqual(payload["routing"]["eligible_count"], 4)
            self.assertEqual(route_embedder.calls, [[f"{ROUTING_QUERY_PREFIX}topic"]])
            self.assertEqual(path.read_bytes(), before)
            self.assertNotIn('"vector": [', stdout)
            self.assertNotIn("vector_hash", stdout)
            self.assertEqual(
                [plan["namespace"] for plan in payload["namespace_plans"]],
                payload["namespaces"],
            )

    def test_dry_preview_uses_mixed_card_ranking_then_independent_global_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            cards = [
                make_card(
                    "a-card",
                    title="route",
                    ranking_mode="page",
                    ranking_profile="none",
                    ranking_pool=17,
                    ranking_aggregation="max",
                ),
                make_card(
                    "b-card",
                    title="route",
                    ranking_mode="file",
                    ranking_profile="repo_code",
                    ranking_pool=29,
                    ranking_aggregation="capped_sum_3",
                ),
            ]
            write_catalog(path, cards)
            with patch("buoy_search.cli.load_routing_embedder", return_value=FixedEmbedder()):
                result, stdout, stderr = run_cli(
                    ["retrieve", "route", "--auto-route", "--catalog", str(path), "--json"]
                )
            self.assertEqual((result, stderr), (0, ""))
            plans = json.loads(stdout)["namespace_plans"]
            self.assertEqual(
                [(plan["ranking_mode"], plan["ranking_profile"], plan["ranking_pool"], plan["ranking_aggregation"]) for plan in plans],
                [("page", "none", 17, "max"), ("file", "repo_code", 29, "capped_sum_3")],
            )

            with patch("buoy_search.cli.load_routing_embedder", return_value=FixedEmbedder()):
                result, stdout, stderr = run_cli(
                    [
                        "retrieve", "route", "--auto-route", "--catalog", str(path),
                        "--ranking-mode", "chunk", "--ranking-pool", "7", "--json",
                    ]
                )
            self.assertEqual((result, stderr), (0, ""))
            overridden = json.loads(stdout)["namespace_plans"]
            self.assertEqual(
                [(plan["ranking_mode"], plan["ranking_profile"], plan["ranking_pool"], plan["ranking_aggregation"]) for plan in overridden],
                [("chunk", "none", 7, "max"), ("chunk", "repo_code", 7, "capped_sum_3")],
            )

    def test_single_selected_card_keeps_explicit_routed_multi_namespace_shape_and_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            write_catalog(path, [make_card("only-card", title="only route")])
            with patch("buoy_search.cli.load_routing_embedder", return_value=FixedEmbedder()):
                result, stdout, stderr = run_cli(
                    ["retrieve", "only route", "--auto-route", "--catalog", str(path)]
                )
            self.assertEqual((result, stderr), (0, ""))
            self.assertIn("Automatic namespace route", stdout)
            self.assertIn("route 1: only-card", stdout)
            self.assertIn("namespaces: only-card", stdout)

    def test_live_route_uses_existing_multi_retriever_order_embed_once_global_controls_and_rrf(self) -> None:
        class RetrievalEmbedder:
            init_calls: list[tuple[str, str]] = []
            encode_calls: list[list[str]] = []

            def __init__(self, model: str, *, precision: str) -> None:
                self.init_calls.append((model, precision))

            def encode(self, texts):  # noqa: ANN001
                self.encode_calls.append(list(texts))
                return [unit_vector()]

        class Namespace:
            def __init__(self, name: str, order: list[str], calls: list[tuple[str, dict[str, object]]]) -> None:
                self.name = name
                self.order = order
                self.calls = calls

            def multi_query(self, **kwargs: object) -> dict[str, object]:
                self.order.append(self.name)
                self.calls.append((self.name, kwargs))
                return {
                    "rows": [
                        {
                            "id": "shared-row",
                            "attributes": {
                                "title": self.name,
                                "url": f"https://{self.name}.example/result",
                                "content": "result",
                            },
                        }
                    ]
                }

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            write_catalog(
                path,
                [
                    make_card("a-card", title="route", ranking_pool=11),
                    make_card(
                        "b-card", title="route", ranking_mode="file", ranking_profile="repo_code",
                        ranking_pool=23, ranking_aggregation="adaptive_sum_3",
                    ),
                ],
            )
            order: list[str] = []
            calls: list[tuple[str, dict[str, object]]] = []

            def build_namespace(*, config, api_key):  # noqa: ANN001
                self.assertEqual(api_key, "test-key")
                return Namespace(config.namespace, order, calls)

            route_embedder = FixedEmbedder()
            with patch("buoy_search.cli.load_routing_embedder", return_value=route_embedder), patch(
                "buoy_search.retriever.SentenceTransformerEmbedder", RetrievalEmbedder
            ), patch("buoy_search.retriever.build_namespace", side_effect=build_namespace):
                result, stdout, stderr = run_cli(
                    [
                        "retrieve", "route", "--auto-route", "--catalog", str(path), "--live",
                        "--top-k", "1", "--candidates", "9", "--doc-kind", "docs", "--json",
                    ],
                    env={"TURBOPUFFER_API_KEY": "test-key"},
                )
            self.assertEqual((result, stderr), (0, ""))
            payload = json.loads(stdout)
            self.assertEqual(route_embedder.calls, [[f"{ROUTING_QUERY_PREFIX}route"]])
            self.assertEqual(RetrievalEmbedder.encode_calls, [["route"]])
            self.assertEqual(RetrievalEmbedder.init_calls, [(ROUTING_MODEL, "float32")])
            self.assertEqual(order, ["a-card", "b-card"])
            self.assertEqual(payload["namespaces"], ["a-card", "b-card"])
            self.assertEqual(payload["top_k"], 1)
            self.assertEqual(len(payload["hits"]), 1)
            self.assertEqual(payload["hits"][0]["namespace"], "a-card")
            self.assertEqual(payload["hits"][0]["score_info"]["cross_namespace_fusion"], "rrf")
            self.assertEqual(
                [(item["ranking_pool"], item["ranking_profile"]) for item in payload["namespace_results"]],
                [(11, "none"), (23, "repo_code")],
            )
            for _namespace, call in calls:
                queries = call["queries"]
                self.assertEqual(queries[0]["limit"], 9)
                self.assertEqual(queries[0]["filters"], ("doc_kind", "Eq", "docs"))
                self.assertEqual(len(queries[0]["rank_by"][2]), ROUTING_DIMENSIONS)
            self.assertNotIn('"vector": [', stdout)
            self.assertNotIn("vector_hash", stdout)

    def test_live_selected_namespace_failure_emits_no_partial_payload(self) -> None:
        class RetrievalEmbedder:
            def __init__(self, _model: str, *, precision: str) -> None:
                self.precision = precision

            def encode(self, _texts):  # noqa: ANN001
                return [unit_vector()]

        class Namespace:
            def __init__(self, name: str) -> None:
                self.name = name

            def multi_query(self, **_kwargs: object) -> dict[str, object]:
                if self.name == "b-card":
                    raise RuntimeError("unavailable")
                return {"rows": [{"id": "first", "attributes": {"title": "first"}}]}

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            write_catalog(path, [make_card("a-card", title="route"), make_card("b-card", title="route")])
            with patch("buoy_search.cli.load_routing_embedder", return_value=FixedEmbedder()), patch(
                "buoy_search.retriever.SentenceTransformerEmbedder", RetrievalEmbedder
            ), patch(
                "buoy_search.retriever.build_namespace",
                side_effect=lambda *, config, api_key: Namespace(config.namespace),
            ):
                result, stdout, stderr = run_cli(
                    ["retrieve", "route", "--auto-route", "--catalog", str(path), "--live", "--json"],
                    env={"TURBOPUFFER_API_KEY": "test-key"},
                )
            self.assertEqual(result, 2)
            self.assertEqual(stdout, "")
            self.assertIn("Retrieval failed for namespace 'b-card'", stderr)

    def test_missing_or_corrupt_catalog_and_missing_model_precede_credential_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing = root / "missing.json"
            corrupt = root / "corrupt.json"
            corrupt.write_text("{", encoding="utf-8")
            for path, expected in ((missing, "no enabled compatible"), (corrupt, "Catalog load failed")):
                environment = CredentialReadSentinel(
                    {"TURBOPUFFER_API_KEY": "must-not-be-read"}
                )
                with self.subTest(path=path), patch(
                    "buoy_search.cli.load_routing_embedder", side_effect=AssertionError("model loaded")
                ), patch(
                    "buoy_search.cli.MultiNamespaceRetriever.from_configs",
                    side_effect=AssertionError("live prepared"),
                ):
                    result, stdout, stderr = run_cli_with_environment(
                        ["retrieve", "query", "--auto-route", "--catalog", str(path), "--live", "--json"],
                        environment,
                    )
                self.assertEqual(result, 2)
                self.assertEqual(stdout, "")
                self.assertIn(expected, stderr)

            valid = root / "valid.json"
            write_catalog(valid, [make_card("card")])
            environment = CredentialReadSentinel(
                {"TURBOPUFFER_API_KEY": "must-not-be-read"}
            )
            with patch(
                "buoy_search.cli.load_routing_embedder",
                side_effect=RuntimeError("not cached; downloads disabled"),
            ), patch(
                "buoy_search.cli.MultiNamespaceRetriever.from_configs",
                side_effect=AssertionError("live prepared"),
            ):
                result, stdout, stderr = run_cli_with_environment(
                    ["retrieve", "query", "--auto-route", "--catalog", str(valid), "--live", "--json"],
                    environment,
                )
            self.assertEqual(result, 2)
            self.assertEqual(stdout, "")
            self.assertIn("Route model load failed", stderr)
            self.assertIn("downloads disabled", stderr)


if __name__ == "__main__":
    unittest.main()
