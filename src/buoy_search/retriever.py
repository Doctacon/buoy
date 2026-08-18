"""Hybrid retrieval helpers for turbopuffer-backed site search.

Dry-run planning is local-only. Live retrieval is intentionally isolated behind
``HybridRetriever.from_config`` so credentials are read only when the caller has
explicitly opted into a live turbopuffer query.
"""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field, replace
import hashlib
import math
import os
import re
from typing import Any, Callable, Literal, Mapping, Protocol, Sequence
import unicodedata

from buoy_search.config import RuntimeConfig
from buoy_search.chunker import SentenceTransformerEmbedder
from buoy_search.cross_encoder import (
    CROSS_ENCODER_MODEL,
    CROSS_ENCODER_REVISION,
    CrossEncoderReranker,
    CrossEncoderRerankerError,
    load_cross_encoder_reranker,
)
from buoy_search.evidence import (
    EvidenceCalibration,
    EvidenceCalibrationError,
    EvidenceDecision as CalibratedEvidenceDecision,
    NON_COLLECT_ACTIVATION_PAUSED_MESSAGE,
    OWNER_AUTHORIZED_ACTIVE_CALIBRATION,
    decide_evidence,
    observe_evidence_scores,
)
from buoy_search.telemetry import (
    EVIDENCE_SPAN_NAME,
    NAMESPACE_QUERY_SPAN_NAME,
    QUERY_EMBED_SPAN_NAME,
    RERANK_SPAN_NAME,
    TelemetrySpan,
    copied_context_callable,
    retrieval_trace,
    telemetry_span,
)

DEFAULT_TOP_K = 5
DEFAULT_CANDIDATES = 200
DEFAULT_RANKING_POOL = 100
DEFAULT_RANKING_MODE = "file"
DEFAULT_RANKING_PROFILE = "repo_code"
DEFAULT_RANKING_AGGREGATION = "adaptive_sum_3"
DEFAULT_WEBSITE_RANKING_MODE = "page"
DEFAULT_WEBSITE_RANKING_PROFILE = "none"
DEFAULT_WEBSITE_RANKING_POOL = 20
DEFAULT_WEBSITE_RANKING_AGGREGATION = "max"
RANKING_MODES = {"chunk", "file", "page"}
RANKING_PROFILES = {"none", "repo_code"}
RANKING_AGGREGATIONS = {"max", "adaptive_sum_3", "capped_sum_3"}
RRF_K = 60
MAX_NAMESPACE_FANOUT = 3
MAX_RERANK_CANDIDATES_PER_NAMESPACE = 8
EVIDENCE_ASSESSMENT_TOP_K = 5
EVIDENCE_PUBLIC_DIAGNOSTIC_FIELDS = frozenset(
    {
        "mode",
        "status",
        "reason",
        "model",
        "model_revision",
        "calibration_id",
        "calibration_revision",
        "feature_contract",
        "threshold",
        "widening_triggered_by_weak_evidence",
        "top_score",
        "second_score",
        "score_gap",
        "candidates_scored",
        "route_selection_reason",
        "route_semantic_score",
        "route_semantic_margin",
        "namespace_failure_count",
    }
)
CROSS_NAMESPACE_RRF_K = 60
CROSS_NAMESPACE_FUSION_METHOD = "equal_weight_ordinal_rrf"
CROSS_NAMESPACE_FUSION = "cross_namespace_equal_weight_ordinal_rrf"
CROSS_NAMESPACE_FUSION_COMPONENTS = (
    "cross_encoder_rank",
    "namespace_rank",
)
CROSS_NAMESPACE_FUSION_TIE_BREAKERS = (
    "cross_encoder_rank",
    "route_rank",
    "namespace_rank",
    "namespace",
    "id",
)
MAX_RERANK_TITLE_CHARS = 512
MAX_RERANK_SECTION_CHARS = 1_024
MAX_RERANK_LOCATION_CHARS = 2_048
MAX_RERANK_CONTENT_CHARS = 8_192
AGENT_ARTIFACT_PATH_SEGMENTS = {".10x", ".agents", ".buoy", ".claude", ".cursor", ".loom", ".pi", ".turbo-search"}
RETRIEVAL_ATTRIBUTES = [
    "title",
    "url",
    "section_path",
    "content",
    "path",
    "repo_path",
    "tags",
    "doc_kind",
    "chunk_index",
]
OPTIONAL_RETRIEVAL_ATTRIBUTES = ("repo_path", "tags")
MISSING_SCHEMA_ATTRIBUTE_RE = re.compile(
    r"\battribute\s+(?P<quote>[\"'])(?P<attribute>[A-Za-z_][A-Za-z0-9_]*)"
    r"(?P=quote)\s+not found in schema\b",
    re.IGNORECASE,
)


class ProviderCallError(RuntimeError):
    """A retrieval failure after a provider query was attempted."""


def namespace_uses_website_defaults(namespace: str) -> bool:
    """Return true when a namespace should use document/page ranking defaults."""

    return namespace.startswith(
        ("site-", "pdf-", "file-", "duckdb-", "bigquery-", "snowflake-")
    )


def ranking_defaults_for_namespace(
    namespace: str,
    *,
    source_kind: str | None = None,
) -> dict[str, object]:
    """Return source-aware defaults, with namespace prefixes as the legacy fallback."""

    if source_kind in {"website", "document", "database"} or (
        source_kind is None and namespace_uses_website_defaults(namespace)
    ):
        return {
            "ranking_mode": DEFAULT_WEBSITE_RANKING_MODE,
            "ranking_profile": DEFAULT_WEBSITE_RANKING_PROFILE,
            "ranking_pool": DEFAULT_WEBSITE_RANKING_POOL,
            "ranking_aggregation": DEFAULT_WEBSITE_RANKING_AGGREGATION,
        }
    return {
        "ranking_mode": DEFAULT_RANKING_MODE,
        "ranking_profile": DEFAULT_RANKING_PROFILE,
        "ranking_pool": DEFAULT_RANKING_POOL,
        "ranking_aggregation": DEFAULT_RANKING_AGGREGATION,
    }


class Embedder(Protocol):
    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""


@dataclass(frozen=True)
class EvidenceRouteContext:
    """Routing facts bound to one automatic evidence assessment."""

    selection_reason: str
    semantic_score: float | None
    semantic_margin: float | None


class EvidenceDecisionLike(Protocol):
    """Structural decision contract supplied by the calibration boundary."""

    @property
    def is_weak(self) -> bool | None:
        """Return whether the observation is weak, or unknown in collect mode."""

    @property
    def status(self) -> str:
        """Return the governed public evidence status."""

    def to_dict(self) -> dict[str, object]:
        """Return content-free public evidence diagnostics."""


class EvidenceAssessor(Protocol):
    """Injected automatic-only evidence scoring and calibration boundary."""

    @property
    def mode(self) -> str:
        """Return collect, shadow, or active."""

    def assess(
        self,
        *,
        query: str,
        hits: Sequence[SearchHit],
        existing_scores: Sequence[float] | None,
        route_context: EvidenceRouteContext,
        namespace_failure_count: int,
        widening_triggered_by_weak_evidence: bool,
    ) -> EvidenceDecisionLike:
        """Assess the exact ordered candidate set without changing its ranking."""


class CalibratedEvidenceAssessor:
    """Score exact automatic hits and apply one validated calibration artifact."""

    def __init__(
        self,
        calibration: EvidenceCalibration,
        *,
        reranker_loader: Callable[[], CrossEncoderReranker] | None = None,
    ) -> None:
        if calibration.mode not in {"collect", "active"} or (
            calibration.mode == "active"
            and calibration != OWNER_AUTHORIZED_ACTIVE_CALIBRATION
        ):
            raise EvidenceCalibrationError(NON_COLLECT_ACTIVATION_PAUSED_MESSAGE)
        self._calibration = calibration
        self._reranker_loader = reranker_loader

    @property
    def mode(self) -> str:
        return self._calibration.mode

    def assess(
        self,
        *,
        query: str,
        hits: Sequence[SearchHit],
        existing_scores: Sequence[float] | None,
        route_context: EvidenceRouteContext,
        namespace_failure_count: int,
        widening_triggered_by_weak_evidence: bool,
    ) -> CalibratedEvidenceDecision:
        if existing_scores is None:
            loader = self._reranker_loader or load_cross_encoder_reranker
            reranker = loader()
            scores = reranker.score(
                query,
                [cross_encoder_passage(hit) for hit in hits],
            )
        else:
            scores = list(existing_scores)
        if len(scores) != len(hits):
            raise CrossEncoderRerankerError(
                "pinned evidence scorer returned the wrong number of scores"
            )
        observation = observe_evidence_scores(
            scores,
            route_selection_reason=route_context.selection_reason,
            route_semantic_score=route_context.semantic_score,
            route_semantic_margin=route_context.semantic_margin,
            namespace_failure_count=namespace_failure_count,
        )
        return decide_evidence(
            self._calibration,
            observation,
            widening_triggered_by_weak_evidence=(
                widening_triggered_by_weak_evidence
            ),
        )


@dataclass(frozen=True)
class RetrievalOptions:
    """Validated knobs for hybrid retrieval."""

    top_k: int = DEFAULT_TOP_K
    candidates: int = DEFAULT_CANDIDATES
    doc_kind: str | None = None
    ranking_mode: str = DEFAULT_RANKING_MODE
    ranking_profile: str = DEFAULT_RANKING_PROFILE
    ranking_pool: int = DEFAULT_RANKING_POOL
    ranking_aggregation: str = DEFAULT_RANKING_AGGREGATION

    def __post_init__(self) -> None:
        if self.top_k <= 0:
            raise ValueError("top_k must be greater than zero.")
        if self.candidates <= 0:
            raise ValueError("candidates must be greater than zero.")
        if self.ranking_pool <= 0:
            raise ValueError("ranking_pool must be greater than zero.")
        if self.ranking_mode not in RANKING_MODES:
            raise ValueError(f"ranking_mode must be one of {sorted(RANKING_MODES)}.")
        if self.ranking_profile not in RANKING_PROFILES:
            raise ValueError(f"ranking_profile must be one of {sorted(RANKING_PROFILES)}.")
        if self.ranking_aggregation not in RANKING_AGGREGATIONS:
            raise ValueError(f"ranking_aggregation must be one of {sorted(RANKING_AGGREGATIONS)}.")

    @property
    def effective_ranking_pool(self) -> int:
        return max(self.top_k, self.ranking_pool if self.ranking_mode in {"file", "page"} else self.top_k)


@dataclass
class SearchHit:
    """One retrieved chunk plus citation and score metadata."""

    id: str
    title: str = ""
    url: str = ""
    section_path: str = ""
    content: str = ""
    path: str = ""
    repo_path: str = ""
    tags: list[str] = field(default_factory=list)
    score_info: dict[str, object] = field(default_factory=dict)
    doc_kind: str = ""
    chunk_index: int | None = None
    namespace: str = ""

    def to_dict(self, *, include_content: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "section_path": self.section_path,
            "path": self.path,
            "repo_path": self.repo_path,
            "tags": list(self.tags),
            "score_info": self.score_info,
        }
        if include_content:
            payload["content"] = self.content
        if self.doc_kind:
            payload["doc_kind"] = self.doc_kind
        if self.chunk_index is not None:
            payload["chunk_index"] = self.chunk_index
        if self.namespace:
            payload["namespace"] = self.namespace
        return payload


@dataclass
class RetrievalResult:
    """Structured retrieval response for CLI/library callers."""

    query: str
    hits: list[SearchHit]
    region: str
    namespace: str
    embedding_model: str
    embedding_precision: str
    top_k: int
    candidates: int
    doc_kind: str | None
    fusion: str
    ranking_mode: str
    ranking_profile: str
    ranking_pool: int
    ranking_aggregation: str
    dry_run: bool = False
    turbopuffer_api_calls: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "command": "retrieve",
            "dry_run": self.dry_run,
            "credentials_required": not self.dry_run,
            "turbopuffer_api_calls": self.turbopuffer_api_calls,
            "api_calls_occurred": self.turbopuffer_api_calls,
            "content_retrieval_occurred": not self.dry_run,
            "query": self.query,
            "region": self.region,
            "namespace": self.namespace,
            "embedding_model": self.embedding_model,
            "embedding_precision": self.embedding_precision,
            "top_k": self.top_k,
            "candidates": self.candidates,
            "doc_kind": self.doc_kind,
            "ranking_mode": self.ranking_mode,
            "ranking_profile": self.ranking_profile,
            "ranking_pool": self.ranking_pool,
            "ranking_aggregation": self.ranking_aggregation,
            "fusion": self.fusion,
            "hits": [hit.to_dict() for hit in self.hits],
        }


@dataclass(frozen=True)
class NamespaceRetrievalFailure:
    """Redacted failure for one attempted content namespace."""

    namespace: str
    route_rank: int
    message: str = "Content retrieval failed for this namespace."

    def to_dict(self) -> dict[str, object]:
        return {
            "namespace": self.namespace,
            "route_rank": self.route_rank,
            "status": "failed",
            "error": "namespace_retrieval_failed",
            "message": self.message,
        }


@dataclass(frozen=True)
class RetrievalFallback:
    """One bounded widening decision made after an initial one-namespace route."""

    widened: bool = False
    reason: Literal["empty_top1", "failed_top1", "weak_top1"] | None = None
    initial_namespaces: tuple[str, ...] = ()
    added_namespaces: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "widened": self.widened,
            "reason": self.reason,
            "initial_namespaces": list(self.initial_namespaces),
            "added_namespaces": list(self.added_namespaces),
        }


@dataclass(frozen=True)
class CrossNamespaceReranking:
    """Public accounting for the bounded local global-ranking step."""

    applied: bool
    candidates_before_dedupe: int
    candidates_after_dedupe: int
    model: str = CROSS_ENCODER_MODEL
    revision: str = CROSS_ENCODER_REVISION
    method: str | None = None
    rrf_k: int | None = None
    components: tuple[str, ...] = ()
    tie_breakers: tuple[str, ...] = ()
    namespace_coverage_possible: bool | None = None
    namespace_coverage_required: tuple[str, ...] = ()
    namespace_coverage_promoted: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "applied": self.applied,
            "model": self.model,
            "revision": self.revision,
            "candidates_before_dedupe": self.candidates_before_dedupe,
            "candidates_after_dedupe": self.candidates_after_dedupe,
            "method": self.method,
            "rrf_k": self.rrf_k,
            "components": list(self.components),
            "tie_breakers": list(self.tie_breakers),
            "namespace_coverage": {
                "enabled": self.applied,
                "possible": self.namespace_coverage_possible,
                "applied": bool(self.namespace_coverage_promoted),
                "required_namespaces": list(self.namespace_coverage_required),
                "promoted_namespaces": list(self.namespace_coverage_promoted),
            },
        }


@dataclass(frozen=True)
class MultiNamespaceRetrievalResult:
    """Structured retrieval result across a bounded ordered namespace route."""

    query: str
    hits: list[SearchHit]
    region: str
    namespaces: list[str]
    embedding_model: str
    embedding_precision: str
    top_k: int
    candidates: int
    namespace_results: list[RetrievalResult]
    namespace_route_ranks: dict[str, int]
    failures: list[NamespaceRetrievalFailure]
    fallback: RetrievalFallback
    reranking: CrossNamespaceReranking
    incomplete: bool
    fusion: str
    evidence: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "command": "retrieve",
            "dry_run": False,
            "credentials_required": True,
            "turbopuffer_api_calls": True,
            "api_calls_occurred": True,
            "content_retrieval_occurred": True,
            "query": self.query,
            "region": self.region,
            "namespaces": list(self.namespaces),
            "embedding_model": self.embedding_model,
            "embedding_precision": self.embedding_precision,
            "top_k": self.top_k,
            "candidates": self.candidates,
            "fusion": self.fusion,
            "routing": {
                "active": False,
                "mode": "explicit",
                "selected_namespaces": list(self.namespaces),
                "initial_fanout": len(self.fallback.initial_namespaces),
                "max_fanout": len(self.namespaces),
            },
            "incomplete": self.incomplete,
            "fallback": self.fallback.to_dict(),
            "reranking": self.reranking.to_dict(),
            "namespace_results": [
                {
                    "namespace": result.namespace,
                    "route_rank": self.namespace_route_ranks[result.namespace],
                    "status": "ok",
                    "fusion": result.fusion,
                    "ranking_mode": result.ranking_mode,
                    "ranking_profile": result.ranking_profile,
                    "ranking_pool": result.ranking_pool,
                    "ranking_aggregation": result.ranking_aggregation,
                    "hit_count": len(result.hits),
                }
                for result in self.namespace_results
            ],
            "namespace_failures": [failure.to_dict() for failure in self.failures],
            "hits": [hit.to_dict() for hit in self.hits],
        }
        if self.evidence is not None:
            payload["evidence"] = dict(self.evidence)
        return payload


@dataclass(frozen=True)
class RetrievalPlan:
    """Safe no-credential plan for one retrieve target."""

    query: str
    config: RuntimeConfig
    options: RetrievalOptions

    def to_dict(self) -> dict[str, object]:
        ann_subquery: dict[str, object] = {
            "name": "ann",
            "rank_by": ["vector", "ANN", "<query embedding>"],
            "limit": self.options.candidates,
            "include_attributes": RETRIEVAL_ATTRIBUTES,
        }
        bm25_subquery: dict[str, object] = {
            "name": "bm25",
            "rank_by": bm25_rank_by(self.query),
            "limit": self.options.candidates,
            "include_attributes": RETRIEVAL_ATTRIBUTES,
        }
        if self.options.doc_kind:
            doc_filter = ("doc_kind", "Eq", self.options.doc_kind)
            ann_subquery["filters"] = doc_filter
            bm25_subquery["filters"] = doc_filter
        return {
            "command": "retrieve",
            "dry_run": True,
            "plan": True,
            "credentials_required": False,
            "turbopuffer_api_calls": False,
            "api_calls_occurred": False,
            "query": self.query,
            "region": self.config.region,
            "content_retrieval_occurred": False,
            "namespace": self.config.namespace,
            "embedding_model": self.config.embedding_model,
            "embedding_precision": self.config.embedding_precision,
            "top_k": self.options.top_k,
            "candidates": self.options.candidates,
            "doc_kind": self.options.doc_kind,
            "ranking_mode": self.options.ranking_mode,
            "ranking_profile": self.options.ranking_profile,
            "ranking_pool": self.options.ranking_pool,
            "ranking_aggregation": self.options.ranking_aggregation,
            "live_execution": "omit --dry-run/--plan to embed the query and call turbopuffer",
            "retrieval": {
                "request": "turbopuffer multi_query",
                "subqueries": [ann_subquery, bm25_subquery],
                "rerank_by": ["RRF"],
                "fallback": "client-side reciprocal-rank fusion if server RRF is unsupported or separate lists are returned",
            },
        }


@dataclass(frozen=True)
class MultiNamespaceRetrievalPlan:
    """Safe no-content-query plan for a bounded explicit namespace set."""

    query: str
    plans: list[RetrievalPlan]
    initial_fanout: int | None = None

    def to_dict(self) -> dict[str, object]:
        first = self.plans[0]
        initial_fanout = self.initial_fanout or len(self.plans)
        return {
            "command": "retrieve",
            "dry_run": True,
            "plan": True,
            "credentials_required": False,
            "turbopuffer_api_calls": False,
            "api_calls_occurred": False,
            "query": self.query,
            "region": first.config.region,
            "content_retrieval_occurred": False,
            "namespaces": [plan.config.namespace for plan in self.plans],
            "embedding_model": first.config.embedding_model,
            "embedding_precision": first.config.embedding_precision,
            "top_k": first.options.top_k,
            "candidates": first.options.candidates,
            "fusion": CROSS_NAMESPACE_FUSION,
            "initial_fanout": initial_fanout,
            "max_fanout": len(self.plans),
            "routing": {
                "active": False,
                "mode": "explicit",
                "selected_namespaces": [
                    plan.config.namespace for plan in self.plans
                ],
                "initial_fanout": initial_fanout,
                "max_fanout": len(self.plans),
            },
            "reranking": {
                "conditional": True,
                "model": CROSS_ENCODER_MODEL,
                "revision": CROSS_ENCODER_REVISION,
                "method": CROSS_NAMESPACE_FUSION_METHOD,
                "rrf_k": CROSS_NAMESPACE_RRF_K,
                "components": list(CROSS_NAMESPACE_FUSION_COMPONENTS),
                "tie_breakers": list(CROSS_NAMESPACE_FUSION_TIE_BREAKERS),
                "max_candidates_per_namespace": MAX_RERANK_CANDIDATES_PER_NAMESPACE,
                "max_candidates": len(self.plans)
                * MAX_RERANK_CANDIDATES_PER_NAMESPACE,
            },
            "namespace_plans": [
                {
                    "namespace": plan.config.namespace,
                    "route_rank": route_rank,
                    "ranking_mode": plan.options.ranking_mode,
                    "ranking_profile": plan.options.ranking_profile,
                    "ranking_pool": plan.options.ranking_pool,
                    "ranking_aggregation": plan.options.ranking_aggregation,
                    "retrieval": plan.to_dict()["retrieval"],
                }
                for route_rank, plan in enumerate(self.plans, start=1)
            ],
            "live_execution": (
                "omit --dry-run/--plan to embed once and query at most three selected namespaces"
            ),
        }


class HybridRetriever:
    """Small wrapper around query embedding and turbopuffer multi-query."""

    def __init__(
        self,
        *,
        namespace: object,
        embedder: Embedder,
        config: RuntimeConfig,
    ) -> None:
        self._namespace = namespace
        self._embedder = embedder
        self._config = config

    @classmethod
    def from_config(cls, config: RuntimeConfig) -> "HybridRetriever":
        """Build a live retriever, reading the API key from the environment only."""

        api_key = os.environ.get("TURBOPUFFER_API_KEY")
        if not api_key:
            raise RuntimeError(
                "TURBOPUFFER_API_KEY must be set in the environment for live retrieval. "
                "Use `retrieve --dry-run` or `retrieve --plan` to inspect the plan without credentials."
            )
        embedder = SentenceTransformerEmbedder(
            config.embedding_model, precision=config.embedding_precision
        )
        try:
            namespace = build_namespace(config=config, api_key=api_key)
        except Exception:
            raise RuntimeError(
                f"Could not prepare namespace {config.namespace!r}."
            ) from None
        return cls(namespace=namespace, embedder=embedder, config=config)

    def retrieve(self, query: str, options: RetrievalOptions) -> RetrievalResult:
        cleaned_query = query.strip()
        if not cleaned_query:
            raise RuntimeError("A non-empty query is required for retrieval.")
        with retrieval_trace(
            mode="explicit_single",
            embedding_model=self._config.embedding_model,
            embedding_precision=self._config.embedding_precision,
            top_k=options.top_k,
            candidates=options.candidates,
            namespace_count=1,
            initial_fanout=1,
        ) as trace_span:
            with telemetry_span(QUERY_EMBED_SPAN_NAME) as embed_span:
                vectors = self._embedder.encode([cleaned_query])
                if not vectors or not vectors[0]:
                    raise RuntimeError(
                        "The embedding model returned no vector for the query."
                    )
                embed_span.mark_ok()
            trace_span.set_attribute("buoy.retrieval.final_fanout", 1)
            with telemetry_span(
                NAMESPACE_QUERY_SPAN_NAME,
                {"buoy.route.rank": 1},
            ) as namespace_span:
                try:
                    result = self.retrieve_embedded(
                        cleaned_query,
                        vectors[0],
                        options,
                    )
                except BaseException:
                    namespace_span.set_attribute("buoy.namespace.status", "failed")
                    trace_span.set_attributes(
                        {
                            "buoy.retrieval.failure_count": 1,
                            "buoy.retrieval.incomplete": True,
                        }
                    )
                    raise
                namespace_span.set_attributes(
                    {
                        "buoy.namespace.status": "ok",
                        "buoy.namespace.hit_count": len(result.hits),
                    }
                )
                namespace_span.mark_ok()
            trace_span.set_attributes(
                {
                    "buoy.retrieval.outcome": "success",
                    "buoy.retrieval.hit_count": len(result.hits),
                    "buoy.retrieval.final_fanout": 1,
                }
            )
            trace_span.mark_ok()
            return result

    def retrieve_embedded(
        self,
        query: str,
        query_vector: Sequence[float],
        options: RetrievalOptions,
    ) -> RetrievalResult:
        """Query one namespace with an already-computed query vector."""

        include_attributes = list(RETRIEVAL_ATTRIBUTES)
        while True:
            subqueries = build_multi_query_subqueries(
                query=query,
                query_vector=query_vector,
                candidates=options.candidates,
                doc_kind=options.doc_kind,
                include_attributes=include_attributes,
            )
            try:
                response, fusion = run_multi_query(self._namespace, subqueries)
                break
            except Exception as exc:  # pragma: no cover - SDK/network/schema failure paths are integration-tested.
                missing_attribute = missing_schema_attribute(exc)
                if (
                    missing_attribute not in OPTIONAL_RETRIEVAL_ATTRIBUTES
                    or missing_attribute not in include_attributes
                ):
                    raise ProviderCallError(user_friendly_query_error(exc)) from None
                include_attributes = [
                    attribute
                    for attribute in include_attributes
                    if attribute != missing_attribute
                ]

        try:
            result_lists = extract_result_lists(response)
            if not result_lists:
                hits: list[SearchHit] = []
            else:
                ranking_pool = options.effective_ranking_pool
                if fusion == "client_rrf" or len(result_lists) > 1:
                    hits = client_side_rrf(result_lists, top_k=ranking_pool)
                    fusion = "client_rrf"
                else:
                    hits = [
                        row_to_hit(row, score_info={"fusion": "server_rrf", "source_rank": rank})
                        for rank, row in enumerate(result_lists[0], start=1)
                    ][:ranking_pool]
                hits = rank_hits(hits, options=options, query=query)[: options.top_k]
        except Exception as exc:
            raise ProviderCallError(user_friendly_query_error(exc)) from None
        return RetrievalResult(
            query=query,
            hits=hits,
            region=self._config.region,
            namespace=self._config.namespace,
            embedding_model=self._config.embedding_model,
            embedding_precision=self._config.embedding_precision,
            top_k=options.top_k,
            candidates=options.candidates,
            doc_kind=options.doc_kind,
            fusion=fusion,
            ranking_mode=options.ranking_mode,
            ranking_profile=options.ranking_profile,
            ranking_pool=options.ranking_pool,
            ranking_aggregation=options.ranking_aggregation,
        )


@dataclass(frozen=True)
class _NamespaceRetrievalTarget:
    route_rank: int
    retriever: HybridRetriever
    options: RetrievalOptions

    @property
    def namespace(self) -> str:
        return self.retriever._config.namespace


@dataclass(frozen=True)
class _NamespaceRetrievalOutcome:
    target: _NamespaceRetrievalTarget
    result: RetrievalResult | None = None
    failure: NamespaceRetrievalFailure | None = None


@dataclass(frozen=True)
class _RerankCandidate:
    hit: SearchHit
    route_rank: int
    namespace_rank: int
    duplicate_namespaces: tuple[str, ...]


@dataclass(frozen=True)
class _FusedRerankCandidate:
    candidate: _RerankCandidate
    cross_encoder_score: float
    cross_encoder_rank: int
    cross_encoder_rrf_score: float
    namespace_rrf_score: float
    fusion_score: float
    namespace_coverage_promoted: bool = False


class MultiNamespaceRetriever:
    """Embed once and query/rerank a bounded ordered namespace route."""

    def __init__(
        self,
        *,
        retrievers: list[HybridRetriever],
        embedder: Embedder,
        reranker_loader: Callable[[], CrossEncoderReranker] | None = None,
    ) -> None:
        if not retrievers:
            raise ValueError("at least one namespace retriever is required")
        if len(retrievers) > MAX_NAMESPACE_FANOUT:
            raise ValueError(
                f"at most {MAX_NAMESPACE_FANOUT} namespace retrievers are allowed"
            )
        namespaces = [retriever._config.namespace for retriever in retrievers]
        if len(namespaces) != len(set(namespaces)):
            raise ValueError("namespace retrievers must be unique")
        first = retrievers[0]._config
        contract = (first.region, first.embedding_model, first.embedding_precision)
        if any(
            (
                retriever._config.region,
                retriever._config.embedding_model,
                retriever._config.embedding_precision,
            )
            != contract
            for retriever in retrievers[1:]
        ):
            raise ValueError(
                "all selected namespaces must use one region, embedding model, and precision"
            )
        self._retrievers = list(retrievers)
        self._embedder = embedder
        self._reranker_loader = reranker_loader

    @classmethod
    def from_configs(cls, configs: Sequence[RuntimeConfig]) -> "MultiNamespaceRetriever":
        if not configs:
            raise ValueError("at least one namespace config is required")
        if len(configs) > MAX_NAMESPACE_FANOUT:
            raise ValueError(f"at most {MAX_NAMESPACE_FANOUT} namespace configs are allowed")
        first = configs[0]
        contract = (first.region, first.embedding_model, first.embedding_precision)
        if any(
            (config.region, config.embedding_model, config.embedding_precision) != contract
            for config in configs[1:]
        ):
            raise ValueError(
                "all selected namespaces must use one region, embedding model, and precision"
            )
        namespaces = [config.namespace for config in configs]
        if len(namespaces) != len(set(namespaces)):
            raise ValueError("namespace configs must be unique")
        api_key = os.environ.get("TURBOPUFFER_API_KEY")
        if not api_key:
            raise RuntimeError(
                "TURBOPUFFER_API_KEY must be set in the environment for live retrieval. "
                "Use `retrieve --dry-run` or `retrieve --plan` to inspect the plan without credentials."
            )
        embedder = SentenceTransformerEmbedder(
            first.embedding_model, precision=first.embedding_precision
        )
        retrievers: list[HybridRetriever] = []
        for config in configs:
            try:
                namespace = build_namespace(config=config, api_key=api_key)
            except Exception:
                raise RuntimeError(
                    f"Could not prepare namespace {config.namespace!r}."
                ) from None
            retrievers.append(
                HybridRetriever(namespace=namespace, embedder=embedder, config=config)
            )
        return cls(retrievers=retrievers, embedder=embedder)

    def retrieve(
        self,
        query: str,
        options: Sequence[RetrievalOptions],
        *,
        initial_fanout: int | None = None,
        evidence_assessor: EvidenceAssessor | None = None,
        evidence_route_context: EvidenceRouteContext | None = None,
    ) -> MultiNamespaceRetrievalResult:
        if (evidence_assessor is None) != (evidence_route_context is None):
            raise ValueError(
                "evidence_assessor and evidence_route_context must be supplied together"
            )
        evidence_mode = (
            _validated_evidence_mode(evidence_assessor.mode)
            if evidence_assessor is not None
            else None
        )
        if len(options) != len(self._retrievers):
            raise ValueError("one retrieval option set is required per namespace")
        first_options = options[0]
        global_contract = (
            first_options.top_k,
            first_options.candidates,
            first_options.doc_kind,
        )
        if any(
            (item.top_k, item.candidates, item.doc_kind) != global_contract
            for item in options[1:]
        ):
            raise ValueError(
                "all selected namespaces must use one top_k, candidates, and doc_kind contract"
            )
        requested_fanout = len(self._retrievers) if initial_fanout is None else initial_fanout
        if type(requested_fanout) is not int or not 1 <= requested_fanout <= len(
            self._retrievers
        ):
            raise ValueError(
                "initial_fanout must be between one and the selected namespace count"
            )

        cleaned_query = query.strip()
        if not cleaned_query:
            raise RuntimeError("A non-empty query is required for retrieval.")
        first_config = self._retrievers[0]._config
        with retrieval_trace(
            mode=("automatic" if evidence_assessor is not None else "explicit_multi"),
            embedding_model=first_config.embedding_model,
            embedding_precision=first_config.embedding_precision,
            top_k=first_options.top_k,
            candidates=first_options.candidates,
            namespace_count=len(self._retrievers),
            initial_fanout=requested_fanout,
            routing_selection_reason=(
                evidence_route_context.selection_reason
                if evidence_route_context is not None
                else None
            ),
            routing_semantic_score=(
                evidence_route_context.semantic_score
                if evidence_route_context is not None
                else None
            ),
            routing_semantic_margin=(
                evidence_route_context.semantic_margin
                if evidence_route_context is not None
                else None
            ),
        ) as trace_span:
            return self._retrieve_traced(
                cleaned_query,
                options,
                first_options=first_options,
                requested_fanout=requested_fanout,
                evidence_assessor=evidence_assessor,
                evidence_route_context=evidence_route_context,
                evidence_mode=evidence_mode,
                trace_span=trace_span,
            )

    def _retrieve_traced(
        self,
        cleaned_query: str,
        options: Sequence[RetrievalOptions],
        *,
        first_options: RetrievalOptions,
        requested_fanout: int,
        evidence_assessor: EvidenceAssessor | None,
        evidence_route_context: EvidenceRouteContext | None,
        evidence_mode: Literal["collect", "shadow", "active"] | None,
        trace_span: TelemetrySpan,
    ) -> MultiNamespaceRetrievalResult:
        with telemetry_span(QUERY_EMBED_SPAN_NAME) as embed_span:
            vectors = self._embedder.encode([cleaned_query])
            if not vectors or not vectors[0]:
                raise RuntimeError("The embedding model returned no vector for the query.")
            embed_span.mark_ok()

        targets = [
            _NamespaceRetrievalTarget(
                route_rank=route_rank,
                retriever=retriever,
                options=namespace_options,
            )
            for route_rank, (retriever, namespace_options) in enumerate(
                zip(self._retrievers, options, strict=True), start=1
            )
        ]
        reranker: CrossEncoderReranker | None = None
        if requested_fanout > 1:
            reranker = self._load_reranker()
        initial_targets = targets[:requested_fanout]
        trace_span.set_attribute(
            "buoy.retrieval.final_fanout",
            len(initial_targets),
        )
        outcomes = self._retrieve_batch(
            initial_targets,
            query=cleaned_query,
            query_vector=vectors[0],
            multi_namespace=requested_fanout > 1,
            single_namespace_top_k=first_options.top_k,
        )
        fallback = RetrievalFallback(
            initial_namespaces=tuple(target.namespace for target in initial_targets)
        )
        evidence_payload: dict[str, object] | None = None
        weak_evidence_widening_triggered = False

        if requested_fanout == 1 and len(targets) > 1:
            first_outcome = outcomes[0]
            should_widen = first_outcome.failure is not None or not (
                first_outcome.result and first_outcome.result.hits
            )
            fallback_reason: Literal[
                "empty_top1", "failed_top1", "weak_top1"
            ] = (
                "failed_top1"
                if first_outcome.failure is not None
                else "empty_top1"
            )
            if not should_widen and evidence_assessor is not None:
                initial_hits, _initial_reranking = cross_namespace_rerank(
                    cleaned_query,
                    [first_outcome],
                    top_k=min(EVIDENCE_ASSESSMENT_TOP_K, first_options.top_k),
                    reranker=None,
                )
                with telemetry_span(EVIDENCE_SPAN_NAME) as evidence_span:
                    initial_decision, evidence_payload = (
                        _assess_retrieval_evidence(
                            evidence_assessor,
                            query=cleaned_query,
                            hits=initial_hits[:EVIDENCE_ASSESSMENT_TOP_K],
                            route_context=evidence_route_context,
                            namespace_failure_count=0,
                            weak_evidence_widening_triggered=False,
                        )
                    )
                    _record_evidence_telemetry(evidence_span, evidence_payload)
                if initial_decision is not None and initial_decision.is_weak is True:
                    should_widen = True
                    fallback_reason = "weak_top1"
                    weak_evidence_widening_triggered = True
                    evidence_payload = None
            if should_widen:
                reranker = self._load_reranker()
                added_targets = targets[1:MAX_NAMESPACE_FANOUT]
                fallback = RetrievalFallback(
                    widened=True,
                    reason=fallback_reason,
                    initial_namespaces=(first_outcome.target.namespace,),
                    added_namespaces=tuple(target.namespace for target in added_targets),
                )
                trace_span.set_attribute(
                    "buoy.retrieval.final_fanout",
                    len(outcomes) + len(added_targets),
                )
                outcomes.extend(
                    self._retrieve_batch(
                        added_targets,
                        query=cleaned_query,
                        query_vector=vectors[0],
                        multi_namespace=True,
                        single_namespace_top_k=first_options.top_k,
                    )
                )
                trace_span.add_event(
                    "retrieval.widened",
                    {
                        "buoy.retrieval.initial_fanout": requested_fanout,
                        "buoy.retrieval.final_fanout": len(outcomes),
                        "buoy.retrieval.fallback_reason": fallback_reason,
                    },
                )

        outcomes.sort(key=lambda outcome: outcome.target.route_rank)
        successful = [outcome for outcome in outcomes if outcome.result is not None]
        failures = [
            outcome.failure for outcome in outcomes if outcome.failure is not None
        ]
        trace_span.set_attributes(
            {
                "buoy.retrieval.final_fanout": len(outcomes),
                "buoy.retrieval.failure_count": len(failures),
                "buoy.retrieval.incomplete": bool(failures),
                "buoy.retrieval.widened": fallback.widened,
                "buoy.retrieval.fallback_reason": fallback.reason,
            }
        )
        if not successful:
            attempted = ", ".join(repr(outcome.target.namespace) for outcome in outcomes)
            raise ProviderCallError(
                f"Retrieval failed for every attempted namespace: {attempted}."
            )

        with telemetry_span(RERANK_SPAN_NAME) as rerank_span:
            hits, reranking = cross_namespace_rerank(
                cleaned_query,
                successful,
                top_k=first_options.top_k,
                reranker=reranker,
            )
            rerank_span.set_attributes(
                {
                    "buoy.rerank.applied": reranking.applied,
                    "buoy.rerank.candidates_before_dedupe": (
                        reranking.candidates_before_dedupe
                    ),
                    "buoy.rerank.candidates_after_dedupe": (
                        reranking.candidates_after_dedupe
                    ),
                    "buoy.reranker.model": (
                        reranking.model if reranking.applied else None
                    ),
                    "buoy.reranker.revision": (
                        reranking.revision if reranking.applied else None
                    ),
                }
            )
            rerank_span.mark_ok()
        if evidence_assessor is not None:
            assessment_hits = hits[:EVIDENCE_ASSESSMENT_TOP_K]
            if evidence_payload is None:
                with telemetry_span(EVIDENCE_SPAN_NAME) as evidence_span:
                    decision, evidence_payload = _assess_retrieval_evidence(
                        evidence_assessor,
                        query=cleaned_query,
                        hits=assessment_hits,
                        route_context=evidence_route_context,
                        namespace_failure_count=len(failures),
                        weak_evidence_widening_triggered=(
                            weak_evidence_widening_triggered
                        ),
                    )
                    _record_evidence_telemetry(evidence_span, evidence_payload)
                if (
                    decision is not None
                    and evidence_mode == "active"
                    and decision.status in {"no_relevant_evidence", "inconclusive"}
                ):
                    hits = []
            if evidence_payload is not None:
                _record_evidence_telemetry(trace_span, evidence_payload)
        first_config = self._retrievers[0]._config
        namespace_results = [
            outcome.result for outcome in successful if outcome.result is not None
        ]
        result = MultiNamespaceRetrievalResult(
            query=cleaned_query,
            hits=hits,
            region=first_config.region,
            namespaces=[outcome.target.namespace for outcome in outcomes],
            embedding_model=first_config.embedding_model,
            embedding_precision=first_config.embedding_precision,
            top_k=first_options.top_k,
            candidates=first_options.candidates,
            namespace_results=namespace_results,
            namespace_route_ranks={
                outcome.target.namespace: outcome.target.route_rank
                for outcome in successful
            },
            failures=[failure for failure in failures if failure is not None],
            fallback=fallback,
            reranking=reranking,
            incomplete=bool(failures),
            fusion=(
                CROSS_NAMESPACE_FUSION
                if reranking.applied
                else "single_namespace"
            ),
            evidence=evidence_payload,
        )
        trace_span.set_attributes(
            {
                "buoy.retrieval.outcome": (
                    "partial" if failures else "success"
                ),
                "buoy.retrieval.hit_count": len(result.hits),
            }
        )
        trace_span.mark_ok()
        return result

    def _load_reranker(self) -> CrossEncoderReranker:
        loader = self._reranker_loader or load_cross_encoder_reranker
        return loader()

    @staticmethod
    def _retrieve_batch(
        targets: Sequence[_NamespaceRetrievalTarget],
        *,
        query: str,
        query_vector: Sequence[float],
        multi_namespace: bool,
        single_namespace_top_k: int | None = None,
    ) -> list[_NamespaceRetrievalOutcome]:
        if not targets:
            return []
        if len(targets) > MAX_NAMESPACE_FANOUT:
            raise ValueError(f"at most {MAX_NAMESPACE_FANOUT} namespaces may be queried")

        futures: dict[Future[RetrievalResult], _NamespaceRetrievalTarget] = {}
        with ThreadPoolExecutor(max_workers=len(targets)) as executor:
            for target in targets:
                target_options = replace(
                    target.options,
                    top_k=(
                        MAX_RERANK_CANDIDATES_PER_NAMESPACE
                        if multi_namespace
                        else single_namespace_top_k or target.options.top_k
                    ),
                )
                future = executor.submit(
                    copied_context_callable(
                        MultiNamespaceRetriever._retrieve_target
                    ),
                    target,
                    query,
                    query_vector,
                    target_options,
                )
                futures[future] = target

            outcomes: list[_NamespaceRetrievalOutcome] = []
            for future, target in futures.items():
                try:
                    result = future.result()
                except (ProviderCallError, RuntimeError):
                    outcomes.append(
                        _NamespaceRetrievalOutcome(
                            target=target,
                            failure=NamespaceRetrievalFailure(
                                namespace=target.namespace,
                                route_rank=target.route_rank,
                            ),
                        )
                    )
                else:
                    outcomes.append(
                        _NamespaceRetrievalOutcome(target=target, result=result)
                    )
        outcomes.sort(key=lambda outcome: outcome.target.route_rank)
        return outcomes

    @staticmethod
    def _retrieve_target(
        target: _NamespaceRetrievalTarget,
        query: str,
        query_vector: Sequence[float],
        options: RetrievalOptions,
    ) -> RetrievalResult:
        with telemetry_span(
            NAMESPACE_QUERY_SPAN_NAME,
            {"buoy.route.rank": target.route_rank},
        ) as namespace_span:
            try:
                result = target.retriever.retrieve_embedded(
                    query,
                    query_vector,
                    options,
                )
            except BaseException:
                namespace_span.set_attribute("buoy.namespace.status", "failed")
                raise
            namespace_span.set_attributes(
                {
                    "buoy.namespace.status": "ok",
                    "buoy.namespace.hit_count": len(result.hits),
                }
            )
            namespace_span.mark_ok()
            return result


def _record_evidence_telemetry(
    span: TelemetrySpan,
    payload: Mapping[str, object],
) -> None:
    """Copy only governed, content-free evidence observations to a span."""

    span.set_attributes(
        {
            "buoy.evidence.mode": payload.get("mode"),
            "buoy.evidence.status": payload.get("status"),
            "buoy.evidence.candidates_scored": payload.get(
                "candidates_scored"
            ),
            "buoy.evidence.top_score": payload.get("top_score"),
            "buoy.evidence.second_score": payload.get("second_score"),
            "buoy.evidence.score_gap": payload.get("score_gap"),
        }
    )


def _validated_evidence_mode(value: object) -> Literal["collect", "shadow", "active"]:
    if not isinstance(value, str) or value not in {"collect", "shadow", "active"}:
        raise ValueError("evidence assessor mode must be collect, shadow, or active")
    return value  # type: ignore[return-value]


def _existing_cross_encoder_scores(
    hits: Sequence[SearchHit],
) -> tuple[float, ...] | None:
    """Reuse scores only when every exact assessed hit carries a finite CE score."""

    scores: list[float] = []
    for hit in hits:
        cross_namespace = hit.score_info.get("cross_namespace")
        if not isinstance(cross_namespace, Mapping):
            return None
        value = cross_namespace.get("cross_encoder_score")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        score = float(value)
        if not math.isfinite(score):
            return None
        scores.append(score)
    return tuple(scores)


def _assess_retrieval_evidence(
    assessor: EvidenceAssessor,
    *,
    query: str,
    hits: Sequence[SearchHit],
    route_context: EvidenceRouteContext | None,
    namespace_failure_count: int,
    weak_evidence_widening_triggered: bool,
) -> tuple[EvidenceDecisionLike | None, dict[str, object]]:
    """Run one automatic assessment with mode-specific fail-closed behavior."""

    if route_context is None:  # Guard the public pair invariant for type checkers.
        raise ValueError("evidence_route_context is required")
    mode = _validated_evidence_mode(assessor.mode)
    assessed_hits = list(hits[:EVIDENCE_ASSESSMENT_TOP_K])
    try:
        decision = assessor.assess(
            query=query,
            hits=assessed_hits,
            existing_scores=_existing_cross_encoder_scores(assessed_hits),
            route_context=route_context,
            namespace_failure_count=namespace_failure_count,
            widening_triggered_by_weak_evidence=(
                weak_evidence_widening_triggered
            ),
        )
        status = decision.status
        weak = decision.is_weak
        allowed_statuses = {
            "collect": {"unassessed": None},
            "shadow": {
                "would_support": False,
                "would_abstain": True,
                "would_be_inconclusive": True,
            },
            "active": {
                "supported": False,
                "no_relevant_evidence": True,
                "inconclusive": True,
            },
        }
        if status not in allowed_statuses[mode] or weak is not allowed_statuses[mode][status]:
            raise ValueError("evidence decision is incompatible with assessor mode")
        raw_payload = decision.to_dict()
        if not isinstance(raw_payload, dict):
            raise ValueError("evidence decision diagnostics must be an object")
    except Exception:
        if mode == "active":
            raise RuntimeError("Automatic evidence assessment failed.") from None
        return None, {
            "mode": mode,
            "status": "assessment_failed",
            "reason": "evidence_assessment_failed",
            "widening_triggered_by_weak_evidence": (
                weak_evidence_widening_triggered
            ),
        }

    if isinstance(decision, CalibratedEvidenceDecision):
        payload = {
            key: value
            for key, value in raw_payload.items()
            if key in EVIDENCE_PUBLIC_DIAGNOSTIC_FIELDS
        }
    else:
        # Injected assessors control routing decisions for library callers, but
        # their free-form values never cross Buoy's public diagnostic boundary.
        payload = {"reason": "custom_evidence_assessor"}
    payload["mode"] = mode
    payload["status"] = status
    payload["widening_triggered_by_weak_evidence"] = (
        weak_evidence_widening_triggered
    )
    return decision, payload


def cross_namespace_rerank(
    query: str,
    outcomes: Sequence[_NamespaceRetrievalOutcome],
    *,
    top_k: int,
    reranker: CrossEncoderReranker | None,
) -> tuple[list[SearchHit], CrossNamespaceReranking]:
    """Fuse cross-encoder and local ordinal ranks without raw provider scores."""

    ordered_outcomes = sorted(outcomes, key=lambda outcome: outcome.target.route_rank)
    candidates: list[_RerankCandidate] = []
    nonempty_namespaces: list[str] = []
    candidate_limit = (
        MAX_RERANK_CANDIDATES_PER_NAMESPACE
        if len(ordered_outcomes) > 1
        else top_k
    )
    for outcome in ordered_outcomes:
        if outcome.result is None or not outcome.result.hits:
            continue
        namespace = outcome.target.namespace
        nonempty_namespaces.append(namespace)
        for namespace_rank, hit in enumerate(
            outcome.result.hits[:candidate_limit], start=1
        ):
            candidates.append(
                _RerankCandidate(
                    hit=replace(hit, namespace=namespace),
                    route_rank=outcome.target.route_rank,
                    namespace_rank=namespace_rank,
                    duplicate_namespaces=(namespace,),
                )
            )

    before_dedupe = len(candidates)
    if len(nonempty_namespaces) <= 1:
        hits = [
            _annotate_cross_namespace_candidate(candidate)
            for candidate in candidates[:top_k]
        ]
        return hits, CrossNamespaceReranking(
            applied=False,
            candidates_before_dedupe=before_dedupe,
            candidates_after_dedupe=before_dedupe,
        )

    if reranker is None:
        raise CrossEncoderRerankerError(
            "the pinned cross-namespace reranker was not loaded before content retrieval"
        )
    deduplicated = deduplicate_rerank_candidates(candidates)
    passages = [cross_encoder_passage(candidate.hit) for candidate in deduplicated]
    try:
        scores = reranker.score(query, passages)
    except CrossEncoderRerankerError:
        raise
    except Exception as exc:
        raise CrossEncoderRerankerError(
            "pinned cross-namespace reranker inference failed"
        ) from exc
    if len(scores) != len(deduplicated):
        raise CrossEncoderRerankerError(
            "pinned cross-namespace reranker returned the wrong number of scores"
        )

    scored: list[tuple[float, _RerankCandidate]] = []
    for candidate, value in zip(deduplicated, scores, strict=True):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise CrossEncoderRerankerError(
                "pinned cross-namespace reranker returned a non-numeric score"
            )
        score = float(value)
        if not math.isfinite(score):
            raise CrossEncoderRerankerError(
                "pinned cross-namespace reranker returned a non-finite score"
            )
        scored.append((score, candidate))
    scored.sort(
        key=lambda item: (
            -item[0],
            item[1].route_rank,
            item[1].namespace_rank,
            item[1].hit.namespace,
            item[1].hit.id,
        )
    )
    fused: list[_FusedRerankCandidate] = []
    for cross_encoder_rank, (cross_encoder_score, candidate) in enumerate(
        scored, start=1
    ):
        cross_encoder_rrf_score = 1.0 / (
            CROSS_NAMESPACE_RRF_K + cross_encoder_rank
        )
        namespace_rrf_score = 1.0 / (
            CROSS_NAMESPACE_RRF_K + candidate.namespace_rank
        )
        fused.append(
            _FusedRerankCandidate(
                candidate=candidate,
                cross_encoder_score=cross_encoder_score,
                cross_encoder_rank=cross_encoder_rank,
                cross_encoder_rrf_score=cross_encoder_rrf_score,
                namespace_rrf_score=namespace_rrf_score,
                fusion_score=cross_encoder_rrf_score + namespace_rrf_score,
            )
        )
    fused.sort(
        key=lambda item: (
            -item.fusion_score,
            item.cross_encoder_rank,
            item.candidate.route_rank,
            item.candidate.namespace_rank,
            item.candidate.hit.namespace,
            item.candidate.hit.id,
        )
    )
    selected, coverage_possible, promoted_namespaces = _namespace_covered_top_k(
        fused,
        top_k=top_k,
        required_namespaces=nonempty_namespaces,
    )
    hits = [
        _annotate_cross_namespace_candidate(item.candidate, fused=item)
        for item in selected
    ]
    return hits, CrossNamespaceReranking(
        applied=True,
        candidates_before_dedupe=before_dedupe,
        candidates_after_dedupe=len(deduplicated),
        method=CROSS_NAMESPACE_FUSION_METHOD,
        rrf_k=CROSS_NAMESPACE_RRF_K,
        components=CROSS_NAMESPACE_FUSION_COMPONENTS,
        tie_breakers=CROSS_NAMESPACE_FUSION_TIE_BREAKERS,
        namespace_coverage_possible=coverage_possible,
        namespace_coverage_required=tuple(nonempty_namespaces),
        namespace_coverage_promoted=promoted_namespaces,
    )


def _namespace_covered_top_k(
    fused: Sequence[_FusedRerankCandidate],
    *,
    top_k: int,
    required_namespaces: Sequence[str],
) -> tuple[list[_FusedRerankCandidate], bool, tuple[str, ...]]:
    """Preserve fused order while giving each nonempty namespace one slot."""

    baseline_indexes = set(range(min(top_k, len(fused))))
    selected_indexes = set(baseline_indexes)
    if top_k < len(required_namespaces):
        return [fused[index] for index in sorted(selected_indexes)], False, ()

    def memberships(index: int) -> tuple[str, ...]:
        return fused[index].candidate.duplicate_namespaces

    promoted_indexes: set[int] = set()
    promoted_namespaces: list[str] = []
    for namespace in required_namespaces:
        if any(namespace in memberships(index) for index in selected_indexes):
            continue
        # Coverage preserves the namespace retriever's strongest evidence,
        # not whichever candidate the cross-encoder happened to prefer inside
        # that corpus. This is the safety rail that keeps a locally ranked #1
        # from disappearing when another corpus dominates the shared scores.
        promotion_index = next(
            (
                index
                for index in range(len(fused))
                if fused[index].candidate.hit.namespace == namespace
                and fused[index].candidate.namespace_rank == 1
            ),
            next(
                (
                    index
                    for index in range(len(fused))
                    if namespace in memberships(index)
                ),
                None,
            ),
        )
        membership_counts: dict[str, int] = {}
        for index in selected_indexes:
            for represented_namespace in memberships(index):
                membership_counts[represented_namespace] = (
                    membership_counts.get(represented_namespace, 0) + 1
                )
        donor_index = next(
            (
                index
                for index in sorted(selected_indexes, reverse=True)
                if all(
                    membership_counts[represented_namespace] > 1
                    for represented_namespace in memberships(index)
                )
            ),
            None,
        )
        if promotion_index is None or donor_index is None:
            return [fused[index] for index in sorted(baseline_indexes)], False, ()
        selected_indexes.remove(donor_index)
        selected_indexes.add(promotion_index)
        promoted_indexes.add(promotion_index)
        promoted_namespaces.append(namespace)

    covered_namespaces = {
        namespace
        for index in selected_indexes
        for namespace in memberships(index)
    }
    if not set(required_namespaces).issubset(covered_namespaces):
        return [fused[index] for index in sorted(baseline_indexes)], False, ()

    return (
        [
            replace(
                fused[index],
                namespace_coverage_promoted=index in promoted_indexes,
            )
            for index in sorted(selected_indexes)
        ],
        True,
        tuple(promoted_namespaces),
    )


def deduplicate_rerank_candidates(
    candidates: Sequence[_RerankCandidate],
) -> list[_RerankCandidate]:
    """Collapse exact citation/section/content duplicates deterministically."""

    ordered = sorted(
        candidates,
        key=lambda candidate: (
            candidate.route_rank,
            candidate.namespace_rank,
            candidate.hit.namespace,
            candidate.hit.id,
        ),
    )
    representatives: dict[tuple[str, str, str], _RerankCandidate] = {}
    duplicate_namespaces: dict[tuple[str, str, str], set[str]] = {}
    for candidate in ordered:
        key = rerank_dedupe_key(candidate.hit)
        representatives.setdefault(key, candidate)
        duplicate_namespaces.setdefault(key, set()).add(candidate.hit.namespace)
    return [
        replace(
            representative,
            duplicate_namespaces=tuple(sorted(duplicate_namespaces[key])),
        )
        for key, representative in representatives.items()
    ]


def rerank_dedupe_key(hit: SearchHit) -> tuple[str, str, str]:
    """Return an exact cross-namespace identity without conflating relative paths."""

    if hit.url:
        locator = f"url:{normalize_page_url(hit.url)}"
    elif hit.repo_path:
        locator = f"repo:{hit.namespace}:{normalize_path(hit.repo_path).casefold()}"
    elif hit.path:
        locator = f"path:{hit.namespace}:{normalize_path(hit.path).casefold()}"
    else:
        locator = f"id:{hit.namespace}:{hit.id}"
    section = " ".join(
        unicodedata.normalize("NFKC", hit.section_path).casefold().split()
    )
    content_hash = hashlib.sha256(hit.content.encode("utf-8")).hexdigest()
    return locator, section, content_hash


def cross_encoder_passage(hit: SearchHit) -> str:
    """Build one bounded, citation-aware passage for local reranking."""

    location = hit.url or hit.repo_path or hit.path
    header = [
        f"Title: {hit.title[:MAX_RERANK_TITLE_CHARS]}",
        f"Section: {hit.section_path[:MAX_RERANK_SECTION_CHARS]}",
        f"Location: {location[:MAX_RERANK_LOCATION_CHARS]}",
    ]
    return "\n".join(header) + f"\n\n{hit.content[:MAX_RERANK_CONTENT_CHARS]}"


def _annotate_cross_namespace_candidate(
    candidate: _RerankCandidate,
    *,
    fused: _FusedRerankCandidate | None = None,
) -> SearchHit:
    score_info = dict(candidate.hit.score_info)
    cross_namespace: dict[str, object] = {
        "route_rank": candidate.route_rank,
        "namespace_rank": candidate.namespace_rank,
    }
    if fused is not None:
        cross_namespace.update(
            {
                "fusion_method": CROSS_NAMESPACE_FUSION_METHOD,
                "rrf_k": CROSS_NAMESPACE_RRF_K,
                "cross_encoder_rank": fused.cross_encoder_rank,
                "cross_encoder_score": fused.cross_encoder_score,
                "reranker_score": fused.cross_encoder_score,
                "cross_encoder_rrf_score": fused.cross_encoder_rrf_score,
                "namespace_rrf_score": fused.namespace_rrf_score,
                "fusion_score": fused.fusion_score,
            }
        )
        if fused.namespace_coverage_promoted:
            cross_namespace["namespace_coverage_promoted"] = True
    if len(candidate.duplicate_namespaces) > 1:
        cross_namespace["duplicate_namespaces"] = list(
            candidate.duplicate_namespaces
        )
    score_info["cross_namespace"] = cross_namespace
    return replace(candidate.hit, score_info=score_info)


def retrieval_plan(query: str, *, config: RuntimeConfig, options: RetrievalOptions) -> RetrievalPlan:
    return RetrievalPlan(query=query, config=config, options=options)


def multi_namespace_retrieval_plan(
    query: str,
    *,
    configs: Sequence[RuntimeConfig],
    options: Sequence[RetrievalOptions],
    initial_fanout: int | None = None,
) -> MultiNamespaceRetrievalPlan:
    if not configs or len(configs) > MAX_NAMESPACE_FANOUT:
        raise ValueError(
            f"between one and {MAX_NAMESPACE_FANOUT} namespace configs are required"
        )
    if len(configs) != len(options):
        raise ValueError("one retrieval option set is required per namespace")
    fanout = len(configs) if initial_fanout is None else initial_fanout
    if type(fanout) is not int or not 1 <= fanout <= len(configs):
        raise ValueError(
            "initial_fanout must be between one and the selected namespace count"
        )
    return MultiNamespaceRetrievalPlan(
        query=query,
        plans=[
            retrieval_plan(query, config=config, options=namespace_options)
            for config, namespace_options in zip(configs, options, strict=True)
        ],
        initial_fanout=fanout,
    )


def build_multi_query_subqueries(
    *,
    query: str,
    query_vector: Sequence[float],
    candidates: int,
    doc_kind: str | None = None,
    include_attributes: Sequence[str] = RETRIEVAL_ATTRIBUTES,
) -> list[dict[str, object]]:
    """Build ANN and boosted BM25 subqueries for one turbopuffer multi-query."""

    common: dict[str, object] = {
        "limit": candidates,
        "include_attributes": list(include_attributes),
    }
    if doc_kind:
        common["filters"] = ("doc_kind", "Eq", doc_kind)
    return [
        {
            **common,
            "rank_by": ("vector", "ANN", list(query_vector)),
        },
        {
            **common,
            "rank_by": bm25_rank_by(query),
        },
    ]


def bm25_rank_by(query: str) -> tuple[object, ...]:
    """Return boosted BM25 expression over citation/content fields."""

    return (
        "Sum",
        [
            ("Product", 2.0, ("title", "BM25", query)),
            ("Product", 1.5, ("section_path", "BM25", query)),
            ("content", "BM25", query),
        ],
    )


def run_multi_query(namespace: object, subqueries: Sequence[dict[str, object]]) -> tuple[object, str]:
    fusion = "server_rrf"
    try:
        return namespace.multi_query(queries=subqueries, rerank_by=("RRF",)), fusion  # type: ignore[attr-defined]
    except TypeError as exc:
        if not is_unsupported_rerank_type_error(exc):
            raise
        fusion = "client_rrf"
        return namespace.multi_query(queries=subqueries), fusion  # type: ignore[attr-defined]


def build_namespace(*, config: RuntimeConfig, api_key: str) -> object:
    try:
        import turbopuffer as tpuf
    except ImportError as exc:  # pragma: no cover - depends on optional install.
        raise RuntimeError("turbopuffer is required for live retrieval. Run `uv sync` first.") from exc

    if hasattr(tpuf, "api_key"):
        setattr(tpuf, "api_key", api_key)
    if hasattr(tpuf, "api_base_url"):
        setattr(tpuf, "api_base_url", f"https://{config.region}.turbopuffer.com")
    if hasattr(tpuf, "Turbopuffer"):
        try:
            client = tpuf.Turbopuffer(api_key=api_key, region=config.region)  # type: ignore[attr-defined]
        except TypeError:
            client = tpuf.Turbopuffer(api_key=api_key)  # type: ignore[attr-defined]
        if hasattr(client, "namespace"):
            return client.namespace(config.namespace)
        if hasattr(client, "Namespace"):
            return client.Namespace(config.namespace)
    if hasattr(tpuf, "Namespace"):
        return tpuf.Namespace(config.namespace)  # type: ignore[attr-defined]
    raise RuntimeError("Unsupported turbopuffer SDK: no Namespace constructor found.")


def is_unsupported_rerank_type_error(exc: TypeError) -> bool:
    message = str(exc).lower()
    return "rerank_by" in message or "unexpected keyword" in message or "unexpected argument" in message


def missing_schema_attribute(exc: BaseException) -> str | None:
    matches = list(MISSING_SCHEMA_ATTRIBUTE_RE.finditer(str(exc)))
    if len(matches) != 1:
        return None
    return matches[0].group("attribute").casefold()


def user_friendly_query_error(exc: BaseException) -> str:
    status = getattr(exc, "status_code", None)
    provider = re.sub(r"[^A-Za-z0-9_.-]", "", exc.__class__.__name__)[:80]
    if not provider:
        provider = "ProviderError"
    detail = (
        f"{provider} (status={status})"
        if isinstance(status, int)
        else provider
    )
    return (
        "Live retrieval failed. Likely fixes: confirm TURBOPUFFER_API_KEY is set, "
        "the explicit --namespace has been indexed, and TURBOPUFFER_REGION matches the indexed corpus. "
        f"Provider error: {detail}."
    )


def extract_result_lists(response: object) -> list[list[object]]:
    """Normalize common SDK multi_query response shapes into row lists."""

    if response is None:
        return []

    direct_rows = get_field(response, "rows")
    if direct_rows is not None:
        return [list(direct_rows)]

    for field_name in ("results", "queries", "responses", "result_sets"):
        value = get_field(response, field_name)
        lists = extract_nested_lists(value)
        if lists:
            return lists

    if isinstance(response, Sequence) and not isinstance(response, (str, bytes, bytearray)):
        lists = extract_nested_lists(response)
        if lists:
            return lists
    return []


def extract_nested_lists(value: object) -> list[list[object]]:
    if value is None:
        return []
    if isinstance(value, Mapping):
        rows = get_field(value, "rows")
        return [list(rows)] if rows is not None else []
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        value_list = list(value)
        if not value_list:
            return []
        if all(is_row_like(item) for item in value_list):
            return [value_list]
        lists: list[list[object]] = []
        for item in value_list:
            rows = get_field(item, "rows")
            if rows is not None:
                lists.append(list(rows))
            elif isinstance(item, Sequence) and not isinstance(item, (str, bytes, bytearray)):
                lists.append(list(item))
        return [rows for rows in lists if rows]
    rows = get_field(value, "rows")
    return [list(rows)] if rows is not None else []


def is_row_like(item: object) -> bool:
    if isinstance(item, Mapping):
        return "id" in item or "attributes" in item or any(name in item for name in RETRIEVAL_ATTRIBUTES)
    return any(hasattr(item, name) for name in ("id", "attributes", "title", "content"))


def client_side_rrf(result_lists: Sequence[Sequence[object]], *, top_k: int, rrf_k: int = RRF_K) -> list[SearchHit]:
    scores: dict[str, float] = {}
    rows_by_key: dict[str, object] = {}
    ranks_by_key: dict[str, dict[str, int]] = {}
    names = ["ann", "bm25"]
    for list_index, rows in enumerate(result_lists):
        source_name = names[list_index] if list_index < len(names) else f"query_{list_index + 1}"
        for rank, row in enumerate(rows, start=1):
            key = row_key(row)
            if not key:
                continue
            scores[key] = scores.get(key, 0.0) + 1.0 / (rrf_k + rank)
            rows_by_key.setdefault(key, row)
            ranks_by_key.setdefault(key, {})[source_name] = rank
    ordered = sorted(scores, key=lambda key: (-scores[key], min(ranks_by_key[key].values()), key))[:top_k]
    hits: list[SearchHit] = []
    for key in ordered:
        hits.append(
            row_to_hit(
                rows_by_key[key],
                score_info={
                    "fusion": "client_rrf",
                    "rrf_score": scores[key],
                    "source_ranks": ranks_by_key[key],
                },
            )
        )
    return hits


def rank_hits(hits: Sequence[SearchHit], *, options: RetrievalOptions, query: str = "") -> list[SearchHit]:
    """Apply the configured final ranking layer to fused retrieval candidates."""

    if options.ranking_mode == "chunk":
        return list(hits)

    groups: dict[str, list[tuple[int, SearchHit]]] = {}
    for rank, hit in enumerate(hits, start=1):
        key = ranking_group_key(hit, options.ranking_mode)
        groups.setdefault(key, []).append((rank, hit))

    ranked_groups: list[tuple[float, int, str, SearchHit]] = []
    for key, group in groups.items():
        best_rank, representative = min(group, key=lambda item: item[0])
        base_score = ranking_group_score(group, options.ranking_aggregation)
        ranking_score = base_score * ranking_group_profile_multiplier(group, options.ranking_profile, query=query)
        ranked_groups.append(
            (
                ranking_score,
                best_rank,
                key,
                hit_with_ranking_info(
                    representative,
                    ranking_score=ranking_score,
                    source_rank=best_rank,
                    file_hit_count=len(group),
                    source_ranks=[rank for rank, _hit in group],
                    options=options,
                ),
            )
        )
    ranked_groups.sort(key=lambda item: (-item[0], item[1], item[2]))
    ranked_hits = [item[3] for item in ranked_groups]
    return diversify_repo_role_hits(ranked_hits, options=options, query=query)


def ranking_group_score(group: Sequence[tuple[int, SearchHit]], aggregation: str) -> float:
    scores = sorted((1.0 / (RRF_K + rank) for rank, _hit in group), reverse=True)
    max_score = scores[0]
    if aggregation == "max":
        return max_score
    if aggregation == "adaptive_sum_3":
        close_extra_hits = sum(1 for score in scores[1:3] if score >= max_score * 0.80)
        return max_score * (1.0 + 0.05 * close_extra_hits)
    if aggregation == "capped_sum_3":
        return sum(scores[:3])
    raise ValueError(f"Unsupported ranking aggregation: {aggregation}")


def ranking_group_key(hit: SearchHit, mode: str) -> str:
    """Group repository chunks by file and, when requested, website chunks by page."""

    if hit.repo_path:
        return f"repo:{normalize_path(hit.repo_path)}"
    if hit.path and hit.url.startswith("https://github.com/"):
        return f"repo:{normalize_path(hit.path)}"
    if mode == "page" and hit.url:
        return f"page:{normalize_page_url(hit.url)}"
    return f"chunk:{hit.id or hit.url or hit.path or hit.title}"


def hit_with_ranking_info(
    hit: SearchHit,
    *,
    ranking_score: float,
    source_rank: int,
    file_hit_count: int,
    source_ranks: Sequence[int],
    options: RetrievalOptions,
) -> SearchHit:
    score_info = dict(hit.score_info)
    score_info["ranking"] = {
        "mode": options.ranking_mode,
        "profile": options.ranking_profile,
        "ranking_pool": options.ranking_pool,
        "aggregation": options.ranking_aggregation,
        "file_score": ranking_score,
        "group_score": ranking_score,
        "file_hit_count": file_hit_count,
        "group_hit_count": file_hit_count,
        "source_rank": source_rank,
        "source_ranks": list(source_ranks),
    }
    return SearchHit(
        id=hit.id,
        title=hit.title,
        url=hit.url,
        section_path=hit.section_path,
        content=hit.content,
        path=hit.path,
        repo_path=hit.repo_path,
        tags=list(hit.tags),
        score_info=score_info,
        doc_kind=hit.doc_kind,
        chunk_index=hit.chunk_index,
        namespace=hit.namespace,
    )


IMPLEMENTATION_INTENT_TOKENS = {"code", "function", "functions", "implement", "implemented", "implementation", "logic", "source"}
EXPERIMENT_INTENT_TOKENS = {"autoresearch", "benchmark", "benchmarks", "experiment", "experiments", "fixture", "fixtures", "hypothesis", "hypotheses", "research"}
EXPERIMENT_PATH_TOKENS = {"autoresearch", "benchmark", "benchmarks", "experiment", "experiments", "fixture", "fixtures", "hypothesis", "hypotheses"}
EXAMPLE_INTENT_TOKENS = {"demo", "demos", "example", "examples", "sample", "samples", "tutorial", "tutorials"}
DOCUMENTATION_INTENT_TOKENS = {
    "doc",
    "docs",
    "document",
    "documentation",
    "documented",
    "guide",
    "guides",
    "readme",
    "tutorial",
    "tutorials",
}
CLI_INTENT_TOKENS = {"cli", "command", "commands", "runner", "script", "scripts"}
COMMAND_RUNTIME_TOKENS = {
    "callback",
    "command",
    "commands",
    "execute",
    "execution",
    "group",
    "groups",
    "invocation",
    "invoke",
    "lookup",
    "main",
    "registration",
    "runtime",
    "subcommand",
}
PARAMETER_METADATA_TOKENS = {
    "annotated",
    "argument",
    "arguments",
    "default",
    "defaults",
    "field",
    "fields",
    "metadata",
    "model",
    "models",
    "option",
    "options",
    "parameter",
    "parameters",
}
UTILITY_INTENT_TOKENS = {"helper", "helpers", "util", "utilities", "utility", "utils"}
DUNDER_INIT_PUBLIC_TOKENS = {
    "api",
    "entry",
    "entrypoint",
    "export",
    "exports",
    "init",
    "initialization",
    "initialize",
    "level",
    "main",
    "module",
    "public",
    "reexport",
    "reexports",
    "top",
}
TERMINAL_UI_TOKENS = {
    "app",
    "appdir",
    "confirm",
    "dir",
    "echo",
    "get",
    "launch",
    "progress",
    "progressbar",
    "prompt",
    "secho",
    "style",
    "terminal",
}
FIXTURE_INTENT_TOKENS = {"fixture", "fixtures", "snapshot", "snapshots", "test", "testing", "tests"}
SOURCE_FILE_EXTENSIONS = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".go",
    ".h",
    ".hpp",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".lua",
    ".php",
    ".py",
    ".pyi",
    ".rb",
    ".rs",
    ".sh",
    ".swift",
    ".ts",
    ".tsx",
}
NON_SOURCE_PATH_PREFIXES = ("docs/", "doc/", "tests/", "test/", "examples/", "example/", "benchmarks/", "benchmark/")
PATH_SYMBOL_STOP_TOKENS = {
    "and",
    "are",
    "as",
    "behavior",
    "code",
    "does",
    "file",
    "files",
    "flow",
    "for",
    "helper",
    "helpers",
    "implement",
    "implemented",
    "implements",
    "in",
    "including",
    "into",
    "is",
    "local",
    "locally",
    "logic",
    "of",
    "or",
    "public",
    "repo",
    "repository",
    "source",
    "such",
    "system",
    "the",
    "to",
    "using",
    "validate",
    "validated",
    "where",
    "with",
}
PATH_SYMBOL_GENERIC_TOKENS = {
    "app",
    "apps",
    "changelog",
    "doc",
    "docs",
    "js",
    "json",
    "lib",
    "md",
    "py",
    "readme",
    "rst",
    "src",
    "test",
    "tests",
    "ts",
    "txt",
    "yaml",
    "yml",
}
PATH_SYMBOL_ALIASES = {
    "auth": {"authentication"},
    "authentication": {"auth"},
    "error": {"exception", "exceptions"},
    "errors": {"exception", "exceptions"},
    "exception": {"error", "errors"},
    "exceptions": {"error", "errors"},
    "utilities": {"util", "utility", "utils"},
    "utility": {"util", "utilities", "utils"},
    "utils": {"util", "utilities", "utility"},
}
IDENTIFIER_TOKEN_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z]|\d|$)|[A-Z]?[a-z]+|\d+")
SYMBOL_DECLARATION_RE = re.compile(r"(?m)^\s*(?:async\s+def|def|class)\s+([A-Za-z_][A-Za-z0-9_]*)")


def ranking_group_profile_multiplier(
    group: Sequence[tuple[int, SearchHit]],
    profile: str,
    *,
    query: str = "",
) -> float:
    """Return the strongest profile signal present in a grouped file/page."""

    if profile == "none":
        return 1.0
    multiplier = max(ranking_profile_multiplier(hit, profile, query=query) for _rank, hit in group)
    if profile == "repo_code" and all(hit_is_repo_file_card(hit) for _rank, hit in group):
        multiplier *= repo_file_card_group_multiplier(group, query=query)
    return multiplier


def hit_is_repo_file_card(hit: SearchHit) -> bool:
    return hit.title.endswith(" file metadata") or hit.section_path.startswith("File metadata:")


def repo_file_card_group_multiplier(group: Sequence[tuple[int, SearchHit]], *, query: str = "") -> float:
    query_tokens = ranking_signal_tokens(query)
    if not query_tokens:
        return 0.75
    best_path_bonus = 0.75
    best_content_overlap = 0
    for _rank, hit in group:
        path = normalize_path(hit.repo_path)
        if file_stem_matches_query(query_tokens, file_stem(path)):
            best_path_bonus = max(best_path_bonus, 1.30)
        elif related_token_count(query_tokens, ranking_signal_tokens(path)) >= 2:
            best_path_bonus = max(best_path_bonus, 1.05)
        best_content_overlap = max(
            best_content_overlap,
            related_token_count(query_tokens, ranking_signal_tokens(f"{hit.title} {hit.section_path} {hit.content}")),
        )
    if best_path_bonus > 0.75:
        return best_path_bonus
    if best_content_overlap >= 3:
        return 0.90
    return 0.75


def ranking_profile_multiplier(hit: SearchHit, profile: str, *, query: str = "") -> float:
    if profile == "none" or not hit.repo_path:
        return 1.0
    path = normalize_path(hit.repo_path)
    lower_path = path.casefold()
    query_tokens = lexical_tokens(query)
    path_tokens = lexical_tokens(path)
    multiplier = 1.0
    if path_has_agent_artifact_segment(lower_path) or lower_path.startswith(("artifacts/", "autoresearch/")):
        multiplier *= 0.20
    elif lower_path.endswith(".json") and "/data/" in lower_path and any(
        marker in lower_path for marker in ("eval", "fixture", "seed", "dataset")
    ):
        multiplier *= 0.20
    elif is_repo_example_path(lower_path) and not query_tokens & EXAMPLE_INTENT_TOKENS:
        multiplier *= 0.70
    elif lower_path.startswith("docs/") or lower_path.endswith(".md") or lower_path in {"readme.md", "changelog.md"}:
        multiplier *= 0.70
    elif lower_path.startswith("tests/"):
        multiplier *= 1.10
    if lower_path.startswith("doc/") and not query_tokens & (DOCUMENTATION_INTENT_TOKENS | EXAMPLE_INTENT_TOKENS):
        multiplier *= 0.80
    if lower_path.startswith("docs/tutorial/") and not query_tokens & (DOCUMENTATION_INTENT_TOKENS | EXAMPLE_INTENT_TOKENS):
        multiplier *= 0.80
    if lower_path.startswith("docs/source/") and not query_tokens & DOCUMENTATION_INTENT_TOKENS:
        multiplier *= 0.80
    private_path_misses_query = nested_private_path_segment_misses_query(path, query=query)
    if private_path_misses_query:
        multiplier *= 0.80
    if is_repo_example_scaffold_path(lower_path) and not query_tokens & EXAMPLE_INTENT_TOKENS:
        multiplier *= 0.80
    if is_repo_fixture_scaffold_path(lower_path) and not query_tokens & FIXTURE_INTENT_TOKENS:
        multiplier *= 0.80
    if path_tokens & EXPERIMENT_PATH_TOKENS and not query_tokens & EXPERIMENT_INTENT_TOKENS:
        multiplier *= 0.70
    if lower_path.startswith("src/") and query_tokens & IMPLEMENTATION_INTENT_TOKENS:
        multiplier *= 1.12
    if rust_crate_root_entrypoint_matches_query(lower_path, query=query):
        multiplier *= 1.35
    if lower_path.endswith("/__init__.py") and not query_tokens & DUNDER_INIT_PUBLIC_TOKENS:
        multiplier *= 0.82
    if lower_path.endswith("/core.py") and query_tokens & COMMAND_RUNTIME_TOKENS:
        multiplier *= 1.20
    if lower_path.endswith("/models.py") and query_tokens & PARAMETER_METADATA_TOKENS:
        multiplier *= 1.20
    if (
        lower_path.endswith("/utils.py")
        and query_tokens & PARAMETER_METADATA_TOKENS
        and not query_tokens & UTILITY_INTENT_TOKENS
    ):
        multiplier *= 0.75
    if lower_path.endswith("/cli.py") and not query_tokens & CLI_INTENT_TOKENS:
        multiplier *= 0.90
    if "/_click/termui.py" in f"/{lower_path}" and query_tokens & TERMINAL_UI_TOKENS:
        multiplier *= 1.20
    if index_parent_matches_query(lower_path, query=query):
        multiplier *= 1.50
    multiplier *= repo_path_symbol_multiplier(hit, query=query)
    return multiplier


def is_repo_example_path(lower_path: str) -> bool:
    return (
        lower_path.startswith(("docs_src/", "examples/"))
        or "example_scripts/" in lower_path
        or "/example/" in lower_path
        or "/examples/" in lower_path
    )


def path_has_agent_artifact_segment(lower_path: str) -> bool:
    return bool(set(normalize_path(lower_path).casefold().split("/")[:-1]) & AGENT_ARTIFACT_PATH_SEGMENTS)


def is_repo_example_scaffold_path(lower_path: str) -> bool:
    return normalize_path(lower_path).casefold().startswith(("docs_src/", "tests/test_tutorial/"))


def index_parent_matches_query(lower_path: str, *, query: str = "") -> bool:
    parts = normalize_path(lower_path).casefold().split("/")
    return len(parts) >= 2 and parts[-1].startswith("index.") and file_stem_matches_query(
        ranking_signal_tokens(query),
        parts[-2],
    )


def rust_crate_root_entrypoint_matches_query(lower_path: str, *, query: str = "") -> bool:
    parts = normalize_path(lower_path).casefold().split("/")
    if (
        len(parts) != 4
        or parts[0] != "crates"
        or parts[2] != "src"
        or parts[3] not in {"lib.rs", "main.rs"}
    ):
        return False
    return related_token_count(ranking_signal_tokens(query), ranking_signal_tokens(parts[1])) >= 1


def is_repo_fixture_scaffold_path(lower_path: str) -> bool:
    normalized = f"/{normalize_path(lower_path).casefold()}"
    return any(marker in normalized for marker in ("/fixtures/", "/snapshots/", "/resources/test/", "/tests/data/"))


def nested_private_path_segment_misses_query(path: str, *, query: str = "") -> bool:
    """Return true for nested private package/topic dirs absent from the query."""

    query_tokens = ranking_signal_tokens(query)
    parts = normalize_path(path).casefold().split("/")
    if len(parts) < 3:
        return False
    package_index = 1 if parts[0] in {"src", "lib"} else 0
    path_tokens = ranking_signal_tokens(path)
    for index, segment in enumerate(parts[:-1]):
        if index <= package_index or not segment.startswith("_"):
            continue
        if segment == "_internal" and related_token_count(query_tokens, path_tokens) >= 2:
            continue
        segment_tokens = ranking_signal_tokens(segment)
        if not segment_tokens or related_token_count(query_tokens, segment_tokens) == 0:
            return True
    return False


def repo_path_symbol_multiplier(hit: SearchHit, *, query: str = "") -> float:
    """Boost precise path and symbol matches without changing index schema."""

    path = normalize_path(hit.repo_path)
    query_tokens = ranking_signal_tokens(query)
    if not query_tokens:
        return 1.0
    if is_docs_path(path) and file_stem_matches_query(query_tokens, file_stem(path)):
        return 1.30
    if not is_source_path(path):
        return 1.0
    extra = 0.0
    if file_stem_matches_query(query_tokens, file_stem(path)):
        extra += 0.04
    if related_token_count(query_tokens, ranking_signal_tokens(" ".join(SYMBOL_DECLARATION_RE.findall(hit.content)))) >= 2:
        extra += 0.04
    return 1.0 + min(extra, 0.06)


def diversify_repo_role_hits(hits: list[SearchHit], *, options: RetrievalOptions, query: str) -> list[SearchHit]:
    """Promote one strong doc/test companion without replacing the top implementation hit."""

    if options.ranking_profile != "repo_code" or options.top_k < 5:
        return hits
    target_window = 5
    if len(hits) <= target_window:
        return hits
    paths = [normalize_path(hit.repo_path or hit.path) for hit in hits]
    if not is_source_path(paths[0]) or any(is_repo_companion_path(path) for path in paths[:target_window]):
        return hits
    query_tokens = ranking_signal_tokens(query)
    if not query_tokens:
        return hits
    top_source_stems = [file_stem(path) for path in paths[:3] if is_source_path(path)]
    candidate = best_repo_role_companion(
        hits,
        paths=paths,
        query_tokens=query_tokens,
        top_source_stems=top_source_stems,
        start_index=target_window,
        stop_index=min(len(hits), 20),
    )
    if candidate is None:
        return hits
    promoted = list(hits)
    hit = promoted.pop(candidate)
    promoted.insert(target_window - 1, hit)
    return promoted


def best_repo_role_companion(
    hits: Sequence[SearchHit],
    *,
    paths: Sequence[str],
    query_tokens: set[str],
    top_source_stems: Sequence[str],
    start_index: int,
    stop_index: int,
) -> int | None:
    best: tuple[int, int, int] | None = None
    for index in range(start_index, stop_index):
        strength = repo_role_companion_strength(
            hits[index],
            paths[index],
            query_tokens=query_tokens,
            top_source_stems=top_source_stems,
        )
        if strength <= 0:
            continue
        candidate = (strength, -index, index)
        if best is None or candidate > best:
            best = candidate
    return best[2] if best is not None else None


def repo_role_companion_strength(
    hit: SearchHit,
    path: str,
    *,
    query_tokens: set[str],
    top_source_stems: Sequence[str],
) -> int:
    if is_tests_path(path):
        stem = test_file_stem(path)
        if file_stem_matches_query(query_tokens, stem) or (top_source_stems and stem == top_source_stems[0]):
            return 3
        return 0
    if not is_docs_path(path):
        return 0
    content_strength = related_token_count(
        query_tokens,
        ranking_signal_tokens(" ".join((hit.title, hit.section_path, hit.content[:2000]))),
    )
    if file_stem_matches_query(query_tokens, file_stem(path)):
        return max(12, content_strength)
    return content_strength if content_strength >= 10 else 0


def file_stem_matches_query(query_tokens: set[str], stem: str) -> bool:
    stem_tokens = ranking_signal_tokens(stem)
    if not stem_tokens:
        return False
    required_matches = 1 if len(stem_tokens) == 1 else min(2, len(stem_tokens))
    return related_token_count(query_tokens, stem_tokens) >= required_matches


def related_token_count(query_tokens: set[str], document_tokens: set[str]) -> int:
    matched_tokens: set[str] = set()
    for document_token in document_tokens:
        for query_token in query_tokens:
            if query_token == document_token or (
                len(query_token) >= 4
                and len(document_token) >= 4
                and (query_token.startswith(document_token) or document_token.startswith(query_token))
            ):
                matched_tokens.add(document_token)
                break
    return len(matched_tokens)


def ranking_signal_tokens(value: str) -> set[str]:
    tokens: set[str] = set()
    for token in re.split(r"[^A-Za-z0-9]+", value):
        for match in IDENTIFIER_TOKEN_RE.findall(token):
            tokens.add(match.casefold())
    for token in list(tokens):
        if len(token) > 3 and token.endswith("ies"):
            tokens.add(f"{token[:-3]}y")
        if len(token) > 3 and token.endswith("s"):
            tokens.add(token[:-1])
        tokens.update(PATH_SYMBOL_ALIASES.get(token, set()))
    return {
        token
        for token in tokens
        if len(token) >= 3 and token not in PATH_SYMBOL_STOP_TOKENS and token not in PATH_SYMBOL_GENERIC_TOKENS
    }


def is_source_path(path: str) -> bool:
    normalized = normalize_path(path).casefold()
    if normalized.startswith(NON_SOURCE_PATH_PREFIXES):
        return False
    if path_has_agent_artifact_segment(normalized) or is_repo_fixture_scaffold_path(normalized):
        return False
    if normalized.startswith(("src/", "lib/")):
        return True
    return file_extension(normalized) in SOURCE_FILE_EXTENSIONS


def file_extension(path: str) -> str:
    name = path.rsplit("/", 1)[-1]
    return f".{name.rsplit('.', 1)[1].casefold()}" if "." in name else ""


def is_docs_path(path: str) -> bool:
    return path.startswith("docs/")


def is_tests_path(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return path.startswith("tests/") or name.startswith("test_") or name.endswith("_test.py")


def is_repo_companion_path(path: str) -> bool:
    return is_docs_path(path) or is_tests_path(path)


def test_file_stem(path: str) -> str:
    stem = file_stem(path)
    if stem.startswith("test_"):
        stem = stem.removeprefix("test_")
    if stem.endswith("_test"):
        stem = stem.removesuffix("_test")
    return stem


def file_stem(path: str) -> str:
    name = path.rsplit("/", 1)[-1]
    return name.rsplit(".", 1)[0]


def lexical_tokens(value: str) -> set[str]:
    return {token for token in re.split(r"[^a-z0-9]+", value.casefold()) if token}


def normalize_path(value: str) -> str:
    return value.replace("\\", "/").strip("/")


def normalize_page_url(value: str) -> str:
    return value.split("#", 1)[0].rstrip("/").casefold()


def row_to_hit(row: object, *, score_info: Mapping[str, object] | None = None) -> SearchHit:
    attrs = row_attributes(row)
    base_score_info: dict[str, object] = {}
    for score_field in ("score", "dist", "distance", "rank", "$dist"):
        value = get_field(row, score_field)
        if value is not None:
            clean_name = "distance" if score_field in {"dist", "$dist"} else score_field.strip("$")
            base_score_info[clean_name] = value
    if score_info:
        base_score_info.update(dict(score_info))
    chunk_index = attrs.get("chunk_index")
    return SearchHit(
        id=str(get_field(row, "id") or attrs.get("id") or row_key(row)),
        title=str(attrs.get("title") or ""),
        url=str(attrs.get("url") or ""),
        section_path=str(attrs.get("section_path") or ""),
        content=str(attrs.get("content") or ""),
        path=str(attrs.get("path") or ""),
        repo_path=str(attrs.get("repo_path") or ""),
        tags=row_tags(attrs),
        doc_kind=str(attrs.get("doc_kind") or ""),
        chunk_index=chunk_index if isinstance(chunk_index, int) else None,
        score_info=base_score_info,
    )


def row_tags(attrs: Mapping[str, object]) -> list[str]:
    value = attrs.get("tags")
    if value is None:
        return []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise RuntimeError("retrieval row tags must be a list of strings")
    tags = list(value)
    if not all(isinstance(tag, str) for tag in tags):
        raise RuntimeError("retrieval row tags must be a list of strings")
    return tags


def row_attributes(row: object) -> dict[str, object]:
    attrs = get_field(row, "attributes")
    if isinstance(attrs, Mapping):
        result = {str(key): value for key, value in attrs.items() if key != "vector"}
    else:
        result = {}
    if isinstance(row, Mapping):
        source_items = row.items()
    else:
        source_items = ((name, getattr(row, name)) for name in RETRIEVAL_ATTRIBUTES if hasattr(row, name))
    for key, value in source_items:
        key_str = str(key)
        if key_str in {"vector", "attributes"}:
            continue
        if key_str in RETRIEVAL_ATTRIBUTES or key_str in {"id"}:
            result.setdefault(key_str, value)
    return result


def row_key(row: object) -> str:
    row_id = get_field(row, "id")
    if row_id is not None:
        return str(row_id)
    attrs = row_attributes(row)
    attr_id = attrs.get("id")
    if attr_id is not None:
        return str(attr_id)
    for fields in (("url", "section_path", "content"), ("path", "chunk_index"), ("title", "content")):
        parts = [str(attrs.get(field) or "") for field in fields]
        if any(parts):
            return "|".join(parts)
    return ""


def get_field(item: object, name: str) -> object | None:
    if isinstance(item, Mapping):
        return item.get(name)
    return getattr(item, name, None)
