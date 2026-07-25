"""Local-only compact delta plan artifacts.

Planning builds a complete desired manifest in memory so existing deterministic
chunk/diff semantics remain authoritative, but persists only changed/new rows,
stale identities, and a small baseline-bound plan descriptor.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import stat
from typing import Any, Iterable, Mapping
from urllib.parse import parse_qsl, quote, unquote, urlsplit

import duckdb

from buoy_search.applied_state import (
    APPLIED_STATE_SCHEMA_VERSION,
    ROW_STATUS_ACTIVE,
    ROW_STATUS_RETAINED_STALE,
    AppliedState,
    AppliedStateRow,
)
from buoy_search.config import DEFAULT_EMBEDDING_PRECISION, EMBEDDING_PRECISIONS
from buoy_search.crawler import namespace_candidate, safe_slug, source_id_for_url, validate_base_url
from buoy_search.source_url import validate_http_url_authority
from buoy_search.chunker import (
    TURBOPUFFER_SCHEMA,
    IndexingPlan,
    MarkdownChunk,
    parse_markdown_file,
    sha256_text,
)

PLAN_SCHEMA_VERSION = 2
DELTA_SCHEMA_VERSION = 1
MAX_PLAN_JSON_BYTES = 131_072
DEFAULT_PLAN_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
VOLATILE_FRONTMATTER_KEYS = {"crawl_timestamp"}
_HEX_SHA256 = re.compile(r"[0-9a-f]{64}")
_PLAN_ID = re.compile(r"plan_[0-9a-f]{16}")
_MANAGED_JOB_ID = re.compile(r"planjob_[0-9a-f]{32}")
_ROW_ID = re.compile(r"ts_[0-9a-f]{32}")
_SAFE_SITE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
_SOURCE_KINDS = {
    "website",
    "github_repo",
    "local_file",
    "pdf",
    "duckdb_relation",
    "bigquery_relation",
    "snowflake_relation",
}
_DIFF_FIELDS = (
    "first_apply",
    "pages_added",
    "pages_changed",
    "pages_unchanged",
    "pages_removed",
    "chunks_unchanged",
    "chunks_to_embed",
    "rows_to_upsert",
    "stale_rows",
    "retained_stale_rows",
)

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
    "database_backend": {"type": "string"},
    "database_source_id": {"type": "string"},
    "database_relation": {"type": "string"},
    "database_document_id": {"type": "string"},
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
    "database_backend",
    "database_source_id",
    "database_relation",
    "database_document_id",
)

JsonObject = dict[str, Any]


@dataclass(frozen=True)
class PageManifestRecord:
    """One desired page retained only during planning."""

    canonical_url: str
    title: str
    content_path: str
    page_hash: str
    status: int | None
    content_type: str
    source_metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ChunkManifestRecord:
    """One complete desired chunk retained only during planning or delta apply."""

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
    """Complete desired source state used only for local diff construction."""

    schema_version: int
    site_id: str
    base_url: str
    namespace: str
    namespace_candidate: str
    pages: list[PageManifestRecord]
    chunks: list[ChunkManifestRecord]


@dataclass(frozen=True)
class PlanDocument:
    """Exact schema-v2 metadata persisted as ``plan.json``."""

    schema_version: int
    command: str
    plan_id: str
    created_at: str
    artifact_hash: str
    source: JsonObject
    site_id: str
    namespace: str
    namespace_candidate: str
    crawl_options: JsonObject
    chunk_options: JsonObject
    embedding_model: str
    embedding_precision: str
    applied_state: JsonObject
    delta: JsonObject
    diff: JsonObject
    originating_job_id: str | None = None


@dataclass(frozen=True)
class PlanArtifacts:
    """Compact persistent artifacts plus ephemeral desired state for callers."""

    plan: PlanDocument
    manifest: ManifestDocument = field(repr=False)
    diff: object = field(repr=False)
    upsert_rows: tuple[JsonObject, ...] = field(repr=False)
    stale_rows: tuple[JsonObject, ...] = field(repr=False)

    def plan_dict(self) -> JsonObject:
        payload = dataclass_to_json_object(self.plan)
        if payload.get("originating_job_id") is None:
            payload.pop("originating_job_id", None)
        return payload

    def manifest_dict(self) -> JsonObject:
        """Return ephemeral desired state for existing in-process diff tests only."""

        return dataclass_to_json_object(self.manifest)

    @property
    def chunks_jsonl(self) -> str:
        """Return ephemeral desired rows; schema-v2 writers never persist this."""

        return "".join(
            stable_json_dumps(dataclass_to_json_object(chunk)) + "\n"
            for chunk in self.manifest.chunks
        )


@dataclass(frozen=True)
class VerifiedDeltaPlan:
    """Fully verified compact plan content reusable by dependent consumers."""

    plan: JsonObject
    upsert_rows: tuple[JsonObject, ...]
    stale_rows: tuple[JsonObject, ...]


def site_id_for_url(base_url: str) -> str:
    return safe_slug(source_id_for_url(base_url), fallback="site")


def state_path_for_site(site_id: str, namespace: str, *, state_root: Path = Path(".buoy")) -> str:
    """Retained helper for applied-state callers; schema-v2 plans do not persist it."""

    return str(Path(state_root) / "state" / site_id / namespace / "state.duckdb")


def generic_site_row_id(
    *,
    site_id: str,
    canonical_url: str,
    section_path: str,
    chunk_hash: str,
    duplicate_ordinal: int = 0,
) -> str:
    parts = [site_id, canonical_url, section_path, chunk_hash]
    if duplicate_ordinal:
        parts.extend(["duplicate", str(duplicate_ordinal)])
    return f"ts_{sha256_text(chr(10).join(parts))[:32]}"


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
    del page_content_path, chunk_index
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
    embedding_precision: str = DEFAULT_EMBEDDING_PRECISION,
    diff: object | None = None,
    state_root: Path = Path(".buoy"),
    applied_state: AppliedState | None = None,
    state_present: bool = False,
    source_summary: Mapping[str, object] | None = None,
    originating_job_id: str | None = None,
) -> PlanArtifacts:
    """Build exact schema-v2 metadata and changed-only logical delta."""

    del out_dir, state_root
    if embedding_precision not in EMBEDDING_PRECISIONS:
        raise ValueError(f"embedding precision must be one of: {', '.join(EMBEDDING_PRECISIONS)}")
    if originating_job_id is not None and _MANAGED_JOB_ID.fullmatch(originating_job_id) is None:
        raise ValueError("originating_job_id must be a safe managed plan-job ID")
    parsed_source = urlsplit(base_url)
    source_scheme = parsed_source.scheme.casefold()
    if parsed_source.username is not None or parsed_source.password is not None:
        raise ValueError("plan source URI must not contain userinfo or credentials")
    if source_scheme in {"http", "https"}:
        validate_http_url_authority(base_url)
    allowed_source_schemes = (
        _PUBLIC_URI_SCHEMES
        if source_scheme in _PUBLIC_URI_SCHEMES
        else frozenset({source_scheme})
        if source_scheme in {"file", "pdf", "duckdb", "bigquery", "snowflake"}
        else frozenset()
    )
    _validate_private_string(
        base_url,
        label="plan source URI",
        allowed_uri_schemes=allowed_source_schemes,
    )
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
                embedding_precision=embedding_precision,
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
    if applied_state is None:
        applied_state = AppliedState(
            schema_version=APPLIED_STATE_SCHEMA_VERSION,
            site_id=site_id,
            namespace=namespace_value,
            base_url=normalized_base_url,
            updated_at="",
            last_plan_id="",
            last_apply_id="",
            rows=[],
            first_apply=True,
        )
        state_present = False
    if (
        applied_state.site_id != site_id
        or applied_state.namespace != namespace_value
        or applied_state.base_url != normalized_base_url
    ):
        raise ValueError("applied state identity does not match the planned source")
    if diff is None:
        from buoy_search.plan_diff import diff_manifest_against_state

        diff = diff_manifest_against_state(manifest, applied_state)
    if not hasattr(diff, "summary_dict"):
        raise ValueError("compact planning requires a complete incremental diff")
    diff_value = normalize_diff(diff.summary_dict())  # type: ignore[attr-defined]
    source = build_plan_source(normalized_base_url, pages, source_summary or {})
    baseline = applied_state_descriptor(applied_state, present=state_present)
    by_row_id = {chunk.row_id: chunk for chunk in chunks}
    upsert_rows = tuple(
        build_delta_upsert(by_row_id[record.row_id], action=record.action)
        for record in sorted(
            diff.rows_to_upsert_records,  # type: ignore[attr-defined]
            key=lambda record: (
                record.canonical_url,
                record.section_path,
                record.chunk_index,
                record.row_id,
            ),
        )
    )
    stale_records = [
        ("stale", record)
        for record in diff.stale_row_records  # type: ignore[attr-defined]
    ]
    stale_records.extend(
        ("retained_stale", record)
        for record in diff.retained_stale_row_records  # type: ignore[attr-defined]
    )
    stale_rows = tuple(
        build_delta_stale(category, record)
        for category, record in sorted(
            stale_records, key=lambda item: (item[1].canonical_url, item[1].row_id)
        )
    )
    logical_hash = delta_logical_hash(upsert_rows, stale_rows)
    delta = {
        "filename": "delta.duckdb",
        "schema_version": DELTA_SCHEMA_VERSION,
        "logical_hash": logical_hash,
        "upsert_count": len(upsert_rows),
        "stale_count": sum(row["category"] == "stale" for row in stale_rows),
        "retained_stale_count": sum(
            row["category"] == "retained_stale" for row in stale_rows
        ),
    }
    identity = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "source": source,
        "site_id": site_id,
        "namespace": namespace_value,
        "namespace_candidate": namespace_hint,
        "crawl_options": normalize_json_object(crawl_options or {}),
        "chunk_options": normalize_json_object(chunk_options or {}),
        "embedding_model": embedding_model,
        "embedding_precision": embedding_precision,
        "applied_state": baseline,
        "delta": delta,
        "diff": diff_value,
    }
    artifact_hash = stable_hash(identity)
    plan = PlanDocument(
        schema_version=PLAN_SCHEMA_VERSION,
        command="plan",
        plan_id=f"plan_{artifact_hash[:16]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        artifact_hash=artifact_hash,
        source=source,
        site_id=site_id,
        namespace=namespace_value,
        namespace_candidate=namespace_hint,
        crawl_options=identity["crawl_options"],
        chunk_options=identity["chunk_options"],
        embedding_model=embedding_model,
        embedding_precision=embedding_precision,
        applied_state=baseline,
        delta=delta,
        diff=diff_value,
        originating_job_id=originating_job_id,
    )
    payload = stable_json_dumps(
        PlanArtifacts(plan, manifest, diff, upsert_rows, stale_rows).plan_dict(), indent=2
    ) + "\n"
    if len(payload.encode("utf-8")) > MAX_PLAN_JSON_BYTES:
        raise ValueError(f"plan.json must contain at most {MAX_PLAN_JSON_BYTES} UTF-8 bytes")
    return PlanArtifacts(plan, manifest, diff, upsert_rows, stale_rows)


def build_page_records(indexing_plan: IndexingPlan) -> list[PageManifestRecord]:
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
    embedding_precision: str = DEFAULT_EMBEDDING_PRECISION,
) -> ChunkManifestRecord:
    chunk_hash = sha256_text(chunk.content)
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
        embedding_text_hash=embedding_hash(chunk.embedding_text, embedding_precision),
        title=chunk.title,
        section_path=chunk.section_path,
        chunk_index=chunk.chunk_index,
        content=chunk.content,
        content_preview=chunk.content[:240].replace("\n", " "),
        doc_kind=chunk.doc_kind,
        tags=sorted(set(chunk.tags)),
        source_metadata=dict(source_metadata or {}),
    )


def embedding_text_for_chunk(chunk: ChunkManifestRecord | Mapping[str, object]) -> str:
    title = chunk.title if isinstance(chunk, ChunkManifestRecord) else str(chunk.get("title", ""))
    section = (
        chunk.section_path
        if isinstance(chunk, ChunkManifestRecord)
        else str(chunk.get("section_path", ""))
    )
    content = chunk.content if isinstance(chunk, ChunkManifestRecord) else str(chunk.get("content", ""))
    context = [
        *( [f"Title: {title}"] if title else [] ),
        *( [f"Section: {section}"] if section else [] ),
        content,
    ]
    return "\n\n".join(part for part in context if part.strip())


def embedding_hash(text: str, precision: str) -> str:
    if precision == "float32":
        return sha256_text(text)
    return sha256_text(f"embedding_precision={precision}\n{text}")


def disambiguate_duplicate_chunk_row_ids(chunks: list[ChunkManifestRecord]) -> list[ChunkManifestRecord]:
    counts: dict[str, int] = {}
    for chunk in chunks:
        counts[chunk.row_id] = counts.get(chunk.row_id, 0) + 1
    seen: dict[str, int] = {}
    result: list[ChunkManifestRecord] = []
    for chunk in chunks:
        base = chunk.row_id
        ordinal = seen.get(base, 0)
        seen[base] = ordinal + 1
        if counts[base] == 1:
            result.append(chunk)
            continue
        row_id = generic_site_row_id(
            site_id=chunk.site_id,
            canonical_url=chunk.canonical_url,
            section_path=chunk.section_path,
            chunk_hash=chunk.chunk_hash,
            duplicate_ordinal=ordinal,
        )
        result.append(
            ChunkManifestRecord(
                **{
                    **asdict(chunk),
                    "row_id": row_id,
                    "row_id_candidate": row_id,
                    "duplicate_ordinal": ordinal,
                }
            )
        )
    return result


def build_plan_source(
    base_url: str,
    pages: list[PageManifestRecord],
    summary: Mapping[str, object],
) -> JsonObject:
    metadata = [page.source_metadata for page in pages]
    raw_kind = str(summary.get("source_kind") or consistent_metadata(metadata, "source_kind") or "website")
    if raw_kind not in _SOURCE_KINDS:
        raise ValueError(f"unsupported plan source kind {raw_kind!r}")
    if raw_kind == "website":
        hostname = (urlsplit(base_url).hostname or "").lower()
        if not hostname:
            raise ValueError("website source requires a hostname")
        return {"kind": raw_kind, "uri": base_url, "title": hostname, "attributes": {}}
    if raw_kind == "github_repo":
        full_name = required_summary(summary, metadata, "repo_full_name")
        owner = str(summary.get("repo_owner") or full_name.split("/", 1)[0])
        name = str(summary.get("repo_name") or full_name.split("/", 1)[-1])
        attributes = {
            "repo_full_name": full_name,
            "repo_owner": owner,
            "repo_name": name,
            "repo_ref": required_summary(summary, metadata, "repo_ref"),
            "commit_sha": required_summary(summary, metadata, "commit_sha"),
            "repo_subdir": str(summary["repo_subdir"]) if summary.get("repo_subdir") else None,
        }
        return {"kind": raw_kind, "uri": base_url, "title": full_name, "attributes": attributes}
    if raw_kind in {"local_file", "pdf"}:
        prefix = "pdf" if raw_kind == "pdf" else "file"
        filename = required_summary(summary, metadata, f"{prefix}_filename")
        attributes: JsonObject = {
            "filename": filename,
            "sha256": required_summary(summary, metadata, f"{prefix}_sha256"),
            "source_id": required_summary(summary, metadata, f"{prefix}_source_id"),
        }
        if raw_kind == "local_file":
            attributes["extension"] = required_summary(summary, metadata, "file_extension")
        return {"kind": raw_kind, "uri": base_url, "title": filename, "attributes": attributes}
    backend = required_summary(summary, metadata, "database_backend")
    source_id = required_summary(summary, metadata, "database_source_id")
    relation = required_summary(summary, metadata, "database_relation")
    if raw_kind != f"{backend}_relation":
        raise ValueError("database source kind and backend disagree")
    return {
        "kind": raw_kind,
        "uri": base_url,
        "title": f"{source_id} ({relation})",
        "attributes": {
            "database_backend": backend,
            "database_source_id": source_id,
            "database_relation": relation,
        },
    }


def consistent_metadata(metadata: Iterable[Mapping[str, str]], key: str) -> str | None:
    values = {str(item[key]) for item in metadata if item.get(key)}
    if len(values) > 1:
        raise ValueError(f"source metadata has contradictory {key} values")
    return next(iter(values), None)


def required_summary(
    summary: Mapping[str, object], metadata: list[Mapping[str, str]], key: str
) -> str:
    value = summary.get(key) or consistent_metadata(metadata, key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"plan source requires non-empty {key}")
    return value


def applied_state_descriptor(state: AppliedState, *, present: bool) -> JsonObject:
    projection = {
        "present": present,
        "schema_version": state.schema_version,
        "site_id": state.site_id,
        "namespace": state.namespace,
        "base_url": state.base_url,
        "updated_at": state.updated_at,
        "last_plan_id": state.last_plan_id,
        "last_apply_id": state.last_apply_id,
        "rows": [
            {
                "row_id": row.row_id,
                "canonical_url": row.canonical_url,
                "page_hash": row.page_hash,
                "chunk_hash": row.chunk_hash,
                "embedding_text_hash": row.embedding_text_hash,
                "plan_id": row.plan_id,
                "applied_at": row.applied_at,
                "status": row.status,
            }
            for row in sorted(state.rows, key=lambda candidate: candidate.row_id)
        ],
    }
    return {
        "present": present,
        "schema_version": state.schema_version,
        "hash": stable_hash(projection),
    }


def build_delta_upsert(chunk: ChunkManifestRecord, *, action: str) -> JsonObject:
    return {
        "action": action,
        "row_id": chunk.row_id,
        "row_id_candidate": chunk.row_id_candidate,
        "site_id": chunk.site_id,
        "duplicate_ordinal": chunk.duplicate_ordinal,
        "canonical_url": chunk.canonical_url,
        "source_path": chunk.page_content_path,
        "page_hash": chunk.page_hash,
        "chunk_hash": chunk.chunk_hash,
        "embedding_text_hash": chunk.embedding_text_hash,
        "title": chunk.title,
        "section_path": chunk.section_path,
        "chunk_index": chunk.chunk_index,
        "content": chunk.content,
        "doc_kind": chunk.doc_kind,
        "tags_json": list(chunk.tags),
        "source_metadata_json": dict(chunk.source_metadata),
    }


def build_delta_stale(category: str, record: object) -> JsonObject:
    return {
        "category": category,
        "row_id": record.row_id,  # type: ignore[attr-defined]
        "canonical_url": record.canonical_url,  # type: ignore[attr-defined]
        "page_hash": record.page_hash,  # type: ignore[attr-defined]
        "chunk_hash": record.chunk_hash,  # type: ignore[attr-defined]
        "embedding_text_hash": record.embedding_text_hash,  # type: ignore[attr-defined]
        "prior_plan_id": record.plan_id,  # type: ignore[attr-defined]
        "prior_applied_at": record.applied_at,  # type: ignore[attr-defined]
        "prior_status": record.status,  # type: ignore[attr-defined]
        "reason": (
            "not_in_desired_source"
            if category == "stale"
            else "retained_stale_not_in_desired_source"
        ),
    }


def delta_logical_hash(
    upsert_rows: Iterable[Mapping[str, object]], stale_rows: Iterable[Mapping[str, object]]
) -> str:
    return stable_hash(
        {
            "schema_version": DELTA_SCHEMA_VERSION,
            "upsert_rows": [normalize_json_object(dict(row)) for row in upsert_rows],
            "stale_rows": [normalize_json_object(dict(row)) for row in stale_rows],
        }
    )


def normalize_diff(value: Mapping[str, object]) -> JsonObject:
    if set(value) != set(_DIFF_FIELDS):
        raise ValueError("diff summary fields do not match schema v2")
    result: JsonObject = {}
    for key in _DIFF_FIELDS:
        item = value[key]
        if key == "first_apply":
            if type(item) is not bool:
                raise ValueError("diff first_apply must be a boolean")
        elif type(item) is not int or item < 0:
            raise ValueError(f"diff {key} must be a non-negative integer")
        result[key] = item
    return result


def write_plan_artifacts(artifacts: PlanArtifacts, out_dir: Path) -> None:
    """Atomically write only schema-v2 ``plan.json`` and ``delta.duckdb``."""

    plan = artifacts.plan_dict()
    validate_plan_document(plan)
    _validate_diff_counts(plan["diff"], plan["delta"])
    if artifacts.upsert_rows != tuple(sorted(artifacts.upsert_rows, key=_upsert_sort_key)):
        raise ValueError("delta upsert rows are not in canonical sort order")
    if artifacts.stale_rows != tuple(sorted(artifacts.stale_rows, key=_stale_sort_key)):
        raise ValueError("delta stale rows are not in canonical sort order")
    if delta_logical_hash(artifacts.upsert_rows, artifacts.stale_rows) != plan["delta"]["logical_hash"]:
        raise ValueError("delta logical hash does not match before persistence")
    for row in artifacts.upsert_rows:
        _validate_upsert_row(plan, row)
    for row in artifacts.stale_rows:
        _validate_stale_row(plan, row)
    if stable_hash(artifact_identity(plan)) != plan["artifact_hash"]:
        raise ValueError("plan artifact hash does not match before persistence")

    out_dir.mkdir(parents=True, exist_ok=True)
    delta_path = out_dir / "delta.duckdb"
    delta_tmp = out_dir / ".delta.duckdb.tmp"
    plan_path = out_dir / "plan.json"
    plan_tmp = out_dir / ".plan.json.tmp"
    for path in (delta_tmp, plan_tmp):
        if path.exists() or path.is_symlink():
            path.unlink()
    try:
        with duckdb.connect(str(delta_tmp)) as connection:
            _create_delta_schema(connection)
            plan = artifacts.plan_dict()
            source = plan["source"]
            delta = plan["delta"]
            connection.execute(
                """
                INSERT INTO delta_metadata VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    DELTA_SCHEMA_VERSION,
                    plan["plan_id"],
                    plan["site_id"],
                    plan["namespace"],
                    source["kind"],
                    source["uri"],
                    plan["applied_state"]["hash"],
                    delta["logical_hash"],
                    delta["upsert_count"],
                    delta["stale_count"],
                    delta["retained_stale_count"],
                ],
            )
            if artifacts.upsert_rows:
                connection.executemany(
                    """
                    INSERT INTO upsert_rows VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            ordinal,
                            row["action"],
                            row["row_id"],
                            row["row_id_candidate"],
                            row["site_id"],
                            row["duplicate_ordinal"],
                            row["canonical_url"],
                            row["source_path"],
                            row["page_hash"],
                            row["chunk_hash"],
                            row["embedding_text_hash"],
                            row["title"],
                            row["section_path"],
                            row["chunk_index"],
                            row["content"],
                            row["doc_kind"],
                            stable_json_dumps(row["tags_json"]),
                            stable_json_dumps(row["source_metadata_json"]),
                        )
                        for ordinal, row in enumerate(artifacts.upsert_rows)
                    ],
                )
            if artifacts.stale_rows:
                connection.executemany(
                    """
                    INSERT INTO stale_rows VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            ordinal,
                            row["category"],
                            row["row_id"],
                            row["canonical_url"],
                            row["page_hash"],
                            row["chunk_hash"],
                            row["embedding_text_hash"],
                            row["prior_plan_id"],
                            row["prior_applied_at"],
                            row["prior_status"],
                            row["reason"],
                        )
                        for ordinal, row in enumerate(artifacts.stale_rows)
                    ],
                )
            connection.execute("CHECKPOINT")
        os.replace(delta_tmp, delta_path)
        payload = stable_json_dumps(artifacts.plan_dict(), indent=2) + "\n"
        if len(payload.encode("utf-8")) > MAX_PLAN_JSON_BYTES:
            raise ValueError(f"plan.json must contain at most {MAX_PLAN_JSON_BYTES} UTF-8 bytes")
        plan_tmp.write_text(payload, encoding="utf-8")
        os.replace(plan_tmp, plan_path)
    finally:
        for path in (delta_tmp, plan_tmp):
            if path.exists() or path.is_symlink():
                path.unlink()


def _create_delta_schema(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute(
        """
        CREATE TABLE delta_metadata (
          schema_version INTEGER NOT NULL CHECK (schema_version = 1),
          plan_id VARCHAR PRIMARY KEY,
          site_id VARCHAR NOT NULL,
          namespace VARCHAR NOT NULL,
          source_kind VARCHAR NOT NULL,
          source_uri VARCHAR NOT NULL,
          applied_state_hash VARCHAR NOT NULL,
          logical_hash VARCHAR NOT NULL,
          upsert_count UBIGINT NOT NULL,
          stale_count UBIGINT NOT NULL,
          retained_stale_count UBIGINT NOT NULL
        );
        CREATE TABLE upsert_rows (
          ordinal UBIGINT PRIMARY KEY,
          action VARCHAR NOT NULL CHECK (action IN ('new','changed','reactivate_retained_stale')),
          row_id VARCHAR NOT NULL UNIQUE,
          row_id_candidate VARCHAR NOT NULL,
          site_id VARCHAR NOT NULL,
          duplicate_ordinal UINTEGER NOT NULL,
          canonical_url VARCHAR NOT NULL,
          source_path VARCHAR NOT NULL,
          page_hash VARCHAR NOT NULL,
          chunk_hash VARCHAR NOT NULL,
          embedding_text_hash VARCHAR NOT NULL,
          title VARCHAR NOT NULL,
          section_path VARCHAR NOT NULL,
          chunk_index UINTEGER NOT NULL,
          content VARCHAR NOT NULL,
          doc_kind VARCHAR NOT NULL,
          tags_json VARCHAR NOT NULL,
          source_metadata_json VARCHAR NOT NULL
        );
        CREATE TABLE stale_rows (
          ordinal UBIGINT PRIMARY KEY,
          category VARCHAR NOT NULL CHECK (category IN ('stale','retained_stale')),
          row_id VARCHAR NOT NULL UNIQUE,
          canonical_url VARCHAR NOT NULL,
          page_hash VARCHAR NOT NULL,
          chunk_hash VARCHAR NOT NULL,
          embedding_text_hash VARCHAR NOT NULL,
          prior_plan_id VARCHAR NOT NULL,
          prior_applied_at VARCHAR NOT NULL,
          prior_status VARCHAR NOT NULL CHECK (prior_status IN ('active','retained_stale')),
          reason VARCHAR NOT NULL CHECK (reason IN ('not_in_desired_source','retained_stale_not_in_desired_source'))
        )
        """
    )


def verify_plan_artifacts(plan_path: Path) -> VerifiedDeltaPlan:
    """Fully verify one schema-v2 plan and its logical delta."""

    if plan_path.is_symlink() or not plan_path.is_file():
        raise ValueError("plan.json must be a regular file")
    opened = plan_path.stat()
    if not stat.S_ISREG(opened.st_mode) or opened.st_size > MAX_PLAN_JSON_BYTES:
        raise ValueError("plan.json is missing, unsafe, or exceeds the size limit")
    try:
        plan = json.loads(
            plan_path.read_text(encoding="utf-8"),
            parse_constant=_reject_json_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("plan.json is unreadable") from exc
    validate_plan_document(plan)
    delta_path = plan_path.with_name("delta.duckdb")
    if delta_path.is_symlink() or not delta_path.is_file():
        raise ValueError("delta.duckdb must be a regular file")
    try:
        with duckdb.connect(str(delta_path), read_only=True) as connection:
            _validate_delta_schema(connection)
            metadata = connection.execute("SELECT * FROM delta_metadata").fetchall()
            if len(metadata) != 1:
                raise ValueError("delta metadata must contain exactly one row")
            upsert_rows = tuple(_read_upserts(connection))
            stale_rows = tuple(_read_stale(connection))
    except duckdb.Error as exc:
        raise ValueError("delta.duckdb is unreadable or invalid") from exc
    delta = plan["delta"]
    source = plan["source"]
    expected_metadata = (
        DELTA_SCHEMA_VERSION,
        plan["plan_id"],
        plan["site_id"],
        plan["namespace"],
        source["kind"],
        source["uri"],
        plan["applied_state"]["hash"],
        delta["logical_hash"],
        delta["upsert_count"],
        delta["stale_count"],
        delta["retained_stale_count"],
    )
    if tuple(metadata[0]) != expected_metadata:
        raise ValueError("delta metadata does not match plan.json")
    if len(upsert_rows) != delta["upsert_count"]:
        raise ValueError("delta upsert count does not match")
    stale_count = sum(row["category"] == "stale" for row in stale_rows)
    retained_count = sum(row["category"] == "retained_stale" for row in stale_rows)
    if stale_count != delta["stale_count"] or retained_count != delta["retained_stale_count"]:
        raise ValueError("delta stale counts do not match")
    _validate_diff_counts(plan["diff"], delta)
    if not plan["applied_state"]["present"] and not plan["diff"]["first_apply"]:
        raise ValueError("absent applied state requires first-apply diff semantics")
    if tuple(upsert_rows) != tuple(sorted(upsert_rows, key=_upsert_sort_key)):
        raise ValueError("delta upsert rows are not in canonical sort order")
    if tuple(stale_rows) != tuple(sorted(stale_rows, key=_stale_sort_key)):
        raise ValueError("delta stale rows are not in canonical sort order")
    if delta_logical_hash(upsert_rows, stale_rows) != delta["logical_hash"]:
        raise ValueError("delta logical hash does not match")
    upsert_ids = {str(row["row_id"]) for row in upsert_rows}
    stale_ids = {str(row["row_id"]) for row in stale_rows}
    if upsert_ids & stale_ids:
        raise ValueError("delta row identity cannot be both upsert and stale")
    for row in upsert_rows:
        _validate_upsert_row(plan, row)
    for row in stale_rows:
        _validate_stale_row(plan, row)
    identity = artifact_identity(plan)
    artifact_hash = stable_hash(identity)
    if artifact_hash != plan["artifact_hash"]:
        raise ValueError("plan artifact hash does not match")
    if plan["plan_id"] != f"plan_{artifact_hash[:16]}":
        raise ValueError("plan ID does not match artifact hash")
    return VerifiedDeltaPlan(plan, upsert_rows, stale_rows)


def _sensitive_key(key: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "_", key.casefold()).strip("_")
    if normalized == "ranking_profile":
        return False
    secret_markers = (
        "password", "passwd", "credential", "secret", "authorization", "cookie",
        "api_key", "apikey", "private_key", "access_key", "session_key",
        "connection_string", "connection_uri", "connection_url", "connection_setting",
    )
    provider_settings = {
        "profile", "source_profile", "provider_profile", "connection", "source_connection",
        "provider_connection", "dsn", "account", "account_identifier",
        "warehouse", "role", "username", "user", "host", "port", "billing_project",
        "query_project", "connection_database", "connection_schema",
    }
    safe_token_fields = {"target_tokens", "max_tokens", "tokenizer_model", "tokenizer_revision"}
    token_bearing = "token" in normalized.split("_") and normalized not in safe_token_fields
    return (
        any(marker in normalized for marker in secret_markers)
        or normalized in provider_settings
        or token_bearing
    )


_MAX_PRIVACY_DEPTH = 16
_MAX_PRIVACY_NODES = 10_000
_MAX_PRIVACY_STRING_BYTES = 65_536
_MAX_URL_DECODE_ROUNDS = 5
_EMBEDDED_ABSOLUTE_URI = re.compile(
    r"(?i)(?<![A-Za-z0-9+.-])([a-z][a-z0-9+.-]{1,31}://[^\s<>\"'\\]+)"
)
_PUBLIC_URI_SCHEMES = frozenset({"http", "https"})


def _validate_private_free_json(
    value: object,
    *,
    label: str,
    allowed_uri_schemes: frozenset[str] = _PUBLIC_URI_SCHEMES,
    _depth: int = 0,
    _budget: list[int] | None = None,
    _allow_source_relative_path: bool = False,
) -> None:
    """Recursively reject private paths, credentials, and provider connection URIs."""

    if _budget is None:
        _budget = [0]
    if _depth > _MAX_PRIVACY_DEPTH:
        raise ValueError(f"plan {label} exceeds the privacy-validation nesting limit")
    _budget[0] += 1
    if _budget[0] > _MAX_PRIVACY_NODES:
        raise ValueError(f"plan {label} exceeds the privacy-validation value limit")
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or _sensitive_key(key):
                raise ValueError(f"plan {label} contains a credential-bearing or provider-connection field")
            _validate_private_free_json(
                item,
                label=label,
                allowed_uri_schemes=allowed_uri_schemes,
                _depth=_depth + 1,
                _budget=_budget,
                _allow_source_relative_path=key in {"include_paths", "exclude_paths"},
            )
    elif isinstance(value, list):
        for item in value:
            _validate_private_free_json(
                item,
                label=label,
                allowed_uri_schemes=allowed_uri_schemes,
                _depth=_depth + 1,
                _budget=_budget,
                _allow_source_relative_path=_allow_source_relative_path,
            )
    elif isinstance(value, str):
        _validate_private_string(
            value,
            label=f"plan {label}",
            allowed_uri_schemes=allowed_uri_schemes,
            depth=_depth,
            allow_source_relative_path=_allow_source_relative_path,
        )
    elif value is None or type(value) in {bool, int, float}:
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f"plan {label} contains a non-finite number")
    else:
        raise ValueError(f"plan {label} contains an unsupported value")


def validate_plan_document(plan: object) -> None:
    if not isinstance(plan, dict):
        raise ValueError("plan.json must be an object")
    required = {
        "schema_version", "command", "plan_id", "created_at", "artifact_hash",
        "source", "site_id", "namespace", "namespace_candidate", "crawl_options",
        "chunk_options", "embedding_model", "embedding_precision", "applied_state",
        "delta", "diff",
    }
    allowed = required | {"originating_job_id"}
    if set(plan) != required and set(plan) != allowed:
        raise ValueError("plan.json fields do not match schema v2")
    if type(plan["schema_version"]) is not int or plan["schema_version"] != PLAN_SCHEMA_VERSION:
        raise ValueError("unsupported plan schema version")
    if plan["command"] != "plan" or not _PLAN_ID.fullmatch(str(plan["plan_id"])):
        raise ValueError("invalid plan command or ID")
    if not _HEX_SHA256.fullmatch(str(plan["artifact_hash"])):
        raise ValueError("invalid artifact hash")
    for key in ("site_id", "namespace", "namespace_candidate", "created_at", "embedding_model"):
        if not isinstance(plan[key], str) or not plan[key] or plan[key] != plan[key].strip():
            raise ValueError(f"plan {key} must be a non-empty trimmed string")
    if _SAFE_SITE_ID.fullmatch(plan["site_id"]) is None:
        raise ValueError("plan site_id is unsafe")
    if any(re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", plan[key]) is None for key in ("namespace", "namespace_candidate")):
        raise ValueError("plan namespace identity is unsafe")
    try:
        created = datetime.fromisoformat(plan["created_at"])
    except ValueError as exc:
        raise ValueError("plan created_at must be an ISO-8601 timestamp") from exc
    if created.tzinfo is None or created.utcoffset() != timezone.utc.utcoffset(created):
        raise ValueError("plan created_at must be a UTC timestamp")
    if plan["embedding_precision"] not in EMBEDDING_PRECISIONS:
        raise ValueError("invalid embedding precision")
    if not isinstance(plan["crawl_options"], dict) or not isinstance(plan["chunk_options"], dict):
        raise ValueError("plan options must be objects")
    _validate_private_free_json(plan["crawl_options"], label="crawl options")
    _validate_private_free_json(plan["chunk_options"], label="chunk options")
    validate_plan_source(plan["source"])
    source = plan["source"]
    expected_site_id = site_id_for_url(str(source["uri"]))
    expected_namespace_candidate = namespace_candidate(str(source["uri"]))
    if plan["site_id"] != expected_site_id:
        raise ValueError("plan site_id does not match source identity")
    if plan["namespace_candidate"] != expected_namespace_candidate:
        raise ValueError("plan namespace_candidate does not match source identity")
    baseline = plan["applied_state"]
    if not isinstance(baseline, dict) or set(baseline) != {"present", "schema_version", "hash"}:
        raise ValueError("invalid applied-state descriptor")
    if (
        type(baseline["present"]) is not bool
        or type(baseline["schema_version"]) is not int
        or baseline["schema_version"] != APPLIED_STATE_SCHEMA_VERSION
    ):
        raise ValueError("invalid applied-state descriptor types or schema version")
    if not _HEX_SHA256.fullmatch(str(baseline["hash"])):
        raise ValueError("invalid applied-state hash")
    delta = plan["delta"]
    if not isinstance(delta, dict) or set(delta) != {
        "filename", "schema_version", "logical_hash", "upsert_count", "stale_count",
        "retained_stale_count",
    }:
        raise ValueError("invalid delta descriptor")
    if (
        delta["filename"] != "delta.duckdb"
        or type(delta["schema_version"]) is not int
        or delta["schema_version"] != DELTA_SCHEMA_VERSION
    ):
        raise ValueError("invalid delta descriptor identity")
    if not _HEX_SHA256.fullmatch(str(delta["logical_hash"])):
        raise ValueError("invalid delta logical hash")
    for key in ("upsert_count", "stale_count", "retained_stale_count"):
        if type(delta[key]) is not int or delta[key] < 0:
            raise ValueError("invalid delta count")
    normalize_diff(plan["diff"])
    if "originating_job_id" in plan and _MANAGED_JOB_ID.fullmatch(str(plan["originating_job_id"])) is None:
        raise ValueError("invalid originating job ID")


_SECRET_URI_COMPONENTS = {
    "token", "access_token", "api_key", "apikey", "key", "secret", "password",
    "passwd", "credential", "credentials", "authorization", "cookie", "profile",
    "connection", "connection_string", "connection_uri", "dsn", "account",
    "snowflake_account", "private",
}
def _normalized_component_tokens(value: str) -> set[str]:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")
    tokens = set(filter(None, normalized.split("_")))
    if normalized:
        tokens.add(normalized)
    return tokens


def _contains_secret_uri_component(value: str) -> bool:
    tokens = _normalized_component_tokens(value)
    if tokens & _SECRET_URI_COMPONENTS:
        return True
    return any(marker in tokens for marker in {"access_token", "api_key", "client_secret"})


def _decoded_variants(value: str) -> Iterable[str]:
    current = value
    yield current
    for _ in range(_MAX_URL_DECODE_ROUNDS):
        decoded = unquote(current)
        if decoded == current:
            return
        current = decoded
        yield current
    if unquote(current) != current:
        raise ValueError("plan privacy validation exceeded the URL decode limit")


def _is_absolute_filesystem_path(value: str) -> bool:
    return PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute()


def _trim_embedded_uri(value: str) -> str:
    return value.rstrip(".,;:!?)]}")


def _validate_absolute_uri(
    value: str,
    *,
    label: str,
    allowed_uri_schemes: frozenset[str],
    depth: int,
) -> None:
    parsed = urlsplit(value)
    scheme = parsed.scheme.casefold()
    if not scheme:
        return
    if parsed.username is not None or parsed.password is not None:
        raise ValueError(f"{label} contains a credential-bearing URI")
    if scheme not in allowed_uri_schemes:
        raise ValueError(f"{label} contains an unapproved provider connection URI")
    if parsed.query:
        for name, item in parse_qsl(parsed.query, keep_blank_values=True):
            if _contains_secret_uri_component(name) or _contains_secret_uri_component(item):
                raise ValueError(f"{label} contains a secret-bearing URI query")
            _validate_private_string(
                item,
                label=label,
                allowed_uri_schemes=_PUBLIC_URI_SCHEMES,
                depth=depth + 1,
            )
    if parsed.fragment:
        fragment_items = parse_qsl(parsed.fragment, keep_blank_values=True)
        values = [parsed.fragment, *(part for pair in fragment_items for part in pair)]
        if any(_contains_secret_uri_component(item) for item in values):
            raise ValueError(f"{label} contains a secret-bearing URI fragment")
        for item in values:
            _validate_private_string(
                item,
                label=label,
                allowed_uri_schemes=_PUBLIC_URI_SCHEMES,
                depth=depth + 1,
            )


def _validate_private_string(
    value: str,
    *,
    label: str,
    allowed_uri_schemes: frozenset[str] = _PUBLIC_URI_SCHEMES,
    depth: int = 0,
    allow_source_relative_path: bool = False,
) -> None:
    if depth > _MAX_PRIVACY_DEPTH:
        raise ValueError(f"{label} exceeds the privacy-validation nesting limit")
    if len(value.encode("utf-8")) > _MAX_PRIVACY_STRING_BYTES:
        raise ValueError(f"{label} exceeds the privacy-validation string limit")
    for decoded in _decoded_variants(value):
        if "\x00" in decoded or (
            _is_absolute_filesystem_path(decoded)
            and not (allow_source_relative_path and PurePosixPath(decoded).is_absolute())
        ):
            raise ValueError(f"{label} contains a private absolute path")
        candidates: list[str] = []
        parsed = urlsplit(decoded)
        if parsed.scheme and "://" in decoded:
            candidates.append(decoded)
        candidates.extend(
            _trim_embedded_uri(match.group(1))
            for match in _EMBEDDED_ABSOLUTE_URI.finditer(decoded)
        )
        seen: set[str] = set()
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            _validate_absolute_uri(
                candidate,
                label=label,
                allowed_uri_schemes=allowed_uri_schemes,
                depth=depth,
            )


def _validate_no_credential_uri(value: str, *, label: str) -> None:
    _validate_private_string(value, label=label)


def _validate_safe_filename(value: str) -> None:
    if (
        not value
        or value != value.strip()
        or value in {".", ".."}
        or "/" in value
        or "\\" in value
        or "\x00" in value
        or _is_absolute_filesystem_path(value)
    ):
        raise ValueError("document plan source filename must be a safe basename")


def _source_allowed_uri_schemes(kind: str) -> frozenset[str]:
    return frozenset({
        "website": {"http", "https"},
        "github_repo": {"https"},
        "local_file": {"file"},
        "pdf": {"pdf"},
        "duckdb_relation": {"duckdb"},
        "bigquery_relation": {"bigquery"},
        "snowflake_relation": {"snowflake"},
    }[kind])


def validate_plan_source(source: object) -> None:
    if not isinstance(source, dict) or set(source) != {"kind", "uri", "title", "attributes"}:
        raise ValueError("invalid plan source object")
    kind = source["kind"]
    if kind not in _SOURCE_KINDS or not isinstance(source["uri"], str) or not source["uri"]:
        raise ValueError("invalid plan source identity")
    if (
        not isinstance(source["title"], str)
        or not source["title"]
        or source["title"] != source["title"].strip()
        or "\x00" in source["title"]
        or not isinstance(source["attributes"], dict)
    ):
        raise ValueError("invalid plan source presentation")
    attrs = source["attributes"]
    allowed_source_schemes = _source_allowed_uri_schemes(str(kind))
    parsed_source = urlsplit(str(source["uri"]))
    if parsed_source.username is not None or parsed_source.password is not None:
        raise ValueError("plan source URI must not contain userinfo or credentials")
    _validate_private_string(
        str(source["uri"]),
        label="plan source URI",
        allowed_uri_schemes=allowed_source_schemes,
    )
    _validate_private_string(str(source["title"]), label="plan source title")
    expected = {
        "website": set(),
        "github_repo": {"repo_full_name", "repo_owner", "repo_name", "repo_ref", "commit_sha", "repo_subdir"},
        "local_file": {"filename", "extension", "sha256", "source_id"},
        "pdf": {"filename", "sha256", "source_id"},
        "duckdb_relation": {"database_backend", "database_source_id", "database_relation"},
        "bigquery_relation": {"database_backend", "database_source_id", "database_relation"},
        "snowflake_relation": {"database_backend", "database_source_id", "database_relation"},
    }[kind]
    if set(attrs) != expected:
        raise ValueError("plan source attributes do not match source kind")
    for key, value in attrs.items():
        if kind == "github_repo" and key == "repo_subdir" and value is None:
            continue
        if not isinstance(value, str) or not value:
            raise ValueError("plan source attributes must be non-empty strings")
        _validate_no_credential_uri(value, label="plan source attributes")
    _validate_private_free_json(attrs, label="source attributes")
    if urlsplit(source["uri"]).scheme in {"http", "https"}:
        validate_http_url_authority(source["uri"])
    uri = validate_base_url(source["uri"])
    if source["uri"] != uri:
        raise ValueError("plan source URI does not equal canonical normalization")
    parsed = urlsplit(uri)
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("plan source URI must not contain credentials")
    if kind == "website":
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or source["title"] != parsed.hostname.lower()
        ):
            raise ValueError("website plan source requires consistent HTTP(S) authority")
    elif kind == "github_repo":
        parts = [part for part in parsed.path.split("/") if part]
        if (
            parsed.scheme != "https"
            or (parsed.hostname or "").lower() != "github.com"
            or parsed.netloc.lower() != "github.com"
            or parsed.query
            or parsed.fragment
            or len(parts) != 2
            or re.fullmatch(r"[A-Za-z0-9_.-]+", str(attrs["repo_owner"])) is None
            or re.fullmatch(r"[A-Za-z0-9_.-]+", str(attrs["repo_name"])) is None
            or f"{attrs['repo_owner']}/{attrs['repo_name']}" != attrs["repo_full_name"]
            or source["title"] != attrs["repo_full_name"]
            or [part.casefold() for part in parts]
            != [str(attrs["repo_owner"]).casefold(), str(attrs["repo_name"]).casefold()]
        ):
            raise ValueError("GitHub plan source identity is inconsistent")
        if attrs["repo_subdir"] is not None:
            _validate_relative_source_path(str(attrs["repo_subdir"]))
    elif kind in {"local_file", "pdf"}:
        expected_scheme = "file" if kind == "local_file" else "pdf"
        filename = str(attrs["filename"])
        _validate_safe_filename(filename)
        if kind == "local_file":
            expected_extension = Path(filename).suffix.removeprefix(".")
            if not expected_extension or str(attrs["extension"]).casefold() != expected_extension.casefold():
                raise ValueError("local-file extension contradicts its filename")
        elif Path(filename).suffix.casefold() != ".pdf":
            raise ValueError("PDF source filename must end in .pdf")
        if (
            source["title"] != filename
            or parsed.scheme != expected_scheme
            or not parsed.netloc
            or parsed.netloc != attrs["source_id"]
            or parsed.path
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("document plan source identity is inconsistent")
    else:
        backend = kind.removesuffix("_relation")
        source_id = str(attrs["database_source_id"])
        relation = str(attrs["database_relation"])
        relation_valid = {
            "duckdb": re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*(?:\.[A-Za-z_][A-Za-z0-9_-]*){0,2}", relation),
            "bigquery": re.fullmatch(r"[a-z][a-z0-9-]*\.[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*", relation),
            "snowflake": re.fullmatch(r"[A-Z_][A-Z0-9_]*\.[A-Z_][A-Z0-9_]*\.[A-Z_][A-Z0-9_]*", relation),
        }[backend]
        if (
            attrs["database_backend"] != backend
            or parsed.scheme != backend
            or parsed.netloc != source_id
            or re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", source_id) is None
            or relation_valid is None
            or source["title"] != f"{source_id} ({relation})"
            or parsed.path
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("database plan source identity is inconsistent")


def artifact_identity(plan: Mapping[str, object]) -> JsonObject:
    return {
        "schema_version": plan["schema_version"],
        "source": plan["source"],
        "site_id": plan["site_id"],
        "namespace": plan["namespace"],
        "namespace_candidate": plan["namespace_candidate"],
        "crawl_options": plan["crawl_options"],
        "chunk_options": plan["chunk_options"],
        "embedding_model": plan["embedding_model"],
        "embedding_precision": plan["embedding_precision"],
        "applied_state": plan["applied_state"],
        "delta": plan["delta"],
        "diff": plan["diff"],
    }


def _validate_delta_schema(connection: duckdb.DuckDBPyConnection) -> None:
    application_relations = {
        (str(row[0]), str(row[1]), str(row[2]))
        for row in connection.execute(
            """
            SELECT table_schema, table_name, table_type
            FROM information_schema.tables
            WHERE table_catalog = current_database()
            """
        ).fetchall()
    }
    expected_relations = {
        ("main", "delta_metadata", "BASE TABLE"),
        ("main", "upsert_rows", "BASE TABLE"),
        ("main", "stale_rows", "BASE TABLE"),
    }
    if application_relations != expected_relations:
        raise ValueError("delta database application tables/views do not match schema")
    application_functions = connection.execute(
        """
        SELECT function_name, function_type
        FROM duckdb_functions()
        WHERE database_oid = CAST(
                (SELECT database_oid FROM duckdb_databases() WHERE database_name = current_database())
              AS VARCHAR)
          AND internal = false
        """
    ).fetchall()
    if application_functions:
        raise ValueError("delta database application macros/functions are not allowed")
    expected_columns = {
        "delta_metadata": [
            ("schema_version", "INTEGER"), ("plan_id", "VARCHAR"), ("site_id", "VARCHAR"),
            ("namespace", "VARCHAR"), ("source_kind", "VARCHAR"), ("source_uri", "VARCHAR"),
            ("applied_state_hash", "VARCHAR"), ("logical_hash", "VARCHAR"),
            ("upsert_count", "UBIGINT"), ("stale_count", "UBIGINT"),
            ("retained_stale_count", "UBIGINT"),
        ],
        "upsert_rows": [
            ("ordinal", "UBIGINT"), ("action", "VARCHAR"), ("row_id", "VARCHAR"),
            ("row_id_candidate", "VARCHAR"), ("site_id", "VARCHAR"),
            ("duplicate_ordinal", "UINTEGER"), ("canonical_url", "VARCHAR"),
            ("source_path", "VARCHAR"), ("page_hash", "VARCHAR"), ("chunk_hash", "VARCHAR"),
            ("embedding_text_hash", "VARCHAR"), ("title", "VARCHAR"),
            ("section_path", "VARCHAR"), ("chunk_index", "UINTEGER"),
            ("content", "VARCHAR"), ("doc_kind", "VARCHAR"), ("tags_json", "VARCHAR"),
            ("source_metadata_json", "VARCHAR"),
        ],
        "stale_rows": [
            ("ordinal", "UBIGINT"), ("category", "VARCHAR"), ("row_id", "VARCHAR"),
            ("canonical_url", "VARCHAR"), ("page_hash", "VARCHAR"), ("chunk_hash", "VARCHAR"),
            ("embedding_text_hash", "VARCHAR"), ("prior_plan_id", "VARCHAR"),
            ("prior_applied_at", "VARCHAR"), ("prior_status", "VARCHAR"), ("reason", "VARCHAR"),
        ],
    }
    for table, expected in expected_columns.items():
        table_info = connection.execute(f"PRAGMA table_info('{table}')").fetchall()
        observed = [(row[1], row[2]) for row in table_info]
        if observed != expected or not all(bool(row[3]) for row in table_info):
            raise ValueError(f"delta table {table} columns do not match schema")
    constraints = {
        (str(table), str(kind), str(text))
        for table, kind, text in connection.execute(
            """
            SELECT table_name, constraint_type, constraint_text
            FROM duckdb_constraints()
            WHERE schema_name='main' AND constraint_type <> 'NOT NULL'
            """
        ).fetchall()
    }
    expected_constraints = {
        ("delta_metadata", "CHECK", "CHECK((schema_version = 1))"),
        ("delta_metadata", "PRIMARY KEY", "PRIMARY KEY(plan_id)"),
        ("upsert_rows", "PRIMARY KEY", "PRIMARY KEY(ordinal)"),
        ("upsert_rows", "UNIQUE", "UNIQUE(row_id)"),
        ("upsert_rows", "CHECK", "CHECK((\"action\" IN ('new', 'changed', 'reactivate_retained_stale')))"),
        ("stale_rows", "PRIMARY KEY", "PRIMARY KEY(ordinal)"),
        ("stale_rows", "UNIQUE", "UNIQUE(row_id)"),
        ("stale_rows", "CHECK", "CHECK((category IN ('stale', 'retained_stale')))"),
        ("stale_rows", "CHECK", "CHECK((prior_status IN ('active', 'retained_stale')))"),
        ("stale_rows", "CHECK", "CHECK((reason IN ('not_in_desired_source', 'retained_stale_not_in_desired_source')))"),
    }
    if constraints != expected_constraints:
        raise ValueError("delta database constraints do not match schema")


def _read_upserts(connection: duckdb.DuckDBPyConnection) -> Iterable[JsonObject]:
    rows = connection.execute("SELECT * FROM upsert_rows ORDER BY ordinal").fetchall()
    if [int(row[0]) for row in rows] != list(range(len(rows))):
        raise ValueError("delta upsert ordinals are not contiguous")
    for row in rows:
        tags_raw = str(row[16])
        metadata_raw = str(row[17])
        try:
            tags = json.loads(tags_raw, parse_constant=_reject_json_constant)
            metadata = json.loads(metadata_raw, parse_constant=_reject_json_constant)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError("delta upsert JSON metadata is invalid") from exc
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            raise ValueError("delta upsert tags must be a string array")
        if stable_json_dumps(tags) != tags_raw:
            raise ValueError("delta upsert tags JSON is not canonical")
        if not isinstance(metadata, dict) or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in metadata.items()
        ):
            raise ValueError("delta upsert source metadata must contain strings")
        if stable_json_dumps(metadata) != metadata_raw:
            raise ValueError("delta upsert source metadata JSON is not canonical")
        yield {
            "action": str(row[1]), "row_id": str(row[2]), "row_id_candidate": str(row[3]),
            "site_id": str(row[4]), "duplicate_ordinal": int(row[5]),
            "canonical_url": str(row[6]), "source_path": str(row[7]),
            "page_hash": str(row[8]), "chunk_hash": str(row[9]),
            "embedding_text_hash": str(row[10]), "title": str(row[11]),
            "section_path": str(row[12]), "chunk_index": int(row[13]),
            "content": str(row[14]), "doc_kind": str(row[15]),
            "tags_json": tags, "source_metadata_json": metadata,
        }


def _read_stale(connection: duckdb.DuckDBPyConnection) -> Iterable[JsonObject]:
    rows = connection.execute("SELECT * FROM stale_rows ORDER BY ordinal").fetchall()
    if [int(row[0]) for row in rows] != list(range(len(rows))):
        raise ValueError("delta stale ordinals are not contiguous")
    for row in rows:
        yield {
            "category": str(row[1]), "row_id": str(row[2]), "canonical_url": str(row[3]),
            "page_hash": str(row[4]), "chunk_hash": str(row[5]),
            "embedding_text_hash": str(row[6]), "prior_plan_id": str(row[7]),
            "prior_applied_at": str(row[8]), "prior_status": str(row[9]), "reason": str(row[10]),
        }


def _upsert_sort_key(row: Mapping[str, object]) -> tuple[str, str, int, str]:
    return (
        str(row["canonical_url"]),
        str(row["section_path"]),
        int(row["chunk_index"]),
        str(row["row_id"]),
    )


def _stale_sort_key(row: Mapping[str, object]) -> tuple[str, str]:
    return (str(row["canonical_url"]), str(row["row_id"]))


def _validate_diff_counts(diff: Mapping[str, object], delta: Mapping[str, object]) -> None:
    if (
        diff["chunks_to_embed"] != delta["upsert_count"]
        or diff["rows_to_upsert"] != delta["upsert_count"]
        or diff["stale_rows"] != delta["stale_count"]
        or diff["retained_stale_rows"] != delta["retained_stale_count"]
    ):
        raise ValueError("plan diff counts do not match delta operations")
    if diff["first_apply"] and any(
        diff[field] != 0
        for field in (
            "pages_changed", "pages_unchanged", "pages_removed",
            "chunks_unchanged", "stale_rows", "retained_stale_rows",
        )
    ):
        raise ValueError("first-apply diff counts are inconsistent")


def _validate_safe_row_uri(value: str, *, source_kind: str) -> None:
    if not value or value != value.strip() or any(character.isspace() for character in value):
        raise ValueError("delta row canonical URL is invalid")
    _validate_private_string(
        value,
        label="delta row canonical URL",
        allowed_uri_schemes=_source_allowed_uri_schemes(source_kind),
    )
    parsed = urlsplit(value)
    if not parsed.scheme or parsed.username is not None or parsed.password is not None:
        raise ValueError("delta row canonical URL is invalid or contains credentials")
    if parsed.scheme in {"http", "https"}:
        validate_http_url_authority(value)
    elif not parsed.netloc:
        raise ValueError("delta row canonical URL requires a safe authority")


def _validate_relative_source_path(value: str) -> None:
    path = PurePosixPath(value)
    if (
        not value
        or value != value.strip()
        or "\\" in value
        or "\x00" in value
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
        or re.match(r"^[A-Za-z]:", value) is not None
    ):
        raise ValueError("delta upsert source_path must be a safe relative path")


_COMMON_SOURCE_METADATA = {
    "url", "title", "status", "content_type", "source_hash", "fetcher", "source_kind",
}
_SOURCE_METADATA_BY_KIND = {
    "website": _COMMON_SOURCE_METADATA,
    "github_repo": _COMMON_SOURCE_METADATA | {
        "repo_full_name", "repo_owner", "repo_name", "repo_ref", "commit_sha",
        "repo_path", "language", "repo_page_kind",
    },
    "local_file": _COMMON_SOURCE_METADATA | {
        "file_filename", "file_extension", "file_sha256", "file_source_id",
    },
    "pdf": _COMMON_SOURCE_METADATA | {
        "file_filename", "file_extension", "file_sha256", "file_source_id",
        "pdf_filename", "pdf_sha256", "pdf_source_id",
    },
    "duckdb_relation": _COMMON_SOURCE_METADATA | {
        "database_backend", "database_source_id", "database_relation",
        "database_document_id", "duckdb_source_id", "duckdb_relation",
        "duckdb_document_id",
    },
    "bigquery_relation": _COMMON_SOURCE_METADATA | {
        "database_backend", "database_source_id", "database_relation",
        "database_document_id",
    },
    "snowflake_relation": _COMMON_SOURCE_METADATA | {
        "database_backend", "database_source_id", "database_relation",
        "database_document_id",
    },
}
_ALL_SOURCE_METADATA_FIELDS = set().union(*_SOURCE_METADATA_BY_KIND.values())


def _validate_safe_metadata(
    metadata: Mapping[str, object],
    *,
    source_kind: str,
    canonical_url: str,
    row_title: str,
) -> None:
    allowed = _SOURCE_METADATA_BY_KIND[source_kind]
    for key, value in metadata.items():
        if (
            not isinstance(key, str)
            or not isinstance(value, str)
            or not key
            or "\x00" in key
            or "\x00" in value
        ):
            raise ValueError("delta upsert source metadata must contain safe strings")
        if _sensitive_key(key):
            raise ValueError(
                "delta upsert source metadata contains a credential-bearing or provider-connection field"
            )
        if _is_absolute_filesystem_path(value):
            raise ValueError("delta upsert source metadata contains a private absolute path")
        _validate_private_string(
            value,
            label="delta upsert source metadata",
            allowed_uri_schemes=(
                _source_allowed_uri_schemes(source_kind)
                if key == "url"
                else _PUBLIC_URI_SCHEMES
            ),
        )
    unknown = set(metadata) - allowed
    if unknown:
        cross_kind = unknown & _ALL_SOURCE_METADATA_FIELDS
        description = "fields from another source kind" if cross_kind else "unapproved custom/provider fields"
        raise ValueError(f"delta row source metadata contains {description}: {sorted(unknown)}")
    if "url" in metadata and metadata["url"] != canonical_url:
        raise ValueError("delta row source metadata URL contradicts canonical URL")
    if "title" in metadata and metadata["title"] != row_title:
        raise ValueError("delta row source metadata title contradicts row title")


def _validate_upsert_row(plan: Mapping[str, object], row: Mapping[str, object]) -> None:
    required_strings = (
        "action", "row_id", "row_id_candidate", "site_id", "canonical_url",
        "source_path", "page_hash", "chunk_hash", "embedding_text_hash", "title",
        "content", "doc_kind",
    )
    if any(not isinstance(row[field], str) or not row[field] for field in required_strings):
        raise ValueError("delta upsert contains an empty or invalid required field")
    if not isinstance(row["section_path"], str):
        raise ValueError("delta upsert section_path must be a string")
    if type(row["duplicate_ordinal"]) is not int or row["duplicate_ordinal"] < 0:
        raise ValueError("delta upsert duplicate ordinal is invalid")
    if type(row["chunk_index"]) is not int or row["chunk_index"] < 0:
        raise ValueError("delta upsert chunk index is invalid")
    if row["site_id"] != plan["site_id"] or _SAFE_SITE_ID.fullmatch(str(row["site_id"])) is None:
        raise ValueError("delta upsert site identity does not match")
    _validate_safe_row_uri(
        str(row["canonical_url"]), source_kind=str(plan["source"]["kind"])
    )
    _validate_relative_source_path(str(row["source_path"]))
    for field in ("page_hash", "chunk_hash", "embedding_text_hash"):
        if _HEX_SHA256.fullmatch(str(row[field])) is None:
            raise ValueError(f"delta upsert {field} is invalid")
    if row["chunk_hash"] != sha256_text(str(row["content"])):
        raise ValueError("delta upsert chunk hash does not match content")
    expected_row_id = generic_site_row_id(
        site_id=str(row["site_id"]),
        canonical_url=str(row["canonical_url"]),
        section_path=str(row["section_path"]),
        chunk_hash=str(row["chunk_hash"]),
        duplicate_ordinal=int(row["duplicate_ordinal"]),
    )
    if (
        _ROW_ID.fullmatch(str(row["row_id"])) is None
        or row["row_id"] != expected_row_id
        or row["row_id_candidate"] != expected_row_id
    ):
        raise ValueError("delta upsert row identity formula does not match")
    tags = row["tags_json"]
    if not isinstance(tags, list) or any(not isinstance(tag, str) or not tag for tag in tags):
        raise ValueError("delta upsert tags are invalid")
    if tags != sorted(set(tags)):
        raise ValueError("delta upsert tags must be sorted and unique")
    _validate_private_free_json(tags, label="delta upsert tags")
    metadata = row["source_metadata_json"]
    if not isinstance(metadata, dict):
        raise ValueError("delta upsert source metadata is invalid")
    _validate_safe_metadata(
        metadata,
        source_kind=str(plan["source"]["kind"]),
        canonical_url=str(row["canonical_url"]),
        row_title=str(row["title"]),
    )
    expected_hash = embedding_hash(embedding_text_for_chunk(row), str(plan["embedding_precision"]))
    if row["embedding_text_hash"] != expected_hash:
        raise ValueError("delta upsert embedding hash does not match")
    _validate_row_source(plan["source"], metadata, str(row["canonical_url"]))


def _validate_stale_row(plan: Mapping[str, object], row: Mapping[str, object]) -> None:
    required = (
        "category", "row_id", "canonical_url", "page_hash", "chunk_hash",
        "embedding_text_hash", "prior_plan_id", "prior_applied_at", "prior_status", "reason",
    )
    if any(not isinstance(row[field], str) or not row[field] for field in required):
        raise ValueError("delta stale row contains an empty or invalid field")
    _validate_safe_row_uri(
        str(row["canonical_url"]), source_kind=str(plan["source"]["kind"])
    )
    _validate_row_url_authority(plan["source"], str(row["canonical_url"]), metadata=None)
    for field in ("page_hash", "chunk_hash", "embedding_text_hash"):
        if _HEX_SHA256.fullmatch(str(row[field])) is None:
            raise ValueError(f"delta stale {field} is invalid")
    if _ROW_ID.fullmatch(str(row["row_id"])) is None or _PLAN_ID.fullmatch(str(row["prior_plan_id"])) is None:
        raise ValueError("delta stale identity is invalid")
    expected = {
        "stale": ("active", "not_in_desired_source"),
        "retained_stale": ("retained_stale", "retained_stale_not_in_desired_source"),
    }[str(row["category"])]
    if (row["prior_status"], row["reason"]) != expected:
        raise ValueError("delta stale category/status/reason correspondence is invalid")


def _validate_row_url_authority(
    source: Mapping[str, object],
    canonical_url: str,
    *,
    metadata: Mapping[str, object] | None,
) -> None:
    kind = str(source["kind"])
    source_uri = str(source["uri"])
    attrs = source["attributes"]
    parsed = urlsplit(canonical_url)
    source_parsed = urlsplit(source_uri)
    if kind == "website":
        if (
            parsed.scheme not in {"http", "https"}
            or (parsed.hostname or "").lower() != (source_parsed.hostname or "").lower()
        ):
            raise ValueError("delta row canonical URL is outside website source authority")
        return
    if kind == "github_repo":
        root_path = f"/{attrs['repo_owner']}/{attrs['repo_name']}/blob/"
        if (
            parsed.scheme != "https"
            or (parsed.hostname or "").lower() != "github.com"
            or not parsed.path.casefold().startswith(root_path.casefold())
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("delta row canonical URL is outside GitHub repository authority")
        if metadata is not None:
            repo_path = str(metadata.get("repo_path", ""))
            if not repo_path:
                raise ValueError("delta row source metadata is missing required repo_path")
            _validate_relative_source_path(repo_path)
            expected = (
                f"{source_uri}/blob/{quote(str(attrs['repo_ref']), safe='/')}/"
                f"{quote(repo_path, safe='/')}"
            )
            if canonical_url != expected:
                raise ValueError("delta row canonical URL contradicts GitHub repository metadata")
        return
    if kind in {"local_file", "pdf"}:
        expected = f"{source_uri}/{quote(str(attrs['filename']), safe='')}"
        if canonical_url != expected:
            raise ValueError("delta row canonical URL contradicts document source authority")
        return
    if (
        parsed.scheme != source_parsed.scheme
        or parsed.netloc != source_parsed.netloc
        or parsed.query
        or parsed.fragment
        or not parsed.path.startswith("/")
        or parsed.path in {"", "/"}
        or "/" in parsed.path[1:]
    ):
        raise ValueError("delta row canonical URL is outside database source authority")
    if metadata is not None:
        document_id = str(metadata.get("database_document_id", ""))
        if not document_id:
            raise ValueError("delta row source metadata is missing required database_document_id")
        expected = f"{source_uri}/{quote(document_id, safe='')}"
        if canonical_url != expected:
            raise ValueError("delta row canonical URL contradicts database document metadata")


def _validate_row_source(
    source: Mapping[str, object],
    metadata: Mapping[str, object],
    canonical_url: str,
) -> None:
    kind = str(source["kind"])
    attrs = source["attributes"]
    expected: dict[str, object] = {"source_kind": kind}
    optional_aliases: dict[str, object] = {}
    if kind == "github_repo":
        expected.update({
            key: attrs[key]
            for key in ("repo_full_name", "repo_owner", "repo_name", "repo_ref", "commit_sha")
        })
    elif kind == "local_file":
        expected.update({
            "file_filename": attrs["filename"], "file_extension": attrs["extension"],
            "file_sha256": attrs["sha256"], "file_source_id": attrs["source_id"],
        })
    elif kind == "pdf":
        expected.update({
            "pdf_filename": attrs["filename"], "pdf_sha256": attrs["sha256"],
            "pdf_source_id": attrs["source_id"],
        })
        optional_aliases.update({
            "file_filename": attrs["filename"], "file_extension": "pdf",
            "file_sha256": attrs["sha256"], "file_source_id": attrs["source_id"],
        })
    elif kind.endswith("_relation"):
        expected.update({
            "database_backend": attrs["database_backend"],
            "database_source_id": attrs["database_source_id"],
            "database_relation": attrs["database_relation"],
        })
        if kind == "duckdb_relation":
            optional_aliases.update({
                "duckdb_source_id": attrs["database_source_id"],
                "duckdb_relation": attrs["database_relation"],
            })
    for key, value in expected.items():
        if kind != "website" and key not in metadata:
            raise ValueError(f"delta row source metadata is missing required {key}")
        if key in metadata and metadata[key] != value:
            raise ValueError(f"delta row source metadata {key} contradicts plan source")
    for key, value in optional_aliases.items():
        if key in metadata and metadata[key] != value:
            raise ValueError(f"delta row source metadata alias {key} contradicts plan source")
    if kind == "duckdb_relation" and "duckdb_document_id" in metadata:
        if metadata.get("database_document_id") != metadata["duckdb_document_id"]:
            raise ValueError("delta row source metadata alias duckdb_document_id contradicts plan source")
    _validate_row_url_authority(source, canonical_url, metadata=metadata)


def build_generic_site_row(
    chunk: ChunkManifestRecord | JsonObject,
    vector: Iterable[float],
    *,
    plan_id: str,
    applied_at: str,
) -> JsonObject:
    record = dataclass_to_json_object(chunk) if isinstance(chunk, ChunkManifestRecord) else normalize_json_object(chunk)
    if "source_path" in record and "page_content_path" not in record:
        record["page_content_path"] = record["source_path"]
    source_metadata = normalize_json_object(
        record.get("source_metadata_json", record.get("source_metadata", {}))
    )
    row = {
        "id": record["row_id"], "vector": list(vector), "content": record["content"],
        "title": record["title"], "url": record["canonical_url"],
        "path": record["page_content_path"], "section_path": record["section_path"],
        "chunk_index": record["chunk_index"], "doc_kind": record["doc_kind"],
        "tags": record.get("tags_json", record.get("tags", [])),
        "source_hash": record["page_hash"],
        "site_id": record["site_id"], "canonical_url": record["canonical_url"],
        "page_hash": record["page_hash"], "chunk_hash": record["chunk_hash"],
        "embedding_text_hash": record["embedding_text_hash"], "plan_id": plan_id,
        "applied_at": applied_at,
    }
    if isinstance(source_metadata, dict):
        for field_name in SOURCE_METADATA_ROW_FIELDS:
            row[field_name] = str(source_metadata.get(field_name, ""))
    return row


def default_diff(indexing_plan: IndexingPlan) -> JsonObject:
    return {
        "first_apply": True, "pages_added": indexing_plan.files_discovered,
        "pages_changed": 0, "pages_unchanged": 0, "pages_removed": 0,
        "chunks_unchanged": 0, "chunks_to_embed": len(indexing_plan.chunks),
        "rows_to_upsert": len(indexing_plan.chunks), "stale_rows": 0,
        "retained_stale_rows": 0,
    }


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number {value}")


def dataclass_to_json_object(value: object) -> JsonObject:
    return normalize_json_object(asdict(value))


def normalize_json_object(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): normalize_json_object(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [normalize_json_object(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite JSON numbers are not supported")
        return value
    if value is None or isinstance(value, (str, int, bool)):
        return value
    return str(value)


def stable_json_dumps(value: Any, *, indent: int | None = None) -> str:
    return json.dumps(
        normalize_json_object(value), ensure_ascii=False, indent=indent,
        separators=None if indent is not None else (",", ":"), sort_keys=True,
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
    """Legacy in-memory helper retained until the dependent apply ticket lands."""

    for line in chunks_jsonl.splitlines():
        if line.strip():
            yield json.loads(line)
