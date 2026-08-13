from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import re
import shutil
import tempfile
import tomllib
import unittest
import yaml

from scripts import release_automation


ROOT = Path(__file__).resolve().parents[1]


class ReleaseAutomationTests(unittest.TestCase):
    def test_current_dynamic_source_and_workflows_validate_read_only(self) -> None:
        result = release_automation.validate_source(ROOT)

        self.assertTrue(result["dynamic_version"])
        self.assertTrue(result["publication_paused"])
        self.assertEqual(result["published_history_through"], "0.5.1")
        self.assertIsNone(result["staged_release"])
        self.assertEqual(
            result["workflows_read_only"],
            list(release_automation.READ_ONLY_WORKFLOWS),
        )

    def test_dynamic_metadata_has_no_static_source_or_lock_version(self) -> None:
        with (ROOT / "pyproject.toml").open("rb") as handle:
            pyproject = tomllib.load(handle)
        with (ROOT / "uv.lock").open("rb") as handle:
            lock = tomllib.load(handle)

        self.assertNotIn("version", pyproject["project"])
        self.assertEqual(pyproject["project"]["dynamic"], ["version"])
        self.assertEqual(pyproject["tool"]["hatch"]["version"], {"source": "vcs"})
        self.assertEqual(
            pyproject["tool"]["hatch"]["build"]["hooks"]["vcs"],
            {"version-file": "src/buoy_search/_version.py"},
        )
        root_package, = [
            package for package in lock["package"] if package["name"] == "buoy-search"
        ]
        self.assertNotIn("version", root_package)
        self.assertEqual(root_package["source"], {"editable": "."})

    def test_release_readiness_preserves_exact_four_check_names(self) -> None:
        text = (ROOT / ".github/workflows/release-readiness.yml").read_text(
            encoding="utf-8"
        )
        self.assertEqual(
            re.findall(r"^    name: (.+)$", text, re.MULTILINE),
            ["Policy", "Python 3.11", "Python 3.13", "Distribution"],
        )
        policy = text.split("  python-311:", 1)[0]
        self.assertIn("astral-sh/setup-uv@", policy)
        self.assertIn("uv lock --check", policy)

    def test_release_related_workflows_are_pinned_and_have_no_write_path(self) -> None:
        for relative in release_automation.READ_ONLY_WORKFLOWS:
            with self.subTest(workflow=relative):
                text = (ROOT / relative).read_text(encoding="utf-8")
                parsed = yaml.safe_load(text)
                self.assertEqual(parsed["permissions"], {"contents": "read"})
                release_automation._load_read_only_workflow(ROOT / relative)
                self.assertNotRegex(
                    text.casefold(),
                    r"contents: write|id-token: write|write-all|gh release|git tag|actions/attest|actions/upload-artifact",
                )
                for reference in re.findall(r"uses:\s*([^@\s]+)@([^\s#]+)", text):
                    _action, revision = reference
                    self.assertRegex(revision, r"^[0-9a-f]{40}$")

    def test_main_push_workflow_only_validates_the_pause(self) -> None:
        text = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
        self.assertIn("name: Publication paused", text)
        self.assertIn("release_automation.py validate-source", text)
        self.assertNotIn("upload-artifact", text)
        self.assertNotIn("GITHUB_TOKEN", text)

    def test_ci_has_no_frontend_or_command_center_job(self) -> None:
        text = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertNotIn("frontend:", text)
        self.assertNotIn("command-center-package:", text)
        self.assertNotIn("--extra ui", text)
        self.assertNotIn("command_center", text)
        self.assertIn('python-version: ["3.11", "3.13"]', text)
        self.assertIn("validate-distribution dist", text)
        self.assertIn("Smoke a clean wheel installation", text)

    def test_source_validator_rejects_static_version_and_write_permission(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            clone = Path(tmp) / "source"
            shutil.copytree(
                ROOT,
                clone,
                ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "dist"),
            )
            pyproject_path = clone / "pyproject.toml"
            text = pyproject_path.read_text(encoding="utf-8")
            pyproject_path.write_text(
                text.replace('dynamic = ["version"]', 'version = "9.9.9"'),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(release_automation.ReleaseError, "project.version"):
                release_automation.validate_source(clone)

            pyproject_path.write_text(text, encoding="utf-8")
            workflow = clone / ".github/workflows/release.yml"
            workflow.write_text(
                workflow.read_text(encoding="utf-8").replace(
                    "contents: read", "contents: write"
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(release_automation.ReleaseError, "read-only"):
                release_automation.validate_source(clone)

    def test_source_validator_accepts_truthful_pre_release_changelog(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            clone = Path(tmp) / "source"
            shutil.copytree(
                ROOT,
                clone,
                ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "dist"),
            )
            changelog = clone / "CHANGELOG.md"
            changelog.write_text(
                changelog.read_text(encoding="utf-8").replace(
                    "## [0.5.1] - 2026-08-13", "## [0.5.1] - pending"
                ),
                encoding="utf-8",
            )

            result = release_automation.validate_source(clone)

            self.assertEqual(result["published_history_through"], "0.5.0")
            self.assertEqual(result["staged_release"], "0.5.1")

    def test_source_validator_rejects_job_permission_escalation_and_malformed_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            clone = Path(tmp) / "source"
            shutil.copytree(
                ROOT,
                clone,
                ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "dist"),
            )
            workflow = clone / ".github/workflows/release.yml"
            original = workflow.read_text(encoding="utf-8")
            workflow.write_text(
                original.replace(
                    "    runs-on: ubuntu-latest",
                    "    runs-on: ubuntu-latest\n    permissions: write-all",
                    1,
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                release_automation.ReleaseError, "may not escalate"
            ):
                release_automation.validate_source(clone)

            workflow.write_text("jobs: [unterminated", encoding="utf-8")
            with self.assertRaisesRegex(
                release_automation.ReleaseError, "not valid workflow YAML"
            ):
                release_automation.validate_source(clone)

            workflow.write_text(
                original.replace(
                    "      - name: Validate source-only release state",
                    "      - uses: actions/upload-artifact@"
                    "ea165f8d65b6e75b540449e92b4886f43607fa02\n"
                    "      - name: Validate source-only release state",
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                release_automation.ReleaseError, "actions/upload-artifact"
            ):
                release_automation.validate_source(clone)

    def test_legacy_publication_commands_fail_cleanly_before_argument_or_io_work(self) -> None:
        for command in ("validate", "artifacts", "state", "github-snapshot", "policy"):
            stdout = StringIO()
            stderr = StringIO()
            with self.subTest(command=command), redirect_stdout(stdout), redirect_stderr(
                stderr
            ):
                result = release_automation.main([command, "--unparsed", "secret"])
            self.assertEqual(result, 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertEqual(stderr.getvalue().strip(), release_automation.PAUSED_MESSAGE)
            self.assertNotIn("Traceback", stderr.getvalue())

    def test_release_docs_and_changelog_state_the_pause_and_recovery_boundary(self) -> None:
        docs = (ROOT / "docs/releasing.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("Automatic publication remains paused", docs)
        self.assertIn("No current workflow has write permission", docs)
        self.assertIn("validate-source", docs)
        self.assertIn("## Unreleased", changelog)
        self.assertIn("## [0.5.1] - 2026-08-13", changelog)
        self.assertIn("## [0.5.0] - 2026-08-01", changelog)
        self.assertIn("## [0.4.0] - 2026-07-21", changelog)
        self.assertEqual(changelog.count(" - pending"), 0)

    def test_focused_package_surface_excludes_operator_assets(self) -> None:
        with (ROOT / "pyproject.toml").open("rb") as handle:
            project = tomllib.load(handle)
        self.assertNotIn("ui", project["project"].get("optional-dependencies", {}))
        self.assertFalse(any(path.is_file() for path in (ROOT / "web").rglob("*")))
        for module in (
            member.removeprefix("buoy_search/")
            for member in release_automation.REMOVED_PACKAGE_MEMBERS
        ):
            self.assertFalse((ROOT / "src/buoy_search" / module).exists())
        self.assertFalse((ROOT / "src/buoy_search/command_center_static").exists())
        readiness = (ROOT / ".github/workflows/release-readiness.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("validate-distribution dist", readiness)
        self.assertIn("buoy-wheel-smoke", readiness)
        self.assertNotIn("upload-artifact", readiness)

    def test_distribution_inventory_rejects_every_removed_surface(self) -> None:
        focused = list(release_automation.REQUIRED_PACKAGE_MEMBERS)
        focused.extend(release_automation.TOKENIZER_MEMBER_SUFFIXES)
        release_automation._validate_archive_members(focused, archive="fixture")
        for member in release_automation.REMOVED_PACKAGE_MEMBERS:
            with self.subTest(member=member), self.assertRaisesRegex(
                release_automation.ReleaseError, "removed product surfaces"
            ):
                release_automation._validate_archive_members(
                    [*focused, member], archive="fixture"
                )
        for member in release_automation.REMOVED_ARCHIVE_MEMBERS:
            with self.subTest(member=member), self.assertRaisesRegex(
                release_automation.ReleaseError, "removed product surfaces"
            ):
                release_automation._validate_archive_members(
                    [*focused, member], archive="fixture"
                )
        for prefix in release_automation.REMOVED_ARCHIVE_PREFIXES:
            with self.subTest(prefix=prefix), self.assertRaisesRegex(
                release_automation.ReleaseError, "removed product surfaces"
            ):
                release_automation._validate_archive_members(
                    [*focused, f"{prefix}result.json"], archive="fixture"
                )


if __name__ == "__main__":
    unittest.main()
