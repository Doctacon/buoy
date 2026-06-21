"""Pure local incremental diffing for generic site RAG plans.

This module compares a desired plan manifest to local applied state. It does
not read credentials, load embedding models, crawl, or call turbopuffer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Literal

from turbo_search.applied_state import (
    ROW_STATUS_ACTIVE,
    ROW_STATUS_DELETED,
    ROW_STATUS_RETAINED_STALE,
    AppliedState,
    AppliedStateRow,
)
from turbo_search.plan_artifacts import ChunkManifestRecord, ManifestDocument, PageManifestRecord, normalize_json_object

ChunkAction = Literal["new", "changed", "reactivate_retained_stale"]
JsonObject = dict[str, Any]


class PlanDiffError(ValueError):
    """Raised when a manifest cannot be safely diffed."""


@dataclass(frozen=True)
class DesiredChunkDiffRecord:
    """One desired chunk classified for future apply."""

    row_id: str
    canonical_url: str
    page_hash: str
    chunk_hash: str
    embedding_text_hash: str
    section_path: str
    chunk_index: int
    action: ChunkAction
    previous_status: str | None = None
    previous_embedding_text_hash: str | None = None


@dataclass(frozen=True)
class UnchangedChunkDiffRecord:
    """One desired chunk already represented by active applied state."""

    row_id: str
    canonical_url: str
    page_hash: str
    chunk_hash: str
    embedding_text_hash: str
    section_path: str
    chunk_index: int


@dataclass(frozen=True)
class StateRowDiffRecord:
    """One existing state row classified by the diff."""

    row_id: str
    canonical_url: str
    page_hash: str
    chunk_hash: str
    embedding_text_hash: str
    plan_id: str
    applied_at: str
    status: str
    reason: str


@dataclass(frozen=True)
class IncrementalPlanDiff:
    """Structured local diff result used by plan summaries and future apply."""

    first_apply: bool
    pages_added: int
    pages_changed: int
    pages_unchanged: int
    pages_removed: int
    chunks_unchanged: int
    chunks_to_embed: int
    rows_to_upsert: int
    stale_rows: int
    retained_stale_rows: int
    unchanged_chunks: list[UnchangedChunkDiffRecord] = field(default_factory=list)
    chunks_to_embed_records: list[DesiredChunkDiffRecord] = field(default_factory=list)
    rows_to_upsert_records: list[DesiredChunkDiffRecord] = field(default_factory=list)
    stale_row_records: list[StateRowDiffRecord] = field(default_factory=list)
    retained_stale_row_records: list[StateRowDiffRecord] = field(default_factory=list)

    def summary_dict(self) -> JsonObject:
        """Return the compact summary expected in ``plan.json``."""

        return {
            "first_apply": self.first_apply,
            "pages_added": self.pages_added,
            "pages_changed": self.pages_changed,
            "pages_unchanged": self.pages_unchanged,
            "pages_removed": self.pages_removed,
            "chunks_unchanged": self.chunks_unchanged,
            "chunks_to_embed": self.chunks_to_embed,
            "rows_to_upsert": self.rows_to_upsert,
            "stale_rows": self.stale_rows,
            "retained_stale_rows": self.retained_stale_rows,
        }

    def to_dict(self) -> JsonObject:
        """Return machine-readable summary and row lists for apply."""

        return normalize_json_object(asdict(self))


def diff_manifest_against_state(manifest: ManifestDocument, state: AppliedState) -> IncrementalPlanDiff:
    """Compare desired manifest chunks to local applied state.

    The diff is deterministic and local-only. Future apply code can use
    ``rows_to_upsert_records`` for embedding/upsert work and
    ``stale_row_records`` for explicit stale deletion.
    """

    desired_chunks = sorted(manifest.chunks, key=chunk_sort_key)
    validate_unique_desired_row_ids(desired_chunks)
    desired_by_row_id = {chunk.row_id: chunk for chunk in desired_chunks}
    active_rows = sorted((row for row in state.rows if row.status == ROW_STATUS_ACTIVE), key=state_row_sort_key)
    retained_rows = sorted(
        (row for row in state.rows if row.status == ROW_STATUS_RETAINED_STALE), key=state_row_sort_key
    )

    active_by_row_id = {row.row_id: row for row in active_rows}
    retained_by_row_id = {row.row_id: row for row in retained_rows}

    unchanged_chunks: list[UnchangedChunkDiffRecord] = []
    rows_to_upsert: list[DesiredChunkDiffRecord] = []

    for chunk in desired_chunks:
        active_row = active_by_row_id.get(chunk.row_id)
        retained_row = retained_by_row_id.get(chunk.row_id)
        if active_row and active_row.embedding_text_hash == chunk.embedding_text_hash:
            unchanged_chunks.append(unchanged_chunk_record(chunk))
            continue
        if active_row:
            rows_to_upsert.append(
                desired_chunk_record(
                    chunk,
                    action="changed",
                    previous_status=active_row.status,
                    previous_embedding_text_hash=active_row.embedding_text_hash,
                )
            )
            continue
        if retained_row:
            rows_to_upsert.append(
                desired_chunk_record(
                    chunk,
                    action="reactivate_retained_stale",
                    previous_status=retained_row.status,
                    previous_embedding_text_hash=retained_row.embedding_text_hash,
                )
            )
            continue
        rows_to_upsert.append(desired_chunk_record(chunk, action=classify_new_or_changed(chunk, active_rows)))

    stale_rows = [
        state_row_record(row, reason="not_in_desired_manifest")
        for row in active_rows
        if row.row_id not in desired_by_row_id
    ]
    retained_stale_rows = [
        state_row_record(row, reason="retained_stale_not_in_desired_manifest")
        for row in retained_rows
        if row.row_id not in desired_by_row_id
    ]

    page_counts = page_diff_counts(manifest.pages, active_rows, first_apply=state.first_apply)
    return IncrementalPlanDiff(
        first_apply=state.first_apply,
        pages_added=page_counts["pages_added"],
        pages_changed=page_counts["pages_changed"],
        pages_unchanged=page_counts["pages_unchanged"],
        pages_removed=page_counts["pages_removed"],
        chunks_unchanged=len(unchanged_chunks),
        chunks_to_embed=len(rows_to_upsert),
        rows_to_upsert=len(rows_to_upsert),
        stale_rows=len(stale_rows),
        retained_stale_rows=len(retained_stale_rows),
        unchanged_chunks=unchanged_chunks,
        chunks_to_embed_records=rows_to_upsert,
        rows_to_upsert_records=rows_to_upsert,
        stale_row_records=stale_rows,
        retained_stale_row_records=retained_stale_rows,
    )


def diff_summary_for_plan(manifest: ManifestDocument, state: AppliedState) -> JsonObject:
    """Return compact plan summary fields for ``plan.json``."""

    return diff_manifest_against_state(manifest, state).summary_dict()


def validate_unique_desired_row_ids(desired_chunks: Iterable[ChunkManifestRecord]) -> None:
    """Fail clearly rather than allowing duplicate desired rows to collapse."""

    seen: set[str] = set()
    duplicates: set[str] = set()
    for chunk in desired_chunks:
        if chunk.row_id in seen:
            duplicates.add(chunk.row_id)
        seen.add(chunk.row_id)
    if duplicates:
        raise PlanDiffError(
            "desired manifest contains duplicate row_id values; "
            f"row IDs must be unique before diff/apply: {', '.join(sorted(duplicates))}"
        )


def page_diff_counts(
    desired_pages: Iterable[PageManifestRecord],
    active_rows: Iterable[AppliedStateRow],
    *,
    first_apply: bool,
) -> dict[str, int]:
    """Return best-effort page-level counts from desired pages and active state rows."""

    desired_by_url = {page.canonical_url: page for page in desired_pages}
    previous_hashes_by_url: dict[str, set[str]] = {}
    for row in active_rows:
        previous_hashes_by_url.setdefault(row.canonical_url, set()).add(row.page_hash)

    pages_added = 0
    pages_changed = 0
    pages_unchanged = 0
    for url, page in desired_by_url.items():
        previous_hashes = previous_hashes_by_url.get(url)
        if not previous_hashes:
            pages_added += 1
        elif page.page_hash in previous_hashes:
            pages_unchanged += 1
        else:
            pages_changed += 1

    pages_removed = len(set(previous_hashes_by_url) - set(desired_by_url))
    if first_apply:
        return {
            "pages_added": len(desired_by_url),
            "pages_changed": 0,
            "pages_unchanged": 0,
            "pages_removed": 0,
        }
    return {
        "pages_added": pages_added,
        "pages_changed": pages_changed,
        "pages_unchanged": pages_unchanged,
        "pages_removed": pages_removed,
    }


def classify_new_or_changed(chunk: ChunkManifestRecord, active_rows: list[AppliedStateRow]) -> ChunkAction:
    """Classify a missing desired row as new or changed using available state lineage."""

    if any(row.canonical_url == chunk.canonical_url for row in active_rows):
        return "changed"
    return "new"


def unchanged_chunk_record(chunk: ChunkManifestRecord) -> UnchangedChunkDiffRecord:
    return UnchangedChunkDiffRecord(
        row_id=chunk.row_id,
        canonical_url=chunk.canonical_url,
        page_hash=chunk.page_hash,
        chunk_hash=chunk.chunk_hash,
        embedding_text_hash=chunk.embedding_text_hash,
        section_path=chunk.section_path,
        chunk_index=chunk.chunk_index,
    )


def desired_chunk_record(
    chunk: ChunkManifestRecord,
    *,
    action: ChunkAction,
    previous_status: str | None = None,
    previous_embedding_text_hash: str | None = None,
) -> DesiredChunkDiffRecord:
    return DesiredChunkDiffRecord(
        row_id=chunk.row_id,
        canonical_url=chunk.canonical_url,
        page_hash=chunk.page_hash,
        chunk_hash=chunk.chunk_hash,
        embedding_text_hash=chunk.embedding_text_hash,
        section_path=chunk.section_path,
        chunk_index=chunk.chunk_index,
        action=action,
        previous_status=previous_status,
        previous_embedding_text_hash=previous_embedding_text_hash,
    )


def state_row_record(row: AppliedStateRow, *, reason: str) -> StateRowDiffRecord:
    return StateRowDiffRecord(
        row_id=row.row_id,
        canonical_url=row.canonical_url,
        page_hash=row.page_hash,
        chunk_hash=row.chunk_hash,
        embedding_text_hash=row.embedding_text_hash,
        plan_id=row.plan_id,
        applied_at=row.applied_at,
        status=row.status,
        reason=reason,
    )


def chunk_sort_key(chunk: ChunkManifestRecord) -> tuple[str, str, int, str]:
    return (chunk.canonical_url, chunk.section_path, chunk.chunk_index, chunk.row_id)


def state_row_sort_key(row: AppliedStateRow) -> tuple[str, str]:
    return (row.canonical_url, row.row_id)
