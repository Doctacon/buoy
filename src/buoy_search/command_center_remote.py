"""Explicit, read-only remote snapshot and search services for the command center.

Construction and local status inspection are inert. Provider clients and routing/content
embedding models are created only by :meth:`RemoteSnapshotService.refresh` and
:meth:`SearchService.execute` after request validation and credential checks.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
import logging
import math
import os
import re
from typing import Callable, Literal, Mapping, Protocol, Sequence
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from buoy_search.catalog import CatalogError, NamespaceCard, load_routing_embedder
from buoy_search.command_center_local import LocalInventoryService, NamespaceInventory
from buoy_search.config import RuntimeConfig
from buoy_search.remote_catalog import (
    REMOTE_CATALOG_NAMESPACE,
    CompatibilityContract,
    RemoteCatalogError,
    RemoteCatalogSnapshot,
    RemoteClient,
    create_client,
    read_remote_catalog,
    redact_remote_error,
    require_eligible,
)
from buoy_search.retriever import (
    DEFAULT_CANDIDATES,
    DEFAULT_TOP_K,
    RANKING_AGGREGATIONS,
    RANKING_MODES,
    RANKING_PROFILES,
    HybridRetriever,
    MultiNamespaceRetriever,
    MultiNamespaceRetrievalResult,
    ProviderCallError,
    RetrievalOptions,
    RetrievalResult,
    SearchHit,
    ranking_defaults_for_namespace,
)
from buoy_search.routing import (
    DEFAULT_ROUTE_TOP_K,
    MAX_ROUTE_TOP_K,
    AutomaticRoutingError,
    RoutingSelection,
    hybrid_route,
)

# Command-center request limits are defensive service boundaries. Existing retrieval
# defaults and ranking behavior remain owned by retriever.py and routing.py.
MAX_QUERY_CHARS = 4_000
MAX_EXPLICIT_NAMESPACES = MAX_ROUTE_TOP_K
MAX_TOP_K = 100
MAX_CANDIDATES = 1_000
MAX_RANKING_POOL = 1_000
MAX_DOC_KIND_CHARS = 128
MAX_CONTENT_PREVIEW_CHARS = 4_000
MAX_REMOTE_SNAPSHOT_NAMESPACES = 1_000
MAX_CITATION_CHARS = 2_000
_NAMESPACE_ID = re.compile(r"^[A-Za-z0-9-_.]{1,128}$")
_DOCUMENT_CITATION = re.compile(
    r"^(?:file|pdf)://[A-Za-z0-9][A-Za-z0-9_.-]{0,127}/"
    r"(?P<filename>(?:[A-Za-z0-9_.~-]|%[0-9A-Fa-f]{2})+)$"
)
_DATABASE_CITATION = re.compile(
    r"^(?:duckdb|bigquery|snowflake)://"
    r"[a-z0-9]+(?:-[a-z0-9]+)*/"
    r"(?P<document_id>(?:[A-Za-z0-9_.~-]|%[0-9A-Fa-f]{2})+)$"
)
_SAFE_DIAGNOSTIC_KEYS = {
    "score",
    "distance",
    "rank",
    "fusion",
    "source_rank",
    "rrf_score",
    "source_ranks",
    "cross_namespace_fusion",
    "cross_namespace_rrf_score",
    "namespace_rank",
    "ranking",
    "mode",
    "profile",
    "ranking_pool",
    "aggregation",
    "file_score",
    "group_score",
    "file_hit_count",
    "group_hit_count",
    "source_ranks",
}
_SAFE_DIAGNOSTIC_STRINGS = {
    "server_rrf",
    "client_rrf",
    "cross_namespace_rrf",
    "rrf",
    "chunk",
    "file",
    "page",
    "none",
    "repo_code",
    "max",
    "adaptive_sum_3",
    "capped_sum_3",
    "ann",
    "bm25",
}


class LocalNamespaceReader(Protocol):
    def list_namespaces(self, *, offset: int = 0, limit: int = 50) -> NamespaceInventory: ...


@dataclass(frozen=True)
class ServiceError:
    code: str
    message: str
    phase: str


@dataclass(frozen=True)
class RemoteNamespaceStatus:
    namespace: str
    local_present: bool
    live: bool | None
    card_present: bool | None
    status: Literal[
        "not_checked",
        "local_only",
        "eligible",
        "missing_card",
        "stale_target",
        "disabled",
        "incompatible",
    ]
    title: str | None = None
    source_kind: str | None = None
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class RemoteSnapshotResult:
    state: Literal["not_checked", "not_configured", "ready", "error"]
    credentials_required: bool
    api_calls_occurred: bool
    writes_occurred: bool
    namespaces: tuple[RemoteNamespaceStatus, ...]
    namespace_total: int
    namespaces_truncated: bool
    counts: dict[str, int] = field(default_factory=dict)
    request_counts: dict[str, int] = field(default_factory=dict)
    snapshot_revision: str | None = None
    error: ServiceError | None = None


RemoteCatalogReader = Callable[..., RemoteCatalogSnapshot]
RemoteClientFactory = Callable[..., RemoteClient]


class RemoteSnapshotService:
    """Combine local inventory with one explicitly requested stable remote read."""

    def __init__(
        self,
        *,
        local_inventory: LocalNamespaceReader | None = None,
        config: RuntimeConfig | None = None,
        environment: Mapping[str, str] | None = None,
        client_factory: RemoteClientFactory = create_client,
        catalog_reader: RemoteCatalogReader = read_remote_catalog,
        logger: logging.Logger | None = None,
    ) -> None:
        self._local_inventory = local_inventory or LocalInventoryService()
        self._config = config or RuntimeConfig()
        self._environment = os.environ if environment is None else environment
        self._client_factory = client_factory
        self._catalog_reader = catalog_reader
        self._logger = logger or logging.getLogger(__name__)

    def not_checked(self) -> RemoteSnapshotResult:
        """Return local rows with an explicit not-checked remote status."""

        local_ids = self._local_namespace_ids()
        statuses = tuple(
            RemoteNamespaceStatus(namespace, True, None, None, "not_checked")
            for namespace in local_ids
        )
        return _snapshot_result(
            state="not_checked",
            credentials_required=False,
            api_calls_occurred=False,
            namespaces=statuses,
        )

    def refresh(self) -> RemoteSnapshotResult:
        """Perform the explicit stable namespace/catalog read; never write or persist it."""

        local_ids = self._local_namespace_ids()
        api_key = self._environment.get("TURBOPUFFER_API_KEY")
        if not api_key:
            return _snapshot_result(
                state="not_configured",
                credentials_required=True,
                api_calls_occurred=False,
                namespaces=tuple(
                    RemoteNamespaceStatus(namespace, True, None, None, "not_checked")
                    for namespace in local_ids
                ),
                error=ServiceError(
                    "remote_credentials_missing",
                    "Remote access is not configured for this process.",
                    "credentials",
                ),
            )

        compatibility = _compatibility(self._config)
        try:
            client = self._client_factory(api_key=api_key, region=self._config.region)
        except (RemoteCatalogError, CatalogError, RuntimeError, OSError) as exc:
            return self._refresh_failure(local_ids, exc=exc, api_calls_occurred=False)
        try:
            snapshot = self._catalog_reader(
                client,
                region=self._config.region,
                compatibility=compatibility,
            )
        except (RemoteCatalogError, CatalogError, RuntimeError, OSError) as exc:
            return self._refresh_failure(local_ids, exc=exc, api_calls_occurred=True)

        return _snapshot_result(
            state="ready",
            credentials_required=True,
            api_calls_occurred=True,
            namespaces=_combined_namespace_statuses(local_ids, snapshot),
            counts=asdict(snapshot.counts),
            request_counts={
                "namespace_list_pages": snapshot.metrics.namespace_list_pages,
                "metadata_requests": snapshot.metrics.metadata_requests,
                "card_query_pages": snapshot.metrics.card_query_pages,
            },
            snapshot_revision=snapshot.snapshot_revision,
        )

    def _local_namespace_ids(self) -> tuple[str, ...]:
        first = self._local_inventory.list_namespaces(offset=0, limit=100)
        ids = [item.namespace for item in first.items]
        offset = len(first.items)
        while offset < first.total:
            page = self._local_inventory.list_namespaces(offset=offset, limit=100)
            if not page.items:
                break
            ids.extend(item.namespace for item in page.items)
            offset += len(page.items)
        return tuple(sorted(set(ids)))

    def _refresh_failure(
        self,
        local_ids: Sequence[str],
        *,
        exc: BaseException,
        api_calls_occurred: bool,
    ) -> RemoteSnapshotResult:
        self._log_safe_failure("remote_snapshot", exc)
        return _snapshot_result(
            state="error",
            credentials_required=True,
            api_calls_occurred=api_calls_occurred,
            namespaces=tuple(
                RemoteNamespaceStatus(namespace, True, None, None, "not_checked")
                for namespace in local_ids
            ),
            error=ServiceError(
                "remote_snapshot_failed",
                "The remote namespace snapshot could not be refreshed.",
                "remote_snapshot",
            ),
        )

    def _log_safe_failure(self, phase: str, exc: BaseException) -> None:
        self._logger.warning("%s failed (%s)", phase, redact_remote_error(exc))


@dataclass(frozen=True)
class SearchRequest:
    query: str
    namespaces: tuple[str, ...] = ()
    automatic: bool = False
    route_top_k: int = DEFAULT_ROUTE_TOP_K
    top_k: int = DEFAULT_TOP_K
    candidates: int = DEFAULT_CANDIDATES
    doc_kind: str | None = None
    ranking_mode: str | None = None
    ranking_profile: str | None = None
    ranking_pool: int | None = None
    ranking_aggregation: str | None = None


@dataclass(frozen=True)
class SearchResultHit:
    namespace: str
    title: str
    citation: str
    section: str
    content_preview: str
    content_truncated: bool
    tags: tuple[str, ...]
    score: dict[str, object]


@dataclass(frozen=True)
class SearchResponse:
    state: Literal["success", "error"]
    credentials_required: bool
    api_calls_occurred: bool
    writes_occurred: bool
    automatic: bool
    namespaces: tuple[str, ...] = ()
    hits: tuple[SearchResultHit, ...] = ()
    diagnostics: dict[str, object] = field(default_factory=dict)
    error: ServiceError | None = None


SingleRetrieverFactory = Callable[[RuntimeConfig], object]
MultiRetrieverFactory = Callable[[Sequence[RuntimeConfig]], object]
RoutingEmbedderFactory = Callable[[], object]


class SearchService:
    """Validate and execute one explicit search through the established retrieval paths."""

    def __init__(
        self,
        *,
        config: RuntimeConfig | None = None,
        environment: Mapping[str, str] | None = None,
        client_factory: RemoteClientFactory = create_client,
        catalog_reader: RemoteCatalogReader = read_remote_catalog,
        routing_embedder_factory: RoutingEmbedderFactory = load_routing_embedder,
        single_retriever_factory: SingleRetrieverFactory = HybridRetriever.from_config,
        multi_retriever_factory: MultiRetrieverFactory = MultiNamespaceRetriever.from_configs,
        logger: logging.Logger | None = None,
    ) -> None:
        self._config = config or RuntimeConfig()
        self._environment = os.environ if environment is None else environment
        self._client_factory = client_factory
        self._catalog_reader = catalog_reader
        self._routing_embedder_factory = routing_embedder_factory
        self._single_retriever_factory = single_retriever_factory
        self._multi_retriever_factory = multi_retriever_factory
        self._logger = logger or logging.getLogger(__name__)

    def execute(self, request: SearchRequest) -> SearchResponse:
        """Execute only after validation and credential checks; return no partial hits."""

        validation_error = _validate_search_request(request)
        automatic = request.automatic
        if validation_error is not None:
            return _search_failure(validation_error, automatic=automatic, credentials=False, calls=False)

        api_key = self._environment.get("TURBOPUFFER_API_KEY")
        if not api_key:
            return _search_failure(
                ServiceError(
                    "remote_credentials_missing",
                    "Remote search is not configured for this process.",
                    "credentials",
                ),
                automatic=automatic,
                credentials=True,
                calls=False,
            )

        query = request.query.strip()
        if request.namespaces:
            return self._explicit_search(request, query=query)
        return self._automatic_search(request, query=query, api_key=api_key)

    def _explicit_search(self, request: SearchRequest, *, query: str) -> SearchResponse:
        configs = [replace(self._config, namespace=namespace) for namespace in request.namespaces]
        options = [_explicit_options(request, namespace=config.namespace) for config in configs]
        try:
            if len(configs) == 1:
                retriever = self._single_retriever_factory(configs[0])
                namespaces = (configs[0].namespace,)
            else:
                retriever = self._multi_retriever_factory(configs)
                namespaces = tuple(config.namespace for config in configs)
        except (RuntimeError, ValueError, OSError) as exc:
            return self._search_error(exc, automatic=False, calls=False)
        try:
            raw_result = retriever.retrieve(query, options[0] if len(configs) == 1 else options)  # type: ignore[attr-defined]
        except (RuntimeError, ValueError, OSError) as exc:
            return self._search_error(
                exc,
                automatic=False,
                calls=isinstance(exc, ProviderCallError),
            )
        return _successful_search(raw_result, automatic=False, namespaces=namespaces)

    def _automatic_search(
        self,
        request: SearchRequest,
        *,
        query: str,
        api_key: str,
    ) -> SearchResponse:
        try:
            client = self._client_factory(api_key=api_key, region=self._config.region)
        except (RemoteCatalogError, CatalogError, RuntimeError, OSError) as exc:
            return self._routing_error(exc, calls=False)
        try:
            snapshot = require_eligible(
                self._catalog_reader(
                    client,
                    region=self._config.region,
                    compatibility=_compatibility(self._config),
                )
            )
        except (RemoteCatalogError, CatalogError, RuntimeError, OSError) as exc:
            return self._routing_error(exc, calls=True)

        try:
            routing = hybrid_route(
                query,
                snapshot.eligible_cards,
                embedder=self._routing_embedder_factory(),
                route_top_k=request.route_top_k,
                catalog_namespace=REMOTE_CATALOG_NAMESPACE,
                region=self._config.region,
                snapshot_revision=snapshot.snapshot_revision,
                exclusion_counts=_exclusion_counts(snapshot),
                remote_counts=asdict(snapshot.counts),
                read_metrics={
                    "namespace_list_pages": snapshot.metrics.namespace_list_pages,
                    "metadata_requests": snapshot.metrics.metadata_requests,
                    "card_query_pages": snapshot.metrics.card_query_pages,
                },
            )
            configs = [_config_for_card(self._config, card) for card in routing.selected_cards]
            options = [_routed_options(request, card=card) for card in routing.selected_cards]
            raw_result = self._multi_retriever_factory(configs).retrieve(query, options)
        except (AutomaticRoutingError, CatalogError, RuntimeError, ValueError, OSError) as exc:
            self._log_safe_failure("automatic_search", exc)
            return _search_failure(
                ServiceError(
                    "remote_search_failed",
                    "Automatic search failed before a complete result set was available.",
                    "automatic_search",
                ),
                automatic=True,
                credentials=True,
                calls=True,
            )
        return _successful_search(
            raw_result,
            automatic=True,
            namespaces=tuple(config.namespace for config in configs),
            routing=routing,
        )

    def _search_error(
        self, exc: BaseException, *, automatic: bool, calls: bool
    ) -> SearchResponse:
        self._log_safe_failure("content_retrieval", exc)
        return _search_failure(
            ServiceError(
                "remote_search_failed",
                "Search failed before a complete result set was available.",
                "content_retrieval",
            ),
            automatic=automatic,
            credentials=True,
            calls=calls,
        )

    def _routing_error(self, exc: BaseException, *, calls: bool) -> SearchResponse:
        self._log_safe_failure("remote_routing_catalog", exc)
        return _search_failure(
            ServiceError(
                "remote_routing_failed",
                "Automatic routing could not read a usable remote catalog.",
                "remote_routing_catalog",
            ),
            automatic=True,
            credentials=True,
            calls=calls,
        )

    def _log_safe_failure(self, phase: str, exc: BaseException) -> None:
        self._logger.warning("%s failed (%s)", phase, redact_remote_error(exc))


def _snapshot_result(
    *,
    state: Literal["not_checked", "not_configured", "ready", "error"],
    credentials_required: bool,
    api_calls_occurred: bool,
    namespaces: tuple[RemoteNamespaceStatus, ...],
    counts: dict[str, int] | None = None,
    request_counts: dict[str, int] | None = None,
    snapshot_revision: str | None = None,
    error: ServiceError | None = None,
) -> RemoteSnapshotResult:
    return RemoteSnapshotResult(
        state=state,
        credentials_required=credentials_required,
        api_calls_occurred=api_calls_occurred,
        writes_occurred=False,
        namespaces=namespaces[:MAX_REMOTE_SNAPSHOT_NAMESPACES],
        namespace_total=len(namespaces),
        namespaces_truncated=len(namespaces) > MAX_REMOTE_SNAPSHOT_NAMESPACES,
        counts=counts or {},
        request_counts=request_counts or {},
        snapshot_revision=snapshot_revision,
        error=error,
    )


def _compatibility(config: RuntimeConfig) -> CompatibilityContract:
    return CompatibilityContract(
        region=config.region,
        embedding_model=config.embedding_model,
        embedding_precision=config.embedding_precision,
    )


def _combined_namespace_statuses(
    local_ids: Sequence[str], snapshot: RemoteCatalogSnapshot
) -> tuple[RemoteNamespaceStatus, ...]:
    local = set(local_ids)
    live = set(snapshot.live_namespace_ids)
    cards = {card.namespace: card for card in snapshot.cards}
    missing = set(snapshot.missing_card_ids)
    stale = set(snapshot.stale_target_ids)
    disabled = set(snapshot.disabled_ids)
    incompatible = set(snapshot.incompatible_ids)
    eligible = {card.namespace for card in snapshot.eligible_cards}
    rows: list[RemoteNamespaceStatus] = []
    for namespace in sorted(local | live | set(cards)):
        if namespace in eligible:
            status = "eligible"
        elif namespace in missing:
            status = "missing_card"
        elif namespace in stale:
            status = "stale_target"
        elif namespace in disabled:
            status = "disabled"
        elif namespace in incompatible:
            status = "incompatible"
        else:
            status = "local_only"
        card = cards.get(namespace)
        rows.append(
            RemoteNamespaceStatus(
                namespace=namespace,
                local_present=namespace in local,
                live=namespace in live,
                card_present=card is not None,
                status=status,  # type: ignore[arg-type]
                title=card.title[:1_000] if card else None,
                source_kind=card.source_kind if card else None,
                tags=(
                    tuple(value[:256] for value in card.tags[:100])
                    if card
                    else ()
                ),
            )
        )
    return tuple(rows)


def _validate_search_request(request: SearchRequest) -> ServiceError | None:
    if not isinstance(request.query, str) or not request.query.strip():
        return ServiceError("invalid_search_request", "A non-empty query is required.", "validation")
    if len(request.query) > MAX_QUERY_CHARS:
        return ServiceError(
            "invalid_search_request",
            f"Query must contain at most {MAX_QUERY_CHARS} characters.",
            "validation",
        )
    if type(request.automatic) is not bool:
        return ServiceError("invalid_search_request", "automatic must be a boolean.", "validation")
    if not isinstance(request.namespaces, Sequence) or isinstance(
        request.namespaces, (str, bytes, bytearray)
    ):
        return ServiceError("invalid_search_request", "namespaces must be a list.", "validation")
    if request.automatic == bool(request.namespaces):
        return ServiceError(
            "invalid_search_request",
            "Choose exactly one search mode: automatic routing or explicit namespaces.",
            "validation",
        )
    if len(request.namespaces) > MAX_EXPLICIT_NAMESPACES:
        return ServiceError(
            "invalid_search_request",
            f"At most {MAX_EXPLICIT_NAMESPACES} explicit namespaces may be searched.",
            "validation",
        )
    if any(not isinstance(value, str) for value in request.namespaces):
        return ServiceError("invalid_search_request", "An explicit namespace ID is invalid.", "validation")
    if len(set(request.namespaces)) != len(request.namespaces):
        return ServiceError("invalid_search_request", "Explicit namespaces must not repeat.", "validation")
    if any(_NAMESPACE_ID.fullmatch(value) is None for value in request.namespaces):
        return ServiceError("invalid_search_request", "An explicit namespace ID is invalid.", "validation")
    integer_bounds = (
        ("route_top_k", request.route_top_k, MAX_ROUTE_TOP_K),
        ("top_k", request.top_k, MAX_TOP_K),
        ("candidates", request.candidates, MAX_CANDIDATES),
    )
    for name, value, maximum in integer_bounds:
        if type(value) is not int or value < 1 or value > maximum:
            return ServiceError(
                "invalid_search_request",
                f"{name} must be between 1 and {maximum}.",
                "validation",
            )
    if request.namespaces and request.route_top_k != DEFAULT_ROUTE_TOP_K:
        return ServiceError(
            "invalid_search_request",
            "route_top_k is valid only for automatic routing.",
            "validation",
        )
    if request.doc_kind is not None and (
        not isinstance(request.doc_kind, str)
        or not request.doc_kind.strip()
        or len(request.doc_kind) > MAX_DOC_KIND_CHARS
    ):
        return ServiceError("invalid_search_request", "doc_kind is invalid.", "validation")
    if request.ranking_mode is not None and (
        not isinstance(request.ranking_mode, str) or request.ranking_mode not in RANKING_MODES
    ):
        return ServiceError("invalid_search_request", "ranking_mode is invalid.", "validation")
    if request.ranking_profile is not None and (
        not isinstance(request.ranking_profile, str)
        or request.ranking_profile not in RANKING_PROFILES
    ):
        return ServiceError("invalid_search_request", "ranking_profile is invalid.", "validation")
    if request.ranking_aggregation is not None and (
        not isinstance(request.ranking_aggregation, str)
        or request.ranking_aggregation not in RANKING_AGGREGATIONS
    ):
        return ServiceError("invalid_search_request", "ranking_aggregation is invalid.", "validation")
    if request.ranking_pool is not None and (
        type(request.ranking_pool) is not int
        or request.ranking_pool < 1
        or request.ranking_pool > MAX_RANKING_POOL
    ):
        return ServiceError(
            "invalid_search_request",
            f"ranking_pool must be between 1 and {MAX_RANKING_POOL}.",
            "validation",
        )
    return None


def _explicit_options(request: SearchRequest, *, namespace: str) -> RetrievalOptions:
    defaults = ranking_defaults_for_namespace(namespace)
    return RetrievalOptions(
        top_k=request.top_k,
        candidates=request.candidates,
        doc_kind=request.doc_kind.strip() if request.doc_kind else None,
        ranking_mode=request.ranking_mode or str(defaults["ranking_mode"]),
        ranking_profile=request.ranking_profile or str(defaults["ranking_profile"]),
        ranking_pool=request.ranking_pool or int(defaults["ranking_pool"]),
        ranking_aggregation=request.ranking_aggregation or str(defaults["ranking_aggregation"]),
    )


def _routed_options(request: SearchRequest, *, card: NamespaceCard) -> RetrievalOptions:
    return RetrievalOptions(
        top_k=request.top_k,
        candidates=request.candidates,
        doc_kind=request.doc_kind.strip() if request.doc_kind else None,
        ranking_mode=request.ranking_mode or card.ranking_mode,
        ranking_profile=request.ranking_profile or card.ranking_profile,
        ranking_pool=request.ranking_pool or card.ranking_pool,
        ranking_aggregation=request.ranking_aggregation or card.ranking_aggregation,
    )


def _config_for_card(config: RuntimeConfig, card: NamespaceCard) -> RuntimeConfig:
    return replace(
        config,
        namespace=card.namespace,
        region=card.region,
        embedding_model=card.embedding_model,
        embedding_precision=card.embedding_precision,
    )


def _exclusion_counts(snapshot: RemoteCatalogSnapshot) -> dict[str, int]:
    values = {
        "missing_card": snapshot.counts.missing_card_count,
        "stale_target": snapshot.counts.stale_target_count,
        "disabled": snapshot.counts.disabled_count,
        "incompatible": snapshot.counts.incompatible_count,
    }
    return {key: value for key, value in values.items() if value}


def _successful_search(
    result: RetrievalResult | MultiNamespaceRetrievalResult | object,
    *,
    automatic: bool,
    namespaces: tuple[str, ...],
    routing: RoutingSelection | None = None,
) -> SearchResponse:
    hits = getattr(result, "hits", ())
    diagnostics: dict[str, object] = {
        "fusion": str(getattr(result, "fusion", ""))[:80],
        "hit_count": len(hits),
    }
    if routing is not None:
        diagnostics["routing"] = {
            "strategy": "hybrid_rrf",
            "snapshot_revision": routing.snapshot_revision,
            "eligible_count": routing.eligible_count,
            "selected": [
                {
                    "namespace": entry.namespace,
                    "route_rank": entry.route_rank,
                    "lexical_rank": entry.lexical_rank,
                    "semantic_rank": entry.semantic_rank,
                    "semantic_score": entry.semantic_score,
                    "hybrid_score": entry.hybrid_score,
                }
                for entry in routing.entries
            ],
        }
    return SearchResponse(
        state="success",
        credentials_required=True,
        api_calls_occurred=True,
        writes_occurred=False,
        automatic=automatic,
        namespaces=namespaces,
        hits=tuple(_safe_hit(hit, fallback_namespace=namespaces[0] if len(namespaces) == 1 else "") for hit in hits),
        diagnostics=diagnostics,
    )


def _safe_hit(hit: SearchHit | object, *, fallback_namespace: str) -> SearchResultHit:
    content = str(getattr(hit, "content", ""))
    preview = content[:MAX_CONTENT_PREVIEW_CHARS]
    tags_value = getattr(hit, "tags", ())
    tags = tuple(str(value)[:256] for value in tags_value if isinstance(value, str))
    return SearchResultHit(
        namespace=str(getattr(hit, "namespace", "") or fallback_namespace)[:128],
        title=str(getattr(hit, "title", ""))[:1_000],
        citation=_safe_citation(getattr(hit, "url", "")),
        section=str(getattr(hit, "section_path", ""))[:1_000],
        content_preview=preview,
        content_truncated=len(content) > len(preview),
        tags=tags[:100],
        score=_safe_diagnostics(getattr(hit, "score_info", {})),
    )


def _safe_citation(value: object) -> str:
    if not isinstance(value, str) or len(value) > MAX_CITATION_CHARS:
        return ""
    database_match = _DATABASE_CITATION.fullmatch(value)
    if database_match is not None:
        document_id = unquote(database_match.group("document_id"))
        if document_id.strip() and quote(document_id, safe="") == database_match.group(
            "document_id"
        ):
            return value
        return ""
    document_match = _DOCUMENT_CITATION.fullmatch(value)
    if document_match is not None:
        filename = unquote(document_match.group("filename"))
        if (
            filename not in {"", ".", ".."}
            and "/" not in filename
            and "\\" not in filename
            and quote(filename, safe="") == document_match.group("filename")
        ):
            return value
        return ""
    try:
        parsed = urlsplit(value)
    except ValueError:
        return ""
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        return ""
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def _safe_diagnostics(value: object, *, depth: int = 0) -> dict[str, object]:
    if depth > 3 or not isinstance(value, Mapping):
        return {}
    safe: dict[str, object] = {}
    for key, item in list(value.items())[:50]:
        if not isinstance(key, str) or key not in _SAFE_DIAGNOSTIC_KEYS:
            continue
        if isinstance(item, bool) or item is None:
            safe[key] = item
        elif isinstance(item, (int, float)) and not isinstance(item, bool) and math.isfinite(item):
            safe[key] = item
        elif isinstance(item, str) and item in _SAFE_DIAGNOSTIC_STRINGS:
            safe[key] = item
        elif isinstance(item, Mapping):
            safe[key] = _safe_diagnostics(item, depth=depth + 1)
        elif isinstance(item, Sequence) and not isinstance(item, (str, bytes, bytearray)):
            safe[key] = [
                child
                for child in list(item)[:50]
                if (
                    child is None
                    or isinstance(child, bool)
                    or (
                        isinstance(child, (int, float))
                        and not isinstance(child, bool)
                        and math.isfinite(child)
                    )
                )
            ]
    return safe


def _search_failure(
    error: ServiceError,
    *,
    automatic: bool,
    credentials: bool,
    calls: bool,
) -> SearchResponse:
    return SearchResponse(
        state="error",
        credentials_required=credentials,
        api_calls_occurred=calls,
        writes_occurred=False,
        automatic=automatic,
        error=error,
    )
