from __future__ import annotations

from contextlib import contextmanager, redirect_stderr, redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from buoy_search.applied_state import AppliedStateError, load_applied_state
from buoy_search.catalog import (
    ROUTING_DIMENSIONS,
    CardFields,
    CatalogError,
    commit_system_card,
    load_catalog,
    parse_card,
    prepare_card,
    save_catalog,
)
import buoy_search.catalog_pending as pending_module
from buoy_search.catalog_pending import load_pending
from buoy_search.cli import main
from buoy_search.plan_artifacts import stable_hash
from tests.test_apply_cli import FakeEmbedder, FakeWriter, build_saved_plan, reset_fakes


UNIT_VECTOR = [1.0] + [0.0] * (ROUTING_DIMENSIONS - 1)


class FixedRoutingEmbedder:
    def encode(self, texts):
        return [list(UNIT_VECTOR) for _ in texts]


class CredentialSentinel(dict[str, str]):
    def get(self, key: str, default=None):
        if key == "TURBOPUFFER_API_KEY":
            raise AssertionError("credential read")
        return super().get(key, default)


def run_cli(args: list[str], *, env: dict[str, str] | None = None) -> tuple[int, str, str]:
    stdout = StringIO()
    stderr = StringIO()
    with patch.dict(os.environ, env or {}, clear=True), redirect_stdout(stdout), redirect_stderr(stderr):
        result = main(args)
    return result, stdout.getvalue(), stderr.getvalue()


def replace_identically(path: Path) -> None:
    replacement = path.with_name(f".{path.name}.replacement")
    replacement.write_bytes(path.read_bytes())
    os.replace(replacement, path)


def approved_args(plan_path: Path, state_root: Path, catalog_path: Path) -> list[str]:
    return [
        "apply", "--approve", "--plan", str(plan_path),
        "--state-root", str(state_root), "--catalog", str(catalog_path),
        "--region", "gcp-us-east4", "--json",
    ]


class CatalogPendingIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_fakes()
        routing = patch("buoy_search.catalog.load_routing_embedder", return_value=FixedRoutingEmbedder())
        routing.start()
        self.addCleanup(routing.stop)

    def test_successful_apply_commits_catalog_after_state_and_removes_pending(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            catalog_path = root / "catalog.json"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            with patch("buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder), patch(
                "buoy_search.apply.TurbopufferWriter", FakeWriter
            ):
                result, stdout, stderr = run_cli(
                    approved_args(plan_path, state_root, catalog_path),
                    env={"TURBOPUFFER_API_KEY": "fake"},
                )
            payload = json.loads(stdout)
            card = load_catalog(catalog_path).cards[0]
            applied_id = load_applied_state(
                site_id=artifacts.manifest.site_id,
                namespace=artifacts.manifest.namespace,
                base_url=artifacts.manifest.base_url,
                state_root=state_root,
            ).last_apply_id
            pending_root = state_root.resolve() / "catalog-pending"
            pending_files = list(pending_root.glob("*.json"))

        self.assertEqual((result, stderr), (0, ""))
        self.assertTrue(payload["remote_apply_succeeded"])
        self.assertTrue(payload["catalog_updated"])
        self.assertEqual(card.namespace, artifacts.manifest.namespace)
        self.assertEqual(card.region, "gcp-us-east4")
        self.assertEqual((card.last_plan_id, card.last_apply_id), (payload["plan_id"], applied_id))
        self.assertFalse(pending_files)

    def test_remote_failure_leaves_unconfirmed_secret_free_pending_and_rerun_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            catalog_path = root / "catalog.json"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            FakeWriter.should_fail = True
            with patch("buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder), patch(
                "buoy_search.apply.TurbopufferWriter", FakeWriter
            ):
                result, stdout, stderr = run_cli(
                    approved_args(plan_path, state_root, catalog_path),
                    env={"TURBOPUFFER_API_KEY": "super-secret"},
                )
            pending_path = next((state_root.resolve() / "catalog-pending").glob("*.json"))
            pending_text = pending_path.read_text(encoding="utf-8")
            pending = load_pending(pending_path)
            reset_fakes()
            with patch("buoy_search.catalog.load_routing_embedder", side_effect=AssertionError("model")), patch(
                "buoy_search.apply.TurbopufferWriter", side_effect=AssertionError("remote")
            ):
                rerun, rerun_stdout, rerun_stderr = run_cli(
                    approved_args(plan_path, state_root, catalog_path),
                    env={"TURBOPUFFER_API_KEY": "must-not-be-used"},
                )

        self.assertEqual(result, 2)
        self.assertEqual(stdout, "")
        self.assertIn("fake upsert failure", stderr)
        self.assertFalse(pending["remote_apply_confirmed"])
        self.assertIsNone(pending["apply_id"])
        self.assertNotIn("super-secret", pending_text)
        self.assertNotIn(artifacts.manifest.chunks[0].content, pending_text)
        self.assertEqual(rerun, 2)
        self.assertEqual(rerun_stdout, "")
        self.assertIn("remote state is indeterminate", rerun_stderr)
        self.assertEqual(FakeWriter.rows, [])

    def test_missing_credentials_leave_pending_block_rerun_and_require_approved_abandon(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            catalog_path = root / "catalog.json"
            _artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            with patch(
                "buoy_search.apply.TurbopufferWriter",
                side_effect=AssertionError("remote writer constructed"),
            ):
                result, stdout, stderr = run_cli(
                    approved_args(plan_path, state_root, catalog_path), env={}
                )
            pending_path = next((state_root.resolve() / "catalog-pending").glob("*.json"))
            pending = load_pending(pending_path)
            with patch(
                "buoy_search.apply.TurbopufferWriter",
                side_effect=AssertionError("remote writer constructed on rerun"),
            ):
                rerun, rerun_stdout, rerun_stderr = run_cli(
                    approved_args(plan_path, state_root, catalog_path),
                    env={"TURBOPUFFER_API_KEY": "not-used"},
                )
            preview, preview_stdout, preview_stderr = run_cli([
                "catalog", "abandon-pending", "--pending", str(pending_path),
                "--catalog", str(catalog_path), "--json",
            ])
            preview_retained = pending_path.exists()
            abandoned, abandon_stdout, abandon_stderr = run_cli([
                "catalog", "abandon-pending", "--pending", str(pending_path),
                "--catalog", str(catalog_path), "--approve", "--json",
            ])

        self.assertEqual(result, 2)
        self.assertEqual(stdout, "")
        self.assertIn("TURBOPUFFER_API_KEY must be set", stderr)
        self.assertFalse(pending["remote_apply_confirmed"])
        self.assertEqual(rerun, 2)
        self.assertEqual(rerun_stdout, "")
        self.assertIn("remote state is indeterminate", rerun_stderr)
        self.assertEqual((preview, preview_stderr), (0, ""))
        self.assertEqual(json.loads(preview_stdout)["mutation_status"], "preview")
        self.assertTrue(preview_retained)
        self.assertEqual((abandoned, abandon_stderr), (0, ""))
        self.assertEqual(json.loads(abandon_stdout)["mutation_status"], "abandoned")
        self.assertFalse(pending_path.exists())

    def test_lock_contention_precedes_catalog_model_pending_credentials_and_remote(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            catalog_path = root / "catalog.json"
            _artifacts, plan_path = build_saved_plan(root, state_root=state_root)

            @contextmanager
            def contended_lock(**_kwargs):
                raise AppliedStateError("namespace busy")
                yield

            environment = CredentialSentinel({"TURBOPUFFER_API_KEY": "must-not-read"})
            with patch("buoy_search.apply.acquire_namespace_apply_lock", contended_lock), patch(
                "buoy_search.catalog.load_routing_embedder", side_effect=AssertionError("model")
            ), patch("buoy_search.apply.TurbopufferWriter", side_effect=AssertionError("remote")), patch(
                "buoy_search.apply.os.environ", environment
            ):
                result, stdout, stderr = run_cli(
                    approved_args(plan_path, state_root, catalog_path), env=environment
                )
            pending_root = state_root.resolve() / "catalog-pending"

        self.assertEqual(result, 2)
        self.assertEqual(stdout, "")
        self.assertIn("namespace busy", stderr)
        self.assertFalse(pending_root.exists())
        self.assertFalse(catalog_path.exists())

    def test_pending_creation_rejects_symlink_and_non_directory_roots(self) -> None:
        for root_kind in ("symlink", "file"):
            with self.subTest(root_kind=root_kind), tempfile.TemporaryDirectory() as tmp:
                reset_fakes()
                root = Path(tmp)
                state_root = root / "state"
                state_root.mkdir()
                catalog_path = root / "catalog.json"
                _artifacts, plan_path = build_saved_plan(root / "plan-source", state_root=state_root)
                pending_root = state_root.resolve() / "catalog-pending"
                outside = root / "outside"
                if root_kind == "symlink":
                    outside.mkdir()
                    pending_root.symlink_to(outside, target_is_directory=True)
                else:
                    pending_root.write_text("not a directory", encoding="utf-8")
                with patch("buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder), patch(
                    "buoy_search.apply.TurbopufferWriter", FakeWriter
                ):
                    result, stdout, stderr = run_cli(
                        approved_args(plan_path, state_root, catalog_path),
                        env={"TURBOPUFFER_API_KEY": "fake"},
                    )
                outside_entries = list(outside.iterdir()) if outside.exists() else []

                self.assertEqual(result, 2)
                self.assertEqual(stdout, "")
                self.assertIn("pending root must be a real directory", stderr)
                self.assertEqual(FakeWriter.rows, [])
                self.assertEqual(outside_entries, [])

    def test_namespace_lock_lifetime_contains_model_remote_state_and_catalog_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            catalog_path = root / "catalog.json"
            _artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            events: list[str] = []

            @contextmanager
            def tracked_lock(**_kwargs):
                events.append("namespace-enter")
                try:
                    yield
                finally:
                    events.append("namespace-exit")

            class EventRoutingEmbedder:
                def encode(self, texts):
                    self.assert_lock()
                    events.append("catalog-model")
                    return [list(UNIT_VECTOR) for _ in texts]

                @staticmethod
                def assert_lock():
                    if not events or events[-1] == "namespace-exit":
                        raise AssertionError("model outside namespace lock")

            class EventWriter(FakeWriter):
                def __init__(self, **kwargs):
                    events.append("remote-client")
                    super().__init__(**kwargs)

            real_commit = commit_system_card

            def tracked_commit(path, card):
                events.append("catalog-commit")
                return real_commit(path, card)

            with patch("buoy_search.apply.acquire_namespace_apply_lock", tracked_lock), patch(
                "buoy_search.catalog.load_routing_embedder", return_value=EventRoutingEmbedder()
            ), patch("buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder), patch(
                "buoy_search.apply.TurbopufferWriter", EventWriter
            ), patch("buoy_search.apply.commit_system_card", side_effect=tracked_commit):
                result, _stdout, stderr = run_cli(
                    approved_args(plan_path, state_root, catalog_path),
                    env={"TURBOPUFFER_API_KEY": "fake"},
                )

        self.assertEqual((result, stderr), (0, ""))
        self.assertEqual(events[0], "namespace-enter")
        self.assertEqual(events[-1], "namespace-exit")
        self.assertLess(events.index("catalog-model"), events.index("remote-client"))
        self.assertLess(events.index("remote-client"), events.index("catalog-commit"))

    def test_preflight_is_model_credential_remote_and_mutation_free_with_catalog_preview(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            catalog_path = root / "catalog.json"
            _artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            args = approved_args(plan_path, state_root, catalog_path)
            args.remove("--approve")
            environment = CredentialSentinel({"TURBOPUFFER_API_KEY": "must-not-read"})
            with patch("buoy_search.catalog.load_routing_embedder", side_effect=AssertionError("model")), patch(
                "buoy_search.apply.TurbopufferWriter", side_effect=AssertionError("remote")
            ), patch("buoy_search.apply.os.environ", environment):
                result, stdout, stderr = run_cli(args, env=environment)
            payload = json.loads(stdout)

        self.assertEqual((result, stderr), (0, ""))
        self.assertEqual(payload["catalog_registration"]["action"], "new")
        self.assertEqual(payload["catalog_registration"]["region"], "gcp-us-east4")
        self.assertFalse(catalog_path.exists())
        self.assertFalse((state_root / "catalog-pending").exists())

    def test_partial_success_reconciles_locally_without_second_remote_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            catalog_path = root / "catalog.json"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            with patch("buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder), patch(
                "buoy_search.apply.TurbopufferWriter", FakeWriter
            ), patch("buoy_search.apply.commit_system_card", side_effect=CatalogError("disk failure")):
                result, stdout, stderr = run_cli(
                    approved_args(plan_path, state_root, catalog_path),
                    env={"TURBOPUFFER_API_KEY": "fake"},
                )
            partial = json.loads(stdout)
            pending_path = Path(partial["pending_path"])
            pending = load_pending(pending_path)
            plan_retained_after_partial = plan_path.parent.exists()
            writes_after_apply = len(FakeWriter.rows)
            with patch("buoy_search.apply.TurbopufferWriter", side_effect=AssertionError("duplicate remote")):
                blocked, blocked_stdout, blocked_stderr = run_cli(
                    approved_args(plan_path, state_root, catalog_path),
                    env={"TURBOPUFFER_API_KEY": "fake"},
                )
            with patch("buoy_search.apply.TurbopufferWriter", side_effect=AssertionError("remote")):
                reconciled, reconcile_stdout, reconcile_stderr = run_cli([
                    "catalog", "reconcile", "--pending", str(pending_path),
                    "--catalog", str(catalog_path), "--json",
                ])
            card = load_catalog(catalog_path).cards[0]

        self.assertEqual((result, stderr), (2, ""))
        self.assertTrue(partial["remote_apply_succeeded"])
        self.assertFalse(partial["catalog_updated"])
        self.assertEqual(partial["catalog_repair_command"], (
            f"buoy catalog reconcile --pending {pending_path} --catalog {catalog_path.resolve()}"
        ))
        self.assertTrue(pending["remote_apply_confirmed"])
        self.assertEqual(blocked, 2)
        self.assertEqual(blocked_stdout, "")
        self.assertIn("confirmed pending", blocked_stderr)
        self.assertEqual((reconciled, reconcile_stderr), (0, ""))
        self.assertEqual(json.loads(reconcile_stdout)["mutation_status"], "committed")
        self.assertFalse(pending_path.exists())
        self.assertEqual(len(FakeWriter.rows), writes_after_apply)
        self.assertEqual(card.last_apply_id, pending["apply_id"])
        self.assertTrue(plan_retained_after_partial)

    def test_catalog_success_with_pending_cleanup_failure_reports_truthful_partial_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            catalog_path = root / "catalog.json"
            _artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            with patch("buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder), patch(
                "buoy_search.apply.TurbopufferWriter", FakeWriter
            ), patch(
                "buoy_search.apply.remove_expected_pending",
                side_effect=OSError("unlink failure"),
            ):
                result, stdout, stderr = run_cli(
                    approved_args(plan_path, state_root, catalog_path),
                    env={"TURBOPUFFER_API_KEY": "fake"},
                )
            partial = json.loads(stdout)
            pending_path = Path(partial["pending_path"])
            pending_before_reconcile = pending_path.exists()
            committed = load_catalog(catalog_path)
            remote_write_count = len(FakeWriter.rows)
            reconciled, reconcile_stdout, reconcile_stderr = run_cli([
                "catalog", "reconcile", "--pending", str(pending_path),
                "--catalog", str(catalog_path), "--json",
            ])

        self.assertEqual((result, stderr), (2, ""))
        self.assertTrue(partial["remote_apply_succeeded"])
        self.assertTrue(partial["catalog_updated"])
        self.assertFalse(partial["pending_cleanup"])
        self.assertEqual(partial["catalog_revision"], committed.catalog_revision)
        self.assertEqual(partial["card_revision"], committed.cards[0].card_revision)
        self.assertTrue(pending_before_reconcile)
        self.assertEqual((reconciled, reconcile_stderr), (0, ""))
        self.assertEqual(json.loads(reconcile_stdout)["mutation_status"], "already-committed")
        self.assertFalse(pending_path.exists())
        self.assertEqual(len(FakeWriter.rows), remote_write_count)

    def test_pending_confirmation_write_failure_is_truthful_and_recoverable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            catalog_path = root / "catalog.json"
            _artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            real_atomic_write = pending_module._atomic_write
            write_calls = 0

            def fail_confirmation(path, payload, *, exclusive=False):
                nonlocal write_calls
                write_calls += 1
                if write_calls == 2:
                    raise pending_module.PendingCatalogError("confirmation disk failure")
                return real_atomic_write(path, payload, exclusive=exclusive)

            with patch("buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder), patch(
                "buoy_search.apply.TurbopufferWriter", FakeWriter
            ), patch("buoy_search.catalog_pending._atomic_write", side_effect=fail_confirmation):
                result, stdout, stderr = run_cli(
                    approved_args(plan_path, state_root, catalog_path),
                    env={"TURBOPUFFER_API_KEY": "fake"},
                )
            partial = json.loads(stdout)
            pending_path = Path(partial["pending_path"])
            pending = load_pending(pending_path)
            remote_write_count = len(FakeWriter.rows)
            with patch("buoy_search.apply.TurbopufferWriter", side_effect=AssertionError("duplicate remote")):
                blocked, blocked_stdout, blocked_stderr = run_cli(
                    approved_args(plan_path, state_root, catalog_path),
                    env={"TURBOPUFFER_API_KEY": "fake"},
                )
            reconciled, reconcile_stdout, reconcile_stderr = run_cli([
                "catalog", "reconcile", "--pending", str(pending_path),
                "--catalog", str(catalog_path), "--json",
            ])
            card = load_catalog(catalog_path).cards[0]

        self.assertEqual((result, stderr), (2, ""))
        self.assertTrue(partial["remote_apply_succeeded"])
        self.assertFalse(partial["catalog_updated"])
        self.assertFalse(pending["remote_apply_confirmed"])
        self.assertIsNone(pending["apply_id"])
        self.assertEqual(blocked, 2)
        self.assertEqual(blocked_stdout, "")
        self.assertIn("applied state proves remote apply success", blocked_stderr)
        self.assertEqual((reconciled, reconcile_stderr), (0, ""))
        self.assertEqual(json.loads(reconcile_stdout)["mutation_status"], "committed")
        self.assertFalse(pending_path.exists())
        self.assertEqual(len(FakeWriter.rows), remote_write_count)
        self.assertIsNotNone(card.last_apply_id)

    def test_reconcile_is_idempotent_for_already_committed_revision_and_rejects_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            catalog_path = root / "catalog.json"
            _artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            with patch("buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder), patch(
                "buoy_search.apply.TurbopufferWriter", FakeWriter
            ), patch("buoy_search.apply.commit_system_card", side_effect=CatalogError("disk failure")):
                result, stdout, _stderr = run_cli(
                    approved_args(plan_path, state_root, catalog_path),
                    env={"TURBOPUFFER_API_KEY": "fake"},
                )
            self.assertEqual(result, 2)
            pending_path = Path(json.loads(stdout)["pending_path"])
            pending = load_pending(pending_path)
            commit_system_card(catalog_path.resolve(), parse_card(pending["prospective_card"]))
            reconciled, reconcile_stdout, reconcile_stderr = run_cli([
                "catalog", "reconcile", "--pending", str(pending_path),
                "--catalog", str(catalog_path), "--json",
            ])

            # A hash-tampered confirmed copy outside the trusted root fails closed.
            tampered_path = state_root.resolve() / "catalog-pending" / "tampered.json"
            tampered = dict(pending)
            tampered["region"] = "tampered-region"
            tampered_path.write_text(json.dumps(tampered), encoding="utf-8")
            rejected, rejected_stdout, rejected_stderr = run_cli([
                "catalog", "reconcile", "--pending", str(tampered_path),
                "--catalog", str(catalog_path), "--json",
            ])
            out_of_root = root / f"{pending['plan_id']}.json"
            out_of_root.write_text(json.dumps(pending), encoding="utf-8")
            out_result, out_stdout, out_stderr = run_cli([
                "catalog", "reconcile", "--pending", str(out_of_root),
                "--catalog", str(catalog_path), "--json",
            ])

        self.assertEqual((reconciled, reconcile_stderr), (0, ""))
        self.assertEqual(json.loads(reconcile_stdout)["mutation_status"], "already-committed")
        self.assertFalse(pending_path.exists())
        self.assertEqual(rejected, 2)
        self.assertEqual(rejected_stdout, "")
        self.assertTrue("binding" in rejected_stderr or "payload_hash" in rejected_stderr)
        self.assertEqual(out_result, 2)
        self.assertEqual(out_stdout, "")
        self.assertIn("directly under", out_stderr)

    def test_reconcile_rejects_replacement_after_lock_and_immediately_before_unlink(self) -> None:
        for replacement_phase in ("after-lock", "before-unlink"):
            with self.subTest(replacement_phase=replacement_phase), tempfile.TemporaryDirectory() as tmp:
                reset_fakes()
                root = Path(tmp)
                state_root = root / "state"
                catalog_path = root / "catalog.json"
                _artifacts, plan_path = build_saved_plan(root, state_root=state_root)
                with patch("buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder), patch(
                    "buoy_search.apply.TurbopufferWriter", FakeWriter
                ), patch("buoy_search.apply.commit_system_card", side_effect=CatalogError("disk failure")):
                    _result, stdout, _stderr = run_cli(
                        approved_args(plan_path, state_root, catalog_path),
                        env={"TURBOPUFFER_API_KEY": "fake"},
                    )
                pending_path = Path(json.loads(stdout)["pending_path"])

                if replacement_phase == "after-lock":
                    @contextmanager
                    def replacing_lock(**_kwargs):
                        replace_identically(pending_path)
                        yield

                    contexts = [patch(
                        "buoy_search.catalog_pending.acquire_namespace_apply_lock",
                        replacing_lock,
                    )]
                else:
                    real_commit = pending_module.commit_system_card

                    def commit_then_replace(path, card):
                        result = real_commit(path, card)
                        replace_identically(pending_path)
                        return result

                    contexts = [patch(
                        "buoy_search.catalog_pending.commit_system_card",
                        side_effect=commit_then_replace,
                    )]

                with contexts[0]:
                    reconciled, reconcile_stdout, reconcile_stderr = run_cli([
                        "catalog", "reconcile", "--pending", str(pending_path),
                        "--catalog", str(catalog_path), "--json",
                    ])
                catalog_cards = load_catalog(catalog_path).cards

                self.assertEqual(reconciled, 2)
                self.assertEqual(reconcile_stdout, "")
                self.assertIn("replaced", reconcile_stderr)
                self.assertTrue(pending_path.exists())
                if replacement_phase == "after-lock":
                    self.assertEqual(catalog_cards, [])
                else:
                    self.assertEqual(len(catalog_cards), 1)

    def test_abandon_rejects_replacement_after_lock_and_immediately_before_unlink(self) -> None:
        for replacement_phase in ("after-lock", "before-unlink"):
            with self.subTest(replacement_phase=replacement_phase), tempfile.TemporaryDirectory() as tmp:
                reset_fakes()
                root = Path(tmp)
                state_root = root / "state"
                catalog_path = root / "catalog.json"
                _artifacts, plan_path = build_saved_plan(root, state_root=state_root)
                FakeWriter.should_fail = True
                with patch("buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder), patch(
                    "buoy_search.apply.TurbopufferWriter", FakeWriter
                ):
                    self.assertEqual(run_cli(
                        approved_args(plan_path, state_root, catalog_path),
                        env={"TURBOPUFFER_API_KEY": "fake"},
                    )[0], 2)
                pending_path = next((state_root.resolve() / "catalog-pending").glob("*.json"))

                if replacement_phase == "after-lock":
                    @contextmanager
                    def replacing_lock(**_kwargs):
                        replace_identically(pending_path)
                        yield

                    context = patch(
                        "buoy_search.catalog_pending.acquire_namespace_apply_lock",
                        replacing_lock,
                    )
                else:
                    real_load = pending_module.load_catalog

                    def load_then_replace(path):
                        result = real_load(path)
                        replace_identically(pending_path)
                        return result

                    context = patch(
                        "buoy_search.catalog_pending.load_catalog",
                        side_effect=load_then_replace,
                    )

                with context:
                    abandoned, abandon_stdout, abandon_stderr = run_cli([
                        "catalog", "abandon-pending", "--pending", str(pending_path),
                        "--catalog", str(catalog_path), "--approve", "--json",
                    ])

                self.assertEqual(abandoned, 2)
                self.assertEqual(abandon_stdout, "")
                self.assertIn("replaced", abandon_stderr)
                self.assertTrue(pending_path.exists())

    def test_legacy_schema_v1_plan_without_precision_registers_from_verified_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            catalog_path = root / "catalog.json"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            plan.pop("embedding_precision")
            manifest = json.loads((plan_path.parent / "manifest.json").read_text(encoding="utf-8"))
            plan["artifact_hash"] = stable_hash({
                "schema_version": 1,
                "base_url": manifest["base_url"],
                "site_id": manifest["site_id"],
                "namespace": manifest["namespace"],
                "namespace_candidate": manifest["namespace_candidate"],
                "crawl_options": plan["crawl_options"],
                "chunk_options": plan["chunk_options"],
                "embedding_model": plan["embedding_model"],
                "manifest": manifest,
            })
            plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
            with patch("buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder), patch(
                "buoy_search.apply.TurbopufferWriter", FakeWriter
            ):
                result, stdout, stderr = run_cli(
                    approved_args(plan_path, state_root, catalog_path),
                    env={"TURBOPUFFER_API_KEY": "fake"},
                )
            card = load_catalog(catalog_path).cards[0]

        self.assertEqual((result, stderr), (0, ""))
        self.assertEqual(card.embedding_precision, "float32")
        self.assertEqual(card.source_kind, "website")
        self.assertEqual(card.source_uri, artifacts.manifest.base_url)
        self.assertTrue(json.loads(stdout)["catalog_updated"])

    def test_manual_disabled_semantics_survive_apply(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            catalog_path = root / "catalog.json"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            namespace = artifacts.manifest.namespace
            manual = prepare_card(
                CardFields(
                    namespace=namespace, enabled=False, source_kind="website",
                    source_uri=artifacts.manifest.base_url, site_id=artifacts.manifest.site_id,
                    title="Curated title", summary="Curated summary", aliases=["curated"], tags=["manual"],
                    semantic_origin="manual", region="old-region",
                    embedding_model="old-model", embedding_precision="float16", plan_schema_version=1,
                    ranking_mode="page", ranking_profile="none", ranking_pool=20,
                    ranking_aggregation="max", last_plan_id=None, last_apply_id=None,
                ),
                embedder=FixedRoutingEmbedder(),
            )
            save_catalog(catalog_path, [manual])
            with patch("buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder), patch(
                "buoy_search.apply.TurbopufferWriter", FakeWriter
            ):
                result, stdout, stderr = run_cli(
                    approved_args(plan_path, state_root, catalog_path),
                    env={"TURBOPUFFER_API_KEY": "fake"},
                )
            card = load_catalog(catalog_path).cards[0]

        self.assertEqual((result, stderr), (0, ""))
        self.assertFalse(card.enabled)
        self.assertEqual((card.title, card.summary, card.aliases, card.tags), (
            manual.title, manual.summary, manual.aliases, manual.tags,
        ))
        self.assertEqual(card.vector, manual.vector)
        self.assertEqual(card.region, "gcp-us-east4")
        self.assertEqual(card.embedding_model, artifacts.plan.embedding_model)
        self.assertTrue(json.loads(stdout)["catalog_updated"])

    def test_abandon_preview_approval_tamper_and_symlink_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            catalog_path = root / "catalog.json"
            _artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            FakeWriter.should_fail = True
            with patch("buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder), patch(
                "buoy_search.apply.TurbopufferWriter", FakeWriter
            ):
                self.assertEqual(run_cli(
                    approved_args(plan_path, state_root, catalog_path),
                    env={"TURBOPUFFER_API_KEY": "fake"},
                )[0], 2)
            pending_path = next((state_root.resolve() / "catalog-pending").glob("*.json"))
            before = pending_path.read_bytes()
            preview, preview_stdout, preview_stderr = run_cli([
                "catalog", "abandon-pending", "--pending", str(pending_path),
                "--catalog", str(catalog_path), "--json",
            ])
            preview_preserved = pending_path.read_bytes() == before
            approved, approved_stdout, approved_stderr = run_cli([
                "catalog", "abandon-pending", "--pending", str(pending_path),
                "--catalog", str(catalog_path), "--approve", "--json",
            ])

            # Recreate and prove a symlink path is rejected before local mutation.
            FakeWriter.should_fail = True
            with patch("buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder), patch(
                "buoy_search.apply.TurbopufferWriter", FakeWriter
            ):
                self.assertEqual(run_cli(
                    approved_args(plan_path, state_root, catalog_path),
                    env={"TURBOPUFFER_API_KEY": "fake"},
                )[0], 2)
            pending_path = next((state_root.resolve() / "catalog-pending").glob("*.json"))
            link = root / "pending-link.json"
            link.symlink_to(pending_path)
            rejected, rejected_stdout, rejected_stderr = run_cli([
                "catalog", "abandon-pending", "--pending", str(link),
                "--catalog", str(catalog_path), "--approve", "--json",
            ])
            pending_preserved_after_rejection = pending_path.exists()

        self.assertEqual((preview, preview_stderr), (0, ""))
        self.assertEqual(json.loads(preview_stdout)["mutation_status"], "preview")
        self.assertTrue(preview_preserved)
        self.assertEqual((approved, approved_stderr), (0, ""))
        self.assertEqual(json.loads(approved_stdout)["mutation_status"], "abandoned")
        self.assertEqual(rejected, 2)
        self.assertEqual(rejected_stdout, "")
        self.assertIn("regular non-symlink", rejected_stderr)
        self.assertTrue(pending_preserved_after_rejection)


if __name__ == "__main__":
    unittest.main()
