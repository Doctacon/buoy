#!/usr/bin/env python3
"""Validate ranking-default authority changes without running a benchmark."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from typing import Any, Literal, Mapping

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_PATH = Path("src/buoy_search/data/ranking_defaults.json")
EVALUATION_VERSIONS_PATH = Path("src/buoy_search/data/repo_evaluation_versions.json")
PROMOTION_BASKETS_PATH = Path("src/buoy_search/data/repo_ranking_promotion_baskets.json")
PROMOTION_ARTIFACT_DIR = Path(".10x/evidence/.storage/ranking-promotions")
INTRODUCTION_AUTHORITY_SHA256 = "ec33b7921b163cd5451cab3c935600b6f2ce90307d23375d8f67c7713a5a9dfc"
EXPECTED_REPOS = {
    "black",
    "buoy",
    "click",
    "django",
    "flask",
    "httpx",
    "mkdocs",
    "pydantic",
    "pytest",
    "requests",
    "rich",
    "ruff",
    "typer",
}
HEX_64 = re.compile(r"[0-9a-f]{64}")
SAFE_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/@+-]{0,127}")
UNSAFE_VALUE = re.compile(
    r"(?:[A-Za-z][A-Za-z0-9+.-]*://|bearer\s|api[_-]?key|authorization|credential|password|secret|token\s*[:=]|(?:^|[^A-Za-z0-9])sk-[A-Za-z0-9])",
    re.IGNORECASE,
)
_AUTHORITY_KEYS = {"authority_revision", "repository", "schema_version", "website"}
_DEFAULT_KEYS = {
    "candidates",
    "ranking_aggregation",
    "ranking_mode",
    "ranking_pool",
    "ranking_profile",
}
_ARTIFACT_KEYS = {
    "artifact_id",
    "authority",
    "baseline",
    "candidate",
    "evaluation_basket",
    "policy",
    "schema_version",
}
_BASKET_REFERENCE_KEYS = {"basket_id", "basket_sha256", "basket_version"}
_BASKET_REGISTRY_KEYS = {"baskets", "schema_version"}
_BASKET_KEYS = {
    "baseline_status",
    "basket_id",
    "basket_sha256",
    "basket_version",
    "repositories",
    "schema_version",
}
_BASKET_REPOSITORY_KEYS = {
    "baseline_status",
    "corpus_manifest_path",
    "corpus_manifest_sha256",
    "dataset_id",
    "dataset_path",
    "dataset_sha256",
    "dataset_version",
    "document_count",
    "document_inventory_sha256",
    "recorded_benchmark_path",
    "recorded_benchmark_sha256",
    "repo_key",
    "repository",
    "source_identity",
}
_RECORDED_BENCHMARK_KEYS = {
    "benchmark_id",
    "corpus_manifest_sha256",
    "dataset_id",
    "dataset_sha256",
    "dataset_version",
    "repo_key",
    "repository",
    "result",
    "retrieval_contract",
    "retrieval_options",
    "schema_version",
    "source_identity",
}
_DATASET_KEYS = {"cases", "dataset_id", "dataset_version", "repository", "schema_version"}
_DATASET_CASE_KEYS = {"id", "judgments", "question"}
_DATASET_JUDGMENT_KEYS = {"grade", "reason", "repo_path"}
_CORPUS_MANIFEST_KEYS = {
    "document_inventory_sha256",
    "documents",
    "manifest_id",
    "repository",
    "schema_version",
    "source_identity",
}
_CORPUS_DOCUMENT_KEYS = {"content_sha256", "path"}
_SOURCE_IDENTITY_KEYS = {"kind", "revision"}
_ARM_KEYS = {"benchmark_id", "benchmark_sha256", "configuration", "repositories"}
_CONFIGURATION_KEYS = {
    "evaluation_basket_sha256",
    "ranking_defaults",
    "retrieval_contract",
    "retrieval_options",
}
_RETRIEVAL_CONTRACT_KEYS = {
    "contract_revision",
    "embedding_model",
    "embedding_revision",
    "reranker_model",
    "reranker_revision",
}
_RETRIEVAL_OPTION_KEYS = {"candidates", "top_k", "use_ann", "use_bm25"}
_RESULT_KEYS = {"precision_at_5", "repo_key", "repo_search_score"}


class PromotionValidationError(ValueError):
    """Raised when a ranking promotion request is inconsistent or incomplete."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PromotionValidationError(message)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        _require(key not in result, f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _load_json_bytes(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
    except PromotionValidationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PromotionValidationError(f"{label} is not valid UTF-8 JSON: {exc}") from exc
    _require(isinstance(value, dict), f"{label} must contain a JSON object")
    return value


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        return _load_json_bytes(path.read_bytes(), label)
    except OSError as exc:
        raise PromotionValidationError(f"cannot read {label} at {path}: {exc}") from exc


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    _require(
        actual == expected,
        f"{label} keys differ: missing={sorted(expected - actual)}, extra={sorted(actual - expected)}",
    )


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()


def _require_hash(value: Any, label: str) -> str:
    _require(isinstance(value, str) and bool(HEX_64.fullmatch(value)), f"{label} must be 64 lowercase hex")
    _require(value != "0" * 64, f"{label} cannot be the all-zero placeholder")
    return value


def _require_safe_identifier(value: Any, label: str) -> str:
    _require(isinstance(value, str) and bool(SAFE_IDENTIFIER.fullmatch(value)), f"{label} is not a bounded safe identifier")
    _require(not UNSAFE_VALUE.search(value), f"{label} contains a prohibited URL or credential-like value")
    return value


def validate_authority_object(value: dict[str, Any], label: str = "ranking authority") -> None:
    """Validate a complete ranking-default authority without pinning one revision."""

    _require_exact_keys(value, _AUTHORITY_KEYS, label)
    _require(value["schema_version"] == 1, f"{label} schema_version must be 1")
    _require_safe_identifier(value["authority_revision"], f"{label} authority_revision")
    allowed = {
        "ranking_mode": {"chunk", "file", "page"},
        "ranking_profile": {"none", "repo_code"},
        "ranking_aggregation": {"max", "adaptive_sum_3", "capped_sum_3"},
    }
    for kind in ("repository", "website"):
        defaults = value[kind]
        _require(isinstance(defaults, dict), f"{label} {kind} defaults must be an object")
        _require_exact_keys(defaults, _DEFAULT_KEYS, f"{label} {kind} defaults")
        for field in ("candidates", "ranking_pool"):
            item = defaults[field]
            _require(
                isinstance(item, int) and not isinstance(item, bool) and item > 0,
                f"{label} {kind} {field} must be a positive integer",
            )
        for field, values in allowed.items():
            _require(defaults[field] in values, f"{label} {kind} {field} is unsupported")
    _require(
        value["repository"]["candidates"] == value["website"]["candidates"],
        f"{label} must retain one shared candidates default",
    )


def _git(root: Path, *args: str, allow_missing_path: bool = False) -> bytes | None:
    completed = subprocess.run(["git", *args], cwd=root, check=False, capture_output=True)
    if completed.returncode == 0:
        return completed.stdout
    if allow_missing_path and completed.returncode == 128:
        stderr = completed.stderr.decode("utf-8", errors="replace")
        if "does not exist in" in stderr or "exists on disk, but not in" in stderr:
            return None
    raise PromotionValidationError(
        f"git {' '.join(args)} failed: {completed.stderr.decode('utf-8', errors='replace').strip()}"
    )


def classify_authority_change(
    root: Path = ROOT,
    base_ref: str | None = None,
    *,
    comparison_mode: Literal["merge-base", "exact"] = "merge-base",
    allow_authority_introduction: bool = False,
) -> dict[str, Any]:
    """Classify exact authority bytes against a PR merge-base or push previous SHA."""

    _require(bool(base_ref), "ranking promotion comparison base is required")
    current_path = root / AUTHORITY_PATH
    try:
        current_raw = current_path.read_bytes()
    except OSError as exc:
        raise PromotionValidationError(f"cannot read ranking authority: {exc}") from exc
    current = _load_json_bytes(current_raw, "current ranking authority")
    validate_authority_object(current, "current ranking authority")

    if comparison_mode == "merge-base":
        comparison_raw = _git(root, "merge-base", "HEAD", str(base_ref))
        assert comparison_raw is not None
        comparison_ref = comparison_raw.decode("ascii").strip()
        _require(bool(comparison_ref), "git merge-base returned an empty identity")
    else:
        comparison_ref = str(base_ref)
        _require(not re.fullmatch(r"0+", comparison_ref), "push previous SHA cannot be all-zero")
        _git(root, "cat-file", "-e", f"{comparison_ref}^{{commit}}")

    base_raw = _git(
        root,
        "show",
        f"{comparison_ref}:{AUTHORITY_PATH.as_posix()}",
        allow_missing_path=True,
    )
    summary: dict[str, Any] = {
        "authority_path": str(AUTHORITY_PATH),
        "base_ref": str(base_ref),
        "comparison_mode": comparison_mode,
        "comparison_ref": comparison_ref,
        "current_sha256": _sha256_bytes(current_raw),
    }
    if base_raw is None:
        _require(allow_authority_introduction, "authority file is absent at comparison base without explicit introduction mode")
        _require(
            summary["current_sha256"] == INTRODUCTION_AUTHORITY_SHA256,
            "authority introduction differs from the reviewed pre-file defaults",
        )
        return {**summary, "classification": "authority-introduction"}

    base = _load_json_bytes(base_raw, "comparison-base ranking authority")
    validate_authority_object(base, "comparison-base ranking authority")
    classification = "unchanged" if base_raw == current_raw else "promotion"
    return {
        **summary,
        "base_sha256": _sha256_bytes(base_raw),
        "classification": classification,
        "base_raw": base_raw,
        "current_raw": current_raw,
    }


def resolve_ci_comparison(
    *,
    explicit_base_ref: str | None = None,
    explicit_mode: str | None = None,
    environment: Mapping[str, str] | None = None,
) -> tuple[str, Literal["merge-base", "exact"]]:
    """Resolve a required PR merge-base or push previous-SHA comparison."""

    if explicit_base_ref:
        mode = explicit_mode or "merge-base"
        _require(mode in {"merge-base", "exact"}, "comparison mode must be merge-base or exact")
        return explicit_base_ref, mode  # type: ignore[return-value]
    env = os.environ if environment is None else environment
    event_name = env.get("BUOY_RANKING_EVENT_NAME", "")
    if event_name == "pull_request":
        ref = env.get("BUOY_RANKING_PR_BASE_REF", "")
        _require(bool(ref), "pull request ranking comparison base is missing")
        return ref, "merge-base"
    if event_name == "push":
        ref = env.get("BUOY_RANKING_PUSH_BEFORE", "")
        _require(bool(ref), "push previous SHA is missing")
        _require(not re.fullmatch(r"0+", ref), "push previous SHA cannot be all-zero")
        return ref, "exact"
    raise PromotionValidationError("ranking comparison event/base is missing; use --base-ref for local validation")


def _validate_retrieval_options(value: Any, label: str) -> dict[str, Any]:
    _require(isinstance(value, dict), f"{label} retrieval_options must be an object")
    _require_exact_keys(value, _RETRIEVAL_OPTION_KEYS, f"{label} retrieval_options")
    top_k = value["top_k"]
    candidates = value["candidates"]
    _require(isinstance(top_k, int) and not isinstance(top_k, bool) and 1 <= top_k <= 100, f"{label} top_k must be in [1, 100]")
    _require(
        isinstance(candidates, int) and not isinstance(candidates, bool) and 1 <= candidates <= 1000,
        f"{label} candidates must be in [1, 1000]",
    )
    for field in ("use_ann", "use_bm25"):
        _require(isinstance(value[field], bool), f"{label} {field} must be boolean")
    _require(value["use_ann"] or value["use_bm25"], f"{label} must enable ANN or BM25")
    return dict(value)


def _validate_retrieval_contract(value: Any, label: str) -> dict[str, str]:
    _require(isinstance(value, dict), f"{label} retrieval_contract must be an object")
    _require_exact_keys(value, _RETRIEVAL_CONTRACT_KEYS, f"{label} retrieval_contract")
    return {key: _require_safe_identifier(value[key], f"{label} retrieval_contract.{key}") for key in sorted(value)}


def _validate_results(
    value: Any,
    label: str,
    *,
    expected_repos: set[str] = EXPECTED_REPOS,
) -> dict[str, dict[str, Any]]:
    _require(isinstance(value, list), f"{label} repositories must be a list")
    _require(len(value) == len(expected_repos), f"{label} must contain {len(expected_repos)} repositories")
    _require(
        [row.get("repo_key") for row in value if isinstance(row, dict)] == sorted(expected_repos),
        f"{label} repository rows must use the sorted complete repository basket",
    )
    result: dict[str, dict[str, Any]] = {}
    for row in value:
        _require(isinstance(row, dict), f"{label} repository result must be an object")
        _require_exact_keys(row, _RESULT_KEYS, f"{label} repository result")
        repo_key = row["repo_key"]
        _require(repo_key in expected_repos and repo_key not in result, f"{label} has invalid/duplicate repo_key")
        score = row["repo_search_score"]
        precision = row["precision_at_5"]
        _require(
            isinstance(score, (int, float)) and not isinstance(score, bool) and math.isfinite(score),
            f"{label} repo_search_score must be finite",
        )
        _require(0.0 <= float(score) <= 100.0, f"{label} repo_search_score must be in [0, 100]")
        _require(
            isinstance(precision, (int, float)) and not isinstance(precision, bool) and math.isfinite(precision),
            f"{label} precision_at_5 must be finite",
        )
        _require(0.0 <= float(precision) <= 1.0, f"{label} precision_at_5 must be in [0, 1]")
        result[repo_key] = {
            "precision_at_5": float(precision),
            "repo_key": repo_key,
            "repo_search_score": float(score),
        }
    _require(set(result) == expected_repos, f"{label} repository basket differs")
    return result


def _policy_summary(
    baseline: dict[str, dict[str, Any]],
    candidate: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    score_deltas = {
        key: candidate[key]["repo_search_score"] - baseline[key]["repo_search_score"]
        for key in EXPECTED_REPOS
    }
    no_score_regression = all(delta >= 0.0 for delta in score_deltas.values())
    no_precision_regression = all(
        candidate[key]["precision_at_5"] >= baseline[key]["precision_at_5"] for key in EXPECTED_REPOS
    )
    positive = [delta for delta in score_deltas.values() if delta > 0.0]
    positive_count = len(positive)
    total_positive = sum(positive)
    largest_share = max(positive) / total_positive if positive else 0.0
    average_delta = sum(score_deltas.values()) / len(EXPECTED_REPOS)
    passed = (
        no_score_regression
        and no_precision_regression
        and positive_count >= 3
        and largest_share <= 0.70
        and average_delta > 0.0
    )
    return {
        "average_score_delta": average_delta,
        "contract": "repo-ranking-promotion-policy-v1",
        "largest_positive_gain_share": largest_share,
        "no_repo_precision_at_5_regression": no_precision_regression,
        "no_repo_score_regression": no_score_regression,
        "passed": passed,
        "positive_score_gain_repositories": positive_count,
    }


def _require_policy_equal(observed: dict[str, Any], expected: dict[str, Any]) -> None:
    _require_exact_keys(observed, set(expected), "promotion policy result")
    for key, expected_value in expected.items():
        observed_value = observed[key]
        if isinstance(expected_value, float):
            _require(
                isinstance(observed_value, (int, float))
                and not isinstance(observed_value, bool)
                and math.isclose(float(observed_value), expected_value, rel_tol=0.0, abs_tol=1e-12),
                f"promotion policy {key} differs from recomputed result",
            )
        else:
            _require(observed_value == expected_value, f"promotion policy {key} differs from recomputed result")


def _resolve_registry_file(root: Path, relative_value: Any, label: str) -> Path:
    _require(isinstance(relative_value, str) and relative_value, f"{label} path must be non-empty")
    relative = Path(relative_value)
    _require(not relative.is_absolute() and ".." not in relative.parts, f"{label} path must stay under the repository root")
    path = root / relative
    try:
        resolved_root = root.resolve(strict=True)
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise PromotionValidationError(f"{label} file is missing: {relative_value}: {exc}") from exc
    _require(resolved.is_relative_to(resolved_root), f"{label} path escapes the repository root")
    _require(path.is_file() and not path.is_symlink(), f"{label} must be a regular non-symlink file")
    return path


def _validate_source_identity(value: Any, label: str) -> dict[str, str]:
    _require(isinstance(value, dict), f"{label} source_identity must be an object")
    _require_exact_keys(value, _SOURCE_IDENTITY_KEYS, f"{label} source_identity")
    _require(value["kind"] == "git-commit", f"{label} source_identity kind must be git-commit")
    revision = value["revision"]
    _require(
        isinstance(revision, str) and bool(re.fullmatch(r"[0-9a-f]{40}", revision)),
        f"{label} source_identity revision must be a full lowercase Git commit",
    )
    return {"kind": "git-commit", "revision": revision}


def _require_canonical_repo_path(value: Any, label: str) -> str:
    _require(isinstance(value, str) and 0 < len(value) <= 1024, f"{label} must be a bounded path string")
    _require("\\" not in value and "\x00" not in value, f"{label} must use canonical POSIX syntax")
    path = PurePosixPath(value)
    _require(not path.is_absolute(), f"{label} must be repository-relative")
    _require(all(part not in {"", ".", ".."} for part in path.parts), f"{label} contains unsafe segments")
    _require(path.as_posix() == value, f"{label} is not canonical")
    return value


def _validate_registered_dataset(
    value: dict[str, Any],
    member: dict[str, Any],
    label: str,
) -> set[str]:
    _require_exact_keys(value, _DATASET_KEYS, label)
    _require(
        isinstance(value["schema_version"], int)
        and not isinstance(value["schema_version"], bool)
        and value["schema_version"] == 1,
        f"{label} schema_version must be 1",
    )
    for field in ("dataset_id", "dataset_version", "repository"):
        _require(value[field] == member[field], f"{label} {field} differs from basket member")
    cases = value["cases"]
    _require(isinstance(cases, list) and cases, f"{label} cases must be a nonempty list")
    case_ids: set[str] = set()
    judgment_paths: set[str] = set()
    for case in cases:
        _require(isinstance(case, dict), f"{label} case must be an object")
        _require_exact_keys(case, _DATASET_CASE_KEYS, f"{label} case")
        case_id = _require_safe_identifier(case["id"], f"{label} case id")
        _require(case_id not in case_ids, f"{label} case ids must be unique")
        case_ids.add(case_id)
        question = case["question"]
        _require(
            isinstance(question, str) and question.strip() == question and 0 < len(question) <= 8192,
            f"{label} case question must be a bounded nonempty string",
        )
        judgments = case["judgments"]
        _require(isinstance(judgments, list) and judgments, f"{label} case judgments must be nonempty")
        case_paths: set[str] = set()
        for judgment in judgments:
            _require(isinstance(judgment, dict), f"{label} judgment must be an object")
            _require_exact_keys(judgment, _DATASET_JUDGMENT_KEYS, f"{label} judgment")
            path = _require_canonical_repo_path(judgment["repo_path"], f"{label} judgment repo_path")
            _require(path not in case_paths, f"{label} judgment paths must be unique within a case")
            case_paths.add(path)
            judgment_paths.add(path)
            grade = judgment["grade"]
            _require(
                isinstance(grade, int) and not isinstance(grade, bool) and 0 <= grade <= 3,
                f"{label} judgment grade must be an integer in [0, 3]",
            )
            reason = judgment["reason"]
            _require(
                isinstance(reason, str) and reason.strip() == reason and 0 < len(reason) <= 8192,
                f"{label} judgment reason must be a bounded nonempty string",
            )
    return judgment_paths


def _validate_registered_corpus_manifest(
    value: dict[str, Any],
    member: dict[str, Any],
    label: str,
) -> set[str]:
    _require_exact_keys(value, _CORPUS_MANIFEST_KEYS, label)
    _require(
        isinstance(value["schema_version"], int)
        and not isinstance(value["schema_version"], bool)
        and value["schema_version"] == 1,
        f"{label} schema_version must be 1",
    )
    _require_safe_identifier(value["manifest_id"], f"{label} manifest_id")
    _require(value["repository"] == member["repository"], f"{label} repository differs from basket member")
    source_identity = _validate_source_identity(value["source_identity"], label)
    _require(source_identity == member["source_identity"], f"{label} source_identity differs from basket member")
    documents = value["documents"]
    _require(isinstance(documents, list) and documents, f"{label} documents must be a nonempty list")
    paths: list[str] = []
    for document in documents:
        _require(isinstance(document, dict), f"{label} document must be an object")
        _require_exact_keys(document, _CORPUS_DOCUMENT_KEYS, f"{label} document")
        paths.append(_require_canonical_repo_path(document["path"], f"{label} document path"))
        _require_hash(document["content_sha256"], f"{label} document content_sha256")
    _require(paths == sorted(set(paths)), f"{label} documents must have sorted unique canonical paths")
    inventory_sha256 = _canonical_sha256(documents)
    _require(value["document_inventory_sha256"] == inventory_sha256, f"{label} document inventory SHA-256 mismatch")
    _require(member["document_count"] == len(documents), f"{label} document_count differs from basket member")
    _require(
        member["document_inventory_sha256"] == inventory_sha256,
        f"{label} document_inventory_sha256 differs from basket member",
    )
    return set(paths)


def _validate_recorded_benchmark(
    value: dict[str, Any],
    member: dict[str, Any],
    label: str,
) -> None:
    _require_exact_keys(value, _RECORDED_BENCHMARK_KEYS, label)
    _require(
        isinstance(value["schema_version"], int)
        and not isinstance(value["schema_version"], bool)
        and value["schema_version"] == 1,
        f"{label} schema_version must be 1",
    )
    _require_safe_identifier(value["benchmark_id"], f"{label} benchmark_id")
    for field in (
        "repo_key",
        "repository",
        "source_identity",
        "dataset_id",
        "dataset_version",
        "dataset_sha256",
        "corpus_manifest_sha256",
    ):
        _require(value[field] == member[field], f"{label} {field} differs from basket member")
    _validate_retrieval_options(value["retrieval_options"], label)
    _validate_retrieval_contract(value["retrieval_contract"], label)
    _validate_results([value["result"]], label, expected_repos={member["repo_key"]})


def validate_promotion_basket_registry(
    root: Path = ROOT,
) -> dict[tuple[str, int], tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]]:
    """Validate every registered promotion basket against actual immutable bytes."""

    registry = _load_json(root / PROMOTION_BASKETS_PATH, "promotion basket registry")
    _require_exact_keys(registry, _BASKET_REGISTRY_KEYS, "promotion basket registry")
    _require(registry["schema_version"] == 1, "promotion basket registry schema_version must be 1")
    baskets = registry["baskets"]
    _require(isinstance(baskets, list), "promotion basket registry baskets must be a list")
    identities = [
        (item.get("basket_id"), item.get("basket_version"))
        for item in baskets
        if isinstance(item, dict)
    ]
    _require(identities == sorted(identities), "promotion basket registry must be sorted by identity")
    _require(len(identities) == len(set(identities)), "promotion basket registry identities must be unique")

    evaluation_registry = _load_json(root / EVALUATION_VERSIONS_PATH, "evaluation version registry")
    evaluation_versions = evaluation_registry.get("versions")
    _require(isinstance(evaluation_versions, list), "evaluation registry versions must be a list")

    validated: dict[
        tuple[str, int],
        tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, dict[str, Any]]],
    ] = {}
    for basket in baskets:
        _require(isinstance(basket, dict), "promotion basket entry must be an object")
        _require_exact_keys(basket, _BASKET_KEYS, "promotion basket entry")
        _require(basket["schema_version"] == 1, "promotion basket schema_version must be 1")
        _require(basket["baseline_status"] == "recorded", "promotion basket must be recorded")
        basket_id = _require_safe_identifier(basket["basket_id"], "promotion basket basket_id")
        basket_version = basket["basket_version"]
        _require(
            isinstance(basket_version, int) and not isinstance(basket_version, bool) and basket_version > 0,
            "promotion basket basket_version must be positive",
        )
        repositories = basket["repositories"]
        _require(isinstance(repositories, list) and len(repositories) == 13, "promotion basket must contain 13 repositories")
        _require(
            [row.get("repo_key") for row in repositories if isinstance(row, dict)] == sorted(EXPECTED_REPOS),
            "promotion basket repositories must be sorted and complete",
        )
        by_key: dict[str, dict[str, Any]] = {}
        benchmarks: dict[str, dict[str, Any]] = {}
        for member in repositories:
            _require(isinstance(member, dict), "promotion basket repository must be an object")
            _require_exact_keys(member, _BASKET_REPOSITORY_KEYS, "promotion basket repository")
            repo_key = member["repo_key"]
            _require(repo_key in EXPECTED_REPOS and repo_key not in by_key, "promotion basket has invalid/duplicate repo_key")
            _require(member["baseline_status"] == "recorded", f"promotion basket {repo_key} must be recorded")
            _require_safe_identifier(member["dataset_id"], f"promotion basket {repo_key} dataset_id")
            _require_safe_identifier(member["repository"], f"promotion basket {repo_key} repository")
            member["source_identity"] = _validate_source_identity(
                member["source_identity"], f"promotion basket {repo_key}"
            )
            _require(
                isinstance(member["dataset_version"], int)
                and not isinstance(member["dataset_version"], bool)
                and member["dataset_version"] > 0,
                f"promotion basket {repo_key} dataset_version must be positive",
            )
            _require(
                isinstance(member["document_count"], int)
                and not isinstance(member["document_count"], bool)
                and member["document_count"] > 0,
                f"promotion basket {repo_key} document_count must be positive",
            )
            _require_hash(
                member["document_inventory_sha256"],
                f"promotion basket {repo_key} document_inventory_sha256",
            )
            dataset_path = _resolve_registry_file(root, member["dataset_path"], f"promotion basket {repo_key} dataset")
            corpus_path = _resolve_registry_file(root, member["corpus_manifest_path"], f"promotion basket {repo_key} corpus manifest")
            benchmark_path = _resolve_registry_file(root, member["recorded_benchmark_path"], f"promotion basket {repo_key} benchmark")
            for field, path in (
                ("dataset_sha256", dataset_path),
                ("corpus_manifest_sha256", corpus_path),
                ("recorded_benchmark_sha256", benchmark_path),
            ):
                expected_hash = _require_hash(member[field], f"promotion basket {repo_key} {field}")
                _require(_sha256_bytes(path.read_bytes()) == expected_hash, f"promotion basket {repo_key} {field} differs from actual bytes")
            dataset = _load_json(dataset_path, f"promotion basket {repo_key} dataset")
            corpus = _load_json(corpus_path, f"promotion basket {repo_key} corpus manifest")
            judgment_paths = _validate_registered_dataset(
                dataset, member, f"promotion basket {repo_key} dataset"
            )
            document_paths = _validate_registered_corpus_manifest(
                corpus, member, f"promotion basket {repo_key} corpus manifest"
            )
            _require(
                judgment_paths <= document_paths,
                f"promotion basket {repo_key} dataset judgments are absent from corpus manifest",
            )
            benchmark = _load_json(benchmark_path, f"promotion basket {repo_key} benchmark")
            _validate_recorded_benchmark(benchmark, member, f"promotion basket {repo_key} benchmark")
            by_key[repo_key] = member
            benchmarks[repo_key] = benchmark

        buoy = by_key["buoy"]
        registered_buoy = next(
            (
                version
                for version in evaluation_versions
                if isinstance(version, dict)
                and version.get("dataset_id") == buoy["dataset_id"]
                and version.get("dataset_version") == buoy["dataset_version"]
            ),
            None,
        )
        _require(isinstance(registered_buoy, dict), "Buoy basket version is not registered")
        _require(registered_buoy.get("baseline_status") == "recorded", "pending Buoy evaluation cannot support promotion")
        _require(registered_buoy.get("promotion_eligible") is True, "Buoy evaluation is not promotion eligible")
        _require("path_membership_manifest_sha256" not in registered_buoy, "path-only Buoy evaluation cannot support promotion")
        for field in ("dataset_sha256", "corpus_manifest_sha256"):
            _require(registered_buoy.get(field) == buoy[field], f"recorded Buoy {field} differs from promotion basket")
        _require(
            registered_buoy.get("benchmark_artifact_sha256") == buoy["recorded_benchmark_sha256"],
            "recorded Buoy benchmark linkage differs from promotion basket",
        )

        expected_basket_hash = _canonical_sha256(
            {key: value for key, value in basket.items() if key != "basket_sha256"}
        )
        _require(basket["basket_sha256"] == expected_basket_hash, "promotion basket SHA-256 mismatch")
        validated[(basket_id, basket_version)] = (basket, by_key, benchmarks)
    return validated


def _validate_basket_reference(
    value: Any,
    root: Path,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    _require(isinstance(value, dict), "evaluation_basket must be an object")
    _require_exact_keys(value, _BASKET_REFERENCE_KEYS, "evaluation_basket")
    basket_id = _require_safe_identifier(value["basket_id"], "evaluation_basket basket_id")
    basket_version = value["basket_version"]
    _require(
        isinstance(basket_version, int) and not isinstance(basket_version, bool) and basket_version > 0,
        "evaluation_basket basket_version must be positive",
    )
    _require_hash(value["basket_sha256"], "evaluation_basket basket_sha256")
    registered = validate_promotion_basket_registry(root)
    entry = registered.get((basket_id, basket_version))
    _require(entry is not None, "evaluation_basket is not registered")
    basket, members, benchmarks = entry
    _require(value["basket_sha256"] == basket["basket_sha256"], "evaluation_basket SHA-256 differs from registry")
    return basket, members, benchmarks


def _validate_configuration(value: Any, label: str, expected_authority: dict[str, Any]) -> dict[str, Any]:
    _require(isinstance(value, dict), f"{label} configuration must be an object")
    _require_exact_keys(value, _CONFIGURATION_KEYS, f"{label} configuration")
    _require(value["ranking_defaults"] == expected_authority, f"{label} ranking defaults differ")
    _require_hash(value["evaluation_basket_sha256"], f"{label} evaluation_basket_sha256")
    options = _validate_retrieval_options(value["retrieval_options"], label)
    contract = _validate_retrieval_contract(value["retrieval_contract"], label)
    return {
        "evaluation_basket_sha256": value["evaluation_basket_sha256"],
        "retrieval_contract": contract,
        "retrieval_options": options,
    }


def _validate_arm_hash(arm: dict[str, Any], label: str) -> None:
    expected = _canonical_sha256(
        {
            "benchmark_id": arm["benchmark_id"],
            "configuration": arm["configuration"],
            "repositories": arm["repositories"],
        }
    )
    _require(arm["benchmark_sha256"] == expected, f"{label} benchmark SHA-256 mismatch")


def validate_promotion_artifact(
    artifact_path: Path,
    *,
    base_raw: bytes,
    proposed_raw: bytes,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Validate one supplied immutable recorded-basket promotion artifact offline."""

    artifact = _load_json(artifact_path, "promotion artifact")
    _require_exact_keys(artifact, _ARTIFACT_KEYS, "promotion artifact")
    _require(artifact["schema_version"] == 2, "promotion artifact schema_version must be 2")
    _require_safe_identifier(artifact["artifact_id"], "promotion artifact_id")

    base = _load_json_bytes(base_raw, "base authority")
    proposed = _load_json_bytes(proposed_raw, "proposed authority")
    validate_authority_object(base, "base authority")
    validate_authority_object(proposed, "proposed authority")
    _require(base != proposed, "promotion artifact cannot describe unchanged defaults")

    authority = artifact["authority"]
    _require(isinstance(authority, dict), "promotion authority must be an object")
    _require_exact_keys(authority, {"base", "base_sha256", "proposed", "proposed_sha256"}, "promotion authority")
    _require(authority["base"] == base, "promotion artifact base authority differs from comparison base")
    _require(authority["proposed"] == proposed, "promotion artifact proposed authority differs from change")
    _require(authority["base_sha256"] == _sha256_bytes(base_raw), "promotion base authority SHA-256 mismatch")
    _require(authority["proposed_sha256"] == _sha256_bytes(proposed_raw), "promotion proposed authority SHA-256 mismatch")

    basket, basket_by_key, recorded_benchmarks = _validate_basket_reference(
        artifact["evaluation_basket"], root
    )
    baskets: dict[str, dict[str, dict[str, Any]]] = {}
    non_authority_inputs: dict[str, dict[str, Any]] = {}
    for label, expected_defaults in (("baseline", base), ("candidate", proposed)):
        arm = artifact[label]
        _require(isinstance(arm, dict), f"{label} must be an object")
        _require_exact_keys(arm, _ARM_KEYS, label)
        _require_safe_identifier(arm["benchmark_id"], f"{label} benchmark_id")
        _require_hash(arm["benchmark_sha256"], f"{label} benchmark_sha256")
        non_authority_inputs[label] = _validate_configuration(arm["configuration"], label, expected_defaults)
        _require(
            arm["configuration"]["evaluation_basket_sha256"] == basket["basket_sha256"],
            f"{label} configuration uses a different evaluation basket",
        )
        baskets[label] = _validate_results(arm["repositories"], label)
        _validate_arm_hash(arm, label)
    _require(
        non_authority_inputs["baseline"] == non_authority_inputs["candidate"],
        "baseline and candidate non-authority inputs differ",
    )

    for repo_key in sorted(EXPECTED_REPOS):
        recorded = recorded_benchmarks[repo_key]
        _require(
            recorded["result"] == baskets["baseline"][repo_key],
            f"promotion basket {repo_key} recorded benchmark result differs from baseline",
        )
        _require(
            recorded["retrieval_contract"] == non_authority_inputs["baseline"]["retrieval_contract"],
            f"promotion basket {repo_key} recorded benchmark retrieval contract differs",
        )
        _require(
            recorded["retrieval_options"] == non_authority_inputs["baseline"]["retrieval_options"],
            f"promotion basket {repo_key} recorded benchmark retrieval options differ",
        )

    expected_policy = _policy_summary(baskets["baseline"], baskets["candidate"])
    policy = artifact["policy"]
    _require(isinstance(policy, dict), "promotion policy must be an object")
    _require_policy_equal(policy, expected_policy)
    _require(expected_policy["passed"] is True, "candidate does not pass repo ranking promotion policy")

    return {
        "artifact_id": artifact["artifact_id"],
        "artifact_sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
        "authority_base_sha256": authority["base_sha256"],
        "authority_proposed_sha256": authority["proposed_sha256"],
        "basket_id": basket["basket_id"],
        "basket_sha256": basket["basket_sha256"],
        "policy": expected_policy,
        "repositories": len(basket_by_key),
    }


def _discover_promotion_artifact(root: Path, proposed_raw: bytes) -> Path:
    proposed_sha256 = _sha256_bytes(proposed_raw)
    candidates: list[Path] = []
    for path in sorted((root / PROMOTION_ARTIFACT_DIR).glob("*.json")):
        try:
            value = _load_json(path, "promotion artifact candidate")
        except PromotionValidationError:
            continue
        authority = value.get("authority")
        if isinstance(authority, dict) and authority.get("proposed_sha256") == proposed_sha256:
            candidates.append(path)
    _require(
        len(candidates) == 1,
        "ranking defaults changed without exactly one matching artifact under "
        f"{PROMOTION_ARTIFACT_DIR} (found {len(candidates)})",
    )
    return candidates[0]


def validate_promotion_gate(
    classification: dict[str, Any],
    promotion_artifact: Path | None,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Apply the promotion-only artifact gate to one authority classification."""

    public_classification = {
        key: value for key, value in classification.items() if key not in {"base_raw", "current_raw"}
    }
    summary: dict[str, Any] = {"authority": public_classification}
    if classification["classification"] == "promotion":
        base_raw = classification.get("base_raw")
        proposed_raw = classification.get("current_raw")
        _require(
            isinstance(base_raw, bytes) and isinstance(proposed_raw, bytes),
            "promotion classification lacks authority bytes",
        )
        resolved_artifact = promotion_artifact or _discover_promotion_artifact(root, proposed_raw)
        summary["promotion"] = validate_promotion_artifact(
            resolved_artifact,
            base_raw=base_raw,
            proposed_raw=proposed_raw,
            root=root,
        )
    elif promotion_artifact is not None:
        raise PromotionValidationError("promotion artifact supplied when ranking defaults did not change")
    return summary


def _environment_flag(value: str | None) -> bool:
    if value is None or value == "":
        return False
    _require(value in {"0", "1", "false", "true"}, "introduction flag must be true/false/1/0")
    return value in {"1", "true"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-ref", help="Explicit local comparison ref/SHA.")
    parser.add_argument("--comparison-mode", choices=("merge-base", "exact"))
    parser.add_argument(
        "--allow-authority-introduction",
        action="store_true",
        default=_environment_flag(os.environ.get("BUOY_RANKING_AUTHORITY_INTRODUCTION")),
        help="Allow the one reviewed authority introduction only when exact bytes match its frozen SHA-256.",
    )
    parser.add_argument(
        "--promotion-artifact",
        type=Path,
        default=(
            Path(os.environ["BUOY_RANKING_PROMOTION_ARTIFACT"])
            if os.environ.get("BUOY_RANKING_PROMOTION_ARTIFACT")
            else None
        ),
        help="Immutable benchmark artifact required only when active defaults changed.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        base_ref, comparison_mode = resolve_ci_comparison(
            explicit_base_ref=args.base_ref,
            explicit_mode=args.comparison_mode,
        )
        registered_baskets = validate_promotion_basket_registry()
        classification = classify_authority_change(
            base_ref=base_ref,
            comparison_mode=comparison_mode,
            allow_authority_introduction=args.allow_authority_introduction,
        )
        summary = validate_promotion_gate(classification, args.promotion_artifact)
        summary["promotion_basket_registry"] = {
            "path": str(PROMOTION_BASKETS_PATH),
            "registered_baskets": len(registered_baskets),
        }
    except (PromotionValidationError, OSError) as exc:
        print(f"ranking promotion validation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
