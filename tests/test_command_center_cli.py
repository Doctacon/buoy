from __future__ import annotations

from contextlib import redirect_stderr
from io import StringIO
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from buoy_search.cli import build_parser, main
from buoy_search.command_center_server import CommandCenterDependencyError, UI_DEPENDENCY_GUIDANCE


class CommandCenterCliTests(unittest.TestCase):
    def test_serve_help_and_defaults(self) -> None:
        parser = build_parser()
        serve = parser._subparsers._group_actions[0].choices["serve"]
        help_text = serve.format_help()
        self.assertIn("--no-browser", help_text)
        self.assertIn("--artifacts-root", help_text)
        self.assertIn("--state-root", help_text)
        self.assertIn("one managed public website or public GitHub plan", help_text)
        self.assertIn("Apply remains an explicit CLI action", help_text)
        option_help = {action.dest: action.help for action in serve._actions}
        self.assertIn("command-center/plans", option_help["artifacts_root"])
        self.assertIn("command-center/jobs", option_help["state_root"])

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("buoy_search.applied_state.DEFAULT_STATE_ROOT", root / ".buoy"), patch(
                "buoy_search.applied_state.LEGACY_STATE_ROOT", root / ".turbo-search"
            ), patch("buoy_search.command_center_server.run_server") as runner, patch.dict(
                os.environ, {}, clear=True
            ):
                result = main(["serve"])

        self.assertEqual(result, 0)
        runner.assert_called_once_with(
            host="127.0.0.1",
            port=8765,
            artifacts_root=Path("artifacts/site-crawls"),
            state_root=root / ".buoy",
            open_browser=True,
        )

    def test_serve_no_browser_and_custom_options(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifacts = root / "plans"
            state = root / "state"
            with patch("buoy_search.command_center_server.run_server") as runner, patch.dict(
                os.environ, {}, clear=True
            ):
                result = main(
                    [
                        "serve",
                        "--host",
                        "::1",
                        "--port",
                        "9876",
                        "--artifacts-root",
                        str(artifacts),
                        "--state-root",
                        str(state),
                        "--no-browser",
                    ]
                )

        self.assertEqual(result, 0)
        runner.assert_called_once_with(
            host="::1",
            port=9876,
            artifacts_root=artifacts,
            state_root=state,
            open_browser=False,
        )

    def test_serve_rejects_every_non_allowlisted_host_before_startup(self) -> None:
        rejected = ["0.0.0.0", "::", "127.0.0.2", "example.com", "LOCALHOST", "localhost."]
        for host in rejected:
            with self.subTest(host=host), patch(
                "buoy_search.command_center_server.run_server"
            ) as runner, self.assertRaises(SystemExit) as raised:
                main(["serve", "--host", host])
            self.assertEqual(raised.exception.code, 2)
            runner.assert_not_called()

    def test_missing_ui_dependencies_are_actionable(self) -> None:
        stderr = StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state"
            with patch(
                "buoy_search.command_center_server.run_server",
                side_effect=CommandCenterDependencyError(UI_DEPENDENCY_GUIDANCE),
            ), patch.dict(os.environ, {}, clear=True), redirect_stderr(stderr):
                result = main(["serve", "--state-root", str(state), "--no-browser"])

        self.assertEqual(result, 2)
        self.assertIn("uv sync --extra ui", stderr.getvalue())

    def test_ordinary_cli_import_does_not_load_optional_or_provider_packages(self) -> None:
        script = """
import json
import sys
import buoy_search.cli
watched = [
    'fastapi', 'uvicorn', 'turbopuffer', 'sentence_transformers', 'transformers',
    'buoy_search.bigquery_relation', 'buoy_search.snowflake_relation',
    'google.cloud.bigquery', 'snowflake.connector',
]
print(json.dumps({name: name in sys.modules for name in watched}, sort_keys=True))
"""
        completed = subprocess.run(
            [sys.executable, "-c", script],
            check=True,
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parents[1],
        )
        self.assertEqual(set(__import__("json").loads(completed.stdout).values()), {False})


if __name__ == "__main__":
    unittest.main()
