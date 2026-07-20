#!/usr/bin/env python3
"""Validate the frozen repository-ranking contract using only the standard library."""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = Path(
    ".10x/evidence/.storage/2026-07-20-repo-ranking-experiment-contract-inventory.json"
)
EXPECTED_REPOS = {
    "black": 5,
    "buoy": 10,
    "click": 10,
    "django": 5,
    "flask": 5,
    "httpx": 5,
    "mkdocs": 5,
    "pydantic": 5,
    "pytest": 10,
    "requests": 10,
    "rich": 5,
    "ruff": 5,
    "typer": 10,
}
EXPERIMENT_NAMESPACE_PATTERN = (
    "github-{owner_slug}-{repo_slug}-exp-{experiment_slug}-"
    "{contract_sha256_12}-v{positive_integer}"
)
INVENTORY_KEYS = {
    "composite_identity_count",
    "contract_id",
    "dataset_bundle_sha256",
    "dataset_count",
    "duplicate_local_case_ids_across_repositories",
    "experiment_namespace_pattern",
    "explicit_zero_judgment_count",
    "folds",
    "identities",
    "inventory_payload_sha256",
    "judgment_count",
    "repositories",
    "schema_version",
    "source_path_manifest_bundle_path",
    "source_path_manifest_bundle_sha256",
    "unique_composite_identity_count",
    "validation_errors",
}
INVENTORY_REPOSITORY_KEYS = {
    "baseline_namespace",
    "baseline_namespace_status",
    "case_count",
    "dataset_path",
    "dataset_sha256",
    "embedding_model",
    "experiment_namespace_pattern",
    "explicit_zero_judgment_count",
    "judgment_count",
    "manifest_chunk_count",
    "missing_judgment_paths",
    "repo_key",
    "repository",
    "selected_corpus_artifact_hash",
    "source_commit",
    "source_manifest_sha256",
    "source_plan_sha256",
    "sufficient",
    "validated_judgment_paths",
}
SOURCE_REPOSITORY_KEYS = {
    "baseline_namespace",
    "baseline_namespace_status",
    "experiment_namespace_pattern",
    "original_manifest_sha256",
    "original_plan_sha256",
    "repo_key",
    "repository",
    "selected_corpus_artifact_hash",
    "selected_path_count",
    "selected_repo_paths",
    "selected_row_count",
    "source_commit",
}
HEX_64 = re.compile(r"[0-9a-f]{64}")
COMMIT_SHA = re.compile(r"[0-9a-f]{40}")


class ContractValidationError(ValueError):
    """Raised when checked-in ranking-contract data is inconsistent."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractValidationError(message)


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractValidationError(f"cannot load {path}: {exc}") from exc
    _require(isinstance(value, dict), f"{path} must contain a JSON object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    _require(actual == expected, f"{label} keys differ: missing={sorted(expected - actual)}, extra={sorted(actual - expected)}")


def _validate_source_bundle(
    bundle: dict[str, Any], inventory_repositories: list[dict[str, Any]]
) -> dict[str, set[str]]:
    _require_exact_keys(
        bundle,
        {"experiment_namespace_pattern", "repositories", "schema_version"},
        "source-path bundle",
    )
    _require(bundle["schema_version"] == 1, "source-path bundle schema_version must be 1")
    _require(
        bundle["experiment_namespace_pattern"] == EXPERIMENT_NAMESPACE_PATTERN,
        "source-path bundle namespace pattern differs from frozen prose",
    )
    source_repositories = bundle["repositories"]
    _require(isinstance(source_repositories, list), "source-path repositories must be a list")
    source_keys = [item.get("repo_key") for item in source_repositories if isinstance(item, dict)]
    _require(source_keys == sorted(EXPECTED_REPOS), "source-path repositories must use sorted expected repo keys")

    inventory_by_key = {item["repo_key"]: item for item in inventory_repositories}
    paths_by_key: dict[str, set[str]] = {}
    for source in source_repositories:
        repo_key = source.get("repo_key", "<missing>")
        _require_exact_keys(source, SOURCE_REPOSITORY_KEYS, f"source-path repository {repo_key}")
        paths = source["selected_repo_paths"]
        _require(isinstance(paths, list) and all(isinstance(path, str) and path for path in paths), f"{repo_key}: selected_repo_paths must be non-empty strings")
        _require(paths == sorted(set(paths)), f"{repo_key}: selected_repo_paths must be sorted and distinct")
        _require(source["selected_path_count"] == len(paths), f"{repo_key}: selected_path_count mismatch")
        _require(isinstance(source["selected_row_count"], int) and source["selected_row_count"] >= len(paths), f"{repo_key}: invalid selected_row_count")
        _require(source["baseline_namespace_status"] in {"existing", "pending_approval"}, f"{repo_key}: invalid baseline namespace status")
        _require(source["experiment_namespace_pattern"] == EXPERIMENT_NAMESPACE_PATTERN, f"{repo_key}: namespace pattern differs from frozen prose")
        _require(bool(COMMIT_SHA.fullmatch(str(source["source_commit"]))), f"{repo_key}: invalid source commit")
        for field in ("original_manifest_sha256", "original_plan_sha256", "selected_corpus_artifact_hash"):
            _require(bool(HEX_64.fullmatch(str(source[field]))), f"{repo_key}: invalid {field}")

        inventory = inventory_by_key[repo_key]
        crosswalk = {
            "baseline_namespace": "baseline_namespace",
            "baseline_namespace_status": "baseline_namespace_status",
            "experiment_namespace_pattern": "experiment_namespace_pattern",
            "original_manifest_sha256": "source_manifest_sha256",
            "original_plan_sha256": "source_plan_sha256",
            "repo_key": "repo_key",
            "repository": "repository",
            "selected_corpus_artifact_hash": "selected_corpus_artifact_hash",
            "selected_row_count": "manifest_chunk_count",
            "source_commit": "source_commit",
        }
        for source_field, inventory_field in crosswalk.items():
            _require(source[source_field] == inventory[inventory_field], f"{repo_key}: {source_field} differs between source bundle and inventory")
        paths_by_key[repo_key] = set(paths)
    return paths_by_key


def validate_contract(root: Path = ROOT, inventory_relative_path: Path = INVENTORY_PATH) -> dict[str, Any]:
    """Validate all contract inputs and return a deterministic summary."""

    inventory_path = root / inventory_relative_path
    inventory = _read_json_object(inventory_path)
    _require_exact_keys(inventory, INVENTORY_KEYS, "inventory")
    _require(inventory["schema_version"] == 1, "inventory schema_version must be 1")
    _require(inventory["contract_id"] == "repo-ranking-experiment-contract-v1", "unexpected contract_id")
    _require(inventory["experiment_namespace_pattern"] == EXPERIMENT_NAMESPACE_PATTERN, "inventory namespace pattern differs from frozen prose")
    inventory_payload = {key: value for key, value in inventory.items() if key != "inventory_payload_sha256"}
    inventory_payload_sha256 = hashlib.sha256(
        json.dumps(
            inventory_payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    _require(inventory_payload_sha256 == inventory["inventory_payload_sha256"], "inventory payload SHA-256 mismatch")

    repositories = inventory["repositories"]
    _require(isinstance(repositories, list), "inventory repositories must be a list")
    repository_keys = [item.get("repo_key") for item in repositories if isinstance(item, dict)]
    _require(repository_keys == sorted(EXPECTED_REPOS), "inventory repositories must use sorted expected repo keys")
    for repository in repositories:
        _require_exact_keys(repository, INVENTORY_REPOSITORY_KEYS, f"inventory repository {repository.get('repo_key', '<missing>')}")
        _require("source_artifact_hash" not in repository, "source_artifact_hash was replaced by selected_corpus_artifact_hash")

    bundle_relative_path = Path(str(inventory["source_path_manifest_bundle_path"]))
    bundle_path = root / bundle_relative_path
    _require(_sha256(bundle_path) == inventory["source_path_manifest_bundle_sha256"], "source-path bundle SHA-256 mismatch")
    paths_by_key = _validate_source_bundle(_read_json_object(bundle_path), repositories)

    identities: list[dict[str, str]] = []
    local_id_repositories: dict[str, set[str]] = defaultdict(set)
    dataset_bundle_rows: list[str] = []
    total_judgments = 0
    total_explicit_zero = 0
    observed_missing: dict[str, list[dict[str, str]]] = {}

    for repository in repositories:
        repo_key = repository["repo_key"]
        expected_cases = EXPECTED_REPOS[repo_key]
        dataset_relative_path = str(repository["dataset_path"])
        dataset_path = root / dataset_relative_path
        dataset_sha256 = _sha256(dataset_path)
        _require(dataset_sha256 == repository["dataset_sha256"], f"{repo_key}: dataset SHA-256 mismatch")
        dataset_bundle_rows.append(f"{dataset_relative_path}\0{dataset_sha256}\n")
        dataset = _read_json_object(dataset_path)
        _require(set(dataset) == {"cases", "metadata"}, f"{repo_key}: dataset top-level schema differs")
        _require(isinstance(dataset["metadata"], dict), f"{repo_key}: metadata must be an object")
        _require(isinstance(dataset["cases"], list), f"{repo_key}: cases must be a list")
        _require(len(dataset["cases"]) == expected_cases == repository["case_count"], f"{repo_key}: case count mismatch")

        repo_judgments = 0
        repo_explicit_zero = 0
        missing: list[dict[str, str]] = []
        for case in dataset["cases"]:
            _require(isinstance(case, dict), f"{repo_key}: case must be an object")
            _require(isinstance(case.get("id"), str) and case["id"], f"{repo_key}: case id must be a non-empty string")
            _require(isinstance(case.get("question"), str) and case["question"], f"{repo_key}:{case['id']}: question must be non-empty")
            _require(isinstance(case.get("judgments"), list), f"{repo_key}:{case['id']}: judgments must be a list")
            case_id = case["id"]
            composite_case_id = f"{repo_key}:{case_id}"
            identities.append({"case_id": case_id, "composite_case_id": composite_case_id, "repo_key": repo_key})
            local_id_repositories[case_id].add(repo_key)
            for judgment in case["judgments"]:
                _require(isinstance(judgment, dict), f"{composite_case_id}: judgment must be an object")
                _require(isinstance(judgment.get("repo_path"), str) and judgment["repo_path"], f"{composite_case_id}: judgment repo_path must be non-empty")
                _require(isinstance(judgment.get("grade"), int), f"{composite_case_id}: judgment grade must be an integer")
                repo_judgments += 1
                if judgment["grade"] == 0:
                    repo_explicit_zero += 1
                if judgment["repo_path"] not in paths_by_key[repo_key]:
                    missing.append({"composite_case_id": composite_case_id, "repo_path": judgment["repo_path"]})

        _require(repo_judgments == repository["judgment_count"], f"{repo_key}: judgment count mismatch")
        _require(repo_explicit_zero == repository["explicit_zero_judgment_count"], f"{repo_key}: explicit-zero count mismatch")
        _require(missing == repository["missing_judgment_paths"], f"{repo_key}: path-membership result differs from inventory")
        _require(repository["validated_judgment_paths"] == repo_judgments - len(missing), f"{repo_key}: validated path count mismatch")
        expected_sufficient = not missing and repository["baseline_namespace_status"] == "existing"
        _require(repository["sufficient"] is expected_sufficient, f"{repo_key}: sufficient status mismatch")
        observed_missing[repo_key] = missing
        total_judgments += repo_judgments
        total_explicit_zero += repo_explicit_zero

    identity_tuples = [(item["repo_key"], item["case_id"]) for item in identities]
    _require(len(identity_tuples) == len(set(identity_tuples)) == 90, "composite identities must be 90 and unique")
    _require(identities == inventory["identities"], "identity inventory differs from regenerated identities")
    duplicates = {case_id: sorted(repo_keys) for case_id, repo_keys in local_id_repositories.items() if len(repo_keys) > 1}
    _require(duplicates == inventory["duplicate_local_case_ids_across_repositories"], "cross-repository duplicate local IDs differ")
    _require(total_judgments == inventory["judgment_count"] == 369, "judgment total must be 369")
    _require(total_explicit_zero == inventory["explicit_zero_judgment_count"], "explicit-zero total mismatch")
    _require(inventory["dataset_count"] == len(repositories) == 13, "dataset count must be 13")
    _require(inventory["composite_identity_count"] == inventory["unique_composite_identity_count"] == 90, "inventory identity counts must be 90")

    dataset_bundle_sha256 = hashlib.sha256("".join(dataset_bundle_rows).encode("utf-8")).hexdigest()
    _require(dataset_bundle_sha256 == inventory["dataset_bundle_sha256"], "dataset bundle SHA-256 mismatch")

    folds = inventory["folds"]
    _require(isinstance(folds, list) and len(folds) == 13, "inventory must contain 13 folds")
    for index, (fold, held_out) in enumerate(zip(folds, repository_keys), 1):
        expected_fold = {
            "fold_id": f"fold-{index:02d}",
            "held_out_repo_key": held_out,
            "training_repo_keys": [key for key in repository_keys if key != held_out],
        }
        _require(fold == expected_fold, f"fold-{index:02d} assignment differs")

    pending = [item["repo_key"] for item in repositories if item["baseline_namespace_status"] == "pending_approval"]
    insufficient = [item["repo_key"] for item in repositories if not item["sufficient"]]
    return {
        "composite_identities": len(identities),
        "dataset_bundle_sha256": dataset_bundle_sha256,
        "datasets": len(repositories),
        "folds": len(folds),
        "insufficient_repositories": insufficient,
        "inventory_payload_sha256": inventory_payload_sha256,
        "inventory_sha256": _sha256(inventory_path),
        "judgments": total_judgments,
        "pending_baseline_approval": pending,
        "source_path_manifest_bundle_sha256": inventory["source_path_manifest_bundle_sha256"],
    }


def main() -> int:
    try:
        summary = validate_contract()
    except (ContractValidationError, OSError) as exc:
        print(f"ranking contract validation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
