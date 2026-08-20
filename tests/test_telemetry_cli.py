from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import os
from pathlib import Path
import subprocess
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from buoy_search.entrypoint import main as entrypoint_main
from buoy_search.telemetry_cli import build_parser, main as telemetry_main


class TelemetryCliTests(unittest.TestCase):
    def test_parser_registers_status_and_flush(self) -> None:
        parser = build_parser()
        choices = parser._subparsers._group_actions[0].choices
        self.assertEqual(set(choices), {"status", "flush"})
        args = parser.parse_args(["flush"])
        self.assertEqual(args.timeout, 30.0)
        self.assertFalse(args.json)

    def test_timeout_rejects_nonfinite_and_out_of_range_values(self) -> None:
        parser = build_parser()
        for value in ("nan", "inf", "-0.1", "120.1", "not-a-number"):
            with self.subTest(value=value), redirect_stderr(StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    parser.parse_args(["flush", "--timeout", value])
            self.assertEqual(raised.exception.code, 2)

    def test_status_handler_is_lazy_and_skips_removed_model_environment(self) -> None:
        fake_writer = ModuleType("buoy_search.telemetry_writer")
        calls: list[bool] = []

        def status(*, json_output: bool):
            calls.append(json_output)
            return SimpleNamespace(exit_code=1, output='{"overall":"degraded"}')

        fake_writer.telemetry_status_command = status  # type: ignore[attr-defined]
        stdout = StringIO()
        stderr = StringIO()
        environment = {
            "TURBO_SEARCH_EMBEDDING_MODEL": "removed-value",
            "TURBO_SEARCH_EMBEDDING_PRECISION": "removed-value",
        }
        with (
            patch.dict(os.environ, environment, clear=True),
            patch.dict(sys.modules, {"buoy_search.telemetry_writer": fake_writer}),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            result = entrypoint_main(["telemetry", "status", "--json"])

        self.assertEqual(result, 1)
        self.assertEqual(calls, [True])
        self.assertEqual(stdout.getvalue(), '{"overall":"degraded"}\n')
        self.assertEqual(stderr.getvalue(), "")

    def test_flush_handler_passes_exact_timeout_and_output_mode(self) -> None:
        fake_writer = ModuleType("buoy_search.telemetry_writer")
        calls: list[tuple[float, bool]] = []

        def flush(*, timeout: float, json_output: bool):
            calls.append((timeout, json_output))
            return SimpleNamespace(exit_code=0, output='{"outcome":"empty"}')

        fake_writer.telemetry_flush_command = flush  # type: ignore[attr-defined]
        stdout = StringIO()
        with (
            patch.dict(sys.modules, {"buoy_search.telemetry_writer": fake_writer}),
            redirect_stdout(stdout),
        ):
            result = telemetry_main(
                ["flush", "--timeout", "0.25", "--json"]
            )

        self.assertEqual(result, 0)
        self.assertEqual(calls, [(0.25, True)])
        self.assertEqual(stdout.getvalue(), '{"outcome":"empty"}\n')

    def test_telemetry_dispatch_never_imports_the_legacy_cli(self) -> None:
        fake_writer = ModuleType("buoy_search.telemetry_writer")
        fake_writer.telemetry_status_command = lambda **_kwargs: SimpleNamespace(
            exit_code=0,
            output="Telemetry: overall=disabled",
        )
        stdout = StringIO()
        with (
            patch.dict(
                sys.modules,
                {
                    "buoy_search.cli": None,
                    "buoy_search.telemetry_writer": fake_writer,
                },
            ),
            redirect_stdout(stdout),
        ):
            result = entrypoint_main(["telemetry", "status"])

        self.assertEqual(result, 0)
        self.assertEqual(stdout.getvalue(), "Telemetry: overall=disabled\n")

    def test_entrypoint_and_telemetry_import_without_legacy_cli(self) -> None:
        script = """
import importlib.abc
import sys

class RejectLegacyCli(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "buoy_search.cli":
            raise AssertionError("legacy CLI imported")
        return None

sys.meta_path.insert(0, RejectLegacyCli())
import buoy_search.entrypoint
import buoy_search.telemetry_cli
assert "buoy_search.cli" not in sys.modules
"""
        completed = subprocess.run(
            [sys.executable, "-I", "-c", script],
            cwd=Path(__file__).resolve().parents[1],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

        self.assertEqual(
            completed.returncode,
            0,
            msg=f"stdout={completed.stdout!r} stderr={completed.stderr!r}",
        )

    def test_nontelemetry_dispatch_lazily_delegates_to_legacy_cli(self) -> None:
        fake_cli = ModuleType("buoy_search.cli")
        calls: list[list[str]] = []

        def legacy(argv: list[str]) -> int:
            calls.append(argv)
            return 7

        fake_cli.main = legacy  # type: ignore[attr-defined]
        with patch.dict(sys.modules, {"buoy_search.cli": fake_cli}):
            result = entrypoint_main(["retrieve", "question", "--dry-run"])

        self.assertEqual(result, 7)
        self.assertEqual(calls, [["retrieve", "question", "--dry-run"]])

    def test_nontelemetry_dispatch_preserves_removed_environment_gate(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        with (
            patch.dict(
                os.environ,
                {"TURBO_SEARCH_EMBEDDING_MODEL": "must-not-be-reported"},
                clear=True,
            ),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            result = entrypoint_main(["retrieve", "question", "--dry-run"])

        self.assertEqual(result, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(
            stderr.getvalue(),
            "Removed environment variable is not supported in Buoy 0.4.0: "
            "TURBO_SEARCH_EMBEDDING_MODEL -> BUOY_EMBEDDING_MODEL\n",
        )
        self.assertNotIn("must-not-be-reported", stderr.getvalue())

    def test_installed_and_module_entrypoints_use_lightweight_dispatch(self) -> None:
        root = Path(__file__).resolve().parents[1]
        pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
        module_main = (
            root / "src" / "buoy_search" / "__main__.py"
        ).read_text(encoding="utf-8")

        self.assertIn('buoy = "buoy_search.entrypoint:main"', pyproject)
        self.assertIn("from buoy_search.entrypoint import main", module_main)


if __name__ == "__main__":
    unittest.main()
