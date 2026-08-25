from __future__ import annotations

import asyncio
from concurrent.futures import CancelledError as FuturesCancelledError, ThreadPoolExecutor
from contextvars import Context
from dataclasses import FrozenInstanceError
import itertools
import json
from pathlib import Path
import threading
import unittest
from unittest.mock import patch

import buoy_search
import buoy_search._provider_invocation_receipt as receipt


def counts(success: int = 0, error: int = 0, interrupted: int = 0) -> dict[str, int]:
    return {"success": success, "error": error, "interrupted": interrupted}


def catalog(
    outcome: str | None = None,
    namespace: dict[str, int] | None = None,
    metadata: dict[str, int] | None = None,
    card: dict[str, int] | None = None,
) -> dict[str, object]:
    namespace = namespace or counts()
    metadata = metadata or counts()
    card = card or counts()
    return {
        "outcome": outcome,
        "invocation_count": sum(namespace.values()) + sum(metadata.values()) + sum(card.values()),
        "namespace_list_page": namespace,
        "metadata": metadata,
        "card_query_page": card,
    }


def attempt(
    index: int,
    request_form: str,
    trigger: str,
    outcome: str,
    error_category: str | None = None,
) -> dict[str, object]:
    return {
        "attempt_index": index,
        "request_form": request_form,
        "trigger": trigger,
        "outcome": outcome,
        "error_category": error_category,
    }


def operation(
    route_rank: int,
    outcome: str,
    attempts: list[dict[str, object]],
) -> dict[str, object]:
    return {"route_rank": route_rank, "outcome": outcome, "attempts": attempts}


def value(
    *,
    operations: list[dict[str, object]] | None = None,
    catalog_value: dict[str, object] | None = None,
) -> dict[str, object]:
    operations = operations or []
    return {
        "receipt_schema_version": 1,
        "unit": "provider_client_invocation",
        "content": {
            "logical_operation_count": len(operations),
            "invocation_count": sum(len(item["attempts"]) for item in operations),
            "operations": operations,
        },
        "catalog": catalog_value or catalog(),
    }


def canonical(payload: dict[str, object]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()


def assert_valid(test: unittest.TestCase, payload: dict[str, object]) -> receipt._Receipt:
    model = receipt._parse_receipt_value(payload)
    encoded = canonical(payload)
    test.assertEqual(receipt._decode_receipt(encoded), model)
    return model


def assert_invalid(test: unittest.TestCase, payload: object) -> None:
    with test.assertRaisesRegex(receipt._ReceiptValidationError, "^provider invocation receipt is invalid$"):
        receipt._parse_receipt_value(payload)


class ReceiptLifecycleTests(unittest.TestCase):
    def test_default_off_uses_no_ledger_and_observer_seams_are_noops(self) -> None:
        marker = object()
        callback_calls = []
        self.assertIsNone(receipt._active_ledger())
        with receipt._content_operation(1) as observer:
            self.assertIs(observer._invoke("server_rrf", "initial", lambda: marker), marker)
            callback_calls.append(True)
        original = lambda: marker
        self.assertIs(receipt._bind_receipt_worker(original), original)
        self.assertEqual(callback_calls, [True])
        self.assertIsNone(receipt._active_ledger())

    def test_active_empty_scope_is_canonical_only_after_exit_and_repeatable(self) -> None:
        with receipt._provider_invocation_receipt_scope() as handle:
            self.assertIsNone(handle.receipt())
            self.assertIsNotNone(receipt._active_ledger())
            observer = handle._catalog_observer()
            self.assertIsNotNone(observer)
        first = handle.receipt()
        second = handle.receipt()
        self.assertIs(first, second)
        self.assertEqual(first, canonical(value()))
        self.assertIsNone(handle._catalog_observer())
        assert first is not None
        assert_valid(self, json.loads(first))

    def test_scope_body_exception_identity_survives_finalization(self) -> None:
        exc = RuntimeError("private")
        caught = None
        try:
            with receipt._provider_invocation_receipt_scope() as handle:
                raise exc
        except RuntimeError as raised:
            caught = raised
        self.assertIs(caught, exc)
        self.assertEqual(handle.receipt(), canonical(value()))

    def test_nested_scope_is_null_and_outer_remains_authoritative(self) -> None:
        with receipt._provider_invocation_receipt_scope() as outer:
            outer_ledger = receipt._active_ledger()
            with receipt._provider_invocation_receipt_scope() as inner:
                self.assertIs(receipt._active_ledger(), outer_ledger)
                with receipt._content_operation(1) as operation_observer:
                    operation_observer._invoke("server_rrf", "initial", lambda: None)
            self.assertIsNone(inner.receipt())
        self.assertIsNotNone(outer.receipt())
        self.assertIsNone(inner.receipt())

    def test_independent_contexts_own_isolated_ledgers(self) -> None:
        barrier = threading.Barrier(2)
        results: dict[int, bytes | None] = {}
        ledgers: dict[int, object] = {}

        def run(rank: int) -> None:
            with receipt._provider_invocation_receipt_scope() as handle:
                ledgers[rank] = receipt._active_ledger()
                barrier.wait(timeout=5)
                with receipt._content_operation(1) as observer:
                    for index in range(rank):
                        callback = (
                            (lambda: None)
                            if index == rank - 1
                            else self._raising(ValueError())
                        )
                        try:
                            observer._invoke(
                                "server_rrf",
                                "initial" if index == 0 else "optional_schema_compatibility",
                                callback,
                            )
                        except ValueError:
                            pass
            results[rank] = handle.receipt()

        with ThreadPoolExecutor(max_workers=2) as executor:
            list(executor.map(run, (1, 2)))
        self.assertIsNot(ledgers[1], ledgers[2])
        self.assertEqual(json.loads(results[1])["content"]["invocation_count"], 1)  # type: ignore[arg-type]
        self.assertEqual(json.loads(results[2])["content"]["invocation_count"], 2)  # type: ignore[arg-type]

    @staticmethod
    def _raising(exc: BaseException):
        def raise_it() -> None:
            raise exc
        return raise_it

    def test_explicit_workers_sort_routes_and_do_not_copy_unrelated_context(self) -> None:
        private = receipt.ContextVar("test-private", default="worker-default")
        token = private.set("caller-secret")
        observations: list[str] = []
        try:
            with receipt._provider_invocation_receipt_scope() as handle:
                def work(route_rank: int) -> object:
                    observations.append(private.get())
                    marker = object()
                    with receipt._content_operation(route_rank) as observer:
                        self.assertIs(
                            observer._invoke("server_rrf", "initial", lambda: marker),
                            marker,
                        )
                    return marker

                bound = [receipt._bind_receipt_worker(work) for _ in range(3)]
                with ThreadPoolExecutor(max_workers=3) as executor:
                    futures = [
                        executor.submit(callback, rank)
                        for callback, rank in zip(reversed(bound), (3, 2, 1), strict=True)
                    ]
                    returned = [future.result(timeout=5) for future in futures]
                self.assertEqual(len({id(item) for item in returned}), 3)
        finally:
            private.reset(token)
        payload = json.loads(handle.receipt())  # type: ignore[arg-type]
        self.assertEqual(
            [item["route_rank"] for item in payload["content"]["operations"]],
            [1, 2, 3],
        )
        self.assertEqual(observations, ["worker-default"] * 3)

    def test_worker_context_is_restored_on_reused_thread(self) -> None:
        with ThreadPoolExecutor(max_workers=1) as executor:
            with receipt._provider_invocation_receipt_scope() as handle:
                callback = receipt._bind_receipt_worker(lambda: receipt._active_ledger())
                observed = executor.submit(callback).result(timeout=5)
                self.assertIsNotNone(observed)
            self.assertIsNone(executor.submit(receipt._active_ledger).result(timeout=5))
        self.assertIsNotNone(handle.receipt())

    def test_in_flight_call_makes_premature_exit_unknown_without_waiting(self) -> None:
        started = threading.Event()
        release = threading.Event()
        marker = object()
        returned: list[object] = []
        with receipt._provider_invocation_receipt_scope() as handle:
            with receipt._content_operation(1) as observer:
                def call() -> object:
                    started.set()
                    release.wait(timeout=5)
                    return marker

                thread = threading.Thread(
                    target=lambda: returned.append(
                        observer._invoke("server_rrf", "initial", call)
                    )
                )
                thread.start()
                self.assertTrue(started.wait(timeout=5))
        self.assertIsNone(handle.receipt())
        release.set()
        thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(returned, [marker])
        self.assertIsNone(handle.receipt())

    def test_never_run_lease_and_premature_exit_are_unknown_without_waiting(self) -> None:
        with receipt._provider_invocation_receipt_scope() as never_run:
            receipt._bind_receipt_worker(lambda: None)
        self.assertIsNone(never_run.receipt())

        started = threading.Event()
        release = threading.Event()
        with receipt._provider_invocation_receipt_scope() as premature:
            def work() -> None:
                started.set()
                release.wait(timeout=5)
            callback = receipt._bind_receipt_worker(work)
            thread = threading.Thread(target=callback)
            thread.start()
            self.assertTrue(started.wait(timeout=5))
        self.assertIsNone(premature.receipt())
        release.set()
        thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        self.assertIsNone(premature.receipt())

    def test_worker_binding_fault_runs_callback_once_and_returns_null(self) -> None:
        marker = object()
        calls = 0

        class BrokenBinding:
            def set(self, _value):
                raise RuntimeError("private")

        with receipt._provider_invocation_receipt_scope() as handle:
            def original() -> object:
                nonlocal calls
                calls += 1
                return marker

            callback = receipt._bind_receipt_worker(original)
            with patch.object(receipt, "_ACTIVE_LEDGER", BrokenBinding()):
                self.assertIs(callback(), marker)
        self.assertEqual(calls, 1)
        self.assertIsNone(handle.receipt())

    def test_unpropagated_worker_is_unobserved(self) -> None:
        with receipt._provider_invocation_receipt_scope() as handle:
            def unbound() -> None:
                self.assertIsNone(receipt._active_ledger())
                with receipt._content_operation(1) as observer:
                    observer._invoke("server_rrf", "initial", lambda: None)
            with ThreadPoolExecutor(max_workers=1) as executor:
                executor.submit(unbound).result(timeout=5)
        payload = json.loads(handle.receipt())  # type: ignore[arg-type]
        self.assertEqual(payload["content"]["invocation_count"], 0)

    def test_late_capability_use_invalidates_a_previously_sealed_receipt(self) -> None:
        with receipt._provider_invocation_receipt_scope() as handle:
            observer = handle._catalog_observer()
            self.assertIsNotNone(observer)
        self.assertIsNotNone(handle.receipt())
        marker = object()
        assert observer is not None
        with observer._operation() as operation_observer:
            self.assertIs(
                operation_observer._invoke("metadata", lambda: marker), marker
            )
        self.assertIsNone(handle.receipt())

    def test_activation_and_context_access_faults_run_body_and_return_null(self) -> None:
        body = []
        with patch.object(receipt, "_Ledger", side_effect=RuntimeError("private")):
            with receipt._provider_invocation_receipt_scope() as handle:
                body.append("ran")
        self.assertEqual(body, ["ran"])
        self.assertIsNone(handle.receipt())

        class BrokenContext:
            def get(self):
                raise RuntimeError("private")

        with patch.object(receipt, "_ACTIVE_LEDGER", BrokenContext()):
            with receipt._provider_invocation_receipt_scope() as broken:
                body.append("also-ran")
        self.assertIsNone(broken.receipt())

    def test_lock_and_serialization_faults_return_null(self) -> None:
        class BrokenLock:
            def __enter__(self):
                raise RuntimeError("private")
            def __exit__(self, *_args):
                return False

        with receipt._provider_invocation_receipt_scope() as locked:
            ledger = receipt._active_ledger()
            assert ledger is not None
            ledger._lock = BrokenLock()  # type: ignore[assignment]
        self.assertIsNone(locked.receipt())

        for target in ("_encode_receipt_model", "_strict_decode_value"):
            with self.subTest(target=target):
                with patch.object(receipt, target, side_effect=RuntimeError("private")):
                    with receipt._provider_invocation_receipt_scope() as handle:
                        pass
                self.assertIsNone(handle.receipt())

    def test_observer_registration_and_completion_faults_preserve_result_identity(self) -> None:
        for method in ("_begin_content_attempt", "_complete_content_attempt"):
            with self.subTest(method=method):
                marker = object()
                calls = 0
                with receipt._provider_invocation_receipt_scope() as handle:
                    ledger = receipt._active_ledger()
                    assert ledger is not None
                    with receipt._content_operation(1) as observer:
                        def callback() -> object:
                            nonlocal calls
                            calls += 1
                            return marker
                        with patch.object(ledger, method, side_effect=RuntimeError("private")):
                            self.assertIs(
                                observer._invoke("server_rrf", "initial", callback),
                                marker,
                            )
                self.assertEqual(calls, 1)
                self.assertIsNone(handle.receipt())

    def test_duplicate_completion_and_duplicate_operation_are_unknown(self) -> None:
        with receipt._provider_invocation_receipt_scope() as handle:
            ledger = receipt._active_ledger()
            assert ledger is not None
            operation_state = ledger._begin_content(1)
            attempt_state = ledger._begin_content_attempt(operation_state, "server_rrf", "initial")
            ledger._complete_content_attempt(operation_state, attempt_state, "success", None)
            with self.assertRaises(receipt._ReceiptStateError):
                ledger._complete_content_attempt(operation_state, attempt_state, "success", None)
        self.assertIsNone(handle.receipt())

        with receipt._provider_invocation_receipt_scope() as catalog_handle:
            catalog_ledger = receipt._active_ledger()
            assert catalog_ledger is not None
            catalog_state = catalog_ledger._begin_catalog()
            marker = catalog_ledger._begin_catalog_attempt(catalog_state, "metadata")
            catalog_ledger._complete_catalog_attempt(
                catalog_state, marker, "metadata", "success"
            )
            with self.assertRaises(receipt._ReceiptStateError):
                catalog_ledger._complete_catalog_attempt(
                    catalog_state, marker, "metadata", "success"
                )
        self.assertIsNone(catalog_handle.receipt())


class InterruptionIdentityTests(unittest.TestCase):
    class CustomControlFlow(BaseException):
        pass

    class ProviderCallError(Exception):
        pass

    def test_exact_precedence_identity_and_error_mapping(self) -> None:
        cases: list[tuple[BaseException, str, str | None]] = [
            (asyncio.CancelledError("private"), "interrupted", None),
            (FuturesCancelledError("private"), "interrupted", None),
            (KeyboardInterrupt("private"), "interrupted", None),
            (SystemExit("private"), "interrupted", None),
            (GeneratorExit("private"), "interrupted", None),
            (self.CustomControlFlow("private"), "interrupted", None),
            (self.ProviderCallError("private"), "error", "provider_call_error"),
            (ValueError("private"), "error", "value_error"),
            (RuntimeError("private"), "error", "runtime_error"),
            (TypeError("private"), "error", "unexpected_error"),
            (Exception("private"), "error", "unexpected_error"),
        ]
        for exc, expected_outcome, expected_category in cases:
            with self.subTest(exc_type=type(exc).__name__):
                caught = None
                with receipt._provider_invocation_receipt_scope() as handle:
                    try:
                        with receipt._content_operation(1) as observer:
                            observer._invoke(
                                "server_rrf", "initial", self._raise_exact(exc)
                            )
                    except BaseException as raised:
                        caught = raised
                self.assertIs(caught, exc)
                payload = json.loads(handle.receipt())  # type: ignore[arg-type]
                attempt_value = payload["content"]["operations"][0]["attempts"][0]
                self.assertEqual(attempt_value["outcome"], expected_outcome)
                self.assertEqual(attempt_value["error_category"], expected_category)
                self.assertEqual(payload["content"]["operations"][0]["outcome"], expected_outcome)

    @staticmethod
    def _raise_exact(exc: BaseException):
        def callback() -> None:
            raise exc
        return callback

    def test_worker_and_catalog_rethrow_identical_exception(self) -> None:
        for family in ("worker", "catalog"):
            with self.subTest(family=family):
                exc = FuturesCancelledError("private")
                caught = None
                with receipt._provider_invocation_receipt_scope() as handle:
                    try:
                        if family == "worker":
                            callback = receipt._bind_receipt_worker(self._raise_exact(exc))
                            with ThreadPoolExecutor(max_workers=1) as executor:
                                executor.submit(callback).result(timeout=5)
                        else:
                            observer = handle._catalog_observer()
                            assert observer is not None
                            with observer._operation() as operation_observer:
                                operation_observer._invoke("metadata", self._raise_exact(exc))
                    except BaseException as raised:
                        caught = raised
                self.assertIs(caught, exc)


class ContentGrammarTests(unittest.TestCase):
    def test_exhaustive_valid_round_shapes_and_terminal_outcomes(self) -> None:
        validated = 0
        for rounds in (1, 2, 3):
            for clients in itertools.product((False, True), repeat=rounds):
                for final_outcome in ("success", "error", "interrupted"):
                    attempts = []
                    for round_index, has_client in enumerate(clients):
                        is_final_round = round_index == rounds - 1
                        server_outcome = final_outcome if is_final_round and not has_client else "error"
                        attempts.append(
                            attempt(
                                len(attempts) + 1,
                                "server_rrf",
                                "initial" if round_index == 0 else "optional_schema_compatibility",
                                server_outcome,
                                "unexpected_error" if server_outcome == "error" else None,
                            )
                        )
                        if has_client:
                            client_outcome = final_outcome if is_final_round else "error"
                            attempts.append(
                                attempt(
                                    len(attempts) + 1,
                                    "client_rrf",
                                    "server_rrf_unsupported",
                                    client_outcome,
                                    "value_error" if client_outcome == "error" else None,
                                )
                            )
                    operation_outcome = final_outcome
                    assert_valid(self, value(operations=[operation(1, operation_outcome, attempts)]))
                    validated += 1
        self.assertEqual(validated, 42)

    def test_successful_final_attempt_allows_post_return_operation_outcomes(self) -> None:
        final = [attempt(1, "server_rrf", "initial", "success")]
        for operation_outcome in ("success", "error", "interrupted"):
            assert_valid(self, value(operations=[operation(1, operation_outcome, final)]))

    def test_zero_attempt_operation_only_allows_terminal_outcome(self) -> None:
        for outcome in ("error", "interrupted"):
            assert_valid(self, value(operations=[operation(1, outcome, [])]))
        assert_invalid(self, value(operations=[operation(1, "success", [])]))

    def test_every_grammar_violation_rejects(self) -> None:
        invalid_attempt_sets = [
            [attempt(1, "client_rrf", "server_rrf_unsupported", "success")],
            [attempt(1, "server_rrf", "optional_schema_compatibility", "success")],
            [attempt(1, "server_rrf", "initial", "success"), attempt(2, "server_rrf", "optional_schema_compatibility", "success")],
            [attempt(1, "server_rrf", "initial", "interrupted"), attempt(2, "server_rrf", "optional_schema_compatibility", "success")],
            [attempt(1, "server_rrf", "initial", "error", "value_error"), attempt(2, "client_rrf", "server_rrf_unsupported", "success")],
            [attempt(1, "server_rrf", "initial", "error", "unexpected_error"), attempt(2, "client_rrf", "initial", "success")],
            [attempt(1, "server_rrf", "initial", "error", "unexpected_error"), attempt(2, "client_rrf", "server_rrf_unsupported", "error", "unexpected_error"), attempt(3, "client_rrf", "server_rrf_unsupported", "success")],
            [
                attempt(index, "server_rrf", "initial" if index == 1 else "optional_schema_compatibility", "error", "unexpected_error")
                for index in range(1, 5)
            ],
        ]
        for attempts in invalid_attempt_sets:
            with self.subTest(attempts=attempts):
                assert_invalid(self, value(operations=[operation(1, "error", attempts)]))

    def test_exact_indexes_route_order_counts_types_and_enums(self) -> None:
        valid_attempt = attempt(1, "server_rrf", "initial", "success")
        invalid_payloads = []
        for bad_index in (0, 2, True, 1.0):
            changed = dict(valid_attempt, attempt_index=bad_index)
            invalid_payloads.append(value(operations=[operation(1, "success", [changed])]))
        invalid_payloads.extend(
            [
                value(operations=[operation(2, "success", [valid_attempt])]),
                value(operations=[operation(1, "success", [dict(valid_attempt, request_form="private")])]),
                value(operations=[operation(1, "success", [dict(valid_attempt, trigger="private")])]),
                value(operations=[operation(1, "success", [dict(valid_attempt, outcome="private")])]),
                value(operations=[operation(1, "success", [dict(valid_attempt, error_category="private")])]),
            ]
        )
        mismatched = value(operations=[operation(1, "success", [valid_attempt])])
        mismatched["content"]["invocation_count"] = 0
        invalid_payloads.append(mismatched)
        for payload in invalid_payloads:
            assert_invalid(self, payload)

    def test_route_and_invocation_maxima(self) -> None:
        attempts = []
        for round_index in range(3):
            attempts.extend(
                [
                    attempt(len(attempts) + 1, "server_rrf", "initial" if round_index == 0 else "optional_schema_compatibility", "error", "unexpected_error"),
                    attempt(len(attempts) + 2, "client_rrf", "server_rrf_unsupported", "error", "value_error"),
                ]
            )
        operations = [operation(rank, "error", attempts) for rank in (1, 2, 3)]
        assert_valid(self, value(operations=operations))
        overflow = value(operations=operations)
        overflow["content"]["operations"].append(operation(4, "error", []))
        overflow["content"]["logical_operation_count"] = 4
        assert_invalid(self, overflow)


class CatalogValidatorTests(unittest.TestCase):
    def test_success_boundaries_and_adjacent_values(self) -> None:
        valid_pairs = [(2, 2), (2, 20_000), (20_000, 2), (20_000, 20_000)]
        for namespace_success, card_success in valid_pairs:
            with self.subTest(namespace=namespace_success, card=card_success):
                assert_valid(
                    self,
                    value(catalog_value=catalog("success", counts(namespace_success), counts(1), counts(card_success))),
                )
        for namespace_success, card_success in ((1, 2), (20_001, 2), (2, 1), (2, 20_001)):
            assert_invalid(
                self,
                value(catalog_value=catalog("success", counts(namespace_success), counts(1), counts(card_success))),
            )
        for metadata_success in (0, 2):
            assert_invalid(
                self,
                value(catalog_value=catalog("success", counts(2), counts(metadata_success), counts(2))),
            )

    def test_terminal_per_category_boundaries_and_adjacent_overflow(self) -> None:
        valid = [
            catalog("error"),
            catalog("error", counts(error=1)),
            catalog("error", counts(9_999, error=1)),
            catalog("error", counts(1), counts(error=1)),
            catalog("interrupted", counts(10_000), counts(interrupted=1)),
            catalog("error", counts(1), counts(1), counts(error=1)),
            catalog("error", counts(10_000), counts(1), counts(19_999, error=1)),
            catalog("error", counts(1, error=1), counts(1), counts(2)),
            catalog("interrupted", counts(20_000, interrupted=1), counts(1), counts(20_000)),
        ]
        for item in valid:
            assert_valid(self, value(catalog_value=item))
        invalid = [
            catalog("error", counts(10_000, error=1)),
            catalog("error", counts(10_001), counts(error=1)),
            catalog("error", counts(1), counts(1), counts(20_000, error=1)),
            catalog("error", counts(20_001, error=1), counts(1), counts(20_000)),
            catalog("error", counts(1), counts(2), counts()),
        ]
        for item in invalid:
            assert_invalid(self, value(catalog_value=item))

    def test_all_source_order_prerequisites_and_impossible_states(self) -> None:
        impossible = [
            catalog("error", counts(), counts(1), counts()),
            catalog("error", counts(), counts(1), counts(1)),
            catalog("error", counts(1), counts(), counts(1)),
            catalog("error", counts(10_001), counts(), counts()),
            catalog("error", counts(10_001), counts(1), counts(1)),
            catalog("error", counts(1, error=1), counts(1), counts()),
            catalog("error", counts(1), counts(error=1), counts(1)),
            catalog("error", counts(1, error=1), counts(1), counts(2, error=1)),
            catalog("success", counts(2, error=1), counts(1), counts(2)),
            catalog("interrupted", counts(1), counts(error=1), counts()),
        ]
        for item in impossible:
            with self.subTest(item=item):
                assert_invalid(self, value(catalog_value=item))

    def test_local_terminal_stage_table(self) -> None:
        valid = [
            catalog("error"),
            catalog("interrupted", counts(1)),
            catalog("error", counts(10_000)),
            catalog("error", counts(1), counts(1)),
            catalog("interrupted", counts(10_000), counts(1)),
            catalog("error", counts(1), counts(1), counts(1)),
            catalog("error", counts(10_000), counts(1), counts(20_000)),
            catalog("error", counts(2), counts(1), counts(2)),
            catalog("error", counts(20_001), counts(1), counts(20_000)),
        ]
        for item in valid:
            assert_valid(self, value(catalog_value=item))
        invalid = [
            catalog("error", counts(10_001)),
            catalog("error", counts(10_001), counts(1)),
            catalog("error", counts(10_001), counts(1), counts(1)),
            catalog("error", counts(), counts(1)),
            catalog("error", counts(1), counts(), counts(1)),
        ]
        for item in invalid:
            assert_invalid(self, value(catalog_value=item))

    def test_exact_40002_terminal_composition_and_total_overflow(self) -> None:
        exact = value(
            catalog_value=catalog("error", counts(20_001), counts(1), counts(20_000))
        )
        assert_valid(self, exact)
        success = value(
            catalog_value=catalog("success", counts(20_001), counts(1), counts(20_000))
        )
        assert_invalid(self, success)
        for item in (
            catalog("error", counts(20_000), counts(1), counts(20_001)),
            catalog("error", counts(20_001), counts(1), counts(20_000, error=1)),
        ):
            assert_invalid(self, value(catalog_value=item))

    def test_ambiguous_l1_10001_and_each_second_list_prerequisite_reject(self) -> None:
        cases = [
            catalog("error", counts(10_001)),
            catalog("error", counts(10_001), counts(error=1), counts(2)),
            catalog("error", counts(10_001), counts(interrupted=1), counts(2)),
            catalog("error", counts(10_001), counts(1), counts(1)),
            catalog("error", counts(10_001), counts(1), counts(error=1)),
        ]
        for item in cases:
            assert_invalid(self, value(catalog_value=item))
        assert_valid(
            self,
            value(catalog_value=catalog("error", counts(10_001), counts(1), counts(2))),
        )

    def test_bools_negative_unknown_keys_and_count_mismatches_reject(self) -> None:
        payloads = []
        for bad in (True, -1, 1.0, "1"):
            item = catalog("error")
            item["namespace_list_page"] = counts()
            item["namespace_list_page"]["success"] = bad
            payloads.append(value(catalog_value=item))
        unknown = value()
        unknown["catalog"]["metadata"]["private"] = 1
        payloads.append(unknown)
        mismatch = value(catalog_value=catalog("error", counts(1)))
        mismatch["catalog"]["invocation_count"] = 0
        payloads.append(mismatch)
        for payload in payloads:
            assert_invalid(self, payload)

    def test_catalog_capability_records_only_when_explicitly_used(self) -> None:
        with receipt._provider_invocation_receipt_scope() as inactive_catalog:
            self.assertIsNotNone(inactive_catalog._catalog_observer())
        self.assertIsNone(json.loads(inactive_catalog.receipt())["catalog"]["outcome"])  # type: ignore[arg-type]

        marker = object()
        with receipt._provider_invocation_receipt_scope() as active_catalog:
            observer = active_catalog._catalog_observer()
            assert observer is not None
            with observer._operation() as operation_observer:
                for category in (
                    "namespace_list_page",
                    "metadata",
                    "card_query_page",
                    "card_query_page",
                    "namespace_list_page",
                ):
                    self.assertIs(operation_observer._invoke(category, lambda: marker), marker)
        payload = json.loads(active_catalog.receipt())  # type: ignore[arg-type]
        self.assertEqual(payload["catalog"]["outcome"], "success")
        self.assertEqual(payload["catalog"]["invocation_count"], 5)

    def test_catalog_fault_runs_callback_once_and_returns_null(self) -> None:
        calls = 0
        marker = object()
        with receipt._provider_invocation_receipt_scope() as handle:
            ledger = receipt._active_ledger()
            observer = handle._catalog_observer()
            assert ledger is not None and observer is not None
            with observer._operation() as operation_observer:
                def callback() -> object:
                    nonlocal calls
                    calls += 1
                    return marker
                with patch.object(ledger, "_begin_catalog_attempt", side_effect=RuntimeError("private")):
                    self.assertIs(operation_observer._invoke("metadata", callback), marker)
        self.assertEqual(calls, 1)
        self.assertIsNone(handle.receipt())


class StrictModelAndCanonicalTests(unittest.TestCase):
    def test_empty_model_is_immutable_strict_and_canonical(self) -> None:
        model = assert_valid(self, value())
        self.assertIs(type(model.content.operations), tuple)
        with self.assertRaises(FrozenInstanceError):
            model.unit = "private"  # type: ignore[misc]
        expected = b'{"catalog":{"card_query_page":{"error":0,"interrupted":0,"success":0},"invocation_count":0,"metadata":{"error":0,"interrupted":0,"success":0},"namespace_list_page":{"error":0,"interrupted":0,"success":0},"outcome":null},"content":{"invocation_count":0,"logical_operation_count":0,"operations":[]},"receipt_schema_version":1,"unit":"provider_client_invocation"}'
        self.assertEqual(receipt._encode_receipt_model(model), expected)

    def test_missing_unknown_wrong_top_level_values_reject(self) -> None:
        payloads = []
        for key in tuple(value()):
            item = value()
            del item[key]
            payloads.append(item)
        unknown = value()
        unknown["private"] = "sentinel"
        payloads.append(unknown)
        for key, bad in (
            ("receipt_schema_version", True),
            ("receipt_schema_version", 2),
            ("unit", "provider_request"),
            ("content", []),
            ("catalog", []),
        ):
            item = value()
            item[key] = bad
            payloads.append(item)
        for item in payloads:
            assert_invalid(self, item)

    def test_duplicate_keys_at_every_depth_reject_without_echo(self) -> None:
        samples = [
            b'{"receipt_schema_version":1,"receipt_schema_version":1}',
            b'{"a":{"success":0,"success":0}}',
            b'{"a":[{"private-sentinel":1,"private-sentinel":2}]}',
        ]
        for data in samples:
            with self.assertRaises(receipt._ReceiptValidationError) as raised:
                receipt._strict_decode_value(data)
            self.assertEqual(str(raised.exception), "provider invocation receipt is invalid")
            self.assertNotIn("private-sentinel", str(raised.exception))

    def test_noncanonical_invalid_utf8_nonfinite_and_byte_limit_reject(self) -> None:
        canonical_empty = canonical(value())
        samples = [
            b" " + canonical_empty,
            canonical_empty + b"\n",
            canonical_empty.replace(b'"catalog":', b'"unit":"provider_client_invocation","catalog":', 1),
            b"\xff",
            b'{"value":NaN}',
            b"{" + b" " * receipt._MAX_RECEIPT_BYTES + b"}",
        ]
        for data in samples:
            with self.subTest(prefix=data[:20]):
                with self.assertRaisesRegex(receipt._ReceiptValidationError, "^provider invocation receipt is invalid$"):
                    receipt._decode_receipt(data)

    def test_noncanonical_key_order_and_unicode_escape_reject(self) -> None:
        payload = value()
        pretty = json.dumps(payload, indent=2, sort_keys=True).encode()
        unsorted = json.dumps(payload, separators=(",", ":"), sort_keys=False).encode()
        for data in (pretty, unsorted):
            with self.assertRaises(receipt._ReceiptValidationError):
                receipt._decode_receipt(data)

    def test_privacy_sentinels_are_neither_models_bytes_nor_errors(self) -> None:
        sentinels = [
            "QUERY_PRIVATE_SENTINEL",
            "ARGV_PRIVATE_SENTINEL",
            "NAMESPACE_PRIVATE_SENTINEL",
            "PROVIDER_PRIVATE_SENTINEL",
            "MODEL_PRIVATE_SENTINEL",
            "CONTENT_PRIVATE_SENTINEL",
            "URL_PRIVATE_SENTINEL",
            "CREDENTIAL_PRIVATE_SENTINEL",
            "ERROR_PRIVATE_SENTINEL",
            "TRACE_PRIVATE_SENTINEL",
            "PATH_PRIVATE_SENTINEL",
        ]
        with receipt._provider_invocation_receipt_scope() as handle:
            with receipt._content_operation(1) as observer:
                observer._invoke("server_rrf", "initial", lambda: object())
        data = handle.receipt()
        self.assertIsNotNone(data)
        for sentinel in sentinels:
            self.assertNotIn(sentinel.encode(), data)  # type: ignore[operator]
            item = value()
            item["private"] = sentinel
            with self.assertRaises(receipt._ReceiptValidationError) as raised:
                receipt._parse_receipt_value(item)
            self.assertNotIn(sentinel, str(raised.exception))

    def test_no_public_export_trigger_or_nonstdlib_dependency(self) -> None:
        self.assertNotIn("provider_invocation", buoy_search.__all__)
        self.assertFalse(hasattr(buoy_search, "provider_invocation_receipt_scope"))
        self.assertEqual(receipt.__all__, ())
        source = Path(receipt.__file__).read_text(encoding="utf-8")
        for prohibited in (
            "os.environ",
            "argparse",
            "telemetry",
            "turbopuffer",
            "requests",
            "urllib",
            "duckdb",
            "open(",
            "Path(",
        ):
            self.assertNotIn(prohibited, source)


if __name__ == "__main__":
    unittest.main()
