from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from buoy_search.command_center_local import LocalInventoryService
from scripts.benchmark_command_center_inventory import (
    MAX_PLAN_JSON_BYTES,
    SENTINEL,
    _operation,
    build_fixture,
    measure_operation,
    structural_observations,
)


class CommandCenterInventoryBenchmarkTests(unittest.TestCase):
    def test_disposable_fixture_and_driver_cover_all_baseline_surfaces(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = build_fixture(
                Path(tmp),
                plan_count=3,
                large_state_rows=11,
                small_state_count=2,
                small_state_rows=3,
                selected_upserts=60,
                selected_stale=60,
                legacy_depth=2,
                legacy_files=4,
            )
            artifacts = fixture["artifacts_root"]
            sentinels = sorted(artifacts.glob("plan-*/delta.duckdb"))[1:]
            service = LocalInventoryService(
                artifacts_root=artifacts, state_root=fixture["state_root"]
            )

            results = {
                name: _operation(service, fixture, name)
                for name in (
                    "dashboard",
                    "plans",
                    "namespaces",
                    "namespace_detail",
                    "plan_detail",
                    "changed_page_1",
                    "changed_page_later",
                    "stale_near_end",
                )
            }
            measurement = measure_operation(fixture, "plans", warm_runs=1)
            structural = structural_observations(fixture)

            self.assertEqual(results["dashboard"].plan_count, 3)
            self.assertEqual(results["plans"].total, 3)
            self.assertEqual(results["namespaces"].total, 3)
            self.assertEqual(results["namespace_detail"].summary.namespace, fixture["namespace"])
            self.assertEqual(results["plan_detail"].payload_verification, "verified")
            self.assertEqual(len(results["changed_page_1"].items), 50)
            self.assertEqual(len(results["changed_page_later"].items), 10)
            self.assertEqual(len(results["stale_near_end"].items), 50)
            self.assertEqual(measurement["operation"], "plans")
            self.assertEqual(len(measurement["warm_ms"]), 1)
            self.assertEqual(structural["plan_scans"], 3)
            self.assertEqual(structural["state_scans"], 3)
            self.assertEqual(structural["delta_connections"], 0)
            self.assertEqual(structural["delta_file_opens"], 0)
            self.assertEqual(structural["applied_row_objects"], 51)
            self.assertTrue(structural["legacy_descendants_traversed"])
            self.assertTrue(all(path.read_bytes() == SENTINEL for path in sentinels))
            self.assertTrue(
                all(
                    path.stat().st_size == MAX_PLAN_JSON_BYTES
                    for path in artifacts.glob("plan-*/plan.json")
                )
            )


if __name__ == "__main__":
    unittest.main()
