"""Optional stdio adapter over Buoy's fixed read-only CLI JSON commands."""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Sequence
import json
import io
import os
import signal
import subprocess
import sys
import threading
from typing import Annotated

from buoy_search import __version__


WORKER_FALLBACK_WARNING = (
    "Warning: local embedding worker failed; using in-process embedding for this command."
)


def create_server():
    """Import the optional SDK only when constructing an actual server."""
    import anyio
    from mcp.server import MCPServer
    from mcp.server.mcpserver.tools import Tool
    from mcp.server.mcpserver.utilities.func_metadata import FuncMetadata
    from mcp.types import CallToolResult, TextContent, ToolAnnotations
    from pydantic import ConfigDict, Field, StrictBool, StrictStr, ValidationError, create_model

    def error(message: str) -> CallToolResult:
        return CallToolResult(isError=True, content=[TextContent(type="text", text=message)])

    async def execute(arguments: list[str]) -> CallToolResult:
        try:
            # AnyIO drains both pipes and kills/reaps this child on cancellation.
            # Never signal a process group: inference/telemetry workers are shared.
            completed = await anyio.run_process(
                [sys.executable, "-m", "buoy_search", *arguments],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if WORKER_FALLBACK_WARNING.encode() in completed.stderr.splitlines():
                print(WORKER_FALLBACK_WARNING, file=sys.stderr)
            if completed.returncode:
                return error(
                    "Buoy read failed. Check TURBOPUFFER_API_KEY in the server environment, "
                    "namespace/catalog availability, and local model setup."
                )
            payload = json.loads(completed.stdout, parse_constant=_reject_json_constant)
            if not isinstance(payload, dict):
                return error("Buoy returned invalid JSON. Check the Buoy installation.")
            text = json.dumps(payload, allow_nan=False)
            return CallToolResult(
                structuredContent=payload, content=[TextContent(type="text", text=text)]
            )
        except (ValueError, UnicodeError):
            return error("Buoy returned invalid JSON. Check the Buoy installation and inputs.")
        except Exception:
            # SDK crash logging can include exception chains; do not let child details escape.
            return error("Buoy read could not run. Check the Buoy installation and server environment.")

    async def retrieve(
        query: StrictStr,
        namespaces: list[StrictStr] | None = None,
        top_k: Annotated[int, Field(strict=True, gt=0)] = 5,
    ) -> CallToolResult:
        """Retrieve evidence, not an answer. Retain source citations and respect incomplete or abstained results.

        May incur provider read costs and use local inference workers and opted-in telemetry.
        """
        if not query.strip():
            return error("query must contain non-whitespace text.")
        selected = [namespace.strip() for namespace in namespaces or []]
        if (
            len(selected) > 3
            or len(set(selected)) != len(selected)
            or any(not name or name == "buoy-routing-catalog-v1" or name.startswith("buoy-evidence-") for name in selected)
        ):
            return error("namespaces must contain at most three unique, nonempty content namespaces; control namespaces are reserved.")
        return await execute([
            "retrieve", "--json", f"--top-k={top_k}",
            *(f"--namespace={name}" for name in selected), "--", query,
        ])

    async def catalog_list(
        search: StrictStr | None = None, include_all: StrictBool = False,
    ) -> CallToolResult:
        """Inspect catalog cards without mutations. May incur provider inventory/catalog read costs."""
        return await execute([
            "catalog", "list", "--json", *(["--all"] if include_all else []),
            *(["--", search] if search is not None else []),
        ])

    async def catalog_show(namespace: StrictStr) -> CallToolResult:
        """Inspect one exact catalog card ID without vectors or source passage banks. May incur provider read costs."""
        if not namespace.strip():
            return error("namespace must contain non-whitespace text.")
        return await execute(["catalog", "show", "--json", "--", namespace])

    class StrictMetadata(FuncMetadata):
        def pre_parse_json(self, data):
            # A literal search string such as "null" or "[]" must remain a string.
            return data

    annotations = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=True)
    tools = []
    for function in (retrieve, catalog_list, catalog_show):
        # These functions use locally imported annotation types. Resolve them before SDK inspection.
        import typing
        function.__annotations__ = typing.get_type_hints(function, localns=locals(), include_extras=True)
        tool = Tool.from_function(function, annotations=annotations)
        model = create_model(
            f"{tool.name}Arguments", __base__=tool.fn_metadata.arg_model,
            __config__=ConfigDict(strict=True, extra="forbid", hide_input_in_errors=True),
        )
        tool.fn_metadata = StrictMetadata(arg_model=model)
        tool.parameters = model.model_json_schema()
        tools.append(tool)
    by_name = {tool.name: tool for tool in tools}

    async def validate_input(ctx, call_next):
        # Validate raw values before SDK JSON-string coercion. Also keep SDK validation
        # details (which can contain caller-provided secrets) out of errors and logs.
        if ctx.method == "tools/call" and isinstance(ctx.params, dict):
            name = ctx.params.get("name")
            if isinstance(name, str):
                tool = by_name.get(name)
                if tool is None:
                    return error("Unknown tool. Use retrieve, catalog_list, or catalog_show.")
                try:
                    tool.fn_metadata.arg_model.model_validate(ctx.params.get("arguments", {}))
                except ValidationError:
                    return error("Invalid tool arguments. Check the tool schema, required fields, and strict input types.")
        return await call_next(ctx)

    return MCPServer("Buoy", version=__version__, tools=tools, middleware=[validate_input])


def _reject_json_constant(_value: str) -> None:
    raise ValueError("Non-JSON numeric constant")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="buoy mcp", description="Serve Buoy's three read-only MCP tools over local stdio (requires buoy-search[mcp]).")
    parser.parse_args(argv)
    try:
        import anyio
        server = create_server()
    except ImportError:
        print("MCP support is not installed. Install Buoy with the optional extra: buoy-search[mcp].", file=sys.stderr)
        return 1
    except Exception:
        print("MCP could not start. Check the Buoy optional MCP installation.", file=sys.stderr)
        return 1

    async def serve() -> None:
        async with anyio.create_task_group() as tasks:
            async def stop_on_signal() -> None:
                with anyio.open_signal_receiver(signal.SIGTERM, signal.SIGINT) as signals:
                    async for _ in signals:
                        tasks.cancel_scope.cancel()
                        break
            tasks.start_soon(stop_on_signal)
            try:
                from mcp.server.stdio import stdio_server

                class CancellableInput(anyio.AsyncFile):
                    async def readline(self):
                        loop = asyncio.get_running_loop()
                        result = loop.create_future()

                        def deliver(line, failed):
                            if not result.done():
                                if failed:
                                    result.set_exception(OSError("MCP input could not be read"))
                                else:
                                    result.set_result(line)

                        def read():
                            try:
                                line, failed = self.wrapped.readline(), False
                            except Exception:
                                line, failed = "", True
                            try:
                                loop.call_soon_threadsafe(deliver, line, failed)
                            except RuntimeError:
                                pass  # The cancelled server has already closed its loop.

                        # AnyIO's non-daemon threadpool otherwise holds interpreter exit.
                        threading.Thread(target=read, daemon=True).start()
                        return await result

                # 10x: SDK 2.2.0 blocks signal shutdown in AsyncFile.readline.
                # Keep SDK framing/stdout protection; remove this private serving seam
                # when the SDK offers cancellable stdio input (dependency pinned meanwhile).
                # Own an unbuffered raw fd: no BufferedReader lock at interpreter exit.
                # Never close/recycle a descriptor under an abandoned reader thread.
                wire = io.TextIOWrapper(
                    os.fdopen(os.dup(sys.stdin.fileno()), "rb", buffering=0, closefd=False),
                    encoding="utf-8", errors="replace",
                )
                async with stdio_server(stdin=CancellableInput(wire)) as (reader, writer):
                    lowlevel = server._lowlevel_server
                    await lowlevel.run(reader, writer, lowlevel.create_initialization_options())
            finally:
                tasks.cancel_scope.cancel()

    try:
        anyio.run(serve)
    except KeyboardInterrupt:
        pass
    except Exception:
        print("MCP stopped unexpectedly. Check the Buoy installation and client connection.", file=sys.stderr)
        return 1
    return 0
