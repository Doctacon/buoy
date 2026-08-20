"""Opt-in, content-free OpenTelemetry traces for local Buoy retrievals.

The module owns only the private in-memory trace producer. Completed traces are
sanitized into a canonical local envelope and handed to the private queue; the
retrieval process never opens DuckDB or waits for database acknowledgement.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import os
import threading
import time
from typing import TYPE_CHECKING, ParamSpec, TypeVar

from opentelemetry.context import Context
from opentelemetry import trace
from opentelemetry.trace import Span, Status, StatusCode
from buoy_search import __version__
from buoy_search.config import DEFAULT_EMBEDDING_MODEL
from buoy_search.telemetry_envelope import (
    ALLOWED_EVENT_NAMES,
    ALLOWED_SPAN_NAMES,
    EVENT_ATTRIBUTE_KEYS as _EVENT_ATTRIBUTE_KEYS,
    EVIDENCE_SPAN_NAME,
    NAMESPACE_QUERY_SPAN_NAME,
    OBSERVATION_SCHEMA_VERSION,
    QUERY_EMBED_SPAN_NAME,
    RERANK_SPAN_NAME,
    ROOT_SPAN_NAME,
    TraceRows as _TraceRows,
    WIDENED_EVENT_NAME,
    encode_trace_envelope_v1,
    sanitize_attribute as _envelope_sanitize_attribute,
    sanitize_attributes as _envelope_sanitize_attributes,
    trace_rows_from_spans,
)
from buoy_search.telemetry_queue import (
    publish_envelope,
    request_writer_start,
    telemetry_paths,
)

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import ReadableSpan, TracerProvider


TELEMETRY_ENV = "BUOY_TELEMETRY"
LOCAL_TELEMETRY_VALUE = "local"
OTEL_SDK_DISABLED_ENV = "OTEL_SDK_DISABLED"

_P = ParamSpec("_P")
_R = TypeVar("_R")


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
    return _envelope_sanitize_attributes(attributes)


def _sanitize_attribute(
    key: str,
    value: object,
) -> str | bool | int | float | None:
    return _envelope_sanitize_attribute(key, value)


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
        rows = trace_rows_from_spans(spans, root_span_id=root_span_id)
        payload = encode_trace_envelope_v1(rows)
        paths = telemetry_paths()
        publication = publish_envelope(payload, paths=paths)
        if publication.published:
            request_writer_start(paths=paths)
    except Exception:
        return


_trace_rows = trace_rows_from_spans


def _time_ns() -> int:
    return time.time_ns()
