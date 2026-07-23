from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

UI_AVAILABLE = importlib.util.find_spec("fastapi") is not None and importlib.util.find_spec("httpx") is not None

if UI_AVAILABLE:
    from fastapi.testclient import TestClient

    from buoy_search.command_center_api import POST_GUARD_HEADER, POST_GUARD_VALUE, SECURITY_HEADERS, create_app
    from buoy_search.command_center_local import InventoryLookupError
    from buoy_search.command_center_server import run_server


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

        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["status"], "ok")
        self.assertEqual(health.json()["api_version"], "v1")
        self.assertTrue(capabilities.json()["read_only"])
        self.assertFalse(capabilities.json()["mutations"])
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
        self.assertEqual(remote.calls, 0)
        self.assertEqual(search.requests, [])

    def test_api_method_surface_has_only_two_guarded_read_only_posts(self) -> None:
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
            {"/api/v1/remote/snapshot", "/api/v1/search"},
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
    root = Path(tmp)
    app = create_app(artifacts_root=root / 'artifacts', state_root=root / 'state')
    endpoint = next(route.endpoint for route in app.routes if route.path == '/api/v1/capabilities')
    capabilities = asyncio.run(endpoint())
    assert capabilities['turbopuffer_credentials_available'] is False
watched = [
    'buoy_search.command_center_remote', 'buoy_search.bigquery_relation',
    'buoy_search.snowflake_relation', 'turbopuffer', 'sentence_transformers',
    'transformers', 'google.cloud.bigquery', 'snowflake.connector',
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
