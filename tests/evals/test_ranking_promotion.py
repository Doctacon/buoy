from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from buoy_search.retrieval.ranking_defaults import (
    RANKING_DEFAULTS_AUTHORITY,
    RankingDefaultsError,
    parse_ranking_defaults,
)
from buoy_search.retrieval.retriever import (
    DEFAULT_CANDIDATES,
    DEFAULT_RANKING_AGGREGATION,
    DEFAULT_RANKING_MODE,
    DEFAULT_RANKING_POOL,
    DEFAULT_RANKING_PROFILE,
    DEFAULT_WEBSITE_RANKING_AGGREGATION,
    DEFAULT_WEBSITE_RANKING_MODE,
    DEFAULT_WEBSITE_RANKING_POOL,
    DEFAULT_WEBSITE_RANKING_PROFILE,
    ranking_defaults_for_namespace,
)
from scripts.validate_ranking_promotion import (
    AUTHORITY_PATH,
    EVALUATION_VERSIONS_PATH,
    EXPECTED_REPOS,
    INTRODUCTION_AUTHORITY_SHA256,
    PROMOTION_BASKETS_PATH,
    PromotionValidationError,
    _canonical_sha256,
    _policy_summary,
    classify_authority_change,
    resolve_ci_comparison,
    validate_promotion_artifact,
    validate_promotion_basket_registry,
    validate_promotion_gate,
)

ROOT = Path(__file__).resolve().parents[2]


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _hash_label(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


class RankingDefaultAuthorityTests(unittest.TestCase):
    def test_packaged_authority_reproduces_established_defaults(self) -> None:
        self.assertEqual(DEFAULT_CANDIDATES, 200)
        self.assertEqual(
            ranking_defaults_for_namespace("github-owner-repo-v1"),
            {
                "ranking_mode": "file",
                "ranking_profile": "repo_code",
                "ranking_pool": 100,
                "ranking_aggregation": "adaptive_sum_3",
            },
        )
        self.assertEqual(
            ranking_defaults_for_namespace("site-example-v1"),
            {
                "ranking_mode": "page",
                "ranking_profile": "none",
                "ranking_pool": 20,
                "ranking_aggregation": "max",
            },
        )
        self.assertEqual(DEFAULT_RANKING_MODE, "file")
        self.assertEqual(DEFAULT_RANKING_PROFILE, "repo_code")
        self.assertEqual(DEFAULT_RANKING_POOL, 100)
        self.assertEqual(DEFAULT_RANKING_AGGREGATION, "adaptive_sum_3")
        self.assertEqual(DEFAULT_WEBSITE_RANKING_MODE, "page")
        self.assertEqual(DEFAULT_WEBSITE_RANKING_PROFILE, "none")
        self.assertEqual(DEFAULT_WEBSITE_RANKING_POOL, 20)
        self.assertEqual(DEFAULT_WEBSITE_RANKING_AGGREGATION, "max")
        authority_raw = (ROOT / AUTHORITY_PATH).read_bytes()
        self.assertEqual(hashlib.sha256(authority_raw).hexdigest(), INTRODUCTION_AUTHORITY_SHA256)
        self.assertEqual(json.loads(authority_raw), RANKING_DEFAULTS_AUTHORITY.to_dict())

    def test_authority_rejects_unknown_and_duplicate_keys(self) -> None:
        value = RANKING_DEFAULTS_AUTHORITY.to_dict()
        value["unexpected"] = True
        with self.assertRaisesRegex(RankingDefaultsError, "keys differ"):
            parse_ranking_defaults(_json_bytes(value))
        raw = (ROOT / AUTHORITY_PATH).read_text(encoding="utf-8").replace(
            '"schema_version": 1,',
            '"schema_version": 1, "schema_version": 1,',
        )
        with self.assertRaisesRegex(RankingDefaultsError, "duplicate key"):
            parse_ranking_defaults(raw.encode("utf-8"))


class RankingPromotionGateTests(unittest.TestCase):
    def _authorities(self) -> tuple[bytes, bytes, dict[str, object], dict[str, object]]:
        base = json.loads((ROOT / AUTHORITY_PATH).read_text(encoding="utf-8"))
        proposed = deepcopy(base)
        proposed["authority_revision"] = "repo-and-website-ranking-defaults-v2"
        proposed["repository"]["ranking_aggregation"] = "capped_sum_3"
        return _json_bytes(base), _json_bytes(proposed), base, proposed

    def _artifact(
        self,
        root: Path,
        *,
        passing: bool = True,
        registry_status: str = "recorded",
        retain_path_membership: bool = False,
    ) -> tuple[Path, bytes, bytes]:
        root.joinpath(EVALUATION_VERSIONS_PATH.parent).mkdir(parents=True, exist_ok=True)
        registry = json.loads((ROOT / EVALUATION_VERSIONS_PATH).read_text(encoding="utf-8"))
        active = next(
            item for item in registry["versions"] if item["dataset_version"] == registry["active_buoy_dataset_version"]
        )
        base_raw, proposed_raw, base, proposed = self._authorities()
        retrieval_options = {"candidates": 200, "top_k": 10, "use_ann": True, "use_bm25": True}
        retrieval_contract = {
            "contract_revision": "hybrid-file-ranking-v1",
            "embedding_model": "fixture/model",
            "embedding_revision": "fixture-embedding-revision",
            "reranker_model": "fixture/reranker",
            "reranker_revision": "fixture-reranker-revision",
        }
        baseline_rows = [
            {"repo_key": key, "repo_search_score": 50.0, "precision_at_5": 0.4}
            for key in sorted(EXPECTED_REPOS)
        ]
        candidate_rows = [
            {
                "repo_key": key,
                "repo_search_score": 51.0 if passing else (49.0 if key == "black" else 50.0),
                "precision_at_5": 0.4,
            }
            for key in sorted(EXPECTED_REPOS)
        ]
        baseline_by_key = {row["repo_key"]: row for row in baseline_rows}
        candidate_by_key = {row["repo_key"]: row for row in candidate_rows}
        fixture_root = root / "promotion-fixtures"
        fixture_root.mkdir(parents=True, exist_ok=True)
        members = []
        for repo_key in sorted(EXPECTED_REPOS):
            dataset_id = f"{repo_key}-repo-search"
            dataset_version = 1
            if repo_key == "buoy":
                dataset_id = active["dataset_id"]
                dataset_version = active["dataset_version"]
            repository = f"example/{repo_key}"
            source_identity = {
                "kind": "git-commit",
                "revision": _hash_label(f"{repo_key}-source")[:40],
            }
            document = {
                "content_sha256": _hash_label(f"{repo_key}-content"),
                "path": f"src/{repo_key}/authority.py",
            }
            dataset_path = fixture_root / f"{repo_key}-dataset.json"
            dataset_path.write_bytes(
                _json_bytes(
                    {
                        "cases": [
                            {
                                "id": f"{repo_key}-authority",
                                "judgments": [
                                    {
                                        "grade": 3,
                                        "reason": "Direct authority implementation.",
                                        "repo_path": document["path"],
                                    }
                                ],
                                "question": f"Where is the {repo_key} authority implemented?",
                            }
                        ],
                        "dataset_id": dataset_id,
                        "dataset_version": dataset_version,
                        "repository": repository,
                        "schema_version": 1,
                    }
                )
            )
            corpus_path = fixture_root / f"{repo_key}-corpus.json"
            corpus_path.write_bytes(
                _json_bytes(
                    {
                        "document_inventory_sha256": _canonical_sha256([document]),
                        "documents": [document],
                        "manifest_id": f"{repo_key}-corpus-v1",
                        "repository": repository,
                        "schema_version": 1,
                        "source_identity": source_identity,
                    }
                )
            )
            member = {
                "baseline_status": "recorded",
                "corpus_manifest_path": corpus_path.relative_to(root).as_posix(),
                "corpus_manifest_sha256": hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
                "dataset_id": dataset_id,
                "dataset_path": dataset_path.relative_to(root).as_posix(),
                "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
                "dataset_version": dataset_version,
                "document_count": 1,
                "document_inventory_sha256": _canonical_sha256([document]),
                "recorded_benchmark_path": "pending",
                "recorded_benchmark_sha256": "1" * 64,
                "repo_key": repo_key,
                "repository": repository,
                "source_identity": source_identity,
            }
            benchmark_path = fixture_root / f"{repo_key}-benchmark.json"
            benchmark_path.write_bytes(
                _json_bytes(
                    {
                        "benchmark_id": f"{repo_key}-recorded-baseline-v1",
                        "corpus_manifest_sha256": member["corpus_manifest_sha256"],
                        "dataset_id": dataset_id,
                        "dataset_sha256": member["dataset_sha256"],
                        "dataset_version": dataset_version,
                        "repo_key": repo_key,
                        "repository": repository,
                        "result": baseline_by_key[repo_key],
                        "retrieval_contract": retrieval_contract,
                        "retrieval_options": retrieval_options,
                        "schema_version": 1,
                        "source_identity": source_identity,
                    }
                )
            )
            member["recorded_benchmark_path"] = benchmark_path.relative_to(root).as_posix()
            member["recorded_benchmark_sha256"] = hashlib.sha256(benchmark_path.read_bytes()).hexdigest()
            members.append(member)
        basket = {
            "baseline_status": "recorded",
            "basket_id": "repo-ranking-basket-test",
            "basket_sha256": "1" * 64,
            "basket_version": 1,
            "repositories": members,
            "schema_version": 1,
        }
        basket["basket_sha256"] = _canonical_sha256(
            {key: value for key, value in basket.items() if key != "basket_sha256"}
        )
        promotion_registry_path = root / PROMOTION_BASKETS_PATH
        promotion_registry_path.parent.mkdir(parents=True, exist_ok=True)
        promotion_registry_path.write_bytes(
            _json_bytes({"baskets": [basket], "schema_version": 1})
        )
        baseline_config = {
            "evaluation_basket_sha256": basket["basket_sha256"],
            "ranking_defaults": base,
            "retrieval_contract": retrieval_contract,
            "retrieval_options": retrieval_options,
        }
        candidate_config = deepcopy(baseline_config)
        candidate_config["ranking_defaults"] = proposed
        baseline = {
            "benchmark_id": "repo-ranking-baseline-test-v1",
            "benchmark_sha256": "1" * 64,
            "configuration": baseline_config,
            "repositories": baseline_rows,
        }
        candidate = {
            "benchmark_id": "repo-ranking-candidate-test-v1",
            "benchmark_sha256": "1" * 64,
            "configuration": candidate_config,
            "repositories": candidate_rows,
        }
        for arm in (baseline, candidate):
            arm["benchmark_sha256"] = _canonical_sha256(
                {
                    "benchmark_id": arm["benchmark_id"],
                    "configuration": arm["configuration"],
                    "repositories": arm["repositories"],
                }
            )

        active["baseline_status"] = registry_status
        buoy_member = next(row for row in members if row["repo_key"] == "buoy")
        active["dataset_sha256"] = buoy_member["dataset_sha256"]
        if registry_status == "recorded":
            active["promotion_eligible"] = True
            active["corpus_manifest_sha256"] = buoy_member["corpus_manifest_sha256"]
            active["benchmark_artifact_sha256"] = buoy_member["recorded_benchmark_sha256"]
            if not retain_path_membership:
                active.pop("path_membership_manifest_path", None)
                active.pop("path_membership_manifest_sha256", None)
        (root / EVALUATION_VERSIONS_PATH).write_bytes(_json_bytes(registry))

        artifact = {
            "artifact_id": "ranking-promotion-test-v2",
            "authority": {
                "base": base,
                "base_sha256": hashlib.sha256(base_raw).hexdigest(),
                "proposed": proposed,
                "proposed_sha256": hashlib.sha256(proposed_raw).hexdigest(),
            },
            "baseline": baseline,
            "candidate": candidate,
            "evaluation_basket": {
                "basket_id": basket["basket_id"],
                "basket_sha256": basket["basket_sha256"],
                "basket_version": basket["basket_version"],
            },
            "policy": _policy_summary(baseline_by_key, candidate_by_key),
            "schema_version": 2,
        }
        path = root / "promotion.json"
        path.write_bytes(_json_bytes(artifact))
        return path, base_raw, proposed_raw

    def _rewrite_artifact(self, path: Path, mutate) -> dict[str, object]:
        artifact = json.loads(path.read_text(encoding="utf-8"))
        mutate(artifact)
        path.write_bytes(_json_bytes(artifact))
        return artifact

    def _rewrite_registry(self, root: Path, mutate, *, rehash: bool = True) -> dict[str, object]:
        path = root / PROMOTION_BASKETS_PATH
        registry = json.loads(path.read_text(encoding="utf-8"))
        mutate(registry)
        if rehash and registry["baskets"]:
            basket = registry["baskets"][0]
            basket["basket_sha256"] = _canonical_sha256(
                {key: value for key, value in basket.items() if key != "basket_sha256"}
            )
        path.write_bytes(_json_bytes(registry))
        return registry

    def _rewrite_registered_file(
        self,
        root: Path,
        artifact_path: Path,
        *,
        repo_index: int,
        path_field: str,
        hash_field: str,
        mutate,
        update_member=None,
    ) -> None:
        registry_path = root / PROMOTION_BASKETS_PATH
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        basket = registry["baskets"][0]
        member = basket["repositories"][repo_index]
        file_path = root / member[path_field]
        value = json.loads(file_path.read_text(encoding="utf-8"))
        mutate(value)
        file_path.write_bytes(_json_bytes(value))
        member[hash_field] = hashlib.sha256(file_path.read_bytes()).hexdigest()
        if update_member is not None:
            update_member(member, value)
        basket["basket_sha256"] = _canonical_sha256(
            {key: item for key, item in basket.items() if key != "basket_sha256"}
        )
        registry_path.write_bytes(_json_bytes(registry))
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        artifact["evaluation_basket"]["basket_sha256"] = basket["basket_sha256"]
        artifact_path.write_bytes(_json_bytes(artifact))

    def _rehash_arm(self, artifact: dict[str, object], arm_name: str) -> None:
        arm = artifact[arm_name]
        arm["benchmark_sha256"] = _canonical_sha256(
            {
                "benchmark_id": arm["benchmark_id"],
                "configuration": arm["configuration"],
                "repositories": arm["repositories"],
            }
        )

    def test_pr_and_push_classification_use_correct_comparison(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            (root / "README.md").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "base"], cwd=root, check=True)
            initial = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
            authority_path = root / AUTHORITY_PATH
            authority_path.parent.mkdir(parents=True)
            shutil.copy2(ROOT / AUTHORITY_PATH, authority_path)

            with self.assertRaisesRegex(PromotionValidationError, "explicit introduction"):
                classify_authority_change(root, initial)
            introduction = classify_authority_change(root, initial, allow_authority_introduction=True)
            self.assertEqual(introduction["classification"], "authority-introduction")

            subprocess.run(["git", "add", AUTHORITY_PATH.as_posix()], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "authority"], cwd=root, check=True)
            authority_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
            (root / "README.md").write_text("implementation only\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "implementation"], cwd=root, check=True)
            self.assertEqual(
                classify_authority_change(root, authority_commit, comparison_mode="merge-base")["classification"],
                "unchanged",
            )
            self.assertEqual(
                classify_authority_change(root, authority_commit, comparison_mode="exact")["classification"],
                "unchanged",
            )

            value = json.loads(authority_path.read_text(encoding="utf-8"))
            value["authority_revision"] = "repo-and-website-ranking-defaults-v2"
            authority_path.write_bytes(_json_bytes(value))
            subprocess.run(["git", "add", AUTHORITY_PATH.as_posix()], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "promotion"], cwd=root, check=True)
            previous = subprocess.check_output(["git", "rev-parse", "HEAD^"], cwd=root, text=True).strip()
            self.assertEqual(
                classify_authority_change(root, previous, comparison_mode="exact")["classification"],
                "promotion",
            )

    def test_introduction_proof_rejects_different_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            (root / "README.md").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "base"], cwd=root, check=True)
            base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
            authority = RANKING_DEFAULTS_AUTHORITY.to_dict()
            authority["repository"]["ranking_pool"] = 99
            path = root / AUTHORITY_PATH
            path.parent.mkdir(parents=True)
            path.write_bytes(_json_bytes(authority))
            with self.assertRaisesRegex(PromotionValidationError, "pre-file defaults"):
                classify_authority_change(root, base, allow_authority_introduction=True)

    def test_ci_comparison_resolution_fails_closed(self) -> None:
        self.assertEqual(
            resolve_ci_comparison(environment={"BUOY_RANKING_EVENT_NAME": "pull_request", "BUOY_RANKING_PR_BASE_REF": "abc"}),
            ("abc", "merge-base"),
        )
        self.assertEqual(
            resolve_ci_comparison(environment={"BUOY_RANKING_EVENT_NAME": "push", "BUOY_RANKING_PUSH_BEFORE": "abc"}),
            ("abc", "exact"),
        )
        for environment in (
            {},
            {"BUOY_RANKING_EVENT_NAME": "pull_request"},
            {"BUOY_RANKING_EVENT_NAME": "push"},
            {"BUOY_RANKING_EVENT_NAME": "push", "BUOY_RANKING_PUSH_BEFORE": "0" * 40},
        ):
            with self.assertRaises(PromotionValidationError):
                resolve_ci_comparison(environment=environment)

    def test_changed_authority_requires_artifact(self) -> None:
        base_raw, proposed_raw, _, _ = self._authorities()
        classification = {"classification": "promotion", "base_raw": base_raw, "current_raw": proposed_raw}
        with tempfile.TemporaryDirectory() as tmp, self.assertRaisesRegex(
            PromotionValidationError, "without exactly one matching artifact"
        ):
            validate_promotion_gate(classification, None, root=Path(tmp))

    def test_valid_recorded_13_repo_basket_passes_offline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, base_raw, proposed_raw = self._artifact(root)
            summary = validate_promotion_artifact(path, base_raw=base_raw, proposed_raw=proposed_raw, root=root)
            self.assertEqual(summary["repositories"], 13)
            self.assertTrue(summary["policy"]["passed"])
            self.assertTrue(re.fullmatch(r"[0-9a-f]{64}", summary["basket_sha256"]))

    def test_pending_and_path_only_versions_cannot_promote(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, base_raw, proposed_raw = self._artifact(root, registry_status="pending")
            with self.assertRaisesRegex(PromotionValidationError, "pending Buoy"):
                validate_promotion_artifact(path, base_raw=base_raw, proposed_raw=proposed_raw, root=root)

            path, base_raw, proposed_raw = self._artifact(root, retain_path_membership=True)
            with self.assertRaisesRegex(PromotionValidationError, "path-only Buoy"):
                validate_promotion_artifact(path, base_raw=base_raw, proposed_raw=proposed_raw, root=root)

            path, base_raw, proposed_raw = self._artifact(root)
            self._rewrite_registry(
                root,
                lambda value: value["baskets"][0].__setitem__("baseline_status", "pending"),
            )
            with self.assertRaisesRegex(PromotionValidationError, "basket must be recorded"):
                validate_promotion_artifact(path, base_raw=base_raw, proposed_raw=proposed_raw, root=root)

            path, base_raw, proposed_raw = self._artifact(root)
            self._rewrite_registry(
                root,
                lambda value: value["baskets"][0]["repositories"][0].__setitem__("baseline_status", "pending"),
            )
            with self.assertRaisesRegex(PromotionValidationError, "must be recorded"):
                validate_promotion_artifact(path, base_raw=base_raw, proposed_raw=proposed_raw, root=root)

    def test_incomplete_or_content_unbound_basket_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, base_raw, proposed_raw = self._artifact(root)
            self._rewrite_registry(root, lambda value: value["baskets"][0]["repositories"].pop())
            with self.assertRaisesRegex(PromotionValidationError, "13 repositories"):
                validate_promotion_artifact(path, base_raw=base_raw, proposed_raw=proposed_raw, root=root)

            path, base_raw, proposed_raw = self._artifact(root)
            self._rewrite_registry(
                root,
                lambda value: value["baskets"][0]["repositories"][0].__setitem__("corpus_manifest_sha256", "0" * 64),
            )
            with self.assertRaisesRegex(PromotionValidationError, "all-zero"):
                validate_promotion_artifact(path, base_raw=base_raw, proposed_raw=proposed_raw, root=root)

    def test_registry_requires_actual_member_bytes_and_registration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, base_raw, proposed_raw = self._artifact(root)
            registry = json.loads((root / PROMOTION_BASKETS_PATH).read_text(encoding="utf-8"))
            member = registry["baskets"][0]["repositories"][0]
            dataset_path = root / member["dataset_path"]
            dataset_path.write_bytes(dataset_path.read_bytes() + b"\n")
            with self.assertRaisesRegex(PromotionValidationError, "dataset_sha256 differs from actual bytes"):
                validate_promotion_artifact(path, base_raw=base_raw, proposed_raw=proposed_raw, root=root)

            path, base_raw, proposed_raw = self._artifact(root)
            registry = json.loads((root / PROMOTION_BASKETS_PATH).read_text(encoding="utf-8"))
            member = registry["baskets"][0]["repositories"][1]
            (root / member["corpus_manifest_path"]).unlink()
            with self.assertRaisesRegex(PromotionValidationError, "corpus manifest file is missing"):
                validate_promotion_artifact(path, base_raw=base_raw, proposed_raw=proposed_raw, root=root)

            path, base_raw, proposed_raw = self._artifact(root)
            registry = json.loads((root / PROMOTION_BASKETS_PATH).read_text(encoding="utf-8"))
            member = registry["baskets"][0]["repositories"][2]
            corpus_path = root / member["corpus_manifest_path"]
            corpus_path.write_bytes(corpus_path.read_bytes() + b"\n")
            with self.assertRaisesRegex(PromotionValidationError, "corpus_manifest_sha256 differs from actual bytes"):
                validate_promotion_artifact(path, base_raw=base_raw, proposed_raw=proposed_raw, root=root)

            path, base_raw, proposed_raw = self._artifact(root)
            registry = json.loads((root / PROMOTION_BASKETS_PATH).read_text(encoding="utf-8"))
            member = registry["baskets"][0]["repositories"][3]
            benchmark_path = root / member["recorded_benchmark_path"]
            benchmark_path.write_bytes(benchmark_path.read_bytes().replace(b"50.0", b"50.5", 1))
            with self.assertRaisesRegex(PromotionValidationError, "recorded_benchmark_sha256 differs from actual bytes"):
                validate_promotion_artifact(path, base_raw=base_raw, proposed_raw=proposed_raw, root=root)

            path, base_raw, proposed_raw = self._artifact(root)
            registry = json.loads((root / PROMOTION_BASKETS_PATH).read_text(encoding="utf-8"))
            member = registry["baskets"][0]["repositories"][4]
            (root / member["recorded_benchmark_path"]).unlink()
            with self.assertRaisesRegex(PromotionValidationError, "benchmark file is missing"):
                validate_promotion_artifact(path, base_raw=base_raw, proposed_raw=proposed_raw, root=root)

            path, base_raw, proposed_raw = self._artifact(root)
            artifact = json.loads(path.read_text(encoding="utf-8"))
            artifact["evaluation_basket"]["basket_version"] = 2
            path.write_bytes(_json_bytes(artifact))
            with self.assertRaisesRegex(PromotionValidationError, "not registered"):
                validate_promotion_artifact(path, base_raw=base_raw, proposed_raw=proposed_raw, root=root)

    def test_semantically_invalid_rehashed_registered_datasets_are_rejected(self) -> None:
        mutations = [
            (lambda value: value.clear(), "dataset keys differ"),
            (lambda value: value.__setitem__("repository", "example/wrong"), "repository differs"),
            (lambda value: value.__setitem__("dataset_id", "wrong-dataset"), "dataset_id differs"),
            (lambda value: value.__setitem__("dataset_version", 99), "dataset_version differs"),
            (lambda value: value.__setitem__("schema_version", 2), "schema_version must be 1"),
            (lambda value: value.__setitem__("cases", []), "cases must be a nonempty list"),
            (lambda value: value["cases"][0]["judgments"][0].__setitem__("grade", 4), "grade"),
            (
                lambda value: value["cases"][0]["judgments"][0].__setitem__(
                    "repo_path", "src/elsewhere/missing.py"
                ),
                "judgments are absent from corpus manifest",
            ),
        ]
        for mutate, message in mutations:
            with self.subTest(message=message), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                path, base_raw, proposed_raw = self._artifact(root)
                self._rewrite_registered_file(
                    root,
                    path,
                    repo_index=0,
                    path_field="dataset_path",
                    hash_field="dataset_sha256",
                    mutate=mutate,
                )
                with self.assertRaisesRegex(PromotionValidationError, message):
                    validate_promotion_artifact(path, base_raw=base_raw, proposed_raw=proposed_raw, root=root)

    def test_semantically_invalid_rehashed_registered_corpora_are_rejected(self) -> None:
        def update_inventory(value: dict[str, object]) -> None:
            documents = value.get("documents", [])
            value["document_inventory_sha256"] = _canonical_sha256(documents)

        mutations = [
            (lambda value: value.clear(), "corpus manifest keys differ"),
            (lambda value: value.__setitem__("repository", "example/wrong"), "repository differs"),
            (
                lambda value: value["source_identity"].__setitem__("revision", "f" * 40),
                "source_identity differs",
            ),
            (lambda value: value.__setitem__("schema_version", 2), "schema_version must be 1"),
            (lambda value: (value.__setitem__("documents", []), update_inventory(value)), "documents must be a nonempty list"),
            (
                lambda value: (
                    value["documents"].append(deepcopy(value["documents"][0])),
                    update_inventory(value),
                ),
                "sorted unique canonical paths",
            ),
            (
                lambda value: (
                    value["documents"][0].__setitem__("path", "../escape.py"),
                    update_inventory(value),
                ),
                "unsafe segments",
            ),
            (
                lambda value: (
                    value["documents"][0].__setitem__("content_sha256", "0" * 64),
                    update_inventory(value),
                ),
                "all-zero",
            ),
        ]
        for mutate, message in mutations:
            with self.subTest(message=message), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                path, base_raw, proposed_raw = self._artifact(root)
                self._rewrite_registered_file(
                    root,
                    path,
                    repo_index=1,
                    path_field="corpus_manifest_path",
                    hash_field="corpus_manifest_sha256",
                    mutate=mutate,
                )
                with self.assertRaisesRegex(PromotionValidationError, message):
                    validate_promotion_artifact(path, base_raw=base_raw, proposed_raw=proposed_raw, root=root)

    def test_production_registry_truthfully_has_no_eligible_basket(self) -> None:
        registry = json.loads((ROOT / PROMOTION_BASKETS_PATH).read_text(encoding="utf-8"))
        self.assertEqual(registry, {"baskets": [], "schema_version": 1})
        self.assertEqual(validate_promotion_basket_registry(ROOT), {})

    def test_baseline_candidate_non_authority_inputs_must_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, base_raw, proposed_raw = self._artifact(root)
            artifact = json.loads(path.read_text(encoding="utf-8"))
            artifact["candidate"]["configuration"]["retrieval_options"]["top_k"] = 11
            self._rehash_arm(artifact, "candidate")
            path.write_bytes(_json_bytes(artifact))
            with self.assertRaisesRegex(PromotionValidationError, "non-authority inputs differ"):
                validate_promotion_artifact(path, base_raw=base_raw, proposed_raw=proposed_raw, root=root)

            path, base_raw, proposed_raw = self._artifact(root)
            artifact = json.loads(path.read_text(encoding="utf-8"))
            artifact["candidate"]["configuration"]["retrieval_contract"]["embedding_revision"] += "-other"
            self._rehash_arm(artifact, "candidate")
            path.write_bytes(_json_bytes(artifact))
            with self.assertRaisesRegex(PromotionValidationError, "non-authority inputs differ"):
                validate_promotion_artifact(path, base_raw=base_raw, proposed_raw=proposed_raw, root=root)

    def test_retrieval_options_and_values_are_strictly_safe(self) -> None:
        mutations = [
            (lambda options: options.__setitem__("headers", {"X": "value"}), "keys differ"),
            (lambda options: options.__setitem__("top_k", "10"), "top_k"),
            (lambda options: options.__setitem__("candidates", 1001), "candidates"),
            (lambda options: options.__setitem__("use_ann", "true"), "use_ann"),
        ]
        for mutate, message in mutations:
            with self.subTest(message=message), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                path, base_raw, proposed_raw = self._artifact(root)
                artifact = json.loads(path.read_text(encoding="utf-8"))
                mutate(artifact["baseline"]["configuration"]["retrieval_options"])
                self._rehash_arm(artifact, "baseline")
                path.write_bytes(_json_bytes(artifact))
                with self.assertRaisesRegex(PromotionValidationError, message):
                    validate_promotion_artifact(path, base_raw=base_raw, proposed_raw=proposed_raw, root=root)

        for unsafe in ("https://example.com/model", "api_key=abc", "Bearer abc", "sk-abcdef"):
            with self.subTest(unsafe=unsafe), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                path, base_raw, proposed_raw = self._artifact(root)
                artifact = json.loads(path.read_text(encoding="utf-8"))
                artifact["baseline"]["configuration"]["retrieval_contract"]["embedding_model"] = unsafe
                self._rehash_arm(artifact, "baseline")
                path.write_bytes(_json_bytes(artifact))
                with self.assertRaises(PromotionValidationError):
                    validate_promotion_artifact(path, base_raw=base_raw, proposed_raw=proposed_raw, root=root)

    def test_basket_and_benchmark_links_are_recomputed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, base_raw, proposed_raw = self._artifact(root)
            self._rewrite_artifact(path, lambda value: value["evaluation_basket"].__setitem__("basket_sha256", "2" * 64))
            with self.assertRaisesRegex(PromotionValidationError, "basket SHA-256"):
                validate_promotion_artifact(path, base_raw=base_raw, proposed_raw=proposed_raw, root=root)

            path, base_raw, proposed_raw = self._artifact(root)
            artifact = json.loads(path.read_text(encoding="utf-8"))
            artifact["baseline"]["repositories"][0]["repo_search_score"] = 50.5
            self._rehash_arm(artifact, "baseline")
            path.write_bytes(_json_bytes(artifact))
            with self.assertRaisesRegex(PromotionValidationError, "recorded benchmark result differs"):
                validate_promotion_artifact(path, base_raw=base_raw, proposed_raw=proposed_raw, root=root)

    def test_authority_mismatch_and_policy_failure_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, base_raw, proposed_raw = self._artifact(root)
            self._rewrite_artifact(path, lambda value: value["authority"].__setitem__("proposed_sha256", "2" * 64))
            with self.assertRaisesRegex(PromotionValidationError, "proposed authority SHA-256"):
                validate_promotion_artifact(path, base_raw=base_raw, proposed_raw=proposed_raw, root=root)

            path, base_raw, proposed_raw = self._artifact(root, passing=False)
            with self.assertRaisesRegex(PromotionValidationError, "does not pass"):
                validate_promotion_artifact(path, base_raw=base_raw, proposed_raw=proposed_raw, root=root)

    def test_command_requires_base_and_explicit_introduction(self) -> None:
        missing = subprocess.run(
            [sys.executable, "scripts/validate_ranking_promotion.py"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            env={key: value for key, value in os.environ.items() if not key.startswith("BUOY_RANKING_")},
        )
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("comparison event/base is missing", missing.stderr)

        explicit = subprocess.run(
            [
                sys.executable,
                "scripts/validate_ranking_promotion.py",
                "--base-ref",
                "HEAD",
                "--allow-authority-introduction",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(explicit.returncode, 0, explicit.stderr)
        self.assertIn(json.loads(explicit.stdout)["authority"]["classification"], {"authority-introduction", "unchanged"})


if __name__ == "__main__":
    unittest.main()
