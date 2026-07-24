"""Read-only, framework-independent local inventory for the Buoy command center.

The service reads saved plan artifacts and compact applied state only. It does
not import source adapters, read credentials, load models, or contact remote
providers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Literal
from urllib.parse import quote, unquote, urlsplit, urlunsplit

import duckdb

from buoy_search.applied_state import (
    ROW_STATUS_ACTIVE,
    ROW_STATUS_RETAINED_STALE,
    AppliedStateError,
    applied_state_paths,
    load_applied_state,
)

DEFAULT_ARTIFACTS_ROOT = Path("artifacts/site-crawls")
DEFAULT_STATE_ROOT = Path(".buoy")
MAX_PAGE_SIZE = 100
MAX_PREVIEW_CHARS = 20_000
MAX_CITATION_CHARS = 2_000
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
SAFE_MANAGED_JOB_ID = re.compile(r"^planjob_[0-9a-f]{32}$")
SAFE_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SAFE_DATABASE_SOURCE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SAFE_DATABASE_RELATION = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_-]*(?:\.[A-Za-z_][A-Za-z0-9_-]*){0,2}$"
)
SAFE_DOCUMENT_CITATION = re.compile(
    r"^(?:file|pdf)://[A-Za-z0-9][A-Za-z0-9_.-]{0,127}/"
    r"(?P<filename>(?:[A-Za-z0-9_.~-]|%[0-9A-Fa-f]{2})+)$"
)
SAFE_DATABASE_CITATION = re.compile(
    r"^(?:duckdb|bigquery|snowflake)://"
    r"[a-z0-9]+(?:-[a-z0-9]+)*/"
    r"(?P<document_id>(?:[A-Za-z0-9_.~-]|%[0-9A-Fa-f]{2})+)$"
)
DATABASE_KINDS = {
    "duckdb_relation": "duckdb",
    "bigquery_relation": "bigquery",
    "snowflake_relation": "snowflake",
}
DIFF_COUNT_FIELDS = (
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


class InventoryLookupError(ValueError):
    """A safe local-inventory lookup or bounds failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class SafeError:
    code: str
    message: str
    artifact_id: str


@dataclass(frozen=True)
class InventoryWarning:
    code: str
    message: str


@dataclass(frozen=True)
class SourceProvenance:
    kind: Literal["website", "github_repo", "document", "database", "unknown"]
    uri: str | None
    title: str | None
    repository: str | None = None
    filename: str | None = None
    database_backend: str | None = None
    database_source_id: str | None = None
    database_relation: str | None = None


@dataclass(frozen=True)
class RetrievalSettings:
    embedding_model: str | None
    embedding_precision: str | None
    ranking_mode: str | None
    ranking_profile: str | None
    ranking_pool: int | None
    ranking_aggregation: str | None
    region: str | None = None


@dataclass(frozen=True)
class SourceActivity:
    credentials_required: bool | None
    api_calls_occurred: bool | None


@dataclass(frozen=True)
class DiffSummary:
    first_apply: bool | None
    pages_added: int | None
    pages_changed: int | None
    pages_unchanged: int | None
    pages_removed: int | None
    chunks_unchanged: int | None
    chunks_to_embed: int | None
    rows_to_upsert: int | None
    stale_rows: int | None
    retained_stale_rows: int | None


@dataclass(frozen=True)
class PlanSummary:
    plan_id: str
    namespace: str
    site_id: str
    created_at: str | None
    source: SourceProvenance
    page_count: int | None
    chunk_count: int | None
    diff: DiffSummary
    source_activity: SourceActivity = SourceActivity(None, None)
    warnings: list[InventoryWarning] = field(default_factory=list)


@dataclass(frozen=True)
class PlanDetail:
    summary: PlanSummary
    namespace_candidate: str
    artifact_hash: str | None
    retrieval: RetrievalSettings
    source_activity: SourceActivity
    originating_job_id: str | None


@dataclass(frozen=True)
class StateSummary:
    namespace: str
    site_id: str
    source: SourceProvenance
    updated_at: str | None
    last_plan_id: str | None
    last_apply_id: str | None
    active_rows: int
    retained_stale_rows: int


@dataclass(frozen=True)
class NamespaceSummary:
    namespace: str
    source: SourceProvenance | None
    plan_count: int
    latest_plan_id: str | None
    latest_plan_created_at: str | None
    applied: bool
    active_rows: int | None
    last_apply_id: str | None
    local_status: Literal["planned", "applied", "pending_changes", "conflict", "error"] = "planned"
    retained_stale_rows: int | None = None
    latest_planned_upserts: int | None = None
    latest_planned_stale_rows: int | None = None
    document_count: int | None = None
    chunk_count: int | None = None
    warnings: list[InventoryWarning] = field(default_factory=list)


@dataclass(frozen=True)
class NamespaceDetail:
    summary: NamespaceSummary
    plans: list[PlanSummary]
    state: StateSummary | None
    retrieval: RetrievalSettings | None


@dataclass(frozen=True)
class PlanInventory:
    items: list[PlanSummary]
    total: int
    offset: int
    limit: int
    errors: list[SafeError]


@dataclass(frozen=True)
class NamespaceInventory:
    items: list[NamespaceSummary]
    total: int
    offset: int
    limit: int
    errors: list[SafeError]


@dataclass(frozen=True)
class PageSummary:
    index: int
    title: str
    canonical_url: str
    status: int | None
    content_type: str


@dataclass(frozen=True)
class PagePreview:
    page: PageSummary
    markdown: str
    truncated: bool


@dataclass(frozen=True)
class ChunkPreview:
    index: int
    row_id: str
    title: str
    canonical_url: str
    section_path: str
    chunk_index: int
    content: str
    truncated: bool


@dataclass(frozen=True)
class PageInventory:
    items: list[PageSummary]
    total: int
    offset: int
    limit: int


@dataclass(frozen=True)
class ChunkInventory:
    items: list[ChunkPreview]
    total: int
    offset: int
    limit: int


@dataclass(frozen=True)
class Dashboard:
    plan_count: int
    namespace_count: int
    applied_namespace_count: int
    pending_namespace_count: int
    active_row_count: int | None
    artifact_error_count: int
    recent_plans: list[PlanSummary]
    attention_items: list[InventoryWarning]
    artifact_errors: list[SafeError]


@dataclass(frozen=True)
class _PlanRecord:
    summary: PlanSummary
    namespace_candidate: str
    artifact_hash: str | None
    retrieval: RetrievalSettings
    source_activity: SourceActivity
    originating_job_id: str | None
    pages: list[dict[str, Any]]
    chunks: list[dict[str, Any]]
    directory: Path = field(repr=False)
    timestamp: datetime | None = field(repr=False)
    candidate_id: str = field(repr=False)


@dataclass(frozen=True)
class _Snapshot:
    plans: list[_PlanRecord]
    states: list[StateSummary]
    errors: list[SafeError]


class LocalInventoryService:
    """Query local plans and applied state without side effects or remote imports."""

    def __init__(
        self,
        *,
        artifacts_root: Path = DEFAULT_ARTIFACTS_ROOT,
        state_root: Path = DEFAULT_STATE_ROOT,
    ) -> None:
        self.artifacts_root = Path(artifacts_root)
        self.state_root = Path(state_root)

    def list_plans(self, *, offset: int = 0, limit: int = 50) -> PlanInventory:
        offset, limit = _validate_pagination(offset, limit)
        snapshot = self._snapshot()
        items = [record.summary for record in snapshot.plans]
        return PlanInventory(items[offset : offset + limit], len(items), offset, limit, snapshot.errors)

    def get_plan(self, plan_id: str) -> PlanDetail:
        record = self._plan_record(plan_id)
        return PlanDetail(
            summary=record.summary,
            namespace_candidate=record.namespace_candidate,
            artifact_hash=record.artifact_hash,
            retrieval=record.retrieval,
            source_activity=record.source_activity,
            originating_job_id=record.originating_job_id,
        )

    def list_plan_pages(
        self, plan_id: str, *, offset: int = 0, limit: int = 50
    ) -> PageInventory:
        offset, limit = _validate_pagination(offset, limit)
        record = self._plan_record(plan_id)
        items = [_page_summary(index, page) for index, page in enumerate(record.pages)]
        return PageInventory(items[offset : offset + limit], len(items), offset, limit)

    def get_plan_page(
        self, plan_id: str, index: int, *, max_chars: int = MAX_PREVIEW_CHARS
    ) -> PagePreview:
        max_chars = _validate_preview_limit(max_chars)
        record = self._plan_record(plan_id)
        if type(index) is not int or index < 0 or index >= len(record.pages):
            raise InventoryLookupError("page_not_found", "Plan page index was not found.")
        page = record.pages[index]
        content_path = str(page["content_path"])
        preview_path = _safe_preview_path(record.directory, content_path)
        try:
            markdown = preview_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise InventoryLookupError("page_unavailable", "Plan page preview is unavailable.") from exc
        text, truncated = _bounded_text(markdown, max_chars)
        return PagePreview(_page_summary(index, page), text, truncated)

    def list_plan_chunks(
        self,
        plan_id: str,
        *,
        offset: int = 0,
        limit: int = 50,
        max_chars: int = 2_000,
    ) -> ChunkInventory:
        offset, limit = _validate_pagination(offset, limit)
        max_chars = _validate_preview_limit(max_chars)
        record = self._plan_record(plan_id)
        selected = record.chunks[offset : offset + limit]
        items = [
            _chunk_preview(index, chunk, max_chars=max_chars)
            for index, chunk in enumerate(selected, start=offset)
        ]
        return ChunkInventory(items, len(record.chunks), offset, limit)

    def list_namespaces(self, *, offset: int = 0, limit: int = 50) -> NamespaceInventory:
        offset, limit = _validate_pagination(offset, limit)
        snapshot = self._snapshot()
        items = _namespace_summaries(snapshot)
        return NamespaceInventory(items[offset : offset + limit], len(items), offset, limit, snapshot.errors)

    def get_namespace(self, namespace: str) -> NamespaceDetail:
        _validate_lookup_id(namespace, label="namespace")
        snapshot = self._snapshot()
        summaries = {item.namespace: item for item in _namespace_summaries(snapshot)}
        summary = summaries.get(namespace)
        if summary is None:
            raise InventoryLookupError("namespace_not_found", "Namespace was not found.")
        plans = [record for record in snapshot.plans if record.summary.namespace == namespace]
        matching_states = [item for item in snapshot.states if item.namespace == namespace]
        state = matching_states[0] if len(matching_states) == 1 else None
        return NamespaceDetail(
            summary=summary,
            plans=[record.summary for record in plans],
            state=state,
            retrieval=plans[0].retrieval if plans else None,
        )

    def dashboard(self, *, recent_limit: int = 10) -> Dashboard:
        if type(recent_limit) is not int or recent_limit < 1 or recent_limit > MAX_PAGE_SIZE:
            raise InventoryLookupError(
                "invalid_limit", f"recent_limit must be between 1 and {MAX_PAGE_SIZE}."
            )
        snapshot = self._snapshot()
        namespaces = _namespace_summaries(snapshot)
        attention = [
            InventoryWarning("artifact_errors", f"{len(snapshot.errors)} local artifact error(s) require attention.")
            for _ in [0]
            if snapshot.errors
        ]
        attention.extend(
            warning
            for record in snapshot.plans
            for warning in record.summary.warnings
        )
        active_counts = [state.active_rows for state in snapshot.states]
        state_namespaces = [state.namespace for state in snapshot.states]
        state_inventory_complete = (
            len(state_namespaces) == len(set(state_namespaces))
            and not any(
                error.code in {"malformed_state", "unsafe_state_root", "unsafe_symlink"}
                for error in snapshot.errors
            )
        )
        attention.extend(
            warning
            for namespace in namespaces
            for warning in namespace.warnings
            if warning.code == "namespace_identity_conflict"
        )
        return Dashboard(
            plan_count=len(snapshot.plans),
            namespace_count=len(namespaces),
            applied_namespace_count=sum(1 for item in namespaces if item.applied),
            pending_namespace_count=sum(
                1 for item in namespaces if item.local_status == "pending_changes"
            ),
            active_row_count=sum(active_counts) if state_inventory_complete else None,
            artifact_error_count=len(snapshot.errors),
            recent_plans=[record.summary for record in snapshot.plans[:recent_limit]],
            attention_items=attention,
            artifact_errors=snapshot.errors,
        )

    def _plan_record(self, plan_id: str) -> _PlanRecord:
        _validate_lookup_id(plan_id, label="plan ID")
        record = next(
            (item for item in self._snapshot().plans if item.summary.plan_id == plan_id),
            None,
        )
        if record is None:
            raise InventoryLookupError("plan_not_found", "Plan was not found.")
        return record

    def _snapshot(self) -> _Snapshot:
        plans, plan_errors = _discover_plans(self.artifacts_root)
        states, state_errors = _discover_states(self.state_root)
        return _Snapshot(plans=plans, states=states, errors=sorted(
            [*plan_errors, *state_errors], key=lambda item: (item.code, item.artifact_id)
        ))


def _discover_plans(root: Path) -> tuple[list[_PlanRecord], list[SafeError]]:
    if not root.exists():
        return [], []
    if root.is_symlink() or not root.is_dir():
        return [], [SafeError("unsafe_artifacts_root", "Artifacts root must be a regular directory.", "artifacts_root")]
    records: list[_PlanRecord] = []
    errors: list[SafeError] = []
    for current, directories, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        safe_directories: list[str] = []
        for name in sorted(directories):
            child = current_path / name
            if child.is_symlink():
                errors.append(_artifact_error(root, child, "unsafe_symlink", "Symlinked artifact directories are not inspected."))
            else:
                safe_directories.append(name)
        directories[:] = safe_directories
        if "plan.json" not in files:
            continue
        plan_path = current_path / "plan.json"
        if plan_path.is_symlink():
            errors.append(_artifact_error(root, plan_path, "unsafe_symlink", "Symlinked plan artifacts are not inspected."))
            continue
        try:
            records.append(_read_plan(root, plan_path))
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
            errors.append(_artifact_error(root, plan_path, "malformed_plan", _safe_parse_message(exc)))

    by_id: dict[str, _PlanRecord] = {}
    duplicate_counts: dict[str, int] = {}
    for record in records:
        current = by_id.get(record.summary.plan_id)
        if current is None:
            by_id[record.summary.plan_id] = record
            continue
        duplicate_counts[record.summary.plan_id] = duplicate_counts.get(record.summary.plan_id, 1) + 1
        if _record_selection_key(record) > _record_selection_key(current):
            by_id[record.summary.plan_id] = record
    deduped: list[_PlanRecord] = []
    for plan_id, record in by_id.items():
        count = duplicate_counts.get(plan_id)
        if count:
            warning = InventoryWarning(
                "duplicate_plan_id",
                f"{count} artifacts shared this plan ID; the newest valid timestamp was selected.",
            )
            record = _replace_record_warnings(record, [*record.summary.warnings, warning])
        deduped.append(record)
    deduped.sort(key=_record_sort_key)
    return deduped, errors


def _read_plan(root: Path, plan_path: Path) -> _PlanRecord:
    plan = _json_object(plan_path)
    plan_id = _required_safe_string(plan, "plan_id")
    namespace = _required_safe_string(plan, "namespace")
    site_id = _required_safe_string(plan, "site_id")
    namespace_candidate = _required_string(plan, "namespace_candidate")
    if plan.get("command") != "plan":
        raise ValueError("plan command is invalid")
    created_at_raw = plan.get("created_at")
    created_at = created_at_raw if isinstance(created_at_raw, str) and created_at_raw else None
    timestamp = _parse_timestamp(created_at)
    warnings: list[InventoryWarning] = []
    if timestamp is None:
        warnings.append(InventoryWarning("invalid_created_at", "Plan creation timestamp is missing or invalid."))

    directory = plan_path.parent
    manifest_path = directory / "manifest.json"
    if manifest_path.is_symlink():
        raise ValueError("manifest is a symlink")
    manifest = _json_object(manifest_path)
    for key, expected in (
        ("namespace", namespace),
        ("site_id", site_id),
        ("base_url", _required_string(plan, "base_url")),
        ("namespace_candidate", namespace_candidate),
    ):
        if manifest.get(key) != expected:
            raise ValueError(f"manifest {key} does not match plan")
    pages = _object_list(manifest, "pages")
    chunks = _object_list(manifest, "chunks")
    for page in pages:
        _required_string(page, "canonical_url")
        _required_string(page, "title")
        _validate_relative_content_path(_required_string(page, "content_path"))
    for chunk in chunks:
        _required_safe_string(chunk, "row_id")
        _required_string(chunk, "canonical_url")
        _required_string(chunk, "content")
        if type(chunk.get("chunk_index")) is not int:
            raise ValueError("manifest chunk_index must be an integer")

    summary_payload = _optional_summary(directory / "summary.json", plan_id, warnings)
    metadata = _source_metadata(pages, chunks)
    source, source_warnings = _map_source(_required_string(plan, "base_url"), site_id, metadata)
    warnings.extend(source_warnings)
    diff = _diff_summary(plan.get("diff"))
    retrieval = _retrieval_settings(plan, summary_payload)
    activity = _source_activity(summary_payload)
    originating_job_id = _originating_job_id(summary_payload, warnings)
    artifact_hash = plan.get("artifact_hash")
    if not isinstance(artifact_hash, str) or re.fullmatch(r"[0-9a-f]{64}", artifact_hash) is None:
        artifact_hash = None
        warnings.append(InventoryWarning("invalid_artifact_hash", "Plan artifact hash is missing or invalid."))
    candidate_id = _artifact_id(root, plan_path)
    summary = PlanSummary(
        plan_id=plan_id,
        namespace=namespace,
        site_id=site_id,
        created_at=created_at if timestamp is not None else None,
        source=source,
        page_count=len(pages),
        chunk_count=len(chunks),
        diff=diff,
        source_activity=activity,
        warnings=warnings,
    )
    return _PlanRecord(
        summary=summary,
        namespace_candidate=namespace_candidate,
        artifact_hash=artifact_hash,
        retrieval=retrieval,
        source_activity=activity,
        originating_job_id=originating_job_id,
        pages=pages,
        chunks=chunks,
        directory=directory,
        timestamp=timestamp,
        candidate_id=candidate_id,
    )


def _discover_states(state_root: Path) -> tuple[list[StateSummary], list[SafeError]]:
    if state_root.is_symlink():
        return [], [SafeError("unsafe_state_root", "Applied-state root must not be a symlink.", "state_root")]
    state_dir = state_root / "state"
    if not state_dir.exists():
        return [], []
    if state_dir.is_symlink() or not state_dir.is_dir():
        return [], [SafeError("unsafe_state_root", "Applied-state directory must be a regular directory.", "state_root")]
    try:
        trusted_root = state_root.resolve(strict=True)
        state_dir.resolve(strict=True).relative_to(trusted_root)
    except (OSError, ValueError):
        return [], [SafeError("unsafe_state_root", "Applied-state directory escapes its configured root.", "state_root")]
    states: list[StateSummary] = []
    errors: list[SafeError] = []
    for current, directories, files in os.walk(state_dir, followlinks=False):
        current_path = Path(current)
        try:
            current_path.resolve(strict=True).relative_to(trusted_root)
        except (OSError, ValueError):
            errors.append(SafeError("unsafe_symlink", "Applied-state path escapes its configured root.", _artifact_id(state_root, current_path)))
            directories[:] = []
            continue
        safe_directories: list[str] = []
        for name in sorted(directories):
            child = current_path / name
            if child.is_symlink():
                errors.append(SafeError(
                    "unsafe_symlink",
                    "Symlinked applied-state directories are not inspected.",
                    _artifact_id(state_root, child),
                ))
            else:
                safe_directories.append(name)
        directories[:] = safe_directories
        if "state.duckdb" not in files:
            continue
        database_path = current_path / "state.duckdb"
        artifact_id = _artifact_id(state_root, database_path)
        if database_path.is_symlink():
            errors.append(SafeError("unsafe_symlink", "Symlinked applied state is not inspected.", artifact_id))
            continue
        try:
            database_path.resolve(strict=True).relative_to(trusted_root)
            with duckdb.connect(str(database_path), read_only=True) as connection:
                rows = connection.execute(
                    "SELECT site_id, namespace, base_url FROM state_metadata"
                ).fetchall()
            if len(rows) != 1:
                raise AppliedStateError("applied state must contain exactly one metadata row")
            site_id, namespace, base_url = (str(value) for value in rows[0])
            expected = applied_state_paths(
                site_id=site_id, namespace=namespace, state_root=state_root
            ).database_path.absolute()
            if database_path.absolute() != expected:
                raise AppliedStateError("applied state path does not match its identity")
            state = load_applied_state(
                site_id=site_id,
                namespace=namespace,
                base_url=base_url,
                state_root=state_root,
            )
            source, _ = _map_source(state.base_url, state.site_id, [])
            states.append(StateSummary(
                namespace=state.namespace,
                site_id=state.site_id,
                source=source,
                updated_at=state.updated_at or None,
                last_plan_id=state.last_plan_id or None,
                last_apply_id=state.last_apply_id or None,
                active_rows=sum(row.status == ROW_STATUS_ACTIVE for row in state.rows),
                retained_stale_rows=sum(
                    row.status == ROW_STATUS_RETAINED_STALE for row in state.rows
                ),
            ))
        except (duckdb.Error, AppliedStateError, OSError, ValueError) as exc:
            errors.append(SafeError("malformed_state", _safe_parse_message(exc), artifact_id))
    states.sort(key=lambda item: item.namespace)
    return states, errors


def _namespace_summaries(snapshot: _Snapshot) -> list[NamespaceSummary]:
    plan_groups: dict[str, list[_PlanRecord]] = {}
    for plan in snapshot.plans:
        plan_groups.setdefault(plan.summary.namespace, []).append(plan)
    state_groups: dict[str, list[StateSummary]] = {}
    for state in snapshot.states:
        state_groups.setdefault(state.namespace, []).append(state)
    summaries: list[NamespaceSummary] = []
    for namespace in sorted(set(plan_groups) | set(state_groups)):
        plans = plan_groups.get(namespace, [])
        states = state_groups.get(namespace, [])
        state = states[0] if len(states) == 1 else None
        latest = plans[0] if plans else None
        warnings = [warning for plan in plans for warning in plan.summary.warnings]
        site_ids = {plan.summary.site_id for plan in plans}
        site_ids.update(item.site_id for item in states)
        if len(states) > 1 or len(site_ids) > 1:
            warnings.append(InventoryWarning(
                "namespace_identity_conflict",
                "Multiple local identities claim this namespace; applied counts are unknown.",
            ))
        identity_conflict = len(states) > 1 or len(site_ids) > 1
        pending_changes = bool(
            latest
            and (
                (latest.summary.diff.rows_to_upsert or 0) > 0
                or (latest.summary.diff.stale_rows or 0) > 0
            )
        )
        local_status: Literal["planned", "applied", "pending_changes", "conflict", "error"]
        if identity_conflict:
            local_status = "conflict"
        elif pending_changes:
            local_status = "pending_changes"
        elif state:
            local_status = "applied"
        else:
            local_status = "planned"
        summaries.append(NamespaceSummary(
            namespace=namespace,
            source=latest.summary.source if latest else (state.source if state else None),
            plan_count=len(plans),
            latest_plan_id=latest.summary.plan_id if latest else None,
            latest_plan_created_at=latest.summary.created_at if latest else None,
            applied=bool(states),
            active_rows=state.active_rows if state and not identity_conflict else None,
            last_apply_id=state.last_apply_id if state and not identity_conflict else None,
            local_status=local_status,
            retained_stale_rows=(
                state.retained_stale_rows if state and not identity_conflict else None
            ),
            latest_planned_upserts=(latest.summary.diff.rows_to_upsert if latest else None),
            latest_planned_stale_rows=(latest.summary.diff.stale_rows if latest else None),
            document_count=latest.summary.page_count if latest else None,
            chunk_count=latest.summary.chunk_count if latest else None,
            warnings=warnings,
        ))
    return summaries


def _map_source(
    base_url: str,
    site_id: str,
    metadata: list[dict[str, str]],
) -> tuple[SourceProvenance, list[InventoryWarning]]:
    warnings: list[InventoryWarning] = []
    raw_kind = _consistent(metadata, "source_kind", warnings)
    parsed = urlsplit(base_url)
    uri = _safe_source_uri(base_url)
    if raw_kind in DATABASE_KINDS or parsed.scheme in {"duckdb", "bigquery", "snowflake"}:
        backend = DATABASE_KINDS.get(raw_kind, parsed.scheme)
        generic_backend = _consistent(metadata, "database_backend", warnings)
        source_id = _consistent(metadata, "database_source_id", warnings) or parsed.netloc
        relation = _consistent(metadata, "database_relation", warnings)
        if raw_kind == "duckdb_relation" and not generic_backend:
            source_id = source_id or _consistent(metadata, "duckdb_source_id", warnings)
            relation = relation or _consistent(metadata, "duckdb_relation", warnings)
        if generic_backend and generic_backend != backend:
            warnings.append(InventoryWarning("source_metadata_conflict", "Database backend metadata is inconsistent."))
        if source_id and SAFE_DATABASE_SOURCE_ID.fullmatch(source_id) is None:
            source_id = None
            warnings.append(InventoryWarning("unsafe_source_metadata", "Database source metadata was omitted because it was unsafe."))
        if relation and SAFE_DATABASE_RELATION.fullmatch(relation) is None:
            relation = None
            warnings.append(InventoryWarning("unsafe_source_metadata", "Database relation metadata was omitted because it was unsafe."))
        return SourceProvenance(
            kind="database",
            uri=uri,
            title=f"{source_id} ({relation})" if source_id and relation else source_id or site_id,
            database_backend=backend,
            database_source_id=source_id,
            database_relation=relation,
        ), warnings
    if raw_kind == "github_repo" or (
        raw_kind is None and parsed.scheme == "https" and (parsed.hostname or "").lower() == "github.com"
    ):
        repository = _consistent(metadata, "repo_full_name", warnings)
        if not repository:
            parts = [part for part in parsed.path.split("/") if part]
            repository = "/".join(parts[:2]) if len(parts) >= 2 else None
        if repository and SAFE_REPOSITORY.fullmatch(repository) is None:
            repository = None
            warnings.append(InventoryWarning("unsafe_source_metadata", "Repository metadata was omitted because it was unsafe."))
        return SourceProvenance(
            kind="github_repo", uri=uri, title=repository or site_id, repository=repository
        ), warnings
    if raw_kind in {"local_file", "pdf"} or parsed.scheme in {"file", "pdf"}:
        filename_key = "pdf_filename" if raw_kind == "pdf" or parsed.scheme == "pdf" else "file_filename"
        filename = _consistent(metadata, filename_key, warnings)
        if filename and (Path(filename).is_absolute() or "/" in filename or "\\" in filename):
            filename = None
            warnings.append(InventoryWarning("unsafe_source_metadata", "Document filename metadata was omitted because it contained a path."))
        return SourceProvenance(
            kind="document", uri=uri, title=filename or site_id, filename=filename
        ), warnings
    if parsed.scheme in {"http", "https"} and parsed.hostname:
        return SourceProvenance(
            kind="website", uri=uri, title=parsed.hostname.lower()
        ), warnings
    warnings.append(InventoryWarning("unknown_source", "Plan source provenance is not recognized."))
    return SourceProvenance(kind="unknown", uri=None, title=site_id), warnings


def _source_metadata(
    pages: list[dict[str, Any]], chunks: list[dict[str, Any]]
) -> list[dict[str, str]]:
    values: list[dict[str, str]] = []
    for record in [*pages, *chunks]:
        metadata = record.get("source_metadata")
        if isinstance(metadata, dict):
            values.append({str(key): str(value) for key, value in metadata.items() if isinstance(value, str)})
    return values


def _consistent(
    metadata: list[dict[str, str]], key: str, warnings: list[InventoryWarning]
) -> str | None:
    values = {item[key].strip() for item in metadata if item.get(key, "").strip()}
    if len(values) > 1:
        warnings.append(InventoryWarning("source_metadata_conflict", f"Source metadata field {key} is inconsistent."))
        return None
    return next(iter(values), None)


def _safe_source_uri(value: str) -> str | None:
    try:
        parsed = urlsplit(value)
        if parsed.username is not None or parsed.password is not None:
            return None
        if parsed.scheme in {"file", "pdf", "duckdb", "bigquery", "snowflake"}:
            if not parsed.netloc or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
                return None
            return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
        if parsed.scheme in {"http", "https"} and parsed.hostname:
            return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    except ValueError:
        pass
    return None


def _retrieval_settings(plan: dict[str, Any], summary: dict[str, Any] | None) -> RetrievalSettings:
    registration = summary.get("catalog_registration") if summary else None
    registration = registration if isinstance(registration, dict) else {}
    embedding_model = _optional_string(plan.get("embedding_model"))
    if embedding_model and _looks_like_private_path(embedding_model):
        embedding_model = None
    region = _optional_string(registration.get("region"))
    if region is not None and SAFE_ID.fullmatch(region) is None:
        region = None
    return RetrievalSettings(
        embedding_model=embedding_model,
        embedding_precision=_optional_string(plan.get("embedding_precision")) or "float32",
        ranking_mode=_optional_string(registration.get("ranking_mode")),
        ranking_profile=_optional_string(registration.get("ranking_profile")),
        ranking_pool=_optional_positive_int(registration.get("ranking_pool")),
        ranking_aggregation=_optional_string(registration.get("ranking_aggregation")),
        region=region,
    )


def _source_activity(summary: dict[str, Any] | None) -> SourceActivity:
    if summary is None:
        return SourceActivity(None, None)
    return SourceActivity(
        _optional_bool(summary.get("source_credentials_required")),
        _optional_bool(summary.get("source_api_calls_occurred")),
    )


def _originating_job_id(
    summary: dict[str, Any] | None, warnings: list[InventoryWarning]
) -> str | None:
    if summary is None or "originating_job_id" not in summary:
        return None
    job_id = summary.get("originating_job_id")
    if isinstance(job_id, str) and SAFE_MANAGED_JOB_ID.fullmatch(job_id):
        return job_id
    warnings.append(
        InventoryWarning(
            "invalid_originating_job_id",
            "Plan origin metadata is missing or invalid.",
        )
    )
    return None


def _optional_summary(
    path: Path, plan_id: str, warnings: list[InventoryWarning]
) -> dict[str, Any] | None:
    if not path.exists():
        return None
    if path.is_symlink():
        warnings.append(InventoryWarning("unsafe_summary", "Symlinked plan summary was ignored."))
        return None
    try:
        summary = _json_object(path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError):
        warnings.append(InventoryWarning("malformed_summary", "Plan summary metadata could not be read."))
        return None
    if summary.get("plan_id") != plan_id:
        warnings.append(InventoryWarning("mismatched_summary", "Plan summary metadata did not match the plan ID."))
        return None
    return summary


def _diff_summary(value: Any) -> DiffSummary:
    payload = value if isinstance(value, dict) else {}
    counts = {key: _optional_nonnegative_int(payload.get(key)) for key in DIFF_COUNT_FIELDS}
    first_apply = payload.get("first_apply")
    return DiffSummary(
        first_apply=first_apply if isinstance(first_apply, bool) else None,
        **counts,
    )


def _page_summary(index: int, page: dict[str, Any]) -> PageSummary:
    status = page.get("status")
    return PageSummary(
        index=index,
        title=str(page["title"]),
        canonical_url=_safe_content_uri(str(page["canonical_url"])) or "",
        status=status if type(status) is int else None,
        content_type=str(page.get("content_type", "")),
    )


def _chunk_preview(index: int, chunk: dict[str, Any], *, max_chars: int) -> ChunkPreview:
    content, truncated = _bounded_text(str(chunk["content"]), max_chars)
    return ChunkPreview(
        index=index,
        row_id=str(chunk["row_id"]),
        title=str(chunk.get("title", "")),
        canonical_url=_safe_content_uri(str(chunk["canonical_url"])) or "",
        section_path=str(chunk.get("section_path", "")),
        chunk_index=int(chunk["chunk_index"]),
        content=content,
        truncated=truncated,
    )


def _safe_preview_path(plan_directory: Path, content_path: str) -> Path:
    _validate_relative_content_path(content_path)
    pages_root = plan_directory / "pages"
    candidate = pages_root / content_path
    if pages_root.is_symlink() or candidate.is_symlink():
        raise InventoryLookupError("unsafe_page_path", "Plan page preview path is unsafe.")
    current = pages_root
    for part in Path(content_path).parts:
        current = current / part
        if current.is_symlink():
            raise InventoryLookupError("unsafe_page_path", "Plan page preview path is unsafe.")
    try:
        candidate.resolve(strict=False).relative_to(pages_root.resolve(strict=False))
    except (OSError, ValueError) as exc:
        raise InventoryLookupError("unsafe_page_path", "Plan page preview path is unsafe.") from exc
    if not candidate.is_file():
        raise InventoryLookupError("page_unavailable", "Plan page preview is unavailable.")
    return candidate


def _validate_relative_content_path(value: str) -> None:
    path = Path(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("manifest content_path is unsafe")


def _validate_pagination(offset: int, limit: int) -> tuple[int, int]:
    if type(offset) is not int or offset < 0:
        raise InventoryLookupError("invalid_offset", "offset must be a non-negative integer.")
    if type(limit) is not int or limit < 1 or limit > MAX_PAGE_SIZE:
        raise InventoryLookupError("invalid_limit", f"limit must be between 1 and {MAX_PAGE_SIZE}.")
    return offset, limit


def _validate_preview_limit(max_chars: int) -> int:
    if type(max_chars) is not int or max_chars < 1 or max_chars > MAX_PREVIEW_CHARS:
        raise InventoryLookupError(
            "invalid_preview_limit",
            f"max_chars must be between 1 and {MAX_PREVIEW_CHARS}.",
        )
    return max_chars


def _validate_lookup_id(value: str, *, label: str) -> None:
    if not isinstance(value, str) or SAFE_ID.fullmatch(value) is None:
        raise InventoryLookupError("invalid_id", f"{label} is invalid.")


def _json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("artifact must contain a JSON object")
    return value


def _object_list(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key)
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ValueError(f"manifest {key} must be a list of objects")
    return value


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"artifact field {key} must be a non-empty string")
    return value


def _required_safe_string(payload: dict[str, Any], key: str) -> str:
    value = _required_string(payload, key)
    if SAFE_ID.fullmatch(value) is None:
        raise ValueError(f"artifact field {key} is not a safe ID")
    return value


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _optional_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _optional_nonnegative_int(value: Any) -> int | None:
    return value if type(value) is int and value >= 0 else None


def _optional_positive_int(value: Any) -> int | None:
    return value if type(value) is int and value > 0 else None


def _looks_like_private_path(value: str) -> bool:
    return (
        Path(value).is_absolute()
        or value.startswith(("~", "file:"))
        or re.match(r"^[A-Za-z]:[\\/]", value) is not None
    )


def _safe_content_uri(value: str) -> str | None:
    if len(value) > MAX_CITATION_CHARS:
        return None
    database_match = SAFE_DATABASE_CITATION.fullmatch(value)
    if database_match is not None:
        document_id = unquote(database_match.group("document_id"))
        if document_id.strip() and quote(document_id, safe="") == database_match.group(
            "document_id"
        ):
            return value
        return None
    document_match = SAFE_DOCUMENT_CITATION.fullmatch(value)
    if document_match is not None:
        filename = unquote(document_match.group("filename"))
        if (
            filename not in {"", ".", ".."}
            and "/" not in filename
            and "\\" not in filename
            and quote(filename, safe="") == document_match.group("filename")
        ):
            return value
        return None
    try:
        parsed = urlsplit(value)
        if parsed.username is not None or parsed.password is not None or not parsed.netloc:
            return None
        if parsed.scheme in {"http", "https"}:
            return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    except ValueError:
        pass
    return None


def _parse_timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _bounded_text(value: str, max_chars: int) -> tuple[str, bool]:
    if len(value) <= max_chars:
        return value, False
    return value[:max_chars], True


def _record_selection_key(record: _PlanRecord) -> tuple[bool, datetime, str]:
    return (
        record.timestamp is not None,
        record.timestamp or datetime.min.replace(tzinfo=timezone.utc),
        record.candidate_id,
    )


def _record_sort_key(record: _PlanRecord) -> tuple[bool, float, str]:
    return (
        record.timestamp is None,
        -(record.timestamp.timestamp() if record.timestamp is not None else 0.0),
        record.summary.plan_id,
    )


def _replace_record_warnings(
    record: _PlanRecord, warnings: list[InventoryWarning]
) -> _PlanRecord:
    summary = PlanSummary(
        plan_id=record.summary.plan_id,
        namespace=record.summary.namespace,
        site_id=record.summary.site_id,
        created_at=record.summary.created_at,
        source=record.summary.source,
        page_count=record.summary.page_count,
        chunk_count=record.summary.chunk_count,
        diff=record.summary.diff,
        source_activity=record.summary.source_activity,
        warnings=warnings,
    )
    return _PlanRecord(
        summary=summary,
        namespace_candidate=record.namespace_candidate,
        artifact_hash=record.artifact_hash,
        retrieval=record.retrieval,
        source_activity=record.source_activity,
        originating_job_id=record.originating_job_id,
        pages=record.pages,
        chunks=record.chunks,
        directory=record.directory,
        timestamp=record.timestamp,
        candidate_id=record.candidate_id,
    )


def _artifact_id(root: Path, path: Path) -> str:
    try:
        relative = str(path.absolute().relative_to(root.absolute()))
    except ValueError:
        relative = path.name
    return "artifact_" + hashlib.sha256(relative.encode("utf-8")).hexdigest()[:16]


def _artifact_error(root: Path, path: Path, code: str, message: str) -> SafeError:
    return SafeError(code, message, _artifact_id(root, path))


def _safe_parse_message(exc: Exception) -> str:
    if isinstance(exc, json.JSONDecodeError):
        return "Local artifact contains invalid JSON."
    if isinstance(exc, (OSError, UnicodeError)):
        return "Local artifact could not be read."
    text = str(exc)
    if text.startswith(("artifact ", "manifest ", "plan ", "applied state ")):
        return text.rstrip(".") + "."
    return "Local artifact is malformed or incompatible."
