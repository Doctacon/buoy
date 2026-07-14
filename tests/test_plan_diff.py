from __future__ import annotations

import unittest

from buoy_search.applied_state import (
    APPLIED_STATE_SCHEMA_VERSION,
    ROW_STATUS_ACTIVE,
    ROW_STATUS_DELETED,
    ROW_STATUS_RETAINED_STALE,
    AppliedState,
    AppliedStateRow,
)
from buoy_search.plan_artifacts import ChunkManifestRecord, ManifestDocument, PageManifestRecord, generic_site_row_id, sha256_text
from buoy_search.plan_diff import PlanDiffError, diff_manifest_against_state, diff_summary_for_plan


SITE_ID = "example-com"
BASE_URL = "https://example.com/docs/"
NAMESPACE = "site-example-com-v1"
APPLIED_AT = "2026-06-20T12:00:00+00:00"


def page(url: str, *, page_hash: str) -> PageManifestRecord:
    return PageManifestRecord(
        canonical_url=url,
        title=url.rsplit("/", 1)[-1],
        content_path=url.rsplit("/", 1)[-1] + ".md",
        page_hash=page_hash,
        status=200,
        content_type="text/html",
        source_metadata={},
    )


def chunk(
    url: str,
    *,
    section_path: str = "Intro",
    chunk_index: int = 0,
    page_hash: str = "page-hash",
    content: str = "useful docs",
) -> ChunkManifestRecord:
    chunk_hash = sha256_text(content)
    embedding_text = f"Title: Example\n\nSection: {section_path}\n\n{content}"
    embedding_text_hash = sha256_text(embedding_text)
    row_id = generic_site_row_id(
        site_id=SITE_ID,
        canonical_url=url,
        section_path=section_path,
        chunk_hash=chunk_hash,
    )
    return ChunkManifestRecord(
        row_id=row_id,
        row_id_candidate=row_id,
        site_id=SITE_ID,
        duplicate_ordinal=0,
        canonical_url=url,
        page_content_path=url.rsplit("/", 1)[-1] + ".md",
        page_hash=page_hash,
        chunk_hash=chunk_hash,
        embedding_text_hash=embedding_text_hash,
        title="Example",
        section_path=section_path,
        chunk_index=chunk_index,
        content=content,
        content_preview=content,
        doc_kind="page",
        tags=["page"],
    )


def manifest(chunks: list[ChunkManifestRecord], pages: list[PageManifestRecord] | None = None) -> ManifestDocument:
    if pages is None:
        seen: dict[str, PageManifestRecord] = {}
        for desired_chunk in chunks:
            seen.setdefault(desired_chunk.canonical_url, page(desired_chunk.canonical_url, page_hash=desired_chunk.page_hash))
        pages = list(seen.values())
    return ManifestDocument(
        schema_version=1,
        site_id=SITE_ID,
        base_url=BASE_URL,
        namespace=NAMESPACE,
        namespace_candidate=NAMESPACE,
        pages=pages,
        chunks=chunks,
    )


def state_row(desired_chunk: ChunkManifestRecord, *, status: str = ROW_STATUS_ACTIVE) -> AppliedStateRow:
    return AppliedStateRow(
        row_id=desired_chunk.row_id,
        canonical_url=desired_chunk.canonical_url,
        page_hash=desired_chunk.page_hash,
        chunk_hash=desired_chunk.chunk_hash,
        embedding_text_hash=desired_chunk.embedding_text_hash,
        plan_id="plan_previous",
        applied_at=APPLIED_AT,
        status=status,  # type: ignore[arg-type]
    )


def custom_state_row(
    *,
    row_id: str,
    canonical_url: str,
    page_hash: str,
    chunk_hash: str = "old-chunk-hash",
    embedding_text_hash: str = "old-embedding-hash",
    status: str = ROW_STATUS_ACTIVE,
) -> AppliedStateRow:
    return AppliedStateRow(
        row_id=row_id,
        canonical_url=canonical_url,
        page_hash=page_hash,
        chunk_hash=chunk_hash,
        embedding_text_hash=embedding_text_hash,
        plan_id="plan_previous",
        applied_at=APPLIED_AT,
        status=status,  # type: ignore[arg-type]
    )


def applied_state(rows: list[AppliedStateRow], *, first_apply: bool = False) -> AppliedState:
    return AppliedState(
        schema_version=APPLIED_STATE_SCHEMA_VERSION,
        site_id=SITE_ID,
        namespace=NAMESPACE,
        base_url=BASE_URL,
        updated_at=APPLIED_AT,
        last_plan_id="plan_previous",
        last_apply_id="apply_previous",
        rows=rows,
        first_apply=first_apply,
    )


class IncrementalPlanDiffTests(unittest.TestCase):
    def test_first_apply_marks_all_desired_chunks_for_embedding_and_upsert(self) -> None:
        first = chunk("https://example.com/docs/a", page_hash="page-a", content="alpha")
        second = chunk("https://example.com/docs/b", page_hash="page-b", content="beta")

        diff = diff_manifest_against_state(manifest([first, second]), applied_state([], first_apply=True))

        self.assertTrue(diff.first_apply)
        self.assertEqual(diff.pages_added, 2)
        self.assertEqual(diff.pages_changed, 0)
        self.assertEqual(diff.pages_unchanged, 0)
        self.assertEqual(diff.pages_removed, 0)
        self.assertEqual(diff.chunks_unchanged, 0)
        self.assertEqual(diff.chunks_to_embed, 2)
        self.assertEqual(diff.rows_to_upsert, 2)
        self.assertEqual(diff.stale_rows, 0)
        self.assertEqual([record.action for record in diff.rows_to_upsert_records], ["new", "new"])
        self.assertEqual([record.row_id for record in diff.rows_to_upsert_records], [first.row_id, second.row_id])
        self.assertEqual(diff.chunks_to_embed_records, diff.rows_to_upsert_records)

    def test_no_change_second_plan_marks_chunks_unchanged(self) -> None:
        desired = chunk("https://example.com/docs/a", page_hash="page-a", content="alpha")

        diff = diff_manifest_against_state(manifest([desired]), applied_state([state_row(desired)]))

        self.assertFalse(diff.first_apply)
        self.assertEqual(diff.pages_added, 0)
        self.assertEqual(diff.pages_changed, 0)
        self.assertEqual(diff.pages_unchanged, 1)
        self.assertEqual(diff.chunks_unchanged, 1)
        self.assertEqual(diff.chunks_to_embed, 0)
        self.assertEqual(diff.rows_to_upsert, 0)
        self.assertEqual(diff.stale_rows, 0)
        self.assertEqual(diff.unchanged_chunks[0].row_id, desired.row_id)
        self.assertEqual(diff.to_dict()["unchanged_chunks"][0]["row_id"], desired.row_id)

    def test_changed_chunk_reports_new_upsert_and_old_row_stale(self) -> None:
        previous = chunk("https://example.com/docs/a", page_hash="page-old", content="old alpha")
        desired = chunk("https://example.com/docs/a", page_hash="page-new", content="new alpha")

        diff = diff_manifest_against_state(manifest([desired]), applied_state([state_row(previous)]))

        self.assertEqual(diff.pages_added, 0)
        self.assertEqual(diff.pages_changed, 1)
        self.assertEqual(diff.pages_unchanged, 0)
        self.assertEqual(diff.chunks_to_embed, 1)
        self.assertEqual(diff.rows_to_upsert, 1)
        self.assertEqual(diff.rows_to_upsert_records[0].row_id, desired.row_id)
        self.assertEqual(diff.rows_to_upsert_records[0].action, "changed")
        self.assertEqual(diff.stale_rows, 1)
        self.assertEqual(diff.stale_row_records[0].row_id, previous.row_id)
        self.assertEqual(diff.stale_row_records[0].reason, "not_in_desired_manifest")

    def test_removed_page_reports_active_rows_as_stale(self) -> None:
        retained = chunk("https://example.com/docs/a", page_hash="page-a", content="alpha")
        removed = chunk("https://example.com/docs/removed", page_hash="page-removed", content="removed")

        diff = diff_manifest_against_state(
            manifest([retained]),
            applied_state([state_row(retained), state_row(removed)]),
        )

        self.assertEqual(diff.pages_removed, 1)
        self.assertEqual(diff.chunks_unchanged, 1)
        self.assertEqual(diff.stale_rows, 1)
        self.assertEqual(diff.stale_row_records[0].row_id, removed.row_id)
        self.assertEqual(diff.stale_row_records[0].canonical_url, "https://example.com/docs/removed")

    def test_retained_stale_rows_remain_visible_until_deleted(self) -> None:
        active = chunk("https://example.com/docs/a", page_hash="page-a", content="alpha")
        retained_stale = chunk("https://example.com/docs/old", page_hash="page-old", content="old")

        diff = diff_manifest_against_state(
            manifest([active]),
            applied_state([state_row(active), state_row(retained_stale, status=ROW_STATUS_RETAINED_STALE)]),
        )

        self.assertEqual(diff.stale_rows, 0)
        self.assertEqual(diff.retained_stale_rows, 1)
        self.assertEqual(diff.retained_stale_row_records[0].row_id, retained_stale.row_id)
        self.assertEqual(diff.retained_stale_row_records[0].status, ROW_STATUS_RETAINED_STALE)
        self.assertEqual(diff.retained_stale_row_records[0].reason, "retained_stale_not_in_desired_manifest")

    def test_retained_stale_row_that_becomes_desired_is_marked_for_reactivation(self) -> None:
        desired_again = chunk("https://example.com/docs/old", page_hash="page-old", content="old")

        diff = diff_manifest_against_state(
            manifest([desired_again]),
            applied_state([state_row(desired_again, status=ROW_STATUS_RETAINED_STALE)]),
        )

        self.assertEqual(diff.retained_stale_rows, 0)
        self.assertEqual(diff.rows_to_upsert, 1)
        self.assertEqual(diff.rows_to_upsert_records[0].row_id, desired_again.row_id)
        self.assertEqual(diff.rows_to_upsert_records[0].action, "reactivate_retained_stale")
        self.assertEqual(diff.rows_to_upsert_records[0].previous_status, ROW_STATUS_RETAINED_STALE)

    def test_deleted_state_rows_are_ignored_by_diff(self) -> None:
        desired = chunk("https://example.com/docs/a", page_hash="page-a", content="alpha")
        deleted = chunk("https://example.com/docs/deleted", page_hash="page-deleted", content="deleted")

        diff = diff_manifest_against_state(
            manifest([desired]),
            applied_state([state_row(desired), state_row(deleted, status=ROW_STATUS_DELETED)]),
        )

        self.assertEqual(diff.stale_rows, 0)
        self.assertEqual(diff.retained_stale_rows, 0)
        self.assertEqual(diff.pages_removed, 0)

    def test_duplicate_desired_row_ids_fail_clearly_before_diff_collapses_them(self) -> None:
        first = chunk("https://example.com/docs/a", page_hash="page-a", content="alpha")
        duplicate = chunk("https://example.com/docs/a", page_hash="page-a", content="alpha")

        with self.assertRaisesRegex(PlanDiffError, "duplicate row_id"):
            diff_manifest_against_state(manifest([first, duplicate]), applied_state([], first_apply=True))

    def test_summary_for_plan_returns_compact_counts_only(self) -> None:
        desired = chunk("https://example.com/docs/a", page_hash="page-a", content="alpha")

        summary = diff_summary_for_plan(manifest([desired]), applied_state([], first_apply=True))

        self.assertEqual(
            summary,
            {
                "first_apply": True,
                "pages_added": 1,
                "pages_changed": 0,
                "pages_unchanged": 0,
                "pages_removed": 0,
                "chunks_unchanged": 0,
                "chunks_to_embed": 1,
                "rows_to_upsert": 1,
                "stale_rows": 0,
                "retained_stale_rows": 0,
            },
        )


if __name__ == "__main__":
    unittest.main()
