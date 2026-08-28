"""Retired historical harness for the completed retrieve-worker live A/B.

The former experimental flag no longer exists and no additional live command is
authorized. The executed campaign logic remains discoverable for its retained
evidence, but ``main`` fails before credentials or subprocess work.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from buoy_search.retrieval import embedding_worker

QUERY = "How is approximate vector recall evaluated?"
HISTORICAL_ONLY = True
COMMANDS = (
    ("baseline", ()),
    ("cold_worker", ("--experimental-embedding-worker",)),
    ("warm_worker", ("--experimental-embedding-worker",)),
)


def _digest(value: object) -> str:
    payload = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _manifest(root: Path, *, exclude_bytecode: bool = False) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        return "absent"
    for path in sorted(root.rglob("*")):
        if exclude_bytecode and (
            "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}
        ):
            continue
        observed = path.lstat()
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(str(observed.st_mode).encode())
        digest.update(str(observed.st_size).encode())
        if path.is_symlink():
            digest.update(os.readlink(path).encode())
        elif path.is_file():
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


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


def _route_identity(payload: dict[str, object]) -> object:
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


def _hit_count(payload: dict[str, object]) -> int:
    hits = payload.get("hits")
    return len(hits) if isinstance(hits, list) else 0


def _namespace_count(payload: dict[str, object]) -> int:
    namespaces = payload.get("namespaces")
    return len(namespaces) if isinstance(namespaces, list) else 0


def _private_file(path: Path):  # noqa: ANN202 - binary file context helper.
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    return os.fdopen(descriptor, "wb")


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


def _run_one(
    name: str,
    extra: tuple[str, ...],
    *,
    root: Path,
    environment: dict[str, str],
) -> dict[str, object]:
    stdout_path = root / f"{name}.stdout"
    stderr_path = root / f"{name}.stderr"
    command = [
        sys.executable,
        "-I",
        "-m",
        "buoy_search",
        "retrieve",
        QUERY,
        "--json",
        *extra,
    ]
    started = time.monotonic_ns()
    with _private_file(stdout_path) as stdout, _private_file(stderr_path) as stderr:
        completed = subprocess.run(
            command,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            check=False,
            timeout=240,
        )
    wall_ms = (time.monotonic_ns() - started) / 1_000_000
    stdout_bytes = stdout_path.read_bytes()
    stderr_bytes = stderr_path.read_bytes()
    try:
        decoded = json.loads(stdout_bytes) if completed.returncode == 0 else {}
        payload = decoded if isinstance(decoded, dict) else {}
        route = _route_identity(payload)
        retained = {
            "exit_code": completed.returncode,
            "wall_ms": wall_ms,
            "stdout_bytes": len(stdout_bytes),
            "stderr_bytes": len(stderr_bytes),
            "stdout_sha256": hashlib.sha256(stdout_bytes).hexdigest(),
            "stderr_sha256": hashlib.sha256(stderr_bytes).hexdigest(),
            "payload_sha256": _digest(payload),
            "shape_sha256": _digest(_shape(payload)),
            "route_sha256": _digest(route),
            "hit_count": _hit_count(payload),
            "namespace_count": _namespace_count(payload),
        }
        return retained
    finally:
        stdout_path.unlink(missing_ok=True)
        stderr_path.unlink(missing_ok=True)


def main() -> int:
    if HISTORICAL_ONLY:
        raise RuntimeError(
            "historical embedding-worker A/B is retired; zero live commands authorized"
        )
    if "TURBOPUFFER_API_KEY" not in os.environ:
        raise RuntimeError("live credential name is absent; zero commands authorized")
    paths = embedding_worker.worker_paths()
    if paths.socket_path.exists() or paths.ready_path.exists():
        raise RuntimeError("compatible worker is not cold; zero commands authorized")

    script = Path(__file__).resolve()
    repository = script.parents[2]
    source_root = repository / "src" / "buoy_search"
    cache_hub = Path(
        os.environ.get(
            "HF_HUB_CACHE",
            Path.home() / ".cache" / "huggingface" / "hub",
        )
    )
    cache_root = cache_hub / "models--BAAI--bge-small-en-v1.5"
    source_before = _manifest(source_root, exclude_bytecode=True)
    cache_before = _manifest(cache_root)

    environment = dict(os.environ)
    environment.update(
        {
            "BUOY_TELEMETRY": "off",
            "DO_NOT_TRACK": "1",
            "HF_HUB_DISABLE_TELEMETRY": "1",
            "HF_HUB_OFFLINE": "1",
            "OTEL_SDK_DISABLED": "true",
            "PYTHONDONTWRITEBYTECODE": "1",
            "TOKENIZERS_PARALLELISM": "false",
            "TRANSFORMERS_OFFLINE": "1",
        }
    )

    retained: dict[str, dict[str, object]] = {}
    worker_pid: int | None = None
    worker_reused = False
    worker_rss: int | None = None
    with tempfile.TemporaryDirectory(prefix="buoy-retrieve-worker-ab-", dir=Path.home()) as value:
        root = Path(value)
        root.chmod(0o700)
        for name, extra in COMMANDS:
            retained[name] = _run_one(
                name,
                extra,
                root=root,
                environment=environment,
            )
            if name == "baseline":
                if paths.socket_path.exists() or paths.ready_path.exists():
                    raise RuntimeError("baseline activated worker; campaign stopped after one command")
            else:
                state = embedding_worker.read_worker_state()
                if state is None or state.get("phase") != "ready":
                    raise RuntimeError("worker state unavailable after authorized command")
                observed_pid = state.get("pid")
                if type(observed_pid) is not int:
                    raise RuntimeError("worker identity unavailable")
                if worker_pid is None:
                    worker_pid = observed_pid
                else:
                    worker_reused = worker_pid == observed_pid
                worker_rss = _rss_bytes(observed_pid)

    parity = {
        "exit_codes_equal": len(
            {retained[name]["exit_code"] for name, _extra in COMMANDS}
        )
        == 1,
        "hit_counts_equal": len(
            {retained[name]["hit_count"] for name, _extra in COMMANDS}
        )
        == 1,
        "namespace_counts_equal": len(
            {retained[name]["namespace_count"] for name, _extra in COMMANDS}
        )
        == 1,
        "routes_equal": len(
            {retained[name]["route_sha256"] for name, _extra in COMMANDS}
        )
        == 1,
        "payload_hashes_equal": len(
            {retained[name]["payload_sha256"] for name, _extra in COMMANDS}
        )
        == 1,
        "shapes_equal": len(
            {retained[name]["shape_sha256"] for name, _extra in COMMANDS}
        )
        == 1,
    }

    cleanup_started = time.monotonic_ns()
    cleanup_deadline = time.monotonic() + 330
    while paths.socket_path.exists() or paths.ready_path.exists():
        if time.monotonic() >= cleanup_deadline:
            raise RuntimeError("worker idle cleanup did not complete")
        time.sleep(0.2)
    cleanup_wait_ms = (time.monotonic_ns() - cleanup_started) / 1_000_000

    source_after = _manifest(source_root, exclude_bytecode=True)
    cache_after = _manifest(cache_root)
    result = {
        "schema_version": 1,
        "live_operation_count": 3,
        "order": ["baseline", "cold_worker", "warm_worker"],
        "runs": retained,
        "parity": parity,
        "worker_pid_reused": worker_reused,
        "worker_rss_bytes": worker_rss,
        "worker_idle_cleanup_complete": True,
        "worker_cleanup_wait_ms": cleanup_wait_ms,
        "source_unchanged": source_before == source_after,
        "model_cache_unchanged": cache_before == cache_after,
        "telemetry_enabled": False,
        "provider_writes": 0,
        "raw_output_retained": False,
    }
    print(json.dumps(result, allow_nan=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
