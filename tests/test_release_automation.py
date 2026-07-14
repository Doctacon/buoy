from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path
import tomllib
import unittest
import xml.etree.ElementTree as ET

import yaml

from scripts.release_checks import (
    module_version,
    project_version,
    verify_remote_annotated_tag,
    verify_assets,
    verify_tag,
)


ROOT = Path(__file__).resolve().parents[1]
PINNED_ACTION = re.compile(r"^[\w.-]+/[\w.-]+@[0-9a-f]{40}$")
EXPECTED_ACTION_MAJORS = {
    "actions/checkout": "v4",
    "astral-sh/setup-uv": "v6",
    "actions/upload-artifact": "v4",
    "actions/download-artifact": "v4",
    "actions/attest-build-provenance": "v2",
}


def load_workflow(name: str) -> dict[str, object]:
    payload = yaml.safe_load((ROOT / ".github" / "workflows" / name).read_text())
    assert isinstance(payload, dict)
    return payload


def workflow_triggers(payload: dict[str, object]) -> dict[str, object]:
    # PyYAML 1.1 treats the unquoted GitHub Actions key `on` as boolean true.
    value = payload.get("on", payload.get(True))
    assert isinstance(value, dict)
    return value


class ReleaseAutomationTests(unittest.TestCase):
    def test_ci_workflow_is_read_only_locked_and_matrixed(self) -> None:
        payload = load_workflow("ci.yml")
        triggers = workflow_triggers(payload)
        self.assertEqual(set(triggers), {"pull_request", "push"})
        self.assertEqual(triggers["push"], {"branches": ["main"]})
        self.assertEqual(payload["permissions"], {"contents": "read"})
        jobs = payload["jobs"]
        self.assertEqual(jobs["test"]["strategy"]["matrix"]["python-version"], ["3.11", "3.13"])
        self.assertEqual(jobs["build"]["needs"], "test")
        text = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
        self.assertIn("uv sync --locked", text)
        self.assertIn("unittest discover", text)
        self.assertEqual(text.count("uv build --out-dir dist"), 1)
        self.assertNotIn("secrets.", text)

    def test_release_is_tag_only_gated_attested_and_github_only(self) -> None:
        payload = load_workflow("release.yml")
        self.assertEqual(workflow_triggers(payload), {"push": {"tags": ["v*"]}})
        self.assertEqual(payload["permissions"], {"contents": "read"})
        jobs = payload["jobs"]
        self.assertEqual(jobs["release"]["environment"], "release")
        self.assertEqual(
            jobs["release"]["permissions"],
            {"contents": "write", "id-token": "write", "attestations": "write"},
        )
        text = (ROOT / ".github" / "workflows" / "release.yml").read_text()
        self.assertEqual(text.count("scripts/release_checks.py remote-tag-object"), 2)
        self.assertEqual(text.count("gh api \"repos/${GITHUB_REPOSITORY}/git/ref/tags/${GITHUB_REF_NAME}\""), 2)
        self.assertEqual(text.count("fetch-depth: 0"), 2)
        self.assertIn("actions/attest-build-provenance@", text)
        self.assertIn("gh release create", text)
        self.assertIn("--verify-tag", text)
        self.assertNotRegex(text.lower(), r"pypi|uv publish|twine|package registry")
        self.assertNotIn("branches:", text)

    def test_all_external_actions_are_sha_pinned_and_identified(self) -> None:
        observed: set[str] = set()
        pattern = re.compile(r"^\s*uses:\s*([^\s#]+)\s+#\s+(v\d+)\s*$", re.MULTILINE)
        for workflow in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
            matches = pattern.findall(workflow.read_text())
            self.assertTrue(matches, workflow)
            for action, comment in matches:
                self.assertRegex(action, PINNED_ACTION, f"unpinned action in {workflow}: {action}")
                owner_name = action.split("@", 1)[0]
                self.assertIn(owner_name, EXPECTED_ACTION_MAJORS)
                self.assertEqual(comment, EXPECTED_ACTION_MAJORS[owner_name])
                observed.add(owner_name)
        self.assertEqual(observed, set(EXPECTED_ACTION_MAJORS))

    def test_release_requires_remote_annotated_tag_metadata(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be annotated"):
            verify_remote_annotated_tag("v0.2.1", "commit")
        verify_remote_annotated_tag("v0.2.1", "tag")

    def test_release_checks_accept_only_current_tag_and_exact_assets(self) -> None:
        self.assertEqual(project_version(), "0.2.1")
        self.assertEqual(module_version(), "0.2.1")
        verify_tag("v0.2.1")
        with self.assertRaisesRegex(ValueError, "release tag mismatch"):
            verify_tag("v0.2.0")
        with tempfile.TemporaryDirectory() as directory:
            dist = Path(directory)
            for name in ("buoy_search-0.2.1-py3-none-any.whl", "buoy_search-0.2.1.tar.gz"):
                (dist / name).touch()
            self.assertEqual(
                verify_assets(dist),
                ["buoy_search-0.2.1-py3-none-any.whl", "buoy_search-0.2.1.tar.gz"],
            )
            (dist / "unexpected.txt").touch()
            with self.assertRaisesRegex(ValueError, "release assets mismatch"):
                verify_assets(dist)

    def test_public_surface_is_truthful_and_linked(self) -> None:
        readme = (ROOT / "README.md").read_text()
        self.assertLessEqual(len(readme.splitlines()), 100)
        self.assertIn("actions/workflows/ci.yml/badge.svg", readme)
        self.assertIn("img.shields.io/github/license", readme)
        for forbidden in ("pypi.org", "coverage.svg", "downloads", "github/stars", "release.svg"):
            self.assertNotIn(forbidden, readme.lower())
        for path in ("CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md", "docs/releasing.md"):
            self.assertTrue((ROOT / path).is_file(), path)
        self.assertIn("not published to PyPI", (ROOT / "docs" / "releasing.md").read_text())
        ET.parse(ROOT / "images" / "buoy.svg")

        for source in [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]:
            for target in re.findall(r"(?<!!)\[[^]]+\]\(([^)]+)\)", source.read_text()):
                if "://" in target or target.startswith(("#", "mailto:")):
                    continue
                relative = target.split("#", 1)[0]
                if relative:
                    self.assertTrue((source.parent / relative).resolve().exists(), f"{source}: {target}")

    def test_package_metadata_describes_public_support(self) -> None:
        with (ROOT / "pyproject.toml").open("rb") as handle:
            project = tomllib.load(handle)["project"]
        self.assertEqual(project["license"], "Apache-2.0")
        self.assertIn("Development Status :: 4 - Beta", project["classifiers"])
        self.assertIn("Programming Language :: Python :: 3.11", project["classifiers"])
        self.assertIn("Programming Language :: Python :: 3.13", project["classifiers"])
        self.assertIn("vector-search", project["keywords"])
        with (ROOT / "pyproject.toml").open("rb") as handle:
            build_system = tomllib.load(handle)["build-system"]
        self.assertEqual(build_system["requires"], ["hatchling==1.31.0"])

    def test_changelog_keeps_unreleased_version_pending(self) -> None:
        changelog = (ROOT / "CHANGELOG.md").read_text()
        self.assertIn("## 0.2.1 (pending GitHub release)", changelog)
        self.assertIn("`v0.2.0` tag was preserved without a GitHub Release", changelog)
        self.assertNotIn("releases/tag/v0.2.1", changelog)
        self.assertNotIn("compare/v0.2.1...HEAD", changelog)

    def test_release_check_cli_rejects_mismatch_without_git_side_effects(self) -> None:
        before = subprocess.run(
            ["git", "show-ref", "--tags"], cwd=ROOT, text=True, capture_output=True, check=False
        ).stdout
        result = subprocess.run(
            ["python3", "scripts/release_checks.py", "tag", "--tag", "v9.9.9"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        after = subprocess.run(
            ["git", "show-ref", "--tags"], cwd=ROOT, text=True, capture_output=True, check=False
        ).stdout
        self.assertEqual(result.returncode, 2)
        self.assertIn("release tag mismatch", result.stderr)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
