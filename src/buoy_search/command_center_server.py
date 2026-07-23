"""Loopback-only runner for the optional command-center web runtime."""

from __future__ import annotations

from pathlib import Path
from typing import Callable
import webbrowser

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
UI_DEPENDENCY_GUIDANCE = "Command Center dependencies are missing. Run: uv sync --extra ui"


class CommandCenterDependencyError(RuntimeError):
    """Raised when the optional local web runtime is unavailable."""


def validate_loopback_host(host: str) -> str:
    """Reject every bind address not explicitly ratified for the local server."""

    if host not in LOOPBACK_HOSTS:
        raise ValueError("--host must be one of: 127.0.0.1, localhost, ::1")
    return host


def _browser_url(host: str, port: int) -> str:
    display_host = f"[{host}]" if host == "::1" else host
    return f"http://{display_host}:{port}/"


def run_server(
    *,
    host: str,
    port: int,
    artifacts_root: Path,
    state_root: Path,
    open_browser: bool,
    static_root: Path | None = None,
    browser_opener: Callable[[str], object] = webbrowser.open,
    uvicorn_runner: Callable[..., object] | None = None,
) -> None:
    """Load optional dependencies only after CLI validation, then run in-process."""

    validate_loopback_host(host)
    if type(port) is not int or port < 1 or port > 65_535:
        raise ValueError("--port must be between 1 and 65535")

    try:
        from buoy_search.command_center_api import create_app
        if uvicorn_runner is None:
            import uvicorn

            uvicorn_runner = uvicorn.run
    except ModuleNotFoundError as exc:
        if exc.name and exc.name.split(".", 1)[0] in {
            "fastapi",
            "pydantic",
            "starlette",
            "uvicorn",
        }:
            raise CommandCenterDependencyError(UI_DEPENDENCY_GUIDANCE) from exc
        raise

    app = create_app(
        artifacts_root=artifacts_root,
        state_root=state_root,
        static_root=static_root,
    )
    if open_browser:
        try:
            browser_opener(_browser_url(host, port))
        except (OSError, webbrowser.Error):
            pass
    uvicorn_runner(app, host=host, port=port)
