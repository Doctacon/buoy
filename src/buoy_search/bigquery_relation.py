"""Read-only BigQuery relation acquisition using Application Default Credentials."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import math
import re
from typing import TYPE_CHECKING, Literal, Any

from buoy_search.database_relation import (
    DatabaseRelationError,
    DatabaseRelationExecution,
    DatabaseScanResult,
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

PROJECT_PATTERN = re.compile(r"^[a-z][a-z0-9-]*[a-z0-9]$|^[a-z]$")
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
DEFAULT_QUERY_TIMEOUT_SECONDS = 300.0


class BigQueryRelationError(DatabaseRelationError):
    """Raised when a BigQuery relation cannot be acquired safely."""


@dataclass(frozen=True)
class BigQueryRelationSource:
    kind: Literal["bigquery_relation"]
    relation: str
    source_id: str
    id_column: str
    content_column: str
    title_column: str | None
    query_project: str | None = field(default=None, repr=False)
    location: str | None = field(default=None, repr=False)
    maximum_bytes_billed: int | None = field(default=None, repr=False)
    query_timeout: float = field(default=DEFAULT_QUERY_TIMEOUT_SECONDS, repr=False)
    operation: str = field(default="plan", repr=False)

    @property
    def backend(self) -> str:
        return "bigquery"

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


def validate_bigquery_identifier(value: str, *, label: str) -> str:
    if not IDENTIFIER_PATTERN.fullmatch(value):
        raise ValueError(f"{label} must be an ordinary unquoted identifier.")
    return value


def validate_bigquery_relation(value: str) -> str:
    components = value.split(".")
    if len(components) != 3:
        raise ValueError("BigQuery --relation must be fully qualified as project.dataset.table_or_view.")
    project, dataset, relation = components
    if not PROJECT_PATTERN.fullmatch(project):
        raise ValueError(
            "BigQuery project must use lowercase letters, digits, and hyphens and begin with a letter."
        )
    validate_bigquery_identifier(dataset, label="BigQuery dataset")
    validate_bigquery_identifier(relation, label="BigQuery table or view")
    return value


def quote_bigquery_identifier(value: str) -> str:
    validate_bigquery_identifier(value, label="BigQuery column")
    return f"`{value}`"


def quote_bigquery_relation(value: str) -> str:
    return f"`{validate_bigquery_relation(value)}`"


def bigquery_relation_source(
    *,
    relation: str,
    source_id: str,
    id_column: str = "document_id",
    content_column: str = "content",
    title_column: str | None = None,
    query_project: str | None = None,
    location: str | None = None,
    maximum_bytes_billed: int | None = None,
    query_timeout: float = DEFAULT_QUERY_TIMEOUT_SECONDS,
    operation: str = "plan",
) -> BigQueryRelationSource:
    if query_project is not None and not PROJECT_PATTERN.fullmatch(query_project):
        raise ValueError("--bigquery-project must be a valid lowercase Google Cloud project ID.")
    if location is not None and not location.strip():
        raise ValueError("--bigquery-location must not be empty.")
    if maximum_bytes_billed is not None and maximum_bytes_billed <= 0:
        raise ValueError("--bigquery-maximum-bytes-billed must be greater than zero.")
    if not math.isfinite(query_timeout) or query_timeout <= 0:
        raise ValueError("--source-query-timeout must be a finite value greater than zero.")
    return BigQueryRelationSource(
        kind="bigquery_relation",
        relation=validate_bigquery_relation(relation),
        source_id=validate_source_id(source_id),
        id_column=validate_bigquery_identifier(id_column, label="--id-column"),
        content_column=validate_bigquery_identifier(content_column, label="--content-column"),
        title_column=(
            validate_bigquery_identifier(title_column, label="--title-column")
            if title_column is not None
            else None
        ),
        query_project=query_project,
        location=location,
        maximum_bytes_billed=maximum_bytes_billed,
        query_timeout=query_timeout,
        operation=operation,
    )


def _load_bigquery() -> Any:
    try:
        from google.cloud import bigquery  # type: ignore[import-not-found]
    except ImportError as exc:
        raise BigQueryRelationError(
            "BigQuery support is not installed. Install the `bigquery` extra. "
            "Run: uv sync --extra bigquery"
        ) from exc
    return bigquery


def _row_value(row: object, key: str, index: int) -> object:
    if isinstance(row, dict):
        return row[key]
    try:
        return row[key]  # type: ignore[index]
    except (KeyError, TypeError, IndexError):
        return row[index]  # type: ignore[index]


def _require_column(available: dict[str, str], requested: str, *, label: str) -> str:
    actual = available.get(requested.casefold())
    if actual is None:
        names = ", ".join(sorted(available.values())) or "<none>"
        raise BigQueryRelationError(
            f"BigQuery relation is missing {label} column {requested!r}; available columns: {names}."
        )
    return actual


def _query_config(bigquery: Any, source: BigQueryRelationSource, *, dry_run: bool) -> object:
    kwargs: dict[str, object] = {
        "dry_run": dry_run,
        "use_query_cache": False if dry_run else True,
        "labels": {"buoy": "database-relation", "buoy-operation": source.operation},
    }
    if not dry_run and source.maximum_bytes_billed is not None:
        kwargs["maximum_bytes_billed"] = source.maximum_bytes_billed
    if not dry_run:
        # Official server-side best-effort timeout bounds warehouse execution in addition
        # to the client polling timeout passed to QueryJob.result().
        kwargs["job_timeout_ms"] = max(1, int(math.ceil(source.query_timeout * 1000)))
    return bigquery.QueryJobConfig(**kwargs)


def _job_result(job: object, *, timeout: float) -> object:
    try:
        return job.result(timeout=timeout)  # type: ignore[attr-defined]
    except Exception as exc:
        if isinstance(exc, TimeoutError) or type(exc).__name__ in {"DeadlineExceeded", "TimeoutError"}:
            try:
                job.cancel()  # type: ignore[attr-defined]
            except Exception:
                pass
            raise BigQueryRelationError(
                "BigQuery source query exceeded --source-query-timeout and cancellation was requested."
            ) from exc
        raise


def _build_source_query(
    *,
    relation_sql: str,
    id_expression: str,
    content_expression: str,
    title_expression: str,
    max_documents: int,
) -> str:
    """Build one read-only statement containing summary, duplicate, and document rows."""

    return f"""WITH converted AS (
  SELECT
    {id_expression} AS document_id,
    {content_expression} AS content,
    {title_expression} AS title
  FROM {relation_sql}
), source_rows AS (
  SELECT
    document_id,
    content,
    title,
    document_id IS NOT NULL AND LENGTH(TRIM(document_id)) > 0 AS valid_id,
    content IS NOT NULL AND LENGTH(TRIM(content)) > 0 AS nonblank_content
  FROM converted
), summary AS (
  SELECT
    COUNT(*) AS rows_discovered,
    COUNTIF(NOT valid_id) AS invalid_ids,
    COUNTIF(NOT nonblank_content) AS skipped_empty,
    COUNTIF(nonblank_content) AS nonblank_documents
  FROM source_rows
), duplicate_ids AS (
  SELECT document_id
  FROM source_rows
  WHERE valid_id
  GROUP BY document_id
  HAVING COUNT(*) > 1
  ORDER BY document_id
  LIMIT 1
), documents AS (
  SELECT document_id, content, title
  FROM source_rows
  WHERE valid_id AND nonblank_content
  ORDER BY document_id
  LIMIT {int(max_documents)}
)
SELECT
  0 AS result_order,
  'summary' AS result_kind,
  rows_discovered,
  invalid_ids,
  skipped_empty,
  nonblank_documents,
  CAST(NULL AS STRING) AS document_id,
  CAST(NULL AS STRING) AS content,
  CAST(NULL AS STRING) AS title
FROM summary
UNION ALL
SELECT
  1,
  'duplicate',
  CAST(NULL AS INT64),
  CAST(NULL AS INT64),
  CAST(NULL AS INT64),
  CAST(NULL AS INT64),
  document_id,
  CAST(NULL AS STRING),
  CAST(NULL AS STRING)
FROM duplicate_ids
UNION ALL
SELECT
  2,
  'document',
  CAST(NULL AS INT64),
  CAST(NULL AS INT64),
  CAST(NULL AS INT64),
  CAST(NULL AS INT64),
  document_id,
  content,
  title
FROM documents
ORDER BY result_order, document_id"""


def scan_bigquery_relation(
    source: BigQueryRelationSource,
    *,
    max_documents: int,
) -> DatabaseScanResult:
    if max_documents <= 0:
        raise ValueError("max_documents must be greater than zero")
    bigquery = _load_bigquery()
    client = None
    try:
        client = bigquery.Client(project=source.query_project, location=source.location)
        table = client.get_table(source.relation)
        available = {str(field.name).casefold(): str(field.name) for field in table.schema}
        id_column = _require_column(available, source.id_column, label="ID")
        content_column = _require_column(available, source.content_column, label="content")
        title_column = (
            _require_column(available, source.title_column, label="title")
            if source.title_column is not None
            else available.get("title")
        )
        relation_sql = quote_bigquery_relation(source.relation)
        id_expression = f"CAST({quote_bigquery_identifier(id_column)} AS STRING)"
        content_expression = f"CAST({quote_bigquery_identifier(content_column)} AS STRING)"
        title_expression = (
            f"CAST({quote_bigquery_identifier(title_column)} AS STRING)"
            if title_column is not None
            else "CAST(NULL AS STRING)"
        )
        query_sql = _build_source_query(
            relation_sql=relation_sql,
            id_expression=id_expression,
            content_expression=content_expression,
            title_expression=title_expression,
            max_documents=max_documents,
        )
        dry_job = client.query(
            query_sql, job_config=_query_config(bigquery, source, dry_run=True)
        )
        estimated_bytes = int(getattr(dry_job, "total_bytes_processed", 0) or 0)
        if (
            source.maximum_bytes_billed is not None
            and estimated_bytes > source.maximum_bytes_billed
        ):
            raise BigQueryRelationError(
                "BigQuery aggregate dry-run estimate exceeds --bigquery-maximum-bytes-billed: "
                f"estimated {estimated_bytes} bytes; cap {source.maximum_bytes_billed} bytes."
            )

        query_job = client.query(
            query_sql, job_config=_query_config(bigquery, source, dry_run=False)
        )
        result_rows = iter(_job_result(query_job, timeout=source.query_timeout))
        summary = next(result_rows, None)
        if summary is None or _row_value(summary, "result_kind", 1) != "summary":
            raise BigQueryRelationError("BigQuery source query returned no summary result.")
        rows_discovered = int(_row_value(summary, "rows_discovered", 2))
        invalid_ids = int(_row_value(summary, "invalid_ids", 3))
        skipped_empty = int(_row_value(summary, "skipped_empty", 4))
        nonblank_documents = int(_row_value(summary, "nonblank_documents", 5))
        if invalid_ids:
            raise BigQueryRelationError(
                f"BigQuery relation {source.relation!r} contains a null or blank document ID "
                f"in column {source.id_column!r}."
            )
        if not nonblank_documents:
            raise BigQueryRelationError(
                f"BigQuery relation {source.relation!r} contains no nonblank documents in "
                f"content column {source.content_column!r}."
            )

        selected_rows: list[tuple[object, object, object]] = []
        for row in result_rows:
            result_kind = _row_value(row, "result_kind", 1)
            if result_kind == "duplicate":
                duplicate_id = str(_row_value(row, "document_id", 6))
                raise BigQueryRelationError(
                    f"BigQuery relation {source.relation!r} contains duplicate document ID "
                    f"{duplicate_id!r} after text conversion."
                )
            if result_kind != "document":
                raise BigQueryRelationError("BigQuery source query returned an unknown result kind.")
            selected_rows.append(
                (
                    _row_value(row, "document_id", 6),
                    _row_value(row, "content", 7),
                    _row_value(row, "title", 8),
                )
            )
        documents = validate_selected_database_rows(
            selected_rows,
            backend="BigQuery",
            relation=source.relation,
            error_type=BigQueryRelationError,
        )
        if not documents:
            raise BigQueryRelationError(
                f"BigQuery relation {source.relation!r} returned no valid selected documents."
            )
        diagnostics: dict[str, object] = {
            "bigquery_estimated_bytes_processed": estimated_bytes,
            "bigquery_total_bytes_processed": int(
                getattr(query_job, "total_bytes_processed", 0) or 0
            ),
            "bigquery_cache_hit": getattr(query_job, "cache_hit", None) is True,
        }
        job_id = getattr(query_job, "job_id", None)
        if job_id:
            diagnostics["bigquery_query_job_id"] = str(job_id)
    except BigQueryRelationError:
        raise
    except Exception as exc:
        raise BigQueryRelationError(
            f"Could not read BigQuery relation {source.relation!r} in read-only mode "
            f"({type(exc).__name__}). Check source authentication, relation access, and timeout."
        ) from exc
    finally:
        if client is not None:
            close = getattr(client, "close", None)
            if callable(close):
                try:
                    close()
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


def crawl_bigquery_relation_with_plan(
    source: BigQueryRelationSource, options: CrawlOptions
) -> DatabaseRelationExecution:
    return crawl_database_relation_with_plan(
        source,
        options,
        scan_relation=scan_bigquery_relation,
        credentials_required=True,
        source_api_calls_occurred=True,
    )


def crawl_bigquery_relation(
    source: BigQueryRelationSource, options: CrawlOptions
) -> dict[str, object]:
    return crawl_bigquery_relation_with_plan(source, options).summary
