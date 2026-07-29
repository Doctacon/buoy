"""Remote orchestration for branch-backed evidence snapshots.

Provider access is injected. Importing this module performs no credential reads,
SDK import, client construction, source access, or remote operation.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import time
from typing import Callable, Iterator, Mapping, Protocol, Sequence, TypeVar

from buoy_search.applied_state import stream_applied_state_rows
from buoy_search.catalog import NamespaceCard
from buoy_search.evidence_snapshot import (
    DEFAULT_EVIDENCE_OUT_ROOT,
    DEFAULT_MAXIMUM_REMOTE_LOGICAL_BYTES,
    DEFAULT_MAXIMUM_ROWS,
    EVIDENCE_CATALOG_NAMESPACE,
    EVIDENCE_SCHEMA_VERSION,
    LEDGER_WRITE_BATCH_SIZE,
    LOCAL_ROW_BATCH_SIZE,
    MAX_MANIFEST_BYTES,
    REMOTE_PAGE_SIZE,
    EvidenceSnapshotError,
    LocalEvidenceSource,
    StateFingerprint,
    acquire_evidence_apply_locks,
    canonical_json,
    derive_snapshot_names,
    discover_local_sources,
    fingerprint_source,
    ledger_document_id,
    ledger_row,
    logical_hash,
    manifest_hash,
    snapshot_identity_payload,
    validate_card_for_source,
    validate_limits,
    validate_namespace_selection,
)
from buoy_search.remote_catalog import (
    CompatibilityContract,
    RemoteCatalogError,
    RemoteCatalogSnapshot,
    read_remote_catalog,
)

STRONG_CONSISTENCY = {"level": "strong"}
RECONCILIATION_ATTRIBUTES = (
    "canonical_url",
    "page_hash",
    "chunk_hash",
    "embedding_text_hash",
    "plan_id",
    "applied_at",
)
LEDGER_ATTRIBUTES = (
    "snapshot_id",
    "source_namespace",
    "branch_namespace",
    "source_row_id",
    "site_id",
    "status",
    "canonical_url",
    "page_hash",
    "chunk_hash",
    "embedding_text_hash",
    "plan_id",
    "applied_at",
    "ordinal",
)
LEDGER_SCHEMA: dict[str, dict[str, object]] = {
    "snapshot_id": {"type": "string", "filterable": False},
    "source_namespace": {"type": "string", "filterable": True},
    "branch_namespace": {"type": "string", "filterable": True},
    "source_row_id": {"type": "string", "filterable": True},
    "site_id": {"type": "string", "filterable": False},
    "status": {"type": "string", "filterable": True},
    "canonical_url": {"type": "string", "filterable": False},
    "page_hash": {"type": "string", "filterable": False},
    "chunk_hash": {"type": "string", "filterable": False},
    "embedding_text_hash": {"type": "string", "filterable": False},
    "plan_id": {"type": "string", "filterable": False},
    "applied_at": {"type": "string", "filterable": False},
    "ordinal": {"type": "uint", "filterable": False},
}
LEDGER_WRITE_MAX_BYTES = 16 * 1024 * 1024

CATALOG_ATTRIBUTES = (
    "snapshot_id",
    "schema_version",
    "state",
    "created_at",
    "region",
    "source_namespaces",
    "branch_namespaces",
    "ledger_namespace",
    "namespace_count",
    "active_row_count",
    "retained_stale_row_count",
    "deleted_row_count",
    "source_state_hashes_json",
    "source_identity_json",
    "last_plan_ids_json",
    "last_apply_ids_json",
    "catalog_card_revisions_json",
    "branch_observations_json",
    "approximate_logical_bytes",
    "exact_ledger_row_count",
    "ledger_logical_hash",
    "snapshot_logical_hash",
    "manifest_hash",
)
CATALOG_SCHEMA: dict[str, dict[str, object]] = {
    "snapshot_id": {"type": "string", "filterable": True},
    "schema_version": {"type": "uint", "filterable": True},
    "state": {"type": "string", "filterable": True},
    "created_at": {"type": "string", "filterable": False},
    "region": {"type": "string", "filterable": True},
    "source_namespaces": {"type": "[]string", "filterable": False},
    "branch_namespaces": {"type": "[]string", "filterable": False},
    "ledger_namespace": {"type": "string", "filterable": False},
    "namespace_count": {"type": "uint", "filterable": False},
    "active_row_count": {"type": "uint", "filterable": False},
    "retained_stale_row_count": {"type": "uint", "filterable": False},
    "deleted_row_count": {"type": "uint", "filterable": False},
    "source_state_hashes_json": {"type": "string", "filterable": False},
    "source_identity_json": {"type": "string", "filterable": False},
    "last_plan_ids_json": {"type": "string", "filterable": False},
    "last_apply_ids_json": {"type": "string", "filterable": False},
    "catalog_card_revisions_json": {"type": "string", "filterable": False},
    "branch_observations_json": {"type": "string", "filterable": False},
    "approximate_logical_bytes": {"type": "uint", "filterable": False},
    "exact_ledger_row_count": {"type": "uint", "filterable": False},
    "ledger_logical_hash": {"type": "string", "filterable": False},
    "snapshot_logical_hash": {"type": "string", "filterable": False},
    "manifest_hash": {"type": "string", "filterable": False},
}


class NamespaceResource(Protocol):
    def exists(self, **kwargs: object) -> object: ...
    def metadata(self, **kwargs: object) -> object: ...
    def branch_from(self, **kwargs: object) -> object: ...
    def query(self, **kwargs: object) -> object: ...
    def write(self, **kwargs: object) -> object: ...
    def delete_all(self, **kwargs: object) -> object: ...


class RemoteClient(Protocol):
    def namespace(self, namespace: str) -> NamespaceResource: ...


T = TypeVar("T")
CatalogReader = Callable[..., RemoteCatalogSnapshot]


def _plain(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
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


def _safe_call(phase: str, function: Callable[..., T], **kwargs: object) -> T:
    try:
        return function(**kwargs)
    except EvidenceSnapshotError:
        raise
    except Exception as exc:
        status = getattr(exc, "status_code", None)
        status_text = f", status={status}" if type(status) is int else ""
        raise EvidenceSnapshotError(
            f"remote evidence {phase} failed ({exc.__class__.__name__}{status_text})"
        ) from None


def _resource_exists(resource: NamespaceResource, *, metrics: dict[str, int]) -> bool:
    result = _safe_call("namespace existence check", resource.exists)
    metrics["remote_queries"] += 1
    if isinstance(result, bool):
        return result
    plain = _plain(result)
    if isinstance(plain, dict) and isinstance(plain.get("exists"), bool):
        return bool(plain["exists"])
    raise EvidenceSnapshotError("remote namespace existence response is invalid")


def _metadata(resource: NamespaceResource, *, metrics: dict[str, int]) -> dict[str, object]:
    result = _safe_call("metadata read", resource.metadata)
    metrics["remote_queries"] += 1
    plain = _plain(result)
    if not isinstance(plain, dict):
        raise EvidenceSnapshotError("remote namespace metadata is invalid")
    return plain


def _metadata_value(metadata: Mapping[str, object], key: str) -> int:
    value = metadata.get(key)
    if type(value) is not int or value < 0:
        raise EvidenceSnapshotError(f"remote metadata {key} is invalid")
    return value


def _branch_write_marker(metadata: Mapping[str, object]) -> str:
    """Return the strongest SDK-exposed timestamp that changes on branch writes."""

    for key in ("last_write_at", "updated_at"):
        value = metadata.get(key)
        if isinstance(value, str) and value:
            return value
    raise EvidenceSnapshotError(
        "remote evidence branch metadata is missing a usable write marker"
    )


def _branch_observation(
    metadata: Mapping[str, object], *, namespace: str, parent: str
) -> dict[str, object]:
    branching = _plain(metadata.get("branching"))
    actual_parent = branching.get("parent") if isinstance(branching, dict) else None
    if actual_parent != parent:
        raise EvidenceSnapshotError(
            f"evidence branch parent mismatch for namespace {namespace!r}"
        )
    return {
        "namespace": namespace,
        "parent": parent,
        "created_at": metadata.get("created_at"),
        # Canonical provider write marker. Official metadata exposes
        # last_write_at; SDK 2.4.0 documents updated_at as its conservative
        # last-modified-by-write fallback.
        "last_write_at": _branch_write_marker(metadata),
        "approx_row_count": metadata.get("approx_row_count"),
        "approx_logical_bytes": metadata.get("approx_logical_bytes"),
    }


def _assert_branch_observation(
    metadata: Mapping[str, object],
    *,
    expected: Mapping[str, object],
    namespace: str,
    parent: str,
    phase: str,
) -> None:
    current = _branch_observation(metadata, namespace=namespace, parent=parent)
    if current != expected:
        raise EvidenceSnapshotError(
            f"evidence branch metadata changed {phase} for namespace {namespace!r}"
        )


def _validate_source_metadata(
    *, namespace: str, metadata: Mapping[str, object], vector_dimensions: int
) -> dict[str, object]:
    if metadata.get("sharding") is not None:
        raise EvidenceSnapshotError(
            f"namespace {namespace!r} is sharded; branch-backed evidence snapshots are unavailable"
        )
    schema = _plain(metadata.get("schema"))
    if not isinstance(schema, dict):
        raise EvidenceSnapshotError(
            f"namespace {namespace!r} metadata is missing schema"
        )
    required = {"canonical_url", "page_hash", "chunk_hash", "embedding_text_hash", "plan_id", "applied_at", "vector"}
    if not required.issubset(schema):
        raise EvidenceSnapshotError(
            f"namespace {namespace!r} schema is incompatible with applied evidence"
        )
    vector = _plain(schema.get("vector"))
    vector_type = vector.get("type") if isinstance(vector, dict) else vector
    if not isinstance(vector_type, str) or not vector_type.startswith(f"[{vector_dimensions}]"):
        raise EvidenceSnapshotError(
            f"namespace {namespace!r} vector schema is incompatible"
        )
    return {
        "approximate_rows": _metadata_value(metadata, "approx_row_count"),
        "approximate_logical_bytes": _metadata_value(metadata, "approx_logical_bytes"),
        "created_at": str(metadata.get("created_at", "")),
        "last_write_at": str(
            metadata.get("last_write_at", metadata.get("updated_at", ""))
        ),
    }


def _cards_for_sources(
    *,
    snapshot: RemoteCatalogSnapshot,
    sources: Sequence[LocalEvidenceSource],
    region: str,
    embedding_model: str,
    embedding_precision: str,
) -> dict[str, NamespaceCard]:
    eligible = {card.namespace: card for card in snapshot.eligible_cards}
    cards: dict[str, NamespaceCard] = {}
    for source in sources:
        card = eligible.get(source.namespace)
        if card is None:
            raise EvidenceSnapshotError(
                f"namespace {source.namespace!r} has no compatible eligible routing card"
            )
        validate_card_for_source(
            source,
            card,
            region=region,
            embedding_model=embedding_model,
            embedding_precision=embedding_precision,
        )
        cards[source.namespace] = card
    return cards


def _base_activity(*, writes: bool, manifest: bool) -> dict[str, object]:
    return {
        "credentials_required": True,
        "api_calls_occurred": True,
        "source_namespace_writes_occurred": False,
        "internal_evidence_writes_occurred": writes,
        "local_full_corpus_written": False,
        "local_manifest_written": manifest,
    }


def _new_metrics() -> dict[str, int]:
    return {
        "branch_create_count": 0,
        "branch_reuse_count": 0,
        "branch_calls": 0,
        "ledger_rows_written": 0,
        "ledger_write_calls": 0,
        "catalog_rows_written": 0,
        "catalog_write_calls": 0,
        "remote_queries": 0,
        "billable_logical_bytes_queried": 0,
        "billable_logical_bytes_returned": 0,
    }


def _capture_catalog_metrics(snapshot: object, metrics: dict[str, int]) -> None:
    read_metrics = getattr(snapshot, "metrics", None)
    if read_metrics is None:
        return
    for field in ("namespace_list_pages", "metadata_requests", "card_query_pages"):
        value = getattr(read_metrics, field, 0)
        if type(value) is int and value >= 0:
            metrics["remote_queries"] += value
    for billing in getattr(read_metrics, "billing", ()):
        _capture_billing({"billing": billing}, metrics)


def _capture_billing(response: object, metrics: dict[str, int]) -> None:
    plain = _plain(response)
    billing = plain.get("billing") if isinstance(plain, dict) else None
    if not isinstance(billing, dict):
        return
    for key in ("billable_logical_bytes_queried", "billable_logical_bytes_returned"):
        value = billing.get(key)
        if type(value) is int and value >= 0:
            metrics[key] += value


def estimate_evidence_snapshot(
    client: RemoteClient,
    *,
    namespaces: Sequence[str],
    state_root: Path,
    region: str,
    embedding_model: str,
    embedding_precision: str,
    maximum_rows: int = DEFAULT_MAXIMUM_ROWS,
    maximum_remote_logical_bytes: int = DEFAULT_MAXIMUM_REMOTE_LOGICAL_BYTES,
    catalog_reader: CatalogReader = read_remote_catalog,
) -> dict[str, object]:
    selected = validate_namespace_selection(namespaces)
    sources = discover_local_sources(namespaces=selected, state_root=state_root)
    compatibility = CompatibilityContract(region, embedding_model, embedding_precision)
    try:
        routing = catalog_reader(client, region=region, compatibility=compatibility)
    except (RemoteCatalogError, ValueError) as exc:
        raise EvidenceSnapshotError(f"routing-catalog compatibility read failed: {exc}") from exc
    cards = _cards_for_sources(
        snapshot=routing,
        sources=sources,
        region=region,
        embedding_model=embedding_model,
        embedding_precision=embedding_precision,
    )
    metrics = _new_metrics()
    _capture_catalog_metrics(routing, metrics)
    rows: list[dict[str, object]] = []
    total_bytes = 0
    total_remote_rows = 0
    total_local_rows = 0
    for source in sources:
        metadata = _metadata(client.namespace(source.namespace), metrics=metrics)
        observed = _validate_source_metadata(
            namespace=source.namespace,
            metadata=metadata,
            vector_dimensions=cards[source.namespace].vector_dimensions,
        )
        total_bytes += int(observed["approximate_logical_bytes"])
        total_remote_rows += int(observed["approximate_rows"])
        total_local_rows += source.summary.total_rows
        rows.append(
            {
                "namespace": source.namespace,
                "branch_supported": True,
                "approximate_rows": observed["approximate_rows"],
                "local_ledger_rows": source.summary.total_rows,
                "approximate_logical_bytes": observed["approximate_logical_bytes"],
                "region": region,
                "last_apply_id": source.summary.last_apply_id,
            }
        )
    limit_error: str | None = None
    try:
        validate_limits(
            row_count=total_local_rows,
            approximate_logical_bytes=total_bytes,
            maximum_rows=maximum_rows,
            maximum_remote_logical_bytes=maximum_remote_logical_bytes,
        )
    except EvidenceSnapshotError as exc:
        limit_error = str(exc)
    result = {
        "command": "evidence estimate",
        "namespaces": rows,
        "namespace_count": len(sources),
        "local_ledger_rows": total_local_rows,
        "approximate_remote_rows": total_remote_rows,
        "approximate_remote_logical_bytes": total_bytes,
        "maximum_rows": maximum_rows,
        "maximum_remote_logical_bytes": maximum_remote_logical_bytes,
        "branch_supported": True,
        "would_pass_limits": limit_error is None,
        "limit_error": limit_error,
        "remote_writes_occurred": False,
        **_base_activity(writes=False, manifest=False),
        **metrics,
    }
    return result


def _query_rows(
    resource: NamespaceResource,
    *,
    include_attributes: Sequence[str],
    metrics: dict[str, int],
    filters: object | None = None,
    rank_by: tuple[str, str] = ("id", "asc"),
    cursor_field: str = "id",
) -> Iterator[dict[str, object]]:
    last: object | None = None
    previous: object | None = None
    while True:
        kwargs: dict[str, object] = {
            "rank_by": rank_by,
            "limit": REMOTE_PAGE_SIZE,
            "include_attributes": list(include_attributes),
            "consistency": dict(STRONG_CONSISTENCY),
        }
        page_filter = (cursor_field, "Gt", last) if last is not None else None
        if filters is not None and page_filter is not None:
            kwargs["filters"] = ("And", [filters, page_filter])
        elif filters is not None:
            kwargs["filters"] = filters
        elif page_filter is not None:
            kwargs["filters"] = page_filter
        response = _safe_call("ordered query", resource.query, **kwargs)
        metrics["remote_queries"] += 1
        _capture_billing(response, metrics)
        plain = _plain(response)
        raw_rows = plain.get("rows") if isinstance(plain, dict) else None
        rows = [] if raw_rows is None else list(raw_rows)
        if len(rows) > REMOTE_PAGE_SIZE:
            raise EvidenceSnapshotError("remote query returned more rows than requested")
        for raw in rows:
            row = _plain(raw)
            if not isinstance(row, dict):
                raise EvidenceSnapshotError("remote query returned an invalid row")
            value = row.get(cursor_field)
            if not isinstance(value, (str, int)) or isinstance(value, bool):
                raise EvidenceSnapshotError("remote query returned an invalid ordered ID")
            if previous is not None and value <= previous:
                raise EvidenceSnapshotError("remote query IDs are duplicate or out of order")
            previous = value
            last = value
            yield row
        if len(rows) < REMOTE_PAGE_SIZE:
            break
        if not rows or last is None:
            raise EvidenceSnapshotError("remote query pagination did not advance")


def _row_matches(expected: Mapping[str, object], actual: Mapping[str, object]) -> str | None:
    for field in ("id", *RECONCILIATION_ATTRIBUTES):
        if actual.get(field) != expected.get(field):
            return field
    return None


def _normalize_schema(metadata: Mapping[str, object]) -> dict[str, dict[str, object]]:
    raw = _plain(metadata.get("schema"))
    if not isinstance(raw, dict):
        raise EvidenceSnapshotError("remote evidence namespace is missing schema")
    normalized: dict[str, dict[str, object]] = {}
    for name, value in raw.items():
        config = _plain(value)
        if isinstance(config, str):
            config = {"type": config}
        if not isinstance(config, dict) or not isinstance(config.get("type"), str):
            raise EvidenceSnapshotError("remote evidence schema is invalid")
        normalized[str(name)] = {
            "type": config["type"],
            "filterable": config.get("filterable", True),
        }
    return normalized


def _validate_exact_schema(
    metadata: Mapping[str, object], expected: Mapping[str, Mapping[str, object]]
) -> None:
    actual = _normalize_schema(metadata)
    implicit_id = actual.pop("id", None)
    if implicit_id != {"type": "string", "filterable": True}:
        raise EvidenceSnapshotError("remote evidence implicit ID schema is invalid")
    if actual != expected:
        raise EvidenceSnapshotError("remote evidence schema mismatch")


def _write_count(response: object, *, expected: int, kind: str) -> None:
    plain = _plain(response)
    count = plain.get("rows_affected") if isinstance(plain, dict) else None
    if count != expected:
        raise EvidenceSnapshotError(
            f"remote {kind} affected {count!r} rows; expected {expected}"
        )


def _send_ledger_batch(
    *,
    resource: NamespaceResource,
    batch: list[dict[str, object]],
    first_batch: bool,
    metrics: dict[str, int],
    mark_created: Callable[[], None],
    mark_uncertain: Callable[[], None],
) -> bool:
    kwargs: dict[str, object] = {"upsert_rows": batch}
    if first_batch:
        # Insert-if-absent makes a concurrent creator observable. Only a fully
        # successful first response proves this invocation created the ledger.
        kwargs.update(
            schema=LEDGER_SCHEMA,
            upsert_condition=("id", "Eq", None),
            return_affected_ids=True,
        )
    payload_bytes = len(canonical_json(kwargs).encode("utf-8"))
    if payload_bytes > LEDGER_WRITE_MAX_BYTES:
        raise EvidenceSnapshotError(
            f"remote ledger write payload exceeds {LEDGER_WRITE_MAX_BYTES} bytes"
        )
    try:
        response = _safe_call("ledger write", resource.write, **kwargs)
    except Exception:
        mark_uncertain()
        raise
    metrics["ledger_write_calls"] += 1
    _capture_billing(response, metrics)
    try:
        _write_count(response, expected=len(batch), kind="ledger write")
    except Exception:
        if first_batch:
            mark_uncertain()
        raise
    if first_batch:
        plain = _plain(response)
        affected_ids = plain.get("upserted_ids") if isinstance(plain, dict) else None
        if affected_ids != [row["id"] for row in batch]:
            mark_uncertain()
            raise EvidenceSnapshotError(
                "remote ledger first write did not prove namespace ownership"
            )
        mark_created()
    metrics["ledger_rows_written"] += len(batch)
    return False


def _write_ledger(
    *,
    resource: NamespaceResource,
    source: LocalEvidenceSource,
    state_root: Path,
    snapshot_id: str,
    branch_namespace: str,
    first_batch: bool,
    metrics: dict[str, int],
    mark_created: Callable[[], None],
    mark_uncertain: Callable[[], None],
) -> bool:
    batch: list[dict[str, object]] = []
    batch_bytes = len(canonical_json({"schema": LEDGER_SCHEMA, "upsert_rows": []}).encode("utf-8"))
    with stream_applied_state_rows(
        database_path=source.database_path,
        state_root=state_root,
        batch_size=LOCAL_ROW_BATCH_SIZE,
    ) as stream:
        for ordinal, row in enumerate(stream.rows):
            value = ledger_row(
                snapshot_id=snapshot_id,
                source=source,
                branch_namespace=branch_namespace,
                row=row,
                ordinal=ordinal,
            )
            value_bytes = len(canonical_json(value).encode("utf-8")) + 1
            if value_bytes >= LEDGER_WRITE_MAX_BYTES:
                raise EvidenceSnapshotError("one remote ledger row exceeds the bounded write payload")
            if batch and (
                len(batch) == LEDGER_WRITE_BATCH_SIZE
                or batch_bytes + value_bytes > LEDGER_WRITE_MAX_BYTES
            ):
                first_batch = _send_ledger_batch(
                    resource=resource,
                    batch=batch,
                    first_batch=first_batch,
                    metrics=metrics,
                    mark_created=mark_created,
                    mark_uncertain=mark_uncertain,
                )
                batch = []
                batch_bytes = len(canonical_json({"upsert_rows": []}).encode("utf-8"))
            batch.append(value)
            batch_bytes += value_bytes
        if batch:
            first_batch = _send_ledger_batch(
                resource=resource,
                batch=batch,
                first_batch=first_batch,
                metrics=metrics,
                mark_created=mark_created,
                mark_uncertain=mark_uncertain,
            )
    return first_batch


def _hash_ledger(
    *, resource: NamespaceResource, snapshot_id: str, metrics: dict[str, int]
) -> tuple[str, dict[str, int]]:
    import hashlib

    digest = hashlib.sha256()
    counts = {"active": 0, "retained_stale": 0, "deleted": 0, "total": 0}
    for row in _query_rows(
        resource, include_attributes=LEDGER_ATTRIBUTES, metrics=metrics
    ):
        if set(row) != {"id", *LEDGER_ATTRIBUTES}:
            raise EvidenceSnapshotError("remote ledger row has invalid fields")
        if row["snapshot_id"] != snapshot_id:
            raise EvidenceSnapshotError("remote ledger row targets another snapshot")
        status = row.get("status")
        if status not in {"active", "retained_stale", "deleted"}:
            raise EvidenceSnapshotError("remote ledger row has invalid status")
        counts[str(status)] += 1
        counts["total"] += 1
        encoded = canonical_json(row).encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
    return digest.hexdigest(), counts


def _ledger_rows_for_source(
    resource: NamespaceResource,
    *, source_namespace: str,
    metrics: dict[str, int],
) -> Iterator[dict[str, object]]:
    return _query_rows(
        resource,
        include_attributes=LEDGER_ATTRIBUTES,
        metrics=metrics,
        filters=("source_namespace", "Eq", source_namespace),
        rank_by=("source_row_id", "asc"),
        cursor_field="source_row_id",
    )


def _reconcile_branch_with_ledger(
    *,
    branch: NamespaceResource,
    ledger: NamespaceResource,
    snapshot_id: str,
    source_namespace: str,
    expected_branch_namespace: str,
    metrics: dict[str, int],
) -> tuple[str, str, dict[str, int]]:
    import hashlib

    remote = iter(
        _query_rows(
            branch,
            include_attributes=RECONCILIATION_ATTRIBUTES,
            metrics=metrics,
        )
    )
    branch_row = next(remote, None)
    digest = hashlib.sha256()
    site_id: str | None = None
    counts = {"active": 0, "retained_stale": 0, "deleted": 0, "total": 0}
    for ordinal, expected in enumerate(
        _ledger_rows_for_source(
            ledger, source_namespace=source_namespace, metrics=metrics
        )
    ):
        source_row_id = expected["source_row_id"]
        if (
            expected.get("snapshot_id") != snapshot_id
            or expected.get("source_namespace") != source_namespace
            or expected.get("branch_namespace") != expected_branch_namespace
            or expected.get("ordinal") != ordinal
            or expected.get("id")
            != ledger_document_id(
                snapshot_id=snapshot_id,
                source_namespace=source_namespace,
                source_row_id=str(source_row_id),
            )
        ):
            raise EvidenceSnapshotError(
                f"namespace {source_namespace!r} category ledger_identity row {source_row_id!r}"
            )
        row_site_id = expected.get("site_id")
        if not isinstance(row_site_id, str) or not row_site_id or (
            site_id is not None and row_site_id != site_id
        ):
            raise EvidenceSnapshotError(
                f"namespace {source_namespace!r} category ledger_site row {source_row_id!r}"
            )
        site_id = row_site_id
        status = str(expected["status"])
        counts[status] += 1
        counts["total"] += 1
        fingerprint_row = {
            "ordinal": ordinal,
            "row_id": source_row_id,
            "canonical_url": expected["canonical_url"],
            "page_hash": expected["page_hash"],
            "chunk_hash": expected["chunk_hash"],
            "embedding_text_hash": expected["embedding_text_hash"],
            "plan_id": expected["plan_id"],
            "applied_at": expected["applied_at"],
            "status": status,
        }
        encoded = canonical_json(fingerprint_row).encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
        if status == "deleted":
            if branch_row is not None and branch_row.get("id") == source_row_id:
                raise EvidenceSnapshotError(
                    f"namespace {source_namespace!r} category deleted_present row {source_row_id!r}"
                )
            continue
        if branch_row is None or branch_row.get("id") != source_row_id:
            raise EvidenceSnapshotError(
                f"namespace {source_namespace!r} category missing row {source_row_id!r}"
            )
        comparison = {"id": source_row_id, **{key: expected[key] for key in RECONCILIATION_ATTRIBUTES}}
        mismatch = _row_matches(comparison, branch_row)
        if mismatch is not None:
            raise EvidenceSnapshotError(
                f"namespace {source_namespace!r} category {mismatch}_mismatch row {source_row_id!r}"
            )
        branch_row = next(remote, None)
    if branch_row is not None:
        raise EvidenceSnapshotError(
            f"namespace {source_namespace!r} category unexpected row {str(branch_row.get('id'))!r}"
        )
    if site_id is None:
        raise EvidenceSnapshotError(
            f"namespace {source_namespace!r} has no remote ledger rows"
        )
    return digest.hexdigest(), site_id, counts


def _validate_existing_ledger(
    *,
    client: RemoteClient,
    resource: NamespaceResource,
    snapshot_id: str,
    sources: Sequence[LocalEvidenceSource],
    fingerprints: Sequence[StateFingerprint],
    branch_namespaces: Mapping[str, str],
    metrics: dict[str, int],
) -> tuple[str, dict[str, int]]:
    metadata = _metadata(resource, metrics=metrics)
    _validate_exact_schema(metadata, LEDGER_SCHEMA)
    ledger_hash, counts = _hash_ledger(
        resource=resource, snapshot_id=snapshot_id, metrics=metrics
    )
    expected_counts = {
        "active": sum(item.active_rows for item in fingerprints),
        "retained_stale": sum(item.retained_stale_rows for item in fingerprints),
        "deleted": sum(item.deleted_rows for item in fingerprints),
        "total": sum(item.total_rows for item in fingerprints),
    }
    if counts != expected_counts:
        raise EvidenceSnapshotError(
            "incomplete snapshot ledger collision: status counts mismatch"
        )
    expected_by_namespace = {item.namespace: item for item in fingerprints}
    for source in sources:
        expected = expected_by_namespace[source.namespace]
        source_hash, site_id, source_counts = _reconcile_branch_with_ledger(
            branch=client.namespace(branch_namespaces[source.namespace]),
            ledger=resource,
            snapshot_id=snapshot_id,
            source_namespace=source.namespace,
            expected_branch_namespace=branch_namespaces[source.namespace],
            metrics=metrics,
        )
        expected_source_counts = {
            "active": expected.active_rows,
            "retained_stale": expected.retained_stale_rows,
            "deleted": expected.deleted_rows,
            "total": expected.total_rows,
        }
        if (
            source_hash != expected.logical_hash
            or site_id != expected.site_id
            or source_counts != expected_source_counts
        ):
            raise EvidenceSnapshotError(
                f"incomplete snapshot ledger collision for namespace {source.namespace!r}"
            )
    return ledger_hash, counts


def _catalog_row_id(snapshot_id: str) -> str:
    return snapshot_id


def _read_catalog_row(
    client: RemoteClient, *, snapshot_id: str, metrics: dict[str, int]
) -> dict[str, object] | None:
    resource = client.namespace(EVIDENCE_CATALOG_NAMESPACE)
    if not _resource_exists(resource, metrics=metrics):
        return None
    metadata = _metadata(resource, metrics=metrics)
    _validate_exact_schema(metadata, CATALOG_SCHEMA)
    response = _safe_call(
        "catalog query",
        resource.query,
        rank_by=("id", "asc"),
        limit=2,
        filters=("id", "Eq", _catalog_row_id(snapshot_id)),
        include_attributes=list(CATALOG_ATTRIBUTES),
        consistency=dict(STRONG_CONSISTENCY),
    )
    metrics["remote_queries"] += 1
    _capture_billing(response, metrics)
    plain = _plain(response)
    rows = list(plain.get("rows", [])) if isinstance(plain, dict) else []
    if len(rows) > 1:
        raise EvidenceSnapshotError("evidence catalog contains duplicate snapshot rows")
    if not rows:
        return None
    row = _plain(rows[0])
    if not isinstance(row, dict) or set(row) != {"id", *CATALOG_ATTRIBUTES}:
        raise EvidenceSnapshotError("evidence catalog row has invalid fields")
    return row


def _json_object_field(row: Mapping[str, object], field: str) -> dict[str, object]:
    value = row.get(field)
    if not isinstance(value, str):
        raise EvidenceSnapshotError(f"catalog field {field} is invalid")
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise EvidenceSnapshotError(f"catalog field {field} is invalid") from exc
    if not isinstance(parsed, dict):
        raise EvidenceSnapshotError(f"catalog field {field} is invalid")
    return parsed


def _manifest_from_catalog(row: Mapping[str, object], *, activity: Mapping[str, object]) -> dict[str, object]:
    manifest = {
        "schema_version": row["schema_version"],
        "snapshot_id": row["snapshot_id"],
        "created_at": row["created_at"],
        "region": row["region"],
        "source_namespaces": row["source_namespaces"],
        "branch_namespaces": row["branch_namespaces"],
        "ledger_namespace": row["ledger_namespace"],
        "evidence_catalog_namespace": EVIDENCE_CATALOG_NAMESPACE,
        "namespace_count": row["namespace_count"],
        "active_row_count": row["active_row_count"],
        "retained_stale_row_count": row["retained_stale_row_count"],
        "deleted_row_count": row["deleted_row_count"],
        "approximate_remote_logical_bytes": row["approximate_logical_bytes"],
        "snapshot_logical_hash": row["snapshot_logical_hash"],
        "activity": dict(activity),
    }
    manifest["manifest_hash"] = manifest_hash(manifest)
    return manifest


def _write_manifest(
    *, out_root: Path, snapshot_id: str, manifest: Mapping[str, object]
) -> tuple[Path, int]:
    encoded = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if len(encoded) > MAX_MANIFEST_BYTES:
        raise EvidenceSnapshotError(
            f"local snapshot manifest exceeds {MAX_MANIFEST_BYTES} bytes"
        )
    directory = Path(out_root) / snapshot_id
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / "snapshot.json"
    descriptor, temporary = tempfile.mkstemp(prefix=".snapshot.", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    return target, len(encoded)


def _verify_catalog_row_shape(row: Mapping[str, object], *, snapshot_id: str) -> None:
    if row.get("id") != snapshot_id or row.get("snapshot_id") != snapshot_id:
        raise EvidenceSnapshotError("evidence catalog snapshot identity mismatch")
    if row.get("schema_version") != EVIDENCE_SCHEMA_VERSION:
        raise EvidenceSnapshotError("evidence catalog schema version mismatch")
    if row.get("state") != "complete":
        raise EvidenceSnapshotError("evidence catalog snapshot is not complete")
    sources = row.get("source_namespaces")
    branches = row.get("branch_namespaces")
    if not isinstance(sources, list) or not isinstance(branches, list) or len(sources) != len(branches):
        raise EvidenceSnapshotError("evidence catalog namespace lists are invalid")
    if sources != sorted(sources) or len(sources) != len(set(sources)):
        raise EvidenceSnapshotError("evidence catalog sources are not unique and sorted")
    if row.get("namespace_count") != len(sources):
        raise EvidenceSnapshotError("evidence catalog namespace count mismatch")


def _verify_snapshot_identity(
    row: Mapping[str, object], *, snapshot_id: str
) -> tuple[dict[str, dict[str, object]], str]:
    import hashlib

    identity = _json_object_field(row, "source_identity_json")
    sources_value = identity.get("sources")
    if (
        identity.get("schema_version") != EVIDENCE_SCHEMA_VERSION
        or identity.get("region") != row.get("region")
        or not isinstance(sources_value, list)
    ):
        raise EvidenceSnapshotError("catalog snapshot identity is invalid")
    required = {
        "namespace", "site_id", "last_plan_id", "last_apply_id",
        "active_rows", "retained_stale_rows", "deleted_rows", "total_rows",
        "logical_hash", "card_revision", "embedding_model",
        "embedding_precision", "vector_dimensions", "plan_schema_version",
    }
    by_source: dict[str, dict[str, object]] = {}
    for value in sources_value:
        if not isinstance(value, dict) or set(value) != required:
            raise EvidenceSnapshotError("catalog source identity is invalid")
        namespace = value.get("namespace")
        if not isinstance(namespace, str) or namespace in by_source:
            raise EvidenceSnapshotError("catalog source identity is invalid")
        by_source[namespace] = value
    sources = list(row["source_namespaces"])
    if list(by_source) != sources:
        raise EvidenceSnapshotError("catalog source identity order mismatch")
    identity_digest = logical_hash(identity)
    if snapshot_id != f"evidence_{identity_digest[:16]}":
        raise EvidenceSnapshotError("catalog source identity does not match snapshot ID")
    expected_branches = [
        f"buoy-evidence-branch-{identity_digest[:16]}-"
        f"{hashlib.sha256(namespace.encode('utf-8')).hexdigest()[:16]}"
        for namespace in sources
    ]
    if row.get("branch_namespaces") != expected_branches:
        raise EvidenceSnapshotError("catalog branch names do not match snapshot identity")
    if row.get("ledger_namespace") != f"buoy-evidence-ledger-{identity_digest[:16]}":
        raise EvidenceSnapshotError("catalog ledger name does not match snapshot identity")
    projections = {
        "source_state_hashes_json": {name: value["logical_hash"] for name, value in by_source.items()},
        "last_plan_ids_json": {name: value["last_plan_id"] for name, value in by_source.items()},
        "last_apply_ids_json": {name: value["last_apply_id"] for name, value in by_source.items()},
        "catalog_card_revisions_json": {name: value["card_revision"] for name, value in by_source.items()},
    }
    for field, expected in projections.items():
        if _json_object_field(row, field) != expected:
            raise EvidenceSnapshotError(f"catalog field {field} conflicts with snapshot identity")
    return by_source, identity_digest


def verify_evidence_snapshot(
    client: RemoteClient,
    *,
    snapshot_id: str,
    manifest_path: Path | None = None,
    _metrics: dict[str, int] | None = None,
) -> dict[str, object]:
    if not isinstance(snapshot_id, str) or not snapshot_id.startswith("evidence_"):
        raise EvidenceSnapshotError("snapshot ID is invalid")
    metrics = _new_metrics() if _metrics is None else _metrics
    row = _read_catalog_row(client, snapshot_id=snapshot_id, metrics=metrics)
    if row is None:
        raise EvidenceSnapshotError(f"completed snapshot {snapshot_id!r} was not found")
    _verify_catalog_row_shape(row, snapshot_id=snapshot_id)
    identity_sources, identity_digest = _verify_snapshot_identity(
        row, snapshot_id=snapshot_id
    )
    observations = _json_object_field(row, "branch_observations_json")
    sources = list(row["source_namespaces"])
    branches = list(row["branch_namespaces"])
    if set(observations) != set(sources):
        raise EvidenceSnapshotError("catalog branch observations do not match sources")
    ledger_resource = client.namespace(str(row["ledger_namespace"]))
    if not _resource_exists(ledger_resource, metrics=metrics):
        raise EvidenceSnapshotError("snapshot ledger namespace is missing")
    ledger_metadata = _metadata(ledger_resource, metrics=metrics)
    _validate_exact_schema(ledger_metadata, LEDGER_SCHEMA)
    ledger_hash, counts = _hash_ledger(
        resource=ledger_resource, snapshot_id=snapshot_id, metrics=metrics
    )
    expected_counts = {
        "active": row["active_row_count"],
        "retained_stale": row["retained_stale_row_count"],
        "deleted": row["deleted_row_count"],
        "total": row["exact_ledger_row_count"],
    }
    if counts != expected_counts or ledger_hash != row.get("ledger_logical_hash"):
        raise EvidenceSnapshotError("remote snapshot ledger hash or counts mismatch")
    recomputed_source_hashes: dict[str, str] = {}
    recomputed_source_counts = {"active": 0, "retained_stale": 0, "deleted": 0, "total": 0}
    for source_namespace, branch_namespace in zip(sources, branches, strict=True):
        observation = observations.get(source_namespace)
        if (
            not isinstance(observation, dict)
            or observation.get("namespace") != branch_namespace
            or observation.get("parent") != source_namespace
        ):
            raise EvidenceSnapshotError("catalog branch observation is invalid")
        branch = client.namespace(str(branch_namespace))
        if not _resource_exists(branch, metrics=metrics):
            raise EvidenceSnapshotError(
                f"evidence branch for namespace {source_namespace!r} is missing"
            )
        metadata = _metadata(branch, metrics=metrics)
        _assert_branch_observation(
            metadata,
            expected=observation,
            namespace=str(branch_namespace),
            parent=str(source_namespace),
            phase="since snapshot creation",
        )
        source_hash, site_id, source_counts = _reconcile_branch_with_ledger(
            branch=branch,
            ledger=ledger_resource,
            snapshot_id=snapshot_id,
            source_namespace=str(source_namespace),
            expected_branch_namespace=str(branch_namespace),
            metrics=metrics,
        )
        identity = identity_sources[str(source_namespace)]
        if source_hash != identity.get("logical_hash") or site_id != identity.get("site_id"):
            raise EvidenceSnapshotError(
                f"remote ledger source fingerprint mismatch for namespace {source_namespace!r}"
            )
        expected_source_counts = {
            "active": identity.get("active_rows"),
            "retained_stale": identity.get("retained_stale_rows"),
            "deleted": identity.get("deleted_rows"),
            "total": identity.get("total_rows"),
        }
        if source_counts != expected_source_counts:
            raise EvidenceSnapshotError(
                f"remote ledger source counts mismatch for namespace {source_namespace!r}"
            )
        recomputed_source_hashes[str(source_namespace)] = source_hash
        for key in recomputed_source_counts:
            recomputed_source_counts[key] += source_counts[key]
    if recomputed_source_counts != counts or recomputed_source_hashes != _json_object_field(
        row, "source_state_hashes_json"
    ):
        raise EvidenceSnapshotError("remote ledger source fingerprints mismatch")
    snapshot_hash = logical_hash(
        {
            "snapshot_identity_hash": identity_digest,
            "ledger_logical_hash": ledger_hash,
            "counts": counts,
        }
    )
    if snapshot_hash != row.get("snapshot_logical_hash"):
        raise EvidenceSnapshotError("evidence catalog snapshot logical hash mismatch")
    catalog_manifest = _manifest_from_catalog(
        row, activity=_base_activity(writes=True, manifest=True)
    )
    if catalog_manifest.get("manifest_hash") != row.get("manifest_hash"):
        raise EvidenceSnapshotError("evidence catalog manifest hash mismatch")
    if manifest_path is not None:
        if not Path(manifest_path).exists():
            raise EvidenceSnapshotError("supplied local snapshot manifest does not exist")
        try:
            manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise EvidenceSnapshotError("local snapshot manifest is invalid") from exc
        if not isinstance(manifest, dict) or manifest_hash(manifest) != manifest.get("manifest_hash"):
            raise EvidenceSnapshotError("local snapshot manifest hash mismatch")
        if manifest != catalog_manifest:
            raise EvidenceSnapshotError("local snapshot manifest does not match remote snapshot")
    return {
        "command": "evidence verify",
        "snapshot_id": snapshot_id,
        "namespace_count": len(sources),
        "ledger_row_count": counts["total"],
        "active_rows": counts["active"],
        "retained_stale_rows": counts["retained_stale"],
        "deleted_rows": counts["deleted"],
        "snapshot_logical_hash": snapshot_hash,
        "verified": True,
        "approximate_remote_logical_bytes": row["approximate_logical_bytes"],
        **_base_activity(writes=False, manifest=False),
        **metrics,
    }


def create_evidence_snapshot(
    client: RemoteClient,
    *,
    namespaces: Sequence[str],
    state_root: Path,
    region: str,
    embedding_model: str,
    embedding_precision: str,
    out_root: Path = DEFAULT_EVIDENCE_OUT_ROOT,
    maximum_rows: int = DEFAULT_MAXIMUM_ROWS,
    maximum_remote_logical_bytes: int = DEFAULT_MAXIMUM_REMOTE_LOGICAL_BYTES,
    catalog_reader: CatalogReader = read_remote_catalog,
) -> dict[str, object]:
    selected = validate_namespace_selection(namespaces)
    sources = discover_local_sources(namespaces=selected, state_root=state_root)
    compatibility = CompatibilityContract(region, embedding_model, embedding_precision)
    try:
        routing = catalog_reader(client, region=region, compatibility=compatibility)
    except (RemoteCatalogError, ValueError) as exc:
        raise EvidenceSnapshotError(f"routing-catalog compatibility read failed: {exc}") from exc
    cards = _cards_for_sources(
        snapshot=routing,
        sources=sources,
        region=region,
        embedding_model=embedding_model,
        embedding_precision=embedding_precision,
    )
    metrics = _new_metrics()
    _capture_catalog_metrics(routing, metrics)
    created: list[tuple[str, str | None]] = []
    uncertain: set[str] = set()
    snapshot_id_for_cleanup: str | None = None
    finalized = False
    started = time.monotonic()
    try:
        with acquire_evidence_apply_locks(sources, state_root=state_root):
            fingerprints = [
                fingerprint_source(source, state_root=state_root) for source in sources
            ]
            source_metadata: dict[str, dict[str, object]] = {}
            approximate_bytes = 0
            for source in sources:
                metadata = _metadata(client.namespace(source.namespace), metrics=metrics)
                observed = _validate_source_metadata(
                    namespace=source.namespace,
                    metadata=metadata,
                    vector_dimensions=cards[source.namespace].vector_dimensions,
                )
                source_metadata[source.namespace] = observed
                approximate_bytes += int(observed["approximate_logical_bytes"])
            total_rows = sum(item.total_rows for item in fingerprints)
            validate_limits(
                row_count=total_rows,
                approximate_logical_bytes=approximate_bytes,
                maximum_rows=maximum_rows,
                maximum_remote_logical_bytes=maximum_remote_logical_bytes,
            )
            names = derive_snapshot_names(
                region=region, fingerprints=fingerprints, cards=cards
            )
            snapshot_id_for_cleanup = names.snapshot_id
            existing = _read_catalog_row(
                client, snapshot_id=names.snapshot_id, metrics=metrics
            )
            creation_activity = _base_activity(writes=True, manifest=True)
            if existing is not None:
                verified = verify_evidence_snapshot(
                    client, snapshot_id=names.snapshot_id, _metrics=metrics
                )
                if existing.get("ledger_namespace") != names.ledger_namespace or existing.get("branch_namespaces") != [names.branches[value] for value in selected]:
                    raise EvidenceSnapshotError("completed snapshot conflicts with deterministic identity")
                manifest = _manifest_from_catalog(
                    existing, activity=creation_activity
                )
                if manifest["manifest_hash"] != existing.get("manifest_hash"):
                    raise EvidenceSnapshotError("completed snapshot manifest hash conflicts")
                reuse_activity = _base_activity(writes=False, manifest=True)
                path, local_bytes = _write_manifest(
                    out_root=out_root,
                    snapshot_id=names.snapshot_id,
                    manifest=manifest,
                )
                return {
                    "command": "evidence snapshot",
                    "snapshot_id": names.snapshot_id,
                    "local_manifest_path": str(path),
                    "local_bytes_written": local_bytes,
                    "evidence_catalog_namespace": EVIDENCE_CATALOG_NAMESPACE,
                    "ledger_namespace": names.ledger_namespace,
                    "branch_namespaces": [names.branches[value] for value in selected],
                    "namespace_count": len(selected),
                    "active_rows": verified["active_rows"],
                    "retained_stale_rows": verified["retained_stale_rows"],
                    "deleted_rows": verified["deleted_rows"],
                    "approximate_remote_logical_bytes": verified[
                        "approximate_remote_logical_bytes"
                    ],
                    "reused_snapshot": True,
                    **reuse_activity,
                    **metrics,
                }

            activity = creation_activity
            observations: dict[str, dict[str, object]] = {}
            for source in sources:
                branch_name = names.branches[source.namespace]
                branch = client.namespace(branch_name)
                if _resource_exists(branch, metrics=metrics):
                    metadata = _metadata(branch, metrics=metrics)
                    branching = _plain(metadata.get("branching"))
                    parent = branching.get("parent") if isinstance(branching, dict) else None
                    if parent != source.namespace:
                        raise EvidenceSnapshotError(
                            f"incomplete branch collision for namespace {source.namespace!r}"
                        )
                    metrics["branch_reuse_count"] += 1
                else:
                    try:
                        branch_response = _safe_call(
                            "branch create",
                            branch.branch_from,
                            source_namespace=source.namespace,
                        )
                    except Exception:
                        uncertain.add(branch_name)
                        raise
                    _capture_billing(branch_response, metrics)
                    # Only a definite success proves this invocation created it.
                    created.append((branch_name, source.namespace))
                    metrics["branch_create_count"] += 1
                    metrics["branch_calls"] += 1
                    metadata = _metadata(branch, metrics=metrics)
                observations[source.namespace] = _branch_observation(
                    metadata, namespace=branch_name, parent=source.namespace
                )

            ledger_resource = client.namespace(names.ledger_namespace)
            ledger_exists = _resource_exists(ledger_resource, metrics=metrics)
            if ledger_exists:
                # Deterministic incomplete resources may be left by a prior
                # post-ledger/pre-catalog failure. Reuse only a complete exact
                # ledger that reconciles to the locked local fingerprints and
                # the exact deterministic branches. Never patch a collision.
                _validate_existing_ledger(
                    client=client,
                    resource=ledger_resource,
                    snapshot_id=names.snapshot_id,
                    sources=sources,
                    fingerprints=fingerprints,
                    branch_namespaces=names.branches,
                    metrics=metrics,
                )
            else:
                ledger_marked_created = False

                def mark_ledger_created() -> None:
                    nonlocal ledger_marked_created
                    if not ledger_marked_created:
                        created.append((names.ledger_namespace, None))
                        ledger_marked_created = True
                        uncertain.discard(names.ledger_namespace)

                def mark_ledger_uncertain() -> None:
                    uncertain.add(names.ledger_namespace)

                first_batch = True
                for source in sources:
                    first_batch = _write_ledger(
                        resource=ledger_resource,
                        source=source,
                        state_root=state_root,
                        snapshot_id=names.snapshot_id,
                        branch_namespace=names.branches[source.namespace],
                        first_batch=first_batch,
                        metrics=metrics,
                        mark_created=mark_ledger_created,
                        mark_uncertain=mark_ledger_uncertain,
                    )
                if first_batch:
                    response = _safe_call(
                        "empty ledger schema write", ledger_resource.write, schema=LEDGER_SCHEMA
                    )
                    metrics["ledger_write_calls"] += 1
                    _write_count(response, expected=0, kind="empty ledger schema write")
                ledger_metadata = _metadata(ledger_resource, metrics=metrics)
                _validate_exact_schema(ledger_metadata, LEDGER_SCHEMA)

            # Re-read every remote ledger row and reconcile it to both the
            # locked local fingerprints and its immutable branch immediately
            # before publication. This deliberately repeats validation for a
            # reused ledger so a mutation after the initial collision check
            # cannot be finalized.
            ledger_hash, counts = _validate_existing_ledger(
                client=client,
                resource=ledger_resource,
                snapshot_id=names.snapshot_id,
                sources=sources,
                fingerprints=fingerprints,
                branch_namespaces=names.branches,
                metrics=metrics,
            )
            # Exact ledger verification is complete; branch metadata must
            # remain stable through this final pre-publication check.
            for source in sources:
                after = _metadata(
                    client.namespace(names.branches[source.namespace]), metrics=metrics
                )
                observation = observations[source.namespace]
                _assert_branch_observation(
                    after,
                    expected=observation,
                    namespace=names.branches[source.namespace],
                    parent=source.namespace,
                    phase="before finalization",
                )

            source_hashes = {item.namespace: item.logical_hash for item in fingerprints}
            source_identity = snapshot_identity_payload(
                region=region, fingerprints=fingerprints, cards=cards
            )
            identity_digest = logical_hash(source_identity)
            snapshot_hash = logical_hash(
                {
                    "snapshot_identity_hash": identity_digest,
                    "ledger_logical_hash": ledger_hash,
                    "counts": counts,
                }
            )
            created_at = datetime.now(timezone.utc).isoformat()
            branch_names = [names.branches[value] for value in selected]
            manifest_preview = {
                "schema_version": EVIDENCE_SCHEMA_VERSION,
                "snapshot_id": names.snapshot_id,
                "created_at": created_at,
                "region": region,
                "source_namespaces": list(selected),
                "branch_namespaces": branch_names,
                "ledger_namespace": names.ledger_namespace,
                "evidence_catalog_namespace": EVIDENCE_CATALOG_NAMESPACE,
                "namespace_count": len(selected),
                "active_row_count": counts["active"],
                "retained_stale_row_count": counts["retained_stale"],
                "deleted_row_count": counts["deleted"],
                "approximate_remote_logical_bytes": approximate_bytes,
                "snapshot_logical_hash": snapshot_hash,
                "activity": dict(activity),
            }
            calculated_manifest_hash = manifest_hash(manifest_preview)
            manifest_preview["manifest_hash"] = calculated_manifest_hash
            catalog_row = {
                "id": _catalog_row_id(names.snapshot_id),
                "snapshot_id": names.snapshot_id,
                "schema_version": EVIDENCE_SCHEMA_VERSION,
                "state": "complete",
                "created_at": created_at,
                "region": region,
                "source_namespaces": list(selected),
                "branch_namespaces": branch_names,
                "ledger_namespace": names.ledger_namespace,
                "namespace_count": len(selected),
                "active_row_count": counts["active"],
                "retained_stale_row_count": counts["retained_stale"],
                "deleted_row_count": counts["deleted"],
                "source_state_hashes_json": canonical_json(source_hashes),
                "source_identity_json": canonical_json(source_identity),
                "last_plan_ids_json": canonical_json({item.namespace: item.last_plan_id for item in fingerprints}),
                "last_apply_ids_json": canonical_json({item.namespace: item.last_apply_id for item in fingerprints}),
                "catalog_card_revisions_json": canonical_json({value: cards[value].card_revision for value in selected}),
                "branch_observations_json": canonical_json(observations),
                "approximate_logical_bytes": approximate_bytes,
                "exact_ledger_row_count": total_rows,
                "ledger_logical_hash": ledger_hash,
                "snapshot_logical_hash": snapshot_hash,
                "manifest_hash": calculated_manifest_hash,
            }
            catalog_resource = client.namespace(EVIDENCE_CATALOG_NAMESPACE)
            response = _safe_call(
                "catalog finalization",
                catalog_resource.write,
                schema=CATALOG_SCHEMA,
                upsert_rows=[catalog_row],
                upsert_condition=("id", "Eq", None),
                return_affected_ids=True,
            )
            metrics["catalog_write_calls"] += 1
            _capture_billing(response, metrics)
            response_plain = _plain(response)
            affected = response_plain.get("rows_affected") if isinstance(response_plain, dict) else None
            if affected == 0:
                raced = _read_catalog_row(
                    client, snapshot_id=names.snapshot_id, metrics=metrics
                )
                if (
                    raced is None
                    or raced.get("state") != "complete"
                    or raced.get("snapshot_logical_hash") != snapshot_hash
                    or raced.get("ledger_namespace") != names.ledger_namespace
                    or raced.get("branch_namespaces") != branch_names
                ):
                    raise EvidenceSnapshotError(
                        "conditional catalog finalization conflicted with remote state"
                    )
                verify_evidence_snapshot(
                    client, snapshot_id=names.snapshot_id, _metrics=metrics
                )
                manifest_preview = _manifest_from_catalog(raced, activity=activity)
                if manifest_preview["manifest_hash"] != raced.get("manifest_hash"):
                    raise EvidenceSnapshotError(
                        "concurrent completed snapshot manifest hash conflicts"
                    )
            elif affected == 1:
                affected_ids = response_plain.get("upserted_ids")
                if affected_ids != [_catalog_row_id(names.snapshot_id)]:
                    raise EvidenceSnapshotError(
                        "remote catalog finalization returned unexpected affected IDs"
                    )
                metrics["catalog_rows_written"] = 1
            else:
                raise EvidenceSnapshotError(
                    f"remote catalog finalization affected {affected!r} rows; expected 1"
                )
            finalized = True
            path, local_bytes = _write_manifest(
                out_root=out_root,
                snapshot_id=names.snapshot_id,
                manifest=manifest_preview,
            )
            return {
                "command": "evidence snapshot",
                "snapshot_id": names.snapshot_id,
                "snapshot_logical_hash": snapshot_hash,
                "local_manifest_path": str(path),
                "local_bytes_written": local_bytes,
                "evidence_catalog_namespace": EVIDENCE_CATALOG_NAMESPACE,
                "ledger_namespace": names.ledger_namespace,
                "branch_namespaces": branch_names,
                "namespace_count": len(selected),
                "active_rows": counts["active"],
                "retained_stale_rows": counts["retained_stale"],
                "deleted_rows": counts["deleted"],
                "approximate_remote_logical_bytes": approximate_bytes,
                "reused_snapshot": False,
                "elapsed_reconciliation_seconds": round(time.monotonic() - started, 6),
                **activity,
                **metrics,
            }
    except Exception as primary:
        if finalized:
            raise
        completion_uncertain = False
        if snapshot_id_for_cleanup is not None:
            try:
                completed_row = _read_catalog_row(
                    client, snapshot_id=snapshot_id_for_cleanup, metrics=metrics
                )
                completion_uncertain = (
                    completed_row is not None and completed_row.get("state") == "complete"
                )
            except Exception:
                completion_uncertain = True
        incomplete = sorted(
            {namespace for namespace, _ in created} | uncertain
        )
        # Deterministic names are shared by concurrent hosts. Even a definite
        # create response cannot prove that another invocation has not begun
        # reusing the namespace or finalized immediately after a catalog read.
        # Report owned incomplete resources rather than risk deleting concurrent,
        # preexisting, or completed evidence.
        if completion_uncertain:
            raise EvidenceSnapshotError(
                f"{primary}; completed catalog state exists or could not be ruled out, so internal cleanup was skipped"
            ) from primary
        if incomplete:
            raise EvidenceSnapshotError(
                f"{primary}; no valid snapshot was finalized; conservatively retained incomplete internal namespaces: {incomplete}"
            ) from primary
        raise
