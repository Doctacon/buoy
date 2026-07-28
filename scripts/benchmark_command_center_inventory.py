#!/usr/bin/env python3
"""Build and measure the disposable Command Center inventory baseline fixture.

The default command creates its fixture under the system temporary directory,
measures unchanged runtime code in isolated worker processes, prints one JSON
result, and removes the fixture. It performs no provider, source, plan, or apply
operation.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import platform
import resource
import statistics
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import duckdb

from buoy_search.applied_state import _initialize_schema
from buoy_search.command_center_local import MAX_PLAN_JSON_BYTES, LocalInventoryService
from buoy_search.plan_artifacts import (
    _create_delta_schema,
    artifact_identity,
    embedding_hash,
    embedding_text_for_chunk,
    generic_site_row_id,
    normalize_json_object,
    stable_hash,
    stable_json_dumps,
    validate_plan_document,
    verify_plan_artifacts,
)

BASE_COMMIT = "01f2d19432c4bc77e9d6bd7ab8a657b5f4583521"
CREATED_AT = "2026-07-27T00:00:00+00:00"
NAMESPACE = "site-example-com-v1"
SITE_ID = "example-com"
BASE_URL = "https://example.com/docs"
SENTINEL = b"DELTA_SENTINEL_DO_NOT_OPEN\n"
OPERATIONS = (
    "dashboard",
    "plans",
    "namespaces",
    "namespace_detail",
    "plan_detail",
    "changed_page_1",
    "changed_page_later",
    "stale_near_end",
)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _upsert_row(index: int) -> dict[str, Any]:
    canonical_url = f"https://example.com/docs/changed/{index:06d}"
    content = f"Changed benchmark content {index:06d}."
    title = f"Changed {index:06d}"
    chunk_hash = _sha256(content)
    row_id = generic_site_row_id(
        site_id=SITE_ID,
        canonical_url=canonical_url,
        section_path="",
        chunk_hash=chunk_hash,
    )
    row: dict[str, Any] = {
        "action": "changed",
        "row_id": row_id,
        "row_id_candidate": row_id,
        "site_id": SITE_ID,
        "duplicate_ordinal": 0,
        "canonical_url": canonical_url,
        "source_path": f"changed/{index:06d}.md",
        "page_hash": _sha256(f"page-{index}"),
        "chunk_hash": chunk_hash,
        "embedding_text_hash": "",
        "title": title,
        "section_path": "",
        "chunk_index": 0,
        "content": content,
        "doc_kind": "text",
        "tags_json": [],
        "source_metadata_json": {
            "source_kind": "website",
            "title": title,
            "url": canonical_url,
        },
    }
    row["embedding_text_hash"] = embedding_hash(
        embedding_text_for_chunk(row), "float32"
    )
    return row


def _stale_row(index: int) -> dict[str, Any]:
    return {
        "category": "stale",
        "row_id": f"ts_{index:032x}",
        "canonical_url": f"https://example.com/docs/removed/{index:06d}",
        "page_hash": "a" * 64,
        "chunk_hash": "b" * 64,
        "embedding_text_hash": "c" * 64,
        "prior_plan_id": "plan_" + "d" * 16,
        "prior_applied_at": CREATED_AT,
        "prior_status": "active",
        "reason": "not_in_desired_source",
    }


def _logical_hash(upserts: list[dict[str, Any]], stale_count: int) -> str:
    digest = hashlib.sha256()
    digest.update(b'{"schema_version":1,"stale_rows":[')
    for index in range(stale_count):
        if index:
            digest.update(b",")
        digest.update(
            stable_json_dumps(normalize_json_object(_stale_row(index))).encode("utf-8")
        )
    digest.update(b'],"upsert_rows":[')
    for index, row in enumerate(upserts):
        if index:
            digest.update(b",")
        digest.update(stable_json_dumps(normalize_json_object(row)).encode("utf-8"))
    digest.update(b"]}")
    return digest.hexdigest()


def _selected_plan(upsert_count: int, stale_count: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    upserts = [_upsert_row(index) for index in range(upsert_count)]
    plan: dict[str, Any] = {
        "schema_version": 2,
        "command": "plan",
        "plan_id": "plan_" + "0" * 16,
        "created_at": CREATED_AT,
        "artifact_hash": "0" * 64,
        "source": {
            "kind": "website",
            "uri": BASE_URL,
            "title": "example.com",
            "attributes": {},
        },
        "site_id": SITE_ID,
        "namespace": NAMESPACE,
        "namespace_candidate": NAMESPACE,
        "crawl_options": {"inventory_fixture": 0},
        "chunk_options": {},
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "embedding_precision": "float32",
        "applied_state": {
            "present": True,
            "schema_version": 1,
            "hash": "e" * 64,
        },
        "delta": {
            "filename": "delta.duckdb",
            "schema_version": 1,
            "logical_hash": _logical_hash(upserts, stale_count),
            "upsert_count": upsert_count,
            "stale_count": stale_count,
            "retained_stale_count": 0,
        },
        "diff": {
            "first_apply": False,
            "pages_added": 0,
            "pages_changed": upsert_count,
            "pages_unchanged": 0,
            "pages_removed": stale_count,
            "chunks_unchanged": 0,
            "chunks_to_embed": upsert_count,
            "rows_to_upsert": upsert_count,
            "stale_rows": stale_count,
            "retained_stale_rows": 0,
        },
    }
    plan["artifact_hash"] = stable_hash(artifact_identity(plan))
    plan["plan_id"] = f"plan_{plan['artifact_hash'][:16]}"
    validate_plan_document(plan)
    return plan, upserts


def _write_near_limit_plan(path: Path, plan: dict[str, Any]) -> None:
    payload = stable_json_dumps(plan)
    encoded = payload.encode("utf-8")
    if len(encoded) > MAX_PLAN_JSON_BYTES:
        raise ValueError("benchmark plan metadata exceeded the runtime limit")
    path.write_bytes(encoded + b" " * (MAX_PLAN_JSON_BYTES - len(encoded)))


def _write_delta(
    path: Path,
    plan: dict[str, Any],
    upserts: list[dict[str, Any]],
    stale_count: int,
) -> None:
    with duckdb.connect(str(path)) as connection:
        _create_delta_schema(connection)
        delta = plan["delta"]
        source = plan["source"]
        connection.execute(
            "INSERT INTO delta_metadata VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                1,
                plan["plan_id"],
                plan["site_id"],
                plan["namespace"],
                source["kind"],
                source["uri"],
                plan["applied_state"]["hash"],
                delta["logical_hash"],
                len(upserts),
                stale_count,
                0,
            ],
        )
        if upserts:
            connection.executemany(
                "INSERT INTO upsert_rows VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        ordinal,
                        row["action"],
                        row["row_id"],
                        row["row_id_candidate"],
                        row["site_id"],
                        row["duplicate_ordinal"],
                        row["canonical_url"],
                        row["source_path"],
                        row["page_hash"],
                        row["chunk_hash"],
                        row["embedding_text_hash"],
                        row["title"],
                        row["section_path"],
                        row["chunk_index"],
                        row["content"],
                        row["doc_kind"],
                        stable_json_dumps(row["tags_json"]),
                        stable_json_dumps(row["source_metadata_json"]),
                    )
                    for ordinal, row in enumerate(upserts)
                ],
            )
        connection.execute(
            """
            INSERT INTO stale_rows
            SELECT i, 'stale', 'ts_' || printf('%032x', i),
                   'https://example.com/docs/removed/' || printf('%06d', i),
                   repeat('a', 64), repeat('b', 64), repeat('c', 64),
                   'plan_' || repeat('d', 16), ?, 'active', 'not_in_desired_source'
            FROM range(?) rows(i)
            """,
            [CREATED_AT, stale_count],
        )
        connection.execute("CHECKPOINT")


def _write_state(
    state_root: Path,
    *,
    namespace: str,
    site_id: str,
    row_count: int,
) -> None:
    directory = state_root / "state" / site_id / namespace
    directory.mkdir(parents=True)
    path = directory / "state.duckdb"
    with duckdb.connect(str(path)) as connection:
        _initialize_schema(connection)
        connection.execute(
            "INSERT INTO state_metadata VALUES (1, ?, ?, ?, ?, ?, ?)",
            [site_id, namespace, BASE_URL, CREATED_AT, "plan_state", "apply_state"],
        )
        connection.execute(
            """
            INSERT INTO applied_rows
            SELECT 'ts_' || md5(? || CAST(i AS VARCHAR)),
                   'https://example.com/docs/state/' || ? || '/' || printf('%06d', i),
                   repeat('a', 64), repeat('b', 64), repeat('c', 64),
                   'plan_' || repeat('d', 16), ?,
                   CASE WHEN i % 20 = 0 THEN 'deleted'
                        WHEN i % 10 = 0 THEN 'retained_stale'
                        ELSE 'active' END
            FROM range(?) rows(i)
            """,
            [namespace, namespace, CREATED_AT, row_count],
        )
        connection.execute("CHECKPOINT")


def build_fixture(
    root: Path,
    *,
    plan_count: int = 1_000,
    large_state_rows: int = 100_003,
    small_state_count: int = 4,
    small_state_rows: int = 257,
    selected_upserts: int = 100,
    selected_stale: int = 100_000,
    legacy_depth: int = 32,
    legacy_files: int = 5_000,
) -> dict[str, Any]:
    artifacts_root = root / "artifacts"
    state_root = root / "state-root"
    artifacts_root.mkdir(parents=True)
    state_root.mkdir(parents=True)

    selected_plan, upserts = _selected_plan(selected_upserts, selected_stale)
    for index in range(plan_count):
        directory = artifacts_root / f"plan-{index:04d}"
        directory.mkdir()
        if index == 0:
            plan = selected_plan
        else:
            plan = json.loads(json.dumps(selected_plan))
            plan["crawl_options"] = {"inventory_fixture": index}
            plan["artifact_hash"] = stable_hash(artifact_identity(plan))
            plan["plan_id"] = f"plan_{plan['artifact_hash'][:16]}"
            validate_plan_document(plan)
        _write_near_limit_plan(directory / "plan.json", plan)
        if index == 0:
            _write_delta(directory / "delta.duckdb", plan, upserts, selected_stale)
        else:
            (directory / "delta.duckdb").write_bytes(SENTINEL)

    legacy = artifacts_root / "legacy"
    legacy.mkdir()
    (legacy / "plan.json").write_text(
        '{"schema_version":1,"plan_id":"plan_legacy"}', encoding="utf-8"
    )
    pages = legacy / "pages"
    pages.mkdir()
    current = pages
    for index in range(legacy_depth):
        current = current / f"depth-{index:02d}"
        current.mkdir()
    for index in range(legacy_files):
        target = pages / f"bucket-{index % 100:03d}"
        target.mkdir(exist_ok=True)
        (target / f"page-{index:05d}.json").write_text("{}", encoding="utf-8")

    _write_state(
        state_root,
        namespace=NAMESPACE,
        site_id=SITE_ID,
        row_count=large_state_rows,
    )
    for index in range(small_state_count):
        _write_state(
            state_root,
            namespace=f"small-{index:02d}",
            site_id=f"small-site-{index:02d}",
            row_count=small_state_rows,
        )

    verified = verify_plan_artifacts(
        artifacts_root / "plan-0000" / "plan.json", materialize=False
    )
    if verified.plan["plan_id"] != selected_plan["plan_id"]:
        raise AssertionError("selected fixture verification returned the wrong plan")
    return {
        "artifacts_root": artifacts_root,
        "state_root": state_root,
        "selected_plan_id": selected_plan["plan_id"],
        "namespace": NAMESPACE,
        "counts": {
            "summary_plans": plan_count,
            "near_limit_plan_bytes": MAX_PLAN_JSON_BYTES,
            "delta_sentinels": plan_count - 1,
            "selected_upserts": selected_upserts,
            "selected_stale": selected_stale,
            "large_state_rows": large_state_rows,
            "small_state_databases": small_state_count,
            "small_state_rows_each": small_state_rows,
            "total_state_rows": large_state_rows + small_state_count * small_state_rows,
            "legacy_depth": legacy_depth,
            "legacy_page_files": legacy_files,
            "legacy_bucket_directories": min(100, legacy_files),
        },
    }


def _operation(
    service: LocalInventoryService, fixture: dict[str, Any], name: str
) -> Any:
    plan_id = fixture["selected_plan_id"]
    namespace = fixture["namespace"]
    operations = {
        "dashboard": lambda: service.dashboard(),
        "plans": lambda: service.list_plans(limit=100),
        "namespaces": lambda: service.list_namespaces(limit=100),
        "namespace_detail": lambda: service.get_namespace(namespace),
        "plan_detail": lambda: service.get_plan(plan_id),
        "changed_page_1": lambda: service.list_plan_chunks(plan_id, offset=0, limit=50),
        "changed_page_later": lambda: service.list_plan_chunks(plan_id, offset=50, limit=50),
        "stale_near_end": lambda: service.list_plan_stale_rows(
            plan_id, offset=int(fixture["counts"]["selected_stale"]) - 50, limit=50
        ),
    }
    return operations[name]()


def _rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if platform.system() == "Darwin" else value * 1024


def measure_operation(fixture: dict[str, Any], name: str, *, warm_runs: int = 5) -> dict[str, Any]:
    service = LocalInventoryService(
        artifacts_root=fixture["artifacts_root"], state_root=fixture["state_root"]
    )
    timings: list[float] = []
    for _ in range(warm_runs + 1):
        gc.collect()
        started = time.perf_counter()
        result = _operation(service, fixture, name)
        timings.append((time.perf_counter() - started) * 1_000)
        del result
    return {
        "operation": name,
        "cold_ms": round(timings[0], 3),
        "warm_ms": [round(value, 3) for value in timings[1:]],
        "warm_p50_ms": round(statistics.median(timings[1:]), 3),
        "peak_rss_bytes": _rss_bytes(),
    }


def structural_observations(fixture: dict[str, Any]) -> dict[str, Any]:
    import buoy_search.applied_state as state_module
    import buoy_search.command_center_local as local_module

    counters = {
        "plan_scans": 0,
        "state_scans": 0,
        "delta_connections": 0,
        "delta_file_opens": 0,
        "state_connections": 0,
        "applied_row_objects": 0,
        "artifact_walk_directories": 0,
        "state_walk_directories": 0,
    }
    real_discover_plans = local_module._discover_plans
    real_discover_states = local_module._discover_states
    real_connect = duckdb.connect
    real_applied_row = state_module.AppliedStateRow
    real_open = os.open
    real_walk = os.walk

    def discover_plans(root: Path):
        counters["plan_scans"] += 1
        return real_discover_plans(root)

    def discover_states(root: Path):
        counters["state_scans"] += 1
        return real_discover_states(root)

    def connect(path: str, *args: Any, **kwargs: Any):
        name = Path(path).name
        if name == "delta.duckdb":
            counters["delta_connections"] += 1
        elif name == "state.duckdb":
            counters["state_connections"] += 1
        return real_connect(path, *args, **kwargs)

    def applied_row(*args: Any, **kwargs: Any):
        counters["applied_row_objects"] += 1
        return real_applied_row(*args, **kwargs)

    def open_file(path: str | os.PathLike[str], *args: Any, **kwargs: Any):
        if Path(path).name == "delta.duckdb":
            counters["delta_file_opens"] += 1
        return real_open(path, *args, **kwargs)

    def walk(top: str | os.PathLike[str], *args: Any, **kwargs: Any) -> Iterator[Any]:
        category = (
            "artifact_walk_directories"
            if Path(top) == fixture["artifacts_root"]
            else "state_walk_directories"
        )
        for item in real_walk(top, *args, **kwargs):
            counters[category] += 1
            yield item

    local_module._discover_plans = discover_plans
    local_module._discover_states = discover_states
    duckdb.connect = connect
    state_module.AppliedStateRow = applied_row
    os.open = open_file
    os.walk = walk
    try:
        service = LocalInventoryService(
            artifacts_root=fixture["artifacts_root"], state_root=fixture["state_root"]
        )
        service.dashboard()
        service.list_namespaces(limit=100)
        service.list_plans(limit=100)
    finally:
        local_module._discover_plans = real_discover_plans
        local_module._discover_states = real_discover_states
        duckdb.connect = real_connect
        state_module.AppliedStateRow = real_applied_row
        os.open = real_open
        os.walk = real_walk

    return {
        **counters,
        "summary_sequence": ["dashboard", "namespaces", "plans"],
        "legacy_descendants_traversed": counters["artifact_walk_directories"]
        > 3 * (int(fixture["counts"]["summary_plans"]) + 2),
        "summary_delta_payload_opened": counters["delta_connections"] != 0,
        "event_loop": {
            "observation": "All eight measured API route handlers are async functions that call the synchronous inventory method directly.",
            "source": "src/buoy_search/command_center_api.py:712-760",
            "blocking_work_offloaded": False,
        },
    }


def _public_fixture(root: Path, counts: dict[str, Any], plan_id: str) -> dict[str, Any]:
    return {
        "artifacts_root": root / "artifacts",
        "state_root": root / "state-root",
        "selected_plan_id": plan_id,
        "namespace": NAMESPACE,
        "counts": counts,
    }


def _worker(args: argparse.Namespace) -> int:
    root = Path(args.fixture_root)
    fixture = _public_fixture(root, json.loads(args.counts), args.plan_id)
    if args.operation == "structural":
        result = structural_observations(fixture)
    else:
        result = measure_operation(fixture, args.operation, warm_runs=args.warm_runs)
    print(json.dumps(result, sort_keys=True))
    return 0


def _host() -> dict[str, Any]:
    return {
        "os": platform.platform(),
        "architecture": platform.machine(),
        "python": platform.python_version(),
        "duckdb": duckdb.__version__,
        "logical_cpus": os.cpu_count(),
    }


def run_benchmark(*, warm_runs: int = 5) -> dict[str, Any]:
    if warm_runs < 5:
        raise ValueError("the baseline requires at least five warm runs")
    with tempfile.TemporaryDirectory(prefix="buoy-command-center-baseline-") as tmp:
        root = Path(tmp)
        fixture = build_fixture(root)
        counts_json = json.dumps(fixture["counts"], separators=(",", ":"))
        common = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--fixture-root",
            str(root),
            "--plan-id",
            fixture["selected_plan_id"],
            "--counts",
            counts_json,
            "--warm-runs",
            str(warm_runs),
        ]
        measurements = []
        for operation in OPERATIONS:
            completed = subprocess.run(
                [*common, "--operation", operation],
                check=True,
                capture_output=True,
                text=True,
            )
            measurements.append(json.loads(completed.stdout))
        structural = subprocess.run(
            [*common, "--operation", "structural"],
            check=True,
            capture_output=True,
            text=True,
        )
        return {
            "base_commit": BASE_COMMIT,
            "host": _host(),
            "fixture": fixture["counts"],
            "method": {
                "clock": "time.perf_counter wall time",
                "cold": "first call in a fresh worker process; OS filesystem caches were not dropped",
                "warm": f"next {warm_runs} calls, same fixture and runtime source",
                "warm_p50": f"median of {warm_runs} warm calls",
                "rss": "process ru_maxrss including interpreter/import/runtime; bytes",
                "fixture_lifecycle": "system temporary directory created once, reused by workers, then deleted",
            },
            "measurements": measurements,
            "structural": json.loads(structural.stdout),
            "side_effects": {
                "provider_operations": 0,
                "source_operations": 0,
                "plan_operations": 0,
                "apply_operations": 0,
            },
        }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-root")
    parser.add_argument("--plan-id")
    parser.add_argument("--counts")
    parser.add_argument("--operation", choices=(*OPERATIONS, "structural"))
    parser.add_argument("--warm-runs", type=int, default=5)
    args = parser.parse_args()
    worker_fields = (args.fixture_root, args.plan_id, args.counts, args.operation)
    if any(worker_fields) and not all(worker_fields):
        parser.error("worker mode requires fixture root, plan ID, counts, and operation")
    return args


def main() -> int:
    args = _parse_args()
    if args.fixture_root:
        return _worker(args)
    print(json.dumps(run_benchmark(warm_runs=args.warm_runs), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
