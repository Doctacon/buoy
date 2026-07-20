from __future__ import annotations

from copy import deepcopy
import json
import subprocess
import sys
import unittest

from scripts.validate_ranking_contract import (
    ContractValidationError,
    EXPERIMENT_NAMESPACE_PATTERN,
    INVENTORY_PATH,
    ROOT,
    _validate_source_bundle,
    validate_contract,
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

    def test_buoy_ratified_internal_judgment_is_absent_but_approval_stays_pending(self) -> None:
        buoy = next(repository for repository in self.inventory["repositories"] if repository["repo_key"] == "buoy")
        dataset = json.loads((ROOT / buoy["dataset_path"]).read_text(encoding="utf-8"))
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
