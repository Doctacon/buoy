"""Private POSIX filesystem queue for local retrieval telemetry.

This module is deliberately transport-only.  It owns fixed local paths,
descriptor-relative filesystem validation, queue publication, queue movement,
content-free state, and detached writer election/start coordination.  It does
not import OpenTelemetry, DuckDB, the retriever, or the writer/store modules.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, replace
import errno
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import sys
import time
import warnings
from typing import Any, Literal

try:  # The strong queue is intentionally POSIX-only.
    import fcntl
except ImportError:  # pragma: no cover - exercised through the capability gate.
    fcntl = None  # type: ignore[assignment]

from buoy_search.local_paths import default_buoy_home


ENVELOPE_MAX_BYTES = 65_536
PUBLISHED_MAX_ENTRIES = 4_096
PUBLISHED_MAX_BYTES = 67_108_864
TEMP_MAX_ENTRIES = 4_096
TEMP_MAX_BYTES = 67_108_864
RECEIPT_MAX_ENTRIES = 4_096
RECEIPT_MAX_BYTES = 4_194_304
RECEIPT_MAX_FILE_BYTES = 1_024
RECEIPT_MIN_AGE_SECONDS = 121
STALE_ENVELOPE_TEMP_SECONDS = 86_400
STATE_MAX_BYTES = 262_144
ACCOUNTING_MAX_BYTES = 4_096
START_LEASE_MAX_BYTES = 256
START_LEASE_SECONDS = 30
LOCK_TIMEOUT_MS = 250
PUBLICATION_LOCK_TIMEOUT_MS = 500
LOCK_POLL_MS = 5
SCAN_MAX_ENTRIES = 8_193
SCAN_BETWEEN_CALLS_TIMEOUT_MS = 250
COUNTER_MAX = 9_223_372_036_854_775_807

_DIRECTORY_MODE = 0o700
_FILE_MODE = 0o600
_TOKEN_RE = re.compile(r"^[0-9a-f]{32}$")
_ENVELOPE_RE = re.compile(r"^v1-([0-9a-f]{32})\.json$")
_ENVELOPE_TEMP_RE = re.compile(r"^v1-([0-9a-f]{32})\.part$")
_RECEIPT_RE = re.compile(r"^r1-([0-9a-f]{32})\.json$")
_RECEIPT_TEMP_RE = re.compile(r"^r1-([0-9a-f]{32})\.part$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_RECOGNIZED_DIRECTORY_FSYNC_ERRORS = frozenset(
    {
        errno.EINVAL,
        errno.EBADF,
        getattr(errno, "ENOTSUP", errno.EINVAL),
        getattr(errno, "EOPNOTSUPP", errno.EINVAL),
    }
)

WriterPhase = Literal["starting", "idle", "draining", "blocked", "stopped"]
WriterStoreState = Literal[
    "absent", "compatible", "incompatible", "busy", "unreadable", "unsafe"
]
WriterReason = Literal[
    "database_busy",
    "database_incompatible",
    "database_unreadable",
    "unsafe_path",
    "queue_unsafe",
    "receipt_failure",
    "retry_deadline",
]
ReceiptKind = Literal["committed", "replayed", "rejected", "conflict"]
ReceiptReason = Literal[
    "invalid_utf8",
    "invalid_json",
    "noncanonical_json",
    "unsupported_envelope_version",
    "invalid_shape",
    "invalid_value",
    "invalid_graph",
    "oversized",
    "trace_conflict",
]

_WRITER_PHASES = frozenset({"starting", "idle", "draining", "blocked", "stopped"})
_WRITER_STORE_STATES = frozenset(
    {"absent", "compatible", "incompatible", "busy", "unreadable", "unsafe"}
)
_WRITER_REASONS = frozenset(
    {
        "database_busy",
        "database_incompatible",
        "database_unreadable",
        "unsafe_path",
        "queue_unsafe",
        "receipt_failure",
        "retry_deadline",
    }
)
_RECEIPT_KINDS = frozenset({"committed", "replayed", "rejected", "conflict"})
_RECEIPT_REASONS = frozenset(
    {
        "invalid_utf8",
        "invalid_json",
        "noncanonical_json",
        "unsupported_envelope_version",
        "invalid_shape",
        "invalid_value",
        "invalid_graph",
        "oversized",
        "trace_conflict",
    }
)


class TelemetryQueueError(RuntimeError):
    """Base error for a failed or unsafe queue operation."""


class UnsupportedPlatformError(TelemetryQueueError):
    """The strong POSIX queue primitives are unavailable."""


class UnsafePathError(TelemetryQueueError):
    """A fixed queue path failed its ownership/type/link/mode contract."""


class UnreadablePathError(TelemetryQueueError):
    """A fixed queue path could not be read because of an I/O/access failure."""


class QueueLockTimeout(TelemetryQueueError):
    """A bounded verified advisory lock could not be acquired."""


class InvalidStateError(TelemetryQueueError):
    """A fixed content-free state or receipt file is invalid."""


@dataclass(frozen=True)
class TelemetryPaths:
    """All fixed filesystem locations for the v1 private writer."""

    directory: Path
    database_path: Path
    database_wal_path: Path
    lock_path: Path
    queue_lock_path: Path
    writer_lock_path: Path
    writer_start_lock_path: Path
    writer_start_path: Path
    writer_start_temp_path: Path
    producer_accounting_path: Path
    producer_accounting_temp_path: Path
    writer_state_path: Path
    writer_state_temp_path: Path
    database_init_directory: Path
    init_database_path: Path
    init_wal_path: Path
    inbox_directory: Path
    temp_directory: Path
    ready_directory: Path
    claimed_directory: Path
    receipts_directory: Path


@dataclass(frozen=True)
class CapabilityResult:
    supported: bool
    reason: str | None


@dataclass(frozen=True)
class PublicationResult:
    published: bool
    source_name: str | None
    reason: str | None
    durability_degraded: bool = False


@dataclass(frozen=True)
class WriterStartResult:
    started: bool
    suppressed: bool
    reason: str


@dataclass(frozen=True)
class ClaimReadResult:
    source_name: str
    envelope_bytes: int
    payload: bytes | None
    envelope_sha256: str | None
    digest_complete: bool
    oversized: bool


@dataclass(frozen=True)
class QueueSnapshot:
    present: bool
    ready: int = 0
    claimed: int = 0
    temporary: int = 0
    receipts: int = 0
    pending_bytes: int = 0
    temporary_bytes: int = 0
    receipt_bytes: int = 0
    oldest_pending_mtime_ns: int | None = None
    capacity_full: bool = False
    scan_incomplete: bool = False
    unsafe: bool = False
    unreadable: bool = False
    ready_names: tuple[str, ...] = ()
    claimed_names: tuple[str, ...] = ()
    receipt_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class PendingItem:
    source_name: str
    location: Literal["ready", "claimed"]
    terminal_kind: ReceiptKind | None = None


@dataclass(frozen=True)
class PendingSnapshot:
    items: tuple[PendingItem, ...]
    scan_incomplete: bool = False


@dataclass(frozen=True)
class ProducerAccounting:
    schema_version: int = 1
    queue_full: int = 0
    queue_lock_timeout: int = 0
    publication_failure: int = 0
    directory_sync_failure: int = 0
    writer_start_failure: int = 0
    updated_at_unix_ms: int | None = None
    accounting_incomplete: bool = False

    @property
    def producer_dropped_lower_bound(self) -> int:
        return min(
            COUNTER_MAX,
            self.queue_full + self.queue_lock_timeout + self.publication_failure,
        )


@dataclass(frozen=True)
class WriterStartLease:
    schema_version: int
    lease_started_unix_ms: int


@dataclass(frozen=True)
class WriterState:
    schema_version: int = 1
    phase: WriterPhase = "starting"
    reason: WriterReason | None = None
    heartbeat_unix_ms: int = 0
    last_writer_commit_unix_ms: int | None = None
    store_state: WriterStoreState = "absent"
    store_schema_version: int | None = None
    persisted_runs_snapshot: int | None = None
    database_device: int | None = None
    database_inode: int | None = None
    database_bytes: int | None = None
    rejected: int = 0
    conflicts: int = 0
    replays: int = 0
    recovered_claims: int = 0
    write_failures: int = 0
    receipts_rotated: int = 0
    durability_degraded: bool = False
    accounting_incomplete: bool = False
    accounted_receipts: tuple[str, ...] = ()


@dataclass(frozen=True)
class TerminalReceipt:
    schema_version: int
    kind: ReceiptKind
    source_name: str
    envelope_sha256: str | None
    digest_complete: bool
    envelope_bytes: int
    recorded_at_unix_ms: int
    reason: ReceiptReason | None


@dataclass(frozen=True)
class ReceiptPublicationResult:
    published: bool
    already_present: bool
    rotated_names: tuple[str, ...] = ()
    durability_degraded: bool = False


def telemetry_paths(directory: Path | None = None) -> TelemetryPaths:
    """Return fixed v1 paths without touching the filesystem."""

    root = (
        default_buoy_home() / "telemetry"
        if directory is None
        else Path(os.path.abspath(os.fspath(directory)))
    )
    inbox = root / "inbox-v1"
    scratch = root / "database-init-v1"
    return TelemetryPaths(
        directory=root,
        database_path=root / "telemetry.duckdb",
        database_wal_path=root / "telemetry.duckdb.wal",
        lock_path=root / "write.lock",
        queue_lock_path=root / "queue.lock",
        writer_lock_path=root / "writer.lock",
        writer_start_lock_path=root / "writer-start.lock",
        writer_start_path=root / "writer-start-v1.json",
        writer_start_temp_path=root / ".writer-start-v1.tmp",
        producer_accounting_path=root / "producer-accounting-v1.json",
        producer_accounting_temp_path=root / ".producer-accounting-v1.tmp",
        writer_state_path=root / "writer-state-v1.json",
        writer_state_temp_path=root / ".writer-state-v1.tmp",
        database_init_directory=scratch,
        init_database_path=scratch / "telemetry.duckdb",
        init_wal_path=scratch / "telemetry.duckdb.wal",
        inbox_directory=inbox,
        temp_directory=inbox / "tmp",
        ready_directory=inbox / "ready",
        claimed_directory=inbox / "claimed",
        receipts_directory=inbox / "receipts",
    )


def posix_writer_capability() -> CapabilityResult:
    """Return whether this interpreter exposes every strong queue primitive."""

    if os.name != "posix" or fcntl is None:
        return CapabilityResult(False, "platform_unsupported")
    required_attributes = (
        "O_DIRECTORY",
        "O_NOFOLLOW",
        "O_CLOEXEC",
        "geteuid",
        "fstat",
        "fchmod",
        "fsync",
    )
    if any(not hasattr(os, attribute) for attribute in required_attributes):
        return CapabilityResult(False, "platform_unsupported")
    required_dir_fd = (
        os.mkdir,
        os.open,
        os.stat,
        os.rename,
        os.link,
        os.unlink,
        os.rmdir,
    )
    if any(function not in os.supports_dir_fd for function in required_dir_fd):
        return CapabilityResult(False, "platform_unsupported")
    if os.stat not in os.supports_follow_symlinks:
        return CapabilityResult(False, "platform_unsupported")
    return CapabilityResult(True, None)


def require_posix_writer_capability() -> None:
    result = posix_writer_capability()
    if not result.supported:
        raise UnsupportedPlatformError(result.reason or "platform_unsupported")


def _require_basename(name: str) -> None:
    if (
        not isinstance(name, str)
        or not name
        or name in {".", ".."}
        or "/" in name
        or (os.altsep is not None and os.altsep in name)
        or "\x00" in name
    ):
        raise ValueError("a fixed path basename is required")


def _mode_bits(observed: os.stat_result) -> int:
    return stat.S_IMODE(observed.st_mode)


def verify_private_directory_fd(
    descriptor: int,
    *,
    repair_mode: bool = True,
) -> os.stat_result:
    """Verify one opened private directory, repairing mode only after ownership."""

    observed = os.fstat(descriptor)
    if not stat.S_ISDIR(observed.st_mode) or observed.st_uid != os.geteuid():
        raise UnsafePathError("private directory metadata is unsafe")
    if _mode_bits(observed) != _DIRECTORY_MODE:
        if not repair_mode:
            raise UnsafePathError("private directory mode is unsafe")
        os.fchmod(descriptor, _DIRECTORY_MODE)
        observed = os.fstat(descriptor)
        if _mode_bits(observed) != _DIRECTORY_MODE:
            raise UnsafePathError("private directory mode is unsafe")
    return observed


def verify_private_file_fd(
    descriptor: int,
    *,
    max_bytes: int | None = None,
    allowed_nlinks: Sequence[int] = (1,),
    repair_mode: bool = True,
) -> os.stat_result:
    """Verify one opened private regular file without following another name."""

    observed = os.fstat(descriptor)
    if (
        not stat.S_ISREG(observed.st_mode)
        or observed.st_uid != os.geteuid()
        or observed.st_nlink not in set(allowed_nlinks)
        or (max_bytes is not None and observed.st_size > max_bytes)
    ):
        raise UnsafePathError("private file metadata is unsafe")
    if _mode_bits(observed) != _FILE_MODE:
        if not repair_mode:
            raise UnsafePathError("private file mode is unsafe")
        os.fchmod(descriptor, _FILE_MODE)
        observed = os.fstat(descriptor)
        if _mode_bits(observed) != _FILE_MODE:
            raise UnsafePathError("private file mode is unsafe")
    return observed


def open_verified_directory(
    path: Path | str,
    *,
    repair_mode: bool = True,
) -> int:
    """Open and verify a private directory without following its final name."""

    require_posix_writer_capability()
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        descriptor = os.open(os.fspath(path), flags)
    except FileNotFoundError:
        raise
    except OSError as exc:
        if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise UnsafePathError("private directory could not be opened safely") from exc
        raise UnreadablePathError("private directory could not be read") from exc
    try:
        verify_private_directory_fd(descriptor, repair_mode=repair_mode)
    except Exception:
        os.close(descriptor)
        raise
    return descriptor


def open_private_directory_at(
    parent_fd: int,
    name: str,
    *,
    create: bool = False,
    repair_mode: bool = True,
) -> int:
    """Open a fixed private child directory relative to a verified descriptor."""

    require_posix_writer_capability()
    _require_basename(name)
    if create:
        try:
            os.mkdir(name, _DIRECTORY_MODE, dir_fd=parent_fd)
        except FileExistsError:
            pass
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        descriptor = os.open(name, flags, dir_fd=parent_fd)
    except FileNotFoundError:
        raise
    except OSError as exc:
        if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise UnsafePathError(
                "private child directory could not be opened safely"
            ) from exc
        raise UnreadablePathError("private child directory could not be read") from exc
    try:
        verify_private_directory_fd(descriptor, repair_mode=repair_mode)
    except Exception:
        os.close(descriptor)
        raise
    return descriptor


def open_private_file_at(
    parent_fd: int,
    name: str,
    *,
    flags: int,
    mode: int = _FILE_MODE,
    max_bytes: int | None = None,
    allowed_nlinks: Sequence[int] = (1,),
    repair_mode: bool = True,
) -> int:
    """Open and verify a fixed regular child file relative to a directory fd."""

    require_posix_writer_capability()
    _require_basename(name)
    # Opening a FIFO with plain O_RDONLY can block before fstat gets a chance
    # to reject it.  Inspect the stable directory entry first for every
    # existing-file open.  The descriptor and name are still reverified after
    # open, so this is a bounded precondition rather than the identity proof.
    if not flags & os.O_CREAT:
        observed = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if (
            not stat.S_ISREG(observed.st_mode)
            or observed.st_uid != os.geteuid()
            or observed.st_nlink not in set(allowed_nlinks)
            or (max_bytes is not None and observed.st_size > max_bytes)
            or (not repair_mode and _mode_bits(observed) != _FILE_MODE)
        ):
            raise UnsafePathError("private file metadata is unsafe")
    safe_flags = flags | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        descriptor = os.open(name, safe_flags, mode, dir_fd=parent_fd)
    except FileNotFoundError:
        raise
    except FileExistsError as exc:
        raise UnsafePathError("private child file already exists") from exc
    except OSError as exc:
        if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise UnsafePathError("private child file could not be opened safely") from exc
        raise UnreadablePathError("private child file could not be read") from exc
    try:
        verify_private_file_fd(
            descriptor,
            max_bytes=max_bytes,
            allowed_nlinks=allowed_nlinks,
            repair_mode=repair_mode,
        )
        _require_open_name_matches_fd(parent_fd, name, descriptor)
    except Exception:
        os.close(descriptor)
        raise
    return descriptor


def stat_private_entry_at(
    parent_fd: int,
    name: str,
    *,
    kind: Literal["file", "directory"],
    max_bytes: int | None = None,
    allowed_nlinks: Sequence[int] = (1,),
) -> os.stat_result:
    """Lstat one fixed child and enforce its complete private metadata."""

    _require_basename(name)
    observed = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if observed.st_uid != os.geteuid():
        raise UnsafePathError("private entry ownership is unsafe")
    if kind == "directory":
        if not stat.S_ISDIR(observed.st_mode) or _mode_bits(observed) != _DIRECTORY_MODE:
            raise UnsafePathError("private directory metadata is unsafe")
    elif (
        not stat.S_ISREG(observed.st_mode)
        or _mode_bits(observed) != _FILE_MODE
        or observed.st_nlink not in set(allowed_nlinks)
        or (max_bytes is not None and observed.st_size > max_bytes)
    ):
        raise UnsafePathError("private file metadata is unsafe")
    return observed


def _require_open_name_matches_fd(parent_fd: int, name: str, descriptor: int) -> None:
    named = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    opened = os.fstat(descriptor)
    if (named.st_dev, named.st_ino) != (opened.st_dev, opened.st_ino):
        raise UnsafePathError("private path was replaced while open")


def safe_unlink_at(
    parent_fd: int,
    name: str,
    *,
    missing_ok: bool = False,
    allowed_nlinks: Sequence[int] = (1,),
) -> None:
    """Unlink only a verified private regular file."""

    _require_basename(name)
    try:
        stat_private_entry_at(
            parent_fd,
            name,
            kind="file",
            allowed_nlinks=allowed_nlinks,
        )
    except FileNotFoundError:
        if missing_ok:
            return
        raise
    os.unlink(name, dir_fd=parent_fd)


def safe_rmdir_at(
    parent_fd: int,
    name: str,
    *,
    missing_ok: bool = False,
) -> None:
    """Remove only a verified empty private directory."""

    _require_basename(name)
    try:
        stat_private_entry_at(parent_fd, name, kind="directory")
    except FileNotFoundError:
        if missing_ok:
            return
        raise
    os.rmdir(name, dir_fd=parent_fd)


def safe_link_at(
    src_parent_fd: int,
    src_name: str,
    dst_parent_fd: int,
    dst_name: str,
) -> None:
    """Hard-link one verified private one-link file to an absent fixed name."""

    _require_basename(src_name)
    _require_basename(dst_name)
    source = stat_private_entry_at(
        src_parent_fd,
        src_name,
        kind="file",
        allowed_nlinks=(1,),
    )
    try:
        os.stat(dst_name, dir_fd=dst_parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        pass
    else:
        raise FileExistsError(dst_name)
    os.link(
        src_name,
        dst_name,
        src_dir_fd=src_parent_fd,
        dst_dir_fd=dst_parent_fd,
        follow_symlinks=False,
    )
    source_after = stat_private_entry_at(
        src_parent_fd,
        src_name,
        kind="file",
        allowed_nlinks=(2,),
    )
    destination = stat_private_entry_at(
        dst_parent_fd,
        dst_name,
        kind="file",
        allowed_nlinks=(2,),
    )
    if (
        (source.st_dev, source.st_ino)
        != (source_after.st_dev, source_after.st_ino)
        or (source_after.st_dev, source_after.st_ino)
        != (destination.st_dev, destination.st_ino)
    ):
        raise UnsafePathError("private hard-link publication is inconsistent")


def fsync_directory(descriptor: int) -> bool:
    """Synchronize a directory; return False only for recognized unsupported fs."""

    try:
        os.fsync(descriptor)
    except OSError as exc:
        if exc.errno in _RECOGNIZED_DIRECTORY_FSYNC_ERRORS:
            return False
        raise
    return True


def _open_parent_for_root(
    paths: TelemetryPaths,
    *,
    create: bool,
    repair_mode: bool = True,
) -> int:
    parent = paths.directory.parent
    try:
        return open_verified_directory(parent, repair_mode=repair_mode)
    except FileNotFoundError:
        if not create:
            raise
    grandparent = parent.parent
    grandparent_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        grandparent_fd = os.open(grandparent, grandparent_flags)
    except OSError as exc:
        raise UnsafePathError("telemetry parent could not be opened safely") from exc
    try:
        grandparent_stat = os.fstat(grandparent_fd)
        if not stat.S_ISDIR(grandparent_stat.st_mode) or grandparent_stat.st_uid != os.geteuid():
            raise UnsafePathError("telemetry parent ownership is unsafe")
        return open_private_directory_at(
            grandparent_fd,
            parent.name,
            create=True,
            repair_mode=repair_mode,
        )
    finally:
        os.close(grandparent_fd)


def _open_telemetry_root(
    paths: TelemetryPaths,
    *,
    create: bool,
    repair_mode: bool = True,
) -> int:
    require_posix_writer_capability()
    parent_fd = _open_parent_for_root(
        paths,
        create=create,
        repair_mode=repair_mode,
    )
    try:
        return open_private_directory_at(
            parent_fd,
            paths.directory.name,
            create=create,
            repair_mode=repair_mode,
        )
    finally:
        os.close(parent_fd)


@dataclass
class _QueueDirectoryFds:
    root: int
    inbox: int
    temporary: int
    ready: int
    claimed: int
    receipts: int

    def close(self) -> None:
        for descriptor in (
            self.receipts,
            self.claimed,
            self.ready,
            self.temporary,
            self.inbox,
            self.root,
        ):
            try:
                os.close(descriptor)
            except OSError:
                pass


def _open_queue_directories(
    paths: TelemetryPaths,
    *,
    create: bool,
    repair_mode: bool = True,
) -> _QueueDirectoryFds:
    root_fd = _open_telemetry_root(
        paths,
        create=create,
        repair_mode=repair_mode,
    )
    inbox_fd: int | None = None
    temp_fd: int | None = None
    ready_fd: int | None = None
    claimed_fd: int | None = None
    receipts_fd: int | None = None
    try:
        inbox_fd = open_private_directory_at(
            root_fd, "inbox-v1", create=create, repair_mode=repair_mode
        )
        temp_fd = open_private_directory_at(
            inbox_fd, "tmp", create=create, repair_mode=repair_mode
        )
        ready_fd = open_private_directory_at(
            inbox_fd, "ready", create=create, repair_mode=repair_mode
        )
        claimed_fd = open_private_directory_at(
            inbox_fd, "claimed", create=create, repair_mode=repair_mode
        )
        receipts_fd = open_private_directory_at(
            inbox_fd, "receipts", create=create, repair_mode=repair_mode
        )
        # Unknown siblings inside the governed v1 inbox are unsafe.  This is
        # checked for writer operations as well as the read-only status path.
        _scan_inbox_directory_names(inbox_fd)
        return _QueueDirectoryFds(
            root=root_fd,
            inbox=inbox_fd,
            temporary=temp_fd,
            ready=ready_fd,
            claimed=claimed_fd,
            receipts=receipts_fd,
        )
    except Exception:
        for descriptor in (receipts_fd, claimed_fd, ready_fd, temp_fd, inbox_fd, root_fd):
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
        raise


def _open_or_create_lock(root_fd: int, name: str) -> int:
    try:
        return open_private_file_at(
            root_fd,
            name,
            flags=os.O_RDWR | os.O_CREAT | os.O_EXCL,
            max_bytes=0,
        )
    except UnsafePathError as exc:
        cause = exc.__cause__
        if not isinstance(cause, FileExistsError):
            raise
    return open_private_file_at(
        root_fd,
        name,
        flags=os.O_RDWR,
        max_bytes=0,
    )


@contextmanager
def _verified_lock(
    paths: TelemetryPaths,
    name: str,
    *,
    timeout_ms: int,
    create_root: bool,
) -> Iterator[int]:
    if type(timeout_ms) is not int or timeout_ms < 0:
        raise ValueError("lock timeout must be a nonnegative integer")
    root_fd = _open_telemetry_root(paths, create=create_root)
    lock_fd: int | None = None
    try:
        lock_fd = _open_or_create_lock(root_fd, name)
        assert fcntl is not None
        deadline = time.monotonic_ns() + timeout_ms * 1_000_000
        while True:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic_ns() >= deadline:
                    raise QueueLockTimeout("verified lock acquisition timed out")
                remaining_ns = deadline - time.monotonic_ns()
                time.sleep(min(LOCK_POLL_MS / 1_000, remaining_ns / 1_000_000_000))
        verify_private_file_fd(lock_fd, max_bytes=0)
        _require_open_name_matches_fd(root_fd, name, lock_fd)
        try:
            yield lock_fd
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
    finally:
        if lock_fd is not None:
            os.close(lock_fd)
        os.close(root_fd)


def queue_lock(
    paths: TelemetryPaths,
    timeout_ms: int = LOCK_TIMEOUT_MS,
) -> Iterator[int]:
    return _verified_lock(
        paths,
        "queue.lock",
        timeout_ms=timeout_ms,
        create_root=True,
    )


def writer_start_lock(
    paths: TelemetryPaths,
    timeout_ms: int = LOCK_TIMEOUT_MS,
) -> Iterator[int]:
    return _verified_lock(
        paths,
        "writer-start.lock",
        timeout_ms=timeout_ms,
        create_root=True,
    )


def writer_lifetime_lock(
    paths: TelemetryPaths,
    timeout_ms: int = 0,
) -> Iterator[int]:
    return _verified_lock(
        paths,
        "writer.lock",
        timeout_ms=timeout_ms,
        create_root=True,
    )


def database_write_lock(
    paths: TelemetryPaths,
    timeout_ms: int = LOCK_TIMEOUT_MS,
) -> Iterator[int]:
    return _verified_lock(
        paths,
        "write.lock",
        timeout_ms=timeout_ms,
        create_root=True,
    )


def _reject_duplicate_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise InvalidStateError("duplicate state key")
        result[key] = value
    return result


def _reject_nonfinite_constant(_value: str) -> object:
    raise InvalidStateError("nonfinite state number")


def _canonical_json_bytes(value: Mapping[str, object], *, maximum: int) -> bytes:
    try:
        payload = json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise InvalidStateError("state is not canonical JSON") from exc
    if len(payload) > maximum:
        raise InvalidStateError("state exceeds its byte limit")
    return payload


def _read_all_verified(
    parent_fd: int,
    name: str,
    *,
    maximum: int,
) -> bytes:
    descriptor = open_private_file_at(
        parent_fd,
        name,
        flags=os.O_RDONLY,
        max_bytes=maximum,
        repair_mode=False,
    )
    try:
        before = verify_private_file_fd(
            descriptor,
            max_bytes=maximum,
            repair_mode=False,
        )
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 65_536))
            if not chunk:
                raise InvalidStateError("private file ended before its verified size")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            raise InvalidStateError("private file grew while being read")
        after = verify_private_file_fd(
            descriptor,
            max_bytes=maximum,
            repair_mode=False,
        )
        _require_open_name_matches_fd(parent_fd, name, descriptor)
        if (
            (before.st_dev, before.st_ino, before.st_size)
            != (after.st_dev, after.st_ino, after.st_size)
        ):
            raise UnsafePathError("private file changed while being read")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _parse_canonical_object(payload: bytes) -> dict[str, object]:
    try:
        text = payload.decode("utf-8")
        parsed = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_nonfinite_constant,
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        InvalidStateError,
        RecursionError,
        ValueError,
    ) as exc:
        raise InvalidStateError("state is invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise InvalidStateError("state must be one JSON object")
    try:
        canonical = _canonical_json_bytes(
            parsed,
            maximum=max(len(payload), 1),
        )
    except (RecursionError, ValueError) as exc:
        raise InvalidStateError("state is invalid JSON") from exc
    if canonical != payload:
        raise InvalidStateError("state is not canonically encoded")
    return parsed


def _write_all(descriptor: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        written = os.write(descriptor, payload[offset:])
        if written <= 0:
            raise OSError("private file write did not advance")
        offset += written


def _existing_private_file(
    parent_fd: int,
    name: str,
    *,
    maximum: int,
) -> bool:
    try:
        stat_private_entry_at(
            parent_fd,
            name,
            kind="file",
            max_bytes=maximum,
        )
    except FileNotFoundError:
        return False
    return True


def _write_fixed_json_at(
    parent_fd: int,
    *,
    final_name: str,
    temporary_name: str,
    payload: bytes,
    maximum: int,
) -> bool:
    """Atomically replace one fixed canonical state file.

    The caller owns the state-specific lock.  A recognized safe construction
    temporary may be removed; an unsafe one blocks replacement.
    """

    if len(payload) > maximum:
        raise InvalidStateError("state exceeds its byte limit")
    if _existing_private_file(parent_fd, temporary_name, maximum=maximum):
        safe_unlink_at(parent_fd, temporary_name)
    if _existing_private_file(parent_fd, final_name, maximum=maximum):
        # Establish safety before an atomic replacement.  Callers that require
        # semantic validity read/validate the old state before reaching here.
        stat_private_entry_at(
            parent_fd,
            final_name,
            kind="file",
            max_bytes=maximum,
        )
    descriptor = open_private_file_at(
        parent_fd,
        temporary_name,
        flags=os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        max_bytes=maximum,
    )
    try:
        _write_all(descriptor, payload)
        os.fchmod(descriptor, _FILE_MODE)
        os.fsync(descriptor)
        observed = verify_private_file_fd(descriptor, max_bytes=maximum)
        if observed.st_size != len(payload):
            raise UnsafePathError("state temporary size changed")
        _require_open_name_matches_fd(parent_fd, temporary_name, descriptor)
    finally:
        os.close(descriptor)
    os.rename(
        temporary_name,
        final_name,
        src_dir_fd=parent_fd,
        dst_dir_fd=parent_fd,
    )
    return fsync_directory(parent_fd)


def _require_exact_keys(value: Mapping[str, object], expected: set[str]) -> None:
    if set(value) != expected:
        raise InvalidStateError("state fields are incompatible")


def _require_counter(value: object, *, nullable: bool = False) -> int | None:
    if value is None and nullable:
        return None
    if type(value) is not int or value < 0 or value > COUNTER_MAX:
        raise InvalidStateError("state counter is invalid")
    return value


def _require_boolean(value: object) -> bool:
    if type(value) is not bool:
        raise InvalidStateError("state boolean is invalid")
    return value


_ACCOUNTING_FIELDS = {
    "schema_version",
    "queue_full",
    "queue_lock_timeout",
    "publication_failure",
    "directory_sync_failure",
    "writer_start_failure",
    "updated_at_unix_ms",
    "accounting_incomplete",
}


def _accounting_object(value: ProducerAccounting) -> dict[str, object]:
    return {
        "schema_version": value.schema_version,
        "queue_full": value.queue_full,
        "queue_lock_timeout": value.queue_lock_timeout,
        "publication_failure": value.publication_failure,
        "directory_sync_failure": value.directory_sync_failure,
        "writer_start_failure": value.writer_start_failure,
        "updated_at_unix_ms": value.updated_at_unix_ms,
        "accounting_incomplete": value.accounting_incomplete,
    }


def _parse_accounting(value: Mapping[str, object]) -> ProducerAccounting:
    _require_exact_keys(value, _ACCOUNTING_FIELDS)
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise InvalidStateError("producer accounting version is incompatible")
    updated = _require_counter(value["updated_at_unix_ms"], nullable=True)
    return ProducerAccounting(
        queue_full=int(_require_counter(value["queue_full"])),
        queue_lock_timeout=int(_require_counter(value["queue_lock_timeout"])),
        publication_failure=int(_require_counter(value["publication_failure"])),
        directory_sync_failure=int(
            _require_counter(value["directory_sync_failure"])
        ),
        writer_start_failure=int(_require_counter(value["writer_start_failure"])),
        updated_at_unix_ms=updated,
        accounting_incomplete=_require_boolean(value["accounting_incomplete"]),
    )


def _read_accounting_at(root_fd: int) -> ProducerAccounting | None:
    try:
        payload = _read_all_verified(
            root_fd,
            "producer-accounting-v1.json",
            maximum=ACCOUNTING_MAX_BYTES,
        )
    except FileNotFoundError:
        return None
    return _parse_accounting(_parse_canonical_object(payload))


def read_producer_accounting(
    paths: TelemetryPaths | None = None,
) -> ProducerAccounting | None:
    selected = paths or telemetry_paths()
    try:
        root_fd = _open_telemetry_root(
            selected,
            create=False,
            repair_mode=False,
        )
    except FileNotFoundError:
        return None
    try:
        return _read_accounting_at(root_fd)
    finally:
        os.close(root_fd)


def _increment_accounting_at(
    root_fd: int,
    field: str,
    *,
    now_unix_ms: int | None = None,
) -> bool:
    if field not in _ACCOUNTING_FIELDS - {
        "schema_version",
        "updated_at_unix_ms",
        "accounting_incomplete",
    }:
        raise ValueError("unknown producer accounting counter")
    try:
        current = _read_accounting_at(root_fd) or ProducerAccounting()
    except (InvalidStateError, UnsafePathError, UnreadablePathError, OSError):
        return False
    old_value = int(getattr(current, field))
    incomplete = current.accounting_incomplete or old_value == COUNTER_MAX
    next_value = min(COUNTER_MAX, old_value + 1)
    updated = replace(
        current,
        **{
            field: next_value,
            "updated_at_unix_ms": (
                _time_unix_ms() if now_unix_ms is None else now_unix_ms
            ),
            "accounting_incomplete": incomplete,
        },
    )
    try:
        payload = _canonical_json_bytes(
            _accounting_object(updated),
            maximum=ACCOUNTING_MAX_BYTES,
        )
        _write_fixed_json_at(
            root_fd,
            final_name="producer-accounting-v1.json",
            temporary_name=".producer-accounting-v1.tmp",
            payload=payload,
            maximum=ACCOUNTING_MAX_BYTES,
        )
    except (TelemetryQueueError, OSError):
        return False
    return True


def increment_producer_accounting(
    field: str,
    *,
    paths: TelemetryPaths | None = None,
) -> bool:
    """Best-effort increment one producer counter under the queue lock."""

    selected = paths or telemetry_paths()
    try:
        with queue_lock(selected):
            root_fd = _open_telemetry_root(selected, create=False)
            try:
                return _increment_accounting_at(root_fd, field)
            finally:
                os.close(root_fd)
    except (TelemetryQueueError, OSError):
        return False


_START_LEASE_FIELDS = {"schema_version", "lease_started_unix_ms"}


def _start_lease_object(value: WriterStartLease) -> dict[str, object]:
    return {
        "schema_version": value.schema_version,
        "lease_started_unix_ms": value.lease_started_unix_ms,
    }


def _parse_start_lease(value: Mapping[str, object]) -> WriterStartLease:
    _require_exact_keys(value, _START_LEASE_FIELDS)
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise InvalidStateError("writer-start lease version is incompatible")
    return WriterStartLease(
        schema_version=1,
        lease_started_unix_ms=int(
            _require_counter(value["lease_started_unix_ms"])
        ),
    )


def _read_start_lease_at(root_fd: int) -> WriterStartLease | None:
    try:
        payload = _read_all_verified(
            root_fd,
            "writer-start-v1.json",
            maximum=START_LEASE_MAX_BYTES,
        )
    except FileNotFoundError:
        return None
    return _parse_start_lease(_parse_canonical_object(payload))


def read_writer_start_lease(
    paths: TelemetryPaths | None = None,
) -> WriterStartLease | None:
    selected = paths or telemetry_paths()
    try:
        root_fd = _open_telemetry_root(
            selected,
            create=False,
            repair_mode=False,
        )
    except FileNotFoundError:
        return None
    try:
        return _read_start_lease_at(root_fd)
    finally:
        os.close(root_fd)


def _write_start_lease_at(root_fd: int, lease: WriterStartLease) -> bool:
    payload = _canonical_json_bytes(
        _start_lease_object(lease),
        maximum=START_LEASE_MAX_BYTES,
    )
    return _write_fixed_json_at(
        root_fd,
        final_name="writer-start-v1.json",
        temporary_name=".writer-start-v1.tmp",
        payload=payload,
        maximum=START_LEASE_MAX_BYTES,
    )


def clear_writer_start_lease(paths: TelemetryPaths | None = None) -> bool:
    selected = paths or telemetry_paths()
    try:
        with writer_start_lock(selected):
            root_fd = _open_telemetry_root(selected, create=False)
            try:
                safe_unlink_at(
                    root_fd,
                    "writer-start-v1.json",
                    missing_ok=True,
                )
                if _existing_private_file(
                    root_fd,
                    ".writer-start-v1.tmp",
                    maximum=START_LEASE_MAX_BYTES,
                ):
                    safe_unlink_at(root_fd, ".writer-start-v1.tmp")
                return fsync_directory(root_fd)
            finally:
                os.close(root_fd)
    except (TelemetryQueueError, OSError):
        return False


_WRITER_STATE_FIELDS = {
    "schema_version",
    "phase",
    "reason",
    "heartbeat_unix_ms",
    "last_writer_commit_unix_ms",
    "store_state",
    "store_schema_version",
    "persisted_runs_snapshot",
    "database_device",
    "database_inode",
    "database_bytes",
    "rejected",
    "conflicts",
    "replays",
    "recovered_claims",
    "write_failures",
    "receipts_rotated",
    "durability_degraded",
    "accounting_incomplete",
    "accounted_receipts",
}


def _writer_state_object(value: WriterState) -> dict[str, object]:
    return {
        "schema_version": value.schema_version,
        "phase": value.phase,
        "reason": value.reason,
        "heartbeat_unix_ms": value.heartbeat_unix_ms,
        "last_writer_commit_unix_ms": value.last_writer_commit_unix_ms,
        "store_state": value.store_state,
        "store_schema_version": value.store_schema_version,
        "persisted_runs_snapshot": value.persisted_runs_snapshot,
        "database_device": value.database_device,
        "database_inode": value.database_inode,
        "database_bytes": value.database_bytes,
        "rejected": value.rejected,
        "conflicts": value.conflicts,
        "replays": value.replays,
        "recovered_claims": value.recovered_claims,
        "write_failures": value.write_failures,
        "receipts_rotated": value.receipts_rotated,
        "durability_degraded": value.durability_degraded,
        "accounting_incomplete": value.accounting_incomplete,
        "accounted_receipts": list(value.accounted_receipts),
    }


def _parse_writer_state(value: Mapping[str, object]) -> WriterState:
    _require_exact_keys(value, _WRITER_STATE_FIELDS)
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise InvalidStateError("writer state version is incompatible")
    phase = value["phase"]
    store_state = value["store_state"]
    reason = value["reason"]
    if not isinstance(phase, str) or phase not in _WRITER_PHASES:
        raise InvalidStateError("writer phase is invalid")
    if not isinstance(store_state, str) or store_state not in _WRITER_STORE_STATES:
        raise InvalidStateError("writer store state is invalid")
    if reason is not None and (
        not isinstance(reason, str) or reason not in _WRITER_REASONS
    ):
        raise InvalidStateError("writer reason is invalid")
    store_schema = value["store_schema_version"]
    if store_schema is not None and (
        type(store_schema) is not int or store_schema != 1
    ):
        raise InvalidStateError("writer store schema is invalid")
    receipts = value["accounted_receipts"]
    if not isinstance(receipts, list) or len(receipts) > RECEIPT_MAX_ENTRIES:
        raise InvalidStateError("writer accounted receipts are invalid")
    if any(not isinstance(name, str) or _RECEIPT_RE.fullmatch(name) is None for name in receipts):
        raise InvalidStateError("writer accounted receipt name is invalid")
    if receipts != sorted(set(receipts)):
        raise InvalidStateError("writer accounted receipts are not sorted and unique")
    return WriterState(
        schema_version=1,
        phase=phase,  # type: ignore[arg-type]
        reason=reason,  # type: ignore[arg-type]
        heartbeat_unix_ms=int(_require_counter(value["heartbeat_unix_ms"])),
        last_writer_commit_unix_ms=_require_counter(
            value["last_writer_commit_unix_ms"], nullable=True
        ),
        store_state=store_state,  # type: ignore[arg-type]
        store_schema_version=store_schema,
        persisted_runs_snapshot=_require_counter(
            value["persisted_runs_snapshot"], nullable=True
        ),
        database_device=_require_counter(value["database_device"], nullable=True),
        database_inode=_require_counter(value["database_inode"], nullable=True),
        database_bytes=_require_counter(value["database_bytes"], nullable=True),
        rejected=int(_require_counter(value["rejected"])),
        conflicts=int(_require_counter(value["conflicts"])),
        replays=int(_require_counter(value["replays"])),
        recovered_claims=int(_require_counter(value["recovered_claims"])),
        write_failures=int(_require_counter(value["write_failures"])),
        receipts_rotated=int(_require_counter(value["receipts_rotated"])),
        durability_degraded=_require_boolean(value["durability_degraded"]),
        accounting_incomplete=_require_boolean(value["accounting_incomplete"]),
        accounted_receipts=tuple(receipts),
    )


def _read_writer_state_at(root_fd: int) -> WriterState | None:
    try:
        payload = _read_all_verified(
            root_fd,
            "writer-state-v1.json",
            maximum=STATE_MAX_BYTES,
        )
    except FileNotFoundError:
        return None
    return _parse_writer_state(_parse_canonical_object(payload))


def read_writer_state(paths: TelemetryPaths | None = None) -> WriterState | None:
    selected = paths or telemetry_paths()
    try:
        root_fd = _open_telemetry_root(
            selected,
            create=False,
            repair_mode=False,
        )
    except FileNotFoundError:
        return None
    try:
        return _read_writer_state_at(root_fd)
    finally:
        os.close(root_fd)


def write_writer_state(
    state: WriterState,
    *,
    paths: TelemetryPaths | None = None,
) -> bool:
    """Write canonical writer state; caller must hold lifetime authority."""

    selected = paths or telemetry_paths()
    parsed = _parse_writer_state(_writer_state_object(state))
    payload = _canonical_json_bytes(
        _writer_state_object(parsed),
        maximum=STATE_MAX_BYTES,
    )
    root_fd = _open_telemetry_root(selected, create=True)
    try:
        try:
            existing = _read_writer_state_at(root_fd)
        except FileNotFoundError:
            existing = None
        except (InvalidStateError, UnsafePathError, UnreadablePathError, OSError):
            # A writer may replace malformed semantic state only when the fixed
            # path itself remains a verified private regular file.
            stat_private_entry_at(
                root_fd,
                "writer-state-v1.json",
                kind="file",
                max_bytes=STATE_MAX_BYTES,
            )
            existing = None
            state = replace(state, accounting_incomplete=True)
            payload = _canonical_json_bytes(
                _writer_state_object(state),
                maximum=STATE_MAX_BYTES,
            )
        del existing
        return _write_fixed_json_at(
            root_fd,
            final_name="writer-state-v1.json",
            temporary_name=".writer-state-v1.tmp",
            payload=payload,
            maximum=STATE_MAX_BYTES,
        )
    finally:
        os.close(root_fd)


def _receipt_object(value: TerminalReceipt) -> dict[str, object]:
    return {
        "schema_version": value.schema_version,
        "kind": value.kind,
        "source_name": value.source_name,
        "envelope_sha256": value.envelope_sha256,
        "digest_complete": value.digest_complete,
        "envelope_bytes": value.envelope_bytes,
        "recorded_at_unix_ms": value.recorded_at_unix_ms,
        "reason": value.reason,
    }


_RECEIPT_FIELDS = {
    "schema_version",
    "kind",
    "source_name",
    "envelope_sha256",
    "digest_complete",
    "envelope_bytes",
    "recorded_at_unix_ms",
    "reason",
}


def _parse_receipt(value: Mapping[str, object]) -> TerminalReceipt:
    _require_exact_keys(value, _RECEIPT_FIELDS)
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise InvalidStateError("receipt version is incompatible")
    kind = value["kind"]
    source_name = value["source_name"]
    digest = value["envelope_sha256"]
    reason = value["reason"]
    digest_complete = _require_boolean(value["digest_complete"])
    if not isinstance(kind, str) or kind not in _RECEIPT_KINDS:
        raise InvalidStateError("receipt kind is invalid")
    if not isinstance(source_name, str) or _ENVELOPE_RE.fullmatch(source_name) is None:
        raise InvalidStateError("receipt source name is invalid")
    if digest is not None and (
        not isinstance(digest, str) or _SHA256_RE.fullmatch(digest) is None
    ):
        raise InvalidStateError("receipt digest is invalid")
    if reason is not None and (
        not isinstance(reason, str) or reason not in _RECEIPT_REASONS
    ):
        raise InvalidStateError("receipt reason is invalid")
    envelope_bytes = int(_require_counter(value["envelope_bytes"]))
    recorded_at = int(_require_counter(value["recorded_at_unix_ms"]))
    if kind in {"committed", "replayed"}:
        if reason is not None or not digest_complete or digest is None:
            raise InvalidStateError("successful receipt fields are inconsistent")
        if envelope_bytes > ENVELOPE_MAX_BYTES:
            raise InvalidStateError("successful receipt byte count is invalid")
    elif kind == "conflict":
        if reason != "trace_conflict" or not digest_complete or digest is None:
            raise InvalidStateError("conflict receipt fields are inconsistent")
    elif reason is None or reason == "trace_conflict":
        raise InvalidStateError("rejected receipt reason is inconsistent")
    if reason == "oversized":
        if digest_complete or digest is not None or envelope_bytes <= ENVELOPE_MAX_BYTES:
            raise InvalidStateError("oversized receipt fields are inconsistent")
    elif kind in {"rejected", "conflict"} and (
        not digest_complete or digest is None or envelope_bytes > ENVELOPE_MAX_BYTES
    ):
        raise InvalidStateError("classified receipt digest fields are inconsistent")
    return TerminalReceipt(
        schema_version=1,
        kind=kind,  # type: ignore[arg-type]
        source_name=source_name,
        envelope_sha256=digest,
        digest_complete=digest_complete,
        envelope_bytes=envelope_bytes,
        recorded_at_unix_ms=recorded_at,
        reason=reason,  # type: ignore[arg-type]
    )


def receipt_name_for_source(source_name: str) -> str:
    match = _ENVELOPE_RE.fullmatch(source_name)
    if match is None:
        raise ValueError("recognized v1 envelope name required")
    return f"r1-{match.group(1)}.json"


def receipt_temp_name_for_source(source_name: str) -> str:
    match = _ENVELOPE_RE.fullmatch(source_name)
    if match is None:
        raise ValueError("recognized v1 envelope name required")
    return f"r1-{match.group(1)}.part"


def _read_receipt_at(receipts_fd: int, receipt_name: str) -> TerminalReceipt:
    payload = _read_all_verified(
        receipts_fd,
        receipt_name,
        maximum=RECEIPT_MAX_FILE_BYTES,
    )
    receipt = _parse_receipt(_parse_canonical_object(payload))
    expected = receipt_name_for_source(receipt.source_name)
    if receipt_name != expected:
        raise InvalidStateError("receipt name and source do not match")
    return receipt


def read_terminal_receipt(
    source_name: str,
    *,
    paths: TelemetryPaths | None = None,
) -> TerminalReceipt | None:
    selected = paths or telemetry_paths()
    receipt_name = receipt_name_for_source(source_name)
    try:
        directories = _open_queue_directories(
            selected,
            create=False,
            repair_mode=False,
        )
    except FileNotFoundError:
        return None
    try:
        try:
            return _read_receipt_at(directories.receipts, receipt_name)
        except FileNotFoundError:
            return None
    finally:
        directories.close()


def _time_unix_ms() -> int:
    return time.time_ns() // 1_000_000


@dataclass(frozen=True)
class _ScannedEntry:
    name: str
    size: int
    mtime_ns: int


@dataclass(frozen=True)
class _DirectoryScan:
    entries: tuple[_ScannedEntry, ...]
    incomplete: bool

    @property
    def total_bytes(self) -> int:
        return sum(item.size for item in self.entries)


def _scan_private_files(
    directory_fd: int,
    *,
    accepted: re.Pattern[str],
    maximum_file_bytes: int,
    entry_limit: int = SCAN_MAX_ENTRIES,
    elapsed_limit_ms: int = SCAN_BETWEEN_CALLS_TIMEOUT_MS,
) -> _DirectoryScan:
    """Boundedly scan one verified directory and reject every unknown entry."""

    started = time.monotonic_ns()
    entries: list[_ScannedEntry] = []
    incomplete = False
    with os.scandir(directory_fd) as iterator:
        for entry in iterator:
            if len(entries) >= entry_limit or (
                time.monotonic_ns() - started >= elapsed_limit_ms * 1_000_000
            ):
                incomplete = True
                break
            name = entry.name
            if accepted.fullmatch(name) is None:
                raise UnsafePathError("queue contains an unrecognized entry")
            observed = stat_private_entry_at(
                directory_fd,
                name,
                kind="file",
                max_bytes=maximum_file_bytes,
            )
            entries.append(
                _ScannedEntry(
                    name=name,
                    size=observed.st_size,
                    mtime_ns=observed.st_mtime_ns,
                )
            )
    entries.sort(key=lambda item: item.name)
    return _DirectoryScan(tuple(entries), incomplete)


def _scan_receipt_files(
    receipts_fd: int,
) -> tuple[_DirectoryScan, _DirectoryScan]:
    """Scan final receipts and receipt temporaries in one bounded pass."""

    started = time.monotonic_ns()
    finals: list[_ScannedEntry] = []
    temporaries: list[_ScannedEntry] = []
    incomplete = False
    with os.scandir(receipts_fd) as iterator:
        for entry in iterator:
            if len(finals) + len(temporaries) >= SCAN_MAX_ENTRIES or (
                time.monotonic_ns() - started
                >= SCAN_BETWEEN_CALLS_TIMEOUT_MS * 1_000_000
            ):
                incomplete = True
                break
            name = entry.name
            is_final = _RECEIPT_RE.fullmatch(name) is not None
            is_temporary = _RECEIPT_TEMP_RE.fullmatch(name) is not None
            if not is_final and not is_temporary:
                raise UnsafePathError("receipt directory contains an unknown entry")
            observed = stat_private_entry_at(
                receipts_fd,
                name,
                kind="file",
                max_bytes=RECEIPT_MAX_FILE_BYTES,
            )
            scanned = _ScannedEntry(name, observed.st_size, observed.st_mtime_ns)
            (finals if is_final else temporaries).append(scanned)
    finals.sort(key=lambda item: item.name)
    temporaries.sort(key=lambda item: item.name)
    return (
        _DirectoryScan(tuple(finals), incomplete),
        _DirectoryScan(tuple(temporaries), incomplete),
    )


def _strict_queue_scans(
    directories: _QueueDirectoryFds,
) -> tuple[_DirectoryScan, _DirectoryScan, _DirectoryScan, _DirectoryScan, _DirectoryScan]:
    temporary = _scan_private_files(
        directories.temporary,
        accepted=_ENVELOPE_TEMP_RE,
        maximum_file_bytes=ENVELOPE_MAX_BYTES,
    )
    ready = _scan_private_files(
        directories.ready,
        accepted=_ENVELOPE_RE,
        maximum_file_bytes=COUNTER_MAX,
    )
    claimed = _scan_private_files(
        directories.claimed,
        accepted=_ENVELOPE_RE,
        maximum_file_bytes=max(ENVELOPE_MAX_BYTES, COUNTER_MAX),
    )
    receipts, receipt_temps = _scan_receipt_files(directories.receipts)
    if any(
        scan.incomplete
        for scan in (temporary, ready, claimed, receipts, receipt_temps)
    ):
        raise UnsafePathError("queue scan exceeded its governed bound")
    ready_names = {item.name for item in ready.entries}
    claimed_names = {item.name for item in claimed.entries}
    if ready_names & claimed_names:
        raise UnsafePathError("one envelope appears in ready and claimed")
    return temporary, ready, claimed, receipts, receipt_temps


def _verify_preflight_directory_fd(descriptor: int) -> None:
    """Verify directory type/ownership without mutating a repairable mode."""

    observed = os.fstat(descriptor)
    if not stat.S_ISDIR(observed.st_mode) or observed.st_uid != os.geteuid():
        raise UnsafePathError("private directory metadata is unsafe")


def _open_preflight_directory(path: Path | str) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        descriptor = os.open(os.fspath(path), flags)
    except FileNotFoundError:
        raise
    except OSError as exc:
        if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise UnsafePathError("private directory could not be opened safely") from exc
        raise UnreadablePathError("private directory could not be read") from exc
    try:
        _verify_preflight_directory_fd(descriptor)
    except Exception:
        os.close(descriptor)
        raise
    return descriptor


def _open_preflight_directory_at(parent_fd: int, name: str) -> int:
    _require_basename(name)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        descriptor = os.open(name, flags, dir_fd=parent_fd)
    except FileNotFoundError:
        raise
    except OSError as exc:
        if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise UnsafePathError(
                "private child directory could not be opened safely"
            ) from exc
        raise UnreadablePathError("private child directory could not be read") from exc
    try:
        _verify_preflight_directory_fd(descriptor)
    except Exception:
        os.close(descriptor)
        raise
    return descriptor


def _scan_inbox_directory_names(inbox_fd: int) -> frozenset[str]:
    expected = frozenset({"tmp", "ready", "claimed", "receipts"})
    started = time.monotonic_ns()
    names: set[str] = set()
    with os.scandir(inbox_fd) as iterator:
        for entry in iterator:
            if len(names) >= SCAN_MAX_ENTRIES or (
                time.monotonic_ns() - started
                >= SCAN_BETWEEN_CALLS_TIMEOUT_MS * 1_000_000
            ):
                raise TelemetryQueueError("inbox preflight scan exceeded its bound")
            if entry.name not in expected:
                raise UnsafePathError("inbox contains an unrecognized entry")
            names.add(entry.name)
    return frozenset(names)


def _preflight_existing_publication_tree(paths: TelemetryPaths) -> None:
    """Reject an unsafe existing v1 tree before creating or repairing anything.

    Directory modes remain repairable after ownership is established under the
    queue lock.  Existing payload entries retain the same strict metadata and
    bounded-name checks as the authoritative scan.
    """

    try:
        parent_fd = _open_preflight_directory(paths.directory.parent)
    except FileNotFoundError:
        return
    root_fd: int | None = None
    inbox_fd: int | None = None
    child_fds: dict[str, int] = {}
    try:
        try:
            root_fd = _open_preflight_directory_at(
                parent_fd,
                paths.directory.name,
            )
        except FileNotFoundError:
            return
        try:
            inbox_fd = _open_preflight_directory_at(root_fd, "inbox-v1")
        except FileNotFoundError:
            return

        names = _scan_inbox_directory_names(inbox_fd)
        for name in ("tmp", "ready", "claimed", "receipts"):
            if name not in names:
                continue
            child_fds[name] = _open_preflight_directory_at(inbox_fd, name)

        try:
            queue_lock_stat = os.stat(
                "queue.lock",
                dir_fd=root_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            queue_lock_exists = False
        else:
            queue_lock_exists = True
            if (
                not stat.S_ISREG(queue_lock_stat.st_mode)
                or queue_lock_stat.st_uid != os.geteuid()
                or queue_lock_stat.st_nlink != 1
                or queue_lock_stat.st_size != 0
            ):
                raise UnsafePathError("queue lock metadata is unsafe")

        # The authoritative locked scan will recheck all contents.  This first
        # pass is needed only when that operation would otherwise create a lock
        # or a missing fixed directory before discovering an unsafe entry.
        if queue_lock_exists and names == frozenset(
            {"tmp", "ready", "claimed", "receipts"}
        ):
            return

        empty = _DirectoryScan((), False)
        temporary = (
            _scan_private_files(
                child_fds["tmp"],
                accepted=_ENVELOPE_TEMP_RE,
                maximum_file_bytes=ENVELOPE_MAX_BYTES,
            )
            if "tmp" in child_fds
            else empty
        )
        ready = (
            _scan_private_files(
                child_fds["ready"],
                accepted=_ENVELOPE_RE,
                maximum_file_bytes=COUNTER_MAX,
            )
            if "ready" in child_fds
            else empty
        )
        claimed = (
            _scan_private_files(
                child_fds["claimed"],
                accepted=_ENVELOPE_RE,
                maximum_file_bytes=COUNTER_MAX,
            )
            if "claimed" in child_fds
            else empty
        )
        if "receipts" in child_fds:
            receipts, receipt_temps = _scan_receipt_files(child_fds["receipts"])
        else:
            receipts, receipt_temps = empty, empty
        if any(
            scan.incomplete
            for scan in (temporary, ready, claimed, receipts, receipt_temps)
        ):
            raise TelemetryQueueError("queue preflight scan exceeded its bound")
        if {item.name for item in ready.entries} & {
            item.name for item in claimed.entries
        }:
            raise UnsafePathError("one envelope appears in ready and claimed")
    finally:
        for descriptor in child_fds.values():
            try:
                os.close(descriptor)
            except OSError:
                pass
        if inbox_fd is not None:
            os.close(inbox_fd)
        if root_fd is not None:
            os.close(root_fd)
        os.close(parent_fd)


def _open_read_only_queue(
    paths: TelemetryPaths,
) -> _QueueDirectoryFds | None:
    try:
        root_fd = _open_telemetry_root(paths, create=False, repair_mode=False)
    except FileNotFoundError:
        return None
    try:
        for lock_name in (
            "queue.lock",
            "writer.lock",
            "writer-start.lock",
            "write.lock",
        ):
            try:
                stat_private_entry_at(
                    root_fd,
                    lock_name,
                    kind="file",
                    max_bytes=0,
                )
            except FileNotFoundError:
                pass
        try:
            inbox_fd = open_private_directory_at(
                root_fd,
                "inbox-v1",
                create=False,
                repair_mode=False,
            )
        except FileNotFoundError:
            os.close(root_fd)
            return None
        _scan_inbox_directory_names(inbox_fd)
        child_fds: list[int] = []
        try:
            for name in ("tmp", "ready", "claimed", "receipts"):
                child_fds.append(
                    open_private_directory_at(
                        inbox_fd,
                        name,
                        create=False,
                        repair_mode=False,
                    )
                )
        except Exception:
            for descriptor in child_fds:
                os.close(descriptor)
            os.close(inbox_fd)
            raise
        return _QueueDirectoryFds(
            root=root_fd,
            inbox=inbox_fd,
            temporary=child_fds[0],
            ready=child_fds[1],
            claimed=child_fds[2],
            receipts=child_fds[3],
        )
    except Exception:
        try:
            os.close(root_fd)
        except OSError:
            pass
        raise


def scan_queue_read_only(
    paths: TelemetryPaths | None = None,
) -> QueueSnapshot:
    """Inspect the fixed queue without creating, repairing, locking, or deleting."""

    selected = paths or telemetry_paths()
    capability = posix_writer_capability()
    if not capability.supported:
        return QueueSnapshot(present=False, unsafe=True)
    try:
        directories = _open_read_only_queue(selected)
        if directories is None:
            return QueueSnapshot(present=False)
        try:
            temporary = _scan_private_files(
                directories.temporary,
                accepted=_ENVELOPE_TEMP_RE,
                maximum_file_bytes=ENVELOPE_MAX_BYTES,
            )
            ready = _scan_private_files(
                directories.ready,
                accepted=_ENVELOPE_RE,
                maximum_file_bytes=COUNTER_MAX,
            )
            claimed = _scan_private_files(
                directories.claimed,
                accepted=_ENVELOPE_RE,
                maximum_file_bytes=COUNTER_MAX,
            )
            receipts, receipt_temps = _scan_receipt_files(directories.receipts)
        finally:
            directories.close()
        pending = ready.entries + claimed.entries
        pending_bytes = sum(item.size for item in pending)
        scan_incomplete = any(
            scan.incomplete
            for scan in (temporary, ready, claimed, receipts, receipt_temps)
        )
        return QueueSnapshot(
            present=True,
            ready=len(ready.entries),
            claimed=len(claimed.entries),
            temporary=len(temporary.entries),
            receipts=len(receipts.entries),
            pending_bytes=pending_bytes,
            temporary_bytes=temporary.total_bytes,
            receipt_bytes=receipts.total_bytes + receipt_temps.total_bytes,
            oldest_pending_mtime_ns=(
                min(item.mtime_ns for item in pending) if pending else None
            ),
            capacity_full=(
                len(pending) >= PUBLISHED_MAX_ENTRIES
                or pending_bytes >= PUBLISHED_MAX_BYTES
                or len(temporary.entries) >= TEMP_MAX_ENTRIES
                or temporary.total_bytes >= TEMP_MAX_BYTES
            ),
            scan_incomplete=scan_incomplete,
            ready_names=tuple(item.name for item in ready.entries),
            claimed_names=tuple(item.name for item in claimed.entries),
            receipt_names=tuple(item.name for item in receipts.entries),
        )
    except (UnsafePathError, InvalidStateError):
        return QueueSnapshot(present=True, unsafe=True)
    except (UnreadablePathError, OSError):
        return QueueSnapshot(present=True, unreadable=True)


def _name_exists(parent_fd: int, name: str) -> bool:
    try:
        os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    return True


def _fresh_token(directories: _QueueDirectoryFds) -> str:
    for _ in range(8):
        token = secrets.token_hex(16)
        if _TOKEN_RE.fullmatch(token) is None:
            continue
        temp_name = f"v1-{token}.part"
        source_name = f"v1-{token}.json"
        receipt_name = f"r1-{token}.json"
        receipt_temp_name = f"r1-{token}.part"
        if not any(
            (
                _name_exists(directories.temporary, temp_name),
                _name_exists(directories.ready, source_name),
                _name_exists(directories.claimed, source_name),
                _name_exists(directories.receipts, receipt_name),
                _name_exists(directories.receipts, receipt_temp_name),
            )
        ):
            return token
    raise TelemetryQueueError("could not allocate a unique envelope token")


def publish_envelope(
    payload: bytes,
    *,
    paths: TelemetryPaths | None = None,
) -> PublicationResult:
    """Atomically publish one already-canonical governed envelope."""

    selected = paths or telemetry_paths()
    capability = posix_writer_capability()
    if not capability.supported:
        return PublicationResult(False, None, "platform_unsupported")
    try:
        _preflight_existing_publication_tree(selected)
    except (TelemetryQueueError, OSError, ValueError):
        # Accounting would itself create queue.lock, violating the unsafe-path
        # zero-new-asset boundary that this preflight protects.
        return PublicationResult(False, None, "publication_failure")
    if not isinstance(payload, bytes) or not payload or len(payload) > ENVELOPE_MAX_BYTES:
        increment_producer_accounting("publication_failure", paths=selected)
        return PublicationResult(False, None, "publication_failure")
    try:
        with queue_lock(
            selected,
            timeout_ms=PUBLICATION_LOCK_TIMEOUT_MS,
        ):
            directories = _open_queue_directories(selected, create=True)
            try:
                renamed_source_name: str | None = None
                temporary, ready, claimed, _receipts, _receipt_temps = (
                    _strict_queue_scans(directories)
                )
                pending_count = len(ready.entries) + len(claimed.entries)
                pending_bytes = ready.total_bytes + claimed.total_bytes
                if (
                    pending_count >= PUBLISHED_MAX_ENTRIES
                    or pending_bytes + len(payload) > PUBLISHED_MAX_BYTES
                    or len(temporary.entries) >= TEMP_MAX_ENTRIES
                    or temporary.total_bytes + len(payload) > TEMP_MAX_BYTES
                ):
                    _increment_accounting_at(directories.root, "queue_full")
                    return PublicationResult(False, None, "queue_full")
                token = _fresh_token(directories)
                temp_name = f"v1-{token}.part"
                source_name = f"v1-{token}.json"
                descriptor = open_private_file_at(
                    directories.temporary,
                    temp_name,
                    flags=os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    max_bytes=ENVELOPE_MAX_BYTES,
                )
                try:
                    _write_all(descriptor, payload)
                    os.fchmod(descriptor, _FILE_MODE)
                    os.fsync(descriptor)
                    observed = verify_private_file_fd(
                        descriptor,
                        max_bytes=ENVELOPE_MAX_BYTES,
                    )
                    if observed.st_size != len(payload):
                        raise UnsafePathError("envelope temporary size changed")
                    _require_open_name_matches_fd(
                        directories.temporary,
                        temp_name,
                        descriptor,
                    )
                    os.rename(
                        temp_name,
                        source_name,
                        src_dir_fd=directories.temporary,
                        dst_dir_fd=directories.ready,
                    )
                    renamed_source_name = source_name
                finally:
                    os.close(descriptor)
                durability_degraded = False
                try:
                    durability_degraded = not fsync_directory(directories.ready)
                except OSError:
                    durability_degraded = True
                if durability_degraded:
                    try:
                        _increment_accounting_at(
                            directories.root,
                            "directory_sync_failure",
                        )
                    except Exception:
                        # Accounting is explicitly a lower bound.  Once the
                        # ready rename has completed it cannot revoke or
                        # reclassify the published envelope.
                        pass
                return PublicationResult(
                    True,
                    source_name,
                    "published",
                    durability_degraded=durability_degraded,
                )
            except Exception as exc:
                if renamed_source_name is not None:
                    # The ready rename is the publication linearization point.
                    # No later close/sync/accounting failure may reclassify the
                    # recoverable envelope as a producer drop.
                    try:
                        _increment_accounting_at(
                            directories.root,
                            "directory_sync_failure",
                        )
                    except Exception:
                        pass
                    return PublicationResult(
                        True,
                        renamed_source_name,
                        "published",
                        durability_degraded=True,
                    )
                if not isinstance(exc, (UnsafePathError, UnreadablePathError)):
                    _increment_accounting_at(
                        directories.root,
                        "publication_failure",
                    )
                raise
            finally:
                directories.close()
    except QueueLockTimeout:
        # The counter is a lower bound: the same unavailable queue lock may
        # prevent its safe update.
        return PublicationResult(False, None, "queue_lock_timeout")
    except UnsupportedPlatformError:
        return PublicationResult(False, None, "platform_unsupported")
    except (TelemetryQueueError, OSError):
        return PublicationResult(False, None, "publication_failure")


def cleanup_stale_envelope_temporaries(
    *,
    paths: TelemetryPaths | None = None,
    now_unix_ns: int | None = None,
) -> tuple[str, ...]:
    """Remove only recognized private publication temps at least 24 hours old."""

    selected = paths or telemetry_paths()
    cutoff = (
        time.time_ns() if now_unix_ns is None else now_unix_ns
    ) - STALE_ENVELOPE_TEMP_SECONDS * 1_000_000_000
    removed: list[str] = []
    with queue_lock(selected):
        directories = _open_queue_directories(selected, create=False)
        try:
            scan = _scan_private_files(
                directories.temporary,
                accepted=_ENVELOPE_TEMP_RE,
                maximum_file_bytes=ENVELOPE_MAX_BYTES,
            )
            if scan.incomplete:
                raise TelemetryQueueError("temporary scan exceeded its bound")
            for item in sorted(scan.entries, key=lambda value: (value.mtime_ns, value.name)):
                if item.mtime_ns > cutoff:
                    continue
                safe_unlink_at(directories.temporary, item.name)
                removed.append(item.name)
            if removed:
                fsync_directory(directories.temporary)
            return tuple(removed)
        finally:
            directories.close()


def claim_ready_batch(
    paths: TelemetryPaths,
    limit: int = 128,
) -> tuple[str, ...]:
    """Atomically claim up to the fixed writer batch maximum."""

    if type(limit) is not int or not 1 <= limit <= 128:
        raise ValueError("claim limit must be between 1 and 128")
    claimed_names: list[str] = []
    with queue_lock(paths):
        directories = _open_queue_directories(paths, create=False)
        try:
            _temporary, ready, existing_claimed, _receipts, _receipt_temps = (
                _strict_queue_scans(directories)
            )
            existing = {item.name for item in existing_claimed.entries}
            for item in ready.entries[:limit]:
                if item.name in existing:
                    raise UnsafePathError("claim destination already exists")
                os.rename(
                    item.name,
                    item.name,
                    src_dir_fd=directories.ready,
                    dst_dir_fd=directories.claimed,
                )
                claimed_names.append(item.name)
            if claimed_names:
                fsync_directory(directories.ready)
                fsync_directory(directories.claimed)
            return tuple(claimed_names)
        finally:
            directories.close()


def recover_claim(
    paths: TelemetryPaths,
    source_name: str,
) -> bool:
    """Return one receipt-free claimed envelope to ready under queue authority."""

    if _ENVELOPE_RE.fullmatch(source_name) is None:
        raise ValueError("recognized v1 envelope name required")
    with queue_lock(paths):
        directories = _open_queue_directories(paths, create=False)
        try:
            _strict_queue_scans(directories)
            stat_private_entry_at(
                directories.claimed,
                source_name,
                kind="file",
                max_bytes=COUNTER_MAX,
            )
            if _name_exists(directories.ready, source_name):
                raise UnsafePathError("claim recovery destination exists")
            if _name_exists(
                directories.receipts,
                receipt_name_for_source(source_name),
            ):
                return False
            os.rename(
                source_name,
                source_name,
                src_dir_fd=directories.claimed,
                dst_dir_fd=directories.ready,
            )
            fsync_directory(directories.claimed)
            fsync_directory(directories.ready)
            return True
        finally:
            directories.close()


def recover_all_claims(
    paths: TelemetryPaths,
) -> tuple[str, ...]:
    """Recover every bounded receipt-free claim after writer election."""

    recovered: list[str] = []
    with queue_lock(paths):
        directories = _open_queue_directories(paths, create=False)
        try:
            _temporary, ready, claimed, _receipts, _receipt_temps = (
                _strict_queue_scans(directories)
            )
            ready_names = {item.name for item in ready.entries}
            for item in claimed.entries:
                if item.name in ready_names:
                    raise UnsafePathError("claim recovery destination exists")
                receipt_name = receipt_name_for_source(item.name)
                if _name_exists(directories.receipts, receipt_name):
                    continue
                os.rename(
                    item.name,
                    item.name,
                    src_dir_fd=directories.claimed,
                    dst_dir_fd=directories.ready,
                )
                recovered.append(item.name)
            if recovered:
                fsync_directory(directories.claimed)
                fsync_directory(directories.ready)
            return tuple(recovered)
        finally:
            directories.close()


def read_claimed_envelope(
    paths: TelemetryPaths,
    source_name: str,
) -> ClaimReadResult:
    """Read one stable claimed file with the exact oversized/digest boundary."""

    if _ENVELOPE_RE.fullmatch(source_name) is None:
        raise ValueError("recognized v1 envelope name required")
    directories = _open_queue_directories(paths, create=False)
    try:
        descriptor = open_private_file_at(
            directories.claimed,
            source_name,
            flags=os.O_RDONLY,
            repair_mode=False,
        )
        try:
            before = verify_private_file_fd(descriptor, repair_mode=False)
            if before.st_size > ENVELOPE_MAX_BYTES:
                _require_open_name_matches_fd(
                    directories.claimed,
                    source_name,
                    descriptor,
                )
                return ClaimReadResult(
                    source_name,
                    before.st_size,
                    None,
                    None,
                    False,
                    True,
                )
            chunks: list[bytes] = []
            remaining = ENVELOPE_MAX_BYTES + 1
            while remaining:
                chunk = os.read(descriptor, min(remaining, 65_536))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            payload = b"".join(chunks)
            after = verify_private_file_fd(descriptor, repair_mode=False)
            _require_open_name_matches_fd(
                directories.claimed,
                source_name,
                descriptor,
            )
            if (
                (before.st_dev, before.st_ino, before.st_size)
                != (after.st_dev, after.st_ino, after.st_size)
            ):
                raise UnsafePathError("claimed envelope changed while being read")
            if len(payload) != before.st_size:
                raise UnsafePathError("claimed envelope size changed while being read")
            if len(payload) > ENVELOPE_MAX_BYTES:
                return ClaimReadResult(
                    source_name,
                    after.st_size,
                    None,
                    None,
                    False,
                    True,
                )
            return ClaimReadResult(
                source_name,
                len(payload),
                payload,
                hashlib.sha256(payload).hexdigest(),
                True,
                False,
            )
        finally:
            os.close(descriptor)
    finally:
        directories.close()


def _rotate_receipts_for_payload(
    directories: _QueueDirectoryFds,
    *,
    payload_bytes: int,
    now_unix_ms: int,
) -> tuple[str, ...]:
    finals, temporaries = _scan_receipt_files(directories.receipts)
    if finals.incomplete or temporaries.incomplete:
        raise TelemetryQueueError("receipt scan exceeded its bound")
    if (
        len(temporaries.entries) >= RECEIPT_MAX_ENTRIES
        or temporaries.total_bytes + payload_bytes > RECEIPT_MAX_BYTES
    ):
        raise TelemetryQueueError("receipt temporary capacity is full")
    remaining_count = len(finals.entries)
    remaining_bytes = finals.total_bytes
    if (
        remaining_count + 1 <= RECEIPT_MAX_ENTRIES
        and remaining_bytes + payload_bytes <= RECEIPT_MAX_BYTES
    ):
        return ()
    cutoff_ns = (now_unix_ms - RECEIPT_MIN_AGE_SECONDS * 1_000) * 1_000_000
    eligible = sorted(
        (item for item in finals.entries if item.mtime_ns <= cutoff_ns),
        key=lambda item: (item.mtime_ns, item.name),
    )
    removed: list[str] = []
    for item in eligible:
        if (
            remaining_count + 1 <= RECEIPT_MAX_ENTRIES
            and remaining_bytes + payload_bytes <= RECEIPT_MAX_BYTES
        ):
            break
        safe_unlink_at(directories.receipts, item.name)
        removed.append(item.name)
        remaining_count -= 1
        remaining_bytes -= item.size
    if (
        remaining_count + 1 > RECEIPT_MAX_ENTRIES
        or remaining_bytes + payload_bytes > RECEIPT_MAX_BYTES
    ):
        raise TelemetryQueueError("receipt capacity has no eligible rotation")
    return tuple(removed)


def publish_terminal_receipt(
    paths: TelemetryPaths,
    receipt: TerminalReceipt,
) -> ReceiptPublicationResult:
    """Durably publish one unique content-free terminal receipt."""

    validated = _parse_receipt(_receipt_object(receipt))
    payload = _canonical_json_bytes(
        _receipt_object(validated),
        maximum=RECEIPT_MAX_FILE_BYTES,
    )
    receipt_name = receipt_name_for_source(validated.source_name)
    temporary_name = receipt_temp_name_for_source(validated.source_name)
    with queue_lock(paths):
        directories = _open_queue_directories(paths, create=False)
        try:
            _strict_queue_scans(directories)
            stat_private_entry_at(
                directories.claimed,
                validated.source_name,
                kind="file",
                max_bytes=COUNTER_MAX,
            )
            if _name_exists(directories.receipts, receipt_name):
                existing = _read_receipt_at(directories.receipts, receipt_name)
                if existing != validated:
                    raise InvalidStateError("terminal receipt classification differs")
                return ReceiptPublicationResult(False, True)
            rotated = _rotate_receipts_for_payload(
                directories,
                payload_bytes=len(payload),
                now_unix_ms=validated.recorded_at_unix_ms,
            )
            if _name_exists(directories.receipts, temporary_name):
                raise TelemetryQueueError("terminal receipt temporary already exists")
            descriptor = open_private_file_at(
                directories.receipts,
                temporary_name,
                flags=os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                max_bytes=RECEIPT_MAX_FILE_BYTES,
            )
            try:
                _write_all(descriptor, payload)
                os.fchmod(descriptor, _FILE_MODE)
                os.fsync(descriptor)
                observed = verify_private_file_fd(
                    descriptor,
                    max_bytes=RECEIPT_MAX_FILE_BYTES,
                )
                if observed.st_size != len(payload):
                    raise UnsafePathError("receipt temporary size changed")
                _require_open_name_matches_fd(
                    directories.receipts,
                    temporary_name,
                    descriptor,
                )
            finally:
                os.close(descriptor)
            os.rename(
                temporary_name,
                receipt_name,
                src_dir_fd=directories.receipts,
                dst_dir_fd=directories.receipts,
            )
            durability_degraded = False
            try:
                durability_degraded = not fsync_directory(directories.receipts)
            except OSError:
                durability_degraded = True
            return ReceiptPublicationResult(
                True,
                False,
                rotated_names=rotated,
                durability_degraded=durability_degraded,
            )
        finally:
            directories.close()


def acknowledge_claim(
    paths: TelemetryPaths,
    source_name: str,
) -> bool:
    """Remove one claim only after its matching valid final receipt exists."""

    if _ENVELOPE_RE.fullmatch(source_name) is None:
        raise ValueError("recognized v1 envelope name required")
    with queue_lock(paths):
        directories = _open_queue_directories(paths, create=False)
        try:
            _strict_queue_scans(directories)
            receipt = _read_receipt_at(
                directories.receipts,
                receipt_name_for_source(source_name),
            )
            if receipt.source_name != source_name:
                raise InvalidStateError("receipt does not acknowledge this claim")
            try:
                safe_unlink_at(directories.claimed, source_name)
            except FileNotFoundError:
                return False
            fsync_directory(directories.claimed)
            return True
        finally:
            directories.close()


def inspect_receipt_temporaries(
    paths: TelemetryPaths,
) -> tuple[str, ...]:
    """Return bounded recognized receipt-temp names for elected-writer recovery."""

    directories = _open_queue_directories(paths, create=False)
    try:
        _finals, temporaries = _scan_receipt_files(directories.receipts)
        if temporaries.incomplete:
            raise TelemetryQueueError("receipt temporary scan exceeded its bound")
        return tuple(item.name for item in temporaries.entries)
    finally:
        directories.close()


def read_terminal_receipt_temporary(
    paths: TelemetryPaths,
    temporary_name: str,
) -> TerminalReceipt:
    """Read and validate a recognized construction temporary without finalizing it."""

    match = _RECEIPT_TEMP_RE.fullmatch(temporary_name)
    if match is None:
        raise ValueError("recognized v1 receipt temporary name required")
    directories = _open_queue_directories(paths, create=False)
    try:
        payload = _read_all_verified(
            directories.receipts,
            temporary_name,
            maximum=RECEIPT_MAX_FILE_BYTES,
        )
        receipt = _parse_receipt(_parse_canonical_object(payload))
        if receipt_temp_name_for_source(receipt.source_name) != temporary_name:
            raise InvalidStateError("receipt temporary name and source differ")
        return receipt
    finally:
        directories.close()


def resolve_receipt_temporary(
    paths: TelemetryPaths,
    temporary_name: str,
    *,
    terminal_condition_proven: bool,
) -> bool:
    """Finalize a proven receipt temp, otherwise safely discard only that temp.

    The elected writer independently proves the envelope/database terminal
    condition before passing ``terminal_condition_proven=True``.
    """

    match = _RECEIPT_TEMP_RE.fullmatch(temporary_name)
    if match is None:
        raise ValueError("recognized v1 receipt temporary name required")
    with queue_lock(paths):
        directories = _open_queue_directories(paths, create=False)
        try:
            _strict_queue_scans(directories)
            try:
                payload = _read_all_verified(
                    directories.receipts,
                    temporary_name,
                    maximum=RECEIPT_MAX_FILE_BYTES,
                )
                receipt = _parse_receipt(_parse_canonical_object(payload))
                valid_name = (
                    receipt_temp_name_for_source(receipt.source_name)
                    == temporary_name
                )
            except (InvalidStateError, UnsafePathError, UnreadablePathError):
                receipt = None
                valid_name = False
            final_name = f"r1-{match.group(1)}.json"
            source_name = f"v1-{match.group(1)}.json"
            final_exists = _name_exists(directories.receipts, final_name)
            claim_exists = _name_exists(directories.claimed, source_name)
            if final_exists:
                _read_receipt_at(directories.receipts, final_name)
                safe_unlink_at(directories.receipts, temporary_name)
                fsync_directory(directories.receipts)
                return False
            if (
                receipt is not None
                and valid_name
                and claim_exists
                and terminal_condition_proven
            ):
                os.rename(
                    temporary_name,
                    final_name,
                    src_dir_fd=directories.receipts,
                    dst_dir_fd=directories.receipts,
                )
                fsync_directory(directories.receipts)
                return True
            safe_unlink_at(directories.receipts, temporary_name)
            fsync_directory(directories.receipts)
            return False
        finally:
            directories.close()


def snapshot_pending(
    paths: TelemetryPaths | None = None,
) -> PendingSnapshot:
    """Capture flush's fixed ready/claimed set and any existing terminal receipt."""

    selected = paths or telemetry_paths()
    try:
        probe = _open_read_only_queue(selected)
        if probe is None:
            return PendingSnapshot(())
    except FileNotFoundError:
        return PendingSnapshot(())
    else:
        probe.close()
    with queue_lock(selected):
        directories = _open_queue_directories(selected, create=False)
        try:
            _temporary, ready, claimed, _receipts, _receipt_temps = (
                _strict_queue_scans(directories)
            )
            items: list[PendingItem] = []
            for location, scan in (("ready", ready), ("claimed", claimed)):
                for entry in scan.entries:
                    receipt_name = receipt_name_for_source(entry.name)
                    terminal: ReceiptKind | None = None
                    if _name_exists(directories.receipts, receipt_name):
                        terminal = _read_receipt_at(
                            directories.receipts,
                            receipt_name,
                        ).kind
                    items.append(
                        PendingItem(
                            source_name=entry.name,
                            location=location,  # type: ignore[arg-type]
                            terminal_kind=terminal,
                        )
                    )
            items.sort(key=lambda item: (item.source_name, item.location))
            return PendingSnapshot(tuple(items))
        finally:
            directories.close()


def terminal_kind_for_snapshot_item(
    paths: TelemetryPaths,
    item: PendingItem,
) -> ReceiptKind | None:
    """Return a terminal classification only after the item has left the queue."""

    directories = _open_queue_directories(paths, create=False, repair_mode=False)
    try:
        if _name_exists(directories.ready, item.source_name) or _name_exists(
            directories.claimed, item.source_name
        ):
            return None
        try:
            receipt = _read_receipt_at(
                directories.receipts,
                receipt_name_for_source(item.source_name),
            )
        except FileNotFoundError:
            return item.terminal_kind
        return receipt.kind
    finally:
        directories.close()


def increment_writer_counter(
    state: WriterState,
    field: str,
    amount: int = 1,
) -> WriterState:
    """Return state with one governed saturating writer counter advanced."""

    allowed = {
        "rejected",
        "conflicts",
        "replays",
        "recovered_claims",
        "write_failures",
        "receipts_rotated",
    }
    if field not in allowed or type(amount) is not int or amount < 0:
        raise ValueError("invalid writer counter update")
    current = int(getattr(state, field))
    incomplete = state.accounting_incomplete or current > COUNTER_MAX - amount
    return replace(
        state,
        **{
            field: min(COUNTER_MAX, current + amount),
            "accounting_incomplete": incomplete,
        },
    )


def reconcile_writer_receipts(
    state: WriterState,
    *,
    paths: TelemetryPaths | None = None,
) -> WriterState:
    """Idempotently reconcile visible terminal receipts into aggregate state."""

    selected = paths or telemetry_paths()
    with queue_lock(selected):
        directories = _open_queue_directories(selected, create=False)
        try:
            finals, temporaries = _scan_receipt_files(directories.receipts)
            if finals.incomplete or temporaries.incomplete:
                return replace(state, accounting_incomplete=True)
            visible_names = {item.name for item in finals.entries}
            accounted = set(state.accounted_receipts)
            updated = state
            for missing in sorted(accounted - visible_names):
                del missing
                updated = increment_writer_counter(updated, "receipts_rotated")
            for receipt_name in sorted(visible_names - accounted):
                receipt = _read_receipt_at(directories.receipts, receipt_name)
                if receipt.kind == "replayed":
                    updated = increment_writer_counter(updated, "replays")
                elif receipt.kind == "rejected":
                    updated = increment_writer_counter(updated, "rejected")
                elif receipt.kind == "conflict":
                    updated = increment_writer_counter(updated, "conflicts")
            return replace(
                updated,
                accounted_receipts=tuple(sorted(visible_names)),
            )
        finally:
            directories.close()


def _fresh_writer_state_suppresses_start(
    state: WriterState | None,
    *,
    now_unix_ms: int,
) -> bool:
    if state is None or state.phase == "stopped":
        return False
    age = max(0, now_unix_ms - state.heartbeat_unix_ms)
    return state.phase in {"starting", "idle", "draining", "blocked"} and (
        age < START_LEASE_SECONDS * 1_000
    )


def request_writer_start(
    *,
    paths: TelemetryPaths | None = None,
) -> WriterStartResult:
    """Make one exact best-effort detached writer start attempt."""

    selected = paths or telemetry_paths()
    capability = posix_writer_capability()
    if not capability.supported:
        return WriterStartResult(False, False, "platform_unsupported")
    try:
        with writer_start_lock(selected):
            root_fd = _open_telemetry_root(selected, create=False)
            try:
                now_ms = _time_unix_ms()
                try:
                    state = _read_writer_state_at(root_fd)
                except InvalidStateError:
                    state = None
                if _fresh_writer_state_suppresses_start(
                    state,
                    now_unix_ms=now_ms,
                ):
                    return WriterStartResult(False, True, "active_writer")
                try:
                    lease = _read_start_lease_at(root_fd)
                except InvalidStateError:
                    lease = None
                if lease is not None and (
                    max(0, now_ms - lease.lease_started_unix_ms)
                    < START_LEASE_SECONDS * 1_000
                ):
                    return WriterStartResult(False, True, "start_lease")
                _write_start_lease_at(
                    root_fd,
                    WriterStartLease(1, now_ms),
                )
                executable = os.path.abspath(sys.executable)
                if not executable or not os.path.isabs(executable):
                    raise OSError("current Python executable is unavailable")
                # This child is intentionally detached and never waited on by
                # the producer.  CPython's Popen destructor warns for that
                # exact fire-and-forget lifecycle, so release it while a
                # narrowly scoped ResourceWarning filter is active.
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", ResourceWarning)
                    child = subprocess.Popen(
                        [
                            executable,
                            "-I",
                            "-X",
                            "utf8",
                            "-m",
                            "buoy_search.telemetry_writer",
                        ],
                        cwd=os.fspath(selected.directory),
                        env={},
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        close_fds=True,
                        start_new_session=True,
                        shell=False,
                    )
                    del child
                return WriterStartResult(True, False, "started")
            finally:
                os.close(root_fd)
    except QueueLockTimeout:
        increment_producer_accounting("writer_start_failure", paths=selected)
        return WriterStartResult(False, False, "start_lock_timeout")
    except UnsupportedPlatformError:
        return WriterStartResult(False, False, "platform_unsupported")
    except (TelemetryQueueError, OSError, ValueError):
        increment_producer_accounting("writer_start_failure", paths=selected)
        return WriterStartResult(False, False, "writer_start_failure")


def publish_envelope_and_start(
    payload: bytes,
    *,
    paths: TelemetryPaths | None = None,
) -> PublicationResult:
    """Producer convenience: publish first, then make one best-effort start."""

    selected = paths or telemetry_paths()
    publication = publish_envelope(payload, paths=selected)
    if publication.published:
        request_writer_start(paths=selected)
    return publication
