"""Provider-independent contracts for local-only semantic inference.

Importing this module performs no network, credential, provider, or model work.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Mapping, Protocol, Sequence

LOCAL_CHAT_PROTOCOL = "openai_chat_completions_local_v1"
MODEL_CONTRACT_VERSION = 1
DETERMINISM_BEST_EFFORT = "best_effort"
STRUCTURED_OUTPUT_MODES = ("openai_json_schema", "llama_cpp_json_schema")
MAX_STRUCTURED_REPAIR_RETRIES = 2


class LocalModelError(ValueError):
    """Sanitized local-model contract or transport failure."""

    def __init__(self, message: str, *, code: str = "local_model_error") -> None:
        super().__init__(message)
        self.code = code


class StructuredOutputError(LocalModelError):
    """Sanitized strict-output failure with optional process-local repair input."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "structured_output_error",
        invalid_output: str | None = None,
    ) -> None:
        super().__init__(message, code=code)
        # 10x: kept private and bounded solely for the next in-memory repair
        # request; never include it in repr/str, logs, records, or persistence.
        self._invalid_output = (
            invalid_output[:16_384] if isinstance(invalid_output, str) else None
        )


@dataclass(frozen=True)
class ModelContract:
    contract_version: int
    runtime_protocol: str
    runtime_identity: str
    runtime_version: str | None
    model_id: str
    model_revision: str
    revision_verification: str
    model_quantization: str | None
    model_context_window: int
    seed: int
    seed_supported: bool
    structured_output_supported: bool
    structured_output_mode: str
    prompt_contract_version: str
    determinism: str = DETERMINISM_BEST_EFFORT

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @property
    def contract_hash(self) -> str:
        encoded = canonical_json(self.to_dict()).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class StructuredResult:
    value: dict[str, object]
    response_bytes: int
    latency_seconds: float


@dataclass(frozen=True)
class RepairedStructuredResult:
    result: StructuredResult
    retry_count: int
    validation_codes: tuple[str, ...]


class LocalInferenceClient(Protocol):
    def structured_chat(
        self,
        *,
        messages: Sequence[Mapping[str, str]],
        schema: Mapping[str, object],
        max_output_tokens: int,
    ) -> StructuredResult: ...


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def validate_json_schema_contract(schema: Mapping[str, object]) -> None:
    """Validate every node in Buoy's deliberately small JSON-schema subset."""

    if not isinstance(schema, Mapping):
        raise StructuredOutputError("structured output schema is invalid", code="schema_invalid")
    allowed = {
        "type", "required", "properties", "additionalProperties", "enum",
        "items", "minItems", "maxItems", "minLength", "maxLength",
        "minimum", "maximum", "description",
    }
    if set(schema) - allowed:
        raise StructuredOutputError("structured output schema is unsupported", code="schema_unsupported")
    if "description" in schema and not isinstance(schema["description"], str):
        raise StructuredOutputError("structured output schema is invalid", code="schema_invalid")
    expected = schema.get("type")
    if expected not in {"object", "array", "string", "boolean", "integer", "number"}:
        raise StructuredOutputError("structured output schema is unsupported", code="schema_unsupported")
    allowed_by_type = {
        "object": {"type", "required", "properties", "additionalProperties", "description"},
        "array": {"type", "items", "minItems", "maxItems", "description"},
        "string": {"type", "minLength", "maxLength", "enum", "description"},
        "boolean": {"type", "enum", "description"},
        "integer": {"type", "minimum", "maximum", "enum", "description"},
        "number": {"type", "minimum", "maximum", "enum", "description"},
    }
    if set(schema) - allowed_by_type[str(expected)]:
        raise StructuredOutputError("structured output schema is unsupported", code="schema_unsupported")
    if expected == "object":
        properties = schema.get("properties")
        required = schema.get("required")
        additional = schema.get("additionalProperties")
        if (
            not isinstance(properties, Mapping)
            or not isinstance(required, list)
            or any(not isinstance(item, str) for item in required)
            or len(required) != len(set(required))
            or not set(required).issubset(properties)
            or type(additional) is not bool
        ):
            raise StructuredOutputError("structured output schema is invalid", code="schema_invalid")
        for name, child in properties.items():
            if not isinstance(name, str) or not isinstance(child, Mapping):
                raise StructuredOutputError("structured output schema is invalid", code="schema_invalid")
            validate_json_schema_contract(child)
    elif expected == "array":
        items = schema.get("items")
        if not isinstance(items, Mapping):
            raise StructuredOutputError("structured output schema is invalid", code="schema_invalid")
        _validate_schema_bounds(schema, "Items")
        validate_json_schema_contract(items)
    elif expected == "string":
        _validate_schema_bounds(schema, "Length")
    elif expected in {"integer", "number"}:
        _validate_numeric_schema_bounds(schema)
    enum = schema.get("enum")
    if enum is not None:
        if not isinstance(enum, list) or not enum:
            raise StructuredOutputError("structured output schema is invalid", code="schema_invalid")
        for item in enum:
            if expected == "string" and not isinstance(item, str):
                raise StructuredOutputError("structured output schema is invalid", code="schema_invalid")
            if expected == "boolean" and type(item) is not bool:
                raise StructuredOutputError("structured output schema is invalid", code="schema_invalid")
            if expected == "integer" and type(item) is not int:
                raise StructuredOutputError("structured output schema is invalid", code="schema_invalid")
            if expected == "number" and (
                isinstance(item, bool)
                or not isinstance(item, (int, float))
                or not math.isfinite(float(item))
            ):
                raise StructuredOutputError("structured output schema is invalid", code="schema_invalid")


def validate_json_schema(value: object, schema: Mapping[str, object]) -> None:
    """Validate one value after first validating the complete schema tree."""

    validate_json_schema_contract(schema)
    _validate_json_value(value, schema)


def _validate_json_value(value: object, schema: Mapping[str, object]) -> None:
    expected = schema["type"]
    if expected == "object":
        if not isinstance(value, dict):
            raise StructuredOutputError("structured output has an invalid type", code="schema_type")
        properties = schema["properties"]
        required = schema["required"]
        assert isinstance(properties, Mapping) and isinstance(required, list)
        if set(required) - set(value):
            raise StructuredOutputError("structured output is missing required fields", code="schema_required")
        if schema["additionalProperties"] is False and set(value) - set(properties):
            raise StructuredOutputError("structured output has unknown fields", code="schema_unknown_fields")
        for key, item in value.items():
            child = properties.get(key)
            if isinstance(child, Mapping):
                _validate_json_value(item, child)
    elif expected == "array":
        if not isinstance(value, list):
            raise StructuredOutputError("structured output has an invalid type", code="schema_type")
        _validate_count(value, schema, "Items")
        child = schema["items"]
        assert isinstance(child, Mapping)
        for item in value:
            _validate_json_value(item, child)
    elif expected == "string":
        if not isinstance(value, str):
            raise StructuredOutputError("structured output has an invalid type", code="schema_type")
        _validate_count(value, schema, "Length")
    elif expected == "boolean":
        if type(value) is not bool:
            raise StructuredOutputError("structured output has an invalid type", code="schema_type")
    elif expected == "integer":
        if type(value) is not int:
            raise StructuredOutputError("structured output has an invalid type", code="schema_type")
        _validate_number(float(value), schema)
    elif expected == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise StructuredOutputError("structured output has an invalid number", code="schema_number")
        _validate_number(float(value), schema)
    enum = schema.get("enum")
    if enum is not None and value not in enum:
        raise StructuredOutputError("structured output has an invalid enum value", code="schema_enum")


def structured_chat_with_repair(
    client: LocalInferenceClient,
    *,
    messages: Sequence[Mapping[str, str]],
    schema: Mapping[str, object],
    max_output_tokens: int,
    maximum_retries: int = MAX_STRUCTURED_REPAIR_RETRIES,
) -> RepairedStructuredResult:
    """Retry schema failures with the same caller context and safe validation codes.

    The evidence-bearing caller messages are copied unchanged on every attempt.
    Only a bounded generic repair instruction and sanitized validation code are
    added. Raw model output is never surfaced or persisted by this helper.
    """

    if type(maximum_retries) is not int or not 0 <= maximum_retries <= MAX_STRUCTURED_REPAIR_RETRIES:
        raise LocalModelError("structured repair retries must be between zero and two", code="repair_retries")
    original = tuple(dict(message) for message in messages)
    codes: list[str] = []
    invalid_output: str | None = None
    for attempt in range(maximum_retries + 1):
        request_messages = original
        if attempt:
            prior = invalid_output or "<unavailable>"
            request_messages = (*original, {
                "role": "user",
                "content": (
                    "Repair the prior structured response below. Return only JSON matching the "
                    f"supplied schema. Validation code: {codes[-1]}.\n"
                    f"<invalid-structured-output>{prior}</invalid-structured-output>"
                ),
            })
        try:
            result = client.structured_chat(
                messages=request_messages,
                schema=schema,
                max_output_tokens=max_output_tokens,
            )
            return RepairedStructuredResult(result, attempt, tuple(codes))
        except StructuredOutputError as exc:
            codes.append(exc.code[:64])
            invalid_output = exc._invalid_output
            if attempt == maximum_retries:
                raise StructuredOutputError(
                    "local model structured output remained invalid after bounded repair",
                    code="repair_exhausted",
                ) from None
    raise AssertionError("unreachable")


def _validate_schema_bounds(schema: Mapping[str, object], suffix: str) -> None:
    lower = schema.get(f"min{suffix}")
    upper = schema.get(f"max{suffix}")
    if lower is not None and (type(lower) is not int or lower < 0):
        raise StructuredOutputError("structured output schema is invalid", code="schema_invalid")
    if upper is not None and (type(upper) is not int or upper < 0):
        raise StructuredOutputError("structured output schema is invalid", code="schema_invalid")
    if lower is not None and upper is not None and lower > upper:
        raise StructuredOutputError("structured output schema is invalid", code="schema_invalid")


def _validate_numeric_schema_bounds(schema: Mapping[str, object]) -> None:
    lower = schema.get("minimum")
    upper = schema.get("maximum")
    for bound in (lower, upper):
        if bound is not None and (
            isinstance(bound, bool)
            or not isinstance(bound, (int, float))
            or not math.isfinite(float(bound))
        ):
            raise StructuredOutputError("structured output schema is invalid", code="schema_invalid")
    if lower is not None and upper is not None and float(lower) > float(upper):
        raise StructuredOutputError("structured output schema is invalid", code="schema_invalid")


def _validate_count(value: Sequence[object], schema: Mapping[str, object], suffix: str) -> None:
    lower = schema.get(f"min{suffix}")
    upper = schema.get(f"max{suffix}")
    if lower is not None and len(value) < lower:
        raise StructuredOutputError("structured output is shorter than allowed", code="schema_minimum")
    if upper is not None and len(value) > upper:
        raise StructuredOutputError("structured output is longer than allowed", code="schema_maximum")


def _validate_number(value: float, schema: Mapping[str, object]) -> None:
    lower = schema.get("minimum")
    upper = schema.get("maximum")
    if lower is not None and value < float(lower):
        raise StructuredOutputError("structured output number is below minimum", code="schema_minimum")
    if upper is not None and value > float(upper):
        raise StructuredOutputError("structured output number is above maximum", code="schema_maximum")
