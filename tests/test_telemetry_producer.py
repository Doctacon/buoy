from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import duckdb

from buoy_search import telemetry
from buoy_search.telemetry_envelope import decode_trace_envelope_v1
from buoy_search.telemetry_queue import (
    PublicationResult,
    scan_queue_read_only,
    telemetry_paths,
)


class TelemetryProducerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.home = Path(self._temporary.name)
        self._home_patch = patch(
            "buoy_search.local_paths.Path.home",
            return_value=self.home,
        )
        self._environment_patch = patch.dict(
            os.environ,
            {"BUOY_TELEMETRY": "local"},
            clear=True,
        )
        self._home_patch.start()
        self._environment_patch.start()

    def tearDown(self) -> None:
        self._environment_patch.stop()
        self._home_patch.stop()
        self._temporary.cleanup()

    def _complete_trace(self) -> None:
        with telemetry.retrieval_trace(
            mode="explicit_single",
            embedding_model="BAAI/bge-small-en-v1.5",
            embedding_precision="float32",
            top_k=3,
            candidates=12,
            namespace_count=1,
            initial_fanout=1,
        ) as root:
            root.set_attributes(
                {
                    "buoy.retrieval.outcome": "success",
                    "buoy.retrieval.hit_count": 0,
                    "buoy.retrieval.final_fanout": 0,
                }
            )
            root.mark_ok()

    def test_completion_publishes_canonical_envelope_without_duckdb_call(self) -> None:
        captured: list[bytes] = []

        def publish(payload: bytes, *, paths: object) -> PublicationResult:
            del paths
            captured.append(payload)
            return PublicationResult(
                published=True,
                source_name="v1-00000000000000000000000000000001.json",
                reason="published",
            )

        with (
            patch.object(telemetry, "publish_envelope", side_effect=publish),
            patch.object(telemetry, "request_writer_start") as start,
            patch.object(
                duckdb,
                "connect",
                side_effect=AssertionError("producer opened DuckDB"),
            ),
        ):
            self._complete_trace()

        self.assertEqual(len(captured), 1)
        rows = decode_trace_envelope_v1(captured[0])
        self.assertEqual(rows.run[5:9], ("explicit_single", "success", 0, 1))
        start.assert_called_once()

    def test_publication_failure_is_silent_and_does_not_start_writer(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        with (
            patch.object(
                telemetry,
                "publish_envelope",
                side_effect=RuntimeError("private failure detail"),
            ),
            patch.object(telemetry, "request_writer_start") as start,
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            self._complete_trace()

        start.assert_not_called()
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")

    def test_disabled_completion_has_zero_files_and_no_start_attempt(self) -> None:
        os.environ.clear()
        with patch.object(telemetry, "request_writer_start") as start:
            self._complete_trace()

        start.assert_not_called()
        self.assertFalse((self.home / ".buoy").exists())

    def test_published_trace_drains_to_the_existing_duckdb_v1_schema(self) -> None:
        from buoy_search import telemetry_writer

        with patch.object(telemetry, "request_writer_start"):
            self._complete_trace()
        paths = telemetry_paths()
        before = scan_queue_read_only(paths)
        self.assertEqual((before.ready, before.claimed), (1, 0))

        with patch.object(telemetry_writer, "IDLE_EXIT_SECONDS", 0.0):
            self.assertEqual(telemetry_writer.run_writer(paths), 0)

        after = scan_queue_read_only(paths)
        self.assertEqual((after.ready, after.claimed, after.receipts), (0, 0, 1))
        with duckdb.connect(str(paths.database_path), read_only=True) as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT retrieval_mode, outcome, hit_count FROM trace_runs"
                ).fetchall(),
                [("explicit_single", "success", 0)],
            )


if __name__ == "__main__":
    unittest.main()
