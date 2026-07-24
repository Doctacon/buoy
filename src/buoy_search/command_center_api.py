"""Local command center with read-only reviews and bounded local public-source planning."""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import asdict, is_dataclass
from importlib.metadata import PackageNotFoundError, version
import json
import logging
import os
from pathlib import Path
import re
import secrets
from typing import Any, Callable, Iterator
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from buoy_search import __version__
from buoy_search.command_center_local import InventoryLookupError, LocalInventoryService

API_PREFIX = "/api/v1"
DEFAULT_STATIC_ROOT = Path(__file__).with_name("command_center_static")
ALLOWED_HOSTS = {"127.0.0.1", "localhost", "::1"}
POST_GUARD_HEADER = "X-Buoy-Command-Center"
POST_GUARD_VALUE = "1"
CSRF_HEADER = "X-Buoy-CSRF-Token"
MAX_PLAN_JOB_BODY_BYTES = 16 * 1024
MAX_JOB_LIST_SIZE = 100
MAX_JOB_LIST_OFFSET = 1_000
MAX_SSE_EVENTS_PER_CONNECTION = 1_000
MAX_PATH_FILTERS = 100
MAX_PATH_FILTER_LENGTH = 500
MAX_NAMESPACE_LENGTH = 128
MAX_PLAN_ITEMS = 120_000
MANAGED_PLANNING_UNAVAILABLE_MESSAGE = (
    "Managed public-source planning is unavailable on this platform."
)
_SAFE_JOB_ID = re.compile(r"planjob_[0-9a-f]{32}")
_LOGGER = logging.getLogger(__name__)
_LOGGER.addHandler(logging.NullHandler())
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
        parsed.scheme in {"http", "https"}
        and parsed.path in {"", "/"}
        and not parsed.query
        and not parsed.fragment
        and parsed.username is None
        and parsed.password is None
        and parsed.scheme == request.url.scheme
        and (parsed.hostname or "").lower() == (request.url.hostname or "").lower()
        and origin_port == request_port
    )


def _header_values(request: Request, name: str) -> list[str]:
    key = name.casefold().encode("ascii")
    return [value.decode("latin-1") for header, value in request.scope["headers"] if header == key]


def _valid_loopback_host(value: str) -> bool:
    try:
        parsed = urlsplit(f"//{value}")
        parsed.port
    except ValueError:
        return False
    return (
        parsed.username is None
        and parsed.password is None
        and (parsed.hostname or "").casefold() in ALLOWED_HOSTS
        and parsed.path == ""
        and not parsed.query
        and not parsed.fragment
    )


async def _read_bounded_body(request: Request) -> bytes:
    content_lengths = _header_values(request, "content-length")
    if len(content_lengths) > 1:
        raise ValueError("invalid_content_length")
    content_length = content_lengths[0] if content_lengths else None
    declared: int | None = None
    if content_length is not None:
        try:
            declared = int(content_length)
        except ValueError as exc:
            raise ValueError("invalid_content_length") from exc
        if declared < 0:
            raise ValueError("invalid_content_length")
        if declared > MAX_PLAN_JOB_BODY_BYTES:
            raise OverflowError("request_body_too_large")
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_PLAN_JOB_BODY_BYTES:
            raise OverflowError("request_body_too_large")
        body.extend(chunk)
    if declared is not None and len(body) != declared:
        raise ValueError("invalid_content_length")
    return bytes(body)


def _parse_plan_job_request(body: bytes) -> object:
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for key, value in pairs:
            if key in payload:
                raise ValueError("JSON fields must not be repeated.")
            payload[key] = value
        return payload

    try:
        payload = json.loads(body.decode("utf-8"), object_pairs_hook=reject_duplicate_keys)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("The request body must contain a valid JSON object.") from exc
    if not isinstance(payload, dict):
        raise ValueError("The request body must contain a JSON object.")
    allowed = {
        "source_url",
        "max_pages_or_files",
        "max_chunks",
        "namespace",
        "include_paths",
        "exclude_paths",
    }
    if set(payload) - allowed:
        raise ValueError("The request body contains unsupported fields.")
    source_url = payload.get("source_url")
    if not isinstance(source_url, str):
        raise ValueError("source_url must be an HTTP(S) URL.")
    values: dict[str, Any] = {"source_url": source_url}
    for name in ("max_pages_or_files", "max_chunks"):
        value = payload.get(name)
        if value is not None and (
            type(value) is not int or value < 1 or value > MAX_PLAN_ITEMS
        ):
            raise ValueError(f"{name} must be between 1 and {MAX_PLAN_ITEMS}.")
        values[name] = value
    namespace = payload.get("namespace")
    if namespace is not None and (
        not isinstance(namespace, str) or not namespace or len(namespace) > MAX_NAMESPACE_LENGTH
    ):
        raise ValueError(
            f"namespace must be a non-empty string of at most {MAX_NAMESPACE_LENGTH} characters."
        )
    values["namespace"] = namespace
    for name in ("include_paths", "exclude_paths"):
        value = payload.get(name, [])
        if (
            not isinstance(value, list)
            or len(value) > MAX_PATH_FILTERS
            or any(
                not isinstance(item, str)
                or not item
                or len(item) > MAX_PATH_FILTER_LENGTH
                for item in value
            )
        ):
            raise ValueError(
                f"{name} must contain at most {MAX_PATH_FILTERS} non-empty bounded strings."
            )
        values[name] = tuple(value)
    from buoy_search.command_center_jobs import PlanJobRequest

    return PlanJobRequest(**values)


def _job_error_response(exc: Exception) -> JSONResponse:
    from buoy_search.command_center_jobs import (
        ActiveJobConflict,
        JobIntegrityError,
        JobNotFoundError,
        PlanJobError,
        ServiceOwnershipError,
    )

    if isinstance(exc, ActiveJobConflict):
        return _error(
            "active_job_conflict",
            "Another plan job is already active.",
            status_code=409,
            details={"active_job_id": exc.active_job_id},
        )
    if isinstance(exc, JobNotFoundError):
        return _error("job_not_found", "Plan job was not found.", status_code=404)
    if isinstance(exc, (ServiceOwnershipError, JobIntegrityError)):
        _LOGGER.error("Plan-job service operation failed (%s).", type(exc).__name__)
        return _error(
            "job_service_unavailable",
            "The local plan-job service is unavailable.",
            status_code=503,
        )
    if isinstance(exc, (ValueError, TypeError)):
        return _error(
            "invalid_plan_job_request",
            "The plan-job request is invalid.",
            status_code=422,
        )
    if isinstance(exc, PlanJobError):
        _LOGGER.error("Plan-job service operation failed (%s).", type(exc).__name__)
        return _error(
            "job_service_error",
            "The plan-job request could not be completed.",
            status_code=500,
        )
    _LOGGER.error("Command Center job request failed (%s).", type(exc).__name__)
    return _error(
        "job_service_error",
        "The plan-job request could not be completed.",
        status_code=500,
    )


def _parse_sequence(value: str | None) -> int:
    if value is None or value == "":
        return 0
    if not value.isascii() or not value.isdecimal():
        raise ValueError("Event sequence must be a non-negative integer.")
    sequence = int(value)
    if sequence > 9_223_372_036_854_775_807:
        raise ValueError("Event sequence is out of range.")
    return sequence


def _valid_job_id(job_id: str) -> bool:
    return _SAFE_JOB_ID.fullmatch(job_id) is not None


def _sse_frame(event: object) -> bytes:
    sequence = event.sequence  # type: ignore[attr-defined]
    data = json.dumps(
        event.to_dict(),  # type: ignore[attr-defined]
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return f"id: {sequence}\nevent: plan-job-event\ndata: {data}\n\n".encode("utf-8")


def _sse_events(service: object, job_id: str, after_sequence: int) -> Iterator[bytes]:
    from buoy_search.command_center_jobs import TERMINAL_STATES

    sequence = after_sequence
    emitted = 0
    while emitted < MAX_SSE_EVENTS_PER_CONNECTION:
        for event in service.observe_events(  # type: ignore[attr-defined]
            job_id, after_sequence=sequence, timeout=1.0
        ):
            sequence = event.sequence
            emitted += 1
            yield _sse_frame(event)
            if emitted >= MAX_SSE_EVENTS_PER_CONNECTION:
                return

        # Snapshot state before the final durable drain. A terminal transition can
        # commit after the timed observer returns, so closure is safe only when the
        # terminal snapshot is followed by an empty drain.
        terminal = service.get(job_id).state in TERMINAL_STATES  # type: ignore[attr-defined]
        drained = service.events_after(job_id, sequence)  # type: ignore[attr-defined]
        for event in drained:
            sequence = event.sequence
            emitted += 1
            yield _sse_frame(event)
            if emitted >= MAX_SSE_EVENTS_PER_CONNECTION:
                return
        if terminal:
            while drained:
                drained = service.events_after(job_id, sequence)  # type: ignore[attr-defined]
                for event in drained:
                    sequence = event.sequence
                    emitted += 1
                    yield _sse_frame(event)
                    if emitted >= MAX_SSE_EVENTS_PER_CONNECTION:
                        return
            return


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
    plan_job_service_factory: Callable[[], object] | None = None,
) -> FastAPI:
    """Create the API without constructing remote clients, retrievers, models, or workers."""

    def make_plan_job_service() -> object:
        if plan_job_service_factory is not None:
            return plan_job_service_factory()
        from buoy_search.command_center_jobs import PlanJobService

        return PlanJobService(state_root=state_root, artifacts_root=artifacts_root)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        from buoy_search.command_center_jobs import (
            ManagedPlanningUnsupportedError,
            require_managed_planning_platform,
        )

        service: object | None = None
        try:
            try:
                # Probe before constructing the service so unsupported platforms
                # create neither a worker nor managed job/artifact directories.
                require_managed_planning_platform()
                service = make_plan_job_service()
            except ManagedPlanningUnsupportedError:
                application.state.managed_public_planning_available = False
                application.state.managed_public_planning_unavailable_reason = (
                    "platform_unsupported"
                )
                _LOGGER.warning(
                    "Managed public-source planning is unavailable on this platform; read-only Command Center features remain available."
                )
            else:
                application.state.managed_public_planning_available = True
                application.state.managed_public_planning_unavailable_reason = None
                application.state.plan_job_service = service
            yield
        finally:
            application.state.plan_job_service = None
            if service is not None:
                service.shutdown(wait=True)  # type: ignore[attr-defined]

    app = FastAPI(
        title="Buoy local command center",
        description="Read-only reviews plus bounded local credential-free HTTP(S) and public GitHub planning.",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.plan_job_service = None
    app.state.managed_public_planning_available = True
    app.state.managed_public_planning_unavailable_reason = None
    csrf_token = secrets.token_urlsafe(32)
    inventory = local_inventory or LocalInventoryService(
        artifacts_root=artifacts_root,
        state_root=state_root,
    )
    frontend_root = Path(static_root) if static_root is not None else DEFAULT_STATIC_ROOT
    creation_path = f"{API_PREFIX}/plan-jobs"

    @app.middleware("http")
    async def local_request_boundary(request: Request, call_next: Callable[..., Any]):
        host_values = _header_values(request, "host")
        if len(host_values) != 1 or not _valid_loopback_host(host_values[0]):
            response = _error(
                "invalid_host",
                "Command Center accepts requests only through a loopback host.",
                status_code=400,
            )
        elif (
            not app.state.managed_public_planning_available
            and (
                request.url.path == creation_path
                or request.url.path.startswith(f"{creation_path}/")
            )
        ):
            # Intercept before request parsing and route validation so every managed
            # job route has one unavailable response and constructs no service.
            response = _error(
                "managed_planning_unavailable",
                MANAGED_PLANNING_UNAVAILABLE_MESSAGE,
                status_code=503,
            )
        elif request.method == "POST" and request.url.path == creation_path:
            origin_values = _header_values(request, "origin")
            csrf_values = _header_values(request, CSRF_HEADER)
            content_types = _header_values(request, "content-type")
            media_type = content_types[0].split(";", 1)[0].strip().casefold() if len(content_types) == 1 else ""
            same_origin = (
                len(origin_values) == 1
                and _origin_matches_request(origin_values[0], request)
            )
            if (
                not same_origin
                or len(csrf_values) != 1
                or not secrets.compare_digest(csrf_values[0], csrf_token)
                or request.headers.get("sec-fetch-site", "same-origin") not in {"same-origin", "none"}
            ):
                response = _error(
                    "request_forbidden",
                    "The local plan operation was rejected.",
                    status_code=403,
                )
            elif media_type != "application/json":
                response = _error(
                    "unsupported_media_type",
                    "Plan-job creation requires application/json.",
                    status_code=415,
                )
            else:
                try:
                    request._body = await _read_bounded_body(request)  # type: ignore[attr-defined]
                except OverflowError:
                    response = _error(
                        "request_body_too_large",
                        "The plan-job request body is too large.",
                        status_code=413,
                    )
                except ValueError:
                    response = _error(
                        "invalid_content_length",
                        "The request Content-Length is invalid.",
                        status_code=400,
                    )
                else:
                    response = await call_next(request)
        elif request.method == "POST" and request.url.path in {
            f"{API_PREFIX}/remote/snapshot",
            f"{API_PREFIX}/search",
        }:
            origin_values = _header_values(request, "origin")
            same_origin = (
                len(origin_values) == 0
                or (len(origin_values) == 1 and _origin_matches_request(origin_values[0], request))
            )
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
        _LOGGER.error("Command Center request failed (%s).", type(_exc).__name__)
        return _error(
            "internal_error",
            "The request could not be completed.",
            status_code=500,
        )

    def managed_planning_unavailable() -> JSONResponse | None:
        if app.state.managed_public_planning_available:
            return None
        return _error(
            "managed_planning_unavailable",
            MANAGED_PLANNING_UNAVAILABLE_MESSAGE,
            status_code=503,
        )

    def plan_job_service() -> object:
        service = app.state.plan_job_service
        if service is None:
            raise RuntimeError("Plan-job service lifecycle is not active.")
        return service

    @app.get(f"{API_PREFIX}/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "api_version": "v1", "buoy_version": __version__}

    @app.get(f"{API_PREFIX}/csrf-token")
    async def csrf() -> JSONResponse:
        response = JSONResponse({"csrf_token": csrf_token})
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get(f"{API_PREFIX}/capabilities")
    async def capabilities() -> dict[str, object]:
        return {
            "api_version": "v1",
            "buoy_version": __version__,
            "loopback_only": True,
            "review_routes_read_only": True,
            "local_plan_job_creation": app.state.managed_public_planning_available,
            "managed_public_planning_available": app.state.managed_public_planning_available,
            "managed_public_planning_unavailable_reason": app.state.managed_public_planning_unavailable_reason,
            "durable_plan_job_history_available": app.state.managed_public_planning_available,
            "remote_mutations": False,
            "remote_snapshot": True,
            "search": True,
            "artifacts_root_available": _available_directory(Path(artifacts_root)),
            "state_root_available": _available_directory(Path(state_root)),
            "turbopuffer_credentials_available": bool(os.environ.get("TURBOPUFFER_API_KEY")),
            "ui_build_available": _safe_static_file(frontend_root, "index.html") is not None,
            "bigquery_extra_installed": _distribution_available("google-cloud-bigquery"),
            "snowflake_extra_installed": _distribution_available("snowflake-connector-python"),
        }

    @app.post(f"{API_PREFIX}/plan-jobs", status_code=202)
    async def create_plan_job(request: Request) -> Any:
        unavailable = managed_planning_unavailable()
        if unavailable is not None:
            return unavailable
        try:
            plan_request = _parse_plan_job_request(await request.body())
            return plan_job_service().start(plan_request).to_dict()  # type: ignore[attr-defined]
        except Exception as exc:
            return _job_error_response(exc)

    @app.get(f"{API_PREFIX}/plan-jobs")
    async def list_plan_jobs(offset: int = 0, limit: int = 50) -> Any:
        unavailable = managed_planning_unavailable()
        if unavailable is not None:
            return unavailable
        if (
            offset < 0
            or offset > MAX_JOB_LIST_OFFSET
            or limit < 1
            or limit > MAX_JOB_LIST_SIZE
        ):
            return _error(
                "invalid_pagination",
                f"offset must be between 0 and {MAX_JOB_LIST_OFFSET} and limit must be between 1 and {MAX_JOB_LIST_SIZE}.",
                status_code=422,
            )
        try:
            jobs, total = plan_job_service().list_window(  # type: ignore[attr-defined]
                offset=offset, limit=limit
            )
            return {
                "items": [job.to_dict() for job in jobs],
                "total": total,
                "offset": offset,
                "limit": limit,
            }
        except Exception as exc:
            return _job_error_response(exc)

    @app.get(f"{API_PREFIX}/plan-jobs/{{job_id}}")
    async def plan_job_detail(job_id: str) -> Any:
        unavailable = managed_planning_unavailable()
        if unavailable is not None:
            return unavailable
        if not _valid_job_id(job_id):
            return _error("job_not_found", "Plan job was not found.", status_code=404)
        try:
            return plan_job_service().get(job_id).to_dict()  # type: ignore[attr-defined]
        except Exception as exc:
            return _job_error_response(exc)

    @app.get(f"{API_PREFIX}/plan-jobs/{{job_id}}/events")
    async def plan_job_events(request: Request, job_id: str, after_sequence: str | None = None) -> Any:
        unavailable = managed_planning_unavailable()
        if unavailable is not None:
            return unavailable
        if not _valid_job_id(job_id):
            return _error("job_not_found", "Plan job was not found.", status_code=404)
        try:
            header_values = _header_values(request, "last-event-id")
            if len(header_values) > 1:
                raise ValueError("Last-Event-ID must not be repeated.")
            header_sequence = _parse_sequence(header_values[0]) if header_values else 0
            sequence = (
                header_sequence
                if header_values
                else _parse_sequence(after_sequence)
            )
            service = plan_job_service()
            service.get(job_id)  # type: ignore[attr-defined]
        except Exception as exc:
            return _job_error_response(exc)
        return StreamingResponse(
            _sse_events(service, job_id, sequence),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

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
