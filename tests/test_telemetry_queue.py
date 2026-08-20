from __future__ import annotations

import ast
from contextlib import contextmanager
import json
import os
from pathlib import Path
import stat
import tempfile
import time
import unittest
import warnings
from unittest.mock import Mock, patch

from buoy_search import telemetry_queue as queue


class TelemetryQueueTests(unittest.TestCase):
    def setUp(self) -> None:
        capability = queue.posix_writer_capability()
        if not capability.supported:
            self.skipTest(capability.reason or "POSIX writer unsupported")
        self._temporary = tempfile.TemporaryDirectory(
            prefix="buoy-telemetry-queue-test-"
        )
        self.parent = Path(self._temporary.name)
        self.paths = queue.telemetry_paths(self.parent / "telemetry")

    def tearDown(self) -> None:
        self._temporary.cleanup()

    @staticmethod
    def payload(label: str = "one") -> bytes:
        return json.dumps(
            {"opaque": label},
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    def publish(self, label: str = "one") -> queue.PublicationResult:
        result = queue.publish_envelope(self.payload(label), paths=self.paths)
        self.assertTrue(result.published, result)
        self.assertIsNotNone(result.source_name)
        return result

    def test_paths_are_the_complete_fixed_v1_layout(self) -> None:
        root = self.parent / "telemetry"
        paths = self.paths
        self.assertEqual(paths.directory, root)
        self.assertEqual(paths.database_path, root / "telemetry.duckdb")
        self.assertEqual(paths.database_wal_path, root / "telemetry.duckdb.wal")
        self.assertEqual(paths.lock_path, root / "write.lock")
        self.assertEqual(paths.queue_lock_path, root / "queue.lock")
        self.assertEqual(paths.writer_lock_path, root / "writer.lock")
        self.assertEqual(paths.writer_start_lock_path, root / "writer-start.lock")
        self.assertEqual(paths.writer_start_path, root / "writer-start-v1.json")
        self.assertEqual(paths.writer_start_temp_path, root / ".writer-start-v1.tmp")
        self.assertEqual(
            paths.producer_accounting_path,
            root / "producer-accounting-v1.json",
        )
        self.assertEqual(
            paths.producer_accounting_temp_path,
            root / ".producer-accounting-v1.tmp",
        )
        self.assertEqual(paths.writer_state_path, root / "writer-state-v1.json")
        self.assertEqual(paths.writer_state_temp_path, root / ".writer-state-v1.tmp")
        self.assertEqual(paths.database_init_directory, root / "database-init-v1")
        self.assertEqual(paths.init_database_path, root / "database-init-v1/telemetry.duckdb")
        self.assertEqual(paths.init_wal_path, root / "database-init-v1/telemetry.duckdb.wal")
        self.assertEqual(paths.inbox_directory, root / "inbox-v1")
        self.assertEqual(paths.temp_directory, root / "inbox-v1/tmp")
        self.assertEqual(paths.ready_directory, root / "inbox-v1/ready")
        self.assertEqual(paths.claimed_directory, root / "inbox-v1/claimed")
        self.assertEqual(paths.receipts_directory, root / "inbox-v1/receipts")

    def test_read_only_scan_of_absent_queue_has_zero_side_effects(self) -> None:
        before = set(self.parent.iterdir())
        snapshot = queue.scan_queue_read_only(self.paths)
        self.assertFalse(snapshot.present)
        self.assertEqual(set(self.parent.iterdir()), before)
        self.assertFalse(self.paths.directory.exists())

    def test_publish_is_atomic_private_opaque_and_scannable(self) -> None:
        payload = self.payload("opaque-value")
        result = queue.publish_envelope(payload, paths=self.paths)

        self.assertTrue(result.published)
        self.assertRegex(result.source_name or "", r"^v1-[0-9a-f]{32}\.json$")
        ready = self.paths.ready_directory / str(result.source_name)
        self.assertEqual(ready.read_bytes(), payload)
        self.assertEqual(list(self.paths.temp_directory.iterdir()), [])
        self.assertEqual(stat.S_IMODE(self.paths.directory.stat().st_mode), 0o700)
        for directory in (
            self.paths.inbox_directory,
            self.paths.temp_directory,
            self.paths.ready_directory,
            self.paths.claimed_directory,
            self.paths.receipts_directory,
        ):
            self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(ready.stat().st_mode), 0o600)
        self.assertEqual(ready.stat().st_nlink, 1)
        snapshot = queue.scan_queue_read_only(self.paths)
        self.assertEqual(snapshot.ready, 1)
        self.assertEqual(snapshot.claimed, 0)
        self.assertEqual(snapshot.pending_bytes, len(payload))
        self.assertEqual(snapshot.ready_names, (result.source_name,))

    def test_unsupported_capability_fails_before_creating_any_path(self) -> None:
        with patch.object(
            queue,
            "posix_writer_capability",
            return_value=queue.CapabilityResult(False, "platform_unsupported"),
        ):
            result = queue.publish_envelope(self.payload(), paths=self.paths)

        self.assertEqual(result.reason, "platform_unsupported")
        self.assertFalse(result.published)
        self.assertFalse(self.paths.directory.exists())

    def test_oversized_input_is_not_published(self) -> None:
        result = queue.publish_envelope(
            b"x" * (queue.ENVELOPE_MAX_BYTES + 1),
            paths=self.paths,
        )
        self.assertFalse(result.published)
        self.assertEqual(result.reason, "publication_failure")
        self.assertFalse(self.paths.ready_directory.exists())

    def test_count_and_byte_capacity_drop_only_newest(self) -> None:
        first = self.publish("first")
        original = (self.paths.ready_directory / str(first.source_name)).read_bytes()

        with patch.object(queue, "PUBLISHED_MAX_ENTRIES", 1):
            full = queue.publish_envelope(self.payload("second"), paths=self.paths)
        self.assertFalse(full.published)
        self.assertEqual(full.reason, "queue_full")
        self.assertEqual(
            (self.paths.ready_directory / str(first.source_name)).read_bytes(),
            original,
        )

        with patch.object(queue, "PUBLISHED_MAX_BYTES", len(original)):
            byte_full = queue.publish_envelope(self.payload("third"), paths=self.paths)
        self.assertFalse(byte_full.published)
        self.assertEqual(byte_full.reason, "queue_full")
        accounting = queue.read_producer_accounting(self.paths)
        self.assertIsNotNone(accounting)
        assert accounting is not None
        self.assertEqual(accounting.queue_full, 2)
        self.assertEqual(accounting.producer_dropped_lower_bound, 2)

    def test_exact_byte_capacity_is_allowed(self) -> None:
        payload = self.payload("exact")
        with patch.object(queue, "PUBLISHED_MAX_BYTES", len(payload)):
            result = queue.publish_envelope(payload, paths=self.paths)
        self.assertTrue(result.published)

    def test_unique_token_checks_all_queue_and_receipt_names_eight_times(self) -> None:
        first = self.publish("first")
        token = str(first.source_name)[3:-5]
        with patch.object(queue.secrets, "token_hex", return_value=token):
            result = queue.publish_envelope(self.payload("second"), paths=self.paths)
        self.assertFalse(result.published)
        self.assertEqual(result.reason, "publication_failure")
        self.assertEqual(queue.scan_queue_read_only(self.paths).ready, 1)

    def test_symlinked_queue_child_is_rejected_without_following(self) -> None:
        initial = self.publish("initial")
        redirected = self.parent / "redirected"
        redirected.mkdir(mode=0o700)
        (self.paths.ready_directory / str(initial.source_name)).unlink()
        self.paths.ready_directory.rmdir()
        self.paths.ready_directory.symlink_to(redirected, target_is_directory=True)

        result = queue.publish_envelope(self.payload("private"), paths=self.paths)

        self.assertFalse(result.published)
        self.assertEqual(result.reason, "publication_failure")
        self.assertEqual(list(redirected.iterdir()), [])

    def test_unsafe_preexisting_child_creates_no_queue_asset(self) -> None:
        self.paths.directory.mkdir(mode=0o700)
        self.paths.inbox_directory.mkdir(mode=0o700)
        redirected = self.parent / "redirected-preflight"
        redirected.mkdir(mode=0o700)
        self.paths.ready_directory.symlink_to(
            redirected,
            target_is_directory=True,
        )

        before_root = set(self.paths.directory.iterdir())
        before_inbox = set(self.paths.inbox_directory.iterdir())
        result = queue.publish_envelope(self.payload("private"), paths=self.paths)

        self.assertFalse(result.published)
        self.assertEqual(result.reason, "publication_failure")
        self.assertEqual(set(self.paths.directory.iterdir()), before_root)
        self.assertEqual(set(self.paths.inbox_directory.iterdir()), before_inbox)
        self.assertFalse(self.paths.queue_lock_path.exists())
        self.assertEqual(list(redirected.iterdir()), [])

    def test_unsafe_complete_tree_creates_no_accounting_asset(self) -> None:
        self.publish("layout")
        unknown = self.paths.temp_directory / "unknown"
        unknown.write_bytes(b"unsafe")
        unknown.chmod(0o600)
        before_root = set(self.paths.directory.iterdir())

        result = queue.publish_envelope(self.payload("private"), paths=self.paths)

        self.assertFalse(result.published)
        self.assertEqual(result.reason, "publication_failure")
        self.assertEqual(set(self.paths.directory.iterdir()), before_root)
        self.assertFalse(self.paths.producer_accounting_path.exists())

    def test_post_rename_accounting_failure_still_reports_published(self) -> None:
        accounting_attempts: list[str] = []

        def fail_accounting(_root_fd: int, field: str) -> None:
            accounting_attempts.append(field)
            raise OSError("injected accounting failure")

        with (
            patch.object(queue, "fsync_directory", return_value=False),
            patch.object(queue, "_increment_accounting_at", fail_accounting),
        ):
            result = queue.publish_envelope(self.payload("linearized"), paths=self.paths)

        self.assertTrue(result.published)
        self.assertEqual(result.reason, "published")
        self.assertTrue(result.durability_degraded)
        self.assertEqual(accounting_attempts, ["directory_sync_failure"])
        assert result.source_name is not None
        self.assertTrue((self.paths.ready_directory / result.source_name).is_file())

    def test_hardlinked_ready_file_makes_read_only_scan_unsafe(self) -> None:
        result = self.publish()
        source = self.paths.ready_directory / str(result.source_name)
        os.link(source, self.parent / "second-link")
        snapshot = queue.scan_queue_read_only(self.paths)
        self.assertTrue(snapshot.unsafe)

    def test_unknown_inbox_child_makes_read_only_scan_unsafe(self) -> None:
        self.publish()
        unknown = self.paths.inbox_directory / "unknown"
        unknown.mkdir(mode=0o700)

        snapshot = queue.scan_queue_read_only(self.paths)

        self.assertTrue(snapshot.unsafe)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFOs are unavailable")
    def test_fixed_state_fifo_is_rejected_before_open(self) -> None:
        self.paths.directory.mkdir(mode=0o700)
        os.mkfifo(self.paths.writer_state_path, mode=0o600)
        root_fd = queue.open_verified_directory(self.paths.directory)
        try:
            with self.assertRaises(queue.UnsafePathError):
                queue._read_all_verified(
                    root_fd,
                    "writer-state-v1.json",
                    maximum=queue.STATE_MAX_BYTES,
                )
        finally:
            os.close(root_fd)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFOs are unavailable")
    def test_read_only_scan_rejects_unsafe_operational_locks(self) -> None:
        cases = (
            ("queue-symlink", "queue_lock_path", "symlink"),
            ("writer-hardlink", "writer_lock_path", "hardlink"),
            ("start-fifo", "writer_start_lock_path", "fifo"),
            ("write-mode", "lock_path", "mode"),
        )
        for label, field, kind in cases:
            with self.subTest(label=label):
                paths = queue.telemetry_paths(self.parent / label)
                queue.publish_envelope(self.payload(label), paths=paths)
                lock_path = getattr(paths, field)
                lock_path.unlink(missing_ok=True)
                target = self.parent / f"{label}-target"
                if kind == "symlink":
                    target.write_bytes(b"")
                    target.chmod(0o600)
                    lock_path.symlink_to(target)
                elif kind == "hardlink":
                    target.write_bytes(b"")
                    target.chmod(0o600)
                    os.link(target, lock_path)
                elif kind == "fifo":
                    os.mkfifo(lock_path, mode=0o600)
                else:
                    lock_path.write_bytes(b"")
                    lock_path.chmod(0o644)

                snapshot = queue.scan_queue_read_only(paths)

                self.assertTrue(snapshot.unsafe)
                self.assertFalse(snapshot.unreadable)

    def test_claim_read_receipt_and_acknowledgement_are_ordered(self) -> None:
        result = self.publish("claim")
        source_name = str(result.source_name)
        self.assertEqual(
            queue.claim_ready_batch(self.paths),
            (source_name,),
        )
        read = queue.read_claimed_envelope(self.paths, source_name)
        self.assertEqual(read.payload, self.payload("claim"))
        self.assertTrue(read.digest_complete)
        self.assertEqual(
            read.envelope_sha256,
            queue.hashlib.sha256(self.payload("claim")).hexdigest(),
        )
        with self.assertRaises(FileNotFoundError):
            queue.acknowledge_claim(self.paths, source_name)

        receipt = queue.TerminalReceipt(
            schema_version=1,
            kind="committed",
            source_name=source_name,
            envelope_sha256=read.envelope_sha256,
            digest_complete=True,
            envelope_bytes=read.envelope_bytes,
            recorded_at_unix_ms=int(time.time() * 1_000),
            reason=None,
        )
        published = queue.publish_terminal_receipt(self.paths, receipt)
        self.assertTrue(published.published)
        self.assertTrue(queue.acknowledge_claim(self.paths, source_name))
        self.assertFalse((self.paths.claimed_directory / source_name).exists())
        observed = queue.read_terminal_receipt(source_name, paths=self.paths)
        self.assertEqual(observed, receipt)

    def test_claim_recovery_preserves_bytes_and_skips_terminal_claim(self) -> None:
        result = self.publish("recover")
        source_name = str(result.source_name)
        queue.claim_ready_batch(self.paths)
        self.assertTrue(queue.recover_claim(self.paths, source_name))
        self.assertEqual(
            (self.paths.ready_directory / source_name).read_bytes(),
            self.payload("recover"),
        )

    def test_oversized_claim_is_not_read_or_hashed(self) -> None:
        result = self.publish("small")
        source_name = str(result.source_name)
        queue.claim_ready_batch(self.paths)
        claim = self.paths.claimed_directory / source_name
        claim.write_bytes(b"x" * (queue.ENVELOPE_MAX_BYTES + 1))
        claim.chmod(0o600)

        observed = queue.read_claimed_envelope(self.paths, source_name)

        self.assertTrue(observed.oversized)
        self.assertIsNone(observed.payload)
        self.assertIsNone(observed.envelope_sha256)
        self.assertFalse(observed.digest_complete)

    def test_receipt_is_canonical_content_free_and_unique(self) -> None:
        result = self.publish("receipt")
        source_name = str(result.source_name)
        queue.claim_ready_batch(self.paths)
        read = queue.read_claimed_envelope(self.paths, source_name)
        receipt = queue.TerminalReceipt(
            1,
            "replayed",
            source_name,
            read.envelope_sha256,
            True,
            read.envelope_bytes,
            123,
            None,
        )
        first = queue.publish_terminal_receipt(self.paths, receipt)
        second = queue.publish_terminal_receipt(self.paths, receipt)
        self.assertTrue(first.published)
        self.assertTrue(second.already_present)
        receipt_path = self.paths.receipts_directory / queue.receipt_name_for_source(
            source_name
        )
        raw = receipt_path.read_bytes()
        self.assertFalse(raw.endswith(b"\n"))
        self.assertEqual(
            raw,
            json.dumps(
                json.loads(raw),
                ensure_ascii=True,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode(),
        )

    def test_invalid_receipt_combinations_are_rejected_before_filesystem_change(self) -> None:
        invalid = queue.TerminalReceipt(
            1,
            "committed",
            "v1-" + "a" * 32 + ".json",
            None,
            False,
            1,
            1,
            None,
        )
        with self.assertRaises(queue.InvalidStateError):
            queue.publish_terminal_receipt(self.paths, invalid)
        self.assertFalse(self.paths.directory.exists())

        rejected_conflict = queue.TerminalReceipt(
            1,
            "rejected",
            "v1-" + "a" * 32 + ".json",
            "b" * 64,
            True,
            1,
            1,
            "trace_conflict",
        )
        with self.assertRaises(queue.InvalidStateError):
            queue.publish_terminal_receipt(self.paths, rejected_conflict)
        self.assertFalse(self.paths.directory.exists())

    def test_boolean_versions_and_counters_are_never_integers(self) -> None:
        accounting = queue._accounting_object(queue.ProducerAccounting())
        accounting["schema_version"] = True
        with self.assertRaises(queue.InvalidStateError):
            queue._parse_accounting(accounting)

        lease = {"schema_version": True, "lease_started_unix_ms": 0}
        with self.assertRaises(queue.InvalidStateError):
            queue._parse_start_lease(lease)

        writer_state = queue._writer_state_object(queue.WriterState())
        writer_state["schema_version"] = True
        with self.assertRaises(queue.InvalidStateError):
            queue._parse_writer_state(writer_state)
        writer_state["schema_version"] = 1
        writer_state["store_schema_version"] = True
        with self.assertRaises(queue.InvalidStateError):
            queue._parse_writer_state(writer_state)

        receipt = {
            "schema_version": True,
            "kind": "committed",
            "source_name": "v1-" + "a" * 32 + ".json",
            "envelope_sha256": "b" * 64,
            "digest_complete": True,
            "envelope_bytes": 1,
            "recorded_at_unix_ms": 1,
            "reason": None,
        }
        with self.assertRaises(queue.InvalidStateError):
            queue._parse_receipt(receipt)
        with self.assertRaises(queue.InvalidStateError):
            queue._require_counter(True)

    def test_json_parser_normalizes_huge_integer_and_depth_failures(self) -> None:
        hostile_payloads = (
            b'{"schema_version":' + b"9" * 5_000 + b"}",
            b'{"value":' + b"[" * 10_000 + b"0" + b"]" * 10_000 + b"}",
        )

        for payload in hostile_payloads:
            with self.subTest(payload_bytes=len(payload)):
                with self.assertRaises(queue.InvalidStateError) as raised:
                    queue._parse_canonical_object(payload)
                self.assertEqual(str(raised.exception), "state is invalid JSON")

    def test_producer_accounting_is_canonical_and_saturating(self) -> None:
        self.assertTrue(
            queue.increment_producer_accounting("publication_failure", paths=self.paths)
        )
        observed = queue.read_producer_accounting(self.paths)
        self.assertIsNotNone(observed)
        assert observed is not None
        self.assertEqual(observed.publication_failure, 1)
        raw = self.paths.producer_accounting_path.read_bytes()
        self.assertEqual(raw, queue._canonical_json_bytes(queue._accounting_object(observed), maximum=4096))
        saturated = queue.replace(
            observed,
            publication_failure=queue.COUNTER_MAX,
        )
        root_fd = queue._open_telemetry_root(self.paths, create=False)
        try:
            queue._write_fixed_json_at(
                root_fd,
                final_name="producer-accounting-v1.json",
                temporary_name=".producer-accounting-v1.tmp",
                payload=queue._canonical_json_bytes(
                    queue._accounting_object(saturated), maximum=4096
                ),
                maximum=4096,
            )
        finally:
            os.close(root_fd)
        self.assertTrue(
            queue.increment_producer_accounting("publication_failure", paths=self.paths)
        )
        after = queue.read_producer_accounting(self.paths)
        assert after is not None
        self.assertEqual(after.publication_failure, queue.COUNTER_MAX)
        self.assertTrue(after.accounting_incomplete)

    def test_malformed_producer_accounting_is_left_byte_unchanged(self) -> None:
        self.publish()
        malformed = b'{"schema_version":1,"schema_version":1}'
        self.paths.producer_accounting_path.write_bytes(malformed)
        self.paths.producer_accounting_path.chmod(0o600)
        self.assertFalse(
            queue.increment_producer_accounting("queue_full", paths=self.paths)
        )
        self.assertEqual(self.paths.producer_accounting_path.read_bytes(), malformed)

    def test_writer_state_round_trip_and_receipt_reconciliation_are_idempotent(self) -> None:
        result = self.publish("state")
        source_name = str(result.source_name)
        queue.claim_ready_batch(self.paths)
        read = queue.read_claimed_envelope(self.paths, source_name)
        receipt = queue.TerminalReceipt(
            1,
            "rejected",
            source_name,
            read.envelope_sha256,
            True,
            read.envelope_bytes,
            456,
            "invalid_value",
        )
        queue.publish_terminal_receipt(self.paths, receipt)
        state = queue.WriterState(heartbeat_unix_ms=456, phase="draining")
        first = queue.reconcile_writer_receipts(state, paths=self.paths)
        second = queue.reconcile_writer_receipts(first, paths=self.paths)
        self.assertEqual(first.rejected, 1)
        self.assertEqual(second.rejected, 1)
        self.assertEqual(first.accounted_receipts, second.accounted_receipts)
        self.assertTrue(queue.write_writer_state(second, paths=self.paths))
        self.assertEqual(queue.read_writer_state(self.paths), second)

    def test_safe_link_and_unlink_enforce_the_governed_link_window(self) -> None:
        self.publish()
        root_fd = queue.open_verified_directory(self.paths.directory)
        scratch_fd = queue.open_private_directory_at(
            root_fd,
            "database-init-v1",
            create=True,
        )
        try:
            descriptor = queue.open_private_file_at(
                scratch_fd,
                "telemetry.duckdb",
                flags=os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            )
            os.close(descriptor)
            queue.safe_link_at(
                scratch_fd,
                "telemetry.duckdb",
                root_fd,
                "telemetry.duckdb",
            )
            scratch_stat = queue.stat_private_entry_at(
                scratch_fd,
                "telemetry.duckdb",
                kind="file",
                allowed_nlinks=(2,),
            )
            final_stat = queue.stat_private_entry_at(
                root_fd,
                "telemetry.duckdb",
                kind="file",
                allowed_nlinks=(2,),
            )
            self.assertEqual(
                (scratch_stat.st_dev, scratch_stat.st_ino),
                (final_stat.st_dev, final_stat.st_ino),
            )
            queue.safe_unlink_at(
                scratch_fd,
                "telemetry.duckdb",
                allowed_nlinks=(2,),
            )
            queue.stat_private_entry_at(
                root_fd,
                "telemetry.duckdb",
                kind="file",
                allowed_nlinks=(1,),
            )
        finally:
            os.close(scratch_fd)
            os.close(root_fd)

    def test_writer_start_uses_exact_command_empty_environment_and_fresh_lease(self) -> None:
        self.publish()
        process = Mock()
        with patch.object(queue.subprocess, "Popen", return_value=process) as popen:
            started = queue.request_writer_start(paths=self.paths)
            suppressed = queue.request_writer_start(paths=self.paths)

        self.assertTrue(started.started)
        self.assertFalse(started.suppressed)
        self.assertFalse(suppressed.started)
        self.assertTrue(suppressed.suppressed)
        self.assertEqual(suppressed.reason, "start_lease")
        self.assertEqual(popen.call_count, 1)
        args, kwargs = popen.call_args
        self.assertEqual(
            args[0],
            [
                os.path.abspath(queue.sys.executable),
                "-I",
                "-X",
                "utf8",
                "-m",
                "buoy_search.telemetry_writer",
            ],
        )
        self.assertEqual(kwargs["cwd"], str(self.paths.directory))
        self.assertEqual(kwargs["env"], {})
        self.assertIs(kwargs["stdin"], queue.subprocess.DEVNULL)
        self.assertIs(kwargs["stdout"], queue.subprocess.DEVNULL)
        self.assertIs(kwargs["stderr"], queue.subprocess.DEVNULL)
        self.assertTrue(kwargs["close_fds"])
        self.assertTrue(kwargs["start_new_session"])
        self.assertFalse(kwargs["shell"])
        lease = queue.read_writer_start_lease(self.paths)
        self.assertIsNotNone(lease)

    def test_huge_integer_writer_state_does_not_suppress_start(self) -> None:
        self.publish()
        self.paths.writer_state_path.write_bytes(
            b'{"schema_version":' + b"9" * 5_000 + b"}"
        )
        self.paths.writer_state_path.chmod(0o600)

        with patch.object(queue.subprocess, "Popen", return_value=Mock()) as popen:
            started = queue.request_writer_start(paths=self.paths)

        self.assertTrue(started.started)
        self.assertEqual(started.reason, "started")
        popen.assert_called_once()

    def test_semantically_invalid_start_lease_is_atomically_replaced(self) -> None:
        self.publish()
        self.paths.writer_start_path.write_bytes(b"{}")
        self.paths.writer_start_path.chmod(0o600)

        with patch.object(queue.subprocess, "Popen", return_value=Mock()) as popen:
            started = queue.request_writer_start(paths=self.paths)
            suppressed = queue.request_writer_start(paths=self.paths)

        self.assertTrue(started.started)
        self.assertEqual(started.reason, "started")
        self.assertTrue(suppressed.suppressed)
        self.assertEqual(suppressed.reason, "start_lease")
        popen.assert_called_once()
        self.assertNotEqual(self.paths.writer_start_path.read_bytes(), b"{}")
        self.assertIsNotNone(queue.read_writer_start_lease(self.paths))

    def test_detached_writer_start_suppresses_only_expected_resource_warning(self) -> None:
        self.publish()

        class DetachedProcess:
            def __del__(self) -> None:
                warnings.warn(
                    "subprocess is still running",
                    ResourceWarning,
                    stacklevel=1,
                )

        with warnings.catch_warnings(record=True) as observed:
            warnings.simplefilter("always", ResourceWarning)
            with patch.object(
                queue.subprocess,
                "Popen",
                side_effect=lambda *_args, **_kwargs: DetachedProcess(),
            ):
                started = queue.request_writer_start(paths=self.paths)

        self.assertTrue(started.started)
        self.assertEqual(observed, [])

    def test_fresh_writer_state_suppresses_spawn_but_stopped_never_does(self) -> None:
        self.publish()
        now = queue._time_unix_ms()
        self.assertTrue(
            queue.write_writer_state(
                queue.WriterState(phase="draining", heartbeat_unix_ms=now),
                paths=self.paths,
            )
        )
        with patch.object(queue.subprocess, "Popen") as popen:
            active = queue.request_writer_start(paths=self.paths)
        self.assertTrue(active.suppressed)
        self.assertEqual(active.reason, "active_writer")
        popen.assert_not_called()

        self.assertTrue(
            queue.write_writer_state(
                queue.WriterState(phase="stopped", heartbeat_unix_ms=now),
                paths=self.paths,
            )
        )
        with patch.object(queue.subprocess, "Popen") as popen:
            stopped = queue.request_writer_start(paths=self.paths)
        self.assertTrue(stopped.started)
        popen.assert_called_once()

    def test_spawn_failure_keeps_published_envelope_and_accounts_lower_bound(self) -> None:
        result = self.publish("still-pending")
        with patch.object(queue.subprocess, "Popen", side_effect=OSError("hidden")):
            started = queue.request_writer_start(paths=self.paths)
        self.assertFalse(started.started)
        self.assertEqual(started.reason, "writer_start_failure")
        self.assertTrue(
            (self.paths.ready_directory / str(result.source_name)).is_file()
        )
        accounting = queue.read_producer_accounting(self.paths)
        assert accounting is not None
        self.assertEqual(accounting.writer_start_failure, 1)

    def test_queue_lock_timeout_drops_newest_without_touching_existing(self) -> None:
        first = self.publish("first")
        observed_timeouts: list[int | None] = []

        @contextmanager
        def timeout_lock(*_args: object, **kwargs: object):
            observed_timeouts.append(kwargs.get("timeout_ms"))
            raise queue.QueueLockTimeout("busy")
            yield 0

        with patch.object(queue, "queue_lock", timeout_lock):
            second = queue.publish_envelope(self.payload("second"), paths=self.paths)
        self.assertFalse(second.published)
        self.assertEqual(second.reason, "queue_lock_timeout")
        self.assertEqual(observed_timeouts, [queue.PUBLICATION_LOCK_TIMEOUT_MS])
        self.assertEqual(
            (self.paths.ready_directory / str(first.source_name)).read_bytes(),
            self.payload("first"),
        )

    def test_status_capacity_full_includes_the_separate_temp_cap(self) -> None:
        self.publish("layout")
        temporary = self.paths.temp_directory / ("v1-" + "a" * 32 + ".part")
        temporary.write_bytes(b"x")
        temporary.chmod(0o600)

        with (
            patch.object(queue, "TEMP_MAX_ENTRIES", 1),
            patch.object(queue, "TEMP_MAX_BYTES", 1),
        ):
            snapshot = queue.scan_queue_read_only(self.paths)

        self.assertTrue(snapshot.capacity_full)

    def test_module_has_no_forbidden_runtime_imports(self) -> None:
        source = Path(queue.__file__).read_text(encoding="utf-8")
        modules: set[str] = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                modules.add(node.module)
        self.assertFalse(any(name == "duckdb" or name.startswith("duckdb.") for name in modules))
        self.assertFalse(
            any(name == "opentelemetry" or name.startswith("opentelemetry.") for name in modules)
        )
        self.assertNotIn("buoy_search.telemetry_writer", modules)
        self.assertNotIn("buoy_search.telemetry_store", modules)


if __name__ == "__main__":
    unittest.main()
