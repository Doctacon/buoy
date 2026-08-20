from __future__ import annotations

import ast
from contextlib import contextmanager
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import duckdb

from buoy_search.telemetry_envelope import TraceRows, encode_trace_envelope_v1
from buoy_search import telemetry_store, telemetry_writer
from buoy_search.telemetry_queue import (
    TerminalReceipt,
    claim_ready_batch,
    publish_envelope,
    read_claimed_envelope,
    read_terminal_receipt,
    read_writer_state,
    scan_queue_read_only,
    telemetry_paths,
)


def _canonical(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _valid_rows(number: int = 1) -> TraceRows:
    trace_id = f"{number:032x}"
    root_span_id = f"{number * 2:016x}"
    started = datetime(2026, 8, 19, 12, 0) + timedelta(seconds=number)
    ended = started + timedelta(milliseconds=5)
    attributes = {
        "buoy.embedding.model": "custom",
        "buoy.embedding.precision": "custom",
        "buoy.observation.schema_version": 1,
        "buoy.retrieval.candidates": 12,
        "buoy.retrieval.failure_count": 0,
        "buoy.retrieval.final_fanout": 0,
        "buoy.retrieval.hit_count": 0,
        "buoy.retrieval.incomplete": False,
        "buoy.retrieval.initial_fanout": 1,
        "buoy.retrieval.mode": "explicit_single",
        "buoy.retrieval.namespace_count": 1,
        "buoy.retrieval.outcome": "success",
        "buoy.retrieval.top_k": 3,
        "buoy.retrieval.widened": False,
        "buoy.version": "0+test",
    }
    return TraceRows(
        run=(
            trace_id,
            root_span_id,
            started,
            ended,
            5.0,
            "explicit_single",
            "success",
            0,
            1,
            1,
            0,
            0,
            False,
            False,
            None,
            None,
            "custom",
            "custom",
            3,
            12,
            "0+test",
            1,
        ),
        spans=(
            (
                trace_id,
                root_span_id,
                None,
                "buoy.retrieve",
                started,
                ended,
                5.0,
                "OK",
                _canonical(attributes),
            ),
        ),
        events=(),
    )


class TelemetryWriterTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name) / "telemetry"
        self.paths = telemetry_paths(self.root)

    def publish(self, number: int = 1):
        return publish_envelope(
            encode_trace_envelope_v1(_valid_rows(number)),
            paths=self.paths,
        )

    def drain(self) -> int:
        with patch.object(telemetry_writer, "IDLE_EXIT_SECONDS", 0.0):
            return telemetry_writer.run_writer(self.paths)

    def test_absent_status_is_exact_read_only_and_disabled(self) -> None:
        value = telemetry_writer.telemetry_status(
            paths=self.paths,
            environment={},
            now_unix_ms=1,
        )

        self.assertEqual(
            set(value),
            {
                "schema_version",
                "requested",
                "effective",
                "enablement_reason",
                "overall",
                "database_path",
                "store",
                "queue",
                "writer",
                "accounting",
            },
        )
        self.assertEqual(value["overall"], "disabled")
        self.assertEqual(value["store"]["state"], "absent")
        self.assertEqual(value["queue"]["state"], "absent")
        self.assertFalse(self.root.exists())
        command = telemetry_writer.telemetry_status_command(
            json_output=True,
            paths=self.paths,
            environment={},
        )
        self.assertEqual(command.exit_code, 0)
        self.assertEqual(json.loads(command.output), value | {
            "writer": value["writer"] | {"heartbeat_age_ms": None}
        })
        self.assertFalse(self.root.exists())

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFOs are unavailable")
    def test_status_and_flush_block_without_opening_state_fifo(self) -> None:
        self.publish()
        os.mkfifo(self.paths.writer_state_path, mode=0o600)

        status = telemetry_writer.telemetry_status(
            paths=self.paths,
            environment={"BUOY_TELEMETRY": "local"},
        )
        flushed = telemetry_writer.telemetry_flush(timeout=0, paths=self.paths)

        self.assertEqual(status["overall"], "blocked")
        self.assertEqual(flushed["outcome"], "blocked")

    def test_unsafe_writer_state_metadata_blocks_status(self) -> None:
        self.publish()
        self.paths.writer_state_path.write_bytes(b"{}")
        self.paths.writer_state_path.chmod(0o644)

        status = telemetry_writer.telemetry_status(
            paths=self.paths,
            environment={"BUOY_TELEMETRY": "local"},
        )

        self.assertEqual(status["overall"], "blocked")

    def test_hostile_json_state_is_bounded_and_writer_recovers(self) -> None:
        hostile_payloads = (
            b'{"schema_version":' + b"9" * 5_000 + b"}",
            b'{"value":' + b"[" * 10_000 + b"0" + b"]" * 10_000 + b"}",
        )

        for index, payload in enumerate(hostile_payloads, start=1):
            with self.subTest(payload_bytes=len(payload)):
                paths = telemetry_paths(self.root.parent / f"telemetry-{index}")
                publish_envelope(
                    encode_trace_envelope_v1(_valid_rows(index)),
                    paths=paths,
                )
                paths.writer_state_path.write_bytes(payload)
                paths.writer_state_path.chmod(0o600)

                status = telemetry_writer.telemetry_status(
                    paths=paths,
                    environment={"BUOY_TELEMETRY": "local"},
                )
                self.assertEqual(status["overall"], "degraded")
                self.assertTrue(status["accounting"]["incomplete"])
                with patch.object(telemetry_writer, "IDLE_EXIT_SECONDS", 0.0):
                    self.assertEqual(telemetry_writer.run_writer(paths), 0)
                with duckdb.connect(
                    str(paths.database_path),
                    read_only=True,
                ) as connection:
                    self.assertEqual(
                        connection.execute(
                            "SELECT count(*) FROM trace_runs"
                        ).fetchone()[0],
                        1,
                    )

    def test_unsafe_initialization_scratch_blocks_status_and_flush(self) -> None:
        cases = ("symlink", "unknown-entry", "hardlinked-database")
        for index, kind in enumerate(cases, start=1):
            with self.subTest(kind=kind):
                paths = telemetry_paths(self.root.parent / f"scratch-{kind}")
                publish_envelope(
                    encode_trace_envelope_v1(_valid_rows(index)),
                    paths=paths,
                )
                if kind == "symlink":
                    target = self.root.parent / "outside-scratch"
                    target.mkdir(mode=0o700, exist_ok=True)
                    paths.database_init_directory.symlink_to(target)
                elif kind == "unknown-entry":
                    paths.database_init_directory.mkdir(mode=0o700)
                    unknown = paths.database_init_directory / "unknown"
                    unknown.write_bytes(b"private")
                    unknown.chmod(0o600)
                else:
                    paths.database_init_directory.mkdir(mode=0o700)
                    target = self.root.parent / "outside-scratch-database"
                    target.write_bytes(b"private")
                    target.chmod(0o600)
                    os.link(target, paths.init_database_path)

                status = telemetry_writer.telemetry_status(
                    paths=paths,
                    environment={"BUOY_TELEMETRY": "local"},
                )
                flushed = telemetry_writer.telemetry_flush(
                    timeout=0,
                    paths=paths,
                )

                self.assertEqual(status["overall"], "blocked")
                self.assertEqual(status["store"]["state"], "unsafe")
                self.assertEqual(flushed["outcome"], "blocked")

    def test_unsafe_operational_lock_blocks_status_and_flush(self) -> None:
        self.publish()
        target = self.root.parent / "outside-lock"
        target.write_bytes(b"")
        target.chmod(0o600)
        self.paths.writer_lock_path.symlink_to(target)

        status = telemetry_writer.telemetry_status(
            paths=self.paths,
            environment={"BUOY_TELEMETRY": "local"},
        )
        flushed = telemetry_writer.telemetry_flush(
            timeout=0,
            paths=self.paths,
        )

        self.assertEqual(status["overall"], "blocked")
        self.assertEqual(status["queue"]["state"], "unsafe")
        self.assertEqual(flushed["outcome"], "blocked")

    def test_same_inode_initialization_crash_is_flush_recoverable(self) -> None:
        rows = _valid_rows()
        telemetry_store.append_trace(self.paths, rows)
        publish_envelope(
            encode_trace_envelope_v1(rows),
            paths=self.paths,
        )
        self.paths.database_init_directory.mkdir(mode=0o700)
        os.link(self.paths.database_path, self.paths.init_database_path)
        self.assertEqual(self.paths.database_path.stat().st_nlink, 2)

        status = telemetry_writer.telemetry_status(
            paths=self.paths,
            environment={"BUOY_TELEMETRY": "local"},
        )

        def start(*, paths: object) -> None:
            del paths
            with patch.object(telemetry_writer, "IDLE_EXIT_SECONDS", 0.0):
                self.assertEqual(telemetry_writer.run_writer(self.paths), 0)

        with patch.object(
            telemetry_writer,
            "request_writer_start",
            side_effect=start,
        ):
            flushed = telemetry_writer.telemetry_flush(
                timeout=2,
                paths=self.paths,
            )

        self.assertEqual(status["overall"], "degraded")
        self.assertEqual(status["store"]["state"], "present_unverified")
        self.assertEqual(flushed["outcome"], "flushed")
        self.assertEqual(flushed["replayed"], 1)
        self.assertFalse(self.paths.database_init_directory.exists())
        self.assertEqual(self.paths.database_path.stat().st_nlink, 1)
        with duckdb.connect(
            str(self.paths.database_path),
            read_only=True,
        ) as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT count(*) FROM trace_runs"
                ).fetchone()[0],
                1,
            )

    def test_unknown_inbox_child_blocks_status_and_flush(self) -> None:
        self.publish()
        unknown = self.paths.inbox_directory / "unknown"
        unknown.mkdir(mode=0o700)

        status = telemetry_writer.telemetry_status(
            paths=self.paths,
            environment={"BUOY_TELEMETRY": "local"},
        )
        flushed = telemetry_writer.telemetry_flush(timeout=0, paths=self.paths)

        self.assertEqual(status["overall"], "blocked")
        self.assertEqual(flushed["outcome"], "blocked")

    def test_ready_trace_commits_receipts_and_acknowledges(self) -> None:
        publication = self.publish()
        self.assertTrue(publication.published)

        self.assertEqual(self.drain(), 0)

        queue = scan_queue_read_only(self.paths)
        self.assertEqual((queue.ready, queue.claimed, queue.receipts), (0, 0, 1))
        receipt = read_terminal_receipt(str(publication.source_name), paths=self.paths)
        self.assertIsNotNone(receipt)
        assert receipt is not None
        self.assertEqual(receipt.kind, "committed")
        with duckdb.connect(str(self.paths.database_path), read_only=True) as connection:
            self.assertEqual(
                connection.execute("SELECT count(*) FROM trace_runs").fetchone(),
                (1,),
            )
        state = read_writer_state(self.paths)
        self.assertIsNotNone(state)
        assert state is not None
        self.assertEqual(state.phase, "stopped")
        self.assertEqual(state.persisted_runs_snapshot, 1)

    def test_malformed_item_is_rejected_without_stopping_later_valid_work(self) -> None:
        malformed = publish_envelope(b'{"bad":1}', paths=self.paths)
        valid = self.publish(2)

        self.assertEqual(self.drain(), 0)

        malformed_receipt = read_terminal_receipt(
            str(malformed.source_name),
            paths=self.paths,
        )
        valid_receipt = read_terminal_receipt(
            str(valid.source_name),
            paths=self.paths,
        )
        assert malformed_receipt is not None and valid_receipt is not None
        self.assertEqual(malformed_receipt.kind, "rejected")
        self.assertIn(
            malformed_receipt.reason,
            {"invalid_shape", "noncanonical_json"},
        )
        self.assertEqual(valid_receipt.kind, "committed")
        state = read_writer_state(self.paths)
        assert state is not None
        self.assertEqual(state.rejected, 1)

    def test_unexpected_decoder_failure_retains_claim(self) -> None:
        publication = self.publish()

        with (
            patch.object(
                telemetry_writer,
                "decode_trace_envelope_v1",
                side_effect=RuntimeError("private decoder detail"),
            ),
            patch.object(telemetry_writer, "IDLE_EXIT_SECONDS", 0.0),
        ):
            self.assertEqual(telemetry_writer.run_writer(self.paths), 0)

        snapshot = scan_queue_read_only(self.paths)
        state = read_writer_state(self.paths)
        self.assertEqual(snapshot.ready, 0)
        self.assertEqual(snapshot.claimed, 1)
        self.assertEqual(snapshot.receipts, 0)
        self.assertIn(str(publication.source_name), snapshot.claimed_names)
        self.assertIsNotNone(state)
        assert state is not None
        self.assertEqual(state.phase, "blocked")
        self.assertEqual(state.reason, "receipt_failure")
        self.assertFalse(self.paths.database_path.exists())

    def test_unexpected_decoder_failure_cannot_prove_rejected_receipt(self) -> None:
        publication = self.publish()
        source_name = str(publication.source_name)
        self.assertEqual(claim_ready_batch(self.paths), (source_name,))
        claim = read_claimed_envelope(self.paths, source_name)
        receipt = TerminalReceipt(
            1,
            "rejected",
            source_name,
            claim.envelope_sha256,
            True,
            claim.envelope_bytes,
            1,
            "invalid_value",
        )
        self.assertTrue(
            telemetry_writer.publish_terminal_receipt(
                self.paths,
                receipt,
            ).published
        )

        with (
            patch.object(
                telemetry_writer,
                "decode_trace_envelope_v1",
                side_effect=RuntimeError("private decoder detail"),
            ),
            patch.object(telemetry_writer, "IDLE_EXIT_SECONDS", 0.0),
        ):
            self.assertEqual(telemetry_writer.run_writer(self.paths), 0)

        snapshot = scan_queue_read_only(self.paths)
        state = read_writer_state(self.paths)
        self.assertEqual(snapshot.claimed, 1)
        self.assertEqual(snapshot.receipts, 1)
        self.assertFalse(self.paths.database_path.exists())
        self.assertIsNotNone(state)
        assert state is not None
        self.assertEqual(state.phase, "blocked")
        self.assertEqual(state.reason, "receipt_failure")

    def test_unexpected_decoder_failure_cannot_prove_committed_receipt(self) -> None:
        publication = self.publish()
        source_name = str(publication.source_name)
        self.assertEqual(claim_ready_batch(self.paths), (source_name,))
        claim = read_claimed_envelope(self.paths, source_name)
        receipt = TerminalReceipt(
            1,
            "committed",
            source_name,
            claim.envelope_sha256,
            True,
            claim.envelope_bytes,
            1,
            None,
        )
        self.assertTrue(
            telemetry_writer.publish_terminal_receipt(
                self.paths,
                receipt,
            ).published
        )

        with patch.object(
            telemetry_writer,
            "decode_trace_envelope_v1",
            side_effect=RuntimeError("private decoder detail"),
        ):
            self.assertEqual(telemetry_writer.run_writer(self.paths), 0)

        snapshot = scan_queue_read_only(self.paths)
        state = read_writer_state(self.paths)
        self.assertEqual(snapshot.claimed, 1)
        self.assertEqual(snapshot.receipts, 1)
        self.assertIsNotNone(state)
        assert state is not None
        self.assertEqual(state.phase, "blocked")
        self.assertEqual(state.reason, "receipt_failure")

    def test_commit_without_receipt_recovers_as_exact_replay(self) -> None:
        publication = self.publish()
        source_name = str(publication.source_name)
        self.assertEqual(claim_ready_batch(self.paths), (source_name,))
        committed = telemetry_store.append_trace(self.paths, _valid_rows())
        self.assertEqual(committed.outcome, "committed")

        self.assertEqual(self.drain(), 0)

        receipt = read_terminal_receipt(source_name, paths=self.paths)
        assert receipt is not None
        self.assertEqual(receipt.kind, "replayed")
        state = read_writer_state(self.paths)
        assert state is not None
        self.assertEqual(state.recovered_claims, 1)
        self.assertEqual(state.replays, 1)
        self.assertEqual(state.persisted_runs_snapshot, 1)

    def test_incompatible_store_blocks_and_preserves_claim_and_bytes(self) -> None:
        publication = self.publish()
        with duckdb.connect(str(self.paths.database_path)) as connection:
            connection.execute("CREATE TABLE incompatible(secret VARCHAR)")
            connection.execute("INSERT INTO incompatible VALUES ('owned')")
        os.chmod(self.paths.database_path, 0o600)
        before = self.paths.database_path.read_bytes()

        self.assertEqual(self.drain(), 0)

        self.assertEqual(self.paths.database_path.read_bytes(), before)
        queue = scan_queue_read_only(self.paths)
        self.assertEqual((queue.ready, queue.claimed), (0, 1))
        self.assertEqual(queue.claimed_names, (str(publication.source_name),))
        status = telemetry_writer.telemetry_status(
            paths=self.paths,
            environment={"BUOY_TELEMETRY": "local"},
        )
        self.assertEqual(status["overall"], "blocked")
        self.assertEqual(status["store"]["state"], "incompatible")
        self.assertEqual(status["writer"]["reason"], "database_incompatible")

    def test_flush_timeout_is_bounded_and_keeps_fixed_pending_snapshot(self) -> None:
        self.publish()
        with patch.object(telemetry_writer, "request_writer_start"):
            value = telemetry_writer.telemetry_flush(
                timeout=0,
                paths=self.paths,
            )

        self.assertEqual(value["outcome"], "timeout")
        self.assertEqual((value["snapshot"], value["pending"]), (1, 1))

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks are unavailable")
    def test_flush_empty_snapshot_still_reports_an_unsafe_store_as_blocked(self) -> None:
        self.root.mkdir(mode=0o700)
        target = self.root.parent / "outside.duckdb"
        target.write_bytes(b"outside")
        self.paths.database_path.symlink_to(target)

        value = telemetry_writer.telemetry_flush(
            timeout=0,
            paths=self.paths,
        )

        self.assertEqual(value["outcome"], "blocked")
        self.assertEqual((value["snapshot"], value["pending"]), (0, 0))
        self.assertEqual(target.read_bytes(), b"outside")

    def test_flush_excludes_work_published_after_its_snapshot(self) -> None:
        self.publish(1)

        def start(*, paths: object) -> None:
            del paths
            self.publish(2)
            self.drain()

        with patch.object(
            telemetry_writer,
            "request_writer_start",
            side_effect=start,
        ):
            value = telemetry_writer.telemetry_flush(
                timeout=2,
                paths=self.paths,
            )

        self.assertEqual(value["outcome"], "flushed")
        self.assertEqual(value["snapshot"], 1)
        self.assertEqual(value["committed"], 1)
        with duckdb.connect(str(self.paths.database_path), read_only=True) as connection:
            self.assertEqual(
                connection.execute("SELECT count(*) FROM trace_runs").fetchone(),
                (2,),
            )

    def test_flush_reports_rejected_snapshot_as_classified(self) -> None:
        publish_envelope(b'{"bad":1}', paths=self.paths)

        def start(*, paths: object) -> None:
            del paths
            self.drain()

        with patch.object(
            telemetry_writer,
            "request_writer_start",
            side_effect=start,
        ):
            value = telemetry_writer.telemetry_flush(
                timeout=2,
                paths=self.paths,
            )

        self.assertEqual(value["outcome"], "classified")
        self.assertEqual((value["rejected"], value["pending"]), (1, 0))

    def test_stopped_transition_releases_lifetime_inside_start_authority(self) -> None:
        order: list[str] = []

        @contextmanager
        def authority(*_args: object, **_kwargs: object):
            order.append("start-enter")
            try:
                yield 1
            finally:
                order.append("start-exit")

        runtime = telemetry_writer._WriterRuntime(
            self.paths,
            lambda: order.append("lifetime-release"),
        )
        with (
            patch.object(telemetry_writer, "writer_start_lock", authority),
            patch.object(
                runtime,
                "_persist_state",
                side_effect=lambda **_kwargs: order.append("state"),
            ),
        ):
            stopped = runtime._stop_with_reason("retry_deadline", "busy")

        self.assertTrue(stopped)
        self.assertEqual(
            order,
            ["start-enter", "state", "lifetime-release", "start-exit"],
        )
        self.assertEqual(runtime.state.phase, "stopped")

    def test_stopped_transition_keeps_lifetime_when_start_lock_times_out(self) -> None:
        released: list[bool] = []

        @contextmanager
        def timeout(*_args: object, **_kwargs: object):
            raise telemetry_writer.QueueLockTimeout("busy")
            yield 1

        runtime = telemetry_writer._WriterRuntime(
            self.paths,
            lambda: released.append(True),
        )
        with patch.object(telemetry_writer, "writer_start_lock", timeout):
            stopped = runtime._stop_with_reason("retry_deadline", "busy")

        self.assertFalse(stopped)
        self.assertEqual(released, [])
        self.assertNotEqual(runtime.state.phase, "stopped")

    def test_start_lease_cleanup_is_bounded_and_fails_closed(self) -> None:
        runtime = telemetry_writer._WriterRuntime(self.paths, lambda: None)
        with (
            patch.object(telemetry_writer, "START_LEASE_SECONDS", 0),
            patch.object(
                telemetry_writer,
                "clear_writer_start_lease",
                return_value=False,
            ),
            patch.object(
                telemetry_writer,
                "read_writer_start_lease",
                return_value=object(),
            ),
        ):
            with self.assertRaises(telemetry_writer.UnsafePathError):
                runtime._clear_start_lease()

    def test_database_busy_retry_uses_governed_ten_ms_cadence(self) -> None:
        attempts = 0
        result = object()
        sleeps: list[float] = []

        class FakeStore:
            StoreBusyError = telemetry_store.StoreBusyError
            StoreIncompatibleError = telemetry_store.StoreIncompatibleError
            StoreUnsafeError = telemetry_store.StoreUnsafeError
            StoreUnreadableError = telemetry_store.StoreUnreadableError
            StoreWriteError = telemetry_store.StoreWriteError

            @staticmethod
            def append_trace(*_args: object, **_kwargs: object) -> object:
                nonlocal attempts
                attempts += 1
                if attempts < 3:
                    raise telemetry_store.StoreBusyError("private detail")
                return result

        runtime = telemetry_writer._WriterRuntime(self.paths, lambda: None)
        with (
            patch.object(
                telemetry_writer,
                "_load_store_module",
                return_value=FakeStore,
            ),
            patch.object(runtime, "_record_store_failure"),
            patch.object(runtime, "_persist_state"),
            patch.object(
                telemetry_writer.time,
                "sleep",
                side_effect=sleeps.append,
            ),
        ):
            observed = runtime._append_with_retry(_valid_rows())

        self.assertIs(observed, result)
        self.assertEqual(attempts, 3)
        self.assertEqual(sleeps, [0.01, 0.01])

    def test_receipt_temp_without_proven_store_is_reclassified_safely(self) -> None:
        publication = self.publish()
        source_name = str(publication.source_name)
        self.assertEqual(claim_ready_batch(self.paths), (source_name,))
        claim = read_claimed_envelope(self.paths, source_name)
        receipt = TerminalReceipt(
            schema_version=1,
            kind="committed",
            source_name=source_name,
            envelope_sha256=claim.envelope_sha256,
            digest_complete=True,
            envelope_bytes=claim.envelope_bytes,
            recorded_at_unix_ms=1,
            reason=None,
        )
        payload = _canonical(
            {
                "schema_version": receipt.schema_version,
                "kind": receipt.kind,
                "source_name": receipt.source_name,
                "envelope_sha256": receipt.envelope_sha256,
                "digest_complete": receipt.digest_complete,
                "envelope_bytes": receipt.envelope_bytes,
                "recorded_at_unix_ms": receipt.recorded_at_unix_ms,
                "reason": receipt.reason,
            }
        ).encode("ascii")
        temporary = self.paths.receipts_directory / (
            "r1-" + source_name[3:-5] + ".part"
        )
        temporary.write_bytes(payload)
        os.chmod(temporary, 0o600)

        self.assertEqual(self.drain(), 0)

        final = read_terminal_receipt(source_name, paths=self.paths)
        assert final is not None
        self.assertEqual(final.kind, "committed")
        self.assertNotEqual(final.recorded_at_unix_ms, 1)
        self.assertFalse(temporary.exists())
        self.assertEqual(scan_queue_read_only(self.paths).claimed, 0)
        with duckdb.connect(str(self.paths.database_path), read_only=True) as connection:
            self.assertEqual(
                connection.execute("SELECT count(*) FROM trace_runs").fetchone(),
                (1,),
            )

    def test_proven_committed_receipt_temp_keeps_its_classification(self) -> None:
        publication = self.publish()
        source_name = str(publication.source_name)
        self.assertEqual(claim_ready_batch(self.paths), (source_name,))
        claim = read_claimed_envelope(self.paths, source_name)
        self.assertEqual(
            telemetry_store.append_trace(self.paths, _valid_rows()).outcome,
            "committed",
        )
        recorded_at = 123
        payload = _canonical(
            {
                "schema_version": 1,
                "kind": "committed",
                "source_name": source_name,
                "envelope_sha256": claim.envelope_sha256,
                "digest_complete": True,
                "envelope_bytes": claim.envelope_bytes,
                "recorded_at_unix_ms": recorded_at,
                "reason": None,
            }
        ).encode("ascii")
        temporary = self.paths.receipts_directory / (
            "r1-" + source_name[3:-5] + ".part"
        )
        temporary.write_bytes(payload)
        os.chmod(temporary, 0o600)

        self.assertEqual(self.drain(), 0)

        final = read_terminal_receipt(source_name, paths=self.paths)
        assert final is not None
        self.assertEqual((final.kind, final.recorded_at_unix_ms), ("committed", recorded_at))
        self.assertFalse(temporary.exists())
        self.assertEqual(scan_queue_read_only(self.paths).claimed, 0)

    def test_module_has_no_top_level_duckdb_or_store_import(self) -> None:
        source = Path(telemetry_writer.__file__).read_text(encoding="utf-8")
        ast.parse(source)
        script = """
import importlib.abc
import sys

class RejectForbidden(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in {"duckdb", "buoy_search.telemetry_store"}:
            raise AssertionError(f"forbidden eager import: {fullname}")
        return None

sys.meta_path.insert(0, RejectForbidden())
import buoy_search.telemetry_writer
assert "duckdb" not in sys.modules
assert "buoy_search.telemetry_store" not in sys.modules
"""
        completed = subprocess.run(
            [sys.executable, "-I", "-c", script],
            cwd=Path(__file__).resolve().parents[1],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            0,
            msg=f"stdout={completed.stdout!r} stderr={completed.stderr!r}",
        )


if __name__ == "__main__":
    unittest.main()
