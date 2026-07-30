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
import math
import os
from pathlib import Path
import re
import stat
import threading
import time
from typing import Any, Callable, Literal
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from buoy_search.applied_state import AppliedStateError, load_applied_state_summary
from buoy_search.plan_validation import validate_plan_document

DEFAULT_ARTIFACTS_ROOT = Path("artifacts/site-crawls")
DEFAULT_STATE_ROOT = Path(".buoy")
PLAN_SCHEMA_VERSION = 2
MAX_PLAN_JSON_BYTES = 131_072
MAX_PAGE_SIZE = 100
MAX_PREVIEW_CHARS = 20_000
MAX_CITATION_CHARS = 2_000
MAX_FILTER_CHARS = 256
ARTIFACT_ERROR_SAMPLE_LIMIT = 20
SOURCE_KINDS = frozenset({"website", "github_repo", "document", "database", "unknown"})
LOCAL_STATUSES = frozenset({"planned", "applied", "pending_changes", "conflict", "error"})
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


class _LegacyPlan(ValueError):
    """Internal sentinel for inert unsupported plan artifacts."""


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
    payload_verification: Literal["not_checked"] = "not_checked"
    source_activity: SourceActivity = SourceActivity(None, None)
    warnings: list[InventoryWarning] = field(default_factory=list)


@dataclass(frozen=True)
class PlanDetail:
    summary: PlanSummary
    namespace_candidate: str
    artifact_hash: str
    retrieval: RetrievalSettings
    source_activity: SourceActivity
    originating_job_id: str | None
    payload_verification: Literal["verified"]
    applied_state_present: bool
    applied_state_hash: str


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
    plan_total: int
    plan_offset: int
    plan_limit: int
    plans_truncated: bool
    state: StateSummary | None
    retrieval: RetrievalSettings | None


@dataclass(frozen=True)
class PlanInventory:
    items: list[PlanSummary]
    total: int
    offset: int
    limit: int
    errors: list[SafeError]
    error_total: int = 0
    errors_truncated: bool = False


@dataclass(frozen=True)
class NamespaceInventory:
    items: list[NamespaceSummary]
    total: int
    offset: int
    limit: int
    errors: list[SafeError]
    error_total: int = 0
    errors_truncated: bool = False


@dataclass(frozen=True)
class ArtifactErrorInventory:
    items: list[SafeError]
    total: int
    offset: int
    limit: int


@dataclass(frozen=True)
class ChunkPreview:
    index: int
    action: str
    row_id: str
    title: str
    canonical_url: str
    section_path: str
    chunk_index: int
    content: str
    truncated: bool


@dataclass(frozen=True)
class ChunkInventory:
    items: list[ChunkPreview]
    total: int
    offset: int
    limit: int


@dataclass(frozen=True)
class StaleRowPreview:
    index: int
    category: str
    row_id: str
    canonical_url: str
    prior_status: str
    reason: str


@dataclass(frozen=True)
class StaleRowInventory:
    items: list[StaleRowPreview]
    total: int
    offset: int
    limit: int


@dataclass(frozen=True)
class PlanReview:
    detail: PlanDetail
    chunks: ChunkInventory
    stale_rows: StaleRowInventory


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
    artifact_errors_truncated: bool = False


@dataclass(frozen=True)
class _PlanRecord:
    summary: PlanSummary
    namespace_candidate: str
    artifact_hash: str
    retrieval: RetrievalSettings
    source_activity: SourceActivity
    originating_job_id: str | None
    plan_path: Path = field(repr=False)
    directory: Path = field(repr=False)
    directory_identity: tuple[int, int] = field(repr=False)
    plan_identity: tuple[int, int] = field(repr=False)
    delta_identity: tuple[int, int] = field(repr=False)
    timestamp: datetime | None = field(repr=False)
    candidate_id: str = field(repr=False)


@dataclass(frozen=True)
class _Snapshot:
    plans: list[_PlanRecord]
    states: list[StateSummary]
    errors: list[SafeError]
    error_namespaces: frozenset[str]


class LocalInventoryService:
    """Query local plans and applied state without side effects or remote imports."""

    def __init__(
        self,
        *,
        artifacts_root: Path = DEFAULT_ARTIFACTS_ROOT,
        state_root: Path = DEFAULT_STATE_ROOT,
        cache_ttl: float = 1.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if (
            isinstance(cache_ttl, bool)
            or not isinstance(cache_ttl, (int, float))
            or not math.isfinite(cache_ttl)
            or cache_ttl < 0.5
            or cache_ttl > 2.0
        ):
            raise ValueError("cache_ttl must be finite and between 0.5 and 2.0 seconds")
        self.artifacts_root = Path(artifacts_root)
        self.state_root = Path(state_root)
        self._cache_ttl = float(cache_ttl)
        self._clock = clock
        self._cache_lock = threading.Lock()
        self._cached_snapshot: _Snapshot | None = None
        self._cache_expires_at = 0.0

    def invalidate(self) -> None:
        """Clear this service's summary snapshot without failing its caller."""

        try:
            with self._cache_lock:
                self._cached_snapshot = None
                self._cache_expires_at = 0.0
        except Exception:
            return

    def list_plans(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        q: str | None = None,
        namespace: str | None = None,
        source_kind: str | None = None,
    ) -> PlanInventory:
        offset, limit = _validate_pagination(offset, limit)
        query = _validate_query_filter(q)
        if namespace is not None:
            _validate_filter_id(namespace, label="namespace")
        source_kind = _validate_choice_filter(
            source_kind, choices=SOURCE_KINDS, label="source_kind"
        )
        snapshot = self._snapshot()
        records = [
            record
            for record in snapshot.plans
            if _plan_matches_filters(
                record.summary,
                query=query,
                namespace=namespace,
                source_kind=source_kind,
            )
        ]
        items = [record.summary for record in records]
        error_sample = snapshot.errors[:ARTIFACT_ERROR_SAMPLE_LIMIT]
        return PlanInventory(
            items[offset : offset + limit],
            len(items),
            offset,
            limit,
            error_sample,
            len(snapshot.errors),
            len(error_sample) < len(snapshot.errors),
        )

    def list_artifact_errors(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        q: str | None = None,
    ) -> ArtifactErrorInventory:
        offset, limit = _validate_pagination(offset, limit)
        query = _validate_query_filter(q)
        errors = [
            error
            for error in self._snapshot().errors
            if query is None
            or query in error.code.casefold()
            or query in error.message.casefold()
            or query in error.artifact_id.casefold()
        ]
        return ArtifactErrorInventory(
            errors[offset : offset + limit], len(errors), offset, limit
        )

    def get_plan(self, plan_id: str) -> PlanDetail:
        record = self._plan_record(plan_id)
        try:
            verified = _verify_record(record, materialize=False)
        except (OSError, ValueError) as exc:
            raise InventoryLookupError(
                "plan_payload_invalid", "Plan delta could not be fully verified."
            ) from exc
        return _plan_detail(verified.plan, warnings=record.summary.warnings)

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
        try:
            verified = _verify_record(
                record, materialize=False, upsert_window=(offset, limit)
            )
        except (OSError, ValueError) as exc:
            raise InventoryLookupError(
                "plan_payload_invalid", "Plan delta could not be fully verified."
            ) from exc
        return _chunk_inventory(
            verified.plan,
            verified.upsert_rows,
            offset=offset,
            limit=limit,
            max_chars=max_chars,
        )

    def list_plan_stale_rows(
        self,
        plan_id: str,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> StaleRowInventory:
        offset, limit = _validate_pagination(offset, limit)
        record = self._plan_record(plan_id)
        try:
            verified = _verify_record(
                record, materialize=False, stale_window=(offset, limit)
            )
        except (OSError, ValueError) as exc:
            raise InventoryLookupError(
                "plan_payload_invalid", "Plan delta could not be fully verified."
            ) from exc
        return _stale_inventory(
            verified.plan,
            verified.stale_rows,
            offset=offset,
            limit=limit,
        )

    def get_plan_review(
        self,
        plan_id: str,
        *,
        chunk_offset: int = 0,
        chunk_limit: int = 10,
        max_chars: int = 2_000,
        stale_offset: int = 0,
        stale_limit: int = 10,
    ) -> PlanReview:
        chunk_offset, chunk_limit = _validate_pagination(chunk_offset, chunk_limit)
        stale_offset, stale_limit = _validate_pagination(stale_offset, stale_limit)
        max_chars = _validate_preview_limit(max_chars)
        record = self._plan_record(plan_id)
        try:
            verified = _verify_record(
                record,
                materialize=False,
                upsert_window=(chunk_offset, chunk_limit),
                stale_window=(stale_offset, stale_limit),
            )
        except (OSError, ValueError) as exc:
            raise InventoryLookupError(
                "plan_payload_invalid", "Plan delta could not be fully verified."
            ) from exc
        return PlanReview(
            detail=_plan_detail(verified.plan, warnings=record.summary.warnings),
            chunks=_chunk_inventory(
                verified.plan,
                verified.upsert_rows,
                offset=chunk_offset,
                limit=chunk_limit,
                max_chars=max_chars,
            ),
            stale_rows=_stale_inventory(
                verified.plan,
                verified.stale_rows,
                offset=stale_offset,
                limit=stale_limit,
            ),
        )

    def list_namespaces(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        q: str | None = None,
        source_kind: str | None = None,
        local_status: str | None = None,
    ) -> NamespaceInventory:
        offset, limit = _validate_pagination(offset, limit)
        query = _validate_query_filter(q)
        source_kind = _validate_choice_filter(
            source_kind, choices=SOURCE_KINDS, label="source_kind"
        )
        local_status = _validate_choice_filter(
            local_status, choices=LOCAL_STATUSES, label="local_status"
        )
        snapshot = self._snapshot()
        items = [
            item
            for item in _namespace_summaries(snapshot)
            if _namespace_matches_filters(
                item,
                query=query,
                source_kind=source_kind,
                local_status=local_status,
            )
        ]
        error_sample = snapshot.errors[:ARTIFACT_ERROR_SAMPLE_LIMIT]
        return NamespaceInventory(
            items[offset : offset + limit],
            len(items),
            offset,
            limit,
            error_sample,
            len(snapshot.errors),
            len(error_sample) < len(snapshot.errors),
        )

    def get_namespace(
        self,
        namespace: str,
        *,
        plan_offset: int = 0,
        plan_limit: int = 20,
    ) -> NamespaceDetail:
        _validate_lookup_id(namespace, label="namespace")
        plan_offset, plan_limit = _validate_pagination(plan_offset, plan_limit)
        snapshot = self._snapshot()
        summary = next(
            (item for item in _namespace_summaries(snapshot) if item.namespace == namespace),
            None,
        )
        if summary is None:
            snapshot = self._snapshot(force=True, previous=snapshot)
            summary = next(
                (item for item in _namespace_summaries(snapshot) if item.namespace == namespace),
                None,
            )
        if summary is None:
            raise InventoryLookupError("namespace_not_found", "Namespace was not found.")
        plans = [record for record in snapshot.plans if record.summary.namespace == namespace]
        matching_states = [item for item in snapshot.states if item.namespace == namespace]
        state = matching_states[0] if len(matching_states) == 1 else None
        selected_plans = plans[plan_offset : plan_offset + plan_limit]
        return NamespaceDetail(
            summary=summary,
            plans=[record.summary for record in selected_plans],
            plan_total=len(plans),
            plan_offset=plan_offset,
            plan_limit=plan_limit,
            plans_truncated=len(selected_plans) < len(plans),
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
            artifact_errors=snapshot.errors[:ARTIFACT_ERROR_SAMPLE_LIMIT],
            artifact_errors_truncated=(
                len(snapshot.errors) > ARTIFACT_ERROR_SAMPLE_LIMIT
            ),
        )

    def _plan_record(self, plan_id: str) -> _PlanRecord:
        _validate_lookup_id(plan_id, label="plan ID")
        snapshot = self._snapshot()
        record = next(
            (item for item in snapshot.plans if item.summary.plan_id == plan_id),
            None,
        )
        if record is None:
            snapshot = self._snapshot(force=True, previous=snapshot)
            record = next(
                (item for item in snapshot.plans if item.summary.plan_id == plan_id),
                None,
            )
        if record is None:
            raise InventoryLookupError("plan_not_found", "Plan was not found.")
        return record

    def _snapshot(
        self, *, force: bool = False, previous: _Snapshot | None = None
    ) -> _Snapshot:
        with self._cache_lock:
            rebuild_started_at = self._clock()
            cached = self._cached_snapshot
            if (
                force
                and previous is not None
                and cached is not None
                and cached is not previous
                and rebuild_started_at < self._cache_expires_at
            ):
                return cached
            if (
                not force
                and cached is not None
                and rebuild_started_at < self._cache_expires_at
            ):
                return cached
            plans, plan_errors = _discover_plans(self.artifacts_root)
            states, state_errors, error_namespaces = _discover_states(self.state_root)
            snapshot = _Snapshot(
                plans=plans,
                states=states,
                errors=sorted(
                    [*plan_errors, *state_errors],
                    key=lambda item: (item.code, item.artifact_id),
                ),
                error_namespaces=frozenset(error_namespaces),
            )
            self._cached_snapshot = snapshot
            self._cache_expires_at = rebuild_started_at + self._cache_ttl
            return snapshot


def _discover_plans(root: Path) -> tuple[list[_PlanRecord], list[SafeError]]:
    if not root.exists():
        return [], []
    if root.is_symlink() or not root.is_dir():
        return [], [SafeError("unsafe_artifacts_root", "Artifacts root must be a regular directory.", "artifacts_root")]
    records: list[_PlanRecord] = []
    errors: list[SafeError] = []
    for current, directories, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        has_plan = "plan.json" in files
        if has_plan:
            directories[:] = []
        else:
            safe_directories: list[str] = []
            for name in sorted(directories):
                child = current_path / name
                if child.is_symlink():
                    errors.append(_artifact_error(root, child, "unsafe_symlink", "Symlinked artifact directories are not inspected."))
                else:
                    safe_directories.append(name)
            directories[:] = safe_directories
        if not has_plan:
            continue
        plan_path = current_path / "plan.json"
        if plan_path.is_symlink():
            errors.append(_artifact_error(root, plan_path, "unsafe_symlink", "Symlinked plan artifacts are not inspected."))
            continue
        try:
            records.append(_read_plan(root, plan_path))
        except _LegacyPlan:
            continue
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
    directory_metadata = plan_path.parent.lstat()
    if stat.S_ISLNK(directory_metadata.st_mode) or not stat.S_ISDIR(directory_metadata.st_mode):
        raise ValueError("plan directory must be a regular directory")
    plan, plan_identity = _bounded_plan_object(plan_path)
    schema_version = plan.get("schema_version")
    if type(schema_version) is int and schema_version == 1:
        raise _LegacyPlan("unsupported schema-v1 plan")
    if type(schema_version) is not int or schema_version != PLAN_SCHEMA_VERSION:
        raise ValueError("unsupported plan schema version")
    validate_plan_document(plan)
    delta_path = plan_path.with_name("delta.duckdb")
    try:
        delta_metadata = delta_path.lstat()
    except OSError as exc:
        raise ValueError("delta.duckdb is missing") from exc
    if stat.S_ISLNK(delta_metadata.st_mode) or not stat.S_ISREG(delta_metadata.st_mode):
        raise ValueError("delta.duckdb must be a regular file")
    directory_after = plan_path.parent.lstat()
    if (
        not stat.S_ISDIR(directory_after.st_mode)
        or (directory_after.st_dev, directory_after.st_ino)
        != (directory_metadata.st_dev, directory_metadata.st_ino)
    ):
        raise ValueError("plan directory changed during summary qualification")

    (
        summary,
        namespace_candidate,
        artifact_hash,
        retrieval,
        activity,
        originating_job_id,
        timestamp,
    ) = _plan_response_fields(plan)
    return _PlanRecord(
        summary=summary,
        namespace_candidate=namespace_candidate,
        artifact_hash=artifact_hash,
        retrieval=retrieval,
        source_activity=activity,
        originating_job_id=originating_job_id,
        plan_path=plan_path,
        directory=plan_path.parent,
        directory_identity=(directory_metadata.st_dev, directory_metadata.st_ino),
        plan_identity=plan_identity,
        delta_identity=(delta_metadata.st_dev, delta_metadata.st_ino),
        timestamp=timestamp,
        candidate_id=_artifact_id(root, plan_path),
    )


def _plan_response_fields(
    plan: dict[str, Any], *, warnings: list[InventoryWarning] | None = None
) -> tuple[
    PlanSummary,
    str,
    str,
    RetrievalSettings,
    SourceActivity,
    str | None,
    datetime,
]:
    """Reconstruct every document-backed response field from verified metadata."""

    created_at = str(plan["created_at"])
    timestamp = _parse_timestamp(created_at)
    if timestamp is None:
        raise ValueError("plan created_at is invalid")
    diff = _diff_summary(plan["diff"])
    source = _source_from_plan(plan["source"])
    retrieval = _retrieval_settings_v2(plan)
    activity = _source_activity_v2(str(plan["source"]["kind"]))
    originating_job_id = plan.get("originating_job_id")
    if originating_job_id is not None:
        originating_job_id = str(originating_job_id)
    summary = PlanSummary(
        plan_id=str(plan["plan_id"]),
        namespace=str(plan["namespace"]),
        site_id=str(plan["site_id"]),
        created_at=created_at,
        source=source,
        page_count=sum(
            int(plan["diff"][key])
            for key in ("pages_added", "pages_changed", "pages_unchanged")
        ),
        chunk_count=int(plan["diff"]["chunks_unchanged"])
        + int(plan["diff"]["rows_to_upsert"]),
        diff=diff,
        payload_verification="not_checked",
        source_activity=activity,
        warnings=list(warnings or []),
    )
    return (
        summary,
        str(plan["namespace_candidate"]),
        str(plan["artifact_hash"]),
        retrieval,
        activity,
        originating_job_id,
        timestamp,
    )


def _verify_plan_artifacts(plan_path: Path, **kwargs: Any) -> Any:
    from buoy_search.plan_artifacts import verify_plan_artifacts

    return verify_plan_artifacts(plan_path, **kwargs)


def _verify_record(record: _PlanRecord, **kwargs: Any) -> Any:
    """Fully verify exactly the inventory record selected before payload access."""

    before = _record_path_observations(record)
    expected = (
        record.directory_identity,
        record.plan_identity,
        record.delta_identity,
    )
    if tuple(item[:2] for item in before) != expected:
        raise ValueError("selected plan artifacts changed before verification")
    selected_plan, selected_plan_observation = _bounded_plan_snapshot(record.plan_path)
    if selected_plan_observation != before[1]:
        raise ValueError("selected plan artifacts changed before verification")

    verified = _verify_plan_artifacts(record.plan_path, **kwargs)

    current_plan, current_plan_observation = _bounded_plan_snapshot(record.plan_path)
    after = _record_path_observations(record)
    if (
        str(verified.plan["plan_id"]) != record.summary.plan_id
        or str(verified.plan["artifact_hash"]) != record.artifact_hash
        or str(verified.plan["namespace"]) != record.summary.namespace
        or after != before
        or current_plan_observation != after[1]
        or verified.plan != selected_plan
        or current_plan != selected_plan
    ):
        raise ValueError("selected plan artifacts changed during verification")
    return verified


def _record_path_observations(
    record: _PlanRecord,
) -> tuple[
    tuple[int, int, int, int, int],
    tuple[int, int, int, int, int],
    tuple[int, int, int, int, int],
]:
    directory = record.directory.lstat()
    plan = record.plan_path.lstat()
    delta = record.plan_path.with_name("delta.duckdb").lstat()
    if (
        stat.S_ISLNK(directory.st_mode)
        or not stat.S_ISDIR(directory.st_mode)
        or stat.S_ISLNK(plan.st_mode)
        or not stat.S_ISREG(plan.st_mode)
        or stat.S_ISLNK(delta.st_mode)
        or not stat.S_ISREG(delta.st_mode)
    ):
        raise ValueError("selected plan artifacts are no longer regular files")
    return (
        _mutation_identity(directory),
        _mutation_identity(plan),
        _mutation_identity(delta),
    )


def _mutation_identity(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _bounded_plan_object(path: Path) -> tuple[dict[str, Any], tuple[int, int]]:
    value, observation = _bounded_plan_snapshot(path)
    return value, observation[:2]


def _bounded_plan_snapshot(
    path: Path,
) -> tuple[dict[str, Any], tuple[int, int, int, int, int]]:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_size > MAX_PLAN_JSON_BYTES:
            raise ValueError("plan.json is missing, unsafe, or exceeds the size limit")
        with os.fdopen(os.dup(descriptor), "r", encoding="utf-8") as handle:
            text = handle.read(MAX_PLAN_JSON_BYTES + 1)
        if len(text.encode("utf-8")) > MAX_PLAN_JSON_BYTES:
            raise ValueError("plan.json exceeds the size limit")
        opened_after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("plan.json must contain an object")
    current = path.lstat()
    observation = _mutation_identity(opened)
    if (
        _mutation_identity(opened_after) != observation
        or stat.S_ISLNK(current.st_mode)
        or not stat.S_ISREG(current.st_mode)
        or _mutation_identity(current) != observation
    ):
        raise ValueError("plan.json changed during summary qualification")
    return value, observation


def _discover_states(
    state_root: Path,
) -> tuple[list[StateSummary], list[SafeError], set[str]]:
    if state_root.is_symlink():
        return [], [SafeError("unsafe_state_root", "Applied-state root must not be a symlink.", "state_root")], set()
    state_dir = state_root / "state"
    if not state_dir.exists():
        return [], [], set()
    if state_dir.is_symlink() or not state_dir.is_dir():
        return [], [SafeError("unsafe_state_root", "Applied-state directory must be a regular directory.", "state_root")], set()
    try:
        trusted_root = state_root.resolve(strict=True)
        state_dir.resolve(strict=True).relative_to(trusted_root)
    except (OSError, ValueError):
        return [], [SafeError("unsafe_state_root", "Applied-state directory escapes its configured root.", "state_root")], set()
    states: list[StateSummary] = []
    errors: list[SafeError] = []
    error_namespaces: set[str] = set()
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
            namespace = _attributable_state_namespace(state_root, database_path)
            if namespace is not None:
                error_namespaces.add(namespace)
            continue
        try:
            database_path.resolve(strict=True).relative_to(trusted_root)
            state = load_applied_state_summary(
                database_path=database_path, state_root=state_root
            )
            source, _ = _map_source(state.base_url, state.site_id, [])
            states.append(StateSummary(
                namespace=state.namespace,
                site_id=state.site_id,
                source=source,
                updated_at=state.updated_at or None,
                last_plan_id=state.last_plan_id or None,
                last_apply_id=state.last_apply_id or None,
                active_rows=state.active_rows,
                retained_stale_rows=state.retained_stale_rows,
            ))
        except (AppliedStateError, OSError, ValueError) as exc:
            errors.append(SafeError("malformed_state", _safe_parse_message(exc), artifact_id))
            namespace = _attributable_state_namespace(state_root, database_path)
            if namespace is not None and not _state_summary_capability_error(exc):
                error_namespaces.add(namespace)
    states.sort(key=lambda item: item.namespace)
    return states, errors, error_namespaces


def _state_summary_capability_error(exc: Exception) -> bool:
    return str(exc) == "applied state safe summary descriptor primitives are unavailable"


def _attributable_state_namespace(state_root: Path, database_path: Path) -> str | None:
    try:
        relative = database_path.absolute().relative_to(state_root.absolute())
    except ValueError:
        return None
    if (
        len(relative.parts) != 4
        or relative.parts[0] != "state"
        or relative.parts[3] != "state.duckdb"
        or SAFE_ID.fullmatch(relative.parts[1]) is None
        or SAFE_ID.fullmatch(relative.parts[2]) is None
    ):
        return None
    return relative.parts[2]


def _namespace_summaries(snapshot: _Snapshot) -> list[NamespaceSummary]:
    plan_groups: dict[str, list[_PlanRecord]] = {}
    for plan in snapshot.plans:
        plan_groups.setdefault(plan.summary.namespace, []).append(plan)
    state_groups: dict[str, list[StateSummary]] = {}
    for state in snapshot.states:
        state_groups.setdefault(state.namespace, []).append(state)
    summaries: list[NamespaceSummary] = []
    for namespace in sorted(
        value
        for value in set(plan_groups) | set(state_groups) | set(snapshot.error_namespaces)
        if not value.startswith(("buoy-evidence-", "buoy-semantics-"))
    ):
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
        if namespace in snapshot.error_namespaces:
            local_status = "error"
        elif identity_conflict:
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


def _source_from_plan(value: object) -> SourceProvenance:
    if not isinstance(value, dict):
        raise ValueError("plan source is invalid")
    kind = str(value["kind"])
    uri = str(value["uri"])
    title = str(value["title"])
    attributes = value["attributes"]
    if not isinstance(attributes, dict):
        raise ValueError("plan source attributes are invalid")
    if kind == "website":
        return SourceProvenance(kind="website", uri=uri, title=title)
    if kind == "github_repo":
        return SourceProvenance(
            kind="github_repo",
            uri=uri,
            title=title,
            repository=str(attributes["repo_full_name"]),
        )
    if kind in {"local_file", "pdf"}:
        return SourceProvenance(
            kind="document", uri=uri, title=title, filename=str(attributes["filename"])
        )
    if kind in DATABASE_KINDS:
        return SourceProvenance(
            kind="database",
            uri=uri,
            title=title,
            database_backend=str(attributes["database_backend"]),
            database_source_id=str(attributes["database_source_id"]),
            database_relation=str(attributes["database_relation"]),
        )
    raise ValueError("plan source kind is unsupported")


def _retrieval_settings_v2(plan: dict[str, Any]) -> RetrievalSettings:
    options = plan.get("chunk_options")
    options = options if isinstance(options, dict) else {}
    return RetrievalSettings(
        embedding_model=str(plan["embedding_model"]),
        embedding_precision=str(plan["embedding_precision"]),
        ranking_mode=_optional_string(options.get("ranking_mode")),
        ranking_profile=_optional_string(options.get("ranking_profile")),
        ranking_pool=_optional_positive_int(options.get("ranking_pool")),
        ranking_aggregation=_optional_string(options.get("ranking_aggregation")),
        region=None,
    )


def _source_activity_v2(source_kind: str) -> SourceActivity:
    remote_database = source_kind in {"bigquery_relation", "snowflake_relation"}
    return SourceActivity(remote_database, remote_database)


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


def _plan_detail(
    plan: dict[str, Any], *, warnings: list[InventoryWarning]
) -> PlanDetail:
    (
        summary,
        namespace_candidate,
        artifact_hash,
        retrieval,
        source_activity,
        originating_job_id,
        _,
    ) = _plan_response_fields(plan, warnings=warnings)
    applied_state = plan["applied_state"]
    return PlanDetail(
        summary=summary,
        namespace_candidate=namespace_candidate,
        artifact_hash=artifact_hash,
        retrieval=retrieval,
        source_activity=source_activity,
        originating_job_id=originating_job_id,
        payload_verification="verified",
        applied_state_present=bool(applied_state["present"]),
        applied_state_hash=str(applied_state["hash"]),
    )


def _chunk_inventory(
    plan: dict[str, Any],
    rows: tuple[dict[str, Any], ...],
    *,
    offset: int,
    limit: int,
    max_chars: int,
) -> ChunkInventory:
    return ChunkInventory(
        [
            _chunk_preview(index, row, max_chars=max_chars)
            for index, row in enumerate(rows, start=offset)
        ],
        int(plan["delta"]["upsert_count"]),
        offset,
        limit,
    )


def _stale_inventory(
    plan: dict[str, Any],
    rows: tuple[dict[str, Any], ...],
    *,
    offset: int,
    limit: int,
) -> StaleRowInventory:
    return StaleRowInventory(
        [
            _stale_preview(index, row)
            for index, row in enumerate(rows, start=offset)
        ],
        int(plan["delta"]["stale_count"])
        + int(plan["delta"]["retained_stale_count"]),
        offset,
        limit,
    )


def _plan_matches_filters(
    summary: PlanSummary,
    *,
    query: str | None,
    namespace: str | None,
    source_kind: str | None,
) -> bool:
    if namespace is not None and summary.namespace != namespace:
        return False
    if source_kind is not None and summary.source.kind != source_kind:
        return False
    if query is None:
        return True
    return any(
        query in value.casefold()
        for value in (
            summary.plan_id,
            summary.namespace,
            summary.source.title or "",
            summary.source.uri or "",
        )
    )


def _namespace_matches_filters(
    summary: NamespaceSummary,
    *,
    query: str | None,
    source_kind: str | None,
    local_status: str | None,
) -> bool:
    return (
        (query is None or query in summary.namespace.casefold())
        and (
            source_kind is None
            or (summary.source.kind if summary.source is not None else "unknown")
            == source_kind
        )
        and (local_status is None or summary.local_status == local_status)
    )


def _chunk_preview(index: int, chunk: dict[str, Any], *, max_chars: int) -> ChunkPreview:
    content, truncated = _bounded_text(str(chunk["content"]), max_chars)
    return ChunkPreview(
        index=index,
        action=str(chunk["action"]),
        row_id=str(chunk["row_id"]),
        title=str(chunk.get("title", "")),
        canonical_url=_safe_content_uri(str(chunk["canonical_url"])) or "",
        section_path=str(chunk.get("section_path", "")),
        chunk_index=int(chunk["chunk_index"]),
        content=content,
        truncated=truncated,
    )


def _stale_preview(index: int, row: dict[str, Any]) -> StaleRowPreview:
    return StaleRowPreview(
        index=index,
        category=str(row["category"]),
        row_id=str(row["row_id"]),
        canonical_url=_safe_content_uri(str(row["canonical_url"])) or "",
        prior_status=str(row["prior_status"]),
        reason=str(row["reason"]),
    )


def _validate_query_filter(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > MAX_FILTER_CHARS:
        raise InventoryLookupError(
            "invalid_request", f"q must contain at most {MAX_FILTER_CHARS} characters."
        )
    return value.casefold()


def _validate_filter_id(value: str, *, label: str) -> None:
    if not isinstance(value, str) or SAFE_ID.fullmatch(value) is None:
        raise InventoryLookupError("invalid_request", f"{label} is invalid.")


def _validate_choice_filter(
    value: str | None, *, choices: frozenset[str], label: str
) -> str | None:
    if value is not None and value not in choices:
        raise InventoryLookupError(
            "invalid_request", f"{label} is not a supported filter value."
        )
    return value


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
        payload_verification="not_checked",
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
        plan_path=record.plan_path,
        directory=record.directory,
        directory_identity=record.directory_identity,
        plan_identity=record.plan_identity,
        delta_identity=record.delta_identity,
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
