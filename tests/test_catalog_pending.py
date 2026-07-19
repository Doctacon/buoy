from __future__ import annotations

from contextlib import contextmanager, nullcontext, redirect_stderr, redirect_stdout
from dataclasses import replace
from io import StringIO
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from buoy_search.applied_state import load_applied_state
from buoy_search.catalog import (
    CardFields,
    NamespaceCard,
    card_revision,
    card_to_dict,
    catalog_revision,
    parse_card,
    prepare_card,
)
import buoy_search.catalog_pending as pending_module
from buoy_search.catalog_pending import load_pending
from buoy_search.cli import main, print_apply_text
from buoy_search.remote_catalog import (
    REMOTE_CATALOG_NAMESPACE,
    CatalogCounts,
    MutationResult,
    ReadMetrics,
    RemoteCatalogError,
    RemoteCatalogSnapshot,
    remote_card_id,
)
from tests.test_apply_cli import (
    FakeEmbedder,
    FakeWriter,
    FixedRoutingEmbedder,
    build_saved_plan,
    reset_fakes,
)


REGION = "gcp-us-east4"


def run_cli(args: list[str], *, env: dict[str, str] | None = None) -> tuple[int, str, str]:
    stdout = StringIO()
    stderr = StringIO()
    with patch.dict(os.environ, env or {}, clear=True), redirect_stdout(stdout), redirect_stderr(stderr):
        result = main(args)
    return result, stdout.getvalue(), stderr.getvalue()


def approved_args(plan_path: Path, state_root: Path) -> list[str]:
    return [
        "apply", "--approve", "--plan", str(plan_path),
        "--state-root", str(state_root), "--region", REGION, "--json",
    ]


def card_fields(card: NamespaceCard, **changes: object) -> CardFields:
    values: dict[str, object] = {
        "namespace": card.namespace,
        "enabled": card.enabled,
        "source_kind": card.source_kind,
        "source_uri": card.source_uri,
        "site_id": card.site_id,
        "title": card.title,
        "summary": card.summary,
        "aliases": list(card.aliases),
        "tags": list(card.tags),
        "semantic_origin": card.semantic_origin,
        "region": card.region,
        "embedding_model": card.embedding_model,
        "embedding_precision": card.embedding_precision,
        "plan_schema_version": card.plan_schema_version,
        "ranking_mode": card.ranking_mode,
        "ranking_profile": card.ranking_profile,
        "ranking_pool": card.ranking_pool,
        "ranking_aggregation": card.ranking_aggregation,
        "last_plan_id": card.last_plan_id,
        "last_apply_id": card.last_apply_id,
    }
    values.update(changes)
    return CardFields(**values)  # type: ignore[arg-type]


def revised_card(card: NamespaceCard, **changes: object) -> NamespaceCard:
    revised = prepare_card(
        card_fields(card, **changes),
        embedder=FixedRoutingEmbedder(),
        now="2026-07-18T12:00:00+00:00",
    )
    revised = replace(revised, created_at=card.created_at, card_revision="pending")
    return replace(revised, card_revision=card_revision(revised))


class FakeRemoteCatalog:
    def __init__(self) -> None:
        self.cards: list[NamespaceCard] = []
        self.client = SimpleNamespace(namespace=self.namespace)
        self.resource = object()
        self.create_error: Exception | None = None
        self.update_error: Exception | None = None
        self.create_calls: list[NamespaceCard] = []
        self.update_calls: list[tuple[NamespaceCard, str]] = []
        self.strong_reads = 0
        self.strong_read_cards: tuple[NamespaceCard | None, NamespaceCard | None] | None = None
        self.snapshot_calls = 0
        self.snapshot_error_on_call: int | None = None

    def namespace(self, name: str) -> object:
        if name != REMOTE_CATALOG_NAMESPACE:
            raise AssertionError(f"unexpected remote namespace {name}")
        return self.resource

    def snapshot(self, client, *, region: str, compatibility) -> RemoteCatalogSnapshot:  # noqa: ANN001
        if client is not self.client or region != REGION:
            raise AssertionError("unexpected fake remote binding")
        del compatibility
        self.snapshot_calls += 1
        if self.snapshot_error_on_call == self.snapshot_calls:
            raise RemoteCatalogError("simulated full catalog snapshot failure")
        live = tuple(sorted(card.namespace for card in self.cards))
        return RemoteCatalogSnapshot(
            cards=tuple(self.cards),
            eligible_cards=tuple(card for card in self.cards if card.enabled),
            live_namespace_ids=live,
            missing_card_ids=(),
            stale_target_ids=(),
            disabled_ids=tuple(card.namespace for card in self.cards if not card.enabled),
            incompatible_ids=(),
            snapshot_revision=catalog_revision(self.cards),
            counts=CatalogCounts(
                listed_total=1 + len(live), control_plane_count=1,
                content_live_count=len(live), card_count=len(self.cards),
                stale_target_count=0, missing_card_count=0,
                disabled_count=sum(not card.enabled for card in self.cards),
                incompatible_count=0, eligible_count=sum(card.enabled for card in self.cards),
            ),
            metrics=ReadMetrics(2, 1, 2, ()),
        )

    def create(self, resource, cards, *, region: str) -> MutationResult:  # noqa: ANN001
        if resource is not self.resource or region != REGION:
            raise AssertionError("unexpected fake create binding")
        card = cards[0]
        self.create_calls.append(card)
        if self.create_error:
            raise self.create_error
        if any(current.namespace == card.namespace for current in self.cards):
            raise RemoteCatalogError("conditional card create conflicted with current remote state")
        self.cards.append(card)
        return MutationResult(True, card, 1, (remote_card_id(card.namespace),))

    def update(self, resource, card, *, expected_revision: str, region: str) -> MutationResult:  # noqa: ANN001
        if resource is not self.resource or region != REGION:
            raise AssertionError("unexpected fake update binding")
        self.update_calls.append((card, expected_revision))
        if self.update_error:
            raise self.update_error
        current = next((item for item in self.cards if item.namespace == card.namespace), None)
        if current is None or current.card_revision != expected_revision:
            raise RemoteCatalogError("conditional card update conflicted with a newer remote revision")
        self.cards = [item for item in self.cards if item.namespace != card.namespace] + [card]
        return MutationResult(True, card, 1, (remote_card_id(card.namespace),))

    def read_twice(
        self, resource, *, namespace: str, region: str, preserve_reads: bool = False,
    ) -> tuple[NamespaceCard, ...]:  # noqa: ANN001
        if resource is not self.resource or region != REGION:
            raise AssertionError("unexpected fake read binding")
        self.strong_reads += 2
        card = next((item for item in self.cards if item.namespace == namespace), None)
        reads = self.strong_read_cards or (card, card)
        if preserve_reads:
            return tuple(value for value in reads if value is not None)
        return (reads[0],) if reads[0] is not None else ()


class CatalogPendingIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_fakes()
        self.remote = FakeRemoteCatalog()
        patchers = [
            patch("buoy_search.catalog.load_routing_embedder", return_value=FixedRoutingEmbedder()),
            patch("buoy_search.catalog_cli.load_routing_embedder", return_value=FixedRoutingEmbedder()),
            patch("buoy_search.apply.REMOTE_CATALOG_CLIENT_FACTORY", return_value=self.remote.client),
            patch("buoy_search.apply.read_remote_catalog", side_effect=self.remote.snapshot),
            patch("buoy_search.apply.create_remote_cards", side_effect=self.remote.create),
            patch("buoy_search.apply.update_remote_card", side_effect=self.remote.update),
            patch("buoy_search.catalog_cli.REMOTE_CATALOG_CLIENT_FACTORY", return_value=self.remote.client),
            patch("buoy_search.catalog_pending.read_remote_card_twice", side_effect=self.remote.read_twice),
            patch("buoy_search.catalog_pending.read_remote_catalog", side_effect=self.remote.snapshot),
            patch("buoy_search.catalog_pending.create_remote_cards", side_effect=self.remote.create),
            patch("buoy_search.catalog_pending.update_remote_card", side_effect=self.remote.update),
            patch("buoy_search.remote_catalog.create_client", side_effect=AssertionError("real SDK factory used")),
        ]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def apply(self, plan_path: Path, state_root: Path) -> tuple[int, str, str]:
        with patch("buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder), patch(
            "buoy_search.apply.TurbopufferWriter", FakeWriter
        ):
            return run_cli(
                approved_args(plan_path, state_root),
                env={"TURBOPUFFER_API_KEY": "fake-secret"},
            )

    def make_confirmed_pending(
        self,
        root: Path,
        *,
        existing: NamespaceCard | None = None,
    ) -> tuple[Path, dict[str, object]]:
        state_root = root / "state"
        artifacts, plan_path = build_saved_plan(root, state_root=state_root)
        if existing:
            self.remote.cards = [existing]
            self.remote.update_error = RemoteCatalogError("simulated catalog update conflict")
        else:
            self.remote.create_error = RemoteCatalogError("simulated catalog create conflict")
        result, stdout, stderr = self.apply(plan_path, state_root)
        self.assertEqual(result, 2, (stdout, stderr))
        output = json.loads(stdout)
        self.assertFalse(output["catalog_updated"])
        path = Path(output["pending_path"])
        payload = load_pending(path)
        state = load_applied_state(
            site_id=str(payload["site_id"]), namespace=str(payload["namespace"]),
            base_url=str(payload["base_url"]), state_root=Path(payload["state_root"]),
        )
        self.assertTrue(payload["remote_apply_confirmed"])
        self.assertEqual(payload["plan_id"], artifacts.plan.plan_id)
        self.assertEqual(payload["intended_state_hash"], pending_module.applied_state_hash(state))
        self.remote.create_error = None
        self.remote.update_error = None
        return path, payload

    def reconcile(self, path: Path, *options: str) -> tuple[int, str, str]:
        return run_cli([
            "catalog", "reconcile", "--pending", str(path),
            *options, "--region", REGION, "--json",
        ], env={"TURBOPUFFER_API_KEY": "fake-secret"})

    def test_preview_reports_unknown_remote_state_without_model_credentials_or_api(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            _artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            with patch("buoy_search.catalog.load_routing_embedder", side_effect=AssertionError("model")), patch(
                "buoy_search.apply.REMOTE_CATALOG_CLIENT_FACTORY", side_effect=AssertionError("api")
            ), patch("buoy_search.apply.SentenceTransformerEmbedder", side_effect=AssertionError("content model")):
                result, stdout, stderr = run_cli([
                    "apply", "--dry-run", "--plan", str(plan_path), "--state-root", str(state_root),
                    "--region", REGION, "--json",
                ])
            payload = json.loads(stdout)

        self.assertEqual((result, stderr), (0, ""))
        self.assertEqual(payload["catalog_registration"]["remote_catalog_state"], "unknown_until_approved")
        self.assertFalse((state_root / "catalog-pending").exists())

    def test_approved_create_confirms_canonical_private_pending_then_cleans_up(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            captured: dict[str, object] = {}
            real_confirm = pending_module.confirm_pending

            def inspect_confirm(path: Path, payload: dict[str, object], *, apply_id: str):
                result = real_confirm(path, payload, apply_id=apply_id)
                captured.update(result)
                captured["mode"] = path.stat().st_mode & 0o777
                captured["path"] = str(path)
                return result

            with patch("buoy_search.apply.confirm_pending", side_effect=inspect_confirm):
                result, stdout, stderr = self.apply(plan_path, state_root)
            output = json.loads(stdout)
            expected_path = pending_module.pending_path_for_plan(state_root, artifacts.plan.plan_id)
            pending_cleaned = not expected_path.exists()

        self.assertEqual((result, stderr), (0, ""))
        self.assertEqual(captured["path"], str(expected_path))
        self.assertEqual(captured["mode"], 0o600)
        self.assertEqual(captured["catalog_namespace"], REMOTE_CATALOG_NAMESPACE)
        self.assertEqual(captured["state_root"], str(state_root.resolve()))
        self.assertEqual(captured["plan_id"], output["plan_id"])
        self.assertEqual(captured["apply_id"], self.remote.cards[0].last_apply_id)
        self.assertEqual(len(self.remote.create_calls), 1)
        self.assertTrue(pending_cleaned)

    def test_verified_apply_mutation_snapshot_failure_reports_committed_revision_and_retains_pending(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            self.remote.snapshot_error_on_call = 2
            result, stdout, stderr = self.apply(plan_path, state_root)
            output = json.loads(stdout)
            pending_path = Path(output["pending_path"])
            pending = load_pending(pending_path)
            pending_retained = pending_path.exists()
            text = StringIO()
            with redirect_stdout(text):
                print_apply_text(output)

        self.assertEqual((result, stderr), (2, ""))
        self.assertTrue(output["catalog_updated"])
        self.assertFalse(output["catalog_snapshot_complete"])
        self.assertFalse(output["pending_cleanup"])
        self.assertIsNone(output["snapshot_revision"])
        self.assertEqual(output["card_revision"], self.remote.cards[0].card_revision)
        self.assertEqual(output["catalog_repair_command"], f"buoy catalog reconcile --pending {pending_path}")
        self.assertTrue(pending["remote_apply_confirmed"])
        self.assertTrue(pending_retained)
        self.assertEqual(len(FakeWriter.rows), output["rows_upserted"])
        self.assertNotIn("fake-secret", stdout)
        self.assertNotIn(artifacts.manifest.chunks[0].content, stdout)
        self.assertNotIn('"vector"', stdout)
        self.assertIn(f"committed_card_revision: {output['card_revision']}", text.getvalue())
        self.assertIn("catalog_snapshot: incomplete", text.getvalue())
        self.assertIn(output["catalog_repair_command"], text.getvalue())

    def test_verified_apply_mutation_cleanup_failure_reports_stable_snapshot_and_retains_pending(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            _artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            with patch("buoy_search.apply.remove_expected_pending", side_effect=OSError("cleanup denied")):
                result, stdout, stderr = self.apply(plan_path, state_root)
            output = json.loads(stdout)
            pending_path = Path(output["pending_path"])
            pending_retained = pending_path.exists()

        self.assertEqual((result, stderr), (2, ""))
        self.assertTrue(output["catalog_updated"])
        self.assertTrue(output["catalog_snapshot_complete"])
        self.assertFalse(output["pending_cleanup"])
        self.assertEqual(output["snapshot_revision"], catalog_revision(self.remote.cards))
        self.assertEqual(output["card_revision"], self.remote.cards[0].card_revision)
        self.assertTrue(pending_retained)

    def test_approved_update_preserves_manual_semantics_and_disabled_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            prospective = prepare_card(CardFields(
                namespace=artifacts.manifest.namespace, enabled=False,
                source_kind="website", source_uri=artifacts.manifest.base_url,
                site_id=artifacts.manifest.site_id, title="Curated", summary="Manual summary",
                aliases=["manual"], tags=["curated"], semantic_origin="manual", region=REGION,
                embedding_model=artifacts.plan.embedding_model,
                embedding_precision=artifacts.plan.embedding_precision,
                plan_schema_version=1, ranking_mode="page", ranking_profile="none",
                ranking_pool=20, ranking_aggregation="max", last_plan_id="old-plan",
                last_apply_id="old-apply",
            ), embedder=FixedRoutingEmbedder())
            self.remote.cards = [prospective]
            result, stdout, stderr = self.apply(plan_path, state_root)
            output = json.loads(stdout)
            updated = self.remote.cards[0]

        self.assertEqual((result, stderr), (0, ""))
        self.assertFalse(updated.enabled)
        self.assertEqual((updated.title, updated.summary, updated.aliases, updated.tags), (
            prospective.title, prospective.summary, prospective.aliases, prospective.tags,
        ))
        self.assertEqual(self.remote.update_calls[0][1], prospective.card_revision)
        self.assertEqual(updated.last_plan_id, output["plan_id"])
        self.assertIsNotNone(updated.last_apply_id)

    def test_content_failure_retains_unconfirmed_secret_free_pending_and_blocks_replay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            FakeWriter.should_fail = True
            result, stdout, stderr = self.apply(plan_path, state_root)
            pending_path = next((state_root.resolve() / "catalog-pending").glob("*.json"))
            text = pending_path.read_text(encoding="utf-8")
            payload = load_pending(pending_path)
            reset_fakes()
            rerun, rerun_stdout, rerun_stderr = self.apply(plan_path, state_root)

        self.assertEqual((result, stdout), (2, ""))
        self.assertIn("fake upsert failure", stderr)
        self.assertFalse(payload["remote_apply_confirmed"])
        self.assertIsNone(payload["apply_id"])
        self.assertNotIn("fake-secret", text)
        self.assertNotIn(artifacts.manifest.chunks[0].content, text)
        self.assertEqual((rerun, rerun_stdout), (2, ""))
        self.assertIn("indeterminate", rerun_stderr)
        self.assertEqual(FakeWriter.rows, [])

    def test_abandon_preview_and_approval_are_api_free_with_null_zero_common_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            FakeWriter.should_fail = True
            failed, _stdout, _stderr = self.apply(plan_path, state_root)
            pending_path = next((state_root.resolve() / "catalog-pending").glob("*.json"))
            reset_fakes()
            with patch(
                "buoy_search.catalog_cli.REMOTE_CATALOG_CLIENT_FACTORY",
                side_effect=AssertionError("abandon contacted remote"),
            ):
                preview_result, preview_stdout, preview_stderr = run_cli([
                    "catalog", "abandon-pending", "--pending", str(pending_path),
                    "--region", REGION, "--json",
                ])
                approved_result, approved_stdout, approved_stderr = run_cli([
                    "catalog", "abandon-pending", "--pending", str(pending_path),
                    "--approve", "--region", REGION, "--json",
                ])
            preview = json.loads(preview_stdout)
            approved = json.loads(approved_stdout)
            pending_removed = not pending_path.exists()

        self.assertEqual(failed, 2)
        self.assertEqual((preview_result, preview_stderr), (0, ""))
        self.assertEqual((approved_result, approved_stderr), (0, ""))
        for output in (preview, approved):
            self.assertEqual(output["catalog_namespace"], REMOTE_CATALOG_NAMESPACE)
            self.assertEqual(output["region"], REGION)
            self.assertIsNone(output["snapshot_revision"])
            self.assertIsNone(output["counts"])
            self.assertEqual(output["remote_state"], "not_read")
            self.assertEqual(output["read_metrics"], {
                "namespace_list_pages": 0, "metadata_requests": 0,
                "card_query_pages": 0, "billing": [],
            })
            self.assertEqual(output["request_summary"]["total_requests"], 0)
            self.assertEqual(output["request_summary"]["billing"], [])
            self.assertNotIn("fake-secret", json.dumps(output))
            self.assertNotIn(artifacts.manifest.chunks[0].content, json.dumps(output))
        self.assertFalse(preview["approved"])
        self.assertTrue(approved["approved"])
        self.assertTrue(pending_removed)

    def test_confirmed_pending_cannot_be_abandoned_without_remote_access(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path, _payload = self.make_confirmed_pending(Path(tmp))
            with patch(
                "buoy_search.catalog_cli.REMOTE_CATALOG_CLIENT_FACTORY",
                side_effect=AssertionError("abandon contacted remote"),
            ):
                result, stdout, stderr = run_cli([
                    "catalog", "abandon-pending", "--pending", str(path),
                    "--approve", "--region", REGION, "--json",
                ])
            pending_retained = path.exists()

        self.assertEqual((result, stdout), (2, ""))
        self.assertIn("must be reconciled", stderr)
        self.assertTrue(pending_retained)

    def test_catalog_failure_retains_confirmed_pending_and_ordinary_recovery_replays_no_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, payload = self.make_confirmed_pending(root)
            writes = len(FakeWriter.rows)
            pre_operation_revision = catalog_revision(self.remote.cards)
            result, stdout, stderr = self.reconcile(path)
            output = json.loads(stdout)
            pending_cleaned = not path.exists()

        self.assertEqual((result, stderr), (0, ""))
        self.assertEqual(output["action"], "committed")
        self.assertFalse(output["content_replayed"])
        self.assertEqual(len(FakeWriter.rows), writes)
        self.assertTrue(pending_cleaned)
        self.assertTrue(output["pending_cleanup"])
        self.assertTrue(output["catalog_snapshot_complete"])
        self.assertNotEqual(output["snapshot_revision"], pre_operation_revision)
        self.assertEqual(output["snapshot_revision"], catalog_revision(self.remote.cards))
        self.assertEqual(output["card_revision"], self.remote.cards[0].card_revision)
        self.assertEqual(output["affected_ids"], [remote_card_id(self.remote.cards[0].namespace)])
        self.assertEqual(output["read_metrics"]["namespace_list_pages"], 2)
        self.assertEqual(output["request_summary"]["precondition_verification_query_requests"], 2)
        self.assertEqual(output["request_summary"]["total_requests"], 7)
        self.assertTrue(output["request_summary"]["complete"])
        self.assertEqual(output["request_summary"]["billing"], [])
        self.assertTrue(output["request_summary"]["billing_complete"])
        self.assertEqual(self.remote.cards[0].last_apply_id, payload["apply_id"])

    def test_reconcile_snapshot_failure_after_verified_mutation_is_truthful_and_replay_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, _payload = self.make_confirmed_pending(root)
            writes = len(FakeWriter.rows)
            self.remote.snapshot_error_on_call = self.remote.snapshot_calls + 1
            result, stdout, stderr = self.reconcile(path)
            output = json.loads(stdout)
            pending_retained = path.exists()

        self.assertEqual((result, stderr), (2, ""))
        self.assertEqual(output["action"], "committed")
        self.assertTrue(output["catalog_updated"])
        self.assertFalse(output["catalog_snapshot_complete"])
        self.assertIsNone(output["snapshot_revision"])
        self.assertFalse(output["pending_cleanup"])
        self.assertEqual(output["card_revision"], self.remote.cards[0].card_revision)
        self.assertEqual(output["catalog_repair_command"], f"buoy catalog reconcile --pending {path}")
        self.assertFalse(output["content_replayed"])
        self.assertEqual(len(FakeWriter.rows), writes)
        self.assertTrue(pending_retained)
        self.assertNotIn("fake-secret", stdout)
        self.assertNotIn('"vector"', stdout)

    def test_reconcile_snapshot_failure_marks_request_accounting_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path, _payload = self.make_confirmed_pending(Path(tmp))
            self.remote.snapshot_error_on_call = self.remote.snapshot_calls + 1
            result, stdout, stderr = self.reconcile(path)
            output = json.loads(stdout)
            pending_retained = path.exists()

        self.assertEqual((result, stderr), (2, ""))
        self.assertEqual(output["read_metrics"], {
            "namespace_list_pages": None, "metadata_requests": None,
            "card_query_pages": None, "billing": [],
        })
        self.assertEqual(set(output["request_summary"]), {
            "namespace_list_requests", "metadata_requests", "catalog_page_query_requests",
            "precondition_verification_query_requests", "mutation_verification_query_requests",
            "write_requests", "total_requests", "complete", "billing", "billing_complete",
        })
        self.assertEqual(output["request_summary"]["precondition_verification_query_requests"], 2)
        self.assertIsNone(output["request_summary"]["total_requests"])
        self.assertFalse(output["request_summary"]["complete"])
        self.assertFalse(output["request_summary"]["billing_complete"])
        self.assertTrue(pending_retained)

    def test_reconcile_missing_verified_card_uses_completed_snapshot_accounting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path, _payload = self.make_confirmed_pending(Path(tmp))

            def snapshot_without_card(client, *, region: str, compatibility):  # noqa: ANN001
                snapshot = self.remote.snapshot(client, region=region, compatibility=compatibility)
                return replace(snapshot, cards=(), eligible_cards=())

            with patch(
                "buoy_search.catalog_pending.read_remote_catalog",
                side_effect=snapshot_without_card,
            ):
                result, stdout, stderr = self.reconcile(path)
            output = json.loads(stdout)
            pending_retained = path.exists()

        self.assertEqual((result, stderr), (2, ""))
        self.assertTrue(output["catalog_snapshot_complete"])
        self.assertEqual(output["read_metrics"], {
            "namespace_list_pages": 2, "metadata_requests": 1,
            "card_query_pages": 2, "billing": [],
        })
        self.assertEqual(set(output["request_summary"]), {
            "namespace_list_requests", "metadata_requests", "catalog_page_query_requests",
            "precondition_verification_query_requests", "mutation_verification_query_requests",
            "write_requests", "total_requests", "complete", "billing", "billing_complete",
        })
        self.assertEqual(output["request_summary"]["total_requests"], 7)
        self.assertTrue(output["request_summary"]["complete"])
        self.assertTrue(output["request_summary"]["billing_complete"])
        self.assertFalse(output["pending_cleanup"])
        self.assertTrue(pending_retained)

    def test_safe_rebase_preserves_concurrent_manual_edit_and_disable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, _ = build_saved_plan(root / "source", state_root=state_root)
            base = prepare_card(CardFields(
                namespace=artifacts.manifest.namespace, enabled=True,
                source_kind="website", source_uri=artifacts.manifest.base_url,
                site_id=artifacts.manifest.site_id, title="Base", summary="Base summary",
                aliases=[], tags=[], semantic_origin="manual", region=REGION,
                embedding_model=artifacts.plan.embedding_model,
                embedding_precision=artifacts.plan.embedding_precision,
                plan_schema_version=1, ranking_mode="page", ranking_profile="none",
                ranking_pool=20, ranking_aggregation="max", last_plan_id="old-plan",
                last_apply_id="old-apply",
            ), embedder=FixedRoutingEmbedder())
            path, _payload = self.make_confirmed_pending(root, existing=base)
            self.remote.cards = [revised_card(
                base, enabled=False, title="Concurrent curation", summary="Edited",
                aliases=["new"], tags=["manual"], semantic_origin="manual",
            )]
            writes = len(FakeWriter.rows)
            result, stdout, stderr = self.reconcile(path, "--rebase", "--approve")
            output = json.loads(stdout)
            card = self.remote.cards[0]

        self.assertEqual((result, stderr), (0, ""))
        self.assertEqual(output["action"], "rebased")
        self.assertEqual((card.enabled, card.title, card.summary), (False, "Concurrent curation", "Edited"))
        self.assertEqual(card.aliases, ["new"])
        self.assertEqual(len(FakeWriter.rows), writes)
        self.assertFalse(output["content_replayed"])

    def test_safe_rebase_rejects_concurrent_system_change_and_retains_pending(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, _ = build_saved_plan(root / "source", state_root=state_root)
            base = prepare_card(CardFields(
                namespace=artifacts.manifest.namespace, enabled=True,
                source_kind="website", source_uri=artifacts.manifest.base_url,
                site_id=artifacts.manifest.site_id, title="Base", summary="Base",
                aliases=[], tags=[], semantic_origin="generated", region=REGION,
                embedding_model=artifacts.plan.embedding_model,
                embedding_precision=artifacts.plan.embedding_precision,
                plan_schema_version=1, ranking_mode="page", ranking_profile="none",
                ranking_pool=20, ranking_aggregation="max", last_plan_id="old-plan",
                last_apply_id="old-apply",
            ))
            path, _payload = self.make_confirmed_pending(root, existing=base)
            self.remote.cards = [revised_card(base, ranking_pool=99)]
            writes = len(FakeWriter.rows)
            result, stdout, stderr = self.reconcile(path, "--rebase", "--approve")
            pending_retained = path.exists()

        self.assertEqual((result, stdout), (2, ""))
        self.assertIn("unsafe concurrent field changes", stderr)
        self.assertTrue(pending_retained)
        self.assertEqual(len(FakeWriter.rows), writes)

    def test_first_apply_manual_race_is_rebase_safe_only_for_matching_system_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, payload = self.make_confirmed_pending(root)
            desired = parse_card(payload["prospective_card"])
            manual = prepare_card(
                card_fields(
                    desired, enabled=False, title="Operator title", summary="Operator summary",
                    aliases=["operator"], tags=["manual"], semantic_origin="manual",
                    last_plan_id=None, last_apply_id=None,
                ),
                embedder=FixedRoutingEmbedder(),
            )
            self.remote.cards = [manual]
            result, stdout, stderr = self.reconcile(path, "--rebase", "--approve")
            merged = self.remote.cards[0]

        self.assertEqual((result, stderr), (0, ""))
        self.assertEqual(json.loads(stdout)["action"], "rebased")
        self.assertEqual((merged.enabled, merged.title), (False, "Operator title"))
        self.assertEqual((merged.last_plan_id, merged.last_apply_id), (
            payload["plan_id"], payload["apply_id"],
        ))

    def test_accept_remote_uses_two_stable_reads_no_write_and_reports_both_identities(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, payload = self.make_confirmed_pending(root)
            desired = parse_card(payload["prospective_card"])
            remote = revised_card(desired, last_plan_id="other-plan", last_apply_id="other-apply")
            self.remote.cards = [remote]
            writes = len(self.remote.create_calls) + len(self.remote.update_calls)
            result, stdout, stderr = self.reconcile(
                path, "--accept-remote", "--approve",
                "--expected-remote-revision", remote.card_revision,
            )
            output = json.loads(stdout)
            pending_cleaned = not path.exists()

        self.assertEqual((result, stderr), (0, ""))
        self.assertEqual(self.remote.strong_reads, 2)
        self.assertEqual(len(self.remote.create_calls) + len(self.remote.update_calls), writes)
        self.assertEqual((output["pending_plan_id"], output["pending_apply_id"]), (
            payload["plan_id"], payload["apply_id"],
        ))
        self.assertEqual((output["remote_plan_id"], output["remote_apply_id"]), (
            "other-plan", "other-apply",
        ))
        self.assertEqual(output["operator_accepted_exact_revision"], remote.card_revision)
        self.assertFalse(output["content_replayed"])
        self.assertTrue(pending_cleaned)

    def test_accept_remote_rejects_a_different_second_strong_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path, payload = self.make_confirmed_pending(Path(tmp))
            desired = parse_card(payload["prospective_card"])
            first = revised_card(desired, last_plan_id="other-plan", last_apply_id="other-apply")
            second = revised_card(first, title="Concurrent operator edit")
            self.remote.cards = [first]
            self.remote.strong_read_cards = (first, second)
            result, stdout, stderr = self.reconcile(
                path, "--accept-remote", "--approve",
                "--expected-remote-revision", first.card_revision,
            )
            pending_retained = path.exists()

        self.assertEqual((result, stdout), (2, ""))
        self.assertIn("accept-remote remote card changed between strong reads", stderr)
        self.assertEqual(self.remote.strong_reads, 2)
        self.assertTrue(pending_retained)

    def test_recovery_modes_require_approval_expected_revision_and_mutual_exclusion(self) -> None:
        cases = [
            (["--rebase"], "require --approve"),
            (["--accept-remote"], "require --approve"),
            (["--accept-remote", "--approve"], "expected-remote-revision"),
            (["--expected-remote-revision", "revision"], "valid only with --accept-remote"),
        ]
        for options, message in cases:
            with self.subTest(options=options), tempfile.TemporaryDirectory() as tmp:
                path, _payload = self.make_confirmed_pending(Path(tmp))
                result, stdout, stderr = self.reconcile(path, *options)
                self.assertEqual((result, stdout), (2, ""))
                self.assertIn(message, stderr)
                self.assertTrue(path.exists())
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
            main([
                "catalog", "reconcile", "--pending", "unused",
                "--rebase", "--accept-remote", "--approve",
            ])

    def test_confirmation_interruption_promotes_from_exact_ledger_without_content_replay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            _artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            real_atomic_write = pending_module._atomic_write
            calls = 0

            def fail_second(path, payload, *, exclusive=False):  # noqa: ANN001
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise pending_module.PendingCatalogError("confirmation interruption")
                return real_atomic_write(path, payload, exclusive=exclusive)

            with patch("buoy_search.catalog_pending._atomic_write", side_effect=fail_second):
                result, stdout, stderr = self.apply(plan_path, state_root)
            self.assertEqual((result, stderr), (2, ""))
            path = Path(json.loads(stdout)["pending_path"])
            self.assertFalse(load_pending(path)["remote_apply_confirmed"])
            writes = len(FakeWriter.rows)
            reconciled, reconcile_stdout, reconcile_stderr = self.reconcile(path)
            pending_cleaned = not path.exists()

        self.assertEqual((reconciled, reconcile_stderr), (0, ""))
        self.assertEqual(json.loads(reconcile_stdout)["action"], "committed")
        self.assertEqual(len(FakeWriter.rows), writes)
        self.assertTrue(pending_cleaned)

    def test_pending_output_and_artifact_redact_credentials_content_and_vectors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, payload = self.make_confirmed_pending(root)
            text = path.read_text(encoding="utf-8")
            self.remote.cards = [parse_card(payload["prospective_card"])]
            result, stdout, stderr = self.reconcile(path)

        self.assertEqual((result, stderr), (0, ""))
        self.assertNotIn("fake-secret", text + stdout + stderr)
        self.assertNotIn("Alpha useful docs", text + stdout)
        self.assertNotIn("\"vector\"", stdout)
        self.assertNotIn("\"prospective_card\"", stdout)

    def test_pending_creation_rejects_symlink_root_without_remote_or_content_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            state_root.mkdir()
            _artifacts, plan_path = build_saved_plan(root / "plan", state_root=state_root)
            outside = root / "outside"
            outside.mkdir()
            (state_root / "catalog-pending").symlink_to(outside, target_is_directory=True)
            result, stdout, stderr = self.apply(plan_path, state_root)
            outside_entries = list(outside.iterdir())

        self.assertEqual((result, stdout), (2, ""))
        self.assertIn("pending root must be a real directory", stderr)
        self.assertEqual(FakeWriter.rows, [])
        self.assertEqual(self.remote.create_calls, [])
        self.assertEqual(outside_entries, [])

    def test_reconcile_rejects_symlink_and_identity_replacement_after_lock(self) -> None:
        for phase in ("symlink", "after-lock"):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                path, _payload = self.make_confirmed_pending(root)
                if phase == "symlink":
                    candidate = root / "pending-link.json"
                    candidate.symlink_to(path)
                    context = nullcontext()
                else:
                    candidate = path

                    @contextmanager
                    def replacing_lock(**_kwargs):
                        replacement = path.with_suffix(".replacement")
                        replacement.write_bytes(path.read_bytes())
                        os.replace(replacement, path)
                        yield

                    context = patch(
                        "buoy_search.catalog_pending.acquire_namespace_apply_lock",
                        replacing_lock,
                    )
                with context:
                    result, stdout, stderr = self.reconcile(candidate)
                self.assertEqual((result, stdout), (2, ""))
                self.assertIn("regular non-symlink" if phase == "symlink" else "replaced", stderr)
                self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
