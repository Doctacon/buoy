"""Deterministic semantic routing over validated remote namespace cards."""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Callable, Sequence

from buoy_search.catalog import (
    ROUTING_DIMENSIONS,
    ROUTING_MODEL,
    ROUTING_MODEL_REVISION,
    ROUTING_QUERY_PREFIX,
    ROUTING_PROTOTYPE_CONTRACT,
    MAX_ROUTING_EXAMPLES,
    CatalogDocument,
    CatalogError,
    NamespaceCard,
    RoutingEmbedder,
    canonical_text,
    card_passage_text,
    routing_example_passage_text,
    normalize_routing_examples,
    routing_prototype_hash_for_fields,
    validate_vector,
    vector_hash,
)
from buoy_search.config import RuntimeConfig
from buoy_search.cross_encoder import (
    CROSS_ENCODER_MODEL,
    CROSS_ENCODER_REVISION,
    CrossEncoderReranker,
)
from buoy_search.plan_artifacts import stable_hash
from buoy_search.retriever import (
    RRF_K,
    MultiNamespaceRetrievalPlan,
    MultiNamespaceRetrievalResult,
)

DEFAULT_ROUTE_TOP_K = 3
MAX_ROUTE_TOP_K = 3
SEMANTIC_CONFIDENCE_FLOOR = 0.65
SEMANTIC_MARGIN_FLOOR = 0.05
ROUTING_SHORTLIST_LIMIT = 12
ROUTING_PROTOTYPE_STRATEGY = "title_alias_then_bounded_prototype_rerank"
ROUTING_CONFIDENCE_ARTIFACT_ID = "automatic-routing-confidence-v2"
ROUTING_CONFIDENCE_COLLECT_REVISION = "collect-unassessed-v1"
ROUTING_CONFIDENCE_FEATURE_CONTRACT = "max_prototype_score_and_margin_v1"

if RRF_K != 60:  # Keep routing fusion tied to Buoy's established retrieval contract.
    raise RuntimeError(f"automatic routing requires RRF_K=60, found {RRF_K}")


class AutomaticRoutingError(ValueError):
    """Raised when eligible cards cannot be scored into a safe route."""


@dataclass(frozen=True)
class EligibilityResult:
    cards: list[NamespaceCard]
    exclusion_counts: dict[str, int]


@dataclass(frozen=True)
class RouteEntry:
    namespace: str
    route_rank: int
    lexical_rank: int | None
    lexical_matched_descriptors: int
    lexical_matched_token_count: int
    semantic_rank: int
    semantic_score: float
    hybrid_score: float
    exact_name_match: bool = False
    shortlist_rank: int | None = None
    shortlist_cosine_score: float | None = None
    reranker_rank: int | None = None
    reranker_score: float | None = None
    winning_prototype_kind: str | None = None
    winning_prototype_index: int | None = None
    winning_prototype_hash: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "namespace": self.namespace,
            "route_rank": self.route_rank,
            "lexical_rank": self.lexical_rank,
            "lexical_matched_descriptors": self.lexical_matched_descriptors,
            "lexical_matched_token_count": self.lexical_matched_token_count,
            "semantic_rank": self.semantic_rank,
            "semantic_score": self.semantic_score,
            "hybrid_score": self.hybrid_score,
            "exact_name_match": self.exact_name_match,
        }
        optional = {
            "shortlist_rank": self.shortlist_rank,
            "shortlist_cosine_score": self.shortlist_cosine_score,
            "reranker_rank": self.reranker_rank,
            "reranker_score": self.reranker_score,
            "winning_prototype_kind": self.winning_prototype_kind,
            "winning_prototype_hash": self.winning_prototype_hash,
        }
        payload.update({key: value for key, value in optional.items() if value is not None})
        if self.winning_prototype_kind is not None:
            payload["winning_prototype_index"] = self.winning_prototype_index
        return payload


@dataclass(frozen=True)
class PrototypeRouteScore:
    """Content-free score record for one shortlisted corpus."""

    card: NamespaceCard
    shortlist_rank: int
    shortlist_cosine_score: float
    reranker_rank: int
    reranker_score: float
    winning_prototype_kind: str
    winning_prototype_index: int | None
    winning_prototype_hash: str


@dataclass(frozen=True)
class RoutingSelection:
    catalog_namespace: str
    region: str
    snapshot_revision: str
    requested_limit: int
    eligible_count: int
    exclusion_counts: dict[str, int]
    exclusion_ids: dict[str, list[str]]
    remote_counts: dict[str, int]
    read_metrics: dict[str, object]
    selected_cards: list[NamespaceCard]
    entries: list[RouteEntry]
    initial_fanout: int
    selection_reason: str
    high_confidence: bool
    semantic_margin: float | None
    strategy: str = "title_alias_then_semantic"
    reranker_margin: float | None = None
    confidence_score_floor: float | None = None
    confidence_margin_floor: float | None = None
    confidence_calibration_id: str | None = None
    confidence_calibration_revision: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "active": self.strategy != ROUTING_PROTOTYPE_STRATEGY,
            "strategy": self.strategy,
            "catalog_namespace": self.catalog_namespace,
            "region": self.region,
            "snapshot_revision": self.snapshot_revision,
            "credentials_required": True,
            "read_only_api_calls_occurred": True,
            "content_retrieval_occurred": False,
            "routing_model": ROUTING_MODEL,
            "routing_model_revision": ROUTING_MODEL_REVISION,
            "requested_limit": self.requested_limit,
            "initial_fanout": self.initial_fanout,
            "selection_reason": self.selection_reason,
            "high_confidence": self.high_confidence,
            "semantic_confidence_floor": SEMANTIC_CONFIDENCE_FLOOR,
            "semantic_margin_floor": SEMANTIC_MARGIN_FLOOR,
            "semantic_margin": self.semantic_margin,
            "eligible_count": self.eligible_count,
            "exclusion_counts": dict(self.exclusion_counts),
            "exclusion_ids": {
                key: list(values)
                for key, values in sorted(self.exclusion_ids.items())
            },
            "remote_counts": dict(self.remote_counts),
            "read_metrics": dict(self.read_metrics),
            "selected_cards": [entry.to_dict() for entry in self.entries],
        }
        if self.strategy == ROUTING_PROTOTYPE_STRATEGY:
            payload.pop("semantic_confidence_floor")
            payload.pop("semantic_margin_floor")
            payload.update(
                {
                    "routing_reranker_model": CROSS_ENCODER_MODEL,
                    "routing_reranker_revision": CROSS_ENCODER_REVISION,
                    "shortlist_limit": ROUTING_SHORTLIST_LIMIT,
                    "prototype_contract": ROUTING_PROTOTYPE_CONTRACT,
                    "reranker_margin": self.reranker_margin,
                    "confidence_score_floor": self.confidence_score_floor,
                    "confidence_margin_floor": self.confidence_margin_floor,
                    "confidence_calibration_id": self.confidence_calibration_id,
                    "confidence_calibration_revision": self.confidence_calibration_revision,
                    "confidence_artifact": {
                        "id": ROUTING_CONFIDENCE_ARTIFACT_ID,
                        "revision": ROUTING_CONFIDENCE_COLLECT_REVISION,
                        "mode": "collect",
                        "owner_approved": False,
                        "feature_contract": ROUTING_CONFIDENCE_FEATURE_CONTRACT,
                    },
                }
            )
        return payload


@dataclass(frozen=True)
class RoutedRetrievalPlan:
    plan: MultiNamespaceRetrievalPlan
    routing: RoutingSelection
    evidence: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        routing = self.routing.to_dict()
        payload = {
            **self.plan.to_dict(),
            "credentials_required": routing["credentials_required"],
            "turbopuffer_api_calls": routing["read_only_api_calls_occurred"],
            "api_calls_occurred": routing["read_only_api_calls_occurred"],
            "routing": routing,
        }
        if self.evidence is not None:
            payload["evidence"] = dict(self.evidence)
        return payload


@dataclass(frozen=True)
class RoutedRetrievalResult:
    result: MultiNamespaceRetrievalResult
    routing: RoutingSelection

    def to_dict(self) -> dict[str, object]:
        routing = self.routing.to_dict()
        routing["content_retrieval_occurred"] = True
        return {**self.result.to_dict(), "content_retrieval_occurred": True, "routing": routing}


def eligible_catalog_cards(
    document: CatalogDocument,
    *,
    config: RuntimeConfig,
) -> EligibilityResult:
    """Apply enabled/runtime compatibility gates before any relevance work."""

    cards: list[NamespaceCard] = []
    exclusions: dict[str, int] = {}
    for card in document.cards:
        reason: str | None = None
        if not card.enabled:
            reason = "disabled"
        elif card.region != config.region:
            reason = "region"
        elif card.embedding_model != config.embedding_model:
            reason = "embedding_model"
        elif card.embedding_precision != config.embedding_precision:
            reason = "embedding_precision"
        elif card.vector_dimensions != ROUTING_DIMENSIONS:
            reason = "vector_dimensions"
        if reason is not None:
            exclusions[reason] = exclusions.get(reason, 0) + 1
        else:
            cards.append(card)
    return EligibilityResult(cards=cards, exclusion_counts=exclusions)


def require_eligible_cards(result: EligibilityResult, *, catalog_path: object = None) -> list[NamespaceCard]:
    """Compatibility helper retained for provider-neutral unit callers."""
    if result.cards:
        return result.cards
    excluded = ", ".join(
        f"{reason}={count}" for reason, count in sorted(result.exclusion_counts.items())
    ) or "none registered"
    raise CatalogError(
        f"no enabled compatible namespace cards ({excluded}); inspect `buoy catalog list --all`"
    )


def lexical_route(
    query: str,
    cards: Sequence[NamespaceCard],
) -> list[tuple[NamespaceCard, int, int]]:
    """Rank complete normalized descriptor phrases without frequency weighting."""

    normalized_query = canonical_text(query)
    padded_query = f" {normalized_query} "
    matched: list[tuple[NamespaceCard, int, int]] = []
    for card in cards:
        descriptors = {
            descriptor
            for value in (card.title, *card.aliases, *card.tags)
            if (descriptor := canonical_text(value))
        }
        matches = {
            descriptor
            for descriptor in descriptors
            if f" {descriptor} " in padded_query
        }
        if matches:
            matched.append(
                (card, len(matches), sum(len(descriptor.split()) for descriptor in matches))
            )
    matched.sort(key=lambda item: (-item[1], -item[2], item[0].namespace))
    return matched


def named_route(
    query: str,
    cards: Sequence[NamespaceCard],
) -> list[NamespaceCard]:
    """Return cards whose complete normalized title or alias appears in the query."""

    normalized_query = canonical_text(query)
    padded_query = f" {normalized_query} "
    matched: list[tuple[NamespaceCard, int, int]] = []
    for card in cards:
        descriptors = {
            descriptor
            for value in (*_title_descriptors(card.title), *card.aliases)
            if (descriptor := canonical_text(value))
        }
        matches = {
            descriptor
            for descriptor in descriptors
            if f" {descriptor} " in padded_query
        }
        if matches:
            matched.append(
                (card, len(matches), sum(len(descriptor.split()) for descriptor in matches))
            )
    matched.sort(key=lambda item: (-item[1], -item[2], item[0].namespace))
    return [card for card, _count, _tokens in matched]


def _title_descriptors(title: str) -> tuple[str, ...]:
    """Return the stored title plus a safe stem for a simple domain title.

    Historical generated cards may use a bare two-label host such as
    ``turbopuffer.com`` as their title. Treating its first label as a title
    variant lets the natural product name match without mutating the card or
    broadening the shortcut to summaries/tags.
    """

    stripped = title.strip()
    match = re.fullmatch(
        r"(?:www\.)?([A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)\.[A-Za-z]{2,63}",
        stripped,
        flags=re.IGNORECASE,
    )
    if match is None:
        return (stripped,)
    return stripped, match.group(1)


def semantic_route(
    query: str,
    cards: Sequence[NamespaceCard],
    *,
    embedder: RoutingEmbedder,
) -> list[tuple[NamespaceCard, float]]:
    """Rank persisted card vectors against one pinned local query embedding."""

    return _semantic_route_by_vector(
        query,
        cards,
        embedder=embedder,
        prototype=False,
    )


def _semantic_route_by_vector(
    query: str,
    cards: Sequence[NamespaceCard],
    *,
    embedder: RoutingEmbedder,
    prototype: bool,
) -> list[tuple[NamespaceCard, float]]:
    """Rank one isolated vector authority using exactly one query embedding."""

    cleaned_query = query.strip()
    if not cleaned_query:
        raise AutomaticRoutingError("a non-empty query is required for automatic routing")
    try:
        encoded = embedder.encode([f"{ROUTING_QUERY_PREFIX}{cleaned_query}"])
    except Exception:
        raise AutomaticRoutingError("routing query embedding failed") from None
    if len(encoded) != 1:
        raise AutomaticRoutingError("routing model must return exactly one query vector")
    query_vector = _validated_query_vector(encoded[0])
    ranked: list[tuple[NamespaceCard, float]] = []
    for card in cards:
        card_vector = (
            card.routing_prototype_vector if prototype else card.vector
        )
        score = sum(
            left * right
            for left, right in zip(query_vector, card_vector, strict=True)
        )
        if not math.isfinite(score):
            raise AutomaticRoutingError(
                f"non-finite semantic score for namespace {card.namespace!r}"
            )
        ranked.append((card, score))
    ranked.sort(key=lambda item: (-item[1], item[0].namespace))
    return ranked


def prototype_route_scores(
    query: str,
    cards: Sequence[NamespaceCard],
    *,
    embedder: RoutingEmbedder,
    reranker: CrossEncoderReranker,
    include_exact_names: bool = False,
) -> list[PrototypeRouteScore]:
    """Score an exact local vector shortlist against bounded card prototypes.

    This function never talks to a provider. It consumes only the cards already
    returned by the authoritative catalog read, embeds the query once, and
    passes at most twelve cards times nine passages to the pinned reranker.
    """

    _validate_prototype_cards(cards)
    semantic = _semantic_route_by_vector(
        query,
        cards,
        embedder=embedder,
        prototype=True,
    )
    if include_exact_names:
        named = named_route(query, cards)
        if len(named) > MAX_ROUTE_TOP_K:
            raise AutomaticRoutingError(
                f"query names {len(named)} corpora; select at most "
                f"{MAX_ROUTE_TOP_K} with repeated --namespace"
            )
        by_namespace = {card.namespace: score for card, score in semantic}
        named_names = {card.namespace for card in named}
        semantic = [
            *((card, by_namespace[card.namespace]) for card in named),
            *((card, score) for card, score in semantic if card.namespace not in named_names),
        ]
    shortlist = semantic[:ROUTING_SHORTLIST_LIMIT]
    return _rerank_prototype_shortlist(query, shortlist, reranker=reranker)


def _rerank_prototype_shortlist(
    query: str,
    shortlist: Sequence[tuple[NamespaceCard, float]],
    *,
    reranker: CrossEncoderReranker,
) -> list[PrototypeRouteScore]:
    """Rerank one already-authoritative exact shortlist without re-embedding."""

    if len(shortlist) > ROUTING_SHORTLIST_LIMIT:
        raise AutomaticRoutingError("routing shortlist exceeds the governed limit")
    passages: list[str] = []
    prototype_keys: list[tuple[int, str, int | None, str]] = []
    for card_index, (card, _score) in enumerate(shortlist):
        base = card_passage_text(
            title=card.title,
            summary=card.summary,
            aliases=card.aliases,
            tags=card.tags,
        )
        passages.append(base)
        prototype_keys.append(
            (
                card_index,
                "card",
                None,
                stable_hash(
                    {
                        "contract": ROUTING_PROTOTYPE_CONTRACT,
                        "kind": "card",
                        "passage": base,
                    }
                ),
            )
        )
        for example_index, example in enumerate(card.routing_examples):
            passage = routing_example_passage_text(
                title=card.title,
                summary=card.summary,
                example=example,
            )
            passages.append(passage)
            prototype_keys.append(
                (
                    card_index,
                    "example",
                    example_index,
                    stable_hash(
                        {
                            "contract": ROUTING_PROTOTYPE_CONTRACT,
                            "kind": "example",
                            "passage": passage,
                        }
                    ),
                )
            )
    if len(passages) > ROUTING_SHORTLIST_LIMIT * (MAX_ROUTING_EXAMPLES + 1):
        raise AutomaticRoutingError("routing prototype passage count exceeds the governed limit")
    try:
        raw_scores = reranker.score(query.strip(), passages)
    except Exception:
        raise AutomaticRoutingError("routing shortlist reranking failed") from None
    if not isinstance(raw_scores, Sequence) or isinstance(
        raw_scores, (str, bytes, bytearray)
    ):
        raise AutomaticRoutingError("routing shortlist reranker returned an invalid score sequence")
    if len(raw_scores) != len(prototype_keys):
        raise AutomaticRoutingError("routing shortlist reranker returned the wrong score count")

    best: dict[int, tuple[float, str, int | None, str]] = {}
    for key, raw_score in zip(prototype_keys, raw_scores, strict=True):
        card_index, kind, example_index, prototype_hash = key
        if isinstance(raw_score, bool) or not isinstance(raw_score, (int, float)):
            raise AutomaticRoutingError("routing shortlist reranker returned a non-numeric score")
        score = float(raw_score)
        if not math.isfinite(score):
            raise AutomaticRoutingError("routing shortlist reranker returned a non-finite score")
        # Passages are emitted base-first and then in canonical example order;
        # a strict improvement therefore preserves the governed tie order.
        current = best.get(card_index)
        if current is None or score > current[0]:
            best[card_index] = (score, kind, example_index, prototype_hash)

    intermediate: list[tuple[NamespaceCard, int, float, float, str, int | None, str]] = []
    for card_index, (card, cosine_score) in enumerate(shortlist):
        score, kind, example_index, prototype_hash = best[card_index]
        intermediate.append(
            (
                card,
                card_index + 1,
                cosine_score,
                score,
                kind,
                example_index,
                prototype_hash,
            )
        )
    intermediate.sort(key=lambda item: (-item[3], item[1], item[0].namespace))
    return [
        PrototypeRouteScore(
            card=card,
            shortlist_rank=shortlist_rank,
            shortlist_cosine_score=cosine_score,
            reranker_rank=reranker_rank,
            reranker_score=reranker_score,
            winning_prototype_kind=kind,
            winning_prototype_index=example_index,
            winning_prototype_hash=prototype_hash,
        )
        for reranker_rank, (
            card,
            shortlist_rank,
            cosine_score,
            reranker_score,
            kind,
            example_index,
            prototype_hash,
        ) in enumerate(intermediate, start=1)
    ]


def _validate_prototype_cards(cards: Sequence[NamespaceCard]) -> None:
    if not cards:
        raise AutomaticRoutingError("automatic routing requires at least one eligible card")
    namespaces = [card.namespace for card in cards]
    if len(namespaces) != len(set(namespaces)):
        raise AutomaticRoutingError("routing candidate cards contain duplicate namespaces")
    for card in cards:
        if len(card.routing_examples) > MAX_ROUTING_EXAMPLES:
            raise AutomaticRoutingError(
                f"routing cards may contain at most {MAX_ROUTING_EXAMPLES} examples"
            )
        try:
            normalized = normalize_routing_examples(card.routing_examples)
        except CatalogError:
            raise AutomaticRoutingError(
                "routing candidate card examples are invalid"
            ) from None
        if normalized != card.routing_examples:
            raise AutomaticRoutingError(
                "routing candidate card examples are not canonical"
            )
        try:
            prototype_vector = validate_vector(
                card.routing_prototype_vector,
                namespace=card.namespace,
                field="routing_prototype_vector",
            )
            expected_hash = routing_prototype_hash_for_fields(
                title=card.title,
                summary=card.summary,
                aliases=card.aliases,
                tags=card.tags,
                routing_examples=card.routing_examples,
            )
        except CatalogError:
            raise AutomaticRoutingError(
                "routing candidate card prototype projection is invalid"
            ) from None
        if (
            card.routing_prototype_hash != expected_hash
            or card.routing_prototype_vector_hash != vector_hash(prototype_vector)
        ):
            raise AutomaticRoutingError(
                "routing candidate card prototype projection is stale"
            )
        if not card.routing_examples and (
            card.routing_prototype_hash != card.semantic_hash
            or prototype_vector != card.vector
            or card.routing_prototype_vector_hash != card.vector_hash
        ):
            raise AutomaticRoutingError(
                "empty routing prototype does not equal its base projection"
            )


def prototype_route(
    query: str,
    cards: Sequence[NamespaceCard],
    *,
    embedder: RoutingEmbedder,
    reranker_loader: Callable[[], CrossEncoderReranker],
    route_top_k: int,
    catalog_namespace: str = "buoy-routing-catalog-v1",
    region: str = "",
    snapshot_revision: str = "",
    exclusion_counts: dict[str, int] | None = None,
    exclusion_ids: dict[str, list[str]] | None = None,
    remote_counts: dict[str, int] | None = None,
    read_metrics: dict[str, object] | None = None,
) -> RoutingSelection:
    """Exercise the inactive bounded-prototype candidate route.

    This entry point is deliberately collect-only: descriptor-free cases retain
    the first three candidates and cannot manufacture a confident singleton.
    A future production activation must accept one fully validated packaged
    calibration object rather than loose threshold arguments.
    """

    if route_top_k != DEFAULT_ROUTE_TOP_K:
        raise AutomaticRoutingError(
            f"automatic routing uses exactly {DEFAULT_ROUTE_TOP_K} fallback candidates"
        )
    if not cards:
        raise AutomaticRoutingError("automatic routing requires at least one eligible card")
    _validate_prototype_cards(cards)
    named = named_route(query, cards)
    if len(named) > MAX_ROUTE_TOP_K:
        raise AutomaticRoutingError(
            f"query names {len(named)} corpora; select at most {MAX_ROUTE_TOP_K} with repeated --namespace"
        )
    lexical = lexical_route(query, cards)
    lexical_by_namespace = {
        card.namespace: (rank, count, tokens)
        for rank, (card, count, tokens) in enumerate(lexical, start=1)
    }
    semantic = _semantic_route_by_vector(
        query,
        cards,
        embedder=embedder,
        prototype=True,
    )
    semantic_by_namespace = {
        card.namespace: (rank, score)
        for rank, (card, score) in enumerate(semantic, start=1)
    }
    cards_by_namespace = {card.namespace: card for card in cards}
    named_names = [card.namespace for card in named]
    reranker_margin: float | None = None
    score_by_namespace: dict[str, PrototypeRouteScore] = {}

    if named:
        semantic_names = [card.namespace for card, _score in semantic]
        selected_names = [
            *named_names,
            *(namespace for namespace in semantic_names if namespace not in named_names),
        ]
        if len(named) == 1:
            selected_names = selected_names[:route_top_k]
            initial_fanout = 1
            selection_reason = "unique_title_or_alias"
        else:
            selected_names = named_names
            initial_fanout = len(named_names)
            selection_reason = "multiple_named_corpora"
        high_confidence = True
    else:
        try:
            reranker = reranker_loader()
        except Exception:
            raise AutomaticRoutingError(
                "routing shortlist reranker loading failed"
            ) from None
        scored = _rerank_prototype_shortlist(
            query,
            semantic[:ROUTING_SHORTLIST_LIMIT],
            reranker=reranker,
        )
        score_by_namespace = {item.card.namespace: item for item in scored}
        selected_names = [item.card.namespace for item in scored[:route_top_k]]
        top_score = scored[0].reranker_score
        reranker_margin = (
            top_score - scored[1].reranker_score if len(scored) > 1 else None
        )
        high_confidence = False
        initial_fanout = len(selected_names)
        selection_reason = "ambiguous_prototype"

    if not selected_names:
        raise AutomaticRoutingError("automatic routing produced an empty selected route")
    selected_cards = [cards_by_namespace[namespace] for namespace in selected_names]
    entries: list[RouteEntry] = []
    for route_rank, namespace in enumerate(selected_names, start=1):
        lexical_values = lexical_by_namespace.get(namespace)
        semantic_rank, semantic_score = semantic_by_namespace[namespace]
        prototype = score_by_namespace.get(namespace)
        entries.append(
            RouteEntry(
                namespace=namespace,
                route_rank=route_rank,
                lexical_rank=lexical_values[0] if lexical_values else None,
                lexical_matched_descriptors=lexical_values[1] if lexical_values else 0,
                lexical_matched_token_count=lexical_values[2] if lexical_values else 0,
                semantic_rank=semantic_rank,
                semantic_score=semantic_score,
                hybrid_score=(
                    prototype.reranker_score if prototype is not None else semantic_score
                ),
                exact_name_match=namespace in named_names,
                shortlist_rank=(
                    prototype.shortlist_rank
                    if prototype
                    else semantic_rank
                    if semantic_rank <= ROUTING_SHORTLIST_LIMIT
                    else None
                ),
                shortlist_cosine_score=(
                    prototype.shortlist_cosine_score
                    if prototype
                    else semantic_score
                    if semantic_rank <= ROUTING_SHORTLIST_LIMIT
                    else None
                ),
                reranker_rank=prototype.reranker_rank if prototype else None,
                reranker_score=prototype.reranker_score if prototype else None,
                winning_prototype_kind=(
                    prototype.winning_prototype_kind if prototype else None
                ),
                winning_prototype_index=(
                    prototype.winning_prototype_index if prototype else None
                ),
                winning_prototype_hash=(
                    prototype.winning_prototype_hash if prototype else None
                ),
            )
        )
    top_semantic = semantic[0][1]
    semantic_margin = top_semantic - semantic[1][1] if len(semantic) > 1 else None
    return RoutingSelection(
        catalog_namespace=catalog_namespace,
        region=region,
        snapshot_revision=snapshot_revision,
        requested_limit=route_top_k,
        eligible_count=len(cards),
        exclusion_counts=dict(sorted((exclusion_counts or {}).items())),
        exclusion_ids={
            key: sorted(values) for key, values in sorted((exclusion_ids or {}).items())
        },
        remote_counts=dict(remote_counts or {}),
        read_metrics=dict(read_metrics or {}),
        selected_cards=selected_cards,
        entries=entries,
        initial_fanout=initial_fanout,
        selection_reason=selection_reason,
        high_confidence=high_confidence,
        semantic_margin=semantic_margin,
        strategy=ROUTING_PROTOTYPE_STRATEGY,
        reranker_margin=reranker_margin,
        confidence_score_floor=None,
        confidence_margin_floor=None,
        confidence_calibration_id=ROUTING_CONFIDENCE_ARTIFACT_ID,
        confidence_calibration_revision=ROUTING_CONFIDENCE_COLLECT_REVISION,
    )


def hybrid_route(
    query: str,
    cards: Sequence[NamespaceCard],
    *,
    embedder: RoutingEmbedder,
    route_top_k: int,
    catalog_namespace: str = "buoy-routing-catalog-v1",
    region: str = "",
    snapshot_revision: str | None = None,
    exclusion_counts: dict[str, int] | None = None,
    exclusion_ids: dict[str, list[str]] | None = None,
    remote_counts: dict[str, int] | None = None,
    read_metrics: dict[str, object] | None = None,
    # Internal call compatibility for provider-neutral routing tests; never emitted.
    catalog_path: object = None,
    catalog_revision: str | None = None,
) -> RoutingSelection:
    if route_top_k != DEFAULT_ROUTE_TOP_K:
        raise AutomaticRoutingError(
            f"automatic routing uses exactly {DEFAULT_ROUTE_TOP_K} fallback candidates"
        )
    if not cards:
        raise AutomaticRoutingError("automatic routing requires at least one eligible card")
    lexical = lexical_route(query, cards)
    named = named_route(query, cards)
    if len(named) > MAX_ROUTE_TOP_K:
        raise AutomaticRoutingError(
            f"query names {len(named)} corpora; select at most {MAX_ROUTE_TOP_K} with repeated --namespace"
        )
    semantic = semantic_route(query, cards, embedder=embedder)
    lexical_by_namespace = {
        card.namespace: (rank, count, tokens)
        for rank, (card, count, tokens) in enumerate(lexical, start=1)
    }
    semantic_by_namespace = {
        card.namespace: (rank, score)
        for rank, (card, score) in enumerate(semantic, start=1)
    }
    cards_by_namespace = {card.namespace: card for card in cards}
    fused: list[tuple[str, float]] = []
    for namespace in cards_by_namespace:
        score = 1.0 / (RRF_K + semantic_by_namespace[namespace][0])
        lexical_values = lexical_by_namespace.get(namespace)
        if lexical_values is not None:
            score += 1.0 / (RRF_K + lexical_values[0])
        fused.append((namespace, score))
    fused.sort(key=lambda item: (-item[1], item[0]))
    semantic_names = [card.namespace for card, _score in semantic]
    named_names = [card.namespace for card in named]
    if named:
        selected_names = [
            *named_names,
            *(
                namespace
                for namespace in semantic_names
                if namespace not in named_names
            ),
        ]
        if len(named) == 1:
            selected_names = selected_names[:route_top_k]
            initial_fanout = 1
            selection_reason = "unique_title_or_alias"
            high_confidence = True
        else:
            selected_names = named_names
            initial_fanout = len(named_names)
            selection_reason = "multiple_named_corpora"
            high_confidence = True
    else:
        top_score = semantic[0][1]
        margin = top_score - semantic[1][1] if len(semantic) > 1 else None
        confident = top_score >= SEMANTIC_CONFIDENCE_FLOOR and (
            margin is None or margin >= SEMANTIC_MARGIN_FLOOR
        )
        selected_names = semantic_names[:route_top_k]
        initial_fanout = 1 if confident else len(selected_names)
        selection_reason = "high_confidence_semantic" if confident else "ambiguous_semantic"
        high_confidence = confident
    selected_scores = {namespace: score for namespace, score in fused}
    selected = [(namespace, selected_scores[namespace]) for namespace in selected_names]
    if not selected:
        raise AutomaticRoutingError("automatic routing produced an empty selected route")

    selected_cards = [cards_by_namespace[namespace] for namespace, _score in selected]
    entries: list[RouteEntry] = []
    for route_rank, (namespace, hybrid_score) in enumerate(selected, start=1):
        lexical_values = lexical_by_namespace.get(namespace)
        semantic_rank, semantic_score = semantic_by_namespace[namespace]
        entries.append(
            RouteEntry(
                namespace=namespace,
                route_rank=route_rank,
                lexical_rank=lexical_values[0] if lexical_values else None,
                lexical_matched_descriptors=lexical_values[1] if lexical_values else 0,
                lexical_matched_token_count=lexical_values[2] if lexical_values else 0,
                semantic_rank=semantic_rank,
                semantic_score=semantic_score,
                hybrid_score=hybrid_score,
                exact_name_match=namespace in named_names,
            )
        )
    top_semantic_score = semantic[0][1]
    semantic_margin = (
        top_semantic_score - semantic[1][1] if len(semantic) > 1 else None
    )
    return RoutingSelection(
        catalog_namespace=catalog_namespace,
        region=region,
        snapshot_revision=snapshot_revision or catalog_revision or "",
        requested_limit=route_top_k,
        eligible_count=len(cards),
        exclusion_counts=dict(sorted((exclusion_counts or {}).items())),
        exclusion_ids={
            key: sorted(values)
            for key, values in sorted((exclusion_ids or {}).items())
        },
        remote_counts=dict(remote_counts or {}),
        read_metrics=dict(read_metrics or {}),
        selected_cards=selected_cards,
        entries=entries,
        initial_fanout=initial_fanout,
        selection_reason=selection_reason,
        high_confidence=high_confidence,
        semantic_margin=semantic_margin,
    )


def _validated_query_vector(value: object) -> list[float]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise AutomaticRoutingError("routing model query vector must be a numeric sequence")
    if len(value) != ROUTING_DIMENSIONS:
        raise AutomaticRoutingError(
            f"routing model query vector must contain exactly {ROUTING_DIMENSIONS} numbers"
        )
    vector: list[float] = []
    for index, item in enumerate(value):
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise AutomaticRoutingError(
                f"routing model query vector[{index}] must be a finite number"
            )
        number = float(item)
        if not math.isfinite(number):
            raise AutomaticRoutingError(
                f"routing model query vector[{index}] must be a finite number"
            )
        vector.append(number)
    norm = math.sqrt(sum(item * item for item in vector))
    if norm == 0.0 or abs(norm - 1.0) > 1e-4:
        raise AutomaticRoutingError(
            "routing model query vector must be normalized and non-zero"
        )
    return vector
