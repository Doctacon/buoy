"""Inert remote Turbopuffer routing-catalog backend.

This module has no public CLI/apply/retrieve integration. Callers inject a client
or explicitly construct one with :func:`create_client`; it never reads process
credentials, local catalog files, or other state.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, replace
import hashlib
import math
import re
import struct
from typing import Any, Callable, Iterable, Mapping, Protocol, Sequence, TypeVar

from buoy_search.catalog import (
    CardFields,
    CatalogError,
    NamespaceCard,
    ROUTING_DIMENSIONS,
    RoutingEmbedder,
    card_revision,
    card_to_dict,
    catalog_revision,
    merge_system_card,
    parse_card,
    prepare_card,
)

REMOTE_CATALOG_NAMESPACE = "buoy-routing-catalog-v1"
NAMESPACE_PAGE_SIZE = 1000
CARD_PAGE_SIZE = 100
MAX_PAGES_PER_PASS = 10_000
DISTANCE_METRIC = "cosine_distance"
STRONG_CONSISTENCY = {"level": "strong"}
REMOTE_CARD_ATTRIBUTES = tuple(field.name for field in fields(NamespaceCard))


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
    plan_schema_version: int = 1


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


@dataclass(frozen=True)
class MigrationState:
    state: str
    missing_cards: tuple[NamespaceCard, ...]
    existing_cards: tuple[NamespaceCard, ...]
    reason: str | None = None


@dataclass(frozen=True)
class RemoteMigrationSnapshot:
    catalog_exists: bool
    cards: tuple[NamespaceCard, ...]
    live_namespace_ids: tuple[str, ...]
    snapshot_revision: str
    metrics: ReadMetrics


T = TypeVar("T")


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


def remote_card_id(namespace: str) -> str:
    _validate_target_namespace(namespace, allow_reserved=True)
    digest = hashlib.sha256(namespace.encode("utf-8")).hexdigest()
    return f"bc_{digest[:61]}"


def card_to_remote_row(card: NamespaceCard) -> dict[str, object]:
    parsed = parse_card(card_to_dict(card, include_vector=True))
    return {"id": remote_card_id(parsed.namespace), **card_to_dict(parsed, include_vector=True)}


def card_from_remote_row(row: object, *, region: str) -> NamespaceCard:
    payload = _plain(row)
    if not isinstance(payload, dict):
        raise RemoteCatalogError("remote card row must be an object")
    row_id = payload.pop("id", None)
    payload.pop("$dist", None)
    payload.pop("dist", None)
    # The provider omits requested attributes whose stored value is null.
    # Only the two application-nullable lineage fields may be reconstructed.
    payload.setdefault("last_plan_id", None)
    payload.setdefault("last_apply_id", None)
    if set(payload) != set(REMOTE_CARD_ATTRIBUTES):
        unknown = sorted(set(payload) - set(REMOTE_CARD_ATTRIBUTES))
        missing = sorted(set(REMOTE_CARD_ATTRIBUTES) - set(payload))
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
    value = _plain(metadata)
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
    if schema != REMOTE_CATALOG_SCHEMA:
        missing = sorted(set(REMOTE_CATALOG_SCHEMA) - set(schema))
        extra = sorted(set(schema) - set(REMOTE_CATALOG_SCHEMA))
        changed = sorted(
            name
            for name in set(schema) & set(REMOTE_CATALOG_SCHEMA)
            if schema[name] != REMOTE_CATALOG_SCHEMA[name]
        )
        raise RemoteCatalogError(
            f"remote catalog schema mismatch (missing={missing}, extra={extra}, changed={changed})"
        )
    return schema


def read_remote_catalog(
    client: RemoteClient,
    *,
    region: str,
    compatibility: CompatibilityContract,
) -> RemoteCatalogSnapshot:
    first_ids, first_pages = _list_namespaces(client)
    if REMOTE_CATALOG_NAMESPACE not in first_ids:
        raise RemoteCatalogError(
            f"remote catalog namespace {REMOTE_CATALOG_NAMESPACE!r} does not exist in region {region!r}"
        )
    resource = client.namespace(REMOTE_CATALOG_NAMESPACE)
    metadata = _call("metadata read", resource.metadata)
    validate_remote_schema(metadata)
    first_cards, first_card_pages, first_billing = _read_card_pass(resource, region=region)
    second_cards, second_card_pages, second_billing = _read_card_pass(resource, region=region)
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
    )


def read_remote_migration_snapshot(
    client: RemoteClient,
    *,
    region: str,
    compatibility: CompatibilityContract,
) -> RemoteMigrationSnapshot:
    """Read stable remote state while allowing the reserved namespace to be absent."""

    first_ids, first_pages = _list_namespaces(client)
    second_ids, second_pages = _list_namespaces(client)
    if first_ids != second_ids:
        raise RemoteCatalogError("remote namespace listing changed between migration read passes")
    if REMOTE_CATALOG_NAMESPACE not in first_ids:
        return RemoteMigrationSnapshot(
            catalog_exists=False,
            cards=(),
            live_namespace_ids=tuple(first_ids),
            snapshot_revision=catalog_revision([]),
            metrics=ReadMetrics(first_pages + second_pages, 0, 0, ()),
        )
    snapshot = read_remote_catalog(client, region=region, compatibility=compatibility)
    return RemoteMigrationSnapshot(
        catalog_exists=True,
        cards=snapshot.cards,
        live_namespace_ids=(REMOTE_CATALOG_NAMESPACE, *snapshot.live_namespace_ids),
        snapshot_revision=snapshot.snapshot_revision,
        metrics=ReadMetrics(
            namespace_list_pages=first_pages + second_pages + snapshot.metrics.namespace_list_pages,
            metadata_requests=snapshot.metrics.metadata_requests,
            card_query_pages=snapshot.metrics.card_query_pages,
            billing=snapshot.metrics.billing,
        ),
    )


def read_remote_card_twice(
    resource: NamespaceResource,
    *,
    namespace: str,
    region: str,
    preserve_reads: bool = False,
) -> tuple[NamespaceCard, ...]:
    """Strongly read one exact remote card twice, optionally preserving both reads."""

    _validate_target_namespace(namespace, allow_reserved=False)
    return _read_exact_cards_twice(
        resource,
        [remote_card_id(namespace)],
        region=region,
        allow_missing=True,
        preserve_single_reads=preserve_reads,
    )


def require_eligible(snapshot: RemoteCatalogSnapshot) -> RemoteCatalogSnapshot:
    """Require at least one card for routing while preserving generic management reads."""

    if snapshot.counts.eligible_count == 0:
        raise RemoteCatalogError(
            "no eligible live remote namespace cards; run `buoy catalog list --all` to inspect "
            "missing, stale, disabled, and incompatible cards"
        )
    return snapshot


def classify_remote_catalog(
    *,
    live_namespace_ids: Sequence[str],
    cards: Sequence[NamespaceCard],
    compatibility: CompatibilityContract,
    metrics: ReadMetrics | None = None,
) -> RemoteCatalogSnapshot:
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
    content_live = set(listed) - {REMOTE_CATALOG_NAMESPACE}
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
        control_plane_count=int(REMOTE_CATALOG_NAMESPACE in listed),
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
    )


def create_remote_cards(
    resource: NamespaceResource,
    cards: Sequence[NamespaceCard],
    *,
    region: str,
) -> MutationResult:
    ordered = tuple(sorted((parse_card(card_to_dict(card, include_vector=True)) for card in cards), key=lambda c: c.namespace))
    if not ordered:
        raise RemoteCatalogError("remote card create requires at least one card")
    _validate_mutation_cards(ordered, region=region)
    rows = [card_to_remote_row(card) for card in ordered]
    response = _call(
        "conditional card create",
        resource.write,
        distance_metric=DISTANCE_METRIC,
        schema=REMOTE_CATALOG_SCHEMA,
        upsert_rows=rows,
        upsert_condition=("id", "Eq", None),
        return_affected_ids=True,
    )
    affected, affected_ids = _write_result(response, kind="upserted")
    expected_ids = tuple(row["id"] for row in rows)
    billing = _response_billing(response)
    verification_billing: list[dict[str, object]] = []
    metrics = MutationMetrics(1, len(expected_ids) * 2, ())
    if affected == 0:
        current = _read_exact_cards_twice(
            resource, expected_ids, region=region, billing=verification_billing
        )
        metrics = replace(metrics, billing=tuple([*billing, *verification_billing]))
        if _same_cards(current, ordered):
            return MutationResult(False, ordered[0] if len(ordered) == 1 else None, 0, (), metrics)
        raise RemoteCatalogError("conditional card create conflicted with existing remote state")
    if affected != len(expected_ids) or tuple(sorted(affected_ids)) != tuple(sorted(expected_ids)):
        # Strong read makes any partial race observable for the next migration attempt.
        _read_exact_cards_twice(
            resource, expected_ids, region=region, allow_missing=True,
            billing=verification_billing,
        )
        raise RemoteCatalogError(
            f"conditional card create affected unexpected IDs: expected {sorted(expected_ids)}, got {sorted(affected_ids)}"
        )
    current = _read_exact_cards_twice(
        resource, expected_ids, region=region, billing=verification_billing
    )
    if not _same_cards(current, ordered):
        raise RemoteCatalogError("remote card create verification did not match intended cards")
    metrics = replace(metrics, billing=tuple([*billing, *verification_billing]))
    return MutationResult(
        True, ordered[0] if len(ordered) == 1 else None, affected,
        tuple(affected_ids), metrics,
    )


def update_remote_card(
    resource: NamespaceResource,
    card: NamespaceCard,
    *,
    expected_revision: str,
    region: str,
) -> MutationResult:
    parsed = parse_card(card_to_dict(card, include_vector=True))
    _validate_mutation_cards((parsed,), region=region)
    if not isinstance(expected_revision, str) or not expected_revision:
        raise RemoteCatalogError("expected card revision must be a non-empty string")
    expected_id = remote_card_id(parsed.namespace)
    response = _call(
        "conditional card update",
        resource.write,
        distance_metric=DISTANCE_METRIC,
        schema=REMOTE_CATALOG_SCHEMA,
        upsert_rows=[card_to_remote_row(parsed)],
        upsert_condition=("card_revision", "Eq", expected_revision),
        return_affected_ids=True,
    )
    affected, ids = _write_result(response, kind="upserted")
    verification_billing: list[dict[str, object]] = []
    current = _read_exact_cards_twice(
        resource, [expected_id], region=region, allow_missing=True,
        billing=verification_billing,
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


def delete_remote_card(
    resource: NamespaceResource,
    *,
    namespace: str,
    expected_revision: str,
    region: str,
) -> MutationResult:
    _validate_target_namespace(namespace, allow_reserved=False)
    if not isinstance(region, str) or not region:
        raise RemoteCatalogError("resolved region must be a non-empty string")
    if not isinstance(expected_revision, str) or not expected_revision:
        raise RemoteCatalogError("expected card revision must be a non-empty string")
    expected_id = remote_card_id(namespace)
    response = _call(
        "conditional card delete",
        resource.write,
        distance_metric=DISTANCE_METRIC,
        deletes=[expected_id],
        delete_condition=("card_revision", "Eq", expected_revision),
        return_affected_ids=True,
    )
    affected, ids = _write_result(response, kind="deleted")
    verification_billing: list[dict[str, object]] = []
    current = _read_exact_cards_twice(
        resource, [expected_id], region=region, allow_missing=True,
        billing=verification_billing,
    )
    metrics = MutationMetrics(
        1, 2, tuple([*_response_billing(response), *verification_billing])
    )
    if affected == 0:
        state = "card is absent" if not current else "a newer remote revision exists"
        raise RemoteCatalogError(f"conditional card delete conflicted: {state}")
    if affected != 1 or ids != [expected_id] or current:
        raise RemoteCatalogError("remote card delete affected or verified an unexpected row")
    return MutationResult(True, None, 1, (expected_id,), metrics)


def classify_migration_state(
    *,
    catalog_exists: bool,
    existing_cards: Sequence[NamespaceCard],
    intended_cards: Sequence[NamespaceCard],
    schema_valid: bool = True,
) -> MigrationState:
    intended = tuple(sorted((parse_card(card_to_dict(card, include_vector=True)) for card in intended_cards), key=lambda c: c.namespace))
    existing = tuple(sorted((parse_card(card_to_dict(card, include_vector=True)) for card in existing_cards), key=lambda c: c.namespace))
    if len({card.namespace for card in intended}) != len(intended) or not intended:
        raise RemoteCatalogError("migration intended cards must be non-empty and unique")
    if not catalog_exists:
        if existing:
            return MigrationState("conflict", (), existing, "absent catalog cannot contain rows")
        return MigrationState("absent", intended, ())
    if not schema_valid:
        return MigrationState("conflict", (), existing, "incompatible remote schema")
    intended_by_name = {card.namespace: card for card in intended}
    existing_by_name = {card.namespace: card for card in existing}
    extra = sorted(set(existing_by_name) - set(intended_by_name))
    if extra:
        return MigrationState("conflict", (), existing, f"unexpected remote card targets: {extra}")
    for namespace, current in existing_by_name.items():
        if card_to_dict(current, include_vector=True) != card_to_dict(intended_by_name[namespace], include_vector=True):
            return MigrationState("conflict", (), existing, f"remote card {namespace!r} differs from intended card")
    missing = tuple(intended_by_name[name] for name in sorted(set(intended_by_name) - set(existing_by_name)))
    if not existing:
        return MigrationState("empty", intended, existing)
    if missing:
        return MigrationState("partial", missing, existing)
    return MigrationState("exact", (), existing)


_REBASE_SEMANTIC_FIELDS = {"title", "summary", "aliases", "tags", "semantic_origin"}
_REBASE_DERIVED_FIELDS = {
    "enabled",
    "updated_at",
    "card_revision",
    "semantic_hash",
    "vector",
    "vector_hash",
}


def rebase_remote_card(
    *,
    base: NamespaceCard | None,
    current: NamespaceCard,
    pending: NamespaceCard,
    embedder: RoutingEmbedder | None = None,
) -> NamespaceCard:
    current = parse_card(card_to_dict(current, include_vector=True))
    pending = parse_card(card_to_dict(pending, include_vector=True))
    if current.namespace != pending.namespace:
        raise RemoteCatalogError("cannot rebase different target namespaces")
    recompute_projection = base is None
    if base is None:
        if current.semantic_origin != "manual" or current.last_plan_id is not None or current.last_apply_id is not None:
            raise RemoteCatalogError("first-apply rebase requires a lineage-free manual remote card")
        for field in _system_contract_fields():
            if getattr(current, field) != getattr(pending, field):
                raise RemoteCatalogError(f"first-apply rebase is unsafe because field {field} differs")
    else:
        base = parse_card(card_to_dict(base, include_vector=True))
        if base.namespace != current.namespace:
            raise RemoteCatalogError("rebase base snapshot targets a different namespace")
        changed = {
            name
            for name in REMOTE_CARD_ATTRIBUTES
            if getattr(base, name) != getattr(current, name)
        }
        allowed = _REBASE_DERIVED_FIELDS | _REBASE_SEMANTIC_FIELDS
        if changed - allowed:
            raise RemoteCatalogError(
                f"remote card has unsafe concurrent field changes: {sorted(changed - allowed)}"
            )
        semantic_changed = any(
            getattr(base, field) != getattr(current, field)
            for field in _REBASE_SEMANTIC_FIELDS
        )
        if semantic_changed and current.semantic_origin != "manual":
            raise RemoteCatalogError("concurrent semantic changes are rebase-safe only for manual cards")
        if semantic_changed:
            recompute_projection = True
        elif not _same_projection(base, current):
            raise RemoteCatalogError(
                "remote semantic fields are unchanged but semantic/vector projection differs from base"
            )
    if not recompute_projection:
        return merge_system_card(current, pending)
    if embedder is None:
        raise RemoteCatalogError("safe rebase with manual semantics requires an injected routing embedder")
    fields = CardFields(
        namespace=pending.namespace,
        enabled=current.enabled,
        source_kind=pending.source_kind,
        source_uri=pending.source_uri,
        site_id=pending.site_id,
        title=current.title,
        summary=current.summary,
        aliases=list(current.aliases),
        tags=list(current.tags),
        semantic_origin="manual",
        region=pending.region,
        embedding_model=pending.embedding_model,
        embedding_precision=pending.embedding_precision,
        plan_schema_version=pending.plan_schema_version,
        ranking_mode=pending.ranking_mode,
        ranking_profile=pending.ranking_profile,
        ranking_pool=pending.ranking_pool,
        ranking_aggregation=pending.ranking_aggregation,
        last_plan_id=pending.last_plan_id,
        last_apply_id=pending.last_apply_id,
    )
    try:
        rebased = prepare_card(fields, embedder=embedder, now=pending.updated_at)
    except CatalogError as exc:
        raise RemoteCatalogError(f"safe rebase projection failed: {exc}") from exc
    rebased = replace(rebased, created_at=current.created_at, card_revision="pending")
    return replace(rebased, card_revision=card_revision(rebased))


def validate_accept_remote(
    *,
    current_reads: Sequence[NamespaceCard],
    pending: NamespaceCard,
    expected_remote_revision: str,
) -> NamespaceCard:
    if len(current_reads) != 2:
        raise RemoteCatalogError("accept-remote requires exactly two strong remote card reads")
    first = parse_card(card_to_dict(current_reads[0], include_vector=True))
    second = parse_card(card_to_dict(current_reads[1], include_vector=True))
    if card_to_dict(first, include_vector=True) != card_to_dict(second, include_vector=True):
        raise RemoteCatalogError("accept-remote remote card changed between strong reads")
    pending = parse_card(card_to_dict(pending, include_vector=True))
    if first.namespace != pending.namespace:
        raise RemoteCatalogError("accepted remote card targets a different namespace")
    if first.card_revision != expected_remote_revision:
        raise RemoteCatalogError("accepted remote revision does not match the operator-supplied revision")
    if first.last_plan_id is None or first.last_apply_id is None:
        raise RemoteCatalogError("accepted remote card must have complete apply lineage")
    if (first.last_plan_id, first.last_apply_id) == (pending.last_plan_id, pending.last_apply_id):
        raise RemoteCatalogError("accepted remote card must have different apply lineage from pending")
    return first


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
    page = _call("namespace listing", client.namespaces, page_size=NAMESPACE_PAGE_SIZE)
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
        if hasattr(page, "namespaces"):
            items = getattr(page, "namespaces")
        elif isinstance(page, Mapping) and "namespaces" in page:
            items = page["namespaces"]
        else:
            # Plain iterables are accepted for simple injected clients and count as one page.
            items = page
        try:
            batch = list(items)
        except TypeError as exc:
            raise RemoteCatalogError("namespace listing response is not iterable") from exc
        for summary in batch:
            plain = _plain(summary)
            value = plain.get("id") if isinstance(plain, dict) else None
            if not isinstance(value, str) or not value:
                raise RemoteCatalogError("namespace listing returned an invalid ID")
            if value in seen_ids:
                raise RemoteCatalogError(f"namespace listing repeated ID {value!r} during pagination")
            seen_ids.add(value)
            values.append(value)
        cursor = _namespace_page_cursor(page)
        signature = (tuple(values[-len(batch):]) if batch else (), cursor)
        if signature in seen_signatures:
            raise RemoteCatalogError("namespace listing repeated a page cursor/signature")
        seen_signatures.add(signature)
        if cursor is not None:
            if cursor in seen_cursors:
                raise RemoteCatalogError("namespace listing repeated a page cursor/signature")
            seen_cursors.add(cursor)
        has_next = getattr(page, "has_next_page", None)
        if not callable(has_next) or not has_next():
            break
        if not batch:
            raise RemoteCatalogError("namespace listing pagination did not advance")
        getter = getattr(page, "get_next_page", None)
        if not callable(getter):
            raise RemoteCatalogError("namespace listing advertised a next page without a getter")
        page = _call("namespace listing pagination", getter)
    return tuple(sorted(values)), pages


def _read_card_pass(
    resource: NamespaceResource,
    *,
    region: str,
) -> tuple[tuple[NamespaceCard, ...], int, tuple[dict[str, object], ...]]:
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
            "include_attributes": list(REMOTE_CARD_ATTRIBUTES),
            "vector_encoding": "float",
            "consistency": dict(STRONG_CONSISTENCY),
        }
        if last_id is not None:
            kwargs["filters"] = ("id", "Gt", last_id)
        response = _call("card page query", resource.query, **kwargs)
        pages += 1
        plain = _plain(response)
        rows_value = plain.get("rows") if isinstance(plain, dict) else None
        rows = [] if rows_value is None else list(rows_value)
        if len(rows) > CARD_PAGE_SIZE:
            raise RemoteCatalogError("remote card query returned more rows than requested")
        page_ids: list[str] = []
        for row in rows:
            row_plain = _plain(row)
            row_id = row_plain.get("id") if isinstance(row_plain, dict) else None
            if not isinstance(row_id, str) or not row_id:
                raise RemoteCatalogError("remote card query returned an invalid row ID")
            page_ids.append(row_id)
            if row_id in seen_row_ids:
                raise RemoteCatalogError("remote card pagination repeated a row ID")
            seen_row_ids.add(row_id)
            cards.append(card_from_remote_row(row, region=region))
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
    allow_missing: bool = False,
    preserve_single_reads: bool = False,
    billing: list[dict[str, object]] | None = None,
) -> tuple[NamespaceCard, ...]:
    expected = tuple(sorted(row_ids))
    passes: list[tuple[NamespaceCard, ...]] = []
    for _ in range(2):
        rows: list[NamespaceCard] = []
        for row_id in expected:
            response = _call(
                "card verification query",
                resource.query,
                rank_by=("id", "asc"),
                top_k=2,
                filters=("id", "Eq", row_id),
                include_attributes=list(REMOTE_CARD_ATTRIBUTES),
                vector_encoding="float",
                consistency=dict(STRONG_CONSISTENCY),
            )
            plain = _plain(response)
            if billing is not None:
                bill = plain.get("billing") if isinstance(plain, dict) else None
                if bill is not None:
                    billing.append(_safe_billing(bill))
            raw_rows = plain.get("rows") if isinstance(plain, dict) else None
            values = [] if raw_rows is None else list(raw_rows)
            if len(values) > 1:
                raise RemoteCatalogError("card verification returned duplicate row IDs")
            if values:
                card = card_from_remote_row(values[0], region=region)
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
        and card.plan_schema_version == compatibility.plan_schema_version
    )


def _same_projection(first: NamespaceCard, second: NamespaceCard) -> bool:
    return (
        first.semantic_hash == second.semantic_hash
        and first.vector_hash == second.vector_hash
        and first.vector == second.vector
    )


def _system_contract_fields() -> tuple[str, ...]:
    return (
        "namespace",
        "source_kind",
        "source_uri",
        "site_id",
        "region",
        "embedding_model",
        "embedding_precision",
        "vector_dimensions",
        "plan_schema_version",
        "ranking_mode",
        "ranking_profile",
        "ranking_pool",
        "ranking_aggregation",
        "routing_model",
        "routing_model_revision",
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
    plain = _plain(response)
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


def _response_billing(response: object) -> tuple[dict[str, object], ...]:
    plain = _plain(response)
    bill = plain.get("billing") if isinstance(plain, dict) else None
    return (_safe_billing(bill),) if bill is not None else ()


def _safe_billing(value: object) -> dict[str, object]:
    plain = _plain(value)
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
    class_name = re.sub(r"[^A-Za-z0-9_.-]", "_", exc.__class__.__name__)[:80]
    status = getattr(exc, "status_code", None)
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
