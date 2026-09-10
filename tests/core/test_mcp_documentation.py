"""Consumer examples stay tied to the discoverable MCP schema and CI smoke."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs/mcp.md"


class MCPDocumentationTests(unittest.TestCase):
    def test_agent_neutral_configuration_and_single_readme_link(self):
        text = DOC.read_text()
        examples = re.findall(r"```json\n(.*?)\n```", text, re.DOTALL)
        self.assertEqual([json.loads(example) for example in examples], [
            {"mcpServers": {"buoy": {"command": "buoy", "args": ["mcp"]}}},
        ])
        self.assertEqual((ROOT / "README.md").read_text().count("(docs/mcp.md)"), 1)
        self.assertIn("uv sync --locked --extra mcp --python 3.13", text)
        self.assertIn("uv run --locked --extra mcp buoy mcp", text)
        self.assertIn("MCP is unreleased", text)
        self.assertIn("does **not** auto-load `.env`", text)

    def test_ci_preserves_base_and_requires_clean_extra_smoke(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        self.assertIn("--extra mcp --python ${{ matrix.python-version }}", workflow)
        self.assertIn("exact_token_count(load_pinned_tokenizer()", workflow)
        self.assertIn("mcp_installation_smoke.py --mode base", workflow)
        self.assertIn("mcp_installation_smoke.py --mode extra", workflow)
        self.assertIn('"$wheel[mcp]"', workflow)
        self.assertIn("HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1", workflow)


@unittest.skipUnless(importlib.util.find_spec("mcp"), "optional MCP extra not installed")
class MCPDocumentedSchemaTests(unittest.IsolatedAsyncioTestCase):
    async def test_documented_signatures_match_discovered_required_fields_and_defaults(self):
        from mcp import Client
        from buoy_search.mcp import create_server

        text = DOC.read_text()
        signatures = {
            "retrieve": ("retrieve(query: string, namespaces?: string[] | null, top_k: integer = 5)", ["query"], {"namespaces": None, "top_k": 5}),
            "catalog_list": ("catalog_list(search?: string | null, include_all: boolean = false)", [], {"search": None, "include_all": False}),
            "catalog_show": ("catalog_show(namespace: string)", ["namespace"], {}),
        }
        async with Client(create_server()) as client:
            tools = (await client.list_tools()).tools
        self.assertEqual({tool.name for tool in tools}, set(signatures))
        for tool in tools:
            signature, required, defaults = signatures[tool.name]
            self.assertIn(f"### `{signature}`", text)
            schema = tool.input_schema
            self.assertEqual(schema.get("required", []), required)
            self.assertEqual(set(schema["properties"]), set(required) | set(defaults))
            self.assertEqual({key: value["default"] for key, value in schema["properties"].items() if "default" in value}, defaults)
            self.assertFalse(schema["additionalProperties"])


if __name__ == "__main__":
    unittest.main()
