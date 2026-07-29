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
    ledger_row,
    logical_hash,
    manifest_hash,
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
        "last_write_at": str(metadata.get("last_write_at", "")),
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


def _reconcile_branch_with_local(
    *,
    resource: NamespaceResource,
    source: LocalEvidenceSource,
    state_root: Path,
    metrics: dict[str, int],
) -> None:
    remote = iter(
        _query_rows(
            resource,
            include_attributes=RECONCILIATION_ATTRIBUTES,
            metrics=metrics,
        )
    )
    current_remote = next(remote, None)
    with stream_applied_state_rows(
        database_path=source.database_path,
        state_root=state_root,
        batch_size=LOCAL_ROW_BATCH_SIZE,
    ) as stream:
        for local in stream.rows:
            if local.status == "deleted":
                if current_remote is not None and current_remote.get("id") == local.row_id:
                    raise EvidenceSnapshotError(
                        f"namespace {source.namespace!r} category deleted_present row {local.row_id!r}"
                    )
                continue
            if current_remote is None:
                raise EvidenceSnapshotError(
                    f"namespace {source.namespace!r} category missing row {local.row_id!r}"
                )
            remote_id = current_remote.get("id")
            if remote_id != local.row_id:
                category = "unexpected" if str(remote_id) < local.row_id else "missing"
                raise EvidenceSnapshotError(
                    f"namespace {source.namespace!r} category {category} row {str(remote_id if category == 'unexpected' else local.row_id)!r}"
                )
            expected = {
                "id": local.row_id,
                "canonical_url": local.canonical_url,
                "page_hash": local.page_hash,
                "chunk_hash": local.chunk_hash,
                "embedding_text_hash": local.embedding_text_hash,
                "plan_id": local.plan_id,
                "applied_at": local.applied_at,
            }
            mismatch = _row_matches(expected, current_remote)
            if mismatch is not None:
                raise EvidenceSnapshotError(
                    f"namespace {source.namespace!r} category {mismatch}_mismatch row {local.row_id!r}"
                )
            current_remote = next(remote, None)
    if current_remote is not None:
        raise EvidenceSnapshotError(
            f"namespace {source.namespace!r} category unexpected row {str(current_remote.get('id'))!r}"
        )


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


def _write_ledger(
    *,
    resource: NamespaceResource,
    source: LocalEvidenceSource,
    state_root: Path,
    snapshot_id: str,
    branch_namespace: str,
    first_batch: bool,
    metrics: dict[str, int],
) -> bool:
    batch: list[dict[str, object]] = []
    with stream_applied_state_rows(
        database_path=source.database_path,
        state_root=state_root,
        batch_size=LOCAL_ROW_BATCH_SIZE,
    ) as stream:
        for ordinal, row in enumerate(stream.rows):
            batch.append(
                ledger_row(
                    snapshot_id=snapshot_id,
                    source=source,
                    branch_namespace=branch_namespace,
                    row=row,
                    ordinal=ordinal,
                )
            )
            if len(batch) == LEDGER_WRITE_BATCH_SIZE:
                kwargs: dict[str, object] = {"upsert_rows": batch}
                if first_batch:
                    kwargs["schema"] = LEDGER_SCHEMA
                response = _safe_call("ledger write", resource.write, **kwargs)
                metrics["ledger_write_calls"] += 1
                _capture_billing(response, metrics)
                _write_count(response, expected=len(batch), kind="ledger write")
                metrics["ledger_rows_written"] += len(batch)
                first_batch = False
                batch = []
        if batch:
            kwargs = {"upsert_rows": batch}
            if first_batch:
                kwargs["schema"] = LEDGER_SCHEMA
            response = _safe_call("ledger write", resource.write, **kwargs)
            metrics["ledger_write_calls"] += 1
            _capture_billing(response, metrics)
            _write_count(response, expected=len(batch), kind="ledger write")
            metrics["ledger_rows_written"] += len(batch)
            first_batch = False
    return first_batch


def _hash_ledger(
    *, resource: NamespaceResource, snapshot_id: str, metrics: dict[str, int]
) -> tuple[str, dict[str, int]]:
    import hashlib

    digest = hashlib.sha256()
    counts = {"active": 0, "retained_stale": 0, "deleted": 0, "total": 0}
    seen_ids: set[str] = set()
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
        row_id = str(row["id"])
        if row_id in seen_ids:
            raise EvidenceSnapshotError("remote ledger contains a duplicate row")
        seen_ids.add(row_id)
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
    source_namespace: str,
    metrics: dict[str, int],
) -> None:
    remote = iter(
        _query_rows(
            branch,
            include_attributes=RECONCILIATION_ATTRIBUTES,
            metrics=metrics,
        )
    )
    branch_row = next(remote, None)
    for expected in _ledger_rows_for_source(
        ledger, source_namespace=source_namespace, metrics=metrics
    ):
        source_row_id = expected["source_row_id"]
        if expected["status"] == "deleted":
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


def verify_evidence_snapshot(
    client: RemoteClient,
    *,
    snapshot_id: str,
    manifest_path: Path | None = None,
) -> dict[str, object]:
    if not isinstance(snapshot_id, str) or not snapshot_id.startswith("evidence_"):
        raise EvidenceSnapshotError("snapshot ID is invalid")
    metrics = _new_metrics()
    row = _read_catalog_row(client, snapshot_id=snapshot_id, metrics=metrics)
    if row is None:
        raise EvidenceSnapshotError(f"completed snapshot {snapshot_id!r} was not found")
    _verify_catalog_row_shape(row, snapshot_id=snapshot_id)
    observations = _json_object_field(row, "branch_observations_json")
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
    sources = list(row["source_namespaces"])
    branches = list(row["branch_namespaces"])
    for source_namespace, branch_namespace in zip(sources, branches, strict=True):
        observation = observations.get(source_namespace)
        if not isinstance(observation, dict):
            raise EvidenceSnapshotError("catalog branch observation is missing")
        branch = client.namespace(str(branch_namespace))
        if not _resource_exists(branch, metrics=metrics):
            raise EvidenceSnapshotError(
                f"evidence branch for namespace {source_namespace!r} is missing"
            )
        metadata = _metadata(branch, metrics=metrics)
        branching = _plain(metadata.get("branching"))
        parent = branching.get("parent") if isinstance(branching, dict) else None
        if parent != source_namespace:
            raise EvidenceSnapshotError(
                f"evidence branch parent mismatch for namespace {source_namespace!r}"
            )
        for field in ("created_at", "last_write_at", "approx_row_count", "approx_logical_bytes"):
            if metadata.get(field) != observation.get(field):
                raise EvidenceSnapshotError(
                    f"evidence branch metadata changed for namespace {source_namespace!r}: {field}"
                )
        _reconcile_branch_with_ledger(
            branch=branch,
            ledger=ledger_resource,
            source_namespace=str(source_namespace),
            metrics=metrics,
        )
    snapshot_hash = logical_hash(
        {
            "schema_version": row["schema_version"],
            "snapshot_id": snapshot_id,
            "source_state_hashes": _json_object_field(row, "source_state_hashes_json"),
            "ledger_logical_hash": ledger_hash,
            "counts": counts,
        }
    )
    if snapshot_hash != row.get("snapshot_logical_hash"):
        raise EvidenceSnapshotError("evidence catalog snapshot logical hash mismatch")
    if manifest_path is not None and Path(manifest_path).exists():
        try:
            manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise EvidenceSnapshotError("local snapshot manifest is invalid") from exc
        if not isinstance(manifest, dict) or manifest_hash(manifest) != manifest.get("manifest_hash"):
            raise EvidenceSnapshotError("local snapshot manifest hash mismatch")
        if manifest.get("snapshot_id") != snapshot_id or manifest.get("snapshot_logical_hash") != snapshot_hash:
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
            activity = _base_activity(writes=True, manifest=True)
            if existing is not None:
                verified = verify_evidence_snapshot(client, snapshot_id=names.snapshot_id)
                if existing.get("ledger_namespace") != names.ledger_namespace or existing.get("branch_namespaces") != [names.branches[value] for value in selected]:
                    raise EvidenceSnapshotError("completed snapshot conflicts with deterministic identity")
                manifest = _manifest_from_catalog(existing, activity=activity)
                if manifest["manifest_hash"] != existing.get("manifest_hash"):
                    raise EvidenceSnapshotError("completed snapshot manifest hash conflicts")
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
                    "approximate_remote_logical_bytes": approximate_bytes,
                    "reused_snapshot": True,
                    **activity,
                    **metrics,
                }

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
                        # A transport failure can happen after server-side creation.
                        # Track the deterministic destination so guarded cleanup can
                        # inspect parentage instead of silently losing the resource.
                        created.append((branch_name, source.namespace))
                        raise
                    _capture_billing(branch_response, metrics)
                    created.append((branch_name, source.namespace))
                    metrics["branch_create_count"] += 1
                    metrics["branch_calls"] += 1
                    metadata = _metadata(branch, metrics=metrics)
                branching = _plain(metadata.get("branching"))
                parent = branching.get("parent") if isinstance(branching, dict) else None
                if parent != source.namespace:
                    raise EvidenceSnapshotError(
                        f"evidence branch parent mismatch for namespace {source.namespace!r}"
                    )
                observations[source.namespace] = {
                    "namespace": branch_name,
                    "parent": source.namespace,
                    "created_at": metadata.get("created_at"),
                    "last_write_at": metadata.get("last_write_at"),
                    "approx_row_count": metadata.get("approx_row_count"),
                    "approx_logical_bytes": metadata.get("approx_logical_bytes"),
                }

            ledger_resource = client.namespace(names.ledger_namespace)
            if _resource_exists(ledger_resource, metrics=metrics):
                raise EvidenceSnapshotError("incomplete snapshot ledger collision")
            created.append((names.ledger_namespace, None))
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
                )
            if first_batch:
                response = _safe_call(
                    "empty ledger schema write", ledger_resource.write, schema=LEDGER_SCHEMA
                )
                metrics["ledger_write_calls"] += 1
                _write_count(response, expected=0, kind="empty ledger schema write")
            ledger_metadata = _metadata(ledger_resource, metrics=metrics)
            _validate_exact_schema(ledger_metadata, LEDGER_SCHEMA)

            for source in sources:
                branch = client.namespace(names.branches[source.namespace])
                _reconcile_branch_with_local(
                    resource=branch,
                    source=source,
                    state_root=state_root,
                    metrics=metrics,
                )
                after = _metadata(branch, metrics=metrics)
                observation = observations[source.namespace]
                for field in ("created_at", "last_write_at", "approx_row_count", "approx_logical_bytes"):
                    if after.get(field) != observation.get(field):
                        raise EvidenceSnapshotError(
                            f"evidence branch changed during reconciliation for namespace {source.namespace!r}"
                        )

            ledger_hash, counts = _hash_ledger(
                resource=ledger_resource,
                snapshot_id=names.snapshot_id,
                metrics=metrics,
            )
            expected_counts = {
                "active": sum(item.active_rows for item in fingerprints),
                "retained_stale": sum(item.retained_stale_rows for item in fingerprints),
                "deleted": sum(item.deleted_rows for item in fingerprints),
                "total": total_rows,
            }
            if counts != expected_counts:
                raise EvidenceSnapshotError("remote snapshot ledger status counts mismatch")
            source_hashes = {item.namespace: item.logical_hash for item in fingerprints}
            snapshot_hash = logical_hash(
                {
                    "schema_version": EVIDENCE_SCHEMA_VERSION,
                    "snapshot_id": names.snapshot_id,
                    "source_state_hashes": source_hashes,
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
                verify_evidence_snapshot(client, snapshot_id=names.snapshot_id)
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
        leaked: list[str] = []
        completed_during_failure = False
        if not finalized and snapshot_id_for_cleanup is not None:
            try:
                completed_row = _read_catalog_row(
                    client, snapshot_id=snapshot_id_for_cleanup, metrics=metrics
                )
                completed_during_failure = (
                    completed_row is not None and completed_row.get("state") == "complete"
                )
            except Exception:
                # An unreadable completion marker makes deletion unsafe.
                completed_during_failure = True
        if not finalized and not completed_during_failure:
            for namespace, expected_parent in reversed(created):
                resource = client.namespace(namespace)
                try:
                    if not namespace.startswith("buoy-evidence-"):
                        leaked.append(namespace)
                        continue
                    if not _resource_exists(resource, metrics=metrics):
                        continue
                    metadata = _metadata(resource, metrics=metrics)
                    if expected_parent is not None:
                        branching = _plain(metadata.get("branching"))
                        parent = branching.get("parent") if isinstance(branching, dict) else None
                        if parent != expected_parent:
                            leaked.append(namespace)
                            continue
                    else:
                        _validate_exact_schema(metadata, LEDGER_SCHEMA)
                    _safe_call("incomplete namespace cleanup", resource.delete_all)
                except Exception:
                    leaked.append(namespace)
        if completed_during_failure:
            raise EvidenceSnapshotError(
                f"{primary}; completed catalog state could not be ruled out, so internal cleanup was skipped"
            ) from primary
        if leaked:
            raise EvidenceSnapshotError(
                f"{primary}; no valid snapshot was finalized; incomplete internal namespaces: {sorted(leaked)}"
            ) from primary
        raise
