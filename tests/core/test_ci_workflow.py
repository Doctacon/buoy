from __future__ import annotations

import ast
import importlib
from importlib.resources import files
import json
from pathlib import Path
import re
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = ROOT / ".github/workflows/ci.yml"

# These implementation modules were removed by the concern-oriented package migration.
REMOVED_FLAT_MODULES = {
    "buoy_search._provider_invocation_receipt",
    "buoy_search.applied_state",
    "buoy_search.apply",
    "buoy_search.autoresearch",
    "buoy_search.bigquery_relation",
    "buoy_search.catalog_cli",
    "buoy_search.chunker",
    "buoy_search.crawler",
    "buoy_search.cross_encoder",
    "buoy_search.database_relation",
    "buoy_search.duckdb_relation",
    "buoy_search.entrypoint",
    "buoy_search.evidence",
    "buoy_search.evidence_evals",
    "buoy_search.github_repo",
    "buoy_search.multi_corpus_evals",
    "buoy_search.plan_artifacts",
    "buoy_search.plan_cleanup",
    "buoy_search.plan_diff",
    "buoy_search.plan_validation",
    "buoy_search.planning_service",
    "buoy_search.remote_catalog",
    "buoy_search.repo_syntax_chunking",
    "buoy_search.retriever",
    "buoy_search.routing",
    "buoy_search.routing_quality",
    "buoy_search.snowflake_relation",
    "buoy_search.telemetry_cli",
    "buoy_search.telemetry_envelope",
    "buoy_search.telemetry_queue",
    "buoy_search.telemetry_store",
    "buoy_search.telemetry_writer",
    "buoy_search.treatment_token_budget",
}


def _embedded_python(source: str) -> list[str]:
    snippets: list[str] = []
    lines = source.splitlines()
    index = 0
    while index < len(lines):
        if lines[index].rstrip().endswith("<<'PY'"):
            start = index + 1
            index = start
            while index < len(lines) and lines[index].strip() != "PY":
                index += 1
            if index == len(lines):
                raise AssertionError("CI workflow has an unterminated Python heredoc")
            snippets.append(textwrap.dedent("\n".join(lines[start:index])) + "\n")
        index += 1
    return snippets


def _imported_modules(snippet: str) -> set[str]:
    tree = ast.parse(snippet)
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
    return modules


def _is_removed(module: str) -> bool:
    return any(module == removed or module.startswith(f"{removed}.") for removed in REMOVED_FLAT_MODULES)


class HostedWorkflowPythonTests(unittest.TestCase):
    def test_packaged_production_basket_registry_is_truthfully_empty(self) -> None:
        registry = json.loads(
            files("buoy_search").joinpath("data/repo_ranking_promotion_baskets.json").read_bytes()
        )
        self.assertEqual(registry, {"baskets": [], "schema_version": 1})

    def test_workflow_contains_no_removed_flat_python_imports(self) -> None:
        source = CI_WORKFLOW.read_text(encoding="utf-8")
        for module in sorted(REMOVED_FLAT_MODULES):
            with self.subTest(module=module):
                pattern = rf"(?m)^\s*(?:from\s+{re.escape(module)}(?:\.[A-Za-z_]\w*)*\s+import\b|import\s+{re.escape(module)}(?:\.[A-Za-z_]\w*)*(?:\s|$))"
                self.assertIsNone(re.search(pattern, source), module)

    def test_embedded_python_compiles_and_buoy_imports_resolve(self) -> None:
        snippets = _embedded_python(CI_WORKFLOW.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(snippets), 1)
        imported: set[str] = set()
        for index, snippet in enumerate(snippets):
            with self.subTest(snippet=index):
                compile(snippet, f"{CI_WORKFLOW}#python-{index}", "exec")
                imported.update(
                    module for module in _imported_modules(snippet) if module == "buoy_search" or module.startswith("buoy_search.")
                )
        self.assertTrue(imported)
        self.assertFalse({module for module in imported if _is_removed(module)})
        for module in sorted(imported):
            with self.subTest(module=module):
                importlib.import_module(module)


if __name__ == "__main__":
    unittest.main()
