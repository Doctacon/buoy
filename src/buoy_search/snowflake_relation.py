"""Read-only Snowflake relation acquisition through a named connection."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import hashlib
import math
import re
import time
from typing import TYPE_CHECKING, Literal, Any

from buoy_search.database_relation import (
    DatabaseRelationError,
    DatabaseRelationExecution,
    DatabaseScanResult,
    PYTHON_STRIP_CHARACTERS,
    crawl_database_relation_with_plan,
    database_base_url,
    database_default_out_dir,
    database_document_url,
    database_namespace_candidate,
    database_site_id,
    validate_selected_database_rows,
    validate_source_id,
)

if TYPE_CHECKING:
    from buoy_search.crawler import CrawlOptions

IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
DEFAULT_QUERY_TIMEOUT_SECONDS = 300.0
DEFAULT_FETCH_BATCH_SIZE = 500
SNOWFLAKE_QUERY_TAG_MAX_LENGTH = 2000


class SnowflakeRelationError(DatabaseRelationError):
    """Raised when a Snowflake relation cannot be acquired safely."""


@dataclass(frozen=True)
class SnowflakeRelationSource:
    kind: Literal["snowflake_relation"]
    relation: str
    source_id: str
    id_column: str
    content_column: str
    title_column: str | None
    connection_name: str = field(repr=False)
    query_timeout: float = field(default=DEFAULT_QUERY_TIMEOUT_SECONDS, repr=False)
    operation: str = field(default="plan", repr=False)

    @property
    def backend(self) -> str:
        return "snowflake"

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


def canonicalize_snowflake_identifier(value: str, *, label: str) -> str:
    if not IDENTIFIER_PATTERN.fullmatch(value):
        raise ValueError(f"{label} must be an ordinary unquoted Snowflake identifier.")
    return value.upper()


def validate_snowflake_relation(value: str) -> str:
    components = value.split(".")
    if len(components) != 3:
        raise ValueError(
            "Snowflake --relation must be fully qualified as database.schema.table_or_view."
        )
    return ".".join(
        canonicalize_snowflake_identifier(component, label="each Snowflake relation component")
        for component in components
    )


def quote_snowflake_identifier(value: str) -> str:
    canonical = canonicalize_snowflake_identifier(value, label="Snowflake identifier")
    return f'"{canonical}"'


def quote_snowflake_relation(value: str) -> str:
    canonical = validate_snowflake_relation(value)
    return ".".join(f'"{component}"' for component in canonical.split("."))


def snowflake_relation_source(
    *,
    relation: str,
    source_id: str,
    connection_name: str,
    id_column: str = "document_id",
    content_column: str = "content",
    title_column: str | None = None,
    query_timeout: float = DEFAULT_QUERY_TIMEOUT_SECONDS,
    operation: str = "plan",
) -> SnowflakeRelationSource:
    if not connection_name or not connection_name.strip():
        raise ValueError("--snowflake-connection is required for Snowflake database mode.")
    if not math.isfinite(query_timeout) or query_timeout <= 0:
        raise ValueError("--source-query-timeout must be a finite value greater than zero.")
    return SnowflakeRelationSource(
        kind="snowflake_relation",
        relation=validate_snowflake_relation(relation),
        source_id=validate_source_id(source_id),
        id_column=canonicalize_snowflake_identifier(id_column, label="--id-column"),
        content_column=canonicalize_snowflake_identifier(content_column, label="--content-column"),
        title_column=(
            canonicalize_snowflake_identifier(title_column, label="--title-column")
            if title_column is not None
            else None
        ),
        connection_name=connection_name,
        query_timeout=query_timeout,
        operation=operation,
    )


def _load_connector() -> Any:
    try:
        import snowflake.connector as connector  # type: ignore[import-not-found]
    except ImportError as exc:
        raise SnowflakeRelationError(
            "Snowflake support is not installed. Install the `snowflake` extra. "
            "Run: uv sync --extra snowflake"
        ) from exc
    return connector


def _require_column(available: dict[str, str], requested: str, *, label: str) -> str:
    actual = available.get(requested.upper())
    if actual is None:
        names = ", ".join(sorted(available.values())) or "<none>"
        raise SnowflakeRelationError(
            f"Snowflake relation is missing {label} column {requested!r}; available columns: {names}."
        )
    return actual


def _execute(cursor: object, sql: str, *, timeout: float) -> object:
    return cursor.execute(sql, timeout=timeout)  # type: ignore[attr-defined]


def build_snowflake_query_tag(source_id: str, operation: str) -> str:
    """Return a readable query tag bounded by Snowflake's 2,000-character limit."""

    prefix = f"buoy:{operation}:database-relation:"
    query_tag = f"{prefix}{source_id}"
    if len(query_tag) <= SNOWFLAKE_QUERY_TAG_MAX_LENGTH:
        return query_tag
    source_digest = hashlib.sha256(source_id.encode("utf-8")).hexdigest()
    suffix = f"-sha256-{source_digest}"
    source_prefix_length = SNOWFLAKE_QUERY_TAG_MAX_LENGTH - len(prefix) - len(suffix)
    if source_prefix_length >= 0:
        return f"{prefix}{source_id[:source_prefix_length]}{suffix}"
    operation_digest = hashlib.sha256(operation.encode("utf-8")).hexdigest()
    return (
        f"buoy:operation-sha256-{operation_digest}:database-relation:"
        f"source-sha256-{source_digest}"
    )


def scan_snowflake_relation(
    source: SnowflakeRelationSource,
    *,
    max_documents: int,
    batch_size: int = DEFAULT_FETCH_BATCH_SIZE,
) -> DatabaseScanResult:
    if max_documents <= 0:
        raise ValueError("max_documents must be greater than zero")
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")
    connector = _load_connector()
    connection = None
    cursor = None
    started_at = time.monotonic()
    try:
        query_tag = build_snowflake_query_tag(source.source_id, source.operation)
        connection = connector.connect(
            connection_name=source.connection_name,
            autocommit=False,
            session_parameters={
                "QUERY_TAG": query_tag,
                "STATEMENT_TIMEOUT_IN_SECONDS": int(math.ceil(source.query_timeout)),
            },
        )
        cursor = connection.cursor()
        relation_sql = quote_snowflake_relation(source.relation)
        _execute(cursor, f"SELECT * FROM {relation_sql} LIMIT 0", timeout=source.query_timeout)
        description = cursor.description or ()
        # Ordinary unquoted Snowflake identifiers resolve to uppercase. Quoted mixed-case
        # columns are intentionally not addressable in v1 and must not be mistaken for them.
        available = {
            name: name
            for column in description
            if (name := str(column[0])) == name.upper() and IDENTIFIER_PATTERN.fullmatch(name)
        }
        id_column = _require_column(available, source.id_column, label="ID")
        content_column = _require_column(available, source.content_column, label="content")
        title_column = (
            _require_column(available, source.title_column, label="title")
            if source.title_column is not None
            else available.get("TITLE")
        )
        id_expression = f"CAST({quote_snowflake_identifier(id_column)} AS VARCHAR)"
        content_expression = f"CAST({quote_snowflake_identifier(content_column)} AS VARCHAR)"
        title_expression = (
            f"CAST({quote_snowflake_identifier(title_column)} AS VARCHAR)"
            if title_column is not None
            else "CAST(NULL AS VARCHAR)"
        )
        strip_characters = " || ".join(
            f"CHR({ord(character)})" for character in PYTHON_STRIP_CHARACTERS
        )
        valid_id = (
            f"{id_expression} IS NOT NULL "
            f"AND LENGTH(TRIM({id_expression}, {strip_characters})) > 0"
        )
        nonblank_content = (
            f"{content_expression} IS NOT NULL "
            f"AND LENGTH(TRIM({content_expression}, {strip_characters})) > 0"
        )
        validation_sql = (
            f"SELECT COUNT(*), "
            f"COALESCE(SUM(IFF(NOT ({valid_id}), 1, 0)), 0), "
            f"COALESCE(SUM(IFF(NOT ({nonblank_content}), 1, 0)), 0), "
            f"COALESCE(SUM(IFF({nonblank_content}, 1, 0)), 0) FROM {relation_sql}"
        )
        _execute(cursor, validation_sql, timeout=source.query_timeout)
        validation = cursor.fetchone()
        if validation is None:
            raise SnowflakeRelationError("Snowflake validation query returned no result.")
        rows_discovered, invalid_ids, skipped_empty, nonblank_documents = map(int, validation)
        if invalid_ids:
            raise SnowflakeRelationError(
                f"Snowflake relation {source.relation!r} contains a null or blank document ID "
                f"in column {source.id_column!r}."
            )
        duplicate_sql = (
            f"SELECT {id_expression}, COUNT(*) FROM {relation_sql} WHERE {valid_id} "
            f"GROUP BY {id_expression} HAVING COUNT(*) > 1 ORDER BY {id_expression} LIMIT 1"
        )
        _execute(cursor, duplicate_sql, timeout=source.query_timeout)
        duplicate = cursor.fetchone()
        if duplicate is not None:
            raise SnowflakeRelationError(
                f"Snowflake relation {source.relation!r} contains duplicate document ID "
                f"{str(duplicate[0])!r} after text conversion."
            )
        if not nonblank_documents:
            raise SnowflakeRelationError(
                f"Snowflake relation {source.relation!r} contains no nonblank documents in "
                f"content column {source.content_column!r}."
            )
        documents_sql = (
            f"SELECT {id_expression}, {content_expression}, {title_expression} "
            f"FROM {relation_sql} WHERE ({valid_id}) AND ({nonblank_content}) "
            f"ORDER BY {id_expression} LIMIT {int(max_documents)}"
        )
        _execute(cursor, documents_sql, timeout=source.query_timeout)
        query_id = getattr(cursor, "sfqid", None)
        selected_rows: list[tuple[object, object, object]] = []
        while True:
            rows = cursor.fetchmany(batch_size)
            if not rows:
                break
            selected_rows.extend(rows)
        documents = validate_selected_database_rows(
            selected_rows,
            backend="Snowflake",
            relation=source.relation,
            error_type=SnowflakeRelationError,
        )
        if not documents:
            raise SnowflakeRelationError(
                f"Snowflake relation {source.relation!r} returned no valid selected documents."
            )
        diagnostics: dict[str, object] = {
            "source_query_elapsed_seconds": max(0.0, time.monotonic() - started_at),
        }
        if query_id:
            diagnostics["snowflake_query_id"] = str(query_id)
    except SnowflakeRelationError:
        raise
    except Exception as exc:
        raise SnowflakeRelationError(
            f"Could not read Snowflake relation {source.relation!r} in read-only mode "
            f"({type(exc).__name__}). Check the named connection, relation access, and timeout."
        ) from exc
    finally:
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                pass
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass

    selected = len(documents)
    return DatabaseScanResult(
        documents=documents,
        rows_discovered=rows_discovered,
        documents_skipped_empty=skipped_empty,
        documents_skipped_limit=max(0, nonblank_documents - selected),
        title_column=title_column,
        diagnostics=diagnostics,
    )


def crawl_snowflake_relation_with_plan(
    source: SnowflakeRelationSource, options: CrawlOptions
) -> DatabaseRelationExecution:
    return crawl_database_relation_with_plan(
        source,
        options,
        scan_relation=scan_snowflake_relation,
        credentials_required=True,
        source_api_calls_occurred=True,
    )


def crawl_snowflake_relation(
    source: SnowflakeRelationSource, options: CrawlOptions
) -> dict[str, object]:
    return crawl_snowflake_relation_with_plan(source, options).summary
