from __future__ import annotations

import unittest

from buoy_search.semantics_models import (
    LocalModelError,
    ModelContract,
    StructuredOutputError,
    StructuredResult,
    structured_chat_with_repair,
    validate_json_schema,
)


class SequencedClient:
    def __init__(self, values: list[StructuredResult | StructuredOutputError]) -> None:
        self.values = values
        self.messages: list[tuple[dict[str, str], ...]] = []

    def structured_chat(self, *, messages, schema, max_output_tokens):
        self.messages.append(tuple(dict(item) for item in messages))
        value = self.values.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value


class SemanticsModelsTests(unittest.TestCase):
    def test_model_contract_hash_is_stable_and_endpoint_free(self) -> None:
        contract = ModelContract(
            contract_version=1,
            runtime_protocol="openai_chat_completions_local_v1",
            runtime_identity="ollama",
            runtime_version="1.2.3",
            model_id="model",
            model_revision="sha256:" + "a" * 64,
            revision_verification="runtime_digest",
            model_quantization="Q4_K_M",
            model_context_window=8192,
            seed=7,
            seed_supported=True,
            structured_output_supported=True,
            structured_output_mode="openai_json_schema",
            prompt_contract_version="extract-v1",
        )
        self.assertEqual(contract.contract_hash, contract.contract_hash)
        self.assertNotIn("endpoint", contract.to_dict())
        changed = ModelContract(**{**contract.to_dict(), "seed": 8})
        self.assertNotEqual(contract.contract_hash, changed.contract_hash)

    def test_strict_schema_accepts_exact_bounded_object(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "minLength": 1, "maxLength": 10},
                "score": {"type": "number", "minimum": 0, "maximum": 1},
                "tags": {"type": "array", "items": {"type": "string"}, "maxItems": 2},
            },
            "required": ["name", "score", "tags"],
            "additionalProperties": False,
        }
        validate_json_schema({"name": "SSO", "score": 0.9, "tags": ["auth"]}, schema)

    def test_strict_schema_rejects_unknown_missing_and_invalid_values(self) -> None:
        schema = {
            "type": "object",
            "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"],
            "additionalProperties": False,
        }
        cases = [({}, "schema_required"), ({"ok": True, "extra": 1}, "schema_unknown_fields"), ({"ok": 1}, "schema_type")]
        for value, code in cases:
            with self.subTest(value=value), self.assertRaises(StructuredOutputError) as caught:
                validate_json_schema(value, schema)
            self.assertEqual(caught.exception.code, code)

    def test_schema_validates_omitted_optional_children_and_nested_bounds(self) -> None:
        invalid_schemas = [
            {
                "type": "object",
                "properties": {
                    "optional": {"type": "string", "pattern": "secret"},
                },
                "required": [],
                "additionalProperties": False,
            },
            {
                "type": "object",
                "properties": {
                    "optional": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 2},
                },
                "required": [],
                "additionalProperties": False,
            },
            {
                "type": "object",
                "properties": {"optional": {"type": "boolean", "minimum": 1}},
                "required": [],
                "additionalProperties": False,
            },
        ]
        for schema in invalid_schemas:
            with self.subTest(schema=schema), self.assertRaises(StructuredOutputError):
                validate_json_schema({}, schema)

    def test_schema_rejects_unimplemented_keywords(self) -> None:
        with self.assertRaises(StructuredOutputError) as caught:
            validate_json_schema("x", {"type": "string", "pattern": "x"})
        self.assertEqual(caught.exception.code, "schema_unsupported")

    def test_bounded_repair_reuses_context_and_reports_codes_only(self) -> None:
        secret = "PRIVATE EVIDENCE"
        invalid = '{"ok":"PRIVATE INVALID MODEL OUTPUT"}'
        client = SequencedClient([
            StructuredOutputError(
                "safe", code="malformed_json", invalid_output=invalid
            ),
            StructuredResult({"ok": True}, 10, 0.1),
        ])
        result = structured_chat_with_repair(
            client,
            messages=({"role": "user", "content": secret},),
            schema={
                "type": "object",
                "properties": {"ok": {"type": "boolean"}},
                "required": ["ok"],
                "additionalProperties": False,
            },
            max_output_tokens=10,
        )
        self.assertEqual(result.retry_count, 1)
        self.assertEqual(result.validation_codes, ("malformed_json",))
        self.assertEqual(client.messages[0][0]["content"], secret)
        self.assertEqual(client.messages[1][0]["content"], secret)
        self.assertIn("malformed_json", client.messages[1][-1]["content"])
        self.assertIn(invalid, client.messages[1][-1]["content"])
        self.assertNotIn(secret, client.messages[1][-1]["content"])
        self.assertNotIn("PRIVATE INVALID", str(StructuredOutputError(
            "safe", code="x", invalid_output=invalid
        )))

    def test_bounded_repair_caps_retries_and_sanitizes_exhaustion(self) -> None:
        client = SequencedClient([
            StructuredOutputError("private one", code="one"),
            StructuredOutputError("private two", code="two"),
            StructuredOutputError("private three", code="three"),
        ])
        with self.assertRaises(StructuredOutputError) as caught:
            structured_chat_with_repair(
                client,
                messages=({"role": "user", "content": "evidence"},),
                schema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                    "additionalProperties": False,
                },
                max_output_tokens=10,
            )
        self.assertEqual(caught.exception.code, "repair_exhausted")
        self.assertEqual(len(client.messages), 3)
        self.assertNotIn("private", str(caught.exception))
        with self.assertRaises(LocalModelError):
            structured_chat_with_repair(
                client,
                messages=(),
                schema={},
                max_output_tokens=1,
                maximum_retries=3,
            )

    def test_local_model_errors_expose_only_sanitized_code(self) -> None:
        error = LocalModelError("safe", code="timeout")
        self.assertEqual(str(error), "safe")
        self.assertEqual(error.code, "timeout")


if __name__ == "__main__":
    unittest.main()
