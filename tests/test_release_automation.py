from __future__ import annotations

import base64
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile
import tomllib
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile

import yaml

from scripts.release_automation import (
    LEGACY_V040_ASSETS,
    LEGACY_V040_SHA,
    LEGACY_V040_SOURCE_REF,
    REPOSITORY,
    SOURCE_REF,
    WORKFLOW,
    ReleaseError,
    evaluate_state,
    expected_provenance,
    make_plan,
    validate_changelog,
    validate_policy,
    validate_release_policy,
    validate_versions,
    verify_artifacts,
    _normalize_provenance,
)


ROOT = Path(__file__).resolve().parents[1]
PINNED_ACTION = re.compile(r"^[\w.-]+/[\w.-]+@[0-9a-f]{40}$")
EXPECTED_ACTION_MAJORS = {
    "actions/checkout": "v5",
    "astral-sh/setup-uv": "v7",
    "actions/upload-artifact": "v4",
    "actions/download-artifact": "v4",
    "actions/attest-build-provenance": "v2",
}
SHA = "1" * 40


def load_workflow(name: str) -> dict[str, object]:
    payload = yaml.safe_load((ROOT / ".github" / "workflows" / name).read_text())
    assert isinstance(payload, dict)
    return payload


def workflow_triggers(payload: dict[str, object]) -> dict[str, object]:
    # PyYAML 1.1 treats the unquoted GitHub Actions key `on` as boolean true.
    value = payload.get("on", payload.get(True))
    assert isinstance(value, dict)
    return value


def manifest() -> dict[str, object]:
    return {
        "version": "1.2.3",
        "tag": "v1.2.3",
        "assets": [
            {"name": "buoy_search-1.2.3-py3-none-any.whl", "sha256": "a" * 64},
            {"name": "buoy_search-1.2.3.tar.gz", "sha256": "b" * 64},
        ],
    }


def exact_snapshot() -> dict[str, object]:
    value = manifest()
    return {
        "tag": {"name": "v1.2.3", "object_type": "tag", "peel_sha": SHA},
        "release": {
            "tag_name": "v1.2.3",
            "name": "Buoy 1.2.3",
            "draft": False,
            "prerelease": False,
            "target": "v1.2.3",
            "assets": copy.deepcopy(value["assets"]),
        },
        "provenance": expected_provenance(value, SHA),
    }


def legacy_v040_manifest() -> dict[str, object]:
    return {
        "version": "0.4.0",
        "tag": "v0.4.0",
        "assets": [{"name": name, "sha256": digest} for name, digest in LEGACY_V040_ASSETS.items()],
    }


def legacy_v040_snapshot() -> dict[str, object]:
    value = legacy_v040_manifest()
    return {
        "tag": {"name": "v0.4.0", "object_type": "tag", "peel_sha": LEGACY_V040_SHA},
        "release": {
            "tag_name": "v0.4.0",
            "name": "Buoy v0.4.0",
            "draft": False,
            "prerelease": False,
            "target": "v0.4.0",
            "assets": copy.deepcopy(value["assets"]),
        },
        "provenance": expected_provenance(
            value, LEGACY_V040_SHA, source_ref=LEGACY_V040_SOURCE_REF
        ),
    }


def write_release_root(root: Path, versions: tuple[str, str, str], changelog: str) -> None:
    project, module, lock = versions
    (root / "src" / "buoy_search").mkdir(parents=True, exist_ok=True)
    (root / "pyproject.toml").write_text(f'[project]\nname = "buoy-search"\nversion = "{project}"\n')
    (root / "src" / "buoy_search" / "__init__.py").write_text(f'__version__ = "{module}"\n')
    (root / "uv.lock").write_text(
        f'version = 1\nrevision = 3\nrequires-python = ">=3.11"\n\n[[package]]\nname = "buoy-search"\nversion = "{lock}"\n'
    )
    (root / "CHANGELOG.md").write_text(changelog)


def valid_changelog() -> str:
    return """# Changelog

## [Unreleased]

## [1.2.3] - pending

- Current.

## [1.2.2] - 2026-07-20

- Older.
"""


def publication_plan(asset_payloads: dict[str, bytes]) -> dict[str, object]:
    value = manifest()
    value["assets"] = [
        {"name": name, "sha256": hashlib.sha256(payload).hexdigest()}
        for name, payload in asset_payloads.items()
    ]
    return make_plan({"tag": None, "release": None}, value, SHA)["plan"]


def fake_gh(root: Path, plan: dict[str, object], *, partial_release: bool = False) -> tuple[Path, Path]:
    binary = root / "bin" / "gh"
    binary.parent.mkdir()
    log = root / "gh.log"
    assets = {"buoy_search-1.2.3-py3-none-any.whl": b"wheel", "buoy_search-1.2.3.tar.gz": b"sdist"}
    hosted_assets = [
        {"name": item["name"], "digest": f"sha256:{item['sha256']}"}
        for item in plan["assets"]
    ]
    if partial_release:
        hosted_assets.pop()
    release = {
        "tag_name": plan["tag"],
        "name": plan["release_name"],
        "draft": False,
        "prerelease": False,
        "assets": hosted_assets,
    }
    binary.write_text(
        """#!/usr/bin/env python3
import base64, json, os, pathlib, sys
args = sys.argv[1:]
with open(os.environ["FAKE_GH_LOG"], "a") as handle:
    handle.write(json.dumps(args) + "\\n")
joined = " ".join(args)
if args[0] == "api" and "--method POST" in joined and "/git/tags" in joined:
    print(json.dumps({"sha": "9" * 40}))
elif args[0] == "api" and "--method POST" in joined and "/git/refs" in joined:
    print("HTTP 422: Validation Failed", file=sys.stderr)
    raise SystemExit(1)
elif args[0] == "api" and "/git/ref/tags/" in joined:
    print(json.dumps({"object": {"type": "tag", "sha": "8" * 40}}))
elif args[0] == "api" and "/git/tags/" in joined:
    print(json.dumps({"object": {"type": "commit", "sha": os.environ["FAKE_SHA"]}}))
elif args[0] == "api" and "/releases/tags/" in joined:
    print(os.environ["FAKE_RELEASE"])
elif args[:2] == ["release", "download"]:
    target = pathlib.Path(args[args.index("--dir") + 1])
    target.mkdir(parents=True, exist_ok=True)
    for name, payload in json.loads(os.environ["FAKE_ASSETS"]).items():
        (target / name).write_bytes(base64.b64decode(payload))
elif args[:2] == ["attestation", "verify"]:
    pass
else:
    print(f"unexpected gh call: {args}", file=sys.stderr)
    raise SystemExit(3)
"""
    )
    binary.chmod(0o755)
    environment = {
        "FAKE_GH_LOG": str(log),
        "FAKE_SHA": SHA,
        "FAKE_RELEASE": json.dumps(release),
        "FAKE_ASSETS": json.dumps(
            {name: base64.b64encode(payload).decode() for name, payload in assets.items()}
        ),
    }
    (root / "fake-env.json").write_text(json.dumps(environment))
    return binary.parent, log


def run_publication_step(
    step_name: str, root: Path, plan: dict[str, object], *, partial_release: bool = False
) -> tuple[subprocess.CompletedProcess[str], list[list[str]], str]:
    publication = root / "publication"
    publication.mkdir()
    envelope = {"plan": plan}
    encoded = json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()
    envelope["sha256"] = hashlib.sha256(encoded).hexdigest()
    (publication / "release-plan.json").write_text(json.dumps(envelope))
    bin_dir, log = fake_gh(root, plan, partial_release=partial_release)
    environment = os.environ.copy()
    environment.update(json.loads((root / "fake-env.json").read_text()))
    environment.update(
        {
            "PATH": f"{bin_dir}:{environment['PATH']}",
            "GITHUB_REPOSITORY": REPOSITORY,
            "GITHUB_OUTPUT": str(root / "github-output"),
        }
    )
    workflow = load_workflow("release.yml")
    step = next(item for item in workflow["jobs"]["publish"]["steps"] if item["name"] == step_name)
    completed = subprocess.run(
        ["bash", "-euo", "pipefail", "-c", step["run"]],
        cwd=root,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    output_path = root / "github-output"
    return completed, calls, output_path.read_text() if output_path.exists() else ""


class ReleaseAutomationTests(unittest.TestCase):
    def test_ci_workflow_is_read_only_locked_and_matrixed(self) -> None:
        payload = load_workflow("ci.yml")
        triggers = workflow_triggers(payload)
        self.assertEqual(set(triggers), {"pull_request", "push"})
        self.assertEqual(triggers["push"], {"branches": ["main", "develop"]})
        self.assertEqual(payload["permissions"], {"contents": "read"})
        jobs = payload["jobs"]
        self.assertEqual(jobs["test"]["strategy"]["matrix"]["python-version"], ["3.11", "3.13"])
        self.assertEqual(jobs["build"]["needs"], "test")
        text = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
        self.assertIn("uv sync --locked", text)
        self.assertIn("unittest discover", text)
        self.assertEqual(text.count("uv build --out-dir dist"), 1)
        self.assertNotIn("secrets.", text)

    def test_release_readiness_exposes_exact_four_main_pr_checks(self) -> None:
        payload = load_workflow("release-readiness.yml")
        self.assertEqual(workflow_triggers(payload), {"pull_request": {"branches": ["main"]}})
        self.assertEqual(payload["permissions"], {"contents": "read"})
        jobs = payload["jobs"]
        self.assertEqual(
            [jobs[name]["name"] for name in jobs],
            ["Policy", "Python 3.11", "Python 3.13", "Distribution"],
        )
        self.assertEqual(jobs["distribution"]["needs"], ["python-311", "python-313"])
        text = (ROOT / ".github" / "workflows" / "release-readiness.yml").read_text()
        self.assertIn("github.event.pull_request.base.sha", text)
        self.assertIn("github.event.pull_request.head.sha", text)
        self.assertIn("github.event.pull_request.head.repo.full_name", text)
        self.assertIn("scripts/release_automation.py policy", text)
        self.assertEqual(text.count("uv build --out-dir"), 1)

    def test_release_is_serialized_non_cancelling_main_push_only(self) -> None:
        payload = load_workflow("release.yml")
        self.assertEqual(workflow_triggers(payload), {"push": {"branches": ["main"]}})
        self.assertEqual(payload["concurrency"], {"group": "release-main", "cancel-in-progress": False})
        self.assertEqual(payload["permissions"], {"contents": "read"})
        self.assertEqual(payload["jobs"]["validate"]["strategy"]["matrix"]["python-version"], ["3.11", "3.13"])
        self.assertEqual((ROOT / ".github" / "workflows" / "release.yml").read_text().count("uv build --out-dir"), 1)

    def test_write_permissions_exist_only_on_final_dependency_free_job(self) -> None:
        payload = load_workflow("release.yml")
        jobs = payload["jobs"]
        for name in ("validate", "build"):
            self.assertNotIn("permissions", jobs[name])
        self.assertEqual(jobs["state"]["permissions"], {"contents": "read", "attestations": "read"})
        self.assertEqual(
            jobs["publish"]["permissions"],
            {"contents": "write", "id-token": "write", "attestations": "write", "actions": "read"},
        )
        publish = yaml.safe_dump(jobs["publish"])
        self.assertNotIn("actions/checkout", publish)
        self.assertNotIn("setup-uv", publish)
        self.assertNotIn("scripts/", publish)
        self.assertNotRegex(publish, r"\b(?:uv|pip) install\b")

    def test_workflows_pin_actions_and_contain_no_forbidden_release_operations(self) -> None:
        observed: set[str] = set()
        pattern = re.compile(r"^\s*uses:\s*([^\s#]+)\s+#\s+(v\d+)\s*$", re.MULTILINE)
        release_text = ""
        for workflow in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
            text = workflow.read_text()
            matches = pattern.findall(text)
            self.assertTrue(matches, workflow)
            for action, comment in matches:
                self.assertRegex(action, PINNED_ACTION, f"unpinned action in {workflow}: {action}")
                owner_name = action.split("@", 1)[0]
                self.assertIn(owner_name, EXPECTED_ACTION_MAJORS)
                self.assertEqual(comment, EXPECTED_ACTION_MAJORS[owner_name])
                observed.add(owner_name)
            if workflow.name in {"release.yml", "release-readiness.yml"}:
                release_text += text.lower()
        self.assertEqual(observed, set(EXPECTED_ACTION_MAJORS))
        for forbidden in (
            "workflow_dispatch",
            "environment: release",
            "uv publish",
            "twine",
            "pypi",
            "turbopuffer",
            "gh release delete",
            "git push --force",
            "git tag -f",
            "git update-ref -d",
        ):
            self.assertNotIn(forbidden, release_text)
        self.assertNotRegex(release_text, r"push:\s*\n\s*tags:")

    def test_workflows_lock_validation_determinism_smoke_and_publication_shape(self) -> None:
        readiness = (ROOT / ".github" / "workflows" / "release-readiness.yml").read_text()
        release = (ROOT / ".github" / "workflows" / "release.yml").read_text()
        for text in (readiness, release):
            self.assertIn("uv sync --locked", text)
            self.assertIn("validate_ranking_contract.py", text)
            self.assertIn("c6_syntax_forecast.py validate", text)
            self.assertIn("unittest discover", text)
            self.assertIn("SOURCE_DATE_EPOCH", text)
            self.assertIn('PYTHONHASHSEED: "0"', text)
            self.assertIn("TZ: UTC", text)
            self.assertIn("LC_ALL: C", text)
            self.assertIn("pip install --disable-pip-version-check", text)
            self.assertIn("load_pinned_tokenizer", text)
            self.assertIn("== 9", text)
        self.assertIn("actions/attest-build-provenance@", release)
        self.assertIn("--generate-notes --title", release)
        self.assertIn('--target "$tag"', release)
        self.assertIn("HTTP 422", release)
        self.assertEqual(release.count("git/refs"), 1)
        self.assertIn("gh release download", release)
        self.assertNotIn("if [ \"$ACTION\" = noop ]", release)
        self.assertEqual(release.count("--source-digest \"$sha\""), 2)
        self.assertEqual(release.count('Path(os.environ["PUBLISHED"]).iterdir()'), 2)
        self.assertIn('Path("validated/dist").iterdir()', release)
        self.assertIn('asset["sha256"] for asset in plan["assets"]', release)
        steps = load_workflow("release.yml")["jobs"]["publish"]["steps"]
        attest = next(step for step in steps if step["name"] == "Attest exact validated distributions")
        create = next(step for step in steps if step["name"] == "Create immutable GitHub Release")
        expected_condition = "needs.state.outputs.action == 'create' && steps.tag_transition.outputs.resolved_action == 'create'"
        self.assertEqual(attest["if"], expected_condition)
        self.assertEqual(create["if"], expected_condition)

    def test_versions_require_exact_stable_agreement_across_project_module_lock(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_release_root(root, ("1.2.3", "1.2.3", "1.2.3"), valid_changelog())
            self.assertEqual(validate_versions(root), "1.2.3")
            for values in (("1.2.4", "1.2.3", "1.2.3"), ("1.2.3", "1.2.4", "1.2.3"), ("1.2.3", "1.2.3", "1.2.4")):
                with self.subTest(values=values):
                    write_release_root(root, values, valid_changelog())
                    with self.assertRaisesRegex(ReleaseError, "version mismatch"):
                        validate_versions(root)
            for unstable in (
                "1.2",
                "v1.2.3",
                "1.2.3-rc.1",
                "1.2.3+build",
                "01.2.3",
                "1.02.3",
                "1.2.03",
                "00.0.0",
            ):
                with self.subTest(unstable=unstable):
                    write_release_root(root, (unstable,) * 3, valid_changelog())
                    with self.assertRaisesRegex(ReleaseError, "stable MAJOR.MINOR.PATCH"):
                        validate_versions(root)

    def test_changelog_requires_empty_unreleased_one_pending_current_and_dated_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_release_root(root, ("1.2.3",) * 3, valid_changelog())
            validate_changelog("1.2.3", root)
            mutations = {
                "nonempty Unreleased": valid_changelog().replace("## [Unreleased]\n", "## [Unreleased]\n\n- Work.\n"),
                "missing current": valid_changelog().replace("## [1.2.3] - pending", "## [1.2.4] - pending"),
                "duplicate current": valid_changelog() + "\n## [1.2.3] - pending\n",
                "undated older": valid_changelog().replace("## [1.2.2] - 2026-07-20", "## [1.2.2] - pending"),
                "invalid calendar date": valid_changelog().replace("2026-07-20", "2026-02-30"),
                "invalid month": valid_changelog().replace("2026-07-20", "2026-13-01"),
            }
            for name, text in mutations.items():
                with self.subTest(name=name):
                    (root / "CHANGELOG.md").write_text(text)
                    with self.assertRaises(ReleaseError):
                        validate_changelog("1.2.3", root)

    def test_policy_scans_all_workflows_and_release_helpers_for_forbidden_services(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflows = root / ".github" / "workflows"
            scripts = root / "scripts"
            workflows.mkdir(parents=True)
            scripts.mkdir()
            (workflows / "ci.yml").write_text("name: CI\n")
            (workflows / "nested.txt").write_text("publish to PyPI\n")
            (scripts / "release_automation.py").write_text("# local GitHub release only\n")
            (scripts / "release_checks.py").write_text("# local GitHub release only\n")
            validate_release_policy(root)
            for relative, text in (
                (Path(".github/workflows/ci.yml"), "publish to PyPI\n"),
                (Path(".github/workflows/other.yaml"), "deploy Turbopuffer\n"),
                (Path("scripts/release_checks.py"), "PYPI upload\n"),
                (Path("scripts/release_automation.py"), "turbopuffer release\n"),
                (Path("scripts/future_release.sh"), "upload PYPI\n"),
            ):
                with self.subTest(path=relative):
                    target = root / relative
                    original = target.read_text() if target.exists() else None
                    target.write_text(text)
                    with self.assertRaisesRegex(ReleaseError, "forbidden publication service"):
                        validate_release_policy(root)
                    if original is None:
                        target.unlink()
                    else:
                        target.write_text(original)

    def test_422_transition_executably_accepts_only_exact_complete_state(self) -> None:
        assets = {
            "buoy_search-1.2.3-py3-none-any.whl": b"wheel",
            "buoy_search-1.2.3.tar.gz": b"sdist",
        }
        plan = publication_plan(assets)
        with tempfile.TemporaryDirectory() as directory:
            completed, calls, output = run_publication_step(
                "Create immutable annotated tag when absent", Path(directory), plan
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(output, "resolved_action=noop\n")
            self.assertTrue(any(call[:2] == ["release", "download"] for call in calls))
            self.assertEqual(sum(call[:2] == ["attestation", "verify"] for call in calls), 2)
        with tempfile.TemporaryDirectory() as directory:
            completed, calls, output = run_publication_step(
                "Create immutable annotated tag when absent",
                Path(directory),
                plan,
                partial_release=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(output, "")
            self.assertFalse(any(call[:2] == ["release", "download"] for call in calls))
            self.assertFalse(any(call[:2] == ["attestation", "verify"] for call in calls))

    def test_final_verification_executably_downloads_digests_and_checks_provenance(self) -> None:
        assets = {
            "buoy_search-1.2.3-py3-none-any.whl": b"wheel",
            "buoy_search-1.2.3.tar.gz": b"sdist",
        }
        plan = publication_plan(assets)
        for initial_action in ("create", "noop"):
            with self.subTest(initial_action=initial_action), tempfile.TemporaryDirectory() as directory:
                case_plan = copy.deepcopy(plan)
                case_plan["action"] = initial_action
                completed, calls, _ = run_publication_step(
                    "Reinspect and verify exact published state", Path(directory), case_plan
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertTrue(any(call[:2] == ["release", "download"] for call in calls))
                verifies = [call for call in calls if call[:2] == ["attestation", "verify"]]
                self.assertEqual(len(verifies), 2)
                self.assertTrue(all("--source-ref" in call and SOURCE_REF in call for call in verifies))
                self.assertTrue(all("--source-digest" in call and SHA in call for call in verifies))

    def test_state_machine_create_and_exact_noop(self) -> None:
        self.assertEqual(evaluate_state({"tag": None, "release": None, "provenance": []}, manifest(), SHA), "create")
        self.assertEqual(evaluate_state(exact_snapshot(), manifest(), SHA), "noop")

    def test_exact_legacy_v040_noop_requires_tag_workflow_provenance_and_all_pins(self) -> None:
        value = legacy_v040_manifest()
        snapshot = legacy_v040_snapshot()
        self.assertEqual(evaluate_state(snapshot, value, LEGACY_V040_SHA), "noop")
        with self.assertRaisesRegex(ReleaseError, "permanent failure"):
            evaluate_state(snapshot, value, "2" * 40)
        plan = make_plan(snapshot, value, LEGACY_V040_SHA)["plan"]
        self.assertEqual(plan["release_name"], "Buoy v0.4.0")
        self.assertEqual(
            {item["source_ref"] for item in plan["provenance"]}, {LEGACY_V040_SOURCE_REF}
        )

        mutations = {
            "tag": ("tag", "name", "v0.4.1"),
            "commit": ("tag", "peel_sha", "2" * 40),
            "wheel digest": ("release", "assets", [
                {"name": name, "sha256": ("c" * 64 if name.endswith(".whl") else digest)}
                for name, digest in LEGACY_V040_ASSETS.items()
            ]),
            "sdist digest": ("release", "assets", [
                {"name": name, "sha256": ("c" * 64 if name.endswith(".tar.gz") else digest)}
                for name, digest in LEGACY_V040_ASSETS.items()
            ]),
        }
        for name, (section, field, replacement) in mutations.items():
            with self.subTest(name=name):
                changed = copy.deepcopy(snapshot)
                changed[section][field] = replacement
                with self.assertRaisesRegex(ReleaseError, "permanent failure"):
                    evaluate_state(changed, value, LEGACY_V040_SHA)
        for field, replacement in (
            ("repository", "other/repo"),
            ("workflow", "other.yml"),
            ("source_ref", SOURCE_REF),
            ("source_commit", "2" * 40),
        ):
            with self.subTest(provenance=field):
                changed = copy.deepcopy(snapshot)
                changed["provenance"][0][field] = replacement
                with self.assertRaisesRegex(ReleaseError, "permanent failure"):
                    evaluate_state(changed, value, LEGACY_V040_SHA)

    def test_future_versions_require_main_source_ref(self) -> None:
        snapshot = exact_snapshot()
        snapshot["provenance"] = expected_provenance(manifest(), SHA, source_ref="refs/tags/v1.2.3")
        with self.assertRaisesRegex(ReleaseError, "permanent failure: provenance mismatch"):
            evaluate_state(snapshot, manifest(), SHA)

    def test_attestation_normalization_uses_repository_path_ref_and_commit(self) -> None:
        digest = "a" * 64
        statement = {
            "subject": [{"name": "asset.whl", "digest": {"sha256": digest}}],
            "predicate": {
                "buildDefinition": {
                    "externalParameters": {
                        "workflow": {
                            "repository": "https://github.com/Doctacon/buoy-search",
                            "path": ".github/workflows/release.yml",
                            "ref": "refs/heads/main",
                        }
                    },
                    "resolvedDependencies": [{"digest": {"gitCommit": SHA}}],
                }
            },
        }
        self.assertEqual(
            _normalize_provenance(statement, "asset.whl", digest),
            {
                "name": "asset.whl",
                "sha256": digest,
                "repository": REPOSITORY,
                "workflow": WORKFLOW,
                "source_ref": SOURCE_REF,
                "source_commit": SHA,
            },
        )

    def test_state_machine_permanently_fails_every_partial_or_mismatched_state(self) -> None:
        cases: dict[str, dict[str, object]] = {}
        base = exact_snapshot()
        only_tag = copy.deepcopy(base)
        only_tag["release"] = None
        cases["tag-only"] = only_tag
        only_release = copy.deepcopy(base)
        only_release["tag"] = None
        cases["Release-only"] = only_release
        mutations = {
            "lightweight": ("tag", "object_type", "commit"),
            "wrong tag": ("tag", "name", "v9.9.9"),
            "wrong peel": ("tag", "peel_sha", "2" * 40),
            "Release tag": ("release", "tag_name", "v9.9.9"),
            "Release name": ("release", "name", "wrong"),
            "draft": ("release", "draft", True),
            "prerelease": ("release", "prerelease", True),
            "target": ("release", "target", "main"),
        }
        for name, (section, field, value) in mutations.items():
            changed = copy.deepcopy(base)
            changed[section][field] = value
            cases[name] = changed
        missing_asset = copy.deepcopy(base)
        missing_asset["release"]["assets"].pop()
        cases["missing asset"] = missing_asset
        extra_asset = copy.deepcopy(base)
        extra_asset["release"]["assets"].append({"name": "extra", "sha256": "c" * 64})
        cases["extra asset"] = extra_asset
        duplicate_asset = copy.deepcopy(base)
        duplicate_asset["release"]["assets"].append(copy.deepcopy(duplicate_asset["release"]["assets"][0]))
        cases["duplicate asset"] = duplicate_asset
        wrong_digest = copy.deepcopy(base)
        wrong_digest["release"]["assets"][0]["sha256"] = "c" * 64
        cases["asset digest"] = wrong_digest
        missing_provenance = copy.deepcopy(base)
        missing_provenance["provenance"].pop()
        cases["missing provenance"] = missing_provenance
        for field in ("name", "sha256", "repository", "workflow", "source_ref", "source_commit"):
            changed = copy.deepcopy(base)
            changed["provenance"][0][field] = "wrong"
            cases[f"provenance {field}"] = changed
        for name, snapshot in cases.items():
            with self.subTest(name=name):
                with self.assertRaisesRegex(ReleaseError, "permanent failure"):
                    evaluate_state(snapshot, manifest(), SHA)

    def test_state_plan_is_canonical_hash_addressed_and_rejects_short_sha(self) -> None:
        first = make_plan({"tag": None, "release": None}, manifest(), SHA)
        second = make_plan({"release": None, "tag": None}, manifest(), SHA)
        self.assertEqual(first, second)
        encoded = json.dumps(first["plan"], sort_keys=True, separators=(",", ":")).encode()
        import hashlib

        self.assertEqual(first["sha256"], hashlib.sha256(encoded).hexdigest())
        self.assertEqual(first["plan"]["tagger"]["email"], "41898282+github-actions[bot]@users.noreply.github.com")
        self.assertEqual(first["plan"]["tag_message"], "Buoy 1.2.3")
        with self.assertRaisesRegex(ReleaseError, "full 40-character SHA"):
            make_plan({}, manifest(), "123")

    def test_policy_requires_exact_develop_identity_merge_parents_and_absent_version(self) -> None:
        completed = subprocess.CompletedProcess([], 0, stdout=f"{'3' * 40} {'4' * 40} {'5' * 40}\n", stderr="")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_release_root(root, ("1.2.3",) * 3, valid_changelog())
            with patch("scripts.release_automation.subprocess.run", return_value=completed):
                self.assertEqual(
                    validate_policy(
                        head_repository=REPOSITORY,
                        head_ref="develop",
                        base_sha="4" * 40,
                        head_sha="5" * 40,
                        snapshot={"tag": None, "release": None},
                        root=root,
                    ),
                    "1.2.3",
                )
                with self.assertRaisesRegex(ReleaseError, "head must"):
                    validate_policy(
                        head_repository="fork/buoy-search",
                        head_ref="develop",
                        base_sha="4" * 40,
                        head_sha="5" * 40,
                        snapshot={},
                        root=root,
                    )
                with self.assertRaisesRegex(ReleaseError, "already has"):
                    validate_policy(
                        head_repository=REPOSITORY,
                        head_ref="develop",
                        base_sha="4" * 40,
                        head_sha="5" * 40,
                        snapshot={"tag": {"name": "v1.2.3"}, "release": None},
                        root=root,
                    )
            wrong = subprocess.CompletedProcess([], 0, stdout=f"{'3' * 40} {'5' * 40} {'4' * 40}\n", stderr="")
            with patch("scripts.release_automation.subprocess.run", return_value=wrong):
                with self.assertRaisesRegex(ReleaseError, "prospective merge"):
                    validate_policy(
                        head_repository=REPOSITORY,
                        head_ref="develop",
                        base_sha="4" * 40,
                        head_sha="5" * 40,
                        snapshot={},
                        root=root,
                    )

    def test_artifact_manifest_checks_names_metadata_inventory_entry_point_and_tokenizer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "root"
            dist = Path(directory) / "dist"
            root.mkdir()
            dist.mkdir()
            write_release_root(root, ("1.2.3",) * 3, valid_changelog())
            wheel = dist / "buoy_search-1.2.3-py3-none-any.whl"
            with zipfile.ZipFile(wheel, "w") as archive:
                archive.writestr("buoy_search-1.2.3.dist-info/METADATA", "Name: buoy-search\nVersion: 1.2.3\n")
                archive.writestr("buoy_search-1.2.3.dist-info/entry_points.txt", "[console_scripts]\nbuoy = buoy_search.cli:main\n")
                prefix = "buoy_search/data/bge-small-en-v1.5/5c38ec7c405ec4b44b94cc5a9bb96e735b38267a/"
                for name in ("special_tokens_map.json", "tokenizer.json", "tokenizer_config.json", "vocab.txt"):
                    archive.writestr(prefix + name, "{}")
            sdist = dist / "buoy_search-1.2.3.tar.gz"
            with tarfile.open(sdist, "w:gz") as archive:
                payload = b"Name: buoy-search\nVersion: 1.2.3\n"
                info = tarfile.TarInfo("buoy_search-1.2.3/PKG-INFO")
                info.size = len(payload)
                archive.addfile(info, io.BytesIO(payload))
                prefix = "buoy_search-1.2.3/src/buoy_search/data/bge-small-en-v1.5/5c38ec7c405ec4b44b94cc5a9bb96e735b38267a/"
                for name in ("special_tokens_map.json", "tokenizer.json", "tokenizer_config.json", "vocab.txt"):
                    info = tarfile.TarInfo(prefix + name)
                    info.size = 2
                    archive.addfile(info, io.BytesIO(b"{}"))
            (dist / ".gitignore").write_text("*")
            result = verify_artifacts(dist, root)
            self.assertEqual(result["version"], "1.2.3")
            self.assertEqual([asset["name"] for asset in result["assets"]], [wheel.name, sdist.name])
            (dist / "extra").touch()
            with self.assertRaisesRegex(ReleaseError, "asset names mismatch"):
                verify_artifacts(dist, root)

    def test_current_changelog_records_verified_v0_4_release(self) -> None:
        changelog = (ROOT / "CHANGELOG.md").read_text()
        self.assertIn("## [Unreleased]\n\n## [0.4.0] - 2026-07-21", changelog)
        self.assertIn("[Unreleased]: https://github.com/Doctacon/buoy-search/compare/v0.4.0...HEAD", changelog)
        self.assertIn("[0.4.0]: https://github.com/Doctacon/buoy-search/releases/tag/v0.4.0", changelog)

    def test_release_docs_describe_simple_flow_and_self_hosted_mapping(self) -> None:
        text = (ROOT / "docs" / "releasing.md").read_text()
        for required in (
            "Release readiness / Policy",
            "automatically validates",
            "There is no release-specific ancestry sync",
            "An absent tag and absent Release",
            "Self-hosted migration",
            "in-toto/SLSA",
            "release_automation.py policy",
            "sole transition exception",
            "refs/tags/v0.4.0",
            "Every future version requires `refs/heads/main`",
            "not published to PyPI",
        ):
            self.assertIn(required, text)

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

    def test_package_metadata_describes_v0_4_public_support(self) -> None:
        with (ROOT / "pyproject.toml").open("rb") as handle:
            config = tomllib.load(handle)
        project = config["project"]
        self.assertEqual(project["license"], "Apache-2.0")
        self.assertEqual(project["version"], "0.4.0")
        self.assertEqual(project["scripts"], {"buoy": "buoy_search.cli:main"})
        self.assertIn("transformers==5.12.1", project["dependencies"])
        self.assertIn("Development Status :: 4 - Beta", project["classifiers"])
        self.assertIn("Programming Language :: Python :: 3.11", project["classifiers"])
        self.assertIn("Programming Language :: Python :: 3.13", project["classifiers"])
        self.assertIn("vector-search", project["keywords"])
        self.assertEqual(config["build-system"]["requires"], ["hatchling==1.31.0"])
        self.assertEqual(config["tool"]["hatch"]["build"]["exclude"], ["/.10x/**"])

    def test_finalized_changelog_retains_v0_4_release_content_and_history(self) -> None:
        changelog = (ROOT / "CHANGELOG.md").read_text()
        self.assertIn("## [0.4.0] - 2026-07-21", changelog)
        self.assertIn("## [0.3.0] - 2026-07-16", changelog)
        self.assertIn("scheduled for removal in 0.4", changelog)
        self.assertIn("Removed\n\n- The deprecated package-owned `turbo-search` console entry point", changelog)
        self.assertIn("Replace only the executable name with `buoy`", changelog)
        self.assertIn("does not delete user-created shell aliases", changelog)
        for release_note in (
            "Retrieval results now return the automatic tags",
            "`fixed-80-python-breadcrumbs` and `python-ast` experiment arms",
            "Website crawling stays on the exact requested hostname",
            "MarkItDown ingestion again removes C0 and C1 control characters",
            "Opt-in float16 corpus and query embedding inference",
            "Read-only `buoy namespaces` discovery",
            "Explicit repeatable `--namespace` retrieval",
            "overlaps coordinator-thread embedding with one ordered background upsert",
            "Plan/apply preflight and success output expose decision-complete",
        ):
            self.assertIn(release_note, changelog)
        self.assertIn("## [0.2.1] - 2026-07-14", changelog)
        self.assertIn("`v0.2.0` tag was preserved without a GitHub Release", changelog)
        self.assertIn("[0.2.1]: https://github.com/Doctacon/buoy-search/releases/tag/v0.2.1", changelog)

    def test_console_alias_is_removed_for_v0_4_without_claiming_user_launcher_cleanup(self) -> None:
        self.assertNotIn("def legacy_main", (ROOT / "src" / "buoy_search" / "cli.py").read_text())
        migration = (ROOT / "docs" / "migrating-to-buoy.md").read_text()
        section = migration.split("## Command and Python package\n", 1)[1].split("\n## ", 1)[0]
        self.assertIn("Buoy 0.4 removes the deprecated `turbo-search` console entry point", section)
        self.assertIn("replacing only the executable name", section)
        self.assertIn("arguments, parser behavior, output, and exit codes are unchanged", section)
        self.assertIn("does not delete user-created shell aliases", section)

    def test_legacy_environment_alias_removal_remains_consistent(self) -> None:
        migration = (ROOT / "docs" / "migrating-to-buoy.md").read_text()
        section = migration.split("## Environment variables\n", 1)[1].split("\n## ", 1)[0]
        for mapping in (
            "TURBO_SEARCH_EMBEDDING_MODEL -> BUOY_EMBEDDING_MODEL",
            "TURBO_SEARCH_EMBEDDING_PRECISION -> BUOY_EMBEDDING_PRECISION",
        ):
            self.assertIn(mapping, section)
        for contract in ("exits 2", "no stdout", "never values", "Help, version", "does not migrate or delete"):
            self.assertIn(contract, section)
        config_source = (ROOT / "src" / "buoy_search" / "config.py").read_text()
        self.assertNotIn("legacy_model", config_source)
        self.assertNotIn("legacy_precision", config_source)
        self.assertNotIn("deprecated; use", config_source)
        self.assertIn("rejected by CLI entry points before dispatch", config_source)
        self.assertIn(
            "removes the `TURBO_SEARCH_EMBEDDING_MODEL` and `TURBO_SEARCH_EMBEDDING_PRECISION` fallbacks",
            (ROOT / "CHANGELOG.md").read_text(),
        )

    def test_legacy_release_check_cli_rejects_mismatch_without_git_side_effects(self) -> None:
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
