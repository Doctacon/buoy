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
EVALUATION_VERSIONS_PATH = Path("src/buoy_search/data/repo_evaluation_versions.json")
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
EVALUATION_REGISTRY_KEYS = {
    "active_buoy_dataset_id",
    "active_buoy_dataset_version",
    "schema_version",
    "versions",
}
EVALUATION_VERSION_IDENTITY_KEYS = {
    "baseline_status",
    "dataset_id",
    "dataset_path",
    "dataset_sha256",
    "dataset_version",
}
HISTORICAL_EVALUATION_VERSION_KEYS = EVALUATION_VERSION_IDENTITY_KEYS | {
    "corpus_manifest_path",
    "corpus_manifest_sha256",
    "historical_contract_inventory_path",
    "historical_contract_inventory_sha256",
    "source_snapshot",
}
PENDING_EVALUATION_VERSION_KEYS = EVALUATION_VERSION_IDENTITY_KEYS | {
    "path_membership_manifest_path",
    "path_membership_manifest_sha256",
    "promotion_eligible",
}
V2_ARTIFACT_KEYS = {
    "baseline_status",
    "dataset_id",
    "dataset_version",
    "derived_from",
    "migration",
    "path_membership_manifest_path",
    "path_membership_manifest_sha256",
    "promotion_eligible",
    "schema_version",
}
V2_MANIFEST_KEYS = {
    "baseline_status",
    "dataset_id",
    "dataset_version",
    "manifest_id",
    "manifest_kind",
    "path_set_sha256",
    "promotion_eligible",
    "schema_version",
    "selected_path_count",
    "selected_repo_paths",
}


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


def _path_set_sha256(paths: list[str]) -> str:
    return hashlib.sha256("".join(f"{path}\n" for path in paths).encode("utf-8")).hexdigest()


def validate_versioned_buoy_evaluations(root: Path = ROOT) -> dict[str, Any]:
    """Validate immutable Buoy v1/v2 and the baseline-pending current v3."""

    registry = _read_json_object(root / EVALUATION_VERSIONS_PATH)
    _require_exact_keys(registry, EVALUATION_REGISTRY_KEYS, "evaluation version registry")
    _require(registry["schema_version"] == 1, "evaluation registry schema_version must be 1")
    _require(registry["active_buoy_dataset_id"] == "buoy-search-repo-search-seed", "unexpected active Buoy dataset id")
    _require(registry["active_buoy_dataset_version"] == 3, "active Buoy dataset version must be 3")
    versions = registry["versions"]
    _require(isinstance(versions, list) and len(versions) == 3, "evaluation registry must contain v1, v2, and v3")
    _require([item.get("dataset_version") for item in versions if isinstance(item, dict)] == [1, 2, 3], "evaluation versions must be ordered v1, v2, v3")
    v1, v2, v3 = versions
    _require_exact_keys(v1, HISTORICAL_EVALUATION_VERSION_KEYS, "Buoy evaluation v1 registry entry")
    _require_exact_keys(v2, PENDING_EVALUATION_VERSION_KEYS, "Buoy evaluation v2 registry entry")
    _require_exact_keys(v3, PENDING_EVALUATION_VERSION_KEYS, "Buoy evaluation v3 registry entry")
    for version in versions:
        _require(version["dataset_id"] == "buoy-search-repo-search-seed", "Buoy evaluation dataset id mismatch")
        _require(version["baseline_status"] in {"pending", "recorded"}, "invalid baseline status")
        _require(bool(HEX_64.fullmatch(str(version["dataset_sha256"]))), "invalid dataset_sha256")
        _require(_sha256(root / version["dataset_path"]) == version["dataset_sha256"], f"Buoy v{version['dataset_version']} dataset SHA-256 mismatch")
    _require(bool(HEX_64.fullmatch(str(v1["corpus_manifest_sha256"]))), "invalid historical corpus_manifest_sha256")
    _require(_sha256(root / v1["corpus_manifest_path"]) == v1["corpus_manifest_sha256"], "Buoy v1 corpus manifest SHA-256 mismatch")
    for pending in (v2, v3):
        version = pending["dataset_version"]
        _require(bool(HEX_64.fullmatch(str(pending["path_membership_manifest_sha256"]))), "invalid pending path_membership_manifest_sha256")
        _require(
            _sha256(root / pending["path_membership_manifest_path"]) == pending["path_membership_manifest_sha256"],
            f"Buoy v{version} path-membership manifest SHA-256 mismatch",
        )
        _require("corpus_manifest_path" not in pending and "corpus_manifest_sha256" not in pending, f"pending Buoy v{version} cannot claim corpus identity")
        _require("source_snapshot" not in pending, f"pending Buoy v{version} cannot claim a source snapshot")
        _require(pending["promotion_eligible"] is False, f"pending Buoy v{version} cannot be promotion eligible")

    _require(v1["dataset_sha256"] == "60008af2950ae8fa27da59c0af737ebf5b4a3e618680bfa113ec75951d338792", "historical Buoy v1 bytes changed")
    _require(v2["dataset_sha256"] == "691566d85d1187717cfc06daebeb8bb965d9b337787050fab071afe8fad4d0ae", "immutable Buoy v2 dataset bytes changed")
    _require(v2["path_membership_manifest_sha256"] == "4b7739515d15cd14b9cf9e374e5318c7fa9e7a3bb7e208f25878e6489751068b", "immutable Buoy v2 path-membership bytes changed")
    _require(v1["baseline_status"] == "pending", "historical Buoy v1 baseline status must remain pending")
    _require(v2["baseline_status"] == "pending", "immutable Buoy v2 baseline status must remain pending")
    _require(v3["baseline_status"] == "pending", "current Buoy v3 baseline status must be pending")
    _require(_sha256(root / v1["historical_contract_inventory_path"]) == v1["historical_contract_inventory_sha256"], "historical inventory SHA-256 mismatch")

    v1_dataset = _read_json_object(root / v1["dataset_path"])
    v2_dataset = _read_json_object(root / v2["dataset_path"])
    v3_dataset = _read_json_object(root / v3["dataset_path"])
    _require(set(v1_dataset) == {"cases", "metadata"}, "historical Buoy v1 dataset schema differs")
    _require(set(v2_dataset) == {"artifact", "cases", "metadata"}, "immutable Buoy v2 dataset schema differs")
    _require(set(v3_dataset) == {"artifact", "cases", "metadata"}, "current Buoy v3 dataset schema differs")
    artifact = v2_dataset["artifact"]
    _require(isinstance(artifact, dict), "current Buoy v2 artifact must be an object")
    _require_exact_keys(artifact, V2_ARTIFACT_KEYS, "current Buoy v2 artifact")
    _require(artifact["schema_version"] == 1, "current Buoy artifact schema_version must be 1")
    _require(artifact["dataset_id"] == v2["dataset_id"] and artifact["dataset_version"] == 2, "current Buoy artifact identity mismatch")
    _require(artifact["baseline_status"] == "pending", "current Buoy artifact must be baseline pending")
    _require(artifact["promotion_eligible"] is False, "current pending Buoy artifact cannot be promotion eligible")
    _require("corpus_manifest_path" not in artifact and "corpus_manifest_sha256" not in artifact, "current pending Buoy artifact cannot claim corpus identity")
    _require(
        artifact["path_membership_manifest_path"] == v2["path_membership_manifest_path"],
        "current Buoy path-membership manifest path differs from registry",
    )
    _require(
        artifact["path_membership_manifest_sha256"] == v2["path_membership_manifest_sha256"],
        "current Buoy path-membership manifest hash differs from registry",
    )
    derived_from = artifact["derived_from"]
    _require(isinstance(derived_from, dict), "current Buoy derived_from must be an object")
    expected_derived_from = {
        key: v1[key]
        for key in ("corpus_manifest_path", "corpus_manifest_sha256", "dataset_id", "dataset_path", "dataset_sha256", "dataset_version")
    }
    _require(derived_from == expected_derived_from, "current Buoy v2 lineage differs from v1 registry")

    migration = artifact["migration"]
    _require(isinstance(migration, dict) and set(migration) == {"kind", "path_map"}, "current Buoy migration schema differs")
    _require(migration["kind"] == "repo-path-map-v1", "current Buoy migration kind differs")
    path_map_rows = migration["path_map"]
    _require(isinstance(path_map_rows, list) and path_map_rows, "current Buoy path map must be non-empty")
    _require(all(isinstance(row, dict) and set(row) == {"from", "to"} for row in path_map_rows), "current Buoy path map row schema differs")
    _require(path_map_rows == sorted(path_map_rows, key=lambda row: row["from"]), "current Buoy path map must be sorted")
    path_map = {row["from"]: row["to"] for row in path_map_rows}
    _require(len(path_map) == len(path_map_rows), "current Buoy path map sources must be unique")
    _require(len(set(path_map.values())) == len(path_map), "current Buoy path map targets must be unique")
    _require(all(source != target for source, target in path_map.items()), "current Buoy path map cannot contain identity mappings")

    expected_metadata = dict(v1_dataset["metadata"])
    expected_metadata["id"] = "buoy-search-repo-search-seed-v2"
    _require(v2_dataset["metadata"] == expected_metadata, "current Buoy metadata drifted beyond version identity")
    expected_cases = json.loads(json.dumps(v1_dataset["cases"]))
    observed_mappings: set[str] = set()
    for case in expected_cases:
        for judgment in case["judgments"]:
            source = judgment["repo_path"]
            if source in path_map:
                judgment["repo_path"] = path_map[source]
                observed_mappings.add(source)
    _require(observed_mappings == set(path_map), "current Buoy path map contains unused or missing mappings")
    _require(v2_dataset["cases"] == expected_cases, "current Buoy judgments drifted beyond declared path mapping")

    v2_manifest = _read_json_object(root / v2["path_membership_manifest_path"])
    _require_exact_keys(v2_manifest, V2_MANIFEST_KEYS, "immutable Buoy v2 path manifest")
    _require(v2_manifest["dataset_id"] == v2["dataset_id"] and v2_manifest["dataset_version"] == 2, "immutable Buoy v2 path manifest identity mismatch")
    v2_paths = v2_manifest["selected_repo_paths"]
    _require(isinstance(v2_paths, list) and v2_paths == sorted(set(v2_paths)), "immutable Buoy v2 selected paths must be sorted and unique")
    _require(v2_manifest["selected_path_count"] == len(v2_paths), "immutable Buoy v2 selected path count mismatch")
    _require(v2_manifest["path_set_sha256"] == _path_set_sha256(v2_paths), "immutable Buoy v2 path-set SHA-256 mismatch")

    v3_artifact = v3_dataset["artifact"]
    _require(isinstance(v3_artifact, dict), "current Buoy v3 artifact must be an object")
    _require_exact_keys(v3_artifact, V2_ARTIFACT_KEYS, "current Buoy v3 artifact")
    _require(v3_artifact["schema_version"] == 1, "current Buoy v3 artifact schema_version must be 1")
    _require(v3_artifact["dataset_id"] == v3["dataset_id"] and v3_artifact["dataset_version"] == 3, "current Buoy v3 artifact identity mismatch")
    _require(v3_artifact["baseline_status"] == "pending", "current Buoy v3 artifact must be baseline pending")
    _require(v3_artifact["promotion_eligible"] is False, "current pending Buoy v3 cannot be promotion eligible")
    _require("corpus_manifest_path" not in v3_artifact and "corpus_manifest_sha256" not in v3_artifact, "current pending Buoy v3 cannot claim corpus identity")
    _require(v3_artifact["path_membership_manifest_path"] == v3["path_membership_manifest_path"], "current Buoy v3 path-membership path differs from registry")
    _require(v3_artifact["path_membership_manifest_sha256"] == v3["path_membership_manifest_sha256"], "current Buoy v3 path-membership hash differs from registry")
    expected_v3_lineage = {
        key: v2[key]
        for key in (
            "dataset_id", "dataset_path", "dataset_sha256", "dataset_version",
            "path_membership_manifest_path", "path_membership_manifest_sha256",
        )
    }
    _require(v3_artifact["derived_from"] == expected_v3_lineage, "current Buoy v3 lineage differs from immutable v2")

    v3_migration = v3_artifact["migration"]
    _require(isinstance(v3_migration, dict) and set(v3_migration) == {"kind", "path_map"}, "current Buoy v3 migration schema differs")
    _require(v3_migration["kind"] == "repo-path-map-v1", "current Buoy v3 migration kind differs")
    v3_path_rows = v3_migration["path_map"]
    _require(isinstance(v3_path_rows, list) and all(isinstance(row, dict) and set(row) == {"from", "to"} for row in v3_path_rows), "current Buoy v3 path map row schema differs")
    _require(v3_path_rows == sorted(v3_path_rows, key=lambda row: row["from"]), "current Buoy v3 path map must be sorted")
    v3_path_map = {row["from"]: row["to"] for row in v3_path_rows}
    expected_v3_path_map = {
        "tests/test_cli.py": "tests/cli/test_cli.py",
        "tests/test_crawler.py": "tests/indexing/test_crawler.py",
        "tests/test_evals.py": "tests/evals/test_evals.py",
        "tests/test_github_repo.py": "tests/indexing/test_github_repo.py",
        "tests/test_retriever.py": "tests/retrieval/test_retriever.py",
    }
    _require(v3_path_map == expected_v3_path_map, "current Buoy v3 must contain exactly the approved five test-path mappings")

    expected_v3_metadata = dict(v2_dataset["metadata"])
    expected_v3_metadata["id"] = "buoy-search-repo-search-seed-v3"
    _require(v3_dataset["metadata"] == expected_v3_metadata, "current Buoy v3 metadata drifted beyond version identity")
    expected_v3_cases = json.loads(json.dumps(v2_dataset["cases"]))
    observed_v3_mappings: set[str] = set()
    for case in expected_v3_cases:
        for judgment in case["judgments"]:
            source = judgment["repo_path"]
            if source in v3_path_map:
                judgment["repo_path"] = v3_path_map[source]
                observed_v3_mappings.add(source)
    _require(observed_v3_mappings == set(v3_path_map), "current Buoy v3 path map contains unused or missing mappings")
    _require(v3_dataset["cases"] == expected_v3_cases, "current Buoy v3 judgments drifted beyond declared path mapping")

    v3_manifest = _read_json_object(root / v3["path_membership_manifest_path"])
    _require_exact_keys(v3_manifest, V2_MANIFEST_KEYS, "current Buoy v3 path manifest")
    _require(v3_manifest["schema_version"] == 1 and v3_manifest["manifest_kind"] == "active-path-membership-v1", "current Buoy v3 path manifest contract differs")
    _require(v3_manifest["dataset_id"] == v3["dataset_id"] and v3_manifest["dataset_version"] == 3, "current Buoy v3 path manifest identity mismatch")
    _require(v3_manifest["baseline_status"] == "pending" and v3_manifest["promotion_eligible"] is False, "current Buoy v3 path manifest authority differs")
    selected_paths = v3_manifest["selected_repo_paths"]
    _require(isinstance(selected_paths, list) and selected_paths == sorted(set(selected_paths)), "current Buoy v3 selected paths must be sorted and unique")
    judgment_paths = sorted({judgment["repo_path"] for case in v3_dataset["cases"] for judgment in case["judgments"]})
    _require(selected_paths == judgment_paths, "current Buoy v3 path manifest must equal current judgment paths")
    _require(v3_manifest["selected_path_count"] == len(selected_paths), "current Buoy v3 selected path count mismatch")
    _require(v3_manifest["path_set_sha256"] == _path_set_sha256(selected_paths), "current Buoy v3 path-set SHA-256 mismatch")
    missing = [path for path in selected_paths if not (root / path).is_file()]
    _require(not missing, f"current Buoy v3 judgment paths do not exist: {missing}")

    return {
        "active_dataset_version": 3,
        "baseline_status": "pending",
        "current_dataset_sha256": v3["dataset_sha256"],
        "current_path_membership_manifest_sha256": v3["path_membership_manifest_sha256"],
        "historical_dataset_sha256": v1["dataset_sha256"],
        "immutable_v2_dataset_sha256": v2["dataset_sha256"],
        "mapped_paths": len(v3_path_map),
        "promotion_eligible": False,
    }


def validate_contract(root: Path = ROOT, inventory_relative_path: Path = INVENTORY_PATH) -> dict[str, Any]:
    """Validate all contract inputs and return a deterministic summary."""

    versioned_buoy = validate_versioned_buoy_evaluations(root)
    registry = _read_json_object(root / EVALUATION_VERSIONS_PATH)
    historical_buoy_path = Path(registry["versions"][0]["dataset_path"])
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
        dataset_path = root / (historical_buoy_path if repo_key == "buoy" else Path(dataset_relative_path))
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
        "versioned_buoy": versioned_buoy,
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
