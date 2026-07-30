from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch

from buoy_search.cli import build_parser, main
from buoy_search.semantics_models import LocalModelError, ModelContract


class SemanticsCliTests(unittest.TestCase):
    def test_parser_exposes_all_semantic_workflows_and_limits(self) -> None:
        parser = build_parser()
        common = ["--model-id", "local", "--model-revision", "sha256:" + "a" * 64, "--model-context-window", "8192"]
        estimate = parser.parse_args(["semantics", "estimate", "--snapshot-id", "evidence_test", *common])
        build = parser.parse_args(["semantics", "build", "--snapshot-id", "evidence_test", *common, "--sample-size", "5", "--resume"])
        verify = parser.parse_args(["semantics", "verify", "--build-id", "semantics_test"])
        inspect = parser.parse_args(["semantics", "inspect", "--build-id", "semantics_test", "--kind", "mentions", "--status", "provisional", "--limit", "100"])
        self.assertEqual((estimate.estimate_sample_rows, build.maximum_evidence_rows, build.model_concurrency), (20, 500, 1))
        self.assertEqual((build.sample_size, build.resume), (5, True))
        self.assertEqual(verify.semantics_command, "verify")
        self.assertEqual((inspect.kind, inspect.status, inspect.limit), ("mentions", "provisional", 100))
        with self.assertRaises(SystemExit):
            parser.parse_args(["semantics", "inspect", "--build-id", "semantics_test", "--kind", "concepts", "--limit", "101"])

    def test_parser_exposes_local_doctor_contract(self) -> None:
        parser = build_parser()
        args = parser.parse_args([
            "semantics", "doctor", "--model-id", "local-model",
            "--model-revision", "sha256:abc", "--model-context-window", "8192",
        ])
        self.assertEqual(args.semantics_command, "doctor")
        self.assertEqual(args.model_endpoint, "http://127.0.0.1:11434/v1")
        self.assertEqual(args.model_id, "local-model")
        self.assertEqual(args.model_context_window, 8192)
        self.assertEqual(args.model_seed, 0)

    def test_doctor_json_uses_explicit_contract_and_prints_activity(self) -> None:
        payload = {
            "command": "semantics doctor",
            "healthy": True,
            "evidence_transmitted": False,
            "turbopuffer_api_calls_occurred": False,
            "hosted_model_calls_occurred": False,
        }
        instance = Mock()
        instance.doctor.return_value = payload
        stdout = io.StringIO()
        with patch("buoy_search.semantics_local_model.OpenAICompatibleLocalClient", return_value=instance) as factory, redirect_stdout(stdout):
            result = main([
                "semantics", "doctor", "--model-endpoint", "http://localhost:1234/v1",
                "--model-id", "model", "--model-revision", "rev", "--model-context-window", "4096",
                "--model-timeout-seconds", "5", "--model-seed", "9", "--json",
            ])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(stdout.getvalue()), payload)
        self.assertEqual(factory.call_args.kwargs["endpoint"], "http://localhost:1234/v1")
        self.assertEqual(factory.call_args.kwargs["seed"], 9)
        self.assertEqual(factory.call_args.kwargs["timeout_seconds"], 5.0)

    def test_doctor_reports_sanitized_failure(self) -> None:
        stderr = io.StringIO()
        with patch(
            "buoy_search.semantics_local_model.OpenAICompatibleLocalClient",
            side_effect=LocalModelError("local model redirects are prohibited", code="redirect_prohibited"),
        ), redirect_stderr(stderr):
            result = main([
                "semantics", "doctor", "--model-id", "model", "--model-revision", "rev",
                "--model-context-window", "4096",
            ])
        self.assertEqual(result, 2)
        self.assertEqual(stderr.getvalue(), "local model redirects are prohibited\n")

    def test_invalid_context_and_timeout_are_parser_errors(self) -> None:
        parser = build_parser()
        for option, value in (("--model-context-window", "0"), ("--model-timeout-seconds", "nan")):
            with self.subTest(option=option), self.assertRaises(SystemExit):
                parser.parse_args([
                    "semantics", "doctor", "--model-id", "model", option, value,
                    *([] if option == "--model-context-window" else ["--model-context-window", "4096"]),
                ])

    def test_import_and_help_are_model_provider_and_connection_inert(self) -> None:
        code = r'''
import builtins, socket, sys
real_import = builtins.__import__
def guarded(name, *args, **kwargs):
    if name in {'turbopuffer', 'sentence_transformers', 'openai', 'anthropic'} or name.startswith(('turbopuffer.', 'sentence_transformers.', 'openai.', 'anthropic.')):
        raise AssertionError('provider/model import')
    return real_import(name, *args, **kwargs)
builtins.__import__ = guarded
def no_connection(*args, **kwargs):
    raise AssertionError('connection attempted')
socket.create_connection = no_connection
from buoy_search.cli import main
for argv in (['semantics', '--help'], ['semantics', 'doctor', '--help'], ['semantics', 'estimate', '--help'], ['semantics', 'build', '--help'], ['semantics', 'verify', '--help'], ['semantics', 'inspect', '--help']):
    try:
        main(argv)
    except SystemExit as exc:
        assert exc.code == 0
for forbidden in ('turbopuffer', 'sentence_transformers', 'openai', 'anthropic'):
    assert forbidden not in sys.modules
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=Path(__file__).parents[1],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("loopback local model", result.stdout)
        self.assertIn("synthetic local model contract", result.stdout)
        self.assertIn("without a", result.stdout)
        self.assertIn("local model", result.stdout)

    def test_estimate_passes_contract_probe_into_hard_model_call_budget(self) -> None:
        contract = ModelContract(
            1, "openai_chat_completions_local_v1", "fake", "1", "model",
            "sha256:" + "a" * 64, "runtime_digest", None, 4096, 0,
            True, True, "openai_json_schema", "semantics-doctor-v1",
        )
        model = Mock()
        model.doctor.return_value = {"model_contract": contract.to_dict()}
        payload = {
            "command": "semantics estimate",
            "would_pass_limits": False,
            "estimated_model_calls": 2,
            "model_call_count": 1,
        }
        output = io.StringIO()
        with patch("buoy_search.semantics_cli._model", return_value=model), patch(
            "buoy_search.semantics_cli._remote_client", return_value=Mock()
        ), patch(
            "buoy_search.semantics_remote.estimate_semantic_build",
            return_value=payload,
        ) as estimate, redirect_stdout(output):
            result = main([
                "semantics", "estimate", "--snapshot-id", "evidence_test",
                "--model-id", "model", "--model-revision", contract.model_revision,
                "--model-context-window", "4096", "--maximum-model-calls", "1",
                "--json",
            ])
        self.assertEqual(result, 2)
        self.assertEqual(estimate.call_args.kwargs["prior_model_calls"], 1)
        self.assertEqual(json.loads(output.getvalue())["contract_probe_model_calls"], 1)

    def test_build_activity_distinguishes_fresh_and_reused(self) -> None:
        contract = ModelContract(
            1, "openai_chat_completions_local_v1", "fake", "1", "model",
            "sha256:" + "a" * 64, "runtime_digest", None, 4096, 0,
            True, True, "openai_json_schema", "semantics-doctor-v1",
        )
        model = Mock()
        model.doctor.return_value = {"model_contract": contract.to_dict()}
        common = [
            "semantics", "build", "--snapshot-id", "evidence_test",
            "--model-id", "model", "--model-revision", contract.model_revision,
            "--model-context-window", "4096", "--json",
        ]
        for reused in (False, True):
            with self.subTest(reused=reused):
                output = io.StringIO()
                payload = {
                    "build_id": "semantics_test", "reused_build": reused,
                    "model_calls": 1 if reused else 4,
                    "local_manifest_written": True,
                    "turbopuffer_internal_writes_occurred": not reused,
                }
                with patch("buoy_search.semantics_cli._model", return_value=model), patch(
                    "buoy_search.semantics_cli._remote_client", return_value=Mock()
                ), patch(
                    "buoy_search.semantics_remote.create_semantic_build", return_value=payload
                ) as create, redirect_stdout(output):
                    self.assertEqual(main(common), 0)
                result = json.loads(output.getvalue())
                self.assertEqual(result["turbopuffer_internal_writes_occurred"], not reused)
                self.assertTrue(result["local_manifest_written"])
                self.assertEqual(create.call_args.kwargs["initial_model_calls"], 1)

    def test_help_requires_no_model_or_turbopuffer_environment(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            parser = build_parser()
            help_text = parser._subparsers._group_actions[0].choices["semantics"].format_help()
        self.assertIn("Hosted inference endpoints", help_text)
        self.assertNotIn("OpenAI API key", help_text)


if __name__ == "__main__":
    unittest.main()
