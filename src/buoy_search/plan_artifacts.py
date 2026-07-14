"""Local-only plan artifact models for generic site RAG indexing.

This module builds deterministic review/apply artifacts from an already-created
Markdown corpus and indexing plan. It does not read credentials, load embedding
models, or call turbopuffer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable

from buoy_search.crawler import namespace_candidate, safe_slug, source_id_for_url, validate_base_url
from buoy_search.chunker import (
    TURBOPUFFER_SCHEMA,
    IndexingPlan,
    MarkdownChunk,
    parse_markdown_file,
    sha256_text,
)

PLAN_SCHEMA_VERSION = 1
DEFAULT_PLAN_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
VOLATILE_FRONTMATTER_KEYS = {"crawl_timestamp"}
GENERIC_SITE_TURBOPUFFER_SCHEMA = {
    **TURBOPUFFER_SCHEMA,
    "site_id": {"type": "string"},
    "canonical_url": {"type": "string"},
    "page_hash": {"type": "string"},
    "chunk_hash": {"type": "string"},
    "embedding_text_hash": {"type": "string"},
    "plan_id": {"type": "string"},
    "applied_at": {"type": "string"},
    "source_kind": {"type": "string"},
    "repo_full_name": {"type": "string"},
    "repo_owner": {"type": "string"},
    "repo_name": {"type": "string"},
    "repo_ref": {"type": "string"},
    "commit_sha": {"type": "string"},
    "repo_path": {"type": "string"},
    "language": {"type": "string"},
    "file_filename": {"type": "string"},
    "file_extension": {"type": "string"},
    "file_sha256": {"type": "string"},
    "file_source_id": {"type": "string"},
    "pdf_filename": {"type": "string"},
    "pdf_sha256": {"type": "string"},
    "pdf_source_id": {"type": "string"},
}
SOURCE_METADATA_ROW_FIELDS = (
    "source_kind",
    "repo_full_name",
    "repo_owner",
    "repo_name",
    "repo_ref",
    "commit_sha",
    "repo_path",
    "language",
    "file_filename",
    "file_extension",
    "file_sha256",
    "file_source_id",
    "pdf_filename",
    "pdf_sha256",
    "pdf_source_id",
)

JsonObject = dict[str, Any]


@dataclass(frozen=True)
class PageManifestRecord:
    """One crawled Markdown page represented in a plan manifest."""

    canonical_url: str
    title: str
    content_path: str
    page_hash: str
    status: int | None
    content_type: str
    source_metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ChunkManifestRecord:
    """One desired chunk represented in a plan manifest and JSONL output."""

    row_id: str
    row_id_candidate: str
    site_id: str
    duplicate_ordinal: int
    canonical_url: str
    page_content_path: str
    page_hash: str
    chunk_hash: str
    embedding_text_hash: str
    title: str
    section_path: str
    chunk_index: int
    content: str
    content_preview: str
    doc_kind: str
    tags: list[str]
    source_metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ManifestDocument:
    """Complete desired source/page/chunk manifest for an applyable plan."""

    schema_version: int
    site_id: str
    base_url: str
    namespace: str
    namespace_candidate: str
    pages: list[PageManifestRecord]
    chunks: list[ChunkManifestRecord]


@dataclass(frozen=True)
class PlanDocument:
    """Top-level plan metadata written to ``plan.json``."""

    schema_version: int
    command: str
    plan_id: str
    created_at: str
    base_url: str
    site_id: str
    namespace: str
    namespace_candidate: str
    state_backend: str
    state_path: str
    crawl_options: JsonObject
    chunk_options: JsonObject
    embedding_model: str
    artifact_hash: str
    manifest_path: str
    chunks_path: str
    pages_dir: str
    diff: JsonObject


@dataclass(frozen=True)
class PlanArtifacts:
    """Serializable plan artifacts before/after writing to disk."""

    plan: PlanDocument
    manifest: ManifestDocument
    chunks_jsonl: str

    def plan_dict(self) -> JsonObject:
        return dataclass_to_json_object(self.plan)

    def manifest_dict(self) -> JsonObject:
        return dataclass_to_json_object(self.manifest)


def site_id_for_url(base_url: str) -> str:
    """Return the deterministic local state site ID for an absolute URL."""

    return safe_slug(source_id_for_url(base_url), fallback="site")


def state_path_for_site(site_id: str, namespace: str, *, state_root: Path = Path(".buoy")) -> str:
    """Return the local applied-state path for a site/namespace."""

    return str(Path(state_root) / "state" / site_id / namespace / "state.duckdb")


def generic_site_row_id(
    *,
    site_id: str,
    canonical_url: str,
    section_path: str,
    chunk_hash: str,
    duplicate_ordinal: int = 0,
) -> str:
    """Return a stable generic-site row ID independent of page-level hashes.

    The default identity uses semantic chunk inputs only. A duplicate ordinal is
    included only when the same URL/section/content group appears more than
    once in a manifest, preventing row ID collisions without making ordinary
    unique chunks depend on page hash, page path, or chunk index.
    """

    parts = [site_id, canonical_url, section_path, chunk_hash]
    if duplicate_ordinal:
        parts.extend(["duplicate", str(duplicate_ordinal)])
    digest = sha256_text("\n".join(parts))[:32]
    return f"ts_{digest}"


def generic_row_id_candidate(
    *,
    site_id: str,
    canonical_url: str,
    section_path: str,
    chunk_hash: str,
    page_content_path: str = "",
    chunk_index: int | None = None,
    duplicate_ordinal: int = 0,
) -> str:
    """Return a deterministic candidate row ID for generic-site chunks.

    ``page_content_path`` and ``chunk_index`` are accepted for compatibility
    with the first plan-artifact model, but they are intentionally not part of
    the generic row identity. Including them would make unchanged content churn
    when a page file is renamed or chunks before it are inserted.
    """

    return generic_site_row_id(
        site_id=site_id,
        canonical_url=canonical_url,
        section_path=section_path,
        chunk_hash=chunk_hash,
        duplicate_ordinal=duplicate_ordinal,
    )


def build_plan_artifacts(
    *,
    indexing_plan: IndexingPlan,
    base_url: str,
    out_dir: Path,
    namespace: str | None = None,
    crawl_options: JsonObject | None = None,
    chunk_options: JsonObject | None = None,
    embedding_model: str = DEFAULT_PLAN_EMBEDDING_MODEL,
    diff: JsonObject | None = None,
    state_root: Path = Path(".buoy"),
) -> PlanArtifacts:
    """Build deterministic plan/manifest/chunk artifacts from local chunks.

    The artifact hash intentionally ignores volatile generated frontmatter such
    as ``crawl_timestamp`` by hashing parsed normalized page bodies and chunk
    records instead of raw Markdown file bytes.
    """

    normalized_base_url = validate_base_url(base_url)
    namespace_value = namespace or namespace_candidate(normalized_base_url)
    namespace_hint = namespace_candidate(normalized_base_url)
    site_id = site_id_for_url(normalized_base_url)
    pages = build_page_records(indexing_plan)
    page_hashes = {page.content_path: page.page_hash for page in pages}
    page_metadata = {page.content_path: page.source_metadata for page in pages}
    chunks = disambiguate_duplicate_chunk_row_ids(
        [
            build_chunk_record(
                chunk,
                site_id=site_id,
                page_hash=page_hashes.get(chunk.path, chunk.source_hash),
                source_metadata=page_metadata.get(chunk.path, {}),
            )
            for chunk in indexing_plan.chunks
        ]
    )
    manifest = ManifestDocument(
        schema_version=PLAN_SCHEMA_VERSION,
        site_id=site_id,
        base_url=normalized_base_url,
        namespace=namespace_value,
        namespace_candidate=namespace_hint,
        pages=pages,
        chunks=chunks,
    )
    crawl_options_value = normalize_json_object(crawl_options or {})
    chunk_options_value = normalize_json_object(chunk_options or {})
    diff_value = normalize_json_object(diff or default_diff(indexing_plan))
    artifact_payload = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "base_url": normalized_base_url,
        "site_id": site_id,
        "namespace": namespace_value,
        "namespace_candidate": namespace_hint,
        "crawl_options": crawl_options_value,
        "chunk_options": chunk_options_value,
        "embedding_model": embedding_model,
        "manifest": dataclass_to_json_object(manifest),
    }
    artifact_hash = stable_hash(artifact_payload)
    plan_id = f"plan_{artifact_hash[:16]}"
    plan = PlanDocument(
        schema_version=PLAN_SCHEMA_VERSION,
        command="plan",
        plan_id=plan_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        base_url=normalized_base_url,
        site_id=site_id,
        namespace=namespace_value,
        namespace_candidate=namespace_hint,
        state_backend="local",
        state_path=state_path_for_site(site_id, namespace_value, state_root=state_root),
        crawl_options=crawl_options_value,
        chunk_options=chunk_options_value,
        embedding_model=embedding_model,
        artifact_hash=artifact_hash,
        manifest_path=str(out_dir / "manifest.json"),
        chunks_path=str(out_dir / "chunks.jsonl"),
        pages_dir=str(out_dir / "pages"),
        diff=diff_value,
    )
    chunks_jsonl = "".join(
        stable_json_dumps(dataclass_to_json_object(chunk)) + "\n" for chunk in chunks
    )
    return PlanArtifacts(plan=plan, manifest=manifest, chunks_jsonl=chunks_jsonl)


def build_page_records(indexing_plan: IndexingPlan) -> list[PageManifestRecord]:
    """Return deterministic page records for every parsed Markdown file."""

    records: list[PageManifestRecord] = []
    for path in sorted(indexing_plan.corpus_dir.rglob("*.md")):
        if not path.is_file():
            continue
        document = parse_markdown_file(path, indexing_plan.corpus_dir)
        metadata = {
            key: value
            for key, value in sorted(document.metadata.items())
            if key not in VOLATILE_FRONTMATTER_KEYS
        }
        records.append(
            PageManifestRecord(
                canonical_url=document.url,
                title=document.title,
                content_path=document.relative_path,
                page_hash=document.source_hash,
                status=parse_optional_int(document.metadata.get("status")),
                content_type=document.metadata.get("content_type", ""),
                source_metadata=metadata,
            )
        )
    return records


def build_chunk_record(
    chunk: MarkdownChunk,
    *,
    site_id: str,
    page_hash: str,
    source_metadata: dict[str, str] | None = None,
) -> ChunkManifestRecord:
    chunk_hash = sha256_text(chunk.content)
    embedding_text_hash = sha256_text(chunk.embedding_text)
    row_id = generic_site_row_id(
        site_id=site_id,
        canonical_url=chunk.url,
        section_path=chunk.section_path,
        chunk_hash=chunk_hash,
    )
    return ChunkManifestRecord(
        row_id=row_id,
        row_id_candidate=row_id,
        site_id=site_id,
        duplicate_ordinal=0,
        canonical_url=chunk.url,
        page_content_path=chunk.path,
        page_hash=page_hash,
        chunk_hash=chunk_hash,
        embedding_text_hash=embedding_text_hash,
        title=chunk.title,
        section_path=chunk.section_path,
        chunk_index=chunk.chunk_index,
        content=chunk.content,
        content_preview=chunk.content[:240].replace("\n", " "),
        doc_kind=chunk.doc_kind,
        tags=list(chunk.tags),
        source_metadata=dict(source_metadata or {}),
    )


def disambiguate_duplicate_chunk_row_ids(chunks: list[ChunkManifestRecord]) -> list[ChunkManifestRecord]:
    """Return chunks with deterministic row IDs for duplicate identity groups.

    Unique chunks keep their ordinary row ID. Only repeated URL/section/content
    groups receive a non-zero duplicate ordinal on later occurrences, avoiding
    collision while preserving normal incremental stability.
    """

    counts: dict[str, int] = {}
    for chunk in chunks:
        counts[chunk.row_id] = counts.get(chunk.row_id, 0) + 1

    seen: dict[str, int] = {}
    disambiguated: list[ChunkManifestRecord] = []
    for chunk in chunks:
        base_row_id = chunk.row_id
        duplicate_ordinal = seen.get(base_row_id, 0)
        seen[base_row_id] = duplicate_ordinal + 1
        if counts[base_row_id] == 1:
            disambiguated.append(chunk)
            continue
        row_id = generic_site_row_id(
            site_id=chunk.site_id,
            canonical_url=chunk.canonical_url,
            section_path=chunk.section_path,
            chunk_hash=chunk.chunk_hash,
            duplicate_ordinal=duplicate_ordinal,
        )
        disambiguated.append(
            ChunkManifestRecord(
                row_id=row_id,
                row_id_candidate=row_id,
                site_id=chunk.site_id,
                duplicate_ordinal=duplicate_ordinal,
                canonical_url=chunk.canonical_url,
                page_content_path=chunk.page_content_path,
                page_hash=chunk.page_hash,
                chunk_hash=chunk.chunk_hash,
                embedding_text_hash=chunk.embedding_text_hash,
                title=chunk.title,
                section_path=chunk.section_path,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                content_preview=chunk.content_preview,
                doc_kind=chunk.doc_kind,
                tags=list(chunk.tags),
                source_metadata=dict(chunk.source_metadata),
            )
        )
    return disambiguated


def build_generic_site_row(
    chunk: ChunkManifestRecord | JsonObject,
    vector: Iterable[float],
    *,
    plan_id: str,
    applied_at: str,
) -> JsonObject:
    """Build a turbopuffer row for one generic-site manifest chunk.

    This is a local row-construction helper only. It does not embed text, read
    credentials, or call turbopuffer.
    """

    record = dataclass_to_json_object(chunk) if isinstance(chunk, ChunkManifestRecord) else normalize_json_object(chunk)
    source_metadata = normalize_json_object(record.get("source_metadata", {}))
    row = {
        "id": record["row_id"],
        "vector": list(vector),
        "content": record["content"],
        "title": record["title"],
        "url": record["canonical_url"],
        "path": record["page_content_path"],
        "section_path": record["section_path"],
        "chunk_index": record["chunk_index"],
        "doc_kind": record["doc_kind"],
        "tags": record["tags"],
        "source_hash": record["page_hash"],
        "site_id": record["site_id"],
        "canonical_url": record["canonical_url"],
        "page_hash": record["page_hash"],
        "chunk_hash": record["chunk_hash"],
        "embedding_text_hash": record["embedding_text_hash"],
        "plan_id": plan_id,
        "applied_at": applied_at,
    }
    if isinstance(source_metadata, dict):
        for field_name in SOURCE_METADATA_ROW_FIELDS:
            row[field_name] = str(source_metadata.get(field_name, ""))
    return row


def write_plan_artifacts(artifacts: PlanArtifacts, out_dir: Path) -> None:
    """Write ``plan.json``, ``manifest.json``, and ``chunks.jsonl``."""

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "plan.json").write_text(
        stable_json_dumps(artifacts.plan_dict(), indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "manifest.json").write_text(
        stable_json_dumps(artifacts.manifest_dict(), indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "chunks.jsonl").write_text(artifacts.chunks_jsonl, encoding="utf-8")


def default_diff(indexing_plan: IndexingPlan) -> JsonObject:
    """Return a first-apply placeholder diff for artifact-model consumers."""

    return {
        "first_apply": True,
        "pages_added": indexing_plan.files_discovered,
        "pages_changed": 0,
        "pages_unchanged": 0,
        "pages_removed": 0,
        "chunks_unchanged": 0,
        "chunks_to_embed": len(indexing_plan.chunks),
        "rows_to_upsert": len(indexing_plan.chunks),
        "stale_rows": 0,
    }


def dataclass_to_json_object(value: object) -> JsonObject:
    return normalize_json_object(asdict(value))


def normalize_json_object(value: Any) -> Any:
    """Normalize JSON-ish values so serialization is stable and supported."""

    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): normalize_json_object(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [normalize_json_object(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def stable_json_dumps(value: Any, *, indent: int | None = None) -> str:
    separators = None if indent is not None else (",", ":")
    return json.dumps(
        normalize_json_object(value),
        ensure_ascii=False,
        indent=indent,
        separators=separators,
        sort_keys=True,
    )


def stable_hash(value: Any) -> str:
    return sha256_text(stable_json_dumps(value))


def parse_optional_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def chunk_jsonl_records(chunks_jsonl: str) -> Iterable[JsonObject]:
    """Yield chunk dictionaries from generated JSONL content."""

    for line in chunks_jsonl.splitlines():
        if line.strip():
            yield json.loads(line)
