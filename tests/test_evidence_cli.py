from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from buoy_search.cli import build_parser, main


class EvidenceCliTests(unittest.TestCase):
    def test_parser_exposes_required_product_terms_and_defaults(self) -> None:
        parser = build_parser()
        estimate = parser.parse_args(["evidence", "estimate", "--namespace", "site-one-v1"])
        snapshot = parser.parse_args(["evidence", "snapshot", "--namespace", "site-one-v1"])
        verify = parser.parse_args(["evidence", "verify", "--snapshot-id", "evidence_0123456789abcdef"])
        self.assertEqual(estimate.evidence_command, "estimate")
        self.assertEqual(snapshot.evidence_command, "snapshot")
        self.assertEqual(verify.evidence_command, "verify")
        self.assertEqual(estimate.maximum_rows, 1_000_000)
        self.assertEqual(estimate.maximum_remote_logical_bytes, 5_368_709_120)

    def test_missing_credentials_fails_before_remote_function(self) -> None:
        stderr = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), patch(
            "buoy_search.evidence_remote.estimate_evidence_snapshot"
        ) as operation, redirect_stderr(stderr):
            result = main(["evidence", "estimate", "--namespace", "site-one-v1"])
        self.assertEqual(result, 2)
        self.assertIn("TURBOPUFFER_API_KEY", stderr.getvalue())
        operation.assert_not_called()

    def test_estimate_json_uses_injected_client_and_exact_namespace_list(self) -> None:
        client = object()
        payload = {
            "command": "evidence estimate",
            "namespace_count": 2,
            "would_pass_limits": True,
            "remote_writes_occurred": False,
        }
        stdout = io.StringIO()
        with patch.dict(os.environ, {"TURBOPUFFER_API_KEY": "secret"}, clear=True), patch(
            "buoy_search.evidence_cli.EVIDENCE_CLIENT_FACTORY", return_value=client
        ) as factory, patch(
            "buoy_search.evidence_remote.estimate_evidence_snapshot", return_value=payload
        ) as operation, redirect_stdout(stdout):
            result = main(
                [
                    "evidence", "estimate",
                    "--namespace", "site-b-v1",
                    "--namespace", "site-a-v1",
                    "--state-root", "/tmp/state",
                    "--json",
                ]
            )
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(stdout.getvalue()), payload)
        factory.assert_called_once()
        self.assertEqual(operation.call_args.kwargs["namespaces"], ["site-b-v1", "site-a-v1"])
        self.assertEqual(operation.call_args.kwargs["state_root"], Path("/tmp/state"))

    def test_estimate_limit_report_returns_failure_with_json_payload(self) -> None:
        payload = {
            "command": "evidence estimate",
            "would_pass_limits": False,
            "limit_error": "maximum-rows exceeded",
            "remote_writes_occurred": False,
        }
        stdout = io.StringIO()
        with patch.dict(os.environ, {"TURBOPUFFER_API_KEY": "secret"}, clear=True), patch(
            "buoy_search.evidence_cli.EVIDENCE_CLIENT_FACTORY", return_value=object()
        ), patch(
            "buoy_search.evidence_remote.estimate_evidence_snapshot", return_value=payload
        ), redirect_stdout(stdout):
            result = main(
                ["evidence", "estimate", "--namespace", "site-one-v1", "--json"]
            )
        self.assertEqual(result, 2)
        self.assertEqual(json.loads(stdout.getvalue()), payload)

    def test_import_and_help_are_provider_inert(self) -> None:
        code = """
import builtins, sys
real = builtins.__import__
def guarded(name, *args, **kwargs):
    if name == 'turbopuffer' or name.startswith('turbopuffer.'):
        raise AssertionError('provider import')
    return real(name, *args, **kwargs)
builtins.__import__ = guarded
from buoy_search.cli import main
assert main(['evidence', 'snapshot', '--help']) == 0
assert 'turbopuffer' not in sys.modules
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=Path(__file__).parents[1],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Bounded manifest root", result.stdout)


if __name__ == "__main__":
    unittest.main()
