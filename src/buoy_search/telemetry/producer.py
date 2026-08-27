"""Opt-in, content-free OpenTelemetry traces for local Buoy retrievals."""

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
from buoy_search.telemetry.envelope import (
    ALLOWED_EVENT_NAMES,
    ALLOWED_SPAN_NAMES,
    EVENT_ATTRIBUTE_KEYS as _EVENT_ATTRIBUTE_KEYS,
    EVIDENCE_SPAN_NAME,
    NAMESPACE_QUERY_SPAN_NAME,
    QUERY_EMBED_SPAN_NAME,
    RERANK_SPAN_NAME,
    ROOT_SPAN_NAME,
    V2_COMMAND_ROOT_SPAN_NAME,
    V2_PIPELINE_SPAN_NAME,
    V2_SPAN_NAMES,
    WIDENED_EVENT_NAME,
    command_trace_rows_from_spans,
    encode_trace_envelope_v1,
    encode_trace_envelope_v2,
    sanitize_attribute as _envelope_sanitize_attribute,
    sanitize_attributes as _envelope_sanitize_attributes,
    sanitize_v2_span_attributes,
    trace_rows_from_spans,
)
from buoy_search.telemetry.queue import (
    publish_envelope,
    request_writer_start,
    telemetry_paths,
    telemetry_paths_v2,
)

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import ReadableSpan, TracerProvider


TELEMETRY_ENV = "BUOY_TELEMETRY"
LOCAL_TELEMETRY_VALUE = "local"
OTEL_SDK_DISABLED_ENV = "OTEL_SDK_DISABLED"

__all__ = [
    "EVIDENCE_SPAN_NAME",
    "NAMESPACE_QUERY_SPAN_NAME",
    "QUERY_EMBED_SPAN_NAME",
    "RERANK_SPAN_NAME",
    "WIDENED_EVENT_NAME",
    "CommandTelemetry",
    "TelemetrySpan",
    "copied_context_callable",
    "local_telemetry_enabled",
    "retrieval_trace",
    "retrieve_command_trace",
    "safe_time_ns",
    "telemetry_span",
]

CLI_BOOTSTRAP_SPAN_NAME = "buoy.cli.bootstrap"
RETRIEVE_PREPARE_SPAN_NAME = "buoy.retrieve.prepare"
ROUTING_CATALOG_SPAN_NAME = "buoy.routing.catalog"
ROUTING_MODEL_SPAN_NAME = "buoy.routing.model"
ROUTING_SELECT_SPAN_NAME = "buoy.routing.select"
OUTPUT_RENDER_SPAN_NAME = "buoy.output.render"

_COMMAND_ERROR_TYPES = frozenset(
    {
        "configuration_error",
        "catalog_error",
        "routing_error",
        "model_error",
        "provider_call_error",
        "render_error",
        "unexpected_error",
    }
)

_P = ParamSpec("_P")
_R = TypeVar("_R")


class _BufferingSpanExporter:
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


class _BufferingSpanProcessor:
    """Synchronously buffer private spans without SDK diagnostic logging."""

    def __init__(self, exporter: _BufferingSpanExporter) -> None:
        self._exporter = exporter

    def on_start(self, span: Span, parent_context: Context | None = None) -> None:
        del span, parent_context

    def _on_ending(self, span: Span) -> None:
        del span

    def on_end(self, span: ReadableSpan) -> None:
        try:
            self._exporter.export((span,))
        except Exception:
            return

    def shutdown(self) -> None:
        try:
            self._exporter.shutdown()
        except Exception:
            return

    def force_flush(self, timeout_millis: int = 30_000) -> bool:
        del timeout_millis
        return True


@dataclass
class _TraceSession:
    provider: TracerProvider
    tracer: trace.Tracer
    exporter: _BufferingSpanExporter
    schema_version: int
    root_span_id: int | None = None
    root_span: Span | None = None
    pipeline_present: bool = False


class TelemetrySpan:
    """Small safe facade over one private OpenTelemetry span."""

    def __init__(
        self,
        span: Span | None = None,
        *,
        schema_version: int = 1,
        name: str = "",
    ) -> None:
        self._span = span
        self._schema_version = schema_version
        self._name = name

    @property
    def enabled(self) -> bool:
        return self._span is not None

    def set_attribute(self, key: str, value: object) -> None:
        if self._span is None:
            return
        if self._schema_version == 2:
            sanitized = sanitize_v2_span_attributes(self._name, {key: value}).get(key)
        else:
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
        if self._schema_version == 2 and self._name != V2_PIPELINE_SPAN_NAME:
            return
        safe_attributes = {
            key: value
            for key, value in _sanitize_attributes(attributes or {}).items()
            if key in _EVENT_ATTRIBUTE_KEYS
        }
        timestamp = safe_time_ns()
        if timestamp is None:
            return
        try:
            self._span.add_event(name, attributes=safe_attributes, timestamp=timestamp)
        except Exception:
            return

    def mark_ok(self) -> None:
        if self._span is None:
            return
        try:
            self._span.set_status(Status(StatusCode.OK))
        except Exception:
            return

    def mark_error_type(self, error_type: str) -> None:
        if self._span is None:
            return
        self.set_attribute("buoy.error.type", error_type)
        try:
            self._span.set_status(Status(StatusCode.ERROR))
        except Exception:
            return

    def mark_error(self, exc: BaseException) -> None:
        self.mark_error_type(_error_category(exc))


_NOOP_SPAN = TelemetrySpan()
_ACTIVE_SESSION: ContextVar[_TraceSession | None] = ContextVar(
    "buoy_active_telemetry_session", default=None
)
_ACTIVE_SPAN: ContextVar[Span | None] = ContextVar(
    "buoy_active_telemetry_span", default=None
)


class CommandTelemetry:
    """Failure-isolated command trace controls used by the retrieve CLI."""

    def __init__(
        self,
        session: _TraceSession | None = None,
        root: TelemetrySpan | None = None,
    ) -> None:
        self._session = session
        self._root = root or _NOOP_SPAN
        self.error_type: str | None = None
        self._finished = False

    @property
    def enabled(self) -> bool:
        return self._root.enabled

    def set_error_type(self, error_type: str, *, replace: bool = False) -> None:
        if error_type not in _COMMAND_ERROR_TYPES:
            error_type = "unexpected_error"
        if self.error_type is None or replace:
            self.error_type = error_type

    @contextmanager
    def stage(
        self,
        name: str,
        *,
        error_type: str = "unexpected_error",
        replace_error: bool = False,
    ) -> Iterator[TelemetrySpan]:
        try:
            with telemetry_span(name, auto_error=False) as span:
                try:
                    yield span
                except BaseException:
                    category = (
                        error_type
                        if replace_error or self.error_type is None
                        else self.error_type
                    )
                    self.set_error_type(category, replace=replace_error)
                    span.mark_error_type(category)
                    raise
                else:
                    span.mark_ok()
        except BaseException:
            raise

    def finish(self, exit_code: int, *, error_type: str | None = None) -> None:
        if self._finished:
            return
        self._finished = True
        if exit_code == 0:
            self._root.set_attributes(
                {
                    "buoy.command.outcome": "success",
                    "buoy.command.exit_code": 0,
                    "buoy.retrieval.pipeline_present": bool(
                        self._session and self._session.pipeline_present
                    ),
                }
            )
            self._root.mark_ok()
            return
        self.set_error_type(error_type or self.error_type or "unexpected_error")
        self._root.set_attributes(
            {
                "buoy.command.outcome": "error",
                "buoy.command.exit_code": max(0, min(255, exit_code)),
                "buoy.error.type": self.error_type or "unexpected_error",
                "buoy.retrieval.pipeline_present": bool(
                    self._session and self._session.pipeline_present
                ),
            }
        )
        self._root.mark_error_type(self.error_type or "unexpected_error")


def local_telemetry_enabled(
    environment: Mapping[str, str] | None = None,
) -> bool:
    source = os.environ if environment is None else environment
    if source.get(TELEMETRY_ENV, "").strip().lower() != LOCAL_TELEMETRY_VALUE:
        return False
    return source.get(OTEL_SDK_DISABLED_ENV, "").strip().lower() != "true"


def safe_time_ns() -> int | None:
    """Return one epoch-nanosecond timestamp without affecting command behavior."""

    try:
        value = _time_ns()
    except Exception:
        return None
    return value if type(value) is int and value >= 0 else None


def safe_embedding_model(value: object) -> str:
    return DEFAULT_EMBEDDING_MODEL if value == DEFAULT_EMBEDDING_MODEL else "custom"


def safe_embedding_precision(value: object) -> str:
    return str(value) if value in {"float16", "float32"} else "custom"


def copied_context_callable(callback: Callable[_P, _R]) -> Callable[_P, _R]:
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
def retrieve_command_trace(
    *,
    started_at_ns: int | None,
    bootstrap_ended_at_ns: int | None,
    execution_mode: str,
    retrieval_mode: str,
) -> Iterator[CommandTelemetry]:
    """Create and publish one best-effort version-2 retrieve command trace."""

    if (
        not local_telemetry_enabled()
        or type(started_at_ns) is not int
        or type(bootstrap_ended_at_ns) is not int
        or bootstrap_ended_at_ns < started_at_ns
        or _ACTIVE_SESSION.get() is not None
    ):
        yield CommandTelemetry()
        return

    session: _TraceSession | None = None
    span: Span | None = None
    session_token = None
    span_token = None
    try:
        session = _new_trace_session(schema_version=2)
        span = session.tracer.start_span(
            V2_COMMAND_ROOT_SPAN_NAME,
            context=Context(),
            attributes=sanitize_v2_span_attributes(
                V2_COMMAND_ROOT_SPAN_NAME,
                {
                    "buoy.observation.schema_version": 2,
                    "buoy.version": __version__,
                    "buoy.command.name": "retrieve",
                    "buoy.command.execution_mode": execution_mode,
                    "buoy.retrieval.mode": retrieval_mode,
                    "buoy.retrieval.pipeline_present": False,
                },
            ),
            start_time=started_at_ns,
            record_exception=False,
            set_status_on_exception=False,
        )
        session.root_span_id = span.get_span_context().span_id
        session.root_span = span
        session_token = _ACTIVE_SESSION.set(session)
        span_token = _ACTIVE_SPAN.set(span)
        _record_completed_child(
            session,
            CLI_BOOTSTRAP_SPAN_NAME,
            started_at_ns,
            bootstrap_ended_at_ns,
        )
    except Exception:
        _reset_private_context(session_token, span_token)
        if span is not None:
            try:
                span.end()
            except Exception:
                pass
        try:
            if session is not None:
                session.provider.shutdown()
        except Exception:
            pass
        yield CommandTelemetry()
        return

    assert session is not None and span is not None
    command = CommandTelemetry(
        session,
        TelemetrySpan(span, schema_version=2, name=V2_COMMAND_ROOT_SPAN_NAME),
    )
    try:
        yield command
    except BaseException:
        command.finish(1, error_type=command.error_type or "unexpected_error")
        raise
    finally:
        if not command._finished:
            command.finish(1, error_type=command.error_type or "unexpected_error")
        end_time = safe_time_ns()
        try:
            if end_time is None:
                span.end()
            else:
                span.end(end_time=end_time)
        except Exception:
            pass
        _reset_private_context(session_token, span_token)
        try:
            spans = session.exporter.snapshot()
        except Exception:
            spans = ()
        try:
            session.provider.shutdown()
        except Exception:
            pass
        _persist_command_trace_best_effort(spans, root_span_id=session.root_span_id)


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
    """Create one live pipeline, nested in v2 or standalone/persisted as v1."""

    active = _ACTIVE_SESSION.get()
    if active is not None:
        if active.schema_version != 2 or active.pipeline_present:
            yield _NOOP_SPAN
            return
        attributes = _retrieval_attributes(
            schema_version=2,
            mode=mode,
            embedding_model=embedding_model,
            embedding_precision=embedding_precision,
            top_k=top_k,
            candidates=candidates,
            namespace_count=namespace_count,
            initial_fanout=initial_fanout,
            routing_selection_reason=routing_selection_reason,
            routing_semantic_score=routing_semantic_score,
            routing_semantic_margin=routing_semantic_margin,
        )
        with _private_span(V2_PIPELINE_SPAN_NAME, attributes) as handle:
            if not handle.enabled:
                yield handle
                return
            active.pipeline_present = True
            if active.root_span is not None:
                try:
                    active.root_span.set_attribute(
                        "buoy.retrieval.pipeline_present", True
                    )
                except Exception:
                    pass
            try:
                yield handle
            except BaseException as exc:
                handle.set_attribute("buoy.retrieval.outcome", "error")
                handle.mark_error(exc)
                raise
        return

    if not local_telemetry_enabled():
        yield _NOOP_SPAN
        return

    session: _TraceSession | None = None
    span: Span | None = None
    session_token = None
    span_token = None
    try:
        session = _new_trace_session(schema_version=1)
        start = safe_time_ns()
        if start is None:
            raise RuntimeError("clock unavailable")
        span = session.tracer.start_span(
            ROOT_SPAN_NAME,
            context=Context(),
            attributes=_sanitize_attributes(
                _retrieval_attributes(
                    schema_version=1,
                    mode=mode,
                    embedding_model=embedding_model,
                    embedding_precision=embedding_precision,
                    top_k=top_k,
                    candidates=candidates,
                    namespace_count=namespace_count,
                    initial_fanout=initial_fanout,
                    routing_selection_reason=routing_selection_reason,
                    routing_semantic_score=routing_semantic_score,
                    routing_semantic_margin=routing_semantic_margin,
                )
            ),
            start_time=start,
            record_exception=False,
            set_status_on_exception=False,
        )
        session.root_span_id = span.get_span_context().span_id
        session.root_span = span
        session_token = _ACTIVE_SESSION.set(session)
        span_token = _ACTIVE_SPAN.set(span)
    except Exception:
        _reset_private_context(session_token, span_token)
        try:
            if session is not None:
                session.provider.shutdown()
        except Exception:
            pass
        yield _NOOP_SPAN
        return

    assert session is not None and span is not None
    handle = TelemetrySpan(span, schema_version=1, name=ROOT_SPAN_NAME)
    try:
        yield handle
    except BaseException as exc:
        handle.set_attribute("buoy.retrieval.outcome", "error")
        handle.mark_error(exc)
        raise
    finally:
        end = safe_time_ns()
        try:
            span.end(end_time=end) if end is not None else span.end()
        except Exception:
            pass
        _reset_private_context(session_token, span_token)
        try:
            spans = session.exporter.snapshot()
        except Exception:
            spans = ()
        try:
            session.provider.shutdown()
        except Exception:
            pass
        _persist_trace_best_effort(spans, root_span_id=session.root_span_id)


@contextmanager
def telemetry_span(
    name: str,
    attributes: Mapping[str, object] | None = None,
    *,
    auto_error: bool = True,
) -> Iterator[TelemetrySpan]:
    """Create one governed child span inside the current private trace."""

    session = _ACTIVE_SESSION.get()
    parent_span = _ACTIVE_SPAN.get()
    allowed = V2_SPAN_NAMES if session and session.schema_version == 2 else ALLOWED_SPAN_NAMES
    roots = {ROOT_SPAN_NAME, V2_COMMAND_ROOT_SPAN_NAME, V2_PIPELINE_SPAN_NAME}
    if session is None or parent_span is None or name not in allowed or name in roots:
        yield _NOOP_SPAN
        return
    with _private_span(name, attributes or {}) as handle:
        try:
            yield handle
        except BaseException as exc:
            if auto_error:
                handle.mark_error(exc)
            raise


@contextmanager
def _private_span(
    name: str,
    attributes: Mapping[str, object],
) -> Iterator[TelemetrySpan]:
    session = _ACTIVE_SESSION.get()
    parent_span = _ACTIVE_SPAN.get()
    if session is None or parent_span is None:
        yield _NOOP_SPAN
        return
    span: Span | None = None
    token = None
    try:
        start = safe_time_ns()
        if start is None:
            raise RuntimeError("clock unavailable")
        sanitized = (
            sanitize_v2_span_attributes(name, attributes)
            if session.schema_version == 2
            else _sanitize_attributes(attributes)
        )
        span = session.tracer.start_span(
            name,
            context=trace.set_span_in_context(parent_span, Context()),
            attributes=sanitized,
            start_time=start,
            record_exception=False,
            set_status_on_exception=False,
        )
        token = _ACTIVE_SPAN.set(span)
    except Exception:
        yield _NOOP_SPAN
        return
    handle = TelemetrySpan(span, schema_version=session.schema_version, name=name)
    try:
        yield handle
    finally:
        if token is not None:
            try:
                _ACTIVE_SPAN.reset(token)
            except Exception:
                pass
        end = safe_time_ns()
        try:
            span.end(end_time=end) if end is not None else span.end()
        except Exception:
            pass


def _record_completed_child(
    session: _TraceSession,
    name: str,
    start: int,
    end: int,
) -> None:
    assert session.root_span is not None
    child = session.tracer.start_span(
        name,
        context=trace.set_span_in_context(session.root_span, Context()),
        start_time=start,
        record_exception=False,
        set_status_on_exception=False,
    )
    child.set_status(Status(StatusCode.OK))
    child.end(end_time=end)


def _retrieval_attributes(
    *,
    schema_version: int,
    mode: str,
    embedding_model: object,
    embedding_precision: object,
    top_k: int,
    candidates: int,
    namespace_count: int,
    initial_fanout: int,
    routing_selection_reason: object | None,
    routing_semantic_score: object | None,
    routing_semantic_margin: object | None,
) -> dict[str, object]:
    return {
        "buoy.observation.schema_version": schema_version,
        "buoy.version": __version__,
        "buoy.retrieval.mode": mode,
        "buoy.embedding.model": safe_embedding_model(embedding_model),
        "buoy.embedding.precision": safe_embedding_precision(embedding_precision),
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


def _new_trace_session(*, schema_version: int) -> _TraceSession:
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import SpanLimits, TracerProvider
    from opentelemetry.sdk.trace.export import SpanExportResult
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
            {"service.name": "buoy-search", "service.version": __version__}
        ),
        shutdown_on_exit=False,
    )
    provider.add_span_processor(_BufferingSpanProcessor(exporter))
    tracer = provider.get_tracer("buoy_search.telemetry.producer", __version__)
    return _TraceSession(provider, tracer, exporter, schema_version)


def _sanitize_attributes(
    attributes: Mapping[str, object],
) -> dict[str, str | bool | int | float]:
    return _envelope_sanitize_attributes(attributes)


def _sanitize_attribute(
    key: str, value: object
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
    spans: Sequence[ReadableSpan], *, root_span_id: int | None
) -> None:
    if not spans or root_span_id is None:
        return
    try:
        payload = encode_trace_envelope_v1(
            trace_rows_from_spans(spans, root_span_id=root_span_id)
        )
        paths = telemetry_paths()
        publication = publish_envelope(payload, paths=paths)
        if publication.published:
            request_writer_start(paths=paths)
    except Exception:
        return


def _persist_command_trace_best_effort(
    spans: Sequence[ReadableSpan], *, root_span_id: int | None
) -> None:
    if not spans or root_span_id is None:
        return
    try:
        payload = encode_trace_envelope_v2(
            command_trace_rows_from_spans(spans, root_span_id=root_span_id)
        )
        paths = telemetry_paths_v2(telemetry_paths().directory)
        publication = publish_envelope(payload, paths=paths)
        if publication.published:
            request_writer_start(paths=paths)
    except Exception:
        return


def _reset_private_context(session_token: object, span_token: object) -> None:
    if span_token is not None:
        try:
            _ACTIVE_SPAN.reset(span_token)  # type: ignore[arg-type]
        except Exception:
            pass
    if session_token is not None:
        try:
            _ACTIVE_SESSION.reset(session_token)  # type: ignore[arg-type]
        except Exception:
            pass


_trace_rows = trace_rows_from_spans


def _time_ns() -> int:
    return time.time_ns()
