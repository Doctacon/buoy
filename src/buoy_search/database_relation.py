"""Shared materialization for database-backed document relations.

Backend adapters are responsible only for safe row acquisition. This module owns
stable logical identity, Markdown artifacts, shared chunking, and common summary
semantics. It never opens a database connection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
from typing import TYPE_CHECKING, Callable, Iterable, Mapping, Protocol
from urllib.parse import quote, urlparse

from buoy_search.chunker import IndexingPlan, process_corpus, sha256_text

if TYPE_CHECKING:
    from buoy_search.crawler import CrawlOptions

SOURCE_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DATABASE_BACKENDS = frozenset({"duckdb", "bigquery", "snowflake"})
# The exact characters removed by Python's str.strip() under the supported runtime.
# Backends use this fixed set so blank validation does not depend on narrower SQL TRIM defaults.
PYTHON_STRIP_CHARACTERS = "\t\n\v\f\r\x1c\x1d\x1e\x1f \x85\xa0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000"


class DatabaseRelationError(RuntimeError):
    """Raised when a database document relation cannot be acquired safely."""


class DatabaseRelationSource(Protocol):
    """Small internal contract shared by concrete relation sources."""

    kind: str
    backend: str
    relation: str
    source_id: str
    id_column: str
    content_column: str
    title_column: str | None

    @property
    def base_url(self) -> str: ...

    @property
    def site_id(self) -> str: ...

    @property
    def namespace_candidate(self) -> str: ...

    @property
    def default_out_dir(self) -> Path: ...

    def document_url(self, document_id: str) -> str: ...


@dataclass(frozen=True)
class DatabaseDocument:
    document_id: str
    content: str
    title: str


@dataclass(frozen=True)
class DatabaseScanResult:
    documents: list[DatabaseDocument]
    rows_discovered: int
    documents_skipped_empty: int
    documents_skipped_limit: int
    title_column: str | None
    diagnostics: dict[str, object] = field(default_factory=dict)

    @property
    def rows_scanned(self) -> int:
        """Compatibility spelling retained for existing DuckDB consumers."""

        return self.rows_discovered


@dataclass(frozen=True)
class DatabaseRelationExecution:
    summary: dict[str, object]
    indexing_plan: IndexingPlan


def validate_selected_database_rows(
    rows: Iterable[tuple[object, object, object]],
    *,
    backend: str,
    relation: str,
    error_type: type[DatabaseRelationError] = DatabaseRelationError,
) -> list[DatabaseDocument]:
    """Validate the bounded acquired rows before any Markdown is materialized."""

    backend_name = backend
    documents: list[DatabaseDocument] = []
    document_ids: set[str] = set()
    for raw_id, raw_content, raw_title in rows:
        if raw_id is None:
            raise error_type(
                f"{backend_name} relation {relation!r} selected a null document ID."
            )
        document_id = str(raw_id)
        if not document_id.strip():
            raise error_type(
                f"{backend_name} relation {relation!r} selected a blank document ID."
            )
        if document_id in document_ids:
            raise error_type(
                f"{backend_name} relation {relation!r} selected duplicate document ID "
                f"{document_id!r} after text conversion."
            )
        if raw_content is None:
            raise error_type(
                f"{backend_name} relation {relation!r} selected null content for document ID "
                f"{document_id!r}."
            )
        content = str(raw_content)
        if not content.strip():
            raise error_type(
                f"{backend_name} relation {relation!r} selected blank content for document ID "
                f"{document_id!r}."
            )
        title = "" if raw_title is None else str(raw_title)
        document_ids.add(document_id)
        documents.append(
            DatabaseDocument(
                document_id=document_id,
                content=content,
                title=title if title.strip() else document_id,
            )
        )
    return documents


def validate_source_id(value: str) -> str:
    if not SOURCE_ID_PATTERN.fullmatch(value):
        raise ValueError(
            "--source-id must match ^[a-z0-9]+(?:-[a-z0-9]+)*$ "
            "(lowercase letters, digits, and single hyphens only)."
        )
    return value


def database_base_url(backend: str, source_id: str) -> str:
    if backend not in DATABASE_BACKENDS:
        raise ValueError(f"unsupported database backend {backend!r}")
    return f"{backend}://{validate_source_id(source_id)}"


def validate_database_base_url(value: str) -> str:
    parsed = urlparse(value)
    if (
        parsed.scheme not in DATABASE_BACKENDS
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
            "Database base URL must be duckdb://, bigquery://, or snowflake://<source-id> "
            "with no path, credentials, port, query, or fragment."
        )
    validate_source_id(parsed.netloc)
    return f"{parsed.scheme}://{parsed.netloc}"


def is_database_base_url(value: str) -> bool:
    return urlparse(value).scheme in DATABASE_BACKENDS


def database_identity_from_url(value: str) -> tuple[str, str]:
    parsed = urlparse(validate_database_base_url(value))
    return parsed.scheme, parsed.netloc


def database_site_id(backend: str, source_id: str) -> str:
    validate_source_id(source_id)
    return f"{backend}-{source_id}"


def database_namespace_candidate(backend: str, source_id: str) -> str:
    return f"{database_site_id(backend, source_id)}-v1"


def database_default_out_dir(backend: str, source_id: str) -> Path:
    return Path("artifacts/site-crawls") / database_site_id(backend, source_id)


def database_document_url(backend: str, source_id: str, document_id: str) -> str:
    return f"{database_base_url(backend, source_id)}/{quote(document_id, safe='')}"


def stable_page_filename(source: DatabaseRelationSource, document_id: str) -> str:
    digest = hashlib.sha256(source.document_url(document_id).encode("utf-8")).hexdigest()
    return f"document-{digest[:24]}.md"


def write_database_corpus(
    source: DatabaseRelationSource,
    documents: list[DatabaseDocument],
    pages_dir: Path,
    *,
    crawl_timestamp: str,
    legacy_metadata: Callable[[DatabaseDocument], Mapping[str, object]] | None = None,
) -> None:
    """Write deterministic, scalar-safe Markdown pages for acquired documents."""

    pages_dir.mkdir(parents=True, exist_ok=True)
    for stale_page in pages_dir.glob("*.md"):
        stale_page.unlink()
    for document in documents:
        frontmatter: dict[str, object] = {
            "url": source.document_url(document.document_id),
            "title": document.title,
            "status": 200,
            "content_type": "text/markdown; charset=utf-8",
            "source_kind": source.kind,
            "database_backend": source.backend,
            "database_source_id": source.source_id,
            "database_relation": source.relation,
            "database_document_id": document.document_id,
        }
        if legacy_metadata is not None:
            frontmatter.update(legacy_metadata(document))
        frontmatter.update(
            {
                "source_hash": sha256_text(document.content),
                "crawl_timestamp": crawl_timestamp,
                "fetcher": f"{source.backend}-read-only",
            }
        )
        lines = ["---"]
        lines.extend(
            f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in frontmatter.items()
        )
        lines.extend(["---", ""])
        (pages_dir / stable_page_filename(source, document.document_id)).write_text(
            "\n".join(lines) + document.content, encoding="utf-8"
        )


def crawl_database_relation_with_plan(
    source: DatabaseRelationSource,
    options: CrawlOptions,
    *,
    scan_relation: Callable[..., DatabaseScanResult],
    credentials_required: bool,
    source_api_calls_occurred: bool,
    summary_fields: Mapping[str, object] | None = None,
    legacy_metadata: Callable[[DatabaseDocument], Mapping[str, object]] | None = None,
) -> DatabaseRelationExecution:
    """Acquire, materialize, and process one relation through the shared corpus path."""

    started_at = time.monotonic()
    scan_started_at = time.monotonic()
    scan = scan_relation(source, max_documents=options.max_pages)
    scan_seconds = max(0.0, time.monotonic() - scan_started_at)
    pages_dir = options.out_dir / "pages"
    write_started_at = time.monotonic()
    write_database_corpus(
        source,
        scan.documents,
        pages_dir,
        crawl_timestamp=datetime.now(timezone.utc).isoformat(),
        legacy_metadata=legacy_metadata,
    )
    corpus_write_seconds = max(0.0, time.monotonic() - write_started_at)
    chunk_started_at = time.monotonic()
    plan = process_corpus(
        pages_dir,
        limit_chunks=options.max_chunks,
        target_tokens=options.target_tokens,
        overlap_sentences=options.overlap_sentences,
    )
    chunking_seconds = max(0.0, time.monotonic() - chunk_started_at)
    summary: dict[str, object] = {
        "command": "crawl",
        "dry_run": True,
        "credentials_required": credentials_required,
        "api_calls_occurred": source_api_calls_occurred,
        "source_credentials_required": credentials_required,
        "source_api_calls_occurred": source_api_calls_occurred,
        "turbopuffer_credentials_required": False,
        "turbopuffer_api_calls": False,
        "source_kind": source.kind,
        "base_url": source.base_url,
        "database_backend": source.backend,
        "database_source_id": source.source_id,
        "database_relation": source.relation,
        "id_column": source.id_column,
        "content_column": source.content_column,
        "title_column": scan.title_column,
        "title_column_detected": scan.title_column is not None,
        "allowed_host": "",
        "namespace_candidate": source.namespace_candidate,
        "crawl_strategy": f"{source.backend}-read-only",
        "requested_crawl_strategy": options.crawl_strategy,
        "docs_version_policy": options.docs_version_policy,
        "docs_version_report": {"detected": False, "policy": options.docs_version_policy},
        "language_policy": options.language_policy,
        "language_report": {"detected": False, "policy": options.language_policy},
        "sitemap_seed_urls": [],
        "out_dir": str(options.out_dir),
        "pages_dir": str(pages_dir),
        "max_pages": options.max_pages,
        "max_chunks": options.max_chunks,
        "include_paths": [],
        "exclude_paths": [],
        "strip_trailing_slash": options.strip_trailing_slash,
        "css_selector": None,
        "target_tokens": options.target_tokens,
        "overlap_sentences": options.overlap_sentences,
        "rows_discovered": scan.rows_discovered,
        "rows_scanned": scan.rows_discovered,
        "documents_selected": len(scan.documents),
        "documents_generated": len(scan.documents),
        "documents_skipped_empty": scan.documents_skipped_empty,
        "documents_skipped_limit": scan.documents_skipped_limit,
        "pages_scraped": len(scan.documents),
        "requests_count": 0,
        "robots_disallowed_count": 0,
        "blocked_requests_count": 0,
        "failed_requests_count": 0,
        "files_discovered": plan.files_discovered,
        "files_seen": plan.stats.files_seen,
        "files_error": plan.stats.files_error,
        "chunks_generated": plan.stats.chunks_generated,
        "document_limit_reached": bool(scan.documents_skipped_limit),
        "chunk_limit_reached": plan.limit_reached,
        "limit_reached": bool(scan.documents_skipped_limit) or plan.limit_reached,
        "sample_chunks": [
            {
                "id": chunk.id,
                "title": chunk.title,
                "url": chunk.url,
                "section_path": chunk.section_path,
                "content_preview": chunk.content[:240].replace("\n", " "),
            }
            for chunk in plan.chunks[:3]
        ],
        "errors": [error.__dict__ for error in plan.stats.errors[:10]],
        "timing": {
            "elapsed_seconds": max(0.0, time.monotonic() - started_at),
            "sitemap_policy_seconds": 0.0,
            "crawl_seconds": scan_seconds,
            "corpus_write_seconds": corpus_write_seconds,
            "chunking_seconds": chunking_seconds,
        },
    }
    if summary_fields:
        summary.update(summary_fields)
    summary.update(scan.diagnostics)
    options.out_dir.mkdir(parents=True, exist_ok=True)
    (options.out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    return DatabaseRelationExecution(summary=summary, indexing_plan=plan)
