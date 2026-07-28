#!/usr/bin/env python3
"""Measure bounded Command Center browser transport and plan review requests.

The fixture and all raw results live under system temporary paths. The driver
uses only local FastAPI requests and verified disposable artifacts; it performs
no provider, source, model, plan, apply, catalog, or namespace operation.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import resource
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

import duckdb

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.benchmark_command_center_inventory import build_fixture

INVENTORY_LIMIT = 50
REVIEW_LIMIT = 10
REVIEW_MAX_CHARS = 2_000


def _rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if platform.system() == "Darwin" else value * 1024


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _command_version(*command: str) -> str | None:
    try:
        return subprocess.run(
            command, check=True, capture_output=True, text=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _checkout() -> dict[str, Any]:
    repository = Path(__file__).resolve().parents[1]
    commit = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "-C", str(repository), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    production_changes = []
    for line in status:
        path = line[3:]
        if path.startswith("src/") or (
            path.startswith("web/src/") and not path.endswith(".test.tsx")
        ):
            production_changes.append(path)
    return {
        "commit": commit,
        "working_tree_status_entries": len(status),
        "production_behavior_files_changed": production_changes,
    }


def _host() -> dict[str, Any]:
    return {
        "os": platform.platform(),
        "architecture": platform.machine(),
        "logical_cpus": os.cpu_count(),
        "python": platform.python_version(),
        "duckdb": duckdb.__version__,
        "fastapi": _package_version("fastapi"),
        "starlette": _package_version("starlette"),
        "httpx": _package_version("httpx"),
        "node": _command_version("node", "--version"),
        "npm": _command_version("npm", "--version"),
    }


def measure_browser_inventory(client: Any, path: str) -> dict[str, Any]:
    """Execute the current frontend's one-page inventory request shape."""

    request_path = f"{path}?offset=0&limit={INVENTORY_LIMIT}"
    started = time.perf_counter()
    response = client.get(request_path)
    wall_ms = (time.perf_counter() - started) * 1_000
    if response.status_code != 200:
        raise AssertionError(
            f"inventory request failed: {request_path} -> {response.status_code}"
        )
    payload = response.json()
    items = payload["items"]
    total = int(payload["total"])
    if int(payload["offset"]) != 0 or int(payload["limit"]) != INVENTORY_LIMIT:
        raise AssertionError("inventory pagination metadata did not match the request")
    expected_rows = min(total, INVENTORY_LIMIT)
    if len(items) != expected_rows:
        raise AssertionError("inventory response did not contain exactly one current page")
    return {
        "request_paths": [request_path],
        "initial_request_count": 1,
        "total_matching_records": total,
        "records_transferred": len(items),
        "approximate_json_bytes": len(response.content),
        "wall_ms": round(wall_ms, 3),
        "current_react_row_count": len(items),
        "current_page_limit": INVENTORY_LIMIT,
        "peak_rss_bytes": _rss_bytes(),
    }


def _review_request(plan_id: str, transition: str) -> tuple[str, str]:
    if transition == "initial":
        return (
            "review",
            f"/api/v1/plans/{plan_id}/review?chunk_offset=0&chunk_limit={REVIEW_LIMIT}"
            f"&max_chars={REVIEW_MAX_CHARS}&stale_offset=0&stale_limit={REVIEW_LIMIT}",
        )
    if transition == "chunk_pagination":
        return (
            "chunks",
            f"/api/v1/plans/{plan_id}/chunks?offset={REVIEW_LIMIT}"
            f"&limit={REVIEW_LIMIT}&max_chars={REVIEW_MAX_CHARS}",
        )
    if transition == "stale_pagination":
        return (
            "stale_rows",
            f"/api/v1/plans/{plan_id}/stale-rows?offset={REVIEW_LIMIT}"
            f"&limit={REVIEW_LIMIT}",
        )
    raise ValueError(f"unknown review transition: {transition}")


def measure_review_transition(
    client: Any,
    plan_id: str,
    transition: str,
    verifier_events: list[dict[str, Any]],
    event_lock: threading.Lock,
) -> dict[str, Any]:
    label, path = _review_request(plan_id, transition)
    with event_lock:
        event_start = len(verifier_events)

    started = time.perf_counter()
    response = client.get(path)
    wall_ms = (time.perf_counter() - started) * 1_000
    if response.status_code != 200:
        raise AssertionError(f"review request failed: {path} -> {response.status_code}")
    payload = response.json()
    if label == "review":
        materialized_rows = {
            "detail": 0,
            "chunks": len(payload["chunks"]["items"]),
            "stale_rows": len(payload["stale_rows"]["items"]),
        }
    else:
        materialized_rows = {
            "detail": 0,
            "chunks": len(payload["items"]) if label == "chunks" else 0,
            "stale_rows": len(payload["items"]) if label == "stale_rows" else 0,
        }
    request = {
        "label": label,
        "path": path,
        "status": response.status_code,
        "approximate_json_bytes": len(response.content),
        "response_materialized_rows": materialized_rows,
        "response_materialized_row_total": sum(materialized_rows.values()),
    }
    with event_lock:
        events = [dict(event) for event in verifier_events[event_start:]]
    if len(events) != 1:
        raise AssertionError(
            f"{transition} expected one complete verification, observed {len(events)}"
        )
    expected_window = label
    if events[0]["window"] != expected_window:
        raise AssertionError(
            f"{transition} verifier window was {events[0]['window']}, expected {expected_window}"
        )
    durations = [float(event["duration_ms"]) for event in events]
    return {
        "transition": transition,
        "browser_request_count": 1,
        "requests": [request],
        "verifier_call_count": 1,
        "verifier_calls": events,
        "complete_verification_duration_ms": {
            "values": [round(value, 3) for value in sorted(durations)],
            "p50": round(statistics.median(durations), 3),
            "sum": round(sum(durations), 3),
        },
        "wall_ms": round(wall_ms, 3),
        "peak_rss_bytes": _rss_bytes(),
        "worker_thread_behavior": {
            "main_thread_id": threading.main_thread().ident,
            "verifier_thread_ids": [int(events[0]["thread_id"])],
            "verifier_thread_names": [str(events[0]["thread_name"])],
            "unique_verifier_threads": 1,
            "all_verifiers_off_main_thread": (
                events[0]["thread_id"] != threading.main_thread().ident
            ),
        },
    }


def run_benchmark() -> dict[str, Any]:
    try:
        from fastapi.testclient import TestClient
        import buoy_search.command_center_local as local_module
        from buoy_search.command_center_api import create_app
        from buoy_search.command_center_local import LocalInventoryService
    except ImportError as exc:
        raise RuntimeError("run `uv sync --extra ui` before this benchmark") from exc

    checkout = _checkout()

    with tempfile.TemporaryDirectory(prefix="buoy-bounded-review-final-") as tmp:
        root = Path(tmp)
        fixture = build_fixture(
            root,
            plan_count=1_000,
            plan_namespace_count=1_000,
            large_state_rows=1,
            small_state_count=0,
            small_state_rows=1,
            selected_upserts=100,
            selected_stale=100_000,
            legacy_depth=0,
            legacy_files=0,
        )
        service = LocalInventoryService(
            artifacts_root=fixture["artifacts_root"], state_root=fixture["state_root"]
        )

        class InertPlanJobs:
            def shutdown(self, *, wait: bool) -> None:
                del wait

        app = create_app(
            artifacts_root=fixture["artifacts_root"],
            state_root=fixture["state_root"],
            local_inventory=service,
            plan_job_service_factory=InertPlanJobs,
        )

        verifier_events: list[dict[str, Any]] = []
        event_lock = threading.Lock()
        real_verify = local_module._verify_plan_artifacts

        def instrumented_verify(plan_path: Path, **kwargs: Any) -> Any:
            started = time.perf_counter()
            result = real_verify(plan_path, **kwargs)
            duration_ms = (time.perf_counter() - started) * 1_000
            if (
                kwargs.get("upsert_window") is not None
                and kwargs.get("stale_window") is not None
            ):
                window = "review"
            elif kwargs.get("upsert_window") is not None:
                window = "chunks"
            elif kwargs.get("stale_window") is not None:
                window = "stale_rows"
            else:
                window = "detail"
            event = {
                "window": window,
                "duration_ms": round(duration_ms, 3),
                "materialize": kwargs.get("materialize"),
                "upsert_window": kwargs.get("upsert_window"),
                "stale_window": kwargs.get("stale_window"),
                "verified_upsert_rows_materialized": len(result.upsert_rows),
                "verified_stale_rows_materialized": len(result.stale_rows),
                "thread_id": threading.get_ident(),
                "thread_name": threading.current_thread().name,
            }
            with event_lock:
                verifier_events.append(event)
            return result

        local_module._verify_plan_artifacts = instrumented_verify
        try:
            with TestClient(app, base_url="http://localhost") as client:
                inventories = {
                    "plans": measure_browser_inventory(client, "/api/v1/plans"),
                    "namespaces": measure_browser_inventory(client, "/api/v1/namespaces"),
                }
                review = [
                    measure_review_transition(
                        client,
                        fixture["selected_plan_id"],
                        transition,
                        verifier_events,
                        event_lock,
                    )
                    for transition in (
                        "initial",
                        "chunk_pagination",
                        "stale_pagination",
                    )
                ]
        finally:
            local_module._verify_plan_artifacts = real_verify

        expected_namespaces = int(fixture["counts"]["plan_namespaces"])
        if inventories["plans"]["total_matching_records"] != 1_000:
            raise AssertionError("plans inventory total did not cover the complete fixture")
        if inventories["namespaces"]["total_matching_records"] != expected_namespaces:
            raise AssertionError("namespaces inventory total did not cover the complete fixture")
        if any(
            inventory["records_transferred"] != INVENTORY_LIMIT
            for inventory in inventories.values()
        ):
            raise AssertionError("inventory transport exceeded or missed one current page")
        return {
            "measured_checkout": checkout,
            "host": _host(),
            "fixture": fixture["counts"],
            "method": {
                "clock": "time.perf_counter wall time",
                "browser_inventory": (
                    "current frontend one-page request shape, offset 0 and limit 50"
                ),
                "react_rows": (
                    "one React item row per transferred current-page record, bound by the "
                    "focused 1,000-record frontend regression"
                ),
                "review": (
                    "current initial combined or focused pagination request issued "
                    "synchronously through FastAPI TestClient"
                ),
                "json_bytes": (
                    "sum of exact UTF-8 API response body bytes; excludes headers and "
                    "transport framing"
                ),
                "rss": (
                    "process ru_maxrss after each measurement; cumulative whole-process "
                    "peak in bytes"
                ),
                "fixture_lifecycle": "system temporary directory, deleted automatically",
                "verification": (
                    "instrumented unchanged _verify_plan_artifacts calls with "
                    "materialize=False"
                ),
            },
            "browser_inventory": inventories,
            "selected_plan_review": review,
            "side_effects": {
                "provider_operations": 0,
                "source_operations": 0,
                "model_loads": 0,
                "plan_operations": 0,
                "apply_operations": 0,
                "catalog_or_namespace_mutations": 0,
                "turbopuffer_writes": 0,
            },
            "limits": [
                (
                    "TestClient executes the production ASGI app without a network socket "
                    "or graphical browser."
                ),
                (
                    "Frontend tests separately bind these measured request shapes to "
                    "current React/api behavior."
                ),
                (
                    "Wall times retain OS filesystem caches; review transitions run "
                    "sequentially and each performs one fresh complete verification."
                ),
                (
                    "Peak RSS is cumulative and process-wide, not transition-attributed "
                    "incremental memory."
                ),
                (
                    "Measurements are observational for this host and fixture, not "
                    "portable CI thresholds."
                ),
            ],
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    print(json.dumps(run_benchmark(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
