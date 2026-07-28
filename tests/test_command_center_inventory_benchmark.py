from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from buoy_search.command_center_local import LocalInventoryService
from scripts.benchmark_command_center_inventory import (
    MAX_PLAN_JSON_BYTES,
    OPERATIONS,
    SENTINEL,
    _operation,
    _validate_operation_result,
    build_fixture,
    measure_operation,
    structural_observations,
)


class CommandCenterInventoryBenchmarkTests(unittest.TestCase):
    def _fixture(self, root: Path) -> dict[str, Any]:
        return build_fixture(
            root,
            plan_count=3,
            large_state_rows=11,
            small_state_count=2,
            small_state_rows=3,
            selected_upserts=60,
            selected_stale=60,
            legacy_depth=2,
            legacy_files=4,
        )

    def test_disposable_fixture_and_driver_cover_permanent_surfaces(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self._fixture(Path(tmp))
            artifacts = fixture["artifacts_root"]
            sentinels = sorted(artifacts.glob("plan-*/delta.duckdb"))[1:]
            service = LocalInventoryService(
                artifacts_root=artifacts, state_root=fixture["state_root"]
            )

            for name in OPERATIONS:
                result = _operation(service, fixture, name)
                _validate_operation_result(fixture, name, result)

            measurement = measure_operation(fixture, "plans", warm_runs=1)
            self.assertEqual(measurement["operation"], "plans")
            self.assertEqual(len(measurement["warm_ms"]), 1)
            self.assertTrue(all(path.read_bytes() == SENTINEL for path in sentinels))
            self.assertTrue(
                all(
                    path.stat().st_size == MAX_PLAN_JSON_BYTES
                    for path in artifacts.glob("plan-*/plan.json")
                )
            )

    def test_measurement_rejects_an_invalid_result_after_timing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self._fixture(Path(tmp))
            with patch(
                "scripts.benchmark_command_center_inventory._operation",
                return_value=SimpleNamespace(total=-1, errors=[]),
            ):
                with self.assertRaisesRegex(AssertionError, "invalid full-fixture result"):
                    measure_operation(fixture, "plans", warm_runs=0)

    def test_structural_instrumentation_reports_dynamic_baseline_signals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self._fixture(Path(tmp))
            structural = structural_observations(fixture)
            delta_counter_names = (
                "delta_duckdb_connections",
                "delta_os_opens",
                "delta_builtin_opens",
                "delta_io_opens",
            )

            self.assertGreaterEqual(structural["plan_scans"], 1)
            self.assertGreaterEqual(structural["state_scans"], 1)
            self.assertGreaterEqual(structural["applied_row_objects"], 0)
            self.assertIsInstance(structural["legacy_descendants_traversed"], bool)
            self.assertEqual(
                structural["summary_delta_payload_open_count"],
                sum(structural[name] for name in delta_counter_names),
            )
            self.assertEqual(
                structural["summary_delta_payload_opened"],
                any(structural[name] != 0 for name in delta_counter_names),
            )
            self.assertFalse(structural["summary_delta_payload_opened"])


if __name__ == "__main__":
    unittest.main()
