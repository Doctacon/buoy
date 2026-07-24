"""Durable, local-only execution for managed public-source plan jobs."""

from __future__ import annotations

from concurrent.futures import Executor, Future, ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import errno
import heapq
import json
import logging
import os
from pathlib import Path, PurePosixPath
import re
import stat
from threading import Condition, Event, RLock
import time
from typing import TYPE_CHECKING, Any, Callable, Iterator, Literal, Mapping

import portalocker
from urllib.parse import urlunsplit
from uuid import uuid4

from buoy_search.source_url import validate_http_url_authority

if TYPE_CHECKING:
    from buoy_search.planning_service import (
        ManagedPublicPlanningRequest,
        PlanProgress,
        PlanningService,
    )

JOB_SCHEMA_VERSION = 1
MAX_MANAGED_SOURCE_URL_LENGTH = 2_048
MAX_PROGRESS_STAGE_LENGTH = 64
MAX_PROGRESS_MESSAGE_LENGTH = 500
MAX_EVENT_REPLAY_SIZE = 1_000
MAX_JOB_LIST_OFFSET = 1_000
MAX_DURABLE_EVENTS_PER_JOB = 5_000
MAX_EVENT_LINE_BYTES = 8 * 1024
COALESCED_PROGRESS_MESSAGE = (
    "Additional progress updates are being coalesced while planning continues."
)
_LOGGER = logging.getLogger(__name__)
_LOGGER.addHandler(logging.NullHandler())
JobState = Literal["queued", "running", "succeeded", "failed", "interrupted"]
JobStage = Literal[
    "queued",
    "validation",
    "source-acquisition",
    "source-discovery",
    "crawl",
    "clone",
    "processing",
    "chunk",
    "artifact",
    "diff",
    "write",
    "succeeded",
    "failed",
    "interrupted",
]
SourceKind = Literal["website", "github_repo"]

ACTIVE_STATES = frozenset({"queued", "running"})
TERMINAL_STATES = frozenset({"succeeded", "failed", "interrupted"})
ALLOWED_TRANSITIONS: Mapping[JobState, frozenset[JobState]] = {
    "queued": frozenset({"running", "failed"}),
    "running": frozenset({"succeeded", "failed", "interrupted"}),
    "succeeded": frozenset(),
    "failed": frozenset(),
    "interrupted": frozenset(),
}
_SAFE_JOB_ID = re.compile(r"planjob_[0-9a-f]{32}")
_SAFE_CODE = re.compile(r"[a-z][a-z0-9_]{0,63}")
_SAFE_COUNT_KEY = re.compile(r"[a-z][a-z0-9_]{0,63}")
_SAFE_COUNT_KEYS = frozenset(
    {
        "cap",
        "chunks",
        "documents",
        "errors",
        "files",
        "pages",
        "queued",
        "requests",
        "rows",
        "sitemap",
    }
)
_STAGE_VALUES = frozenset(
    {
        "queued",
        "validation",
        "source-acquisition",
        "source-discovery",
        "crawl",
        "clone",
        "processing",
        "chunk",
        "artifact",
        "diff",
        "write",
        "succeeded",
        "failed",
        "interrupted",
    }
)
_JOB_FIELDS = frozenset(
    {
        "schema_version",
        "job_id",
        "operation",
        "actor",
        "state",
        "source_kind",
        "source_url",
        "namespace",
        "artifact_path",
        "plan_id",
        "created_at",
        "updated_at",
        "event_sequence",
        "started_at",
        "completed_at",
        "latest_progress",
        "error",
        "request_summary",
    }
)
_EVENT_FIELDS = frozenset({"sequence", "timestamp", "stage", "message", "counts"})
_REQUEST_SUMMARY_FIELDS = frozenset(
    {
        "max_pages_or_files",
        "max_chunks",
        "namespace",
        "include_path_count",
        "exclude_path_count",
    }
)


class PlanJobError(ValueError):
    """Base class for safe durable job failures."""


class JobNotFoundError(PlanJobError):
    """Raised when a job ID has no durable record."""


class ManagedPlanningUnsupportedError(PlanJobError):
    """Raised only when required managed-planning platform primitives are absent."""


class JobIntegrityError(PlanJobError):
    """Raised when a durable job record or event log is malformed or unsafe."""


class JobDurabilityError(JobIntegrityError):
    """Raised when a required durable filesystem commit fails."""


class InvalidJobTransitionError(PlanJobError):
    """Raised when a state transition is outside the ratified state machine."""


class ServiceOwnershipError(PlanJobError):
    """Raised when another live service owns the command-center worker."""


class ActiveJobConflict(PlanJobError):
    """Raised when another queued or running job already owns the worker."""

    def __init__(self, active_job_id: str) -> None:
        self.active_job_id = active_job_id
        super().__init__("Another plan job is already active.")


@dataclass(frozen=True)
class PlanJobRequest:
    """Credential-free input accepted by the managed plan-job service."""

    source_url: str
    max_pages_or_files: int | None = None
    max_chunks: int | None = None
    namespace: str | None = None
    include_paths: tuple[str, ...] = ()
    exclude_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class JobRequestSummary:
    max_pages_or_files: int | None
    max_chunks: int | None
    namespace: str | None
    include_path_count: int
    exclude_path_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "max_pages_or_files": self.max_pages_or_files,
            "max_chunks": self.max_chunks,
            "namespace": self.namespace,
            "include_path_count": self.include_path_count,
            "exclude_path_count": self.exclude_path_count,
        }


@dataclass(frozen=True)
class JobProgress:
    stage: JobStage
    message: str
    counts: dict[str, int]

    def to_dict(self) -> dict[str, object]:
        return {"stage": self.stage, "message": self.message, "counts": dict(self.counts)}


@dataclass(frozen=True)
class SafeJobError:
    code: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


@dataclass(frozen=True)
class PlanJobEvent:
    sequence: int
    timestamp: str
    stage: JobStage
    message: str
    counts: dict[str, int]

    def to_dict(self) -> dict[str, object]:
        return {
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "stage": self.stage,
            "message": self.message,
            "counts": dict(self.counts),
        }


@dataclass(frozen=True)
class _EventScan:
    events: list[PlanJobEvent]
    count: int
    latest: PlanJobEvent | None
    complete_length: int
    total_length: int


@dataclass(frozen=True)
class PlanJob:
    schema_version: int
    job_id: str
    operation: Literal["plan"]
    actor: Literal["local-operator"]
    state: JobState
    source_kind: SourceKind
    source_url: str
    namespace: str | None
    artifact_path: str
    plan_id: str | None
    created_at: str
    updated_at: str
    event_sequence: int
    started_at: str | None
    completed_at: str | None
    latest_progress: JobProgress
    error: SafeJobError | None
    request_summary: JobRequestSummary

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "job_id": self.job_id,
            "operation": self.operation,
            "actor": self.actor,
            "state": self.state,
            "source_kind": self.source_kind,
            "source_url": self.source_url,
            "namespace": self.namespace,
            "artifact_path": self.artifact_path,
            "plan_id": self.plan_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "event_sequence": self.event_sequence,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "latest_progress": self.latest_progress.to_dict(),
            "error": self.error.to_dict() if self.error is not None else None,
            "request_summary": self.request_summary.to_dict(),
        }


Clock = Callable[[], str]
JobIdFactory = Callable[[], str]
FaultInjector = Callable[[str], None]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def make_job_id() -> str:
    return f"planjob_{uuid4().hex}"


class PlanJobStore:
    """Atomic JSON job records paired with durable append-only JSONL events."""

    def __init__(
        self,
        state_root: Path,
        *,
        clock: Clock = utc_now,
        fault_injector: FaultInjector | None = None,
    ) -> None:
        self.state_root = Path(state_root)
        self.jobs_root = self.state_root / "command-center" / "jobs"
        self._clock = clock
        self._fault_injector = fault_injector
        self._lock = RLock()
        _require_safe_filesystem_primitives()
        self._jobs_directory_identities = self._ensure_jobs_root()

    def create(
        self,
        *,
        job_id: str,
        source_kind: SourceKind,
        source_url: str,
        namespace: str | None,
        artifact_path: str,
        request_summary: JobRequestSummary,
    ) -> PlanJob:
        _validate_job_id(job_id)
        _validate_relative_path(artifact_path)
        with self._lock, self._mutation_lock():
            active = self._active_job_locked()
            if active is not None:
                raise ActiveJobConflict(active.job_id)
            now = self._clock()
            progress = JobProgress("queued", "Plan job queued.", {})
            job = PlanJob(
                schema_version=JOB_SCHEMA_VERSION,
                job_id=job_id,
                operation="plan",
                actor="local-operator",
                state="queued",
                source_kind=source_kind,
                source_url=_safe_persisted_url(source_url),
                namespace=_safe_optional_text(namespace),
                artifact_path=artifact_path,
                plan_id=None,
                created_at=now,
                updated_at=now,
                event_sequence=1,
                started_at=None,
                completed_at=None,
                latest_progress=progress,
                error=None,
                request_summary=request_summary,
            )
            _validate_job(job)
            # Record-first commits ensure an event can never durably get ahead of
            # the authoritative record. A missing final event is reconstructed on read.
            self._atomic_write_record(job, exclusive=True)
            self._append_event(
                job_id,
                PlanJobEvent(1, now, progress.stage, progress.message, progress.counts),
            )
            return job

    def get(self, job_id: str) -> PlanJob:
        _validate_job_id(job_id)
        with self._lock, self._mutation_lock():
            return self._get_locked(job_id)

    def _get_locked(self, job_id: str) -> PlanJob:
        job = self._read_record(job_id)
        self._reconcile_record_events(job)
        return job

    def list(self) -> list[PlanJob]:
        with self._lock, self._mutation_lock():
            return self._list_locked()

    def list_window(self, *, offset: int, limit: int) -> tuple[list[PlanJob], int]:
        if type(offset) is not int or offset < 0 or offset > MAX_JOB_LIST_OFFSET:
            raise ValueError(
                f"offset must be between 0 and {MAX_JOB_LIST_OFFSET}"
            )
        if type(limit) is not int or limit < 1 or limit > MAX_EVENT_REPLAY_SIZE:
            raise ValueError(f"limit must be between 1 and {MAX_EVENT_REPLAY_SIZE}")
        with self._lock, self._mutation_lock():
            candidates, total = self._select_record_window(
                offset=offset, limit=limit
            )
            selected = [
                self._read_record(
                    job_id,
                    expected_identity=(device, inode),
                )
                for _mtime_ns, job_id, device, inode in candidates
            ]
            for job in selected:
                self._reconcile_record_events(job)
            return selected, total

    def _select_record_window(
        self, *, offset: int, limit: int
    ) -> tuple[list[tuple[int, str, int, int]], int]:
        retained, total = self._scan_record_metadata(retain_count=offset + limit)
        return retained[offset:], total

    def _scan_record_metadata(
        self, *, retain_count: int | None
    ) -> tuple[list[tuple[int, str, int, int]], int]:
        retained: list[tuple[int, str, int, int]] = []
        total = 0
        directory_fd = self._open_jobs_directory()
        try:
            with os.scandir(directory_fd) as entries:
                for entry in entries:
                    name = entry.name
                    if not name.startswith("planjob_") or not name.endswith(".json"):
                        continue
                    job_id = _validate_job_id(name[:-5])
                    metadata = entry.stat(follow_symlinks=False)
                    _validate_private_regular_file(metadata, label="record")
                    total += 1
                    candidate = (
                        metadata.st_mtime_ns,
                        job_id,
                        metadata.st_dev,
                        metadata.st_ino,
                    )
                    if retain_count is None:
                        retained.append(candidate)
                    elif len(retained) < retain_count:
                        heapq.heappush(retained, candidate)
                    elif candidate[:2] > retained[0][:2]:
                        heapq.heapreplace(retained, candidate)
        except OSError as exc:
            raise JobIntegrityError(
                "Plan-job records could not be enumerated safely."
            ) from exc
        finally:
            os.close(directory_fd)
        retained.sort(reverse=True)
        return retained, total

    def _list_locked(self) -> list[PlanJob]:
        candidates, _total = self._scan_record_metadata(retain_count=None)
        jobs = [
            self._read_record(job_id, expected_identity=(device, inode))
            for _mtime_ns, job_id, device, inode in candidates
        ]
        for job in jobs:
            self._reconcile_record_events(job)
        return jobs

    def active_job(self) -> PlanJob | None:
        with self._lock, self._mutation_lock():
            return self._active_job_locked()

    def _active_job_locked(self) -> PlanJob | None:
        active = [job for job in self._list_locked() if job.state in ACTIVE_STATES]
        if len(active) > 1:
            raise JobIntegrityError("Multiple active plan-job records were found.")
        return active[0] if active else None

    def transition(
        self,
        job_id: str,
        state: JobState,
        *,
        plan_id: str | None = None,
        namespace: str | None = None,
        error: SafeJobError | None = None,
    ) -> PlanJob:
        with self._lock, self._mutation_lock():
            return self._transition_locked(
                job_id, state, plan_id=plan_id, namespace=namespace, error=error
            )

    def _transition_locked(
        self,
        job_id: str,
        state: JobState,
        *,
        plan_id: str | None = None,
        namespace: str | None = None,
        error: SafeJobError | None = None,
    ) -> PlanJob:
        current = self._get_locked(job_id)
        if state not in ALLOWED_TRANSITIONS[current.state]:
            raise InvalidJobTransitionError(
                f"Plan job cannot transition from {current.state} to {state}."
            )
        now = self._clock()
        if state == "succeeded":
            if not isinstance(plan_id, str) or not plan_id.strip() or error is not None:
                raise InvalidJobTransitionError(
                    "A succeeded plan job requires a verified plan ID and no error."
                )
            progress = JobProgress("succeeded", "Plan artifacts verified successfully.", {})
            safe_plan_id = _safe_identifier(plan_id, label="plan ID")
        elif state == "failed":
            if plan_id is not None or error is None:
                raise InvalidJobTransitionError(
                    "A failed plan job requires a safe error and no plan ID."
                )
            progress = JobProgress("failed", error.message, {})
            safe_plan_id = None
        elif state == "interrupted":
            if plan_id is not None:
                raise InvalidJobTransitionError(
                    "An interrupted plan job cannot have a plan ID."
                )
            error = error or SafeJobError(
                "job_interrupted",
                "Planning was interrupted by a local service restart.",
            )
            progress = JobProgress("interrupted", error.message, {})
            safe_plan_id = None
        else:
            if plan_id is not None or error is not None:
                raise InvalidJobTransitionError(
                    "A non-terminal plan job cannot have a plan ID or error."
                )
            progress = JobProgress(
                "validation",
                "Plan request validated; planning started.",
                {},
            )
            safe_plan_id = None
        safe_error = _validate_safe_error(error) if error is not None else None
        sequence = current.event_sequence + 1
        event = PlanJobEvent(
            sequence, now, progress.stage, progress.message, progress.counts
        )
        terminal = state in TERMINAL_STATES
        updated = replace(
            current,
            state=state,
            namespace=(
                _safe_optional_text(namespace)
                if namespace is not None
                else current.namespace
            ),
            plan_id=safe_plan_id,
            updated_at=now,
            event_sequence=sequence,
            started_at=now if state == "running" else current.started_at,
            completed_at=now if terminal else None,
            latest_progress=progress,
            error=safe_error,
        )
        _validate_job(updated)
        self._atomic_write_record(updated)
        self._append_event(job_id, event)
        return updated

    def record_progress(self, job_id: str, progress: PlanProgress) -> PlanJob | None:
        """Persist bounded progress, returning ``None`` when the callback is coalesced."""

        with self._lock, self._mutation_lock():
            current = self._get_locked(job_id)
            if current.state != "running":
                raise InvalidJobTransitionError(
                    "Progress can be recorded only while a plan job is running."
                )
            if current.event_sequence >= MAX_DURABLE_EVENTS_PER_JOB - 1:
                return None
            safe_progress = (
                JobProgress("processing", COALESCED_PROGRESS_MESSAGE, {})
                if current.event_sequence == MAX_DURABLE_EVENTS_PER_JOB - 2
                else progress_from_service(progress)
            )
            now = self._clock()
            sequence = current.event_sequence + 1
            event = PlanJobEvent(
                sequence,
                now,
                safe_progress.stage,
                safe_progress.message,
                safe_progress.counts,
            )
            updated = replace(
                current,
                updated_at=now,
                event_sequence=sequence,
                latest_progress=safe_progress,
            )
            _validate_job(updated)
            self._atomic_write_record(updated)
            self._append_event(job_id, event)
            return updated

    def events_after(
        self,
        job_id: str,
        after_sequence: int = 0,
        *,
        limit: int = MAX_EVENT_REPLAY_SIZE,
    ) -> list[PlanJobEvent]:
        _validate_job_id(job_id)
        if type(after_sequence) is not int or after_sequence < 0:
            raise ValueError("after_sequence must be a non-negative integer")
        if type(limit) is not int or limit < 1 or limit > MAX_EVENT_REPLAY_SIZE:
            raise ValueError(f"limit must be between 1 and {MAX_EVENT_REPLAY_SIZE}")
        with self._lock, self._mutation_lock():
            job = self._read_record(job_id)
            return self._reconcile_record_events(
                job, after_sequence=after_sequence, limit=limit
            )

    def interrupt_active_jobs(self) -> list[PlanJob]:
        """Apply the startup-only queued/running-to-interrupted recovery rule."""

        interrupted: list[PlanJob] = []
        with self._lock, self._mutation_lock():
            active = [job for job in self._list_locked() if job.state in ACTIVE_STATES]
            for job in active:
                if job.state == "running":
                    interrupted.append(self._transition_locked(job.job_id, "interrupted"))
                    continue
                now = self._clock()
                error = SafeJobError(
                    "job_interrupted",
                    "Planning was interrupted by a local service restart.",
                )
                progress = JobProgress("interrupted", error.message, {})
                sequence = job.event_sequence + 1
                event = PlanJobEvent(
                    sequence,
                    now,
                    progress.stage,
                    progress.message,
                    progress.counts,
                )
                updated = replace(
                    job,
                    state="interrupted",
                    updated_at=now,
                    event_sequence=sequence,
                    completed_at=now,
                    latest_progress=progress,
                    error=error,
                )
                _validate_job(updated)
                self._atomic_write_record(updated)
                self._append_event(job.job_id, event)
                interrupted.append(updated)
        return interrupted

    def _record_path(self, job_id: str) -> Path:
        return self.jobs_root / f"{job_id}.json"

    def _events_path(self, job_id: str) -> Path:
        return self.jobs_root / f"{job_id}.events.jsonl"

    def _read_record(
        self,
        job_id: str,
        *,
        expected_identity: tuple[int, int] | None = None,
    ) -> PlanJob:
        name = f"{job_id}.json"
        try:
            data = self._safe_read_named(
                name,
                label="record",
                expected_identity=expected_identity,
            )
            payload = json.loads(data.decode("utf-8"))
        except JobNotFoundError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise JobIntegrityError("Plan-job record is unreadable or malformed.") from exc
        job = _job_from_dict(payload)
        if job.job_id != job_id:
            raise JobIntegrityError("Plan-job record identity does not match its filename.")
        return job

    def _safe_read_named(
        self,
        name: str,
        *,
        label: str,
        expected_identity: tuple[int, int] | None = None,
    ) -> bytes:
        directory_fd = self._open_jobs_directory()
        try:
            try:
                fd = os.open(
                    name,
                    os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
                    dir_fd=directory_fd,
                )
            except FileNotFoundError as exc:
                if label == "record":
                    raise JobNotFoundError("Plan job was not found.") from exc
                raise JobIntegrityError("Plan-job event log is missing.") from exc
            try:
                opened = os.fstat(fd)
                _validate_private_regular_file(opened, label=label)
                if expected_identity is not None and (
                    opened.st_dev,
                    opened.st_ino,
                ) != expected_identity:
                    raise JobIntegrityError(
                        f"Plan-job {label} changed after list selection."
                    )
                chunks: list[bytes] = []
                while True:
                    chunk = os.read(fd, 64 * 1024)
                    if not chunk:
                        break
                    chunks.append(chunk)
                current = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                if (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino):
                    raise JobIntegrityError(f"Plan-job {label} was replaced while being read.")
                _validate_private_regular_file(current, label=label)
                return b"".join(chunks)
            finally:
                os.close(fd)
        except OSError as exc:
            raise JobIntegrityError(f"Plan-job {label} could not be opened safely.") from exc
        finally:
            os.close(directory_fd)

    def _scan_event_data(
        self,
        job_id: str,
        *,
        after_sequence: int,
        limit: int,
        allow_missing: bool = False,
        allow_partial: bool = False,
    ) -> _EventScan:
        name = f"{job_id}.events.jsonl"
        directory_fd = self._open_jobs_directory()
        try:
            try:
                fd = os.open(
                    name,
                    os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
                    dir_fd=directory_fd,
                )
            except FileNotFoundError as exc:
                if allow_missing:
                    return _EventScan([], 0, None, 0, 0)
                raise JobIntegrityError("Plan-job event log is missing.") from exc
            try:
                opened = os.fstat(fd)
                if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
                    raise JobIntegrityError("Plan-job event log is not a private regular file.")
                selected: list[PlanJobEvent] = []
                latest: PlanJobEvent | None = None
                count = 0
                complete_length = 0
                total_length = 0
                buffered = bytearray()
                while True:
                    chunk = os.read(fd, 64 * 1024)
                    if not chunk:
                        break
                    total_length += len(chunk)
                    buffered.extend(chunk)
                    while True:
                        newline = buffered.find(b"\n")
                        if newline < 0:
                            break
                        line = bytes(buffered[:newline])
                        del buffered[: newline + 1]
                        complete_length += newline + 1
                        if not line or len(line) > MAX_EVENT_LINE_BYTES:
                            raise JobIntegrityError("Plan-job event log is malformed.")
                        try:
                            event = _event_from_dict(json.loads(line.decode("utf-8")))
                        except (UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
                            raise JobIntegrityError("Plan-job event log is malformed.") from exc
                        count += 1
                        if event.sequence != count:
                            raise JobIntegrityError("Plan-job event sequence is not contiguous.")
                        latest = event
                        if event.sequence > after_sequence and len(selected) < limit:
                            selected.append(event)
                    if len(buffered) > MAX_EVENT_LINE_BYTES:
                        raise JobIntegrityError("Plan-job event log is malformed.")
                if buffered and not allow_partial:
                    raise JobIntegrityError("Plan-job event log has an incomplete final event.")
                current = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                if (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino):
                    raise JobIntegrityError("Plan-job event log was replaced while being read.")
                return _EventScan(
                    selected, count, latest, complete_length, total_length
                )
            finally:
                os.close(fd)
        except OSError as exc:
            raise JobIntegrityError("Plan-job event log could not be opened safely.") from exc
        finally:
            os.close(directory_fd)

    def _read_event_tail(self, job_id: str) -> _EventScan:
        name = f"{job_id}.events.jsonl"
        directory_fd = self._open_jobs_directory()
        try:
            try:
                fd = os.open(
                    name,
                    os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
                    dir_fd=directory_fd,
                )
            except FileNotFoundError:
                return _EventScan([], 0, None, 0, 0)
            try:
                opened = os.fstat(fd)
                if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
                    raise JobIntegrityError("Plan-job event log is not a private regular file.")
                total_length = opened.st_size
                window = 2 * (MAX_EVENT_LINE_BYTES + 1)
                offset = max(0, total_length - window)
                os.lseek(fd, offset, os.SEEK_SET)
                data = os.read(fd, total_length - offset)
                if len(data) != total_length - offset:
                    raise JobIntegrityError("Plan-job event log could not be read safely.")
                if offset:
                    boundary = data.find(b"\n")
                    if boundary < 0:
                        raise JobIntegrityError("Plan-job event log is malformed.")
                    data = data[boundary + 1 :]
                trailing_newline = data.endswith(b"\n")
                parts = data.split(b"\n")
                partial = b"" if trailing_newline else parts.pop()
                if trailing_newline:
                    parts.pop()
                if len(partial) > MAX_EVENT_LINE_BYTES:
                    raise JobIntegrityError("Plan-job event log is malformed.")
                parsed: list[PlanJobEvent] = []
                for line in parts:
                    if not line or len(line) > MAX_EVENT_LINE_BYTES:
                        raise JobIntegrityError("Plan-job event log is malformed.")
                    try:
                        parsed.append(
                            _event_from_dict(json.loads(line.decode("utf-8")))
                        )
                    except (UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
                        raise JobIntegrityError("Plan-job event log is malformed.") from exc
                if any(
                    current.sequence != previous.sequence + 1
                    for previous, current in zip(parsed, parsed[1:])
                ):
                    raise JobIntegrityError("Plan-job event sequence is not contiguous.")
                current = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                if (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino):
                    raise JobIntegrityError("Plan-job event log was replaced while being read.")
                latest = parsed[-1] if parsed else None
                return _EventScan(
                    [],
                    latest.sequence if latest is not None else 0,
                    latest,
                    total_length - len(partial),
                    total_length,
                )
            finally:
                os.close(fd)
        except OSError as exc:
            raise JobIntegrityError("Plan-job event log could not be opened safely.") from exc
        finally:
            os.close(directory_fd)

    def _reconcile_record_events(
        self,
        job: PlanJob,
        *,
        after_sequence: int = 0,
        limit: int = 0,
    ) -> list[PlanJobEvent]:
        scan = (
            self._read_event_tail(job.job_id)
            if limit == 0
            else self._scan_event_data(
                job.job_id,
                after_sequence=after_sequence,
                limit=limit,
                allow_missing=True,
                allow_partial=True,
            )
        )
        if scan.count == job.event_sequence:
            if scan.complete_length != scan.total_length:
                raise JobIntegrityError("Plan-job event log has data beyond the committed event.")
            self._validate_latest_event(job, scan.latest)
            return scan.events
        if scan.count != job.event_sequence - 1:
            raise JobIntegrityError("Plan-job record and event sequence are inconsistent.")
        if scan.complete_length != scan.total_length:
            self._truncate_event_log(job.job_id, scan.complete_length)
        progress = job.latest_progress
        repaired = PlanJobEvent(
            job.event_sequence,
            job.updated_at,
            progress.stage,
            progress.message,
            progress.counts,
        )
        self._append_event(job.job_id, repaired)
        self._validate_latest_event(job, repaired)
        if repaired.sequence > after_sequence and len(scan.events) < limit:
            scan.events.append(repaired)
        return scan.events

    def _truncate_event_log(self, job_id: str, length: int) -> None:
        directory_fd = self._open_jobs_directory()
        try:
            fd = os.open(
                f"{job_id}.events.jsonl",
                os.O_WRONLY | os.O_NOFOLLOW,
                dir_fd=directory_fd,
            )
            try:
                opened = os.fstat(fd)
                if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
                    raise JobIntegrityError("Plan-job event log is not a private regular file.")
                os.ftruncate(fd, length)
                os.fsync(fd)
            finally:
                os.close(fd)
            _fsync_directory(directory_fd)
        except OSError as exc:
            raise JobDurabilityError("Plan-job event log could not be reconciled.") from exc
        finally:
            os.close(directory_fd)

    def _validate_latest_event(
        self, job: PlanJob, latest: PlanJobEvent | None
    ) -> None:
        if latest is None or latest.sequence != job.event_sequence:
            raise JobIntegrityError("Plan-job record and event sequence are inconsistent.")
        if (
            latest.timestamp != job.updated_at
            or latest.stage != job.latest_progress.stage
            or latest.message != job.latest_progress.message
            or latest.counts != job.latest_progress.counts
        ):
            raise JobIntegrityError("Plan-job record and event log are inconsistent.")

    def _atomic_write_record(self, job: PlanJob, *, exclusive: bool = False) -> None:
        data = (json.dumps(job.to_dict(), indent=2, sort_keys=True) + "\n").encode("utf-8")
        temporary_name = f".{job.job_id}.{os.getpid()}.{uuid4().hex}.tmp"
        directory_fd = self._open_jobs_directory()
        try:
            fd = os.open(
                temporary_name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=directory_fd,
            )
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            self._inject_fault("record-temp-fsync")
            if exclusive:
                try:
                    os.link(
                        temporary_name,
                        f"{job.job_id}.json",
                        src_dir_fd=directory_fd,
                        dst_dir_fd=directory_fd,
                        follow_symlinks=False,
                    )
                except FileExistsError as exc:
                    raise JobIntegrityError("Plan-job ID collided with an existing record.") from exc
                os.unlink(temporary_name, dir_fd=directory_fd)
            else:
                os.replace(
                    temporary_name,
                    f"{job.job_id}.json",
                    src_dir_fd=directory_fd,
                    dst_dir_fd=directory_fd,
                )
            self._inject_fault("record-replace")
            _fsync_directory(directory_fd)
            self._inject_fault("record-directory-fsync")
        except OSError as exc:
            raise JobDurabilityError("Plan-job record durability commit failed.") from exc
        finally:
            try:
                os.unlink(temporary_name, dir_fd=directory_fd)
            except FileNotFoundError:
                pass
            finally:
                os.close(directory_fd)

    def _append_event(self, job_id: str, event: PlanJobEvent) -> None:
        data = (json.dumps(event.to_dict(), sort_keys=True, separators=(",", ":")) + "\n").encode(
            "utf-8"
        )
        directory_fd = self._open_jobs_directory()
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW
        try:
            fd = os.open(f"{job_id}.events.jsonl", flags, 0o600, dir_fd=directory_fd)
            try:
                opened = os.fstat(fd)
                if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
                    raise JobIntegrityError("Plan-job event log is not a private regular file.")
                written = 0
                while written < len(data):
                    count = os.write(fd, data[written:])
                    if count <= 0:
                        raise OSError(errno.EIO, "event append made no progress")
                    written += count
                self._inject_fault("event-write")
                os.fsync(fd)
                self._inject_fault("event-fsync")
            finally:
                os.close(fd)
            _fsync_directory(directory_fd)
            self._inject_fault("event-directory-fsync")
        except OSError as exc:
            raise JobDurabilityError("Plan-job event durability commit failed.") from exc
        finally:
            os.close(directory_fd)

    def _inject_fault(self, point: str) -> None:
        if self._fault_injector is not None:
            self._fault_injector(point)

    def _ensure_jobs_root(self) -> tuple[tuple[int, int], ...]:
        root_fd = _open_or_create_managed_root(self.state_root)
        try:
            command_center_fd = _open_managed_child(root_fd, "command-center")
            try:
                jobs_fd = _open_managed_child(command_center_fd, "jobs")
                try:
                    identities = tuple(
                        (opened.st_dev, opened.st_ino)
                        for opened in map(os.fstat, (root_fd, command_center_fd, jobs_fd))
                    )
                    for name in (".mutation.lock", ".service.lock"):
                        self._ensure_private_lock_file(jobs_fd, name)
                    return identities
                finally:
                    os.close(jobs_fd)
            finally:
                os.close(command_center_fd)
        finally:
            os.close(root_fd)

    def _ensure_private_lock_file(self, directory_fd: int, name: str) -> None:
        flags = os.O_RDWR | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        try:
            try:
                descriptor = os.open(name, flags | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=directory_fd)
                _fsync_directory(directory_fd)
            except FileExistsError:
                descriptor = os.open(name, flags, dir_fd=directory_fd)
            try:
                opened = os.fstat(descriptor)
                if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
                    raise JobIntegrityError("Plan-job lock is not a private regular file.")
            finally:
                os.close(descriptor)
        except OSError as exc:
            raise JobIntegrityError("Plan-job lock could not be initialized safely.") from exc

    def _open_jobs_directory(self) -> int:
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        descriptors: list[int] = []
        try:
            absolute = Path(os.path.abspath(self.state_root))
            descriptor = os.open(absolute.anchor, flags)
            descriptors.append(descriptor)
            for component in absolute.parts[1:]:
                descriptor = os.open(component, flags, dir_fd=descriptor)
                descriptors.append(descriptor)
            descriptor = os.open("command-center", flags, dir_fd=descriptor)
            descriptors.append(descriptor)
            descriptor = os.open("jobs", flags, dir_fd=descriptor)
            descriptors.append(descriptor)
            observed = tuple(
                (os.fstat(candidate).st_dev, os.fstat(candidate).st_ino)
                for candidate in descriptors[-3:]
            )
            if observed != self._jobs_directory_identities:
                raise JobIntegrityError("Plan-job storage identity changed after initialization.")
            jobs_fd = descriptors.pop()
            for candidate in reversed(descriptors):
                os.close(candidate)
            return jobs_fd
        except OSError as exc:
            for descriptor in reversed(descriptors):
                os.close(descriptor)
            raise JobIntegrityError("Plan-job storage could not be opened safely.") from exc
        except Exception:
            for descriptor in reversed(descriptors):
                os.close(descriptor)
            raise

    @contextmanager
    def _mutation_lock(self) -> Iterator[None]:
        directory_fd = self._open_jobs_directory()
        handle = None
        locked = False
        try:
            fd = os.open(
                ".mutation.lock",
                os.O_RDWR | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
                dir_fd=directory_fd,
            )
            handle = os.fdopen(fd, "a+", encoding="utf-8")
            opened = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
                raise JobIntegrityError("Plan-job mutation lock is not a private regular file.")
            portalocker.lock(handle, portalocker.LOCK_EX)
            locked = True
            yield
        except (portalocker.exceptions.LockException, OSError) as exc:
            raise JobDurabilityError("Plan-job mutation lock could not be acquired.") from exc
        finally:
            if handle is not None:
                try:
                    if locked:
                        portalocker.unlock(handle)
                finally:
                    handle.close()
            os.close(directory_fd)

    def acquire_service_ownership(self) -> object:
        """Acquire the lifetime lock before recovery or worker construction."""

        directory_fd = self._open_jobs_directory()
        try:
            try:
                fd = os.open(
                    ".service.lock",
                    os.O_RDWR | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
                    dir_fd=directory_fd,
                )
            except OSError as exc:
                raise ServiceOwnershipError(
                    "The command-center service lock could not be opened safely."
                ) from exc
            handle = os.fdopen(fd, "a+", encoding="utf-8")
            opened = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
                handle.close()
                raise ServiceOwnershipError(
                    "The command-center service lock is not a private regular file."
                )
            try:
                portalocker.lock(handle, portalocker.LOCK_EX | portalocker.LOCK_NB)
            except (portalocker.exceptions.LockException, OSError) as exc:
                handle.close()
                raise ServiceOwnershipError(
                    "Another command-center plan service is already running."
                ) from exc
            return handle
        finally:
            os.close(directory_fd)


class PlanJobService:
    """Run one managed plan at a time and expose historical/live observation."""

    def __init__(
        self,
        *,
        state_root: Path,
        artifacts_root: Path,
        planning_service: PlanningService | None = None,
        executor: Executor | None = None,
        clock: Clock = utc_now,
        job_id_factory: JobIdFactory = make_job_id,
    ) -> None:
        self.state_root = Path(state_root)
        self.artifacts_root = Path(artifacts_root)
        self.store = PlanJobStore(self.state_root, clock=clock)
        self._owner_handle = self.store.acquire_service_ownership()
        self._artifact_directory_fds: tuple[int, int, int] | None = None
        try:
            # Only the process that owns the lifetime lock may perform recovery.
            self.store.interrupt_active_jobs()
            self._artifact_directory_fds = _open_managed_artifact_directories(
                self.artifacts_root
            )
            self._planning_service = planning_service
            self._executor = executor or ThreadPoolExecutor(
                max_workers=1, thread_name_prefix="buoy-plan"
            )
        except Exception:
            if self._artifact_directory_fds is not None:
                for descriptor in reversed(self._artifact_directory_fds):
                    os.close(descriptor)
                self._artifact_directory_fds = None
            portalocker.unlock(self._owner_handle)
            self._owner_handle.close()
            raise
        self._owns_executor = executor is None
        self._job_id_factory = job_id_factory
        self._condition = Condition(RLock())
        self._start_lock = RLock()
        self._futures: dict[str, Future[Any]] = {}
        self._closed = False
        self._shutdown_complete = Event()
        self._shutdown_error: BaseException | None = None
        self._shutdown_warning_job_id: str | None = None

    def start(self, request: PlanJobRequest) -> PlanJob:
        source = _validate_request(request)
        source_kind = getattr(source, "kind", None)
        if source_kind not in {"website", "github_repo"}:
            raise ValueError("managed source_url is unsupported")
        with self._start_lock:
            if self._closed:
                raise ServiceOwnershipError("The command-center plan service is closed.")
            active = self.store.active_job()
            if active is not None:
                raise ActiveJobConflict(active.job_id)
            while True:
                job_id = self._job_id_factory()
                _validate_job_id(job_id)
                try:
                    self.store.get(job_id)
                except JobNotFoundError:
                    break
            artifact_path = PurePosixPath("command-center", "plans", job_id).as_posix()
            out_dir = self.artifacts_root / Path(artifact_path)
            output_descriptor, output_identity = self._create_job_output(job_id)
            if self._artifact_directory_fds is None:
                os.close(output_descriptor)
                raise ServiceOwnershipError("The command-center plan service is closed.")
            ancestor_identities = tuple(
                (opened.st_dev, opened.st_ino)
                for opened in map(os.fstat, self._artifact_directory_fds)
            )
            from buoy_search.planning_service import ManagedPublicPlanningRequest

            managed_request = ManagedPublicPlanningRequest(
                source_url=request.source_url,
                out_dir=out_dir,
                state_root=self.state_root,
                max_pages_or_files=request.max_pages_or_files,
                max_chunks=request.max_chunks,
                namespace=request.namespace,
                include_paths=tuple(request.include_paths),
                exclude_paths=tuple(request.exclude_paths),
                originating_job_id=job_id,
                precreated_output_identity=output_identity,
                precreated_output_ancestor_identities=ancestor_identities,
                precreated_output_descriptor=output_descriptor,
            )
            try:
                # Validate the complete shared-service request before worker submission.
                managed_request.to_planning_request()
                job = self.store.create(
                    job_id=job_id,
                    source_kind=source_kind,
                    source_url=str(getattr(source, "base_url")),
                    namespace=request.namespace,
                    artifact_path=artifact_path,
                    request_summary=JobRequestSummary(
                        max_pages_or_files=request.max_pages_or_files,
                        max_chunks=request.max_chunks,
                        namespace=_safe_optional_text(request.namespace),
                        include_path_count=len(request.include_paths),
                        exclude_path_count=len(request.exclude_paths),
                    ),
                )
            except Exception:
                os.close(output_descriptor)
                self._remove_empty_job_output(job_id)
                raise
            self._notify()
            try:
                future = self._executor.submit(self._execute, job_id, managed_request)
                self._futures[job_id] = future
            except Exception:
                os.close(output_descriptor)
                failed = self.store.transition(
                    job_id,
                    "failed",
                    error=SafeJobError(
                        "executor_unavailable",
                        "The local plan worker could not be started.",
                    ),
                )
                self._notify()
                return failed
            return job

    def get(self, job_id: str) -> PlanJob:
        return self.store.get(job_id)

    def list(self) -> list[PlanJob]:
        return self.store.list()

    def list_window(self, *, offset: int, limit: int) -> tuple[list[PlanJob], int]:
        return self.store.list_window(offset=offset, limit=limit)

    def events_after(self, job_id: str, after_sequence: int = 0) -> list[PlanJobEvent]:
        return self.store.events_after(
            job_id, after_sequence, limit=MAX_EVENT_REPLAY_SIZE
        )

    def observe_events(
        self,
        job_id: str,
        *,
        after_sequence: int = 0,
        timeout: float | None = None,
    ) -> Iterator[PlanJobEvent]:
        if timeout is not None and timeout < 0:
            raise ValueError("timeout must be non-negative")
        deadline = None if timeout is None else time.monotonic() + timeout
        sequence = after_sequence
        while True:
            events = self.store.events_after(job_id, sequence)
            for event in events:
                sequence = event.sequence
                yield event
            if self.store.get(job_id).state in TERMINAL_STATES:
                if self.store.events_after(job_id, sequence):
                    continue
                return
            with self._condition:
                events = self.store.events_after(job_id, sequence)
                if events or self.store.get(job_id).state in TERMINAL_STATES:
                    continue
                remaining = None if deadline is None else deadline - time.monotonic()
                if remaining is not None and remaining <= 0:
                    return
                self._condition.wait(remaining)

    def wait(self, job_id: str, *, timeout: float | None = None) -> PlanJob:
        if timeout is not None and timeout < 0:
            raise ValueError("timeout must be non-negative")
        deadline = None if timeout is None else time.monotonic() + timeout
        with self._condition:
            while True:
                job = self.store.get(job_id)
                if job.state in TERMINAL_STATES:
                    return job
                future = self._futures.get(job_id)
                if future is not None and future.done() and future.exception() is not None:
                    raise future.exception()  # type: ignore[misc]
                remaining = None if deadline is None else deadline - time.monotonic()
                if remaining is not None and remaining <= 0:
                    raise TimeoutError("Plan job did not reach a terminal state in time.")
                self._condition.wait(remaining)

    def _create_job_output(self, job_id: str) -> tuple[int, tuple[int, int]]:
        if self._artifact_directory_fds is None:
            raise ServiceOwnershipError("The command-center plan service is closed.")
        plans_fd = self._artifact_directory_fds[2]
        try:
            os.mkdir(job_id, 0o700, dir_fd=plans_fd)
            _fsync_directory(plans_fd)
            descriptor = os.open(
                job_id,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
                dir_fd=plans_fd,
            )
        except FileExistsError as exc:
            raise JobIntegrityError("Managed plan output already exists or was tampered with.") from exc
        except OSError as exc:
            raise JobIntegrityError("Managed plan output could not be created safely.") from exc
        try:
            opened = os.fstat(descriptor)
        except OSError as exc:
            os.close(descriptor)
            raise JobIntegrityError("Managed plan output could not be inspected safely.") from exc
        if not stat.S_ISDIR(opened.st_mode):
            os.close(descriptor)
            raise JobIntegrityError("Managed plan output is not a directory.")
        return descriptor, (opened.st_dev, opened.st_ino)

    def _remove_empty_job_output(self, job_id: str) -> None:
        if self._artifact_directory_fds is None:
            return
        try:
            os.rmdir(job_id, dir_fd=self._artifact_directory_fds[2])
            _fsync_directory(self._artifact_directory_fds[2])
        except OSError:
            pass

    def shutdown(self, *, wait: bool = True) -> None:
        with self._start_lock:
            if self._closed:
                shutdown_complete = self._shutdown_complete
                already_started = True
            else:
                futures = tuple(self._futures.items())
                active_futures = tuple(
                    (job_id, future) for job_id, future in futures if not future.done()
                )
                if not wait and active_futures:
                    self._log_shutdown_wait(active_futures[0][0])
                    raise ServiceOwnershipError(
                        "Cannot release service ownership while a plan worker is still active."
                    )
                # Prevent a validated start from submitting work after the shutdown
                # snapshot. Running futures retain authority to finish normally.
                self._closed = True
                shutdown_complete = self._shutdown_complete
                already_started = False

        if already_started:
            if wait:
                shutdown_complete.wait()
                if self._shutdown_error is not None:
                    raise self._shutdown_error
            return

        if active_futures:
            self._log_shutdown_wait(active_futures[0][0])
        operation_error: BaseException | None = None
        try:
            if self._owns_executor:
                self._executor.shutdown(wait=wait)
            elif wait:
                for _job_id, future in futures:
                    future.result()
        except BaseException as exc:
            operation_error = exc
        cleanup_error = self._release_service_resources()
        self._shutdown_error = cleanup_error or operation_error
        shutdown_complete.set()
        if self._shutdown_error is not None:
            raise self._shutdown_error

    def announce_shutdown(self) -> None:
        """Log the non-cancellable active worker when the server receives shutdown."""

        with self._start_lock:
            active_job_id = next(
                (job_id for job_id, future in self._futures.items() if not future.done()),
                None,
            )
        if active_job_id is not None:
            self._log_shutdown_wait(active_job_id)

    def _log_shutdown_wait(self, job_id: str) -> None:
        with self._start_lock:
            if self._shutdown_warning_job_id == job_id:
                return
            self._shutdown_warning_job_id = job_id
        active = self._shutdown_job_state(job_id)
        _LOGGER.warning(
            "Waiting for active plan job %s (%s) during shutdown; cancellation is not supported in Phase 2A.",
            active[0],
            active[1],
        )

    def _release_service_resources(self) -> BaseException | None:
        """Attempt every shutdown cleanup step and return the first failure."""

        first_error: BaseException | None = None

        def attempt(operation: Callable[[], None]) -> None:
            nonlocal first_error
            try:
                operation()
            except BaseException as exc:
                if first_error is None:
                    first_error = exc

        descriptors = self._artifact_directory_fds
        self._artifact_directory_fds = None
        if descriptors is not None:
            for descriptor in reversed(descriptors):
                attempt(lambda descriptor=descriptor: os.close(descriptor))
        attempt(lambda: portalocker.unlock(self._owner_handle))
        attempt(self._owner_handle.close)
        attempt(self._notify)
        return first_error

    def _shutdown_job_state(self, job_id: str) -> tuple[str, str]:
        try:
            state = self.store.get(job_id).state
        except Exception:
            # Shutdown and ownership release must not be bypassed by a damaged
            # audit record. Never log the exception or source-bearing data.
            state = "unknown"
        return job_id, state

    def _execute(self, job_id: str, request: ManagedPublicPlanningRequest) -> None:
        from buoy_search.planning_service import PlanningService, validate_precreated_output

        try:
            self.store.transition(job_id, "running")
            self._notify()
            validate_precreated_output(request.to_planning_request())
            planning_service = self._planning_service
            if planning_service is None:
                planning_service = PlanningService()
                self._planning_service = planning_service
            result = planning_service.plan(
                request,
                progress_callback=lambda progress: self._record_progress(job_id, progress),
            )
            plan_id = result.summary.get("plan_id")
            namespace = result.summary.get("namespace")
            if not isinstance(plan_id, str) or not plan_id.strip():
                raise JobIntegrityError("Planning returned no verified plan ID.")
            if not isinstance(namespace, str) or not namespace:
                raise JobIntegrityError("Planning returned no verified namespace.")
            if request.namespace is not None and namespace != request.namespace:
                raise JobIntegrityError("Planning returned an unexpected namespace.")
            if Path(result.out_dir) != Path(request.out_dir):
                raise JobIntegrityError("Planning returned an unexpected artifact directory.")
            validate_precreated_output(request.to_planning_request())
            self.store.transition(
                job_id,
                "succeeded",
                plan_id=plan_id,
                namespace=namespace,
            )
        except JobDurabilityError:
            self._notify()
            raise
        except Exception as exc:
            # Never interpolate the exception: provider/source failures can contain
            # credentials, paths, response bodies, or other untrusted values.
            _LOGGER.error("Plan job %s failed (%s).", job_id, type(exc).__name__)
            try:
                current = self.store.get(job_id)
                if current.state in ACTIVE_STATES:
                    self.store.transition(
                        job_id,
                        "failed",
                        error=SafeJobError(
                            "planning_failed",
                            "Planning failed; incomplete managed artifacts were preserved when safe.",
                        ),
                    )
            finally:
                self._notify()
        else:
            self._notify()
        finally:
            descriptor = request.precreated_output_descriptor
            if descriptor is not None:
                os.close(descriptor)

    def _record_progress(self, job_id: str, progress: PlanProgress) -> None:
        if self.store.record_progress(job_id, progress) is not None:
            self._notify()

    def _notify(self) -> None:
        with self._condition:
            self._condition.notify_all()


_STAGE_MESSAGES: Mapping[JobStage, str] = {
    "source-acquisition": "Acquiring public source content.",
    "source-discovery": "Discovering public source content.",
    "crawl": "Crawling credential-free HTTP(S) website content.",
    "clone": "Cloning public repository content.",
    "processing": "Processing source content.",
    "chunk": "Chunking source content.",
    "artifact": "Building review artifacts.",
    "diff": "Diffing against local applied state.",
    "write": "Writing and verifying review artifacts.",
    "validation": "Validating the plan request.",
    "queued": "Plan job queued.",
    "succeeded": "Plan artifacts verified successfully.",
    "failed": "Planning failed.",
    "interrupted": "Planning was interrupted by a local service restart.",
}


def progress_from_service(progress: PlanProgress) -> JobProgress:
    """Project service callbacks onto bounded, non-source-controlled job events."""

    stage = map_progress_stage(progress.stage, progress.message)
    counts = {
        key: value
        for key, value in progress.counts.items()
        if (
            isinstance(key, str)
            and key in _SAFE_COUNT_KEYS
            and _SAFE_COUNT_KEY.fullmatch(key) is not None
            and type(value) is int
            and value >= 0
        )
    }
    return JobProgress(stage, _STAGE_MESSAGES[stage], counts)


def map_progress_stage(stage: str, message: str = "") -> JobStage:
    # The shared service stage is bounded; raw source/provider message text must
    # never select or populate durable fields.
    del message
    text = stage.casefold()
    if "crawl" in text or "scrap" in text:
        return "crawl"
    if "clone" in text or "github" in text or "repo" in text:
        return "clone"
    if "chunk" in text:
        return "chunk"
    if "discover" in text or "sitemap" in text:
        return "source-discovery"
    if "acquir" in text or "fetch" in text or "download" in text:
        return "source-acquisition"
    if "artifact" in text or "build" in text:
        return "artifact"
    if "diff" in text:
        return "diff"
    if "write" in text or "publish" in text or "complete" in text or "verify" in text:
        return "write"
    if "valid" in text or "prepar" in text:
        return "validation"
    return "processing"


def _validate_request(request: PlanJobRequest) -> object:
    from buoy_search.planning_service import validate_managed_public_source

    if not isinstance(request, PlanJobRequest):
        raise TypeError("request must be a PlanJobRequest")
    for name, value in (
        ("max_pages_or_files", request.max_pages_or_files),
        ("max_chunks", request.max_chunks),
    ):
        if value is not None and (type(value) is not int or value <= 0):
            raise ValueError(f"{name} must be a positive integer")
    if request.namespace is not None and not isinstance(request.namespace, str):
        raise ValueError("namespace must be a string")
    if not all(isinstance(value, str) for value in (*request.include_paths, *request.exclude_paths)):
        raise ValueError("include_paths and exclude_paths must contain strings")
    return validate_managed_public_source(request.source_url)


def _safe_persisted_url(value: str) -> str:
    try:
        parsed = validate_http_url_authority(value)
    except ValueError as exc:
        raise JobIntegrityError("Plan-job source URL is invalid.") from exc
    safe = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    if not safe:
        raise JobIntegrityError("Plan-job source URL is invalid.")
    return safe


def _safe_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    return _bounded_text(value, MAX_PROGRESS_MESSAGE_LENGTH)


def _bounded_text(value: str, maximum: int) -> str:
    return " ".join(str(value).split())[:maximum]


def _safe_identifier(value: str, *, label: str) -> str:
    text = _bounded_text(value, MAX_PROGRESS_MESSAGE_LENGTH)
    if not text or Path(text).name != text or text in {".", ".."} or "/" in text or "\\" in text:
        raise JobIntegrityError(f"Plan-job {label} is unsafe.")
    return text


def _validate_private_regular_file(metadata: os.stat_result, *, label: str) -> None:
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or metadata.st_mode & 0o077
    ):
        raise JobIntegrityError(f"Plan-job {label} is not a private regular file.")


def _validate_job_id(job_id: str) -> str:
    if not isinstance(job_id, str) or _SAFE_JOB_ID.fullmatch(job_id) is None:
        raise JobIntegrityError("Plan-job ID is unsafe.")
    return job_id


def _validate_relative_path(value: str) -> str:
    path = PurePosixPath(value)
    if (
        not isinstance(value, str)
        or not value
        or path.is_absolute()
        or "\\" in value
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise JobIntegrityError("Plan-job artifact path must be a safe relative path.")
    return value


def _validate_safe_error(error: SafeJobError) -> SafeJobError:
    if _SAFE_CODE.fullmatch(error.code) is None:
        raise JobIntegrityError("Plan-job error code is unsafe.")
    message = _bounded_text(error.message, MAX_PROGRESS_MESSAGE_LENGTH)
    if not message:
        raise JobIntegrityError("Plan-job error message is empty.")
    return SafeJobError(error.code, message)


def _validate_timestamp(value: object, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str):
        raise JobIntegrityError("Plan-job timestamp is invalid.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise JobIntegrityError("Plan-job timestamp is invalid.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise JobIntegrityError("Plan-job timestamp must be UTC.")
    return value


def _validate_job(job: PlanJob) -> PlanJob:
    _validate_job_id(job.job_id)
    _validate_relative_path(job.artifact_path)
    if (
        type(job.schema_version) is not int
        or job.schema_version != JOB_SCHEMA_VERSION
        or job.operation != "plan"
        or job.actor != "local-operator"
    ):
        raise JobIntegrityError("Plan-job record identity is incompatible.")
    if (
        not isinstance(job.state, str)
        or job.state not in ALLOWED_TRANSITIONS
        or not isinstance(job.source_kind, str)
        or job.source_kind not in {"website", "github_repo"}
    ):
        raise JobIntegrityError("Plan-job record state or source kind is invalid.")
    if (
        not isinstance(job.source_url, str)
        or len(job.source_url) > MAX_MANAGED_SOURCE_URL_LENGTH
        or _safe_persisted_url(job.source_url) != job.source_url
    ):
        raise JobIntegrityError("Plan-job source URL is not safely normalized.")
    if _safe_optional_text(job.namespace) != job.namespace:
        raise JobIntegrityError("Plan-job namespace is not safely normalized.")
    _validate_request_summary(job.request_summary)
    _validate_timestamp(job.created_at)
    _validate_timestamp(job.updated_at)
    _positive_int(job.event_sequence)
    _validate_timestamp(job.started_at, optional=True)
    _validate_timestamp(job.completed_at, optional=True)
    if job.state == "queued" and (
        job.started_at is not None or job.latest_progress.stage != "queued"
    ):
        raise JobIntegrityError("Queued plan job progress or timestamp is invalid.")
    if job.state == "running" and (
        job.started_at is None
        or job.completed_at is not None
        or job.latest_progress.stage in {"queued", "succeeded", "failed", "interrupted"}
    ):
        raise JobIntegrityError("Running plan job progress or timestamps are invalid.")
    if job.state in TERMINAL_STATES and (
        job.completed_at is None or job.latest_progress.stage != job.state
    ):
        raise JobIntegrityError("Terminal plan job progress or timestamp is invalid.")
    if job.state == "succeeded":
        if job.plan_id is None or job.error is not None:
            raise JobIntegrityError("Succeeded plan job result is invalid.")
        _safe_identifier(job.plan_id, label="plan ID")
    elif job.plan_id is not None:
        raise JobIntegrityError("Non-succeeded plan job cannot contain a plan ID.")
    if job.state in {"failed", "interrupted"}:
        if job.error is None:
            raise JobIntegrityError("Failed or interrupted plan job has no safe error.")
        _validate_safe_error(job.error)
        if job.latest_progress.message != job.error.message:
            raise JobIntegrityError("Terminal plan-job progress does not match its safe error.")
    elif job.error is not None:
        raise JobIntegrityError("Non-failed plan job cannot contain an error.")
    _validate_progress(job.latest_progress)
    return job


def _validate_request_summary(summary: JobRequestSummary) -> JobRequestSummary:
    _optional_positive_int(summary.max_pages_or_files)
    _optional_positive_int(summary.max_chunks)
    if _safe_optional_text(summary.namespace) != summary.namespace:
        raise JobIntegrityError("Plan-job request namespace is not safely normalized.")
    _non_negative_int(summary.include_path_count)
    _non_negative_int(summary.exclude_path_count)
    return summary


def _validate_progress(progress: JobProgress) -> JobProgress:
    if not isinstance(progress.stage, str) or progress.stage not in _STAGE_VALUES:
        raise JobIntegrityError("Plan-job progress stage is invalid.")
    if not progress.message or len(progress.message) > MAX_PROGRESS_MESSAGE_LENGTH:
        raise JobIntegrityError("Plan-job progress message is invalid.")
    if len(progress.stage) > MAX_PROGRESS_STAGE_LENGTH:
        raise JobIntegrityError("Plan-job progress stage is too long.")
    for key, value in progress.counts.items():
        if key not in _SAFE_COUNT_KEYS or type(value) is not int or value < 0:
            raise JobIntegrityError("Plan-job progress counts are invalid.")
    return progress


def _job_from_dict(payload: object) -> PlanJob:
    if not isinstance(payload, dict) or frozenset(payload) != _JOB_FIELDS:
        raise JobIntegrityError("Plan-job record fields are invalid.")
    progress = _progress_from_dict(payload["latest_progress"])
    error_payload = payload["error"]
    if error_payload is None:
        error = None
    elif isinstance(error_payload, dict) and frozenset(error_payload) == {"code", "message"}:
        error = _validate_safe_error(
            SafeJobError(
                _required_string(error_payload["code"]),
                _required_string(error_payload["message"]),
            )
        )
    else:
        raise JobIntegrityError("Plan-job error fields are invalid.")
    summary_payload = payload["request_summary"]
    if not isinstance(summary_payload, dict) or frozenset(summary_payload) != _REQUEST_SUMMARY_FIELDS:
        raise JobIntegrityError("Plan-job request summary fields are invalid.")
    summary = JobRequestSummary(
        max_pages_or_files=_optional_positive_int(summary_payload["max_pages_or_files"]),
        max_chunks=_optional_positive_int(summary_payload["max_chunks"]),
        namespace=_optional_string(summary_payload["namespace"]),
        include_path_count=_non_negative_int(summary_payload["include_path_count"]),
        exclude_path_count=_non_negative_int(summary_payload["exclude_path_count"]),
    )
    try:
        job = PlanJob(
            schema_version=payload["schema_version"],  # type: ignore[arg-type]
            job_id=_required_string(payload["job_id"]),
            operation=payload["operation"],  # type: ignore[arg-type]
            actor=payload["actor"],  # type: ignore[arg-type]
            state=payload["state"],  # type: ignore[arg-type]
            source_kind=payload["source_kind"],  # type: ignore[arg-type]
            source_url=_required_string(payload["source_url"]),
            namespace=_optional_string(payload["namespace"]),
            artifact_path=_required_string(payload["artifact_path"]),
            plan_id=_optional_string(payload["plan_id"]),
            created_at=_required_string(payload["created_at"]),
            updated_at=_required_string(payload["updated_at"]),
            event_sequence=_positive_int(payload["event_sequence"]),
            started_at=_optional_string(payload["started_at"]),
            completed_at=_optional_string(payload["completed_at"]),
            latest_progress=progress,
            error=error,
            request_summary=summary,
        )
    except (TypeError, ValueError) as exc:
        raise JobIntegrityError("Plan-job record values are invalid.") from exc
    return _validate_job(job)


def _progress_from_dict(payload: object) -> JobProgress:
    if not isinstance(payload, dict) or frozenset(payload) != {"stage", "message", "counts"}:
        raise JobIntegrityError("Plan-job progress fields are invalid.")
    counts_payload = payload["counts"]
    if not isinstance(counts_payload, dict):
        raise JobIntegrityError("Plan-job progress counts are invalid.")
    progress = JobProgress(
        stage=payload["stage"],  # type: ignore[arg-type]
        message=_required_string(payload["message"]),
        counts={str(key): value for key, value in counts_payload.items()},  # type: ignore[misc]
    )
    return _validate_progress(progress)


def _event_from_dict(payload: object) -> PlanJobEvent:
    if not isinstance(payload, dict) or frozenset(payload) != _EVENT_FIELDS:
        raise JobIntegrityError("Plan-job event fields are invalid.")
    sequence = _positive_int(payload["sequence"])
    timestamp = _validate_timestamp(payload["timestamp"])
    progress = _progress_from_dict(
        {"stage": payload["stage"], "message": payload["message"], "counts": payload["counts"]}
    )
    return PlanJobEvent(sequence, str(timestamp), progress.stage, progress.message, progress.counts)


def _required_string(value: object) -> str:
    if not isinstance(value, str):
        raise JobIntegrityError("Plan-job string is invalid.")
    return value


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return _required_string(value)


def _positive_int(value: object) -> int:
    if type(value) is not int or value <= 0:
        raise JobIntegrityError("Plan-job positive integer is invalid.")
    return value


def _optional_positive_int(value: object) -> int | None:
    return None if value is None else _positive_int(value)


def _non_negative_int(value: object) -> int:
    if type(value) is not int or value < 0:
        raise JobIntegrityError("Plan-job non-negative integer is invalid.")
    return value


def _open_or_create_managed_root(path: Path) -> int:
    """Open every absolute path component without following symlinks."""

    absolute = Path(os.path.abspath(path))
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    try:
        descriptor = os.open(absolute.anchor, flags)
    except OSError as exc:
        raise JobIntegrityError("Managed artifacts root contains an unsafe directory.") from exc
    try:
        for component in absolute.parts[1:]:
            try:
                child = os.open(component, flags, dir_fd=descriptor)
            except FileNotFoundError:
                try:
                    os.mkdir(component, 0o700, dir_fd=descriptor)
                    _fsync_directory(descriptor)
                except FileExistsError:
                    pass
                child = os.open(component, flags, dir_fd=descriptor)
            opened = os.fstat(child)
            if not stat.S_ISDIR(opened.st_mode):
                os.close(child)
                raise JobIntegrityError("Managed artifacts path is not a directory.")
            os.close(descriptor)
            descriptor = child
        return descriptor
    except OSError as exc:
        os.close(descriptor)
        raise JobIntegrityError("Managed artifacts root could not be created safely.") from exc
    except Exception:
        os.close(descriptor)
        raise


def _open_managed_child(parent_fd: int, name: str) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    try:
        try:
            os.mkdir(name, 0o700, dir_fd=parent_fd)
            _fsync_directory(parent_fd)
        except FileExistsError:
            pass
        descriptor = os.open(name, flags, dir_fd=parent_fd)
    except OSError as exc:
        raise JobIntegrityError("Managed artifacts path contains a symlink or non-directory.") from exc
    if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise JobIntegrityError("Managed artifacts path is not a directory.")
    return descriptor


def _open_managed_artifact_directories(artifacts_root: Path) -> tuple[int, int, int]:
    root_fd = _open_or_create_managed_root(artifacts_root)
    try:
        command_center_fd = _open_managed_child(root_fd, "command-center")
        try:
            plans_fd = _open_managed_child(command_center_fd, "plans")
        except Exception:
            os.close(command_center_fd)
            raise
    except Exception:
        os.close(root_fd)
        raise
    return root_fd, command_center_fd, plans_fd


def require_managed_planning_platform() -> None:
    """Fail only when the platform lacks mandatory safe filesystem primitives."""

    required = ("O_NOFOLLOW", "O_DIRECTORY")
    if any(getattr(os, name, None) is None for name in required):
        raise ManagedPlanningUnsupportedError(
            "Managed planning requires no-follow directory opens."
        )
    if (
        os.open not in os.supports_dir_fd
        or os.stat not in os.supports_dir_fd
        or os.mkdir not in os.supports_dir_fd
        or os.rmdir not in os.supports_dir_fd
        or os.link not in os.supports_dir_fd
        or os.unlink not in os.supports_dir_fd
        or os.rename not in os.supports_dir_fd
        or os.listdir not in os.supports_fd
        or os.scandir not in os.supports_fd
    ):
        raise ManagedPlanningUnsupportedError(
            "Managed planning requires descriptor-relative filesystem access."
        )


def _require_safe_filesystem_primitives() -> None:
    require_managed_planning_platform()


def _fsync_directory(directory_fd: int) -> None:
    try:
        os.fsync(directory_fd)
    except OSError as exc:
        raise JobDurabilityError("Plan-job directory durability sync failed.") from exc
