"""Clean-wheel acceptance, run explicitly with the installed interpreter (no source path).

Usage: python /checkout/tests/core/mcp_installation_smoke.py --mode base|extra --wheel /path.whl
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
from urllib.parse import unquote, urlparse
import zipfile


# Fail closed even if a future invalid-input regression tries to invoke a read.
# This directory contains only this hook, never a source copy of Buoy or MCP.
GUARD = '''
import importlib.abc, pathlib, sys
root = pathlib.Path(__file__).parent

def fail():
    (root / "boundary-violation").write_text("forbidden runtime operation")
    raise AssertionError("forbidden runtime operation")

class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, *args):
        if fullname.split(".")[0] in {"turbopuffer", "torch", "transformers", "sentence_transformers", "dotenv"} or fullname in {"buoy_search.cli.main", "buoy_search.retrieval.embedding_worker"}:
            fail()

sys.meta_path.insert(0, Guard())
def audit(event, args):
    if event in {"socket.connect", "socket.bind", "subprocess.Popen", "os.system"}:
        fail()
    if event == "open" and isinstance(args[0], (str, bytes)) and pathlib.Path(str(args[0])).name == ".env":
        fail()
sys.addaudithook(audit)
'''


def environment(root: Path) -> dict[str, str]:
    return {
        "PATH": str(Path(sys.executable).parent) + os.pathsep + os.defpath,
        "HOME": str(root), "XDG_CACHE_HOME": str(root / "cache"),
        "HF_HOME": str(root / "hf"), "TORCH_HOME": str(root / "torch"),
        "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
        "HF_HUB_DISABLE_IMPLICIT_TOKEN": "1", "HF_HUB_DISABLE_TELEMETRY": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }


def installed_identity(wheel: Path, mode: str) -> dict:
    import buoy_search
    import buoy_search.mcp

    distribution = importlib.metadata.distribution("buoy-search")
    origin = json.loads(distribution.read_text("direct_url.json"))
    assert "dir_info" not in origin, "wheel smoke cannot use an editable/source install"
    assert Path(unquote(urlparse(origin["url"]).path)).resolve() == wheel.resolve()
    adapter = Path(buoy_search.mcp.__file__).resolve()
    assert adapter.is_relative_to(Path(sys.prefix).resolve()), adapter
    assert buoy_search.__version__ == distribution.version
    with zipfile.ZipFile(wheel) as archive:
        assert adapter.read_bytes() == archive.read("buoy_search/mcp.py")
        metadata = archive.read(next(n for n in archive.namelist() if n.endswith(".dist-info/METADATA"))).decode()
        assert f"Version: {distribution.version}\n" in metadata
        assert "Provides-Extra: mcp\n" in metadata
        assert "Requires-Dist: mcp==2.2.0; extra == 'mcp'" in metadata
    has_mcp = importlib.util.find_spec("mcp") is not None
    assert has_mcp == (mode == "extra"), "optional-extra installation differs from requested mode"
    versions = {name: importlib.metadata.version(name) for name in ("mcp", "mcp-types", "anyio", "pydantic")} if has_mcp else {}
    if has_mcp:
        assert versions["mcp"] == versions["mcp-types"] == "2.2.0"
    return {
        "python": sys.version, "executable": sys.executable, "buoy": distribution.version,
        "adapter": str(adapter), "direct_url": origin, "dependencies": versions,
        "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
    }


async def wire_smoke(executable: Path, root: Path, env: dict[str, str], version: str, stop: str) -> list[dict]:
    process = await asyncio.create_subprocess_exec(
        str(executable), "mcp", cwd=root, env=env,
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    transcript = []

    async def send(message):
        process.stdin.write(json.dumps(message).encode() + b"\n")
        await process.stdin.drain()

    async def request(identifier, method, params):
        await send({"jsonrpc": "2.0", "id": identifier, "method": method, "params": params})
        response = json.loads(await asyncio.wait_for(process.stdout.readline(), 20))
        assert response["jsonrpc"] == "2.0" and response["id"] == identifier, response
        transcript.append(response)
        return response["result"]

    try:
        initialized = await request(1, "initialize", {
            "protocolVersion": "2025-11-25", "capabilities": {},
            "clientInfo": {"name": "buoy-installed-wheel-smoke", "version": "1"},
        })
        assert initialized["serverInfo"] == {"name": "Buoy", "version": version}
        await send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        tools = (await request(2, "tools/list", {}))["tools"]
        assert {tool["name"] for tool in tools} == {"retrieve", "catalog_list", "catalog_show"}
        for tool in tools:
            assert tool["inputSchema"]["additionalProperties"] is False
            assert tool["annotations"]["readOnlyHint"] is True
        for identifier, name, arguments in (
            (3, "retrieve", {"query": "validation-only", "top_k": True}),
            (4, "catalog_list", {"include_all": "PRIVATE-INPUT-SENTINEL"}),
            (5, "catalog_show", {"namespace": " "}),
        ):
            result = await request(identifier, "tools/call", {"name": name, "arguments": arguments})
            assert result["isError"] is True
            assert "PRIVATE-INPUT-SENTINEL" not in json.dumps(result)
        if stop == "eof":
            process.stdin.close()
        else:
            process.send_signal(signal.SIGTERM if stop == "sigterm" else signal.SIGINT)
        await asyncio.wait_for(process.wait(), 20)
        assert process.returncode == 0, process.returncode
        assert await process.stdout.read() == b"", "non-protocol stdout on shutdown"
        assert await process.stderr.read() == b"", "unexpected stderr on shutdown"
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()
    return transcript


async def sdk_smoke(executable: Path, root: Path, env: dict[str, str]) -> None:
    from mcp import Client, StdioServerParameters

    async with Client(StdioServerParameters(command=str(executable), args=["mcp"], cwd=root, env=env)) as client:
        assert {tool.name for tool in (await client.list_tools()).tools} == {"retrieve", "catalog_list", "catalog_show"}
        assert (await client.call_tool("retrieve", {"query": " "})).is_error
        assert (await client.list_resources()).resources == []
        assert (await client.list_prompts()).prompts == []


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=("base", "extra"))
    parser.add_argument("--wheel", required=True, type=Path)
    args = parser.parse_args()
    report = installed_identity(args.wheel, args.mode)
    executable = Path(sys.executable).parent / ("buoy.exe" if os.name == "nt" else "buoy")
    with tempfile.TemporaryDirectory(prefix="bmcp-") as directory:
        root = Path(directory)
        env = environment(root)
        for command in ([str(executable), "--help"], [str(executable), "mcp", "--help"], [sys.executable, "-m", "buoy_search", "--help"]):
            completed = subprocess.run(command, cwd=root, env=env, capture_output=True, timeout=30)
            assert completed.returncode == 0 and b"mcp" in completed.stdout, completed
            assert completed.stderr == b""
        assert list(root.iterdir()) == [], "help created runtime assets"
        if args.mode == "base":
            completed = subprocess.run([str(executable), "mcp"], cwd=root, env=env, capture_output=True, timeout=20)
            assert completed.returncode == 1 and completed.stdout == b"", completed
            assert b"buoy-search[mcp]" in completed.stderr and b"Traceback" not in completed.stderr
            report["missing_extra_stderr"] = completed.stderr.decode()
            assert list(root.iterdir()) == []
        else:
            (root / "sitecustomize.py").write_text(GUARD)
            # A synthetic fixture only, never a user's credential file.
            (root / ".env").write_text("TURBOPUFFER_API_KEY=PRIVATE-DOTENV-SENTINEL\n")
            env["PYTHONPATH"] = str(root)
            before = sorted(path.name for path in root.iterdir())
            report["wire"] = {}
            for stop in ("eof", "sigterm", "sigint"):
                report["wire"][stop] = asyncio.run(wire_smoke(executable, root, env, report["buoy"], stop))
            asyncio.run(sdk_smoke(executable, root, env))
            assert sorted(str(path.relative_to(root)) for path in root.rglob("*")) == before, "runtime assets or guard violations"
            report["official_sdk_client"] = "initialize/list/invalid/resources/prompts/disconnect passed"
        report["runtime_assets_created"] = False
        report["runtime_home"] = directory
    report["temporary_home_removed"] = not Path(directory).exists()
    assert report["temporary_home_removed"]
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
