from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import shlex
import tempfile
import unittest
from unittest.mock import Mock, patch

import buoy_search.apply as apply_module
from buoy_search.applied_state import load_applied_state, save_applied_state
from buoy_search.apply import (
    ApplyPlanError,
    CatalogRegistrationPartialSuccess,
    build_state_after_apply,
    generated_card_for_apply,
    load_verified_apply_plan,
    register_apply_catalog_card,
    run_approved_apply,
)
from buoy_search.catalog import (
    MAX_ROUTING_EVIDENCE,
    CardFields,
    ROUTING_DIMENSIONS,
    card_to_dict,
    prepare_card,
)
from buoy_search.config import RuntimeConfig
from buoy_search.remote_catalog import (
    REMOTE_CATALOG_NAMESPACE,
    REMOTE_SCHEMA_V2,
    REMOTE_SCHEMA_V3,
    CompatibilityContract,
    MutationMetrics,
    MutationResult,
    RemoteCatalogMissingError,
    classify_remote_catalog,
    remote_card_id,
)
from tests.test_apply_cli import (
    FakeEmbedder,
    FakeWriter,
    build_saved_plan,
    reset_fakes,
)
from tests.test_catalog_cli import run_cli


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


def manual_card(
    namespace: str,
    *,
    routing_examples: list[str] | None = None,
):  # noqa: ANN201 - test helper
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
            plan_schema_version=3,
            ranking_mode="page",
            ranking_profile="none",
            ranking_pool=20,
            ranking_aggregation="max",
            last_plan_id="plan_previous",
            last_apply_id="apply_previous",
            routing_examples=(
                routing_examples
                if routing_examples is not None
                else ["How do I use the operator routing policy?"]
            ),
        ),
        embedder=FixedRoutingEmbedder(),
        now="2026-08-12T00:00:00+00:00",
    )


def generated_card(namespace: str):  # noqa: ANN201 - test helper
    return prepare_card(
        CardFields(
            namespace=namespace,
            enabled=True,
            source_kind="website",
            source_uri="https://old-generated.example.com/",
            site_id="old-generated-site",
            title="Old generated title",
            summary="Old generated routing summary.",
            aliases=["old generated alias"],
            tags=["old generated tag"],
            semantic_origin="generated",
            region=REGION,
            embedding_model=MODEL,
            embedding_precision="float32",
            plan_schema_version=3,
            ranking_mode="page",
            ranking_profile="none",
            ranking_pool=20,
            ranking_aggregation="max",
            last_plan_id="plan_previous",
            last_apply_id="apply_previous",
            routing_examples=["How do I use the reviewed generated-card workflow?"],
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
            reviewed_examples = [
                f"How do I use operator routing policy {index}?"
                for index in range(MAX_ROUTING_EVIDENCE - 1)
            ]
            existing = manual_card(
                artifacts.manifest.namespace,
                routing_examples=reviewed_examples,
            )

            with patch(
                "buoy_search.catalog.load_routing_embedder",
                return_value=FixedRoutingEmbedder(),
            ):
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
        self.assertEqual(
            card.routing_passages,
            [verified.routing_prototypes[0]["passage_text"]],
        )
        self.assertEqual(
            len(card.routing_examples) + len(card.routing_passages),
            MAX_ROUTING_EVIDENCE,
        )
        self.assertEqual(card.vector, existing.vector)
        self.assertNotEqual(
            card.routing_prototype_hash,
            existing.routing_prototype_hash,
        )
        self.assertEqual(card.source_uri, artifacts.plan.source["uri"])
        self.assertEqual(card.site_id, artifacts.plan.site_id)
        self.assertEqual(card.last_plan_id, artifacts.plan.plan_id)
        self.assertEqual(card.last_apply_id, "apply_current")

    def test_emitted_repair_recreates_exact_generated_and_manual_card_authority(self) -> None:
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
            committed = build_state_after_apply(
                verified,
                applied_at="2026-08-16T12:00:00+00:00",
            )
            save_applied_state(committed, state_root=state_root)
            apply_id = committed.last_apply_id
            for existing in (None, manual_card(namespace)):
                with self.subTest(
                    existing="absent" if existing is None else "manual"
                ), patch(
                    "buoy_search.catalog.load_routing_embedder",
                    return_value=FixedRoutingEmbedder(),
                ):
                    intended = generated_card_for_apply(
                        verified,
                        namespace=namespace,
                        region=REGION,
                        apply_id=apply_id,
                        existing=existing,
                    )
                    command = apply_module._catalog_repair_command(
                        verified,
                        namespace=namespace,
                        region=REGION,
                        apply_id=apply_id,
                        existing_revision=(
                            existing.card_revision if existing is not None else None
                        ),
                    )
                    initial = classify_remote_catalog(
                        live_namespace_ids=(REMOTE_CATALOG_NAMESPACE, namespace),
                        cards=(() if existing is None else (existing,)),
                        compatibility=CompatibilityContract(
                            region=REGION,
                            embedding_model=MODEL,
                            embedding_precision="float32",
                        ),
                        catalog_schema_version=REMOTE_SCHEMA_V3,
                    )
                    sent = []

                    def write(_resource, card_or_cards, **_kwargs):  # noqa: ANN001, ANN003, ANN202
                        card = (
                            card_or_cards[0]
                            if isinstance(card_or_cards, list)
                            else card_or_cards
                        )
                        sent.append(card)
                        return MutationResult(
                            True,
                            card,
                            1,
                            (remote_card_id(namespace),),
                            MutationMetrics(1, 2, ()),
                        )

                    def read_catalog(*_args, **_kwargs):  # noqa: ANN002, ANN003, ANN202
                        if not sent:
                            return initial
                        return classify_remote_catalog(
                            live_namespace_ids=(REMOTE_CATALOG_NAMESPACE, namespace),
                            cards=(sent[0],),
                            compatibility=CompatibilityContract(
                                region=REGION,
                                embedding_model=MODEL,
                                embedding_precision="float32",
                            ),
                            catalog_schema_version=REMOTE_SCHEMA_V3,
                        )

                    result, _stdout, stderr = run_cli(
                        shlex.split(command)[1:],
                        patches=(
                            patch(
                                "buoy_search.apply.REMOTE_CATALOG_CLIENT_FACTORY",
                                return_value=FakeClient(),
                            ),
                            patch(
                                "buoy_search.apply.read_remote_catalog",
                                side_effect=read_catalog,
                            ),
                            patch(
                                "buoy_search.apply.create_remote_cards",
                                side_effect=write,
                            ),
                            patch(
                                "buoy_search.apply.update_remote_card",
                                side_effect=write,
                            ),
                            patch(
                                "buoy_search.catalog.load_routing_embedder",
                                return_value=FixedRoutingEmbedder(),
                            ),
                            patch(
                                "buoy_search.plan_cleanup.cleanup_applied_plan_directory",
                                return_value=[],
                            ),
                        ),
                    )

                    self.assertEqual((result, stderr), (0, ""))
                    self.assertEqual(len(sent), 1)
                    repaired = sent[0]
                    self.assertEqual(repaired.card_revision, intended.card_revision)
                    intended_payload = card_to_dict(intended, include_vector=True)
                    repaired_payload = card_to_dict(repaired, include_vector=True)
                    for timestamp in ("created_at", "updated_at"):
                        intended_payload.pop(timestamp)
                        repaired_payload.pop(timestamp)
                    self.assertEqual(repaired_payload, intended_payload)

    def test_inspection_emits_bound_absent_or_revision_repair_without_writing(self) -> None:
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
            committed = build_state_after_apply(
                verified,
                applied_at="2026-08-16T12:00:00+00:00",
            )
            save_applied_state(committed, state_root=state_root)
            inspection_command = apply_module._catalog_repair_inspect_command(
                verified,
                namespace=namespace,
                region=REGION,
                apply_id=committed.last_apply_id,
            )

            for existing in (None, manual_card(namespace)):
                with self.subTest(
                    existing="absent" if existing is None else "present"
                ):
                    snapshot = classify_remote_catalog(
                        live_namespace_ids=(REMOTE_CATALOG_NAMESPACE, namespace),
                        cards=(() if existing is None else (existing,)),
                        compatibility=CompatibilityContract(
                            region=REGION,
                            embedding_model=MODEL,
                            embedding_precision="float32",
                        ),
                        catalog_schema_version=REMOTE_SCHEMA_V3,
                    )
                    client = FakeClient()
                    result, stdout, stderr = run_cli(
                        [*shlex.split(inspection_command)[1:], "--json"],
                        patches=(
                            patch(
                                "buoy_search.apply.REMOTE_CATALOG_CLIENT_FACTORY",
                                return_value=client,
                            ),
                            patch(
                                "buoy_search.apply.read_remote_catalog",
                                return_value=snapshot,
                            ),
                            patch(
                                "buoy_search.apply.create_remote_cards",
                                side_effect=AssertionError(
                                    "inspection attempted a card create"
                                ),
                            ),
                            patch(
                                "buoy_search.apply.update_remote_card",
                                side_effect=AssertionError(
                                    "inspection attempted a card update"
                                ),
                            ),
                            patch(
                                "buoy_search.catalog.load_routing_embedder",
                                side_effect=AssertionError(
                                    "inspection loaded the routing model"
                                ),
                            ),
                            patch(
                                "buoy_search.plan_cleanup.cleanup_applied_plan_directory",
                                side_effect=AssertionError(
                                    "inspection cleaned the retained plan"
                                ),
                            ),
                        ),
                    )

                    self.assertEqual((result, stderr), (0, ""))
                    payload = json.loads(stdout)
                    self.assertTrue(payload["inspection"])
                    self.assertTrue(payload["plan_retained"])
                    self.assertFalse(payload["catalog_card_write_attempted"])
                    self.assertFalse(payload["routing_model_loaded"])
                    bound = shlex.split(payload["catalog_repair_command"])
                    self.assertIn("--approve", bound)
                    self.assertNotIn("--inspect-current", bound)
                    if existing is None:
                        self.assertIn("--expect-absent", bound)
                        self.assertNotIn("--expected-card-revision", bound)
                    else:
                        self.assertEqual(
                            bound[bound.index("--expected-card-revision") + 1],
                            existing.card_revision,
                        )
                        self.assertNotIn("--expect-absent", bound)
                    self.assertTrue(plan_path.exists())
                    self.assertEqual(client.namespace_calls, [])

    def test_ambiguous_create_or_update_is_idempotent_when_authority_matches(self) -> None:
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
            committed = build_state_after_apply(
                verified,
                applied_at="2026-08-16T12:00:00+00:00",
            )
            save_applied_state(committed, state_root=state_root)

            for label, previous in (("create", None), ("update", manual_card(namespace))):
                with self.subTest(label=label), patch(
                    "buoy_search.catalog.load_routing_embedder",
                    return_value=FixedRoutingEmbedder(),
                ):
                    intended = generated_card_for_apply(
                        verified,
                        namespace=namespace,
                        region=REGION,
                        apply_id=committed.last_apply_id,
                        existing=previous,
                    )
                command = apply_module._catalog_repair_command(
                    verified,
                    namespace=namespace,
                    region=REGION,
                    apply_id=committed.last_apply_id,
                    existing_revision=(
                        previous.card_revision if previous is not None else None
                    ),
                )
                snapshot = classify_remote_catalog(
                    live_namespace_ids=(REMOTE_CATALOG_NAMESPACE, namespace),
                    cards=(intended,),
                    compatibility=CompatibilityContract(
                        region=REGION,
                        embedding_model=MODEL,
                        embedding_precision="float32",
                    ),
                    catalog_schema_version=REMOTE_SCHEMA_V3,
                )
                client = FakeClient()
                cleanup = Mock(return_value=[])
                result, stdout, stderr = run_cli(
                    [*shlex.split(command)[1:], "--json"],
                    patches=(
                        patch.object(
                            apply_module,
                            "REMOTE_CATALOG_CLIENT_FACTORY",
                            return_value=client,
                        ),
                        patch.object(
                            apply_module,
                            "read_remote_catalog",
                            return_value=snapshot,
                        ),
                        patch.object(
                            apply_module,
                            "create_remote_cards",
                            side_effect=AssertionError(
                                "idempotent repair created a card"
                            ),
                        ),
                        patch.object(
                            apply_module,
                            "update_remote_card",
                            side_effect=AssertionError(
                                "idempotent repair updated a card"
                            ),
                        ),
                        patch(
                            "buoy_search.catalog.load_routing_embedder",
                            side_effect=AssertionError(
                                "idempotent repair regenerated routing embeddings"
                            ),
                        ),
                        patch(
                            "buoy_search.plan_cleanup.cleanup_applied_plan_directory",
                            cleanup,
                        ),
                    ),
                )

                self.assertEqual((result, stderr), (0, ""))
                payload = json.loads(stdout)
                self.assertEqual(payload["catalog_mutation_status"], "unchanged")
                self.assertEqual(
                    payload["catalog_card_revision"], intended.card_revision
                )
                self.assertTrue(payload["routing_projection_reused"])
                self.assertEqual(payload["routing_embeddings_generated"], 0)
                self.assertEqual(client.namespace_calls, [])
                cleanup.assert_called_once()

    def test_inspection_requires_exact_v3_and_retains_plan(self) -> None:
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
            committed = build_state_after_apply(
                verified,
                applied_at="2026-08-16T12:00:00+00:00",
            )
            save_applied_state(committed, state_root=state_root)
            command = apply_module._catalog_repair_inspect_command(
                verified,
                namespace=namespace,
                region=REGION,
                apply_id=committed.last_apply_id,
            )
            snapshot = classify_remote_catalog(
                live_namespace_ids=(REMOTE_CATALOG_NAMESPACE, namespace),
                cards=(),
                compatibility=CompatibilityContract(
                    region=REGION,
                    embedding_model=MODEL,
                    embedding_precision="float32",
                ),
                catalog_schema_version=REMOTE_SCHEMA_V2,
            )
            result, _stdout, stderr = run_cli(
                shlex.split(command)[1:],
                patches=(
                    patch.object(
                        apply_module,
                        "REMOTE_CATALOG_CLIENT_FACTORY",
                        return_value=FakeClient(),
                    ),
                    patch.object(
                        apply_module,
                        "read_remote_catalog",
                        return_value=snapshot,
                    ),
                    patch(
                        "buoy_search.catalog.load_routing_embedder",
                        side_effect=AssertionError(
                            "v2 inspection loaded the routing model"
                        ),
                    ),
                    patch(
                        "buoy_search.plan_cleanup.cleanup_applied_plan_directory",
                        side_effect=AssertionError(
                            "v2 inspection cleaned the retained plan"
                        ),
                    ),
                ),
            )

            self.assertEqual(result, 2)
            self.assertIn("schema-v3 migration", stderr)
            self.assertTrue(plan_path.exists())

            secret = "tpuf_INSPECTION_SECRET"
            result, _stdout, stderr = run_cli(
                shlex.split(command)[1:],
                patches=(
                    patch.object(
                        apply_module,
                        "REMOTE_CATALOG_CLIENT_FACTORY",
                        side_effect=RuntimeError(f"Bearer {secret}"),
                    ),
                ),
            )
            self.assertEqual(result, 2)
            self.assertIn("RuntimeError", stderr)
            self.assertNotIn(secret, stderr)
            self.assertNotIn("Bearer", stderr)
            self.assertTrue(plan_path.exists())

    def test_repair_revalidates_state_under_lock_before_provider_work(self) -> None:
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
            committed = build_state_after_apply(
                verified,
                applied_at="2026-08-16T12:00:00+00:00",
            )
            save_applied_state(committed, state_root=state_root)
            command = apply_module._catalog_repair_command(
                verified,
                namespace=namespace,
                region=REGION,
                apply_id=committed.last_apply_id,
            )
            real_loader = apply_module.load_verified_catalog_repair_plan
            calls = 0

            def advance_after_preflight(**kwargs):  # noqa: ANN003, ANN202
                nonlocal calls
                calls += 1
                result = real_loader(**kwargs)
                if calls == 1:
                    current = load_applied_state(
                        site_id=artifacts.manifest.site_id,
                        namespace=namespace,
                        base_url=artifacts.manifest.base_url,
                        state_root=state_root,
                    )
                    save_applied_state(
                        replace(
                            current,
                            last_plan_id="newer_plan",
                            last_apply_id="newer_apply",
                        ),
                        state_root=state_root,
                    )
                return result

            provider = Mock(
                side_effect=AssertionError(
                    "stale repair reached provider work after state advanced"
                )
            )
            result, _stdout, _stderr = run_cli(
                [*shlex.split(command)[1:], "--json"],
                patches=(
                    patch(
                        "buoy_search.apply.load_verified_catalog_repair_plan",
                        side_effect=advance_after_preflight,
                    ),
                    patch(
                        "buoy_search.apply.REMOTE_CATALOG_CLIENT_FACTORY",
                        provider,
                    ),
                ),
            )

            self.assertEqual(result, 2)
            self.assertEqual(calls, 2)
            provider.assert_not_called()
            self.assertTrue(plan_path.exists())

    def test_stale_bound_repair_prints_fresh_opaque_command_in_text_mode(self) -> None:
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
            committed = build_state_after_apply(
                verified,
                applied_at="2026-08-16T12:00:00+00:00",
            )
            save_applied_state(committed, state_root=state_root)
            current = manual_card(namespace)
            snapshot = classify_remote_catalog(
                live_namespace_ids=(REMOTE_CATALOG_NAMESPACE, namespace),
                cards=(current,),
                compatibility=CompatibilityContract(
                    region=REGION,
                    embedding_model=MODEL,
                    embedding_precision="float32",
                ),
                catalog_schema_version=REMOTE_SCHEMA_V3,
            )
            stale_command = apply_module._catalog_repair_command(
                verified,
                namespace=namespace,
                region=REGION,
                apply_id=committed.last_apply_id,
                existing_revision="a" * 64,
            )
            client = FakeClient()
            result, stdout, stderr = run_cli(
                shlex.split(stale_command)[1:],
                patches=(
                    patch.object(
                        apply_module,
                        "REMOTE_CATALOG_CLIENT_FACTORY",
                        return_value=client,
                    ),
                    patch.object(
                        apply_module,
                        "read_remote_catalog",
                        return_value=snapshot,
                    ),
                    patch.object(
                        apply_module,
                        "create_remote_cards",
                        side_effect=AssertionError("stale repair created a card"),
                    ),
                    patch.object(
                        apply_module,
                        "update_remote_card",
                        side_effect=AssertionError("stale repair updated a card"),
                    ),
                    patch(
                        "buoy_search.catalog.load_routing_embedder",
                        return_value=FixedRoutingEmbedder(),
                    ),
                    patch(
                        "buoy_search.plan_cleanup.cleanup_applied_plan_directory",
                        side_effect=AssertionError("stale repair cleaned its plan"),
                    ),
                ),
            )

            self.assertEqual((result, stdout), (2, ""))
            self.assertIn("Repair with: buoy catalog repair-apply", stderr)
            self.assertIn(current.card_revision, stderr)
            self.assertIn("--approve", stderr)
            for prototype in artifacts.routing_prototypes:
                self.assertNotIn(prototype["passage_text"], stderr)
            self.assertTrue(plan_path.exists())
            self.assertEqual(client.namespace_calls, [])

    def test_repair_diagnostics_never_render_source_passages_or_control_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            verified = load_verified_apply_plan(
                plan_path=plan_path,
                namespace=artifacts.manifest.namespace,
                state_root=state_root,
            )
            secret = "\x1b]8;;https://attacker.invalid\x07SECRET-PASSAGE\x1b]8;;\x07"
            tainted = replace(
                verified,
                routing_prototypes=({"passage_text": secret},),
            )
            command = apply_module._catalog_repair_command(
                tainted,
                namespace=artifacts.manifest.namespace,
                region=REGION,
                apply_id="apply_current",
            )

        self.assertNotIn("SECRET-PASSAGE", command)
        self.assertNotIn("\x1b", command)
        self.assertIn("catalog repair-apply", command)
        with self.assertRaisesRegex(ApplyPlanError, "control characters"):
            load_verified_apply_plan(
                plan_path=Path("unsafe\nplan.json"),
                namespace=None,
                state_root=Path(".buoy"),
            )

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
            with patch(
                "buoy_search.catalog.load_routing_embedder",
                return_value=FixedRoutingEmbedder(),
            ):
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
                        catalog_schema_version=REMOTE_SCHEMA_V3,
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
                    self.assertFalse(result["automatic_retrieval_ready"])
                    self.assertEqual(result["automatic_routing_status"], "disabled")
                    self.assertEqual(client.namespace_calls, [REMOTE_CATALOG_NAMESPACE])
                    if label == "update":
                        self.assertEqual(
                            mutation.call_args.kwargs["expected_revision"],
                            existing.card_revision,
                        )
                    self.assertEqual(
                        mutation.call_args.kwargs["schema_version"],
                        REMOTE_SCHEMA_V3,
                    )

    def test_generated_v3_registration_preserves_reviewed_examples_and_publishes_passages(self) -> None:
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
            existing = generated_card(namespace)
            snapshot = classify_remote_catalog(
                live_namespace_ids=(REMOTE_CATALOG_NAMESPACE, namespace),
                cards=(existing,),
                compatibility=CompatibilityContract(
                    region=REGION,
                    embedding_model=MODEL,
                    embedding_precision="float32",
                ),
                catalog_schema_version=REMOTE_SCHEMA_V3,
            )
            client = FakeClient()
            updated_cards = []

            def update(_resource, card, **_kwargs):  # noqa: ANN001, ANN003, ANN202
                updated_cards.append(card)
                return MutationResult(
                    True,
                    card,
                    1,
                    (remote_card_id(namespace),),
                    MutationMetrics(1, 2, ()),
                )

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
                "update_remote_card",
                side_effect=update,
            ), patch(
                "buoy_search.catalog.load_routing_embedder",
                return_value=FixedRoutingEmbedder(),
            ):
                result = register_apply_catalog_card(
                    verified,
                    config=RuntimeConfig(region=REGION, namespace=namespace),
                    namespace=namespace,
                    apply_id="apply_current",
                    api_key="test-key",
                )

        self.assertEqual(result["catalog_mutation_status"], "updated")
        self.assertFalse(result["catalog_manual_semantics_preserved"])
        self.assertEqual(len(updated_cards), 1)
        updated = updated_cards[0]
        self.assertEqual(updated.semantic_origin, "generated")
        self.assertEqual(updated.routing_examples, existing.routing_examples)
        self.assertEqual(
            updated.routing_passages,
            [prototype["passage_text"] for prototype in verified.routing_prototypes],
        )
        self.assertLessEqual(
            len(updated.routing_examples) + len(updated.routing_passages),
            MAX_ROUTING_EVIDENCE,
        )
        self.assertNotEqual(updated.title, existing.title)
        self.assertNotEqual(updated.routing_prototype_hash, existing.routing_prototype_hash)
        self.assertEqual(updated.source_uri, artifacts.plan.source["uri"])
        self.assertEqual(updated.site_id, artifacts.plan.site_id)
        self.assertEqual(updated.last_plan_id, artifacts.plan.plan_id)
        self.assertEqual(updated.last_apply_id, "apply_current")

    def test_unchanged_routing_profile_reuses_projection_without_model_work(self) -> None:
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
            with patch(
                "buoy_search.catalog.load_routing_embedder",
                return_value=FixedRoutingEmbedder(),
            ):
                existing = generated_card_for_apply(
                    verified,
                    namespace=namespace,
                    region=REGION,
                    apply_id="apply_previous",
                    existing=None,
                )
            snapshot = classify_remote_catalog(
                live_namespace_ids=(REMOTE_CATALOG_NAMESPACE, namespace),
                cards=(existing,),
                compatibility=CompatibilityContract(
                    region=REGION,
                    embedding_model=MODEL,
                    embedding_precision="float32",
                ),
                catalog_schema_version=REMOTE_SCHEMA_V3,
            )
            updated_cards = []

            def update(_resource, card, **_kwargs):  # noqa: ANN001, ANN003, ANN202
                updated_cards.append(card)
                return MutationResult(
                    True,
                    card,
                    1,
                    (remote_card_id(namespace),),
                    MutationMetrics(1, 2, ()),
                )

            with patch.object(
                apply_module,
                "REMOTE_CATALOG_CLIENT_FACTORY",
                return_value=FakeClient(),
            ), patch.object(
                apply_module,
                "read_remote_catalog",
                return_value=snapshot,
            ), patch.object(
                apply_module,
                "update_remote_card",
                side_effect=update,
            ), patch(
                "buoy_search.catalog.load_routing_embedder",
                side_effect=AssertionError("unchanged routing profile was re-embedded"),
            ):
                result = register_apply_catalog_card(
                    verified,
                    config=RuntimeConfig(region=REGION, namespace=namespace),
                    namespace=namespace,
                    apply_id="apply_current",
                    api_key="test-key",
                )

        self.assertTrue(result["routing_projection_reused"])
        self.assertEqual(result["routing_embeddings_generated"], 0)
        self.assertTrue(result["automatic_retrieval_ready"])
        self.assertEqual(result["automatic_routing_status"], "provisional_ready")
        self.assertEqual(len(updated_cards), 1)
        self.assertEqual(
            updated_cards[0].routing_prototype_vector,
            existing.routing_prototype_vector,
        )
        self.assertEqual(
            updated_cards[0].routing_prototype_vector_hash,
            existing.routing_prototype_vector_hash,
        )

    def test_missing_catalog_fails_without_schema_or_card_mutation(self) -> None:
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
                side_effect=RemoteCatalogMissingError("missing"),
            ) as read, patch.object(
                apply_module,
                "create_remote_cards",
                side_effect=AssertionError("missing catalog attempted card write"),
            ), patch(
                "buoy_search.catalog.load_routing_embedder",
                side_effect=AssertionError("missing catalog loaded routing model"),
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

        self.assertEqual(read.call_count, 1)
        self.assertIn("missing", str(raised.exception))
        repair = shlex.split(raised.exception.repair_command)
        self.assertEqual(repair[:3], ["buoy", "catalog", "repair-apply"])
        self.assertIn("--inspect-current", repair)
        self.assertNotIn("--approve", repair)
        self.assertNotIn("--expect-absent", repair)
        self.assertNotIn("--expected-card-revision", repair)

    def test_schema_v2_passage_registration_fails_before_remote_write(self) -> None:
        class NeverWriteResource:
            def write(self, **_kwargs):  # noqa: ANN003, ANN201
                raise AssertionError("schema-v2 passage registration attempted a write")

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
            snapshot = classify_remote_catalog(
                live_namespace_ids=(REMOTE_CATALOG_NAMESPACE, namespace),
                cards=(),
                compatibility=CompatibilityContract(
                    region=REGION,
                    embedding_model=MODEL,
                    embedding_precision="float32",
                ),
                catalog_schema_version=REMOTE_SCHEMA_V2,
            )
            client = FakeClient()
            client.resource = NeverWriteResource()

            with patch.object(
                apply_module,
                "REMOTE_CATALOG_CLIENT_FACTORY",
                return_value=client,
            ), patch.object(
                apply_module,
                "read_remote_catalog",
                return_value=snapshot,
            ), patch(
                "buoy_search.catalog.load_routing_embedder",
                side_effect=AssertionError("schema-v2 registration loaded model"),
            ) as model:
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

        self.assertIn("schema-v3 migration", str(raised.exception))
        repair = shlex.split(raised.exception.repair_command)
        self.assertEqual(repair[:3], ["buoy", "catalog", "repair-apply"])
        self.assertIn("--inspect-current", repair)
        self.assertNotIn("--approve", repair)
        self.assertNotIn("--expect-absent", repair)
        self.assertNotIn("--expected-card-revision", repair)
        model.assert_not_called()

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

        repair = shlex.split(raised.exception.repair_command)
        self.assertEqual(repair[:3], ["buoy", "catalog", "repair-apply"])
        self.assertIn("--inspect-current", repair)
        self.assertNotIn("--approve", repair)
        self.assertNotIn("--expect-absent", repair)
        self.assertNotIn("--expected-card-revision", repair)
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
                catalog_schema_version=REMOTE_SCHEMA_V3,
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
        self.assertIn("buoy catalog repair-apply", raised.exception.repair_command)
        self.assertIn("--expected-card-revision", raised.exception.repair_command)
        self.assertNotIn("operator routing policy", raised.exception.repair_command)
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
                    repair_command="buoy catalog repair-apply --plan retained/plan.json --approve",
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
        self.assertIn("buoy catalog repair-apply", summary["catalog_repair_command"])
        self.assertEqual(state.last_apply_id, summary["apply_id"])
        self.assertEqual(len(FakeWriter.rows), len(artifacts.manifest.chunks))
        self.assertEqual(len(cleanup_bindings), 1)


if __name__ == "__main__":
    unittest.main()
