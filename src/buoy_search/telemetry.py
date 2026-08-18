"""Opt-in, content-free OpenTelemetry traces for local Buoy retrievals.

The module deliberately owns a private tracer provider instead of changing the
process-global OpenTelemetry provider. One short-lived retrieval trace is
buffered in memory and appended to a dedicated DuckDB in one transaction.
Every telemetry failure is best-effort and isolated from retrieval behavior.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import tempfile
import threading
import time
from typing import TYPE_CHECKING, ParamSpec, TypeVar

import duckdb
from opentelemetry.context import Context
from opentelemetry import trace
from opentelemetry.trace import Span, Status, StatusCode
import portalocker

from buoy_search import __version__
from buoy_search.config import DEFAULT_EMBEDDING_MODEL
from buoy_search.local_paths import default_buoy_home, prepare_default_buoy_home

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import ReadableSpan, TracerProvider


TELEMETRY_ENV = "BUOY_TELEMETRY"
LOCAL_TELEMETRY_VALUE = "local"
OTEL_SDK_DISABLED_ENV = "OTEL_SDK_DISABLED"
TELEMETRY_SCHEMA_VERSION = 1
OBSERVATION_SCHEMA_VERSION = 1
_SAFE_DUCKDB_CONFIG = {
    "enable_external_access": "false",
    "autoinstall_known_extensions": "false",
    "autoload_known_extensions": "false",
    "allow_community_extensions": "false",
}

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
_EVENT_ATTRIBUTE_KEYS = frozenset(
    {
        "buoy.retrieval.initial_fanout",
        "buoy.retrieval.final_fanout",
        "buoy.retrieval.fallback_reason",
    }
)
_VERSION_RE = re.compile(r"^[0-9A-Za-z][0-9A-Za-z.+-]{0,95}$")
_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")

_P = ParamSpec("_P")
_R = TypeVar("_R")


@dataclass(frozen=True)
class TelemetryPaths:
    """Canonical local paths for the private telemetry store."""

    directory: Path
    database_path: Path
    lock_path: Path


@dataclass(frozen=True)
class _TraceRows:
    run: tuple[object, ...]
    spans: tuple[tuple[object, ...], ...]
    events: tuple[tuple[object, ...], ...]


class _BufferingSpanExporter:
    """Thread-safe one-retrieval buffer with no external side effects."""

    def __init__(self, success_result: object) -> None:
        self._lock = threading.Lock()
        self._spans: list[ReadableSpan] = []
        self._success_result = success_result

    def export(self, spans: Sequence[ReadableSpan]) -> object:
        with self._lock:
            self._spans.extend(spans)
        return self._success_result

    def shutdown(self) -> None:
        return None

    def snapshot(self) -> tuple[ReadableSpan, ...]:
        with self._lock:
            return tuple(self._spans)


@dataclass
class _TraceSession:
    provider: TracerProvider
    tracer: trace.Tracer
    exporter: _BufferingSpanExporter
    root_span_id: int | None = None


class TelemetrySpan:
    """Small safe facade over an OpenTelemetry span."""

    def __init__(self, span: Span | None = None) -> None:
        self._span = span

    @property
    def enabled(self) -> bool:
        return self._span is not None

    def set_attribute(self, key: str, value: object) -> None:
        if self._span is None:
            return
        sanitized = _sanitize_attribute(key, value)
        if sanitized is None:
            return
        try:
            self._span.set_attribute(key, sanitized)
        except Exception:
            return

    def set_attributes(self, attributes: Mapping[str, object]) -> None:
        for key, value in attributes.items():
            self.set_attribute(key, value)

    def add_event(
        self,
        name: str,
        attributes: Mapping[str, object] | None = None,
    ) -> None:
        if self._span is None or name not in ALLOWED_EVENT_NAMES:
            return
        safe_attributes = {
            key: value
            for key, value in _sanitize_attributes(attributes or {}).items()
            if key in _EVENT_ATTRIBUTE_KEYS
        }
        try:
            self._span.add_event(
                name,
                attributes=safe_attributes,
                timestamp=_time_ns(),
            )
        except Exception:
            return

    def mark_ok(self) -> None:
        if self._span is None:
            return
        try:
            self._span.set_status(Status(StatusCode.OK))
        except Exception:
            return

    def mark_error(self, exc: BaseException) -> None:
        if self._span is None:
            return
        self.set_attribute("buoy.error.type", _error_category(exc))
        try:
            self._span.set_status(Status(StatusCode.ERROR))
        except Exception:
            return


_NOOP_SPAN = TelemetrySpan()
_ACTIVE_SESSION: ContextVar[_TraceSession | None] = ContextVar(
    "buoy_active_telemetry_session",
    default=None,
)
_ACTIVE_SPAN: ContextVar[Span | None] = ContextVar(
    "buoy_active_telemetry_span",
    default=None,
)


def local_telemetry_enabled(
    environment: Mapping[str, str] | None = None,
) -> bool:
    """Return whether the exact local, opt-in trace sink is enabled."""

    source = os.environ if environment is None else environment
    if source.get(TELEMETRY_ENV, "").strip().lower() != LOCAL_TELEMETRY_VALUE:
        return False
    return source.get(OTEL_SDK_DISABLED_ENV, "").strip().lower() != "true"


def telemetry_paths() -> TelemetryPaths:
    """Return canonical telemetry paths without creating them."""

    directory = default_buoy_home() / "telemetry"
    return TelemetryPaths(
        directory=directory,
        database_path=directory / "telemetry.duckdb",
        lock_path=directory / "write.lock",
    )


def safe_embedding_model(value: object) -> str:
    """Return a useful model label without persisting custom paths or IDs."""

    return DEFAULT_EMBEDDING_MODEL if value == DEFAULT_EMBEDDING_MODEL else "custom"


def safe_embedding_precision(value: object) -> str:
    """Return a bounded precision label."""

    return str(value) if value in {"float16", "float32"} else "custom"


def copied_context_callable(
    callback: Callable[_P, _R],
) -> Callable[_P, _R]:
    """Bind only Buoy's private trace state to a worker callable."""

    session = _ACTIVE_SESSION.get()
    parent_span = _ACTIVE_SPAN.get()
    if session is None or parent_span is None:
        return callback

    def run(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        session_token = None
        span_token = None
        try:
            session_token = _ACTIVE_SESSION.set(session)
            span_token = _ACTIVE_SPAN.set(parent_span)
        except Exception:
            if session_token is not None:
                try:
                    _ACTIVE_SESSION.reset(session_token)
                except Exception:
                    pass
            return callback(*args, **kwargs)
        try:
            return callback(*args, **kwargs)
        finally:
            if span_token is not None:
                try:
                    _ACTIVE_SPAN.reset(span_token)
                except Exception:
                    pass
            if session_token is not None:
                try:
                    _ACTIVE_SESSION.reset(session_token)
                except Exception:
                    pass

    return run


@contextmanager
def retrieval_trace(
    *,
    mode: str,
    embedding_model: object,
    embedding_precision: object,
    top_k: int,
    candidates: int,
    namespace_count: int,
    initial_fanout: int,
    routing_selection_reason: object | None = None,
    routing_semantic_score: object | None = None,
    routing_semantic_margin: object | None = None,
) -> Iterator[TelemetrySpan]:
    """Create and persist one best-effort live retrieval trace."""

    if not local_telemetry_enabled() or _ACTIVE_SESSION.get() is not None:
        yield _NOOP_SPAN
        return

    session: _TraceSession | None = None
    span: Span | None = None
    active_session_token = None
    active_span_token = None
    try:
        session = _new_trace_session()
        span = session.tracer.start_span(
            ROOT_SPAN_NAME,
            context=Context(),
            attributes=_sanitize_attributes(
                {
                    "buoy.observation.schema_version": OBSERVATION_SCHEMA_VERSION,
                    "buoy.version": __version__,
                    "buoy.retrieval.mode": mode,
                    "buoy.embedding.model": safe_embedding_model(embedding_model),
                    "buoy.embedding.precision": safe_embedding_precision(
                        embedding_precision
                    ),
                    "buoy.retrieval.top_k": top_k,
                    "buoy.retrieval.candidates": candidates,
                    "buoy.retrieval.namespace_count": namespace_count,
                    "buoy.retrieval.initial_fanout": initial_fanout,
                    "buoy.retrieval.final_fanout": 0,
                    "buoy.retrieval.failure_count": 0,
                    "buoy.retrieval.hit_count": 0,
                    "buoy.retrieval.incomplete": False,
                    "buoy.retrieval.widened": False,
                    "buoy.retrieval.outcome": "error",
                    "buoy.routing.selection_reason": routing_selection_reason,
                    "buoy.routing.semantic_score": routing_semantic_score,
                    "buoy.routing.semantic_margin": routing_semantic_margin,
                }
            ),
            start_time=_time_ns(),
            record_exception=False,
            set_status_on_exception=False,
        )
        session.root_span_id = span.get_span_context().span_id
        active_session_token = _ACTIVE_SESSION.set(session)
        active_span_token = _ACTIVE_SPAN.set(span)
    except Exception:
        if active_span_token is not None:
            try:
                _ACTIVE_SPAN.reset(active_span_token)
            except Exception:
                pass
        if active_session_token is not None:
            try:
                _ACTIVE_SESSION.reset(active_session_token)
            except Exception:
                pass
        if span is not None:
            try:
                span.end(end_time=_time_ns())
            except Exception:
                pass
        try:
            if session is not None:
                session.provider.shutdown()
        except Exception:
            pass
        yield _NOOP_SPAN
        return

    assert session is not None
    assert span is not None
    handle = TelemetrySpan(span)
    try:
        yield handle
    except BaseException as exc:
        handle.set_attribute("buoy.retrieval.outcome", "error")
        handle.mark_error(exc)
        raise
    finally:
        try:
            span.end(end_time=_time_ns())
        except Exception:
            pass
        if active_span_token is not None:
            try:
                _ACTIVE_SPAN.reset(active_span_token)
            except Exception:
                pass
        if active_session_token is not None:
            try:
                _ACTIVE_SESSION.reset(active_session_token)
            except Exception:
                pass
        try:
            spans = session.exporter.snapshot()
        except Exception:
            spans = ()
        try:
            session.provider.shutdown()
        except Exception:
            pass
        try:
            _persist_trace_best_effort(spans, root_span_id=session.root_span_id)
        except Exception:
            pass


@contextmanager
def telemetry_span(
    name: str,
    attributes: Mapping[str, object] | None = None,
) -> Iterator[TelemetrySpan]:
    """Create one governed child span inside the current retrieval trace."""

    session = _ACTIVE_SESSION.get()
    parent_span = _ACTIVE_SPAN.get()
    if (
        session is None
        or parent_span is None
        or name not in ALLOWED_SPAN_NAMES
        or name == ROOT_SPAN_NAME
    ):
        yield _NOOP_SPAN
        return
    span: Span | None = None
    span_token = None
    try:
        span = session.tracer.start_span(
            name,
            context=trace.set_span_in_context(parent_span, Context()),
            attributes=_sanitize_attributes(attributes or {}),
            start_time=_time_ns(),
            record_exception=False,
            set_status_on_exception=False,
        )
        span_token = _ACTIVE_SPAN.set(span)
    except Exception:
        if span_token is not None:
            try:
                _ACTIVE_SPAN.reset(span_token)
            except Exception:
                pass
        if span is not None:
            try:
                span.end(end_time=_time_ns())
            except Exception:
                pass
        yield _NOOP_SPAN
        return

    assert span is not None
    handle = TelemetrySpan(span)
    try:
        yield handle
    except BaseException as exc:
        handle.mark_error(exc)
        raise
    finally:
        if span_token is not None:
            try:
                _ACTIVE_SPAN.reset(span_token)
            except Exception:
                pass
        try:
            span.end(end_time=_time_ns())
        except Exception:
            pass


def _new_trace_session() -> _TraceSession:
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import SpanLimits, TracerProvider
    from opentelemetry.sdk.trace.export import (
        SimpleSpanProcessor,
        SpanExportResult,
    )
    from opentelemetry.sdk.trace.sampling import ALWAYS_ON

    exporter = _BufferingSpanExporter(SpanExportResult.SUCCESS)
    provider = TracerProvider(
        sampler=ALWAYS_ON,
        span_limits=SpanLimits(
            max_attributes=64,
            max_events=8,
            max_links=0,
            max_span_attributes=64,
            max_event_attributes=8,
            max_link_attributes=0,
            max_attribute_length=256,
            max_span_attribute_length=256,
        ),
        resource=Resource(
            {
                "service.name": "buoy-search",
                "service.version": __version__,
            }
        ),
        shutdown_on_exit=False,
    )
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("buoy_search.telemetry", __version__)
    return _TraceSession(provider=provider, tracer=tracer, exporter=exporter)


def _sanitize_attributes(
    attributes: Mapping[str, object],
) -> dict[str, str | bool | int | float]:
    sanitized: dict[str, str | bool | int | float] = {}
    for key, value in attributes.items():
        normalized = _sanitize_attribute(key, value)
        if normalized is not None:
            sanitized[key] = normalized
    return sanitized


def _sanitize_attribute(
    key: str,
    value: object,
) -> str | bool | int | float | None:
    if key not in ALLOWED_ATTRIBUTE_KEYS or value is None:
        return None
    if key in _INTEGER_ATTRIBUTE_KEYS:
        if type(value) is not int or value < 0:
            return None
        if key == "buoy.observation.schema_version" and value != 1:
            return None
        return value
    if key in _FLOAT_ATTRIBUTE_KEYS:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        normalized = float(value)
        return normalized if math.isfinite(normalized) else None
    if key in _BOOLEAN_ATTRIBUTE_KEYS:
        return value if type(value) is bool else None
    if not isinstance(value, str):
        return None
    if key == _VERSION_ATTRIBUTE_KEY:
        return value if _VERSION_RE.fullmatch(value) else None
    if key == _REVISION_ATTRIBUTE_KEY:
        return value if _REVISION_RE.fullmatch(value) else None
    allowed_values = _STRING_ATTRIBUTE_VALUES.get(key)
    return value if allowed_values is not None and value in allowed_values else None


def _error_category(exc: BaseException) -> str:
    name = type(exc).__name__
    if name == "ProviderCallError":
        return "provider_call_error"
    if name == "CrossEncoderRerankerError":
        return "reranker_error"
    if isinstance(exc, ValueError):
        return "value_error"
    if isinstance(exc, RuntimeError):
        return "runtime_error"
    return "unexpected_error"


def _persist_trace_best_effort(
    spans: Sequence[ReadableSpan],
    *,
    root_span_id: int | None,
) -> None:
    if not spans or root_span_id is None:
        return
    try:
        _write_trace(spans, root_span_id=root_span_id)
    except Exception:
        return


def _write_trace(
    spans: Sequence[ReadableSpan],
    *,
    root_span_id: int,
) -> None:
    rows = _trace_rows(spans, root_span_id=root_span_id)
    paths = telemetry_paths()
    prepare_default_buoy_home(paths.directory, require_resolved_home=True)
    _prepare_private_directory(paths.directory)
    _prepare_private_file(paths.lock_path)

    with portalocker.Lock(
        str(paths.lock_path),
        mode="a+",
        timeout=0,
        fail_when_locked=True,
    ):
        try:
            paths.database_path.lstat()
        except FileNotFoundError:
            _initialize_database_atomically(paths, rows)
        else:
            _require_private_regular_file(paths.database_path)
            with _connect_database(
                paths.database_path,
                read_only=True,
            ) as validation_connection:
                _validate_schema(validation_connection)
            with _connect_database(paths.database_path) as connection:
                _insert_trace_transaction(connection, rows, initialize=False)
        _chmod_private(paths.database_path)
        _chmod_private(paths.lock_path)


def _initialize_database_atomically(
    paths: TelemetryPaths,
    rows: _TraceRows,
) -> None:
    """Build a complete first database privately before publishing its path."""

    with tempfile.TemporaryDirectory(
        prefix=".initialize-",
        dir=paths.directory,
    ) as temporary_directory:
        temporary_database = Path(temporary_directory) / "telemetry.duckdb"
        with _connect_database(temporary_database) as connection:
            _insert_trace_transaction(connection, rows, initialize=True)
        _chmod_private(temporary_database)
        os.link(temporary_database, paths.database_path, follow_symlinks=False)


def _insert_trace_transaction(
    connection: duckdb.DuckDBPyConnection,
    rows: _TraceRows,
    *,
    initialize: bool,
) -> None:
    connection.execute("BEGIN TRANSACTION")
    try:
        if initialize:
            _initialize_schema(connection)
        connection.execute(
            """
            INSERT INTO trace_runs VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            rows.run,
        )
        connection.executemany(
            "INSERT INTO spans VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows.spans,
        )
        if rows.events:
            connection.executemany(
                "INSERT INTO span_events VALUES (?, ?, ?, ?, ?, ?)",
                rows.events,
            )
    except Exception:
        try:
            connection.execute("ROLLBACK")
        except Exception:
            pass
        raise
    else:
        connection.execute("COMMIT")


def _connect_database(
    path: Path | str,
    *,
    read_only: bool = False,
) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(
        str(path),
        read_only=read_only,
        config=_SAFE_DUCKDB_CONFIG,
    )


def _trace_rows(
    spans: Sequence[ReadableSpan],
    *,
    root_span_id: int,
) -> _TraceRows:
    allowed = [span for span in spans if span.name in ALLOWED_SPAN_NAMES]
    root = next(
        (
            span
            for span in allowed
            if span.context is not None and span.context.span_id == root_span_id
        ),
        None,
    )
    if root is None or root.context is None or root.end_time is None:
        raise ValueError("completed retrieval root span is required")

    trace_id = f"{root.context.trace_id:032x}"
    root_attributes = _sanitize_attributes(root.attributes or {})
    start = _timestamp(root.start_time)
    end = _timestamp(root.end_time)
    duration_ms = _duration_ms(root.start_time, root.end_time)
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
    for readable in sorted(allowed, key=lambda item: item.start_time or 0):
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
        attributes = _sanitize_attributes(readable.attributes or {})
        span_rows.append(
            (
                trace_id,
                span_id,
                parent_id,
                readable.name,
                _timestamp(readable.start_time),
                _timestamp(readable.end_time),
                _duration_ms(readable.start_time, readable.end_time),
                readable.status.status_code.name,
                _json_object(attributes),
            )
        )
        if readable.context.span_id != root_span_id:
            continue
        for event_index, event in enumerate(readable.events or ()):
            if event.name not in ALLOWED_EVENT_NAMES or event.timestamp is None:
                continue
            event_attributes = {
                key: value
                for key, value in _sanitize_attributes(event.attributes or {}).items()
                if key in _EVENT_ATTRIBUTE_KEYS
            }
            event_rows.append(
                (
                    trace_id,
                    span_id,
                    event_index,
                    event.name,
                    _timestamp(event.timestamp),
                    _json_object(event_attributes),
                )
            )
    if not span_rows:
        raise ValueError("completed retrieval spans are required")
    return _TraceRows(
        run=run,
        spans=tuple(span_rows),
        events=tuple(event_rows),
    )


def _timestamp(value: int | None) -> datetime:
    if type(value) is not int or value < 0:
        raise ValueError("span timestamp must be a nonnegative integer")
    # DuckDB's TIMESTAMP is timezone-naive. Bind a naive UTC value so the
    # connection's local TimeZone cannot shift the recorded instant.
    return datetime(1970, 1, 1) + timedelta(
        microseconds=value // 1_000
    )


def _duration_ms(start: int | None, end: int | None) -> float:
    if type(start) is not int or type(end) is not int or end < start:
        raise ValueError("span duration must be finite and nonnegative")
    duration = (end - start) / 1_000_000.0
    if not math.isfinite(duration):
        raise ValueError("span duration must be finite and nonnegative")
    return duration


def _json_object(attributes: Mapping[str, object]) -> str:
    return json.dumps(attributes, sort_keys=True, separators=(",", ":"))


def _prepare_private_directory(path: Path) -> None:
    try:
        observed = path.lstat()
    except FileNotFoundError:
        path.mkdir(mode=0o700)
        observed = path.lstat()
    if not stat.S_ISDIR(observed.st_mode) or path.is_symlink():
        raise ValueError(f"telemetry directory must be a real directory: {path}")
    try:
        path.chmod(0o700)
    except OSError:
        if os.name == "posix":
            raise


def _prepare_private_file(path: Path) -> None:
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError:
        observed = path.lstat()
        if not stat.S_ISREG(observed.st_mode) or path.is_symlink():
            raise ValueError(f"telemetry file must be a real regular file: {path}")
    else:
        os.close(descriptor)
    _chmod_private(path)


def _require_private_regular_file(path: Path) -> None:
    observed = path.lstat()
    if not stat.S_ISREG(observed.st_mode) or path.is_symlink():
        raise ValueError(f"telemetry file must be a real regular file: {path}")


def _chmod_private(path: Path) -> None:
    try:
        path.chmod(0o600)
    except OSError:
        if os.name == "posix":
            raise


_TABLE_LAYOUTS: dict[
    str,
    tuple[tuple[str, str, bool, bool], ...],
] = {
    "telemetry_metadata": (
        ("singleton", "BOOLEAN", True, True),
        ("schema_version", "INTEGER", True, False),
        ("created_at", "TIMESTAMP", True, False),
        ("runs_view_sha256", "VARCHAR", True, False),
        ("stage_view_sha256", "VARCHAR", True, False),
    ),
    "trace_runs": (
        ("trace_id", "VARCHAR", True, True),
        ("root_span_id", "VARCHAR", True, False),
        ("started_at", "TIMESTAMP", True, False),
        ("ended_at", "TIMESTAMP", True, False),
        ("duration_ms", "DOUBLE", True, False),
        ("retrieval_mode", "VARCHAR", True, False),
        ("outcome", "VARCHAR", True, False),
        ("hit_count", "INTEGER", True, False),
        ("namespace_count", "INTEGER", True, False),
        ("initial_fanout", "INTEGER", True, False),
        ("final_fanout", "INTEGER", True, False),
        ("failure_count", "INTEGER", True, False),
        ("incomplete", "BOOLEAN", True, False),
        ("widened", "BOOLEAN", True, False),
        ("fallback_reason", "VARCHAR", False, False),
        ("evidence_status", "VARCHAR", False, False),
        ("embedding_model", "VARCHAR", True, False),
        ("embedding_precision", "VARCHAR", True, False),
        ("top_k", "INTEGER", True, False),
        ("candidates", "INTEGER", True, False),
        ("buoy_version", "VARCHAR", True, False),
        ("observation_schema_version", "INTEGER", True, False),
    ),
    "spans": (
        ("trace_id", "VARCHAR", True, True),
        ("span_id", "VARCHAR", True, True),
        ("parent_span_id", "VARCHAR", False, False),
        ("name", "VARCHAR", True, False),
        ("started_at", "TIMESTAMP", True, False),
        ("ended_at", "TIMESTAMP", True, False),
        ("duration_ms", "DOUBLE", True, False),
        ("status_code", "VARCHAR", True, False),
        ("attributes", "JSON", True, False),
    ),
    "span_events": (
        ("trace_id", "VARCHAR", True, True),
        ("span_id", "VARCHAR", True, True),
        ("event_index", "INTEGER", True, True),
        ("name", "VARCHAR", True, False),
        ("occurred_at", "TIMESTAMP", True, False),
        ("attributes", "JSON", True, False),
    ),
}
_VIEW_LAYOUTS: dict[str, tuple[tuple[str, str], ...]] = {
    "retrieval_runs_v1": tuple(
        (name, column_type)
        for name, column_type, _not_null, _primary_key in _TABLE_LAYOUTS[
            "trace_runs"
        ]
    ),
    "retrieval_stage_latency_v1": (
        ("trace_id", "VARCHAR"),
        ("retrieval_started_at", "TIMESTAMP"),
        ("retrieval_mode", "VARCHAR"),
        ("outcome", "VARCHAR"),
        ("span_id", "VARCHAR"),
        ("parent_span_id", "VARCHAR"),
        ("stage", "VARCHAR"),
        ("started_at", "TIMESTAMP"),
        ("ended_at", "TIMESTAMP"),
        ("duration_ms", "DOUBLE"),
        ("status_code", "VARCHAR"),
        ("attributes", "JSON"),
    ),
}


_TABLES_DDL = """
    CREATE TABLE telemetry_metadata (
        singleton BOOLEAN PRIMARY KEY CHECK (singleton),
        schema_version INTEGER NOT NULL,
        created_at TIMESTAMP NOT NULL,
        runs_view_sha256 VARCHAR NOT NULL,
        stage_view_sha256 VARCHAR NOT NULL
    );
    CREATE TABLE trace_runs (
        trace_id VARCHAR PRIMARY KEY,
        root_span_id VARCHAR NOT NULL,
        started_at TIMESTAMP NOT NULL,
        ended_at TIMESTAMP NOT NULL,
        duration_ms DOUBLE NOT NULL CHECK (duration_ms >= 0),
        retrieval_mode VARCHAR NOT NULL,
        outcome VARCHAR NOT NULL,
        hit_count INTEGER NOT NULL CHECK (hit_count >= 0),
        namespace_count INTEGER NOT NULL CHECK (namespace_count >= 0),
        initial_fanout INTEGER NOT NULL CHECK (initial_fanout >= 0),
        final_fanout INTEGER NOT NULL CHECK (final_fanout >= 0),
        failure_count INTEGER NOT NULL CHECK (failure_count >= 0),
        incomplete BOOLEAN NOT NULL,
        widened BOOLEAN NOT NULL,
        fallback_reason VARCHAR,
        evidence_status VARCHAR,
        embedding_model VARCHAR NOT NULL,
        embedding_precision VARCHAR NOT NULL,
        top_k INTEGER NOT NULL CHECK (top_k >= 0),
        candidates INTEGER NOT NULL CHECK (candidates >= 0),
        buoy_version VARCHAR NOT NULL,
        observation_schema_version INTEGER NOT NULL
    );
    CREATE TABLE spans (
        trace_id VARCHAR NOT NULL,
        span_id VARCHAR NOT NULL,
        parent_span_id VARCHAR,
        name VARCHAR NOT NULL,
        started_at TIMESTAMP NOT NULL,
        ended_at TIMESTAMP NOT NULL,
        duration_ms DOUBLE NOT NULL CHECK (duration_ms >= 0),
        status_code VARCHAR NOT NULL,
        attributes JSON NOT NULL,
        PRIMARY KEY (trace_id, span_id)
    );
    CREATE TABLE span_events (
        trace_id VARCHAR NOT NULL,
        span_id VARCHAR NOT NULL,
        event_index INTEGER NOT NULL CHECK (event_index >= 0),
        name VARCHAR NOT NULL,
        occurred_at TIMESTAMP NOT NULL,
        attributes JSON NOT NULL,
        PRIMARY KEY (trace_id, span_id, event_index)
    );
"""
_RUNS_VIEW_DDL = """
    CREATE VIEW retrieval_runs_v1 AS
        SELECT *
        FROM trace_runs
        WHERE observation_schema_version = 1;
"""
_STAGE_VIEW_DDL = """
    CREATE VIEW retrieval_stage_latency_v1 AS
        SELECT
            runs.trace_id,
            runs.started_at AS retrieval_started_at,
            runs.retrieval_mode,
            runs.outcome,
            spans.span_id,
            spans.parent_span_id,
            spans.name AS stage,
            spans.started_at,
            spans.ended_at,
            spans.duration_ms,
            spans.status_code,
            spans.attributes
        FROM retrieval_runs_v1 AS runs
        JOIN spans USING (trace_id)
        WHERE spans.name <> 'buoy.retrieve';
"""


def _create_schema_objects(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute(_TABLES_DDL)
    connection.execute(_RUNS_VIEW_DDL)
    connection.execute(_STAGE_VIEW_DDL)


def _initialize_schema(connection: duckdb.DuckDBPyConnection) -> None:
    _create_schema_objects(connection)
    view_digests = _view_sql_digests(connection)
    expected_digests = _expected_view_sql_digests()
    if view_digests != expected_digests:
        raise ValueError("telemetry DuckDB views are incompatible")
    connection.execute(
        """
        INSERT INTO telemetry_metadata VALUES (
            true,
            1,
            current_timestamp AT TIME ZONE 'UTC',
            ?,
            ?
        )
        """,
        (
            expected_digests["retrieval_runs_v1"],
            expected_digests["retrieval_stage_latency_v1"],
        ),
    )


def _validate_schema(connection: duckdb.DuckDBPyConnection) -> None:
    table_names = {
        str(name)
        for (name,) in connection.execute(
            """
            SELECT table_name
            FROM system.duckdb_tables()
            WHERE database_name = system.current_database()
              AND schema_name = 'main'
            """
        ).fetchall()
    }
    view_names = {
        str(name)
        for (name,) in connection.execute(
            """
            SELECT view_name
            FROM system.duckdb_views()
            WHERE database_name = system.current_database()
              AND schema_name = 'main'
              AND NOT internal
            """
        ).fetchall()
    }
    if table_names != set(_TABLE_LAYOUTS) or view_names != set(_VIEW_LAYOUTS):
        raise ValueError("telemetry DuckDB schema objects are incompatible")
    for table_name, expected_layout in _TABLE_LAYOUTS.items():
        actual_layout = tuple(
            (str(row[1]), str(row[2]), bool(row[3]), bool(row[5]))
            for row in connection.execute(
                f"SELECT * FROM system.pragma_table_info('{table_name}')"
            ).fetchall()
        )
        if actual_layout != expected_layout:
            raise ValueError(
                f"telemetry DuckDB table {table_name!r} is incompatible"
            )
    for view_name, expected_layout in _VIEW_LAYOUTS.items():
        actual_layout = tuple(
            (str(name), str(column_type))
            for name, column_type in connection.execute(
                """
                SELECT column_name, data_type
                FROM system.duckdb_columns()
                WHERE database_name = system.current_database()
                  AND schema_name = 'main'
                  AND table_name = ?
                ORDER BY column_index
                """,
                (view_name,),
            ).fetchall()
        )
        if actual_layout != expected_layout:
            raise ValueError(
                f"telemetry DuckDB view {view_name!r} is incompatible"
            )
    metadata = connection.execute(
        """
        SELECT
            singleton,
            schema_version,
            runs_view_sha256,
            stage_view_sha256
        FROM telemetry_metadata
        """
    ).fetchall()
    view_digests = _view_sql_digests(connection)
    expected_digests = _expected_view_sql_digests()
    if view_digests != expected_digests:
        raise ValueError("telemetry DuckDB views are incompatible")
    expected_metadata = [
        (
            True,
            TELEMETRY_SCHEMA_VERSION,
            expected_digests["retrieval_runs_v1"],
            expected_digests["retrieval_stage_latency_v1"],
        )
    ]
    if metadata != expected_metadata:
        raise ValueError("telemetry DuckDB schema version is incompatible")


def _view_sql_digests(
    connection: duckdb.DuckDBPyConnection,
) -> dict[str, str]:
    rows = connection.execute(
        """
        SELECT view_name, sql
        FROM system.duckdb_views()
        WHERE database_name = system.current_database()
          AND schema_name = 'main'
          AND view_name IN (
              'retrieval_runs_v1',
              'retrieval_stage_latency_v1'
          )
        """
    ).fetchall()
    if len(rows) != len(_VIEW_LAYOUTS):
        raise ValueError("telemetry DuckDB views are incompatible")
    return {
        str(name): hashlib.sha256(str(sql).encode("utf-8")).hexdigest()
        for name, sql in rows
    }


@lru_cache(maxsize=1)
def _expected_view_sql_digests() -> dict[str, str]:
    with _connect_database(":memory:") as connection:
        _create_schema_objects(connection)
        return _view_sql_digests(connection)


def _time_ns() -> int:
    return time.time_ns()
