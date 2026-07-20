from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "c6_syntax_forecast", ROOT / "scripts" / "c6_syntax_forecast.py"
)
assert SPEC and SPEC.loader
forecast_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(forecast_module)


class C6SyntaxForecastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.forecast = forecast_module.read_json(ROOT / forecast_module.FORECAST_PATH)
        cls.authority = forecast_module.read_json(ROOT / forecast_module.AUTHORITY_PATH)
        cls.token_report = forecast_module.read_json(ROOT / forecast_module.TOKEN_REPORT_PATH)

    @staticmethod
    def _resign(payload: dict[str, object]) -> None:
        payload["artifact_sha256"] = forecast_module.artifact_sha256(payload)

    def _assert_forecast_mutation_rejected(self, mutate) -> None:
        changed = copy.deepcopy(self.forecast)
        mutate(changed)
        self._resign(changed)
        with self.assertRaises(ValueError):
            forecast_module.validate_forecast(changed, self.authority)

    def _assert_token_mutation_rejected(self, mutate, forecast=None) -> None:
        changed = copy.deepcopy(self.token_report)
        mutate(changed)
        self._resign(changed)
        with self.assertRaises(ValueError):
            forecast_module.validate_token_report(changed, forecast or self.forecast)

    def test_checked_in_forecast_and_exact_token_checkpoint_validate(self) -> None:
        forecast_module.validate_forecast(self.forecast, self.authority)
        forecast_module.validate_token_report(self.token_report, self.forecast)
        self.assertFalse(self.token_report["summary"]["ready"])
        self.assertGreater(self.token_report["summary"]["incompatible_rows"], 0)
        self.assertEqual(
            forecast_module.canonical_sha256(self.authority),
            forecast_module.AUTHORITY_SHA256,
        )

    def test_forecast_rejects_mutated_compact_authority(self) -> None:
        changed = copy.deepcopy(self.authority)
        changed["forecast"]["safety"]["namespace_writes"] = 1
        with self.assertRaisesRegex(ValueError, "authority hash mismatch"):
            forecast_module.validate_forecast(self.forecast, changed)

    def test_forecast_rejects_plan_artifact_and_signature_identity_mutations(self) -> None:
        mutations = {
            "artifact hash": lambda value: value["repositories"]["buoy"]["arms"]["python-ast"].__setitem__("artifact_hash", "0" * 64),
            "plan id": lambda value: value["repositories"]["pytest"]["arms"]["current-default"].__setitem__("plan_id", "plan_0000000000000000"),
            "plan signature": lambda value: value["repositories"]["ruff"]["arms"]["python-ast"].__setitem__("plan_signature_sha256", "0" * 64),
            "plan file hash": lambda value: value["repositories"]["buoy"]["arms"]["python-ast"]["local_artifact_file_sha256"].__setitem__("plan.json", "0" * 64),
            "manifest file hash": lambda value: value["repositories"]["buoy"]["arms"]["python-ast"]["local_artifact_file_sha256"].__setitem__("manifest.json", "0" * 64),
            "JSONL file hash": lambda value: value["repositories"]["buoy"]["arms"]["python-ast"]["local_artifact_file_sha256"].__setitem__("chunks.jsonl", "0" * 64),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                self._assert_forecast_mutation_rejected(mutate)

    def test_forecast_rejects_control_header_namespace_and_fallback_mutations(self) -> None:
        mutations = {
            "control parity": lambda value: value["repositories"]["buoy"].__setitem__("current_default_equivalent_to_ordinary_no_arm", False),
            "ordinary control signature": lambda value: value["repositories"]["pytest"].__setitem__("ordinary_no_arm_plan_signature_sha256", "0" * 64),
            "header identity": lambda value: value["repositories"]["ruff"]["arms"]["python-ast"].__setitem__("header_identity_sha256", "0" * 64),
            "namespace": lambda value: value["repositories"]["buoy"]["arms"]["python-ast"].__setitem__("namespace", "mutated"),
            "fallback path hash": lambda value: value["fallback_path_categories"]["ruff"]["python_parse_fallback"].__setitem__("paths_sha256", "0" * 64),
            "fallback category count": lambda value: value["fallback_path_categories"]["pytest"]["non_python_fallback"].__setitem__("count", 54),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                self._assert_forecast_mutation_rejected(mutate)

    def test_forecast_rejects_citation_treatment_isolation_and_safety_mutations(self) -> None:
        mutations = {
            "treatment citation": lambda value: value["repositories"]["buoy"]["arms"]["python-ast"]["chunk_distribution"].__setitem__("source_rows_without_parseable_lines_component", 1),
            "citation path hash": lambda value: value["preflight_findings"].__setitem__("ruff_current_default_affected_paths_sha256", "0" * 64),
            "metadata treatment": lambda value: value["settings"].__setitem__("repo_search_metadata", True),
            "namespace write": lambda value: value["safety"].__setitem__("namespace_writes", 1),
            "provider call": lambda value: value["safety"].__setitem__("provider_calls", 1),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                self._assert_forecast_mutation_rejected(mutate)

    def test_forecast_rejects_jsonl_content_row_class_and_summary_mutations(self) -> None:
        mutations = {
            "row class": lambda value: value["repositories"]["buoy"]["arms"]["python-ast"].__setitem__("source_rows", 1299),
            "content bytes": lambda value: value["repositories"]["pytest"]["arms"]["current-default"]["storage_estimates_bytes"].__setitem__("content_utf8", 2844425),
            "JSONL bytes": lambda value: value["repositories"]["ruff"]["arms"]["python-ast"]["storage_estimates_bytes"].__setitem__("serialized_plan_chunks_jsonl", 129330409),
            "raw-vector bytes": lambda value: value["repositories"]["pytest"]["arms"]["current-default"]["storage_estimates_bytes"].__setitem__("raw_384_dim_f16_vectors", 2682626),
            "token row classes": lambda value: value["repositories"]["buoy"]["arms"]["python-ast"]["token_distribution"]["header_rows"].__setitem__("count", 47),
            "token buckets": lambda value: value["repositories"]["buoy"]["arms"]["python-ast"]["token_distribution"]["all_final_row_buckets"].__setitem__("0-64", 593),
            "arm total": lambda value: value["totals"]["python-ast"].__setitem__("final_rows", 53304),
            "approval arithmetic": lambda value: value["approval_checkpoint"].__setitem__("maximum_rows_and_estimated_row_writes", 151991),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                self._assert_forecast_mutation_rejected(mutate)

    def test_token_report_rejects_rows_scanned_plan_counts_and_row_classes(self) -> None:
        mutations = {
            "summary rows scanned": lambda value: value["summary"].__setitem__("rows_scanned", 91213),
            "per-plan rows scanned": lambda value: value["per_plan"]["ruff"]["python-ast"].__setitem__("rows_scanned", 44984),
            "per-plan incompatible count": lambda value: value["per_plan"]["buoy"]["python-ast"].__setitem__("incompatible_rows", 122),
            "row classes": lambda value: value["summary"]["row_classes"].__setitem__("source", 54577),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                self._assert_token_mutation_rejected(mutate)

    def test_token_report_rejects_maximum_and_tokenizer_contract_mutations(self) -> None:
        mutations = {
            "maximum tokens": lambda value: value["summary"].__setitem__("maximum_observed_tokens", 12784),
            "revision": lambda value: value["tokenizer"].__setitem__("revision", "0" * 40),
            "tokenizer file": lambda value: value["tokenizer"]["files"][0].__setitem__("sha256", "0" * 64),
            "tokenizer files hash": lambda value: value["tokenizer"].__setitem__("files_sha256", "0" * 64),
            "special tokens": lambda value: value["tokenizer"].__setitem__("add_special_tokens", False),
            "truncation": lambda value: value["tokenizer"].__setitem__("truncation", True),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                self._assert_token_mutation_rejected(mutate)

    def test_token_report_rejects_safety_and_duplicated_checkpoint_mutations(self) -> None:
        safety_mutations = {
            "network calls": lambda value: value["safety"].__setitem__("network_calls", 1),
            "model construction": lambda value: value["safety"].__setitem__("model_constructions", 1),
            "remote write": lambda value: value["safety"].__setitem__("remote_writes", 1),
        }
        for name, mutate in safety_mutations.items():
            with self.subTest(name=name):
                self._assert_token_mutation_rejected(mutate)

        checkpoint_fields = (
            "artifact_sha256",
            "incompatible_paths",
            "incompatible_paths_sha256",
            "incompatible_rows",
            "incompatible_rows_sha256",
            "maximum_observed_tokens",
            "model",
            "model_max_tokens",
            "ready",
            "revision",
            "tokenizer_files_sha256",
        )
        for field in checkpoint_fields:
            with self.subTest(checkpoint_field=field):
                changed_forecast = copy.deepcopy(self.forecast)
                original = changed_forecast["model_tokenizer_preflight"][field]
                changed_forecast["model_tokenizer_preflight"][field] = not original if isinstance(original, bool) else (original + 1 if isinstance(original, int) else f"mutated-{original}")
                with self.assertRaisesRegex(ValueError, f"forecast/token report {field} mismatch"):
                    forecast_module.validate_token_report(self.token_report, changed_forecast)

    def test_token_report_rejects_a_row_at_or_below_the_model_maximum(self) -> None:
        changed = copy.deepcopy(self.token_report)
        changed["incompatible_rows"][0]["token_count"] = forecast_module.MODEL_MAX_TOKENS
        changed["summary"]["incompatible_rows_sha256"] = forecast_module.canonical_sha256(
            changed["incompatible_rows"]
        )
        self._resign(changed)
        with self.assertRaisesRegex(ValueError, "compatible row"):
            forecast_module.validate_token_report(changed, self.forecast)


if __name__ == "__main__":
    unittest.main()
