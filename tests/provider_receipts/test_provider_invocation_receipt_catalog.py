from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterator
import copy
from concurrent.futures import CancelledError as FuturesCancelledError
from contextlib import contextmanager
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from buoy_search.retrieval import _provider_invocation_receipt as receipt
from buoy_search.catalog.local import CardFields, NamespaceCard, prepare_card
from buoy_search.catalog.remote import (
    CARD_PAGE_SIZE,
    NAMESPACE_PAGE_SIZE,
    REMOTE_CATALOG_NAMESPACE,
    REMOTE_CATALOG_SCHEMA,
    CompatibilityContract,
    RemoteCatalogError,
    card_to_remote_row,
    read_remote_catalog,
)

REGION = "gcp-us-central1"
MODEL = "BAAI/bge-small-en-v1.5"
PRIVACY_SENTINELS = (
    "tpuf_PRIVATE_CREDENTIAL",
    "private-namespace",
    "private-card",
    "private-cursor",
    "private-response",
    "private-billing",
    "private-provider",
    "private-error",
    "private/path",
)


class FixedEmbedder:
    def encode(self, texts: list[str]) -> list[list[float]]:
        return [[1.0] + [0.0] * 383 for _ in texts]


def make_card(namespace: str) -> NamespaceCard:
    return prepare_card(
        CardFields(
            namespace=namespace,
            enabled=True,
            source_kind="website",
            source_uri=f"https://{namespace}.example.com/",
            site_id=namespace,
            title=namespace,
            summary=f"Knowledge for {namespace}.",
            aliases=[],
            tags=["website"],
            semantic_origin="manual",
            region=REGION,
            embedding_model=MODEL,
            embedding_precision="float32",
            plan_schema_version=1,
            ranking_mode="page",
            ranking_profile="none",
            ranking_pool=20,
            ranking_aggregation="max",
            last_plan_id=None,
            last_apply_id=None,
        ),
        embedder=FixedEmbedder(),
        now="2026-08-24T00:00:00+00:00",
    )


def metadata_schema() -> dict[str, object]:
    schema: dict[str, object] = {
        "id": {"type": "string"},
        **copy.deepcopy(REMOTE_CATALOG_SCHEMA),
    }
    for config in schema.values():
        if isinstance(config, dict) and config.get("filterable") is True:
            config.pop("filterable")
    return {"schema": schema}


def interrupted(exc: BaseException) -> bool:
    return isinstance(exc, (asyncio.CancelledError, FuturesCancelledError)) or not isinstance(
        exc, Exception
    )


class RecordingOperation:
    def __init__(self, owner: "RecordingObserver") -> None:
        self.owner = owner

    def _invoke(self, category: str, callback: Callable[[], object]) -> object:
        self.owner.trace.append(f"observe:{category}")
        try:
            result = callback()
        except BaseException as exc:
            outcome = "interrupted" if interrupted(exc) else "error"
            self.owner.counts[category][outcome] += 1
            self.owner.expression_errors.append(exc)
            raise
        self.owner.counts[category]["success"] += 1
        return result


class RecordingObserver:
    def __init__(self, trace: list[str] | None = None) -> None:
        self.trace = trace if trace is not None else []
        self.counts = {
            "namespace_list_page": {"success": 0, "error": 0, "interrupted": 0},
            "metadata": {"success": 0, "error": 0, "interrupted": 0},
            "card_query_page": {"success": 0, "error": 0, "interrupted": 0},
        }
        self.operation_count = 0
        self.outcome: str | None = None
        self.expression_errors: list[BaseException] = []

    @contextmanager
    def _operation(self) -> Iterator[RecordingOperation]:
        self.operation_count += 1
        try:
            yield RecordingOperation(self)
        except BaseException as exc:
            self.outcome = (
                "interrupted"
                if any(counts["interrupted"] for counts in self.counts.values())
                else "interrupted"
                if interrupted(exc)
                else "error"
            )
            raise
        else:
            self.outcome = "success"

    def catalog(self, outcome: str | None = None) -> receipt._Catalog:
        models = {
            category: receipt._OutcomeCounts(**counts)
            for category, counts in self.counts.items()
        }
        return receipt._Catalog(
            outcome=self.outcome if outcome is None else outcome,  # type: ignore[arg-type]
            invocation_count=sum(sum(counts.values()) for counts in self.counts.values()),
            namespace_list_page=models["namespace_list_page"],
            metadata=models["metadata"],
            card_query_page=models["card_query_page"],
        )

    @classmethod
    def aggregate(
        cls,
        *,
        outcome: str,
        namespace: tuple[int, int, int] = (0, 0, 0),
        metadata: tuple[int, int, int] = (0, 0, 0),
        card: tuple[int, int, int] = (0, 0, 0),
    ) -> "RecordingObserver":
        observer = cls()
        observer.outcome = outcome
        for category, values in (
            ("namespace_list_page", namespace),
            ("metadata", metadata),
            ("card_query_page", card),
        ):
            observer.counts[category] = dict(
                zip(("success", "error", "interrupted"), values, strict=True)
            )
        return observer


class NamespacePage:
    def __init__(
        self,
        ids: list[str],
        trace: list[str],
        label: str,
        next_page: "NamespacePage | None" = None,
    ) -> None:
        self.namespaces = [SimpleNamespace(id=value) for value in ids]
        self.trace = trace
        self.label = label
        self.next_page = next_page
        self.next_calls = 0

    def has_next_page(self) -> bool:
        return self.next_page is not None

    def get_next_page(self) -> "NamespacePage | None":
        self.trace.append(f"call:{self.label}:next")
        self.next_calls += 1
        return self.next_page


class FakeResource:
    def __init__(
        self,
        cards: list[NamespaceCard],
        trace: list[str],
        *,
        metadata: object | None = None,
        query_error: BaseException | None = None,
    ) -> None:
        self.cards = cards
        self.trace = trace
        self.metadata_value = metadata if metadata is not None else metadata_schema()
        self.query_error = query_error
        self.metadata_calls: list[dict[str, object]] = []
        self.query_calls: list[dict[str, object]] = []
        self.completed_passes = 0

    def metadata(self, **kwargs: object) -> object:
        self.trace.append("call:metadata")
        self.metadata_calls.append(kwargs)
        if isinstance(self.metadata_value, BaseException):
            raise self.metadata_value
        return self.metadata_value

    def query(self, **kwargs: object) -> object:
        self.trace.append(f"call:card:{self.completed_passes + 1}")
        self.query_calls.append(kwargs)
        if self.query_error is not None:
            raise self.query_error
        rows = sorted(
            (card_to_remote_row(card) for card in self.cards),
            key=lambda row: row["id"],
        )
        filters = kwargs.get("filters")
        if filters is not None:
            rows = [row for row in rows if row["id"] > filters[2]]  # type: ignore[index]
        selected = rows[: int(kwargs["top_k"])]
        if len(selected) < int(kwargs["top_k"]):
            self.completed_passes += 1
        return {
            "rows": selected,
            "billing": {"private-billing": "private-response"},
        }

    def write(self, **kwargs: object) -> object:
        self.trace.append("call:write")
        return {"private-response": kwargs}


class FakeClient:
    def __init__(
        self,
        pages: list[NamespacePage | BaseException],
        resource: FakeResource,
        trace: list[str],
    ) -> None:
        self.pages = list(pages)
        self.resource = resource
        self.trace = trace
        self.namespaces_calls: list[dict[str, object]] = []
        self.namespace_calls: list[str] = []

    def namespaces(self, **kwargs: object) -> object:
        self.trace.append("call:namespaces")
        self.namespaces_calls.append(kwargs)
        page = self.pages.pop(0)
        if isinstance(page, BaseException):
            raise page
        return page

    def namespace(self, namespace: str) -> FakeResource:
        self.trace.append("call:namespace-resource")
        self.namespace_calls.append(namespace)
        return self.resource


def compatibility() -> CompatibilityContract:
    return CompatibilityContract(REGION, MODEL, "float32")


def make_client(
    *,
    cards: list[NamespaceCard] | None = None,
    multipage_namespaces: bool = False,
    metadata: object | None = None,
    query_error: BaseException | None = None,
) -> tuple[FakeClient, FakeResource, list[str]]:
    trace: list[str] = []
    cards = cards or []
    ids = [REMOTE_CATALOG_NAMESPACE, *(card.namespace for card in cards)]
    if multipage_namespaces:
        split = max(1, len(ids) // 2)
        first_tail = NamespacePage(ids[split:], trace, "L1")
        second_tail = NamespacePage(ids[split:], trace, "L2")
        pages = [
            NamespacePage(ids[:split], trace, "L1", first_tail),
            NamespacePage(ids[:split], trace, "L2", second_tail),
        ]
    else:
        pages = [
            NamespacePage(ids, trace, "L1"),
            NamespacePage(ids, trace, "L2"),
        ]
    resource = FakeResource(
        cards,
        trace,
        metadata=metadata,
        query_error=query_error,
    )
    return FakeClient(pages, resource, trace), resource, trace


def validate_catalog(observer: RecordingObserver) -> None:
    receipt._validate_catalog_source_order(observer.catalog())


def invalid_catalog(observer: RecordingObserver) -> bool:
    try:
        validate_catalog(observer)
    except receipt._ReceiptValidationError:
        return True
    return False


class CatalogInvocationInstrumentationTests(unittest.TestCase):
    def test_minimum_read_records_five_and_exact_source_order(self) -> None:
        client, resource, trace = make_client()
        observer = RecordingObserver(trace)

        snapshot = read_remote_catalog(
            client,
            region=REGION,
            compatibility=compatibility(),
            _invocation_observer=observer,  # type: ignore[arg-type]
        )

        self.assertEqual(observer.operation_count, 1)
        self.assertEqual(observer.outcome, "success")
        self.assertEqual(
            observer.counts,
            {
                "namespace_list_page": {"success": 2, "error": 0, "interrupted": 0},
                "metadata": {"success": 1, "error": 0, "interrupted": 0},
                "card_query_page": {"success": 2, "error": 0, "interrupted": 0},
            },
        )
        self.assertEqual(observer.catalog().invocation_count, 5)
        self.assertEqual(snapshot.metrics.namespace_list_pages, 2)
        self.assertEqual(snapshot.metrics.metadata_requests, 1)
        self.assertEqual(snapshot.metrics.card_query_pages, 2)
        self.assertEqual(
            trace,
            [
                "observe:namespace_list_page",
                "call:namespaces",
                "call:namespace-resource",
                "observe:metadata",
                "call:metadata",
                "observe:card_query_page",
                "call:card:1",
                "observe:card_query_page",
                "call:card:2",
                "observe:namespace_list_page",
                "call:namespaces",
            ],
        )
        self.assertEqual(client.namespaces_calls, [{"page_size": NAMESPACE_PAGE_SIZE}] * 2)
        self.assertEqual(client.namespace_calls, [REMOTE_CATALOG_NAMESPACE])
        self.assertEqual(resource.metadata_calls, [{}])
        self.assertTrue(all(call["consistency"] == {"level": "strong"} for call in resource.query_calls))
        validate_catalog(observer)

    def test_multipage_aggregates_preserve_passes_arguments_and_order(self) -> None:
        cards = [make_card(f"site-{index}-v1") for index in range(3)]
        client, resource, trace = make_client(cards=cards, multipage_namespaces=True)
        observer = RecordingObserver(trace)

        with patch("buoy_search.catalog.remote.CARD_PAGE_SIZE", 2):
            snapshot = read_remote_catalog(
                client,
                region=REGION,
                compatibility=compatibility(),
                _invocation_observer=observer,  # type: ignore[arg-type]
            )

        self.assertEqual(snapshot.cards, tuple(cards))
        self.assertEqual(snapshot.metrics.namespace_list_pages, 4)
        self.assertEqual(snapshot.metrics.card_query_pages, 4)
        self.assertEqual(observer.counts["namespace_list_page"]["success"], 4)
        self.assertEqual(observer.counts["metadata"]["success"], 1)
        self.assertEqual(observer.counts["card_query_page"]["success"], 4)
        self.assertEqual(observer.catalog().invocation_count, 9)
        self.assertEqual([call.get("filters") is not None for call in resource.query_calls], [False, True, False, True])
        categories = [item for item in trace if item.startswith("observe:")]
        self.assertEqual(
            categories,
            [
                "observe:namespace_list_page",
                "observe:namespace_list_page",
                "observe:metadata",
                "observe:card_query_page",
                "observe:card_query_page",
                "observe:card_query_page",
                "observe:card_query_page",
                "observe:namespace_list_page",
                "observe:namespace_list_page",
            ],
        )
        validate_catalog(observer)

    def test_success_and_terminal_category_bounds_and_adjacent_overflow(self) -> None:
        valid = [
            RecordingObserver.aggregate(outcome="success", namespace=(2, 0, 0), metadata=(1, 0, 0), card=(2, 0, 0)),
            RecordingObserver.aggregate(outcome="success", namespace=(20_000, 0, 0), metadata=(1, 0, 0), card=(20_000, 0, 0)),
            RecordingObserver.aggregate(outcome="error"),
            RecordingObserver.aggregate(outcome="error", namespace=(0, 1, 0)),
            RecordingObserver.aggregate(outcome="error", namespace=(9_999, 1, 0)),
            RecordingObserver.aggregate(outcome="interrupted", namespace=(10_000, 0, 0), metadata=(0, 0, 1)),
            RecordingObserver.aggregate(outcome="error", namespace=(10_000, 0, 0), metadata=(1, 0, 0), card=(19_999, 1, 0)),
            RecordingObserver.aggregate(outcome="error", namespace=(20_001, 0, 0), metadata=(1, 0, 0), card=(20_000, 0, 0)),
        ]
        invalid = [
            RecordingObserver.aggregate(outcome="success", namespace=(1, 0, 0), metadata=(1, 0, 0), card=(2, 0, 0)),
            RecordingObserver.aggregate(outcome="success", namespace=(20_001, 0, 0), metadata=(1, 0, 0), card=(2, 0, 0)),
            RecordingObserver.aggregate(outcome="success", namespace=(2, 0, 0), metadata=(0, 0, 0), card=(2, 0, 0)),
            RecordingObserver.aggregate(outcome="success", namespace=(2, 0, 0), metadata=(2, 0, 0), card=(2, 0, 0)),
            RecordingObserver.aggregate(outcome="success", namespace=(2, 0, 0), metadata=(1, 0, 0), card=(1, 0, 0)),
            RecordingObserver.aggregate(outcome="success", namespace=(2, 0, 0), metadata=(1, 0, 0), card=(20_001, 0, 0)),
            RecordingObserver.aggregate(outcome="error", namespace=(10_000, 1, 0)),
            RecordingObserver.aggregate(outcome="error", namespace=(10_001, 0, 0), metadata=(0, 1, 0)),
            RecordingObserver.aggregate(outcome="error", namespace=(1, 0, 0), metadata=(1, 0, 0), card=(20_000, 1, 0)),
            RecordingObserver.aggregate(outcome="error", namespace=(20_001, 1, 0), metadata=(1, 0, 0), card=(20_000, 0, 0)),
        ]
        for observer in valid:
            with self.subTest(valid=observer.catalog()):
                validate_catalog(observer)
        for observer in invalid:
            with self.subTest(invalid=observer.catalog()):
                self.assertTrue(invalid_catalog(observer))

    def test_all_ordered_prerequisites_terminal_evidence_and_pass_decomposition(self) -> None:
        impossible = [
            RecordingObserver.aggregate(outcome="error", metadata=(1, 0, 0)),
            RecordingObserver.aggregate(outcome="error", metadata=(1, 0, 0), card=(1, 0, 0)),
            RecordingObserver.aggregate(outcome="error", namespace=(1, 0, 0), card=(1, 0, 0)),
            RecordingObserver.aggregate(outcome="error", namespace=(10_001, 0, 0)),
            RecordingObserver.aggregate(outcome="error", namespace=(10_001, 0, 0), metadata=(1, 0, 0), card=(1, 0, 0)),
            RecordingObserver.aggregate(outcome="error", namespace=(1, 1, 0), metadata=(1, 0, 0)),
            RecordingObserver.aggregate(outcome="error", namespace=(1, 0, 0), metadata=(0, 1, 0), card=(1, 0, 0)),
            RecordingObserver.aggregate(outcome="error", namespace=(1, 1, 0), metadata=(1, 0, 0), card=(2, 1, 0)),
            RecordingObserver.aggregate(outcome="success", namespace=(2, 1, 0), metadata=(1, 0, 0), card=(2, 0, 0)),
            RecordingObserver.aggregate(outcome="interrupted", namespace=(1, 0, 0), metadata=(0, 1, 0)),
            RecordingObserver.aggregate(outcome="error", namespace=(10_001, 0, 0), metadata=(1, 0, 0), card=(0, 1, 0)),
            RecordingObserver.aggregate(outcome="error", namespace=(10_001, 0, 0), metadata=(1, 0, 0), card=(1, 0, 1)),
        ]
        local_valid = [
            RecordingObserver.aggregate(outcome="error"),
            RecordingObserver.aggregate(outcome="interrupted", namespace=(1, 0, 0)),
            RecordingObserver.aggregate(outcome="error", namespace=(10_000, 0, 0)),
            RecordingObserver.aggregate(outcome="error", namespace=(1, 0, 0), metadata=(1, 0, 0)),
            RecordingObserver.aggregate(outcome="interrupted", namespace=(10_000, 0, 0), metadata=(1, 0, 0)),
            RecordingObserver.aggregate(outcome="error", namespace=(1, 0, 0), metadata=(1, 0, 0), card=(1, 0, 0)),
            RecordingObserver.aggregate(outcome="error", namespace=(10_000, 0, 0), metadata=(1, 0, 0), card=(20_000, 0, 0)),
            RecordingObserver.aggregate(outcome="error", namespace=(2, 0, 0), metadata=(1, 0, 0), card=(2, 0, 0)),
        ]
        for observer in impossible:
            with self.subTest(impossible=observer.catalog()):
                self.assertTrue(invalid_catalog(observer))
        for observer in local_valid:
            with self.subTest(local_valid=observer.catalog()):
                validate_catalog(observer)

    def test_40001_success_exact_40002_terminal_and_every_higher_or_other_composition(self) -> None:
        success = RecordingObserver.aggregate(
            outcome="success",
            namespace=(20_000, 0, 0),
            metadata=(1, 0, 0),
            card=(20_000, 0, 0),
        )
        exact_terminal = RecordingObserver.aggregate(
            outcome="error",
            namespace=(20_001, 0, 0),
            metadata=(1, 0, 0),
            card=(20_000, 0, 0),
        )
        validate_catalog(success)
        validate_catalog(exact_terminal)
        self.assertEqual(success.catalog().invocation_count, 40_001)
        self.assertEqual(exact_terminal.catalog().invocation_count, 40_002)

        invalid = [
            RecordingObserver.aggregate(outcome="success", namespace=(20_001, 0, 0), metadata=(1, 0, 0), card=(20_000, 0, 0)),
            RecordingObserver.aggregate(outcome="error", namespace=(20_000, 0, 0), metadata=(1, 0, 0), card=(20_001, 0, 0)),
            RecordingObserver.aggregate(outcome="error", namespace=(20_001, 0, 0), metadata=(1, 0, 0), card=(19_999, 1, 0)),
            RecordingObserver.aggregate(outcome="error", namespace=(20_001, 1, 0), metadata=(1, 0, 0), card=(20_000, 0, 0)),
        ]
        for observer in invalid:
            with self.subTest(observer=observer.catalog()):
                self.assertTrue(invalid_catalog(observer))

    def test_sdk_errors_and_all_interruption_classes_stop_and_keep_identity(self) -> None:
        class CustomControlFlow(BaseException):
            pass

        for exc in (
            asyncio.CancelledError("private-error"),
            FuturesCancelledError("private-error"),
            KeyboardInterrupt("private-error"),
            SystemExit("private-error"),
            GeneratorExit("private-error"),
            CustomControlFlow("private-error"),
        ):
            client, _resource, _trace = make_client()
            client.pages[0] = exc
            observer = RecordingObserver()
            caught = None
            try:
                read_remote_catalog(
                    client,
                    region=REGION,
                    compatibility=compatibility(),
                    _invocation_observer=observer,  # type: ignore[arg-type]
                )
            except BaseException as raised:
                caught = raised
            with self.subTest(exc=type(exc).__name__):
                if isinstance(exc, FuturesCancelledError):
                    self.assertIsInstance(caught, RemoteCatalogError)
                    self.assertEqual(
                        str(caught),
                        "remote routing catalog namespace listing failed (CancelledError)",
                    )
                else:
                    self.assertIs(caught, exc)
                self.assertIs(observer.expression_errors[-1], exc)
                self.assertEqual(observer.outcome, "interrupted")
                self.assertEqual(observer.counts["namespace_list_page"]["interrupted"], 1)
                self.assertEqual(sum(sum(item.values()) for item in observer.counts.values()), 1)
                validate_catalog(observer)

        baseline_client, _resource, _trace = make_client()
        baseline_client.pages[0] = FuturesCancelledError("private-error")
        with self.assertRaises(RemoteCatalogError) as baseline:
            read_remote_catalog(
                baseline_client,
                region=REGION,
                compatibility=compatibility(),
            )
        observed_client, _resource, _trace = make_client()
        observed_client.pages[0] = FuturesCancelledError("private-error")
        with receipt._provider_invocation_receipt_scope() as handle:
            live_observer = handle._catalog_observer()
            assert live_observer is not None
            with self.assertRaises(RemoteCatalogError) as observed:
                read_remote_catalog(
                    observed_client,
                    region=REGION,
                    compatibility=compatibility(),
                    _invocation_observer=live_observer,
                )
        self.assertEqual(type(observed.exception), type(baseline.exception))
        self.assertEqual(str(observed.exception), str(baseline.exception))
        self.assertIsNone(observed.exception.__cause__)
        authoritative = json.loads(handle.receipt() or b"null")
        self.assertEqual(authoritative["catalog"]["outcome"], "interrupted")
        self.assertEqual(authoritative["catalog"]["invocation_count"], 1)
        self.assertEqual(
            authoritative["catalog"]["namespace_list_page"],
            {"success": 0, "error": 0, "interrupted": 1},
        )

        for exc in (ValueError("private-error"), RuntimeError("private-error")):
            client, _resource, _trace = make_client(query_error=exc)
            observer = RecordingObserver()
            with self.subTest(exc=type(exc).__name__), self.assertRaises(RemoteCatalogError) as raised:
                read_remote_catalog(
                    client,
                    region=REGION,
                    compatibility=compatibility(),
                    _invocation_observer=observer,  # type: ignore[arg-type]
                )
            self.assertNotIn("private-error", str(raised.exception))
            self.assertEqual(observer.outcome, "error")
            self.assertEqual(observer.counts["card_query_page"]["error"], 1)
            self.assertEqual(observer.catalog().invocation_count, 3)
            validate_catalog(observer)

        ordinary_client, _resource, _trace = make_client(
            query_error=ValueError("private-error")
        )
        with receipt._provider_invocation_receipt_scope() as ordinary_handle:
            live_observer = ordinary_handle._catalog_observer()
            assert live_observer is not None
            with self.assertRaises(RemoteCatalogError):
                read_remote_catalog(
                    ordinary_client,
                    region=REGION,
                    compatibility=compatibility(),
                    _invocation_observer=live_observer,
                )
        authoritative = json.loads(ordinary_handle.receipt() or b"null")
        self.assertEqual(authoritative["catalog"]["outcome"], "error")
        self.assertEqual(
            authoritative["catalog"]["card_query_page"],
            {"success": 0, "error": 1, "interrupted": 0},
        )

    def test_metadata_expression_error_counts_once_and_stops_before_cards(self) -> None:
        exact = RuntimeError("private-error")
        client, resource, _trace = make_client(metadata=exact)
        observer = RecordingObserver()

        with self.assertRaises(RemoteCatalogError) as raised:
            read_remote_catalog(
                client,
                region=REGION,
                compatibility=compatibility(),
                _invocation_observer=observer,  # type: ignore[arg-type]
            )

        self.assertNotIn("private-error", str(raised.exception))
        self.assertIs(observer.expression_errors[-1], exact)
        self.assertEqual(observer.outcome, "error")
        self.assertEqual(observer.counts["namespace_list_page"]["success"], 1)
        self.assertEqual(observer.counts["metadata"]["error"], 1)
        self.assertEqual(observer.counts["card_query_page"]["success"], 0)
        self.assertEqual(resource.query_calls, [])
        validate_catalog(observer)

    def test_post_return_local_error_and_interruption_do_not_fabricate_call_failure(self) -> None:
        bad_metadata = {"schema": {"private-response": "private-card"}}
        client, _resource, _trace = make_client(metadata=bad_metadata)
        observer = RecordingObserver()
        with self.assertRaises(RemoteCatalogError):
            read_remote_catalog(
                client,
                region=REGION,
                compatibility=compatibility(),
                _invocation_observer=observer,  # type: ignore[arg-type]
            )
        self.assertEqual(observer.outcome, "error")
        self.assertEqual(observer.counts["namespace_list_page"]["success"], 1)
        self.assertEqual(observer.counts["metadata"]["success"], 1)
        self.assertEqual(observer.counts["metadata"]["error"], 0)
        validate_catalog(observer)

        interruption = KeyboardInterrupt("private-error")
        client, _resource, _trace = make_client()
        observer = RecordingObserver()
        caught = None
        with patch("buoy_search.catalog.remote.validate_remote_schema", side_effect=interruption):
            try:
                read_remote_catalog(
                    client,
                    region=REGION,
                    compatibility=compatibility(),
                    _invocation_observer=observer,  # type: ignore[arg-type]
                )
            except BaseException as raised:
                caught = raised
        self.assertIs(caught, interruption)
        self.assertEqual(observer.outcome, "interrupted")
        self.assertEqual(observer.counts["metadata"]["success"], 1)
        self.assertEqual(observer.counts["metadata"]["interrupted"], 0)
        validate_catalog(observer)

    def test_page_bound_failures_happen_after_only_reached_expressions(self) -> None:
        trace: list[str] = []
        tail = NamespacePage(["site-next-v1"], trace, "L1-tail")
        first = NamespacePage([REMOTE_CATALOG_NAMESPACE], trace, "L1", tail)
        resource = FakeResource([], trace)
        client = FakeClient([first], resource, trace)
        observer = RecordingObserver(trace)
        with patch("buoy_search.catalog.remote.MAX_PAGES_PER_PASS", 1):
            with self.assertRaisesRegex(RemoteCatalogError, "exceeded 1 pages"):
                read_remote_catalog(
                    client,
                    region=REGION,
                    compatibility=compatibility(),
                    _invocation_observer=observer,  # type: ignore[arg-type]
                )
        self.assertEqual(observer.counts["namespace_list_page"]["success"], 2)
        self.assertEqual(observer.counts["namespace_list_page"]["error"], 0)
        self.assertEqual(observer.outcome, "error")
        validate_catalog(observer)

        card = make_card("site-bound-v1")
        client, _resource, _trace = make_client(cards=[card])
        observer = RecordingObserver()
        with patch("buoy_search.catalog.remote.CARD_PAGE_SIZE", 1), patch(
            "buoy_search.catalog.remote.MAX_PAGES_PER_PASS", 1
        ):
            with self.assertRaisesRegex(RemoteCatalogError, "card query exceeded 1 pages"):
                read_remote_catalog(
                    client,
                    region=REGION,
                    compatibility=compatibility(),
                    _invocation_observer=observer,  # type: ignore[arg-type]
                )
        self.assertEqual(observer.counts["card_query_page"]["success"], 1)
        self.assertEqual(observer.counts["card_query_page"]["error"], 0)
        self.assertEqual(observer.outcome, "error")
        validate_catalog(observer)

    def test_default_none_active_scope_and_all_existing_callers_remain_unobserved(self) -> None:
        client, _resource, _trace = make_client()
        with receipt._provider_invocation_receipt_scope() as handle:
            snapshot = read_remote_catalog(
                client,
                region=REGION,
                compatibility=compatibility(),
            )
        self.assertEqual(snapshot.metrics.namespace_list_pages, 2)
        data = json.loads(handle.receipt() or b"null")
        self.assertIsNone(data["catalog"]["outcome"])
        self.assertEqual(data["catalog"]["invocation_count"], 0)

        root = Path(__file__).resolve().parents[2]
        for relative in (
            "src/buoy_search/planning/apply.py",
            "src/buoy_search/cli/catalog.py",
            "scripts/evaluate_multi_corpus_retrieval.py",
            "scripts/evaluate_routing_quality.py",
        ):
            source = (root / relative).read_text(encoding="utf-8")
            with self.subTest(relative=relative):
                self.assertNotIn("_invocation_observer", source)
        cli_source = (root / "src/buoy_search/cli/main.py").read_text(encoding="utf-8")
        self.assertEqual(cli_source.count("_invocation_observer"), 1)
        self.assertIn("_invocation_observer=_active_catalog_observer()", cli_source)
        remote_source = (root / "src/buoy_search/catalog/remote.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("_active_ledger", remote_source)
        self.assertNotIn("ContextVar", remote_source)

    def test_observer_faults_preserve_expression_result_exception_and_full_read(self) -> None:
        from buoy_search.catalog.remote import _invoke_catalog_expression

        result = object()

        class FaultBefore:
            def _invoke(self, category: str, callback: Callable[[], object]) -> object:
                raise RuntimeError("observer fault")

        class FaultAfter:
            def _invoke(self, category: str, callback: Callable[[], object]) -> object:
                callback_result = callback()
                self.callback_result = callback_result
                raise RuntimeError("observer fault")

        calls = 0

        def return_result() -> object:
            nonlocal calls
            calls += 1
            return result

        self.assertIs(
            _invoke_catalog_expression(FaultBefore(), "metadata", return_result),  # type: ignore[arg-type]
            result,
        )
        self.assertIs(
            _invoke_catalog_expression(FaultAfter(), "metadata", return_result),  # type: ignore[arg-type]
            result,
        )
        self.assertEqual(calls, 2)

        exact = KeyboardInterrupt("private-error")

        class ReplaceError:
            def _invoke(self, category: str, callback: Callable[[], object]) -> object:
                try:
                    callback()
                except BaseException:
                    raise RuntimeError("observer fault")
                raise AssertionError("unreachable")

        def raise_exact() -> object:
            raise exact

        caught = None
        try:
            _invoke_catalog_expression(ReplaceError(), "metadata", raise_exact)  # type: ignore[arg-type]
        except BaseException as raised:
            caught = raised
        self.assertIs(caught, exact)

        class EnterFault:
            @contextmanager
            def _operation(self) -> Iterator[RecordingOperation]:
                raise RuntimeError("observer enter fault")
                yield RecordingOperation(RecordingObserver())

        class ExitFault:
            @contextmanager
            def _operation(self) -> Iterator[RecordingOperation]:
                yield RecordingOperation(RecordingObserver())
                raise RuntimeError("observer exit fault")

        for observer in (EnterFault(), ExitFault()):
            client, _resource, _trace = make_client()
            snapshot = read_remote_catalog(
                client,
                region=REGION,
                compatibility=compatibility(),
                _invocation_observer=observer,  # type: ignore[arg-type]
            )
            with self.subTest(observer=type(observer).__name__):
                self.assertEqual(snapshot.metrics.namespace_list_pages, 2)
                self.assertEqual(snapshot.metrics.metadata_requests, 1)
                self.assertEqual(snapshot.metrics.card_query_pages, 2)

        client, _resource, _trace = make_client()
        with receipt._provider_invocation_receipt_scope() as enter_handle:
            live_observer = enter_handle._catalog_observer()
            assert live_observer is not None
            live_observer._operation = EnterFault()._operation  # type: ignore[method-assign]
            snapshot = read_remote_catalog(
                client,
                region=REGION,
                compatibility=compatibility(),
                _invocation_observer=live_observer,
            )
        self.assertEqual(snapshot.metrics.card_query_pages, 2)
        self.assertIsNone(enter_handle.receipt())

        client, _resource, _trace = make_client()
        with patch.object(
            receipt._CatalogOperationObserver,
            "_invoke",
            side_effect=RuntimeError("observer invoke fault"),
        ):
            with receipt._provider_invocation_receipt_scope() as invoke_handle:
                live_observer = invoke_handle._catalog_observer()
                assert live_observer is not None
                snapshot = read_remote_catalog(
                    client,
                    region=REGION,
                    compatibility=compatibility(),
                    _invocation_observer=live_observer,
                )
        self.assertEqual(snapshot.metrics.card_query_pages, 2)
        self.assertIsNone(invoke_handle.receipt())

    def test_receipt_bytes_retain_only_fixed_aggregate_categories(self) -> None:
        observer = RecordingObserver.aggregate(
            outcome="success",
            namespace=(2, 0, 0),
            metadata=(1, 0, 0),
            card=(2, 0, 0),
        )
        model = receipt._Receipt(
            receipt_schema_version=1,
            unit="provider_client_invocation",
            content=receipt._Content(0, 0, ()),
            catalog=observer.catalog(),
        )
        encoded = receipt._encode_receipt_model(model)
        self.assertEqual(receipt._decode_receipt(encoded), model)
        self.assertEqual(
            set(json.loads(encoded)["catalog"]),
            {
                "outcome",
                "invocation_count",
                "namespace_list_page",
                "metadata",
                "card_query_page",
            },
        )
        for sentinel in PRIVACY_SENTINELS:
            self.assertNotIn(sentinel.encode(), encoded)


if __name__ == "__main__":
    unittest.main()
