"""Provider-free MCP contract tests, including actual CLI rendering and stdio."""
from __future__ import annotations

import asyncio
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from io import StringIO
import functools
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, Mock, patch

from buoy_search import __version__
from buoy_search.cli.entrypoint import main as entrypoint
from buoy_search.mcp import WORKER_FALLBACK_WARNING, create_server

HAS_MCP = importlib.util.find_spec("mcp") is not None
ROOT = Path(__file__).resolve().parents[2]
SECRET = "PRIVATE-CREDENTIAL-EXCEPTION-SENTINEL"


def isolated_env(root: Path) -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", ""), "HOME": str(root),
        "XDG_CACHE_HOME": str(root / "cache"), "HF_HOME": str(root / "hf"),
        "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(ROOT / "src"),
    }


class MCPLaunchTests(unittest.TestCase):
    def test_lazy_help_and_missing_extra(self):
        for args in (["mcp", "--help"], ["mcp"]):
            with self.subTest(args=args), patch.dict(sys.modules, {"mcp": None}), \
                    redirect_stdout(StringIO()) as out, redirect_stderr(StringIO()) as err:
                if "--help" in args:
                    with self.assertRaises(SystemExit) as exc:
                        entrypoint(args)
                    self.assertEqual(exc.exception.code, 0)
                    self.assertIn("stdio", out.getvalue())
                else:
                    self.assertEqual(entrypoint(args), 1)
                    self.assertIn("buoy-search[mcp]", err.getvalue())
                    self.assertNotIn("Traceback", err.getvalue())

    def test_discovery_imports_are_inert_without_sdk(self):
        code = """
import importlib.abc, sys
class Guard(importlib.abc.MetaPathFinder):
 def find_spec(self, fullname, *args):
  if fullname.split('.')[0] in {'mcp','turbopuffer','torch','transformers','sentence_transformers','dotenv'} or fullname in {'buoy_search.cli.main','buoy_search.retrieval.embedding_worker'}:
   raise AssertionError('forbidden import: ' + fullname)
sys.meta_path.insert(0, Guard())
from buoy_search.cli.entrypoint import main
main(['mcp', '--help'])
"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            completed = subprocess.run([sys.executable, "-c", code], env=isolated_env(root), capture_output=True, timeout=20)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(list(root.iterdir()), [])

    def test_top_level_help_advertises_mcp(self):
        from buoy_search.cli.main import build_parser
        self.assertIn("mcp", build_parser().format_help())


def with_client(function):
    @functools.wraps(function)
    async def run(self):
        from mcp import Client
        async with Client(create_server()) as client:
            self.client = client
            await function(self)
    return run


@unittest.skipUnless(HAS_MCP, "optional MCP extra not installed")
class MCPToolTests(unittest.IsolatedAsyncioTestCase):
    def assert_payload(self, result, payload):
        self.assertFalse(result.is_error, result)
        self.assertEqual(result.structured_content, payload)
        self.assertEqual(len(result.content), 1)
        self.assertEqual(json.loads(result.content[0].text), payload)

    @with_client
    async def test_discovery_has_exact_strict_read_tools(self):
        listed = await self.client.list_tools()
        self.assertEqual({t.name for t in listed.tools}, {"retrieve", "catalog_list", "catalog_show"})
        for tool in listed.tools:
            self.assertFalse(tool.input_schema["additionalProperties"])
            self.assertTrue(tool.annotations.read_only_hint)
            self.assertFalse(tool.annotations.destructive_hint)
            self.assertTrue(tool.annotations.open_world_hint)
        tools = {t.name: t for t in listed.tools}
        self.assertEqual(tools["retrieve"].input_schema["properties"]["top_k"]["default"], 5)
        self.assertEqual((await self.client.list_resources()).resources, [])
        self.assertEqual((await self.client.list_prompts()).prompts, [])

    @with_client
    async def test_fixed_argv_and_value_containment(self):
        cases = [
            ("retrieve", {"query": " q "}, ["retrieve", "--json", "--top-k=5", "--", " q "]),
            ("retrieve", {"query": "q", "namespaces": None}, ["retrieve", "--json", "--top-k=5", "--", "q"]),
            ("retrieve", {"query": "q", "namespaces": []}, ["retrieve", "--json", "--top-k=5", "--", "q"]),
            ("retrieve", {"query": "q", "namespaces": [" a "]}, ["retrieve", "--json", "--top-k=5", "--namespace=a", "--", "q"]),
            ("retrieve", {"query": "--approve;$(touch nope)\n'", "namespaces": [" --all ", "b", "c"], "top_k": 99},
             ["retrieve", "--json", "--top-k=99", "--namespace=--all", "--namespace=b", "--namespace=c", "--", "--approve;$(touch nope)\n'"]),
            ("catalog_list", {}, ["catalog", "list", "--json"]),
            ("catalog_list", {"search": None}, ["catalog", "list", "--json"]),
            *(("catalog_list", {"search": value}, ["catalog", "list", "--json", "--", value]) for value in ("null", "[]", "{}", '"quoted"')),
            ("catalog_list", {"search": ""}, ["catalog", "list", "--json", "--", ""]),
            ("catalog_list", {"search": "--all;\n$(false)", "include_all": True}, ["catalog", "list", "--json", "--all", "--", "--all;\n$(false)"]),
            ("catalog_show", {"namespace": " --include-vector "}, ["catalog", "show", "--json", "--", " --include-vector "]),
        ]
        for tool, args, argv in cases:
            with self.subTest(tool=tool, args=args), patch("anyio.run_process", new_callable=AsyncMock) as run:
                run.return_value = subprocess.CompletedProcess([], 0, b'{"hits":[]}', b'')
                self.assert_payload(await self.client.call_tool(tool, args), {"hits": []})
                run.assert_awaited_once_with([sys.executable, "-m", "buoy_search", *argv], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

    @with_client
    async def test_invalid_inputs_never_launch_and_do_not_echo_values(self):
        cases = [("retrieve", args) for args in (
            {}, {"query": " "}, {"query": 1}, {"query": None},
            *({"query": "q", "top_k": k} for k in (True, False, "5", 1.5, 0, -1, None)),
            *({"query": "q", "namespaces": n} for n in (
                "[]", [1], [None], [""], [" "], ["a", " a "], ["a", "b", "c", "d"],
                ["buoy-routing-catalog-v1"], [" buoy-evidence-test "],
            )), {"query": "q", "api_key": SECRET},
        )]
        cases += [("catalog_list", args) for args in (
            {"search": 1}, {"search": []}, *({"include_all": b} for b in (1, 0, "true", "false", None)), {"approve": SECRET},
        )]
        cases += [("catalog_show", args) for args in ({}, {"namespace": " "}, {"namespace": 1}, {"namespace": None}, {"namespace": "x", "include_vector": SECRET})]
        cases += [(SECRET, {})]
        with patch("anyio.run_process", new_callable=AsyncMock) as run, redirect_stderr(StringIO()) as err:
            for tool, args in cases:
                with self.subTest(tool=tool, args=args):
                    result = await self.client.call_tool(tool, args)
                    self.assertTrue(result.is_error, result)
                    self.assertNotIn(SECRET, str(result))
            run.assert_not_called()
            self.assertNotIn(SECRET, err.getvalue())

    @with_client
    async def test_failures_are_sanitized_no_retry_and_safe_warning_once(self):
        outcomes = [
            subprocess.CompletedProcess([], 2, SECRET.encode(), SECRET.encode()),
            *(subprocess.CompletedProcess([], 0, value, SECRET.encode()) for value in (SECRET.encode(), b'[]', b'null', b'{"x":NaN}', b'\xff')),
            OSError(SECRET), RuntimeError(SECRET),
        ]
        for outcome in outcomes:
            with self.subTest(outcome=type(outcome)), patch("anyio.run_process", new_callable=AsyncMock) as run, redirect_stderr(StringIO()) as err:
                if isinstance(outcome, Exception):
                    run.side_effect = outcome
                else:
                    run.return_value = outcome
                result = await self.client.call_tool("catalog_list", {})
                self.assertTrue(result.is_error)
                run.assert_awaited_once()
                self.assertNotIn(SECRET, str(result) + err.getvalue())
                self.assertNotIn("Traceback", err.getvalue())
        for status in (0, 2):
            with patch("anyio.run_process", new_callable=AsyncMock) as run, redirect_stderr(StringIO()) as err:
                run.return_value = subprocess.CompletedProcess([], status, b'{}', f'{SECRET}\n{WORKER_FALLBACK_WARNING}\n{WORKER_FALLBACK_WARNING}\n{SECRET}'.encode())
                await self.client.call_tool("catalog_list", {})
                self.assertEqual(err.getvalue(), WORKER_FALLBACK_WARNING + "\n")

    @with_client
    async def test_actual_catalog_cli_parity(self):
        from cli.test_catalog_cli import make_card, make_snapshot, run_cli
        from buoy_search.catalog.remote import REMOTE_SCHEMA_V3
        cards = [
            make_card("z-live", title="Data_Vault", routing_examples=["reviewed lookup question"], routing_passages=["private source passage"]),
            make_card("a-disabled", enabled=False), make_card("m-stale"),
            make_card("incompatible", embedding_model="other-model"),
        ]
        snapshot = make_snapshot(*cards, live=("z-live", "a-disabled", "missing-live", "incompatible"), schema_version=REMOTE_SCHEMA_V3)
        calls = []
        def cli(argv):
            with patch("buoy_search.cli.catalog.read_remote_catalog", return_value=snapshot) as read:
                result = run_cli(argv)
                self.assertEqual(read.call_count, 1)
                calls.append(argv)
                return result
        cases = [
            ("catalog_list", {}, ["catalog", "list", "--json"]),
            ("catalog_list", {"include_all": True}, ["catalog", "list", "--all", "--json"]),
            *(("catalog_list", {"search": search}, ["catalog", "list", "--json", "--", search]) for search in ("data vault", "reviewed lookup", "", "   ", "no-match", "--all", "null", "[]", "{}")),
            *(("catalog_show", {"namespace": ns}, ["catalog", "show", "--json", "--", ns]) for ns in ("z-live", "m-stale", "missing", " z-live ", "--include-vector")),
        ]
        for tool, args, direct in cases:
            with self.subTest(tool=tool, args=args):
                status, out, _ = cli(direct)
                async def invoke(argv, **kwargs):
                    code, stdout, stderr = cli(argv[3:])
                    return subprocess.CompletedProcess(argv, code, stdout.encode(), stderr.encode())
                with patch("anyio.run_process", side_effect=invoke) as run:
                    result = await self.client.call_tool(tool, args)
                    run.assert_awaited_once()
                if status:
                    self.assertTrue(result.is_error)
                else:
                    payload = json.loads(out)
                    self.assert_payload(result, payload)
                    encoded = json.dumps(payload)
                    self.assertNotIn('"vector"', encoded)
                    self.assertNotIn('"routing_passages"', encoded)
                    self.assertNotIn("private source passage", encoded)
                    if args == {}:
                        self.assertEqual([c["namespace"] for c in payload["cards"]], ["incompatible", "z-live"])
                        self.assertIn("reviewed lookup question", encoded)
                    if args == {"include_all": True}:
                        self.assertEqual(len(payload["cards"]), 4)
        self.assertEqual(len(calls), len(cases) * 2)

    @with_client
    async def test_actual_retrieve_cli_provider_model_parity(self):
        from cli.test_catalog_cli import FixedEmbedder, make_card, make_snapshot
        from retrieval.test_multi_namespace_retrieval import RankedNamespace, EmptyNamespace, FailingNamespace, RecordingEmbedder, FixedReranker
        from buoy_search.cli.main import main
        from buoy_search.retrieval.retriever import HybridRetriever, MultiNamespaceRetriever
        from types import SimpleNamespace
        snapshot = make_snapshot(make_card("a", title="Alpha"), make_card("b", title="Beta"))
        cases = [
            ({"query": " Alpha ", "namespaces": [" a "]}, "hits"),
            ({"query": "Alpha", "namespaces": ["a"]}, "empty"),
            ({"query": "Alpha Beta", "namespaces": ["a", "b"], "top_k": 2}, "hits"),
            ({"query": "Alpha Beta", "namespaces": ["a", "b"]}, "partial"),
            ({"query": "Alpha Beta", "namespaces": ["a", "b"]}, "failed"),
            ({"query": "Alpha Beta"}, "hits"),
            ({"query": "Alpha"}, "hits"),
            ({"query": "Alpha Beta", "namespaces": None}, "weak"),
            ({"query": "Alpha Beta", "namespaces": []}, "inconclusive"),
            ({"query": "Alpha Beta"}, "empty"),
            ({"query": "Alpha Beta"}, "failed"),
            ({"query": "--approve;$(false)\n'", "namespaces": ["--all"]}, "hits"),
        ]
        for arguments, mode in cases:
            with self.subTest(arguments=arguments, mode=mode):
                def cli(argv):
                    events = []
                    embedder = RecordingEmbedder()
                    reranker = FixedReranker()
                    # Use real Hybrid/Multi retrieval, ranking and evidence orchestration.
                    # Only provider resources and local inference are fake.
                    def single(config, **kwargs):
                        namespace_type = EmptyNamespace if mode == "empty" else FailingNamespace if mode == "failed" or (config.namespace == "b" and mode in {"partial", "inconclusive"}) else RankedNamespace
                        resource = namespace_type(config.namespace, ["one", "two"], events) if namespace_type is RankedNamespace else namespace_type(config.namespace, events)
                        return HybridRetriever(namespace=resource, embedder=embedder, config=config)
                    def multi(configs, **kwargs):
                        return MultiNamespaceRetriever(retrievers=[single(config) for config in configs], embedder=embedder, reranker_loader=lambda: reranker)
                    def score(query, passages):
                        return [(-20.0 if mode in {"weak", "inconclusive"} else 1.0)] * len(passages)
                    reranker.score = score
                    out, err = StringIO(), StringIO()
                    with ExitStack() as stack:
                        stack.enter_context(patch.dict(os.environ, {"TURBOPUFFER_API_KEY": "fake-only", "TURBOPUFFER_NAMESPACE": "ignored"}, clear=True))
                        stack.enter_context(patch("buoy_search.cli.main.EMBEDDING_WORKER_CAPABILITY_FACTORY", return_value=False))
                        stack.enter_context(patch("buoy_search.cli.main.REMOTE_CATALOG_CLIENT_FACTORY", return_value=object()))
                        read = stack.enter_context(patch("buoy_search.cli.main.read_remote_catalog", return_value=snapshot))
                        route_embed = stack.enter_context(patch("buoy_search.cli.main.ROUTING_EMBEDDER_FACTORY", return_value=FixedEmbedder()))
                        stack.enter_context(patch("buoy_search.cli.main.ROUTING_CONFIDENCE_FACTORY", return_value=SimpleNamespace(mode="collect")))
                        stack.enter_context(patch("buoy_search.cli.main.HybridRetriever.from_config", side_effect=single))
                        stack.enter_context(patch("buoy_search.cli.main.MultiNamespaceRetriever.from_configs", side_effect=multi))
                        stack.enter_context(patch("buoy_search.retrieval.retriever.load_cross_encoder_reranker", return_value=reranker))
                        with redirect_stdout(out), redirect_stderr(err):
                            status = main(argv)
                    return status, out.getvalue(), err.getvalue(), (sorted(events), embedder.calls, read.call_count, route_embed.call_count)
                direct = ["retrieve", "--json", f'--top-k={arguments.get("top_k", 5)}']
                direct += [f'--namespace={ns.strip()}' for ns in arguments.get("namespaces") or []]
                direct += ["--", arguments["query"]]
                status, stdout, stderr, operations = cli(direct)
                observed = []
                async def invoke(argv, **kwargs):
                    code, out, err, ops = cli(argv[3:])
                    observed.append(ops)
                    return subprocess.CompletedProcess(argv, code, out.encode(), err.encode())
                with patch("anyio.run_process", side_effect=invoke) as run:
                    result = await self.client.call_tool("retrieve", arguments)
                    run.assert_awaited_once()
                self.assertEqual(observed, [operations])
                self.assertEqual(operations[2:], (0, 0) if arguments.get("namespaces") else (1, 1))
                self.assertEqual(len(operations[1]), 1)
                if mode == "failed":
                    self.assertNotEqual(status, 0)
                    self.assertTrue(result.is_error)
                else:
                    self.assertEqual(status, 0, stderr)
                    payload = json.loads(stdout)
                    self.assert_payload(result, payload)
                    if mode in {"partial", "inconclusive"}:
                        self.assertTrue(payload["incomplete"])
                    if mode in {"weak", "inconclusive"}:
                        self.assertEqual(payload["evidence"]["status"], "inconclusive" if mode == "inconclusive" else "no_relevant_evidence")
                    if mode in {"empty", "weak", "inconclusive"}:
                        self.assertEqual(payload["hits"], [])


@unittest.skipUnless(HAS_MCP, "optional MCP extra not installed")
class MCPStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_official_stdio_client_initialize_discover_invalid_and_disconnect(self):
        from mcp import Client, StdioServerParameters
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # A dotenv file must not be read; no credential reaches the server environment.
            (root / ".env").write_text(f"TURBOPUFFER_API_KEY={SECRET}\n")
            before = sorted(str(p.relative_to(root)) for p in root.rglob("*"))
            params = StdioServerParameters(command=sys.executable, args=["-m", "buoy_search", "mcp"], env=isolated_env(root), cwd=root)
            async with Client(params) as client:
                tools = (await client.list_tools()).tools
                self.assertEqual({t.name for t in tools}, {"retrieve", "catalog_list", "catalog_show"})
                result = await client.call_tool("retrieve", {"query": "q", "top_k": True})
                self.assertTrue(result.is_error)
                self.assertNotIn(SECRET, str(result))
                # Actual credential-free CLI child: dotenv must not supply its fake key.
                result = await client.call_tool("catalog_list", {})
                self.assertTrue(result.is_error)
                self.assertNotIn(SECRET, str(result))
            self.assertEqual(sorted(str(p.relative_to(root)) for p in root.rglob("*")), before)

    async def start_wire(self, root, code=None):
        args = [sys.executable, "-m", "buoy_search", "mcp"] if code is None else [sys.executable, "-c", code]
        process = await asyncio.create_subprocess_exec(*args, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=isolated_env(root), cwd=root)
        self.addAsyncCleanup(self.cleanup_process, process)
        await self.send(process, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}}})
        initialized = await self.receive(process)
        self.assertEqual(initialized["result"]["serverInfo"], {"name": "Buoy", "version": __version__})
        await self.send(process, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        return process

    async def cleanup_process(self, process):
        if process.returncode is None:
            process.kill()
            await process.wait()

    async def send(self, process, message):
        process.stdin.write(json.dumps(message).encode() + b"\n")
        await process.stdin.drain()

    async def receive(self, process):
        line = await asyncio.wait_for(process.stdout.readline(), 15)
        self.assertTrue(line, "server closed protocol stdout unexpectedly")
        return json.loads(line)

    async def test_wire_stdout_is_only_protocol_and_help_is_inert(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Refuse heavyweight/runtime imports during startup and discovery.
            (root / "sitecustomize.py").write_text("""
import importlib.abc, sys
class Guard(importlib.abc.MetaPathFinder):
 def find_spec(self, fullname, *args):
  if fullname.split('.')[0] in {'turbopuffer','torch','transformers','sentence_transformers','dotenv'} or fullname in {'buoy_search.cli.main','buoy_search.retrieval.embedding_worker'}:
   raise AssertionError('forbidden discovery import')
sys.meta_path.insert(0, Guard())
""")
            code = f"import sys; sys.path.insert(0, {str(root)!r}); import sitecustomize; from buoy_search.cli.entrypoint import main; raise SystemExit(main(['mcp']))"
            process = await self.start_wire(root, code)
            await self.send(process, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
            self.assertEqual(len((await self.receive(process))["result"]["tools"]), 3)
            await self.send(process, {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "catalog_list", "arguments": {"include_all": SECRET}}})
            self.assertTrue((await self.receive(process))["result"]["isError"])
            # Split a UTF-8 code point across writes; preserve CRLF line semantics.
            message = json.dumps({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "retrieve", "arguments": {"query": "\u2003"}}}, ensure_ascii=False).encode() + b"\r\n"
            boundary = message.index("\u2003".encode()) + 1
            process.stdin.write(message[:boundary])
            await process.stdin.drain()
            await asyncio.sleep(.02)
            process.stdin.write(message[boundary:])
            await process.stdin.drain()
            self.assertTrue((await self.receive(process))["result"]["isError"])
            process.stdin.close()
            await asyncio.wait_for(process.wait(), 15)
            self.assertEqual(process.returncode, 0)
            self.assertEqual(await process.stdout.read(), b"")
            self.assertEqual(await process.stderr.read(), b"")
            self.assertEqual([p.name for p in root.iterdir()], ["sitecustomize.py"])

    async def test_cancellation_eof_and_signals_reap_only_command_child(self):
        for action in ("cancel", "eof", "sigterm", "sigint"):
            with self.subTest(action=action), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                child_file = root / "child.pid"
                # Substitute only the external command at the process boundary. Exercise
                # real SDK dispatch/cancellation and the real AnyIO process lifecycle.
                child_code = f"import os,time; from pathlib import Path; Path({str(child_file)!r}).write_text(str(os.getpid())); time.sleep(120)"
                code = f"""
import anyio
original = anyio.run_process
async def fake_command(argv, **kwargs):
 return await original([{sys.executable!r}, '-c', {child_code!r}], **kwargs)
anyio.run_process = fake_command
from buoy_search.cli.entrypoint import main
raise SystemExit(main(['mcp']))
"""
                shared = await asyncio.create_subprocess_exec(sys.executable, "-c", "import time; time.sleep(120)", env=isolated_env(root))
                self.addAsyncCleanup(self.cleanup_process, shared)
                process = await self.start_wire(root, code)
                await self.send(process, {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "catalog_list", "arguments": {}}})
                for _ in range(300):
                    if child_file.exists():
                        break
                    await asyncio.sleep(.02)
                self.assertTrue(child_file.exists())
                pid = int(child_file.read_text())
                if action == "cancel":
                    await self.send(process, {"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 2}})
                elif action == "eof":
                    process.stdin.close()
                else:
                    process.send_signal(signal.SIGTERM if action == "sigterm" else signal.SIGINT)
                for _ in range(300):
                    try:
                        os.kill(pid, 0)
                    except ProcessLookupError:
                        break
                    await asyncio.sleep(.02)
                else:
                    os.kill(pid, signal.SIGKILL)
                    self.fail(f"{action} left command child alive")
                self.assertIsNone(shared.returncode)
                if action == "cancel":
                    # Cancellation leaves the server available for the next request.
                    await self.send(process, {"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}})
                    response = await self.receive(process)
                    while response.get("id") != 3:
                        response = await self.receive(process)
                    self.assertEqual(len(response["result"]["tools"]), 3)
                    process.stdin.close()
                await asyncio.wait_for(process.wait(), 15)
                for line in (await process.stdout.read()).splitlines():
                    json.loads(line)
                self.assertEqual(await process.stderr.read(), b"")
                await self.cleanup_process(shared)


if __name__ == "__main__":
    unittest.main()
