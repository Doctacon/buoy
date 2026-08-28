"""Explicit provider-free validation for the dormant embedding worker prototype.

Run manually from the repository root with offline model assets already cached:

    uv run python tests/fixtures/embedding_worker_validation.py

The harness never calls a provider or retrieval path. It emits one sanitized
JSON result and removes its private worker home after the bounded worker exits.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from buoy_search.retrieval import embedding_worker as worker

QUERIES = (
    "how does automatic namespace routing select a source",
    "where is local retrieval telemetry stored",
    "how are repository chunks ranked",
)
_CREDENTIAL_NAMES = frozenset(
    {
        "TURBOPUFFER_API_KEY",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "AZURE_CLIENT_SECRET",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
    }
)


def _manifest(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.exists():
        return "absent"
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix().encode()
        observed = path.lstat()
        digest.update(relative)
        digest.update(str(observed.st_mode).encode())
        digest.update(str(observed.st_size).encode())
        if path.is_symlink():
            digest.update(os.readlink(path).encode())
        elif path.is_file():
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def _cache_root(real_home: Path) -> Path:
    configured = os.environ.get("HF_HUB_CACHE")
    hub = Path(configured) if configured else real_home / ".cache" / "huggingface" / "hub"
    return hub / "models--BAAI--bge-small-en-v1.5"


def _clean_environment(*, isolated_home: Path, cache_hub: Path) -> dict[str, str]:
    environment = worker._minimal_worker_environment() | {
        "HOME": os.fspath(isolated_home),
        "HF_HUB_CACHE": os.fspath(cache_hub),
    }
    if set(environment) & _CREDENTIAL_NAMES:
        raise RuntimeError("credential environment validation failed")
    return environment


def _cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def _client(home: Path) -> int:
    started = time.monotonic_ns()
    vectors = worker.encode(QUERIES, buoy_home=home)
    elapsed_ms = (time.monotonic_ns() - started) / 1_000_000
    state = worker.read_worker_state(buoy_home=home)
    print(
        json.dumps(
            {
                "elapsed_ms": elapsed_ms,
                "pid": state["pid"] if state else None,
                "sentence_transformers_imported": "sentence_transformers" in sys.modules,
                "vectors": vectors,
            },
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


def _server(home: Path) -> int:
    # Fifteen seconds is a harness cleanup bound, not a configurable product
    # behavior. Unit coverage separately verifies the fixed 300-second contract.
    return worker.run_worker(worker.worker_paths(home), idle_seconds=15.0)


def _run_client(script: Path, home: Path, environment: dict[str, str]) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, "-I", os.fspath(script), "--client", os.fspath(home)],
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=worker.REQUEST_TIMEOUT_SECONDS,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError("fresh client failed")
    return json.loads(completed.stdout)


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


def main() -> int:
    script = Path(__file__).resolve()
    repository = script.parents[2]
    source_root = repository / "src" / "buoy_search"
    real_home = Path.home()
    cache_root = _cache_root(real_home)
    cache_hub = cache_root.parent
    revision = cache_root / "snapshots" / worker.REVISION
    if not revision.is_dir():
        raise RuntimeError("exact model revision is not cached locally")

    source_before = _manifest(source_root)
    cache_before = _manifest(cache_root)
    from sentence_transformers import SentenceTransformer

    model_started = time.monotonic_ns()
    model = SentenceTransformer(
        worker.MODEL,
        revision=worker.REVISION,
        local_files_only=True,
    )
    direct = model.encode(
        list(QUERIES), normalize_embeddings=True, show_progress_bar=False
    )
    direct_vectors = [value.tolist() for value in direct]
    direct_ms = (time.monotonic_ns() - model_started) / 1_000_000

    with tempfile.TemporaryDirectory(prefix="buoy-worker-validation-", dir=real_home) as root:
        private_root = Path(root)
        isolated_home = private_root / "home"
        isolated_home.mkdir(mode=0o700)
        buoy_home = isolated_home / ".buoy"
        environment = _clean_environment(isolated_home=isolated_home, cache_hub=cache_hub)
        startup = time.monotonic_ns()
        server = subprocess.Popen(
            [sys.executable, "-I", os.fspath(script), "--server", os.fspath(buoy_home)],
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            start_new_session=True,
        )
        deadline = time.monotonic() + worker.STARTUP_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            state = worker.read_worker_state(buoy_home=buoy_home)
            if state is not None and state.get("phase") == "ready":
                break
            if server.poll() is not None:
                raise RuntimeError("worker exited before readiness")
            time.sleep(0.02)
        else:
            raise RuntimeError("worker readiness timed out")
        startup_ms = (time.monotonic_ns() - startup) / 1_000_000

        first = _run_client(script, buoy_home, environment)
        second = _run_client(script, buoy_home, environment)
        pid = int(first["pid"])
        if pid != int(second["pid"]) or pid != server.pid:
            raise RuntimeError("fresh clients did not reuse one worker")
        worker_vectors = first["vectors"]
        maximum_delta = max(
            abs(float(actual) - float(expected))
            for actual_vector, expected_vector in zip(worker_vectors, direct_vectors, strict=True)
            for actual, expected in zip(actual_vector, expected_vector, strict=True)
        )
        direct_order = sorted(
            range(1, len(direct_vectors)),
            key=lambda index: (-_cosine(direct_vectors[0], direct_vectors[index]), index),
        )
        worker_order = sorted(
            range(1, len(worker_vectors)),
            key=lambda index: (-_cosine(worker_vectors[0], worker_vectors[index]), index),
        )
        rss_bytes = _rss_bytes(pid)
        server_result = server.wait(timeout=30)
        if server_result != 0:
            raise RuntimeError("worker did not exit cleanly")
        if worker.worker_paths(buoy_home).socket_path.exists():
            raise RuntimeError("worker socket remained after exit")

    source_after = _manifest(source_root)
    cache_after = _manifest(cache_root)
    result = {
        "schema_version": 1,
        "model": worker.MODEL,
        "revision": worker.REVISION,
        "precision": worker.PRECISION,
        "dimensions": worker.DIMENSIONS,
        "direct_model_and_encode_ms": direct_ms,
        "worker_startup_ms": startup_ms,
        "first_fresh_client_ms": first["elapsed_ms"],
        "second_fresh_client_ms": second["elapsed_ms"],
        "worker_pid_reused": True,
        "fresh_clients_imported_sentence_transformers": bool(
            first["sentence_transformers_imported"]
            or second["sentence_transformers_imported"]
        ),
        "maximum_vector_delta": maximum_delta,
        "ranking_order_equal": direct_order == worker_order,
        "worker_rss_bytes": rss_bytes,
        "rss_below_4_gib": rss_bytes is not None and rss_bytes < 4 * 1024**3,
        "source_unchanged": source_before == source_after,
        "model_cache_unchanged": cache_before == cache_after,
        "provider_operations": 0,
        "network_operations_requested": 0,
        "telemetry_operations": 0,
        "worker_cleanup_complete": True,
    }
    if not all(
        (
            maximum_delta <= 1e-6,
            result["ranking_order_equal"],
            not result["fresh_clients_imported_sentence_transformers"],
            result["rss_below_4_gib"],
            result["source_unchanged"],
            result["model_cache_unchanged"],
        )
    ):
        raise RuntimeError("embedding worker validation failed")
    print(json.dumps(result, allow_nan=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--client":
        raise SystemExit(_client(Path(sys.argv[2])))
    if len(sys.argv) == 3 and sys.argv[1] == "--server":
        raise SystemExit(_server(Path(sys.argv[2])))
    if len(sys.argv) != 1:
        raise SystemExit(2)
    raise SystemExit(main())
