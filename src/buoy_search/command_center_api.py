"""Lazy optional FastAPI application for the local read-only command center."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from importlib.metadata import PackageNotFoundError, version
import os
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from buoy_search import __version__
from buoy_search.command_center_local import InventoryLookupError, LocalInventoryService

API_PREFIX = "/api/v1"
DEFAULT_STATIC_ROOT = Path(__file__).with_name("command_center_static")
ALLOWED_HOSTS = {"127.0.0.1", "localhost", "::1"}
POST_GUARD_HEADER = "X-Buoy-Command-Center"
POST_GUARD_VALUE = "1"
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; base-uri 'none'; frame-ancestors 'none'; "
        "form-action 'none'; object-src 'none'; script-src 'self'; "
        "style-src 'self'; img-src 'self' data:; connect-src 'self'"
    ),
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}


class SearchPayload(BaseModel):
    query: str
    namespaces: list[str] = Field(default_factory=list)
    automatic: bool = False
    route_top_k: int = 3
    top_k: int = 5
    candidates: int = 200
    doc_kind: str | None = None
    ranking_mode: str | None = None
    ranking_profile: str | None = None
    ranking_pool: int | None = None
    ranking_aggregation: str | None = None

    class Config:
        extra = "forbid"


def _error(
    code: str,
    message: str,
    *,
    status_code: int,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    error: dict[str, Any] = {"code": code, "message": message}
    if details:
        error["details"] = details
    return JSONResponse({"error": error}, status_code=status_code)


def _service_payload(value: object) -> Any:
    payload = asdict(value) if is_dataclass(value) else value
    if isinstance(payload, dict) and isinstance(payload.get("error"), dict):
        service_error = payload["error"]
        safe_error: dict[str, Any] = {
            "code": str(service_error.get("code", "service_error")),
            "message": str(service_error.get("message", "The request could not be completed.")),
        }
        phase = service_error.get("phase")
        if isinstance(phase, str) and phase:
            safe_error["details"] = {"phase": phase}
        payload["error"] = safe_error
    return jsonable_encoder(payload)


def _validation_details(exc: RequestValidationError) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    for issue in exc.errors()[:20]:
        location = ".".join(str(part) for part in issue.get("loc", ()) if part != "body")
        issues.append(
            {
                "location": location or "request",
                "message": str(issue.get("msg", "Invalid value."))[:200],
                "type": str(issue.get("type", "validation_error"))[:100],
            }
        )
    return {"issues": issues}


def _origin_matches_request(origin: str, request: Request) -> bool:
    try:
        parsed = urlsplit(origin)
        origin_port = parsed.port or (443 if parsed.scheme == "https" else 80)
        request_port = request.url.port or (443 if request.url.scheme == "https" else 80)
    except ValueError:
        return False
    return (
        parsed.scheme == request.url.scheme
        and (parsed.hostname or "").lower() == (request.url.hostname or "").lower()
        and origin_port == request_port
    )


def _distribution_available(distribution: str) -> bool:
    try:
        version(distribution)
    except PackageNotFoundError:
        return False
    return True


def _available_directory(path: Path) -> bool:
    return not path.is_symlink() and path.is_dir()


def _safe_static_file(root: Path, requested: str) -> Path | None:
    if root.is_symlink() or not root.is_dir():
        return None
    relative = Path(requested)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        return None
    candidate = root.joinpath(relative)
    try:
        candidate.resolve(strict=False).relative_to(root.resolve(strict=False))
    except (OSError, ValueError):
        return None
    if candidate.is_symlink() or not candidate.is_file():
        return None
    return candidate


def create_app(
    *,
    artifacts_root: Path,
    state_root: Path,
    static_root: Path | None = None,
    local_inventory: object | None = None,
    remote_snapshot_service: object | None = None,
    search_service: object | None = None,
    remote_snapshot_factory: Callable[[], object] | None = None,
    search_factory: Callable[[], object] | None = None,
) -> FastAPI:
    """Create the API without constructing remote clients, retrievers, or models."""

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    inventory = local_inventory or LocalInventoryService(
        artifacts_root=artifacts_root,
        state_root=state_root,
    )
    frontend_root = Path(static_root) if static_root is not None else DEFAULT_STATIC_ROOT

    @app.middleware("http")
    async def local_request_boundary(request: Request, call_next: Callable[..., Any]):
        host = (request.url.hostname or "").lower()
        if host not in ALLOWED_HOSTS:
            response = _error(
                "invalid_host",
                "Command Center accepts requests only through a loopback host.",
                status_code=400,
            )
        elif request.method == "POST" and request.url.path in {
            f"{API_PREFIX}/remote/snapshot",
            f"{API_PREFIX}/search",
        }:
            origin = request.headers.get("origin")
            same_origin = _origin_matches_request(origin, request) if origin else True
            if (
                request.headers.get(POST_GUARD_HEADER) != POST_GUARD_VALUE
                or request.headers.get("sec-fetch-site", "same-origin") not in {"same-origin", "none"}
                or not same_origin
            ):
                response = _error(
                    "request_forbidden",
                    "The explicit local operation was rejected.",
                    status_code=403,
                )
            else:
                response = await call_next(request)
        else:
            response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers[name] = value
        return response

    @app.exception_handler(InventoryLookupError)
    async def inventory_error(_request: Request, exc: InventoryLookupError) -> JSONResponse:
        status = 404 if exc.code.endswith("_not_found") else 400
        return _error(exc.code, exc.message, status_code=status)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return _error(
            "invalid_request",
            "The request parameters are invalid.",
            status_code=422,
            details=_validation_details(exc),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == 404 and request.url.path.startswith("/api/"):
            return _error("api_route_not_found", "API route was not found.", status_code=404)
        if exc.status_code == 405:
            return _error("method_not_allowed", "HTTP method is not allowed.", status_code=405)
        return _error("route_not_found", "Route was not found.", status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def unexpected_error(_request: Request, _exc: Exception) -> JSONResponse:
        return _error(
            "internal_error",
            "The request could not be completed.",
            status_code=500,
        )

    @app.get(f"{API_PREFIX}/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "api_version": "v1", "buoy_version": __version__}

    @app.get(f"{API_PREFIX}/capabilities")
    async def capabilities() -> dict[str, object]:
        return {
            "api_version": "v1",
            "buoy_version": __version__,
            "loopback_only": True,
            "read_only": True,
            "remote_snapshot": True,
            "search": True,
            "mutations": False,
            "artifacts_root_available": _available_directory(Path(artifacts_root)),
            "state_root_available": _available_directory(Path(state_root)),
            "turbopuffer_credentials_available": bool(os.environ.get("TURBOPUFFER_API_KEY")),
            "ui_build_available": _safe_static_file(frontend_root, "index.html") is not None,
            "bigquery_extra_installed": _distribution_available("google-cloud-bigquery"),
            "snowflake_extra_installed": _distribution_available("snowflake-connector-python"),
        }

    @app.get(f"{API_PREFIX}/dashboard")
    async def dashboard(recent_limit: int = 10) -> Any:
        return _service_payload(inventory.dashboard(recent_limit=recent_limit))  # type: ignore[attr-defined]

    @app.get(f"{API_PREFIX}/namespaces")
    async def namespaces(offset: int = 0, limit: int = 50) -> Any:
        return _service_payload(inventory.list_namespaces(offset=offset, limit=limit))  # type: ignore[attr-defined]

    @app.get(f"{API_PREFIX}/namespaces/{{namespace}}")
    async def namespace_detail(namespace: str) -> Any:
        return _service_payload(inventory.get_namespace(namespace))  # type: ignore[attr-defined]

    @app.get(f"{API_PREFIX}/plans")
    async def plans(offset: int = 0, limit: int = 50) -> Any:
        return _service_payload(inventory.list_plans(offset=offset, limit=limit))  # type: ignore[attr-defined]

    @app.get(f"{API_PREFIX}/plans/{{plan_id}}")
    async def plan_detail(plan_id: str) -> Any:
        return _service_payload(inventory.get_plan(plan_id))  # type: ignore[attr-defined]

    @app.get(f"{API_PREFIX}/plans/{{plan_id}}/pages")
    async def plan_pages(plan_id: str, offset: int = 0, limit: int = 50) -> Any:
        return _service_payload(
            inventory.list_plan_pages(plan_id, offset=offset, limit=limit)  # type: ignore[attr-defined]
        )

    @app.get(f"{API_PREFIX}/plans/{{plan_id}}/pages/{{page_index}}")
    async def plan_page(plan_id: str, page_index: int, max_chars: int = 20_000) -> Any:
        return _service_payload(
            inventory.get_plan_page(plan_id, page_index, max_chars=max_chars)  # type: ignore[attr-defined]
        )

    @app.get(f"{API_PREFIX}/plans/{{plan_id}}/chunks")
    async def plan_chunks(
        plan_id: str,
        offset: int = 0,
        limit: int = 50,
        max_chars: int = 2_000,
    ) -> Any:
        return _service_payload(
            inventory.list_plan_chunks(  # type: ignore[attr-defined]
                plan_id,
                offset=offset,
                limit=limit,
                max_chars=max_chars,
            )
        )

    def remote_service() -> object:
        nonlocal remote_snapshot_service
        if remote_snapshot_service is None:
            if remote_snapshot_factory is not None:
                remote_snapshot_service = remote_snapshot_factory()
            else:
                from buoy_search.command_center_remote import RemoteSnapshotService
                from buoy_search.config import load_config

                remote_snapshot_service = RemoteSnapshotService(
                    local_inventory=inventory,
                    config=load_config(),
                )
        return remote_snapshot_service

    def searcher() -> object:
        nonlocal search_service
        if search_service is None:
            if search_factory is not None:
                search_service = search_factory()
            else:
                from buoy_search.command_center_remote import SearchService
                from buoy_search.config import load_config

                search_service = SearchService(config=load_config())
        return search_service

    @app.post(f"{API_PREFIX}/remote/snapshot")
    async def refresh_remote_snapshot() -> Any:
        return _service_payload(remote_service().refresh())  # type: ignore[attr-defined]

    @app.post(f"{API_PREFIX}/search")
    async def search(payload: SearchPayload) -> Any:
        from buoy_search.command_center_remote import SearchRequest

        request = SearchRequest(
            query=payload.query,
            namespaces=tuple(payload.namespaces),
            automatic=payload.automatic,
            route_top_k=payload.route_top_k,
            top_k=payload.top_k,
            candidates=payload.candidates,
            doc_kind=payload.doc_kind,
            ranking_mode=payload.ranking_mode,
            ranking_profile=payload.ranking_profile,
            ranking_pool=payload.ranking_pool,
            ranking_aggregation=payload.ranking_aggregation,
        )
        return _service_payload(searcher().execute(request))  # type: ignore[attr-defined]

    @app.get("/{path:path}")
    async def frontend(path: str) -> Any:
        if path == "api" or path.startswith("api/"):
            return _error("api_route_not_found", "API route was not found.", status_code=404)
        requested = path or "index.html"
        asset = _safe_static_file(frontend_root, requested)
        if asset is not None:
            return FileResponse(asset)
        index = _safe_static_file(frontend_root, "index.html")
        if index is not None:
            return FileResponse(index, media_type="text/html")
        return _error(
            "ui_assets_unavailable",
            "Command Center frontend assets are not installed.",
            status_code=503,
        )

    return app
