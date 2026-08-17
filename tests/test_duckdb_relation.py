from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import duckdb

from buoy_search.chunker import parse_markdown_file, process_corpus
from buoy_search.crawler import CrawlOptions, default_out_dir, namespace_candidate, source_id_for_url, validate_base_url
from buoy_search.duckdb_relation import (
    DuckDBRelationError,
    DuckDBScanResult,
    SAFE_DUCKDB_CONFIG,
    crawl_duckdb_relation,
    duckdb_relation_source,
    scan_duckdb_relation,
    stable_page_filename,
)


def create_database(path: Path, statements: list[str]) -> None:
    with duckdb.connect(str(path)) as connection:
        for statement in statements:
            connection.execute(statement)


class DuckDBRelationTests(unittest.TestCase):
    def test_source_identity_is_strict_and_path_independent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first.duckdb"
            second = Path(tmp) / "nested" / "second.duckdb"
            second.parent.mkdir()
            for path in (first, second):
                create_database(path, ["CREATE TABLE docs(document_id VARCHAR, content VARCHAR)"])

            with patch("buoy_search.local_paths.Path.home", return_value=Path(tmp)):
                first_source = duckdb_relation_source(first, relation="main.docs", source_id="gong-calls")
                second_source = duckdb_relation_source(second, relation="main.docs", source_id="gong-calls")

            self.assertEqual(first_source.base_url, "duckdb://gong-calls")
            self.assertEqual(first_source.site_id, "duckdb-gong-calls")
            self.assertEqual(first_source.namespace_candidate, "duckdb-gong-calls-v1")
            with patch("buoy_search.local_paths.Path.home", return_value=Path(tmp)):
                self.assertEqual(
                    first_source.default_out_dir,
                    Path(tmp) / ".buoy/artifacts/site-crawls/duckdb-gong-calls",
                )
            self.assertEqual(first_source.document_url("call/1 ?"), "duckdb://gong-calls/call%2F1%20%3F")
            self.assertEqual(
                stable_page_filename(first_source, "call/1 ?"),
                stable_page_filename(second_source, "call/1 ?"),
            )
            self.assertEqual(validate_base_url(first_source.base_url), first_source.base_url)
            self.assertEqual(namespace_candidate(first_source.base_url), "duckdb-gong-calls-v1")
            self.assertEqual(source_id_for_url(first_source.base_url), "duckdb-gong-calls")
            with patch("buoy_search.local_paths.Path.home", return_value=Path(tmp)):
                self.assertEqual(default_out_dir(first_source.base_url), first_source.default_out_dir)

            for invalid in ("Gong-calls", "gong_calls", "gong--calls", "-gong", "gong-"):
                with self.subTest(source_id=invalid):
                    with self.assertRaisesRegex(ValueError, "source-id must match"):
                        with patch("buoy_search.local_paths.Path.home", return_value=Path(tmp)):
                            duckdb_relation_source(first, relation="docs", source_id=invalid)
            for invalid in ("docs;drop", "a.b.c.d", "main.bad-name", "main..docs"):
                with self.subTest(relation=invalid):
                    with self.assertRaises(ValueError):
                        with patch("buoy_search.local_paths.Path.home", return_value=Path(tmp)):
                            duckdb_relation_source(first, relation=invalid, source_id="gong-calls")

    def test_scan_result_preserves_rows_scanned_constructor_compatibility(self) -> None:
        result = DuckDBScanResult(
            documents=[],
            rows_scanned=7,
            documents_skipped_empty=2,
            documents_skipped_limit=3,
            title_column=None,
        )
        self.assertEqual(result.rows_scanned, 7)
        self.assertEqual(result.rows_discovered, 7)

    def test_table_and_view_scan_mapped_columns_titles_empty_rows_and_cap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "documents.duckdb"
            create_database(
                database,
                [
                    "CREATE TABLE docs(doc_key INTEGER, body VARCHAR, heading VARCHAR)",
                    "INSERT INTO docs VALUES (3, 'third body', NULL), (1, 'first body', ' First '), (4, '   ', 'empty'), (2, 'second body', '')",
                    "CREATE VIEW docs_view AS SELECT * FROM docs",
                ],
            )
            source = duckdb_relation_source(
                database,
                relation="docs_view",
                source_id="mapped-docs",
                id_column="doc_key",
                content_column="body",
                title_column="heading",
            )

            scan = scan_duckdb_relation(source, max_documents=2, batch_size=1)

            self.assertEqual([document.document_id for document in scan.documents], ["1", "2"])
            self.assertEqual([document.title for document in scan.documents], [" First ", "2"])
            self.assertEqual([document.content for document in scan.documents], ["first body", "second body"])
            self.assertEqual(scan.rows_scanned, 4)
            self.assertEqual(scan.documents_skipped_empty, 1)
            self.assertEqual(scan.documents_skipped_limit, 1)
            self.assertEqual(scan.title_column, "heading")

    def test_absent_title_column_falls_back_to_document_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "documents.duckdb"
            create_database(
                database,
                [
                    "CREATE TABLE docs(document_id VARCHAR, content VARCHAR)",
                    "INSERT INTO docs VALUES ('alpha', 'Alpha body')",
                ],
            )
            source = duckdb_relation_source(database, relation="docs", source_id="untitled-docs")

            scan = scan_duckdb_relation(source, max_documents=10)

            self.assertIsNone(scan.title_column)
            self.assertEqual(scan.documents[0].title, "alpha")

    def test_safe_connection_disables_external_and_extension_access_before_scan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "documents.duckdb"
            create_database(
                database,
                [
                    "CREATE TABLE docs(document_id VARCHAR, content VARCHAR)",
                    "INSERT INTO docs VALUES ('alpha', 'Alpha body')",
                ],
            )
            source = duckdb_relation_source(database, relation="docs", source_id="safe-docs")
            real_connect = duckdb.connect
            observed_config: dict[str, str] = {}

            def capture_connect(*args, **kwargs):  # noqa: ANN002, ANN003 - DuckDB factory wrapper.
                observed_config.update(kwargs.get("config", {}))
                return real_connect(*args, **kwargs)

            with patch("buoy_search.duckdb_relation.duckdb.connect", side_effect=capture_connect):
                scan = scan_duckdb_relation(source, max_documents=10)

            self.assertEqual(scan.documents[0].document_id, "alpha")
            self.assertEqual(observed_config, SAFE_DUCKDB_CONFIG)
            self.assertEqual(
                observed_config,
                {
                    "enable_external_access": "false",
                    "autoinstall_known_extensions": "false",
                    "autoload_known_extensions": "false",
                    "allow_community_extensions": "false",
                },
            )

    def test_persisted_external_view_is_blocked_without_reading_external_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            external_csv = root / "secret.csv"
            external_csv.write_text("document_id,content\nalpha,external secret body\n", encoding="utf-8")
            database = root / "documents.duckdb"
            with duckdb.connect(str(database)) as connection:
                connection.execute(
                    f"CREATE VIEW docs AS SELECT * FROM read_csv_auto('{external_csv.as_posix()}')"
                )
            database_before = database.read_bytes()
            source = duckdb_relation_source(database, relation="docs", source_id="hostile-view")

            with self.assertRaises(DuckDBRelationError) as raised:
                scan_duckdb_relation(source, max_documents=10)

            self.assertEqual(
                str(raised.exception),
                "DuckDB relation 'docs' depends on external files, databases, or extensions, "
                "which Buoy disables for safe read-only indexing. Materialize the final relation "
                "as a table in this DuckDB database upstream, then plan again.",
            )
            self.assertNotIn(str(external_csv), str(raised.exception))
            self.assertEqual(database.read_bytes(), database_before)

    def test_self_contained_view_error_containing_security_marker_is_not_reclassified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "documents.duckdb"
            create_database(
                database,
                [
                    "CREATE VIEW docs AS SELECT 'alpha' AS document_id, "
                    "CAST('file system operations are disabled by configuration' AS INTEGER) "
                    'AS "content"'
                ],
            )
            source = duckdb_relation_source(database, relation="docs", source_id="broken-view")

            with self.assertRaises(DuckDBRelationError) as raised:
                scan_duckdb_relation(source, max_documents=10)

            self.assertIn(
                "Could not read DuckDB relation 'docs' in read-only mode", str(raised.exception)
            )
            self.assertIn(
                "file system operations are disabled by configuration", str(raised.exception)
            )
            self.assertNotIn("depends on external files", str(raised.exception))

    def test_extension_permission_marker_is_classified_without_loading_extension(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "documents.duckdb"
            create_database(database, ["CREATE TABLE docs(document_id VARCHAR, content VARCHAR)"])
            source = duckdb_relation_source(database, relation="docs", source_id="extension-view")
            error = duckdb.PermissionException(
                "Loading external extensions is disabled through configuration"
            )

            with patch("buoy_search.duckdb_relation.duckdb.connect", side_effect=error):
                with self.assertRaises(DuckDBRelationError) as raised:
                    scan_duckdb_relation(source, max_documents=10)

            self.assertIn(
                "depends on external files, databases, or extensions", str(raised.exception)
            )
            self.assertNotIn("Loading external extensions", str(raised.exception))

    def test_timestamptz_document_ids_are_always_converted_in_utc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "documents.duckdb"
            with duckdb.connect(str(database)) as connection:
                connection.execute("SET TimeZone='Pacific/Auckland'")
                connection.execute("CREATE TABLE docs(document_id TIMESTAMPTZ, content VARCHAR)")
                connection.execute(
                    "INSERT INTO docs VALUES "
                    "(TIMESTAMPTZ '2025-01-02 08:34:05+05:30', 'Timestamp body')"
                )
            source = duckdb_relation_source(database, relation="docs", source_id="timestamp-docs")
            original_timezone = os.environ.get("TZ")
            converted_ids: list[str] = []
            try:
                for host_timezone in ("America/Los_Angeles", "Asia/Tokyo"):
                    os.environ["TZ"] = host_timezone
                    if hasattr(time, "tzset"):
                        time.tzset()
                    converted_ids.append(
                        scan_duckdb_relation(source, max_documents=10).documents[0].document_id
                    )
            finally:
                if original_timezone is None:
                    os.environ.pop("TZ", None)
                else:
                    os.environ["TZ"] = original_timezone
                if hasattr(time, "tzset"):
                    time.tzset()

            self.assertEqual(converted_ids, ["2025-01-02 03:04:05+00"] * 2)

    def test_quoted_and_backslash_scalars_round_trip_through_shared_parser(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            database = root / "documents.duckdb"
            document_id = 'doc\\path"quoted'
            title = 'Title "quoted" at C:\\docs\\file'
            with duckdb.connect(str(database)) as connection:
                connection.execute("CREATE TABLE docs(document_id VARCHAR, content VARCHAR, title VARCHAR)")
                connection.execute(
                    "INSERT INTO docs VALUES (?, ?, ?)",
                    [document_id, "Fidelity body text.", title],
                )
            source = duckdb_relation_source(database, relation="docs", source_id="fidelity-docs")
            out_dir = root / "out"

            summary = crawl_duckdb_relation(
                source,
                CrawlOptions(base_url=source.base_url, out_dir=out_dir, max_pages=10),
            )

            page = next((out_dir / "pages").glob("*.md"))
            parsed = parse_markdown_file(page, out_dir / "pages")
            expected_url = source.document_url(document_id)
            self.assertEqual(parsed.url, expected_url)
            self.assertEqual(parsed.title, title)
            self.assertEqual(parsed.metadata["duckdb_document_id"], document_id)
            self.assertEqual(parsed.metadata["title"], title)
            self.assertEqual(summary["sample_chunks"][0]["title"], title)
            self.assertEqual(summary["sample_chunks"][0]["url"], expected_url)

    def test_auto_detects_title_and_materializes_stable_path_private_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            database = root / "private-location.duckdb"
            create_database(
                database,
                [
                    "CREATE TABLE docs(document_id VARCHAR, content VARCHAR, title VARCHAR)",
                    "INSERT INTO docs VALUES ('zeta', 'Useful zeta document body.', NULL), ('alpha', 'Useful alpha document body.', 'Alpha title')",
                ],
            )
            source = duckdb_relation_source(database, relation="docs", source_id="knowledge-base")
            out_dir = root / "output"

            summary = crawl_duckdb_relation(
                source,
                CrawlOptions(base_url=source.base_url, out_dir=out_dir, max_pages=10, max_chunks=10),
            )

            self.assertEqual(summary["source_kind"], "duckdb_relation")
            self.assertEqual(summary["database_backend"], "duckdb")
            self.assertEqual(summary["database_source_id"], "knowledge-base")
            self.assertEqual(summary["database_relation"], "docs")
            self.assertEqual(summary["rows_discovered"], 2)
            self.assertEqual(summary["rows_scanned"], 2)
            self.assertEqual(summary["documents_selected"], 2)
            self.assertFalse(summary["source_credentials_required"])
            self.assertFalse(summary["source_api_calls_occurred"])
            self.assertFalse(summary["turbopuffer_credentials_required"])
            self.assertTrue(summary["title_column_detected"])
            self.assertEqual(summary["namespace_candidate"], "duckdb-knowledge-base-v1")
            page_files = sorted((out_dir / "pages").glob("*.md"))
            self.assertEqual(
                [path.name for path in page_files],
                sorted(stable_page_filename(source, document_id) for document_id in ("alpha", "zeta")),
            )
            serialized = json.dumps(summary, sort_keys=True) + "".join(
                path.read_text(encoding="utf-8") for path in page_files
            )
            body_by_url = {}
            for path in page_files:
                page_text = path.read_text(encoding="utf-8")
                frontmatter, body = page_text.split("---\n", 2)[1:]
                url_line = next(line for line in frontmatter.splitlines() if line.startswith("url: "))
                body_by_url[json.loads(url_line.removeprefix("url: "))] = body
            self.assertEqual(body_by_url["duckdb://knowledge-base/alpha"], "Useful alpha document body.")
            self.assertEqual(body_by_url["duckdb://knowledge-base/zeta"], "Useful zeta document body.")
            self.assertNotIn(str(database), serialized)
            self.assertIn('url: "duckdb://knowledge-base/alpha"', serialized)
            self.assertIn('source_kind: "duckdb_relation"', serialized)
            self.assertIn('database_backend: "duckdb"', serialized)
            self.assertIn('database_source_id: "knowledge-base"', serialized)
            self.assertIn('database_relation: "docs"', serialized)
            self.assertIn('database_document_id: "alpha"', serialized)
            self.assertIn('duckdb_source_id: "knowledge-base"', serialized)
            self.assertIn('duckdb_relation: "docs"', serialized)
            self.assertIn('duckdb_document_id: "alpha"', serialized)
            self.assertIn('fetcher: "duckdb-read-only"', serialized)
            plan = process_corpus(out_dir / "pages")
            self.assertEqual(plan.stats.files_seen, 2)
            self.assertEqual({chunk.url for chunk in plan.chunks}, {"duckdb://knowledge-base/alpha", "duckdb://knowledge-base/zeta"})

    def test_insertion_order_and_database_path_do_not_change_non_temporal_corpus(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshots: list[dict[str, str]] = []
            for index, values in enumerate(
                (
                    "('b', 'Body B', 'B'), ('a', 'Body A', 'A')",
                    "('a', 'Body A', 'A'), ('b', 'Body B', 'B')",
                )
            ):
                database = root / f"database-{index}.duckdb"
                create_database(
                    database,
                    [
                        "CREATE TABLE docs(document_id VARCHAR, content VARCHAR, title VARCHAR)",
                        f"INSERT INTO docs VALUES {values}",
                    ],
                )
                source = duckdb_relation_source(database, relation="docs", source_id="stable-source")
                out_dir = root / f"out-{index}"
                crawl_duckdb_relation(
                    source,
                    CrawlOptions(base_url=source.base_url, out_dir=out_dir, max_pages=10, max_chunks=10),
                )
                snapshot: dict[str, str] = {}
                for path in sorted((out_dir / "pages").glob("*.md")):
                    text = path.read_text(encoding="utf-8")
                    text = "\n".join(
                        line for line in text.splitlines() if not line.startswith("crawl_timestamp:")
                    )
                    snapshot[path.name] = text
                snapshots.append(snapshot)

            self.assertEqual(snapshots[0], snapshots[1])

    def test_scan_and_materialization_do_not_change_database_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            database = root / "documents.duckdb"
            create_database(
                database,
                [
                    "CREATE TABLE docs(document_id VARCHAR, content VARCHAR)",
                    "INSERT INTO docs VALUES ('alpha', 'Immutable database body')",
                ],
            )
            before_bytes = database.read_bytes()
            before_stat = database.stat()
            source = duckdb_relation_source(database, relation="docs", source_id="immutable-docs")

            crawl_duckdb_relation(
                source,
                CrawlOptions(base_url=source.base_url, out_dir=root / "out", max_pages=10),
            )

            after_stat = database.stat()
            self.assertEqual(database.read_bytes(), before_bytes)
            self.assertEqual(after_stat.st_size, before_stat.st_size)
            self.assertEqual(after_stat.st_mtime_ns, before_stat.st_mtime_ns)

    def test_identity_changes_only_with_source_or_document_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            database = root / "documents.duckdb"
            create_database(
                database,
                [
                    "CREATE TABLE docs(document_id VARCHAR, content VARCHAR, title VARCHAR)",
                    "INSERT INTO docs VALUES ('document-one', 'First content', 'First title')",
                ],
            )
            first_source = duckdb_relation_source(database, relation="docs", source_id="first-source")
            second_source = duckdb_relation_source(database, relation="docs", source_id="second-source")
            first_out = root / "first"
            second_out = root / "second"
            crawl_duckdb_relation(
                first_source,
                CrawlOptions(base_url=first_source.base_url, out_dir=first_out, max_pages=10),
            )
            first_page = next((first_out / "pages").glob("*.md"))
            first_document = parse_markdown_file(first_page, first_out / "pages")
            with duckdb.connect(str(database)) as connection:
                connection.execute("UPDATE docs SET content='Changed content', title='Changed title'")
            crawl_duckdb_relation(
                first_source,
                CrawlOptions(base_url=first_source.base_url, out_dir=second_out, max_pages=10),
            )
            second_page = next((second_out / "pages").glob("*.md"))
            second_document = parse_markdown_file(second_page, second_out / "pages")

            self.assertEqual(first_page.name, second_page.name)
            self.assertEqual(first_document.url, second_document.url)
            self.assertNotEqual(first_document.title, second_document.title)
            self.assertNotEqual(first_document.body, second_document.body)
            self.assertNotEqual(first_document.url, first_source.document_url("document-two"))
            self.assertNotEqual(first_page.name, stable_page_filename(first_source, "document-two"))
            self.assertNotEqual(first_document.url, second_source.document_url("document-one"))
            self.assertNotEqual(first_page.name, stable_page_filename(second_source, "document-one"))

    def test_invalid_mapped_columns_fail_actionably(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "documents.duckdb"
            create_database(
                database,
                ["CREATE TABLE docs(actual_id VARCHAR, actual_content VARCHAR, actual_title VARCHAR)"],
            )
            cases = (
                ("missing_id", "actual_content", "actual_title", "missing ID column 'missing_id'"),
                ("actual_id", "missing_content", "actual_title", "missing content column 'missing_content'"),
                ("actual_id", "actual_content", "missing_title", "missing title column 'missing_title'"),
            )
            for id_column, content_column, title_column, message in cases:
                with self.subTest(message=message):
                    source = duckdb_relation_source(
                        database,
                        relation="docs",
                        source_id="mapped-errors",
                        id_column=id_column,
                        content_column=content_column,
                        title_column=title_column,
                    )
                    with self.assertRaisesRegex(DuckDBRelationError, message):
                        scan_duckdb_relation(source, max_documents=10)

    def test_invalid_ids_columns_relation_and_all_empty_content_fail_before_pages(self) -> None:
        cases = {
            "null-id": (
                ["CREATE TABLE docs(document_id VARCHAR, content VARCHAR)", "INSERT INTO docs VALUES (NULL, 'body')"],
                "null or blank document ID",
            ),
            "blank-id": (
                ["CREATE TABLE docs(document_id VARCHAR, content VARCHAR)", "INSERT INTO docs VALUES ('  ', 'body')"],
                "null or blank document ID",
            ),
            "unicode-blank-id": (
                [
                    "CREATE TABLE docs(document_id VARCHAR, content VARCHAR)",
                    "INSERT INTO docs VALUES (chr(9) || chr(12288), 'body')",
                ],
                "null or blank document ID",
            ),
            "duplicate-id": (
                ["CREATE TABLE docs(document_id INTEGER, content VARCHAR)", "INSERT INTO docs VALUES (1, 'a'), (1, 'b')"],
                "duplicate document ID",
            ),
            "empty-content": (
                ["CREATE TABLE docs(document_id VARCHAR, content VARCHAR)", "INSERT INTO docs VALUES ('a', NULL), ('b', '  ')"],
                "no nonblank documents",
            ),
            "unicode-empty-content": (
                [
                    "CREATE TABLE docs(document_id VARCHAR, content VARCHAR)",
                    "INSERT INTO docs VALUES ('a', chr(10) || chr(160) || chr(12288))",
                ],
                "no nonblank documents",
            ),
        }
        for name, (statements, message) in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                database = root / "documents.duckdb"
                create_database(database, statements)
                source = duckdb_relation_source(database, relation="docs", source_id="bad-docs")
                out_dir = root / "out"
                with self.assertRaisesRegex(DuckDBRelationError, message):
                    crawl_duckdb_relation(
                        source,
                        CrawlOptions(base_url=source.base_url, out_dir=out_dir, max_pages=10),
                    )
                self.assertFalse((out_dir / "pages").exists())

        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "documents.duckdb"
            create_database(database, ["CREATE TABLE docs(other VARCHAR, content VARCHAR)"])
            source = duckdb_relation_source(database, relation="docs", source_id="missing-column")
            with self.assertRaisesRegex(DuckDBRelationError, "missing ID column 'document_id'"):
                scan_duckdb_relation(source, max_documents=10)
            missing_relation = duckdb_relation_source(database, relation="missing", source_id="missing-relation")
            with self.assertRaises(DuckDBRelationError) as raised:
                scan_duckdb_relation(missing_relation, max_documents=10)
            self.assertIn("Could not read DuckDB relation 'missing'", str(raised.exception))
            self.assertIn("Table with name missing does not exist", str(raised.exception))
            self.assertNotIn("Materialize the final relation", str(raised.exception))

    def test_global_validation_uses_aggregate_queries_and_limited_document_fetch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "documents.duckdb"
            with duckdb.connect(str(database)) as connection:
                connection.execute("CREATE TABLE docs(document_id INTEGER, content VARCHAR)")
                connection.execute(
                    "INSERT INTO docs SELECT value, "
                    "CASE WHEN value % 1000 = 0 THEN ' ' ELSE 'body ' || value END "
                    "FROM range(5000) AS values(value)"
                )
            source = duckdb_relation_source(database, relation="docs", source_id="bounded-docs")
            real_connect = duckdb.connect
            statements: list[str] = []

            class TrackingConnection:
                def __init__(self, connection):
                    self.connection = connection

                def __enter__(self):
                    self.connection.__enter__()
                    return self

                def __exit__(self, *args):
                    return self.connection.__exit__(*args)

                def execute(self, sql, *args):
                    statements.append(sql)
                    self.connection.execute(sql, *args)
                    return self

                @property
                def description(self):
                    return self.connection.description

                def fetchone(self):
                    return self.connection.fetchone()

                def fetchmany(self, size):
                    return self.connection.fetchmany(size)

            def tracked_connect(*args, **kwargs):  # noqa: ANN002, ANN003 - test proxy.
                return TrackingConnection(real_connect(*args, **kwargs))

            with patch("buoy_search.duckdb_relation.duckdb.connect", side_effect=tracked_connect):
                scan = scan_duckdb_relation(source, max_documents=2, batch_size=1)

            self.assertEqual(scan.rows_discovered, 5000)
            self.assertEqual(scan.documents_skipped_empty, 5)
            self.assertEqual(scan.documents_skipped_limit, 4993)
            self.assertEqual([item.document_id for item in scan.documents], ["1", "10"])
            selected_queries = [sql for sql in statements if "ORDER BY" in sql and "FROM" in sql]
            self.assertTrue(any("LIMIT 2" in sql for sql in selected_queries), statements)
            self.assertFalse(any("LIMIT 2" not in sql and "HAVING COUNT(*)" not in sql for sql in selected_queries))

    def test_path_must_exist_and_be_regular_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(ValueError, "does not exist"):
                duckdb_relation_source(root / "missing.duckdb", relation="docs", source_id="docs")
            with self.assertRaisesRegex(ValueError, "regular file"):
                duckdb_relation_source(root, relation="docs", source_id="docs")


if __name__ == "__main__":
    unittest.main()
