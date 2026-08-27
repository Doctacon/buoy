"""Read-only DuckDB relation acquisition for local corpus planning."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import TYPE_CHECKING, Literal
from urllib.parse import urlparse

import duckdb

from buoy_search.relations.base import (
    DatabaseDocument,
    DatabaseRelationError,
    DatabaseRelationExecution,
    PYTHON_STRIP_CHARACTERS,
    crawl_database_relation_with_plan,
    database_base_url,
    database_default_out_dir,
    database_document_url,
    database_namespace_candidate,
    database_site_id,
    stable_page_filename as _stable_page_filename,
    validate_source_id,
    write_database_corpus,
)

if TYPE_CHECKING:
    from buoy_search.indexing.crawler import CrawlOptions

IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
DEFAULT_SCAN_BATCH_SIZE = 500
SAFE_DUCKDB_CONFIG = {
    "enable_external_access": "false",
    "autoinstall_known_extensions": "false",
    "autoload_known_extensions": "false",
    "allow_community_extensions": "false",
}
BLOCKED_EXTERNAL_DEPENDENCY_ERRORS = (
    "file system operations are disabled by configuration",
    "loading external extensions is disabled through configuration",
)


class DuckDBRelationError(DatabaseRelationError):
    """Raised when a DuckDB relation cannot be acquired safely."""


@dataclass(frozen=True)
class DuckDBRelationSource:
    """One DuckDB table or view with stable, path-private logical identity."""

    kind: Literal["duckdb_relation"]
    database_path: Path = field(repr=False)
    relation: str
    source_id: str
    id_column: str
    content_column: str
    title_column: str | None

    @property
    def backend(self) -> str:
        return "duckdb"

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


# Compatibility names retained for existing Python consumers.
DuckDBDocument = DatabaseDocument


@dataclass(frozen=True)
class DuckDBScanResult:
    documents: list[DuckDBDocument]
    rows_scanned: int
    documents_skipped_empty: int
    documents_skipped_limit: int
    title_column: str | None
    diagnostics: dict[str, object] = field(default_factory=dict)

    @property
    def rows_discovered(self) -> int:
        return self.rows_scanned


DuckDBRelationExecution = DatabaseRelationExecution


def validate_identifier(value: str, *, label: str) -> str:
    if not IDENTIFIER_PATTERN.fullmatch(value):
        raise ValueError(
            f"{label} must match ^[A-Za-z_][A-Za-z0-9_]*$ (an ordinary SQL identifier)."
        )
    return value


def validate_relation(value: str) -> str:
    components = value.split(".")
    if not 1 <= len(components) <= 3:
        raise ValueError("--relation must contain one to three dot-separated identifiers.")
    for component in components:
        validate_identifier(component, label="each --relation component")
    return value


def quote_identifier(value: str) -> str:
    """Quote one already-validated ordinary DuckDB identifier."""

    validate_identifier(value, label="identifier")
    return f'"{value}"'


def quote_relation(value: str) -> str:
    validate_relation(value)
    return ".".join(quote_identifier(component) for component in value.split("."))


def validate_duckdb_base_url(value: str) -> str:
    parsed = urlparse(value)
    if (
        parsed.scheme != "duckdb"
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
        or parsed.path != ""
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "DuckDB base URL must be duckdb://<source-id> with no path, "
            "credentials, port, query, or fragment."
        )
    validate_source_id(parsed.netloc)
    return f"duckdb://{parsed.netloc}"


def is_duckdb_base_url(value: str) -> bool:
    return urlparse(value).scheme == "duckdb"


def source_id_from_base_url(value: str) -> str:
    return urlparse(validate_duckdb_base_url(value)).netloc


def duckdb_relation_source(
    database_path: str | Path,
    *,
    relation: str,
    source_id: str,
    id_column: str = "document_id",
    content_column: str = "content",
    title_column: str | None = None,
) -> DuckDBRelationSource:
    path = Path(database_path).expanduser()
    if not path.exists():
        raise ValueError(f"DuckDB database path does not exist: {database_path}")
    if not path.is_file():
        raise ValueError(f"DuckDB database path must be an existing regular file: {database_path}")
    return DuckDBRelationSource(
        kind="duckdb_relation",
        database_path=path,
        relation=validate_relation(relation),
        source_id=validate_source_id(source_id),
        id_column=validate_identifier(id_column, label="--id-column"),
        content_column=validate_identifier(content_column, label="--content-column"),
        title_column=(
            validate_identifier(title_column, label="--title-column")
            if title_column is not None
            else None
        ),
    )


def scan_duckdb_relation(
    source: DuckDBRelationSource,
    *,
    max_documents: int,
    batch_size: int = DEFAULT_SCAN_BATCH_SIZE,
) -> DuckDBScanResult:
    """Validate globally, then acquire only the selected deterministic documents."""

    if max_documents <= 0:
        raise ValueError("max_documents must be greater than zero")
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")

    relation_sql = quote_relation(source.relation)
    try:
        with duckdb.connect(
            str(source.database_path),
            read_only=True,
            config=SAFE_DUCKDB_CONFIG,
        ) as connection:
            # Text conversion of TIMESTAMPTZ values otherwise inherits the host/session zone.
            connection.execute("SET TimeZone='UTC'")
            connection.execute("BEGIN TRANSACTION")
            try:
                description = connection.execute(f"SELECT * FROM {relation_sql} LIMIT 0").description
                available = {str(column[0]).casefold(): str(column[0]) for column in description}
                id_column = require_column(available, source.id_column, label="ID")
                content_column = require_column(available, source.content_column, label="content")
                if source.title_column is not None:
                    title_column = require_column(available, source.title_column, label="title")
                else:
                    title_column = available.get("title")

                id_expression = f"CAST({quote_identifier(id_column)} AS VARCHAR)"
                content_expression = f"CAST({quote_identifier(content_column)} AS VARCHAR)"
                title_expression = (
                    f"CAST({quote_identifier(title_column)} AS VARCHAR)"
                    if title_column is not None
                    else "NULL"
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
                rows_discovered, invalid_ids, skipped_empty, nonblank_documents = connection.execute(
                    f"SELECT COUNT(*), "
                    f"COALESCE(SUM(CASE WHEN NOT ({valid_id}) THEN 1 ELSE 0 END), 0), "
                    f"COALESCE(SUM(CASE WHEN NOT ({nonblank_content}) THEN 1 ELSE 0 END), 0), "
                    f"COALESCE(SUM(CASE WHEN {nonblank_content} THEN 1 ELSE 0 END), 0) "
                    f"FROM {relation_sql}"
                ).fetchone()
                if invalid_ids:
                    raise DuckDBRelationError(
                        f"DuckDB relation {source.relation!r} contains a null or blank document ID "
                        f"in column {source.id_column!r}."
                    )

                duplicate = connection.execute(
                    f"SELECT {id_expression}, COUNT(*) AS duplicate_count "
                    f"FROM {relation_sql} WHERE {valid_id} "
                    f"GROUP BY {id_expression} HAVING COUNT(*) > 1 "
                    f"ORDER BY {id_expression} COLLATE \"binary\" LIMIT 1"
                ).fetchone()
                if duplicate is not None:
                    raise DuckDBRelationError(
                        f"DuckDB relation {source.relation!r} contains duplicate document ID "
                        f"{str(duplicate[0])!r} after text conversion."
                    )
                if not nonblank_documents:
                    raise DuckDBRelationError(
                        f"DuckDB relation {source.relation!r} contains no nonblank documents in "
                        f"content column {source.content_column!r}."
                    )

                cursor = connection.execute(
                    f"SELECT {id_expression}, {content_expression}, {title_expression} "
                    f"FROM {relation_sql} WHERE {nonblank_content} "
                    f"ORDER BY {id_expression} COLLATE \"binary\" LIMIT {int(max_documents)}"
                )
                documents: list[DatabaseDocument] = []
                while True:
                    rows = cursor.fetchmany(batch_size)
                    if not rows:
                        break
                    for raw_id, raw_content, raw_title in rows:
                        document_id = str(raw_id)
                        title = str(raw_title) if raw_title is not None else ""
                        documents.append(
                            DatabaseDocument(
                                document_id=document_id,
                                content=str(raw_content),
                                title=title if title.strip() else document_id,
                            )
                        )
            finally:
                connection.execute("ROLLBACK")
    except DuckDBRelationError:
        raise
    except duckdb.Error as exc:
        if isinstance(exc, duckdb.PermissionException) and any(
            marker in str(exc).casefold() for marker in BLOCKED_EXTERNAL_DEPENDENCY_ERRORS
        ):
            raise DuckDBRelationError(
                f"DuckDB relation {source.relation!r} depends on external files, databases, "
                "or extensions, which Buoy disables for safe read-only indexing. Materialize "
                "the final relation as a table in this DuckDB database upstream, then plan again."
            ) from exc
        raise DuckDBRelationError(
            f"Could not read DuckDB relation {source.relation!r} in read-only mode: {exc}"
        ) from exc

    selected = len(documents)
    return DuckDBScanResult(
        documents=documents,
        rows_scanned=int(rows_discovered),
        documents_skipped_empty=int(skipped_empty),
        documents_skipped_limit=max(0, int(nonblank_documents) - selected),
        title_column=title_column,
    )


def require_column(available: dict[str, str], requested: str, *, label: str) -> str:
    actual = available.get(requested.casefold())
    if actual is None:
        names = ", ".join(sorted(available.values())) or "<none>"
        raise DuckDBRelationError(
            f"DuckDB relation is missing {label} column {requested!r}; available columns: {names}."
        )
    return actual


def stable_page_filename(source: DuckDBRelationSource, document_id: str) -> str:
    return _stable_page_filename(source, document_id)


def write_duckdb_corpus(
    source: DuckDBRelationSource,
    documents: list[DuckDBDocument],
    pages_dir: Path,
    *,
    crawl_timestamp: str,
) -> None:
    """Compatibility wrapper around shared database corpus materialization."""

    write_database_corpus(
        source,
        documents,
        pages_dir,
        crawl_timestamp=crawl_timestamp,
        legacy_metadata=lambda document: {
            "duckdb_source_id": source.source_id,
            "duckdb_relation": source.relation,
            "duckdb_document_id": document.document_id,
        },
    )


def crawl_duckdb_relation_with_plan(
    source: DuckDBRelationSource, options: CrawlOptions
) -> DuckDBRelationExecution:
    """Materialize one relation and hand it to the shared corpus processor."""

    execution = crawl_database_relation_with_plan(
        source,
        options,
        scan_relation=scan_duckdb_relation,
        credentials_required=False,
        source_api_calls_occurred=False,
        summary_fields={
            "duckdb_source_id": source.source_id,
            "duckdb_relation": source.relation,
        },
        legacy_metadata=lambda document: {
            "duckdb_source_id": source.source_id,
            "duckdb_relation": source.relation,
            "duckdb_document_id": document.document_id,
        },
    )
    return execution


def crawl_duckdb_relation(
    source: DuckDBRelationSource, options: CrawlOptions
) -> dict[str, object]:
    return crawl_duckdb_relation_with_plan(source, options).summary
