from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from scripts.benchmark_command_center_bounded_review import (
    measure_browser_inventory,
    measure_review_transition,
)
from scripts.benchmark_command_center_inventory import build_fixture


class _Response:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.status_code = 200
        self.content = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


class _PagedClient:
    def __init__(self, total: int) -> None:
        self.total = total
        self.paths: list[str] = []

    def get(self, path: str) -> _Response:
        self.paths.append(path)
        query = parse_qs(urlsplit(path).query)
        offset = int(query["offset"][0])
        limit = int(query["limit"][0])
        items = [
            {"id": index}
            for index in range(offset, min(offset + limit, self.total))
        ]
        return _Response(
            {
                "items": items,
                "total": self.total,
                "offset": offset,
                "limit": limit,
                "errors": [],
            }
        )


class CommandCenterBoundedReviewBenchmarkTests(unittest.TestCase):
    def test_browser_inventory_measurement_transfers_one_current_page(self) -> None:
        client = _PagedClient(205)

        result = measure_browser_inventory(client, "/api/v1/plans")

        self.assertEqual(result["initial_request_count"], 1)
        self.assertEqual(result["total_matching_records"], 205)
        self.assertEqual(result["records_transferred"], 50)
        self.assertEqual(result["current_react_row_count"], 50)
        self.assertEqual(result["current_page_limit"], 50)
        self.assertEqual(client.paths, ["/api/v1/plans?offset=0&limit=50"])
        self.assertEqual(
            result["approximate_json_bytes"],
            len(_PagedClient(205).get(client.paths[0]).content),
        )

    def test_fixture_can_represent_independent_namespaces(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = build_fixture(
                Path(tmp),
                plan_count=4,
                plan_namespace_count=4,
                large_state_rows=1,
                small_state_count=0,
                selected_upserts=2,
                selected_stale=3,
                legacy_depth=0,
                legacy_files=0,
            )

            self.assertEqual(fixture["counts"]["summary_plans"], 4)
            self.assertEqual(fixture["counts"]["plan_namespaces"], 4)
            self.assertEqual(fixture["counts"]["selected_namespace_plans"], 1)

    def test_api_transitions_each_make_one_complete_verifier_call(self) -> None:
        try:
            from fastapi.testclient import TestClient
            import buoy_search.command_center_local as local_module
            from buoy_search.command_center_api import create_app
            from buoy_search.command_center_local import LocalInventoryService
        except ImportError as exc:  # pragma: no cover - core-only environment
            self.skipTest(str(exc))

        with tempfile.TemporaryDirectory() as tmp:
            fixture = build_fixture(
                Path(tmp),
                plan_count=3,
                plan_namespace_count=3,
                large_state_rows=1,
                small_state_count=0,
                selected_upserts=12,
                selected_stale=30,
                legacy_depth=0,
                legacy_files=0,
            )
            service = LocalInventoryService(
                artifacts_root=fixture["artifacts_root"],
                state_root=fixture["state_root"],
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
            events: list[dict[str, Any]] = []
            event_lock = threading.Lock()
            real_verify = local_module._verify_plan_artifacts

            def instrumented(plan_path: Path, **kwargs: Any) -> Any:
                result = real_verify(plan_path, **kwargs)
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
                with event_lock:
                    events.append(
                        {
                            "window": window,
                            "duration_ms": 1.0,
                            "materialize": kwargs.get("materialize"),
                            "upsert_window": kwargs.get("upsert_window"),
                            "stale_window": kwargs.get("stale_window"),
                            "verified_upsert_rows_materialized": len(result.upsert_rows),
                            "verified_stale_rows_materialized": len(result.stale_rows),
                            "thread_id": threading.get_ident(),
                            "thread_name": threading.current_thread().name,
                        }
                    )
                return result

            with patch.object(local_module, "_verify_plan_artifacts", instrumented):
                with TestClient(app, base_url="http://localhost") as client:
                    results = [
                        measure_review_transition(
                            client,
                            fixture["selected_plan_id"],
                            transition,
                            events,
                            event_lock,
                        )
                        for transition in (
                            "initial",
                            "chunk_pagination",
                            "stale_pagination",
                        )
                    ]

            self.assertEqual(
                [result["browser_request_count"] for result in results], [1, 1, 1]
            )
            self.assertEqual(
                [result["verifier_call_count"] for result in results], [1, 1, 1]
            )
            self.assertEqual(
                [result["verifier_calls"][0]["window"] for result in results],
                ["review", "chunks", "stale_rows"],
            )
            self.assertTrue(
                all(
                    result["verifier_calls"][0]["materialize"] is False
                    for result in results
                )
            )
            self.assertEqual(
                [
                    (
                        result["verifier_calls"][0][
                            "verified_upsert_rows_materialized"
                        ],
                        result["verifier_calls"][0][
                            "verified_stale_rows_materialized"
                        ],
                    )
                    for result in results
                ],
                [(10, 10), (2, 0), (0, 10)],
            )
            self.assertEqual(
                [
                    result["requests"][0]["response_materialized_row_total"]
                    for result in results
                ],
                [20, 2, 10],
            )


if __name__ == "__main__":
    unittest.main()
