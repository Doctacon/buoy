from __future__ import annotations

import json
import tempfile
from pathlib import Path
import unittest

from buoy_search.applied_state import AppliedStateRow, build_applied_state
from buoy_search.chunker import IndexingPlan, IndexingStats, MarkdownChunk, process_corpus
from buoy_search.plan_artifacts import (
    GENERIC_SITE_TURBOPUFFER_SCHEMA,
    PLAN_SCHEMA_VERSION,
    build_generic_site_row,
    build_plan_artifacts,
    chunk_jsonl_records,
    verify_plan_artifacts,
    write_plan_artifacts,
)
from buoy_search.plan_diff import diff_manifest_against_state


def write_page(corpus: Path, *, crawl_timestamp: str, body: str, name: str = "page.md") -> None:
    (corpus / name).write_text(
        "\n".join(
            [
                "---",
                'url: "https://example.com/docs/page"',
                'title: "Example Page"',
                'status: "200"',
                'content_type: "text/html; charset=utf-8"',
                'source_hash: "raw-source-hash"',
                f'crawl_timestamp: "{crawl_timestamp}"',
                'fetcher: "scrapling-static-spider"',
                "---",
                "",
                body,
                "",
            ]
        ),
        encoding="utf-8",
    )


class PlanArtifactTests(unittest.TestCase):
    def build_artifacts(
        self,
        *,
        crawl_timestamp: str = "2026-06-20T00:00:00+00:00",
        body: str = "# Intro\n\nUseful documentation text for retrieval.",
        crawl_options: dict[str, object] | None = None,
        chunk_options: dict[str, object] | None = None,
        embedding_precision: str = "float32",
        diff: dict[str, object] | None = None,
    ):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        corpus = root / "pages"
        corpus.mkdir()
        write_page(corpus, crawl_timestamp=crawl_timestamp, body=body)
        indexing_plan = process_corpus(corpus)
        return build_plan_artifacts(
            indexing_plan=indexing_plan,
            base_url="https://example.com/docs/#ignored",
            out_dir=root / "plan",
            crawl_options=crawl_options or {"css_selector": "main", "max_pages": 10},
            chunk_options=chunk_options or {"target_tokens": 300, "overlap_sentences": 2},
            embedding_precision=embedding_precision,
            diff=diff,
        )

    def test_plan_and_delta_have_required_schema_v2_fields(self) -> None:
        artifacts = self.build_artifacts()
        plan = artifacts.plan_dict()
        upsert = artifacts.upsert_rows[0]

        self.assertEqual(plan["schema_version"], PLAN_SCHEMA_VERSION)
        self.assertEqual(plan["command"], "plan")
        self.assertTrue(plan["plan_id"].startswith("plan_"))
        self.assertRegex(plan["created_at"], r"^\d{4}-\d{2}-\d{2}T")
        self.assertEqual(plan["source"], {
            "kind": "website", "uri": "https://example.com/docs/",
            "title": "example.com", "attributes": {},
        })
        self.assertEqual(plan["site_id"], "example-com")
        self.assertEqual(plan["namespace_candidate"], "site-example-com-v1")
        self.assertEqual(plan["namespace"], "site-example-com-v1")
        self.assertEqual(plan["applied_state"]["present"], False)
        self.assertEqual(plan["delta"]["filename"], "delta.duckdb")
        self.assertEqual(plan["delta"]["upsert_count"], 1)
        self.assertEqual(plan["diff"]["rows_to_upsert"], 1)
        self.assertRegex(plan["artifact_hash"], r"^[0-9a-f]{64}$")
        self.assertNotIn("state_path", plan)
        self.assertNotIn("manifest_path", plan)
        self.assertEqual(upsert["action"], "new")
        self.assertTrue(upsert["row_id"].startswith("ts_"))
        self.assertEqual(upsert["source_path"], "page.md")
        self.assertIn("Useful documentation", upsert["content"])
        self.assertNotIn("content_preview", upsert)

    def test_schema_v2_plan_identity_golden_is_deterministic(self) -> None:
        artifacts = self.build_artifacts()
        plan = artifacts.plan_dict()
        chunks = list(chunk_jsonl_records(artifacts.chunks_jsonl))

        # Precision-aware plans retain deterministic row and namespace identity.
        self.assertEqual(
            plan["artifact_hash"],
            "d6b5e13bbbfdbbdeacef69ec5f154e9340038f88b28b40160135e7d9ed1014e0",
        )
        self.assertEqual(plan["namespace"], "site-example-com-v1")
        self.assertEqual(chunks[0]["row_id"], "ts_2fd4695f91b79df01d0f8b1d47587127")

    def test_precision_changes_embedding_identity_but_not_row_or_namespace(self) -> None:
        float32 = self.build_artifacts(embedding_precision="float32")
        float16 = self.build_artifacts(embedding_precision="float16")
        row32 = float32.manifest.chunks[0]
        row16 = float16.manifest.chunks[0]

        self.assertEqual(row32.row_id, row16.row_id)
        self.assertEqual(float32.manifest.namespace, float16.manifest.namespace)
        self.assertNotEqual(row32.embedding_text_hash, row16.embedding_text_hash)
        self.assertNotEqual(float32.plan.artifact_hash, float16.plan.artifact_hash)

    def test_float16_plan_reupserts_float32_state_with_stable_row_id(self) -> None:
        float32 = self.build_artifacts(embedding_precision="float32")
        float16 = self.build_artifacts(embedding_precision="float16")
        previous = float32.manifest.chunks[0]
        state = build_applied_state(
            site_id=float32.manifest.site_id,
            namespace=float32.manifest.namespace,
            base_url=float32.manifest.base_url,
            last_plan_id=float32.plan.plan_id,
            last_apply_id="apply_previous",
            rows=[AppliedStateRow(
                row_id=previous.row_id,
                canonical_url=previous.canonical_url,
                page_hash=previous.page_hash,
                chunk_hash=previous.chunk_hash,
                embedding_text_hash=previous.embedding_text_hash,
                plan_id=float32.plan.plan_id,
                applied_at="2026-07-14T00:00:00+00:00",
            )],
        )

        diff = diff_manifest_against_state(float16.manifest, state)

        self.assertEqual(diff.rows_to_upsert, 1)
        self.assertEqual(diff.rows_to_upsert_records[0].row_id, previous.row_id)
        self.assertEqual(diff.chunks_unchanged, 0)

    def test_schema_v2_plan_excludes_legacy_paths_and_full_manifest(self) -> None:
        artifacts = self.build_artifacts()
        plan = artifacts.plan_dict()

        self.assertEqual(set(plan), {
            "schema_version", "command", "plan_id", "created_at", "artifact_hash",
            "source", "site_id", "namespace", "namespace_candidate", "crawl_options",
            "chunk_options", "embedding_model", "embedding_precision", "applied_state",
            "delta", "diff",
        })
        serialized = json.dumps(plan)
        self.assertNotIn("manifest.json", serialized)
        self.assertNotIn("chunks.jsonl", serialized)
        self.assertNotIn("pages_dir", serialized)

    def test_pdf_source_metadata_is_preserved_in_manifest_chunks_and_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus = root / "pages"
            corpus.mkdir()
            (corpus / "pdf-page.md").write_text(
                "\n".join(
                    [
                        "---",
                        'url: "pdf://pdf-research-notes-abc123/Research%20Notes.pdf"',
                        'title: "Research Notes.pdf"',
                        'status: "200"',
                        'content_type: "application/pdf"',
                        'source_kind: "pdf"',
                        'pdf_filename: "Research Notes.pdf"',
                        'pdf_sha256: "abc123"',
                        'pdf_source_id: "pdf-research-notes-abc123"',
                        'source_hash: "raw-source-hash"',
                        'crawl_timestamp: "2026-07-08T00:00:00+00:00"',
                        'fetcher: "markitdown"',
                        "---",
                        "",
                        "# Research Notes",
                        "",
                        "Useful PDF text for retrieval.",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            artifacts = build_plan_artifacts(
                indexing_plan=process_corpus(corpus),
                base_url="pdf://pdf-research-notes-abc123",
                out_dir=root / "plan",
            )

        self.assertEqual(artifacts.plan.source, {
            "kind": "pdf", "uri": "pdf://pdf-research-notes-abc123",
            "title": "Research Notes.pdf",
            "attributes": {"filename": "Research Notes.pdf", "sha256": "abc123", "source_id": "pdf-research-notes-abc123"},
        })
        self.assertEqual(artifacts.plan.site_id, "pdf-research-notes-abc123")
        self.assertEqual(artifacts.plan.namespace_candidate, "pdf-research-notes-abc123-v1")
        self.assertIn("pdf_filename", GENERIC_SITE_TURBOPUFFER_SCHEMA)
        page = artifacts.manifest.pages[0]
        self.assertEqual(page.source_metadata["source_kind"], "pdf")
        self.assertEqual(page.source_metadata["pdf_filename"], "Research Notes.pdf")
        self.assertEqual(page.source_metadata["pdf_sha256"], "abc123")
        self.assertNotIn("crawl_timestamp", page.source_metadata)
        chunk = artifacts.manifest.chunks[0]
        self.assertEqual(chunk.source_metadata["pdf_source_id"], "pdf-research-notes-abc123")
        row = build_generic_site_row(chunk, [0.0], plan_id=artifacts.plan.plan_id, applied_at="2026-07-08T00:00:00+00:00")
        self.assertEqual(row["source_kind"], "pdf")
        self.assertEqual(row["pdf_filename"], "Research Notes.pdf")
        self.assertEqual(row["pdf_sha256"], "abc123")
        self.assertEqual(row["pdf_source_id"], "pdf-research-notes-abc123")

    def test_local_file_source_metadata_is_preserved_in_manifest_chunks_and_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus = root / "pages"
            corpus.mkdir()
            (corpus / "csv-page.md").write_text(
                "\n".join(
                    [
                        "---",
                        'url: "file://file-csv-research-notes-abc123/Research%20Notes.csv"',
                        'title: "Research Notes.csv"',
                        'status: "200"',
                        'content_type: "text/csv"',
                        'source_kind: "local_file"',
                        'file_filename: "Research Notes.csv"',
                        'file_extension: "csv"',
                        'file_sha256: "abc123"',
                        'file_source_id: "file-csv-research-notes-abc123"',
                        'source_hash: "raw-source-hash"',
                        'crawl_timestamp: "2026-07-08T00:00:00+00:00"',
                        'fetcher: "markitdown"',
                        "---",
                        "",
                        "| metric | value |",
                        "| --- | --- |",
                        "| revenue | 42 |",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            artifacts = build_plan_artifacts(
                indexing_plan=process_corpus(corpus),
                base_url="file://file-csv-research-notes-abc123",
                out_dir=root / "plan",
            )

        self.assertEqual(artifacts.plan.source, {
            "kind": "local_file", "uri": "file://file-csv-research-notes-abc123",
            "title": "Research Notes.csv",
            "attributes": {"filename": "Research Notes.csv", "extension": "csv", "sha256": "abc123", "source_id": "file-csv-research-notes-abc123"},
        })
        self.assertEqual(artifacts.plan.site_id, "file-csv-research-notes-abc123")
        self.assertEqual(artifacts.plan.namespace_candidate, "file-csv-research-notes-abc123-v1")
        self.assertIn("file_filename", GENERIC_SITE_TURBOPUFFER_SCHEMA)
        page = artifacts.manifest.pages[0]
        self.assertEqual(page.source_metadata["source_kind"], "local_file")
        self.assertEqual(page.source_metadata["file_filename"], "Research Notes.csv")
        self.assertEqual(page.source_metadata["file_extension"], "csv")
        self.assertEqual(page.source_metadata["file_sha256"], "abc123")
        self.assertNotIn("crawl_timestamp", page.source_metadata)
        chunk = artifacts.manifest.chunks[0]
        self.assertEqual(chunk.source_metadata["file_source_id"], "file-csv-research-notes-abc123")
        row = build_generic_site_row(chunk, [0.0], plan_id=artifacts.plan.plan_id, applied_at="2026-07-08T00:00:00+00:00")
        self.assertEqual(row["source_kind"], "local_file")
        self.assertEqual(row["file_filename"], "Research Notes.csv")
        self.assertEqual(row["file_extension"], "csv")
        self.assertEqual(row["file_sha256"], "abc123")
        self.assertEqual(row["file_source_id"], "file-csv-research-notes-abc123")
        self.assertEqual(row["pdf_filename"], "")

    def test_artifact_hash_is_deterministic_for_same_content_and_options(self) -> None:
        first = self.build_artifacts()
        second = self.build_artifacts()

        self.assertEqual(first.plan.artifact_hash, second.plan.artifact_hash)
        self.assertEqual(first.plan.plan_id, second.plan.plan_id)
        self.assertEqual(first.manifest_dict(), second.manifest_dict())
        self.assertEqual(first.chunks_jsonl, second.chunks_jsonl)

    def test_repeated_build_with_same_complete_diff_is_identical(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        corpus = root / "pages"
        corpus.mkdir()
        write_page(
            corpus,
            crawl_timestamp="2026-06-20T00:00:00+00:00",
            body="# Intro\n\nUseful documentation text for retrieval.",
        )
        indexing_plan = process_corpus(corpus)
        kwargs = {
            "indexing_plan": indexing_plan,
            "base_url": "https://example.com/docs/#ignored",
            "out_dir": root / "plan",
            "crawl_options": {"css_selector": "main", "max_pages": 10},
            "chunk_options": {"target_tokens": 300, "overlap_sentences": 2},
        }
        initial = build_plan_artifacts(**kwargs)
        rebuilt = build_plan_artifacts(**kwargs, diff=initial.diff)

        initial_plan = initial.plan_dict()
        rebuilt_plan = rebuilt.plan_dict()
        initial_plan.pop("created_at")
        rebuilt_plan.pop("created_at")
        self.assertEqual(initial_plan, rebuilt_plan)
        self.assertEqual(initial.upsert_rows, rebuilt.upsert_rows)
        self.assertEqual(initial.stale_rows, rebuilt.stale_rows)

    def test_artifact_hash_ignores_volatile_crawl_timestamp(self) -> None:
        first = self.build_artifacts(crawl_timestamp="2026-06-20T00:00:00+00:00")
        second = self.build_artifacts(crawl_timestamp="2026-06-21T00:00:00+00:00")

        self.assertEqual(first.plan.artifact_hash, second.plan.artifact_hash)

    def test_artifact_hash_changes_when_content_changes(self) -> None:
        first = self.build_artifacts(body="# Intro\n\nUseful documentation text for retrieval.")
        second = self.build_artifacts(body="# Intro\n\nDifferent documentation text for retrieval.")

        self.assertNotEqual(first.plan.artifact_hash, second.plan.artifact_hash)

    def test_artifact_hash_changes_when_relevant_options_change(self) -> None:
        first = self.build_artifacts(chunk_options={"target_tokens": 300, "overlap_sentences": 2})
        second = self.build_artifacts(chunk_options={"target_tokens": 450, "overlap_sentences": 2})

        self.assertNotEqual(first.plan.artifact_hash, second.plan.artifact_hash)

    def test_write_plan_artifacts_creates_inspectable_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "plan"
            artifacts = self.build_artifacts()

            write_plan_artifacts(artifacts, out_dir)

            plan = json.loads((out_dir / "plan.json").read_text(encoding="utf-8"))
            verified = verify_plan_artifacts(out_dir / "plan.json")
            names = {path.name for path in out_dir.iterdir()}

        self.assertEqual(names, {"plan.json", "delta.duckdb"})
        self.assertEqual(plan["artifact_hash"], artifacts.plan.artifact_hash)
        self.assertEqual(len(verified.upsert_rows), 1)
        self.assertEqual(verified.upsert_rows[0]["chunk_hash"], artifacts.upsert_rows[0]["chunk_hash"])

    def test_generic_row_id_is_stable_when_unrelated_page_section_changes(self) -> None:
        original = self.build_artifacts(
            body="# Intro\n\nOriginal intro text.\n\n## Stable Section\n\nStable retrieval text."
        )
        changed = self.build_artifacts(
            body="# Intro\n\nChanged intro text.\n\n## Stable Section\n\nStable retrieval text."
        )

        original_stable = next(
            chunk for chunk in original.manifest.chunks if chunk.section_path.endswith("Stable Section")
        )
        changed_stable = next(
            chunk for chunk in changed.manifest.chunks if chunk.section_path.endswith("Stable Section")
        )

        self.assertNotEqual(original_stable.page_hash, changed_stable.page_hash)
        self.assertEqual(original_stable.chunk_hash, changed_stable.chunk_hash)
        self.assertEqual(original_stable.row_id, changed_stable.row_id)

    def test_generic_row_id_changes_when_chunk_content_changes(self) -> None:
        original = self.build_artifacts(body="# Intro\n\nUseful documentation text for retrieval.")
        changed = self.build_artifacts(body="# Intro\n\nDifferent documentation text for retrieval.")

        original_chunk = original.manifest.chunks[0]
        changed_chunk = changed.manifest.chunks[0]

        self.assertNotEqual(original_chunk.chunk_hash, changed_chunk.chunk_hash)
        self.assertNotEqual(original_chunk.row_id, changed_chunk.row_id)

    def test_duplicate_chunks_get_deterministic_disambiguated_row_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus = root / "pages"
            corpus.mkdir()
            write_page(corpus, crawl_timestamp="2026-06-20T00:00:00+00:00", body="# Intro\n\nRepeated text.")
            duplicate_chunks = [
                MarkdownChunk(
                    id=f"jf_duplicate_{index}",
                    content="Repeated text.",
                    title="Example Page",
                    url="https://example.com/docs/page",
                    path="page.md",
                    section_path="Intro",
                    chunk_index=index,
                    doc_kind="page",
                    tags=["page"],
                    source_hash="page-hash",
                )
                for index in range(2)
            ]
            indexing_plan = IndexingPlan(
                corpus_dir=corpus,
                files_discovered=1,
                chunks=duplicate_chunks,
                stats=IndexingStats(chunks_generated=2),
            )

            first = build_plan_artifacts(
                indexing_plan=indexing_plan,
                base_url="https://example.com/docs/",
                out_dir=root / "first",
            )
            second = build_plan_artifacts(
                indexing_plan=indexing_plan,
                base_url="https://example.com/docs/",
                out_dir=root / "second",
            )

        first_chunks = first.manifest.chunks
        second_chunks = second.manifest.chunks
        self.assertEqual(len({chunk.row_id for chunk in first_chunks}), 2)
        self.assertEqual([chunk.duplicate_ordinal for chunk in first_chunks], [0, 1])
        self.assertEqual(first_chunks[0].chunk_hash, first_chunks[1].chunk_hash)
        self.assertEqual(first_chunks[0].row_id, first_chunks[0].row_id_candidate)
        self.assertEqual(first_chunks[1].row_id, first_chunks[1].row_id_candidate)
        self.assertNotEqual(first_chunks[0].row_id, first_chunks[1].row_id)
        self.assertEqual([chunk.row_id for chunk in first_chunks], [chunk.row_id for chunk in second_chunks])

    def test_duplicate_disambiguation_does_not_reintroduce_page_hash_churn(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus = root / "pages"
            corpus.mkdir()
            write_page(corpus, crawl_timestamp="2026-06-20T00:00:00+00:00", body="# Intro\n\nRepeated text.")
            chunks = [
                MarkdownChunk(
                    id=f"jf_duplicate_{index}",
                    content="Repeated text.",
                    title="Example Page",
                    url="https://example.com/docs/page",
                    path="page.md",
                    section_path="Intro",
                    chunk_index=index,
                    doc_kind="page",
                    tags=["page"],
                    source_hash=source_hash,
                )
                for index, source_hash in enumerate(["page-hash-old", "page-hash-old"])
            ]
            changed_page_hash_chunks = [
                MarkdownChunk(
                    id=f"jf_duplicate_{index}",
                    content=chunk.content,
                    title=chunk.title,
                    url=chunk.url,
                    path=chunk.path,
                    section_path=chunk.section_path,
                    chunk_index=chunk.chunk_index,
                    doc_kind=chunk.doc_kind,
                    tags=chunk.tags,
                    source_hash="page-hash-new",
                )
                for index, chunk in enumerate(chunks)
            ]
            original = build_plan_artifacts(
                indexing_plan=IndexingPlan(
                    corpus_dir=corpus,
                    files_discovered=1,
                    chunks=chunks,
                    stats=IndexingStats(chunks_generated=2),
                ),
                base_url="https://example.com/docs/",
                out_dir=root / "original",
            )
            changed = build_plan_artifacts(
                indexing_plan=IndexingPlan(
                    corpus_dir=corpus,
                    files_discovered=1,
                    chunks=changed_page_hash_chunks,
                    stats=IndexingStats(chunks_generated=2),
                ),
                base_url="https://example.com/docs/",
                out_dir=root / "changed",
            )

        self.assertEqual(
            [chunk.row_id for chunk in original.manifest.chunks],
            [chunk.row_id for chunk in changed.manifest.chunks],
        )

    def test_generic_site_row_contains_incremental_metadata(self) -> None:
        artifacts = self.build_artifacts()
        chunk = artifacts.manifest.chunks[0]
        row = build_generic_site_row(
            chunk,
            [0.1, 0.2, 0.3],
            plan_id="plan_example",
            applied_at="2026-06-20T12:00:00+00:00",
        )

        self.assertEqual(row["id"], chunk.row_id)
        self.assertEqual(row["vector"], [0.1, 0.2, 0.3])
        self.assertEqual(row["site_id"], "example-com")
        self.assertEqual(row["canonical_url"], "https://example.com/docs/page")
        self.assertEqual(row["page_hash"], chunk.page_hash)
        self.assertEqual(row["source_hash"], chunk.page_hash)
        self.assertEqual(row["chunk_hash"], chunk.chunk_hash)
        self.assertEqual(row["embedding_text_hash"], chunk.embedding_text_hash)
        self.assertEqual(row["plan_id"], "plan_example")
        self.assertEqual(row["applied_at"], "2026-06-20T12:00:00+00:00")
        for field in ("site_id", "canonical_url", "page_hash", "chunk_hash", "embedding_text_hash", "plan_id", "applied_at"):
            self.assertIn(field, GENERIC_SITE_TURBOPUFFER_SCHEMA)


if __name__ == "__main__":
    unittest.main()
