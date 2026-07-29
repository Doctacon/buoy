"""Deterministic local contracts for remote-first evidence snapshots.

This module is provider-inert. It reads only compact applied-state metadata and
streams applied rows; it never loads source adapters, embedding models, or full
remote content.
"""

from __future__ import annotations

from contextlib import ExitStack, contextmanager
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Iterator, Mapping, Sequence

from buoy_search.applied_state import (
    APPLIED_STATE_SCHEMA_VERSION,
    AppliedStateError,
    AppliedStateRow,
    AppliedStateSummary,
    acquire_namespace_apply_lock,
    load_applied_state_summary,
    stream_applied_state_rows,
)
from buoy_search.catalog import NamespaceCard
from buoy_search.remote_catalog import REMOTE_CATALOG_NAMESPACE

EVIDENCE_SCHEMA_VERSION = 1
EVIDENCE_INTERNAL_PREFIX = "buoy-evidence-"
EVIDENCE_CATALOG_NAMESPACE = "buoy-evidence-catalog-v1"
DEFAULT_EVIDENCE_OUT_ROOT = Path("artifacts/evidence-snapshots")
DEFAULT_MAXIMUM_ROWS = 1_000_000
DEFAULT_MAXIMUM_REMOTE_LOGICAL_BYTES = 5_368_709_120
MAX_SOURCE_NAMESPACES = 64
LOCAL_ROW_BATCH_SIZE = 1_000
LEDGER_WRITE_BATCH_SIZE = 1_000
REMOTE_PAGE_SIZE = 10_000
MAX_MANIFEST_BYTES = 256 * 1024
_NAMESPACE_ID = re.compile(r"^[A-Za-z0-9-_.]{1,128}$")


class EvidenceSnapshotError(ValueError):
    """Safe evidence-snapshot validation or reconciliation failure."""


@dataclass(frozen=True)
class LocalEvidenceSource:
    namespace: str
    site_id: str
    database_path: Path
    summary: AppliedStateSummary


@dataclass(frozen=True)
class StateFingerprint:
    namespace: str
    site_id: str
    last_plan_id: str
    last_apply_id: str
    active_rows: int
    retained_stale_rows: int
    deleted_rows: int
    total_rows: int
    logical_hash: str


@dataclass(frozen=True)
class SnapshotNames:
    snapshot_id: str
    ledger_namespace: str
    branches: Mapping[str, str]


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def logical_hash(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _update_ordered_hash(digest: "hashlib._Hash", value: object) -> None:
    encoded = canonical_json(value).encode("utf-8")
    digest.update(len(encoded).to_bytes(8, "big"))
    digest.update(encoded)


def validate_namespace_selection(namespaces: Sequence[str]) -> tuple[str, ...]:
    if not namespaces:
        raise EvidenceSnapshotError("at least one --namespace is required")
    if len(namespaces) > MAX_SOURCE_NAMESPACES:
        raise EvidenceSnapshotError(
            f"at most {MAX_SOURCE_NAMESPACES} namespaces may be selected"
        )
    cleaned: list[str] = []
    for namespace in namespaces:
        if not isinstance(namespace, str) or _NAMESPACE_ID.fullmatch(namespace) is None:
            raise EvidenceSnapshotError(
                "namespace IDs must match [A-Za-z0-9-_.]{1,128}"
            )
        if namespace == REMOTE_CATALOG_NAMESPACE:
            raise EvidenceSnapshotError("the routing-catalog namespace cannot be evidence")
        if namespace.startswith(EVIDENCE_INTERNAL_PREFIX):
            raise EvidenceSnapshotError(
                f"reserved evidence namespace {namespace!r} cannot be a source"
            )
        cleaned.append(namespace)
    duplicate = next(
        (value for index, value in enumerate(cleaned) if value in cleaned[:index]),
        None,
    )
    if duplicate is not None:
        raise EvidenceSnapshotError(f"duplicate namespace {duplicate!r}")
    return tuple(sorted(cleaned))


def is_internal_evidence_namespace(namespace: str) -> bool:
    return namespace.startswith(EVIDENCE_INTERNAL_PREFIX)


def discover_local_sources(
    *, namespaces: Sequence[str], state_root: Path
) -> tuple[LocalEvidenceSource, ...]:
    selected = validate_namespace_selection(namespaces)
    root = Path(state_root)
    if root.is_symlink():
        raise EvidenceSnapshotError("applied-state root must not be a symlink")
    state_dir = root / "state"
    if not state_dir.is_dir() or state_dir.is_symlink():
        raise EvidenceSnapshotError("local applied state is missing")
    sources: list[LocalEvidenceSource] = []
    try:
        site_dirs = sorted(
            path for path in state_dir.iterdir() if path.is_dir() and not path.is_symlink()
        )
    except OSError as exc:
        raise EvidenceSnapshotError("local applied state could not be inspected") from exc
    for namespace in selected:
        matches: list[LocalEvidenceSource] = []
        for site_dir_path in site_dirs:
            database = site_dir_path / namespace / "state.duckdb"
            if not database.exists():
                continue
            try:
                summary = load_applied_state_summary(
                    database_path=database, state_root=root
                )
            except (AppliedStateError, OSError, ValueError) as exc:
                raise EvidenceSnapshotError(
                    f"local applied state for namespace {namespace!r} is invalid: {exc}"
                ) from exc
            if summary.namespace != namespace:
                raise EvidenceSnapshotError(
                    f"local applied state identity mismatch for namespace {namespace!r}"
                )
            matches.append(
                LocalEvidenceSource(namespace, summary.site_id, database, summary)
            )
        if not matches:
            raise EvidenceSnapshotError(
                f"local applied state is missing for namespace {namespace!r}"
            )
        if len(matches) != 1:
            raise EvidenceSnapshotError(
                f"local applied state is ambiguous for namespace {namespace!r}"
            )
        source = matches[0]
        if not source.summary.last_plan_id or not source.summary.last_apply_id:
            raise EvidenceSnapshotError(
                f"namespace {namespace!r} is a first-apply state and is not eligible"
            )
        if source.summary.total_rows == 0:
            raise EvidenceSnapshotError(
                f"namespace {namespace!r} has no applied-state rows and cannot publish an empty remote ledger"
            )
        sources.append(source)
    return tuple(sources)


@contextmanager
def acquire_evidence_apply_locks(
    sources: Sequence[LocalEvidenceSource], *, state_root: Path
) -> Iterator[None]:
    """Acquire every selected apply lock in deterministic namespace order."""

    with ExitStack() as stack:
        for source in sorted(sources, key=lambda item: item.namespace):
            stack.enter_context(
                acquire_namespace_apply_lock(
                    site_id=source.site_id,
                    namespace=source.namespace,
                    state_root=state_root,
                )
            )
        yield


def fingerprint_source(
    source: LocalEvidenceSource, *, state_root: Path
) -> StateFingerprint:
    digest = hashlib.sha256()
    counts = {"active": 0, "retained_stale": 0, "deleted": 0}
    with stream_applied_state_rows(
        database_path=source.database_path,
        state_root=state_root,
        batch_size=LOCAL_ROW_BATCH_SIZE,
    ) as stream:
        if stream.summary != source.summary:
            raise EvidenceSnapshotError(
                f"local applied state changed before fingerprinting {source.namespace!r}"
            )
        for ordinal, row in enumerate(stream.rows):
            counts[row.status] += 1
            _update_ordered_hash(
                digest,
                {
                    "ordinal": ordinal,
                    "row_id": row.row_id,
                    "canonical_url": row.canonical_url,
                    "page_hash": row.page_hash,
                    "chunk_hash": row.chunk_hash,
                    "embedding_text_hash": row.embedding_text_hash,
                    "plan_id": row.plan_id,
                    "applied_at": row.applied_at,
                    "status": row.status,
                },
            )
    summary = source.summary
    observed = (
        counts["active"],
        counts["retained_stale"],
        counts["deleted"],
    )
    expected = (
        summary.active_rows,
        summary.retained_stale_rows,
        summary.deleted_rows,
    )
    if observed != expected:
        raise EvidenceSnapshotError(
            f"local applied-state counts changed for namespace {source.namespace!r}"
        )
    return StateFingerprint(
        namespace=source.namespace,
        site_id=source.site_id,
        last_plan_id=summary.last_plan_id,
        last_apply_id=summary.last_apply_id,
        active_rows=summary.active_rows,
        retained_stale_rows=summary.retained_stale_rows,
        deleted_rows=summary.deleted_rows,
        total_rows=summary.total_rows,
        logical_hash=digest.hexdigest(),
    )


def validate_card_for_source(
    source: LocalEvidenceSource,
    card: NamespaceCard,
    *,
    region: str,
    embedding_model: str,
    embedding_precision: str,
) -> None:
    if not card.enabled:
        raise EvidenceSnapshotError(
            f"routing card for namespace {source.namespace!r} is disabled"
        )
    expected = {
        "namespace": source.namespace,
        "site_id": source.site_id,
        "region": region,
        "embedding_model": embedding_model,
        "embedding_precision": embedding_precision,
        "last_plan_id": source.summary.last_plan_id,
        "last_apply_id": source.summary.last_apply_id,
    }
    for field, value in expected.items():
        if getattr(card, field) != value:
            raise EvidenceSnapshotError(
                f"routing card compatibility mismatch for namespace {source.namespace!r}: {field}"
            )
    if card.plan_schema_version not in {1, 2}:
        raise EvidenceSnapshotError(
            f"routing card schema is incompatible for namespace {source.namespace!r}"
        )


def derive_snapshot_names(
    *,
    region: str,
    fingerprints: Sequence[StateFingerprint],
    cards: Mapping[str, NamespaceCard],
) -> SnapshotNames:
    ordered = sorted(fingerprints, key=lambda item: item.namespace)
    identity = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "region": region,
        "sources": [
            {
                **asdict(item),
                "card_revision": cards[item.namespace].card_revision,
                "embedding_model": cards[item.namespace].embedding_model,
                "embedding_precision": cards[item.namespace].embedding_precision,
                "vector_dimensions": cards[item.namespace].vector_dimensions,
                "plan_schema_version": cards[item.namespace].plan_schema_version,
            }
            for item in ordered
        ],
    }
    digest = logical_hash(identity)
    snapshot_id = f"evidence_{digest[:16]}"
    short = digest[:16]
    branches = {
        item.namespace: (
            f"buoy-evidence-branch-{short}-"
            f"{hashlib.sha256(item.namespace.encode('utf-8')).hexdigest()[:16]}"
        )
        for item in ordered
    }
    ledger = f"buoy-evidence-ledger-{short}"
    for value in [ledger, *branches.values()]:
        if len(value.encode("utf-8")) > 128 or _NAMESPACE_ID.fullmatch(value) is None:
            raise EvidenceSnapshotError("derived evidence namespace is invalid")
    return SnapshotNames(snapshot_id, ledger, branches)


def ledger_document_id(
    *, snapshot_id: str, source_namespace: str, source_row_id: str
) -> str:
    digest = logical_hash([snapshot_id, source_namespace, source_row_id])
    return f"el_{digest[:61]}"


def ledger_row(
    *,
    snapshot_id: str,
    source: LocalEvidenceSource,
    branch_namespace: str,
    row: AppliedStateRow,
    ordinal: int,
) -> dict[str, object]:
    return {
        "id": ledger_document_id(
            snapshot_id=snapshot_id,
            source_namespace=source.namespace,
            source_row_id=row.row_id,
        ),
        "snapshot_id": snapshot_id,
        "source_namespace": source.namespace,
        "branch_namespace": branch_namespace,
        "source_row_id": row.row_id,
        "site_id": source.site_id,
        "status": row.status,
        "canonical_url": row.canonical_url,
        "page_hash": row.page_hash,
        "chunk_hash": row.chunk_hash,
        "embedding_text_hash": row.embedding_text_hash,
        "plan_id": row.plan_id,
        "applied_at": row.applied_at,
        "ordinal": ordinal,
    }


def manifest_hash(payload: Mapping[str, object]) -> str:
    value = dict(payload)
    value.pop("manifest_hash", None)
    return logical_hash(value)


def validate_limits(
    *,
    row_count: int,
    approximate_logical_bytes: int,
    maximum_rows: int,
    maximum_remote_logical_bytes: int,
) -> None:
    if type(maximum_rows) is not int or maximum_rows < 1:
        raise EvidenceSnapshotError("--maximum-rows must be a positive integer")
    if (
        type(maximum_remote_logical_bytes) is not int
        or maximum_remote_logical_bytes < 1
    ):
        raise EvidenceSnapshotError(
            "--maximum-remote-logical-bytes must be a positive integer"
        )
    if row_count > maximum_rows:
        raise EvidenceSnapshotError(
            f"exact local ledger row count {row_count} exceeds --maximum-rows {maximum_rows}"
        )
    if approximate_logical_bytes > maximum_remote_logical_bytes:
        raise EvidenceSnapshotError(
            "approximate remote logical bytes "
            f"{approximate_logical_bytes} exceed --maximum-remote-logical-bytes "
            f"{maximum_remote_logical_bytes}"
        )
