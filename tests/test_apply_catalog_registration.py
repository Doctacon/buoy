from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import buoy_search.apply as apply_module
from buoy_search.applied_state import load_applied_state
from buoy_search.apply import (
    CatalogRegistrationPartialSuccess,
    generated_card_for_apply,
    load_verified_apply_plan,
    register_apply_catalog_card,
    run_approved_apply,
)
from buoy_search.catalog import CardFields, ROUTING_DIMENSIONS, prepare_card
from buoy_search.config import RuntimeConfig
from buoy_search.remote_catalog import (
    REMOTE_CATALOG_NAMESPACE,
    REMOTE_SCHEMA_V2,
    CompatibilityContract,
    MutationMetrics,
    MutationResult,
    classify_remote_catalog,
    remote_card_id,
)
from tests.test_apply_cli import (
    FakeEmbedder,
    FakeWriter,
    build_saved_plan,
    reset_fakes,
)


REGION = "gcp-us-central1"
MODEL = "BAAI/bge-small-en-v1.5"
UNIT_VECTOR = [1.0] + [0.0] * (ROUTING_DIMENSIONS - 1)


class FixedRoutingEmbedder:
    def encode(self, texts):  # noqa: ANN001
        return [list(UNIT_VECTOR) for _ in texts]


class FakeClient:
    def __init__(self) -> None:
        self.resource = object()
        self.namespace_calls: list[str] = []

    def namespace(self, namespace: str) -> object:
        self.namespace_calls.append(namespace)
        return self.resource


def manual_card(namespace: str):  # noqa: ANN201 - test helper
    return prepare_card(
        CardFields(
            namespace=namespace,
            enabled=False,
            source_kind="website",
            source_uri="https://old.example.com/",
            site_id="old-site",
            title="Operator title",
            summary="Operator-authored routing summary.",
            aliases=["operator alias"],
            tags=["operator tag"],
            semantic_origin="manual",
            region=REGION,
            embedding_model=MODEL,
            embedding_precision="float32",
            plan_schema_version=2,
            ranking_mode="page",
            ranking_profile="none",
            ranking_pool=20,
            ranking_aggregation="max",
            last_plan_id="plan_previous",
            last_apply_id="apply_previous",
            routing_examples=["How do I use the operator routing policy?"],
        ),
        embedder=FixedRoutingEmbedder(),
        now="2026-08-12T00:00:00+00:00",
    )


class ApplyCatalogRegistrationTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_fakes()

    def test_generated_apply_card_preserves_manual_semantics_vector_and_enabled_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            verified = load_verified_apply_plan(
                plan_path=plan_path,
                namespace=artifacts.manifest.namespace,
                state_root=state_root,
            )
            existing = manual_card(artifacts.manifest.namespace)

            card = generated_card_for_apply(
                verified,
                namespace=artifacts.manifest.namespace,
                region=REGION,
                apply_id="apply_current",
                existing=existing,
            )

        self.assertFalse(card.enabled)
        self.assertEqual(card.semantic_origin, "manual")
        self.assertEqual(card.title, existing.title)
        self.assertEqual(card.summary, existing.summary)
        self.assertEqual(card.aliases, existing.aliases)
        self.assertEqual(card.tags, existing.tags)
        self.assertEqual(card.routing_examples, existing.routing_examples)
        self.assertEqual(card.vector, existing.vector)
        self.assertEqual(card.source_uri, artifacts.plan.source["uri"])
        self.assertEqual(card.site_id, artifacts.plan.site_id)
        self.assertEqual(card.last_plan_id, artifacts.plan.plan_id)
        self.assertEqual(card.last_apply_id, "apply_current")

    def test_registration_conditionally_creates_or_updates_exact_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            verified = load_verified_apply_plan(
                plan_path=plan_path,
                namespace=artifacts.manifest.namespace,
                state_root=state_root,
            )
            namespace = artifacts.manifest.namespace
            config = RuntimeConfig(region=REGION, namespace=namespace)
            existing = manual_card(namespace)
            intended = generated_card_for_apply(
                verified,
                namespace=namespace,
                region=REGION,
                apply_id="apply_current",
                existing=existing,
            )

            for label, cards, mutation_name in (
                ("create", (), "create_remote_cards"),
                ("update", (existing,), "update_remote_card"),
            ):
                with self.subTest(label=label):
                    client = FakeClient()
                    snapshot = classify_remote_catalog(
                        live_namespace_ids=(REMOTE_CATALOG_NAMESPACE, namespace),
                        cards=cards,
                        compatibility=CompatibilityContract(
                            region=REGION,
                            embedding_model=MODEL,
                            embedding_precision="float32",
                        ),
                        catalog_schema_version=REMOTE_SCHEMA_V2,
                    )
                    mutation = Mock(
                        return_value=MutationResult(
                            True,
                            intended,
                            1,
                            (remote_card_id(namespace),),
                            MutationMetrics(1, 2, ()),
                        )
                    )
                    other = "update_remote_card" if mutation_name == "create_remote_cards" else "create_remote_cards"
                    with patch.object(
                        apply_module,
                        "REMOTE_CATALOG_CLIENT_FACTORY",
                        return_value=client,
                    ), patch.object(
                        apply_module,
                        "read_remote_catalog",
                        return_value=snapshot,
                    ), patch.object(
                        apply_module,
                        "generated_card_for_apply",
                        return_value=intended,
                    ), patch.object(
                        apply_module,
                        mutation_name,
                        mutation,
                    ), patch.object(
                        apply_module,
                        other,
                        side_effect=AssertionError("wrong mutation path"),
                    ):
                        result = register_apply_catalog_card(
                            verified,
                            config=config,
                            namespace=namespace,
                            apply_id="apply_current",
                            api_key="test-key",
                        )

                    self.assertTrue(result["catalog_registered"])
                    self.assertEqual(result["catalog_mutation_status"], f"{label}d")
                    self.assertEqual(client.namespace_calls, [REMOTE_CATALOG_NAMESPACE])
                    if label == "update":
                        self.assertEqual(
                            mutation.call_args.kwargs["expected_revision"],
                            existing.card_revision,
                        )
                    self.assertEqual(
                        mutation.call_args.kwargs["schema_version"],
                        REMOTE_SCHEMA_V2,
                    )

    def test_failure_before_catalog_read_only_suggests_safe_inspection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            verified = load_verified_apply_plan(
                plan_path=plan_path,
                namespace=artifacts.manifest.namespace,
                state_root=state_root,
            )
            namespace = artifacts.manifest.namespace
            client = FakeClient()

            with patch.object(
                apply_module,
                "REMOTE_CATALOG_CLIENT_FACTORY",
                return_value=client,
            ), patch.object(
                apply_module,
                "read_remote_catalog",
                side_effect=RuntimeError("catalog read failed"),
            ):
                with self.assertRaises(
                    apply_module._CatalogRegistrationAttemptError
                ) as raised:
                    register_apply_catalog_card(
                        verified,
                        config=RuntimeConfig(region=REGION, namespace=namespace),
                        namespace=namespace,
                        apply_id="apply_current",
                        api_key="test-key",
                    )

        self.assertEqual(
            raised.exception.repair_command,
            f"buoy catalog show {namespace} --region {REGION} --json",
        )
        self.assertNotIn("upsert", raised.exception.repair_command)
        self.assertNotIn("--approve", raised.exception.repair_command)
        self.assertEqual(client.namespace_calls, [])

    def test_catalog_resource_failure_is_redacted_after_existing_card_is_known(self) -> None:
        secret = "tpuf_APPLY_RESOURCE_SECRET"

        class ResourceExplodingClient(FakeClient):
            def namespace(self, namespace: str) -> object:
                self.namespace_calls.append(namespace)
                raise RuntimeError(f"Authorization: Bearer {secret}")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            verified = load_verified_apply_plan(
                plan_path=plan_path,
                namespace=artifacts.manifest.namespace,
                state_root=state_root,
            )
            namespace = artifacts.manifest.namespace
            existing = manual_card(namespace)
            snapshot = classify_remote_catalog(
                live_namespace_ids=(REMOTE_CATALOG_NAMESPACE, namespace),
                cards=(existing,),
                compatibility=CompatibilityContract(
                    region=REGION,
                    embedding_model=MODEL,
                    embedding_precision="float32",
                ),
            )
            client = ResourceExplodingClient()

            with patch.object(
                apply_module,
                "REMOTE_CATALOG_CLIENT_FACTORY",
                return_value=client,
            ), patch.object(
                apply_module,
                "read_remote_catalog",
                return_value=snapshot,
            ):
                with self.assertRaises(
                    apply_module._CatalogRegistrationAttemptError
                ) as raised:
                    register_apply_catalog_card(
                        verified,
                        config=RuntimeConfig(region=REGION, namespace=namespace),
                        namespace=namespace,
                        apply_id="apply_current",
                        api_key=secret,
                    )

        self.assertIn("namespace resource acquisition", str(raised.exception))
        self.assertIn("RuntimeError", str(raised.exception))
        self.assertNotIn(secret, str(raised.exception))
        self.assertNotIn("Authorization", str(raised.exception))
        self.assertIn("buoy catalog upsert", raised.exception.repair_command)
        self.assertIn("--routing-example", raised.exception.repair_command)
        self.assertIn("--approve", raised.exception.repair_command)
        self.assertEqual(client.namespace_calls, [REMOTE_CATALOG_NAMESPACE])

    def test_catalog_failure_after_state_commit_is_truthful_partial_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            verified = load_verified_apply_plan(
                plan_path=plan_path,
                namespace=artifacts.manifest.namespace,
                state_root=state_root,
            )
            cleanup_bindings = []

            def fail_after_observing_state(_verified, **kwargs):  # noqa: ANN001, ANN003, ANN202
                state = load_applied_state(
                    site_id=artifacts.manifest.site_id,
                    namespace=artifacts.manifest.namespace,
                    base_url=artifacts.manifest.base_url,
                    state_root=state_root,
                )
                self.assertEqual(state.last_apply_id, kwargs["apply_id"])
                raise apply_module._CatalogRegistrationAttemptError(
                    "remote routing catalog card write failed (TimeoutError, timeout)",
                    api_calls_occurred=True,
                    repair_command="buoy catalog upsert site-example-com-v1 ... --approve",
                )

            with patch.dict(
                "os.environ",
                {"TURBOPUFFER_API_KEY": "test-key"},
                clear=True,
            ), patch.object(
                apply_module,
                "SentenceTransformerEmbedder",
                FakeEmbedder,
            ), patch.object(
                apply_module,
                "TurbopufferWriter",
                FakeWriter,
            ), patch.object(
                apply_module,
                "register_apply_catalog_card",
                side_effect=fail_after_observing_state,
            ):
                with self.assertRaises(CatalogRegistrationPartialSuccess) as raised:
                    run_approved_apply(
                        verified,
                        config=RuntimeConfig(namespace=artifacts.manifest.namespace),
                        namespace=artifacts.manifest.namespace,
                        batch_size=64,
                        cleanup_binding_callback=cleanup_bindings.append,
                    )

            state = load_applied_state(
                site_id=artifacts.manifest.site_id,
                namespace=artifacts.manifest.namespace,
                base_url=artifacts.manifest.base_url,
                state_root=state_root,
            )

        summary = raised.exception.summary
        self.assertTrue(summary["content_applied"])
        self.assertTrue(summary["state_updated"])
        self.assertTrue(summary["partial_success"])
        self.assertFalse(summary["catalog_registered"])
        self.assertEqual(summary["catalog_mutation_status"], "failed")
        self.assertTrue(summary["api_calls_occurred"])
        self.assertIn("buoy catalog upsert", summary["catalog_repair_command"])
        self.assertEqual(state.last_apply_id, summary["apply_id"])
        self.assertEqual(len(FakeWriter.rows), len(artifacts.manifest.chunks))
        self.assertEqual(len(cleanup_bindings), 1)


if __name__ == "__main__":
    unittest.main()
