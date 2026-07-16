"""Local catalog-backed namespace routing for opt-in retrieval.

Routing is deliberately local-only. Cards are fully validated by the catalog
loader, compatibility is applied before either lexical or semantic scoring,
and persisted card vectors are never returned in ordinary output.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Sequence

from buoy_search.catalog import (
    ROUTING_DIMENSIONS,
    ROUTING_MODEL,
    ROUTING_MODEL_REVISION,
    ROUTING_QUERY_PREFIX,
    CatalogDocument,
    CatalogError,
    NamespaceCard,
    RoutingEmbedder,
    canonical_text,
)
from buoy_search.config import RuntimeConfig
from buoy_search.retriever import (
    RRF_K,
    MultiNamespaceRetrievalPlan,
    MultiNamespaceRetrievalResult,
)

DEFAULT_ROUTE_TOP_K = 3
MAX_ROUTE_TOP_K = 10

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

    def to_dict(self) -> dict[str, object]:
        return {
            "namespace": self.namespace,
            "route_rank": self.route_rank,
            "lexical_rank": self.lexical_rank,
            "lexical_matched_descriptors": self.lexical_matched_descriptors,
            "lexical_matched_token_count": self.lexical_matched_token_count,
            "semantic_rank": self.semantic_rank,
            "semantic_score": self.semantic_score,
            "hybrid_score": self.hybrid_score,
        }


@dataclass(frozen=True)
class RoutingSelection:
    catalog_path: Path
    catalog_revision: str
    requested_limit: int
    eligible_count: int
    exclusion_counts: dict[str, int]
    selected_cards: list[NamespaceCard]
    entries: list[RouteEntry]

    def to_dict(self) -> dict[str, object]:
        return {
            "active": True,
            "strategy": "hybrid_rrf",
            "catalog_path": str(self.catalog_path),
            "catalog_revision": self.catalog_revision,
            "routing_model": ROUTING_MODEL,
            "routing_model_revision": ROUTING_MODEL_REVISION,
            "requested_limit": self.requested_limit,
            "eligible_count": self.eligible_count,
            "exclusion_counts": dict(self.exclusion_counts),
            "selected_cards": [entry.to_dict() for entry in self.entries],
        }


@dataclass(frozen=True)
class RoutedRetrievalPlan:
    plan: MultiNamespaceRetrievalPlan
    routing: RoutingSelection

    def to_dict(self) -> dict[str, object]:
        return {**self.plan.to_dict(), "routing": self.routing.to_dict()}


@dataclass(frozen=True)
class RoutedRetrievalResult:
    result: MultiNamespaceRetrievalResult
    routing: RoutingSelection

    def to_dict(self) -> dict[str, object]:
        return {**self.result.to_dict(), "routing": self.routing.to_dict()}


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


def require_eligible_cards(result: EligibilityResult, *, catalog_path: Path) -> list[NamespaceCard]:
    if result.cards:
        return result.cards
    excluded = ", ".join(
        f"{reason}={count}" for reason, count in sorted(result.exclusion_counts.items())
    ) or "none registered"
    raise CatalogError(
        f"catalog {catalog_path}: no enabled compatible namespace cards ({excluded}); "
        "inspect `buoy catalog list --all`, manually upsert or enable a card, and verify "
        "the region, embedding model, and precision compatibility settings"
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


def semantic_route(
    query: str,
    cards: Sequence[NamespaceCard],
    *,
    embedder: RoutingEmbedder,
) -> list[tuple[NamespaceCard, float]]:
    """Rank persisted card vectors against one pinned local query embedding."""

    cleaned_query = query.strip()
    if not cleaned_query:
        raise AutomaticRoutingError("a non-empty query is required for automatic routing")
    try:
        encoded = embedder.encode([f"{ROUTING_QUERY_PREFIX}{cleaned_query}"])
    except Exception as exc:
        raise AutomaticRoutingError(f"routing query embedding failed: {exc}") from exc
    if len(encoded) != 1:
        raise AutomaticRoutingError("routing model must return exactly one query vector")
    query_vector = _validated_query_vector(encoded[0])
    ranked: list[tuple[NamespaceCard, float]] = []
    for card in cards:
        score = sum(left * right for left, right in zip(query_vector, card.vector, strict=True))
        if not math.isfinite(score):
            raise AutomaticRoutingError(
                f"non-finite semantic score for namespace {card.namespace!r}"
            )
        ranked.append((card, score))
    ranked.sort(key=lambda item: (-item[1], item[0].namespace))
    return ranked


def hybrid_route(
    query: str,
    cards: Sequence[NamespaceCard],
    *,
    embedder: RoutingEmbedder,
    route_top_k: int,
    catalog_path: Path,
    catalog_revision: str,
    exclusion_counts: dict[str, int],
) -> RoutingSelection:
    if route_top_k <= 0 or route_top_k > MAX_ROUTE_TOP_K:
        raise AutomaticRoutingError(
            f"route_top_k must be between 1 and {MAX_ROUTE_TOP_K}"
        )
    lexical = lexical_route(query, cards)
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
    selected = fused[:route_top_k]
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
            )
        )
    return RoutingSelection(
        catalog_path=catalog_path,
        catalog_revision=catalog_revision,
        requested_limit=route_top_k,
        eligible_count=len(cards),
        exclusion_counts=dict(sorted(exclusion_counts.items())),
        selected_cards=selected_cards,
        entries=entries,
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
