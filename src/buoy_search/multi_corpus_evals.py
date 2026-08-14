"""Validated offline contracts and scorers for automatic multi-corpus retrieval."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from math import isfinite, log2
from pathlib import Path
import re
import subprocess
from typing import Mapping, Sequence
from urllib.parse import unquote, urlparse


DEFAULT_MULTI_CORPUS_EVAL_DATASET = (
    Path(__file__).with_name("data") / "automatic_multi_corpus_retrieval_evals.json"
)
CATEGORY_COUNTS = {
    "unambiguous": 20,
    "descriptor_free_confusable": 15,
    "multi_corpus": 10,
    "no_answer": 5,
}
LEGACY_METRIC_CONTRACT = {
    "route_recall_at_3": (
        "Micro required-namespace recall over the 45 answer-bearing cases after truncating "
        "each automatic route to its first three namespaces."
    ),
    "complete_multi_corpus_coverage": (
        "All expected namespaces must appear in the first three automatic routes for every "
        "one of the 10 multi-corpus cases."
    ),
    "incorrect_high_confidence_single_routes": (
        "Count initially high-confidence singleton routes whose initial singleton is not "
        "exactly the case's required namespace set, even when final retrieval widens; the "
        "required count is zero."
    ),
    "automatic_recall_at_5": (
        "Micro recall over unique positive judged (namespace, URL) targets found by exhaustive "
        "retrieval across all four enabled eligible corpora, deduplicated within each query."
    ),
    "reranking_ndcg_at_5": (
        "Macro-average nDCG@5 before and after MiniLM reranking over the 10 multi-corpus cases, "
        "using exhaustive-found judged targets as the ideal set."
    ),
    "reranking_recall_at_5": (
        "Micro Recall@5 before and after reranking over exhaustive-found targets in the 10 "
        "multi-corpus cases; reranking must not regress it."
    ),
    "average_automatic_fanout": (
        "Mean final automatic route count over all 50 cases, including no-answer cases."
    ),
}
METRIC_CONTRACT = {
    **LEGACY_METRIC_CONTRACT,
    "automatic_recall_at_5": (
        "Micro recall over required answer/facet groups made available by exhaustive "
        "retrieval across all four enabled eligible corpora. Any judged equivalent URL "
        "recalls its group, and each group receives credit at most once per query."
    ),
    "reranking_ndcg_at_5": (
        "Macro-average nDCG@5 before and after MiniLM reranking over the 10 multi-corpus "
        "cases. Exhaustive-available answer/facet groups form the ideal set, and each "
        "group receives gain at most once."
    ),
    "reranking_recall_at_5": (
        "Micro Recall@5 before and after reranking over exhaustive-available answer/facet "
        "groups in the 10 multi-corpus cases; reranking must not regress it."
    ),
}
ELIGIBLE_STATUS = "enabled_eligible"
DISABLED_DUPLICATE_STATUS = "disabled_duplicate"
MAX_AUTOMATIC_FANOUT = 3
ROUTE_RECALL_K = 3
RETRIEVAL_RECALL_K = 5
RERANK_NDCG_K = 5
EVAL_RUN_SCHEMA_VERSION = 2
EVALUATOR_VERSION = "3"
LIVE_COLLECTOR_PROVENANCE_MARKER = "buoy.multi_corpus.live_collector/v2"
ROUTE_RECALL_MINIMUM = 0.95
AUTOMATIC_RECALL_MINIMUM = 0.95
RERANK_NDCG_IMPROVEMENT_MINIMUM = 0.03
AVERAGE_FANOUT_MAXIMUM = 2.0
EVAL_RUN_MODES = frozenset({"live", "fixture"})

_RUN_ROOT_FIELDS = {
    "schema_version",
    "dataset_id",
    "mode",
    "provenance",
    "read_only_boundary",
    "catalog",
    "cases",
}
_DERIVED_RUN_FIELDS = {"metrics", "verdict"}
_CATALOG_RUN_FIELDS = {
    "snapshot_revision",
    "live_namespaces",
    "eligible_namespaces",
    "disabled_namespaces",
    "stale_namespaces",
    "missing_namespaces",
    "incompatible_namespaces",
    "read_calls",
}
_CATALOG_READ_CALL_FIELDS = {
    "namespace_list_logical_calls",
    "metadata_logical_calls",
    "catalog_query_logical_calls",
}
_CASE_RUN_FIELDS = {
    "id",
    "route",
    "exhaustive_hits",
    "automatic_hits",
    "pre_rerank_hits",
    "reranked_hits",
    "timing_ms",
    "calls",
    "failures",
}
_ROUTE_RUN_FIELDS = {"namespaces", "initial_high_confidence_namespace"}
_HIT_RUN_FIELDS = {"namespace", "url"}
_TIMING_RUN_FIELDS = {"routing", "automatic", "exhaustive", "total"}
_CASE_CALL_FIELDS = {
    "routing_embedding_logical_calls",
    "content_embedding_logical_calls",
    "reranker_logical_calls",
    "automatic_namespace_logical_calls",
    "exhaustive_namespace_logical_calls",
    "automatic_multi_query_logical_calls",
    "exhaustive_multi_query_logical_calls",
}
_FAILURE_RUN_FIELDS = {"automatic_namespaces", "exhaustive_namespaces"}
_READ_ONLY_BOUNDARY_FIELDS = {
    "provider_mutation_methods_exposed",
    "provider_mutations_precluded",
}
_FIXTURE_PROVENANCE_FIELDS = {"origin"}
_LIVE_PROVENANCE_FIELDS = {
    "origin",
    "collector_produced",
    "dataset_sha256",
    "code",
    "catalog_snapshot_revision",
    "models",
    "evaluator",
    "collector_invocation",
}
_CODE_PROVENANCE_FIELDS = {"commit", "tree", "working_tree_clean"}
_MODEL_PROVENANCE_FIELDS = {"routing", "content_embedding", "reranker"}
_MODEL_IDENTITY_FIELDS = {"model", "revision", "config"}
_ROUTING_MODEL_CONFIG_FIELDS = {
    "dimensions",
    "normalized",
    "precision",
    "query_prefix",
    "route_top_k",
    "semantic_confidence_floor",
    "semantic_margin_floor",
}
_CONTENT_MODEL_CONFIG_FIELDS = {
    "automatic_top_k",
    "candidates_per_namespace",
    "exhaustive_top_k",
    "normalize_embeddings",
    "precision",
    "region",
    "namespace_retrieval",
}
_NAMESPACE_RETRIEVAL_CONFIG_FIELDS = {
    "ranking_aggregation",
    "ranking_mode",
    "ranking_pool",
    "ranking_profile",
}
_RERANKER_MODEL_CONFIG_FIELDS = {
    "batch_size",
    "cross_namespace_fusion_components",
    "cross_namespace_fusion_method",
    "cross_namespace_rrf_k",
    "device",
    "max_candidates_per_namespace",
    "max_length",
    "namespace_coverage_policy",
}
_LOCAL_RANK_ONE_COVERAGE_POLICY = (
    "retain_one_namespace_local_rank_one_hit_per_nonempty_namespace_when_top_k_allows"
)
_EVALUATOR_PROVENANCE_FIELDS = {"version", "sha256"}
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GIT_OBJECT_PATTERN = re.compile(r"^[0-9a-f]{40,64}$")


@dataclass(frozen=True)
class PhysicalNamespace:
    namespace: str
    logical_corpus: str
    status: str
    duplicate_of: str | None = None


@dataclass(frozen=True)
class LogicalCorpus:
    id: str
    namespace: str
    title: str
    aliases: tuple[str, ...]
    source: str


@dataclass(frozen=True)
class MultiCorpusJudgment:
    namespace: str
    url: str
    grade: int
    reason: str
    group: str | None = None

    @property
    def key(self) -> tuple[str, str]:
        return self.namespace, normalize_eval_url(self.url)

    @property
    def group_key(self) -> str:
        # Old datasets had one target URL per required answer/facet. Treating the
        # normalized URL as its group preserves that contract until a reviewer
        # assigns an explicit group to equivalent positives.
        return self.group or f"{self.namespace}\0{normalize_eval_url(self.url)}"


@dataclass(frozen=True)
class MultiCorpusEvalCase:
    id: str
    category: str
    question: str
    source_name_exposed: bool
    expected_namespaces: tuple[str, ...]
    route_requirement: str
    answer_expected: bool
    judgments: tuple[MultiCorpusJudgment, ...]


@dataclass(frozen=True)
class MultiCorpusEvalDataset:
    dataset_id: str
    canonical_sha256: str
    human_approved_ground_truth: bool
    review_status: str
    notes: str
    physical_namespaces: tuple[PhysicalNamespace, ...]
    logical_corpora: tuple[LogicalCorpus, ...]
    cases: tuple[MultiCorpusEvalCase, ...]

    @property
    def eligible_namespaces(self) -> tuple[str, ...]:
        return tuple(
            item.namespace
            for item in self.physical_namespaces
            if item.status == ELIGIBLE_STATUS
        )

    @property
    def disabled_duplicate_namespaces(self) -> tuple[str, ...]:
        return tuple(
            item.namespace
            for item in self.physical_namespaces
            if item.status == DISABLED_DUPLICATE_STATUS
        )

    @property
    def cases_by_id(self) -> dict[str, MultiCorpusEvalCase]:
        return {case.id: case for case in self.cases}


@dataclass(frozen=True)
class RouteObservation:
    namespaces: tuple[str, ...]
    high_confidence_single: bool = False
    initial_high_confidence_namespace: str | None = None


@dataclass(frozen=True)
class RoutingEvalMetrics:
    route_recall_at_3: float
    route_required_total: int
    route_required_found: int
    complete_multi_corpus_coverage: bool
    complete_multi_corpus_cases: int
    multi_corpus_case_total: int
    incorrect_high_confidence_single_routes: int
    average_automatic_fanout: float
    maximum_observed_fanout: int

    def to_dict(self) -> dict[str, object]:
        return {
            "route_recall_at_3": self.route_recall_at_3,
            "route_required_total": self.route_required_total,
            "route_required_found": self.route_required_found,
            "complete_multi_corpus_coverage": self.complete_multi_corpus_coverage,
            "complete_multi_corpus_cases": self.complete_multi_corpus_cases,
            "multi_corpus_case_total": self.multi_corpus_case_total,
            "incorrect_high_confidence_single_routes": self.incorrect_high_confidence_single_routes,
            "average_automatic_fanout": self.average_automatic_fanout,
            "maximum_observed_fanout": self.maximum_observed_fanout,
        }


@dataclass(frozen=True)
class EvalHit:
    namespace: str
    url: str

    @property
    def key(self) -> tuple[str, str]:
        return self.namespace, normalize_eval_url(self.url)


@dataclass(frozen=True)
class RetrievalEvalMetrics:
    automatic_recall_at_5: float
    exhaustive_required_groups: int
    automatic_required_groups_found: int
    pre_rerank_recall_at_5: float
    reranked_recall_at_5: float
    recall_at_5_regressed: bool
    pre_rerank_ndcg_at_5: float
    reranked_ndcg_at_5: float
    ndcg_at_5_improvement: float
    multi_corpus_case_total: int

    def to_dict(self) -> dict[str, object]:
        return {
            "automatic_recall_at_5": self.automatic_recall_at_5,
            "exhaustive_required_groups": self.exhaustive_required_groups,
            "automatic_required_groups_found": self.automatic_required_groups_found,
            "pre_rerank_recall_at_5": self.pre_rerank_recall_at_5,
            "reranked_recall_at_5": self.reranked_recall_at_5,
            "recall_at_5_regressed": self.recall_at_5_regressed,
            "pre_rerank_ndcg_at_5": self.pre_rerank_ndcg_at_5,
            "reranked_ndcg_at_5": self.reranked_ndcg_at_5,
            "ndcg_at_5_improvement": self.ndcg_at_5_improvement,
            "multi_corpus_case_total": self.multi_corpus_case_total,
        }

    @property
    def exhaustive_positive_targets(self) -> int:
        """Compatibility alias for callers written before grouped judgments."""

        return self.exhaustive_required_groups

    @property
    def automatic_positive_targets_found(self) -> int:
        """Compatibility alias for callers written before grouped judgments."""

        return self.automatic_required_groups_found


def load_multi_corpus_eval_dataset(
    dataset_path: Path | None = None,
) -> MultiCorpusEvalDataset:
    """Load the fixed 50-query evaluation basket and enforce its governance contract."""

    path = dataset_path or DEFAULT_MULTI_CORPUS_EVAL_DATASET
    dataset_bytes = path.read_bytes()
    payload = json.loads(dataset_bytes.decode("utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("Multi-corpus eval dataset must be a JSON object.")
    if payload.get("schema_version") != 1:
        raise ValueError("Multi-corpus eval dataset schema_version must be 1.")

    dataset_id = _required_string(payload, "dataset_id", where="dataset")
    approved = payload.get("human_approved_ground_truth")
    if not isinstance(approved, bool):
        raise ValueError("Dataset human_approved_ground_truth must be a boolean.")
    review_status = _required_string(payload, "review_status", where="dataset")
    if approved and review_status != "approved":
        raise ValueError("Human-approved ground truth must use review_status='approved'.")
    if not approved and review_status == "approved":
        raise ValueError("Candidate ground truth cannot use review_status='approved'.")
    notes = _required_string(payload, "notes", where="dataset")
    metric_contract = payload.get("metric_contract")
    if not isinstance(metric_contract, Mapping) or json.dumps(
        metric_contract, sort_keys=True
    ) not in {
        # The checked-in candidate predates explicit answer/facet groups. Its
        # questions and judgments remain unchanged until human review, while
        # newly reviewed datasets can declare the grouped metric wording.
        json.dumps(LEGACY_METRIC_CONTRACT, sort_keys=True),
        json.dumps(METRIC_CONTRACT, sort_keys=True),
    }:
        raise ValueError("Dataset metric_contract does not match the executable scorer contract.")

    physical_payload = _required_list(payload, "physical_namespaces", where="dataset")
    physical = tuple(_parse_physical_namespace(item) for item in physical_payload)
    logical_payload = _required_list(payload, "logical_corpora", where="dataset")
    logical = tuple(_parse_logical_corpus(item) for item in logical_payload)
    cases_payload = _required_list(payload, "cases", where="dataset")
    cases = tuple(_parse_case(item) for item in cases_payload)

    dataset = MultiCorpusEvalDataset(
        dataset_id=dataset_id,
        canonical_sha256=hashlib.sha256(dataset_bytes).hexdigest(),
        human_approved_ground_truth=approved,
        review_status=review_status,
        notes=notes,
        physical_namespaces=physical,
        logical_corpora=logical,
        cases=cases,
    )
    _validate_dataset(dataset, payload)
    return dataset


def evaluator_sha256() -> str:
    """Digest the executable scorer used to validate release evidence."""

    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def score_routing(
    dataset: MultiCorpusEvalDataset,
    observations: Mapping[str, RouteObservation | Mapping[str, object]],
) -> RoutingEvalMetrics:
    """Score final automatic routes, truncating only route-recall credit at three."""

    parsed = _route_observations(dataset, observations)
    required_total = 0
    required_found = 0
    complete_multi = 0
    incorrect_high_confidence = 0
    total_fanout = 0
    maximum_fanout = 0

    for case in dataset.cases:
        observation = parsed[case.id]
        route = observation.namespaces
        credited = set(route[:ROUTE_RECALL_K])
        required = set(case.expected_namespaces)
        required_total += len(required)
        required_found += len(required & credited)
        total_fanout += len(route)
        maximum_fanout = max(maximum_fanout, len(route))
        if case.category == "multi_corpus" and required <= credited:
            complete_multi += 1
        initial_singleton = observation.initial_high_confidence_namespace
        if initial_singleton is None and observation.high_confidence_single:
            initial_singleton = route[0]
        if initial_singleton is not None and {initial_singleton} != required:
            incorrect_high_confidence += 1

    multi_total = CATEGORY_COUNTS["multi_corpus"]
    return RoutingEvalMetrics(
        route_recall_at_3=(required_found / required_total if required_total else 0.0),
        route_required_total=required_total,
        route_required_found=required_found,
        complete_multi_corpus_coverage=complete_multi == multi_total,
        complete_multi_corpus_cases=complete_multi,
        multi_corpus_case_total=multi_total,
        incorrect_high_confidence_single_routes=incorrect_high_confidence,
        average_automatic_fanout=total_fanout / len(dataset.cases),
        maximum_observed_fanout=maximum_fanout,
    )


def score_retrieval(
    dataset: MultiCorpusEvalDataset,
    *,
    exhaustive_hits: Mapping[str, Sequence[EvalHit | Mapping[str, object]]],
    automatic_hits: Mapping[str, Sequence[EvalHit | Mapping[str, object]]],
    pre_rerank_hits: Mapping[str, Sequence[EvalHit | Mapping[str, object]]],
    reranked_hits: Mapping[str, Sequence[EvalHit | Mapping[str, object]]],
) -> RetrievalEvalMetrics:
    """Score retrieval against exhaustive-available answer/facet groups.

    A group may contain multiple equivalent positive URLs. Any one of those URLs
    recalls the group, while duplicate equivalents receive neither extra recall
    nor extra nDCG gain. The micro denominator retains query identity when the
    same group label is reused by different questions.
    """

    exhaustive = _hit_runs(dataset, exhaustive_hits, required_cases=dataset.cases)
    automatic = _hit_runs(dataset, automatic_hits, required_cases=dataset.cases)
    multi_cases = tuple(case for case in dataset.cases if case.category == "multi_corpus")
    pre_rerank = _hit_runs(dataset, pre_rerank_hits, required_cases=multi_cases)
    reranked = _hit_runs(dataset, reranked_hits, required_cases=multi_cases)

    automatic_denominator = 0
    automatic_found = 0
    multi_denominator = 0
    pre_found = 0
    reranked_found = 0
    pre_ndcg: list[float] = []
    reranked_ndcg: list[float] = []

    for case in dataset.cases:
        url_groups, group_grades = _judgment_groups(case)
        exhaustive_groups = {
            url_groups[hit.key]
            for hit in exhaustive[case.id]
            if hit.key in url_groups
        }
        automatic_denominator += len(exhaustive_groups)
        automatic_found += len(
            exhaustive_groups
            & _groups_for_hits(
                automatic[case.id][:RETRIEVAL_RECALL_K], url_groups
            )
        )
        if case.category != "multi_corpus":
            continue
        pre_groups = _groups_for_hits(
            pre_rerank[case.id][:RETRIEVAL_RECALL_K], url_groups
        )
        reranked_groups = _groups_for_hits(
            reranked[case.id][:RETRIEVAL_RECALL_K], url_groups
        )
        multi_denominator += len(exhaustive_groups)
        pre_found += len(exhaustive_groups & pre_groups)
        reranked_found += len(exhaustive_groups & reranked_groups)
        ideal_grades = sorted(
            (group_grades[group] for group in exhaustive_groups), reverse=True
        )[:RERANK_NDCG_K]
        ideal_dcg = _dcg(ideal_grades)
        pre_ndcg.append(
            _dcg_for_grouped_hits(
                pre_rerank[case.id],
                url_groups=url_groups,
                group_grades=group_grades,
                available_groups=exhaustive_groups,
            )
            / ideal_dcg
            if ideal_dcg
            else 0.0
        )
        reranked_ndcg.append(
            _dcg_for_grouped_hits(
                reranked[case.id],
                url_groups=url_groups,
                group_grades=group_grades,
                available_groups=exhaustive_groups,
            )
            / ideal_dcg
            if ideal_dcg
            else 0.0
        )

    automatic_recall = (
        automatic_found / automatic_denominator if automatic_denominator else 0.0
    )
    pre_recall = pre_found / multi_denominator if multi_denominator else 0.0
    reranked_recall = reranked_found / multi_denominator if multi_denominator else 0.0
    pre_average = sum(pre_ndcg) / len(pre_ndcg)
    reranked_average = sum(reranked_ndcg) / len(reranked_ndcg)
    return RetrievalEvalMetrics(
        automatic_recall_at_5=automatic_recall,
        exhaustive_required_groups=automatic_denominator,
        automatic_required_groups_found=automatic_found,
        pre_rerank_recall_at_5=pre_recall,
        reranked_recall_at_5=reranked_recall,
        recall_at_5_regressed=reranked_recall < pre_recall,
        pre_rerank_ndcg_at_5=pre_average,
        reranked_ndcg_at_5=reranked_average,
        ndcg_at_5_improvement=reranked_average - pre_average,
        multi_corpus_case_total=len(multi_cases),
    )


def evaluate_multi_corpus_run(
    dataset: MultiCorpusEvalDataset,
    payload: Mapping[str, object],
) -> dict[str, object]:
    """Validate, normalize, score, and gate one content-free evaluation run.

    The returned report deliberately retains only namespace/URL identities,
    timings, and call accounting. Ground-truth questions, retrieved content,
    vectors, model inputs, and provider responses are never copied into it.
    Stored metrics and verdicts are ignored and recomputed. This public/offline
    path deliberately cannot establish provider-backed provenance, even when a
    payload copies the live collector marker. Only the collector's private
    in-process evaluation path can establish that release check.
    """

    normalized = normalize_multi_corpus_run(dataset, payload)
    return _evaluate_normalized_multi_corpus_run(
        dataset,
        normalized,
        trusted_live_provenance=False,
    )


def _evaluate_collected_multi_corpus_run(
    dataset: MultiCorpusEvalDataset,
    payload: Mapping[str, object],
    *,
    expected_catalog_snapshot_revision: str,
    expected_models: Mapping[str, object],
    expected_collector_invocation: Sequence[str],
) -> dict[str, object]:
    """Evaluate a just-collected run against independent in-process facts.

    This is intentionally private. It is a structural trust boundary for the
    read-only collector, not a cryptographic attestation: the recorded payload
    must exactly match the clean current checkout and the collector's actual
    catalog, model, evaluator, and invocation contracts.
    """

    normalized = normalize_multi_corpus_run(dataset, payload)
    trusted = _qualifies_as_live_collector_provenance(
        dataset,
        normalized,
        expected_catalog_snapshot_revision=expected_catalog_snapshot_revision,
        expected_models=expected_models,
        expected_collector_invocation=expected_collector_invocation,
    )
    return _evaluate_normalized_multi_corpus_run(
        dataset,
        normalized,
        trusted_live_provenance=trusted,
    )


def _evaluate_normalized_multi_corpus_run(
    dataset: MultiCorpusEvalDataset,
    normalized: Mapping[str, object],
    *,
    trusted_live_provenance: bool,
) -> dict[str, object]:
    cases = normalized["cases"]
    if not isinstance(cases, list):  # Normalization guarantees this shape.
        raise AssertionError("normalized eval cases must be a list")

    routes: dict[str, Mapping[str, object]] = {}
    exhaustive: dict[str, Sequence[Mapping[str, object]]] = {}
    automatic: dict[str, Sequence[Mapping[str, object]]] = {}
    pre_rerank: dict[str, Sequence[Mapping[str, object]]] = {}
    reranked: dict[str, Sequence[Mapping[str, object]]] = {}
    complete_cases = 0
    automatic_failure_cases = 0
    exhaustive_failure_cases = 0
    aggregate_timing = {field: 0.0 for field in sorted(_TIMING_RUN_FIELDS)}
    aggregate_calls = {field: 0 for field in sorted(_CASE_CALL_FIELDS)}

    for raw_case in cases:
        if not isinstance(raw_case, Mapping):
            raise AssertionError("normalized eval case must be an object")
        case_id = str(raw_case["id"])
        route = raw_case["route"]
        timing = raw_case["timing_ms"]
        calls = raw_case["calls"]
        failures = raw_case["failures"]
        if not all(
            isinstance(value, Mapping)
            for value in (route, timing, calls, failures)
        ):
            raise AssertionError("normalized eval case objects are malformed")
        routes[case_id] = route
        exhaustive[case_id] = raw_case["exhaustive_hits"]  # type: ignore[assignment]
        automatic[case_id] = raw_case["automatic_hits"]  # type: ignore[assignment]
        pre_rerank[case_id] = raw_case["pre_rerank_hits"]  # type: ignore[assignment]
        reranked[case_id] = raw_case["reranked_hits"]  # type: ignore[assignment]
        automatic_failed = bool(failures["automatic_namespaces"])
        exhaustive_failed = bool(failures["exhaustive_namespaces"])
        automatic_failure_cases += int(automatic_failed)
        exhaustive_failure_cases += int(exhaustive_failed)
        complete_cases += int(not automatic_failed and not exhaustive_failed)
        for field in aggregate_timing:
            aggregate_timing[field] += float(timing[field])
        for field in aggregate_calls:
            aggregate_calls[field] += int(calls[field])

    routing_metrics = score_routing(dataset, routes)
    retrieval_metrics = score_retrieval(
        dataset,
        exhaustive_hits=exhaustive,
        automatic_hits=automatic,
        pre_rerank_hits={
            case.id: pre_rerank[case.id]
            for case in dataset.cases
            if case.category == "multi_corpus"
        },
        reranked_hits={
            case.id: reranked[case.id]
            for case in dataset.cases
            if case.category == "multi_corpus"
        },
    )
    collection_metrics = {
        "case_total": len(cases),
        "complete_cases": complete_cases,
        "automatic_failure_cases": automatic_failure_cases,
        "exhaustive_failure_cases": exhaustive_failure_cases,
        "timing_ms": aggregate_timing,
        "calls": aggregate_calls,
    }
    metrics = {
        "routing": routing_metrics.to_dict(),
        "retrieval": retrieval_metrics.to_dict(),
        "collection": collection_metrics,
    }
    verdict = _release_verdict(
        dataset,
        mode=str(normalized["mode"]),
        provenance=normalized["provenance"],  # type: ignore[arg-type]
        read_only_boundary=normalized["read_only_boundary"],  # type: ignore[arg-type]
        routing=routing_metrics,
        retrieval=retrieval_metrics,
        collection=collection_metrics,
        trusted_live_provenance=trusted_live_provenance,
    )
    return {**normalized, "metrics": metrics, "verdict": verdict}


def normalize_multi_corpus_run(
    dataset: MultiCorpusEvalDataset,
    payload: Mapping[str, object],
) -> dict[str, object]:
    """Fail closed on malformed, content-bearing, or unsafe run observations."""

    root = _required_mapping(payload, where="evaluation run")
    unknown = set(root) - _RUN_ROOT_FIELDS - _DERIVED_RUN_FIELDS
    missing = _RUN_ROOT_FIELDS - set(root)
    if unknown or missing:
        raise ValueError(
            "Evaluation run fields are invalid "
            f"(missing={sorted(missing)}, unknown={sorted(unknown)})."
        )
    if root.get("schema_version") != EVAL_RUN_SCHEMA_VERSION:
        raise ValueError(
            f"Evaluation run schema_version must be {EVAL_RUN_SCHEMA_VERSION}."
        )
    if root.get("dataset_id") != dataset.dataset_id:
        raise ValueError("Evaluation run dataset_id does not match the selected dataset.")
    mode = root.get("mode")
    if mode not in EVAL_RUN_MODES:
        raise ValueError(f"Evaluation run mode must be one of {sorted(EVAL_RUN_MODES)}.")

    provenance = _normalize_run_provenance(dataset, root.get("provenance"))
    read_only_boundary = _normalize_read_only_boundary(root.get("read_only_boundary"))
    catalog = _normalize_run_catalog(dataset, root.get("catalog"), mode=str(mode))
    if (
        provenance.get("origin") == LIVE_COLLECTOR_PROVENANCE_MARKER
        and provenance.get("catalog_snapshot_revision")
        != catalog["snapshot_revision"]
    ):
        raise ValueError(
            "Evaluation run provenance catalog snapshot does not match its catalog observation."
        )
    raw_cases = root.get("cases")
    if not isinstance(raw_cases, list):
        raise ValueError("Evaluation run cases must be a list.")
    if len(raw_cases) != len(dataset.cases):
        raise ValueError(
            f"Evaluation run must contain exactly {len(dataset.cases)} cases."
        )
    by_id: dict[str, Mapping[str, object]] = {}
    for raw_case in raw_cases:
        item = _required_mapping(raw_case, where="evaluation case observation")
        case_id = _required_string(item, "id", where="evaluation case observation")
        if case_id in by_id:
            raise ValueError(f"Evaluation run repeats case {case_id!r}.")
        by_id[case_id] = item
    _require_exact_case_keys(dataset, by_id, label="evaluation run cases")
    cases = [
        _normalize_run_case(dataset, case, by_id[case.id], mode=str(mode))
        for case in dataset.cases
    ]
    return {
        "schema_version": EVAL_RUN_SCHEMA_VERSION,
        "dataset_id": dataset.dataset_id,
        "mode": mode,
        "provenance": provenance,
        "read_only_boundary": read_only_boundary,
        "catalog": catalog,
        "cases": cases,
    }


def canonical_eval_output_url(value: str) -> str:
    """Return a query/fragment-free URL suitable for an evaluation artifact."""

    return f"https://{normalize_eval_url(value)}"


def _normalize_read_only_boundary(payload: object) -> dict[str, bool]:
    item = _required_mapping(payload, where="evaluation read_only_boundary")
    _require_exact_fields(
        item,
        _READ_ONLY_BOUNDARY_FIELDS,
        where="evaluation read_only_boundary",
    )
    exposed = item.get("provider_mutation_methods_exposed")
    precluded = item.get("provider_mutations_precluded")
    if not isinstance(exposed, bool) or not isinstance(precluded, bool):
        raise ValueError("Evaluation read-only boundary assertions must be booleans.")
    return {
        "provider_mutation_methods_exposed": exposed,
        "provider_mutations_precluded": precluded,
    }


def _normalize_run_provenance(
    dataset: MultiCorpusEvalDataset,
    payload: object,
) -> dict[str, object]:
    item = _required_mapping(payload, where="evaluation run provenance")
    origin = _required_string(item, "origin", where="evaluation run provenance")
    if origin == "offline_fixture":
        _require_exact_fields(
            item,
            _FIXTURE_PROVENANCE_FIELDS,
            where="fixture evaluation provenance",
        )
        return {"origin": origin}
    if origin != LIVE_COLLECTOR_PROVENANCE_MARKER:
        # Unknown origins remain valid non-release observations. Requiring the
        # one exact collector marker below prevents validate-run from upgrading
        # an offline or third-party artifact into live release evidence.
        _require_exact_fields(
            item,
            _FIXTURE_PROVENANCE_FIELDS,
            where="non-collector evaluation provenance",
        )
        return {"origin": origin}

    _require_exact_fields(
        item,
        _LIVE_PROVENANCE_FIELDS,
        where="live collector provenance",
    )
    if item.get("collector_produced") is not True:
        raise ValueError("Live collector provenance must assert collector_produced=true.")
    dataset_sha = _sha256(
        item.get("dataset_sha256"), where="live collector dataset_sha256"
    )
    if dataset_sha != dataset.canonical_sha256:
        raise ValueError(
            "Live collector provenance does not bind the selected canonical dataset."
        )

    code = _required_mapping(item.get("code"), where="live collector code provenance")
    _require_exact_fields(code, _CODE_PROVENANCE_FIELDS, where="live collector code provenance")
    commit = _git_object(code.get("commit"), where="live collector code commit")
    tree = _git_object(code.get("tree"), where="live collector code tree")
    clean = code.get("working_tree_clean")
    if not isinstance(clean, bool):
        raise ValueError("Live collector working_tree_clean must be a boolean.")

    models = _normalize_model_provenance(
        item.get("models"),
        eligible_namespaces=dataset.eligible_namespaces,
    )
    evaluator = _required_mapping(
        item.get("evaluator"), where="live collector evaluator provenance"
    )
    _require_exact_fields(
        evaluator,
        _EVALUATOR_PROVENANCE_FIELDS,
        where="live collector evaluator provenance",
    )
    evaluator_version = _required_string(
        evaluator, "version", where="live collector evaluator provenance"
    )
    evaluator_digest = _sha256(
        evaluator.get("sha256"), where="live collector evaluator sha256"
    )
    invocation = _unique_nonempty_string_sequence(
        item.get("collector_invocation"),
        where="live collector invocation",
        require_unique=False,
    )
    snapshot_revision = _required_string(
        item,
        "catalog_snapshot_revision",
        where="live collector provenance",
    )
    return {
        "origin": origin,
        "collector_produced": True,
        "dataset_sha256": dataset_sha,
        "code": {
            "commit": commit,
            "tree": tree,
            "working_tree_clean": clean,
        },
        "catalog_snapshot_revision": snapshot_revision,
        "models": models,
        "evaluator": {
            "version": evaluator_version,
            "sha256": evaluator_digest,
        },
        "collector_invocation": list(invocation),
    }


def _normalize_model_provenance(
    payload: object,
    *,
    eligible_namespaces: Sequence[str],
) -> dict[str, object]:
    models = _required_mapping(payload, where="live collector model provenance")
    _require_exact_fields(
        models,
        _MODEL_PROVENANCE_FIELDS,
        where="live collector model provenance",
    )
    normalized: dict[str, object] = {}
    for role in sorted(_MODEL_PROVENANCE_FIELDS):
        model = _required_mapping(
            models.get(role), where=f"live collector {role} model provenance"
        )
        _require_exact_fields(
            model,
            _MODEL_IDENTITY_FIELDS,
            where=f"live collector {role} model provenance",
        )
        revision = _required_string(
            model, "revision", where=f"live collector {role} model provenance"
        )
        if not _GIT_OBJECT_PATTERN.fullmatch(revision):
            raise ValueError(
                f"Live collector {role} model revision must be an exact commit hash."
            )
        config = _required_mapping(
            model.get("config"), where=f"live collector {role} model config"
        )
        if not config:
            raise ValueError(f"Live collector {role} model config cannot be empty.")
        normalized[role] = {
            "model": _required_string(
                model, "model", where=f"live collector {role} model provenance"
            ),
            "revision": revision,
            "config": _normalize_json_object(
                config, where=f"live collector {role} model config"
            ),
        }
    _validate_complete_model_configs(
        normalized,
        eligible_namespaces=eligible_namespaces,
    )
    return normalized


def _validate_complete_model_configs(
    models: Mapping[str, object],
    *,
    eligible_namespaces: Sequence[str],
) -> None:
    expected_fields = {
        "routing": _ROUTING_MODEL_CONFIG_FIELDS,
        "content_embedding": _CONTENT_MODEL_CONFIG_FIELDS,
        "reranker": _RERANKER_MODEL_CONFIG_FIELDS,
    }
    configs: dict[str, Mapping[str, object]] = {}
    for role, fields in expected_fields.items():
        model = _required_mapping(
            models.get(role), where=f"live collector {role} model provenance"
        )
        config = _required_mapping(
            model.get("config"), where=f"live collector {role} model config"
        )
        _require_exact_fields(
            config,
            fields,
            where=f"live collector {role} model config",
        )
        configs[role] = config

    namespace_retrieval = _required_mapping(
        configs["content_embedding"].get("namespace_retrieval"),
        where="live collector content_embedding namespace_retrieval config",
    )
    if set(namespace_retrieval) != set(eligible_namespaces):
        raise ValueError(
            "Live collector content_embedding namespace_retrieval config must "
            "cover exactly the eligible namespaces."
        )
    for namespace in sorted(namespace_retrieval):
        retrieval = _required_mapping(
            namespace_retrieval.get(namespace),
            where=f"live collector content_embedding retrieval config {namespace!r}",
        )
        _require_exact_fields(
            retrieval,
            _NAMESPACE_RETRIEVAL_CONFIG_FIELDS,
            where=f"live collector content_embedding retrieval config {namespace!r}",
        )

    if (
        configs["reranker"].get("namespace_coverage_policy")
        != _LOCAL_RANK_ONE_COVERAGE_POLICY
    ):
        raise ValueError(
            "Live collector reranker config must record the local-rank-one "
            "namespace coverage policy."
        )


def _normalize_run_catalog(
    dataset: MultiCorpusEvalDataset,
    payload: object,
    *,
    mode: str,
) -> dict[str, object]:
    item = _required_mapping(payload, where="evaluation run catalog")
    _require_exact_fields(item, _CATALOG_RUN_FIELDS, where="evaluation run catalog")
    snapshot_revision = _required_string(
        item, "snapshot_revision", where="evaluation run catalog"
    )
    lists = {
        field: _unique_string_list(
            item.get(field), where=f"evaluation run catalog {field}"
        )
        for field in (
            "live_namespaces",
            "eligible_namespaces",
            "disabled_namespaces",
            "stale_namespaces",
            "missing_namespaces",
            "incompatible_namespaces",
        )
    }
    expected_live = {item.namespace for item in dataset.physical_namespaces}
    expected_eligible = set(dataset.eligible_namespaces)
    expected_disabled = set(dataset.disabled_duplicate_namespaces)
    if set(lists["live_namespaces"]) != expected_live:
        raise ValueError(
            "Evaluation run live namespace inventory does not match the governed five-namespace basket."
        )
    if lists["missing_namespaces"]:
        raise ValueError("Evaluation run catalog coverage has missing cards.")
    if lists["incompatible_namespaces"]:
        raise ValueError("Evaluation run catalog coverage has incompatible cards.")
    if set(lists["eligible_namespaces"]) != expected_eligible:
        raise ValueError(
            "Evaluation run eligible namespaces do not match the governed four-corpus basket."
        )
    if set(lists["disabled_namespaces"]) != expected_disabled:
        raise ValueError(
            "Evaluation run disabled coverage must contain exactly the governed duplicate namespace."
        )
    if set(lists["stale_namespaces"]) & expected_live:
        raise ValueError("Evaluation run cannot classify a live namespace as stale.")

    calls = _required_mapping(item.get("read_calls"), where="catalog read_calls")
    _require_exact_fields(calls, _CATALOG_READ_CALL_FIELDS, where="catalog read_calls")
    normalized_calls = {
        field: _nonnegative_int(calls.get(field), where=f"catalog read_calls {field}")
        for field in sorted(_CATALOG_READ_CALL_FIELDS)
    }
    if mode == "fixture" and any(normalized_calls.values()):
        raise ValueError("Fixture evaluation must make zero catalog/provider calls.")
    if mode == "live" and (
        normalized_calls["namespace_list_logical_calls"] < 1
        or normalized_calls["metadata_logical_calls"] < 1
        or normalized_calls["catalog_query_logical_calls"] < 1
    ):
        raise ValueError("Live evaluation must account for its catalog read requests.")
    return {
        "snapshot_revision": snapshot_revision,
        **{field: sorted(values) for field, values in lists.items()},
        "read_calls": normalized_calls,
    }


def _normalize_run_case(
    dataset: MultiCorpusEvalDataset,
    case: MultiCorpusEvalCase,
    payload: Mapping[str, object],
    *,
    mode: str,
) -> dict[str, object]:
    _require_exact_fields(
        payload, _CASE_RUN_FIELDS, where=f"evaluation case {case.id!r}"
    )
    route = _required_mapping(
        payload.get("route"), where=f"evaluation case {case.id!r} route"
    )
    _require_exact_fields(
        route, _ROUTE_RUN_FIELDS, where=f"evaluation case {case.id!r} route"
    )
    namespaces = _unique_string_list(
        route.get("namespaces"), where=f"evaluation case {case.id!r} route namespaces"
    )
    if not 1 <= len(namespaces) <= MAX_AUTOMATIC_FANOUT:
        raise ValueError(
            f"Evaluation case {case.id!r} automatic fanout must be between one and "
            f"{MAX_AUTOMATIC_FANOUT}."
        )
    if not set(namespaces) <= set(dataset.eligible_namespaces):
        raise ValueError(
            f"Evaluation case {case.id!r} route contains a disabled or unknown namespace."
        )
    initial_high_confidence = route.get("initial_high_confidence_namespace")
    if initial_high_confidence is not None and (
        not isinstance(initial_high_confidence, str)
        or not initial_high_confidence.strip()
    ):
        raise ValueError(
            f"Evaluation case {case.id!r} initial_high_confidence_namespace must be a string or null."
        )
    if isinstance(initial_high_confidence, str):
        initial_high_confidence = initial_high_confidence.strip()
    if initial_high_confidence is not None and initial_high_confidence not in set(
        dataset.eligible_namespaces
    ):
        raise ValueError(
            f"Evaluation case {case.id!r} initial high-confidence namespace is disabled or unknown."
        )
    if initial_high_confidence is not None and initial_high_confidence != namespaces[0]:
        raise ValueError(
            f"Evaluation case {case.id!r} initial high-confidence namespace must be the first final route."
        )

    hits = {
        field: _normalize_identity_hits(
            dataset,
            payload.get(field),
            where=f"evaluation case {case.id!r} {field}",
        )
        for field in (
            "exhaustive_hits",
            "automatic_hits",
            "pre_rerank_hits",
            "reranked_hits",
        )
    }
    timing = _required_mapping(
        payload.get("timing_ms"), where=f"evaluation case {case.id!r} timing_ms"
    )
    _require_exact_fields(
        timing, _TIMING_RUN_FIELDS, where=f"evaluation case {case.id!r} timing_ms"
    )
    normalized_timing = {
        field: _nonnegative_number(
            timing.get(field), where=f"evaluation case {case.id!r} timing_ms {field}"
        )
        for field in sorted(_TIMING_RUN_FIELDS)
    }
    phase_total = sum(
        normalized_timing[field] for field in ("routing", "automatic", "exhaustive")
    )
    if normalized_timing["total"] + 0.001 < phase_total:
        raise ValueError(
            f"Evaluation case {case.id!r} total timing is below its phase timings."
        )

    calls = _required_mapping(
        payload.get("calls"), where=f"evaluation case {case.id!r} calls"
    )
    _require_exact_fields(calls, _CASE_CALL_FIELDS, where=f"evaluation case {case.id!r} calls")
    normalized_calls = {
        field: _nonnegative_int(
            calls.get(field), where=f"evaluation case {case.id!r} calls {field}"
        )
        for field in sorted(_CASE_CALL_FIELDS)
    }
    if mode == "fixture" and any(normalized_calls.values()):
        raise ValueError(f"Fixture evaluation case {case.id!r} must make zero calls.")
    if mode == "live":
        if normalized_calls["routing_embedding_logical_calls"] != 1:
            raise ValueError(
                f"Live evaluation case {case.id!r} must perform one routing embedding logical call."
            )
        if normalized_calls["content_embedding_logical_calls"] != 1:
            raise ValueError(
                f"Live evaluation case {case.id!r} must perform one distinct cached "
                "content embedding logical call."
            )
        if normalized_calls["automatic_namespace_logical_calls"] != len(namespaces):
            raise ValueError(
                f"Live evaluation case {case.id!r} automatic query accounting does not match fanout."
            )
        if normalized_calls["exhaustive_namespace_logical_calls"] != len(
            dataset.eligible_namespaces
        ):
            raise ValueError(
                f"Live evaluation case {case.id!r} must exhaustively query all four corpora."
            )
        if normalized_calls["automatic_multi_query_logical_calls"] < normalized_calls[
            "automatic_namespace_logical_calls"
        ]:
            raise ValueError(
                f"Live evaluation case {case.id!r} undercounts automatic multi_query invocations."
            )
        if normalized_calls["exhaustive_multi_query_logical_calls"] < normalized_calls[
            "exhaustive_namespace_logical_calls"
        ]:
            raise ValueError(
                f"Live evaluation case {case.id!r} undercounts exhaustive multi_query invocations."
            )
        if normalized_calls["reranker_logical_calls"] not in {0, 1}:
            raise ValueError(
                f"Live evaluation case {case.id!r} may perform at most one reranker inference."
            )
        if (
            hits["pre_rerank_hits"] != hits["reranked_hits"]
            and normalized_calls["reranker_logical_calls"] != 1
        ):
            raise ValueError(
                f"Live evaluation case {case.id!r} changed order without one reranker inference."
            )

    failures = _required_mapping(
        payload.get("failures"), where=f"evaluation case {case.id!r} failures"
    )
    _require_exact_fields(
        failures, _FAILURE_RUN_FIELDS, where=f"evaluation case {case.id!r} failures"
    )
    normalized_failures = {
        field: sorted(
            _unique_string_list(
                failures.get(field), where=f"evaluation case {case.id!r} failures {field}"
            )
        )
        for field in sorted(_FAILURE_RUN_FIELDS)
    }
    for field, failed in normalized_failures.items():
        if not set(failed) <= set(dataset.eligible_namespaces):
            raise ValueError(
                f"Evaluation case {case.id!r} {field} contains a disabled or unknown namespace."
            )

    return {
        "id": case.id,
        "route": {
            "namespaces": list(namespaces),
            "initial_high_confidence_namespace": initial_high_confidence,
        },
        **hits,
        "timing_ms": normalized_timing,
        "calls": normalized_calls,
        "failures": normalized_failures,
    }


def _normalize_identity_hits(
    dataset: MultiCorpusEvalDataset,
    payload: object,
    *,
    where: str,
) -> list[dict[str, str]]:
    if not isinstance(payload, list):
        raise ValueError(f"{where} must be a list.")
    eligible = set(dataset.eligible_namespaces)
    normalized: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for index, raw in enumerate(payload):
        hit = _required_mapping(raw, where=f"{where}[{index}]")
        _require_exact_fields(hit, _HIT_RUN_FIELDS, where=f"{where}[{index}]")
        namespace = _required_string(hit, "namespace", where=f"{where}[{index}]")
        if namespace not in eligible:
            raise ValueError(f"{where}[{index}] contains a disabled or unknown namespace.")
        url = canonical_eval_output_url(
            _required_string(hit, "url", where=f"{where}[{index}]")
        )
        key = namespace, normalize_eval_url(url)
        if key in seen:
            continue
        seen.add(key)
        normalized.append({"namespace": namespace, "url": url})
    return normalized


def _release_verdict(
    dataset: MultiCorpusEvalDataset,
    *,
    mode: str,
    provenance: Mapping[str, object],
    read_only_boundary: Mapping[str, object],
    routing: RoutingEvalMetrics,
    retrieval: RetrievalEvalMetrics,
    collection: Mapping[str, object],
    trusted_live_provenance: bool,
) -> dict[str, object]:
    read_only_asserted = (
        read_only_boundary.get("provider_mutation_methods_exposed") is False
        and read_only_boundary.get("provider_mutations_precluded") is True
    )
    checks = {
        "provider_backed_live_run": {
            "passed": mode == "live" and trusted_live_provenance,
            "observed": {
                "mode": mode,
                "provenance_origin": provenance.get("origin"),
                "collector_produced": provenance.get("collector_produced", False),
            },
            "required": "live mode with exact collector-produced provenance",
        },
        "human_approved_ground_truth": {
            "passed": dataset.human_approved_ground_truth,
            "observed": dataset.review_status,
            "required": "human_approved_ground_truth=true and review_status=approved",
        },
        "complete_read_only_collection": {
            "passed": collection["complete_cases"] == len(dataset.cases)
            and read_only_asserted,
            "observed": {
                "complete_cases": collection["complete_cases"],
                "case_total": collection["case_total"],
                "read_only_boundary": dict(read_only_boundary),
            },
            "required": "all 50 cases complete under the asserted mutation-precluding boundary",
        },
        "route_recall_at_3": {
            "passed": routing.route_recall_at_3 >= ROUTE_RECALL_MINIMUM,
            "observed": routing.route_recall_at_3,
            "required": f">={ROUTE_RECALL_MINIMUM}",
        },
        "complete_multi_corpus_coverage": {
            "passed": routing.complete_multi_corpus_coverage,
            "observed": routing.complete_multi_corpus_cases,
            "required": f"{routing.multi_corpus_case_total}/{routing.multi_corpus_case_total}",
        },
        "incorrect_high_confidence_single_routes": {
            "passed": routing.incorrect_high_confidence_single_routes == 0,
            "observed": routing.incorrect_high_confidence_single_routes,
            "required": "0",
        },
        "automatic_recall_at_5": {
            "passed": retrieval.automatic_recall_at_5 >= AUTOMATIC_RECALL_MINIMUM,
            "observed": retrieval.automatic_recall_at_5,
            "required": f">={AUTOMATIC_RECALL_MINIMUM}",
        },
        "reranking_ndcg_at_5_improvement": {
            "passed": retrieval.ndcg_at_5_improvement
            >= RERANK_NDCG_IMPROVEMENT_MINIMUM,
            "observed": retrieval.ndcg_at_5_improvement,
            "required": f">={RERANK_NDCG_IMPROVEMENT_MINIMUM}",
        },
        "reranking_recall_at_5_not_reduced": {
            "passed": not retrieval.recall_at_5_regressed,
            "observed": {
                "pre": retrieval.pre_rerank_recall_at_5,
                "post": retrieval.reranked_recall_at_5,
            },
            "required": "post>=pre",
        },
        "average_automatic_fanout": {
            "passed": routing.average_automatic_fanout <= AVERAGE_FANOUT_MAXIMUM,
            "observed": routing.average_automatic_fanout,
            "required": f"<={AVERAGE_FANOUT_MAXIMUM}",
        },
        "maximum_automatic_fanout": {
            "passed": routing.maximum_observed_fanout <= MAX_AUTOMATIC_FANOUT,
            "observed": routing.maximum_observed_fanout,
            "required": f"<={MAX_AUTOMATIC_FANOUT}",
        },
    }
    failed = [name for name, result in checks.items() if not result["passed"]]
    quality_failures = [
        name
        for name in failed
        if name not in {"provider_backed_live_run", "human_approved_ground_truth"}
    ]
    release_ready = not failed
    if release_ready:
        status = "pass"
    elif mode == "fixture" and not quality_failures:
        status = "fixture"
    elif not dataset.human_approved_ground_truth and failed == [
        "human_approved_ground_truth"
    ]:
        status = "candidate_ground_truth"
    else:
        status = "fail"
    return {
        "release_ready": release_ready,
        "status": status,
        "failed_checks": failed,
        "checks": checks,
    }


def _qualifies_as_live_collector_provenance(
    dataset: MultiCorpusEvalDataset,
    normalized_run: Mapping[str, object],
    *,
    expected_catalog_snapshot_revision: str,
    expected_models: Mapping[str, object],
    expected_collector_invocation: Sequence[str],
) -> bool:
    if normalized_run.get("mode") != "live":
        return False
    provenance = normalized_run.get("provenance")
    catalog = normalized_run.get("catalog")
    if not isinstance(provenance, Mapping) or not isinstance(catalog, Mapping):
        return False
    if (
        provenance.get("origin") != LIVE_COLLECTOR_PROVENANCE_MARKER
        or provenance.get("collector_produced") is not True
        or provenance.get("dataset_sha256") != dataset.canonical_sha256
    ):
        return False
    code = provenance.get("code")
    evaluator = provenance.get("evaluator")
    models = provenance.get("models")
    invocation = provenance.get("collector_invocation")
    if not all(isinstance(value, Mapping) for value in (code, evaluator, models)):
        return False
    current_code = _current_git_code_identity()
    if (
        current_code is None
        or current_code.get("working_tree_clean") is not True
        or dict(code) != current_code  # type: ignore[arg-type]
    ):
        return False
    if (
        evaluator.get("version") != EVALUATOR_VERSION  # type: ignore[union-attr]
        or evaluator.get("sha256") != evaluator_sha256()  # type: ignore[union-attr]
    ):
        return False
    try:
        normalized_expected_models = _normalize_model_provenance(
            expected_models,
            eligible_namespaces=dataset.eligible_namespaces,
        )
    except ValueError:
        return False
    if dict(models) != normalized_expected_models:  # type: ignore[arg-type]
        return False
    if (
        provenance.get("catalog_snapshot_revision")
        != expected_catalog_snapshot_revision
        or catalog.get("snapshot_revision") != expected_catalog_snapshot_revision
    ):
        return False
    expected_invocation = list(expected_collector_invocation)
    return (
        isinstance(invocation, list)
        and invocation == expected_invocation
        and _is_exact_collect_invocation(expected_invocation)
    )


def _is_exact_collect_invocation(invocation: Sequence[str]) -> bool:
    if (
        len(invocation) != 5
        or invocation[0] != "collect"
        or invocation[1] != "--dataset"
        or invocation[3] != "--output"
    ):
        return False
    return Path(invocation[2]).is_absolute() and Path(invocation[4]).is_absolute()


def _current_git_code_identity() -> dict[str, object] | None:
    """Read the current checkout identity independently of saved provenance."""

    repo = Path(__file__).resolve().parents[2]

    def run(*args: str) -> str:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()

    try:
        commit = run("rev-parse", "HEAD")
        tree = run("rev-parse", "HEAD^{tree}")
        status = run("status", "--porcelain", "--untracked-files=normal")
    except (OSError, subprocess.CalledProcessError):
        return None
    return {
        "commit": commit,
        "tree": tree,
        "working_tree_clean": not bool(status),
    }


def _sha256(value: object, *, where: str) -> str:
    if not isinstance(value, str) or not _SHA256_PATTERN.fullmatch(value):
        raise ValueError(f"{where} must be a lowercase SHA-256 digest.")
    return value


def _git_object(value: object, *, where: str) -> str:
    if not isinstance(value, str) or not _GIT_OBJECT_PATTERN.fullmatch(value):
        raise ValueError(f"{where} must be an exact Git object ID.")
    return value


def _unique_nonempty_string_sequence(
    payload: object,
    *,
    where: str,
    require_unique: bool,
) -> tuple[str, ...]:
    values = _string_list(payload, where=where)
    if require_unique:
        _require_unique(values, where=where)
    return values


def _normalize_json_object(
    payload: Mapping[str, object],
    *,
    where: str,
) -> dict[str, object]:
    """Round-trip a small provenance config through strict JSON types."""

    try:
        normalized = json.loads(
            json.dumps(payload, allow_nan=False, separators=(",", ":"), sort_keys=True)
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{where} must contain only finite JSON values.") from exc
    if not isinstance(normalized, dict):
        raise ValueError(f"{where} must be an object.")
    return normalized


def _require_exact_fields(
    payload: Mapping[str, object],
    expected: set[str],
    *,
    where: str,
) -> None:
    missing = expected - set(payload)
    unknown = set(payload) - expected
    if missing or unknown:
        raise ValueError(
            f"{where} fields are invalid (missing={sorted(missing)}, unknown={sorted(unknown)})."
        )


def _unique_string_list(payload: object, *, where: str) -> tuple[str, ...]:
    values = _string_list(payload, where=where)
    _require_unique(values, where=where)
    return values


def _nonnegative_int(value: object, *, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{where} must be a non-negative integer.")
    return value


def _nonnegative_number(value: object, *, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{where} must be a finite non-negative number.")
    number = float(value)
    if not isfinite(number) or number < 0:
        raise ValueError(f"{where} must be a finite non-negative number.")
    return number


def normalize_eval_url(value: str) -> str:
    """Canonicalize an HTTP(S) locator for exact eval matching."""

    cleaned = unquote(value.strip())
    parsed = urlparse(cleaned)
    host = parsed.netloc.casefold()
    path = re.sub(r"/+", "/", parsed.path).rstrip("/") or "/"
    if parsed.scheme not in {"http", "https"} or not host:
        raise ValueError(f"Eval URL must be absolute HTTP(S): {value!r}")
    return f"{host}{path}"


def _parse_physical_namespace(payload: object) -> PhysicalNamespace:
    where = "physical namespace"
    item = _required_mapping(payload, where=where)
    duplicate_of = item.get("duplicate_of")
    if duplicate_of is not None and not isinstance(duplicate_of, str):
        raise ValueError(f"{where} duplicate_of must be a string or null.")
    return PhysicalNamespace(
        namespace=_required_string(item, "namespace", where=where),
        logical_corpus=_required_string(item, "logical_corpus", where=where),
        status=_required_string(item, "status", where=where),
        duplicate_of=duplicate_of,
    )


def _parse_logical_corpus(payload: object) -> LogicalCorpus:
    where = "logical corpus"
    item = _required_mapping(payload, where=where)
    aliases = _string_list(item.get("aliases"), where=f"{where} aliases")
    source = _required_string(item, "source", where=where)
    normalize_eval_url(source)
    return LogicalCorpus(
        id=_required_string(item, "id", where=where),
        namespace=_required_string(item, "namespace", where=where),
        title=_required_string(item, "title", where=where),
        aliases=aliases,
        source=source,
    )


def _parse_case(payload: object) -> MultiCorpusEvalCase:
    item = _required_mapping(payload, where="case")
    case_id = _required_string(item, "id", where="case")
    where = f"case {case_id!r}"
    exposed = item.get("source_name_exposed")
    expected = item.get("answer_expected")
    if not isinstance(exposed, bool) or not isinstance(expected, bool):
        raise ValueError(f"{where} exposure and answer flags must be booleans.")
    judgment_payload = _required_list(item, "judgments", where=where)
    judgments = tuple(_parse_judgment(value, case_id=case_id) for value in judgment_payload)
    return MultiCorpusEvalCase(
        id=case_id,
        category=_required_string(item, "category", where=where),
        question=_required_string(item, "question", where=where),
        source_name_exposed=exposed,
        expected_namespaces=_string_list(
            item.get("expected_namespaces"), where=f"{where} expected_namespaces"
        ),
        route_requirement=_required_string(item, "route_requirement", where=where),
        answer_expected=expected,
        judgments=judgments,
    )


def _parse_judgment(payload: object, *, case_id: str) -> MultiCorpusJudgment:
    where = f"case {case_id!r} judgment"
    item = _required_mapping(payload, where=where)
    grade = item.get("grade")
    if isinstance(grade, bool) or not isinstance(grade, int) or not 1 <= grade <= 3:
        raise ValueError(f"{where} grade must be an integer from 1 through 3.")
    url = _required_string(item, "url", where=where)
    normalize_eval_url(url)
    group = item.get("group")
    if group is not None and (not isinstance(group, str) or not group.strip()):
        raise ValueError(f"{where} group must be a non-empty string when provided.")
    return MultiCorpusJudgment(
        namespace=_required_string(item, "namespace", where=where),
        url=url,
        grade=grade,
        reason=_required_string(item, "reason", where=where),
        group=group.strip() if isinstance(group, str) else None,
    )


def _validate_dataset(
    dataset: MultiCorpusEvalDataset,
    raw_payload: Mapping[str, object],
) -> None:
    if len(dataset.physical_namespaces) != 5:
        raise ValueError("Eval basket must inventory exactly five physical content namespaces.")
    physical_ids = [item.namespace for item in dataset.physical_namespaces]
    _require_unique(physical_ids, where="physical namespace IDs")
    logical_ids = [item.id for item in dataset.logical_corpora]
    logical_namespaces = [item.namespace for item in dataset.logical_corpora]
    if len(dataset.logical_corpora) != 4:
        raise ValueError("Eval basket must define exactly four logical eligible corpora.")
    _require_unique(logical_ids, where="logical corpus IDs")
    _require_unique(logical_namespaces, where="logical corpus namespaces")

    eligible = set(dataset.eligible_namespaces)
    disabled = set(dataset.disabled_duplicate_namespaces)
    if len(eligible) != 4 or len(disabled) != 1:
        raise ValueError("Eval basket requires four enabled eligible namespaces and one disabled duplicate.")
    if eligible != set(logical_namespaces):
        raise ValueError("Logical corpora must map one-to-one to enabled eligible namespaces.")
    physical_by_id = {item.namespace: item for item in dataset.physical_namespaces}
    logical_id_set = set(logical_ids)
    for item in dataset.physical_namespaces:
        if item.logical_corpus not in logical_id_set:
            raise ValueError(f"Physical namespace {item.namespace!r} has an unknown logical corpus.")
        if item.status not in {ELIGIBLE_STATUS, DISABLED_DUPLICATE_STATUS}:
            raise ValueError(f"Physical namespace {item.namespace!r} has an invalid status.")
        if item.status == DISABLED_DUPLICATE_STATUS:
            if item.duplicate_of not in eligible:
                raise ValueError("Disabled duplicate must identify one enabled eligible duplicate_of target.")
            if physical_by_id[item.duplicate_of].logical_corpus != item.logical_corpus:
                raise ValueError("Disabled duplicate and duplicate_of target must share a logical corpus.")
        elif item.duplicate_of is not None:
            raise ValueError("Enabled eligible namespaces cannot declare duplicate_of.")

    declared_counts = raw_payload.get("category_counts")
    if declared_counts != CATEGORY_COUNTS:
        raise ValueError(f"Dataset category_counts must equal {CATEGORY_COUNTS!r}.")
    if len(dataset.cases) != sum(CATEGORY_COUNTS.values()):
        raise ValueError("Multi-corpus eval basket must contain exactly 50 cases.")
    _require_unique([case.id for case in dataset.cases], where="case IDs")
    actual_counts = {
        category: sum(case.category == category for case in dataset.cases)
        for category in CATEGORY_COUNTS
    }
    if actual_counts != CATEGORY_COUNTS:
        raise ValueError(f"Case category counts must equal {CATEGORY_COUNTS!r}.")

    corpus_descriptors = tuple(
        descriptor
        for corpus in dataset.logical_corpora
        for descriptor in (corpus.title, *corpus.aliases)
    )
    source_hosts = {
        corpus.namespace: urlparse(corpus.source).netloc.casefold()
        for corpus in dataset.logical_corpora
    }
    for case in dataset.cases:
        expected = set(case.expected_namespaces)
        if len(expected) != len(case.expected_namespaces):
            raise ValueError(f"Case {case.id!r} repeats an expected namespace.")
        if not expected <= eligible:
            raise ValueError(f"Case {case.id!r} names a disabled or unknown expected namespace.")
        judgment_keys = [judgment.key for judgment in case.judgments]
        _require_unique(judgment_keys, where=f"case {case.id!r} judgment keys")
        groups: dict[str, list[MultiCorpusJudgment]] = {}
        for judgment in case.judgments:
            groups.setdefault(judgment.group_key, []).append(judgment)
        for group_key, members in groups.items():
            if len({member.namespace for member in members}) != 1:
                raise ValueError(
                    f"Case {case.id!r} judgment group {group_key!r} crosses namespaces."
                )
            if len({member.grade for member in members}) != 1:
                raise ValueError(
                    f"Case {case.id!r} judgment group {group_key!r} has inconsistent grades."
                )
        judged_namespaces = {judgment.namespace for judgment in case.judgments}
        if not judged_namespaces <= expected:
            raise ValueError(f"Case {case.id!r} has a judgment outside its expected namespaces.")
        for judgment in case.judgments:
            judgment_host = urlparse(judgment.url).netloc.casefold()
            if judgment_host != source_hosts[judgment.namespace]:
                raise ValueError(
                    f"Case {case.id!r} judgment URL host does not match its logical corpus."
                )
        exposed = _question_exposes_descriptor(case.question, corpus_descriptors)
        if case.source_name_exposed != exposed:
            raise ValueError(f"Case {case.id!r} source_name_exposed does not match its question.")
        if case.category == "no_answer":
            if case.answer_expected or expected or case.judgments or case.route_requirement != "none":
                raise ValueError(f"No-answer case {case.id!r} must have no target or judgment.")
            continue
        if not case.answer_expected or case.route_requirement != "all" or not expected:
            raise ValueError(f"Answer-bearing case {case.id!r} must require every expected namespace.")
        if judged_namespaces != expected:
            raise ValueError(f"Case {case.id!r} needs at least one judgment in every expected namespace.")
        if case.category in {"unambiguous", "descriptor_free_confusable"} and len(expected) != 1:
            raise ValueError(f"Single-corpus case {case.id!r} must expect exactly one namespace.")
        if case.category == "unambiguous" and not case.source_name_exposed:
            raise ValueError(f"Unambiguous case {case.id!r} must expose a source name.")
        if case.category == "descriptor_free_confusable" and case.source_name_exposed:
            raise ValueError(f"Descriptor-free case {case.id!r} cannot expose a source name.")
        if case.category == "multi_corpus" and not 2 <= len(expected) <= MAX_AUTOMATIC_FANOUT:
            raise ValueError(f"Multi-corpus case {case.id!r} must expect two or three namespaces.")


def _route_observations(
    dataset: MultiCorpusEvalDataset,
    payload: Mapping[str, RouteObservation | Mapping[str, object]],
) -> dict[str, RouteObservation]:
    _require_exact_case_keys(dataset, payload, label="route observations")
    eligible = set(dataset.eligible_namespaces)
    observations: dict[str, RouteObservation] = {}
    for case in dataset.cases:
        raw = payload[case.id]
        if isinstance(raw, RouteObservation):
            observation = raw
        else:
            namespaces = _string_list(
                raw.get("namespaces"), where=f"route observation {case.id!r} namespaces"
            )
            initial = raw.get("initial_high_confidence_namespace")
            if initial is not None:
                if not isinstance(initial, str) or not initial.strip():
                    raise ValueError(
                        f"Route observation {case.id!r} initial confidence namespace must be a string or null."
                    )
                initial = initial.strip()
                observation = RouteObservation(
                    namespaces,
                    high_confidence_single=True,
                    initial_high_confidence_namespace=initial,
                )
            else:
                high_confidence = raw.get("high_confidence_single", False)
                if not isinstance(high_confidence, bool):
                    raise ValueError(
                        f"Route observation {case.id!r} confidence flag must be boolean."
                    )
                observation = RouteObservation(namespaces, high_confidence)
        if len(set(observation.namespaces)) != len(observation.namespaces):
            raise ValueError(f"Route observation {case.id!r} repeats a namespace.")
        if not set(observation.namespaces) <= eligible:
            raise ValueError(f"Route observation {case.id!r} contains a disabled or unknown namespace.")
        initial = observation.initial_high_confidence_namespace
        if initial is not None:
            if initial not in eligible:
                raise ValueError(
                    f"Route observation {case.id!r} initial confidence namespace is disabled or unknown."
                )
            if not observation.namespaces or initial != observation.namespaces[0]:
                raise ValueError(
                    f"Route observation {case.id!r} initial confidence namespace must be first."
                )
        elif observation.high_confidence_single and len(observation.namespaces) != 1:
            raise ValueError(
                f"Legacy high-confidence observation {case.id!r} must contain exactly one route."
            )
        observations[case.id] = observation
    return observations


def _hit_runs(
    dataset: MultiCorpusEvalDataset,
    payload: Mapping[str, Sequence[EvalHit | Mapping[str, object]]],
    *,
    required_cases: Sequence[MultiCorpusEvalCase],
) -> dict[str, tuple[EvalHit, ...]]:
    expected_ids = {case.id for case in required_cases}
    if set(payload) != expected_ids:
        missing = sorted(expected_ids - set(payload))
        extra = sorted(set(payload) - expected_ids)
        raise ValueError(f"Hit runs do not match required cases (missing={missing}, extra={extra}).")
    eligible = set(dataset.eligible_namespaces)
    runs: dict[str, tuple[EvalHit, ...]] = {}
    for case in required_cases:
        hits: list[EvalHit] = []
        for raw in payload[case.id]:
            if isinstance(raw, EvalHit):
                hit = raw
            else:
                hit = EvalHit(
                    namespace=_required_string(raw, "namespace", where=f"hit for {case.id!r}"),
                    url=_required_string(raw, "url", where=f"hit for {case.id!r}"),
                )
            if hit.namespace not in eligible:
                raise ValueError(f"Hit for {case.id!r} contains a disabled or unknown namespace.")
            normalize_eval_url(hit.url)
            hits.append(hit)
        seen: set[tuple[str, str]] = set()
        unique: list[EvalHit] = []
        for hit in hits:
            if hit.key in seen:
                continue
            seen.add(hit.key)
            unique.append(hit)
        runs[case.id] = tuple(unique)
    return runs


def _judgment_groups(
    case: MultiCorpusEvalCase,
) -> tuple[
    dict[tuple[str, str], str],
    dict[str, int],
]:
    url_groups = {judgment.key: judgment.group_key for judgment in case.judgments}
    group_grades = {
        judgment.group_key: judgment.grade for judgment in case.judgments
    }
    return url_groups, group_grades


def _groups_for_hits(
    hits: Sequence[EvalHit],
    url_groups: Mapping[tuple[str, str], str],
) -> set[str]:
    return {url_groups[hit.key] for hit in hits if hit.key in url_groups}


def _dcg_for_grouped_hits(
    hits: Sequence[EvalHit],
    *,
    url_groups: Mapping[tuple[str, str], str],
    group_grades: Mapping[str, int],
    available_groups: set[str],
) -> float:
    awarded: set[str] = set()
    grades: list[int] = []
    for hit in hits[:RERANK_NDCG_K]:
        group = url_groups.get(hit.key)
        if group is None or group not in available_groups or group in awarded:
            grades.append(0)
            continue
        awarded.add(group)
        grades.append(group_grades[group])
    return _dcg(grades)


def _dcg(grades: Sequence[int]) -> float:
    return sum(((2**grade) - 1) / log2(rank + 1) for rank, grade in enumerate(grades, 1))


def _question_exposes_descriptor(question: str, descriptors: Sequence[str]) -> bool:
    normalized = f" {_normalize_phrase(question)} "
    return any(
        f" {_normalize_phrase(descriptor)} " in normalized
        for descriptor in descriptors
        if _normalize_phrase(descriptor)
    )


def _normalize_phrase(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.casefold()).split())


def _required_mapping(payload: object, *, where: str) -> Mapping[str, object]:
    if not isinstance(payload, Mapping):
        raise ValueError(f"{where} must be an object.")
    return payload


def _required_list(payload: Mapping[str, object], field: str, *, where: str) -> list[object]:
    value = payload.get(field)
    if not isinstance(value, list):
        raise ValueError(f"{where} {field} must be a list.")
    return value


def _required_string(payload: Mapping[str, object], field: str, *, where: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{where} {field} must be a non-empty string.")
    return value.strip()


def _string_list(payload: object, *, where: str) -> tuple[str, ...]:
    if not isinstance(payload, list) or not all(
        isinstance(value, str) and value.strip() for value in payload
    ):
        raise ValueError(f"{where} must be a list of non-empty strings.")
    return tuple(value.strip() for value in payload)


def _require_unique(values: Sequence[object], *, where: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{where} must be unique.")


def _require_exact_case_keys(
    dataset: MultiCorpusEvalDataset,
    payload: Mapping[str, object],
    *,
    label: str,
) -> None:
    expected = set(dataset.cases_by_id)
    if set(payload) != expected:
        missing = sorted(expected - set(payload))
        extra = sorted(set(payload) - expected)
        raise ValueError(f"{label} do not match dataset cases (missing={missing}, extra={extra}).")
