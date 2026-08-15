from __future__ import annotations

from contextlib import ExitStack, redirect_stderr, redirect_stdout
from io import StringIO
import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from buoy_search.catalog import CardFields, ROUTING_DIMENSIONS, prepare_card
from buoy_search.cli import main
from buoy_search.remote_catalog import (
    REMOTE_CATALOG_NAMESPACE,
    REMOTE_SCHEMA_V1,
    REMOTE_SCHEMA_V2,
    CompatibilityContract,
    MutationMetrics,
    MutationResult,
    ReadMetrics,
    RemoteCatalogError,
    classify_remote_catalog,
    remote_card_id,
)


REGION = "gcp-us-central1"
API_KEY = "test-api-key"
UNIT_VECTOR = [1.0] + [0.0] * (ROUTING_DIMENSIONS - 1)


class FixedEmbedder:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def encode(self, texts):  # noqa: ANN001
        self.calls.append(list(texts))
        return [list(UNIT_VECTOR) for _ in texts]


class FakeClient:
    def __init__(self) -> None:
        self.resource = object()
        self.namespace_calls: list[str] = []

    def namespace(self, namespace: str) -> object:
        self.namespace_calls.append(namespace)
        return self.resource


class ExplodingClient:
    def namespaces(self, **_kwargs: object) -> object:
        raise LeakyProviderError(f"provider leaked {API_KEY}")


class ResourceExplodingClient:
    def namespaces(self, **_kwargs: object) -> object:
        return [
            SimpleNamespace(id=REMOTE_CATALOG_NAMESPACE),
            SimpleNamespace(id="site-example-v1"),
        ]

    def namespace(self, _namespace: str) -> object:
        raise LeakyProviderError(f"resource acquisition leaked {API_KEY}")


class LeakyProviderError(Exception):
    pass


def make_card(
    namespace: str = "site-example-v1",
    *,
    enabled: bool = True,
    title: str = "Example",
    region: str = REGION,
    routing_examples: list[str] | None = None,
):
    return prepare_card(
        CardFields(
            namespace=namespace,
            enabled=enabled,
            source_kind="website",
            source_uri=f"https://example.com/{namespace}",
            site_id=f"site-{namespace}",
            title=title,
            summary="Example documentation.",
            aliases=["example docs"],
            tags=["docs"],
            semantic_origin="manual",
            region=region,
            embedding_model="BAAI/bge-small-en-v1.5",
            embedding_precision="float32",
            plan_schema_version=1,
            ranking_mode="page",
            ranking_profile="none",
            ranking_pool=20,
            ranking_aggregation="max",
            last_plan_id=None,
            last_apply_id=None,
            routing_examples=list(routing_examples or []),
        ),
        embedder=FixedEmbedder(),
        now="2026-07-18T00:00:00Z",
    )


def make_snapshot(
    *cards,
    live: tuple[str, ...] | None = None,
    schema_version: int = REMOTE_SCHEMA_V1,
):  # noqa: ANN002
    if live is None:
        live = tuple(card.namespace for card in cards)
    return classify_remote_catalog(
        live_namespace_ids=(REMOTE_CATALOG_NAMESPACE, *live),
        cards=cards,
        compatibility=CompatibilityContract(
            region=REGION,
            embedding_model="BAAI/bge-small-en-v1.5",
            embedding_precision="float32",
        ),
        metrics=ReadMetrics(2, 1, 2, ({"query_units": 2},)),
        catalog_schema_version=schema_version,
    )


def upsert_args(*, namespace: str = "site-example-v1", source_uri: str | None = None) -> list[str]:
    return [
        "catalog", "upsert", namespace,
        "--source-kind", "website",
        "--source-uri", source_uri or f"https://example.com/{namespace}",
        "--site-id", f"site-{namespace}",
        "--title", "Example",
        "--summary", "Example documentation.",
        "--alias", "example docs",
        "--tag", "docs",
        "--region", REGION,
        "--embedding-model", "BAAI/bge-small-en-v1.5",
        "--embedding-precision", "float32",
        "--plan-schema-version", "1",
        "--ranking-mode", "page",
        "--ranking-profile", "none",
        "--ranking-pool", "20",
        "--ranking-aggregation", "max",
        "--json",
    ]


def run_cli(
    args: list[str],
    *,
    env: dict[str, str] | None = None,
    client: object | None = None,
    patches: tuple[object, ...] = (),
) -> tuple[int, str, str]:
    stdout = StringIO()
    stderr = StringIO()
    fake = client if client is not None else FakeClient()
    environment = {"TURBOPUFFER_API_KEY": API_KEY} if env is None else env
    with ExitStack() as stack:
        stack.enter_context(patch.dict(os.environ, environment, clear=True))
        stack.enter_context(patch(
            "buoy_search.catalog_cli.REMOTE_CATALOG_CLIENT_FACTORY",
            side_effect=lambda **_kwargs: fake,
        ))
        # Any accidental bypass of the explicit injection must fail the test.
        stack.enter_context(patch(
            "buoy_search.remote_catalog.create_client",
            side_effect=AssertionError("real remote client construction attempted"),
        ))
        stack.enter_context(patch(
            "buoy_search.catalog_cli.load_config",
            return_value=SimpleNamespace(
                embedding_model="BAAI/bge-small-en-v1.5",
                embedding_precision="float32",
            ),
        ))
        for context in patches:
            stack.enter_context(context)
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                result = main(args)
            except SystemExit as exc:
                result = int(exc.code or 0)
    return result, stdout.getvalue(), stderr.getvalue()


class CatalogCliTests(unittest.TestCase):
    def test_parser_help_and_removed_catalog_argument(self) -> None:
        result, stdout, stderr = run_cli(["catalog", "--help"], env={})
        self.assertEqual((result, stderr), (0, ""))
        for command in ("list", "show", "upsert", "enable", "disable"):
            self.assertIn(command, stdout)
        self.assertNotIn("remove", stdout)
        self.assertNotIn("migrate-local", stdout)
        self.assertIn("remote namespace", stdout)
        self.assertIn(REMOTE_CATALOG_NAMESPACE, stdout)

        result, stdout, stderr = run_cli(["catalog", "upsert", "--help"], env={})
        self.assertEqual((result, stderr), (0, ""))
        self.assertIn("database", stdout)
        self.assertIn("--routing-example", stdout)

        result, stdout, stderr = run_cli(["catalog", "list", "--catalog", "legacy.json"])
        self.assertEqual((result, stdout), (2, ""))
        self.assertIn("unrecognized arguments: --catalog", stderr)

        result, stdout, stderr = run_cli([*upsert_args(), "--ranking-pool", "0"])
        self.assertEqual((result, stdout), (2, ""))
        self.assertIn("must be greater than zero", stderr)

    def test_list_filters_orders_classifies_and_redacts_vectors(self) -> None:
        enabled = make_card("z-live", title="Data_Vault")
        disabled = make_card("a-disabled", enabled=False)
        stale = make_card("m-stale")
        snapshot = make_snapshot(enabled, disabled, stale, live=("z-live", "a-disabled", "missing-live"))
        read = patch("buoy_search.catalog_cli.read_remote_catalog", return_value=snapshot)

        result, stdout, stderr = run_cli(["catalog", "list", "data vault", "--json"], patches=(read,))
        self.assertEqual((result, stderr), (0, ""))
        payload = json.loads(stdout)
        self.assertEqual([card["namespace"] for card in payload["cards"]], ["z-live"])
        self.assertNotIn("vector", payload["cards"][0])
        self.assertEqual(payload["catalog_namespace"], REMOTE_CATALOG_NAMESPACE)
        self.assertEqual(payload["region"], REGION)
        self.assertEqual(payload["counts"]["missing_card_count"], 1)
        self.assertEqual(payload["counts"]["disabled_count"], 1)
        self.assertEqual(payload["counts"]["stale_target_count"], 1)
        self.assertEqual(payload["coverage"]["eligible_ids"], ["z-live"])
        self.assertEqual(payload["coverage"]["missing_card_ids"], ["missing-live"])
        self.assertEqual(payload["coverage"]["disabled_ids"], ["a-disabled"])
        self.assertEqual(payload["coverage"]["stale_target_ids"], ["m-stale"])
        self.assertEqual(payload["cards"][0]["catalog_status"], "eligible")
        self.assertEqual(payload["cards"][0]["target_status"], "live")
        self.assertEqual(payload["read_metrics"]["billing"], [{"query_units": 2}])

        result, stdout, stderr = run_cli(["catalog", "list", "--all", "--json"], patches=(
            patch("buoy_search.catalog_cli.read_remote_catalog", return_value=snapshot),
        ))
        self.assertEqual((result, stderr), (0, ""))
        all_cards = json.loads(stdout)["cards"]
        self.assertEqual([card["namespace"] for card in all_cards], [
            "a-disabled", "m-stale", "z-live",
        ])
        self.assertEqual(
            [card["catalog_status"] for card in all_cards],
            ["disabled", "stale", "eligible"],
        )

    def test_show_live_stale_vector_visibility_and_missing_failure(self) -> None:
        card = make_card()
        live = make_snapshot(card)
        result, stdout, stderr = run_cli(["catalog", "show", card.namespace, "--json"], patches=(
            patch("buoy_search.catalog_cli.read_remote_catalog", return_value=live),
        ))
        self.assertEqual((result, stderr), (0, ""))
        payload = json.loads(stdout)
        self.assertEqual(payload["target_status"], "live")
        self.assertEqual(payload["catalog_status"], "eligible")
        self.assertNotIn("vector", payload["card"])

        stale = make_snapshot(card, live=())
        result, stdout, stderr = run_cli(
            ["catalog", "show", card.namespace, "--include-vector", "--json"],
            patches=(patch("buoy_search.catalog_cli.read_remote_catalog", return_value=stale),),
        )
        self.assertEqual((result, stderr), (0, ""))
        self.assertEqual(json.loads(stdout)["target_status"], "stale")
        self.assertEqual(len(json.loads(stdout)["card"]["vector"]), ROUTING_DIMENSIONS)

        result, stdout, stderr = run_cli(["catalog", "show", card.namespace, "--include-vector"], patches=(
            patch("buoy_search.catalog_cli.read_remote_catalog", return_value=live),
        ))
        self.assertEqual((result, stdout), (2, ""))
        self.assertIn("requires --json", stderr)

        result, stdout, stderr = run_cli(["catalog", "show", "missing", "--json"], patches=(
            patch("buoy_search.catalog_cli.read_remote_catalog", return_value=make_snapshot()),
        ))
        self.assertEqual((result, stdout), (2, ""))
        self.assertIn("no card for namespace 'missing'", stderr)

    def test_credentials_are_required_before_factory_use(self) -> None:
        factory = Mock(side_effect=AssertionError("factory called without credentials"))
        result, stdout, stderr = run_cli(
            ["catalog", "list", "--json"],
            env={},
            patches=(patch("buoy_search.catalog_cli.REMOTE_CATALOG_CLIENT_FACTORY", factory),),
        )
        self.assertEqual((result, stdout), (2, ""))
        self.assertIn("TURBOPUFFER_API_KEY must be set", stderr)
        factory.assert_not_called()

    def test_provider_failure_is_redacted_from_cli_error(self) -> None:
        result, stdout, stderr = run_cli(["catalog", "list", "--json"], client=ExplodingClient())
        self.assertEqual((result, stdout), (2, ""))
        self.assertIn("LeakyProviderError", stderr)
        self.assertNotIn(API_KEY, stderr)
        self.assertNotIn("provider leaked", stderr)

        result, stdout, stderr = run_cli(
            ["catalog", "list", "--json"],
            client=ResourceExplodingClient(),
        )
        self.assertEqual((result, stdout), (2, ""))
        self.assertIn("namespace resource acquisition", stderr)
        self.assertIn("LeakyProviderError", stderr)
        self.assertNotIn(API_KEY, stderr)
        self.assertNotIn("resource acquisition leaked", stderr)

    def test_upsert_create_and_update_use_remote_conditions_and_redact_vector(self) -> None:
        final_card = make_card()
        empty = make_snapshot(live=(final_card.namespace,))
        final = make_snapshot(final_card)
        create = Mock(return_value=MutationResult(
            True, final_card, 1, (remote_card_id(final_card.namespace),),
            MutationMetrics(1, 2, ({"write_units": 1}, {"query_units": 1}, {"query_units": 1})),
        ))
        embedder = FixedEmbedder()
        create_preview = Mock(side_effect=AssertionError("preview wrote"))
        result, stdout, stderr = run_cli(upsert_args(), patches=(
            patch("buoy_search.catalog_cli.read_remote_catalog", return_value=empty),
            patch("buoy_search.catalog_cli.create_remote_cards", create_preview),
            patch("buoy_search.catalog.load_routing_embedder", return_value=embedder),
        ))
        self.assertEqual((result, stderr), (0, ""))
        preview = json.loads(stdout)
        self.assertFalse(preview["approved"])
        self.assertEqual(preview["mutation_status"], "preview")
        self.assertEqual(preview["request_summary"]["write_requests"], 0)
        create_preview.assert_not_called()

        result, stdout, stderr = run_cli([*upsert_args(), "--approve"], patches=(
            patch("buoy_search.catalog_cli.read_remote_catalog", side_effect=[empty, final]),
            patch("buoy_search.catalog_cli.create_remote_cards", create),
            patch("buoy_search.catalog.load_routing_embedder", return_value=embedder),
        ))
        self.assertEqual((result, stderr), (0, ""))
        payload = json.loads(stdout)
        self.assertEqual(payload["mutation_status"], "created")
        self.assertEqual(payload["request_summary"]["total_requests"], 13)
        self.assertEqual(payload["request_summary"]["write_requests"], 1)
        self.assertNotIn("vector", payload["card"])
        created = create.call_args.args[1][0]
        self.assertEqual(created.semantic_origin, "manual")
        self.assertEqual(created.region, REGION)
        self.assertEqual(len(embedder.calls), 2)

        changed = make_card(title="Changed")
        update = Mock(side_effect=RemoteCatalogError("conditional card update conflicted with a newer remote revision"))
        args = [*upsert_args(), "--approve"]
        args[args.index("Example")] = "Changed"
        result, stdout, stderr = run_cli(args, patches=(
            patch("buoy_search.catalog_cli.read_remote_catalog", return_value=make_snapshot(final_card)),
            patch("buoy_search.catalog_cli.update_remote_card", update),
            patch("buoy_search.catalog.load_routing_embedder", return_value=FixedEmbedder()),
        ))
        self.assertEqual((result, stdout), (2, ""))
        self.assertIn("conditional card update conflicted", stderr)
        self.assertEqual(update.call_args.kwargs["expected_revision"], final_card.card_revision)
        self.assertEqual(update.call_args.args[1].title, changed.title)

    def test_routing_example_preview_and_reader_first_v1_write_gate(self) -> None:
        live_v1 = make_snapshot(live=("site-example-v1",))
        examples = ["Where are retries configured?", "How do I set a timeout?"]
        args = [
            *upsert_args(),
            *(item for example in examples for item in ("--routing-example", example)),
        ]
        write = Mock(side_effect=AssertionError("preview wrote"))
        embedder = FixedEmbedder()

        result, stdout, stderr = run_cli(args, patches=(
            patch("buoy_search.catalog_cli.read_remote_catalog", return_value=live_v1),
            patch("buoy_search.catalog_cli.create_remote_cards", write),
            patch("buoy_search.catalog.load_routing_embedder", return_value=embedder),
        ))

        self.assertEqual((result, stderr), (0, ""))
        payload = json.loads(stdout)
        self.assertEqual(payload["mutation_status"], "preview")
        self.assertEqual(payload["card"]["routing_examples"], sorted(examples))
        self.assertEqual(len(embedder.calls[0]), 3)
        write.assert_not_called()

        model = Mock(side_effect=AssertionError("v1 approval loaded model"))
        result, stdout, stderr = run_cli([*args, "--approve"], patches=(
            patch("buoy_search.catalog_cli.read_remote_catalog", return_value=live_v1),
            patch("buoy_search.catalog_cli.create_remote_cards", write),
            patch("buoy_search.catalog.load_routing_embedder", model),
        ))
        self.assertEqual((result, stdout), (2, ""))
        self.assertIn("reader-first", stderr)
        self.assertIn("no schema-v1 write occurred", stderr)
        model.assert_not_called()
        write.assert_not_called()

    def test_routing_example_approval_uses_observed_v2_schema(self) -> None:
        example = "Where are retries configured?"
        final_card = make_card(routing_examples=[example])
        empty = make_snapshot(
            live=(final_card.namespace,), schema_version=REMOTE_SCHEMA_V2
        )
        final = make_snapshot(final_card, schema_version=REMOTE_SCHEMA_V2)
        create = Mock(return_value=MutationResult(
            True,
            final_card,
            1,
            (remote_card_id(final_card.namespace),),
            MutationMetrics(1, 2, ()),
        ))

        result, stdout, stderr = run_cli(
            [*upsert_args(), "--routing-example", example, "--approve"],
            patches=(
                patch(
                    "buoy_search.catalog_cli.read_remote_catalog",
                    side_effect=[empty, final],
                ),
                patch("buoy_search.catalog_cli.create_remote_cards", create),
                patch(
                    "buoy_search.catalog.load_routing_embedder",
                    return_value=FixedEmbedder(),
                ),
            ),
        )

        self.assertEqual((result, stderr), (0, ""))
        self.assertEqual(json.loads(stdout)["mutation_status"], "created")
        self.assertEqual(create.call_args.kwargs["schema_version"], REMOTE_SCHEMA_V2)
        self.assertEqual(
            create.call_args.args[1][0].routing_examples,
            [example],
        )

    def test_upsert_rejects_nonlive_reserved_and_malformed_card_arguments_before_write(self) -> None:
        create = Mock(side_effect=AssertionError("invalid upsert wrote"))
        for args, message in (
            (upsert_args(namespace="not-live"), "is not live"),
            (upsert_args(namespace=REMOTE_CATALOG_NAMESPACE), "is not live"),
        ):
            with self.subTest(message=message):
                result, stdout, stderr = run_cli(args, patches=(
                    patch("buoy_search.catalog_cli.read_remote_catalog", return_value=make_snapshot()),
                    patch("buoy_search.catalog_cli.create_remote_cards", create),
                ))
                self.assertEqual((result, stdout), (2, ""))
                self.assertIn(message, stderr)
        create.assert_not_called()

        live = make_snapshot(live=("site-example-v1",))
        for source_uri in (" https://example.com", "https://example.com:not-a-port", "urn:example"):
            with self.subTest(source_uri=source_uri):
                result, stdout, stderr = run_cli(upsert_args(source_uri=source_uri), patches=(
                    patch("buoy_search.catalog_cli.read_remote_catalog", return_value=live),
                    patch("buoy_search.catalog_cli.create_remote_cards", create),
                    patch("buoy_search.catalog.load_routing_embedder", side_effect=AssertionError("model loaded")),
                ))
                self.assertEqual((result, stdout), (2, ""))
                self.assertIn("source_uri", stderr)
        create.assert_not_called()

    def test_enable_disable_idempotence_and_conditional_conflict(self) -> None:
        enabled = make_card(enabled=True)
        disabled = make_card(enabled=False)
        update = Mock(return_value=MutationResult(
            True, disabled, 1, (remote_card_id(enabled.namespace),),
            MutationMetrics(1, 2, ({"write_units": 1}, {"query_units": 1}, {"query_units": 1})),
        ))
        preview_write = Mock(side_effect=AssertionError("preview wrote"))
        result, stdout, stderr = run_cli(["catalog", "disable", enabled.namespace, "--json"], patches=(
            patch("buoy_search.catalog_cli.read_remote_catalog", return_value=make_snapshot(enabled)),
            patch("buoy_search.catalog_cli.update_remote_card", preview_write),
        ))
        self.assertEqual((result, stderr), (0, ""))
        preview = json.loads(stdout)
        self.assertFalse(preview["approved"])
        self.assertEqual(preview["mutation_status"], "preview")
        self.assertEqual(preview["request_summary"]["write_requests"], 0)
        self.assertFalse(preview["card"]["enabled"])
        preview_write.assert_not_called()

        result, stdout, stderr = run_cli(
            ["catalog", "disable", enabled.namespace, "--approve", "--json"],
            patches=(
                patch("buoy_search.catalog_cli.read_remote_catalog", side_effect=[make_snapshot(enabled), make_snapshot(disabled)]),
                patch("buoy_search.catalog_cli.update_remote_card", update),
            ),
        )
        self.assertEqual((result, stderr), (0, ""))
        updated = json.loads(stdout)
        self.assertEqual(updated["mutation_status"], "updated")
        self.assertEqual(updated["request_summary"]["total_requests"], 13)
        self.assertEqual(updated["request_summary"]["write_requests"], 1)
        sent = update.call_args.args[1]
        self.assertFalse(sent.enabled)
        self.assertEqual(sent.vector, enabled.vector)
        self.assertEqual(update.call_args.kwargs["expected_revision"], enabled.card_revision)

        result, stdout, stderr = run_cli(["catalog", "disable", disabled.namespace, "--approve", "--json"], patches=(
            patch("buoy_search.catalog_cli.read_remote_catalog", side_effect=[make_snapshot(disabled), make_snapshot(disabled)]),
            patch("buoy_search.catalog_cli.update_remote_card", side_effect=AssertionError("idempotent toggle wrote")),
        ))
        self.assertEqual((result, stderr), (0, ""))
        unchanged = json.loads(stdout)
        self.assertEqual(unchanged["mutation_status"], "unchanged")
        self.assertEqual(unchanged["request_summary"]["total_requests"], 10)
        self.assertEqual(unchanged["request_summary"]["write_requests"], 0)

        result, stdout, stderr = run_cli(["catalog", "enable", disabled.namespace, "--approve", "--json"], patches=(
            patch("buoy_search.catalog_cli.read_remote_catalog", return_value=make_snapshot(disabled)),
            patch("buoy_search.catalog_cli.update_remote_card", side_effect=RemoteCatalogError(
                "conditional card update conflicted with a newer remote revision"
            )),
        ))
        self.assertEqual((result, stdout), (2, ""))
        self.assertIn("conditional card update conflicted", stderr)

if __name__ == "__main__":
    unittest.main()
