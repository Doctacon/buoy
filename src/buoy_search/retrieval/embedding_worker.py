"""Private local worker for exact retrieve embedding and reranker inference."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import socket
import stat
import struct
import subprocess
import sys
import time
from typing import Callable, Iterator, Mapping, Sequence, TypeVar
import warnings

try:  # POSIX-only prototype.
    import fcntl
except ImportError:  # pragma: no cover - exercised only on unsupported platforms.
    fcntl = None  # type: ignore[assignment]

from buoy_search import __version__
from buoy_search.catalog.local import (
    ROUTING_DIMENSIONS,
    ROUTING_MODEL,
    ROUTING_MODEL_REVISION,
    ROUTING_PRECISION,
)
from buoy_search.local_paths import default_buoy_home, normalized_absolute
from buoy_search.model_progress import suppress_model_progress_bars
from buoy_search.retrieval.cross_encoder import (
    CROSS_ENCODER_BATCH_SIZE,
    CROSS_ENCODER_MAX_LENGTH,
    CROSS_ENCODER_MODEL,
    CROSS_ENCODER_REVISION,
    load_cross_encoder_reranker,
)

SCHEMA_VERSION = 2
MODEL = ROUTING_MODEL
REVISION = ROUTING_MODEL_REVISION
PRECISION = ROUTING_PRECISION
DIMENSIONS = ROUTING_DIMENSIONS
RERANKER_MODEL = CROSS_ENCODER_MODEL
RERANKER_REVISION = CROSS_ENCODER_REVISION
RERANKER_DEVICE = "cpu"
RERANKER_MAX_LENGTH = CROSS_ENCODER_MAX_LENGTH
RERANKER_BATCH_SIZE = CROSS_ENCODER_BATCH_SIZE
RERANKER_LOCAL_FILES_ONLY = True
RERANKER_USE_SAFETENSORS = True
RERANKER_TRUST_REMOTE_CODE = False
IDLE_EXIT_SECONDS = 300.0
STARTUP_TIMEOUT_SECONDS = 120.0
REQUEST_TIMEOUT_SECONDS = 120.0
LOCK_POLL_SECONDS = 0.01
MAX_FRAME_BYTES = 8_388_608
MAX_TEXTS = 16
MAX_SCORE_PASSAGES = 108
MAX_TEXT_BYTES = 65_536
MAX_SOCKET_PATH_BYTES = 100
_DIRECTORY_MODE = 0o700
_FILE_MODE = 0o600
_SOCKET_MODE = 0o600

_ENCODE_REQUEST_FIELDS = frozenset(
    {"schema_version", "operation", "model", "revision", "precision", "texts"}
)
_SCORE_REQUEST_FIELDS = frozenset(
    {"schema_version", "operation", "model", "revision", "query", "passages"}
)
_ENCODE_SUCCESS_FIELDS = frozenset(
    {"schema_version", "outcome", "dimensions", "vectors"}
)
_SCORE_SUCCESS_FIELDS = frozenset(
    {"schema_version", "outcome", "model", "revision", "scores"}
)
_ERROR_FIELDS = frozenset({"schema_version", "outcome", "error_type"})
_READY_FIELDS = frozenset(
    {
        "schema_version",
        "outcome",
        "model",
        "revision",
        "precision",
        "dimensions",
        "package_version",
        "python_version",
        "implementation_id",
        "reranker_model",
        "reranker_revision",
        "reranker_device",
        "reranker_max_length",
        "reranker_batch_size",
        "reranker_local_files_only",
        "reranker_use_safetensors",
        "reranker_trust_remote_code",
    }
)
_STATE_FIELDS = frozenset(
    {
        "schema_version",
        "phase",
        "model",
        "revision",
        "precision",
        "dimensions",
        "package_version",
        "python_version",
        "implementation_id",
        "reranker_model",
        "reranker_revision",
        "reranker_device",
        "reranker_max_length",
        "reranker_batch_size",
        "reranker_local_files_only",
        "reranker_use_safetensors",
        "reranker_trust_remote_code",
        "pid",
        "socket_device",
        "socket_inode",
        "error_type",
    }
)
_ERROR_TYPES = frozenset(
    {
        "protocol_error",
        "incompatible_worker",
        "model_unavailable",
        "encoding_failure",
        "scoring_failure",
        "busy_timeout",
        "internal_worker_failure",
    }
)


def _implementation_id() -> str:
    """Bind a resident worker to the exact implementation bytes."""

    try:
        payload = Path(__file__).read_bytes()
    except OSError:
        payload = b"buoy-retrieve-inference-worker-v2"
    return hashlib.sha256(payload).hexdigest()


IMPLEMENTATION_ID = _implementation_id()
PYTHON_VERSION = f"{sys.version_info.major}.{sys.version_info.minor}"


class EmbeddingWorkerError(RuntimeError):
    """A bounded, value-redacted prototype worker failure."""

    def __init__(self, error_type: str) -> None:
        category = error_type if error_type in _ERROR_TYPES else "internal_worker_failure"
        self.error_type = category
        super().__init__(f"local embedding worker failed: {category.replace('_', ' ')}")


class _Unavailable(Exception):
    pass


class _Incompatible(Exception):
    pass


class _ProtocolError(Exception):
    pass


class _TruncatedFrame(_ProtocolError):
    """A peer closed a length-prefixed frame before it was complete."""


class _RerankerUnavailable(Exception):
    """The exact lazy reranker could not be constructed."""


@dataclass(frozen=True)
class WorkerPaths:
    """Fixed private paths for one exact worker identity."""

    buoy_home: Path
    inference_directory: Path
    identity_directory: Path
    socket_path: Path
    ready_path: Path
    start_lock_path: Path
    lifetime_lock_path: Path


@dataclass(frozen=True)
class _EncodeRequest:
    texts: list[str]


@dataclass(frozen=True)
class _ScoreRequest:
    query: str
    passages: list[str]


_Request = _EncodeRequest | _ScoreRequest


def worker_paths(buoy_home: Path | None = None) -> WorkerPaths:
    """Return paths without touching the filesystem.

    The override exists only for isolated tests and the explicit validation
    harness; product code has no path or activation surface for this module.
    """

    root = normalized_absolute(default_buoy_home() if buoy_home is None else buoy_home)
    identity_payload = _canonical_json(
        {
            "schema_version": SCHEMA_VERSION,
            "model": MODEL,
            "revision": REVISION,
            "precision": PRECISION,
            "reranker_model": RERANKER_MODEL,
            "reranker_revision": RERANKER_REVISION,
            "reranker_device": RERANKER_DEVICE,
            "reranker_max_length": RERANKER_MAX_LENGTH,
            "reranker_batch_size": RERANKER_BATCH_SIZE,
        }
    )
    identity = hashlib.sha256(identity_payload).hexdigest()[:16]
    inference = root / "inference"
    leaf = inference / f"v{SCHEMA_VERSION}-{identity}"
    return WorkerPaths(
        buoy_home=root,
        inference_directory=inference,
        identity_directory=leaf,
        socket_path=leaf / "worker.sock",
        ready_path=leaf / "ready.json",
        start_lock_path=leaf / "start.lock",
        lifetime_lock_path=leaf / "lifetime.lock",
    )


def _require_capability() -> None:
    required = ("O_DIRECTORY", "O_NOFOLLOW", "O_CLOEXEC", "geteuid", "fchmod")
    if (
        os.name != "posix"
        or fcntl is None
        or not hasattr(socket, "AF_UNIX")
        or any(not hasattr(os, name) for name in required)
    ):
        raise EmbeddingWorkerError("internal_worker_failure")


def _mode(observed: os.stat_result) -> int:
    return stat.S_IMODE(observed.st_mode)


def _verify_directory_fd(descriptor: int) -> os.stat_result:
    observed = os.fstat(descriptor)
    if (
        not stat.S_ISDIR(observed.st_mode)
        or observed.st_uid != os.geteuid()
        or _mode(observed) != _DIRECTORY_MODE
    ):
        raise EmbeddingWorkerError("internal_worker_failure")
    return observed


def _open_parent_directory(path: Path) -> int:
    """Open the caller-owned parent without imposing Buoy-private modes."""

    try:
        descriptor = os.open(
            os.fspath(path),
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
    except OSError as exc:
        raise EmbeddingWorkerError("internal_worker_failure") from exc
    observed = os.fstat(descriptor)
    if not stat.S_ISDIR(observed.st_mode):
        os.close(descriptor)
        raise EmbeddingWorkerError("internal_worker_failure")
    return descriptor


def _open_or_create_directory(parent_fd: int, name: str) -> int:
    if not name or "/" in name or name in {".", ".."}:
        raise EmbeddingWorkerError("internal_worker_failure")
    try:
        os.mkdir(name, _DIRECTORY_MODE, dir_fd=parent_fd)
    except FileExistsError:
        pass
    except OSError as exc:
        raise EmbeddingWorkerError("internal_worker_failure") from exc
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent_fd,
        )
    except OSError as exc:
        raise EmbeddingWorkerError("internal_worker_failure") from exc
    try:
        _verify_directory_fd(descriptor)
        named = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        opened = os.fstat(descriptor)
        if (named.st_dev, named.st_ino) != (opened.st_dev, opened.st_ino):
            raise EmbeddingWorkerError("internal_worker_failure")
    except Exception:
        os.close(descriptor)
        raise
    return descriptor


def _prepare_identity_directory(paths: WorkerPaths) -> int:
    """Create and verify only the managed boundary from Buoy home downward."""

    _require_capability()
    if len(os.fsencode(paths.socket_path)) > MAX_SOCKET_PATH_BYTES:
        raise EmbeddingWorkerError("internal_worker_failure")
    parent = paths.buoy_home.parent
    parent_fd = _open_parent_directory(parent)
    home_fd: int | None = None
    inference_fd: int | None = None
    identity_fd: int | None = None
    try:
        home_fd = _open_or_create_directory(parent_fd, paths.buoy_home.name)
        inference_fd = _open_or_create_directory(home_fd, "inference")
        identity_fd = _open_or_create_directory(
            inference_fd, paths.identity_directory.name
        )
        return identity_fd
    except Exception:
        if identity_fd is not None:
            os.close(identity_fd)
        raise
    finally:
        if inference_fd is not None:
            os.close(inference_fd)
        if home_fd is not None:
            os.close(home_fd)
        os.close(parent_fd)


def _verify_regular_fd(descriptor: int, *, max_bytes: int = 0) -> os.stat_result:
    observed = os.fstat(descriptor)
    if (
        not stat.S_ISREG(observed.st_mode)
        or observed.st_uid != os.geteuid()
        or observed.st_nlink != 1
        or _mode(observed) != _FILE_MODE
        or observed.st_size > max_bytes
    ):
        raise EmbeddingWorkerError("internal_worker_failure")
    return observed


def _open_lock(directory_fd: int, name: str) -> int:
    flags = os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW
    try:
        descriptor = os.open(
            name, flags | os.O_CREAT | os.O_EXCL, _FILE_MODE, dir_fd=directory_fd
        )
    except FileExistsError:
        try:
            observed = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            if (
                not stat.S_ISREG(observed.st_mode)
                or observed.st_uid != os.geteuid()
                or observed.st_nlink != 1
                or _mode(observed) != _FILE_MODE
                or observed.st_size != 0
            ):
                raise EmbeddingWorkerError("internal_worker_failure")
            descriptor = os.open(name, flags, dir_fd=directory_fd)
        except OSError as exc:
            raise EmbeddingWorkerError("internal_worker_failure") from exc
    except OSError as exc:
        raise EmbeddingWorkerError("internal_worker_failure") from exc
    try:
        opened = _verify_regular_fd(descriptor)
        named = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        if (named.st_dev, named.st_ino) != (opened.st_dev, opened.st_ino):
            raise EmbeddingWorkerError("internal_worker_failure")
    except Exception:
        os.close(descriptor)
        raise
    return descriptor


@contextmanager
def _lock(
    directory_fd: int,
    name: str,
    *,
    timeout_seconds: float,
) -> Iterator[int]:
    descriptor = _open_lock(directory_fd, name)
    assert fcntl is not None
    deadline = time.monotonic() + max(0.0, timeout_seconds)
    try:
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise EmbeddingWorkerError("busy_timeout")
                time.sleep(LOCK_POLL_SECONDS)
        _verify_regular_fd(descriptor)
        yield descriptor
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _reject_duplicate_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise _ProtocolError("duplicate field")
        value[key] = item
    return value


def _decode_json(payload: bytes) -> dict[str, object]:
    try:
        text = payload.decode("utf-8")
        value = json.loads(text, object_pairs_hook=_reject_duplicate_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError, _ProtocolError) as exc:
        raise _ProtocolError("invalid JSON") from exc
    if not isinstance(value, dict):
        raise _ProtocolError("object required")
    return value


def _recv_exact(connection: socket.socket, count: int) -> bytes:
    chunks: list[bytes] = []
    remaining = count
    while remaining:
        chunk = connection.recv(remaining)
        if not chunk:
            raise _TruncatedFrame("truncated frame")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _recv_frame(connection: socket.socket) -> bytes:
    header = _recv_exact(connection, 4)
    (length,) = struct.unpack("!I", header)
    if length == 0 or length > MAX_FRAME_BYTES:
        raise _ProtocolError("invalid frame length")
    return _recv_exact(connection, length)


def _send_frame(connection: socket.socket, value: Mapping[str, object]) -> None:
    payload = _canonical_json(dict(value))
    if not payload or len(payload) > MAX_FRAME_BYTES:
        raise _ProtocolError("invalid frame length")
    connection.sendall(struct.pack("!I", len(payload)) + payload)


def _identity_fields() -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "model": MODEL,
        "revision": REVISION,
        "precision": PRECISION,
        "dimensions": DIMENSIONS,
        "package_version": __version__,
        "python_version": PYTHON_VERSION,
        "implementation_id": IMPLEMENTATION_ID,
        "reranker_model": RERANKER_MODEL,
        "reranker_revision": RERANKER_REVISION,
        "reranker_device": RERANKER_DEVICE,
        "reranker_max_length": RERANKER_MAX_LENGTH,
        "reranker_batch_size": RERANKER_BATCH_SIZE,
        "reranker_local_files_only": RERANKER_LOCAL_FILES_ONLY,
        "reranker_use_safetensors": RERANKER_USE_SAFETENSORS,
        "reranker_trust_remote_code": RERANKER_TRUST_REMOTE_CODE,
    }


def _ready_response() -> dict[str, object]:
    return _identity_fields() | {"outcome": "ready"}


def _validate_ready(value: dict[str, object]) -> None:
    if set(value) != _READY_FIELDS or value != _ready_response():
        raise _Incompatible


def _is_bounded_text(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        return len(value.encode("utf-8")) <= MAX_TEXT_BYTES
    except UnicodeEncodeError:
        return False


def _validate_texts(texts: Sequence[str]) -> list[str]:
    try:
        count = len(texts)
    except TypeError as exc:
        raise EmbeddingWorkerError("protocol_error") from exc
    if isinstance(texts, (str, bytes)) or not 1 <= count <= MAX_TEXTS:
        raise EmbeddingWorkerError("protocol_error")
    validated = list(texts)
    if any(not _is_bounded_text(text) for text in validated):
        raise EmbeddingWorkerError("protocol_error")
    return validated


def _validate_score_input(
    query: str, passages: Sequence[str]
) -> tuple[str, list[str]]:
    try:
        count = len(passages)
    except TypeError as exc:
        raise EmbeddingWorkerError("protocol_error") from exc
    if (
        not _is_bounded_text(query)
        or isinstance(passages, (str, bytes))
        or not 1 <= count <= MAX_SCORE_PASSAGES
    ):
        raise EmbeddingWorkerError("protocol_error")
    validated = list(passages)
    if any(not _is_bounded_text(passage) for passage in validated):
        raise EmbeddingWorkerError("protocol_error")
    request = _score_request_value(query, validated)
    if len(_canonical_json(request)) > MAX_FRAME_BYTES:
        raise EmbeddingWorkerError("protocol_error")
    return query, validated


def _request_value(texts: Sequence[str]) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "operation": "encode",
        "model": MODEL,
        "revision": REVISION,
        "precision": PRECISION,
        "texts": list(texts),
    }


def _score_request_value(
    query: str, passages: Sequence[str]
) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "operation": "score",
        "model": RERANKER_MODEL,
        "revision": RERANKER_REVISION,
        "query": query,
        "passages": list(passages),
    }


def _parse_request(payload: bytes) -> _Request:
    value = _decode_json(payload)
    operation = value.get("operation")
    if operation == "encode":
        if set(value) != _ENCODE_REQUEST_FIELDS:
            raise _ProtocolError("request fields")
        expected = {
            "schema_version": SCHEMA_VERSION,
            "operation": "encode",
            "model": MODEL,
            "revision": REVISION,
            "precision": PRECISION,
        }
        if (
            type(value.get("schema_version")) is not int
            or any(
                value.get(key) != expected_value
                for key, expected_value in expected.items()
            )
        ):
            raise _ProtocolError("request identity")
        texts = value["texts"]
        if not isinstance(texts, list) or not 1 <= len(texts) <= MAX_TEXTS:
            raise _ProtocolError("request texts")
        if any(not _is_bounded_text(text) for text in texts):
            raise _ProtocolError("request text")
        return _EncodeRequest(list(texts))
    if operation == "score":
        if set(value) != _SCORE_REQUEST_FIELDS:
            raise _ProtocolError("request fields")
        expected = {
            "schema_version": SCHEMA_VERSION,
            "operation": "score",
            "model": RERANKER_MODEL,
            "revision": RERANKER_REVISION,
        }
        if (
            type(value.get("schema_version")) is not int
            or any(
                value.get(key) != expected_value
                for key, expected_value in expected.items()
            )
        ):
            raise _ProtocolError("request identity")
        query = value["query"]
        passages = value["passages"]
        if not _is_bounded_text(query):
            raise _ProtocolError("request query")
        if (
            not isinstance(passages, list)
            or not 1 <= len(passages) <= MAX_SCORE_PASSAGES
            or any(not _is_bounded_text(passage) for passage in passages)
        ):
            raise _ProtocolError("request passages")
        return _ScoreRequest(query, list(passages))
    raise _ProtocolError("request operation")


def _validated_vectors(vectors: object, count: int) -> list[list[float]]:
    if not isinstance(vectors, list) or len(vectors) != count:
        raise _ProtocolError("vector count")
    result: list[list[float]] = []
    for vector in vectors:
        if not isinstance(vector, list) or len(vector) != DIMENSIONS:
            raise _ProtocolError("vector dimensions")
        cleaned: list[float] = []
        for item in vector:
            if isinstance(item, bool) or not isinstance(item, (int, float)):
                raise _ProtocolError("vector value")
            number = float(item)
            if not math.isfinite(number):
                raise _ProtocolError("vector value")
            cleaned.append(number)
        norm = math.sqrt(sum(item * item for item in cleaned))
        if not math.isclose(norm, 1.0, rel_tol=1e-4, abs_tol=1e-4):
            raise _ProtocolError("vector normalization")
        result.append(cleaned)
    return result


def _validated_scores(scores: object, count: int) -> list[float]:
    if (
        not isinstance(scores, Sequence)
        or isinstance(scores, (str, bytes, bytearray))
        or len(scores) != count
    ):
        raise _ProtocolError("score count")
    result: list[float] = []
    for value in scores:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise _ProtocolError("score value")
        score = float(value)
        if not math.isfinite(score):
            raise _ProtocolError("score value")
        result.append(score)
    return result


def _raise_error_response(value: dict[str, object]) -> None:
    if set(value) != _ERROR_FIELDS or value.get("schema_version") != SCHEMA_VERSION:
        raise _ProtocolError("error fields")
    error_type = value.get("error_type")
    if not isinstance(error_type, str) or error_type not in _ERROR_TYPES:
        raise _ProtocolError("error category")
    raise EmbeddingWorkerError(error_type)


def _parse_response(payload: bytes, count: int) -> list[list[float]]:
    value = _decode_json(payload)
    if value.get("outcome") == "error":
        _raise_error_response(value)
    if value.get("outcome") != "success" or set(value) != _ENCODE_SUCCESS_FIELDS:
        raise _ProtocolError("response fields")
    if (
        type(value.get("schema_version")) is not int
        or type(value.get("dimensions")) is not int
        or value.get("schema_version") != SCHEMA_VERSION
        or value.get("dimensions") != DIMENSIONS
    ):
        raise _ProtocolError("response identity")
    return _validated_vectors(value.get("vectors"), count)


def _parse_score_response(payload: bytes, count: int) -> list[float]:
    value = _decode_json(payload)
    if value.get("outcome") == "error":
        _raise_error_response(value)
    if value.get("outcome") != "success" or set(value) != _SCORE_SUCCESS_FIELDS:
        raise _ProtocolError("response fields")
    if (
        type(value.get("schema_version")) is not int
        or value.get("schema_version") != SCHEMA_VERSION
        or value.get("model") != RERANKER_MODEL
        or value.get("revision") != RERANKER_REVISION
    ):
        raise _ProtocolError("response identity")
    return _validated_scores(value.get("scores"), count)


def _peer_uid(connection: socket.socket) -> int | None:
    getpeereid = getattr(connection, "getpeereid", None)
    if callable(getpeereid):
        uid, _gid = getpeereid()
        return int(uid)
    peer_credential = getattr(socket, "SO_PEERCRED", None)
    if peer_credential is not None:
        payload = connection.getsockopt(socket.SOL_SOCKET, peer_credential, struct.calcsize("3i"))
        _pid, uid, _gid = struct.unpack("3i", payload)
        return int(uid)
    return None


def _verify_peer(connection: socket.socket) -> None:
    try:
        uid = _peer_uid(connection)
    except OSError as exc:
        raise _ProtocolError("peer identity") from exc
    if uid is not None and uid != os.geteuid():
        raise _ProtocolError("peer identity")


def _verify_socket(path: Path) -> os.stat_result:
    try:
        observed = path.lstat()
    except OSError as exc:
        raise _Unavailable from exc
    if (
        not stat.S_ISSOCK(observed.st_mode)
        or observed.st_uid != os.geteuid()
        or observed.st_nlink != 1
        or _mode(observed) != _SOCKET_MODE
    ):
        raise EmbeddingWorkerError("internal_worker_failure")
    return observed


def _connect_and_encode(
    paths: WorkerPaths,
    texts: Sequence[str],
    *,
    timeout_seconds: float,
) -> list[list[float]]:
    _verify_socket(paths.socket_path)
    try:
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    except OSError as exc:
        raise EmbeddingWorkerError("internal_worker_failure") from exc
    try:
        try:
            connection.settimeout(timeout_seconds)
            connection.connect(os.fspath(paths.socket_path))
            _verify_peer(connection)
        except _ProtocolError as exc:
            raise EmbeddingWorkerError("protocol_error") from exc
        except (socket.timeout, OSError) as exc:
            raise _Unavailable from exc

        # No query has crossed IPC before the exact greeting is validated, so
        # an idle-exit/reset race here is safe for the caller's start/reuse
        # logic to retry. Malformed complete greetings remain incompatible.
        try:
            _validate_ready(_decode_json(_recv_frame(connection)))
        except (socket.timeout, OSError, _TruncatedFrame) as exc:
            raise _Unavailable from exc
        except _ProtocolError as exc:
            raise _Incompatible from exc

        # From the first request byte onward, never retry: the worker may have
        # completed the operation even if its response is lost. Convert every
        # transport/protocol failure to the public bounded error vocabulary.
        try:
            _send_frame(connection, _request_value(texts))
            return _parse_response(_recv_frame(connection), len(texts))
        except EmbeddingWorkerError:
            raise
        except socket.timeout as exc:
            raise EmbeddingWorkerError("busy_timeout") from exc
        except OSError as exc:
            raise EmbeddingWorkerError("internal_worker_failure") from exc
        except _ProtocolError as exc:
            raise EmbeddingWorkerError("protocol_error") from exc
    finally:
        try:
            connection.close()
        except OSError:
            pass


def _connect_and_score(
    paths: WorkerPaths,
    query: str,
    passages: Sequence[str],
    *,
    timeout_seconds: float,
) -> list[float]:
    _verify_socket(paths.socket_path)
    try:
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    except OSError as exc:
        raise EmbeddingWorkerError("internal_worker_failure") from exc
    try:
        try:
            connection.settimeout(timeout_seconds)
            connection.connect(os.fspath(paths.socket_path))
            _verify_peer(connection)
        except _ProtocolError as exc:
            raise EmbeddingWorkerError("protocol_error") from exc
        except (socket.timeout, OSError) as exc:
            raise _Unavailable from exc

        try:
            _validate_ready(_decode_json(_recv_frame(connection)))
        except (socket.timeout, OSError, _TruncatedFrame) as exc:
            raise _Unavailable from exc
        except _ProtocolError as exc:
            raise _Incompatible from exc

        # Local scoring has no durable side effect, but IPC is still never
        # replayed after request transmission because completion is uncertain.
        try:
            _send_frame(connection, _score_request_value(query, passages))
            return _parse_score_response(
                _recv_frame(connection), len(passages)
            )
        except EmbeddingWorkerError:
            raise
        except socket.timeout as exc:
            raise EmbeddingWorkerError("busy_timeout") from exc
        except OSError as exc:
            raise EmbeddingWorkerError("internal_worker_failure") from exc
        except _ProtocolError as exc:
            raise EmbeddingWorkerError("protocol_error") from exc
    finally:
        try:
            connection.close()
        except OSError:
            pass


def _state_value(
    *,
    phase: str,
    pid: int,
    socket_stat: os.stat_result | None = None,
    error_type: str | None = None,
) -> dict[str, object]:
    return _identity_fields() | {
        "phase": phase,
        "pid": pid,
        "socket_device": socket_stat.st_dev if socket_stat is not None else None,
        "socket_inode": socket_stat.st_ino if socket_stat is not None else None,
        "error_type": error_type,
    }


def _write_state(directory_fd: int, value: Mapping[str, object]) -> tuple[int, int]:
    payload = _canonical_json(dict(value))
    if len(payload) > 4096:
        raise EmbeddingWorkerError("internal_worker_failure")
    temporary = "ready.tmp"
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
            _FILE_MODE,
            dir_fd=directory_fd,
        )
    except FileExistsError:
        _safe_unlink_regular(directory_fd, temporary, expected=None)
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
            _FILE_MODE,
            dir_fd=directory_fd,
        )
    try:
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise EmbeddingWorkerError("internal_worker_failure")
            offset += written
        os.fsync(descriptor)
        observed = _verify_regular_fd(descriptor, max_bytes=4096)
    finally:
        os.close(descriptor)
    try:
        os.link(
            temporary,
            "ready.json",
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
            follow_symlinks=False,
        )
    except FileExistsError as exc:
        _safe_unlink_regular(directory_fd, temporary, expected=(observed.st_dev, observed.st_ino))
        raise EmbeddingWorkerError("internal_worker_failure") from exc
    linked = os.stat("ready.json", dir_fd=directory_fd, follow_symlinks=False)
    if (
        not stat.S_ISREG(linked.st_mode)
        or linked.st_nlink != 2
        or (linked.st_dev, linked.st_ino) != (observed.st_dev, observed.st_ino)
    ):
        raise EmbeddingWorkerError("internal_worker_failure")
    os.unlink(temporary, dir_fd=directory_fd)
    os.fsync(directory_fd)
    named = os.stat("ready.json", dir_fd=directory_fd, follow_symlinks=False)
    if (
        named.st_nlink != 1
        or (named.st_dev, named.st_ino) != (observed.st_dev, observed.st_ino)
        or named.st_size != len(payload)
    ):
        raise EmbeddingWorkerError("internal_worker_failure")
    return named.st_dev, named.st_ino


def _read_state(directory_fd: int) -> dict[str, object] | None:
    try:
        observed = os.stat("ready.json", dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    if (
        not stat.S_ISREG(observed.st_mode)
        or observed.st_uid != os.geteuid()
        or observed.st_nlink != 1
        or _mode(observed) != _FILE_MODE
        or observed.st_size > 4096
    ):
        raise EmbeddingWorkerError("internal_worker_failure")
    descriptor = os.open(
        "ready.json", os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=directory_fd
    )
    try:
        opened = _verify_regular_fd(descriptor, max_bytes=4096)
        if (opened.st_dev, opened.st_ino) != (observed.st_dev, observed.st_ino):
            raise EmbeddingWorkerError("internal_worker_failure")
        payload = os.read(descriptor, 4097)
    finally:
        os.close(descriptor)
    value = _decode_json(payload)
    if set(value) != _STATE_FIELDS:
        raise EmbeddingWorkerError("internal_worker_failure")
    return value


def _state_is_compatible(value: Mapping[str, object]) -> bool:
    identity = _identity_fields()
    if not all(value.get(key) == item for key, item in identity.items()):
        return False
    phase = value.get("phase")
    error_type = value.get("error_type")
    pid = value.get("pid")
    device = value.get("socket_device")
    inode = value.get("socket_inode")
    if phase not in {"ready", "error"} or type(pid) is not int or pid <= 0:
        return False
    if phase == "ready":
        return (
            error_type is None
            and type(device) is int
            and device >= 0
            and type(inode) is int
            and inode > 0
        )
    return (
        isinstance(error_type, str)
        and error_type in _ERROR_TYPES
        and device is None
        and inode is None
    )


def _safe_unlink_regular(
    directory_fd: int,
    name: str,
    *,
    expected: tuple[int, int] | None,
) -> None:
    try:
        observed = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    if (
        not stat.S_ISREG(observed.st_mode)
        or observed.st_uid != os.geteuid()
        or observed.st_nlink != 1
        or _mode(observed) != _FILE_MODE
        or (expected is not None and (observed.st_dev, observed.st_ino) != expected)
    ):
        raise EmbeddingWorkerError("internal_worker_failure")
    os.unlink(name, dir_fd=directory_fd)


def _safe_unlink_socket(
    directory_fd: int,
    *,
    expected: tuple[int, int] | None,
) -> None:
    try:
        observed = os.stat("worker.sock", dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    if (
        not stat.S_ISSOCK(observed.st_mode)
        or observed.st_uid != os.geteuid()
        or observed.st_nlink != 1
        or _mode(observed) != _SOCKET_MODE
        or (expected is not None and (observed.st_dev, observed.st_ino) != expected)
    ):
        raise EmbeddingWorkerError("internal_worker_failure")
    os.unlink("worker.sock", dir_fd=directory_fd)


def _recover_state_temporary(directory_fd: int) -> None:
    """Recover the only safe interruption points in no-overwrite publication."""

    try:
        temporary = os.stat("ready.tmp", dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    if (
        not stat.S_ISREG(temporary.st_mode)
        or temporary.st_uid != os.geteuid()
        or _mode(temporary) != _FILE_MODE
        or temporary.st_size > 4096
        or temporary.st_nlink not in {1, 2}
    ):
        raise EmbeddingWorkerError("internal_worker_failure")
    if temporary.st_nlink == 2:
        try:
            ready = os.stat("ready.json", dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError as exc:
            raise EmbeddingWorkerError("internal_worker_failure") from exc
        if (
            not stat.S_ISREG(ready.st_mode)
            or ready.st_uid != os.geteuid()
            or _mode(ready) != _FILE_MODE
            or (ready.st_dev, ready.st_ino) != (temporary.st_dev, temporary.st_ino)
        ):
            raise EmbeddingWorkerError("internal_worker_failure")
    os.unlink("ready.tmp", dir_fd=directory_fd)
    os.fsync(directory_fd)


def _clear_stale_runtime(directory_fd: int) -> None:
    """Remove only validated fixed objects while holding lifetime authority."""

    _recover_state_temporary(directory_fd)
    state = _read_state(directory_fd)
    socket_expected: tuple[int, int] | None = None
    state_expected: tuple[int, int] | None = None
    if state is not None:
        if not _state_is_compatible(state):
            raise EmbeddingWorkerError("incompatible_worker")
        state_stat = os.stat("ready.json", dir_fd=directory_fd, follow_symlinks=False)
        state_expected = (state_stat.st_dev, state_stat.st_ino)
        device = state.get("socket_device")
        inode = state.get("socket_inode")
        if type(device) is int and type(inode) is int:
            socket_expected = (device, inode)
    try:
        socket_stat = os.stat("worker.sock", dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        socket_stat = None
    if socket_stat is not None:
        if socket_expected is not None and (
            socket_stat.st_dev,
            socket_stat.st_ino,
        ) != socket_expected:
            raise EmbeddingWorkerError("internal_worker_failure")
        _safe_unlink_socket(directory_fd, expected=socket_expected)
    _safe_unlink_regular(directory_fd, "ready.json", expected=state_expected)


def _minimal_worker_environment() -> dict[str, str]:
    return {
        "BUOY_TELEMETRY": "off",
        "DO_NOT_TRACK": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "HF_HUB_OFFLINE": "1",
        "OTEL_SDK_DISABLED": "true",
        "PYTHONDONTWRITEBYTECODE": "1",
        "TOKENIZERS_PARALLELISM": "false",
        "TRANSFORMERS_OFFLINE": "1",
    }


def _spawn_worker(paths: WorkerPaths) -> None:
    executable = os.path.abspath(sys.executable)
    if not executable or not os.path.isabs(executable):
        raise EmbeddingWorkerError("internal_worker_failure")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)
            process = subprocess.Popen(
                [
                    executable,
                    "-I",
                    "-X",
                    "utf8",
                    "-m",
                    "buoy_search.retrieval.embedding_worker",
                ],
                cwd=os.fspath(paths.identity_directory),
                env=_minimal_worker_environment(),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                start_new_session=True,
                shell=False,
            )
            del process
    except OSError as exc:
        raise EmbeddingWorkerError("internal_worker_failure") from exc


_T = TypeVar("_T")


def _request_from_worker(
    paths: WorkerPaths,
    request: Callable[[], _T],
    *,
    startup_timeout_seconds: float,
) -> _T:
    directory_fd = _prepare_identity_directory(paths)
    try:
        try:
            return request()
        except _Incompatible as exc:
            raise EmbeddingWorkerError("incompatible_worker") from exc
        except _Unavailable:
            pass

        with _lock(
            directory_fd,
            "start.lock",
            timeout_seconds=startup_timeout_seconds,
        ):
            try:
                return request()
            except _Incompatible as exc:
                raise EmbeddingWorkerError("incompatible_worker") from exc
            except _Unavailable:
                pass

            with _lock(directory_fd, "lifetime.lock", timeout_seconds=0.0):
                _clear_stale_runtime(directory_fd)
            _spawn_worker(paths)
            deadline = time.monotonic() + startup_timeout_seconds
            while True:
                state = _read_state(directory_fd)
                if state is not None:
                    if not _state_is_compatible(state):
                        raise EmbeddingWorkerError("incompatible_worker")
                    if state.get("phase") == "error":
                        category = state.get("error_type")
                        raise EmbeddingWorkerError(
                            category
                            if isinstance(category, str)
                            else "internal_worker_failure"
                        )
                try:
                    return request()
                except _Incompatible as exc:
                    raise EmbeddingWorkerError("incompatible_worker") from exc
                except _Unavailable:
                    if time.monotonic() >= deadline:
                        raise EmbeddingWorkerError("busy_timeout") from None
                    time.sleep(LOCK_POLL_SECONDS)
    except _ProtocolError as exc:
        raise EmbeddingWorkerError("protocol_error") from exc
    finally:
        os.close(directory_fd)


def encode(
    texts: Sequence[str],
    *,
    buoy_home: Path | None = None,
    startup_timeout_seconds: float = STARTUP_TIMEOUT_SECONDS,
    request_timeout_seconds: float = REQUEST_TIMEOUT_SECONDS,
) -> list[list[float]]:
    """Encode texts through the exact private local worker."""

    validated = _validate_texts(texts)
    if startup_timeout_seconds <= 0 or request_timeout_seconds <= 0:
        raise EmbeddingWorkerError("protocol_error")
    paths = worker_paths(buoy_home)
    return _request_from_worker(
        paths,
        lambda: _connect_and_encode(
            paths, validated, timeout_seconds=request_timeout_seconds
        ),
        startup_timeout_seconds=startup_timeout_seconds,
    )


def score(
    query: str,
    passages: Sequence[str],
    *,
    buoy_home: Path | None = None,
    startup_timeout_seconds: float = STARTUP_TIMEOUT_SECONDS,
    request_timeout_seconds: float = REQUEST_TIMEOUT_SECONDS,
) -> list[float]:
    """Score bounded query/passage pairs through the private local worker."""

    validated_query, validated_passages = _validate_score_input(query, passages)
    if startup_timeout_seconds <= 0 or request_timeout_seconds <= 0:
        raise EmbeddingWorkerError("protocol_error")
    paths = worker_paths(buoy_home)
    return _request_from_worker(
        paths,
        lambda: _connect_and_score(
            paths,
            validated_query,
            validated_passages,
            timeout_seconds=request_timeout_seconds,
        ),
        startup_timeout_seconds=startup_timeout_seconds,
    )


class _LocalModel:
    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer

        with suppress_model_progress_bars():
            self._model = SentenceTransformer(
                MODEL,
                revision=REVISION,
                local_files_only=True,
            )

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        values = self._model.encode(
            list(texts),
            batch_size=32,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [
            value.tolist() if hasattr(value, "tolist") else list(value)
            for value in values
        ]


def _publish_error_state(directory_fd: int, error_type: str) -> bool:
    try:
        _write_state(
            directory_fd,
            _state_value(phase="error", pid=os.getpid(), error_type=error_type),
        )
    except Exception:
        return False
    return True


def _bind_server(paths: WorkerPaths, directory_fd: int) -> tuple[socket.socket, os.stat_result]:
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        server.bind(os.fspath(paths.socket_path))
        os.chmod(paths.socket_path, _SOCKET_MODE, follow_symlinks=False)
        observed = _verify_socket(paths.socket_path)
        named = os.stat("worker.sock", dir_fd=directory_fd, follow_symlinks=False)
        if (named.st_dev, named.st_ino) != (observed.st_dev, observed.st_ino):
            raise EmbeddingWorkerError("internal_worker_failure")
        server.listen(MAX_TEXTS)
        return server, observed
    except Exception:
        server.close()
        raise


def _error_response(error_type: str) -> dict[str, object]:
    category = error_type if error_type in _ERROR_TYPES else "internal_worker_failure"
    return {
        "schema_version": SCHEMA_VERSION,
        "outcome": "error",
        "error_type": category,
    }


class _WorkerRuntime:
    """Hold only resident model/runtime objects between serial requests."""

    def __init__(
        self,
        embedder: object,
        reranker_loader: Callable[[], object],
    ) -> None:
        self._embedder = embedder
        self._reranker_loader = reranker_loader
        self._reranker: object | None = None

    def encode(self, texts: Sequence[str]) -> object:
        return self._embedder.encode(texts)  # type: ignore[attr-defined,no-any-return]

    def score(self, query: str, passages: Sequence[str]) -> object:
        if self._reranker is None:
            try:
                self._reranker = self._reranker_loader()
            except Exception as exc:
                raise _RerankerUnavailable from exc
        return self._reranker.score(  # type: ignore[attr-defined,no-any-return]
            query, passages
        )


def _serve_connection(connection: socket.socket, runtime: _WorkerRuntime) -> bool:
    """Serve one connection and report whether a valid request was accepted."""

    accepted = False
    try:
        connection.settimeout(REQUEST_TIMEOUT_SECONDS)
        _verify_peer(connection)
        _send_frame(connection, _ready_response())
        request = _parse_request(_recv_frame(connection))
        accepted = True
        if isinstance(request, _EncodeRequest):
            try:
                values = runtime.encode(request.texts)
                vectors = _validated_vectors(values, len(request.texts))
            except Exception:
                _send_frame(connection, _error_response("encoding_failure"))
                return accepted
            _send_frame(
                connection,
                {
                    "schema_version": SCHEMA_VERSION,
                    "outcome": "success",
                    "dimensions": DIMENSIONS,
                    "vectors": vectors,
                },
            )
            return accepted

        try:
            values = runtime.score(request.query, request.passages)
            scores = _validated_scores(values, len(request.passages))
        except _RerankerUnavailable:
            _send_frame(connection, _error_response("model_unavailable"))
            return accepted
        except Exception:
            _send_frame(connection, _error_response("scoring_failure"))
            return accepted
        _send_frame(
            connection,
            {
                "schema_version": SCHEMA_VERSION,
                "outcome": "success",
                "model": RERANKER_MODEL,
                "revision": RERANKER_REVISION,
                "scores": scores,
            },
        )
    except (_ProtocolError, socket.timeout, OSError):
        try:
            _send_frame(connection, _error_response("protocol_error"))
        except Exception:
            pass
    return accepted


def run_worker(
    paths: WorkerPaths | None = None,
    *,
    model_loader: Callable[[], object] = _LocalModel,
    reranker_loader: Callable[[], object] = load_cross_encoder_reranker,
    idle_seconds: float = IDLE_EXIT_SECONDS,
    monotonic: Callable[[], float] = time.monotonic,
) -> int:
    """Elect and run one serial worker. An extra worker exits successfully."""

    if idle_seconds < 0:
        return 2
    selected = paths or worker_paths(Path.cwd().parent.parent)
    directory_fd = _prepare_identity_directory(selected)
    server: socket.socket | None = None
    socket_identity: tuple[int, int] | None = None
    state_identity: tuple[int, int] | None = None
    retain_error_state = False
    lifetime = _lock(directory_fd, "lifetime.lock", timeout_seconds=0.0)
    lifetime_held = False
    try:
        try:
            lifetime.__enter__()
            lifetime_held = True
        except EmbeddingWorkerError as exc:
            return 0 if exc.error_type == "busy_timeout" else 1

        try:
            _clear_stale_runtime(directory_fd)
            try:
                model = model_loader()
            except Exception:
                retain_error_state = _publish_error_state(
                    directory_fd, "model_unavailable"
                )
                return 1
            runtime = _WorkerRuntime(model, reranker_loader)
            server, socket_stat = _bind_server(selected, directory_fd)
            socket_identity = (socket_stat.st_dev, socket_stat.st_ino)
            state_identity = _write_state(
                directory_fd,
                _state_value(
                    phase="ready",
                    pid=os.getpid(),
                    socket_stat=socket_stat,
                ),
            )
            last_accepted = monotonic()
            while True:
                remaining = idle_seconds - (monotonic() - last_accepted)
                if remaining <= 0:
                    return 0
                server.settimeout(min(remaining, 1.0))
                try:
                    connection, _address = server.accept()
                except socket.timeout:
                    continue
                except OSError:
                    return 1
                with connection:
                    accepted = _serve_connection(connection, runtime)
                if accepted:
                    last_accepted = monotonic()
        except EmbeddingWorkerError:
            return 1
        except (OSError, _ProtocolError):
            retain_error_state = _publish_error_state(
                directory_fd, "internal_worker_failure"
            )
            return 1
        finally:
            # Lifetime authority covers listener close and inode-bound cleanup.
            # A new starter cannot inspect/remove/rebind these names while the
            # old server can still accept or while its ready state is present.
            if server is not None:
                try:
                    server.close()
                except OSError:
                    pass
            try:
                if socket_identity is not None:
                    _safe_unlink_socket(directory_fd, expected=socket_identity)
                if state_identity is not None and not retain_error_state:
                    _safe_unlink_regular(
                        directory_fd, "ready.json", expected=state_identity
                    )
            except EmbeddingWorkerError:
                pass
            finally:
                if lifetime_held:
                    lifetime_held = False
                    lifetime.__exit__(None, None, None)
    finally:
        if lifetime_held:  # defensive for exceptions outside the bounded body.
            lifetime.__exit__(None, None, None)
        os.close(directory_fd)


def read_worker_state(*, buoy_home: Path | None = None) -> dict[str, object] | None:
    """Return validated content-free state for the explicit validation harness."""

    paths = worker_paths(buoy_home)
    try:
        directory_fd = _prepare_identity_directory(paths)
    except EmbeddingWorkerError:
        return None
    try:
        value = _read_state(directory_fd)
        return dict(value) if value is not None else None
    finally:
        os.close(directory_fd)


def main(argv: list[str] | None = None) -> int:
    """Run only from the exact worker identity directory."""

    os.umask(0o077)
    arguments = sys.argv[1:] if argv is None else argv
    if arguments:
        return 2
    cwd = normalized_absolute(Path.cwd())
    if cwd.name != worker_paths(cwd.parent.parent).identity_directory.name:
        return 2
    return run_worker(worker_paths(cwd.parent.parent))


if __name__ == "__main__":  # pragma: no cover - subprocess entry point.
    raise SystemExit(main())
