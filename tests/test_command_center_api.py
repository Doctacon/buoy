from __future__ import annotations

import asyncio
from contextlib import redirect_stderr
from dataclasses import dataclass, replace
import importlib.util
import inspect
from io import StringIO
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from threading import Event, Thread
from typing import Callable
import unittest
from unittest.mock import Mock, patch

UI_AVAILABLE = importlib.util.find_spec("fastapi") is not None and importlib.util.find_spec("httpx") is not None

if UI_AVAILABLE:
    from fastapi.testclient import TestClient

    from buoy_search.applied_state import build_applied_state, save_applied_state
    from buoy_search.command_center_api import (
        CSRF_HEADER,
        MAX_PLAN_JOB_BODY_BYTES,
        MAX_SSE_EVENTS_PER_CONNECTION,
        POST_GUARD_HEADER,
        POST_GUARD_VALUE,
        SECURITY_HEADERS,
        _sse_events,
        create_app,
    )
    from buoy_search.command_center_jobs import (
        ActiveJobConflict,
        JobIntegrityError,
        JobNotFoundError,
        JobProgress,
        JobRequestSummary,
        PlanJob,
        PlanJobEvent,
        PlanJobService,
        PlanJobStore,
        ServiceOwnershipError,
    )
    from buoy_search.command_center_local import (
        InventoryLookupError,
        LocalInventoryService,
        SafeError,
    )
    from buoy_search.command_center_server import run_server
    from buoy_search.planning_service import validate_managed_public_source


class FakeInventory:
    def __init__(self) -> None:
        self.invalidations = 0

    def invalidate(self) -> None:
        self.invalidations += 1

    def dashboard(self, *, recent_limit: int = 10):
        return {"resource": "dashboard", "recent_limit": recent_limit}

    def list_artifact_errors(
        self, *, offset: int = 0, limit: int = 50, q: str | None = None
    ):
        return {
            "resource": "artifact-errors",
            "offset": offset,
            "limit": limit,
            "q": q,
        }

    def list_namespaces(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        q: str | None = None,
        source_kind: str | None = None,
        local_status: str | None = None,
    ):
        return {
            "resource": "namespaces",
            "offset": offset,
            "limit": limit,
            "q": q,
            "source_kind": source_kind,
            "local_status": local_status,
        }

    def get_namespace(
        self, namespace: str, *, plan_offset: int = 0, plan_limit: int = 20
    ):
        if namespace == "missing":
            raise InventoryLookupError("namespace_not_found", "Namespace was not found.")
        return {
            "resource": "namespace",
            "namespace": namespace,
            "plan_offset": plan_offset,
            "plan_limit": plan_limit,
        }

    def list_plans(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        q: str | None = None,
        namespace: str | None = None,
        source_kind: str | None = None,
    ):
        return {
            "resource": "plans",
            "offset": offset,
            "limit": limit,
            "q": q,
            "namespace": namespace,
            "source_kind": source_kind,
        }

    def get_plan(self, plan_id: str):
        return {"resource": "plan", "plan_id": plan_id}

    def get_plan_review(
        self,
        plan_id: str,
        *,
        chunk_offset: int = 0,
        chunk_limit: int = 10,
        max_chars: int = 2_000,
        stale_offset: int = 0,
        stale_limit: int = 10,
    ):
        return {
            "resource": "review",
            "plan_id": plan_id,
            "chunk_offset": chunk_offset,
            "chunk_limit": chunk_limit,
            "max_chars": max_chars,
            "stale_offset": stale_offset,
            "stale_limit": stale_limit,
        }

    def list_plan_chunks(
        self,
        plan_id: str,
        *,
        offset: int = 0,
        limit: int = 50,
        max_chars: int = 2_000,
    ):
        return {
            "resource": "chunks",
            "plan_id": plan_id,
            "offset": offset,
            "limit": limit,
            "max_chars": max_chars,
        }

    def list_plan_stale_rows(self, plan_id: str, *, offset: int = 0, limit: int = 50):
        return {"resource": "stale", "plan_id": plan_id, "offset": offset, "limit": limit}


class BlockingInventory(FakeInventory):
    def __init__(self, blocked_resource: str) -> None:
        super().__init__()
        self.blocked_resource = blocked_resource
        self.entered = Event()
        self.release = Event()

    def _block(self) -> None:
        self.entered.set()
        if not self.release.wait(10):
            raise AssertionError("test did not release blocked inventory request")

    def dashboard(self, *, recent_limit: int = 10):
        if self.blocked_resource == "dashboard":
            self._block()
        return super().dashboard(recent_limit=recent_limit)

    def list_plans(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        q: str | None = None,
        namespace: str | None = None,
        source_kind: str | None = None,
    ):
        if self.blocked_resource == "plans":
            self._block()
        return super().list_plans(
            offset=offset,
            limit=limit,
            q=q,
            namespace=namespace,
            source_kind=source_kind,
        )


def _start_threaded_call(
    call: Callable[[], object],
) -> tuple[Thread, Event, dict[str, object]]:
    completed = Event()
    result: dict[str, object] = {}

    def run() -> None:
        try:
            result["response"] = call()
        except BaseException as exc:
            result["error"] = exc
        finally:
            completed.set()

    thread = Thread(target=run)
    thread.start()
    return thread, completed, result


@dataclass(frozen=True)
class FakeServiceError:
    code: str
    message: str
    phase: str


@dataclass(frozen=True)
class FakeRemoteResult:
    state: str = "not_configured"
    credentials_required: bool = True
    api_calls_occurred: bool = False
    writes_occurred: bool = False
    error: FakeServiceError = FakeServiceError(
        "remote_credentials_missing",
        "Remote access is not configured for this process.",
        "credentials",
    )


class FakeRemote:
    def __init__(self) -> None:
        self.calls = 0

    def refresh(self) -> FakeRemoteResult:
        self.calls += 1
        return FakeRemoteResult()


@dataclass(frozen=True)
class FakeSearchResult:
    state: str = "success"
    writes_occurred: bool = False
    error: None = None


class FakeSearch:
    def __init__(self) -> None:
        self.requests: list[object] = []

    def execute(self, request: object) -> FakeSearchResult:
        self.requests.append(request)
        return FakeSearchResult()


class FakePlanJobService:
    def __init__(self, *, conflict: bool = False, live: bool = False) -> None:
        self.conflict = conflict
        self.live = live
        self.starts: list[object] = []
        self.shutdowns: list[bool] = []
        self.polls = 0
        self.jobs: dict[str, PlanJob] = {}
        self.events: dict[str, list[PlanJobEvent]] = {}

    def start(self, request: object) -> PlanJob:
        if self.conflict:
            raise ActiveJobConflict("planjob_" + "a" * 32)
        source = validate_managed_public_source(getattr(request, "source_url"))
        self.starts.append(request)
        job_id = "planjob_" + "b" * 32
        now = "2026-07-23T12:00:00Z"
        queued = JobProgress("queued", "Plan job queued.", {})
        job = PlanJob(
            schema_version=1,
            job_id=job_id,
            operation="plan",
            actor="local-operator",
            state="queued",
            source_kind=getattr(source, "kind"),
            source_url=str(getattr(source, "base_url")),
            namespace=getattr(request, "namespace"),
            artifact_path=f"command-center/plans/{job_id}",
            plan_id=None,
            created_at=now,
            updated_at=now,
            event_sequence=1,
            started_at=None,
            completed_at=None,
            latest_progress=queued,
            error=None,
            request_summary=JobRequestSummary(
                getattr(request, "max_pages_or_files"),
                getattr(request, "max_chunks"),
                getattr(request, "namespace"),
                len(getattr(request, "include_paths")),
                len(getattr(request, "exclude_paths")),
            ),
        )
        self.jobs[job_id] = job
        self.events[job_id] = [PlanJobEvent(1, now, "queued", "Plan job queued.", {})]
        if not self.live:
            self._complete(job_id)
        return job

    def _complete(self, job_id: str) -> None:
        if self.jobs[job_id].state == "succeeded":
            return
        now = "2026-07-23T12:00:01Z"
        progress = JobProgress("succeeded", "Plan artifacts verified successfully.", {})
        self.jobs[job_id] = replace(
            self.jobs[job_id],
            state="succeeded",
            plan_id="plan-fake",
            namespace=self.jobs[job_id].namespace or "docs-fake",
            updated_at=now,
            completed_at=now,
            event_sequence=2,
            latest_progress=progress,
        )
        self.events[job_id].append(
            PlanJobEvent(2, now, "succeeded", progress.message, {})
        )

    def list(self) -> list[PlanJob]:
        return list(self.jobs.values())

    def list_window(self, *, offset: int, limit: int) -> tuple[list[PlanJob], int]:
        jobs = self.list()
        return jobs[offset : offset + limit], len(jobs)

    def get(self, job_id: str) -> PlanJob:
        try:
            return self.jobs[job_id]
        except KeyError as exc:
            raise JobNotFoundError("Plan job was not found.") from exc

    def events_after(self, job_id: str, after_sequence: int = 0) -> list[PlanJobEvent]:
        self.get(job_id)
        self.polls += 1
        if self.live and self.polls >= 2:
            self._complete(job_id)
        return [event for event in self.events[job_id] if event.sequence > after_sequence]

    def observe_events(self, job_id: str, *, after_sequence: int = 0, timeout=None):
        del timeout
        sequence = after_sequence
        while True:
            events = self.events_after(job_id, sequence)
            for event in events:
                sequence = event.sequence
                yield event
            if self.get(job_id).state == "succeeded":
                return

    def shutdown(self, *, wait: bool = True) -> None:
        self.shutdowns.append(wait)


class NeverCalledPlanningService:
    def __init__(self) -> None:
        self.calls: list[object] = []

    def plan(self, request: object, *, progress_callback=None):
        self.calls.append(request)
        raise AssertionError("startup must not start planning")


class _State:
    def __init__(self, state: str) -> None:
        self.state = state


class TerminalRaceService:
    def __init__(self) -> None:
        from threading import Barrier

        self.observer_returned = Barrier(2)
        self.terminal_committed = Barrier(2)
        self.state = "running"
        self.events: list[PlanJobEvent] = []

    def observe_events(self, _job_id: str, *, after_sequence: int, timeout: float):
        del after_sequence, timeout
        self.observer_returned.wait()
        self.terminal_committed.wait()
        return iter(())

    def get(self, _job_id: str) -> _State:
        return _State(self.state)

    def events_after(self, _job_id: str, after_sequence: int = 0) -> list[PlanJobEvent]:
        return [event for event in self.events if event.sequence > after_sequence]

    def commit_terminal(self) -> None:
        self.observer_returned.wait()
        self.state = "succeeded"
        self.events.append(
            PlanJobEvent(
                1,
                "2026-07-23T12:00:01Z",
                "succeeded",
                "Plan artifacts verified successfully.",
                {},
            )
        )
        self.terminal_committed.wait()


class IteratorProbeService:
    def __init__(self, event_count: int) -> None:
        self.events = [
            PlanJobEvent(
                sequence,
                "2026-07-23T12:00:01Z",
                "processing" if sequence < event_count else "succeeded",
                "Processing source content." if sequence < event_count else "Plan artifacts verified successfully.",
                {},
            )
            for sequence in range(1, event_count + 1)
        ]
        self.iterated = 0
        self.closed = False

    def observe_events(self, _job_id: str, *, after_sequence: int, timeout: float):
        del timeout
        try:
            for event in self.events:
                if event.sequence > after_sequence:
                    self.iterated += 1
                    yield event
        finally:
            self.closed = True

    def get(self, _job_id: str) -> _State:
        return _State("succeeded")

    def events_after(self, _job_id: str, after_sequence: int = 0) -> list[PlanJobEvent]:
        return [event for event in self.events if event.sequence > after_sequence][:1_000]


async def _direct_asgi_disconnect(app: object, path: str) -> list[dict[str, object]]:
    first_body = asyncio.Event()
    received_request = False
    sent: list[dict[str, object]] = []

    async def receive() -> dict[str, object]:
        nonlocal received_request
        if not received_request:
            received_request = True
            return {"type": "http.request", "body": b"", "more_body": False}
        await first_body.wait()
        return {"type": "http.disconnect"}

    async def send(message: dict[str, object]) -> None:
        sent.append(message)
        if message["type"] == "http.response.body" and message.get("body"):
            first_body.set()

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "scheme": "http",
        "method": "GET",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"host", b"localhost")],
        "client": ("127.0.0.1", 50000),
        "server": ("localhost", 80),
    }
    await app(scope, receive, send)  # type: ignore[operator]
    return sent


async def _direct_asgi_request(
    app: object,
    *,
    method: str,
    path: str,
    headers: list[tuple[bytes, bytes]],
    chunks: list[bytes],
) -> list[dict[str, object]]:
    messages = [
        {
            "type": "http.request",
            "body": chunk,
            "more_body": index < len(chunks) - 1,
        }
        for index, chunk in enumerate(chunks)
    ]
    sent: list[dict[str, object]] = []

    async def receive() -> dict[str, object]:
        if messages:
            return messages.pop(0)
        return {"type": "http.disconnect"}

    async def send(message: dict[str, object]) -> None:
        sent.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "scheme": "http",
        "method": method,
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "root_path": "",
        "headers": headers,
        "client": ("127.0.0.1", 50000),
        "server": ("localhost", 80),
    }
    await app(scope, receive, send)  # type: ignore[operator]
    return sent


@unittest.skipUnless(UI_AVAILABLE, "requires the optional FastAPI/httpx UI runtime")
class CommandCenterApiTests(unittest.TestCase):
    def make_client(self, root: Path, **kwargs):
        app = create_app(
            artifacts_root=root / "artifacts",
            state_root=root / "state",
            **kwargs,
        )
        return app, TestClient(app, base_url="http://localhost", raise_server_exceptions=False)

    def test_local_health_capabilities_and_empty_temporary_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "artifacts").mkdir()
            (root / "state").mkdir()
            static = root / "static"
            static.mkdir()
            (static / "index.html").write_text("frontend", encoding="utf-8")
            app, client = self.make_client(root, static_root=static)

            health = client.get("/api/v1/health")
            with patch.dict(os.environ, {"TURBOPUFFER_API_KEY": "secret-value"}), patch(
                "buoy_search.command_center_api._distribution_available",
                side_effect=lambda distribution: distribution == "google-cloud-bigquery",
            ):
                capabilities = client.get("/api/v1/capabilities")
            dashboard = client.get("/api/v1/dashboard")
            namespaces = client.get("/api/v1/namespaces")
            plans = client.get("/api/v1/plans")

        self.assertEqual(app.title, "Buoy local command center")
        self.assertEqual(
            app.description,
            "Read-only reviews plus bounded local credential-free HTTP(S) and public GitHub planning.",
        )
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["status"], "ok")
        self.assertEqual(health.json()["api_version"], "v1")
        self.assertTrue(capabilities.json()["review_routes_read_only"])
        self.assertTrue(capabilities.json()["local_plan_job_creation"])
        self.assertTrue(capabilities.json()["managed_public_planning_available"])
        self.assertIsNone(capabilities.json()["managed_public_planning_unavailable_reason"])
        self.assertTrue(capabilities.json()["durable_plan_job_history_available"])
        self.assertFalse(capabilities.json()["remote_mutations"])
        self.assertNotIn("read_only", capabilities.json())
        self.assertNotIn("mutations", capabilities.json())
        self.assertEqual(
            {key: capabilities.json()[key] for key in (
                "artifacts_root_available",
                "state_root_available",
                "turbopuffer_credentials_available",
                "ui_build_available",
                "bigquery_extra_installed",
                "snowflake_extra_installed",
            )},
            {
                "artifacts_root_available": True,
                "state_root_available": True,
                "turbopuffer_credentials_available": True,
                "ui_build_available": True,
                "bigquery_extra_installed": True,
                "snowflake_extra_installed": False,
            },
        )
        self.assertNotIn("secret-value", json.dumps(capabilities.json()))
        self.assertEqual(dashboard.json()["plan_count"], 0)
        self.assertEqual(namespaces.json()["items"], [])
        self.assertEqual(plans.json()["items"], [])
        methods = {
            (route.path, method)
            for route in app.routes
            for method in getattr(route, "methods", set())
            if route.path.startswith("/api/v1")
        }
        self.assertNotIn(("/api/v1/plans", "POST"), methods)
        self.assertNotIn(("/api/v1/namespaces", "POST"), methods)

    def test_unavailable_state_summary_primitive_keeps_read_only_routes_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = build_applied_state(
                site_id="example-com",
                namespace="site-example-com-v1",
                base_url="https://example.com/docs",
                last_plan_id="plan_123",
                last_apply_id="apply_123",
                updated_at="2026-07-27T00:00:00+00:00",
                rows=[],
            )
            save_applied_state(state, state_root=root / "state")
            app = create_app(
                artifacts_root=root / "artifacts", state_root=root / "state"
            )

            with patch.object(os, "O_NOFOLLOW", None), TestClient(
                app, base_url="http://localhost"
            ) as client:
                dashboard = client.get("/api/v1/dashboard")
                namespaces = client.get("/api/v1/namespaces")
                plans = client.get("/api/v1/plans")

        for response in (dashboard, namespaces, plans):
            self.assertEqual(response.status_code, 200, response.text)
        self.assertIsNone(dashboard.json()["active_row_count"])
        self.assertEqual(dashboard.json()["artifact_error_count"], 1)
        self.assertFalse(dashboard.json()["artifact_errors_truncated"])
        self.assertEqual(namespaces.json()["items"], [])
        self.assertEqual(plans.json()["items"], [])
        for inventory in (namespaces.json(), plans.json()):
            self.assertEqual(inventory["error_total"], 1)
            self.assertFalse(inventory["errors_truncated"])
        for errors in (
            dashboard.json()["artifact_errors"],
            namespaces.json()["errors"],
            plans.json()["errors"],
        ):
            self.assertEqual([error["code"] for error in errors], ["malformed_state"])
            self.assertIn("primitives are unavailable", errors[0]["message"])

    def test_unsupported_managed_planning_keeps_read_only_app_and_returns_uniform_503(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            factory = Mock()
            remote = FakeRemote()
            search = FakeSearch()
            before_modules = set(sys.modules)
            app = create_app(
                artifacts_root=root / "artifacts",
                state_root=root / "state",
                local_inventory=FakeInventory(),
                remote_snapshot_service=remote,
                search_service=search,
                plan_job_service_factory=factory,
            )
            with patch.object(os, "O_NOFOLLOW", None), self.assertLogs("buoy_search.command_center_api", level="WARNING") as logs:
                with TestClient(app, base_url="http://localhost") as client:
                    capabilities = client.get("/api/v1/capabilities")
                    dashboard = client.get("/api/v1/dashboard")
                    namespaces = client.get("/api/v1/namespaces")
                    plans = client.get("/api/v1/plans")
                    responses = [
                        client.post("/api/v1/plan-jobs", json={"source_url": "https://example.com"}),
                        client.get("/api/v1/plan-jobs"),
                        client.get("/api/v1/plan-jobs?offset=not-an-integer"),
                        client.get("/api/v1/plan-jobs?limit=not-an-integer"),
                        client.get("/api/v1/plan-jobs/not-a-job"),
                        client.get("/api/v1/plan-jobs/not-a-job/events"),
                    ]
                    startup_imported = set(sys.modules) - before_modules
                    remote_response = client.post(
                        "/api/v1/remote/snapshot",
                        headers={POST_GUARD_HEADER: POST_GUARD_VALUE},
                    )
                    search_response = client.post(
                        "/api/v1/search",
                        headers={POST_GUARD_HEADER: POST_GUARD_VALUE},
                        json={"query": "q", "namespaces": []},
                    )
            payload = capabilities.json()
            self.assertFalse(payload["local_plan_job_creation"])
            self.assertFalse(payload["managed_public_planning_available"])
            self.assertEqual(
                payload["managed_public_planning_unavailable_reason"],
                "platform_unsupported",
            )
            self.assertFalse(payload["durable_plan_job_history_available"])
            self.assertEqual(dashboard.status_code, 200)
            self.assertEqual(namespaces.status_code, 200)
            self.assertEqual(plans.status_code, 200)
            for response in responses:
                self.assertEqual(response.status_code, 503, response.text)
                self.assertEqual(
                    response.json(),
                    {
                        "error": {
                            "code": "managed_planning_unavailable",
                            "message": "Managed public-source planning is unavailable on this platform.",
                        }
                    },
                )
                for header, expected in SECURITY_HEADERS.items():
                    self.assertEqual(response.headers[header], expected)
            self.assertEqual(remote_response.status_code, 200)
            self.assertEqual(search_response.status_code, 200)
            factory.assert_not_called()
            self.assertFalse((root / "state/command-center/jobs").exists())
            self.assertFalse((root / "artifacts/command-center/plans").exists())
            for forbidden in (
                "turbopuffer",
                "sentence_transformers",
                "transformers",
                "buoy_search.command_center_remote",
                "buoy_search.github_repo",
            ):
                self.assertNotIn(forbidden, startup_imported)
            rendered_logs = "\n".join(logs.output)
            self.assertEqual(rendered_logs.count("Managed public-source planning is unavailable"), 1)
            self.assertNotIn("O_NOFOLLOW", rendered_logs)

    def test_same_app_recovers_managed_planning_after_an_unsupported_lifespan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            services: list[FakePlanJobService] = []

            def factory() -> FakePlanJobService:
                service = FakePlanJobService()
                services.append(service)
                return service

            app = create_app(
                artifacts_root=root / "artifacts",
                state_root=root / "state",
                local_inventory=FakeInventory(),
                plan_job_service_factory=factory,
            )
            with patch.object(os, "O_NOFOLLOW", None):
                with TestClient(app, base_url="http://localhost") as client:
                    unavailable = client.get("/api/v1/capabilities").json()
                    self.assertFalse(unavailable["managed_public_planning_available"])
                    self.assertEqual(
                        unavailable["managed_public_planning_unavailable_reason"],
                        "platform_unsupported",
                    )
                    self.assertEqual(client.get("/api/v1/plan-jobs").status_code, 503)
            self.assertEqual(services, [])

            with TestClient(app, base_url="http://localhost") as client:
                available = client.get("/api/v1/capabilities").json()
                self.assertTrue(available["managed_public_planning_available"])
                self.assertIsNone(
                    available["managed_public_planning_unavailable_reason"]
                )
                self.assertTrue(available["durable_plan_job_history_available"])
                listing = client.get("/api/v1/plan-jobs")
                token = client.get("/api/v1/csrf-token").json()["csrf_token"]
                created = client.post(
                    "/api/v1/plan-jobs",
                    headers={CSRF_HEADER: token, "Origin": "http://localhost"},
                    json={"source_url": "https://example.com/docs"},
                )
            self.assertEqual(listing.status_code, 200)
            self.assertEqual(listing.json()["items"], [])
            self.assertEqual(created.status_code, 202)
            self.assertEqual(len(services), 1)
            self.assertEqual(services[0].shutdowns, [True])

    def test_each_missing_primitive_still_starts_health_and_read_only_inventory(self) -> None:
        primitive_patches = (
            ("O_DIRECTORY", lambda: patch.object(os, "O_DIRECTORY", None)),
            ("descriptor-relative", lambda: patch.object(os, "supports_dir_fd", set())),
            ("descriptor-enumeration", lambda: patch.object(os, "supports_fd", set())),
        )
        for label, make_patch in primitive_patches:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp, make_patch():
                root = Path(tmp)
                factory = Mock()
                app = create_app(
                    artifacts_root=root / "artifacts",
                    state_root=root / "state",
                    local_inventory=FakeInventory(),
                    plan_job_service_factory=factory,
                )
                with TestClient(app, base_url="http://localhost") as client:
                    self.assertEqual(client.get("/api/v1/health").status_code, 200)
                    self.assertEqual(client.get("/api/v1/dashboard").status_code, 200)
                    self.assertFalse(
                        client.get("/api/v1/capabilities").json()[
                            "managed_public_planning_available"
                        ]
                    )
                factory.assert_not_called()
                self.assertFalse((root / "state/command-center/jobs").exists())
                self.assertFalse((root / "artifacts/command-center/plans").exists())

    def test_non_platform_startup_failures_remain_fail_closed(self) -> None:
        for failure in (
            JobIntegrityError("tampered durable state"),
            ServiceOwnershipError("another service owns the lock"),
            PermissionError("permission denied"),
        ):
            with self.subTest(failure=type(failure).__name__), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                app = create_app(
                    artifacts_root=root / "artifacts",
                    state_root=root / "state",
                    local_inventory=FakeInventory(),
                    plan_job_service_factory=Mock(side_effect=failure),
                )
                with self.assertRaises(type(failure)):
                    with TestClient(app, base_url="http://localhost"):
                        pass

    def test_default_managed_job_publication_is_immediately_discoverable(self) -> None:
        from types import SimpleNamespace

        from buoy_search.chunker import process_corpus
        from buoy_search.plan_artifacts import build_plan_artifacts, write_plan_artifacts

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            corpus = root / "fixture-corpus"
            corpus.mkdir()
            (corpus / "page.md").write_text(
                "---\nurl: https://example.com/docs/page\ntitle: Guide\n"
                "status: 200\ncontent_type: text/markdown\nsource_kind: website\n"
                "---\n\n# Published guide\n\nImmediately discoverable content.\n",
                encoding="utf-8",
            )

            def publish_valid_plan(  # noqa: ANN001
                _planning_service, request, *, progress_callback=None
            ):
                del progress_callback
                artifacts = build_plan_artifacts(
                    indexing_plan=process_corpus(corpus),
                    base_url="https://example.com/docs",
                    out_dir=request.out_dir,
                    namespace=request.namespace,
                    originating_job_id=request.originating_job_id,
                )
                write_plan_artifacts(artifacts, request.out_dir)
                return SimpleNamespace(
                    summary={
                        "plan_id": artifacts.plan.plan_id,
                        "namespace": artifacts.plan.namespace,
                    },
                    out_dir=request.out_dir,
                )

            app = create_app(
                artifacts_root=root / "artifacts",
                state_root=root / "state",
            )
            with patch(
                "buoy_search.planning_service.PlanningService.plan",
                new=publish_valid_plan,
            ), TestClient(
                app, base_url="http://localhost", raise_server_exceptions=False
            ) as client:
                cached_empty = client.get("/api/v1/plans")
                token = client.get("/api/v1/csrf-token").json()["csrf_token"]
                created = client.post(
                    "/api/v1/plan-jobs",
                    headers={CSRF_HEADER: token, "Origin": "http://localhost"},
                    json={
                        "source_url": "https://example.com/docs",
                        "namespace": "docs-v1",
                    },
                )
                job_id = created.json()["job_id"]
                deadline = time.monotonic() + 5
                while True:
                    completed = client.get(f"/api/v1/plan-jobs/{job_id}")
                    if completed.json()["state"] in {"succeeded", "failed", "interrupted"}:
                        break
                    if time.monotonic() >= deadline:
                        self.fail("managed publication did not complete")
                    time.sleep(0.01)
                immediately_visible = client.get("/api/v1/plans")

        self.assertEqual(cached_empty.status_code, 200)
        self.assertEqual(cached_empty.json()["total"], 0)
        self.assertEqual(created.status_code, 202, created.text)
        self.assertEqual(completed.status_code, 200, completed.text)
        self.assertEqual(completed.json()["state"], "succeeded")
        self.assertEqual(
            immediately_visible.status_code, 200, immediately_visible.text
        )
        self.assertEqual(immediately_visible.json()["total"], 1)
        self.assertEqual(
            immediately_visible.json()["items"][0]["plan_id"],
            completed.json()["plan_id"],
        )

    def test_non_empty_local_service_contract_is_serialized_through_fastapi(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            from tests.test_command_center_local import write_plan

            plan_id, _ = write_plan(
                root / "artifacts" / "plan-contract",
                originating_job_id=f"planjob_{'c' * 32}",
            )
            _, client = self.make_client(root)
            dashboard_response = client.get("/api/v1/dashboard")
            namespaces_response = client.get("/api/v1/namespaces")
            plans_response = client.get("/api/v1/plans")
            plan_response = client.get(f"/api/v1/plans/{plan_id}")

        for response in (
            dashboard_response,
            namespaces_response,
            plans_response,
            plan_response,
        ):
            self.assertEqual(response.status_code, 200, response.text)

        dashboard = dashboard_response.json()
        self.assertEqual(dashboard["pending_namespace_count"], 1)
        self.assertEqual(dashboard["artifact_error_count"], 0)
        self.assertTrue(dashboard["recent_plans"][0]["diff"]["first_apply"])
        self.assertEqual(
            dashboard["recent_plans"][0]["source_activity"],
            {"credentials_required": False, "api_calls_occurred": False},
        )

        namespace = namespaces_response.json()["items"][0]
        self.assertEqual(namespace["local_status"], "pending_changes")
        self.assertIsNone(namespace["retained_stale_rows"])
        self.assertEqual(namespace["latest_planned_upserts"], 1)
        self.assertEqual(namespace["latest_planned_stale_rows"], 0)
        self.assertEqual(namespace["document_count"], 1)
        self.assertEqual(namespace["chunk_count"], 1)
        self.assertEqual(namespace["latest_plan_id"], plan_id)
        self.assertIsNone(namespace["last_apply_id"])
        self.assertEqual(namespace["source"]["kind"], "website")

        plan_summary = plans_response.json()["items"][0]
        self.assertTrue(plan_summary["diff"]["first_apply"])
        self.assertEqual(plan_summary["diff"]["rows_to_upsert"], 1)
        self.assertEqual(
            plan_summary["source_activity"],
            {"credentials_required": False, "api_calls_occurred": False},
        )
        self.assertIsNone(plan_response.json()["retrieval"]["region"])
        self.assertEqual(
            plan_response.json()["originating_job_id"], f"planjob_{'c' * 32}"
        )

    def test_large_artifact_error_api_is_bounded_filterable_and_inert(self) -> None:
        import buoy_search.command_center_local as local_module

        errors = [
            SafeError(
                f"error_{index % 7}",
                ("Needle diagnostic " if index % 100 == 0 else "Safe diagnostic ")
                + str(index),
                f"artifact-{9_999 - index:05d}",
            )
            for index in range(10_000)
        ]
        expected = sorted(errors, key=lambda item: (item.code, item.artifact_id))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            service = LocalInventoryService(
                artifacts_root=root / "artifacts", state_root=root / "state"
            )
            _, client = self.make_client(root, local_inventory=service)
            with patch(
                "buoy_search.command_center_local._discover_plans",
                return_value=([], errors),
            ) as plans_scan, patch(
                "buoy_search.command_center_local._discover_states",
                return_value=([], [], set()),
            ) as state_scan, patch(
                "buoy_search.command_center_local._verify_plan_artifacts",
                side_effect=AssertionError("diagnostics must not verify deltas"),
            ) as verify:
                dashboard = client.get("/api/v1/dashboard")
                plans = client.get("/api/v1/plans")
                namespaces = client.get("/api/v1/namespaces")
                first_page = client.get("/api/v1/artifact-errors")
                filtered = client.get(
                    "/api/v1/artifact-errors?offset=5&limit=7&q=NEEDLE"
                )
                by_id = client.get(
                    "/api/v1/artifact-errors?q=artifact-00000"
                )
                invalid = [
                    client.get("/api/v1/artifact-errors?offset=-1"),
                    client.get("/api/v1/artifact-errors?limit=101"),
                    client.get("/api/v1/artifact-errors?q=" + "x" * 257),
                ]

        self.assertEqual(
            (plans_scan.call_count, state_scan.call_count, verify.call_count),
            (1, 1, 0),
        )
        for response in (dashboard, plans, namespaces, first_page, filtered, by_id):
            self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(dashboard.json()["artifact_error_count"], 10_000)
        self.assertEqual(len(dashboard.json()["artifact_errors"]), 20)
        self.assertTrue(dashboard.json()["artifact_errors_truncated"])
        for response in (plans, namespaces):
            self.assertEqual(response.json()["error_total"], 10_000)
            self.assertEqual(len(response.json()["errors"]), 20)
            self.assertTrue(response.json()["errors_truncated"])
            self.assertLess(len(response.content), 10_000)
        self.assertEqual(first_page.json()["total"], 10_000)
        self.assertEqual(first_page.json()["limit"], 50)
        self.assertEqual(
            [item["artifact_id"] for item in first_page.json()["items"]],
            [item.artifact_id for item in expected[:50]],
        )
        matching = [item for item in expected if "needle" in item.message.casefold()]
        self.assertEqual(filtered.json()["total"], 100)
        self.assertEqual(
            [item["artifact_id"] for item in filtered.json()["items"]],
            [item.artifact_id for item in matching[5:12]],
        )
        self.assertEqual(by_id.json()["total"], 1)
        self.assertEqual(by_id.json()["items"][0]["artifact_id"], "artifact-00000")
        for response, code in zip(
            invalid,
            ("invalid_offset", "invalid_limit", "invalid_request"),
            strict=True,
        ):
            self.assertEqual(response.status_code, 400, response.text)
            self.assertEqual(response.json()["error"]["code"], code)

    def test_bounded_filters_namespace_history_and_review_api_contracts(self) -> None:
        import buoy_search.command_center_local as local_module
        from buoy_search.command_center_local import LocalInventoryService
        from tests.test_command_center_local import changed_and_stale_state, write_plan

        class InertPlanJobs:
            def shutdown(self, *, wait: bool) -> None:
                del wait

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = changed_and_stale_state(root / "fixture")
            plan_id, _ = write_plan(
                root / "artifacts" / "current", state=state, state_present=True
            )
            broken_state = (
                root
                / "state"
                / "state"
                / "broken-site"
                / "broken-namespace"
                / "state.duckdb"
            )
            broken_state.parent.mkdir(parents=True)
            broken_state.write_bytes(b"malformed state")
            service = LocalInventoryService(
                artifacts_root=root / "artifacts", state_root=root / "state"
            )
            app = create_app(
                artifacts_root=root / "artifacts",
                state_root=root / "state",
                local_inventory=service,
                plan_job_service_factory=InertPlanJobs,
            )
            with patch(
                "buoy_search.command_center_local._verify_plan_artifacts",
                wraps=local_module._verify_plan_artifacts,
            ) as verify, TestClient(app, base_url="http://localhost") as client:
                plans = client.get(
                    "/api/v1/plans?q=EXAMPLE.COM%2FDOCS&namespace=site-example-com-v1&source_kind=website&limit=1"
                )
                namespaces = client.get(
                    "/api/v1/namespaces?q=SITE-EXAMPLE&source_kind=website&local_status=pending_changes&limit=1"
                )
                error_namespaces = client.get(
                    "/api/v1/namespaces?local_status=error"
                )
                unknown_namespaces = client.get(
                    "/api/v1/namespaces?source_kind=unknown"
                )
                unknown_error_namespaces = client.get(
                    "/api/v1/namespaces?source_kind=unknown&local_status=error"
                )
                known_source_namespaces = {
                    kind: client.get(f"/api/v1/namespaces?source_kind={kind}")
                    for kind in ("website", "github_repo", "document", "database")
                }
                namespace = client.get(
                    "/api/v1/namespaces/site-example-com-v1?plan_offset=0&plan_limit=1"
                )
                review = client.get(
                    f"/api/v1/plans/{plan_id}/review?chunk_offset=0&chunk_limit=1&max_chars=8&stale_offset=1&stale_limit=1"
                )
                self.assertEqual(verify.call_count, 1)
                detail = client.get(f"/api/v1/plans/{plan_id}")
                chunks = client.get(
                    f"/api/v1/plans/{plan_id}/chunks?offset=0&limit=1"
                )
                stale = client.get(
                    f"/api/v1/plans/{plan_id}/stale-rows?offset=0&limit=1"
                )
                self.assertEqual(verify.call_count, 4)
                invalid_filter = client.get("/api/v1/plans?source_kind=pdf")
                invalid_query = client.get("/api/v1/namespaces?q=" + "x" * 257)
                invalid_window = client.get(
                    f"/api/v1/plans/{plan_id}/review?chunk_limit=101"
                )
                self.assertEqual(verify.call_count, 4)

        for response in (
            plans,
            namespaces,
            error_namespaces,
            unknown_namespaces,
            unknown_error_namespaces,
            *known_source_namespaces.values(),
            namespace,
            review,
            detail,
            chunks,
            stale,
        ):
            self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(plans.json()["total"], 1)
        self.assertEqual(namespaces.json()["total"], 1)
        self.assertEqual(error_namespaces.json()["total"], 1)
        self.assertEqual(
            error_namespaces.json()["items"][0]["namespace"], "broken-namespace"
        )
        self.assertEqual(error_namespaces.json()["items"][0]["local_status"], "error")
        self.assertIsNone(error_namespaces.json()["items"][0]["source"])
        for response in (unknown_namespaces, unknown_error_namespaces):
            self.assertEqual(response.json()["total"], 1)
            self.assertEqual(
                response.json()["items"][0]["namespace"], "broken-namespace"
            )
            self.assertEqual(response.json()["items"][0]["local_status"], "error")
            self.assertIsNone(response.json()["items"][0]["source"])
        self.assertEqual(
            {
                kind: response.json()["total"]
                for kind, response in known_source_namespaces.items()
            },
            {"website": 1, "github_repo": 0, "document": 0, "database": 0},
        )
        self.assertEqual(
            {
                key: namespace.json()[key]
                for key in (
                    "plan_total",
                    "plan_offset",
                    "plan_limit",
                    "plans_truncated",
                )
            },
            {
                "plan_total": 1,
                "plan_offset": 0,
                "plan_limit": 1,
                "plans_truncated": False,
            },
        )
        self.assertEqual(review.json()["detail"]["summary"]["plan_id"], plan_id)
        self.assertEqual(review.json()["chunks"]["limit"], 1)
        self.assertEqual(len(review.json()["chunks"]["items"][0]["content"]), 8)
        self.assertEqual(review.json()["stale_rows"]["offset"], 1)
        for response in (invalid_filter, invalid_query):
            self.assertEqual(response.status_code, 400, response.text)
            self.assertEqual(response.json()["error"]["code"], "invalid_request")
        self.assertEqual(invalid_window.status_code, 400)
        self.assertEqual(invalid_window.json()["error"]["code"], "invalid_limit")

    def test_all_inventory_detail_and_pagination_routes_delegate_to_service(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _, client = self.make_client(Path(tmp), local_inventory=FakeInventory())
            cases = [
                ("/api/v1/dashboard?recent_limit=4", "dashboard"),
                ("/api/v1/artifact-errors?offset=2&limit=3&q=broken", "artifact-errors"),
                (
                    "/api/v1/namespaces?offset=2&limit=3&q=docs&source_kind=website&local_status=planned",
                    "namespaces",
                ),
                (
                    "/api/v1/namespaces/site-example-v1?plan_offset=2&plan_limit=3",
                    "namespace",
                ),
                (
                    "/api/v1/plans?offset=1&limit=2&q=docs&namespace=site-example-v1&source_kind=website",
                    "plans",
                ),
                ("/api/v1/plans/plan-1", "plan"),
                (
                    "/api/v1/plans/plan-1/review?chunk_offset=2&chunk_limit=3&max_chars=123&stale_offset=4&stale_limit=5",
                    "review",
                ),
                ("/api/v1/plans/plan-1/chunks?offset=2&limit=3&max_chars=123", "chunks"),
                ("/api/v1/plans/plan-1/stale-rows?offset=2&limit=3", "stale"),
            ]
            for path, resource in cases:
                with self.subTest(path=path):
                    response = client.get(path)
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(response.json()["resource"], resource)
            for removed in (
                "/api/v1/plans/plan-1/pages",
                "/api/v1/plans/plan-1/pages/4",
            ):
                response = client.get(removed)
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json()["error"]["code"], "api_route_not_found")

    def test_blocking_service_routes_are_sync_with_async_creation_and_sse_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app, _ = self.make_client(Path(tmp), local_inventory=FakeInventory())

        routes = {
            (route.path, method): route.endpoint
            for route in app.routes
            if hasattr(route, "endpoint")
            for method in getattr(route, "methods", set())
        }
        sync_routes = {
            ("/api/v1/dashboard", "GET"),
            ("/api/v1/artifact-errors", "GET"),
            ("/api/v1/namespaces", "GET"),
            ("/api/v1/namespaces/{namespace}", "GET"),
            ("/api/v1/plans", "GET"),
            ("/api/v1/plans/{plan_id}", "GET"),
            ("/api/v1/plans/{plan_id}/review", "GET"),
            ("/api/v1/plans/{plan_id}/chunks", "GET"),
            ("/api/v1/plans/{plan_id}/stale-rows", "GET"),
            ("/api/v1/plan-jobs", "GET"),
            ("/api/v1/plan-jobs/{job_id}", "GET"),
            ("/api/v1/remote/snapshot", "POST"),
            ("/api/v1/search", "POST"),
        }
        for route in sync_routes:
            with self.subTest(route=route):
                self.assertFalse(inspect.iscoroutinefunction(routes[route]))
        for route in (
            ("/api/v1/plan-jobs", "POST"),
            ("/api/v1/plan-jobs/{job_id}/events", "GET"),
        ):
            with self.subTest(route=route):
                self.assertTrue(inspect.iscoroutinefunction(routes[route]))

    def test_blocked_dashboard_does_not_block_health_or_corrupt_structured_errors(self) -> None:
        inventory = BlockingInventory("dashboard")
        threads: list[Thread] = []
        with tempfile.TemporaryDirectory() as tmp:
            _, client = self.make_client(
                Path(tmp),
                local_inventory=inventory,
                plan_job_service_factory=FakePlanJobService,
            )
            with client:
                blocked, blocked_done, blocked_result = _start_threaded_call(
                    lambda: client.get("/api/v1/dashboard?recent_limit=4")
                )
                threads.append(blocked)
                try:
                    self.assertTrue(inventory.entered.wait(5))
                    health, health_done, health_result = _start_threaded_call(
                        lambda: client.get("/api/v1/health")
                    )
                    missing, missing_done, missing_result = _start_threaded_call(
                        lambda: client.get("/api/v1/namespaces/missing")
                    )
                    threads.extend((health, missing))
                    self.assertTrue(health_done.wait(5))
                    self.assertTrue(missing_done.wait(5))
                    self.assertFalse(inventory.release.is_set())
                    self.assertFalse(blocked_done.is_set())
                finally:
                    inventory.release.set()
                    for thread in threads:
                        thread.join(5)

        for thread in threads:
            self.assertFalse(thread.is_alive())
        for result in (blocked_result, health_result, missing_result):
            if "error" in result:
                raise AssertionError("concurrent request raised outside FastAPI") from result["error"]
        blocked_response = blocked_result["response"]
        health_response = health_result["response"]
        missing_response = missing_result["response"]
        self.assertEqual(getattr(blocked_response, "status_code"), 200)
        self.assertEqual(
            getattr(blocked_response, "json")(),
            {"resource": "dashboard", "recent_limit": 4},
        )
        self.assertEqual(getattr(health_response, "status_code"), 200)
        self.assertEqual(getattr(health_response, "json")()["status"], "ok")
        self.assertEqual(getattr(missing_response, "status_code"), 404)
        self.assertEqual(
            getattr(missing_response, "json")(),
            {
                "error": {
                    "code": "namespace_not_found",
                    "message": "Namespace was not found.",
                }
            },
        )

    def test_active_plan_job_detail_is_observable_while_plan_inventory_is_blocked(self) -> None:
        inventory = BlockingInventory("plans")
        service = FakePlanJobService(live=True)
        threads: list[Thread] = []
        with tempfile.TemporaryDirectory() as tmp:
            app = create_app(
                artifacts_root=Path(tmp) / "artifacts",
                state_root=Path(tmp) / "state",
                local_inventory=inventory,
                plan_job_service_factory=lambda: service,
            )
            with TestClient(
                app, base_url="http://localhost", raise_server_exceptions=False
            ) as client:
                token = client.get("/api/v1/csrf-token").json()["csrf_token"]
                created = client.post(
                    "/api/v1/plan-jobs",
                    headers={CSRF_HEADER: token, "Origin": "http://localhost"},
                    json={"source_url": "https://example.com/docs"},
                )
                job_id = created.json()["job_id"]
                blocked, blocked_done, blocked_result = _start_threaded_call(
                    lambda: client.get("/api/v1/plans")
                )
                threads.append(blocked)
                try:
                    self.assertTrue(inventory.entered.wait(5))
                    observed, observed_done, observed_result = _start_threaded_call(
                        lambda: client.get(f"/api/v1/plan-jobs/{job_id}")
                    )
                    threads.append(observed)
                    self.assertTrue(observed_done.wait(5))
                    self.assertFalse(inventory.release.is_set())
                    self.assertFalse(blocked_done.is_set())
                finally:
                    inventory.release.set()
                    for thread in threads:
                        thread.join(5)

        self.assertEqual(created.status_code, 202)
        for thread in threads:
            self.assertFalse(thread.is_alive())
        for result in (blocked_result, observed_result):
            if "error" in result:
                raise AssertionError("concurrent request raised outside FastAPI") from result["error"]
        blocked_response = blocked_result["response"]
        observed_response = observed_result["response"]
        self.assertEqual(getattr(blocked_response, "status_code"), 200)
        self.assertEqual(getattr(blocked_response, "json")()["resource"], "plans")
        self.assertEqual(getattr(observed_response, "status_code"), 200)
        self.assertEqual(getattr(observed_response, "json")()["job_id"], job_id)
        self.assertEqual(getattr(observed_response, "json")()["state"], "queued")

    def test_remote_refresh_and_search_are_explicit_and_safe(self) -> None:
        remote = FakeRemote()
        search = FakeSearch()
        with tempfile.TemporaryDirectory() as tmp:
            _, client = self.make_client(
                Path(tmp),
                local_inventory=FakeInventory(),
                remote_snapshot_service=remote,
                search_service=search,
            )
            self.assertEqual(remote.calls, 0)
            headers = {POST_GUARD_HEADER: POST_GUARD_VALUE}
            remote_response = client.post("/api/v1/remote/snapshot", headers=headers)
            search_response = client.post(
                "/api/v1/search",
                headers=headers,
                json={"query": "How does Buoy work?", "namespaces": ["site-example-v1"]},
            )

        self.assertEqual(remote.calls, 1)
        self.assertEqual(remote_response.status_code, 200)
        self.assertEqual(
            remote_response.json()["error"],
            {
                "code": "remote_credentials_missing",
                "message": "Remote access is not configured for this process.",
                "details": {"phase": "credentials"},
            },
        )
        self.assertEqual(search_response.status_code, 200)
        self.assertFalse(search_response.json()["writes_occurred"])
        self.assertEqual(getattr(search.requests[0], "namespaces"), ("site-example-v1",))

    def test_host_and_explicit_post_guards_reject_forged_requests(self) -> None:
        remote = FakeRemote()
        search = FakeSearch()
        with tempfile.TemporaryDirectory() as tmp:
            _, client = self.make_client(
                Path(tmp),
                local_inventory=FakeInventory(),
                remote_snapshot_service=remote,
                search_service=search,
            )
            hostile_host = client.get("/api/v1/health", headers={"Host": "attacker.example"})
            userinfo_host = client.get("/api/v1/health", headers={"Host": "attacker@localhost"})
            missing_header = client.post("/api/v1/remote/snapshot")
            cross_origin = client.post(
                "/api/v1/remote/snapshot",
                headers={POST_GUARD_HEADER: POST_GUARD_VALUE, "Origin": "https://attacker.example"},
            )
            cross_site = client.post(
                "/api/v1/search",
                headers={POST_GUARD_HEADER: POST_GUARD_VALUE, "Sec-Fetch-Site": "cross-site"},
                json={"query": "q", "namespaces": ["site-example-v1"]},
            )

        for response in (missing_header, cross_origin, cross_site):
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()["error"]["code"], "request_forbidden")
        self.assertEqual(hostile_host.status_code, 400)
        self.assertEqual(hostile_host.json()["error"]["code"], "invalid_host")
        self.assertEqual(userinfo_host.status_code, 400)
        self.assertEqual(remote.calls, 0)
        self.assertEqual(search.requests, [])

    def test_csrf_issuance_valid_creation_and_service_lifecycle(self) -> None:
        service = FakePlanJobService()
        constructions: list[FakePlanJobService] = []
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app = create_app(
                artifacts_root=root / "artifacts",
                state_root=root / "state",
                local_inventory=FakeInventory(),
                plan_job_service_factory=lambda: constructions.append(service) or service,
            )
            self.assertEqual(constructions, [])
            with TestClient(app, base_url="http://localhost", raise_server_exceptions=False) as client:
                token_response = client.get("/api/v1/csrf-token")
                token = token_response.json()["csrf_token"]
                created = client.post(
                    "/api/v1/plan-jobs",
                    headers={CSRF_HEADER: token, "Origin": "http://localhost"},
                    json={
                        "source_url": "https://example.com/docs",
                        "max_pages_or_files": 7,
                        "max_chunks": 11,
                        "namespace": "docs-v1",
                        "include_paths": ["/guide"],
                        "exclude_paths": ["/private"],
                    },
                )

        self.assertEqual(token_response.status_code, 200)
        self.assertEqual(token_response.headers["cache-control"], "no-store")
        self.assertGreaterEqual(len(token), 32)
        self.assertEqual(created.status_code, 202, created.text)
        self.assertEqual(created.json()["job_id"], "planjob_" + "b" * 32)
        self.assertEqual(len(service.starts), 1)
        self.assertEqual(getattr(service.starts[0], "include_paths"), ("/guide",))
        self.assertEqual(constructions, [service])
        self.assertEqual(service.shutdowns, [True])

    def test_plan_creation_security_content_type_size_and_validation_fail_closed(self) -> None:
        service = FakePlanJobService()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app = create_app(
                artifacts_root=root / "artifacts",
                state_root=root / "state",
                local_inventory=FakeInventory(),
                plan_job_service_factory=lambda: service,
            )
            with TestClient(app, base_url="http://localhost", raise_server_exceptions=False) as client:
                token = client.get("/api/v1/csrf-token").json()["csrf_token"]
                good = {CSRF_HEADER: token, "Origin": "http://localhost"}
                cases = [
                    ({"Origin": "http://localhost"}, {"source_url": "https://example.com"}, 403),
                    ({CSRF_HEADER: "wrong", "Origin": "http://localhost"}, {"source_url": "https://example.com"}, 403),
                    ({CSRF_HEADER: token}, {"source_url": "https://example.com"}, 403),
                    ({CSRF_HEADER: token, "Origin": "https://attacker.example"}, {"source_url": "https://example.com"}, 403),
                    ({**good, "Sec-Fetch-Site": "cross-site"}, {"source_url": "https://example.com"}, 403),
                ]
                for headers, payload, status in cases:
                    with self.subTest(headers=headers):
                        response = client.post("/api/v1/plan-jobs", headers=headers, json=payload)
                        self.assertEqual(response.status_code, status, response.text)
                conflicting_origin = client.post(
                    "/api/v1/plan-jobs",
                    headers=[
                        (CSRF_HEADER, token),
                        ("Origin", "http://localhost"),
                        ("Origin", "http://127.0.0.1"),
                        ("Content-Type", "application/json"),
                    ],
                    content=b'{"source_url":"https://example.com"}',
                )
                wrong_type = client.post(
                    "/api/v1/plan-jobs",
                    headers={**good, "Content-Type": "text/plain"},
                    content=b"{}",
                )
                oversized = client.post(
                    "/api/v1/plan-jobs",
                    headers={**good, "Content-Type": "application/json"},
                    content=b" " * (MAX_PLAN_JOB_BODY_BYTES + 1),
                )
                hostile_host = client.post(
                    "/api/v1/plan-jobs",
                    headers={**good, "Host": "attacker.example"},
                    json={"source_url": "https://example.com"},
                )
                invalid_payloads = [
                    {"source_url": "file:///tmp/private"},
                    {"source_url": "https://user@example.com/docs"},
                    {"source_url": "https://github.com/owner/repo/tree/main"},
                    {"source_url": "https://example.com:bad/docs"},
                    {"source_url": "https://example.com:99999/docs"},
                    {"source_url": "https://example.com:0/docs"},
                    {"source_url": "https://example.com:/docs"},
                    {"source_url": "https://:443/docs"},
                    {"source_url": "https://exa mple.com/docs"},
                    {"source_url": " https://example.com/docs"},
                    {"source_url": "https://-invalid.example/docs"},
                    {"source_url": "https://999.999.999.999/docs"},
                    {"source_url": "https://example.com", "max_chunks": 0},
                    {"source_url": "https://example.com", "max_pages_or_files": 120_001},
                    {"source_url": "https://example.com", "include_paths": [""]},
                    {"source_url": "https://example.com", "unknown": "value"},
                ]
                for payload in invalid_payloads:
                    with self.subTest(payload=payload):
                        response = client.post("/api/v1/plan-jobs", headers=good, json=payload)
                        self.assertEqual(response.status_code, 422, response.text)
                        self.assertIn("error", response.json())

        self.assertEqual(conflicting_origin.status_code, 403)
        self.assertEqual(wrong_type.status_code, 415)
        self.assertEqual(oversized.status_code, 413)
        self.assertEqual(hostile_host.status_code, 400)
        self.assertEqual(service.starts, [])

    def test_malformed_authorities_return_422_before_record_output_or_executor(self) -> None:
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
            "https://[v1.fe]/docs",
        )
        executor = Mock()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            app = create_app(
                artifacts_root=root / "artifacts",
                state_root=root / "state",
                local_inventory=FakeInventory(),
                plan_job_service_factory=lambda: PlanJobService(
                    state_root=root / "state",
                    artifacts_root=root / "artifacts",
                    executor=executor,
                ),
            )
            with TestClient(app, base_url="http://localhost", raise_server_exceptions=False) as client:
                token = client.get("/api/v1/csrf-token").json()["csrf_token"]
                headers = {CSRF_HEADER: token, "Origin": "http://localhost"}
                for source_url in malformed_urls:
                    with self.subTest(source_url=source_url):
                        response = client.post(
                            "/api/v1/plan-jobs",
                            headers=headers,
                            json={"source_url": source_url},
                        )
                        self.assertEqual(response.status_code, 422, response.text)
            executor.submit.assert_not_called()
            self.assertEqual(
                list((root / "state/command-center/jobs").glob("*.json")), []
            )
            self.assertEqual(
                list((root / "state/command-center/jobs").glob("*.events.jsonl")), []
            )
            self.assertEqual(
                list((root / "artifacts/command-center/plans").iterdir()), []
            )

    def test_direct_asgi_rejects_oversized_stream_without_content_length(self) -> None:
        service = FakePlanJobService()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app = create_app(
                artifacts_root=root / "artifacts",
                state_root=root / "state",
                local_inventory=FakeInventory(),
                plan_job_service_factory=lambda: service,
            )
            with TestClient(app, base_url="http://localhost") as client:
                token = client.get("/api/v1/csrf-token").json()["csrf_token"]
                sent = asyncio.run(
                    _direct_asgi_request(
                        app,
                        method="POST",
                        path="/api/v1/plan-jobs",
                        headers=[
                            (b"host", b"localhost"),
                            (b"origin", b"http://localhost"),
                            (CSRF_HEADER.casefold().encode("ascii"), token.encode("ascii")),
                            (b"content-type", b"application/json"),
                        ],
                        chunks=[
                            b" " * (MAX_PLAN_JOB_BODY_BYTES // 2),
                            b" " * (MAX_PLAN_JOB_BODY_BYTES // 2 + 1),
                        ],
                    )
                )

        start = next(message for message in sent if message["type"] == "http.response.start")
        body = b"".join(
            message.get("body", b"")  # type: ignore[arg-type]
            for message in sent
            if message["type"] == "http.response.body"
        )
        self.assertEqual(start["status"], 413)
        self.assertEqual(json.loads(body)["error"]["code"], "request_body_too_large")
        self.assertEqual(service.starts, [])

    def test_creation_origin_ipv6_ports_and_null_are_fail_closed(self) -> None:
        def create(host: str, origin: str) -> int:
            with tempfile.TemporaryDirectory() as tmp:
                service = FakePlanJobService()
                app = create_app(
                    artifacts_root=Path(tmp) / "artifacts",
                    state_root=Path(tmp) / "state",
                    local_inventory=FakeInventory(),
                    plan_job_service_factory=lambda: service,
                )
                with TestClient(app, base_url="http://localhost") as client:
                    token = client.get("/api/v1/csrf-token").json()["csrf_token"]
                    return client.post(
                        "/api/v1/plan-jobs",
                        headers={CSRF_HEADER: token, "Origin": origin, "Host": host},
                        json={"source_url": "https://example.com/docs"},
                    ).status_code

        self.assertEqual(create("[::1]:8765", "http://[::1]:8765"), 202)
        self.assertEqual(create("localhost", "http://localhost:80"), 202)
        self.assertEqual(create("localhost:8765", "http://localhost"), 403)
        self.assertEqual(create("localhost", "null"), 403)

    def test_csrf_rejection_does_not_log_token_or_headers(self) -> None:
        service = FakePlanJobService()
        with tempfile.TemporaryDirectory() as tmp:
            app = create_app(
                artifacts_root=Path(tmp) / "artifacts",
                state_root=Path(tmp) / "state",
                local_inventory=FakeInventory(),
                plan_job_service_factory=lambda: service,
            )
            with TestClient(app, base_url="http://localhost") as client, patch(
                "buoy_search.command_center_api._LOGGER.error"
            ) as logged:
                token = client.get("/api/v1/csrf-token").json()["csrf_token"]
                response = client.post(
                    "/api/v1/plan-jobs",
                    headers={CSRF_HEADER: token, "Origin": "null"},
                    json={"source_url": "https://example.com/docs"},
                )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(logged.call_args_list, [])
        self.assertNotIn(token, response.text)

    def test_plan_creation_conflict_identifies_active_job_without_second_start(self) -> None:
        service = FakePlanJobService(conflict=True)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app = create_app(
                artifacts_root=root / "artifacts",
                state_root=root / "state",
                local_inventory=FakeInventory(),
                plan_job_service_factory=lambda: service,
            )
            with TestClient(app, base_url="http://localhost", raise_server_exceptions=False) as client:
                token = client.get("/api/v1/csrf-token").json()["csrf_token"]
                response = client.post(
                    "/api/v1/plan-jobs",
                    headers={CSRF_HEADER: token, "Origin": "http://localhost"},
                    json={"source_url": "https://example.com/docs"},
                )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "active_job_conflict")
        self.assertEqual(
            response.json()["error"]["details"]["active_job_id"],
            "planjob_" + "a" * 32,
        )
        self.assertEqual(service.starts, [])

    def test_plan_job_list_detail_not_found_and_pagination_bounds(self) -> None:
        service = FakePlanJobService()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app = create_app(
                artifacts_root=root / "artifacts",
                state_root=root / "state",
                local_inventory=FakeInventory(),
                plan_job_service_factory=lambda: service,
            )
            with TestClient(app, base_url="http://localhost", raise_server_exceptions=False) as client:
                token = client.get("/api/v1/csrf-token").json()["csrf_token"]
                created = client.post(
                    "/api/v1/plan-jobs",
                    headers={CSRF_HEADER: token, "Origin": "http://localhost"},
                    json={"source_url": "https://example.com/docs"},
                ).json()
                listing = client.get("/api/v1/plan-jobs?offset=0&limit=1")
                detail = client.get(f"/api/v1/plan-jobs/{created['job_id']}")
                missing = client.get("/api/v1/plan-jobs/planjob_" + "c" * 32)
                invalid = client.get("/api/v1/plan-jobs?limit=101")
                excessive_offset = client.get("/api/v1/plan-jobs?offset=1001&limit=1")
                maximum_offset = client.get("/api/v1/plan-jobs?offset=1000&limit=1")

        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()["total"], 1)
        self.assertEqual(listing.json()["items"][0]["plan_id"], "plan-fake")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["state"], "succeeded")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()["error"]["code"], "job_not_found")
        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(excessive_offset.status_code, 422)
        self.assertEqual(excessive_offset.json()["error"]["code"], "invalid_pagination")
        self.assertEqual(maximum_offset.status_code, 200)
        self.assertEqual(maximum_offset.json()["items"], [])

    def test_external_job_ids_return_404_before_valid_id_integrity_maps_to_503(self) -> None:
        class IntegrityService(FakePlanJobService):
            def __init__(self) -> None:
                super().__init__()
                self.get_calls: list[str] = []

            def get(self, job_id: str) -> PlanJob:
                self.get_calls.append(job_id)
                raise JobIntegrityError("corrupt durable record")

        service = IntegrityService()
        valid_id = "planjob_" + "a" * 32
        with tempfile.TemporaryDirectory() as tmp:
            app = create_app(
                artifacts_root=Path(tmp) / "artifacts",
                state_root=Path(tmp) / "state",
                local_inventory=FakeInventory(),
                plan_job_service_factory=lambda: service,
            )
            with TestClient(app, base_url="http://localhost", raise_server_exceptions=False) as client:
                malformed_detail = client.get("/api/v1/plan-jobs/not-a-job-id")
                malformed_events = client.get("/api/v1/plan-jobs/not-a-job-id/events")
                corrupt_detail = client.get(f"/api/v1/plan-jobs/{valid_id}")
                corrupt_events = client.get(f"/api/v1/plan-jobs/{valid_id}/events")

        for response in (malformed_detail, malformed_events):
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json()["error"]["code"], "job_not_found")
        for response in (corrupt_detail, corrupt_events):
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json()["error"]["code"], "job_service_unavailable")
        self.assertEqual(service.get_calls, [valid_id, valid_id])

    def test_sse_replays_history_honors_sequence_streams_live_terminal_and_closes(self) -> None:
        service = FakePlanJobService(live=True)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app = create_app(
                artifacts_root=root / "artifacts",
                state_root=root / "state",
                local_inventory=FakeInventory(),
                plan_job_service_factory=lambda: service,
            )
            with TestClient(app, base_url="http://localhost", raise_server_exceptions=False) as client:
                token = client.get("/api/v1/csrf-token").json()["csrf_token"]
                job_id = client.post(
                    "/api/v1/plan-jobs",
                    headers={CSRF_HEADER: token, "Origin": "http://localhost"},
                    json={"source_url": "https://example.com/docs"},
                ).json()["job_id"]
                streamed = client.get(f"/api/v1/plan-jobs/{job_id}/events")
                reconnected = client.get(
                    f"/api/v1/plan-jobs/{job_id}/events",
                    headers={"Last-Event-ID": "1"},
                )
                query_reconnected = client.get(
                    f"/api/v1/plan-jobs/{job_id}/events?after_sequence=2"
                )
                conflict = client.get(
                    f"/api/v1/plan-jobs/{job_id}/events?after_sequence=0",
                    headers={"Last-Event-ID": "1"},
                )
                invalid_sequence = client.get(
                    f"/api/v1/plan-jobs/{job_id}/events?after_sequence=-1"
                )
                missing = client.get(
                    "/api/v1/plan-jobs/planjob_" + "e" * 32 + "/events"
                )

        self.assertEqual(streamed.status_code, 200)
        self.assertTrue(streamed.headers["content-type"].startswith("text/event-stream"))
        self.assertEqual(streamed.text.count("id: 1\n"), 1)
        self.assertEqual(streamed.text.count("id: 2\n"), 1)
        self.assertIn('"stage":"succeeded"', streamed.text)
        self.assertNotIn("id: 1\n", reconnected.text)
        self.assertEqual(reconnected.text.count("id: 2\n"), 1)
        self.assertEqual(query_reconnected.text, "")
        self.assertEqual(conflict.status_code, 200)
        self.assertNotIn("id: 1\n", conflict.text)
        self.assertEqual(conflict.text.count("id: 2\n"), 1)
        self.assertEqual(invalid_sequence.status_code, 422)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(len(service.starts), 1)

    def test_sse_terminal_timeout_race_performs_final_durable_drain(self) -> None:
        service = TerminalRaceService()
        worker = Thread(target=service.commit_terminal)
        worker.start()
        frames = list(_sse_events(service, "planjob_" + "a" * 32, 0))
        worker.join(5)

        self.assertFalse(worker.is_alive())
        self.assertEqual(len(frames), 1)
        self.assertIn(b"id: 1\n", frames[0])
        self.assertIn(b'"stage":"succeeded"', frames[0])

    def test_direct_asgi_disconnect_stops_sse_iteration(self) -> None:
        service = IteratorProbeService(10)
        with tempfile.TemporaryDirectory() as tmp:
            app = create_app(
                artifacts_root=Path(tmp) / "artifacts",
                state_root=Path(tmp) / "state",
                local_inventory=FakeInventory(),
                plan_job_service_factory=lambda: service,
            )
            app.state.plan_job_service = service
            sent = asyncio.run(
                _direct_asgi_disconnect(
                    app,
                    "/api/v1/plan-jobs/planjob_" + "a" * 32 + "/events",
                )
            )

        self.assertEqual(sent[0]["type"], "http.response.start")
        self.assertEqual(sent[0]["status"], 200)
        self.assertGreaterEqual(service.iterated, 1)
        self.assertLess(service.iterated, 10)
        self.assertTrue(service.closed)

    def test_sse_iterator_is_lazy_closable_and_caps_each_connection(self) -> None:
        slow = IteratorProbeService(2)
        iterator = _sse_events(slow, "planjob_" + "a" * 32, 0)
        self.assertEqual(slow.iterated, 0)
        first = next(iterator)
        self.assertIn(b"id: 1\n", first)
        self.assertEqual(slow.iterated, 1)
        iterator.close()
        self.assertTrue(slow.closed)
        self.assertEqual(slow.iterated, 1)

        oversized = IteratorProbeService(MAX_SSE_EVENTS_PER_CONNECTION + 1)
        frames = list(_sse_events(oversized, "planjob_" + "b" * 32, 0))
        self.assertEqual(len(frames), MAX_SSE_EVENTS_PER_CONNECTION)
        self.assertIn(b"id: 1000\n", frames[-1])
        self.assertNotIn(b"id: 1001\n", b"".join(frames))

    def test_lifespan_interrupts_persisted_active_job_without_starting_work(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            state_root = root / "state"
            artifacts_root = root / "artifacts"
            store = PlanJobStore(state_root)
            job_id = "planjob_" + "d" * 32
            store.create(
                job_id=job_id,
                source_kind="website",
                source_url="https://example.com/docs",
                namespace=None,
                artifact_path=f"command-center/plans/{job_id}",
                request_summary=JobRequestSummary(None, None, None, 0, 0),
            )
            planning = NeverCalledPlanningService()
            app = create_app(
                artifacts_root=artifacts_root,
                state_root=state_root,
                local_inventory=FakeInventory(),
                plan_job_service_factory=lambda: PlanJobService(
                    state_root=state_root,
                    artifacts_root=artifacts_root,
                    planning_service=planning,
                ),
            )
            with TestClient(app, base_url="http://localhost", raise_server_exceptions=False) as client:
                detail = client.get(f"/api/v1/plan-jobs/{job_id}")

        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual(detail.json()["state"], "interrupted")
        self.assertEqual(detail.json()["error"]["code"], "job_interrupted")
        self.assertEqual(planning.calls, [])

    def test_api_method_surface_adds_only_bounded_plan_creation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app, _ = self.make_client(Path(tmp), local_inventory=FakeInventory())
        methods = {
            (route.path, method)
            for route in app.routes
            for method in getattr(route, "methods", set())
            if route.path.startswith("/api/v1")
        }
        self.assertEqual(
            {path for path, method in methods if method == "POST"},
            {"/api/v1/remote/snapshot", "/api/v1/search", "/api/v1/plan-jobs"},
        )
        self.assertFalse(any(method in {"PUT", "PATCH", "DELETE"} for _path, method in methods))

    def test_structured_lookup_validation_and_unknown_api_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            static = Path(tmp) / "static"
            static.mkdir()
            (static / "index.html").write_text("<h1>frontend</h1>", encoding="utf-8")
            _, client = self.make_client(
                Path(tmp),
                static_root=static,
                local_inventory=FakeInventory(),
            )
            missing = client.get("/api/v1/namespaces/missing")
            invalid = client.get("/api/v1/plans?offset=not-an-int")
            unknown = client.get("/api/v1/not-a-route")

        self.assertEqual(missing.status_code, 404)
        self.assertEqual(
            missing.json(),
            {"error": {"code": "namespace_not_found", "message": "Namespace was not found."}},
        )
        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(invalid.json()["error"]["code"], "invalid_request")
        self.assertNotIn("not-an-int", json.dumps(invalid.json()))
        self.assertEqual(unknown.status_code, 404)
        self.assertEqual(unknown.json()["error"]["code"], "api_route_not_found")
        self.assertNotIn("frontend", unknown.text)

    def test_static_assets_spa_fallback_and_security_headers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            static = root / "static"
            (static / "assets").mkdir(parents=True)
            (static / "index.html").write_text("<h1>frontend</h1>", encoding="utf-8")
            (static / "assets" / "app.js").write_text("console.log('ok')", encoding="utf-8")
            _, client = self.make_client(root, static_root=static, local_inventory=FakeInventory())

            asset = client.get("/assets/app.js")
            fallback = client.get("/plans/plan-1")
            health = client.get("/api/v1/health")

        self.assertEqual(asset.status_code, 200)
        self.assertIn("console.log", asset.text)
        self.assertEqual(fallback.status_code, 200)
        self.assertIn("frontend", fallback.text)
        for response in (asset, fallback, health):
            for name, value in SECURITY_HEADERS.items():
                self.assertEqual(response.headers[name], value)
        self.assertNotIn("access-control-allow-origin", health.headers)

    def test_missing_static_assets_return_structured_response(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _, client = self.make_client(
                Path(tmp),
                static_root=Path(tmp) / "missing",
                local_inventory=FakeInventory(),
            )
            response = client.get("/")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "ui_assets_unavailable")

    def test_server_opens_browser_by_default_and_formats_ipv6_url(self) -> None:
        opened: list[str] = []
        runs: list[tuple[object, dict[str, object]]] = []
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_server(
                host="::1",
                port=8765,
                artifacts_root=root / "artifacts",
                state_root=root / "state",
                open_browser=True,
                static_root=root / "static",
                browser_opener=opened.append,
                uvicorn_runner=lambda app, **kwargs: runs.append((app, kwargs)),
            )

        self.assertEqual(opened, ["http://[::1]:8765/"])
        self.assertEqual(runs[0][1], {"host": "::1", "port": 8765})

    def test_server_no_browser_does_not_invoke_opener(self) -> None:
        opened: list[str] = []
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_server(
                host="localhost",
                port=9876,
                artifacts_root=root / "artifacts",
                state_root=root / "state",
                open_browser=False,
                browser_opener=opened.append,
                uvicorn_runner=lambda _app, **_kwargs: None,
            )
        self.assertEqual(opened, [])

    def test_default_server_signal_announces_active_job_shutdown_once(self) -> None:
        stderr = StringIO()

        class FakeService:
            calls = 0

            def announce_shutdown(self) -> None:
                import logging

                self.calls += 1
                logging.getLogger("buoy_search.command_center_jobs").warning("safe shutdown warning")

        service = FakeService()

        class FakeConfig:
            def __init__(self, app, **_kwargs) -> None:  # noqa: ANN001, ANN003 - uvicorn fake.
                self.app = app

        class FakeServer:
            def __init__(self, config) -> None:  # noqa: ANN001 - uvicorn fake.
                self.config = config

            def handle_exit(self, _sig, _frame) -> None:  # noqa: ANN001 - signal protocol.
                return None

            def run(self) -> None:
                self.config.app.state.plan_job_service = service
                self.handle_exit(signal.SIGTERM, None)

        with tempfile.TemporaryDirectory() as tmp, redirect_stderr(stderr), patch(
            "uvicorn.Config", FakeConfig
        ), patch("uvicorn.Server", FakeServer):
            root = Path(tmp)
            run_server(
                host="127.0.0.1",
                port=8765,
                artifacts_root=root / "artifacts",
                state_root=root / "state",
                open_browser=False,
            )

        self.assertEqual(service.calls, 1)
        self.assertEqual(stderr.getvalue().count("WARNING: safe shutdown warning"), 1)

    def test_app_startup_is_remote_provider_model_and_source_adapter_inert(self) -> None:
        source_root = Path(__file__).resolve().parents[1] / "src"
        script = """
import asyncio
import json
import sys
import tempfile
from pathlib import Path
from buoy_search.command_center_api import create_app
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp).resolve()
    app = create_app(artifacts_root=root / 'artifacts', state_root=root / 'state')
    from fastapi.testclient import TestClient
    with TestClient(app, base_url='http://localhost') as client:
        capabilities = client.get('/api/v1/capabilities').json()
    assert capabilities['turbopuffer_credentials_available'] is False
watched = [
    'buoy_search.command_center_remote', 'buoy_search.crawler',
    'buoy_search.database_relation', 'buoy_search.planning_service',
    'buoy_search.github_repo', 'buoy_search.duckdb_relation',
    'buoy_search.bigquery_relation', 'buoy_search.snowflake_relation',
    'turbopuffer', 'sentence_transformers', 'transformers',
    'google.cloud.bigquery', 'snowflake.connector',
]
print(json.dumps({name: name in sys.modules for name in watched}, sort_keys=True))
"""
        completed = subprocess.run(
            [sys.executable, "-c", script],
            check=True,
            capture_output=True,
            text=True,
            env={"PYTHONPATH": str(source_root)},
        )
        self.assertEqual(set(json.loads(completed.stdout).values()), {False})


if __name__ == "__main__":
    unittest.main()
