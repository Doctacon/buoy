"""Turbopuffer-backed routing catalog with explicit credentials and safe writes.

The public catalog CLI, automatic retrieval, and successful-apply registration
share this module. It never reads credentials, local catalog files, or other
process state; callers resolve and inject the client configuration explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, replace
from functools import wraps
import hashlib
import math
import re
import struct
from typing import Any, Callable, Iterable, Mapping, Protocol, Sequence, TypeVar

from buoy_search.catalog import (
    CatalogError,
    NamespaceCard,
    ROUTING_DIMENSIONS,
    ROUTING_EVIDENCE_VECTOR_FIELD,
    ROUTING_EVIDENCE_VECTOR_HASH_FIELD,
    ROUTING_PASSAGE_FIELD,
    ROUTING_PASSAGE_FIELDS,
    ROUTING_PROTOTYPE_FIELD_ORDER,
    ROUTING_PROTOTYPE_FIELDS,
    card_revision,
    card_to_dict,
    catalog_revision,
    parse_card,
)
from buoy_search.plan_artifacts import PLAN_SCHEMA_VERSION, stable_hash

REMOTE_CATALOG_NAMESPACE = "buoy-routing-catalog-v1"
NAMESPACE_PAGE_SIZE = 1000
CARD_PAGE_SIZE = 100
MAX_PAGES_PER_PASS = 10_000
DISTANCE_METRIC = "cosine_distance"
STRONG_CONSISTENCY = {"level": "strong"}
REMOTE_SCHEMA_V1 = 1
REMOTE_SCHEMA_V2 = 2
REMOTE_SCHEMA_V3 = 3
REMOTE_CARD_ATTRIBUTES_V3 = tuple(field.name for field in fields(NamespaceCard))
REMOTE_CARD_ATTRIBUTES_V2 = tuple(
    name for name in REMOTE_CARD_ATTRIBUTES_V3 if name not in ROUTING_PASSAGE_FIELDS
)
REMOTE_CARD_ATTRIBUTES = tuple(
    name for name in REMOTE_CARD_ATTRIBUTES_V2 if name not in ROUTING_PROTOTYPE_FIELDS
)
REMOTE_CARD_ATTRIBUTES_V1 = REMOTE_CARD_ATTRIBUTES


def _schema(
    type_name: str,
    *,
    filterable: bool,
    ann: bool | Mapping[str, object] | None = None,
) -> dict[str, object]:
    value: dict[str, object] = {"type": type_name, "filterable": filterable}
    if ann is not None:
        value["ann"] = ann
    return value


REMOTE_CATALOG_SCHEMA: dict[str, dict[str, object]] = {
    "vector": _schema(
        f"[{ROUTING_DIMENSIONS}]f32",
        filterable=False,
        ann={"distance_metric": DISTANCE_METRIC},
    ),
    "namespace": _schema("string", filterable=True),
    "enabled": _schema("bool", filterable=True),
    "created_at": _schema("string", filterable=False),
    "updated_at": _schema("string", filterable=False),
    "card_revision": _schema("string", filterable=True),
    "last_plan_id": _schema("string", filterable=False),
    "last_apply_id": _schema("string", filterable=False),
    "source_kind": _schema("string", filterable=False),
    "source_uri": _schema("string", filterable=False),
    "site_id": _schema("string", filterable=False),
    "title": _schema("string", filterable=False),
    "summary": _schema("string", filterable=False),
    "aliases": _schema("[]string", filterable=False),
    "tags": _schema("[]string", filterable=False),
    "semantic_origin": _schema("string", filterable=False),
    "region": _schema("string", filterable=True),
    "embedding_model": _schema("string", filterable=False),
    "embedding_precision": _schema("string", filterable=True),
    "vector_dimensions": _schema("uint", filterable=False),
    "plan_schema_version": _schema("uint", filterable=False),
    "ranking_mode": _schema("string", filterable=False),
    "ranking_profile": _schema("string", filterable=False),
    "ranking_pool": _schema("uint", filterable=False),
    "ranking_aggregation": _schema("string", filterable=False),
    "routing_model": _schema("string", filterable=False),
    "routing_model_revision": _schema("string", filterable=False),
    "semantic_hash": _schema("string", filterable=False),
    "vector_hash": _schema("string", filterable=False),
}
REMOTE_CATALOG_SCHEMA_V2: dict[str, dict[str, object]] = {
    **REMOTE_CATALOG_SCHEMA,
    "routing_examples": _schema("[]string", filterable=False),
    "routing_prototype_hash": _schema("string", filterable=False),
    "routing_prototype_vector": _schema("[]float", filterable=False),
    "routing_prototype_vector_hash": _schema("string", filterable=False),
}
REMOTE_CATALOG_SCHEMA_V3: dict[str, dict[str, object]] = {
    **REMOTE_CATALOG_SCHEMA_V2,
    ROUTING_PASSAGE_FIELD: _schema("[]string", filterable=False),
    ROUTING_EVIDENCE_VECTOR_FIELD: _schema("[]float", filterable=False),
    ROUTING_EVIDENCE_VECTOR_HASH_FIELD: _schema("string", filterable=False),
}
REMOTE_CATALOG_SCHEMA_V2_ADDITIONS: dict[str, dict[str, object]] = {
    name: REMOTE_CATALOG_SCHEMA_V2[name]
    for name in ROUTING_PROTOTYPE_FIELD_ORDER
}
REMOTE_CATALOG_SCHEMA_V1 = REMOTE_CATALOG_SCHEMA
REMOTE_CATALOG_SCHEMA_V3_ADDITIONS: dict[str, dict[str, object]] = {
    name: REMOTE_CATALOG_SCHEMA_V3[name]
    for name in (
        ROUTING_PASSAGE_FIELD,
        ROUTING_EVIDENCE_VECTOR_FIELD,
        ROUTING_EVIDENCE_VECTOR_HASH_FIELD,
    )
}

_SCHEMA_KEYS = {
    "type",
    "filterable",
    "ann",
    "full_text_search",
    "regex",
    "glob",
    "fuzzy",
    "embed",
    "sparse_knn",
}


class RemoteCatalogError(CatalogError):
    """Remote catalog contract, API, or concurrency failure."""


class RemoteCatalogMissingError(RemoteCatalogError):
    """The reserved routing catalog namespace does not exist."""


class NamespaceResource(Protocol):
    def metadata(self, **kwargs: object) -> object: ...

    def query(self, **kwargs: object) -> object: ...

    def write(self, **kwargs: object) -> object: ...


class RemoteClient(Protocol):
    def namespaces(self, **kwargs: object) -> object: ...

    def namespace(self, namespace: str) -> NamespaceResource: ...


@dataclass(frozen=True)
class CompatibilityContract:
    region: str
    embedding_model: str
    embedding_precision: str
    vector_dimensions: int = ROUTING_DIMENSIONS
    plan_schema_version: int = PLAN_SCHEMA_VERSION


@dataclass(frozen=True)
class CatalogCounts:
    listed_total: int
    control_plane_count: int
    content_live_count: int
    card_count: int
    stale_target_count: int
    missing_card_count: int
    disabled_count: int
    incompatible_count: int
    eligible_count: int


@dataclass(frozen=True)
class ReadMetrics:
    namespace_list_pages: int
    metadata_requests: int
    card_query_pages: int
    billing: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class RemoteCatalogSnapshot:
    cards: tuple[NamespaceCard, ...]
    eligible_cards: tuple[NamespaceCard, ...]
    live_namespace_ids: tuple[str, ...]
    missing_card_ids: tuple[str, ...]
    stale_target_ids: tuple[str, ...]
    disabled_ids: tuple[str, ...]
    incompatible_ids: tuple[str, ...]
    snapshot_revision: str
    counts: CatalogCounts
    metrics: ReadMetrics
    catalog_schema_version: int = REMOTE_SCHEMA_V1


@dataclass(frozen=True)
class MutationMetrics:
    write_requests: int = 0
    verification_query_requests: int = 0
    billing: tuple[dict[str, object], ...] = ()


@dataclass(frozen=True)
class MutationResult:
    changed: bool
    card: NamespaceCard | None
    rows_affected: int
    affected_ids: tuple[str, ...]
    metrics: MutationMetrics = field(default_factory=MutationMetrics)


T = TypeVar("T")


def _sanitized_remote_operation(
    phase: str,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Keep every unexpected SDK/response error inside one redacted boundary."""

    def decorate(function: Callable[..., T]) -> Callable[..., T]:
        @wraps(function)
        def wrapped(*args: object, **kwargs: object) -> T:
            try:
                return function(*args, **kwargs)
            except RemoteCatalogError:
                raise
            except Exception as exc:
                raise _remote_error(phase, exc) from None

        return wrapped

    return decorate


def create_client(*, api_key: str, region: str) -> RemoteClient:
    """Construct the SDK client from explicit values without reading environment."""

    try:
        import turbopuffer
    except ImportError as exc:  # pragma: no cover - package dependency.
        raise RemoteCatalogError("turbopuffer is required; run `uv sync` first") from exc
    try:
        return turbopuffer.Turbopuffer(api_key=api_key, region=region)
    except Exception as exc:  # pragma: no cover - constructor is inert in SDK 2.4.
        raise _remote_error("client construction", exc, secrets=(api_key,)) from None


def remote_catalog_resource(client: RemoteClient) -> NamespaceResource:
    """Acquire the one fixed catalog namespace without exposing SDK failures."""

    return _call(
        "namespace resource acquisition",
        lambda: client.namespace(REMOTE_CATALOG_NAMESPACE),
    )


def remote_card_id(namespace: str) -> str:
    _validate_target_namespace(namespace, allow_reserved=True)
    digest = hashlib.sha256(namespace.encode("utf-8")).hexdigest()
    return f"bc_{digest[:61]}"


def _remote_schema(schema_version: int) -> dict[str, dict[str, object]]:
    if schema_version == REMOTE_SCHEMA_V1:
        return REMOTE_CATALOG_SCHEMA
    if schema_version == REMOTE_SCHEMA_V2:
        return REMOTE_CATALOG_SCHEMA_V2
    if schema_version == REMOTE_SCHEMA_V3:
        return REMOTE_CATALOG_SCHEMA_V3
    raise RemoteCatalogError(
        "remote catalog schema version must be "
        f"{REMOTE_SCHEMA_V1}, {REMOTE_SCHEMA_V2}, or {REMOTE_SCHEMA_V3}"
    )


def _remote_card_attributes(schema_version: int) -> tuple[str, ...]:
    _remote_schema(schema_version)
    if schema_version == REMOTE_SCHEMA_V1:
        return REMOTE_CARD_ATTRIBUTES
    if schema_version == REMOTE_SCHEMA_V2:
        return REMOTE_CARD_ATTRIBUTES_V2
    return REMOTE_CARD_ATTRIBUTES_V3


def remote_catalog_schema_fingerprint(schema_version: int) -> str:
    """Return the stable identity of one exact supported remote schema."""

    return stable_hash(_remote_schema(schema_version))


def remote_catalog_projection_sha256(snapshot: RemoteCatalogSnapshot) -> str:
    """Bind the complete vector-inclusive v1 row and live-target projection.

    The projection deliberately excludes the additive prototype values and the
    observed schema version. It therefore remains identical across the v1-to-v2
    schema-only migration while still binding every legacy card field, row ID,
    vector, stale card, and live content namespace. The stored card revision is
    retained, so later example edits are still bound transitively.
    """

    cards = tuple(
        sorted(
            (
                parse_card(card_to_dict(card, include_vector=True))
                for card in snapshot.cards
            ),
            key=lambda card: card.namespace,
        )
    )
    _validate_card_id_collisions(cards)
    return stable_hash(
        {
            "catalog_namespace": REMOTE_CATALOG_NAMESPACE,
            "projection": "remote_catalog_v1_vector_inclusive_v1",
            "live_namespace_ids": list(snapshot.live_namespace_ids),
            "cards": [
                {
                    "id": remote_card_id(card.namespace),
                    **card_to_dict(
                        card,
                        include_vector=True,
                        include_routing_examples=False,
                        include_routing_passages=False,
                    ),
                }
                for card in cards
            ],
        }
    )


def card_to_remote_row(
    card: NamespaceCard,
    *,
    schema_version: int = REMOTE_SCHEMA_V1,
) -> dict[str, object]:
    parsed = parse_card(card_to_dict(card, include_vector=True))
    if schema_version == REMOTE_SCHEMA_V1 and parsed.routing_examples:
        raise RemoteCatalogError(
            "routing_examples requires the explicit reader-first remote catalog "
            "schema-v2 migration; schema-v1 writes cannot add it incidentally"
        )
    if schema_version in {REMOTE_SCHEMA_V1, REMOTE_SCHEMA_V2} and (
        parsed.routing_passages
        or parsed.routing_evidence_vectors
        or parsed.routing_evidence_vectors_hash
    ):
        raise RemoteCatalogError(
            "routing passage evidence requires the explicit reader-first remote catalog "
            "schema-v3 migration; schema-v1/v2 writes cannot add it incidentally"
        )
    payload = card_to_dict(
        parsed,
        include_vector=True,
        include_routing_examples=schema_version >= REMOTE_SCHEMA_V2,
        include_routing_passages=schema_version == REMOTE_SCHEMA_V3,
    )
    _remote_schema(schema_version)
    return {"id": remote_card_id(parsed.namespace), **payload}


def card_from_remote_row(
    row: object,
    *,
    region: str,
    schema_version: int = REMOTE_SCHEMA_V1,
) -> NamespaceCard:
    payload = _call("card row normalization", _plain, row)
    if not isinstance(payload, dict):
        raise RemoteCatalogError("remote card row must be an object")
    row_id = payload.pop("id", None)
    payload.pop("$dist", None)
    payload.pop("dist", None)
    # The provider omits requested attributes whose stored value is null. The
    # two application-nullable lineage fields may always be reconstructed.
    payload.setdefault("last_plan_id", None)
    payload.setdefault("last_apply_id", None)
    reconstruct_prototype = False
    if schema_version in {REMOTE_SCHEMA_V2, REMOTE_SCHEMA_V3}:
        # A row predating the additive bundle has provider-null state for all
        # four attributes. Reconstruct that complete legacy projection, but
        # reject partial backfills because no mixed authority is safe.
        present = set(payload) & ROUTING_PROTOTYPE_FIELDS
        if present and present != ROUTING_PROTOTYPE_FIELDS:
            raise RemoteCatalogError(
                "remote card row has partial routing prototype state "
                f"(present={sorted(present)}, "
                f"missing={sorted(ROUTING_PROTOTYPE_FIELDS - present)})"
            )
        if not present:
            reconstruct_prototype = True
            payload.update(
                {
                    "routing_examples": [],
                    "routing_prototype_hash": payload.get("semantic_hash"),
                    "routing_prototype_vector": [],
                    "routing_prototype_vector_hash": payload.get("vector_hash"),
                }
            )
    if schema_version == REMOTE_SCHEMA_V3:
        # A schema-only v2-to-v3 migration leaves this system-owned bundle null
        # on every pre-existing row. Empty normalization deliberately retains
        # the exact schema-v2 card and prototype revision bytes. Catalog parsing
        # permits that pair only when no source passages require an exact bank.
        if payload.get(ROUTING_PASSAGE_FIELD) is None:
            payload[ROUTING_PASSAGE_FIELD] = []
        if (
            payload.get(ROUTING_EVIDENCE_VECTOR_FIELD) is None
            and payload.get(ROUTING_EVIDENCE_VECTOR_HASH_FIELD) is None
        ):
            payload[ROUTING_EVIDENCE_VECTOR_FIELD] = []
            payload[ROUTING_EVIDENCE_VECTOR_HASH_FIELD] = ""
    expected_attributes = set(_remote_card_attributes(schema_version))
    if set(payload) != expected_attributes:
        unknown = sorted(set(payload) - expected_attributes)
        missing = sorted(expected_attributes - set(payload))
        detail = []
        if unknown:
            detail.append(f"unknown={unknown}")
        if missing:
            detail.append(f"missing={missing}")
        raise RemoteCatalogError(f"remote card row fields are invalid ({'; '.join(detail)})")
    vector = payload["vector"]
    if isinstance(vector, list):
        canonical_vector: list[float] = []
        for index, item in enumerate(vector):
            if isinstance(item, bool) or not isinstance(item, (int, float)):
                raise RemoteCatalogError(
                    f"remote card field vector[{index}] must be a finite float32 number"
                )
            try:
                number = float(item)
                if not math.isfinite(number):
                    raise ValueError
                number = struct.unpack("!f", struct.pack("!f", number))[0]
            except (OverflowError, struct.error, ValueError):
                raise RemoteCatalogError(
                    f"remote card field vector[{index}] must be a finite float32 number"
                ) from None
            canonical_vector.append(number)
        payload["vector"] = canonical_vector
    if reconstruct_prototype:
        payload["routing_prototype_vector"] = list(payload.get("vector", []))
    prototype_vector = payload.get("routing_prototype_vector")
    if isinstance(prototype_vector, list):
        canonical_prototype_vector: list[float] = []
        for index, item in enumerate(prototype_vector):
            if isinstance(item, bool) or not isinstance(item, (int, float)):
                raise RemoteCatalogError(
                    "remote card field routing_prototype_vector"
                    f"[{index}] must be a finite number"
                )
            number = float(item)
            if not math.isfinite(number):
                raise RemoteCatalogError(
                    "remote card field routing_prototype_vector"
                    f"[{index}] must be a finite number"
                )
            canonical_prototype_vector.append(number)
        payload["routing_prototype_vector"] = canonical_prototype_vector
    try:
        card = parse_card(payload)
    except CatalogError as exc:
        raise RemoteCatalogError(f"remote card is invalid: {exc}") from exc
    expected_id = remote_card_id(card.namespace)
    if row_id != expected_id:
        raise RemoteCatalogError(
            f"remote card ID mismatch for namespace {card.namespace!r}: expected {expected_id!r}"
        )
    _validate_target_namespace(card.namespace, allow_reserved=False)
    if card.region != region:
        raise RemoteCatalogError(
            f"remote card {card.namespace!r} region {card.region!r} does not match catalog region {region!r}"
        )
    return card


def normalize_remote_schema(metadata: object) -> dict[str, dict[str, object]]:
    value = _call("metadata response normalization", _plain, metadata)
    schema_value = value.get("schema") if isinstance(value, dict) else None
    if not isinstance(schema_value, dict):
        raise RemoteCatalogError("remote catalog metadata is missing schema")
    schema: dict[str, dict[str, object]] = {}
    for name, raw in schema_value.items():
        config = _plain(raw)
        if isinstance(config, str):
            config = {"type": config}
        if not isinstance(name, str) or not isinstance(config, dict):
            raise RemoteCatalogError("remote catalog schema contains an invalid attribute")
        unknown = set(config) - _SCHEMA_KEYS
        if unknown:
            raise RemoteCatalogError(
                f"remote catalog schema attribute {name!r} has unknown config: {sorted(unknown)}"
            )
        type_name = config.get("type")
        if not isinstance(type_name, str):
            raise RemoteCatalogError(f"remote catalog schema attribute {name!r} has no valid type")
        default_filterable = not (
            name == "vector" and type_name == f"[{ROUTING_DIMENSIONS}]f32"
        )
        normalized: dict[str, object] = {
            "type": type_name,
            "filterable": config.get("filterable", default_filterable),
        }
        for flag in ("full_text_search", "regex", "glob", "fuzzy", "sparse_knn"):
            if config.get(flag) not in (None, False):
                normalized[flag] = config[flag]
        if config.get("embed") is not None:
            normalized["embed"] = config["embed"]
        ann = config.get("ann")
        if ann is True:
            normalized["ann"] = {"distance_metric": DISTANCE_METRIC}
        elif ann in (None, False):
            pass
        else:
            ann_value = _plain(ann)
            if not isinstance(ann_value, dict):
                raise RemoteCatalogError(f"remote catalog schema attribute {name!r} has invalid ANN config")
            normalized["ann"] = ann_value
        schema[name] = normalized
    return schema


def validate_remote_schema(metadata: object) -> dict[str, dict[str, object]]:
    schema = normalize_remote_schema(metadata)
    implicit_id = schema.pop("id", None)
    if implicit_id != {"type": "string", "filterable": True}:
        raise RemoteCatalogError("remote catalog implicit id schema must be filterable string")
    if schema not in (
        REMOTE_CATALOG_SCHEMA,
        REMOTE_CATALOG_SCHEMA_V2,
        REMOTE_CATALOG_SCHEMA_V3,
    ):
        expected = (
            REMOTE_CATALOG_SCHEMA_V3
            if set(schema) & ROUTING_PASSAGE_FIELDS
            else REMOTE_CATALOG_SCHEMA_V2
            if "routing_examples" in schema
            else REMOTE_CATALOG_SCHEMA
        )
        missing = sorted(set(expected) - set(schema))
        extra = sorted(set(schema) - set(expected))
        changed = sorted(
            name
            for name in set(schema) & set(expected)
            if schema[name] != expected[name]
        )
        raise RemoteCatalogError(
            f"remote catalog schema mismatch (missing={missing}, extra={extra}, changed={changed})"
        )
    return schema


@_sanitized_remote_operation("catalog read processing")
def read_remote_catalog(
    client: RemoteClient,
    *,
    region: str,
    compatibility: CompatibilityContract,
) -> RemoteCatalogSnapshot:
    first_ids, first_pages = _list_namespaces(client)
    if REMOTE_CATALOG_NAMESPACE not in first_ids:
        raise RemoteCatalogMissingError(
            f"remote catalog namespace {REMOTE_CATALOG_NAMESPACE!r} does not exist in region {region!r}"
        )
    resource = remote_catalog_resource(client)
    metadata = _call("metadata read", lambda: resource.metadata())
    schema = validate_remote_schema(metadata)
    schema_version = (
        REMOTE_SCHEMA_V3
        if schema == REMOTE_CATALOG_SCHEMA_V3
        else REMOTE_SCHEMA_V2
        if schema == REMOTE_CATALOG_SCHEMA_V2
        else REMOTE_SCHEMA_V1
    )
    first_cards, first_card_pages, first_billing = _read_card_pass(
        resource, region=region, schema_version=schema_version
    )
    second_cards, second_card_pages, second_billing = _read_card_pass(
        resource, region=region, schema_version=schema_version
    )
    first_identity = [(card.namespace, card.card_revision) for card in first_cards]
    second_identity = [(card.namespace, card.card_revision) for card in second_cards]
    first_revision = catalog_revision(first_cards)
    second_revision = catalog_revision(second_cards)
    if first_identity != second_identity or first_revision != second_revision:
        raise RemoteCatalogError("remote catalog changed between strong-consistency read passes")
    second_ids, second_pages = _list_namespaces(client)
    if first_ids != second_ids:
        raise RemoteCatalogError("remote namespace listing changed between read passes")
    return classify_remote_catalog(
        live_namespace_ids=first_ids,
        cards=first_cards,
        compatibility=compatibility,
        metrics=ReadMetrics(
            namespace_list_pages=first_pages + second_pages,
            metadata_requests=1,
            card_query_pages=first_card_pages + second_card_pages,
            billing=tuple([*first_billing, *second_billing]),
        ),
        catalog_schema_version=schema_version,
    )


def require_eligible(snapshot: RemoteCatalogSnapshot) -> RemoteCatalogSnapshot:
    """Require at least one card for routing while preserving generic management reads."""

    if snapshot.counts.eligible_count == 0:
        raise RemoteCatalogError(
            "no eligible live remote namespace cards; run `buoy catalog list --all` to inspect "
            "missing, stale, disabled, and incompatible cards"
        )
    return snapshot


def require_complete_routing_coverage(
    snapshot: RemoteCatalogSnapshot,
) -> RemoteCatalogSnapshot:
    """Require one compatible card for every live content namespace.

    Disabled cards are intentional coverage and stale cards do not block an
    otherwise complete live inventory. Automatic routing calls this gate before
    scoring so it cannot silently ignore an unregistered or incompatible live
    corpus.
    """

    problems: list[str] = []
    if snapshot.missing_card_ids:
        missing = ", ".join(repr(value) for value in snapshot.missing_card_ids)
        repairs = "; ".join(
            f"buoy catalog upsert {value} ... --approve"
            for value in snapshot.missing_card_ids
        )
        problems.append(f"missing cards: {missing} (repair with reviewed {repairs})")
    if snapshot.incompatible_ids:
        incompatible = ", ".join(repr(value) for value in snapshot.incompatible_ids)
        repairs = "; ".join(
            f"buoy catalog show {value} --json, then reviewed buoy catalog upsert {value} ... --approve"
            for value in snapshot.incompatible_ids
        )
        problems.append(
            f"incompatible cards: {incompatible} (inspect and repair with {repairs})"
        )
    if problems:
        raise RemoteCatalogError(
            "automatic routing requires complete live namespace-card coverage; "
            + "; ".join(problems)
        )
    return snapshot


def classify_remote_catalog(
    *,
    live_namespace_ids: Sequence[str],
    cards: Sequence[NamespaceCard],
    compatibility: CompatibilityContract,
    metrics: ReadMetrics | None = None,
    catalog_schema_version: int = REMOTE_SCHEMA_V1,
) -> RemoteCatalogSnapshot:
    _remote_schema(catalog_schema_version)
    listed = tuple(sorted(live_namespace_ids))
    if len(listed) != len(set(listed)):
        raise RemoteCatalogError("remote namespace listing contains duplicate IDs")
    ordered_cards = tuple(sorted((parse_card(card_to_dict(card, include_vector=True)) for card in cards), key=lambda c: c.namespace))
    card_ids = [card.namespace for card in ordered_cards]
    if len(card_ids) != len(set(card_ids)):
        raise RemoteCatalogError("remote catalog contains duplicate target namespaces")
    for card in ordered_cards:
        _validate_target_namespace(card.namespace, allow_reserved=False)
    _validate_card_id_collisions(ordered_cards)
    internal_evidence = {
        namespace for namespace in listed if namespace.startswith("buoy-evidence-")
    }
    content_live = set(listed) - {REMOTE_CATALOG_NAMESPACE} - internal_evidence
    card_by_namespace = {card.namespace: card for card in ordered_cards}
    stale = tuple(sorted(set(card_by_namespace) - content_live))
    missing = tuple(sorted(content_live - set(card_by_namespace)))
    disabled: list[str] = []
    incompatible: list[str] = []
    eligible: list[NamespaceCard] = []
    for namespace in sorted(content_live & set(card_by_namespace)):
        card = card_by_namespace[namespace]
        if not card.enabled:
            disabled.append(namespace)
        elif not _compatible(card, compatibility):
            incompatible.append(namespace)
        else:
            eligible.append(card)
    counts = CatalogCounts(
        listed_total=len(listed),
        control_plane_count=(
            int(REMOTE_CATALOG_NAMESPACE in listed) + len(internal_evidence)
        ),
        content_live_count=len(content_live),
        card_count=len(ordered_cards),
        stale_target_count=len(stale),
        missing_card_count=len(missing),
        disabled_count=len(disabled),
        incompatible_count=len(incompatible),
        eligible_count=len(eligible),
    )
    return RemoteCatalogSnapshot(
        cards=ordered_cards,
        eligible_cards=tuple(eligible),
        live_namespace_ids=tuple(sorted(content_live)),
        missing_card_ids=missing,
        stale_target_ids=stale,
        disabled_ids=tuple(disabled),
        incompatible_ids=tuple(incompatible),
        snapshot_revision=catalog_revision(ordered_cards),
        counts=counts,
        metrics=metrics or ReadMetrics(0, 0, 0, ()),
        catalog_schema_version=catalog_schema_version,
    )


@_sanitized_remote_operation("schema migration processing")
def migrate_remote_catalog_schema_v2(
    resource: NamespaceResource,
) -> MutationResult:
    """Add the exact inert prototype bundle in one schema-only write.

    Callers must establish and bind an exact v1 strong-read snapshot before
    exposing this primitive. No rows, conditions, deletes, or prototype values
    are sent by this function.
    """

    response = _call(
        "schema migration write",
        lambda: resource.write(
            distance_metric=DISTANCE_METRIC,
            schema=REMOTE_CATALOG_SCHEMA_V2,
        ),
    )
    _validate_schema_only_write_result(response)
    return MutationResult(
        changed=True,
        card=None,
        rows_affected=0,
        affected_ids=(),
        metrics=MutationMetrics(
            write_requests=1,
            verification_query_requests=0,
            billing=_response_billing(response),
        ),
    )


@_sanitized_remote_operation("schema-v3 migration processing")
def migrate_remote_catalog_schema_v3(
    resource: NamespaceResource,
) -> MutationResult:
    """Add the system-owned passage/vector/hash bundle in one schema-only write."""

    response = _call(
        "schema-v3 migration write",
        lambda: resource.write(
            distance_metric=DISTANCE_METRIC,
            schema=REMOTE_CATALOG_SCHEMA_V3,
        ),
    )
    _validate_schema_only_write_result(response)
    return MutationResult(
        changed=True,
        card=None,
        rows_affected=0,
        affected_ids=(),
        metrics=MutationMetrics(
            write_requests=1,
            verification_query_requests=0,
            billing=_response_billing(response),
        ),
    )


@_sanitized_remote_operation("card create processing")
def create_remote_cards(
    resource: NamespaceResource,
    cards: Sequence[NamespaceCard],
    *,
    region: str,
    schema_version: int = REMOTE_SCHEMA_V1,
) -> MutationResult:
    schema = _remote_schema(schema_version)
    ordered = tuple(sorted((parse_card(card_to_dict(card, include_vector=True)) for card in cards), key=lambda c: c.namespace))
    if not ordered:
        raise RemoteCatalogError("remote card create requires at least one card")
    _validate_mutation_cards(ordered, region=region)
    rows = [card_to_remote_row(card, schema_version=schema_version) for card in ordered]
    response = _call(
        "conditional card create",
        lambda: resource.write(
            distance_metric=DISTANCE_METRIC,
            schema=schema,
            upsert_rows=rows,
            upsert_condition=("id", "Eq", None),
            return_affected_ids=True,
        ),
    )
    affected, affected_ids = _write_result(response, kind="upserted")
    expected_ids = tuple(row["id"] for row in rows)
    billing = _response_billing(response)
    verification_billing: list[dict[str, object]] = []
    metrics = MutationMetrics(1, len(expected_ids) * 2, ())
    if affected == 0:
        current = _read_exact_cards_twice(
            resource, expected_ids, region=region, schema_version=schema_version,
            billing=verification_billing,
        )
        metrics = replace(metrics, billing=tuple([*billing, *verification_billing]))
        if _same_cards(current, ordered):
            return MutationResult(False, ordered[0] if len(ordered) == 1 else None, 0, (), metrics)
        raise RemoteCatalogError("conditional card create conflicted with existing remote state")
    if affected != len(expected_ids) or tuple(sorted(affected_ids)) != tuple(sorted(expected_ids)):
        # Strong read makes any partial race observable for the next migration attempt.
        _read_exact_cards_twice(
            resource, expected_ids, region=region, allow_missing=True,
            schema_version=schema_version, billing=verification_billing,
        )
        raise RemoteCatalogError(
            f"conditional card create affected unexpected IDs: expected {sorted(expected_ids)}, got {sorted(affected_ids)}"
        )
    current = _read_exact_cards_twice(
        resource, expected_ids, region=region, schema_version=schema_version,
        billing=verification_billing,
    )
    if not _same_cards(current, ordered):
        raise RemoteCatalogError("remote card create verification did not match intended cards")
    metrics = replace(metrics, billing=tuple([*billing, *verification_billing]))
    return MutationResult(
        True, ordered[0] if len(ordered) == 1 else None, affected,
        tuple(affected_ids), metrics,
    )


@_sanitized_remote_operation("card update processing")
def update_remote_card(
    resource: NamespaceResource,
    card: NamespaceCard,
    *,
    expected_revision: str,
    region: str,
    schema_version: int = REMOTE_SCHEMA_V1,
) -> MutationResult:
    schema = _remote_schema(schema_version)
    parsed = parse_card(card_to_dict(card, include_vector=True))
    _validate_mutation_cards((parsed,), region=region)
    if not isinstance(expected_revision, str) or not expected_revision:
        raise RemoteCatalogError("expected card revision must be a non-empty string")
    expected_id = remote_card_id(parsed.namespace)
    response = _call(
        "conditional card update",
        lambda: resource.write(
            distance_metric=DISTANCE_METRIC,
            schema=schema,
            upsert_rows=[card_to_remote_row(parsed, schema_version=schema_version)],
            upsert_condition=("card_revision", "Eq", expected_revision),
            return_affected_ids=True,
        ),
    )
    affected, ids = _write_result(response, kind="upserted")
    verification_billing: list[dict[str, object]] = []
    current = _read_exact_cards_twice(
        resource, [expected_id], region=region, allow_missing=True,
        schema_version=schema_version, billing=verification_billing,
    )
    metrics = MutationMetrics(
        1, 2, tuple([*_response_billing(response), *verification_billing])
    )
    if affected == 0:
        if len(current) == 1 and current[0].card_revision == parsed.card_revision:
            return MutationResult(False, current[0], 0, (), metrics)
        raise RemoteCatalogError("conditional card update conflicted with a newer remote revision")
    if affected != 1 or ids != [expected_id] or len(current) != 1 or current[0].card_revision != parsed.card_revision:
        raise RemoteCatalogError("remote card update affected or verified an unexpected row")
    return MutationResult(True, current[0], 1, (expected_id,), metrics)


def redact_remote_error(value: object) -> str:
    """Return a bounded class/status summary without inspecting provider payload text."""

    if isinstance(value, BaseException):
        return _safe_exception_summary(value)
    return "<redacted provider payload>"


def _namespace_page_cursor(page: object) -> str | None:
    cursor: object = None
    if isinstance(page, Mapping):
        cursor = page.get("next_cursor")
    elif hasattr(page, "next_cursor"):
        cursor = getattr(page, "next_cursor")
    if cursor is None:
        info = getattr(page, "next_page_info", None)
        if callable(info):
            value = _plain(info())
            if isinstance(value, dict):
                cursor = value.get("cursor") or value.get("next_cursor")
    if cursor is None:
        return None
    if not isinstance(cursor, str) or not cursor:
        raise RemoteCatalogError("namespace listing returned an invalid page cursor")
    return cursor


def _list_namespaces(client: RemoteClient) -> tuple[tuple[str, ...], int]:
    page = _call(
        "namespace listing",
        lambda: client.namespaces(page_size=NAMESPACE_PAGE_SIZE),
    )
    pages = 0
    values: list[str] = []
    seen_ids: set[str] = set()
    seen_signatures: set[tuple[tuple[str, ...], str | None]] = set()
    seen_cursors: set[str] = set()
    while True:
        if pages >= MAX_PAGES_PER_PASS:
            raise RemoteCatalogError(
                f"namespace listing exceeded {MAX_PAGES_PER_PASS} pages in one pass"
            )
        pages += 1
        def page_items() -> object:
            if isinstance(page, Mapping) and "namespaces" in page:
                return page["namespaces"]
            marker = object()
            value = getattr(page, "namespaces", marker)
            # Plain iterables are accepted for simple injected clients and count as one page.
            return page if value is marker else value

        items = _call("namespace listing page normalization", page_items)
        try:
            batch = _call("namespace listing page iteration", lambda: list(items))
        except RemoteCatalogError as exc:
            raise RemoteCatalogError("namespace listing response is not iterable") from exc
        for summary in batch:
            plain = _call("namespace summary normalization", _plain, summary)
            value = plain.get("id") if isinstance(plain, dict) else None
            if not isinstance(value, str) or not value:
                raise RemoteCatalogError("namespace listing returned an invalid ID")
            if value in seen_ids:
                raise RemoteCatalogError(f"namespace listing repeated ID {value!r} during pagination")
            seen_ids.add(value)
            values.append(value)
        cursor = _call(
            "namespace pagination state normalization",
            _namespace_page_cursor,
            page,
        )
        signature = (tuple(values[-len(batch):]) if batch else (), cursor)
        if signature in seen_signatures:
            raise RemoteCatalogError("namespace listing repeated a page cursor/signature")
        seen_signatures.add(signature)
        if cursor is not None:
            if cursor in seen_cursors:
                raise RemoteCatalogError("namespace listing repeated a page cursor/signature")
            seen_cursors.add(cursor)
        has_next = _call(
            "namespace pagination method lookup",
            lambda: getattr(page, "has_next_page", None),
        )
        if not callable(has_next) or not _call(
            "namespace pagination state read", has_next
        ):
            break
        if not batch:
            raise RemoteCatalogError("namespace listing pagination did not advance")
        getter = _call(
            "namespace pagination method lookup",
            lambda: getattr(page, "get_next_page", None),
        )
        if not callable(getter):
            raise RemoteCatalogError("namespace listing advertised a next page without a getter")
        page = _call("namespace listing pagination", getter)
    return tuple(sorted(values)), pages


def _read_card_pass(
    resource: NamespaceResource,
    *,
    region: str,
    schema_version: int,
) -> tuple[tuple[NamespaceCard, ...], int, tuple[dict[str, object], ...]]:
    attributes = _remote_card_attributes(schema_version)
    cards: list[NamespaceCard] = []
    seen_row_ids: set[str] = set()
    last_id: str | None = None
    pages = 0
    billing: list[dict[str, object]] = []
    seen_page_signatures: set[tuple[str, ...]] = set()
    while True:
        if pages >= MAX_PAGES_PER_PASS:
            raise RemoteCatalogError(
                f"remote card query exceeded {MAX_PAGES_PER_PASS} pages in one pass"
            )
        kwargs: dict[str, object] = {
            "rank_by": ("id", "asc"),
            "top_k": CARD_PAGE_SIZE,
            "include_attributes": list(attributes),
            "vector_encoding": "float",
            "consistency": dict(STRONG_CONSISTENCY),
        }
        if last_id is not None:
            kwargs["filters"] = ("id", "Gt", last_id)
        response = _call(
            "card page query",
            lambda: resource.query(**kwargs),
        )
        pages += 1
        plain = _call("card page response normalization", _plain, response)
        rows_value = plain.get("rows") if isinstance(plain, dict) else None
        rows = (
            []
            if rows_value is None
            else _call("card page row iteration", lambda: list(rows_value))
        )
        if len(rows) > CARD_PAGE_SIZE:
            raise RemoteCatalogError("remote card query returned more rows than requested")
        page_ids: list[str] = []
        for row in rows:
            row_plain = _call("card row normalization", _plain, row)
            row_id = row_plain.get("id") if isinstance(row_plain, dict) else None
            if not isinstance(row_id, str) or not row_id:
                raise RemoteCatalogError("remote card query returned an invalid row ID")
            page_ids.append(row_id)
            if row_id in seen_row_ids:
                raise RemoteCatalogError("remote card pagination repeated a row ID")
            seen_row_ids.add(row_id)
            cards.append(
                card_from_remote_row(
                    row_plain, region=region, schema_version=schema_version
                )
            )
        page_signature = tuple(page_ids)
        if page_signature in seen_page_signatures:
            raise RemoteCatalogError("remote card pagination repeated a page signature")
        seen_page_signatures.add(page_signature)
        if page_ids != sorted(page_ids) or any(
            page_ids[index] <= page_ids[index - 1] for index in range(1, len(page_ids))
        ):
            raise RemoteCatalogError("remote card page IDs are not strictly increasing")
        if last_id is not None and page_ids and page_ids[0] <= last_id:
            raise RemoteCatalogError("remote card pagination did not advance")
        bill = plain.get("billing") if isinstance(plain, dict) else None
        if bill is not None:
            billing.append(_safe_billing(bill))
        if len(rows) < CARD_PAGE_SIZE:
            break
        if not page_ids or page_ids[-1] == last_id:
            raise RemoteCatalogError("remote card pagination did not advance")
        last_id = page_ids[-1]
    ordered = tuple(sorted(cards, key=lambda card: card.namespace))
    if len({card.namespace for card in ordered}) != len(ordered):
        raise RemoteCatalogError("remote catalog contains duplicate target namespaces")
    return ordered, pages, tuple(billing)


def _read_exact_cards_twice(
    resource: NamespaceResource,
    row_ids: Sequence[str],
    *,
    region: str,
    schema_version: int = REMOTE_SCHEMA_V1,
    allow_missing: bool = False,
    preserve_single_reads: bool = False,
    billing: list[dict[str, object]] | None = None,
) -> tuple[NamespaceCard, ...]:
    attributes = _remote_card_attributes(schema_version)
    expected = tuple(sorted(row_ids))
    passes: list[tuple[NamespaceCard, ...]] = []
    for _ in range(2):
        rows: list[NamespaceCard] = []
        for row_id in expected:
            response = _call(
                "card verification query",
                lambda: resource.query(
                    rank_by=("id", "asc"),
                    top_k=2,
                    filters=("id", "Eq", row_id),
                    include_attributes=list(attributes),
                    vector_encoding="float",
                    consistency=dict(STRONG_CONSISTENCY),
                ),
            )
            plain = _call("card verification response normalization", _plain, response)
            if billing is not None:
                bill = plain.get("billing") if isinstance(plain, dict) else None
                if bill is not None:
                    billing.append(_safe_billing(bill))
            raw_rows = plain.get("rows") if isinstance(plain, dict) else None
            values = (
                []
                if raw_rows is None
                else _call("card verification row iteration", lambda: list(raw_rows))
            )
            if len(values) > 1:
                raise RemoteCatalogError("card verification returned duplicate row IDs")
            if values:
                card = card_from_remote_row(
                    values[0], region=region, schema_version=schema_version
                )
                if remote_card_id(card.namespace) != row_id:
                    raise RemoteCatalogError("card verification returned an unexpected row")
                rows.append(card)
            elif not allow_missing:
                raise RemoteCatalogError(f"card verification did not find expected row {row_id!r}")
        passes.append(tuple(sorted(rows, key=lambda card: card.namespace)))
    if not preserve_single_reads and [
        card_to_dict(card, include_vector=True) for card in passes[0]
    ] != [card_to_dict(card, include_vector=True) for card in passes[1]]:
        raise RemoteCatalogError("card verification changed between strong read passes")
    if preserve_single_reads:
        if any(len(current_pass) > 1 for current_pass in passes):
            raise RemoteCatalogError("single-card verification returned multiple cards")
        return tuple(current_pass[0] for current_pass in passes if current_pass)
    return passes[0]


def _compatible(card: NamespaceCard, compatibility: CompatibilityContract) -> bool:
    return (
        card.region == compatibility.region
        and card.embedding_model == compatibility.embedding_model
        and card.embedding_precision == compatibility.embedding_precision
        and card.vector_dimensions == compatibility.vector_dimensions
        and card.plan_schema_version in {1, 2, compatibility.plan_schema_version}
    )


def _same_cards(actual: Sequence[NamespaceCard], expected: Sequence[NamespaceCard]) -> bool:
    return [card_to_dict(card, include_vector=True) for card in actual] == [
        card_to_dict(card, include_vector=True) for card in expected
    ]


def _validate_target_namespace(namespace: object, *, allow_reserved: bool) -> str:
    if not isinstance(namespace, str) or re.fullmatch(r"[A-Za-z0-9-_.]{1,128}", namespace) is None:
        raise RemoteCatalogError("target namespace must match [A-Za-z0-9-_.]{1,128}")
    if not allow_reserved and namespace == REMOTE_CATALOG_NAMESPACE:
        raise RemoteCatalogError("reserved routing catalog namespace cannot be a target card")
    if not allow_reserved and namespace.startswith("buoy-evidence-"):
        raise RemoteCatalogError("reserved evidence namespace cannot be a target card")
    return namespace


def _validate_mutation_cards(cards: Sequence[NamespaceCard], *, region: str) -> None:
    if not isinstance(region, str) or not region:
        raise RemoteCatalogError("resolved region must be a non-empty string")
    namespaces: set[str] = set()
    for card in cards:
        _validate_target_namespace(card.namespace, allow_reserved=False)
        if card.namespace in namespaces:
            raise RemoteCatalogError(f"duplicate target namespace {card.namespace!r} in mutation")
        namespaces.add(card.namespace)
        if card.region != region:
            raise RemoteCatalogError(
                f"card {card.namespace!r} region {card.region!r} does not match resolved region {region!r}"
            )
    _validate_card_id_collisions(cards)


def _validate_card_id_collisions(cards: Sequence[NamespaceCard]) -> None:
    by_id: dict[str, str] = {}
    for card in cards:
        row_id = remote_card_id(card.namespace)
        previous = by_id.get(row_id)
        if previous is not None and previous != card.namespace:
            raise RemoteCatalogError(
                f"remote card ID collision between namespaces {previous!r} and {card.namespace!r}"
            )
        by_id[row_id] = card.namespace


def _write_result(response: object, *, kind: str) -> tuple[int, list[str]]:
    plain = _call("card write response normalization", _plain, response)
    if not isinstance(plain, dict):
        raise RemoteCatalogError("remote write returned an invalid response")
    affected = plain.get("rows_affected")
    if type(affected) is not int or affected < 0:
        raise RemoteCatalogError("remote write returned invalid rows_affected")
    key = f"{kind}_ids"
    raw_ids = plain.get(key)
    ids = [] if raw_ids is None else list(raw_ids)
    if any(not isinstance(value, str) for value in ids):
        raise RemoteCatalogError(f"remote write returned invalid {key}")
    return affected, ids


def _validate_schema_only_write_result(response: object) -> None:
    plain = _call("schema write response normalization", _plain, response)
    if not isinstance(plain, dict):
        raise RemoteCatalogError("remote schema write returned an invalid response")
    affected = plain.get("rows_affected")
    if type(affected) is not int or affected != 0:
        raise RemoteCatalogError("remote schema write unexpectedly affected rows")
    status = plain.get("status")
    if status != "OK":
        raise RemoteCatalogError("remote schema write returned an invalid status")
    if plain.get("rows_remaining") not in (None, False):
        raise RemoteCatalogError("remote schema write unexpectedly reported remaining rows")
    for key in ("rows_deleted", "rows_patched", "rows_upserted"):
        if plain.get(key) not in (None, 0):
            raise RemoteCatalogError("remote schema write unexpectedly reported row mutation")
    for key in ("deleted_ids", "patched_ids", "upserted_ids"):
        if plain.get(key) not in (None, []):
            raise RemoteCatalogError("remote schema write unexpectedly reported affected IDs")


def _response_billing(response: object) -> tuple[dict[str, object], ...]:
    plain = _call("card write billing normalization", _plain, response)
    bill = plain.get("billing") if isinstance(plain, dict) else None
    return (_safe_billing(bill),) if bill is not None else ()


def _safe_billing(value: object) -> dict[str, object]:
    plain = _call("billing response normalization", _plain, value)
    if not isinstance(plain, dict):
        return {"summary": redact_remote_error(value)}
    safe: dict[str, object] = {}
    for key, item in plain.items():
        if isinstance(key, str) and isinstance(item, (int, float, bool, type(None))):
            safe[key[:80]] = item
    return safe


def _plain(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    for method_name in ("to_dict", "model_dump"):
        method = getattr(value, method_name, None)
        if callable(method):
            return _plain(method())
    if hasattr(value, "__dict__"):
        return {
            key: _plain(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    return value


def _safe_exception_summary(exc: BaseException) -> str:
    class_name = re.sub(r"[^A-Za-z0-9_.-]", "_", type(exc).__name__)[:80]
    try:
        status = getattr(exc, "status_code", None)
    except Exception:
        status = None
    status_text = f", status={status}" if type(status) is int else ""
    category = ", timeout" if isinstance(exc, TimeoutError) or "timeout" in class_name.casefold() else ""
    return f"{class_name}{status_text}{category}"


def _remote_error(
    phase: str,
    exc: BaseException,
    *,
    secrets: Sequence[str] = (),
) -> RemoteCatalogError:
    del secrets  # Provider exception payloads are never inspected, so secret values are unnecessary.
    return RemoteCatalogError(
        f"remote routing catalog {phase} failed ({_safe_exception_summary(exc)})"
    )


def _call(phase: str, function: Callable[..., T], *args: object, **kwargs: object) -> T:
    try:
        return function(*args, **kwargs)
    except RemoteCatalogError:
        raise
    except Exception as exc:
        raise _remote_error(phase, exc) from None
