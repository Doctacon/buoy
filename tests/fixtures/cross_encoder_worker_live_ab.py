"""One-shot privacy-bounded live A/B for schema-v2 inference residency.

Provider-free harness validation is always available:

    uv run python tests/fixtures/cross_encoder_worker_live_ab.py --self-test

The live entry point is retired immediately after the authorized campaign. It
never prints provider content, credentials, paths, process identifiers, or raw
errors; only the bounded redacted campaign result crosses stdout.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
from typing import Mapping, Sequence

from buoy_search import __version__
from buoy_search.retrieval import embedding_worker as worker

QUERY = "How is approximate vector recall evaluated?"
LIVE_AUTHORITY_CONSUMED = True
COMMAND_TIMEOUT_SECONDS = 240
COLD_WAIT_SECONDS = 360.0
IDLE_WAIT_SECONDS = 360.0
COMMANDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("baseline", ("--no-embedding-worker",)),
    ("cold_worker", ()),
    ("warm_worker", ()),
)

_REQUIRED_CREDENTIAL_NAME = "TURBOPUFFER_API_KEY"
_UNRELATED_CREDENTIAL_NAMES = frozenset(
    {
        "ANTHROPIC_API_KEY",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AZURE_CLIENT_SECRET",
        "GITHUB_TOKEN",
        "GOOGLE_API_KEY",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "HF_TOKEN",
        "HUGGING_FACE_HUB_TOKEN",
        "OPENAI_API_KEY",
    }
)
_CONTROL_ENVIRONMENT = {
    "BUOY_TELEMETRY": "off",
    "DO_NOT_TRACK": "1",
    "HF_HUB_DISABLE_TELEMETRY": "1",
    "HF_HUB_OFFLINE": "1",
    "OTEL_SDK_DISABLED": "true",
    "PYTHONDONTWRITEBYTECODE": "1",
    "TOKENIZERS_PARALLELISM": "false",
    "TRANSFORMERS_OFFLINE": "1",
}
_PARITY_FIELDS = (
    "exit_code",
    "stdout_bytes",
    "stderr_bytes",
    "stdout_sha256",
    "stderr_sha256",
    "payload_sha256",
    "shape_sha256",
    "route_sha256",
    "hit_count",
    "namespace_count",
    "catalog_read_operation_count",
    "namespace_result_count",
)


class _CampaignStop(RuntimeError):
    """A bounded stop category with no raw provider/runtime detail."""

    def __init__(self, category: str) -> None:
        self.category = category
        super().__init__(category)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _manifest(root: Path, *, exclude_bytecode: bool = False) -> dict[str, object]:
    digest = hashlib.sha256()
    count = 0
    if not root.exists():
        return {"sha256": "absent", "entry_count": 0}
    for path in sorted(root.rglob("*")):
        if exclude_bytecode and (
            "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}
        ):
            continue
        observed = path.lstat()
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(str(observed.st_mode).encode("ascii"))
        digest.update(str(observed.st_size).encode("ascii"))
        if path.is_symlink():
            digest.update(os.readlink(path).encode("utf-8"))
        elif path.is_file():
            digest.update(hashlib.sha256(path.read_bytes()).digest())
        count += 1
    return {"sha256": digest.hexdigest(), "entry_count": count}


def _files_manifest(paths: Sequence[Path]) -> dict[str, object]:
    digest = hashlib.sha256()
    count = 0
    for index, path in enumerate(paths):
        payload = path.read_bytes()
        digest.update(str(index).encode("ascii"))
        digest.update(str(len(payload)).encode("ascii"))
        digest.update(hashlib.sha256(payload).digest())
        count += 1
    return {"sha256": digest.hexdigest(), "entry_count": count}


def _changed_path_manifest(repository: Path) -> dict[str, object]:
    completed = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=repository,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=30,
    )
    if completed.returncode != 0:
        raise _CampaignStop("changed_path_manifest_failure")
    payload = completed.stdout
    return {
        "sha256": hashlib.sha256(payload).hexdigest(),
        "entry_count": len([part for part in payload.split(b"\0") if part]),
    }


def _runtime_identity() -> dict[str, object]:
    value = {
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "implementation": platform.python_implementation(),
        "platform": platform.system().lower(),
        "machine": platform.machine().lower(),
        "package_version": __version__,
        "worker_schema": worker.SCHEMA_VERSION,
        "worker_implementation_sha256": worker.IMPLEMENTATION_ID,
        "embedding_model": worker.MODEL,
        "embedding_revision": worker.REVISION,
        "embedding_precision": worker.PRECISION,
        "embedding_dimensions": worker.DIMENSIONS,
        "reranker_model": worker.RERANKER_MODEL,
        "reranker_revision": worker.RERANKER_REVISION,
        "reranker_device": worker.RERANKER_DEVICE,
        "reranker_max_length": worker.RERANKER_MAX_LENGTH,
        "reranker_batch_size": worker.RERANKER_BATCH_SIZE,
    }
    return {"sha256": _digest(value), **value}


def _cache_hub() -> Path:
    configured = os.environ.get("HF_HUB_CACHE")
    return (
        Path(configured)
        if configured
        else Path.home() / ".cache" / "huggingface" / "hub"
    )


def _cache_identity(
    root: Path,
    *,
    revision: str,
) -> dict[str, object]:
    snapshot = root / "snapshots" / revision
    if not snapshot.is_dir():
        raise _CampaignStop("model_cache_incomplete")
    files = [path for path in snapshot.rglob("*") if path.is_file()]
    if not files:
        raise _CampaignStop("model_cache_incomplete")
    for path in files:
        try:
            with path.open("rb") as handle:
                handle.read(1)
        except OSError as exc:
            raise _CampaignStop("model_cache_unreadable") from exc
    return _manifest(root)


def _shape(value: object) -> object:
    if isinstance(value, dict):
        return {key: _shape(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [_shape(item) for item in value]
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    return "string"


def _route_identity(payload: Mapping[str, object]) -> object:
    routing = payload.get("routing")
    if not isinstance(routing, dict):
        return None
    selected = routing.get("selected_cards")
    if not isinstance(selected, list):
        return None
    return [
        card.get("namespace")
        for card in selected
        if isinstance(card, dict) and isinstance(card.get("namespace"), str)
    ]


def _provider_read_counts(payload: Mapping[str, object]) -> tuple[int, int]:
    catalog_operations = 0
    routing = payload.get("routing")
    if isinstance(routing, dict):
        metrics = routing.get("read_metrics")
        if isinstance(metrics, dict):
            for key in (
                "namespace_list_pages",
                "metadata_requests",
                "card_query_pages",
            ):
                value = metrics.get(key)
                if type(value) is int and value >= 0:
                    catalog_operations += value
    result = payload.get("result")
    container = result if isinstance(result, dict) else payload
    namespace_results = container.get("namespace_results")
    namespace_count = len(namespace_results) if isinstance(namespace_results, list) else 0
    return catalog_operations, namespace_count


def _payload_counts(payload: Mapping[str, object]) -> tuple[int, int]:
    result = payload.get("result")
    container = result if isinstance(result, dict) else payload
    hits = container.get("hits")
    namespaces = container.get("namespaces")
    return (
        len(hits) if isinstance(hits, list) else 0,
        len(namespaces) if isinstance(namespaces, list) else 0,
    )


def _private_file(path: Path):  # noqa: ANN202 - binary context helper.
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
        0o600,
    )
    return os.fdopen(descriptor, "wb")


def _run_and_reduce(
    role: str,
    command: Sequence[str],
    *,
    root: Path,
    timeout_seconds: float,
) -> dict[str, object]:
    stdout_path = root / f"{role}.stdout"
    stderr_path = root / f"{role}.stderr"
    timed_out = False
    return_code = -1
    started = time.monotonic_ns()
    try:
        with _private_file(stdout_path) as stdout, _private_file(stderr_path) as stderr:
            try:
                completed = subprocess.run(
                    list(command),
                    stdin=subprocess.DEVNULL,
                    stdout=stdout,
                    stderr=stderr,
                    check=False,
                    timeout=timeout_seconds,
                )
                return_code = completed.returncode
            except subprocess.TimeoutExpired:
                timed_out = True
        wall_ms = (time.monotonic_ns() - started) / 1_000_000
        stdout_bytes = stdout_path.read_bytes()
        stderr_bytes = stderr_path.read_bytes()
        failure_category: str | None = None
        payload: dict[str, object] = {}
        if timed_out:
            failure_category = "timeout"
        elif return_code != 0:
            failure_category = "nonzero_exit"
        elif stderr_bytes:
            failure_category = "unexpected_stderr"
        else:
            try:
                decoded = json.loads(stdout_bytes)
            except (UnicodeDecodeError, json.JSONDecodeError):
                failure_category = "malformed_output"
            else:
                if isinstance(decoded, dict):
                    payload = decoded
                else:
                    failure_category = "malformed_output"
                del decoded
        route = _route_identity(payload)
        hit_count, namespace_count = _payload_counts(payload)
        catalog_count, namespace_result_count = _provider_read_counts(payload)
        retained = {
            "role": role,
            "exit_code": return_code,
            "wall_ms": wall_ms,
            "stdout_bytes": len(stdout_bytes),
            "stderr_bytes": len(stderr_bytes),
            "stdout_sha256": hashlib.sha256(stdout_bytes).hexdigest(),
            "stderr_sha256": hashlib.sha256(stderr_bytes).hexdigest(),
            "payload_sha256": _digest(payload),
            "shape_sha256": _digest(_shape(payload)),
            "route_sha256": _digest(route),
            "hit_count": hit_count,
            "namespace_count": namespace_count,
            "catalog_read_operation_count": catalog_count,
            "namespace_result_count": namespace_result_count,
            "failure_category": failure_category,
        }
        del payload, route, stdout_bytes, stderr_bytes
        return retained
    finally:
        stdout_path.unlink(missing_ok=True)
        stderr_path.unlink(missing_ok=True)
        if stdout_path.exists() or stderr_path.exists():
            raise _CampaignStop("raw_output_cleanup_failure")


def _live_command(extra: Sequence[str]) -> list[str]:
    return [
        sys.executable,
        "-I",
        "-m",
        "buoy_search",
        "retrieve",
        QUERY,
        "--json",
        *extra,
    ]


def _matching_worker_pids() -> set[int]:
    completed = subprocess.run(
        ["ps", "-axo", "pid=,command="],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=10,
        text=True,
    )
    if completed.returncode != 0:
        raise _CampaignStop("worker_process_inspection_failure")
    result: set[int] = set()
    marker = "-m buoy_search.retrieval.embedding_worker"
    for line in completed.stdout.splitlines():
        if marker not in line:
            continue
        fields = line.strip().split(None, 1)
        if fields and fields[0].isdigit():
            result.add(int(fields[0]))
    return result


def _worker_absent() -> bool:
    paths = worker.worker_paths()
    return (
        not paths.socket_path.exists()
        and not paths.ready_path.exists()
        and not _matching_worker_pids()
    )


def _wait_for_worker_absence(timeout_seconds: float) -> tuple[bool, float]:
    started = time.monotonic_ns()
    deadline = time.monotonic() + timeout_seconds
    while not _worker_absent():
        if time.monotonic() >= deadline:
            return False, (time.monotonic_ns() - started) / 1_000_000
        time.sleep(0.2)
    return True, (time.monotonic_ns() - started) / 1_000_000


def _worker_state() -> tuple[dict[str, object], int]:
    state = worker.read_worker_state()
    if state is None or state.get("phase") != "ready":
        raise _CampaignStop("worker_state_unavailable")
    if any(state.get(key) != value for key, value in worker._identity_fields().items()):
        raise _CampaignStop("worker_identity_mismatch")
    pid = state.get("pid")
    if type(pid) is not int or pid not in _matching_worker_pids():
        raise _CampaignStop("worker_identity_mismatch")
    return state, pid


def _rss_bytes(pid: int) -> int | None:
    completed = subprocess.run(
        ["ps", "-o", "rss=", "-p", str(pid)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=5,
        text=True,
    )
    value = completed.stdout.strip()
    return int(value) * 1024 if completed.returncode == 0 and value.isdigit() else None


def _parity(runs: Sequence[Mapping[str, object]]) -> dict[str, bool]:
    return {
        f"{field}_equal": len({run.get(field) for run in runs}) == 1
        for field in _PARITY_FIELDS
    }


def _sanitize_live_environment() -> None:
    for name in _UNRELATED_CREDENTIAL_NAMES:
        if name in os.environ:
            del os.environ[name]
    if "PYTHONPATH" in os.environ:
        del os.environ["PYTHONPATH"]
    for name, value in _CONTROL_ENVIRONMENT.items():
        os.environ[name] = value


def _provider_free_self_test() -> dict[str, object]:
    secret = "provider-derived-self-test-sentinel"
    payload = {
        "routing": {
            "selected_cards": [{"namespace": secret}],
            "read_metrics": {
                "namespace_list_pages": 1,
                "metadata_requests": 2,
                "card_query_pages": 1,
            },
        },
        "result": {
            "hits": [{"content": secret}],
            "namespaces": [secret],
            "namespace_results": [{"namespace": secret}],
        },
    }
    script = (
        "import json; print(json.dumps(" + repr(payload) + ", sort_keys=True))"
    )
    with tempfile.TemporaryDirectory(prefix="buoy-worker-ab-selftest-") as value:
        root = Path(value)
        root.chmod(0o700)
        retained = _run_and_reduce(
            "synthetic_success",
            [sys.executable, "-I", "-c", script],
            root=root,
            timeout_seconds=10,
        )
        malformed = _run_and_reduce(
            "synthetic_malformed",
            [sys.executable, "-I", "-c", "print('not-json')"],
            root=root,
            timeout_seconds=10,
        )
        failed = _run_and_reduce(
            "synthetic_failure",
            [sys.executable, "-I", "-c", "raise SystemExit(7)"],
            root=root,
            timeout_seconds=10,
        )
        redacted = secret not in json.dumps(retained, sort_keys=True)
        files_absent = not any(root.iterdir())
    order = [role for role, _extra in COMMANDS]
    return {
        "passed": bool(
            retained["failure_category"] is None
            and retained["hit_count"] == 1
            and retained["namespace_count"] == 1
            and retained["catalog_read_operation_count"] == 4
            and retained["namespace_result_count"] == 1
            and malformed["failure_category"] == "malformed_output"
            and failed["failure_category"] == "nonzero_exit"
            and redacted
            and files_absent
            and order == ["baseline", "cold_worker", "warm_worker"]
            and len(COMMANDS) == 3
        ),
        "redaction_passed": redacted,
        "raw_cleanup_passed": files_absent,
        "malformed_stop_category_passed": (
            malformed["failure_category"] == "malformed_output"
        ),
        "failure_stop_category_passed": (
            failed["failure_category"] == "nonzero_exit"
        ),
        "fixed_order_passed": order == ["baseline", "cold_worker", "warm_worker"],
        "exact_command_count": len(COMMANDS),
    }


def _preflight(repository: Path) -> tuple[dict[str, object], dict[str, object]]:
    if _REQUIRED_CREDENTIAL_NAME not in os.environ:
        raise _CampaignStop("credential_name_absent")
    self_test = _provider_free_self_test()
    if self_test.get("passed") is not True:
        raise _CampaignStop("provider_free_self_test_failure")
    absent, _wait_ms = _wait_for_worker_absence(COLD_WAIT_SECONDS)
    if not absent:
        raise _CampaignStop("worker_not_cold")
    staged = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=repository,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=30,
    )
    if staged.returncode != 0:
        raise _CampaignStop("staged_files_present")
    cache_hub = _cache_hub()
    identity = {
        "source": _manifest(repository / "src" / "buoy_search", exclude_bytecode=True),
        "changed_paths": _changed_path_manifest(repository),
        "lock": _files_manifest([repository / "pyproject.toml", repository / "uv.lock"]),
        "runtime": _runtime_identity(),
        "embedding_cache": _cache_identity(
            cache_hub / "models--BAAI--bge-small-en-v1.5",
            revision=worker.REVISION,
        ),
        "reranker_cache": _cache_identity(
            cache_hub / "models--cross-encoder--ms-marco-MiniLM-L-6-v2",
            revision=worker.RERANKER_REVISION,
        ),
        "telemetry_store": _manifest(worker.worker_paths().buoy_home / "telemetry"),
    }
    return identity, self_test


def _identity_after(repository: Path) -> dict[str, object]:
    cache_hub = _cache_hub()
    return {
        "source": _manifest(repository / "src" / "buoy_search", exclude_bytecode=True),
        "changed_paths": _changed_path_manifest(repository),
        "lock": _files_manifest([repository / "pyproject.toml", repository / "uv.lock"]),
        "runtime": _runtime_identity(),
        "embedding_cache": _cache_identity(
            cache_hub / "models--BAAI--bge-small-en-v1.5",
            revision=worker.REVISION,
        ),
        "reranker_cache": _cache_identity(
            cache_hub / "models--cross-encoder--ms-marco-MiniLM-L-6-v2",
            revision=worker.RERANKER_REVISION,
        ),
        "telemetry_store": _manifest(worker.worker_paths().buoy_home / "telemetry"),
    }


def _execute_live() -> tuple[dict[str, object], int]:
    if LIVE_AUTHORITY_CONSUMED:
        raise _CampaignStop("live_authority_consumed")
    repository = Path(__file__).resolve().parents[2]
    identity_before, self_test = _preflight(repository)
    _sanitize_live_environment()
    ledger = [
        {"ordinal": index, "role": role, "status": "not_started"}
        for index, (role, _extra) in enumerate(COMMANDS, start=1)
    ]
    runs: list[dict[str, object]] = []
    stop_category: str | None = None
    worker_pid: int | None = None
    worker_identity_match = False
    worker_reused = False
    worker_rss: int | None = None
    cleanup_complete = True
    cleanup_wait_ms = 0.0
    external_deleted = False
    temporary_path: Path | None = None
    try:
        with tempfile.TemporaryDirectory(
            prefix="buoy-cross-encoder-worker-ab-", dir=Path.home()
        ) as value:
            root = Path(value)
            temporary_path = root
            root.chmod(0o700)
            for index, (role, extra) in enumerate(COMMANDS):
                ledger[index]["status"] = "started"
                result = _run_and_reduce(
                    role,
                    _live_command(extra),
                    root=root,
                    timeout_seconds=COMMAND_TIMEOUT_SECONDS,
                )
                runs.append(result)
                ledger[index]["status"] = (
                    "completed" if result["failure_category"] is None else "failed"
                )
                if result["failure_category"] is not None:
                    stop_category = str(result["failure_category"])
                    break
                if role == "baseline":
                    if not _worker_absent():
                        stop_category = "baseline_worker_activation"
                        break
                else:
                    _state, observed_pid = _worker_state()
                    worker_identity_match = True
                    if worker_pid is None:
                        worker_pid = observed_pid
                    elif worker_pid != observed_pid:
                        stop_category = "worker_reuse_mismatch"
                        break
                    else:
                        worker_reused = True
                    worker_rss = _rss_bytes(observed_pid)
                if len(runs) > 1 and not all(_parity(runs).values()):
                    stop_category = "within_campaign_parity_mismatch"
                    break
            if worker_pid is not None:
                cleanup_complete, cleanup_wait_ms = _wait_for_worker_absence(
                    IDLE_WAIT_SECONDS
                )
                if not cleanup_complete and stop_category is None:
                    stop_category = "worker_idle_cleanup_failure"
            if any(root.iterdir()) and stop_category is None:
                stop_category = "raw_output_cleanup_failure"
        external_deleted = temporary_path is not None and not temporary_path.exists()
    finally:
        # PID is transient campaign state and must not cross the retained result.
        worker_pid = None

    identity_after = _identity_after(repository)
    identity_equal = {
        f"{key}_unchanged": identity_before[key] == identity_after[key]
        for key in identity_before
    }
    if not all(identity_equal.values()) and stop_category is None:
        stop_category = "identity_drift"
    if not external_deleted and stop_category is None:
        stop_category = "external_cleanup_failure"
    if not _worker_absent() and stop_category is None:
        stop_category = "surviving_worker"

    started_count = sum(item["status"] != "not_started" for item in ledger)
    completed_count = sum(item["status"] == "completed" for item in ledger)
    parity = _parity(runs) if len(runs) > 1 else {}
    success = bool(
        stop_category is None
        and started_count == 3
        and completed_count == 3
        and len(runs) == 3
        and all(parity.values())
        and worker_identity_match
        and worker_reused
        and cleanup_complete
        and external_deleted
        and all(identity_equal.values())
    )
    result = {
        "schema_version": 1,
        "campaign_success": success,
        "live_authority_consumed": started_count > 0,
        "live_operation_count": started_count,
        "completed_operation_count": completed_count,
        "ledger": ledger,
        "runs": runs,
        "parity": parity,
        "stop_category": stop_category,
        "worker_identity_matched": worker_identity_match,
        "worker_reused": worker_reused,
        "worker_rss_bytes": worker_rss,
        "worker_idle_cleanup_complete": cleanup_complete,
        "worker_cleanup_wait_ms": cleanup_wait_ms,
        "external_artifacts_deleted": external_deleted,
        "identity_before": identity_before,
        "identity_equal": identity_equal,
        "provider_credential_name_present": True,
        "provider_write_operations": 0,
        "telemetry_enabled": False,
        "model_network_enabled": False,
        "raw_output_retained": False,
        "decoded_provider_objects_retained": False,
        "provider_free_self_test": self_test,
        "query_sha256": hashlib.sha256(QUERY.encode("utf-8")).hexdigest(),
    }
    return result, 0 if success else 1


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments == ["--self-test"]:
        result = _provider_free_self_test()
        print(json.dumps(result, allow_nan=False, indent=2, sort_keys=True))
        return 0 if result.get("passed") is True else 1
    if arguments != ["--execute-live"]:
        raise RuntimeError("choose exactly --self-test or --execute-live")
    if LIVE_AUTHORITY_CONSUMED:
        raise RuntimeError("cross-encoder worker live A/B authority is consumed")
    try:
        result, return_code = _execute_live()
    except _CampaignStop as exc:
        result = {
            "schema_version": 1,
            "campaign_success": False,
            "live_authority_consumed": False,
            "live_operation_count": 0,
            "completed_operation_count": 0,
            "ledger": [
                {"ordinal": index, "role": role, "status": "not_started"}
                for index, (role, _extra) in enumerate(COMMANDS, start=1)
            ],
            "stop_category": exc.category,
            "raw_output_retained": False,
            "decoded_provider_objects_retained": False,
        }
        return_code = 1
    print(json.dumps(result, allow_nan=False, indent=2, sort_keys=True))
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
