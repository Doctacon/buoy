"""Hybrid retrieval helpers for turbopuffer-backed site search.

Dry-run planning is local-only. Live retrieval is intentionally isolated behind
``HybridRetriever.from_config`` so credentials are read only when the caller has
explicitly opted into a live turbopuffer query.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import os
import re
from typing import Any, Mapping, Protocol, Sequence

from buoy_search.config import RuntimeConfig
from buoy_search.chunker import SentenceTransformerEmbedder

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
AGENT_ARTIFACT_PATH_SEGMENTS = {".10x", ".agents", ".buoy", ".claude", ".cursor", ".loom", ".pi", ".turbo-search"}
RETRIEVAL_ATTRIBUTES = [
    "title",
    "url",
    "section_path",
    "content",
    "path",
    "repo_path",
    "doc_kind",
    "chunk_index",
]
SCHEMA_PORTABLE_RETRIEVAL_ATTRIBUTES = [attribute for attribute in RETRIEVAL_ATTRIBUTES if attribute != "repo_path"]


def namespace_uses_website_defaults(namespace: str) -> bool:
    """Return true when a namespace should use document/page ranking defaults."""

    return namespace.startswith(("site-", "pdf-", "file-"))


def ranking_defaults_for_namespace(namespace: str) -> dict[str, object]:
    """Return namespace-aware ranking defaults for CLI and experiment runners."""

    if namespace_uses_website_defaults(namespace):
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
class MultiNamespaceRetrievalResult:
    """Structured result for an explicitly selected namespace set."""

    query: str
    hits: list[SearchHit]
    region: str
    namespaces: list[str]
    embedding_model: str
    embedding_precision: str
    top_k: int
    candidates: int
    namespace_results: list[RetrievalResult]
    fusion: str = "cross_namespace_rrf"

    def to_dict(self) -> dict[str, object]:
        return {
            "command": "retrieve",
            "dry_run": False,
            "credentials_required": True,
            "turbopuffer_api_calls": True,
            "api_calls_occurred": True,
            "content_retrieval_occurred": True,
            "query": self.query,
            "region": self.region,
            "namespaces": self.namespaces,
            "embedding_model": self.embedding_model,
            "embedding_precision": self.embedding_precision,
            "top_k": self.top_k,
            "candidates": self.candidates,
            "fusion": self.fusion,
            "namespace_results": [
                {
                    "namespace": result.namespace,
                    "fusion": result.fusion,
                    "ranking_mode": result.ranking_mode,
                    "ranking_profile": result.ranking_profile,
                    "ranking_pool": result.ranking_pool,
                    "ranking_aggregation": result.ranking_aggregation,
                    "hit_count": len(result.hits),
                }
                for result in self.namespace_results
            ],
            "hits": [hit.to_dict() for hit in self.hits],
        }


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
            "live_execution": "pass --live to embed the query and call turbopuffer",
            "retrieval": {
                "request": "turbopuffer multi_query",
                "subqueries": [ann_subquery, bm25_subquery],
                "rerank_by": ["RRF"],
                "fallback": "client-side reciprocal-rank fusion if server RRF is unsupported or separate lists are returned",
            },
        }


@dataclass(frozen=True)
class MultiNamespaceRetrievalPlan:
    """Safe no-credential plan for multiple explicit namespace targets."""

    query: str
    plans: list[RetrievalPlan]

    def to_dict(self) -> dict[str, object]:
        first = self.plans[0]
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
            "fusion": "cross_namespace_rrf",
            "namespace_plans": [
                {
                    "namespace": plan.config.namespace,
                    "ranking_mode": plan.options.ranking_mode,
                    "ranking_profile": plan.options.ranking_profile,
                    "ranking_pool": plan.options.ranking_pool,
                    "ranking_aggregation": plan.options.ranking_aggregation,
                    "retrieval": plan.to_dict()["retrieval"],
                }
                for plan in self.plans
            ],
            "live_execution": "pass --live to embed once and query each selected namespace",
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
                "Use `retrieve --dry-run` or omit `--live` to inspect the plan without credentials."
            )
        embedder = SentenceTransformerEmbedder(
            config.embedding_model, precision=config.embedding_precision
        )
        namespace = build_namespace(config=config, api_key=api_key)
        return cls(namespace=namespace, embedder=embedder, config=config)

    def retrieve(self, query: str, options: RetrievalOptions) -> RetrievalResult:
        cleaned_query = query.strip()
        if not cleaned_query:
            raise RuntimeError("A non-empty query is required for retrieval.")
        vectors = self._embedder.encode([cleaned_query])
        if not vectors or not vectors[0]:
            raise RuntimeError("The embedding model returned no vector for the query.")
        return self.retrieve_embedded(cleaned_query, vectors[0], options)

    def retrieve_embedded(
        self,
        query: str,
        query_vector: Sequence[float],
        options: RetrievalOptions,
    ) -> RetrievalResult:
        """Query one namespace with an already-computed query vector."""

        subqueries = build_multi_query_subqueries(
            query=query,
            query_vector=query_vector,
            candidates=options.candidates,
            doc_kind=options.doc_kind,
        )
        try:
            response, fusion = run_multi_query(self._namespace, subqueries)
        except Exception as exc:  # pragma: no cover - SDK/network/schema failure paths are integration-tested.
            if not is_missing_attribute_error(exc, "repo_path"):
                raise RuntimeError(user_friendly_query_error(exc)) from exc
            portable_subqueries = build_multi_query_subqueries(
                query=query,
                query_vector=query_vector,
                candidates=options.candidates,
                doc_kind=options.doc_kind,
                include_attributes=SCHEMA_PORTABLE_RETRIEVAL_ATTRIBUTES,
            )
            try:
                response, fusion = run_multi_query(self._namespace, portable_subqueries)
            except Exception as fallback_exc:  # pragma: no cover - requires SDK/network failure.
                raise RuntimeError(user_friendly_query_error(fallback_exc)) from fallback_exc

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


class MultiNamespaceRetriever:
    """Embed once, query explicit namespaces sequentially, and merge by RRF."""

    def __init__(self, *, retrievers: list[HybridRetriever], embedder: Embedder) -> None:
        self._retrievers = retrievers
        self._embedder = embedder

    @classmethod
    def from_configs(cls, configs: Sequence[RuntimeConfig]) -> "MultiNamespaceRetriever":
        if not configs:
            raise ValueError("at least one namespace config is required")
        first = configs[0]
        contract = (first.region, first.embedding_model, first.embedding_precision)
        if any(
            (config.region, config.embedding_model, config.embedding_precision) != contract
            for config in configs[1:]
        ):
            raise ValueError("all selected namespaces must use one region, embedding model, and precision")
        api_key = os.environ.get("TURBOPUFFER_API_KEY")
        if not api_key:
            raise RuntimeError(
                "TURBOPUFFER_API_KEY must be set in the environment for live retrieval. "
                "Use `retrieve --dry-run` or omit `--live` to inspect the plan without credentials."
            )
        embedder = SentenceTransformerEmbedder(
            first.embedding_model, precision=first.embedding_precision
        )
        retrievers: list[HybridRetriever] = []
        for config in configs:
            try:
                namespace = build_namespace(config=config, api_key=api_key)
            except RuntimeError as exc:
                raise RuntimeError(f"Could not prepare namespace {config.namespace!r}: {exc}") from exc
            retrievers.append(HybridRetriever(namespace=namespace, embedder=embedder, config=config))
        return cls(retrievers=retrievers, embedder=embedder)

    def retrieve(
        self,
        query: str,
        options: Sequence[RetrievalOptions],
    ) -> MultiNamespaceRetrievalResult:
        if len(options) != len(self._retrievers):
            raise ValueError("one retrieval option set is required per namespace")
        cleaned_query = query.strip()
        if not cleaned_query:
            raise RuntimeError("A non-empty query is required for retrieval.")
        vectors = self._embedder.encode([cleaned_query])
        if not vectors or not vectors[0]:
            raise RuntimeError("The embedding model returned no vector for the query.")

        results: list[RetrievalResult] = []
        for retriever, namespace_options in zip(self._retrievers, options, strict=True):
            namespace = retriever._config.namespace
            try:
                result = retriever.retrieve_embedded(cleaned_query, vectors[0], namespace_options)
            except RuntimeError as exc:
                raise RuntimeError(f"Retrieval failed for namespace {namespace!r}: {exc}") from exc
            for hit in result.hits:
                hit.namespace = namespace
            results.append(result)

        first = results[0]
        return MultiNamespaceRetrievalResult(
            query=cleaned_query,
            hits=cross_namespace_rrf(results, top_k=first.top_k),
            region=first.region,
            namespaces=[result.namespace for result in results],
            embedding_model=first.embedding_model,
            embedding_precision=first.embedding_precision,
            top_k=first.top_k,
            candidates=first.candidates,
            namespace_results=results,
        )


def cross_namespace_rrf(
    results: Sequence[RetrievalResult],
    *,
    top_k: int,
    rrf_k: int = RRF_K,
) -> list[SearchHit]:
    """Fuse namespace-local ranked hits without comparing their raw scores."""

    ranked: list[tuple[float, int, int, str, SearchHit]] = []
    for namespace_index, result in enumerate(results):
        for source_rank, hit in enumerate(result.hits, start=1):
            score = 1.0 / (rrf_k + source_rank)
            hit.score_info = {
                **hit.score_info,
                "cross_namespace_fusion": "rrf",
                "cross_namespace_rrf_score": score,
                "namespace_rank": source_rank,
            }
            ranked.append((-score, namespace_index, source_rank, hit.id, hit))
    ranked.sort(key=lambda item: item[:4])
    return [item[4] for item in ranked[:top_k]]


def retrieval_plan(query: str, *, config: RuntimeConfig, options: RetrievalOptions) -> RetrievalPlan:
    return RetrievalPlan(query=query, config=config, options=options)


def multi_namespace_retrieval_plan(
    query: str,
    *,
    configs: Sequence[RuntimeConfig],
    options: Sequence[RetrievalOptions],
) -> MultiNamespaceRetrievalPlan:
    return MultiNamespaceRetrievalPlan(
        query=query,
        plans=[
            retrieval_plan(query, config=config, options=namespace_options)
            for config, namespace_options in zip(configs, options, strict=True)
        ],
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


def is_missing_attribute_error(exc: BaseException, attribute: str) -> bool:
    message = str(exc).casefold()
    attribute_text = attribute.casefold()
    return attribute_text in message and "not found in schema" in message


def user_friendly_query_error(exc: BaseException) -> str:
    message = str(exc) or exc.__class__.__name__
    return (
        "Live retrieval failed. Likely fixes: confirm TURBOPUFFER_API_KEY is set, "
        "the namespace has been indexed, and TURBOPUFFER_REGION/TURBOPUFFER_NAMESPACE match the indexed corpus. "
        f"Underlying error: {message}"
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
        score_info=score_info,
        doc_kind=hit.doc_kind,
        chunk_index=hit.chunk_index,
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
        doc_kind=str(attrs.get("doc_kind") or ""),
        chunk_index=chunk_index if isinstance(chunk_index, int) else None,
        score_info=base_score_info,
    )


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
