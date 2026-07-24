from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tempfile
import unittest

from buoy_search.chunker import parse_markdown_file
from buoy_search.crawler import CrawlOptions
from buoy_search.database_relation import (
    DatabaseDocument,
    DatabaseScanResult,
    crawl_database_relation_with_plan,
    database_base_url,
    database_default_out_dir,
    database_document_url,
    database_namespace_candidate,
    database_site_id,
    stable_page_filename,
    validate_database_base_url,
    validate_selected_database_rows,
    write_database_corpus,
)
from buoy_search.plan_artifacts import GENERIC_SITE_TURBOPUFFER_SCHEMA, SOURCE_METADATA_ROW_FIELDS


@dataclass(frozen=True)
class FakeSource:
    backend: str
    source_id: str = "gong-calls"
    relation: str = "corpus.gong_calls"
    id_column: str = "document_id"
    content_column: str = "content"
    title_column: str | None = None

    @property
    def kind(self) -> str:
        return f"{self.backend}_relation"

    @property
    def base_url(self) -> str:
        return database_base_url(self.backend, self.source_id)

    @property
    def site_id(self) -> str:
        return database_site_id(self.backend, self.source_id)

    @property
    def namespace_candidate(self) -> str:
        return database_namespace_candidate(self.backend, self.source_id)

    @property
    def default_out_dir(self) -> Path:
        return database_default_out_dir(self.backend, self.source_id)

    def document_url(self, document_id: str) -> str:
        return database_document_url(self.backend, self.source_id, document_id)


class DatabaseRelationTests(unittest.TestCase):
    def test_shared_identity_is_stable_and_backend_specific(self) -> None:
        filenames: set[str] = set()
        for backend in ("duckdb", "bigquery", "snowflake"):
            with self.subTest(backend=backend):
                source = FakeSource(backend)
                self.assertEqual(source.base_url, f"{backend}://gong-calls")
                self.assertEqual(source.site_id, f"{backend}-gong-calls")
                self.assertEqual(source.namespace_candidate, f"{backend}-gong-calls-v1")
                self.assertEqual(
                    source.default_out_dir,
                    Path(f"artifacts/site-crawls/{backend}-gong-calls"),
                )
                self.assertEqual(
                    source.document_url("call/1 ? ü"),
                    f"{backend}://gong-calls/call%2F1%20%3F%20%C3%BC",
                )
                filename = stable_page_filename(source, "call/1 ? ü")
                self.assertEqual(filename, stable_page_filename(source, "call/1 ? ü"))
                filenames.add(filename)
        self.assertEqual(len(filenames), 3)

    def test_database_base_url_rejects_trailing_slash(self) -> None:
        for backend in ("duckdb", "bigquery", "snowflake"):
            with self.subTest(backend=backend):
                self.assertEqual(
                    validate_database_base_url(f"{backend}://docs"), f"{backend}://docs"
                )
                with self.assertRaises(ValueError):
                    validate_database_base_url(f"{backend}://docs/")

    def test_shared_markdown_preserves_fixed_provenance_and_scalars(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pages = Path(tmp) / "pages"
            source = FakeSource("bigquery", relation="source-project.corpus.documents")
            document = DatabaseDocument(
                document_id='call\\path"quoted ü',
                title='Title "quoted" at C:\\calls\\ü',
                content="Unicode document body — exact.",
            )
            write_database_corpus(
                source,
                [document],
                pages,
                crawl_timestamp="2026-07-22T00:00:00+00:00",
            )

            parsed = parse_markdown_file(next(pages.glob("*.md")), pages)
            self.assertEqual(parsed.title, document.title)
            self.assertEqual(parsed.url, source.document_url(document.document_id))
            self.assertEqual(parsed.metadata["database_backend"], "bigquery")
            self.assertEqual(parsed.metadata["database_source_id"], "gong-calls")
            self.assertEqual(parsed.metadata["database_relation"], source.relation)
            self.assertEqual(parsed.metadata["database_document_id"], document.document_id)
            self.assertEqual(parsed.metadata["source_kind"], "bigquery_relation")
            self.assertEqual(parsed.metadata["fetcher"], "bigquery-read-only")
            self.assertEqual(parsed.body, document.content)

    def test_shared_selected_row_validation_falls_back_title_without_changing_ids(self) -> None:
        rows = [
            ('call/ü"quoted\\path', "Body one", None),
            ("雪/meeting\\notes", "Body two", "\u3000"),
        ]
        documents = validate_selected_database_rows(
            rows, backend="BigQuery", relation="project.dataset.documents"
        )
        self.assertEqual([document.document_id for document in documents], [row[0] for row in rows])
        self.assertEqual([document.title for document in documents], [row[0] for row in rows])

    def test_shared_execution_reports_document_and_chunk_limits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = FakeSource("snowflake", relation="ANALYTICS.CORPUS.DOCUMENTS")

            def scan(_source, *, max_documents):
                self.assertEqual(max_documents, 2)
                return DatabaseScanResult(
                    documents=[
                        DatabaseDocument("a", "First sentence. Second sentence.", "a"),
                        DatabaseDocument("b", "Third sentence. Fourth sentence.", "B"),
                    ],
                    rows_discovered=5,
                    documents_skipped_empty=1,
                    documents_skipped_limit=2,
                    title_column="TITLE",
                )

            execution = crawl_database_relation_with_plan(
                source,
                CrawlOptions(
                    base_url=source.base_url,
                    out_dir=Path(tmp) / "out",
                    max_pages=2,
                    max_chunks=1,
                    target_tokens=2,
                ),
                scan_relation=scan,
                credentials_required=True,
                source_api_calls_occurred=True,
            )

            summary = execution.summary
            self.assertEqual(summary["rows_discovered"], 5)
            self.assertEqual(summary["documents_selected"], 2)
            self.assertEqual(summary["documents_skipped_empty"], 1)
            self.assertEqual(summary["documents_skipped_limit"], 2)
            self.assertTrue(summary["document_limit_reached"])
            self.assertTrue(summary["chunk_limit_reached"])
            self.assertTrue(summary["limit_reached"])
            self.assertTrue(summary["source_credentials_required"])
            self.assertTrue(summary["source_api_calls_occurred"])
            self.assertFalse(summary["turbopuffer_credentials_required"])
            self.assertFalse(summary["turbopuffer_api_calls"])

    def test_database_provenance_has_fixed_turbopuffer_schema_and_whitelist(self) -> None:
        fields = {
            "database_backend",
            "database_source_id",
            "database_relation",
            "database_document_id",
        }
        self.assertTrue(fields.issubset(GENERIC_SITE_TURBOPUFFER_SCHEMA))
        self.assertTrue(fields.issubset(SOURCE_METADATA_ROW_FIELDS))


if __name__ == "__main__":
    unittest.main()
