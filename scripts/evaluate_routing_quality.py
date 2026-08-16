#!/usr/bin/env python3
"""Collect Buoy's content-free, route-only scalable-routing evidence.

The live boundary reads only namespace inventory and the authoritative routing
catalog.  It never opens dotenv files, constructs a content namespace, exposes
a provider mutation method, or persists questions, examples, passages,
vectors, credentials, or provider payloads.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Mapping, Sequence

from buoy_search import routing_quality as routing_quality_module
from buoy_search.catalog import (
    ROUTING_DIMENSIONS,
    ROUTING_MODEL,
    ROUTING_MODEL_REVISION,
    ROUTING_PRECISION,
    NamespaceCard,
    RoutingEmbedder,
    load_routing_embedder,
)
from buoy_search.config import load_config
from buoy_search.cross_encoder import (
    CROSS_ENCODER_BATCH_SIZE,
    CROSS_ENCODER_MAX_LENGTH,
    CROSS_ENCODER_MODEL,
    CROSS_ENCODER_REVISION,
    CrossEncoderReranker,
    load_cross_encoder_reranker,
)
from buoy_search.multi_corpus_evals import DEFAULT_MULTI_CORPUS_EVAL_DATASET
from buoy_search.plan_artifacts import stable_hash
from buoy_search.remote_catalog import (
    REMOTE_CATALOG_NAMESPACE,
    CompatibilityContract,
    RemoteCatalogSnapshot,
    create_client,
    read_remote_catalog,
    require_complete_routing_coverage,
)
from buoy_search.routing import (
    DEFAULT_ROUTE_TOP_K,
    ROUTING_PROTOTYPE_CONTRACT,
    PrototypeRouteScore,
    hybrid_route,
    named_route,
    prototype_route_scores,
    semantic_route,
)
from buoy_search.routing_quality import (
    DEFAULT_ROUTING_CALIBRATION,
    DEFAULT_ROUTING_CANARY_DIR,
    ROUTING_MAX_EXAMPLES,
    ROUTING_MAX_FANOUT,
    ROUTING_QUALITY_EVALUATOR_VERSION,
    ROUTING_QUALITY_RUN_SCHEMA_VERSION,
    ROUTING_ROUTE_CONTRACT_REVISION,
    ROUTING_SHORTLIST_LIMIT,
    RoutingCaseMetrics,
    RoutingCaseObservation,
    RoutingConfidenceCalibration,
    RoutingCorpusObservation,
    RoutingQualityDataset,
    RoutingQualityMetrics,
    RoutingRouteObservation,
    RoutingThresholdCalibration,
    calibrate_routing_thresholds,
    gate_routing_quality,
    load_routing_confidence_calibration,
    load_routing_quality_dataset,
    routing_catalog_projection_sha256,
    routing_certification_dataset,
    score_route_selection_quality,
    score_routing_quality,
    validate_canary_catalog_contract,
)


LIVE_COLLECTOR_PROVENANCE_MARKER = "buoy.routing_quality.live_collector/v1"


class RoutingQualityCollectionError(RuntimeError):
    """The read-only route collector could not produce trustworthy evidence."""


class _ReadOnlyCatalogNamespace:
    """Expose only the two catalog reads used by ``read_remote_catalog``."""

    def __init__(self, delegate: object) -> None:
        self._delegate = delegate

    def metadata(self, **kwargs: object) -> object:
        method = getattr(self._delegate, "metadata", None)
        if method is None:
            raise RoutingQualityCollectionError(
                "provider catalog resource has no metadata API"
            )
        return method(**kwargs)

    def query(self, **kwargs: object) -> object:
        method = getattr(self._delegate, "query", None)
        if method is None:
            raise RoutingQualityCollectionError(
                "provider catalog resource has no query API"
            )
        return method(**kwargs)


class _ReadOnlyCatalogClient:
    """Restrict an injected provider client to inventory and one catalog."""

    def __init__(self, delegate: object) -> None:
        self._delegate = delegate

    def namespaces(self, **kwargs: object) -> object:
        method = getattr(self._delegate, "namespaces", None)
        if method is None:
            raise RoutingQualityCollectionError(
                "provider client has no namespace inventory API"
            )
        return method(**kwargs)

    def namespace(self, namespace: str) -> _ReadOnlyCatalogNamespace:
        if namespace != REMOTE_CATALOG_NAMESPACE:
            raise RoutingQualityCollectionError(
                "route-only evaluation may acquire only the routing catalog"
            )
        method = getattr(self._delegate, "namespace", None)
        if method is None:
            raise RoutingQualityCollectionError(
                "provider client has no namespace resource API"
            )
        return _ReadOnlyCatalogNamespace(method(namespace))


class _MemoizingCountingRoutingEmbedder:
    """Reuse one real query inference across candidate and baseline routing."""

    def __init__(self, delegate: RoutingEmbedder) -> None:
        self._delegate = delegate
        self._cache: dict[str, list[float]] = {}
        self.inference_calls = 0
        self.encode_requests = 0

    def reset_case_cache(self) -> None:
        self._cache.clear()

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        self.encode_requests += 1
        missing: list[str] = []
        for value in texts:
            if value not in self._cache and value not in missing:
                missing.append(value)
        if missing:
            encoded = self._delegate.encode(missing)
            if len(encoded) != len(missing):
                raise RoutingQualityCollectionError(
                    "routing embedder returned the wrong number of vectors"
                )
            self.inference_calls += 1
            for value, vector in zip(missing, encoded, strict=True):
                self._cache[value] = list(vector)
        return [list(self._cache[value]) for value in texts]


class _CountingReranker:
    def __init__(self, delegate: CrossEncoderReranker) -> None:
        self._delegate = delegate
        self.inference_calls = 0
        self.passages_scored = 0
        self.maximum_passages_per_call = 0

    def score(self, query: str, passages: Sequence[str]) -> list[float]:
        self.inference_calls += 1
        self.passages_scored += len(passages)
        self.maximum_passages_per_call = max(
            self.maximum_passages_per_call, len(passages)
        )
        return self._delegate.score(query, passages)


def collect_live_run(
    dataset: RoutingQualityDataset,
    *,
    collector_invocation: Sequence[str],
) -> dict[str, object]:
    """Collect one read-only candidate/baseline observation for every case."""

    api_key = os.environ.get("TURBOPUFFER_API_KEY")
    if not api_key:
        raise RoutingQualityCollectionError(
            "TURBOPUFFER_API_KEY must already be set in the process environment; "
            "this evaluator does not load .env files"
        )

    config = load_config()
    raw_client = create_client(api_key=api_key, region=config.region)
    client = _ReadOnlyCatalogClient(raw_client)
    snapshot = require_complete_routing_coverage(
        read_remote_catalog(
            client,
            region=config.region,
            compatibility=CompatibilityContract(
                region=config.region,
                embedding_model=config.embedding_model,
                embedding_precision=config.embedding_precision,
            ),
        )
    )
    cards = tuple(snapshot.eligible_cards)
    catalog_projection_sha256 = validate_canary_catalog_contract(dataset, cards)
    confidence_artifact = load_routing_confidence_calibration()

    embedder = _MemoizingCountingRoutingEmbedder(load_routing_embedder())
    reranker = _CountingReranker(load_cross_encoder_reranker())
    raw_candidate: dict[str, RoutingCaseObservation] = {}
    baseline_routes: dict[str, RoutingRouteObservation] = {}
    case_latencies: list[tuple[str, float]] = []

    for case in dataset.cases:
        started = time.perf_counter()
        embedder.reset_case_cache()
        names = named_route(case.question, cards)
        scores = prototype_route_scores(
            case.question,
            cards,
            embedder=embedder,
            reranker=reranker,
            include_exact_names=True,
        )
        raw_candidate[case.id] = _collect_candidate_observation(
            case_id=case.id,
            scores=scores,
            exact_name_namespaces=tuple(card.namespace for card in names),
        )
        baseline_routes[case.id] = _collect_legacy_baseline(
            case_id=case.id,
            query=case.question,
            cards=cards,
            exact_name_namespaces=tuple(card.namespace for card in names),
            embedder=embedder,
            snapshot=snapshot,
            region=config.region,
        )
        if embedder.inference_calls != len(raw_candidate):
            raise RoutingQualityCollectionError(
                f"case {case.id!r} did not reuse exactly one routing query inference"
            )
        case_latencies.append((case.id, _elapsed_ms(started)))

    expected_cases = len(dataset.cases)
    if reranker.inference_calls != expected_cases:
        raise RoutingQualityCollectionError(
            "route-only collection did not perform exactly one bounded reranker inference per case"
        )
    if reranker.maximum_passages_per_call > (
        ROUTING_SHORTLIST_LIMIT * (ROUTING_MAX_EXAMPLES + 1)
    ):
        raise RoutingQualityCollectionError(
            "route-only collection exceeded the bounded prototype passage count"
        )

    threshold_calibration = calibrate_routing_thresholds(dataset, raw_candidate)
    candidate = {
        case.id: _apply_candidate_calibration(
            raw_candidate[case.id], threshold_calibration
        )
        for case in dataset.cases
    }
    certification = routing_certification_dataset(dataset)
    certification_ids = set(certification.cases_by_id)
    candidate_certification = {
        case_id: observation
        for case_id, observation in candidate.items()
        if case_id in certification_ids
    }
    baseline_certification = {
        case_id: observation
        for case_id, observation in baseline_routes.items()
        if case_id in certification_ids
    }
    metrics = score_routing_quality(certification, candidate_certification)
    baseline_metrics = score_route_selection_quality(
        certification, baseline_certification
    )
    quality_verdict = gate_routing_quality(
        certification,
        metrics,
        calibration=threshold_calibration,
        eligible_namespaces=[card.namespace for card in cards],
        baseline=baseline_metrics,
    )
    code = _git_code_identity()
    calls = _call_accounting(
        snapshot,
        case_count=expected_cases,
        embedder=embedder,
        reranker=reranker,
    )
    activation = _activation_verdict(
        dataset=dataset,
        confidence_artifact=confidence_artifact,
        threshold_calibration=threshold_calibration,
        certification=certification,
        quality_verdict=quality_verdict.to_dict(),
        catalog_projection_sha256=catalog_projection_sha256,
        calls=calls,
        code=code,
    )
    return {
        "schema_version": ROUTING_QUALITY_RUN_SCHEMA_VERSION,
        "mode": "live",
        "provenance": _provenance(
            dataset,
            snapshot=snapshot,
            confidence_artifact=confidence_artifact,
            catalog_projection_sha256=catalog_projection_sha256,
            collector_invocation=collector_invocation,
            code=code,
        ),
        "read_only_boundary": {
            "provider_mutation_methods_exposed": False,
            "provider_mutations_precluded": True,
            "content_namespace_resources_acquired": 0,
        },
        "catalog": _catalog_report(snapshot, catalog_projection_sha256),
        "calls": calls,
        "latency_ms": _latency_report(case_latencies),
        "threshold_calibration": threshold_calibration.to_dict(),
        "candidate_observations": [
            _candidate_observation_dict(candidate[case.id])
            for case in dataset.cases
        ],
        "legacy_baseline_observations": [
            _route_observation_dict(baseline_routes[case.id])
            for case in dataset.cases
        ],
        "metrics": _metrics_dict(metrics),
        "legacy_baseline_metrics": _metrics_dict(baseline_metrics),
        "quality_verdict": quality_verdict.to_dict(),
        "activation": activation,
    }


def _collect_candidate_observation(
    *,
    case_id: str,
    scores: Sequence[PrototypeRouteScore],
    exact_name_namespaces: tuple[str, ...],
) -> RoutingCaseObservation:
    if not scores:
        raise RoutingQualityCollectionError(
            f"case {case_id!r} produced no prototype routing scores"
        )
    ranked = sorted(scores, key=lambda item: item.reranker_rank)
    shortlisted = sorted(scores, key=lambda item: item.shortlist_rank)
    exact = set(exact_name_namespaces)
    if exact_name_namespaces:
        if len(exact_name_namespaces) == 1:
            fallback = tuple(
                item.card.namespace
                for item in shortlisted[:ROUTING_MAX_FANOUT]
            )
            initial = fallback[:1]
            reason = "unique_title_or_alias"
        else:
            fallback = exact_name_namespaces
            initial = fallback
            reason = "multiple_named_corpora"
        high_confidence = True
    else:
        fallback = tuple(
            item.card.namespace
            for item in ranked[:ROUTING_MAX_FANOUT]
        )
        initial = fallback
        reason = "ambiguous_prototype"
        high_confidence = False
    margin = (
        ranked[0].reranker_score - ranked[1].reranker_score
        if len(ranked) > 1
        else None
    )
    corpus_scores = tuple(
        RoutingCorpusObservation(
            namespace=item.card.namespace,
            shortlist_rank=item.shortlist_rank,
            shortlist_cosine_score=item.shortlist_cosine_score,
            reranker_rank=item.reranker_rank,
            reranker_score=item.reranker_score,
            exact_name_match=item.card.namespace in exact,
            winning_prototype_kind=item.winning_prototype_kind,
            winning_prototype_index=item.winning_prototype_index,
            winning_prototype_hash=item.winning_prototype_hash,
        )
        for item in ranked
    )
    return RoutingCaseObservation(
        case_id=case_id,
        corpus_scores=corpus_scores,
        reranker_margin=margin,
        fallback_namespaces=fallback,
        initial_namespaces=initial,
        selection_reason=reason,
        high_confidence=high_confidence,
        initial_fanout=len(initial),
    )


def _collect_legacy_baseline(
    *,
    case_id: str,
    query: str,
    cards: Sequence[NamespaceCard],
    exact_name_namespaces: tuple[str, ...],
    embedder: RoutingEmbedder,
    snapshot: RemoteCatalogSnapshot,
    region: str,
) -> RoutingRouteObservation:
    selection = hybrid_route(
        query,
        cards,
        embedder=embedder,
        route_top_k=DEFAULT_ROUTE_TOP_K,
        catalog_namespace=REMOTE_CATALOG_NAMESPACE,
        region=region,
        snapshot_revision=snapshot.snapshot_revision,
    )
    semantic = semantic_route(
        query,
        cards,
        embedder=embedder,
    )
    exact = set(exact_name_namespaces)
    shortlist = tuple(
        [
            *exact_name_namespaces,
            *(
                card.namespace
                for card, _score in semantic
                if card.namespace not in exact
            ),
        ][:ROUTING_SHORTLIST_LIMIT]
    )
    fallback = tuple(card.namespace for card in selection.selected_cards)
    initial = fallback[: selection.initial_fanout]
    return RoutingRouteObservation(
        case_id=case_id,
        shortlist_namespaces=shortlist,
        exact_name_namespaces=exact_name_namespaces,
        fallback_namespaces=fallback,
        initial_namespaces=initial,
        selection_reason=selection.selection_reason,
        high_confidence=selection.high_confidence,
        initial_fanout=selection.initial_fanout,
    )


def _apply_candidate_calibration(
    observation: RoutingCaseObservation,
    calibration: RoutingThresholdCalibration,
) -> RoutingCaseObservation:
    if observation.selection_reason in {
        "unique_title_or_alias",
        "multiple_named_corpora",
    }:
        return observation
    ranked = sorted(
        observation.corpus_scores, key=lambda item: item.reranker_rank
    )
    confident = bool(
        ranked[0].reranker_score >= calibration.score_floor
        and observation.reranker_margin is not None
        and observation.reranker_margin >= calibration.margin_floor
    )
    if not confident:
        return observation
    return replace(
        observation,
        initial_namespaces=observation.fallback_namespaces[:1],
        selection_reason="high_confidence_prototype",
        high_confidence=True,
        initial_fanout=1,
    )


def _call_accounting(
    snapshot: RemoteCatalogSnapshot,
    *,
    case_count: int,
    embedder: _MemoizingCountingRoutingEmbedder,
    reranker: _CountingReranker,
) -> dict[str, object]:
    return {
        "case_count": case_count,
        "routing_query_embedding_inference_calls": embedder.inference_calls,
        "routing_embedder_cache_requests": embedder.encode_requests,
        "routing_reranker_inference_calls": reranker.inference_calls,
        "routing_reranker_passages_scored": reranker.passages_scored,
        "maximum_routing_reranker_passages_per_call": (
            reranker.maximum_passages_per_call
        ),
        "provider": {
            "namespace_list_pages": snapshot.metrics.namespace_list_pages,
            "metadata_requests": snapshot.metrics.metadata_requests,
            "catalog_query_pages": snapshot.metrics.card_query_pages,
            "shortlist_or_per_card_queries": 0,
            "content_queries": 0,
            "writes": 0,
        },
        "model_downloads": 0,
    }


def _activation_verdict(
    *,
    dataset: RoutingQualityDataset,
    confidence_artifact: RoutingConfidenceCalibration,
    threshold_calibration: RoutingThresholdCalibration,
    certification: RoutingQualityDataset,
    quality_verdict: Mapping[str, object],
    catalog_projection_sha256: str,
    calls: Mapping[str, object],
    code: Mapping[str, object],
) -> dict[str, object]:
    unapproved = sorted(
        pack.namespace
        for pack in dataset.packs
        if not pack.human_approved or pack.review_status != "approved"
    )
    bindings = confidence_artifact.bindings
    active_authority = bool(
        confidence_artifact.mode == "active"
        and confidence_artifact.owner_approved is True
    )
    artifact_bound = bool(
        bindings.canary_suite_sha256 == dataset.suite_sha256
        and bindings.catalog_projection_sha256 == catalog_projection_sha256
    )
    calibration_receipt = confidence_artifact.calibration
    calibration_bound = bool(
        confidence_artifact.score_floor == threshold_calibration.score_floor
        and confidence_artifact.margin_floor == threshold_calibration.margin_floor
        and calibration_receipt is not None
        and calibration_receipt.case_count
        == threshold_calibration.calibration_case_count
        and calibration_receipt.case_ids_sha256
        == threshold_calibration.calibration_case_ids_sha256
        and calibration_receipt.incorrect_high_confidence_singletons
        == threshold_calibration.incorrect_high_confidence_singletons
    )
    certification_ids_sha256 = stable_hash(
        [case.id for case in certification.cases]
    )
    quality_verdict_sha256 = _canonical_sha256(quality_verdict)
    certification_bound = bool(
        confidence_artifact.certification_passed is True
        and confidence_artifact.certification_case_count == len(certification.cases)
        and confidence_artifact.certification_case_ids_sha256
        == certification_ids_sha256
        and confidence_artifact.certification_verdict_sha256
        == quality_verdict_sha256
    )
    receipts = confidence_artifact.receipts
    evaluator_receipts_bound = bool(
        receipts is not None
        and receipts.evaluator_runner_sha256 == _file_sha256(Path(__file__))
        and receipts.evaluator_scorer_sha256
        == _file_sha256(Path(str(routing_quality_module.__file__)))
    )
    provider = calls["provider"]
    if not isinstance(provider, Mapping):
        raise AssertionError("provider call accounting must be an object")
    read_only = bool(
        provider["shortlist_or_per_card_queries"] == 0
        and provider["content_queries"] == 0
        and provider["writes"] == 0
        and calls["model_downloads"] == 0
    )
    checks: dict[str, dict[str, object]] = {
        "route_quality_gates": {
            "passed": quality_verdict.get("passed") is True,
            "observed": quality_verdict.get("passed"),
            "required": True,
        },
        "canary_packs_owner_approved": {
            "passed": not unapproved,
            "observed": unapproved,
            "required": [],
        },
        "owner_approved_active_confidence_artifact": {
            "passed": confidence_artifact.mode == "active"
            and confidence_artifact.owner_approved,
            "observed": {
                "mode": confidence_artifact.mode,
                "owner_approved": confidence_artifact.owner_approved,
            },
            "required": {"mode": "active", "owner_approved": True},
        },
        "confidence_artifact_bindings": {
            "passed": artifact_bound,
            "observed": {
                "canary_suite_sha256": bindings.canary_suite_sha256,
                "catalog_projection_sha256": bindings.catalog_projection_sha256,
            },
            "required": {
                "canary_suite_sha256": dataset.suite_sha256,
                "catalog_projection_sha256": catalog_projection_sha256,
            },
        },
        "confidence_threshold_calibration_receipt": {
            "passed": not active_authority or calibration_bound,
            "observed": {
                "score_floor": confidence_artifact.score_floor,
                "margin_floor": confidence_artifact.margin_floor,
                "case_count": (
                    calibration_receipt.case_count
                    if calibration_receipt is not None
                    else None
                ),
                "case_ids_sha256": (
                    calibration_receipt.case_ids_sha256
                    if calibration_receipt is not None
                    else None
                ),
                "incorrect_high_confidence_singletons": (
                    calibration_receipt.incorrect_high_confidence_singletons
                    if calibration_receipt is not None
                    else None
                ),
            },
            "required": {
                "score_floor": threshold_calibration.score_floor,
                "margin_floor": threshold_calibration.margin_floor,
                "case_count": threshold_calibration.calibration_case_count,
                "case_ids_sha256": (
                    threshold_calibration.calibration_case_ids_sha256
                ),
                "incorrect_high_confidence_singletons": (
                    threshold_calibration.incorrect_high_confidence_singletons
                ),
            },
        },
        "confidence_certification_receipt": {
            "passed": not active_authority or certification_bound,
            "observed": {
                "passed": confidence_artifact.certification_passed,
                "case_count": confidence_artifact.certification_case_count,
                "case_ids_sha256": (
                    confidence_artifact.certification_case_ids_sha256
                ),
                "verdict_sha256": (
                    confidence_artifact.certification_verdict_sha256
                ),
            },
            "required": {
                "passed": True,
                "case_count": len(certification.cases),
                "case_ids_sha256": certification_ids_sha256,
                "verdict_sha256": quality_verdict_sha256,
            },
        },
        "confidence_evaluator_source_receipts": {
            "passed": not active_authority or evaluator_receipts_bound,
            "observed": {
                "runner_sha256": (
                    receipts.evaluator_runner_sha256
                    if receipts is not None
                    else None
                ),
                "scorer_sha256": (
                    receipts.evaluator_scorer_sha256
                    if receipts is not None
                    else None
                ),
            },
            "required": {
                "runner_sha256": _file_sha256(Path(__file__)),
                "scorer_sha256": _file_sha256(
                    Path(str(routing_quality_module.__file__))
                ),
            },
        },
        "clean_source_checkout": {
            "passed": code.get("working_tree_clean") is True,
            "observed": code.get("working_tree_clean"),
            "required": True,
        },
        "read_only_call_accounting": {
            "passed": read_only,
            "observed": {
                "shortlist_or_per_card_queries": provider[
                    "shortlist_or_per_card_queries"
                ],
                "content_queries": provider["content_queries"],
                "writes": provider["writes"],
                "model_downloads": calls["model_downloads"],
            },
            "required": {
                "shortlist_or_per_card_queries": 0,
                "content_queries": 0,
                "writes": 0,
                "model_downloads": 0,
            },
        },
    }
    failed = [name for name, check in checks.items() if not check["passed"]]
    return {
        "ready": not failed,
        "status": "pass" if not failed else "collect_only",
        "failed_checks": failed,
        "checks": checks,
    }


def _catalog_report(
    snapshot: RemoteCatalogSnapshot,
    projection_sha256: str,
) -> dict[str, object]:
    return {
        "namespace": REMOTE_CATALOG_NAMESPACE,
        "schema_version": snapshot.catalog_schema_version,
        "snapshot_revision": snapshot.snapshot_revision,
        "routing_projection_sha256": projection_sha256,
        "live_namespaces": list(snapshot.live_namespace_ids),
        "eligible_namespaces": [card.namespace for card in snapshot.eligible_cards],
        "disabled_namespaces": list(snapshot.disabled_ids),
        "stale_namespaces": list(snapshot.stale_target_ids),
        "missing_namespaces": list(snapshot.missing_card_ids),
        "incompatible_namespaces": list(snapshot.incompatible_ids),
        "eligible_card_identities": [
            {
                "namespace": card.namespace,
                "card_revision": card.card_revision,
                "routing_prototype_hash": card.routing_prototype_hash,
                "routing_prototype_vector_hash": (
                    card.routing_prototype_vector_hash
                ),
                "routing_example_count": len(card.routing_examples),
            }
            for card in snapshot.eligible_cards
        ],
    }


def _provenance(
    dataset: RoutingQualityDataset,
    *,
    snapshot: RemoteCatalogSnapshot,
    confidence_artifact: RoutingConfidenceCalibration,
    catalog_projection_sha256: str,
    collector_invocation: Sequence[str],
    code: Mapping[str, object],
) -> dict[str, object]:
    package_dir = Path(str(routing_quality_module.__file__)).resolve().parent
    return {
        "origin": LIVE_COLLECTOR_PROVENANCE_MARKER,
        "collector_produced": True,
        "collector_invocation": list(collector_invocation),
        "code": dict(code),
        "dataset": {
            "suite_sha256": dataset.suite_sha256,
            "legacy_dataset_id": dataset.legacy_dataset_id,
            "legacy_dataset_sha256": dataset.legacy_dataset_sha256,
            "packs": [
                {
                    "corpus_id": pack.corpus_id,
                    "namespace": pack.namespace,
                    "raw_sha256": pack.raw_sha256,
                    "review_status": pack.review_status,
                    "human_approved": pack.human_approved,
                    "route_contract_revision": pack.route_contract_revision,
                }
                for pack in dataset.packs
            ],
        },
        "catalog_snapshot_revision": snapshot.snapshot_revision,
        "catalog_projection_sha256": catalog_projection_sha256,
        "models": {
            "routing_embedding": {
                "model": ROUTING_MODEL,
                "revision": ROUTING_MODEL_REVISION,
                "precision": ROUTING_PRECISION,
                "dimensions": ROUTING_DIMENSIONS,
            },
            "routing_reranker": {
                "model": CROSS_ENCODER_MODEL,
                "revision": CROSS_ENCODER_REVISION,
                "device": "cpu",
                "batch_size": CROSS_ENCODER_BATCH_SIZE,
                "max_length": CROSS_ENCODER_MAX_LENGTH,
            },
        },
        "contracts": {
            "prototype": ROUTING_PROTOTYPE_CONTRACT,
            "route_canaries": ROUTING_ROUTE_CONTRACT_REVISION,
            "projection": confidence_artifact.bindings.projection,
            "legacy_baseline": "hybrid_route_same_snapshot_cached_query_v1",
        },
        "confidence_artifact": _confidence_artifact_dict(confidence_artifact),
        "evaluator": {
            "version": ROUTING_QUALITY_EVALUATOR_VERSION,
            "runner_sha256": _file_sha256(Path(__file__)),
            "scorer_sha256": _file_sha256(
                Path(str(routing_quality_module.__file__))
            ),
            "artifact_sha256": _file_sha256(DEFAULT_ROUTING_CALIBRATION),
            "routing_module_sha256": _file_sha256(package_dir / "routing.py"),
            "cli_module_sha256": _file_sha256(package_dir / "cli.py"),
            "evidence_module_sha256": _file_sha256(package_dir / "evidence.py"),
        },
    }


def _confidence_artifact_dict(
    value: RoutingConfidenceCalibration,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": value.schema_version,
        "calibration_id": value.calibration_id,
        "calibration_revision": value.calibration_revision,
        "mode": value.mode,
        "owner_approved": value.owner_approved,
        "score_floor": value.score_floor,
        "margin_floor": value.margin_floor,
        "bindings": {
            "routing_model": value.bindings.routing_model,
            "routing_model_revision": value.bindings.routing_model_revision,
            "routing_reranker_model": value.bindings.routing_reranker_model,
            "routing_reranker_revision": value.bindings.routing_reranker_revision,
            "schema_contract": value.bindings.schema_contract,
            "projection": value.bindings.projection,
            "shortlist_limit": value.bindings.shortlist_limit,
            "max_examples": value.bindings.max_examples,
            "feature_contract": value.bindings.feature_contract,
            "score_field": value.bindings.score_field,
            "margin_field": value.bindings.margin_field,
            "canary_suite_sha256": value.bindings.canary_suite_sha256,
            "catalog_projection_sha256": (
                value.bindings.catalog_projection_sha256
            ),
        },
        "certification": {
            "passed": value.certification_passed,
            "case_count": value.certification_case_count,
            "case_ids_sha256": value.certification_case_ids_sha256,
            "verdict_sha256": value.certification_verdict_sha256,
        },
    }
    if value.calibration is not None:
        payload["calibration"] = {
            "case_count": value.calibration.case_count,
            "case_ids_sha256": value.calibration.case_ids_sha256,
            "incorrect_high_confidence_singletons": (
                value.calibration.incorrect_high_confidence_singletons
            ),
        }
    if value.receipts is not None:
        payload["receipts"] = {
            "authorization_report_sha256": (
                value.receipts.authorization_report_sha256
            ),
            "authorization_source_commit": (
                value.receipts.authorization_source_commit
            ),
            "authorization_source_tree": value.receipts.authorization_source_tree,
            "certified_dormant_report_sha256": (
                value.receipts.certified_dormant_report_sha256
            ),
            "certified_dormant_source_commit": (
                value.receipts.certified_dormant_source_commit
            ),
            "certified_dormant_source_tree": (
                value.receipts.certified_dormant_source_tree
            ),
            "certified_dormant_working_tree_clean": (
                value.receipts.certified_dormant_working_tree_clean
            ),
            "evaluator_runner_sha256": value.receipts.evaluator_runner_sha256,
            "evaluator_scorer_sha256": value.receipts.evaluator_scorer_sha256,
            "routing_module_sha256": value.receipts.routing_module_sha256,
            "cli_module_sha256": value.receipts.cli_module_sha256,
            "evidence_module_sha256": value.receipts.evidence_module_sha256,
            "collect_artifact_sha256": value.receipts.collect_artifact_sha256,
        }
    return payload


def _candidate_observation_dict(
    value: RoutingCaseObservation,
) -> dict[str, object]:
    return {
        "case_id": value.case_id,
        "corpus_scores": [
            {
                "namespace": item.namespace,
                "shortlist_rank": item.shortlist_rank,
                "shortlist_cosine_score": item.shortlist_cosine_score,
                "reranker_rank": item.reranker_rank,
                "reranker_score": item.reranker_score,
                "exact_name_match": item.exact_name_match,
                "winning_prototype_kind": item.winning_prototype_kind,
                "winning_prototype_index": item.winning_prototype_index,
                "winning_prototype_hash": item.winning_prototype_hash,
            }
            for item in value.corpus_scores
        ],
        "reranker_margin": value.reranker_margin,
        "fallback_namespaces": list(value.fallback_namespaces),
        "initial_namespaces": list(value.initial_namespaces),
        "selection_reason": value.selection_reason,
        "high_confidence": value.high_confidence,
        "initial_fanout": value.initial_fanout,
    }


def _route_observation_dict(value: RoutingRouteObservation) -> dict[str, object]:
    return {
        "case_id": value.case_id,
        "shortlist_namespaces": list(value.shortlist_namespaces),
        "exact_name_namespaces": list(value.exact_name_namespaces),
        "fallback_namespaces": list(value.fallback_namespaces),
        "initial_namespaces": list(value.initial_namespaces),
        "selection_reason": value.selection_reason,
        "high_confidence": value.high_confidence,
        "initial_fanout": value.initial_fanout,
    }


def _metrics_dict(value: RoutingQualityMetrics) -> dict[str, object]:
    return {
        **value.to_dict(),
        "cases": [_case_metrics_dict(item) for item in value.case_metrics],
    }


def _case_metrics_dict(value: RoutingCaseMetrics) -> dict[str, object]:
    return {
        "case_id": value.case_id,
        "subject_namespace": value.subject_namespace,
        "expected_namespaces": list(value.expected_namespaces),
        "shortlist_found": value.shortlist_found,
        "shortlist_complete": value.shortlist_complete,
        "route_found": value.route_found,
        "route_complete": value.route_complete,
        "named_self_passed": value.named_self_passed,
        "contrast_passed": value.contrast_passed,
        "multi_corpus_passed": value.multi_corpus_passed,
        "incorrect_high_confidence_singleton": (
            value.incorrect_high_confidence_singleton
        ),
        "no_answer_high_confidence_singleton": (
            value.no_answer_high_confidence_singleton
        ),
    }


def _latency_report(values: Sequence[tuple[str, float]]) -> dict[str, object]:
    samples = sorted(value for _case_id, value in values)
    if not samples:
        raise RoutingQualityCollectionError("route-only latency sample is empty")

    def percentile(fraction: float) -> float:
        index = max(0, math.ceil(fraction * len(samples)) - 1)
        return samples[index]

    return {
        "case_count": len(values),
        "minimum": samples[0],
        "p50": percentile(0.50),
        "p95": percentile(0.95),
        "maximum": samples[-1],
        "cases": [
            {"case_id": case_id, "total": elapsed}
            for case_id, elapsed in values
        ],
    }


def _git_code_identity() -> dict[str, object]:
    repo = Path(__file__).resolve().parents[1]

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
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RoutingQualityCollectionError(
            "live routing evidence requires an identifiable Git commit and tree"
        ) from exc
    return {
        "commit": commit,
        "tree": tree,
        "working_tree_clean": not bool(status),
    }


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _elapsed_ms(started: float) -> float:
    return (time.perf_counter() - started) * 1000.0


def _write_report(path: Path, report: Mapping[str, object]) -> None:
    if path.exists():
        raise ValueError(f"refusing to overwrite existing evaluation report: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(
        report,
        allow_nan=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)
        handle.write(serialized)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temp_path, path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect Buoy's provider-read-only scalable-routing gate."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    collect = commands.add_parser(
        "collect",
        help="score authoritative live routing cards without content queries or writes",
    )
    collect.add_argument(
        "--canary-dir",
        type=Path,
        default=DEFAULT_ROUTING_CANARY_DIR,
    )
    collect.add_argument(
        "--legacy-dataset",
        type=Path,
        default=DEFAULT_MULTI_CORPUS_EVAL_DATASET,
    )
    collect.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.output.exists():
            raise ValueError(
                f"refusing to overwrite existing evaluation report: {args.output}"
            )
        dataset = load_routing_quality_dataset(
            canary_dir=args.canary_dir,
            legacy_dataset_path=args.legacy_dataset,
        )
        invocation = (
            "collect",
            "--canary-dir",
            str(args.canary_dir.resolve()),
            "--legacy-dataset",
            str(args.legacy_dataset.resolve()),
            "--output",
            str(args.output.resolve()),
        )
        report = collect_live_run(dataset, collector_invocation=invocation)
        _write_report(args.output, report)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"Routing quality evaluation failed: {exc}", file=sys.stderr)
        return 2

    activation = report["activation"]
    if not isinstance(activation, Mapping):
        raise AssertionError("routing activation verdict must be an object")
    print(
        json.dumps(
            {
                "activation_ready": activation["ready"],
                "status": activation["status"],
                "failed_checks": activation["failed_checks"],
            },
            sort_keys=True,
        )
    )
    return 0 if activation["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
