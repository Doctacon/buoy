from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Thread
import unittest
from unittest.mock import Mock, patch

UI_AVAILABLE = importlib.util.find_spec("fastapi") is not None and importlib.util.find_spec("httpx") is not None

if UI_AVAILABLE:
    from fastapi.testclient import TestClient

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
    )
    from buoy_search.command_center_local import InventoryLookupError
    from buoy_search.command_center_server import run_server
    from buoy_search.planning_service import validate_managed_public_source


class FakeInventory:
    def dashboard(self, *, recent_limit: int = 10):
        return {"resource": "dashboard", "recent_limit": recent_limit}

    def list_namespaces(self, *, offset: int = 0, limit: int = 50):
        return {"resource": "namespaces", "offset": offset, "limit": limit}

    def get_namespace(self, namespace: str):
        if namespace == "missing":
            raise InventoryLookupError("namespace_not_found", "Namespace was not found.")
        return {"resource": "namespace", "namespace": namespace}

    def list_plans(self, *, offset: int = 0, limit: int = 50):
        return {"resource": "plans", "offset": offset, "limit": limit}

    def get_plan(self, plan_id: str):
        return {"resource": "plan", "plan_id": plan_id}

    def list_plan_pages(self, plan_id: str, *, offset: int = 0, limit: int = 50):
        return {"resource": "pages", "plan_id": plan_id, "offset": offset, "limit": limit}

    def get_plan_page(self, plan_id: str, index: int, *, max_chars: int = 20_000):
        return {"resource": "page", "plan_id": plan_id, "index": index, "max_chars": max_chars}

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
            "Read-only reviews plus bounded local public-source planning.",
        )
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["status"], "ok")
        self.assertEqual(health.json()["api_version"], "v1")
        self.assertTrue(capabilities.json()["review_routes_read_only"])
        self.assertTrue(capabilities.json()["local_plan_job_creation"])
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

    def test_non_empty_local_service_contract_is_serialized_through_fastapi(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_dir = root / "artifacts" / "plan-contract"
            plan_dir.mkdir(parents=True)
            plan = {
                "command": "plan",
                "plan_id": "plan-contract",
                "namespace": "docs-contract",
                "namespace_candidate": "docs-contract",
                "site_id": "docs-contract",
                "created_at": "2026-07-23T12:00:00+00:00",
                "base_url": "https://example.test/docs",
                "embedding_model": "BAAI/bge-small-en-v1.5",
                "embedding_precision": "float32",
                "artifact_hash": "a" * 64,
                "diff": {
                    "first_apply": True,
                    "pages_added": 1,
                    "pages_changed": 0,
                    "pages_unchanged": 0,
                    "pages_removed": 0,
                    "chunks_unchanged": 0,
                    "chunks_to_embed": 1,
                    "rows_to_upsert": 1,
                    "stale_rows": 0,
                    "retained_stale_rows": 0,
                },
            }
            page = {
                "canonical_url": "https://example.test/docs/page",
                "title": "Contract page",
                "content_path": "page.md",
                "source_metadata": {},
            }
            chunk = {
                "row_id": "ts_contract",
                "canonical_url": page["canonical_url"],
                "content": "Contract content",
                "chunk_index": 0,
                "source_metadata": {},
            }
            manifest = {
                "namespace": plan["namespace"],
                "namespace_candidate": plan["namespace_candidate"],
                "site_id": plan["site_id"],
                "base_url": plan["base_url"],
                "pages": [page],
                "chunks": [chunk],
            }
            summary = {
                "plan_id": plan["plan_id"],
                "source_credentials_required": True,
                "source_api_calls_occurred": True,
                "originating_job_id": f"planjob_{'c' * 32}",
                "catalog_registration": {
                    "ranking_mode": "page",
                    "ranking_profile": "none",
                    "ranking_pool": 20,
                    "ranking_aggregation": "max",
                    "region": "aws-us-east-1",
                },
            }
            for name, payload in (
                ("plan.json", plan),
                ("manifest.json", manifest),
                ("summary.json", summary),
            ):
                (plan_dir / name).write_text(json.dumps(payload), encoding="utf-8")

            _, client = self.make_client(root)
            dashboard_response = client.get("/api/v1/dashboard")
            namespaces_response = client.get("/api/v1/namespaces")
            plans_response = client.get("/api/v1/plans")
            plan_response = client.get("/api/v1/plans/plan-contract")

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
            {"credentials_required": True, "api_calls_occurred": True},
        )

        namespace = namespaces_response.json()["items"][0]
        self.assertEqual(namespace["local_status"], "pending_changes")
        self.assertIsNone(namespace["retained_stale_rows"])
        self.assertEqual(namespace["latest_planned_upserts"], 1)
        self.assertEqual(namespace["latest_planned_stale_rows"], 0)
        self.assertEqual(namespace["document_count"], 1)
        self.assertEqual(namespace["chunk_count"], 1)
        self.assertEqual(namespace["latest_plan_id"], "plan-contract")
        self.assertIsNone(namespace["last_apply_id"])
        self.assertEqual(namespace["source"]["kind"], "website")

        plan_summary = plans_response.json()["items"][0]
        self.assertTrue(plan_summary["diff"]["first_apply"])
        self.assertEqual(plan_summary["diff"]["rows_to_upsert"], 1)
        self.assertEqual(
            plan_summary["source_activity"],
            {"credentials_required": True, "api_calls_occurred": True},
        )
        self.assertEqual(plan_response.json()["retrieval"]["region"], "aws-us-east-1")
        self.assertEqual(
            plan_response.json()["originating_job_id"], f"planjob_{'c' * 32}"
        )

    def test_all_inventory_detail_and_pagination_routes_delegate_to_service(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _, client = self.make_client(Path(tmp), local_inventory=FakeInventory())
            cases = [
                ("/api/v1/dashboard?recent_limit=4", "dashboard"),
                ("/api/v1/namespaces?offset=2&limit=3", "namespaces"),
                ("/api/v1/namespaces/site-example-v1", "namespace"),
                ("/api/v1/plans?offset=1&limit=2", "plans"),
                ("/api/v1/plans/plan-1", "plan"),
                ("/api/v1/plans/plan-1/pages?offset=2&limit=3", "pages"),
                ("/api/v1/plans/plan-1/pages/4?max_chars=123", "page"),
                ("/api/v1/plans/plan-1/chunks?offset=2&limit=3&max_chars=123", "chunks"),
            ]
            for path, resource in cases:
                with self.subTest(path=path):
                    response = client.get(path)
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(response.json()["resource"], resource)

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
