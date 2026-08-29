"""Bounded local writer and content-free telemetry management commands.

Status is deliberately metadata-only and this module does not import DuckDB or
``telemetry_store`` at import time.  The elected writer loads the store only
after independently decoding a valid claimed envelope.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
import json
import math
import os
from pathlib import Path
import sys
import time
from types import ModuleType
from typing import Any

from buoy_search.telemetry.envelope import (
    TraceEnvelopeError,
    CommandTraceRows,
    CommandTraceRowsV3,
    TraceRows,
    decode_trace_envelope_v1,
    decode_trace_envelope_v2,
    decode_trace_envelope_v3,
)
from buoy_search.telemetry.queue import (
    COUNTER_MAX,
    PUBLISHED_MAX_BYTES,
    PUBLISHED_MAX_ENTRIES,
    PendingItem,
    TEMP_MAX_BYTES,
    TEMP_MAX_ENTRIES,
    QueueLockTimeout,
    QueueSnapshot,
    ReceiptKind,
    TelemetryPaths,
    TelemetryQueueError,
    TerminalReceipt,
    UnreadablePathError,
    UnsafePathError,
    UnsupportedPlatformError,
    WriterState,
    acknowledge_claim,
    claim_ready_batch,
    claim_ready_names,
    cleanup_stale_envelope_temporaries,
    clear_writer_start_lease,
    fsync_writer_state_directory,
    inspect_receipt_temporaries,
    open_private_directory_at,
    open_verified_directory,
    posix_writer_capability,
    publish_terminal_receipt,
    queue_lock,
    read_claimed_envelope,
    read_producer_accounting,
    read_terminal_receipt,
    read_terminal_receipt_temporary,
    read_writer_start_lease,
    read_writer_state,
    reconcile_writer_receipts_shared,
    recover_claim,
    request_writer_start,
    resolve_receipt_temporary,
    scan_fixed_private_inventory,
    scan_queue_read_only,
    snapshot_pending,
    stat_private_entry_at,
    telemetry_paths,
    telemetry_paths_v2,
    telemetry_paths_v3,
    terminal_kind_for_snapshot_item,
    write_writer_state,
    writer_state_temporary_present,
    writer_lifetime_lock,
    writer_start_lock,
)


HEARTBEAT_INTERVAL_SECONDS = 1.0
INBOX_POLL_SECONDS = 0.05
DATABASE_RETRY_SECONDS = 0.01
DATABASE_RETRY_WINDOW_SECONDS = 30.0
IDLE_EXIT_SECONDS = 60.0
DRAIN_DEADLINE_SECONDS = 300.0
WRITER_STALE_SECONDS = 35.0
START_LEASE_SECONDS = 30.0
CLAIM_BATCH_SIZE = 128
DATABASE_WAL_MAX_BYTES = 16_777_216
_MIGRATION_SCRATCH_NAMES = frozenset(
    {"telemetry.duckdb", "telemetry.duckdb.wal", "telemetry-v1-backup.duckdb"}
)
_MIGRATION_V3_SCRATCH_NAMES = frozenset(
    {"telemetry.duckdb", "telemetry.duckdb.wal", "telemetry-v2-backup.duckdb"}
)
DATABASE_PATH_DISPLAY = "~/.buoy/telemetry/telemetry.duckdb"


@dataclass(frozen=True)
class CommandResult:
    """One command's exact exit code and newline-free rendered output."""

    exit_code: int
    output: str


@dataclass(frozen=True)
class _StoreInspection:
    state: str
    schema_version: int | None
    bytes: int | None
    persisted_runs_snapshot: int | None
    last_writer_commit_unix_ms: int | None


@dataclass(frozen=True)
class _InitializationScratchInspection:
    present: bool
    database: os.stat_result | None = None
    wal: os.stat_result | None = None


class _ReceiptProofDeferred(RuntimeError):
    """A terminal receipt remains authoritative but cannot yet be proven."""


def _combine_queue_snapshots(snapshots: tuple[QueueSnapshot, ...]) -> QueueSnapshot:
    return QueueSnapshot(
        present=any(item.present for item in snapshots),
        ready=sum(item.ready for item in snapshots),
        claimed=sum(item.claimed for item in snapshots),
        temporary=sum(item.temporary for item in snapshots),
        receipts=sum(item.receipts for item in snapshots),
        pending_bytes=sum(item.pending_bytes for item in snapshots),
        temporary_bytes=sum(item.temporary_bytes for item in snapshots),
        receipt_bytes=sum(item.receipt_bytes for item in snapshots),
        oldest_pending_mtime_ns=min(
            (item.oldest_pending_mtime_ns for item in snapshots if item.oldest_pending_mtime_ns is not None),
            default=None,
        ),
        capacity_full=(
            sum(item.ready + item.claimed for item in snapshots) >= PUBLISHED_MAX_ENTRIES
            or sum(item.pending_bytes for item in snapshots) >= PUBLISHED_MAX_BYTES
            or sum(item.temporary for item in snapshots) >= TEMP_MAX_ENTRIES
            or sum(item.temporary_bytes for item in snapshots) >= TEMP_MAX_BYTES
        ),
        scan_incomplete=any(item.scan_incomplete for item in snapshots),
        unsafe=any(item.unsafe for item in snapshots),
        unreadable=any(item.unreadable for item in snapshots),
        ready_names=tuple(name for item in snapshots for name in item.ready_names),
        claimed_names=tuple(name for item in snapshots for name in item.claimed_names),
        receipt_names=tuple(name for item in snapshots for name in item.receipt_names),
    )


def telemetry_status(
    *,
    paths: TelemetryPaths | None = None,
    environment: Mapping[str, str] | None = None,
    now_unix_ms: int | None = None,
) -> dict[str, object]:
    """Return the exact read-only, content-free status object."""

    selected = telemetry_paths((paths or telemetry_paths()).directory)
    selected_v2 = telemetry_paths_v2(selected.directory)
    selected_v3 = telemetry_paths_v3(selected.directory)
    source = os.environ if environment is None else environment
    now_ms = _time_unix_ms() if now_unix_ms is None else now_unix_ms
    requested = source.get("BUOY_TELEMETRY", "").strip().lower() == "local"
    sdk_disabled = (
        source.get("OTEL_SDK_DISABLED", "").strip().lower() == "true"
    )
    capability = posix_writer_capability()
    if not requested:
        enablement_reason = "not_requested"
    elif sdk_disabled:
        enablement_reason = "otel_sdk_disabled"
    elif not capability.supported:
        enablement_reason = "platform_unsupported"
    else:
        enablement_reason = "enabled"
    effective = requested and not sdk_disabled and capability.supported

    queue_v1 = scan_queue_read_only(selected)
    queue_v2 = scan_queue_read_only(selected_v2)
    queue_v3 = scan_queue_read_only(selected_v3)
    queue = _combine_queue_snapshots((queue_v1, queue_v2, queue_v3))
    state: WriterState | None = None
    state_invalid = False
    state_path_blocked = False
    lease = None
    try:
        state = read_writer_state(selected)
    except (UnsafePathError, UnreadablePathError):
        state_invalid = True
        state_path_blocked = True
    except (TelemetryQueueError, OSError, ValueError):
        state_invalid = True
    try:
        lease = read_writer_start_lease(selected)
    except (UnsafePathError, UnreadablePathError):
        state_invalid = True
        state_path_blocked = True
    except (TelemetryQueueError, OSError, ValueError):
        state_invalid = True

    producer = None
    producer_invalid = False
    producer_path_blocked = False
    try:
        producer = read_producer_accounting(selected)
    except (UnsafePathError, UnreadablePathError):
        producer_invalid = True
        producer_path_blocked = True
    except (TelemetryQueueError, OSError, ValueError):
        producer_invalid = True

    store = _inspect_store(selected, state)
    pending = queue.ready + queue.claimed
    v2_pending = queue_v2.ready + queue_v2.claimed
    v3_pending = queue_v3.ready + queue_v3.claimed
    if store.state == "compatible" and store.schema_version in {1, 2}:
        store = replace(store, state="upgrade_required")
    unsupported_pending = (
        v3_pending if store.schema_version == 2
        else v2_pending + v3_pending if store.schema_version == 1
        else 0
    )
    heartbeat_age = (
        max(0, now_ms - state.heartbeat_unix_ms) if state is not None else None
    )
    lease_fresh = lease is not None and (
        max(0, now_ms - lease.lease_started_unix_ms)
        < int(START_LEASE_SECONDS * 1_000)
    )
    heartbeat_fresh = heartbeat_age is not None and (
        heartbeat_age < int(WRITER_STALE_SECONDS * 1_000)
    )
    blocked_store = store.state in {"incompatible", "unreadable", "unsafe"}
    if state is not None and (state.phase == "blocked" or blocked_store):
        writer_state = "blocked"
    elif pending == 0:
        writer_state = "idle"
    elif lease_fresh or (
        state is not None and state.phase == "starting" and heartbeat_fresh
    ):
        writer_state = "starting"
    elif state is not None and state.phase in {"idle", "draining"} and heartbeat_fresh:
        writer_state = "active"
    elif pending:
        writer_state = "stale"
    else:
        writer_state = "unknown"

    if queue.unsafe:
        queue_state = "unsafe"
    elif queue.unreadable:
        queue_state = "unreadable"
    elif not queue.present:
        queue_state = "absent"
    elif queue.capacity_full:
        queue_state = "full"
    elif pending or queue.temporary:
        queue_state = "backlog"
    else:
        queue_state = "empty"
    oldest_age = (
        max(0, now_ms - queue.oldest_pending_mtime_ns // 1_000_000)
        if queue.oldest_pending_mtime_ns is not None
        else None
    )

    producer_values = producer
    queue_full = producer_values.queue_full if producer_values else 0
    queue_lock_timeout = producer_values.queue_lock_timeout if producer_values else 0
    publication_failure = producer_values.publication_failure if producer_values else 0
    directory_sync_failure = (
        producer_values.directory_sync_failure if producer_values else 0
    )
    writer_start_failure = (
        producer_values.writer_start_failure if producer_values else 0
    )
    producer_dropped = min(
        COUNTER_MAX,
        queue_full + queue_lock_timeout + publication_failure,
    )
    rejected = state.rejected if state else 0
    conflicts = state.conflicts if state else 0
    replays = state.replays if state else 0
    recovered_claims = state.recovered_claims if state else 0
    write_failures = state.write_failures if state else 0
    receipts_rotated = state.receipts_rotated if state else 0
    accounted = set(state.accounted_receipts if state else ())
    receipt_read_failed = False
    if queue.present and not queue.unsafe and not queue.unreadable:
        for versioned_queue, versioned_paths in (
            (queue_v1, selected),
            (queue_v2, selected_v2),
            (queue_v3, selected_v3),
        ):
            for receipt_name in versioned_queue.receipt_names:
                if receipt_name in accounted:
                    continue
                source_name = _source_name_for_receipt_name(receipt_name)
                try:
                    receipt = read_terminal_receipt(
                        source_name, paths=versioned_paths
                    )
                except (TelemetryQueueError, OSError, ValueError):
                    receipt_read_failed = True
                    break
                if receipt is None:
                    receipt_read_failed = True
                    break
                if receipt.kind == "rejected":
                    rejected = min(COUNTER_MAX, rejected + 1)
                elif receipt.kind == "conflict":
                    conflicts = min(COUNTER_MAX, conflicts + 1)
                elif receipt.kind == "replayed":
                    replays = min(COUNTER_MAX, replays + 1)
            if receipt_read_failed:
                break

    accounting_incomplete = any(
        (
            state_invalid,
            producer_invalid,
            receipt_read_failed,
            queue.scan_incomplete,
            bool(state and state.accounting_incomplete),
            bool(producer_values and producer_values.accounting_incomplete),
        )
    )
    durability_degraded = bool(
        directory_sync_failure
        or (state is not None and state.durability_degraded)
    )
    accounting = {
        "producer_dropped_lower_bound": producer_dropped,
        "queue_full": queue_full,
        "queue_lock_timeout": queue_lock_timeout,
        "publication_failure": publication_failure,
        "directory_sync_failure": directory_sync_failure,
        "writer_start_failure": writer_start_failure,
        "rejected": rejected,
        "conflicts": conflicts,
        "replays": replays,
        "recovered_claims": recovered_claims,
        "write_failures": write_failures,
        "receipts_rotated": receipts_rotated,
        "durability_degraded": durability_degraded,
        "incomplete": accounting_incomplete,
    }

    blocked = any(
        (
            not capability.supported,
            queue.unsafe,
            queue.unreadable,
            state_path_blocked,
            producer_path_blocked,
            store.state in {"incompatible", "unreadable", "unsafe"},
            writer_state == "blocked"
            and not (store.state == "upgrade_required" and not unsupported_pending),
            store.state == "upgrade_required" and unsupported_pending > 0,
            receipt_read_failed,
        )
    )
    degraded = any(
        (
            queue_state in {"backlog", "full"},
            queue.scan_incomplete,
            writer_state == "stale",
            store.state in {
                "present_unverified",
                "busy",
                "upgrade_required",
            },
            producer_dropped > 0,
            writer_start_failure > 0,
            rejected > 0,
            conflicts > 0,
            write_failures > 0,
            durability_degraded,
            accounting_incomplete,
        )
    )
    if blocked:
        overall = "blocked"
    elif degraded:
        overall = "degraded"
    elif effective:
        overall = "healthy"
    else:
        overall = "disabled"

    return {
        "schema_version": 3,
        "requested": requested,
        "effective": effective,
        "enablement_reason": enablement_reason,
        "overall": overall,
        "database_path": DATABASE_PATH_DISPLAY,
        "store": {
            "state": store.state,
            "schema_version": store.schema_version,
            "bytes": store.bytes,
            "persisted_runs_snapshot": store.persisted_runs_snapshot,
            "last_writer_commit_unix_ms": store.last_writer_commit_unix_ms,
        },
        "queue": {
            "state": queue_state,
            "ready": queue.ready,
            "claimed": queue.claimed,
            "temporary": queue.temporary,
            "receipts": queue.receipts,
            "pending_bytes": queue.pending_bytes,
            "oldest_pending_age_ms": oldest_age,
            "capacity_full": queue.capacity_full,
            "scan_incomplete": queue.scan_incomplete,
            "v1_ready": queue_v1.ready,
            "v1_claimed": queue_v1.claimed,
            "v2_ready": queue_v2.ready,
            "v2_claimed": queue_v2.claimed,
            "v3_ready": queue_v3.ready,
            "v3_claimed": queue_v3.claimed,
        },
        "migration_backup_present": _migration_backup_present(selected),
        "writer": {
            "state": writer_state,
            "reason": state.reason if state is not None else None,
            "heartbeat_age_ms": heartbeat_age,
        },
        "accounting": accounting,
    }


def telemetry_status_command(
    *,
    json_output: bool,
    paths: TelemetryPaths | None = None,
    environment: Mapping[str, str] | None = None,
) -> CommandResult:
    value = telemetry_status(paths=paths, environment=environment)
    overall = value["overall"]
    exit_code = 2 if overall == "blocked" else 1 if overall == "degraded" else 0
    return CommandResult(
        exit_code=exit_code,
        output=_canonical_json(value) if json_output else _status_text(value),
    )


def telemetry_flush(
    *,
    timeout: float,
    paths: TelemetryPaths | None = None,
) -> dict[str, object]:
    """Start a writer and wait only for the exact pending set at invocation."""

    if (
        type(timeout) not in {int, float}
        or isinstance(timeout, bool)
        or not math.isfinite(timeout)
        or not 0 <= timeout <= 120
    ):
        raise ValueError("telemetry flush timeout must be from 0 through 120")
    started_ns = time.monotonic_ns()
    selected = telemetry_paths((paths or telemetry_paths()).directory)
    selected_v2 = telemetry_paths_v2(selected.directory)
    selected_v3 = telemetry_paths_v3(selected.directory)
    if not posix_writer_capability().supported:
        return _flush_result(
            "blocked", 0, {}, 0, _elapsed_ms(started_ns)
        )
    try:
        snapshot_v1 = snapshot_pending(selected)
        snapshot_v2 = snapshot_pending(selected_v2)
        snapshot_v3 = snapshot_pending(selected_v3)
    except (TelemetryQueueError, OSError, ValueError):
        return _flush_result(
            "blocked", 0, {}, 0, _elapsed_ms(started_ns)
        )
    snapshot_items = snapshot_v1.items + snapshot_v2.items + snapshot_v3.items
    total = len(snapshot_items)
    if _flush_snapshot_blocked(selected, snapshot_items):
        return _flush_result(
            "blocked", total, {}, total, _elapsed_ms(started_ns)
        )
    if total == 0:
        return _flush_result("empty", 0, {}, 0, _elapsed_ms(started_ns))

    request_writer_start(paths=selected)
    deadline_ns = started_ns + int(float(timeout) * 1_000_000_000)
    terminal: dict[str, ReceiptKind] = {}
    while True:
        blocked = False
        for item in snapshot_items:
            if item.source_name in terminal:
                continue
            item_paths = (
                selected_v3 if item.source_name.startswith("v3-")
                else selected_v2 if item.source_name.startswith("v2-")
                else selected
            )
            try:
                kind = terminal_kind_for_snapshot_item(item_paths, item)
            except (TelemetryQueueError, OSError, ValueError):
                blocked = True
                break
            if kind is not None:
                terminal[item.source_name] = kind
        if blocked:
            return _flush_result(
                "blocked",
                total,
                terminal,
                total - len(terminal),
                _elapsed_ms(started_ns),
            )
        if len(terminal) == total:
            classified = any(
                kind in {"rejected", "conflict"} for kind in terminal.values()
            )
            return _flush_result(
                "classified" if classified else "flushed",
                total,
                terminal,
                0,
                _elapsed_ms(started_ns),
            )
        if _flush_snapshot_blocked(selected, snapshot_items):
            return _flush_result(
                "blocked",
                total,
                terminal,
                total - len(terminal),
                _elapsed_ms(started_ns),
            )
        now_ns = time.monotonic_ns()
        if now_ns >= deadline_ns:
            return _flush_result(
                "timeout",
                total,
                terminal,
                total - len(terminal),
                _elapsed_ms(started_ns),
            )
        time.sleep(
            min(INBOX_POLL_SECONDS, (deadline_ns - now_ns) / 1_000_000_000)
        )


def _flush_snapshot_blocked(
    paths: TelemetryPaths,
    items: tuple[PendingItem, ...],
) -> bool:
    v2_in_snapshot = any(item.source_name.startswith("v2-") for item in items)
    v3_in_snapshot = any(item.source_name.startswith("v3-") for item in items)
    for queue_paths in (paths, telemetry_paths_v2(paths.directory), telemetry_paths_v3(paths.directory)):
        queue = scan_queue_read_only(queue_paths)
        if queue.unsafe or queue.unreadable or queue.scan_incomplete:
            return True
    try:
        state = read_writer_state(paths)
    except (TelemetryQueueError, OSError, ValueError):
        return True
    store = _inspect_store(paths, state)
    if store.state in {"incompatible", "unreadable", "unsafe"}:
        return True
    if (v2_in_snapshot and store.schema_version == 1) or (
        v3_in_snapshot and store.schema_version in {1, 2}
    ):
        return True
    if state is not None and state.phase == "blocked":
        return state.reason != "upgrade_required" or v2_in_snapshot or v3_in_snapshot
    return False


def telemetry_flush_command(
    *,
    timeout: float,
    json_output: bool,
    paths: TelemetryPaths | None = None,
) -> CommandResult:
    value = telemetry_flush(timeout=timeout, paths=paths)
    outcome = value["outcome"]
    exit_code = 2 if outcome == "blocked" else 1 if outcome in {
        "classified",
        "timeout",
    } else 0
    return CommandResult(
        exit_code=exit_code,
        output=_canonical_json(value) if json_output else _flush_text(value),
    )




def telemetry_migrate(
    *,
    paths: TelemetryPaths | None = None,
) -> dict[str, object]:
    """Explicitly migrate the canonical store by one supported version."""

    started_ns = time.monotonic_ns()
    selected = telemetry_paths((paths or telemetry_paths()).directory)
    selected_v2 = telemetry_paths_v2(selected.directory)
    selected_v3 = telemetry_paths_v3(selected.directory)
    base = {
        "schema_version": 3,
        "database_path": DATABASE_PATH_DISPLAY,
        "source_schema_version": None,
        "target_schema_version": None,
        "outcome": "blocked",
        "migrated_v1_runs": 0,
        "migrated_v1_spans": 0,
        "migrated_v1_events": 0,
        "pending_v2": 0,
        "backup_present": False,
        "elapsed_ms": 0,
    }
    if not posix_writer_capability().supported:
        return _finish_migration_result(base, started_ns)
    try:
        queue_v1 = scan_queue_read_only(selected)
        queue_v2 = scan_queue_read_only(selected_v2)
        queue_v3 = scan_queue_read_only(selected_v3)
    except (TelemetryQueueError, OSError, ValueError):
        return _finish_migration_result(base, started_ns)
    if any(
        queue.unsafe or queue.unreadable or queue.scan_incomplete
        for queue in (queue_v1, queue_v2, queue_v3)
    ):
        return _finish_migration_result(base, started_ns)
    base["pending_v2"] = queue_v2.ready + queue_v2.claimed
    base["backup_present"] = _migration_backup_present(selected)
    inspection = _inspect_store(selected, None)
    if inspection.state == "absent":
        base["outcome"] = "absent"
        return _finish_migration_result(base, started_ns)
    if (
        inspection.state in {"unsafe", "unreadable"}
        or (inspection.state == "present_unverified" and inspection.bytes is None)
    ):
        return _finish_migration_result(base, started_ns)

    lifetime = writer_lifetime_lock(selected, timeout_ms=0)
    held = False
    try:
        try:
            lifetime.__enter__()
            held = True
        except QueueLockTimeout:
            base["outcome"] = "busy"
            return _finish_migration_result(base, started_ns)
        except (TelemetryQueueError, OSError, ValueError):
            return _finish_migration_result(base, started_ns)
        try:
            queue_v1 = scan_queue_read_only(selected)
            queue_v2 = scan_queue_read_only(selected_v2)
            queue_v3 = scan_queue_read_only(selected_v3)
        except (TelemetryQueueError, OSError, ValueError):
            return _finish_migration_result(base, started_ns)
        if any(
            queue.unsafe or queue.unreadable or queue.scan_incomplete
            for queue in (queue_v1, queue_v2, queue_v3)
        ):
            return _finish_migration_result(base, started_ns)
        base["pending_v2"] = queue_v2.ready + queue_v2.claimed
        store = _load_store_module()
        try:
            version = store.inspect_store_schema_version(selected)
        except store.StoreBusyError:
            base["outcome"] = "busy"
            return _finish_migration_result(base, started_ns)
        except (
            store.StoreIncompatibleError,
            store.StoreUnsafeError,
            store.StoreUnreadableError,
            store.StoreWriteError,
        ):
            return _finish_migration_result(base, started_ns)
        if version is None:
            base["outcome"] = "absent"
            return _finish_migration_result(base, started_ns)
        base["source_schema_version"] = version
        base["target_schema_version"] = version
        base["backup_present"] = _migration_backup_present(selected)
        if version == 3:
            runtime = _WriterRuntime(selected, lambda: None, enforce_drain_deadline=False)
            try:
                reconciled = store.reconcile_already_current_store_v3(selected_v3)
            except store.StoreBusyError:
                base["outcome"] = "busy"
                return _finish_migration_result(base, started_ns)
            except (store.StoreIncompatibleError, store.StoreUnsafeError, store.StoreUnreadableError, store.StoreWriteError):
                return _finish_migration_result(base, started_ns)
            base["backup_present"] = reconciled.backup_present
            if not _publish_exact_store_state(runtime, reconciled.snapshot, durability_degraded=reconciled.durability_degraded):
                return _finish_migration_result(base, started_ns)
            return _finish_successful_migration(base, selected_v3, outcome="already_current", started_ns=started_ns)
        if version == 2:
            runtime = _WriterRuntime(selected, lambda: None, enforce_drain_deadline=False)
            try:
                # A retry after final v2-backup publication must first finish
                # publishing the already-frozen v3 snapshot. Later v1/v2 work
                # stays queued until that publication is complete.
                backup_published = store.migration_backup_matches_v2_source(
                    selected_v3
                )
                store.reconcile_already_current_store(selected)
                runtime._persist_state(force=True)
                for queue_paths in (() if backup_published else (selected, selected_v2)):
                    queue_before = scan_queue_read_only(queue_paths)
                    if queue_before.unsafe or queue_before.unreadable or queue_before.scan_incomplete:
                        return _finish_migration_result(base, started_ns)
                    if queue_before.present:
                        runtime._recover_receipts_and_claims(queue_paths)
                    pending = snapshot_pending(queue_paths)
                    names_all = tuple(item.source_name for item in pending.items)
                    for offset in range(0, len(names_all), CLAIM_BATCH_SIZE):
                        names = claim_ready_names(queue_paths, names_all[offset:offset + CLAIM_BATCH_SIZE])
                        for source_name in names:
                            if not runtime._process_claim(source_name, queue_paths):
                                return _finish_migration_result(base, started_ns)
                    after = scan_queue_read_only(queue_paths)
                    if (
                        runtime.receipt_failure
                        or after.unsafe
                        or after.unreadable
                        or after.scan_incomplete
                        or after.claimed
                    ):
                        return _finish_migration_result(base, started_ns)
                migrated = store.migrate_store_v2_to_v3(selected_v3)
                reconciled = store.reconcile_already_current_store_v3(selected_v3)
            except store.StoreBusyError:
                base["outcome"] = "busy"
                return _finish_migration_result(base, started_ns)
            except (store.StoreIncompatibleError, store.StoreUnsafeError, store.StoreUnreadableError, store.StoreWriteError, TelemetryQueueError, OSError, ValueError):
                return _finish_migration_result(base, started_ns)
            base.update({
                "source_schema_version": 2, "target_schema_version": 3, "outcome": "migrated",
                "migrated_v1_runs": migrated.runs, "migrated_v1_spans": migrated.spans,
                "migrated_v1_events": migrated.events, "backup_present": migrated.backup_present,
            })
            if not _publish_exact_store_state(runtime, reconciled.snapshot, durability_degraded=(migrated.durability_degraded or reconciled.durability_degraded)):
                base["outcome"] = "blocked"
                return _finish_migration_result(base, started_ns)
            return _finish_successful_migration(base, selected_v3, outcome="migrated", started_ns=started_ns)
        if version != 1:
            return _finish_migration_result(base, started_ns)
        try:
            backup_published = store.migration_backup_matches_v1_source(
                selected
            )
            if not backup_published:
                store.recover_prepublication_migration_scratch(selected)
        except store.StoreBusyError:
            base["outcome"] = "busy"
            return _finish_migration_result(base, started_ns)
        except (
            store.StoreIncompatibleError,
            store.StoreUnsafeError,
            store.StoreUnreadableError,
            store.StoreWriteError,
        ):
            return _finish_migration_result(base, started_ns)

        runtime = _WriterRuntime(
            selected,
            lambda: None,
            enforce_drain_deadline=False,
        )
        if not backup_published:
            try:
                runtime._persist_state(force=True)
                queue_before = scan_queue_read_only(selected)
                if (
                    queue_before.unsafe
                    or queue_before.unreadable
                    or queue_before.scan_incomplete
                ):
                    return _finish_migration_result(base, started_ns)
                if queue_before.present:
                    runtime._recover_receipts_and_claims(selected)
                pending = snapshot_pending(selected)
                snapshot_names = tuple(
                    item.source_name for item in pending.items
                )
                for offset in range(0, len(snapshot_names), CLAIM_BATCH_SIZE):
                    names = claim_ready_names(
                        selected,
                        snapshot_names[offset : offset + CLAIM_BATCH_SIZE],
                    )
                    for source_name in names:
                        if not runtime._process_claim(source_name, selected):
                            return _finish_migration_result(base, started_ns)
                after = scan_queue_read_only(selected)
                if (
                    after.unsafe
                    or after.unreadable
                    or after.scan_incomplete
                    or after.claimed
                ):
                    return _finish_migration_result(base, started_ns)
            except (TelemetryQueueError, OSError, ValueError):
                return _finish_migration_result(base, started_ns)

        try:
            migrated = store.migrate_store_v1_to_v2(selected)
        except store.StoreBusyError:
            base["outcome"] = "busy"
            return _finish_migration_result(base, started_ns)
        except (
            store.StoreIncompatibleError,
            store.StoreUnsafeError,
            store.StoreUnreadableError,
            store.StoreWriteError,
        ):
            return _finish_migration_result(base, started_ns)
        base.update(
            {
                "source_schema_version": 1,
                "target_schema_version": 2,
                "outcome": "migrated",
                "migrated_v1_runs": migrated.runs,
                "migrated_v1_spans": migrated.spans,
                "migrated_v1_events": migrated.events,
                "backup_present": migrated.backup_present,
            }
        )
        metadata = _safe_database_metadata(selected)
        if metadata is None:
            base["outcome"] = "blocked"
            return _finish_migration_result(base, started_ns)
        snapshot = store.StoreSnapshot(
            schema_version=2,
            persisted_runs_snapshot=migrated.runs,
            database_device=metadata.st_dev,
            database_inode=metadata.st_ino,
            database_bytes=metadata.st_size,
        )
        if not _publish_exact_store_state(
            runtime,
            snapshot,
            durability_degraded=migrated.durability_degraded,
        ):
            base["outcome"] = "blocked"
            return _finish_migration_result(base, started_ns)
        return _finish_successful_migration(
            base,
            selected_v2,
            outcome="migrated",
            started_ns=started_ns,
        )
    finally:
        if held:
            lifetime.__exit__(None, None, None)


def _finish_successful_migration(
    base: dict[str, object],
    next_version_paths: TelemetryPaths,
    *,
    outcome: str,
    started_ns: int,
) -> dict[str, object]:
    """Finish with the next-version queue snapshot under the fixed public key.

    The compatibility key ``pending_v2`` reports v2 work after v1→v2 and v3
    work after v2→v3. The public migration output schema remains unchanged.
    """

    try:
        with queue_lock(next_version_paths):
            next_version_queue = scan_queue_read_only(next_version_paths)
            if (
                next_version_queue.unsafe
                or next_version_queue.unreadable
                or next_version_queue.scan_incomplete
            ):
                base["outcome"] = "blocked"
                return _finish_migration_result(base, started_ns)
            base["pending_v2"] = (
                next_version_queue.ready + next_version_queue.claimed
            )
    except (TelemetryQueueError, OSError, ValueError):
        base["outcome"] = "blocked"
        return _finish_migration_result(base, started_ns)
    base["outcome"] = outcome
    return _finish_migration_result(base, started_ns)


def _writer_state_matches_snapshot(state: WriterState | None, snapshot: Any) -> bool:
    return state is not None and (
        state.phase == "stopped"
        and state.reason is None
        and state.store_state == "compatible"
        and state.store_schema_version == snapshot.schema_version
        and state.persisted_runs_snapshot == snapshot.persisted_runs_snapshot
        and state.database_device == snapshot.database_device
        and state.database_inode == snapshot.database_inode
        and state.database_bytes == snapshot.database_bytes
    )


def _publish_exact_store_state(
    runtime: _WriterRuntime,
    snapshot: Any,
    *,
    durability_degraded: bool,
) -> bool:
    state = replace(
        runtime.state,
        phase="stopped",
        reason=None,
        heartbeat_unix_ms=_time_unix_ms(),
        store_state="compatible",
        store_schema_version=snapshot.schema_version,
        persisted_runs_snapshot=snapshot.persisted_runs_snapshot,
        database_device=snapshot.database_device,
        database_inode=snapshot.database_inode,
        database_bytes=snapshot.database_bytes,
        durability_degraded=(
            runtime.state.durability_degraded or durability_degraded
        ),
    )
    try:
        if not write_writer_state(state, paths=runtime.paths):
            return False
        observed = read_writer_state(runtime.paths)
    except (TelemetryQueueError, OSError, ValueError):
        return False
    if observed != state:
        return False
    runtime.state = state
    return True


def _finish_migration_result(
    value: dict[str, object],
    started_ns: int,
) -> dict[str, object]:
    value["elapsed_ms"] = _elapsed_ms(started_ns)
    return value


def telemetry_migrate_command(
    *,
    json_output: bool,
    paths: TelemetryPaths | None = None,
) -> CommandResult:
    value = telemetry_migrate(paths=paths)
    outcome = value["outcome"]
    exit_code = 0 if outcome in {"absent", "already_current", "migrated"} else (
        1 if outcome == "busy" else 2
    )
    return CommandResult(
        exit_code=exit_code,
        output=(
            _canonical_json(value)
            if json_output
            else _migration_text(value)
        ),
    )


def run_writer(paths: TelemetryPaths | None = None) -> int:
    """Elect and run one bounded writer; an extra writer exits successfully."""

    selected = paths or telemetry_paths(Path.cwd())
    lifetime = writer_lifetime_lock(selected, timeout_ms=0)
    held = False
    try:
        try:
            lifetime.__enter__()
            held = True
        except QueueLockTimeout:
            return 0
        except (TelemetryQueueError, OSError, ValueError):
            return 1

        def release_lifetime() -> None:
            nonlocal held
            if held:
                lifetime.__exit__(None, None, None)
                held = False

        runtime = _WriterRuntime(selected, release_lifetime)
        return runtime.run()
    finally:
        if held:
            lifetime.__exit__(None, None, None)


def main(argv: list[str] | None = None) -> int:
    """Run only from the verified telemetry cwd with the private umask first."""

    os.umask(0o077)
    arguments = sys.argv[1:] if argv is None else argv
    if arguments:
        return 2
    return run_writer(telemetry_paths(Path.cwd()))


class _WriterRuntime:
    def __init__(
        self,
        paths: TelemetryPaths,
        release_lifetime: Any,
        *,
        enforce_drain_deadline: bool = True,
    ) -> None:
        self.paths = telemetry_paths(paths.directory)
        self.paths_v2 = telemetry_paths_v2(paths.directory)
        self.paths_v3 = telemetry_paths_v3(paths.directory)
        self.queue_paths = (self.paths, self.paths_v2, self.paths_v3)
        self.release_lifetime = release_lifetime
        self.elected_ns = time.monotonic_ns()
        self.enforce_drain_deadline = enforce_drain_deadline
        self.last_heartbeat_ns = 0
        self.receipt_failure = False
        self.state = self._initial_state()

    def _initial_state(self) -> WriterState:
        try:
            prior = read_writer_state(self.paths) or WriterState()
        except (TelemetryQueueError, OSError, ValueError):
            prior = WriterState(accounting_incomplete=True)
        return replace(
            prior,
            phase="starting",
            reason=None,
            heartbeat_unix_ms=_time_unix_ms(),
        )

    def run(self) -> int:
        try:
            self._persist_state(force=True)
            self._clear_start_lease()
            for queue_paths in self.queue_paths:
                queue_snapshot = scan_queue_read_only(queue_paths)
                if (
                    queue_snapshot.unsafe
                    or queue_snapshot.unreadable
                    or queue_snapshot.scan_incomplete
                ):
                    raise UnsafePathError("telemetry queue is unsafe")
                if not queue_snapshot.present:
                    continue
                self._recover_receipts_and_claims(queue_paths)
                try:
                    cleanup_stale_envelope_temporaries(paths=queue_paths)
                except (TelemetryQueueError, OSError, ValueError):
                    self.state = replace(
                        self.state, accounting_incomplete=True
                    )
            idle_since_ns: int | None = None
            while True:
                self._persist_state()
                snapshots = tuple(
                    scan_queue_read_only(queue_paths)
                    for queue_paths in self.queue_paths
                )
                if any(
                    snapshot.unsafe
                    or snapshot.unreadable
                    or snapshot.scan_incomplete
                    for snapshot in snapshots
                ):
                    self._block("queue_unsafe", "unsafe")
                    return 1
                if self._drain_deadline_reached():
                    if self._stop_with_reason(
                        "retry_deadline",
                        self.state.store_state,
                    ):
                        return 0
                    continue
                ready_queue = next(
                    (
                        queue_paths
                        for queue_paths, snapshot in zip(
                            self.queue_paths, snapshots, strict=True
                        )
                        if snapshot.ready
                    ),
                    None,
                )
                if ready_queue is not None:
                    idle_since_ns = None
                    self.state = replace(
                        self.state,
                        phase="draining",
                        reason=None,
                    )
                    names = claim_ready_batch(ready_queue, CLAIM_BATCH_SIZE)
                    for source_name in names:
                        if self._drain_deadline_reached():
                            if self._stop_with_reason(
                                "retry_deadline",
                                self.state.store_state,
                            ):
                                return 0
                            break
                        if not self._process_claim(source_name, ready_queue):
                            return 0
                    continue
                if any(snapshot.claimed for snapshot in snapshots):
                    self._block("receipt_failure", self.state.store_state)
                    return 0
                if self.receipt_failure:
                    self._block("receipt_failure", self.state.store_state)
                    return 0
                now_ns = time.monotonic_ns()
                if idle_since_ns is None:
                    idle_since_ns = now_ns
                    self.state = replace(self.state, phase="idle", reason=None)
                    self._persist_state(force=True)
                if now_ns - idle_since_ns >= int(IDLE_EXIT_SECONDS * 1_000_000_000):
                    if self._stop_if_still_idle():
                        return 0
                    idle_since_ns = None
                    continue
                time.sleep(INBOX_POLL_SECONDS)
        except _ReceiptProofDeferred:
            return 0
        except UnsupportedPlatformError:
            return 1
        except (UnsafePathError, UnreadablePathError, TelemetryQueueError, OSError):
            try:
                self._block("queue_unsafe", "unsafe")
            except Exception:
                pass
            return 1

    def _clear_start_lease(self) -> None:
        """Remove the spawn lease before work or a stopped transition.

        Publishing the fresh ``starting`` heartbeat first prevents a producer
        from establishing a new lease while the elected writer retries the
        bounded start-lock operation.
        """

        deadline_ns = time.monotonic_ns() + int(
            START_LEASE_SECONDS * 1_000_000_000
        )
        while True:
            durable = clear_writer_start_lease(self.paths)
            lease = read_writer_start_lease(self.paths)
            if lease is None:
                if not durable:
                    self.state = replace(
                        self.state,
                        durability_degraded=True,
                    )
                    self._persist_state(force=True)
                return
            if time.monotonic_ns() >= deadline_ns:
                # Do not let a permanently undeletable fixed lease turn the
                # detached writer into an unbounded process.  The original
                # lease is no longer a valid spawn-suppression authority by
                # this point, and the outer runtime records a fail-closed
                # unsafe state before releasing lifetime authority.
                raise UnsafePathError("writer start lease could not be cleared")
            self._persist_state()
            time.sleep(0.005)

    def _recover_receipts_and_claims(self, paths: TelemetryPaths) -> None:
        for temporary_name in inspect_receipt_temporaries(paths):
            proven = False
            receipt: TerminalReceipt | None = None
            try:
                receipt = read_terminal_receipt_temporary(
                    paths,
                    temporary_name,
                )
                proven = self._terminal_receipt_proven(receipt, paths)
            except (TelemetryQueueError, OSError, ValueError):
                proven = False
            finalized = resolve_receipt_temporary(
                paths,
                temporary_name,
                terminal_condition_proven=proven,
            )
            if finalized and receipt is not None:
                acknowledge_claim(paths, receipt.source_name)
            self._persist_state()

        snapshot = scan_queue_read_only(paths)
        if snapshot.unsafe or snapshot.unreadable or snapshot.scan_incomplete:
            raise UnsafePathError("telemetry queue is unsafe")
        for source_name in snapshot.claimed_names:
            receipt = read_terminal_receipt(source_name, paths=paths)
            if receipt is None:
                self._persist_state()
                continue
            if self._terminal_receipt_proven(receipt, paths):
                acknowledge_claim(paths, source_name)
            else:
                self.receipt_failure = True
            self._persist_state()
        remaining = scan_queue_read_only(paths)
        if remaining.unsafe or remaining.unreadable or remaining.scan_incomplete:
            raise UnsafePathError("telemetry queue is unsafe")
        for source_name in remaining.claimed_names:
            if recover_claim(paths, source_name):
                self.state = _increment_state_counter(
                    self.state,
                    "recovered_claims",
                )
                self._persist_state(force=True)
        self._reconcile_state(paths)
        self._persist_state(force=True)

    def _terminal_receipt_proven(
        self,
        receipt: TerminalReceipt,
        paths: TelemetryPaths,
    ) -> bool:
        try:
            claim = read_claimed_envelope(paths, receipt.source_name)
        except (TelemetryQueueError, OSError, ValueError):
            return False
        if (
            claim.envelope_bytes != receipt.envelope_bytes
            or claim.digest_complete != receipt.digest_complete
            or claim.envelope_sha256 != receipt.envelope_sha256
        ):
            return False
        if receipt.kind == "rejected":
            if claim.oversized:
                return receipt.reason == "oversized"
            assert claim.payload is not None
            try:
                _decode_envelope(receipt.schema_version, claim.payload)
            except TraceEnvelopeError as exc:
                return receipt.reason == exc.reason
            except Exception:
                return False
            return False
        if claim.oversized or claim.payload is None:
            return False
        try:
            rows = _decode_envelope(receipt.schema_version, claim.payload)
        except TraceEnvelopeError:
            return False
        except Exception:
            return False
        store = _load_store_module()
        started_ns = time.monotonic_ns()
        while True:
            try:
                result = store.inspect_trace_terminal(self.paths_v3, rows)
                break
            except store.StoreTerminalAbsentError:
                return False
            except store.StoreIncompatibleError:
                self._record_store_failure("incompatible")
                self._block("database_incompatible", "incompatible")
                raise _ReceiptProofDeferred
            except store.StoreUnsafeError:
                self._record_store_failure("unsafe")
                self._block("unsafe_path", "unsafe")
                raise _ReceiptProofDeferred
            except store.StoreBusyError:
                reason = "database_busy"
                store_state = "busy"
                self._record_store_failure(store_state)
            except (store.StoreUnreadableError, store.StoreWriteError):
                reason = "database_unreadable"
                store_state = "unreadable"
                self._record_store_failure(store_state)
            if (
                time.monotonic_ns() - started_ns
                >= int(DATABASE_RETRY_WINDOW_SECONDS * 1_000_000_000)
                or self._drain_deadline_reached()
            ):
                self.state = _increment_state_counter(
                    self.state,
                    "write_failures",
                )
                if reason == "database_busy":
                    while not self._stop_with_reason(reason, store_state):
                        self._persist_state(force=True)
                        time.sleep(DATABASE_RETRY_SECONDS)
                else:
                    self._block(reason, store_state)
                raise _ReceiptProofDeferred
            self.state = replace(
                self.state,
                phase="draining",
                reason=reason,
                store_state=store_state,
            )
            self._persist_state(force=True)
            time.sleep(DATABASE_RETRY_SECONDS)
        self._apply_store_result(result, committed=False)
        if receipt.kind in {"committed", "replayed"}:
            return result.outcome == "replayed"
        return receipt.kind == "conflict" and result.outcome == "conflict"

    def _process_claim(
        self,
        source_name: str,
        paths: TelemetryPaths,
    ) -> bool:
        try:
            claim = read_claimed_envelope(paths, source_name)
        except (TelemetryQueueError, OSError, ValueError):
            self._block("queue_unsafe", "unsafe")
            return False
        if claim.oversized:
            receipt = TerminalReceipt(
                paths.queue_version,
                "rejected",
                source_name,
                None,
                False,
                claim.envelope_bytes,
                _time_unix_ms(),
                "oversized",
            )
            self._publish_and_ack(receipt, paths)
            return True

        assert claim.payload is not None
        try:
            rows = _decode_envelope(paths.queue_version, claim.payload)
        except TraceEnvelopeError as exc:
            receipt = TerminalReceipt(
                paths.queue_version,
                "rejected",
                source_name,
                claim.envelope_sha256,
                True,
                claim.envelope_bytes,
                _time_unix_ms(),
                exc.reason,
            )
            self._publish_and_ack(receipt, paths)
            return True
        except Exception:
            self._block("receipt_failure", self.state.store_state)
            return False

        result = self._append_with_retry(rows, paths=paths)
        if result is None:
            if self.state.reason == "upgrade_required":
                try:
                    recover_claim(paths, source_name)
                except (TelemetryQueueError, OSError, ValueError):
                    pass
            return False
        self._apply_store_result(result, committed=result.outcome == "committed")
        kind: ReceiptKind = result.outcome
        reason = None
        if result.outcome == "conflict":
            kind = "conflict"
            reason = "trace_conflict"
        receipt = TerminalReceipt(
            paths.queue_version,
            kind,
            source_name,
            claim.envelope_sha256,
            True,
            claim.envelope_bytes,
            _time_unix_ms(),
            reason,
        )
        self._publish_and_ack(receipt, paths)
        return True

    def _append_with_retry(
        self,
        rows: TraceRows | CommandTraceRows | CommandTraceRowsV3,
        *,
        paths: TelemetryPaths | None = None,
    ) -> Any | None:
        del paths
        selected_paths = self.paths_v3
        store = _load_store_module()
        started_ns = time.monotonic_ns()
        while True:
            try:
                return store.append_trace(selected_paths, rows)
            except getattr(store, "StoreUpgradeRequiredError", ()):
                try:
                    current_version = store.inspect_store_schema_version(selected_paths)
                except Exception:
                    current_version = None
                self.state = replace(
                    self.state,
                    store_state="upgrade_required",
                    store_schema_version=current_version,
                )
                self._block("upgrade_required", "upgrade_required")
                return None
            except store.StoreIncompatibleError:
                self._record_store_failure("incompatible")
                self._block("database_incompatible", "incompatible")
                return None
            except store.StoreUnsafeError:
                self._record_store_failure("unsafe")
                self._block("unsafe_path", "unsafe")
                return None
            except store.StoreBusyError:
                reason = "database_busy"
                store_state = "busy"
                self._record_store_failure(store_state)
            except store.StoreUnreadableError:
                reason = "database_unreadable"
                store_state = "unreadable"
                self._record_store_failure(store_state)
            except store.StoreWriteError:
                reason = "retry_deadline"
                store_state = self.state.store_state
            if (
                time.monotonic_ns() - started_ns
                >= int(DATABASE_RETRY_WINDOW_SECONDS * 1_000_000_000)
                or self._drain_deadline_reached()
            ):
                self.state = _increment_state_counter(
                    self.state,
                    "write_failures",
                )
                if reason in {"database_busy", "retry_deadline"}:
                    while not self._stop_with_reason(reason, store_state):
                        self._persist_state(force=True)
                        time.sleep(DATABASE_RETRY_SECONDS)
                else:
                    self._block(reason, store_state)
                return None
            self.state = replace(
                self.state,
                phase="draining",
                reason=reason,
                store_state=store_state,
            )
            self._persist_state(force=True)
            time.sleep(DATABASE_RETRY_SECONDS)

    def _record_store_failure(self, store_state: str) -> None:
        metadata = _safe_database_metadata(self.paths)
        device = metadata.st_dev if metadata is not None else None
        inode = metadata.st_ino if metadata is not None else None
        size = metadata.st_size if metadata is not None else None
        preserve_snapshot = (
            store_state == "busy"
            and metadata is not None
            and self.state.database_device == metadata.st_dev
            and self.state.database_inode == metadata.st_ino
            and self.state.database_bytes == metadata.st_size
        )
        self.state = replace(
            self.state,
            store_state=store_state,
            store_schema_version=(
                self.state.store_schema_version if preserve_snapshot else None
            ),
            persisted_runs_snapshot=(
                self.state.persisted_runs_snapshot if preserve_snapshot else None
            ),
            database_device=device,
            database_inode=inode,
            database_bytes=size,
            last_writer_commit_unix_ms=(
                self.state.last_writer_commit_unix_ms
                if preserve_snapshot
                else None
            ),
        )

    def _drain_deadline_reached(self) -> bool:
        return self.enforce_drain_deadline and (
            time.monotonic_ns() - self.elected_ns >= int(
                DRAIN_DEADLINE_SECONDS * 1_000_000_000
            )
        )

    def _publish_and_ack(
        self,
        receipt: TerminalReceipt,
        paths: TelemetryPaths,
    ) -> None:
        try:
            publication = publish_terminal_receipt(paths, receipt)
            if publication.durability_degraded:
                self.state = replace(self.state, durability_degraded=True)
            acknowledge_claim(paths, receipt.source_name)
            self._reconcile_state(paths)
            self._persist_state(force=True)
        except (TelemetryQueueError, OSError, ValueError):
            self.receipt_failure = True
            self.state = replace(self.state, reason="receipt_failure")

    def _apply_store_result(self, result: Any, *, committed: bool) -> None:
        snapshot = result.snapshot
        self.state = replace(
            self.state,
            store_state="compatible",
            store_schema_version=snapshot.schema_version,
            persisted_runs_snapshot=snapshot.persisted_runs_snapshot,
            database_device=snapshot.database_device,
            database_inode=snapshot.database_inode,
            database_bytes=snapshot.database_bytes,
            last_writer_commit_unix_ms=(
                _time_unix_ms()
                if committed
                else self.state.last_writer_commit_unix_ms
            ),
            durability_degraded=(
                self.state.durability_degraded or result.durability_degraded
            ),
        )

    def _reconcile_state(
        self,
        paths: TelemetryPaths | None = None,
    ) -> None:
        try:
            selected = self.queue_paths
            self.state = reconcile_writer_receipts_shared(
                self.state,
                paths=selected,
            )
        except (TelemetryQueueError, OSError, ValueError):
            self.state = replace(self.state, accounting_incomplete=True)

    def _persist_state(self, *, force: bool = False) -> None:
        now_ns = time.monotonic_ns()
        if not force and (
            now_ns - self.last_heartbeat_ns
            < int(HEARTBEAT_INTERVAL_SECONDS * 1_000_000_000)
        ):
            return
        self.state = replace(
            self.state,
            heartbeat_unix_ms=_time_unix_ms(),
        )
        durable = write_writer_state(self.state, paths=self.paths)
        self.last_heartbeat_ns = now_ns
        if not durable and not self.state.durability_degraded:
            self.state = replace(self.state, durability_degraded=True)
            write_writer_state(self.state, paths=self.paths)

    def _block(self, reason: str, store_state: str) -> None:
        self.state = replace(
            self.state,
            phase="blocked",
            reason=reason,
            store_state=store_state,
        )
        self._persist_state(force=True)

    def _stop_with_reason(self, reason: str, store_state: str) -> bool:
        start_authority = writer_start_lock(self.paths)
        try:
            start_authority.__enter__()
        except QueueLockTimeout:
            # Keep lifetime authority and retry the stopped transition.  A
            # producer can therefore never suppress a spawn immediately
            # before this writer releases its lifetime lock.
            return False
        try:
            self.state = replace(
                self.state,
                phase="stopped",
                reason=reason,
                store_state=store_state,
            )
            self._persist_state(force=True)
            self.release_lifetime()
            return True
        finally:
            start_authority.__exit__(None, None, None)

    def _stop_if_still_idle(self) -> bool:
        start_authority = writer_start_lock(self.paths)
        try:
            start_authority.__enter__()
        except QueueLockTimeout:
            return False
        try:
            snapshots = tuple(
                scan_queue_read_only(queue_paths)
                for queue_paths in self.queue_paths
            )
            if any(
                snapshot.unsafe
                or snapshot.unreadable
                or snapshot.scan_incomplete
                for snapshot in snapshots
            ):
                self._block("queue_unsafe", "unsafe")
                return True
            if any(
                snapshot.ready or snapshot.claimed
                for snapshot in snapshots
            ):
                return False
            self.state = replace(self.state, phase="stopped", reason=None)
            self._persist_state(force=True)
            self.release_lifetime()
            return True
        finally:
            start_authority.__exit__(None, None, None)


def _inspect_store(
    paths: TelemetryPaths,
    state: WriterState | None,
) -> _StoreInspection:
    try:
        root_fd = open_verified_directory(paths.directory, repair_mode=False)
    except FileNotFoundError:
        return _StoreInspection("absent", None, None, None, None)
    except UnsafePathError:
        return _StoreInspection("unsafe", None, None, None, None)
    except (UnreadablePathError, OSError):
        return _StoreInspection("unreadable", None, None, None, None)
    try:
        scratch = _inspect_initialization_scratch(root_fd)
        migration_scratch_present = _inspect_migration_scratch(root_fd)
        backups: list[os.stat_result] = []
        for backup_name in ("telemetry-v1-backup.duckdb", "telemetry-v2-backup.duckdb"):
            try:
                backups.append(stat_private_entry_at(
                    root_fd, backup_name, kind="file", allowed_nlinks=(1, 2)
                ))
            except FileNotFoundError:
                continue
        try:
            database = stat_private_entry_at(
                root_fd,
                "telemetry.duckdb",
                kind="file",
                allowed_nlinks=(1, 2),
            )
        except FileNotFoundError:
            database = None
        try:
            wal = stat_private_entry_at(
                root_fd,
                "telemetry.duckdb.wal",
                kind="file",
                max_bytes=DATABASE_WAL_MAX_BYTES,
            )
        except FileNotFoundError:
            wal = None
    except UnsafePathError:
        return _StoreInspection("unsafe", None, None, None, None)
    except (UnreadablePathError, OSError):
        return _StoreInspection("unreadable", None, None, None, None)
    finally:
        os.close(root_fd)
    if any(backup.st_nlink == 2 for backup in backups) and not migration_scratch_present:
        return _StoreInspection("unsafe", None, None, None, None)
    if database is None:
        if scratch.database is not None and scratch.database.st_nlink != 1:
            return _StoreInspection("unsafe", None, None, None, None)
        if (
            scratch.present
            or backups
            or migration_scratch_present
        ) and wal is None:
            return _StoreInspection(
                "present_unverified", None, None, None, None
            )
        return _StoreInspection(
            "unsafe" if wal is not None else "absent",
            None,
            None,
            None,
            None,
        )
    if database.st_nlink == 2:
        scratch_database = scratch.database
        if (
            scratch_database is None
            or scratch_database.st_nlink != 2
            or (scratch_database.st_dev, scratch_database.st_ino)
            != (database.st_dev, database.st_ino)
        ):
            return _StoreInspection("unsafe", None, None, None, None)
    elif scratch.database is not None and scratch.database.st_nlink != 1:
        return _StoreInspection("unsafe", None, None, None, None)
    if wal is not None:
        return _StoreInspection(
            "present_unverified", None, database.st_size, None, None
        )
    if migration_scratch_present:
        return _StoreInspection(
            "present_unverified", None, database.st_size, None, None
        )
    if scratch.present:
        return _StoreInspection(
            "present_unverified", None, database.st_size, None, None
        )
    metadata_matches = state is not None and (
        state.database_device == database.st_dev
        and state.database_inode == database.st_ino
        and state.database_bytes == database.st_size
    )
    if metadata_matches and state is not None:
        observed_state = state.store_state
        if observed_state in {
            "compatible",
            "upgrade_required",
            "incompatible",
            "busy",
            "unreadable",
            "unsafe",
        }:
            return _StoreInspection(
                observed_state,
                state.store_schema_version,
                database.st_size,
                state.persisted_runs_snapshot,
                state.last_writer_commit_unix_ms,
            )
    return _StoreInspection(
        "present_unverified",
        None,
        database.st_size,
        None,
        None,
    )


def _inspect_initialization_scratch(
    root_fd: int,
) -> _InitializationScratchInspection:
    try:
        scratch_fd = open_private_directory_at(
            root_fd,
            "database-init-v1",
            create=False,
            repair_mode=False,
        )
    except FileNotFoundError:
        return _InitializationScratchInspection(False)
    try:
        names: set[str] = set()
        with os.scandir(scratch_fd) as iterator:
            for entry in iterator:
                if entry.name not in {"telemetry.duckdb", "telemetry.duckdb.wal"}:
                    raise UnsafePathError(
                        "telemetry initialization path is unsafe"
                    )
                names.add(entry.name)
        database = (
            stat_private_entry_at(
                scratch_fd,
                "telemetry.duckdb",
                kind="file",
                max_bytes=DATABASE_WAL_MAX_BYTES,
                allowed_nlinks=(1, 2),
            )
            if "telemetry.duckdb" in names
            else None
        )
        wal = (
            stat_private_entry_at(
                scratch_fd,
                "telemetry.duckdb.wal",
                kind="file",
                max_bytes=DATABASE_WAL_MAX_BYTES,
            )
            if "telemetry.duckdb.wal" in names
            else None
        )
        return _InitializationScratchInspection(True, database, wal)
    finally:
        os.close(scratch_fd)


def _migration_backup_present(paths: TelemetryPaths) -> bool:
    """Inspect only fixed backup metadata; never open DuckDB."""

    try:
        root_fd = open_verified_directory(paths.directory, repair_mode=False)
    except (FileNotFoundError, UnsafePathError, UnreadablePathError, OSError):
        return False
    try:
        for name in ("telemetry-v2-backup.duckdb", "telemetry-v1-backup.duckdb"):
            try:
                stat_private_entry_at(root_fd, name, kind="file")
            except FileNotFoundError:
                continue
            return True
        return False
    except (UnsafePathError, UnreadablePathError, OSError):
        return False
    finally:
        os.close(root_fd)


def _inspect_migration_scratch(root_fd: int) -> bool:
    present = False
    for directory_name, allowed, backup_name in (
        ("database-migrate-v2", _MIGRATION_SCRATCH_NAMES, "telemetry-v1-backup.duckdb"),
        ("database-migrate-v3", _MIGRATION_V3_SCRATCH_NAMES, "telemetry-v2-backup.duckdb"),
    ):
        try:
            scratch_fd = open_private_directory_at(
                root_fd, directory_name, create=False, repair_mode=False
            )
        except FileNotFoundError:
            continue
        present = True
        try:
            names = scan_fixed_private_inventory(scratch_fd, allowed_names=allowed)
            for name in names:
                observed = stat_private_entry_at(
                    scratch_fd,
                    name,
                    kind="file",
                    max_bytes=(
                        DATABASE_WAL_MAX_BYTES
                        if name == "telemetry.duckdb.wal"
                        else None
                    ),
                    allowed_nlinks=(1, 2) if name == backup_name else (1,),
                )
                if name == backup_name and observed.st_nlink == 2:
                    final = stat_private_entry_at(root_fd, name, kind="file", allowed_nlinks=(2,))
                    if (observed.st_dev, observed.st_ino) != (final.st_dev, final.st_ino):
                        raise UnsafePathError("telemetry migration backup publication is unsafe")
        finally:
            os.close(scratch_fd)
    return present


def _safe_database_metadata(paths: TelemetryPaths) -> os.stat_result | None:
    """Return only verified fixed-file metadata, never database contents."""

    try:
        root_fd = open_verified_directory(paths.directory, repair_mode=False)
    except (FileNotFoundError, UnsafePathError, UnreadablePathError, OSError):
        return None
    try:
        try:
            return stat_private_entry_at(
                root_fd,
                "telemetry.duckdb",
                kind="file",
            )
        except (
            FileNotFoundError,
            UnsafePathError,
            UnreadablePathError,
            OSError,
        ):
            return None
    finally:
        os.close(root_fd)


def _flush_result(
    outcome: str,
    snapshot: int,
    terminal: Mapping[str, ReceiptKind],
    pending: int,
    elapsed_ms: int,
) -> dict[str, object]:
    counts = {
        kind: sum(1 for value in terminal.values() if value == kind)
        for kind in ("committed", "replayed", "rejected", "conflict")
    }
    return {
        "schema_version": 3,
        "outcome": outcome,
        "snapshot": snapshot,
        "committed": counts["committed"],
        "replayed": counts["replayed"],
        "rejected": counts["rejected"],
        "conflicts": counts["conflict"],
        "pending": pending,
        "elapsed_ms": elapsed_ms,
    }


def _status_text(value: Mapping[str, object]) -> str:
    store = value["store"]
    queue = value["queue"]
    writer = value["writer"]
    accounting = value["accounting"]
    assert isinstance(store, Mapping)
    assert isinstance(queue, Mapping)
    assert isinstance(writer, Mapping)
    assert isinstance(accounting, Mapping)
    return "\n".join(
        (
            "Telemetry: "
            f"overall={value['overall']} requested={_text(value['requested'])} "
            f"effective={_text(value['effective'])} "
            f"reason={value['enablement_reason']}",
            "Store: "
            f"state={store['state']} schema_version={_text(store['schema_version'])} "
            f"bytes={_text(store['bytes'])} "
            f"persisted_runs_snapshot={_text(store['persisted_runs_snapshot'])} "
            f"last_writer_commit_unix_ms={_text(store['last_writer_commit_unix_ms'])}",
            "Queue: "
            f"state={queue['state']} ready={queue['ready']} "
            f"claimed={queue['claimed']} temporary={queue['temporary']} "
            f"receipts={queue['receipts']} pending_bytes={queue['pending_bytes']} "
            f"oldest_pending_age_ms={_text(queue['oldest_pending_age_ms'])} "
            f"capacity_full={_text(queue['capacity_full'])} "
            f"scan_incomplete={_text(queue['scan_incomplete'])} "
            f"v1_ready={queue['v1_ready']} "
            f"v1_claimed={queue['v1_claimed']} "
            f"v2_ready={queue['v2_ready']} "
            f"v2_claimed={queue['v2_claimed']} "
            f"v3_ready={queue['v3_ready']} "
            f"v3_claimed={queue['v3_claimed']} "
            f"migration_backup_present="
            f"{_text(value['migration_backup_present'])}",
            "Writer: "
            f"state={writer['state']} reason={_text(writer['reason'])} "
            f"heartbeat_age_ms={_text(writer['heartbeat_age_ms'])}",
            "Accounting: "
            + " ".join(
                f"{key}={_text(accounting[key])}"
                for key in (
                    "producer_dropped_lower_bound",
                    "queue_full",
                    "queue_lock_timeout",
                    "publication_failure",
                    "directory_sync_failure",
                    "writer_start_failure",
                    "rejected",
                    "conflicts",
                    "replays",
                    "recovered_claims",
                    "write_failures",
                    "receipts_rotated",
                    "durability_degraded",
                    "incomplete",
                )
            ),
        )
    )


def _flush_text(value: Mapping[str, object]) -> str:
    return (
        f"Telemetry flush: outcome={value['outcome']} snapshot={value['snapshot']} "
        f"committed={value['committed']} replayed={value['replayed']} "
        f"rejected={value['rejected']} conflicts={value['conflicts']} "
        f"pending={value['pending']} elapsed_ms={value['elapsed_ms']}"
    )


def _migration_text(value: Mapping[str, object]) -> str:
    return (
        "Telemetry migrate: "
        f"schema_version={value['schema_version']} "
        f"database_path={value['database_path']} "
        f"outcome={value['outcome']} "
        f"source_schema_version={_text(value['source_schema_version'])} "
        f"target_schema_version={_text(value['target_schema_version'])} "
        f"migrated_v1_runs={value['migrated_v1_runs']} "
        f"migrated_v1_spans={value['migrated_v1_spans']} "
        f"migrated_v1_events={value['migrated_v1_events']} "
        f"pending_v2={value['pending_v2']} "
        f"backup_present={_text(value['backup_present'])} "
        f"elapsed_ms={value['elapsed_ms']}"
    )


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _text(value: object) -> str:
    if value is None:
        return "null"
    if type(value) is bool:
        return "true" if value else "false"
    return str(value)


def _source_name_for_receipt_name(receipt_name: str) -> str:
    if not (
        receipt_name[:3] in {"r1-", "r2-", "r3-"}
        and receipt_name.endswith(".json")
        and len(receipt_name) == 40
    ):
        raise ValueError("recognized receipt name required")
    return f"v{receipt_name[1]}-{receipt_name[3:-5]}.json"


def _decode_envelope(
    version: int,
    payload: bytes,
) -> TraceRows | CommandTraceRows | CommandTraceRowsV3:
    if version == 1:
        return decode_trace_envelope_v1(payload)
    if version == 2:
        return decode_trace_envelope_v2(payload)
    if version == 3:
        return decode_trace_envelope_v3(payload)
    raise TraceEnvelopeError("unsupported_envelope_version")


def _increment_state_counter(
    state: WriterState,
    field: str,
    amount: int = 1,
) -> WriterState:
    current = int(getattr(state, field))
    incomplete = state.accounting_incomplete or current > COUNTER_MAX - amount
    return replace(
        state,
        **{
            field: min(COUNTER_MAX, current + amount),
            "accounting_incomplete": incomplete,
        },
    )


def _load_store_module() -> ModuleType:
    from buoy_search.telemetry import store as telemetry_store

    return telemetry_store


def _time_unix_ms() -> int:
    return time.time_ns() // 1_000_000


def _elapsed_ms(started_ns: int) -> int:
    return max(0, (time.monotonic_ns() - started_ns) // 1_000_000)


if __name__ == "__main__":
    raise SystemExit(main())
