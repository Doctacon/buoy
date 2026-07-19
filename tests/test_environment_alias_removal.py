from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from buoy_search import autoresearch
from buoy_search.cli import main


MODEL_ERROR = (
    "Removed environment variable is not supported in Buoy 0.4.0: "
    "TURBO_SEARCH_EMBEDDING_MODEL -> BUOY_EMBEDDING_MODEL\n"
)
PRECISION_ERROR = (
    "Removed environment variable is not supported in Buoy 0.4.0: "
    "TURBO_SEARCH_EMBEDDING_PRECISION -> BUOY_EMBEDDING_PRECISION\n"
)
BOTH_ERROR = (
    "Removed environment variables are not supported in Buoy 0.4.0: "
    "TURBO_SEARCH_EMBEDDING_MODEL -> BUOY_EMBEDDING_MODEL; "
    "TURBO_SEARCH_EMBEDDING_PRECISION -> BUOY_EMBEDDING_PRECISION\n"
)


COMMAND_CASES = (
    ("crawl", "buoy_search.cli._run_crawl", ["crawl", "--base-url", "https://example.com", "--json"]),
    ("plan", "buoy_search.cli._run_plan", ["plan", "https://example.com", "--json"]),
    ("apply interactive decline", "buoy_search.cli._run_apply", ["apply", "--json"]),
    ("apply dry-run", "buoy_search.cli._run_apply", ["apply", "--dry-run", "--json"]),
    ("apply approved", "buoy_search.cli._run_apply", ["apply", "--approve", "--json"]),
    ("namespaces", "buoy_search.cli._run_namespaces", ["namespaces", "--json"]),
    ("retrieve", "buoy_search.cli._run_retrieve", ["retrieve", "question", "--json"]),
    ("evals", "buoy_search.cli._run_evals", ["evals", "--json"]),
    ("catalog list", "buoy_search.catalog_cli._run_list", ["catalog", "list", "--json"]),
    ("catalog show", "buoy_search.catalog_cli._run_show", ["catalog", "show", "site-example-v1", "--json"]),
    (
        "catalog upsert",
        "buoy_search.catalog_cli._run_upsert",
        [
            "catalog", "upsert", "site-example-v1",
            "--source-kind", "website", "--source-uri", "https://example.com",
            "--site-id", "example", "--title", "Example", "--summary", "Example summary",
            "--embedding-model", "current/model", "--embedding-precision", "float32",
            "--plan-schema-version", "1", "--ranking-mode", "page", "--ranking-profile", "none",
            "--ranking-pool", "20", "--ranking-aggregation", "max", "--json",
        ],
    ),
    ("catalog enable", "buoy_search.catalog_cli._run_toggle", ["catalog", "enable", "site-example-v1", "--json"]),
    ("catalog disable", "buoy_search.catalog_cli._run_toggle", ["catalog", "disable", "site-example-v1", "--json"]),
    ("catalog remove preview", "buoy_search.catalog_cli._run_remove", ["catalog", "remove", "site-example-v1", "--json"]),
    ("catalog remove approved", "buoy_search.catalog_cli._run_remove", ["catalog", "remove", "site-example-v1", "--approve", "--json"]),
    ("catalog migrate preview", "buoy_search.catalog_cli._run_migrate_local", ["catalog", "migrate-local", "--source", "missing.json", "--json"]),
    ("catalog migrate approved", "buoy_search.catalog_cli._run_migrate_local", ["catalog", "migrate-local", "--source", "missing.json", "--approve", "--json"]),
    ("catalog reconcile", "buoy_search.catalog_cli._run_reconcile", ["catalog", "reconcile", "--pending", "missing.json", "--json"]),
    ("catalog abandon preview", "buoy_search.catalog_cli._run_abandon_pending", ["catalog", "abandon-pending", "--pending", "missing.json", "--json"]),
    ("catalog abandon approved", "buoy_search.catalog_cli._run_abandon_pending", ["catalog", "abandon-pending", "--pending", "missing.json", "--approve", "--json"]),
)


TOP_LEVEL_COMMANDS = ("crawl", "plan", "apply", "namespaces", "catalog", "retrieve", "evals")
CATALOG_COMMANDS = (
    "list", "show", "upsert", "enable", "disable", "remove", "migrate-local", "reconcile", "abandon-pending"
)


class EnvironmentAliasRemovalTests(unittest.TestCase):
    def test_every_real_command_rejects_each_removed_name_before_handler_dispatch(self) -> None:
        presence_cases = (
            ({"TURBO_SEARCH_EMBEDDING_MODEL": "model-secret"}, MODEL_ERROR),
            ({"TURBO_SEARCH_EMBEDDING_PRECISION": "precision-secret"}, PRECISION_ERROR),
            (
                {
                    "TURBO_SEARCH_EMBEDDING_PRECISION": "precision-secret",
                    "TURBO_SEARCH_EMBEDDING_MODEL": "model-secret",
                },
                BOTH_ERROR,
            ),
        )
        for name, target, argv in COMMAND_CASES:
            for environment, expected in presence_cases:
                with self.subTest(command=name, removed=tuple(environment)):
                    stdout = StringIO()
                    stderr = StringIO()
                    with patch.dict(os.environ, environment, clear=True), patch(
                        target
                    ) as handler, redirect_stdout(stdout), redirect_stderr(stderr):
                        result = main(argv)

                    self.assertEqual(result, 2)
                    self.assertEqual(stdout.getvalue(), "")
                    self.assertEqual(stderr.getvalue(), expected)
                    handler.assert_not_called()

    def test_presence_matrix_has_exact_value_redacted_diagnostics(self) -> None:
        cases = (
            ("model empty", {"TURBO_SEARCH_EMBEDDING_MODEL": ""}, MODEL_ERROR),
            ("precision empty", {"TURBO_SEARCH_EMBEDDING_PRECISION": ""}, PRECISION_ERROR),
            ("model old only", {"TURBO_SEARCH_EMBEDDING_MODEL": "old-model-secret"}, MODEL_ERROR),
            (
                "model old and new equal",
                {"TURBO_SEARCH_EMBEDDING_MODEL": "equal-model-secret", "BUOY_EMBEDDING_MODEL": "equal-model-secret"},
                MODEL_ERROR,
            ),
            (
                "model old and new different",
                {"TURBO_SEARCH_EMBEDDING_MODEL": "old-model-secret", "BUOY_EMBEDDING_MODEL": "new-model-secret"},
                MODEL_ERROR,
            ),
            (
                "precision old and new equal",
                {"TURBO_SEARCH_EMBEDDING_PRECISION": "equal-precision-secret", "BUOY_EMBEDDING_PRECISION": "equal-precision-secret"},
                PRECISION_ERROR,
            ),
            (
                "precision old and new different",
                {"TURBO_SEARCH_EMBEDDING_PRECISION": "old-precision-secret", "BUOY_EMBEDDING_PRECISION": "new-precision-secret"},
                PRECISION_ERROR,
            ),
            (
                "both model inserted first",
                {"TURBO_SEARCH_EMBEDDING_MODEL": "model-secret", "TURBO_SEARCH_EMBEDDING_PRECISION": "precision-secret"},
                BOTH_ERROR,
            ),
            (
                "both precision inserted first",
                {"TURBO_SEARCH_EMBEDDING_PRECISION": "precision-secret", "TURBO_SEARCH_EMBEDDING_MODEL": "model-secret"},
                BOTH_ERROR,
            ),
            (
                "both with new values and CLI overrides",
                {
                    "TURBO_SEARCH_EMBEDDING_PRECISION": "old-precision-secret",
                    "BUOY_EMBEDDING_PRECISION": "new-precision-secret",
                    "TURBO_SEARCH_EMBEDDING_MODEL": "old-model-secret",
                    "BUOY_EMBEDDING_MODEL": "new-model-secret",
                },
                BOTH_ERROR,
            ),
        )
        argv = [
            "retrieve", "question", "--dry-run", "--namespace", "site-example-v1", "--json",
            "--embedding-model", "cli/model", "--embedding-precision", "float16",
        ]
        for name, environment, expected in cases:
            with self.subTest(case=name):
                stdout = StringIO()
                stderr = StringIO()
                with patch.dict(os.environ, environment, clear=True), patch(
                    "buoy_search.cli._run_retrieve"
                ) as handler, redirect_stdout(stdout), redirect_stderr(stderr):
                    result = main(argv)

                self.assertEqual(result, 2)
                self.assertEqual(stdout.getvalue(), "")
                self.assertEqual(stderr.getvalue(), expected)
                self.assertEqual(stderr.getvalue().count("\n"), 1)
                for value in environment.values():
                    if value:
                        self.assertNotIn(value, stderr.getvalue())
                handler.assert_not_called()

    def test_help_version_and_parsed_no_handler_paths_remain_available(self) -> None:
        help_paths = [["--help"], *[[command, "--help"] for command in TOP_LEVEL_COMMANDS]]
        help_paths.extend([["catalog", command, "--help"] for command in CATALOG_COMMANDS])
        environment = {
            "TURBO_SEARCH_EMBEDDING_MODEL": "model-secret",
            "TURBO_SEARCH_EMBEDDING_PRECISION": "precision-secret",
        }
        for argv in help_paths:
            with self.subTest(argv=argv):
                stdout = StringIO()
                stderr = StringIO()
                with patch.dict(os.environ, environment, clear=True), redirect_stdout(stdout), redirect_stderr(stderr):
                    with self.assertRaises(SystemExit) as raised:
                        main(argv)
                self.assertEqual(raised.exception.code, 0)
                self.assertTrue(stdout.getvalue().startswith("usage: buoy"))
                self.assertEqual(stderr.getvalue(), "")

        stdout = StringIO()
        stderr = StringIO()
        with patch.dict(os.environ, environment, clear=True), redirect_stdout(stdout), redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as raised:
                main(["--version"])
        self.assertEqual(raised.exception.code, 0)
        self.assertRegex(stdout.getvalue(), r"^buoy \d+\.\d+\.\d+\n$")
        self.assertEqual(stderr.getvalue(), "")

        for argv in ([], ["catalog"]):
            with self.subTest(argv=argv):
                stdout = StringIO()
                stderr = StringIO()
                with patch.dict(os.environ, environment, clear=True), redirect_stdout(stdout), redirect_stderr(stderr):
                    result = main(argv)
                self.assertEqual(result, 0)
                self.assertTrue(stdout.getvalue().startswith("usage: buoy"))
                self.assertEqual(stderr.getvalue(), "")

    def test_module_help_paths_remain_available(self) -> None:
        environment = os.environ.copy()
        environment.update(
            {
                "PYTHONPATH": str(Path.cwd() / "src"),
                "TURBO_SEARCH_EMBEDDING_MODEL": "model-secret",
                "TURBO_SEARCH_EMBEDDING_PRECISION": "precision-secret",
            }
        )
        for module in ("buoy_search", "buoy_search.autoresearch"):
            with self.subTest(module=module):
                result = subprocess.run(
                    [sys.executable, "-m", module, "--help"],
                    text=True,
                    capture_output=True,
                    env=environment,
                    check=False,
                )
                self.assertEqual(result.returncode, 0)
                self.assertTrue(result.stdout.startswith("usage:"))
                self.assertEqual(result.stderr, "")

    def test_parser_failure_precedes_removed_environment_gate(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        with patch.dict(os.environ, {"TURBO_SEARCH_EMBEDDING_MODEL": "model-secret"}, clear=True), redirect_stdout(
            stdout
        ), redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as raised:
                main(["crawl"])

        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("the following arguments are required: --base-url", stderr.getvalue())
        self.assertNotIn("Removed environment", stderr.getvalue())

    def test_autoresearch_rejects_before_experiment_or_output_access(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            experiment = root / "missing-experiment.json"
            out_dir = root / "out"
            stdout = StringIO()
            stderr = StringIO()
            with patch.dict(
                os.environ,
                {
                    "TURBO_SEARCH_EMBEDDING_PRECISION": "precision-secret",
                    "TURBO_SEARCH_EMBEDDING_MODEL": "model-secret",
                },
                clear=True,
            ), patch("buoy_search.autoresearch.load_experiment") as load, patch(
                "buoy_search.autoresearch.run_experiment"
            ) as run, redirect_stdout(stdout), redirect_stderr(stderr):
                result = autoresearch.main(
                    ["--experiment", str(experiment), "--out", str(out_dir), "--json"]
                )

            self.assertEqual(result, 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertEqual(stderr.getvalue(), BOTH_ERROR)
            load.assert_not_called()
            run.assert_not_called()
            self.assertFalse(out_dir.exists())

    def test_autoresearch_help_and_parser_failure_precede_gate(self) -> None:
        environment = {"TURBO_SEARCH_EMBEDDING_MODEL": "model-secret"}
        stdout = StringIO()
        stderr = StringIO()
        with patch.dict(os.environ, environment, clear=True), redirect_stdout(stdout), redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as raised:
                autoresearch.main(["--help"])
        self.assertEqual(raised.exception.code, 0)
        self.assertTrue(stdout.getvalue().startswith("usage: python -m buoy_search.autoresearch"))
        self.assertEqual(stderr.getvalue(), "")

        stdout = StringIO()
        stderr = StringIO()
        with patch.dict(os.environ, environment, clear=True), redirect_stdout(stdout), redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as raised:
                autoresearch.main([])
        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("the following arguments are required: --experiment", stderr.getvalue())
        self.assertNotIn("Removed environment", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
