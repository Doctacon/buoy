from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from buoy_search.chunker import process_corpus
from buoy_search.local_paths import default_artifact_root, default_state_root
from buoy_search.plan_artifacts import build_plan_artifacts, write_plan_artifacts
from buoy_search import plan_cleanup
from buoy_search.plan_cleanup import cleanup_applied_plan_directory, cleanup_superseded_plan_directories


def write_plan(root: Path, *, namespace: str) -> Path:
    pages = root.parent / f"{root.name}-source"
    pages.mkdir(parents=True)
    (pages / "page.md").write_text(
        "---\nurl: https://example.com/docs/page\ntitle: Example\n---\n\n# Example\n\nUseful text.\n",
        encoding="utf-8",
    )
    artifacts = build_plan_artifacts(
        indexing_plan=process_corpus(pages),
        base_url="https://example.com/docs/",
        out_dir=root,
        namespace=namespace,
        state_root=root / "state",
    )
    write_plan_artifacts(artifacts, root)
    for child in pages.iterdir():
        child.unlink()
    pages.rmdir()
    return root / "plan.json"


def set_created_at(plan_path: Path, value: str) -> None:
    payload = json.loads(plan_path.read_text(encoding="utf-8"))
    payload["created_at"] = value
    plan_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def applied_cleanup(
    plan_path: Path,
    *,
    state_root: Path,
    managed_plan_root: Path | None = None,
) -> list[str]:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    directory = plan_path.parent.stat()
    return cleanup_applied_plan_directory(
        plan_path,
        state_root=state_root,
        managed_plan_root=managed_plan_root,
        expected_plan_id=plan["plan_id"],
        expected_artifact_hash=plan["artifact_hash"],
        expected_namespace=plan["namespace"],
        expected_directory_device=directory.st_dev,
        expected_directory_inode=directory.st_ino,
    )


class PlanCleanupTests(unittest.TestCase):
    def test_supersession_removes_only_verified_same_namespace_sibling(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old_path = write_plan(root / "old", namespace="site-example-com-v1")
            new_path = write_plan(root / "new", namespace="site-example-com-v1")
            other_path = write_plan(root / "other", namespace="site-other-v1")
            malformed = root / "malformed"
            malformed.mkdir()
            (malformed / "plan.json").write_text("not json", encoding="utf-8")

            warnings = cleanup_superseded_plan_directories(
                new_path,
                namespace="site-example-com-v1",
                state_root=root / "state-root",
            )

            self.assertEqual(warnings, [])
            self.assertFalse(old_path.parent.exists())
            self.assertTrue(new_path.parent.exists())
            self.assertTrue(other_path.parent.exists())
            self.assertTrue(malformed.exists())

    def test_supersession_retains_newer_and_equal_creation_times(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            older = write_plan(root / "older", namespace="site-example-com-v1")
            selected = write_plan(root / "selected", namespace="site-example-com-v1")
            equal = write_plan(root / "equal", namespace="site-example-com-v1")
            newer = write_plan(root / "newer", namespace="site-example-com-v1")
            set_created_at(older, "2026-07-25T09:59:59+00:00")
            set_created_at(selected, "2026-07-25T10:00:00+00:00")
            set_created_at(equal, "2026-07-25T10:00:00+00:00")
            set_created_at(newer, "2026-07-25T10:00:01+00:00")

            warnings = cleanup_superseded_plan_directories(
                selected,
                namespace="site-example-com-v1",
                state_root=root / "state-root",
            )

            self.assertEqual(warnings, [])
            self.assertFalse(older.parent.exists())
            self.assertTrue(selected.parent.exists())
            self.assertTrue(equal.parent.exists())
            self.assertTrue(newer.parent.exists())

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks are unavailable")
    def test_cleanup_never_follows_plan_or_child_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            external = root / "external"
            external.mkdir()
            marker = external / "marker.txt"
            marker.write_text("keep", encoding="utf-8")
            plan_path = write_plan(root / "plan", namespace="site-example-com-v1")
            os.symlink(external, plan_path.parent / "external")

            warnings = applied_cleanup(plan_path, state_root=root / "state-root")

            self.assertEqual(len(warnings), 1)
            self.assertTrue(plan_path.parent.exists())
            self.assertTrue(marker.exists())

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks are unavailable")
    def test_cleanup_rejects_explicit_symlink_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            external = root / "external"
            plan_path = write_plan(
                external / "plan",
                namespace="site-example-com-v1",
            )
            linked_parent = root / "linked-parent"
            linked_parent.symlink_to(external, target_is_directory=True)

            warnings = applied_cleanup(
                linked_parent / "plan" / "plan.json",
                state_root=root / "state-root",
            )

            self.assertEqual(len(warnings), 1)
            self.assertIn("could not open plan artifact parent", warnings[0])
            self.assertTrue(plan_path.is_file())
            self.assertTrue(linked_parent.is_symlink())

    def test_cleanup_applied_removes_exact_verified_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_path = write_plan(root / "plan", namespace="site-example-com-v1")

            warnings = applied_cleanup(plan_path, state_root=root / "state-root")

            self.assertEqual(warnings, [])
            self.assertFalse(plan_path.parent.exists())

    def test_cleanup_retains_original_path_without_fd_safe_recursive_removal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_path = write_plan(root / "plan", namespace="site-example-com-v1")

            with patch.object(
                plan_cleanup.shutil.rmtree,
                "avoids_symlink_attacks",
                False,
            ):
                warnings = applied_cleanup(
                    plan_path,
                    state_root=root / "state-root",
                )

            self.assertEqual(len(warnings), 1)
            self.assertIn("could not safely remove", warnings[0])
            self.assertTrue(plan_path.is_file())
            self.assertEqual(list(root.glob(".buoy-plan-delete-*")), [])

    def test_applied_cleanup_does_not_delete_replacement_raced_after_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_path = write_plan(root / "plan", namespace="site-example-com-v1")
            expected = json.loads(plan_path.read_text(encoding="utf-8"))
            expected_directory = plan_path.parent.stat()
            replacement = write_plan(root / "replacement", namespace="site-other-v1").parent
            held = root / "held-original"
            real_rename = os.rename
            raced = False

            def race_then_rename(src, dst, **kwargs):  # noqa: ANN001, ANN003 - os protocol.
                nonlocal raced
                if not raced:
                    raced = True
                    real_rename(root / "plan", held)
                    real_rename(replacement, root / "plan")
                return real_rename(src, dst, **kwargs)

            with patch("buoy_search.plan_cleanup.os.rename", side_effect=race_then_rename):
                warnings = cleanup_applied_plan_directory(
                    plan_path,
                    state_root=root / "state-root",
                    expected_plan_id=expected["plan_id"],
                    expected_artifact_hash=expected["artifact_hash"],
                    expected_namespace=expected["namespace"],
                    expected_directory_device=expected_directory.st_dev,
                    expected_directory_inode=expected_directory.st_ino,
                )

            self.assertEqual(len(warnings), 1)
            self.assertTrue(held.exists())
            self.assertTrue((root / "plan").exists())
            self.assertEqual(
                json.loads((root / "plan/plan.json").read_text(encoding="utf-8"))["namespace"],
                "site-other-v1",
            )

    def test_supersession_does_not_delete_replacement_raced_after_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = write_plan(root / "old", namespace="site-example-com-v1").parent
            new_path = write_plan(root / "new", namespace="site-example-com-v1")
            replacement = write_plan(root / "replacement", namespace="site-other-v1").parent
            held = root / "held-old"
            real_rename = os.rename
            raced = False

            def race_then_rename(src, dst, **kwargs):  # noqa: ANN001, ANN003 - os protocol.
                nonlocal raced
                if not raced and src == "old":
                    raced = True
                    real_rename(old, held)
                    real_rename(replacement, old)
                return real_rename(src, dst, **kwargs)

            with patch("buoy_search.plan_cleanup.os.rename", side_effect=race_then_rename):
                warnings = cleanup_superseded_plan_directories(
                    new_path,
                    namespace="site-example-com-v1",
                    state_root=root / "state-root",
                )

            self.assertEqual(len(warnings), 1)
            self.assertTrue(held.exists())
            self.assertTrue(old.exists())
            self.assertTrue(new_path.parent.exists())
            self.assertEqual(
                json.loads((old / "plan.json").read_text(encoding="utf-8"))["namespace"],
                "site-other-v1",
            )

    def test_supersession_race_to_newer_same_namespace_is_retained(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = write_plan(root / "old", namespace="site-example-com-v1").parent
            new_path = write_plan(root / "new", namespace="site-example-com-v1")
            replacement = write_plan(root / "replacement", namespace="site-example-com-v1")
            set_created_at(old / "plan.json", "2026-07-25T09:00:00+00:00")
            set_created_at(new_path, "2026-07-25T10:00:00+00:00")
            set_created_at(replacement, "2026-07-25T11:00:00+00:00")
            replacement_dir = replacement.parent
            held = root / "held-old"
            real_rename = os.rename
            raced = False

            def race_then_rename(src, dst, **kwargs):  # noqa: ANN001, ANN003 - os protocol.
                nonlocal raced
                if not raced and src == "old":
                    raced = True
                    real_rename(old, held)
                    real_rename(replacement_dir, old)
                return real_rename(src, dst, **kwargs)

            with patch("buoy_search.plan_cleanup.os.rename", side_effect=race_then_rename):
                warnings = cleanup_superseded_plan_directories(
                    new_path,
                    namespace="site-example-com-v1",
                    state_root=root / "state-root",
                )

            self.assertEqual(len(warnings), 1)
            self.assertTrue(held.exists())
            self.assertTrue(old.exists())
            self.assertEqual(
                json.loads((old / "plan.json").read_text(encoding="utf-8"))["created_at"],
                "2026-07-25T11:00:00+00:00",
            )

    def test_supersession_leaves_schema1_and_corrupt_schema2_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            new_path = write_plan(root / "new", namespace="site-example-com-v1")
            schema1 = root / "schema1"
            schema1.mkdir()
            (schema1 / "plan.json").write_text(
                json.dumps({"schema_version": 1, "namespace": "site-example-com-v1"}),
                encoding="utf-8",
            )
            legacy = schema1 / "manifest.json"
            legacy.write_text("keep", encoding="utf-8")
            corrupt_path = write_plan(root / "corrupt", namespace="site-example-com-v1")
            corrupt_path.with_name("delta.duckdb").write_bytes(b"corrupt")

            warnings = cleanup_superseded_plan_directories(
                new_path,
                namespace="site-example-com-v1",
                state_root=root / "state-root",
            )

            self.assertEqual(warnings, [])
            self.assertTrue(schema1.exists())
            self.assertEqual(legacy.read_text(encoding="utf-8"), "keep")
            self.assertTrue(corrupt_path.parent.exists())

    def test_cleanup_rejects_applied_plan_under_configured_state_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / ".turbo-search"
            plan_path = write_plan(state_root / "state" / "injected-plan", namespace="site-example-com-v1")

            warnings = applied_cleanup(plan_path, state_root=state_root)

            self.assertEqual(len(warnings), 1)
            self.assertIn("under state root", warnings[0])
            self.assertTrue(plan_path.parent.exists())

    def test_supersession_rejects_candidates_under_configured_state_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "configured-state"
            old_path = write_plan(state_root / "old", namespace="site-example-com-v1")
            new_path = write_plan(state_root / "new", namespace="site-example-com-v1")

            warnings = cleanup_superseded_plan_directories(
                new_path,
                namespace="site-example-com-v1",
                state_root=state_root,
            )

            self.assertEqual(len(warnings), 1)
            self.assertIn("under state root", warnings[0])
            self.assertTrue(old_path.parent.exists())
            self.assertTrue(new_path.parent.exists())

    def test_cleanup_allows_verified_plan_below_canonical_managed_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            with patch("buoy_search.local_paths.Path.home", return_value=home):
                state_root = default_state_root()
                managed_plan_root = default_artifact_root()
                plan_path = write_plan(
                    managed_plan_root / "example-com-plan",
                    namespace="site-example-com-v1",
                )

                warnings = applied_cleanup(
                    plan_path,
                    state_root=state_root,
                )

            self.assertEqual(warnings, [])
            self.assertFalse(plan_path.parent.exists())

    def test_supersession_allows_verified_plans_below_canonical_managed_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            with patch("buoy_search.local_paths.Path.home", return_value=home):
                state_root = default_state_root()
                managed_plan_root = default_artifact_root()
                old_path = write_plan(
                    managed_plan_root / "old",
                    namespace="site-example-com-v1",
                )
                new_path = write_plan(
                    managed_plan_root / "new",
                    namespace="site-example-com-v1",
                )
                set_created_at(old_path, "2026-07-25T09:59:59+00:00")
                set_created_at(new_path, "2026-07-25T10:00:00+00:00")

                warnings = cleanup_superseded_plan_directories(
                    new_path,
                    namespace="site-example-com-v1",
                    state_root=state_root,
                )

            self.assertEqual(warnings, [])
            self.assertFalse(old_path.parent.exists())
            self.assertTrue(new_path.parent.exists())

    def test_canonical_managed_root_never_weakens_state_tree_protection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            with patch("buoy_search.local_paths.Path.home", return_value=home):
                state_root = default_state_root()
                managed_plan_root = default_artifact_root()
                plan_path = write_plan(
                    state_root / "state" / "injected-plan",
                    namespace="site-example-com-v1",
                )

                warnings = applied_cleanup(
                    plan_path,
                    state_root=state_root,
                    managed_plan_root=managed_plan_root,
                )

            self.assertEqual(len(warnings), 1)
            self.assertIn("under state root", warnings[0])
            self.assertTrue(plan_path.parent.exists())

    def test_canonical_home_remains_protected_with_custom_state_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            home.mkdir()
            custom_state_root = root / "custom-state"
            with patch("buoy_search.local_paths.Path.home", return_value=home):
                canonical_state_root = default_state_root()
                protected_plans = [
                    write_plan(
                        canonical_state_root / "state" / "injected-plan",
                        namespace="site-example-com-v1",
                    ),
                    write_plan(
                        canonical_state_root / "other" / "injected-plan",
                        namespace="site-example-com-v1",
                    ),
                ]

                for plan_path in protected_plans:
                    with self.subTest(plan_path=plan_path):
                        warnings = applied_cleanup(
                            plan_path,
                            state_root=custom_state_root,
                        )

                        self.assertEqual(len(warnings), 1)
                        self.assertIn("under state root", warnings[0])
                        self.assertTrue(plan_path.parent.exists())

    def test_canonical_managed_plan_with_custom_state_uses_bound_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            home.mkdir()
            custom_state_root = root / "custom-state"
            with patch("buoy_search.local_paths.Path.home", return_value=home):
                plan_path = write_plan(
                    default_artifact_root() / "example-com-plan",
                    namespace="site-example-com-v1",
                )
                real_open_chain = plan_cleanup._open_directory_chain
                with patch(
                    "buoy_search.plan_cleanup._open_directory_chain",
                    wraps=real_open_chain,
                ) as open_chain:
                    warnings = applied_cleanup(
                        plan_path,
                        state_root=custom_state_root,
                    )

            self.assertEqual(warnings, [])
            self.assertFalse(plan_path.parent.exists())
            open_chain.assert_called_once()

    def test_noncanonical_selected_state_root_stays_protected_when_broad(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            home.mkdir()
            with patch("buoy_search.local_paths.Path.home", return_value=home):
                plan_path = write_plan(
                    default_artifact_root() / "example-com-plan",
                    namespace="site-example-com-v1",
                )

                warnings = applied_cleanup(
                    plan_path,
                    state_root=home,
                )

            self.assertEqual(len(warnings), 1)
            self.assertIn("under state root", warnings[0])
            self.assertTrue(plan_path.parent.exists())

    def test_dot_segments_cannot_escape_managed_root_into_another_home_subtree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            with patch("buoy_search.local_paths.Path.home", return_value=home):
                state_root = default_state_root()
                managed_plan_root = default_artifact_root()
                managed_plan_root.mkdir(parents=True)
                actual_plan = write_plan(
                    state_root / "other" / "escaped-plan",
                    namespace="site-example-com-v1",
                )
                disguised_plan = (
                    managed_plan_root
                    / ".."
                    / ".."
                    / "other"
                    / "escaped-plan"
                    / "plan.json"
                )

                warnings = applied_cleanup(
                    disguised_plan,
                    state_root=state_root,
                    managed_plan_root=managed_plan_root,
                )

            self.assertEqual(len(warnings), 1)
            self.assertIn("under state root", warnings[0])
            self.assertTrue(actual_plan.parent.exists())

    def test_managed_root_sibling_prefix_is_not_a_cleanup_exception(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            with patch("buoy_search.local_paths.Path.home", return_value=home):
                state_root = default_state_root()
                managed_plan_root = default_artifact_root()
                plan_path = write_plan(
                    managed_plan_root.parent / "site-crawls-backup" / "plan",
                    namespace="site-example-com-v1",
                )

                warnings = applied_cleanup(
                    plan_path,
                    state_root=state_root,
                    managed_plan_root=managed_plan_root,
                )

            self.assertEqual(len(warnings), 1)
            self.assertIn("under state root", warnings[0])
            self.assertTrue(plan_path.parent.exists())

    def test_state_root_sibling_prefix_remains_outside_cleanup_guard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            with patch("buoy_search.local_paths.Path.home", return_value=home):
                state_root = default_state_root()
                managed_plan_root = default_artifact_root()
                plan_path = write_plan(
                    state_root.parent / ".buoy-backup" / "plan",
                    namespace="site-example-com-v1",
                )

                warnings = applied_cleanup(
                    plan_path,
                    state_root=state_root,
                    managed_plan_root=managed_plan_root,
                )

            self.assertEqual(warnings, [])
            self.assertFalse(plan_path.parent.exists())

    def test_canonical_managed_root_itself_is_never_removed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            with patch("buoy_search.local_paths.Path.home", return_value=home):
                state_root = default_state_root()
                managed_plan_root = default_artifact_root()
                plan_path = write_plan(managed_plan_root, namespace="site-example-com-v1")

                warnings = applied_cleanup(
                    plan_path,
                    state_root=state_root,
                    managed_plan_root=managed_plan_root,
                )

            self.assertEqual(len(warnings), 1)
            self.assertIn("under state root", warnings[0])
            self.assertTrue(managed_plan_root.exists())

    def test_canonical_state_root_itself_is_never_removed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            with patch("buoy_search.local_paths.Path.home", return_value=home):
                state_root = default_state_root()
                managed_plan_root = default_artifact_root()
                plan_path = write_plan(state_root, namespace="site-example-com-v1")

                warnings = applied_cleanup(
                    plan_path,
                    state_root=state_root,
                    managed_plan_root=managed_plan_root,
                )

            self.assertEqual(len(warnings), 1)
            self.assertIn("under state root", warnings[0])
            self.assertTrue(state_root.exists())

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks are unavailable")
    def test_cleanup_rejects_nested_symlink_ancestor_under_managed_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            external = root / "external-plan"
            home.mkdir()
            with patch("buoy_search.local_paths.Path.home", return_value=home):
                state_root = default_state_root()
                managed_plan_root = default_artifact_root()
                managed_plan_root.mkdir(parents=True)
                actual_plan = write_plan(external / "plan", namespace="site-example-com-v1")
                linked_ancestor = managed_plan_root / "linked-ancestor"
                linked_ancestor.symlink_to(external, target_is_directory=True)

                warnings = applied_cleanup(
                    linked_ancestor / "plan" / "plan.json",
                    state_root=state_root,
                    managed_plan_root=managed_plan_root,
                )

            self.assertEqual(len(warnings), 1)
            self.assertIn("under state root", warnings[0])
            self.assertTrue(actual_plan.parent.exists())
            self.assertTrue(linked_ancestor.is_symlink())

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks are unavailable")
    def test_cleanup_rejects_managed_ancestor_swapped_to_symlink_after_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            home.mkdir()
            with patch("buoy_search.local_paths.Path.home", return_value=home):
                state_root = default_state_root()
                managed_plan_root = default_artifact_root()
                plan_path = write_plan(
                    managed_plan_root / "example-com-plan",
                    namespace="site-example-com-v1",
                )
                artifacts_root = state_root / "artifacts"
                moved_artifacts = root / "moved-artifacts"
                real_verify = plan_cleanup._verified_plan_identity
                swapped = False

                def verify_then_swap(path: Path):
                    nonlocal swapped
                    identity = real_verify(path)
                    if not swapped and path == plan_path.parent:
                        swapped = True
                        artifacts_root.rename(moved_artifacts)
                        artifacts_root.symlink_to(moved_artifacts, target_is_directory=True)
                    return identity

                with patch(
                    "buoy_search.plan_cleanup._verified_plan_identity",
                    side_effect=verify_then_swap,
                ):
                    warnings = applied_cleanup(plan_path, state_root=state_root)

            self.assertEqual(len(warnings), 1)
            self.assertIn("could not open plan artifact parent", warnings[0])
            self.assertTrue(
                (moved_artifacts / "site-crawls/example-com-plan/plan.json").is_file()
            )
            self.assertTrue(artifacts_root.is_symlink())

    def test_cleanup_never_deletes_replacement_after_quarantine_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_path = write_plan(root / "plan", namespace="site-example-com-v1")
            victim = root / "victim"
            victim.mkdir()
            (victim / "marker.txt").write_text("keep", encoding="utf-8")
            held_verified = root / "held-verified"
            real_verify = plan_cleanup._verified_plan_identity
            swapped = False

            def verify_then_swap(path: Path):
                nonlocal swapped
                identity = real_verify(path)
                if (
                    not swapped
                    and identity is not None
                    and path.name.startswith(".buoy-plan-delete-")
                ):
                    swapped = True
                    path.rename(held_verified)
                    victim.rename(path)
                return identity

            with patch(
                "buoy_search.plan_cleanup._verified_plan_identity",
                side_effect=verify_then_swap,
            ):
                warnings = applied_cleanup(
                    plan_path,
                    state_root=root / "state-root",
                )

            self.assertEqual(len(warnings), 1)
            self.assertIn("replaced quarantined plan artifact", warnings[0])
            self.assertTrue((held_verified / "plan.json").is_file())
            self.assertTrue((held_verified / "delta.duckdb").is_file())
            quarantine_dirs = list(root.glob(".buoy-plan-delete-*"))
            self.assertEqual(len(quarantine_dirs), 1)
            self.assertEqual(
                (quarantine_dirs[0] / "marker.txt").read_text(encoding="utf-8"),
                "keep",
            )

    def test_custom_managed_root_cannot_weaken_configured_state_root_guard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            home.mkdir()
            custom_state_root = root / "custom-state"
            custom_managed_root = custom_state_root / "plans"
            plan_path = write_plan(
                custom_managed_root / "plan",
                namespace="site-example-com-v1",
            )

            with patch("buoy_search.local_paths.Path.home", return_value=home):
                warnings = applied_cleanup(
                    plan_path,
                    state_root=custom_state_root,
                    managed_plan_root=custom_managed_root,
                )

            self.assertEqual(len(warnings), 1)
            self.assertIn("under state root", warnings[0])
            self.assertTrue(plan_path.parent.exists())


if __name__ == "__main__":
    unittest.main()
