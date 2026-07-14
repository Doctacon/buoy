from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest

from buoy_search.chunker import process_corpus
from buoy_search.plan_artifacts import build_plan_artifacts, write_plan_artifacts
from buoy_search.plan_cleanup import cleanup_applied_plan_directory, cleanup_superseded_plan_directories


def write_plan(root: Path, *, namespace: str) -> Path:
    pages = root / "source"
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
    return root / "plan.json"


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

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks are unavailable")
    def test_cleanup_never_follows_plan_or_child_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            external = root / "external"
            external.mkdir()
            marker = external / "marker.txt"
            marker.write_text("keep", encoding="utf-8")
            plan_path = write_plan(root / "plan", namespace="site-example-com-v1")
            os.symlink(external, plan_path.parent / "source" / "external")

            warnings = cleanup_applied_plan_directory(plan_path, state_root=root / "state-root")

            self.assertEqual(len(warnings), 1)
            self.assertTrue(plan_path.parent.exists())
            self.assertTrue(marker.exists())

    def test_cleanup_applied_removes_exact_verified_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_path = write_plan(root / "plan", namespace="site-example-com-v1")

            warnings = cleanup_applied_plan_directory(plan_path, state_root=root / "state-root")

            self.assertEqual(warnings, [])
            self.assertFalse(plan_path.parent.exists())

    def test_cleanup_rejects_applied_plan_under_configured_state_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / ".turbo-search"
            plan_path = write_plan(state_root / "state" / "injected-plan", namespace="site-example-com-v1")

            warnings = cleanup_applied_plan_directory(plan_path, state_root=state_root)

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


if __name__ == "__main__":
    unittest.main()
