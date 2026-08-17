from __future__ import annotations

import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from buoy_search.local_paths import (
    LocalPathError,
    default_artifact_root,
    default_buoy_home,
    default_state_root,
    is_within,
    normalized_absolute,
    prepare_default_buoy_home,
)


class LocalPathTests(unittest.TestCase):
    def test_defaults_are_absolute_and_independent_of_working_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            first_cwd = root / "first"
            second_cwd = root / "second"
            home.mkdir()
            first_cwd.mkdir()
            second_cwd.mkdir()
            original_cwd = Path.cwd()
            try:
                with patch("buoy_search.local_paths.Path.home", return_value=home):
                    os.chdir(first_cwd)
                    first = (default_buoy_home(), default_state_root(), default_artifact_root())
                    os.chdir(second_cwd)
                    second = (default_buoy_home(), default_state_root(), default_artifact_root())
            finally:
                os.chdir(original_cwd)

            expected_home = home / ".buoy"
            self.assertEqual(first, second)
            self.assertEqual(
                first,
                (
                    expected_home,
                    expected_home,
                    expected_home / "artifacts" / "site-crawls",
                ),
            )
            self.assertTrue(all(path.is_absolute() for path in first))
            self.assertFalse(expected_home.exists())

    def test_home_working_directory_names_the_same_canonical_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            original_cwd = Path.cwd()
            try:
                os.chdir(home)
                with patch("buoy_search.local_paths.Path.home", return_value=home):
                    self.assertEqual(default_state_root(), home / ".buoy")
            finally:
                os.chdir(original_cwd)

    def test_normalized_absolute_collapses_dot_segments_without_resolving_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = root / "real"
            real.mkdir()
            linked = root / "linked"
            if hasattr(os, "symlink"):
                linked.symlink_to(real, target_is_directory=True)
                self.assertEqual(
                    normalized_absolute(linked / "child" / ".." / "target"),
                    linked / "target",
                )
            else:
                self.assertEqual(
                    normalized_absolute(real / "child" / ".." / "target"),
                    real / "target",
                )

    def test_containment_rejects_dot_segment_escape_and_sibling_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / ".buoy"

            self.assertTrue(is_within(root / "artifacts" / "site-crawls", root))
            self.assertFalse(is_within(root / "artifacts" / ".." / ".." / "outside", root))
            self.assertFalse(is_within(root.parent / ".buoy-backup" / "state", root))
            self.assertTrue(is_within(root, root))
            self.assertFalse(is_within(root, root, strict=True))

    def test_prepare_creates_only_private_canonical_home_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            target = home / ".buoy" / "artifacts" / "site-crawls" / "plan"

            with patch("buoy_search.local_paths.Path.home", return_value=home):
                prepare_default_buoy_home(target)

            buoy_home = home / ".buoy"
            self.assertTrue(buoy_home.is_dir())
            self.assertEqual(stat.S_IMODE(buoy_home.stat().st_mode), 0o700)
            self.assertFalse((buoy_home / "artifacts").exists())

    def test_prepare_does_not_create_home_for_explicit_outside_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            home.mkdir()

            with patch("buoy_search.local_paths.Path.home", return_value=home):
                prepare_default_buoy_home(root / "explicit" / "output")

            self.assertFalse((home / ".buoy").exists())
            self.assertFalse((root / "explicit").exists())

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks are unavailable")
    def test_prepare_rejects_symlink_at_canonical_home_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            external = root / "external"
            home.mkdir()
            external.mkdir()
            (home / ".buoy").symlink_to(external, target_is_directory=True)

            with patch("buoy_search.local_paths.Path.home", return_value=home):
                with self.assertRaisesRegex(LocalPathError, "must be a real directory"):
                    prepare_default_buoy_home(home / ".buoy" / "state")

            self.assertEqual(list(external.iterdir()), [])

    def test_prepare_rejects_file_at_canonical_home_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            boundary = home / ".buoy"
            boundary.write_text("not a directory", encoding="utf-8")

            with patch("buoy_search.local_paths.Path.home", return_value=home):
                with self.assertRaisesRegex(LocalPathError, "must be a real directory"):
                    prepare_default_buoy_home(boundary / "state")

            self.assertEqual(boundary.read_text(encoding="utf-8"), "not a directory")

    def test_home_resolution_failure_does_not_fall_back_to_working_directory(self) -> None:
        with patch(
            "buoy_search.local_paths.Path.home",
            side_effect=RuntimeError("home unavailable"),
        ):
            with self.assertRaisesRegex(LocalPathError, "could not resolve an absolute user home"):
                default_buoy_home()

    def test_explicit_output_does_not_require_home_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch(
            "buoy_search.local_paths.Path.home",
            side_effect=RuntimeError("home unavailable"),
        ):
            prepare_default_buoy_home(Path(tmp) / "explicit" / "output")

    def test_required_default_home_resolution_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch(
            "buoy_search.local_paths.Path.home",
            side_effect=RuntimeError("home unavailable"),
        ):
            with self.assertRaisesRegex(LocalPathError, "could not resolve an absolute user home"):
                prepare_default_buoy_home(
                    Path(tmp) / "untrusted-default",
                    require_resolved_home=True,
                )


if __name__ == "__main__":
    unittest.main()
