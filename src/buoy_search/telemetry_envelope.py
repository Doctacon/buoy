"""Canonical, content-free envelopes for Buoy's private telemetry writer.

The producer passes only the governed DuckDB-v1 row shape through this module.
The decoder treats the resulting bytes as untrusted and validates their exact
JSON representation, values, and trace graph before reconstructing those rows.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
import json
import math
import re
from typing import TYPE_CHECKING

from buoy_search.config import DEFAULT_EMBEDDING_MODEL

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import ReadableSpan


ENVELOPE_SCHEMA_VERSION = 1
OBSERVATION_SCHEMA_VERSION = 1
MAX_ENVELOPE_BYTES = 65_536
MAX_SPANS = 256
MAX_EVENTS = 1
MAX_SPAN_ATTRIBUTES = 64
MAX_EVENT_ATTRIBUTES = 3
MAX_COUNTER = 2_147_483_647
MAX_TIMESTAMP_UNIX_US = 253_402_300_799_999_999
MAX_FINITE_NUMBER = 1e308

ROOT_SPAN_NAME = "buoy.retrieve"
QUERY_EMBED_SPAN_NAME = "buoy.query.embed"
NAMESPACE_QUERY_SPAN_NAME = "buoy.namespace.query"
RERANK_SPAN_NAME = "buoy.rerank"
EVIDENCE_SPAN_NAME = "buoy.evidence.assess"
WIDENED_EVENT_NAME = "retrieval.widened"

ALLOWED_SPAN_NAMES = frozenset(
    {
        ROOT_SPAN_NAME,
        QUERY_EMBED_SPAN_NAME,
        NAMESPACE_QUERY_SPAN_NAME,
        RERANK_SPAN_NAME,
        EVIDENCE_SPAN_NAME,
    }
)
ALLOWED_EVENT_NAMES = frozenset({WIDENED_EVENT_NAME})

_INTEGER_ATTRIBUTE_KEYS = frozenset(
    {
        "buoy.observation.schema_version",
        "buoy.retrieval.top_k",
        "buoy.retrieval.candidates",
        "buoy.retrieval.hit_count",
        "buoy.retrieval.namespace_count",
        "buoy.retrieval.initial_fanout",
        "buoy.retrieval.final_fanout",
        "buoy.retrieval.failure_count",
        "buoy.route.rank",
        "buoy.namespace.hit_count",
        "buoy.rerank.candidates_before_dedupe",
        "buoy.rerank.candidates_after_dedupe",
        "buoy.evidence.candidates_scored",
    }
)
_FLOAT_ATTRIBUTE_KEYS = frozenset(
    {
        "buoy.routing.semantic_score",
        "buoy.routing.semantic_margin",
        "buoy.evidence.top_score",
        "buoy.evidence.second_score",
        "buoy.evidence.score_gap",
    }
)
_BOOLEAN_ATTRIBUTE_KEYS = frozenset(
    {
        "buoy.retrieval.incomplete",
        "buoy.retrieval.widened",
        "buoy.rerank.applied",
    }
)
_STRING_ATTRIBUTE_VALUES: dict[str, frozenset[str]] = {
    "buoy.retrieval.mode": frozenset(
        {"explicit_single", "explicit_multi", "automatic"}
    ),
    "buoy.retrieval.outcome": frozenset({"success", "partial", "error"}),
    "buoy.retrieval.fallback_reason": frozenset(
        {"empty_top1", "failed_top1", "weak_top1"}
    ),
    "buoy.embedding.model": frozenset({DEFAULT_EMBEDDING_MODEL, "custom"}),
    "buoy.embedding.precision": frozenset({"float16", "float32", "custom"}),
    "buoy.namespace.status": frozenset({"ok", "failed"}),
    "buoy.reranker.model": frozenset(
        {"cross-encoder/ms-marco-MiniLM-L-6-v2"}
    ),
    "buoy.routing.selection_reason": frozenset(
        {
            "unique_title_or_alias",
            "multiple_named_corpora",
            "high_confidence_semantic",
            "ambiguous_semantic",
            "high_confidence_prototype",
            "ambiguous_prototype",
        }
    ),
    "buoy.evidence.mode": frozenset({"collect", "shadow", "active"}),
    "buoy.evidence.status": frozenset(
        {
            "unassessed",
            "assessment_failed",
            "would_support",
            "would_abstain",
            "would_be_inconclusive",
            "supported",
            "no_relevant_evidence",
            "inconclusive",
        }
    ),
    "buoy.error.type": frozenset(
        {
            "provider_call_error",
            "reranker_error",
            "runtime_error",
            "value_error",
            "unexpected_error",
        }
    ),
}
_VERSION_ATTRIBUTE_KEY = "buoy.version"
_REVISION_ATTRIBUTE_KEY = "buoy.reranker.revision"
ALLOWED_ATTRIBUTE_KEYS = frozenset(
    {
        *_INTEGER_ATTRIBUTE_KEYS,
        *_FLOAT_ATTRIBUTE_KEYS,
        *_BOOLEAN_ATTRIBUTE_KEYS,
        *_STRING_ATTRIBUTE_VALUES,
        _VERSION_ATTRIBUTE_KEY,
        _REVISION_ATTRIBUTE_KEY,
    }
)
EVENT_ATTRIBUTE_KEYS = frozenset(
    {
        "buoy.retrieval.initial_fanout",
        "buoy.retrieval.final_fanout",
        "buoy.retrieval.fallback_reason",
    }
)
_EVENT_ATTRIBUTE_KEYS = EVENT_ATTRIBUTE_KEYS

ROOT_ATTRIBUTE_KEYS = frozenset(
    {
        "buoy.observation.schema_version",
        "buoy.version",
        "buoy.retrieval.mode",
        "buoy.retrieval.outcome",
        "buoy.retrieval.top_k",
        "buoy.retrieval.candidates",
        "buoy.retrieval.hit_count",
        "buoy.retrieval.namespace_count",
        "buoy.retrieval.initial_fanout",
        "buoy.retrieval.final_fanout",
        "buoy.retrieval.failure_count",
        "buoy.retrieval.incomplete",
        "buoy.retrieval.widened",
        "buoy.retrieval.fallback_reason",
        "buoy.embedding.model",
        "buoy.embedding.precision",
        "buoy.routing.selection_reason",
        "buoy.routing.semantic_score",
        "buoy.routing.semantic_margin",
        "buoy.evidence.mode",
        "buoy.evidence.status",
        "buoy.evidence.candidates_scored",
        "buoy.evidence.top_score",
        "buoy.evidence.second_score",
        "buoy.evidence.score_gap",
        "buoy.error.type",
    }
)
SPAN_ATTRIBUTE_KEYS: dict[str, frozenset[str]] = {
    ROOT_SPAN_NAME: ROOT_ATTRIBUTE_KEYS,
    QUERY_EMBED_SPAN_NAME: frozenset({"buoy.error.type"}),
    NAMESPACE_QUERY_SPAN_NAME: frozenset(
        {
            "buoy.route.rank",
            "buoy.namespace.status",
            "buoy.namespace.hit_count",
            "buoy.error.type",
        }
    ),
    RERANK_SPAN_NAME: frozenset(
        {
            "buoy.rerank.applied",
            "buoy.rerank.candidates_before_dedupe",
            "buoy.rerank.candidates_after_dedupe",
            "buoy.reranker.model",
            "buoy.reranker.revision",
            "buoy.error.type",
        }
    ),
    EVIDENCE_SPAN_NAME: frozenset(
        {
            "buoy.evidence.mode",
            "buoy.evidence.status",
            "buoy.evidence.candidates_scored",
            "buoy.evidence.top_score",
            "buoy.evidence.second_score",
            "buoy.evidence.score_gap",
            "buoy.error.type",
        }
    ),
}

_VERSION_RE = re.compile(r"^[0-9A-Za-z][0-9A-Za-z.+-]{0,95}$")
_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
_TRACE_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_SPAN_ID_RE = re.compile(r"^[0-9a-f]{16}$")

_ENVELOPE_KEYS = frozenset(
    {
        "envelope_schema_version",
        "observation_schema_version",
        "run",
        "spans",
        "events",
    }
)
_RUN_KEYS = (
    "trace_id",
    "root_span_id",
    "started_at_unix_us",
    "ended_at_unix_us",
    "duration_ms",
    "retrieval_mode",
    "outcome",
    "hit_count",
    "namespace_count",
    "initial_fanout",
    "final_fanout",
    "failure_count",
    "incomplete",
    "widened",
    "fallback_reason",
    "evidence_status",
    "embedding_model",
    "embedding_precision",
    "top_k",
    "candidates",
    "buoy_version",
    "observation_schema_version",
)
_RUN_KEY_SET = frozenset(_RUN_KEYS)
_SPAN_KEYS = (
    "trace_id",
    "span_id",
    "parent_span_id",
    "name",
    "started_at_unix_us",
    "ended_at_unix_us",
    "duration_ms",
    "status_code",
    "attributes",
)
_SPAN_KEY_SET = frozenset(_SPAN_KEYS)
_EVENT_KEYS = (
    "trace_id",
    "span_id",
    "event_index",
    "name",
    "occurred_at_unix_us",
    "attributes",
)
_EVENT_KEY_SET = frozenset(_EVENT_KEYS)

_RUN_ATTRIBUTE_FIELDS = (
    ("retrieval_mode", "buoy.retrieval.mode", False),
    ("outcome", "buoy.retrieval.outcome", False),
    ("hit_count", "buoy.retrieval.hit_count", False),
    ("namespace_count", "buoy.retrieval.namespace_count", False),
    ("initial_fanout", "buoy.retrieval.initial_fanout", False),
    ("final_fanout", "buoy.retrieval.final_fanout", False),
    ("failure_count", "buoy.retrieval.failure_count", False),
    ("incomplete", "buoy.retrieval.incomplete", False),
    ("widened", "buoy.retrieval.widened", False),
    ("fallback_reason", "buoy.retrieval.fallback_reason", True),
    ("evidence_status", "buoy.evidence.status", True),
    ("embedding_model", "buoy.embedding.model", False),
    ("embedding_precision", "buoy.embedding.precision", False),
    ("top_k", "buoy.retrieval.top_k", False),
    ("candidates", "buoy.retrieval.candidates", False),
    ("buoy_version", "buoy.version", False),
    (
        "observation_schema_version",
        "buoy.observation.schema_version",
        False,
    ),
)

ENVELOPE_REASONS = frozenset(
    {
        "invalid_utf8",
        "invalid_json",
        "noncanonical_json",
        "unsupported_envelope_version",
        "invalid_shape",
        "invalid_value",
        "invalid_graph",
        "oversized",
    }
)


class TraceEnvelopeError(ValueError):
    """A content-free envelope rejection with a governed receipt reason."""

    def __init__(self, reason: str) -> None:
        if reason not in ENVELOPE_REASONS:
            reason = "invalid_value"
        self.reason = reason
        super().__init__(reason)


EnvelopeValidationError = TraceEnvelopeError


@dataclass(frozen=True)
class TraceRows:
    """The unchanged DuckDB-v1 run, span, and event tuple shape."""

    run: tuple[object, ...]
    spans: tuple[tuple[object, ...], ...]
    events: tuple[tuple[object, ...], ...]


_TraceRows = TraceRows


def sanitize_attribute(
    key: object,
    value: object,
) -> str | bool | int | float | None:
    """Return one governed scalar attribute, or ``None`` when prohibited."""

    if type(key) is not str or key not in ALLOWED_ATTRIBUTE_KEYS or value is None:
        return None
    if key in _INTEGER_ATTRIBUTE_KEYS:
        if type(value) is not int or not 0 <= value <= MAX_COUNTER:
            return None
        if key == "buoy.observation.schema_version" and value != 1:
            return None
        if key == "buoy.route.rank" and value == 0:
            return None
        return value
    if key in _FLOAT_ATTRIBUTE_KEYS:
        if type(value) not in {int, float}:
            return None
        try:
            normalized = float(value)
        except (OverflowError, TypeError, ValueError):
            return None
        if not math.isfinite(normalized) or abs(normalized) > MAX_FINITE_NUMBER:
            return None
        return normalized
    if key in _BOOLEAN_ATTRIBUTE_KEYS:
        return value if type(value) is bool else None
    if type(value) is not str:
        return None
    if key == _VERSION_ATTRIBUTE_KEY:
        return value if _VERSION_RE.fullmatch(value) else None
    if key == _REVISION_ATTRIBUTE_KEY:
        return value if _REVISION_RE.fullmatch(value) else None
    allowed_values = _STRING_ATTRIBUTE_VALUES.get(key)
    return value if allowed_values is not None and value in allowed_values else None


_sanitize_attribute = sanitize_attribute


def sanitize_attributes(
    attributes: Mapping[object, object],
) -> dict[str, str | bool | int | float]:
    """Drop all non-governed keys and values from an attribute mapping."""

    sanitized: dict[str, str | bool | int | float] = {}
    for key, value in attributes.items():
        normalized = sanitize_attribute(key, value)
        if normalized is not None:
            assert isinstance(key, str)
            sanitized[key] = normalized
    return sanitized


_sanitize_attributes = sanitize_attributes


def trace_rows_from_spans(
    spans: Sequence[ReadableSpan],
    *,
    root_span_id: int,
) -> TraceRows:
    """Construct sanitized DuckDB-v1 rows from one private completed trace."""

    allowed = [span for span in spans if span.name in ALLOWED_SPAN_NAMES]
    root = next(
        (
            span
            for span in allowed
            if span.name == ROOT_SPAN_NAME
            and span.context is not None
            and span.context.span_id == root_span_id
        ),
        None,
    )
    if root is None or root.context is None or root.end_time is None:
        raise TraceEnvelopeError("invalid_graph")

    trace_id = f"{root.context.trace_id:032x}"
    root_attributes = _attributes_for_span(
        ROOT_SPAN_NAME,
        root.attributes or {},
    )
    start = _timestamp_from_ns(root.start_time)
    end = _timestamp_from_ns(root.end_time)
    duration_ms = _duration_ms_from_ns(root.start_time, root.end_time)
    run = (
        trace_id,
        f"{root.context.span_id:016x}",
        start,
        end,
        duration_ms,
        root_attributes.get("buoy.retrieval.mode"),
        root_attributes.get("buoy.retrieval.outcome"),
        root_attributes.get("buoy.retrieval.hit_count", 0),
        root_attributes.get("buoy.retrieval.namespace_count", 0),
        root_attributes.get("buoy.retrieval.initial_fanout", 0),
        root_attributes.get("buoy.retrieval.final_fanout", 0),
        root_attributes.get("buoy.retrieval.failure_count", 0),
        root_attributes.get("buoy.retrieval.incomplete", False),
        root_attributes.get("buoy.retrieval.widened", False),
        root_attributes.get("buoy.retrieval.fallback_reason"),
        root_attributes.get("buoy.evidence.status"),
        root_attributes.get("buoy.embedding.model"),
        root_attributes.get("buoy.embedding.precision"),
        root_attributes.get("buoy.retrieval.top_k", 0),
        root_attributes.get("buoy.retrieval.candidates", 0),
        root_attributes.get("buoy.version"),
        root_attributes.get(
            "buoy.observation.schema_version",
            OBSERVATION_SCHEMA_VERSION,
        ),
    )

    span_rows: list[tuple[object, ...]] = []
    event_rows: list[tuple[object, ...]] = []
    for readable in allowed:
        if (
            readable.context is None
            or readable.context.trace_id != root.context.trace_id
            or readable.end_time is None
        ):
            continue
        span_id = f"{readable.context.span_id:016x}"
        parent_id = (
            f"{readable.parent.span_id:016x}"
            if readable.parent is not None and readable.parent.span_id
            else None
        )
        attributes = _attributes_for_span(
            readable.name,
            readable.attributes or {},
        )
        span_rows.append(
            (
                trace_id,
                span_id,
                parent_id,
                readable.name,
                _timestamp_from_ns(readable.start_time),
                _timestamp_from_ns(readable.end_time),
                _duration_ms_from_ns(readable.start_time, readable.end_time),
                readable.status.status_code.name,
                _canonical_json_text(attributes),
            )
        )
        if readable.context.span_id != root_span_id:
            continue
        allowed_events = [
            event
            for event in readable.events or ()
            if event.name == WIDENED_EVENT_NAME and event.timestamp is not None
        ]
        for event_index, event in enumerate(allowed_events):
            event_attributes = {
                key: value
                for key, value in sanitize_attributes(
                    event.attributes or {}
                ).items()
                if key in EVENT_ATTRIBUTE_KEYS
            }
            event_rows.append(
                (
                    trace_id,
                    span_id,
                    event_index,
                    event.name,
                    _timestamp_from_ns(event.timestamp),
                    _canonical_json_text(event_attributes),
                )
            )

    span_rows.sort(key=lambda row: (row[4], row[1]))
    event_rows.sort(key=lambda row: row[2])
    rows = TraceRows(
        run=run,
        spans=tuple(span_rows),
        events=tuple(event_rows),
    )
    _validate_envelope_object(_envelope_object_from_rows(rows))
    return rows


def encode_trace_envelope_v1(rows: TraceRows) -> bytes:
    """Validate and encode rows as exact canonical ``trace-envelope/v1`` bytes."""

    try:
        envelope = _envelope_object_from_rows(rows)
        _validate_envelope_object(envelope)
        payload = _canonical_json_bytes(envelope)
    except TraceEnvelopeError:
        raise
    except (OverflowError, TypeError, ValueError):
        raise TraceEnvelopeError("invalid_value") from None
    if len(payload) > MAX_ENVELOPE_BYTES:
        raise TraceEnvelopeError("oversized")
    return payload


def decode_trace_envelope_v1(payload: bytes) -> TraceRows:
    """Strictly parse and independently validate untrusted envelope bytes."""

    envelope = _load_canonical_envelope(payload)
    _validate_envelope_object(envelope)
    return _rows_from_envelope_object(envelope)


def _attributes_for_span(
    name: str,
    attributes: Mapping[object, object],
) -> dict[str, str | bool | int | float]:
    allowed_keys = SPAN_ATTRIBUTE_KEYS[name]
    return {
        key: value
        for key, value in sanitize_attributes(attributes).items()
        if key in allowed_keys
    }


def _timestamp_from_ns(value: int | None) -> datetime:
    if type(value) is not int or value < 0:
        raise TraceEnvelopeError("invalid_value")
    unix_us = value // 1_000
    if unix_us > MAX_TIMESTAMP_UNIX_US:
        raise TraceEnvelopeError("invalid_value")
    return _datetime_from_unix_us(unix_us)


def _duration_ms_from_ns(start: int | None, end: int | None) -> float:
    if type(start) is not int or type(end) is not int or end < start:
        raise TraceEnvelopeError("invalid_value")
    try:
        duration = (end - start) / 1_000_000.0
    except OverflowError:
        raise TraceEnvelopeError("invalid_value") from None
    if (
        not math.isfinite(duration)
        or duration < 0
        or abs(duration) > MAX_FINITE_NUMBER
    ):
        raise TraceEnvelopeError("invalid_value")
    return duration


def _canonical_json_text(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _canonical_json_bytes(value: object) -> bytes:
    return _canonical_json_text(value).encode("utf-8")


class _DuplicateObjectKeyError(ValueError):
    pass


class _NonfiniteJSONConstantError(ValueError):
    pass


class _JSONNumberOutOfBoundsError(ValueError):
    pass


def _object_without_duplicates(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    observed: dict[str, object] = {}
    for key, value in pairs:
        if key in observed:
            raise _DuplicateObjectKeyError
        observed[key] = value
    return observed


def _reject_json_constant(_value: str) -> object:
    raise _NonfiniteJSONConstantError


def _parse_json_integer(value: str) -> int:
    # No valid envelope number needs more than the 309 decimal digits of 1e308.
    # Checking first also avoids depending on the interpreter's integer-string
    # conversion limit for the receipt classification of a hostile payload.
    if len(value.removeprefix("-")) > 309:
        raise _JSONNumberOutOfBoundsError
    return int(value)


def _parse_json_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed) or abs(parsed) > MAX_FINITE_NUMBER:
        raise _JSONNumberOutOfBoundsError
    return parsed


def _load_canonical_envelope(payload: bytes) -> dict[str, object]:
    if type(payload) is not bytes:
        raise TraceEnvelopeError("invalid_shape")
    if len(payload) > MAX_ENVELOPE_BYTES:
        raise TraceEnvelopeError("oversized")
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        raise TraceEnvelopeError("invalid_utf8") from None
    try:
        parsed = json.loads(
            text,
            object_pairs_hook=_object_without_duplicates,
            parse_constant=_reject_json_constant,
            parse_int=_parse_json_integer,
            parse_float=_parse_json_float,
        )
    except (_NonfiniteJSONConstantError, _JSONNumberOutOfBoundsError):
        raise TraceEnvelopeError("invalid_value") from None
    except (_DuplicateObjectKeyError, json.JSONDecodeError, RecursionError, ValueError):
        raise TraceEnvelopeError("invalid_json") from None
    try:
        canonical = _canonical_json_bytes(parsed)
    except (OverflowError, TypeError, ValueError):
        raise TraceEnvelopeError("invalid_value") from None
    if canonical != payload:
        raise TraceEnvelopeError("noncanonical_json")
    if type(parsed) is not dict:
        raise TraceEnvelopeError("invalid_shape")
    return parsed


def _load_attribute_object(value: object) -> dict[str, object]:
    if type(value) is not str:
        raise TraceEnvelopeError("invalid_shape")
    try:
        parsed = json.loads(
            value,
            object_pairs_hook=_object_without_duplicates,
            parse_constant=_reject_json_constant,
            parse_int=_parse_json_integer,
            parse_float=_parse_json_float,
        )
    except (
        _DuplicateObjectKeyError,
        _NonfiniteJSONConstantError,
        _JSONNumberOutOfBoundsError,
        json.JSONDecodeError,
        RecursionError,
        ValueError,
    ):
        raise TraceEnvelopeError("invalid_value") from None
    if type(parsed) is not dict:
        raise TraceEnvelopeError("invalid_shape")
    try:
        canonical = _canonical_json_text(parsed)
    except (OverflowError, TypeError, ValueError):
        raise TraceEnvelopeError("invalid_value") from None
    if canonical != value:
        raise TraceEnvelopeError("invalid_value")
    return parsed


def _envelope_object_from_rows(rows: TraceRows) -> dict[str, object]:
    if not isinstance(rows, TraceRows):
        raise TraceEnvelopeError("invalid_shape")
    if type(rows.run) is not tuple or len(rows.run) != len(_RUN_KEYS):
        raise TraceEnvelopeError("invalid_shape")
    if type(rows.spans) is not tuple or type(rows.events) is not tuple:
        raise TraceEnvelopeError("invalid_shape")

    run = dict(zip(_RUN_KEYS, rows.run, strict=True))
    run["started_at_unix_us"] = _unix_us_from_datetime(
        run["started_at_unix_us"]
    )
    run["ended_at_unix_us"] = _unix_us_from_datetime(run["ended_at_unix_us"])

    spans: list[dict[str, object]] = []
    for row in rows.spans:
        if type(row) is not tuple or len(row) != len(_SPAN_KEYS):
            raise TraceEnvelopeError("invalid_shape")
        span = dict(zip(_SPAN_KEYS, row, strict=True))
        span["started_at_unix_us"] = _unix_us_from_datetime(
            span["started_at_unix_us"]
        )
        span["ended_at_unix_us"] = _unix_us_from_datetime(
            span["ended_at_unix_us"]
        )
        span["attributes"] = _load_attribute_object(span["attributes"])
        spans.append(span)

    events: list[dict[str, object]] = []
    for row in rows.events:
        if type(row) is not tuple or len(row) != len(_EVENT_KEYS):
            raise TraceEnvelopeError("invalid_shape")
        event = dict(zip(_EVENT_KEYS, row, strict=True))
        event["occurred_at_unix_us"] = _unix_us_from_datetime(
            event["occurred_at_unix_us"]
        )
        event["attributes"] = _load_attribute_object(event["attributes"])
        events.append(event)

    return {
        "envelope_schema_version": ENVELOPE_SCHEMA_VERSION,
        "observation_schema_version": run["observation_schema_version"],
        "run": run,
        "spans": spans,
        "events": events,
    }


def _rows_from_envelope_object(envelope: dict[str, object]) -> TraceRows:
    run_object = envelope["run"]
    span_objects = envelope["spans"]
    event_objects = envelope["events"]
    assert isinstance(run_object, dict)
    assert isinstance(span_objects, list)
    assert isinstance(event_objects, list)

    run_values = dict(run_object)
    run_values["started_at_unix_us"] = _datetime_from_unix_us(
        run_values["started_at_unix_us"]
    )
    run_values["ended_at_unix_us"] = _datetime_from_unix_us(
        run_values["ended_at_unix_us"]
    )
    run_values["duration_ms"] = float(run_values["duration_ms"])
    run = tuple(run_values[key] for key in _RUN_KEYS)

    span_rows: list[tuple[object, ...]] = []
    for span_object in span_objects:
        assert isinstance(span_object, dict)
        values = dict(span_object)
        values["started_at_unix_us"] = _datetime_from_unix_us(
            values["started_at_unix_us"]
        )
        values["ended_at_unix_us"] = _datetime_from_unix_us(
            values["ended_at_unix_us"]
        )
        values["duration_ms"] = float(values["duration_ms"])
        values["attributes"] = _canonical_json_text(values["attributes"])
        span_rows.append(tuple(values[key] for key in _SPAN_KEYS))

    event_rows: list[tuple[object, ...]] = []
    for event_object in event_objects:
        assert isinstance(event_object, dict)
        values = dict(event_object)
        values["occurred_at_unix_us"] = _datetime_from_unix_us(
            values["occurred_at_unix_us"]
        )
        values["attributes"] = _canonical_json_text(values["attributes"])
        event_rows.append(tuple(values[key] for key in _EVENT_KEYS))
    return TraceRows(run=run, spans=tuple(span_rows), events=tuple(event_rows))


def _unix_us_from_datetime(value: object) -> int:
    if type(value) is not datetime or value.tzinfo is not None:
        raise TraceEnvelopeError("invalid_value")
    epoch = datetime(1970, 1, 1)
    if value < epoch:
        raise TraceEnvelopeError("invalid_value")
    delta = value - epoch
    unix_us = (
        delta.days * 86_400_000_000
        + delta.seconds * 1_000_000
        + delta.microseconds
    )
    if unix_us > MAX_TIMESTAMP_UNIX_US:
        raise TraceEnvelopeError("invalid_value")
    return unix_us


def _datetime_from_unix_us(value: object) -> datetime:
    if type(value) is not int or not 0 <= value <= MAX_TIMESTAMP_UNIX_US:
        raise TraceEnvelopeError("invalid_value")
    try:
        return datetime(1970, 1, 1) + timedelta(microseconds=value)
    except OverflowError:
        raise TraceEnvelopeError("invalid_value") from None


def _validate_envelope_object(envelope: object) -> None:
    if type(envelope) is not dict:
        raise TraceEnvelopeError("invalid_shape")
    _require_exact_keys(envelope, _ENVELOPE_KEYS)
    version = envelope["envelope_schema_version"]
    if type(version) is not int:
        raise TraceEnvelopeError("invalid_value")
    if version != ENVELOPE_SCHEMA_VERSION:
        raise TraceEnvelopeError("unsupported_envelope_version")
    _require_exact_integer(envelope["observation_schema_version"], 1)

    run = envelope["run"]
    spans = envelope["spans"]
    events = envelope["events"]
    if type(run) is not dict or type(spans) is not list or type(events) is not list:
        raise TraceEnvelopeError("invalid_shape")
    if not 1 <= len(spans) <= MAX_SPANS or len(events) > MAX_EVENTS:
        raise TraceEnvelopeError("invalid_shape")

    _validate_run(run)
    for span in spans:
        _validate_span(span)
    for event in events:
        _validate_event(event)
    _validate_graph(run, spans, events)


def _validate_run(run: dict[str, object]) -> None:
    _require_exact_keys(run, _RUN_KEY_SET)
    _require_trace_id(run["trace_id"])
    _require_span_id(run["root_span_id"])
    start = _require_timestamp(run["started_at_unix_us"])
    end = _require_timestamp(run["ended_at_unix_us"])
    if end < start:
        raise TraceEnvelopeError("invalid_value")
    _require_number(run["duration_ms"], nonnegative=True)
    _require_enum(
        run["retrieval_mode"],
        {"explicit_single", "explicit_multi", "automatic"},
    )
    _require_enum(run["outcome"], {"success", "partial", "error"})
    for key in (
        "hit_count",
        "namespace_count",
        "initial_fanout",
        "final_fanout",
        "failure_count",
        "top_k",
        "candidates",
    ):
        _require_counter(run[key])
    for key in ("incomplete", "widened"):
        if type(run[key]) is not bool:
            raise TraceEnvelopeError("invalid_value")
    _require_nullable_enum(
        run["fallback_reason"],
        {"empty_top1", "failed_top1", "weak_top1"},
    )
    _require_nullable_enum(
        run["evidence_status"],
        {
            "unassessed",
            "assessment_failed",
            "would_support",
            "would_abstain",
            "would_be_inconclusive",
            "supported",
            "no_relevant_evidence",
            "inconclusive",
        },
    )
    _require_enum(run["embedding_model"], {DEFAULT_EMBEDDING_MODEL, "custom"})
    _require_enum(
        run["embedding_precision"],
        {"float16", "float32", "custom"},
    )
    if type(run["buoy_version"]) is not str or not _VERSION_RE.fullmatch(
        run["buoy_version"]
    ):
        raise TraceEnvelopeError("invalid_value")
    _require_exact_integer(run["observation_schema_version"], 1)


def _validate_span(span: object) -> None:
    if type(span) is not dict:
        raise TraceEnvelopeError("invalid_shape")
    _require_exact_keys(span, _SPAN_KEY_SET)
    _require_trace_id(span["trace_id"])
    _require_span_id(span["span_id"])
    parent = span["parent_span_id"]
    if parent is not None:
        _require_span_id(parent)
    name = span["name"]
    if type(name) is not str or name not in ALLOWED_SPAN_NAMES:
        raise TraceEnvelopeError("invalid_value")
    start = _require_timestamp(span["started_at_unix_us"])
    end = _require_timestamp(span["ended_at_unix_us"])
    if end < start:
        raise TraceEnvelopeError("invalid_value")
    _require_number(span["duration_ms"], nonnegative=True)
    _require_enum(span["status_code"], {"UNSET", "OK", "ERROR"})
    _validate_attributes(
        span["attributes"],
        allowed_keys=SPAN_ATTRIBUTE_KEYS[name],
        maximum=MAX_SPAN_ATTRIBUTES,
        exact_keys=None,
    )


def _validate_event(event: object) -> None:
    if type(event) is not dict:
        raise TraceEnvelopeError("invalid_shape")
    _require_exact_keys(event, _EVENT_KEY_SET)
    _require_trace_id(event["trace_id"])
    _require_span_id(event["span_id"])
    _require_exact_integer(event["event_index"], 0)
    _require_enum(event["name"], {WIDENED_EVENT_NAME})
    _require_timestamp(event["occurred_at_unix_us"])
    _validate_attributes(
        event["attributes"],
        allowed_keys=EVENT_ATTRIBUTE_KEYS,
        maximum=MAX_EVENT_ATTRIBUTES,
        exact_keys=EVENT_ATTRIBUTE_KEYS,
    )


def _validate_attributes(
    attributes: object,
    *,
    allowed_keys: frozenset[str],
    maximum: int,
    exact_keys: frozenset[str] | None,
) -> None:
    if type(attributes) is not dict or len(attributes) > maximum:
        raise TraceEnvelopeError("invalid_shape")
    observed_keys = frozenset(attributes)
    if not observed_keys <= allowed_keys:
        raise TraceEnvelopeError("invalid_shape")
    if exact_keys is not None and observed_keys != exact_keys:
        raise TraceEnvelopeError("invalid_shape")
    for key, value in attributes.items():
        if type(key) is not str:
            raise TraceEnvelopeError("invalid_shape")
        normalized = sanitize_attribute(key, value)
        if normalized is None or normalized != value:
            raise TraceEnvelopeError("invalid_value")


def _validate_graph(
    run: dict[str, object],
    spans: list[object],
    events: list[object],
) -> None:
    typed_spans = [span for span in spans if isinstance(span, dict)]
    typed_events = [event for event in events if isinstance(event, dict)]
    roots = [span for span in typed_spans if span["name"] == ROOT_SPAN_NAME]
    if len(roots) != 1:
        raise TraceEnvelopeError("invalid_graph")
    root = roots[0]
    trace_id = run["trace_id"]
    root_span_id = run["root_span_id"]
    if (
        root["trace_id"] != trace_id
        or root["span_id"] != root_span_id
        or root["parent_span_id"] is not None
    ):
        raise TraceEnvelopeError("invalid_graph")

    seen_span_ids: set[object] = set()
    for span in typed_spans:
        span_id = span["span_id"]
        if span["trace_id"] != trace_id or span_id in seen_span_ids:
            raise TraceEnvelopeError("invalid_graph")
        seen_span_ids.add(span_id)
        if span is not root and span["parent_span_id"] != root_span_id:
            raise TraceEnvelopeError("invalid_graph")
    ordered_spans = sorted(
        typed_spans,
        key=lambda span: (span["started_at_unix_us"], span["span_id"]),
    )
    if typed_spans != ordered_spans:
        raise TraceEnvelopeError("invalid_graph")
    if typed_events != sorted(typed_events, key=lambda event: event["event_index"]):
        raise TraceEnvelopeError("invalid_graph")

    root_start = root["started_at_unix_us"]
    root_end = root["ended_at_unix_us"]
    for span in typed_spans:
        if not (
            root_start <= span["started_at_unix_us"]
            and span["ended_at_unix_us"] <= root_end
        ):
            raise TraceEnvelopeError("invalid_graph")
        _require_duration_agreement(
            span["duration_ms"],
            span["started_at_unix_us"],
            span["ended_at_unix_us"],
        )
    for event in typed_events:
        if (
            event["trace_id"] != trace_id
            or event["span_id"] != root_span_id
            or not root_start <= event["occurred_at_unix_us"] <= root_end
        ):
            raise TraceEnvelopeError("invalid_graph")

    if (
        run["started_at_unix_us"] != root_start
        or run["ended_at_unix_us"] != root_end
        or run["duration_ms"] != root["duration_ms"]
    ):
        raise TraceEnvelopeError("invalid_graph")
    _require_duration_agreement(
        run["duration_ms"],
        run["started_at_unix_us"],
        run["ended_at_unix_us"],
    )

    root_attributes = root["attributes"]
    assert isinstance(root_attributes, dict)
    for run_key, attribute_key, optional in _RUN_ATTRIBUTE_FIELDS:
        run_value = run[run_key]
        if optional and run_value is None:
            if attribute_key in root_attributes:
                raise TraceEnvelopeError("invalid_graph")
        elif root_attributes.get(attribute_key) != run_value:
            raise TraceEnvelopeError("invalid_graph")

    widened = run["widened"]
    if widened:
        if len(typed_events) != 1 or run["fallback_reason"] is None:
            raise TraceEnvelopeError("invalid_graph")
        event_attributes = typed_events[0]["attributes"]
        assert isinstance(event_attributes, dict)
        if event_attributes != {
            "buoy.retrieval.initial_fanout": run["initial_fanout"],
            "buoy.retrieval.final_fanout": run["final_fanout"],
            "buoy.retrieval.fallback_reason": run["fallback_reason"],
        }:
            raise TraceEnvelopeError("invalid_graph")
    elif typed_events:
        raise TraceEnvelopeError("invalid_graph")

    if run["incomplete"] is not (run["failure_count"] != 0):
        raise TraceEnvelopeError("invalid_graph")
    if (
        run["final_fanout"] > run["namespace_count"]
        or run["failure_count"] > run["final_fanout"]
    ):
        raise TraceEnvelopeError("invalid_graph")


def _require_exact_keys(
    value: dict[object, object],
    expected: frozenset[str],
) -> None:
    if frozenset(value) != expected:
        raise TraceEnvelopeError("invalid_shape")


def _require_trace_id(value: object) -> None:
    if (
        type(value) is not str
        or not _TRACE_ID_RE.fullmatch(value)
        or value == "0" * 32
    ):
        raise TraceEnvelopeError("invalid_value")


def _require_span_id(value: object) -> None:
    if (
        type(value) is not str
        or not _SPAN_ID_RE.fullmatch(value)
        or value == "0" * 16
    ):
        raise TraceEnvelopeError("invalid_value")


def _require_timestamp(value: object) -> int:
    if type(value) is not int or not 0 <= value <= MAX_TIMESTAMP_UNIX_US:
        raise TraceEnvelopeError("invalid_value")
    return value


def _require_counter(value: object) -> None:
    if type(value) is not int or not 0 <= value <= MAX_COUNTER:
        raise TraceEnvelopeError("invalid_value")


def _require_number(value: object, *, nonnegative: bool) -> None:
    if type(value) not in {int, float}:
        raise TraceEnvelopeError("invalid_value")
    try:
        finite = math.isfinite(value)
    except (OverflowError, TypeError, ValueError):
        raise TraceEnvelopeError("invalid_value") from None
    if (
        not finite
        or abs(value) > MAX_FINITE_NUMBER
        or (nonnegative and value < 0)
    ):
        raise TraceEnvelopeError("invalid_value")


def _require_duration_agreement(
    duration_ms: object,
    start_unix_us: object,
    end_unix_us: object,
) -> None:
    assert type(duration_ms) in {int, float}
    assert type(start_unix_us) is int
    assert type(end_unix_us) is int
    observed = Decimal(str(duration_ms))
    expected = Decimal(end_unix_us - start_unix_us) / Decimal(1_000)
    if abs(observed - expected) > Decimal("0.001"):
        raise TraceEnvelopeError("invalid_graph")


def _require_enum(value: object, choices: set[str]) -> None:
    if type(value) is not str or value not in choices:
        raise TraceEnvelopeError("invalid_value")


def _require_nullable_enum(value: object, choices: set[str]) -> None:
    if value is not None:
        _require_enum(value, choices)


def _require_exact_integer(value: object, expected: int) -> None:
    if type(value) is not int or value != expected:
        raise TraceEnvelopeError("invalid_value")
