from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from buoy_search.crawler import CrawlOptions
from buoy_search.snowflake_relation import (
    SNOWFLAKE_QUERY_TAG_MAX_LENGTH,
    SnowflakeRelationError,
    build_snowflake_query_tag,
    canonicalize_snowflake_identifier,
    crawl_snowflake_relation,
    scan_snowflake_relation,
    snowflake_relation_source,
    validate_snowflake_relation,
)


class FakeSnowflakeCursor:
    schema = ["DOCUMENT_ID", "CONTENT", "TITLE"]
    validation = (4, 0, 1, 3)
    duplicate: tuple[object, ...] | None = None
    documents = [
        ("a/1", "Alpha body", "Alpha"),
        ("b", "Beta body", None),
    ]
    fail_on: str | None = None

    def __init__(self) -> None:
        self.description: list[tuple[object, ...]] | None = None
        self.executions: list[tuple[str, float]] = []
        self._rows: list[tuple[object, ...]] = []
        self.fetchmany_calls: list[int] = []
        self.closed = False
        self.sfqid: str | None = None

    def execute(self, sql: str, *, timeout: float) -> "FakeSnowflakeCursor":
        self.executions.append((sql, timeout))
        if type(self).fail_on and type(self).fail_on in sql:
            raise RuntimeError("warehouse failure")
        if "SELECT *" in sql and "LIMIT 0" in sql:
            self.description = [(name,) for name in type(self).schema]
            self._rows = []
        elif "SELECT COUNT(*)" in sql:
            self._rows = [tuple(type(self).validation)]
        elif "HAVING COUNT(*) > 1" in sql:
            self._rows = [] if type(self).duplicate is None else [type(self).duplicate]
        else:
            self._rows = list(type(self).documents)
            self.sfqid = "snow-query-123"
        return self

    def fetchone(self) -> tuple[object, ...] | None:
        return self._rows.pop(0) if self._rows else None

    def fetchmany(self, size: int) -> list[tuple[object, ...]]:
        self.fetchmany_calls.append(size)
        rows, self._rows = self._rows[:size], self._rows[size:]
        return rows

    def close(self) -> None:
        self.closed = True


class FakeSnowflakeConnection:
    def __init__(self) -> None:
        self.cursor_instance = FakeSnowflakeCursor()
        self.rolled_back = False
        self.closed = False

    def cursor(self) -> FakeSnowflakeCursor:
        return self.cursor_instance

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


class FakeSnowflakeConnector:
    calls: list[dict[str, object]] = []
    connections: list[FakeSnowflakeConnection] = []

    @classmethod
    def connect(cls, **kwargs: object) -> FakeSnowflakeConnection:
        cls.calls.append(kwargs)
        connection = FakeSnowflakeConnection()
        cls.connections.append(connection)
        return connection


class SnowflakeRelationTests(unittest.TestCase):
    def setUp(self) -> None:
        FakeSnowflakeConnector.calls.clear()
        FakeSnowflakeConnector.connections.clear()
        FakeSnowflakeCursor.schema = ["DOCUMENT_ID", "CONTENT", "TITLE"]
        FakeSnowflakeCursor.validation = (4, 0, 1, 3)
        FakeSnowflakeCursor.duplicate = None
        FakeSnowflakeCursor.documents = [
            ("a/1", "Alpha body", "Alpha"),
            ("b", "Beta body", None),
        ]
        FakeSnowflakeCursor.fail_on = None

    def test_source_canonicalizes_ordinary_identifiers_and_identity(self) -> None:
        source = snowflake_relation_source(
            relation="analytics.corpus.documents",
            source_id="gong-calls",
            connection_name="secret-profile",
            id_column="document_id",
            content_column="content",
        )
        self.assertEqual(source.relation, "ANALYTICS.CORPUS.DOCUMENTS")
        self.assertEqual(source.id_column, "DOCUMENT_ID")
        self.assertEqual(source.base_url, "snowflake://gong-calls")
        self.assertEqual(source.site_id, "snowflake-gong-calls")
        self.assertEqual(source.namespace_candidate, "snowflake-gong-calls-v1")
        self.assertEqual(source.document_url("call/a"), "snowflake://gong-calls/call%2Fa")
        self.assertNotIn("secret-profile", repr(source))
        with self.assertRaises(ValueError):
            canonicalize_snowflake_identifier("abc_$1", label="x")
        for invalid in (
            "DB.SCHEMA",
            '"Db".SCHEMA.TABLE',
            "DB.SCHEMA.TABLE;DROP",
            "DB.SCHE MA.TABLE",
            "DB.SCHEMA.*",
            "DB.SCHEMA.FUNC()",
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                validate_snowflake_relation(invalid)

    def test_named_connection_query_tag_timeout_read_only_sql_and_fetchmany(self) -> None:
        source = snowflake_relation_source(
            relation="analytics.corpus.documents",
            source_id="gong-calls",
            connection_name="analytics",
            query_timeout=12.25,
            operation="crawl",
        )
        with patch("buoy_search.snowflake_relation._load_connector", return_value=FakeSnowflakeConnector):
            result = scan_snowflake_relation(source, max_documents=2, batch_size=1)

        call = FakeSnowflakeConnector.calls[0]
        self.assertEqual(call["connection_name"], "analytics")
        self.assertFalse(call["autocommit"])
        self.assertEqual(
            call["session_parameters"],
            {
                "QUERY_TAG": "buoy:crawl:database-relation:gong-calls",
                "STATEMENT_TIMEOUT_IN_SECONDS": 13,
            },
        )
        connection = FakeSnowflakeConnector.connections[0]
        cursor = connection.cursor_instance
        self.assertTrue(connection.rolled_back)
        self.assertTrue(connection.closed)
        self.assertTrue(cursor.closed)
        self.assertGreaterEqual(len(cursor.fetchmany_calls), 3)
        self.assertTrue(all(timeout == 12.25 for _, timeout in cursor.executions))
        sql = "\n".join(query for query, _ in cursor.executions)
        self.assertIn('FROM "ANALYTICS"."CORPUS"."DOCUMENTS"', sql)
        self.assertIn("WHERE (CAST(\"DOCUMENT_ID\" AS VARCHAR) IS NOT NULL", sql)
        self.assertIn("AND (CAST(\"CONTENT\" AS VARCHAR) IS NOT NULL", sql)
        self.assertIn("ORDER BY CAST(\"DOCUMENT_ID\" AS VARCHAR) LIMIT 2", sql)
        self.assertIn("CHR(9)", sql)
        self.assertIn("CHR(12288)", sql)
        self.assertNotRegex(sql, r"(?i)\b(CREATE|INSERT|UPDATE|DELETE|MERGE|DROP|ALTER)\b")
        self.assertEqual([doc.document_id for doc in result.documents], ["a/1", "b"])
        self.assertEqual(result.documents[1].title, "b")
        self.assertEqual(result.rows_discovered, 4)
        self.assertEqual(result.documents_skipped_empty, 1)
        self.assertEqual(result.documents_skipped_limit, 1)
        self.assertEqual(result.diagnostics["snowflake_query_id"], "snow-query-123")

    def test_query_tag_is_deterministically_bounded(self) -> None:
        self.assertEqual(
            build_snowflake_query_tag("gong-calls", "crawl"),
            "buoy:crawl:database-relation:gong-calls",
        )
        shared_prefix = "a" * 2500
        first = build_snowflake_query_tag(f"{shared_prefix}-one", "plan")
        second = build_snowflake_query_tag(f"{shared_prefix}-two", "plan")
        self.assertLessEqual(len(first), SNOWFLAKE_QUERY_TAG_MAX_LENGTH)
        self.assertLessEqual(len(second), SNOWFLAKE_QUERY_TAG_MAX_LENGTH)
        self.assertTrue(first.startswith("buoy:plan:database-relation:"))
        self.assertIn("-sha256-", first)
        self.assertNotEqual(first, second)
        self.assertNotIn("secret-profile", first)
        self.assertNotIn("analytics-account", first)

        long_source_id = "a" * 2501
        source = snowflake_relation_source(
            relation="DB.SCHEMA.DOCS",
            source_id=long_source_id,
            connection_name="secret-profile",
        )
        with patch(
            "buoy_search.snowflake_relation._load_connector",
            return_value=FakeSnowflakeConnector,
        ):
            scan_snowflake_relation(source, max_documents=2)
        configured_tag = FakeSnowflakeConnector.calls[-1]["session_parameters"]["QUERY_TAG"]
        self.assertEqual(configured_tag, build_snowflake_query_tag(long_source_id, "plan"))
        self.assertLessEqual(len(configured_tag), SNOWFLAKE_QUERY_TAG_MAX_LENGTH)
        self.assertNotIn("secret-profile", configured_tag)

    def test_custom_mapping_and_title_auto_detection(self) -> None:
        FakeSnowflakeCursor.schema = ["CALL_ID", "TRANSCRIPT"]
        source = snowflake_relation_source(
            relation="analytics.corpus.calls",
            source_id="calls",
            connection_name="analytics",
            id_column="call_id",
            content_column="transcript",
        )
        with patch("buoy_search.snowflake_relation._load_connector", return_value=FakeSnowflakeConnector):
            result = scan_snowflake_relation(source, max_documents=2)
        self.assertIsNone(result.title_column)
        sql = FakeSnowflakeConnector.connections[0].cursor_instance.executions[-1][0]
        self.assertIn("CAST(NULL AS VARCHAR)", sql)

    def test_quoted_mixed_case_schema_column_is_not_treated_as_ordinary(self) -> None:
        FakeSnowflakeCursor.schema = ["Document_Id", "CONTENT"]
        source = snowflake_relation_source(
            relation="DB.SCHEMA.DOCS", source_id="docs", connection_name="analytics"
        )
        with patch("buoy_search.snowflake_relation._load_connector", return_value=FakeSnowflakeConnector):
            with self.assertRaisesRegex(SnowflakeRelationError, "missing ID column"):
                scan_snowflake_relation(source, max_documents=1)
        self.assertTrue(FakeSnowflakeConnector.connections[-1].closed)

    def test_nonfinite_timeout_is_rejected(self) -> None:
        for timeout in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(timeout=timeout), self.assertRaisesRegex(ValueError, "finite value"):
                snowflake_relation_source(
                    relation="DB.SCHEMA.DOCS",
                    source_id="docs",
                    connection_name="analytics",
                    query_timeout=timeout,
                )

    def test_null_duplicate_and_all_empty_failures_close_resources(self) -> None:
        source = snowflake_relation_source(
            relation="DB.SCHEMA.DOCS", source_id="docs", connection_name="analytics"
        )
        FakeSnowflakeCursor.validation = (1, 1, 0, 1)
        with patch("buoy_search.snowflake_relation._load_connector", return_value=FakeSnowflakeConnector):
            with self.assertRaisesRegex(SnowflakeRelationError, "null or blank"):
                scan_snowflake_relation(source, max_documents=1)
        self.assertTrue(FakeSnowflakeConnector.connections[-1].closed)
        self.assertTrue(FakeSnowflakeConnector.connections[-1].cursor_instance.closed)

        FakeSnowflakeCursor.validation = (2, 0, 0, 2)
        FakeSnowflakeCursor.duplicate = ("1", 2)
        with patch("buoy_search.snowflake_relation._load_connector", return_value=FakeSnowflakeConnector):
            with self.assertRaisesRegex(SnowflakeRelationError, "duplicate document ID '1'"):
                scan_snowflake_relation(source, max_documents=1)
        FakeSnowflakeCursor.duplicate = None
        FakeSnowflakeCursor.validation = (1, 0, 1, 0)
        with patch("buoy_search.snowflake_relation._load_connector", return_value=FakeSnowflakeConnector):
            with self.assertRaisesRegex(SnowflakeRelationError, "no nonblank documents"):
                scan_snowflake_relation(source, max_documents=1)

    def test_selected_rows_are_revalidated_after_global_validation(self) -> None:
        source = snowflake_relation_source(
            relation="DB.SCHEMA.DOCS", source_id="docs", connection_name="analytics"
        )
        cases = (
            ([(None, "body", None)], "null document ID"),
            ([("\u3000", "body", None)], "blank document ID"),
            ([('same', "one", None), ('same', "two", None)], "selected duplicate document ID 'same'"),
            ([("a", None, None)], "null content"),
            ([("a", "\u2003", None)], "blank content"),
        )
        for documents, message in cases:
            with self.subTest(message=message):
                FakeSnowflakeConnector.calls.clear()
                FakeSnowflakeConnector.connections.clear()
                FakeSnowflakeCursor.documents = documents
                with patch(
                    "buoy_search.snowflake_relation._load_connector",
                    return_value=FakeSnowflakeConnector,
                ):
                    with self.assertRaisesRegex(SnowflakeRelationError, message):
                        scan_snowflake_relation(source, max_documents=2)
                connection = FakeSnowflakeConnector.connections[-1]
                self.assertTrue(connection.rolled_back)
                self.assertTrue(connection.cursor_instance.closed)
                self.assertTrue(connection.closed)

    def test_selected_validation_fails_before_markdown_materialization(self) -> None:
        FakeSnowflakeCursor.documents = [(None, "body", None)]
        source = snowflake_relation_source(
            relation="DB.SCHEMA.DOCS", source_id="docs", connection_name="analytics"
        )
        with tempfile.TemporaryDirectory() as tmp:
            options = CrawlOptions(
                base_url=source.base_url, out_dir=Path(tmp) / "out", max_pages=1
            )
            with patch(
                "buoy_search.snowflake_relation._load_connector",
                return_value=FakeSnowflakeConnector,
            ):
                with self.assertRaises(SnowflakeRelationError):
                    crawl_snowflake_relation(source, options)
            self.assertFalse((Path(tmp) / "out" / "pages").exists())

    def test_selected_valid_complex_ids_round_trip(self) -> None:
        complex_ids = ['call/ü"quoted\\path', "雪/meeting\\notes"]
        FakeSnowflakeCursor.documents = [
            (value, f"Body {index}", "\u3000") for index, value in enumerate(complex_ids)
        ]
        source = snowflake_relation_source(
            relation="DB.SCHEMA.DOCS", source_id="docs", connection_name="analytics"
        )
        with patch(
            "buoy_search.snowflake_relation._load_connector",
            return_value=FakeSnowflakeConnector,
        ):
            result = scan_snowflake_relation(source, max_documents=2)
        self.assertEqual([document.document_id for document in result.documents], complex_ids)
        self.assertEqual([document.title for document in result.documents], complex_ids)

    def test_connector_failure_closes_cursor_and_connection(self) -> None:
        source = snowflake_relation_source(
            relation="DB.SCHEMA.DOCS", source_id="docs", connection_name="analytics"
        )
        FakeSnowflakeCursor.fail_on = "SELECT COUNT(*)"
        with patch("buoy_search.snowflake_relation._load_connector", return_value=FakeSnowflakeConnector):
            with self.assertRaisesRegex(SnowflakeRelationError, r"\(RuntimeError\).+named connection"):
                scan_snowflake_relation(source, max_documents=1)
        connection = FakeSnowflakeConnector.connections[-1]
        self.assertTrue(connection.rolled_back)
        self.assertTrue(connection.cursor_instance.closed)
        self.assertTrue(connection.closed)

    def test_missing_dependency_error(self) -> None:
        import buoy_search.snowflake_relation as module

        with patch.dict(sys.modules, {"snowflake": None, "snowflake.connector": None}):
            with self.assertRaisesRegex(SnowflakeRelationError, "uv sync --extra snowflake"):
                module._load_connector()

    def test_crawl_summary_has_truthful_remote_activity_without_profile_leak(self) -> None:
        source = snowflake_relation_source(
            relation="DB.SCHEMA.DOCS",
            source_id="docs",
            connection_name="sensitive-profile",
        )
        with tempfile.TemporaryDirectory() as tmp:
            options = CrawlOptions(base_url=source.base_url, out_dir=Path(tmp), max_pages=2, max_chunks=10)
            with patch("buoy_search.snowflake_relation._load_connector", return_value=FakeSnowflakeConnector):
                summary = crawl_snowflake_relation(source, options)
            self.assertTrue(summary["credentials_required"])
            self.assertTrue(summary["api_calls_occurred"])
            self.assertFalse(summary["turbopuffer_api_calls"])
            serialized = str(summary) + "".join(
                page.read_text(encoding="utf-8") for page in (Path(tmp) / "pages").glob("*.md")
            )
            self.assertNotIn("sensitive-profile", serialized)


if __name__ == "__main__":
    unittest.main()
