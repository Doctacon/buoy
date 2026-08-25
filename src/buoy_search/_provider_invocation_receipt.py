"""Private, default-off provider client invocation receipt core."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterator
from concurrent.futures import CancelledError as FuturesCancelledError
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
import json
import threading
from typing import Literal, ParamSpec, TypeVar

__all__: tuple[str, ...] = ()

_P = ParamSpec("_P")
_R = TypeVar("_R")

_Outcome = Literal["success", "error", "interrupted"]
_RequestForm = Literal["server_rrf", "client_rrf"]
_Trigger = Literal[
    "initial", "server_rrf_unsupported", "optional_schema_compatibility"
]
_ErrorCategory = Literal[
    "provider_call_error", "value_error", "runtime_error", "unexpected_error"
]
_CatalogCategory = Literal["namespace_list_page", "metadata", "card_query_page"]

_INVALID_RECEIPT = "provider invocation receipt is invalid"
_MAX_RECEIPT_BYTES = 65_536
_CONTENT_KEYS = frozenset({"logical_operation_count", "invocation_count", "operations"})
_OPERATION_KEYS = frozenset({"route_rank", "outcome", "attempts"})
_ATTEMPT_KEYS = frozenset(
    {"attempt_index", "request_form", "trigger", "outcome", "error_category"}
)
_CATALOG_KEYS = frozenset(
    {"outcome", "invocation_count", "namespace_list_page", "metadata", "card_query_page"}
)
_COUNT_KEYS = frozenset({"success", "error", "interrupted"})
_RECEIPT_KEYS = frozenset({"receipt_schema_version", "unit", "content", "catalog"})
_OUTCOMES = frozenset({"success", "error", "interrupted"})
_REQUEST_FORMS = frozenset({"server_rrf", "client_rrf"})
_TRIGGERS = frozenset(
    {"initial", "server_rrf_unsupported", "optional_schema_compatibility"}
)
_ERROR_CATEGORIES = frozenset(
    {"provider_call_error", "value_error", "runtime_error", "unexpected_error"}
)


class _ReceiptValidationError(ValueError):
    def __init__(self) -> None:
        super().__init__(_INVALID_RECEIPT)


class _ReceiptStateError(RuntimeError):
    pass


@dataclass(frozen=True)
class _ContentAttempt:
    attempt_index: int
    request_form: _RequestForm
    trigger: _Trigger
    outcome: _Outcome
    error_category: _ErrorCategory | None


@dataclass(frozen=True)
class _ContentOperation:
    route_rank: int
    outcome: _Outcome
    attempts: tuple[_ContentAttempt, ...]


@dataclass(frozen=True)
class _Content:
    logical_operation_count: int
    invocation_count: int
    operations: tuple[_ContentOperation, ...]


@dataclass(frozen=True)
class _OutcomeCounts:
    success: int = 0
    error: int = 0
    interrupted: int = 0

    @property
    def _total(self) -> int:
        return self.success + self.error + self.interrupted


@dataclass(frozen=True)
class _Catalog:
    outcome: _Outcome | None
    invocation_count: int
    namespace_list_page: _OutcomeCounts
    metadata: _OutcomeCounts
    card_query_page: _OutcomeCounts


@dataclass(frozen=True)
class _Receipt:
    receipt_schema_version: int
    unit: str
    content: _Content
    catalog: _Catalog


@dataclass
class _MutableAttempt:
    attempt_index: int
    request_form: _RequestForm
    trigger: _Trigger
    outcome: _Outcome | None = None
    error_category: _ErrorCategory | None = None


@dataclass
class _MutableContentOperation:
    route_rank: int
    attempts: list[_MutableAttempt] = field(default_factory=list)
    outcome: _Outcome | None = None


@dataclass
class _MutableCatalogOperation:
    counts: dict[_CatalogCategory, dict[_Outcome, int]] = field(
        default_factory=lambda: {
            "namespace_list_page": {"success": 0, "error": 0, "interrupted": 0},
            "metadata": {"success": 0, "error": 0, "interrupted": 0},
            "card_query_page": {"success": 0, "error": 0, "interrupted": 0},
        }
    )
    attempts: dict[object, _CatalogCategory] = field(default_factory=dict)
    outcome: _Outcome | None = None


class _Ledger:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._healthy = True
        self._sealed = False
        self._receipt_bytes: bytes | None = None
        self._in_flight = 0
        self._next_lease = 1
        self._leases: dict[int, Literal["registered", "running"]] = {}
        self._content: dict[int, _MutableContentOperation] = {}
        self._catalog: _MutableCatalogOperation | None = None

    def _fault(self) -> None:
        try:
            with self._lock:
                self._healthy = False
                self._receipt_bytes = None
        except BaseException:
            self._healthy = False
            self._receipt_bytes = None

    def _require_live_locked(self) -> None:
        if self._sealed:
            self._healthy = False
            self._receipt_bytes = None
            raise _ReceiptStateError()
        if not self._healthy:
            raise _ReceiptStateError()

    def _is_live(self) -> bool:
        with self._lock:
            return self._healthy and not self._sealed

    def _begin_content(self, route_rank: int) -> _MutableContentOperation:
        with self._lock:
            self._require_live_locked()
            if type(route_rank) is not int or not 1 <= route_rank <= 3:
                self._healthy = False
                raise _ReceiptStateError()
            if route_rank in self._content or len(self._content) >= 3:
                self._healthy = False
                raise _ReceiptStateError()
            operation = _MutableContentOperation(route_rank=route_rank)
            self._content[route_rank] = operation
            return operation

    def _begin_content_attempt(
        self,
        operation: _MutableContentOperation,
        request_form: _RequestForm,
        trigger: _Trigger,
    ) -> _MutableAttempt:
        with self._lock:
            self._require_live_locked()
            if self._content.get(operation.route_rank) is not operation:
                self._healthy = False
                raise _ReceiptStateError()
            if operation.outcome is not None or len(operation.attempts) >= 6:
                self._healthy = False
                raise _ReceiptStateError()
            if (
                type(request_form) is not str
                or request_form not in _REQUEST_FORMS
                or type(trigger) is not str
                or trigger not in _TRIGGERS
            ):
                self._healthy = False
                raise _ReceiptStateError()
            attempt = _MutableAttempt(
                attempt_index=len(operation.attempts) + 1,
                request_form=request_form,
                trigger=trigger,
            )
            operation.attempts.append(attempt)
            self._in_flight += 1
            return attempt

    def _complete_content_attempt(
        self,
        operation: _MutableContentOperation,
        attempt: _MutableAttempt,
        outcome: _Outcome,
        error_category: _ErrorCategory | None,
    ) -> None:
        with self._lock:
            self._require_live_locked()
            if (
                self._content.get(operation.route_rank) is not operation
                or attempt not in operation.attempts
                or attempt.outcome is not None
                or self._in_flight <= 0
                or outcome not in _OUTCOMES
                or (outcome == "error") != (error_category in _ERROR_CATEGORIES)
            ):
                self._healthy = False
                raise _ReceiptStateError()
            attempt.outcome = outcome
            attempt.error_category = error_category
            self._in_flight -= 1

    def _complete_content(
        self, operation: _MutableContentOperation, outcome: _Outcome
    ) -> None:
        with self._lock:
            self._require_live_locked()
            if (
                self._content.get(operation.route_rank) is not operation
                or operation.outcome is not None
                or outcome not in _OUTCOMES
                or any(attempt.outcome is None for attempt in operation.attempts)
            ):
                self._healthy = False
                raise _ReceiptStateError()
            operation.outcome = outcome

    def _begin_catalog(self) -> _MutableCatalogOperation:
        with self._lock:
            self._require_live_locked()
            if self._catalog is not None:
                self._healthy = False
                raise _ReceiptStateError()
            self._catalog = _MutableCatalogOperation()
            return self._catalog

    def _begin_catalog_attempt(
        self,
        operation: _MutableCatalogOperation,
        category: _CatalogCategory,
    ) -> object:
        with self._lock:
            self._require_live_locked()
            if (
                self._catalog is not operation
                or operation.outcome is not None
                or type(category) is not str
                or category not in operation.counts
            ):
                self._healthy = False
                raise _ReceiptStateError()
            marker = object()
            operation.attempts[marker] = category
            self._in_flight += 1
            return marker

    def _complete_catalog_attempt(
        self,
        operation: _MutableCatalogOperation,
        marker: object,
        category: _CatalogCategory,
        outcome: _Outcome,
    ) -> None:
        with self._lock:
            self._require_live_locked()
            if (
                self._catalog is not operation
                or operation.outcome is not None
                or operation.attempts.get(marker) != category
                or category not in operation.counts
                or outcome not in _OUTCOMES
                or self._in_flight <= 0
            ):
                self._healthy = False
                raise _ReceiptStateError()
            del operation.attempts[marker]
            operation.counts[category][outcome] += 1
            self._in_flight -= 1

    def _complete_catalog(
        self, operation: _MutableCatalogOperation, outcome: _Outcome
    ) -> None:
        with self._lock:
            self._require_live_locked()
            if (
                self._catalog is not operation
                or operation.outcome is not None
                or operation.attempts
                or outcome not in _OUTCOMES
            ):
                self._healthy = False
                raise _ReceiptStateError()
            operation.outcome = outcome

    def _register_lease(self) -> int:
        with self._lock:
            self._require_live_locked()
            lease = self._next_lease
            self._next_lease += 1
            self._leases[lease] = "registered"
            return lease

    def _claim_lease(self, lease: int) -> bool:
        with self._lock:
            self._require_live_locked()
            if self._leases.get(lease) != "registered":
                self._healthy = False
                raise _ReceiptStateError()
            self._leases[lease] = "running"
            return True

    def _release_lease(self, lease: int) -> None:
        with self._lock:
            self._require_live_locked()
            if self._leases.get(lease) != "running":
                self._healthy = False
                raise _ReceiptStateError()
            del self._leases[lease]

    def _model_locked(self) -> _Receipt:
        operations = tuple(
            _ContentOperation(
                route_rank=operation.route_rank,
                outcome=operation.outcome,  # type: ignore[arg-type]
                attempts=tuple(
                    _ContentAttempt(
                        attempt_index=attempt.attempt_index,
                        request_form=attempt.request_form,
                        trigger=attempt.trigger,
                        outcome=attempt.outcome,  # type: ignore[arg-type]
                        error_category=attempt.error_category,
                    )
                    for attempt in operation.attempts
                ),
            )
            for operation in sorted(self._content.values(), key=lambda item: item.route_rank)
        )
        content = _Content(
            logical_operation_count=len(operations),
            invocation_count=sum(len(operation.attempts) for operation in operations),
            operations=operations,
        )
        if self._catalog is None:
            catalog = _Catalog(
                outcome=None,
                invocation_count=0,
                namespace_list_page=_OutcomeCounts(),
                metadata=_OutcomeCounts(),
                card_query_page=_OutcomeCounts(),
            )
        else:
            count_models = {
                category: _OutcomeCounts(**counts)
                for category, counts in self._catalog.counts.items()
            }
            catalog = _Catalog(
                outcome=self._catalog.outcome,
                invocation_count=sum(count._total for count in count_models.values()),
                namespace_list_page=count_models["namespace_list_page"],
                metadata=count_models["metadata"],
                card_query_page=count_models["card_query_page"],
            )
        return _Receipt(
            receipt_schema_version=1,
            unit="provider_client_invocation",
            content=content,
            catalog=catalog,
        )

    def _seal(self) -> None:
        try:
            with self._lock:
                if self._sealed:
                    self._healthy = False
                    self._receipt_bytes = None
                    return
                self._sealed = True
                if (
                    not self._healthy
                    or self._in_flight != 0
                    or self._leases
                    or any(operation.outcome is None for operation in self._content.values())
                    or (self._catalog is not None and self._catalog.outcome is None)
                ):
                    self._healthy = False
                    self._receipt_bytes = None
                    return
                model = self._model_locked()
                _validate_receipt_model(model)
                encoded = _encode_receipt_model(model)
                decoded = _decode_receipt(encoded)
                if decoded != model or _encode_receipt_model(decoded) != encoded:
                    raise _ReceiptValidationError()
                self._receipt_bytes = encoded
        except BaseException:
            self._fault()

    def _receipt(self) -> bytes | None:
        try:
            with self._lock:
                if not self._healthy or not self._sealed:
                    return None
                return self._receipt_bytes
        except BaseException:
            self._fault()
            return None


_ACTIVE_LEDGER: ContextVar[_Ledger | None] = ContextVar(
    "buoy_private_provider_invocation_receipt_ledger", default=None
)


class _ReceiptHandle:
    def __init__(self, ledger: _Ledger | None = None) -> None:
        self._ledger = ledger

    def receipt(self) -> bytes | None:
        if self._ledger is None:
            return None
        return self._ledger._receipt()

    def _catalog_observer(self) -> _CatalogObserver | None:
        ledger = self._ledger
        if ledger is None:
            return None
        try:
            if _ACTIVE_LEDGER.get() is not ledger or not ledger._is_live():
                return None
            return _CatalogObserver(ledger)
        except BaseException:
            ledger._fault()
            return None


@contextmanager
def _provider_invocation_receipt_scope() -> Iterator[_ReceiptHandle]:
    try:
        active = _ACTIVE_LEDGER.get()
    except BaseException:
        yield _ReceiptHandle()
        return
    if active is not None:
        yield _ReceiptHandle()
        return

    try:
        ledger = _Ledger()
        token = _ACTIVE_LEDGER.set(ledger)
    except BaseException:
        if "ledger" in locals():
            ledger._fault()
        yield _ReceiptHandle()
        return

    handle = _ReceiptHandle(ledger)
    try:
        yield handle
    finally:
        try:
            _ACTIVE_LEDGER.reset(token)
        except BaseException:
            ledger._fault()
        ledger._seal()


def _active_ledger() -> _Ledger | None:
    try:
        return _ACTIVE_LEDGER.get()
    except BaseException:
        return None


class _ContentOperationObserver:
    def __init__(
        self,
        ledger: _Ledger | None,
        operation: _MutableContentOperation | None,
    ) -> None:
        self._ledger = ledger
        self._operation = operation

    def _invoke(
        self,
        request_form: _RequestForm,
        trigger: _Trigger,
        callback: Callable[_P, _R],
        *args: _P.args,
        **kwargs: _P.kwargs,
    ) -> _R:
        ledger = self._ledger
        operation = self._operation
        attempt: _MutableAttempt | None = None
        if ledger is not None and operation is not None:
            try:
                attempt = ledger._begin_content_attempt(operation, request_form, trigger)
            except BaseException:
                ledger._fault()
        try:
            result = callback(*args, **kwargs)
        except BaseException as exc:
            if ledger is not None and operation is not None and attempt is not None:
                outcome = _exception_outcome(exc)
                category = _content_error_category(exc) if outcome == "error" else None
                try:
                    ledger._complete_content_attempt(
                        operation, attempt, outcome, category
                    )
                except BaseException:
                    ledger._fault()
            raise
        if ledger is not None and operation is not None and attempt is not None:
            try:
                ledger._complete_content_attempt(
                    operation, attempt, "success", None
                )
            except BaseException:
                ledger._fault()
        return result


@contextmanager
def _content_operation(route_rank: int) -> Iterator[_ContentOperationObserver]:
    ledger = _active_ledger()
    operation: _MutableContentOperation | None = None
    if ledger is not None:
        try:
            operation = ledger._begin_content(route_rank)
        except BaseException:
            ledger._fault()
    observer = _ContentOperationObserver(ledger, operation)
    try:
        yield observer
    except BaseException as exc:
        if ledger is not None and operation is not None:
            try:
                ledger._complete_content(operation, _exception_outcome(exc))
            except BaseException:
                ledger._fault()
        raise
    else:
        if ledger is not None and operation is not None:
            outcome: _Outcome = "success"
            if operation.attempts and operation.attempts[-1].outcome in _OUTCOMES:
                final = operation.attempts[-1].outcome
                if final != "success":
                    outcome = final  # type: ignore[assignment]
            try:
                ledger._complete_content(operation, outcome)
            except BaseException:
                ledger._fault()


class _CatalogObserver:
    def __init__(self, ledger: _Ledger) -> None:
        self._ledger = ledger

    @contextmanager
    def _operation(self) -> Iterator[_CatalogOperationObserver]:
        operation: _MutableCatalogOperation | None = None
        try:
            operation = self._ledger._begin_catalog()
        except BaseException:
            self._ledger._fault()
        observer = _CatalogOperationObserver(self._ledger, operation)
        try:
            yield observer
        except BaseException as exc:
            if operation is not None:
                try:
                    self._ledger._complete_catalog(
                        operation, _exception_outcome(exc)
                    )
                except BaseException:
                    self._ledger._fault()
            raise
        else:
            if operation is not None:
                try:
                    self._ledger._complete_catalog(operation, "success")
                except BaseException:
                    self._ledger._fault()


class _CatalogOperationObserver:
    def __init__(
        self,
        ledger: _Ledger,
        operation: _MutableCatalogOperation | None,
    ) -> None:
        self._ledger = ledger
        self._operation = operation

    def _invoke(
        self,
        category: _CatalogCategory,
        callback: Callable[_P, _R],
        *args: _P.args,
        **kwargs: _P.kwargs,
    ) -> _R:
        marker: object | None = None
        if self._operation is not None:
            try:
                marker = self._ledger._begin_catalog_attempt(
                    self._operation, category
                )
            except BaseException:
                self._ledger._fault()
        try:
            result = callback(*args, **kwargs)
        except BaseException as exc:
            if self._operation is not None and marker is not None:
                try:
                    self._ledger._complete_catalog_attempt(
                        self._operation,
                        marker,
                        category,
                        _exception_outcome(exc),
                    )
                except BaseException:
                    self._ledger._fault()
            raise
        if self._operation is not None and marker is not None:
            try:
                self._ledger._complete_catalog_attempt(
                    self._operation, marker, category, "success"
                )
            except BaseException:
                self._ledger._fault()
        return result


def _bind_receipt_worker(callback: Callable[_P, _R]) -> Callable[_P, _R]:
    ledger = _active_ledger()
    if ledger is None:
        return callback
    try:
        lease = ledger._register_lease()
    except BaseException:
        ledger._fault()
        return callback

    def run(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        claimed = False
        token = None
        try:
            try:
                claimed = ledger._claim_lease(lease)
            except BaseException:
                ledger._fault()
            if claimed:
                try:
                    token = _ACTIVE_LEDGER.set(ledger)
                except BaseException:
                    ledger._fault()
            return callback(*args, **kwargs)
        finally:
            if token is not None:
                try:
                    _ACTIVE_LEDGER.reset(token)
                except BaseException:
                    ledger._fault()
            if claimed:
                try:
                    ledger._release_lease(lease)
                except BaseException:
                    ledger._fault()

    return run


def _exception_outcome(exc: BaseException) -> _Outcome:
    if isinstance(exc, (asyncio.CancelledError, FuturesCancelledError)):
        return "interrupted"
    if not isinstance(exc, Exception):
        return "interrupted"
    return "error"


def _content_error_category(exc: BaseException) -> _ErrorCategory:
    if type(exc).__name__ == "ProviderCallError":
        return "provider_call_error"
    if isinstance(exc, ValueError):
        return "value_error"
    if isinstance(exc, RuntimeError):
        return "runtime_error"
    return "unexpected_error"


def _invalid() -> None:
    raise _ReceiptValidationError()


def _exact_dict(value: object, keys: frozenset[str]) -> dict[str, object]:
    if type(value) is not dict or frozenset(value) != keys:
        _invalid()
    return value  # type: ignore[return-value]


def _exact_int(value: object, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        _invalid()
    return value


def _exact_enum(value: object, allowed: frozenset[str]) -> str:
    if type(value) is not str or value not in allowed:
        _invalid()
    return value


def _parse_attempt(value: object) -> _ContentAttempt:
    item = _exact_dict(value, _ATTEMPT_KEYS)
    outcome = _exact_enum(item["outcome"], _OUTCOMES)
    error_category = item["error_category"]
    if outcome == "error":
        error_category = _exact_enum(error_category, _ERROR_CATEGORIES)
    elif error_category is not None:
        _invalid()
    return _ContentAttempt(
        attempt_index=_exact_int(item["attempt_index"], 1, 6),
        request_form=_exact_enum(item["request_form"], _REQUEST_FORMS),  # type: ignore[arg-type]
        trigger=_exact_enum(item["trigger"], _TRIGGERS),  # type: ignore[arg-type]
        outcome=outcome,  # type: ignore[arg-type]
        error_category=error_category,  # type: ignore[arg-type]
    )


def _validate_attempt_grammar(attempts: tuple[_ContentAttempt, ...]) -> None:
    index = 0
    round_index = 0
    while index < len(attempts):
        if round_index >= 3:
            _invalid()
        server = attempts[index]
        expected_trigger = "initial" if round_index == 0 else "optional_schema_compatibility"
        if server.request_form != "server_rrf" or server.trigger != expected_trigger:
            _invalid()
        index += 1
        if server.outcome in {"success", "interrupted"}:
            if index != len(attempts):
                _invalid()
            break
        if index < len(attempts) and attempts[index].request_form == "client_rrf":
            client = attempts[index]
            if (
                server.error_category != "unexpected_error"
                or client.trigger != "server_rrf_unsupported"
            ):
                _invalid()
            index += 1
            if client.outcome in {"success", "interrupted"}:
                if index != len(attempts):
                    _invalid()
                break
        if index < len(attempts) and attempts[index].request_form != "server_rrf":
            _invalid()
        round_index += 1


def _parse_operation(value: object) -> _ContentOperation:
    item = _exact_dict(value, _OPERATION_KEYS)
    raw_attempts = item["attempts"]
    if type(raw_attempts) is not list or len(raw_attempts) > 6:
        _invalid()
    attempts = tuple(_parse_attempt(attempt) for attempt in raw_attempts)
    if tuple(attempt.attempt_index for attempt in attempts) != tuple(
        range(1, len(attempts) + 1)
    ):
        _invalid()
    _validate_attempt_grammar(attempts)
    outcome = _exact_enum(item["outcome"], _OUTCOMES)
    if not attempts:
        if outcome == "success":
            _invalid()
    else:
        final = attempts[-1].outcome
        if final == "error" and outcome != "error":
            _invalid()
        if final == "interrupted" and outcome != "interrupted":
            _invalid()
    return _ContentOperation(
        route_rank=_exact_int(item["route_rank"], 1, 3),
        outcome=outcome,  # type: ignore[arg-type]
        attempts=attempts,
    )


def _parse_content(value: object) -> _Content:
    item = _exact_dict(value, _CONTENT_KEYS)
    raw_operations = item["operations"]
    if type(raw_operations) is not list or len(raw_operations) > 3:
        _invalid()
    operations = tuple(_parse_operation(operation) for operation in raw_operations)
    logical_count = _exact_int(item["logical_operation_count"], 0, 3)
    invocation_count = _exact_int(item["invocation_count"], 0, 18)
    if logical_count != len(operations):
        _invalid()
    if tuple(operation.route_rank for operation in operations) != tuple(
        range(1, logical_count + 1)
    ):
        _invalid()
    if invocation_count != sum(len(operation.attempts) for operation in operations):
        _invalid()
    return _Content(logical_count, invocation_count, operations)


def _parse_counts(value: object, maximum: int) -> _OutcomeCounts:
    item = _exact_dict(value, _COUNT_KEYS)
    counts = _OutcomeCounts(
        success=_exact_int(item["success"], 0, maximum),
        error=_exact_int(item["error"], 0, 1),
        interrupted=_exact_int(item["interrupted"], 0, 1),
    )
    if counts._total > maximum:
        _invalid()
    return counts


def _two_passes(total: int) -> bool:
    return 2 <= total <= 20_000


def _validate_catalog_source_order(catalog: _Catalog) -> None:
    namespace = catalog.namespace_list_page
    metadata = catalog.metadata
    card = catalog.card_query_page
    terminal_count = (
        namespace.error
        + namespace.interrupted
        + metadata.error
        + metadata.interrupted
        + card.error
        + card.interrupted
    )
    if terminal_count > 1:
        _invalid()
    if namespace._total > 20_001 or metadata._total > 1 or card._total > 20_000:
        _invalid()
    if catalog.invocation_count != namespace._total + metadata._total + card._total:
        _invalid()
    if catalog.invocation_count > 40_002:
        _invalid()

    if catalog.outcome is None:
        if catalog.invocation_count != 0:
            _invalid()
        return

    expected_terminal = "error" if (
        namespace.error or metadata.error or card.error
    ) else "interrupted" if (
        namespace.interrupted or metadata.interrupted or card.interrupted
    ) else None
    if expected_terminal is not None and catalog.outcome != expected_terminal:
        _invalid()

    if catalog.outcome == "success":
        if terminal_count or metadata.success != 1:
            _invalid()
        if not _two_passes(namespace.success) or not _two_passes(card.success):
            _invalid()
        if namespace.success > 20_000 or catalog.invocation_count > 40_001:
            _invalid()
        return

    if metadata.error or metadata.interrupted:
        if not (
            1 <= namespace.success <= 10_000
            and namespace._total == namespace.success
            and metadata._total == 1
            and card._total == 0
        ):
            _invalid()
        return

    if card.error or card.interrupted:
        if not (
            1 <= namespace.success <= 10_000
            and namespace._total == namespace.success
            and metadata.success == 1
            and metadata._total == 1
            and 1 <= card._total <= 20_000
            and card.success == card._total - 1
        ):
            _invalid()
        return

    if namespace.error or namespace.interrupted:
        if metadata._total == 0 and card._total == 0:
            if not (
                1 <= namespace._total <= 10_000
                and namespace.success == namespace._total - 1
            ):
                _invalid()
            return
        if not (
            metadata.success == 1
            and metadata._total == 1
            and card._total == card.success
            and _two_passes(card.success)
            and 2 <= namespace._total <= 20_001
            and namespace.success == namespace._total - 1
        ):
            _invalid()
        return

    # No invocation itself was terminal; the operation ended in local work.
    if namespace._total != namespace.success or metadata._total != metadata.success or card._total != card.success:
        _invalid()
    if catalog.invocation_count == 0:
        return
    if metadata._total == 0:
        if card._total != 0 or not 1 <= namespace.success <= 10_000:
            _invalid()
        return
    if metadata.success != 1 or namespace.success < 1:
        _invalid()
    if card.success == 0:
        if namespace.success > 10_000:
            _invalid()
        return
    if namespace.success > 10_000 and not _two_passes(card.success):
        _invalid()
    if namespace.success > 20_001 or card.success > 20_000:
        _invalid()
    if catalog.invocation_count == 40_002 and not (
        namespace.success == 20_001
        and metadata.success == 1
        and card.success == 20_000
    ):
        _invalid()


def _parse_catalog(value: object) -> _Catalog:
    item = _exact_dict(value, _CATALOG_KEYS)
    raw_outcome = item["outcome"]
    outcome: _Outcome | None
    if raw_outcome is None:
        outcome = None
    else:
        outcome = _exact_enum(raw_outcome, _OUTCOMES)  # type: ignore[assignment]
    catalog = _Catalog(
        outcome=outcome,
        invocation_count=_exact_int(item["invocation_count"], 0, 40_002),
        namespace_list_page=_parse_counts(item["namespace_list_page"], 20_001),
        metadata=_parse_counts(item["metadata"], 1),
        card_query_page=_parse_counts(item["card_query_page"], 20_000),
    )
    _validate_catalog_source_order(catalog)
    return catalog


def _parse_receipt_value(value: object) -> _Receipt:
    item = _exact_dict(value, _RECEIPT_KEYS)
    if _exact_int(item["receipt_schema_version"], 1, 1) != 1:
        _invalid()
    if type(item["unit"]) is not str or item["unit"] != "provider_client_invocation":
        _invalid()
    return _Receipt(
        receipt_schema_version=1,
        unit="provider_client_invocation",
        content=_parse_content(item["content"]),
        catalog=_parse_catalog(item["catalog"]),
    )


def _model_to_value(model: _Receipt) -> dict[str, object]:
    return {
        "receipt_schema_version": model.receipt_schema_version,
        "unit": model.unit,
        "content": {
            "logical_operation_count": model.content.logical_operation_count,
            "invocation_count": model.content.invocation_count,
            "operations": [
                {
                    "route_rank": operation.route_rank,
                    "outcome": operation.outcome,
                    "attempts": [
                        {
                            "attempt_index": attempt.attempt_index,
                            "request_form": attempt.request_form,
                            "trigger": attempt.trigger,
                            "outcome": attempt.outcome,
                            "error_category": attempt.error_category,
                        }
                        for attempt in operation.attempts
                    ],
                }
                for operation in model.content.operations
            ],
        },
        "catalog": {
            "outcome": model.catalog.outcome,
            "invocation_count": model.catalog.invocation_count,
            "namespace_list_page": {
                "success": model.catalog.namespace_list_page.success,
                "error": model.catalog.namespace_list_page.error,
                "interrupted": model.catalog.namespace_list_page.interrupted,
            },
            "metadata": {
                "success": model.catalog.metadata.success,
                "error": model.catalog.metadata.error,
                "interrupted": model.catalog.metadata.interrupted,
            },
            "card_query_page": {
                "success": model.catalog.card_query_page.success,
                "error": model.catalog.card_query_page.error,
                "interrupted": model.catalog.card_query_page.interrupted,
            },
        },
    }


def _validate_receipt_model(model: _Receipt) -> None:
    if type(model) is not _Receipt:
        _invalid()
    parsed = _parse_receipt_value(_model_to_value(model))
    if parsed != model:
        _invalid()


def _encode_receipt_model(model: _Receipt) -> bytes:
    _validate_receipt_model(model)
    try:
        encoded = json.dumps(
            _model_to_value(model),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError):
        raise _ReceiptValidationError() from None
    if len(encoded) > _MAX_RECEIPT_BYTES:
        _invalid()
    return encoded


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _invalid()
        result[key] = value
    return result


def _reject_constant(_value: str) -> object:
    _invalid()


def _strict_decode_value(data: bytes) -> object:
    if type(data) is not bytes or len(data) > _MAX_RECEIPT_BYTES:
        _invalid()
    try:
        text = data.decode("utf-8")
        return json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except _ReceiptValidationError:
        raise
    except (UnicodeError, json.JSONDecodeError, TypeError, ValueError, RecursionError):
        raise _ReceiptValidationError() from None


def _decode_receipt(data: bytes) -> _Receipt:
    model = _parse_receipt_value(_strict_decode_value(data))
    if _encode_receipt_model(model) != data:
        _invalid()
    return model
