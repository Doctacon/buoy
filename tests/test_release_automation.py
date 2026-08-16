from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import hashlib
from io import StringIO
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
import yaml

from buoy_search import routing_quality as routing_quality_module
from scripts import release_automation


ROOT = Path(__file__).resolve().parents[1]


def routing_module_bytes(root: Path = ROOT) -> dict[str, bytes]:
    return {
        member: (root / f"src/{member}").read_bytes()
        for member in release_automation.ACTIVE_ROUTING_RECEIPT_MODULES.values()
    }


def active_routing_artifact(
    modules: dict[str, bytes],
    *,
    evaluator_runner: bytes,
) -> dict[str, object]:
    module_hashes = {
        member: hashlib.sha256(raw).hexdigest()
        for member, raw in modules.items()
    }
    return {
        "schema_version": routing_quality_module.ROUTING_ACTIVE_CALIBRATION_SCHEMA_VERSION,
        "calibration_id": routing_quality_module.ROUTING_CALIBRATION_ID,
        "calibration_revision": (
            routing_quality_module.ROUTING_ACTIVE_CALIBRATION_REVISION
        ),
        "mode": "active",
        "owner_approved": True,
        "score_floor": routing_quality_module.ROUTING_ACTIVE_SCORE_FLOOR,
        "margin_floor": routing_quality_module.ROUTING_ACTIVE_MARGIN_FLOOR,
        "bindings": {
            "routing_model": routing_quality_module.ROUTING_MODEL,
            "routing_model_revision": routing_quality_module.ROUTING_MODEL_REVISION,
            "routing_reranker_model": routing_quality_module.CROSS_ENCODER_MODEL,
            "routing_reranker_revision": routing_quality_module.CROSS_ENCODER_REVISION,
            "schema_contract": routing_quality_module.ROUTING_SCHEMA_CONTRACT,
            "projection": routing_quality_module.ROUTING_PROJECTION_CONTRACT,
            "shortlist_limit": routing_quality_module.ROUTING_SHORTLIST_LIMIT,
            "max_examples": routing_quality_module.ROUTING_MAX_EXAMPLES,
            "feature_contract": (
                routing_quality_module.ROUTING_CONFIDENCE_FEATURE_CONTRACT
            ),
            "score_field": routing_quality_module.ROUTING_CONFIDENCE_SCORE_FIELD,
            "margin_field": routing_quality_module.ROUTING_CONFIDENCE_MARGIN_FIELD,
            "canary_suite_sha256": (
                routing_quality_module.ROUTING_ACTIVE_CANARY_SUITE_SHA256
            ),
            "catalog_projection_sha256": (
                routing_quality_module.ROUTING_ACTIVE_CATALOG_PROJECTION_SHA256
            ),
        },
        "calibration": {
            "case_count": (
                routing_quality_module.ROUTING_ACTIVE_CALIBRATION_CASE_COUNT
            ),
            "case_ids_sha256": (
                routing_quality_module.ROUTING_ACTIVE_CALIBRATION_CASE_IDS_SHA256
            ),
            "incorrect_high_confidence_singletons": 0,
        },
        "certification": {
            "passed": True,
            "case_count": (
                routing_quality_module.ROUTING_ACTIVE_CERTIFICATION_CASE_COUNT
            ),
            "case_ids_sha256": (
                routing_quality_module.ROUTING_ACTIVE_CERTIFICATION_CASE_IDS_SHA256
            ),
            "verdict_sha256": (
                routing_quality_module.ROUTING_ACTIVE_QUALITY_VERDICT_SHA256
            ),
        },
        "receipts": {
            "authorization_report_sha256": (
                routing_quality_module.ROUTING_ACTIVATION_AUTHORIZATION_REPORT_SHA256
            ),
            "authorization_source_commit": (
                routing_quality_module.ROUTING_ACTIVATION_AUTHORIZATION_SOURCE_COMMIT
            ),
            "authorization_source_tree": (
                routing_quality_module.ROUTING_ACTIVATION_AUTHORIZATION_SOURCE_TREE
            ),
            "certified_dormant_report_sha256": "ab" * 32,
            "certified_dormant_source_commit": "bc" * 20,
            "certified_dormant_source_tree": "cd" * 20,
            "certified_dormant_working_tree_clean": True,
            "evaluator_runner_sha256": hashlib.sha256(
                evaluator_runner
            ).hexdigest(),
            "evaluator_scorer_sha256": module_hashes[
                "buoy_search/routing_quality.py"
            ],
            "routing_module_sha256": module_hashes["buoy_search/routing.py"],
            "cli_module_sha256": module_hashes["buoy_search/cli.py"],
            "evidence_module_sha256": module_hashes["buoy_search/evidence.py"],
            "collect_artifact_sha256": (
                routing_quality_module.ROUTING_COLLECT_ARTIFACT_SHA256
            ),
        },
    }


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
        self.assertEqual(
            result["routing_canaries"]["members"],
            sorted(release_automation.ROUTING_CANARY_MEMBERS),
        )
        self.assertEqual(
            result["routing_canaries"]["sha256"],
            release_automation.ROUTING_CANARY_MEMBERS,
        )
        self.assertEqual(
            result["routing_canaries"]["suite_sha256"],
            release_automation.ROUTING_CANARY_SUITE_SHA256,
        )
        packaged_mode = json.loads(
            (
                ROOT
                / "src/buoy_search/data/automatic_routing_confidence_calibration.json"
            ).read_bytes()
        )["mode"]
        self.assertEqual(result["routing_authority"]["mode"], packaged_mode)
        self.assertEqual(
            result["routing_authority"]["artifact_sha256"],
            hashlib.sha256(
                (
                    ROOT
                    / "src/buoy_search/data/automatic_routing_confidence_calibration.json"
                ).read_bytes()
            ).hexdigest(),
        )
        self.assertEqual(
            result["routing_authority"]["active_module_receipts_validated"],
            packaged_mode == "active",
        )
        self.assertEqual(
            result["routing_authority"]["active_runner_receipt_validated"],
            packaged_mode == "active",
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
        self.assertIn("load_routing_confidence_calibration()", text)
        readiness = (ROOT / ".github/workflows/release-readiness.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("load_routing_confidence_calibration()", readiness)

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

    def test_source_validator_rejects_consumed_v0_5_1_pending_state(self) -> None:
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

            with self.assertRaisesRegex(
                release_automation.ReleaseError,
                "published v0.5.1 history dated 2026-08-13",
            ):
                release_automation.validate_source(clone)

    def test_source_validator_requires_exact_approved_routing_canaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            clone = Path(tmp) / "source"
            shutil.copytree(
                ROOT,
                clone,
                ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "dist"),
            )
            canaries = clone / "src/buoy_search/data/routing_canaries"
            extra = canaries / "fleetdeck.json"
            extra.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(
                release_automation.ReleaseError,
                "inventory must be exactly",
            ):
                release_automation.validate_source(clone)

            extra.unlink()
            rentptr = canaries / "rentptr.json"
            rentptr.write_bytes(rentptr.read_bytes() + b"\n")
            with self.assertRaisesRegex(
                release_automation.ReleaseError,
                "hashes do not match",
            ):
                release_automation.validate_source(clone)

    def test_routing_canary_receipt_reconstructs_exact_approved_suite(self) -> None:
        canary_root = ROOT / "src/buoy_search/data/routing_canaries"
        canaries = {
            member: (canary_root / Path(member).name).read_bytes()
            for member in release_automation.ROUTING_CANARY_MEMBERS
        }
        legacy = (
            ROOT
            / "src/buoy_search/data/automatic_multi_corpus_retrieval_evals.json"
        ).read_bytes()

        receipt = release_automation._validate_routing_canary_bytes(
            canaries,
            legacy,
            where="test",
        )

        self.assertEqual(
            receipt,
            {
                "members": sorted(release_automation.ROUTING_CANARY_MEMBERS),
                "sha256": release_automation.ROUTING_CANARY_MEMBERS,
                "suite_sha256": release_automation.ROUTING_CANARY_SUITE_SHA256,
            },
        )

    def test_active_archive_receipts_require_exact_complete_module_bytes(self) -> None:
        modules = routing_module_bytes()
        runner = (ROOT / release_automation.ACTIVE_ROUTING_RUNNER_RECEIPT[1]).read_bytes()
        artifact = json.dumps(
            active_routing_artifact(modules, evaluator_runner=runner)
        ).encode("utf-8")

        receipt = release_automation._validate_routing_authority_bytes(
            artifact,
            modules,
            where="wheel fixture",
        )

        self.assertEqual(receipt["mode"], "active")
        self.assertEqual(
            receipt["artifact_sha256"],
            hashlib.sha256(artifact).hexdigest(),
        )
        self.assertTrue(receipt["active_module_receipts_validated"])
        self.assertEqual(
            receipt["module_sha256"],
            {
                member: hashlib.sha256(raw).hexdigest()
                for member, raw in modules.items()
            },
        )
        runner_receipt = release_automation._validate_routing_runner_receipt(
            artifact,
            runner,
            where="sdist fixture",
        )
        self.assertTrue(runner_receipt["active_runner_receipt_validated"])
        self.assertEqual(
            runner_receipt["evaluator_runner_sha256"],
            hashlib.sha256(runner).hexdigest(),
        )

        mismatched = dict(modules)
        mismatched["buoy_search/routing.py"] += b"\n"
        with self.assertRaisesRegex(
            release_automation.ReleaseError,
            "does not match buoy_search/routing.py",
        ):
            release_automation._validate_routing_authority_bytes(
                artifact,
                mismatched,
                where="wheel fixture",
            )

        incomplete = dict(modules)
        incomplete.pop("buoy_search/cli.py")
        with self.assertRaisesRegex(
            release_automation.ReleaseError,
            "must include exact module bytes",
        ):
            release_automation._validate_routing_authority_bytes(
                artifact,
                incomplete,
                where="sdist fixture",
            )

        with self.assertRaisesRegex(
            release_automation.ReleaseError,
            "does not match scripts/evaluate_routing_quality.py",
        ):
            release_automation._validate_routing_runner_receipt(
                artifact,
                runner + b"\n",
                where="sdist fixture",
            )

        changed_payload = active_routing_artifact(
            modules,
            evaluator_runner=runner,
        )
        changed_payload["score_floor"] = -9.0
        changed_artifact = json.dumps(changed_payload).encode("utf-8")
        changed_receipt = release_automation._validate_routing_authority_bytes(
            changed_artifact,
            modules,
            where="sdist fixture",
        )
        self.assertNotEqual(
            receipt["artifact_sha256"],
            changed_receipt["artifact_sha256"],
        )

    def test_collect_authority_requires_exact_governed_raw_bytes(self) -> None:
        artifact = (
            ROOT
            / "src/buoy_search/data/automatic_routing_confidence_calibration.json"
        ).read_bytes()
        modules = routing_module_bytes()

        receipt = release_automation._validate_routing_authority_bytes(
            artifact,
            modules,
            where="source fixture",
        )

        self.assertEqual(receipt["mode"], "collect")
        self.assertEqual(
            receipt["artifact_sha256"],
            release_automation.ROUTING_COLLECT_ARTIFACT_SHA256,
        )
        with self.assertRaisesRegex(
            release_automation.ReleaseError,
            "collect routing authority does not match its governed bytes",
        ):
            release_automation._validate_routing_authority_bytes(
                artifact + b"\n",
                modules,
                where="wheel fixture",
            )

    def test_source_and_installed_active_authority_load_exact_module_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            clone = Path(tmp) / "source"
            shutil.copytree(
                ROOT,
                clone,
                ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "dist"),
            )
            modules = routing_module_bytes(clone)
            runner_path = clone / release_automation.ACTIVE_ROUTING_RUNNER_RECEIPT[1]
            artifact = active_routing_artifact(
                modules,
                evaluator_runner=runner_path.read_bytes(),
            )
            artifact_path = (
                clone
                / "src/buoy_search/data/automatic_routing_confidence_calibration.json"
            )
            artifact_path.write_text(json.dumps(artifact), encoding="utf-8")

            source_receipt = release_automation.validate_source(clone)[
                "routing_authority"
            ]
            self.assertEqual(source_receipt["mode"], "active")
            self.assertTrue(source_receipt["active_module_receipts_validated"])
            self.assertTrue(source_receipt["active_runner_receipt_validated"])

            install_root = Path(tmp) / "installed"
            installed_package = install_root / "buoy_search"
            shutil.copytree(clone / "src/buoy_search", installed_package)
            version_file = installed_package / "_version.py"
            if not version_file.exists():
                version_file.write_text(
                    '__version__ = version = "test"\n',
                    encoding="utf-8",
                )
            code = (
                "import sys; "
                f"sys.path.insert(0, {str(install_root)!r}); "
                "from buoy_search.routing_quality import "
                "load_routing_confidence_calibration; "
                "authority = load_routing_confidence_calibration(); "
                "assert authority.mode == 'active'; "
                "assert authority.owner_approved is True; "
                "assert authority.receipts is not None; "
                "print(authority.mode)"
            )
            completed = subprocess.run(
                [sys.executable, "-I", "-c", code],
                cwd=tmp,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stdout.strip(), "active")

            routing_path = clone / "src/buoy_search/routing.py"
            routing_path.write_bytes(routing_path.read_bytes() + b"\n")
            with self.assertRaisesRegex(
                release_automation.ReleaseError,
                "does not match buoy_search/routing.py",
            ):
                release_automation.validate_source(clone)

            routing_path.write_bytes(modules["buoy_search/routing.py"])
            runner_path.write_bytes(runner_path.read_bytes() + b"\n")
            with self.assertRaisesRegex(
                release_automation.ReleaseError,
                "does not match scripts/evaluate_routing_quality.py",
            ):
                release_automation.validate_source(clone)

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

    def test_focused_package_surface_includes_routing_but_excludes_operator_assets(self) -> None:
        with (ROOT / "pyproject.toml").open("rb") as handle:
            project = tomllib.load(handle)
        self.assertNotIn("ui", project["project"].get("optional-dependencies", {}))
        self.assertFalse(any(path.is_file() for path in (ROOT / "web").rglob("*")))
        for module in (
            member.removeprefix("buoy_search/")
            for member in release_automation.REMOVED_PACKAGE_MEMBERS
        ):
            self.assertFalse((ROOT / "src/buoy_search" / module).exists())
        for module in (
            "catalog.py",
            "catalog_cli.py",
            "cross_encoder.py",
            "remote_catalog.py",
            "routing.py",
            "routing_quality.py",
        ):
            self.assertTrue((ROOT / "src/buoy_search" / module).is_file())
        self.assertEqual(
            release_automation.REQUIRED_SDIST_MEMBERS,
            (
                "scripts/evaluate_multi_corpus_retrieval.py",
                "scripts/evaluate_routing_quality.py",
            ),
        )
        for member in release_automation.REQUIRED_SDIST_MEMBERS:
            self.assertTrue((ROOT / member).is_file())
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

    def test_distribution_inventory_requires_only_approved_routing_canaries(self) -> None:
        focused = list(release_automation.REQUIRED_PACKAGE_MEMBERS)
        focused.extend(release_automation.TOKENIZER_MEMBER_SUFFIXES)
        release_automation._validate_archive_members(focused, archive="fixture")

        with self.assertRaisesRegex(
            release_automation.ReleaseError,
            "routing canary inventory must be exactly",
        ):
            release_automation._validate_archive_members(
                [*focused, "buoy_search/data/routing_canaries/fleetdeck.json"],
                archive="fixture",
            )

        without_rentptr = [
            member
            for member in focused
            if member != "buoy_search/data/routing_canaries/rentptr.json"
        ]
        with self.assertRaisesRegex(
            release_automation.ReleaseError,
            "missing focused package members",
        ):
            release_automation._validate_archive_members(
                without_rentptr,
                archive="fixture",
            )


if __name__ == "__main__":
    unittest.main()
