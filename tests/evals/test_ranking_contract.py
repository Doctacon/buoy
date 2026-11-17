from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from scripts.validate_ranking_contract import (
    ContractValidationError,
    EVALUATION_VERSIONS_PATH,
    EXPERIMENT_NAMESPACE_PATTERN,
    INVENTORY_PATH,
    ROOT,
    _validate_source_bundle,
    validate_contract,
    validate_versioned_buoy_evaluations,
)


class RankingContractValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.inventory = json.loads((ROOT / INVENTORY_PATH).read_text(encoding="utf-8"))
        bundle_path = ROOT / self.inventory["source_path_manifest_bundle_path"]
        self.bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

    def test_checked_in_contract_regenerates_expected_counts_and_hashes(self) -> None:
        summary = validate_contract()

        self.assertEqual(summary["datasets"], 13)
        self.assertEqual(summary["composite_identities"], 90)
        self.assertEqual(summary["judgments"], 369)
        self.assertEqual(summary["folds"], 13)
        self.assertEqual(summary["insufficient_repositories"], ["buoy"])
        self.assertEqual(summary["pending_baseline_approval"], ["buoy"])
        self.assertEqual(summary["versioned_buoy"]["active_dataset_version"], 3)
        self.assertEqual(summary["versioned_buoy"]["baseline_status"], "pending")

    def test_versioned_buoy_evaluation_preserves_v1_and_validates_current_paths(self) -> None:
        summary = validate_versioned_buoy_evaluations()
        registry = json.loads((ROOT / EVALUATION_VERSIONS_PATH).read_text(encoding="utf-8"))
        v1, v2, v3 = registry["versions"]
        historical = json.loads((ROOT / v1["dataset_path"]).read_text(encoding="utf-8"))
        current = json.loads((ROOT / v3["dataset_path"]).read_text(encoding="utf-8"))
        manifest = json.loads((ROOT / v3["path_membership_manifest_path"]).read_text(encoding="utf-8"))

        self.assertEqual(summary["historical_dataset_sha256"], "60008af2950ae8fa27da59c0af737ebf5b4a3e618680bfa113ec75951d338792")
        self.assertEqual(current["artifact"]["baseline_status"], "pending")
        self.assertFalse(current["artifact"]["promotion_eligible"])
        self.assertFalse(v3["promotion_eligible"])
        self.assertFalse(manifest["promotion_eligible"])
        self.assertNotIn("benchmark_artifact", current["artifact"])
        self.assertNotIn("corpus_manifest_path", current["artifact"])
        self.assertNotIn("corpus_manifest_sha256", current["artifact"])
        self.assertNotIn("corpus_manifest_path", v3)
        self.assertNotIn("corpus_manifest_sha256", v3)
        self.assertNotIn("source_snapshot", v3)
        self.assertNotIn("source_snapshot", manifest)
        self.assertEqual(
            summary["current_path_membership_manifest_sha256"],
            v3["path_membership_manifest_sha256"],
        )
        self.assertFalse(summary["promotion_eligible"])
        self.assertEqual(summary["mapped_paths"], 5)
        self.assertEqual(summary["immutable_v2_dataset_sha256"], "691566d85d1187717cfc06daebeb8bb965d9b337787050fab071afe8fad4d0ae")
        self.assertTrue(any(judgment["repo_path"] == "src/buoy_search/cli.py" for case in historical["cases"] for judgment in case["judgments"]))
        self.assertFalse((ROOT / "src/buoy_search/cli.py").exists())
        self.assertTrue(all((ROOT / path).is_file() for path in manifest["selected_repo_paths"]))

    def test_versioned_buoy_evaluation_rejects_non_path_judgment_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(ROOT / "src/buoy_search/data", root / "src/buoy_search/data")
            shutil.copytree(ROOT / ".10x/evidence/.storage", root / ".10x/evidence/.storage")
            registry_path = root / EVALUATION_VERSIONS_PATH
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            current_path = root / registry["versions"][2]["dataset_path"]
            current = json.loads(current_path.read_text(encoding="utf-8"))
            current["cases"][0]["question"] += " changed"
            current_path.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            registry["versions"][2]["dataset_sha256"] = hashlib.sha256(current_path.read_bytes()).hexdigest()
            registry_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

            with self.assertRaisesRegex(ContractValidationError, "judgments drifted"):
                validate_versioned_buoy_evaluations(root)

    def test_pending_buoy_v2_rejects_a_corpus_identity_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(ROOT / "src/buoy_search/data", root / "src/buoy_search/data")
            shutil.copytree(ROOT / ".10x/evidence/.storage", root / ".10x/evidence/.storage")
            registry_path = root / EVALUATION_VERSIONS_PATH
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            registry["versions"][1]["corpus_manifest_sha256"] = "0" * 64
            registry_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

            with self.assertRaisesRegex(ContractValidationError, "registry entry keys differ"):
                validate_versioned_buoy_evaluations(root)

    def test_buoy_ratified_internal_judgment_is_absent_but_approval_stays_pending(self) -> None:
        buoy = next(repository for repository in self.inventory["repositories"] if repository["repo_key"] == "buoy")
        registry = json.loads((ROOT / EVALUATION_VERSIONS_PATH).read_text(encoding="utf-8"))
        dataset = json.loads((ROOT / registry["versions"][0]["dataset_path"]).read_text(encoding="utf-8"))
        judgments = [
            judgment
            for case in dataset["cases"]
            for judgment in case["judgments"]
        ]

        self.assertEqual(len(judgments), 32)
        self.assertNotIn(
            ".10x/specs/repo-search-eval-autoresearch.md",
            {judgment["repo_path"] for judgment in judgments},
        )
        self.assertEqual(buoy["missing_judgment_paths"], [])
        self.assertEqual(buoy["validated_judgment_paths"], 32)
        self.assertEqual(buoy["baseline_namespace_status"], "pending_approval")
        self.assertFalse(buoy["sufficient"])

    def test_source_paths_must_be_sorted_and_distinct(self) -> None:
        bundle = deepcopy(self.bundle)
        bundle["repositories"][0]["selected_repo_paths"].append(
            bundle["repositories"][0]["selected_repo_paths"][0]
        )

        with self.assertRaisesRegex(ContractValidationError, "sorted and distinct"):
            _validate_source_bundle(bundle, self.inventory["repositories"])

    def test_authoritative_json_uses_exact_namespace_and_corpus_hash_names(self) -> None:
        self.assertEqual(self.inventory["experiment_namespace_pattern"], EXPERIMENT_NAMESPACE_PATTERN)
        for repository in self.inventory["repositories"]:
            self.assertEqual(repository["experiment_namespace_pattern"], EXPERIMENT_NAMESPACE_PATTERN)
            self.assertIn("selected_corpus_artifact_hash", repository)
            self.assertNotIn("source_artifact_hash", repository)

    def test_standard_library_command_succeeds(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/validate_ranking_contract.py"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["composite_identities"], 90)


if __name__ == "__main__":
    unittest.main()
