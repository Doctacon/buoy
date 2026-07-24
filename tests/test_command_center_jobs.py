from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import tempfile
from threading import Barrier, Event, Thread
import unittest
from unittest.mock import patch

from buoy_search.command_center_jobs import (
    ACTIVE_STATES,
    ALLOWED_TRANSITIONS,
    ActiveJobConflict,
    InvalidJobTransitionError,
    JobDurabilityError,
    JobIntegrityError,
    JobRequestSummary,
    MAX_EVENT_REPLAY_SIZE,
    MAX_JOB_LIST_OFFSET,
    PlanJobEvent,
    PlanJobRequest,
    PlanJobService,
    PlanJobStore,
    SafeJobError,
    ServiceOwnershipError,
)
from buoy_search.chunker import process_corpus
from buoy_search.crawler import CrawlExecution, CrawlOptions
from buoy_search.github_repo import GitHubRepoMetadata
from buoy_search.planning_service import PlanProgress, PlanningService


JOB_IDS = [f"planjob_{index:032x}" for index in range(1, 30)]


def create_job(store: PlanJobStore, job_id: str = JOB_IDS[0]):
    return store.create(
        job_id=job_id,
        source_kind="website",
        source_url="https://example.com/docs?token=must-not-persist#fragment",
        namespace="docs-v1",
        artifact_path=f"command-center/plans/{job_id}",
        request_summary=JobRequestSummary(3, 10, "docs-v1", 1, 1),
    )


def _write_offline_page(pages_dir: Path) -> None:
    pages_dir.mkdir(parents=True, exist_ok=True)
    (pages_dir / "page.md").write_text(
        "\n".join(
            (
                "---",
                'url: "https://example.com/docs/page"',
                'title: "Offline Page"',
                'status: "200"',
                'content_type: "text/html"',
                'source_hash: "offline-source-hash"',
                'crawl_timestamp: "2026-07-23T00:00:00+00:00"',
                'fetcher: "test"',
                "---",
                "",
                "# Offline managed planning",
                "",
                "Portable staging content.",
                "",
            )
        ),
        encoding="utf-8",
    )


def _offline_crawl_summary(
    options: CrawlOptions, *, source_kind: str
) -> dict[str, object]:
    return {
        "command": "crawl",
        "dry_run": True,
        "credentials_required": False,
        "source_credentials_required": False,
        "source_api_calls_occurred": False,
        "turbopuffer_api_calls": False,
        "api_calls_occurred": False,
        "source_kind": source_kind,
        "base_url": options.base_url,
        "allowed_host": "example.com",
        "namespace_candidate": f"{source_kind}-offline-v1",
        "crawl_strategy": options.crawl_strategy,
        "requested_crawl_strategy": options.crawl_strategy,
        "docs_version_policy": options.docs_version_policy,
        "language_policy": options.language_policy,
        "out_dir": str(options.out_dir),
        "pages_dir": str(options.out_dir / "pages"),
        "max_pages": options.max_pages,
        "max_chunks": options.max_chunks,
        "include_paths": list(options.include_paths),
        "exclude_paths": list(options.exclude_paths),
        "strip_trailing_slash": options.strip_trailing_slash,
        "css_selector": options.css_selector,
        "target_tokens": options.target_tokens,
        "overlap_sentences": options.overlap_sentences,
        "pages_scraped": 1,
        "requests_count": 1,
        "files_discovered": 1,
        "files_seen": 1,
        "files_error": 0,
        "chunks_generated": 1,
        "limit_reached": False,
        "sample_chunks": [],
        "errors": [],
    }


class SuccessfulPlanningService:
    def __init__(self) -> None:
        self.calls = []

    def plan(self, request, *, progress_callback=None):  # noqa: ANN001
        self.calls.append(request)
        if progress_callback is not None:
            progress_callback(
                PlanProgress(
                    "crawl\nprovider-secret",
                    "https://example.com/page?token=provider-secret pages=2 chunks=4",
                    {"pages": 2, "chunks": 4, "token": 999, "negative": -1},
                )
            )
            progress_callback(PlanProgress("artifacts", "raw provider artifact", {}))
        return SimpleNamespace(
            summary={"plan_id": "plan_verified", "namespace": "docs-v1"},
            out_dir=request.out_dir,
        )


class BlockingPlanningService:
    def __init__(self) -> None:
        self.started = Event()
        self.release = Event()
        self.calls = []

    def plan(self, request, *, progress_callback=None):  # noqa: ANN001
        self.calls.append(request)
        if progress_callback is not None:
            progress_callback(PlanProgress("discovery", "raw discovery output", {"files": 1}))
        self.started.set()
        if not self.release.wait(5):
            raise RuntimeError("test worker timed out")
        if progress_callback is not None:
            progress_callback(PlanProgress("write", "raw write output", {"pages": 2}))
        return SimpleNamespace(
            summary={"plan_id": "plan_blocking", "namespace": "docs-v1"},
            out_dir=request.out_dir,
        )


class CapturingExecutor:
    def __init__(self) -> None:
        self.future: Future[object] | None = None
        self.call = None

    def submit(self, function, *args):  # noqa: ANN001
        self.future = Future()
        self.call = (function, args)
        return self.future

    def run(self) -> None:
        assert self.future is not None and self.call is not None
        function, args = self.call
        try:
            self.future.set_result(function(*args))
        except BaseException as exc:
            self.future.set_exception(exc)


class PlanJobStoreTests(unittest.TestCase):
    def test_every_allowed_transition_and_terminal_immutability(self) -> None:
        self.assertEqual(
            ALLOWED_TRANSITIONS,
            {
                "queued": frozenset({"running", "failed"}),
                "running": frozenset({"succeeded", "failed", "interrupted"}),
                "succeeded": frozenset(),
                "failed": frozenset(),
                "interrupted": frozenset(),
            },
        )
        cases = (
            ("running", None),
            ("failed", SafeJobError("request_failed", "Request failed safely.")),
        )
        for final_state, error in cases:
            with self.subTest(state=f"queued->{final_state}"), tempfile.TemporaryDirectory() as tmp:
                store = PlanJobStore(Path(tmp).resolve())
                create_job(store)
                transitioned = store.transition(JOB_IDS[0], final_state, error=error)
                self.assertEqual(transitioned.state, final_state)

        running_cases = (
            ("succeeded", None),
            ("failed", SafeJobError("planning_failed", "Planning failed safely.")),
            ("interrupted", None),
        )
        for final_state, error in running_cases:
            with self.subTest(state=f"running->{final_state}"), tempfile.TemporaryDirectory() as tmp:
                store = PlanJobStore(Path(tmp).resolve())
                create_job(store)
                store.transition(JOB_IDS[0], "running")
                transitioned = store.transition(
                    JOB_IDS[0],
                    final_state,
                    plan_id="plan_verified" if final_state == "succeeded" else None,
                    error=error,
                )
                self.assertEqual(transitioned.state, final_state)
                self.assertIsNotNone(transitioned.completed_at)
                for candidate in ALLOWED_TRANSITIONS:
                    with self.assertRaises(InvalidJobTransitionError):
                        store.transition(JOB_IDS[0], candidate)  # type: ignore[arg-type]

    def test_invalid_transitions_and_result_invariants_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = PlanJobStore(Path(tmp).resolve())
            create_job(store)
            for state in ("queued", "succeeded", "interrupted"):
                with self.subTest(state=state), self.assertRaises(InvalidJobTransitionError):
                    store.transition(JOB_IDS[0], state)  # type: ignore[arg-type]
            store.transition(JOB_IDS[0], "running")
            with self.assertRaises(InvalidJobTransitionError):
                store.transition(JOB_IDS[0], "succeeded")
            with self.assertRaises(InvalidJobTransitionError):
                store.transition(
                    JOB_IDS[0],
                    "failed",
                    plan_id="must-not-survive",
                    error=SafeJobError("planning_failed", "Failed."),
                )

    def test_atomic_records_append_only_events_and_safe_relative_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            store = PlanJobStore(root)
            job = create_job(store)
            events_path = store.jobs_root / f"{job.job_id}.events.jsonl"
            initial = events_path.read_bytes()
            with patch("buoy_search.command_center_jobs.os.replace", wraps=__import__("os").replace) as replace_mock:
                store.transition(job.job_id, "running")
                store.record_progress(
                    job.job_id,
                    PlanProgress("crawl", "raw URL https://example.com/?secret=yes", {"pages": 1}),
                )
                self.assertGreaterEqual(replace_mock.call_count, 2)
            self.assertTrue(events_path.read_bytes().startswith(initial))
            record_path = store.jobs_root / f"{job.job_id}.json"
            payload = json.loads(record_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["artifact_path"], f"command-center/plans/{job.job_id}")
            self.assertFalse(Path(payload["artifact_path"]).is_absolute())
            self.assertEqual(payload["source_url"], "https://example.com/docs")
            serialized = record_path.read_text(encoding="utf-8") + events_path.read_text(encoding="utf-8")
            self.assertNotIn("secret", serialized.casefold())
            self.assertEqual(list(store.jobs_root.glob("*.tmp")), [])
            self.assertEqual(record_path.stat().st_mode & 0o777, 0o600)
            sequences = [event.sequence for event in store.events_after(job.job_id)]
            self.assertEqual(sequences, list(range(1, len(sequences) + 1)))

    def test_event_replay_scans_incrementally_and_returns_a_1000_event_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = PlanJobStore(Path(tmp).resolve())
            job = create_job(store)
            events = [
                PlanJobEvent(
                    sequence,
                    job.updated_at,
                    "queued",
                    "Plan job queued.",
                    {},
                )
                for sequence in range(1, MAX_EVENT_REPLAY_SIZE + 2)
            ]
            (store.jobs_root / f"{job.job_id}.events.jsonl").write_text(
                "".join(
                    json.dumps(event.to_dict(), sort_keys=True, separators=(",", ":")) + "\n"
                    for event in events
                ),
                encoding="utf-8",
            )
            store._atomic_write_record(  # type: ignore[attr-defined]
                replace(job, event_sequence=len(events))
            )

            replay = store.events_after(job.job_id)
            tail = store.events_after(job.job_id, MAX_EVENT_REPLAY_SIZE)

        self.assertEqual(len(replay), MAX_EVENT_REPLAY_SIZE)
        self.assertEqual((replay[0].sequence, replay[-1].sequence), (1, 1_000))
        self.assertEqual([event.sequence for event in tail], [1_001])

    def test_list_window_many_jobs_decodes_and_reconciles_only_the_mtime_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = PlanJobStore(Path(tmp).resolve())
            created = []
            for job_id in JOB_IDS[:20]:
                job = create_job(store, job_id)
                created.append(job)
                store.transition(
                    job.job_id,
                    "failed",
                    error=SafeJobError("failed", "Failed safely."),
                )
            base_mtime = 2_000_000_000_000_000_000
            for index, job in enumerate(created):
                mtime = base_mtime - index
                os.utime(
                    store.jobs_root / f"{job.job_id}.json",
                    ns=(mtime, mtime),
                )
            tie_mtime = base_mtime - 3
            for job in created[3:5]:
                os.utime(
                    store.jobs_root / f"{job.job_id}.json",
                    ns=(tie_mtime, tie_mtime),
                )

            with patch.object(
                store,
                "_read_record",
                wraps=store._read_record,  # type: ignore[attr-defined]
            ) as record_reads, patch.object(
                store,
                "_read_event_tail",
                wraps=store._read_event_tail,  # type: ignore[attr-defined]
            ) as tail_reads, patch.object(
                store,
                "_scan_event_data",
                wraps=store._scan_event_data,  # type: ignore[attr-defined]
            ) as full_scans:
                first, total = store.list_window(offset=0, limit=1)

            tied, tied_total = store.list_window(offset=3, limit=2)
            retained, retained_total = store._select_record_window(  # type: ignore[attr-defined]
                offset=3, limit=2
            )
            all_jobs = store.list()

        self.assertEqual(total, 20)
        self.assertEqual(tied_total, 20)
        self.assertEqual(retained_total, 20)
        self.assertEqual(len(retained), 2)
        self.assertEqual([job.job_id for job in first], [created[0].job_id])
        self.assertEqual(first[0].created_at, created[0].created_at)
        self.assertEqual(
            [job.job_id for job in tied],
            [created[4].job_id, created[3].job_id],
        )
        self.assertEqual(
            [job.job_id for job in all_jobs[3:5]],
            [created[4].job_id, created[3].job_id],
        )
        self.assertEqual(record_reads.call_count, 1)
        self.assertEqual(tail_reads.call_count, 1)
        self.assertEqual(full_scans.call_count, 0)

        with tempfile.TemporaryDirectory() as tmp:
            store = PlanJobStore(Path(tmp).resolve())
            with self.assertRaises(ValueError):
                store.list_window(offset=MAX_JOB_LIST_OFFSET + 1, limit=1)
            self.assertEqual(store.list_window(offset=MAX_JOB_LIST_OFFSET, limit=1), ([], 0))

    def test_restart_interrupts_queued_and_running_without_execution(self) -> None:
        for initial_state in ("queued", "running"):
            with self.subTest(state=initial_state), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                store = PlanJobStore(root / "state")
                create_job(store)
                if initial_state == "running":
                    store.transition(JOB_IDS[0], "running")
                fake = SuccessfulPlanningService()
                service = PlanJobService(
                    state_root=root / "state",
                    artifacts_root=root / "artifacts",
                    planning_service=fake,  # type: ignore[arg-type]
                )
                try:
                    recovered = service.get(JOB_IDS[0])
                    self.assertEqual(recovered.state, "interrupted")
                    self.assertEqual(recovered.error.code, "job_interrupted")  # type: ignore[union-attr]
                    self.assertIsNone(recovered.plan_id)
                    self.assertEqual(service.events_after(JOB_IDS[0])[-1].stage, "interrupted")
                    self.assertEqual(fake.calls, [])
                finally:
                    service.shutdown()

    def test_malformed_or_secret_bearing_record_fails_integrity_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = PlanJobStore(Path(tmp).resolve())
            job = create_job(store)
            path = store.jobs_root / f"{job.job_id}.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["csrf_token"] = "secret"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(JobIntegrityError):
                store.get(job.job_id)

    def test_store_rejects_malformed_persisted_http_authorities_before_record_write(self) -> None:
        malformed_urls = (
            "https://example.com:bad/docs",
            "https://example.com:99999/docs",
            "https://example.com:0/docs",
            "https://example.com:/docs",
            "https://:443/docs",
            "https://exa mple.com/docs",
            " https://example.com/docs",
            "https://-invalid.example/docs",
            "https://999.999.999.999/docs",
        )
        with tempfile.TemporaryDirectory() as tmp:
            store = PlanJobStore(Path(tmp).resolve())
            for index, source_url in enumerate(malformed_urls, start=1):
                with self.subTest(source_url=source_url), self.assertRaises(JobIntegrityError):
                    store.create(
                        job_id=JOB_IDS[index],
                        source_kind="website",
                        source_url=source_url,
                        namespace=None,
                        artifact_path=f"command-center/plans/{JOB_IDS[index]}",
                        request_summary=JobRequestSummary(None, None, None, 0, 0),
                    )
            self.assertEqual(list(store.jobs_root.glob("*.json")), [])
            self.assertEqual(list(store.jobs_root.glob("*.events.jsonl")), [])

    def test_store_rejects_second_active_job_and_unsafe_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = PlanJobStore(Path(tmp).resolve())
            first = create_job(store)
            with self.assertRaises(ActiveJobConflict) as conflict:
                create_job(store, JOB_IDS[1])
            self.assertEqual(conflict.exception.active_job_id, first.job_id)
            with self.assertRaises(JobIntegrityError):
                store.create(
                    job_id=JOB_IDS[2],
                    source_kind="website",
                    source_url="https://example.com/",
                    namespace=None,
                    artifact_path="../escape",
                    request_summary=JobRequestSummary(None, None, None, 0, 0),
                )

    def test_kill_boundaries_reconcile_and_leave_active_jobs_interruptible(self) -> None:
        script = r'''
import os
from pathlib import Path
import sys
from buoy_search.command_center_jobs import JobRequestSummary, PlanJobStore, SafeJobError
from buoy_search.planning_service import PlanProgress
root, job_id, operation, point = sys.argv[1:]
def crash(candidate):
    if candidate == point:
        os._exit(86)
store = PlanJobStore(Path(root), fault_injector=crash)
if operation == "create":
    store.create(job_id=job_id, source_kind="website", source_url="https://example.com/docs", namespace=None, artifact_path=f"command-center/plans/{job_id}", request_summary=JobRequestSummary(None, None, None, 0, 0))
elif operation == "progress":
    store.record_progress(job_id, PlanProgress("crawl", "raw", {"pages": 1}))
elif operation == "terminal":
    store.transition(job_id, "succeeded", plan_id="plan_verified")
elif operation == "restart":
    store.interrupt_active_jobs()
'''
        points = (
            "record-temp-fsync",
            "record-replace",
            "record-directory-fsync",
            "event-write",
            "event-fsync",
        )
        for operation in ("create", "progress", "terminal", "restart"):
            for point in points:
                with self.subTest(operation=operation, point=point), tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp).resolve() / "state"
                    if operation != "create":
                        setup = PlanJobStore(root)
                        create_job(setup)
                        if operation in {"progress", "terminal"}:
                            setup.transition(JOB_IDS[0], "running")
                    completed = subprocess.run(
                        [sys.executable, "-c", script, str(root), JOB_IDS[0], operation, point],
                        env={**os.environ, "PYTHONPATH": "src"},
                        check=False,
                        capture_output=True,
                        text=True,
                    )
                    self.assertEqual(completed.returncode, 86, completed.stderr)
                    reopened = PlanJobStore(root)
                    jobs = reopened.list()
                    self.assertLessEqual(len(jobs), 1)
                    reopened.interrupt_active_jobs()
                    self.assertFalse(
                        [job for job in reopened.list() if job.state in ACTIVE_STATES]
                    )
                    if jobs:
                        self.assertEqual(
                            [event.sequence for event in reopened.events_after(JOB_IDS[0])],
                            list(range(1, reopened.get(JOB_IDS[0]).event_sequence + 1)),
                        )

    def test_two_store_instances_serialize_active_check_and_create(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            stores = (PlanJobStore(root), PlanJobStore(root))
            barrier = Barrier(2)
            created = []
            errors = []

            def run(store: PlanJobStore, job_id: str) -> None:
                barrier.wait()
                try:
                    created.append(create_job(store, job_id))
                except Exception as exc:  # asserted below
                    errors.append(exc)

            threads = [
                Thread(target=run, args=(stores[0], JOB_IDS[0])),
                Thread(target=run, args=(stores[1], JOB_IDS[1])),
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(5)
                self.assertFalse(thread.is_alive())
            self.assertEqual(len(created), 1)
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], ActiveJobConflict)
            self.assertEqual(len(PlanJobStore(root).list()), 1)

    def test_overlapping_cross_store_reconcile_and_writer_share_mutation_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            writer_store = PlanJobStore(root)
            reader_store = PlanJobStore(root)
            create_job(writer_store)
            writer_store.transition(JOB_IDS[0], "running")
            record_installed = Event()
            reader_started = Event()
            errors: list[BaseException] = []
            observed = []
            append_event = writer_store._append_event

            def blocking_append(job_id, event):  # noqa: ANN001
                if event.sequence == 3:
                    record_installed.set()
                    if not reader_started.wait(5):
                        raise RuntimeError("reader did not overlap writer")
                append_event(job_id, event)

            def write_progress() -> None:
                try:
                    with patch.object(writer_store, "_append_event", side_effect=blocking_append):
                        writer_store.record_progress(
                            JOB_IDS[0], PlanProgress("crawl", "raw", {"pages": 1})
                        )
                except BaseException as exc:
                    errors.append(exc)

            def reconcile_read() -> None:
                if not record_installed.wait(5):
                    errors.append(RuntimeError("writer did not install record"))
                    return
                reader_started.set()
                try:
                    observed.append(reader_store.get(JOB_IDS[0]))
                except BaseException as exc:
                    errors.append(exc)

            threads = [Thread(target=write_progress), Thread(target=reconcile_read)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(5)
                self.assertFalse(thread.is_alive())

            self.assertEqual(errors, [])
            self.assertEqual(observed[0].event_sequence, 3)
            reopened = PlanJobStore(root)
            self.assertEqual(
                [event.sequence for event in reopened.events_after(JOB_IDS[0])],
                [1, 2, 3],
            )

    def test_post_construction_state_ancestor_replacement_blocks_reads_and_mutations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            original_parent = root / "original" / "nested"
            substitute_parent = root / "substitute" / "nested"
            store = PlanJobStore(original_parent / "state")
            original_job = create_job(store)
            substitute = PlanJobStore(substitute_parent / "state")
            substitute_job = create_job(substitute, JOB_IDS[1])
            before = tuple(job.job_id for job in substitute.list())

            moved = root / "moved-original"
            (root / "original").rename(moved)
            (root / "substitute").rename(root / "original")

            with self.assertRaisesRegex(JobIntegrityError, "identity changed"):
                store.list()
            with self.assertRaisesRegex(JobIntegrityError, "identity changed"):
                create_job(store, JOB_IDS[2])
            reopened_substitute = PlanJobStore(root / "original/nested/state")
            self.assertEqual(tuple(job.job_id for job in reopened_substitute.list()), before)
            self.assertEqual(original_job.job_id, JOB_IDS[0])
            self.assertEqual(substitute_job.job_id, JOB_IDS[1])
            self.assertFalse(
                (root / "original/nested/state/command-center/jobs" / f"{JOB_IDS[2]}.json").exists()
            )

    def test_event_symlink_and_hardlink_reads_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = PlanJobStore(Path(tmp).resolve())
            job = create_job(store)
            events = store.jobs_root / f"{job.job_id}.events.jsonl"
            original = events.read_bytes()
            events.unlink()
            target = store.jobs_root / "outside-events"
            target.write_bytes(original)
            events.symlink_to(target)
            with self.assertRaises(JobIntegrityError):
                store.events_after(job.job_id)
            events.unlink()
            os.link(target, events)
            with self.assertRaisesRegex(JobIntegrityError, "private regular file"):
                store.events_after(job.job_id)

    def test_directory_sync_failure_is_propagated_and_recoverable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            store = PlanJobStore(root)
            with patch(
                "buoy_search.command_center_jobs._fsync_directory",
                side_effect=OSError("injected directory sync failure"),
            ):
                with self.assertRaises(JobDurabilityError):
                    create_job(store)
            reopened = PlanJobStore(root)
            self.assertEqual(reopened.get(JOB_IDS[0]).state, "queued")
            self.assertEqual(reopened.interrupt_active_jobs()[0].state, "interrupted")

    def test_event_sync_failure_propagates_and_reopen_repairs_committed_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            enabled = False

            def fail_event_sync(point: str) -> None:
                if enabled and point == "event-fsync":
                    raise OSError("injected event sync failure")

            store = PlanJobStore(root, fault_injector=fail_event_sync)
            create_job(store)
            store.transition(JOB_IDS[0], "running")
            enabled = True
            with self.assertRaises(JobDurabilityError):
                store.record_progress(
                    JOB_IDS[0], PlanProgress("crawl", "raw", {"pages": 1})
                )
            reopened = PlanJobStore(root)
            self.assertEqual(reopened.get(JOB_IDS[0]).latest_progress.stage, "crawl")
            self.assertEqual(reopened.interrupt_active_jobs()[0].state, "interrupted")

    def test_list_window_metadata_and_selected_identity_tampering_fail_closed(self) -> None:
        for tamper in ("symlink", "hardlink", "public-mode"):
            with self.subTest(tamper=tamper), tempfile.TemporaryDirectory() as tmp:
                store = PlanJobStore(Path(tmp).resolve())
                job = create_job(store)
                store.transition(
                    job.job_id,
                    "failed",
                    error=SafeJobError("failed", "Failed."),
                )
                record = store.jobs_root / f"{job.job_id}.json"
                target = store.jobs_root / "target"
                target.write_bytes(record.read_bytes())
                target.chmod(0o600)
                if tamper == "symlink":
                    record.unlink()
                    record.symlink_to(target)
                elif tamper == "hardlink":
                    record.unlink()
                    os.link(target, record)
                else:
                    record.chmod(0o644)
                with self.assertRaisesRegex(
                    JobIntegrityError, "private regular file"
                ):
                    store.list_window(offset=0, limit=1)

        with tempfile.TemporaryDirectory() as tmp:
            store = PlanJobStore(Path(tmp).resolve())
            job = create_job(store)
            store.transition(
                job.job_id,
                "failed",
                error=SafeJobError("failed", "Failed."),
            )
            record = store.jobs_root / f"{job.job_id}.json"
            original_select = store._select_record_window  # type: ignore[attr-defined]

            def replace_after_selection(*, offset: int, limit: int):
                selected, total = original_select(offset=offset, limit=limit)
                replacement = store.jobs_root / "replacement"
                replacement.write_bytes(record.read_bytes())
                replacement.chmod(0o600)
                os.replace(replacement, record)
                return selected, total

            with patch.object(
                store,
                "_select_record_window",
                side_effect=replace_after_selection,
            ), self.assertRaisesRegex(JobIntegrityError, "after list selection"):
                store.list_window(offset=0, limit=1)

    def test_record_identity_symlink_hardlink_and_replacement_tampering_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            store = PlanJobStore(root)
            first = create_job(store)
            store.transition(first.job_id, "failed", error=SafeJobError("failed", "Failed."))
            second = create_job(store, JOB_IDS[1])
            first_path = store.jobs_root / f"{first.job_id}.json"
            second_path = store.jobs_root / f"{second.job_id}.json"

            original_second = second_path.read_bytes()
            second_path.write_bytes(first_path.read_bytes())
            with self.assertRaisesRegex(JobIntegrityError, "filename"):
                store.get(second.job_id)
            second_path.write_bytes(original_second)

            replacement = store.jobs_root / "replacement.json"
            replacement.write_bytes(original_second)
            real_read = os.read
            raced = False

            def replace_during_read(fd: int, size: int) -> bytes:
                nonlocal raced
                data = real_read(fd, size)
                if data and not raced:
                    raced = True
                    os.replace(replacement, second_path)
                return data

            with patch("buoy_search.command_center_jobs.os.read", side_effect=replace_during_read):
                with self.assertRaisesRegex(JobIntegrityError, "replaced"):
                    store.get(second.job_id)

            second_path.unlink()
            second_path.symlink_to(first_path)
            with self.assertRaises(JobIntegrityError):
                store.get(second.job_id)
            second_path.unlink()
            os.link(first_path, second_path)
            with self.assertRaisesRegex(JobIntegrityError, "private regular file"):
                store.get(second.job_id)


class PlanJobServiceTests(unittest.TestCase):
    def test_malformed_http_authorities_fail_before_job_output_record_or_executor(self) -> None:
        malformed_urls = (
            "https://example.com:bad/docs",
            "https://example.com:99999/docs",
            "https://example.com:0/docs",
            "https://example.com:/docs",
            "https://:443/docs",
            "https://exa mple.com/docs",
            " https://example.com/docs",
            "https://example..com/docs",
            "https://999.999.999.999/docs",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            executor = CapturingExecutor()
            service = PlanJobService(
                state_root=root / "state",
                artifacts_root=root / "artifacts",
                planning_service=SuccessfulPlanningService(),  # type: ignore[arg-type]
                executor=executor,  # type: ignore[arg-type]
                job_id_factory=lambda: JOB_IDS[0],
            )
            try:
                for source_url in malformed_urls:
                    with self.subTest(source_url=source_url), self.assertRaises(ValueError):
                        service.start(PlanJobRequest(source_url))
                self.assertIsNone(executor.call)
                self.assertEqual(list(service.store.jobs_root.glob("*.json")), [])
                self.assertEqual(
                    list((root / "artifacts/command-center/plans").iterdir()), []
                )
            finally:
                service.shutdown()

    def test_offline_managed_website_succeeds_through_private_staging(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            write_dirs: list[Path] = []

            def offline_crawl(_source: object, options: CrawlOptions) -> CrawlExecution:
                write_dirs.append(options.out_dir)
                _write_offline_page(options.out_dir / "pages")
                return CrawlExecution(
                    summary=_offline_crawl_summary(options, source_kind="website"),
                    indexing_plan=process_corpus(options.out_dir / "pages"),
                )

            service = PlanJobService(
                state_root=root / "state",
                artifacts_root=root / "artifacts",
                planning_service=PlanningService(crawl_runner=offline_crawl),
                job_id_factory=lambda: JOB_IDS[0],
            )
            try:
                job = service.start(PlanJobRequest("https://example.com/docs"))
                finished = service.wait(job.job_id, timeout=5)
                self.assertEqual(finished.state, "succeeded")
                final = root / "artifacts/command-center/plans" / job.job_id
                self.assertEqual(
                    {"plan.json", "manifest.json", "chunks.jsonl", "summary.json", "pages"},
                    {path.name for path in final.iterdir()},
                )
                self.assertEqual(len(write_dirs), 1)
                self.assertNotEqual(write_dirs[0], final)
                self.assertFalse(write_dirs[0].exists())
                persisted = "\n".join(
                    path.read_text(encoding="utf-8")
                    for path in final.rglob("*")
                    if path.is_file()
                )
                self.assertNotIn("buoy-managed-plan-", persisted)
                self.assertNotIn("/dev/fd/", persisted)
                self.assertNotIn("/proc/", persisted)
            finally:
                service.shutdown()

    def test_offline_managed_github_succeeds_and_excludes_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            remote = root / "remote"
            remote.mkdir()
            subprocess.run(
                ["git", "init", "-b", "main", str(remote)],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "-C", str(remote), "config", "user.email", "test@example.com"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(remote), "config", "user.name", "Test User"],
                check=True,
            )
            (remote / "README.md").write_text(
                "# Offline repository\n\nPortable Git staging content.\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "-C", str(remote), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(remote), "commit", "-m", "initial"],
                check=True,
                capture_output=True,
                text=True,
            )
            metadata = GitHubRepoMetadata(
                owner="owner",
                repo="repo",
                repo_full_name="owner/repo",
                repo_root_url="https://github.com/owner/repo",
                clone_url=str(remote),
                default_branch="main",
            )
            service = PlanJobService(
                state_root=root / "state",
                artifacts_root=root / "artifacts",
                planning_service=PlanningService(),
                job_id_factory=lambda: JOB_IDS[0],
            )
            try:
                with patch(
                    "buoy_search.github_repo.fetch_github_repo_metadata",
                    return_value=metadata,
                ):
                    job = service.start(PlanJobRequest("https://github.com/owner/repo"))
                    finished = service.wait(job.job_id, timeout=10)
                self.assertEqual(finished.state, "succeeded")
                final = root / "artifacts/command-center/plans" / job.job_id
                self.assertEqual(
                    {"plan.json", "manifest.json", "chunks.jsonl", "summary.json", "pages"},
                    {path.name for path in final.iterdir()},
                )
                self.assertFalse((final / "repo-checkout").exists())
                persisted = "\n".join(
                    path.read_text(encoding="utf-8")
                    for path in final.rglob("*")
                    if path.is_file()
                )
                self.assertNotIn("buoy-managed-plan-", persisted)
                self.assertNotIn("/dev/fd/", persisted)
                self.assertNotIn("/proc/", persisted)
            finally:
                service.shutdown()

    def test_success_integrates_shared_service_and_sanitizes_progress(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            fake = SuccessfulPlanningService()
            service = PlanJobService(
                state_root=root / "state",
                artifacts_root=root / "artifacts",
                planning_service=fake,  # type: ignore[arg-type]
                job_id_factory=lambda: JOB_IDS[0],
            )
            try:
                created = service.start(
                    PlanJobRequest(
                        "https://example.com/docs?access_token=must-not-persist#section",
                        max_pages_or_files=7,
                        max_chunks=11,
                        namespace="docs-v1",
                        include_paths=("/docs/**",),
                        exclude_paths=("/docs/old/**",),
                    )
                )
                finished = service.wait(created.job_id, timeout=5)
                self.assertEqual(finished.state, "succeeded")
                self.assertEqual(finished.plan_id, "plan_verified")
                self.assertIsNone(finished.error)
                self.assertEqual(
                    finished.artifact_path,
                    f"command-center/plans/{created.job_id}",
                )
                delegated = fake.calls[0]
                self.assertEqual(delegated.max_pages_or_files, 7)
                self.assertEqual(delegated.max_chunks, 11)
                self.assertEqual(delegated.originating_job_id, created.job_id)
                self.assertEqual(
                    delegated.out_dir,
                    root / "artifacts" / "command-center" / "plans" / created.job_id,
                )
                events = service.events_after(created.job_id)
                self.assertEqual(events[0].stage, "queued")
                self.assertEqual(events[1].stage, "validation")
                self.assertEqual(events[-1].stage, "succeeded")
                crawl = next(event for event in events if event.stage == "crawl")
                self.assertEqual(crawl.message, "Crawling public website content.")
                self.assertEqual(crawl.counts, {"pages": 2, "chunks": 4})
                serialized = "\n".join(
                    path.read_text(encoding="utf-8")
                    for path in service.store.jobs_root.iterdir()
                )
                self.assertNotIn("must-not-persist", serialized)
                self.assertNotIn("provider-secret", serialized)
                self.assertNotIn('"token"', serialized)
            finally:
                service.shutdown()

    def test_unverified_result_cannot_transition_to_success(self) -> None:
        class UnverifiedService:
            def plan(self, request, *, progress_callback=None):  # noqa: ANN001
                return SimpleNamespace(
                    summary={"namespace": "docs-v1"},
                    out_dir=request.out_dir,
                )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            service = PlanJobService(
                state_root=root / "state",
                artifacts_root=root / "artifacts",
                planning_service=UnverifiedService(),  # type: ignore[arg-type]
                job_id_factory=lambda: JOB_IDS[0],
            )
            try:
                job = service.start(
                    PlanJobRequest("https://example.com/docs", namespace="docs-v1")
                )
                failed = service.wait(job.job_id, timeout=5)
                self.assertEqual(failed.state, "failed")
                self.assertIsNone(failed.plan_id)
                self.assertEqual(service.events_after(job.job_id)[-1].stage, "failed")
            finally:
                service.shutdown()

    def test_failure_preserves_safe_record_without_plan_id_or_raw_exception(self) -> None:
        class FailingService:
            def plan(self, request, *, progress_callback=None):  # noqa: ANN001
                request.out_dir.mkdir(parents=True, exist_ok=True)
                (request.out_dir / "incomplete.txt").write_text("partial", encoding="utf-8")
                raise RuntimeError("RAW-SECRET provider exception /private/path")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            service = PlanJobService(
                state_root=root / "state",
                artifacts_root=root / "artifacts",
                planning_service=FailingService(),  # type: ignore[arg-type]
                job_id_factory=lambda: JOB_IDS[0],
            )
            try:
                with self.assertLogs("buoy_search.command_center_jobs", level="ERROR") as logs:
                    job = service.start(PlanJobRequest("https://example.com/docs"))
                    failed = service.wait(job.job_id, timeout=5)
                self.assertEqual(failed.state, "failed")
                self.assertEqual(failed.error.code, "planning_failed")  # type: ignore[union-attr]
                self.assertIn("RuntimeError", "\n".join(logs.output))
                self.assertNotIn("RAW-SECRET", "\n".join(logs.output))
                self.assertNotIn("/private/path", "\n".join(logs.output))
                self.assertIsNone(failed.plan_id)
                self.assertTrue(
                    (
                        root
                        / "artifacts"
                        / "command-center"
                        / "plans"
                        / job.job_id
                        / "incomplete.txt"
                    ).exists()
                )
                serialized = "\n".join(
                    path.read_text(encoding="utf-8")
                    for path in service.store.jobs_root.iterdir()
                )
                self.assertNotIn("RAW-SECRET", serialized)
                self.assertNotIn("/private/path", serialized)
            finally:
                service.shutdown()

    def test_one_active_concurrency_one_and_no_duplicate_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            fake = BlockingPlanningService()
            executor = ThreadPoolExecutor(max_workers=1)
            ids = iter(JOB_IDS)
            service = PlanJobService(
                state_root=root / "state",
                artifacts_root=root / "artifacts",
                planning_service=fake,  # type: ignore[arg-type]
                executor=executor,
                job_id_factory=lambda: next(ids),
            )
            try:
                first = service.start(PlanJobRequest("https://example.com/docs"))
                self.assertTrue(fake.started.wait(5))
                self.assertIn(service.get(first.job_id).state, ACTIVE_STATES)
                with self.assertRaises(ActiveJobConflict) as conflict:
                    service.start(PlanJobRequest("https://github.com/Doctacon/buoy"))
                self.assertEqual(conflict.exception.active_job_id, first.job_id)
                self.assertEqual(len(fake.calls), 1)
                fake.release.set()
                self.assertEqual(service.wait(first.job_id, timeout=5).state, "succeeded")
                second = service.start(PlanJobRequest("https://example.com/docs"))
                self.assertNotEqual(first.job_id, second.job_id)
                self.assertEqual(service.wait(second.job_id, timeout=5).state, "succeeded")
                self.assertEqual(len(fake.calls), 2)
                self.assertNotEqual(fake.calls[0].out_dir, fake.calls[1].out_dir)
            finally:
                fake.release.set()
                executor.shutdown(wait=True)
                service.shutdown()

    def test_retry_of_colliding_id_uses_a_new_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            fake = SuccessfulPlanningService()
            ids = iter((JOB_IDS[0], JOB_IDS[0], JOB_IDS[1]))
            service = PlanJobService(
                state_root=root / "state",
                artifacts_root=root / "artifacts",
                planning_service=fake,  # type: ignore[arg-type]
                job_id_factory=lambda: next(ids),
            )
            try:
                first = service.start(PlanJobRequest("https://example.com/docs"))
                service.wait(first.job_id, timeout=5)
                retried = service.start(PlanJobRequest("https://example.com/docs"))
                self.assertEqual(retried.job_id, JOB_IDS[1])
                self.assertEqual(service.wait(retried.job_id, timeout=5).state, "succeeded")
            finally:
                service.shutdown()

    def test_historical_replay_reconnect_and_live_observation_close_at_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            fake = BlockingPlanningService()
            service = PlanJobService(
                state_root=root / "state",
                artifacts_root=root / "artifacts",
                planning_service=fake,  # type: ignore[arg-type]
                job_id_factory=lambda: JOB_IDS[0],
            )
            observed = []
            try:
                job = service.start(PlanJobRequest("https://example.com/docs"))
                self.assertTrue(fake.started.wait(5))
                historical = service.events_after(job.job_id)
                self.assertGreaterEqual(len(historical), 3)
                after = historical[-1].sequence
                thread = Thread(
                    target=lambda: observed.extend(
                        service.observe_events(job.job_id, after_sequence=after, timeout=5)
                    )
                )
                thread.start()
                fake.release.set()
                thread.join(5)
                self.assertFalse(thread.is_alive())
                self.assertEqual(observed[-1].stage, "succeeded")
                self.assertEqual(
                    [event.sequence for event in service.events_after(job.job_id, after)],
                    [event.sequence for event in observed],
                )
                terminal_replay = list(
                    service.observe_events(job.job_id, after_sequence=observed[-1].sequence)
                )
                self.assertEqual(terminal_replay, [])
            finally:
                fake.release.set()
                service.shutdown()

    def test_second_live_service_fails_closed_without_interrupting_owner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            fake = BlockingPlanningService()
            first = PlanJobService(
                state_root=root / "state",
                artifacts_root=root / "artifacts",
                planning_service=fake,  # type: ignore[arg-type]
                job_id_factory=lambda: JOB_IDS[0],
            )
            try:
                job = first.start(PlanJobRequest("https://example.com/docs"))
                self.assertTrue(fake.started.wait(5))
                before = first.get(job.job_id)
                with self.assertRaises(ServiceOwnershipError):
                    PlanJobService(
                        state_root=root / "state",
                        artifacts_root=root / "artifacts",
                        planning_service=SuccessfulPlanningService(),  # type: ignore[arg-type]
                    )
                after = first.get(job.job_id)
                self.assertEqual(after.state, before.state)
                self.assertIn(after.state, ACTIVE_STATES)
                self.assertEqual(len(fake.calls), 1)
                fake.release.set()
                self.assertEqual(first.wait(job.job_id, timeout=5).state, "succeeded")
            finally:
                fake.release.set()
                first.shutdown()
            replacement = PlanJobService(
                state_root=root / "state",
                artifacts_root=root / "artifacts",
                planning_service=SuccessfulPlanningService(),  # type: ignore[arg-type]
            )
            replacement.shutdown()

    def test_service_lifetime_lock_excludes_another_process(self) -> None:
        script = r'''
from pathlib import Path
import sys, time
from buoy_search.command_center_jobs import PlanJobService
service = PlanJobService(state_root=Path(sys.argv[1]), artifacts_root=Path(sys.argv[2]))
print("READY", flush=True)
time.sleep(30)
'''
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            child = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    script,
                    str(root / "state"),
                    str(root / "artifacts"),
                ],
                env={**os.environ, "PYTHONPATH": "src"},
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                assert child.stdout is not None
                self.assertEqual(child.stdout.readline().strip(), "READY")
                with self.assertRaises(ServiceOwnershipError):
                    PlanJobService(
                        state_root=root / "state",
                        artifacts_root=root / "artifacts",
                    )
            finally:
                child.kill()
                child.communicate(timeout=5)
            reopened = PlanJobService(
                state_root=root / "state",
                artifacts_root=root / "artifacts",
            )
            reopened.shutdown()

    def test_managed_output_rejects_intermediate_configured_root_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            outside_parent = root / "outside-parent"
            artifacts = outside_parent / "artifacts"
            artifacts.mkdir(parents=True)
            link = root / "link"
            link.symlink_to(outside_parent, target_is_directory=True)

            with self.assertRaises(JobIntegrityError):
                PlanJobService(
                    state_root=root / "state",
                    artifacts_root=link / "artifacts",
                    planning_service=SuccessfulPlanningService(),  # type: ignore[arg-type]
                )
            self.assertEqual(list(artifacts.iterdir()), [])

    def test_managed_output_rejects_root_ancestor_final_symlinks_and_replacement(self) -> None:
        for component in ("artifacts", "command-center", "plans"):
            with self.subTest(component=component), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                outside = root / "outside"
                outside.mkdir()
                artifacts = root / "artifacts"
                if component == "artifacts":
                    artifacts.symlink_to(outside, target_is_directory=True)
                else:
                    artifacts.mkdir()
                    target = artifacts / "command-center"
                    if component == "plans":
                        target.mkdir()
                        target = target / "plans"
                    target.symlink_to(outside, target_is_directory=True)
                with self.assertRaises(JobIntegrityError):
                    PlanJobService(
                        state_root=root / "state",
                        artifacts_root=artifacts,
                        planning_service=SuccessfulPlanningService(),  # type: ignore[arg-type]
                    )
                self.assertEqual(list(outside.iterdir()), [])

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            outside = root / "outside"
            outside.mkdir()
            service = PlanJobService(
                state_root=root / "state",
                artifacts_root=root / "artifacts",
                planning_service=SuccessfulPlanningService(),  # type: ignore[arg-type]
                executor=CapturingExecutor(),  # type: ignore[arg-type]
                job_id_factory=lambda: JOB_IDS[0],
            )
            try:
                final = root / "artifacts/command-center/plans" / JOB_IDS[0]
                final.symlink_to(outside, target_is_directory=True)
                with self.assertRaises(JobIntegrityError):
                    service.start(PlanJobRequest("https://example.com/docs"))
                self.assertEqual(list(outside.iterdir()), [])
            finally:
                service.shutdown()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            outside = root / "outside"
            outside.mkdir()
            executor = CapturingExecutor()
            fake = SuccessfulPlanningService()
            service = PlanJobService(
                state_root=root / "state",
                artifacts_root=root / "artifacts",
                planning_service=fake,  # type: ignore[arg-type]
                executor=executor,  # type: ignore[arg-type]
                job_id_factory=lambda: JOB_IDS[0],
            )
            try:
                job = service.start(PlanJobRequest("https://example.com/docs"))
                output = root / "artifacts/command-center/plans" / job.job_id
                moved = root / "moved-output"
                output.rename(moved)
                output.symlink_to(outside, target_is_directory=True)
                executor.run()
                self.assertEqual(service.get(job.job_id).state, "failed")
                self.assertEqual(fake.calls, [])
                self.assertEqual(list(outside.iterdir()), [])
            finally:
                service.shutdown()

    def test_in_operation_output_replacement_cannot_redirect_planning_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            outside = root / "outside"
            outside.mkdir()
            moved = root / "moved-output"
            logical = root / "artifacts/command-center/plans" / JOB_IDS[0]

            def replacing_crawl(_source, options):  # noqa: ANN001
                logical.rename(moved)
                logical.symlink_to(outside, target_is_directory=True)
                pages = options.out_dir / "pages"
                _write_offline_page(pages)
                return CrawlExecution(
                    summary=_offline_crawl_summary(options, source_kind="website"),
                    indexing_plan=process_corpus(pages),
                )

            service = PlanJobService(
                state_root=root / "state",
                artifacts_root=root / "artifacts",
                planning_service=PlanningService(crawl_runner=replacing_crawl),
                job_id_factory=lambda: JOB_IDS[0],
            )
            try:
                job = service.start(PlanJobRequest("https://example.com/docs"))
                self.assertEqual(service.wait(job.job_id, timeout=5).state, "failed")
                self.assertEqual(list(outside.iterdir()), [])
                self.assertTrue((moved / "pages/page.md").is_file())
                self.assertNotIn("buoy-managed-plan-", (moved / "pages/page.md").read_text(encoding="utf-8"))
            finally:
                service.shutdown()

    def test_invalid_request_is_rejected_before_worker_submission(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            fake = SuccessfulPlanningService()
            service = PlanJobService(
                state_root=root / "state",
                artifacts_root=root / "artifacts",
                planning_service=fake,  # type: ignore[arg-type]
            )
            try:
                for request in (
                    PlanJobRequest("file:///tmp/secret"),
                    PlanJobRequest("https://user@example.com/docs"),
                    PlanJobRequest("https://example.com", max_chunks=0),
                    PlanJobRequest("https://github.com/Doctacon/buoy/tree/main/src"),
                ):
                    with self.subTest(request=request), self.assertRaises(ValueError):
                        service.start(request)
                self.assertEqual(fake.calls, [])
                self.assertEqual(service.list(), [])
            finally:
                service.shutdown()


if __name__ == "__main__":
    unittest.main()
