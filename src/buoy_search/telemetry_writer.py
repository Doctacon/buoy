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

from buoy_search.telemetry_envelope import (
    TraceEnvelopeError,
    TraceRows,
    decode_trace_envelope_v1,
)
from buoy_search.telemetry_queue import (
    COUNTER_MAX,
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
    cleanup_stale_envelope_temporaries,
    clear_writer_start_lease,
    inspect_receipt_temporaries,
    open_private_directory_at,
    open_verified_directory,
    posix_writer_capability,
    publish_terminal_receipt,
    read_claimed_envelope,
    read_producer_accounting,
    read_terminal_receipt,
    read_terminal_receipt_temporary,
    read_writer_start_lease,
    read_writer_state,
    reconcile_writer_receipts,
    recover_claim,
    request_writer_start,
    resolve_receipt_temporary,
    scan_queue_read_only,
    snapshot_pending,
    stat_private_entry_at,
    telemetry_paths,
    terminal_kind_for_snapshot_item,
    write_writer_state,
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


def telemetry_status(
    *,
    paths: TelemetryPaths | None = None,
    environment: Mapping[str, str] | None = None,
    now_unix_ms: int | None = None,
) -> dict[str, object]:
    """Return the exact read-only, content-free status object."""

    selected = paths or telemetry_paths()
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

    queue = scan_queue_read_only(selected)
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
        for receipt_name in queue.receipt_names:
            if receipt_name in accounted:
                continue
            source_name = _source_name_for_receipt_name(receipt_name)
            try:
                receipt = read_terminal_receipt(source_name, paths=selected)
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
            writer_state == "blocked",
            receipt_read_failed,
        )
    )
    degraded = any(
        (
            queue_state in {"backlog", "full"},
            queue.scan_incomplete,
            writer_state == "stale",
            store.state in {"present_unverified", "busy"},
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
        "schema_version": 1,
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
        },
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
    selected = paths or telemetry_paths()
    if not posix_writer_capability().supported:
        return _flush_result(
            "blocked", 0, {}, 0, _elapsed_ms(started_ns)
        )
    try:
        snapshot = snapshot_pending(selected)
    except (TelemetryQueueError, OSError, ValueError):
        return _flush_result(
            "blocked", 0, {}, 0, _elapsed_ms(started_ns)
        )
    total = len(snapshot.items)
    initial_status = telemetry_status(paths=selected)
    if initial_status["overall"] == "blocked":
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
        for item in snapshot.items:
            if item.source_name in terminal:
                continue
            try:
                kind = terminal_kind_for_snapshot_item(selected, item)
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
        status = telemetry_status(paths=selected)
        if status["overall"] == "blocked":
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
    ) -> None:
        self.paths = paths
        self.release_lifetime = release_lifetime
        self.elected_ns = time.monotonic_ns()
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
            self._recover_receipts_and_claims()
            try:
                cleanup_stale_envelope_temporaries(paths=self.paths)
            except (TelemetryQueueError, OSError, ValueError):
                self.state = replace(self.state, accounting_incomplete=True)
            idle_since_ns: int | None = None
            while True:
                self._persist_state()
                snapshot = scan_queue_read_only(self.paths)
                if snapshot.unsafe or snapshot.unreadable:
                    self._block("queue_unsafe", "unsafe")
                    return 1
                if self._drain_deadline_reached():
                    if self._stop_with_reason(
                        "retry_deadline",
                        self.state.store_state,
                    ):
                        return 0
                    continue
                if snapshot.ready:
                    idle_since_ns = None
                    self.state = replace(
                        self.state,
                        phase="draining",
                        reason=None,
                    )
                    names = claim_ready_batch(self.paths, CLAIM_BATCH_SIZE)
                    for source_name in names:
                        if self._drain_deadline_reached():
                            if self._stop_with_reason(
                                "retry_deadline",
                                self.state.store_state,
                            ):
                                return 0
                            break
                        if not self._process_claim(source_name):
                            return 0
                    continue
                if snapshot.claimed:
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

    def _recover_receipts_and_claims(self) -> None:
        for temporary_name in inspect_receipt_temporaries(self.paths):
            proven = False
            receipt: TerminalReceipt | None = None
            try:
                receipt = read_terminal_receipt_temporary(
                    self.paths,
                    temporary_name,
                )
                proven = self._terminal_receipt_proven(receipt)
            except (TelemetryQueueError, OSError, ValueError):
                proven = False
            finalized = resolve_receipt_temporary(
                self.paths,
                temporary_name,
                terminal_condition_proven=proven,
            )
            if finalized and receipt is not None:
                acknowledge_claim(self.paths, receipt.source_name)
            self._persist_state()

        snapshot = scan_queue_read_only(self.paths)
        if snapshot.unsafe or snapshot.unreadable:
            raise UnsafePathError("telemetry queue is unsafe")
        for source_name in snapshot.claimed_names:
            receipt = read_terminal_receipt(source_name, paths=self.paths)
            if receipt is None:
                self._persist_state()
                continue
            if self._terminal_receipt_proven(receipt):
                acknowledge_claim(self.paths, source_name)
            else:
                self.receipt_failure = True
            self._persist_state()
        remaining = scan_queue_read_only(self.paths)
        if remaining.unsafe or remaining.unreadable:
            raise UnsafePathError("telemetry queue is unsafe")
        for source_name in remaining.claimed_names:
            if recover_claim(self.paths, source_name):
                self.state = _increment_state_counter(
                    self.state,
                    "recovered_claims",
                )
                self._persist_state(force=True)
        self._reconcile_state()
        self._persist_state(force=True)

    def _terminal_receipt_proven(self, receipt: TerminalReceipt) -> bool:
        try:
            claim = read_claimed_envelope(self.paths, receipt.source_name)
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
                decode_trace_envelope_v1(claim.payload)
            except TraceEnvelopeError as exc:
                return receipt.reason == exc.reason
            except Exception:
                return False
            return False
        if claim.oversized or claim.payload is None:
            return False
        try:
            rows = decode_trace_envelope_v1(claim.payload)
        except TraceEnvelopeError:
            return False
        except Exception:
            return False
        store = _load_store_module()
        started_ns = time.monotonic_ns()
        while True:
            try:
                result = store.inspect_trace_terminal(self.paths, rows)
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

    def _process_claim(self, source_name: str) -> bool:
        try:
            claim = read_claimed_envelope(self.paths, source_name)
        except (TelemetryQueueError, OSError, ValueError):
            self._block("queue_unsafe", "unsafe")
            return False
        if claim.oversized:
            receipt = TerminalReceipt(
                1,
                "rejected",
                source_name,
                None,
                False,
                claim.envelope_bytes,
                _time_unix_ms(),
                "oversized",
            )
            self._publish_and_ack(receipt)
            return True

        assert claim.payload is not None
        try:
            rows = decode_trace_envelope_v1(claim.payload)
        except TraceEnvelopeError as exc:
            receipt = TerminalReceipt(
                1,
                "rejected",
                source_name,
                claim.envelope_sha256,
                True,
                claim.envelope_bytes,
                _time_unix_ms(),
                exc.reason,
            )
            self._publish_and_ack(receipt)
            return True
        except Exception:
            self._block("receipt_failure", self.state.store_state)
            return False

        result = self._append_with_retry(rows)
        if result is None:
            return False
        self._apply_store_result(result, committed=result.outcome == "committed")
        kind: ReceiptKind = result.outcome
        reason = None
        if result.outcome == "conflict":
            kind = "conflict"
            reason = "trace_conflict"
        receipt = TerminalReceipt(
            1,
            kind,
            source_name,
            claim.envelope_sha256,
            True,
            claim.envelope_bytes,
            _time_unix_ms(),
            reason,
        )
        self._publish_and_ack(receipt)
        return True

    def _append_with_retry(self, rows: TraceRows) -> Any | None:
        store = _load_store_module()
        started_ns = time.monotonic_ns()
        while True:
            try:
                return store.append_trace(self.paths, rows)
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
        return time.monotonic_ns() - self.elected_ns >= int(
            DRAIN_DEADLINE_SECONDS * 1_000_000_000
        )

    def _publish_and_ack(self, receipt: TerminalReceipt) -> None:
        try:
            publication = publish_terminal_receipt(self.paths, receipt)
            if publication.durability_degraded:
                self.state = replace(self.state, durability_degraded=True)
            acknowledge_claim(self.paths, receipt.source_name)
            self._reconcile_state()
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

    def _reconcile_state(self) -> None:
        try:
            self.state = reconcile_writer_receipts(
                self.state,
                paths=self.paths,
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
            snapshot = scan_queue_read_only(self.paths)
            if snapshot.unsafe or snapshot.unreadable:
                self._block("queue_unsafe", "unsafe")
                return True
            if snapshot.ready:
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
    if database is None:
        if scratch.database is not None and scratch.database.st_nlink != 1:
            return _StoreInspection("unsafe", None, None, None, None)
        if scratch.present and wal is None:
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
        "schema_version": 1,
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
            f"scan_incomplete={_text(queue['scan_incomplete'])}",
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
        receipt_name.startswith("r1-")
        and receipt_name.endswith(".json")
        and len(receipt_name) == 40
    ):
        raise ValueError("recognized receipt name required")
    return f"v1-{receipt_name[3:-5]}.json"


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
    from buoy_search import telemetry_store

    return telemetry_store


def _time_unix_ms() -> int:
    return time.time_ns() // 1_000_000


def _elapsed_ms(started_ns: int) -> int:
    return max(0, (time.monotonic_ns() - started_ns) // 1_000_000)


if __name__ == "__main__":
    raise SystemExit(main())
