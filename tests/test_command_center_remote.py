from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest

from buoy_search.catalog import ROUTING_DIMENSIONS, CardFields, prepare_card
from buoy_search.command_center_local import NamespaceInventory, NamespaceSummary
from buoy_search.command_center_remote import (
    MAX_CANDIDATES,
    MAX_CONTENT_PREVIEW_CHARS,
    MAX_EXPLICIT_NAMESPACES,
    MAX_QUERY_CHARS,
    MAX_REMOTE_SNAPSHOT_NAMESPACES,
    RemoteSnapshotService,
    SearchRequest,
    SearchService,
)
from buoy_search.config import RuntimeConfig
from buoy_search.database_relation import database_document_url
from buoy_search.remote_catalog import (
    REMOTE_CATALOG_NAMESPACE,
    CompatibilityContract,
    ReadMetrics,
    classify_remote_catalog,
)
from buoy_search.retriever import (
    HybridRetriever,
    MultiNamespaceRetrievalResult,
    ProviderCallError,
    RetrievalResult,
    SearchHit,
)

REGION = "gcp-us-central1"
MODEL = "BAAI/bge-small-en-v1.5"
KEY = "tpuf_secret-never-return"


class UnitEmbedder:
    def __init__(self, index: int = 0) -> None:
        self.index = index
        self.calls: list[list[str]] = []

    def encode(self, texts):  # noqa: ANN001 - protocol fake.
        self.calls.append(list(texts))
        vector = [0.0] * ROUTING_DIMENSIONS
        vector[self.index] = 1.0
        return [list(vector) for _ in texts]


def make_card(namespace: str, **overrides: object):  # noqa: ANN201 - test helper.
    fields: dict[str, object] = {
        "namespace": namespace,
        "enabled": True,
        "source_kind": "website",
        "source_uri": f"https://{namespace}.example/",
        "site_id": f"site-{namespace}",
        "title": namespace,
        "summary": f"Knowledge for {namespace}.",
        "aliases": [],
        "tags": ["docs"],
        "semantic_origin": "manual",
        "region": REGION,
        "embedding_model": MODEL,
        "embedding_precision": "float32",
        "plan_schema_version": 1,
        "ranking_mode": "page",
        "ranking_profile": "none",
        "ranking_pool": 20,
        "ranking_aggregation": "max",
    }
    fields.update(overrides)
    return prepare_card(
        CardFields(**fields),  # type: ignore[arg-type]
        embedder=UnitEmbedder(),
        now="2026-07-23T12:00:00+00:00",
    )


def namespace_summary(namespace: str) -> NamespaceSummary:
    return NamespaceSummary(
        namespace=namespace,
        source=None,
        plan_count=1,
        latest_plan_id="plan-one",
        latest_plan_created_at="2026-07-23T12:00:00+00:00",
        applied=False,
        active_rows=0,
        last_apply_id=None,
    )


class FakeLocalInventory:
    def __init__(self, namespaces: list[str]) -> None:
        self.namespaces = namespaces
        self.calls: list[tuple[int, int]] = []

    def list_namespaces(self, *, offset: int = 0, limit: int = 50) -> NamespaceInventory:
        self.calls.append((offset, limit))
        items = [namespace_summary(value) for value in self.namespaces]
        return NamespaceInventory(items[offset : offset + limit], len(items), offset, limit, [])


class FakeRemoteClient:
    def __init__(self, *, live: list[str], cards: list[object]) -> None:
        self.live = live
        self.cards = cards
        self.write_calls = 0

    def write(self, **_kwargs: object) -> object:
        self.write_calls += 1
        raise AssertionError("read-only service attempted a write")


def classified_reader(client: FakeRemoteClient, *, region: str, compatibility: CompatibilityContract):
    assert region == REGION
    return classify_remote_catalog(
        live_namespace_ids=client.live,
        cards=client.cards,  # type: ignore[arg-type]
        compatibility=compatibility,
        metrics=ReadMetrics(2, 1, 2, ({"secret": KEY, "reads": 2},)),
    )


def retrieval_result(namespace: str, *, content: str = "content") -> RetrievalResult:
    return RetrievalResult(
        query="query",
        hits=[
            SearchHit(
                id="hit-one",
                title="Result title",
                url="https://example.test/citation",
                section_path="Result section",
                content=content,
                path="/private/must-not-escape",
                repo_path="/also/private",
                tags=["docs", "python"],
                score_info={"fusion": "server_rrf", "source_rank": 1},
                namespace=namespace,
            )
        ],
        region=REGION,
        namespace=namespace,
        embedding_model=MODEL,
        embedding_precision="float32",
        top_k=5,
        candidates=200,
        doc_kind=None,
        fusion="server_rrf",
        ranking_mode="page",
        ranking_profile="none",
        ranking_pool=20,
        ranking_aggregation="max",
    )


def multi_result(namespaces: list[str]) -> MultiNamespaceRetrievalResult:
    results = [retrieval_result(namespace) for namespace in namespaces]
    hits = []
    for result in results:
        hits.extend(result.hits)
    return MultiNamespaceRetrievalResult(
        query="query",
        hits=hits,
        region=REGION,
        namespaces=namespaces,
        embedding_model=MODEL,
        embedding_precision="float32",
        top_k=5,
        candidates=200,
        namespace_results=results,
    )


class RemoteSnapshotServiceTests(unittest.TestCase):
    def test_clean_import_loads_no_provider_or_embedding_packages(self) -> None:
        source_root = Path(__file__).resolve().parents[1] / "src"
        script = """
import json
import sys
import buoy_search.command_center_remote
watched = [
    "turbopuffer",
    "sentence_transformers",
    "transformers",
    "google.cloud.bigquery",
    "snowflake.connector",
]
print(json.dumps({name: name in sys.modules for name in watched}, sort_keys=True))
"""
        completed = subprocess.run(
            [sys.executable, "-c", script],
            check=True,
            capture_output=True,
            text=True,
            env={"PYTHONPATH": str(source_root)},
        )
        self.assertEqual(set(json.loads(completed.stdout).values()), {False})

    def test_not_checked_is_local_only_and_constructs_no_remote_or_model_objects(self) -> None:
        local = FakeLocalInventory(["local-b", "local-a"])
        service = RemoteSnapshotService(
            local_inventory=local,
            environment={},
            client_factory=lambda **_kwargs: (_ for _ in ()).throw(AssertionError("client constructed")),
            catalog_reader=lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("catalog read")),
        )

        result = service.not_checked()

        self.assertEqual(result.state, "not_checked")
        self.assertFalse(result.credentials_required)
        self.assertFalse(result.api_calls_occurred)
        self.assertFalse(result.writes_occurred)
        self.assertEqual(
            [(item.namespace, item.status, item.live) for item in result.namespaces],
            [("local-a", "not_checked", None), ("local-b", "not_checked", None)],
        )
        self.assertEqual(result.namespace_total, 2)
        self.assertFalse(result.namespaces_truncated)

    def test_local_status_result_is_bounded_and_reports_truncation(self) -> None:
        namespaces = [
            f"namespace-{index:04d}"
            for index in range(MAX_REMOTE_SNAPSHOT_NAMESPACES + 1)
        ]
        service = RemoteSnapshotService(
            local_inventory=FakeLocalInventory(namespaces),
            environment={},
        )

        result = service.not_checked()

        self.assertEqual(len(result.namespaces), MAX_REMOTE_SNAPSHOT_NAMESPACES)
        self.assertEqual(result.namespace_total, MAX_REMOTE_SNAPSHOT_NAMESPACES + 1)
        self.assertTrue(result.namespaces_truncated)

    def test_missing_credentials_is_structured_and_keeps_remote_status_not_checked(self) -> None:
        service = RemoteSnapshotService(
            local_inventory=FakeLocalInventory(["local-only"]),
            environment={},
            client_factory=lambda **_kwargs: (_ for _ in ()).throw(AssertionError("client constructed")),
        )

        result = service.refresh()

        self.assertEqual(result.state, "not_configured")
        self.assertEqual(result.error.code, "remote_credentials_missing")  # type: ignore[union-attr]
        self.assertTrue(result.credentials_required)
        self.assertFalse(result.api_calls_occurred)
        self.assertFalse(result.writes_occurred)
        self.assertEqual(result.namespaces[0].status, "not_checked")

    def test_refresh_combines_existing_classifier_output_with_local_inventory_without_writes(self) -> None:
        cards = [
            make_card("eligible"),
            make_card("disabled", enabled=False),
            make_card("incompatible", embedding_precision="float16"),
            make_card("stale"),
        ]
        client = FakeRemoteClient(
            live=[REMOTE_CATALOG_NAMESPACE, "eligible", "disabled", "incompatible", "missing"],
            cards=cards,
        )
        service = RemoteSnapshotService(
            local_inventory=FakeLocalInventory(["eligible", "local-only"]),
            environment={"TURBOPUFFER_API_KEY": KEY},
            client_factory=lambda **kwargs: client,
            catalog_reader=classified_reader,
        )

        result = service.refresh()

        self.assertEqual(result.state, "ready")
        self.assertTrue(result.api_calls_occurred)
        self.assertFalse(result.writes_occurred)
        self.assertEqual(client.write_calls, 0)
        self.assertEqual(
            {item.namespace: item.status for item in result.namespaces},
            {
                "disabled": "disabled",
                "eligible": "eligible",
                "incompatible": "incompatible",
                "local-only": "local_only",
                "missing": "missing_card",
                "stale": "stale_target",
            },
        )
        eligible = next(item for item in result.namespaces if item.namespace == "eligible")
        self.assertTrue(eligible.local_present)
        self.assertEqual(eligible.title, "eligible")
        self.assertEqual(result.counts["eligible_count"], 1)
        self.assertEqual(result.request_counts, {
            "namespace_list_pages": 2,
            "metadata_requests": 1,
            "card_query_pages": 2,
        })
        self.assertNotIn(KEY, repr(result))
        self.assertNotIn("billing", repr(result))

    def test_provider_failure_is_sanitized_and_returns_no_remote_claims(self) -> None:
        secret_failure = f"Authorization: Bearer {KEY}; /Users/private/catalog"

        def failing_reader(*_args: object, **_kwargs: object) -> object:
            raise RuntimeError(secret_failure)

        service = RemoteSnapshotService(
            local_inventory=FakeLocalInventory(["local"]),
            environment={"TURBOPUFFER_API_KEY": KEY},
            client_factory=lambda **_kwargs: object(),  # type: ignore[arg-type]
            catalog_reader=failing_reader,  # type: ignore[arg-type]
        )
        with self.assertLogs("buoy_search.command_center_remote", level="WARNING") as logs:
            result = service.refresh()

        self.assertEqual(result.state, "error")
        self.assertEqual(result.error.code, "remote_snapshot_failed")  # type: ignore[union-attr]
        self.assertEqual(result.namespaces[0].status, "not_checked")
        self.assertNotIn(KEY, repr(result))
        self.assertNotIn(KEY, "\n".join(logs.output))
        self.assertNotIn("/Users/private", "\n".join(logs.output))


class SearchServiceTests(unittest.TestCase):
    def test_explicit_single_bypasses_catalog_and_route_model_and_uses_namespace_defaults(self) -> None:
        captured: list[tuple[str, object]] = []

        class SingleRetriever:
            def retrieve(self, query: str, options: object) -> RetrievalResult:
                captured.append((query, options))
                return retrieval_result("site-explicit")

        service = SearchService(
            environment={"TURBOPUFFER_API_KEY": KEY},
            client_factory=lambda **_kwargs: (_ for _ in ()).throw(AssertionError("remote catalog client")),
            catalog_reader=lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("catalog read")),
            routing_embedder_factory=lambda: (_ for _ in ()).throw(AssertionError("route model loaded")),
            single_retriever_factory=lambda config: SingleRetriever(),
        )

        result = service.execute(SearchRequest(query="  query  ", namespaces=("site-explicit",)))

        self.assertEqual(result.state, "success")
        self.assertFalse(result.automatic)
        self.assertEqual(result.namespaces, ("site-explicit",))
        self.assertEqual(captured[0][0], "query")
        options = captured[0][1]
        self.assertEqual(options.ranking_mode, "page")
        self.assertEqual(options.ranking_profile, "none")
        self.assertEqual(result.hits[0].namespace, "site-explicit")
        self.assertEqual(result.hits[0].citation, "https://example.test/citation")
        self.assertEqual(result.hits[0].tags, ("docs", "python"))
        self.assertNotIn("/private", repr(result))

    def test_explicit_multi_reuses_multi_retriever_and_returns_no_partial_result_on_failure(self) -> None:
        calls: list[list[str]] = []

        class FailingMultiRetriever:
            def retrieve(self, _query: str, _options: object) -> object:
                raise ProviderCallError(f"second provider failed api_key={KEY} /Users/private")

        def factory(configs):  # noqa: ANN001 - protocol fake.
            calls.append([config.namespace for config in configs])
            return FailingMultiRetriever()

        service = SearchService(
            environment={"TURBOPUFFER_API_KEY": KEY},
            multi_retriever_factory=factory,
        )
        with self.assertLogs("buoy_search.command_center_remote", level="WARNING") as logs:
            result = service.execute(
                SearchRequest(query="query", namespaces=("one", "two"))
            )

        self.assertEqual(calls, [["one", "two"]])
        self.assertEqual(result.state, "error")
        self.assertEqual(result.hits, ())
        self.assertEqual(result.namespaces, ())
        self.assertEqual(result.error.code, "remote_search_failed")  # type: ignore[union-attr]
        self.assertTrue(result.api_calls_occurred)
        self.assertNotIn(KEY, repr(result))
        self.assertNotIn(KEY, "\n".join(logs.output))
        self.assertNotIn("/Users/private", "\n".join(logs.output))

    def test_explicit_multi_success_preserves_order_and_uses_one_multi_path(self) -> None:
        captured: list[tuple[list[str], list[object]]] = []

        class MultiRetriever:
            def __init__(self, configs):  # noqa: ANN001
                self.configs = configs

            def retrieve(self, _query: str, options: list[object]) -> MultiNamespaceRetrievalResult:
                names = [config.namespace for config in self.configs]
                captured.append((names, options))
                return multi_result(names)

        service = SearchService(
            environment={"TURBOPUFFER_API_KEY": KEY},
            multi_retriever_factory=lambda configs: MultiRetriever(configs),
        )
        result = service.execute(
            SearchRequest(
                query="query",
                namespaces=("github-first", "site-second"),
                ranking_pool=25,
            )
        )

        self.assertEqual(result.state, "success")
        self.assertEqual(result.namespaces, ("github-first", "site-second"))
        self.assertEqual(captured[0][0], ["github-first", "site-second"])
        self.assertEqual([option.ranking_mode for option in captured[0][1]], ["file", "page"])
        self.assertEqual([option.ranking_pool for option in captured[0][1]], [25, 25])
        self.assertEqual([hit.namespace for hit in result.hits], ["github-first", "site-second"])

    def test_automatic_reuses_catalog_classifier_hybrid_route_card_settings_and_multi_retriever(self) -> None:
        cards = [
            make_card("alpha", title="alpha", ranking_pool=31),
            make_card("chosen", title="chosen phrase", ranking_pool=47),
        ]
        client = FakeRemoteClient(
            live=[REMOTE_CATALOG_NAMESPACE, "alpha", "chosen"],
            cards=cards,
        )
        route_embedder = UnitEmbedder()
        captured: list[tuple[list[str], list[object]]] = []

        class MultiRetriever:
            def __init__(self, configs):  # noqa: ANN001
                self.configs = configs

            def retrieve(self, _query: str, options: list[object]) -> MultiNamespaceRetrievalResult:
                names = [config.namespace for config in self.configs]
                captured.append((names, options))
                return multi_result(names)

        service = SearchService(
            environment={"TURBOPUFFER_API_KEY": KEY},
            client_factory=lambda **_kwargs: client,
            catalog_reader=classified_reader,
            routing_embedder_factory=lambda: route_embedder,
            single_retriever_factory=lambda _config: (_ for _ in ()).throw(AssertionError("single path")),
            multi_retriever_factory=lambda configs: MultiRetriever(configs),
        )

        result = service.execute(SearchRequest(query="chosen phrase", automatic=True, route_top_k=2))

        self.assertEqual(result.state, "success")
        self.assertTrue(result.automatic)
        self.assertEqual(result.namespaces, ("chosen", "alpha"))
        self.assertEqual(captured[0][0], ["chosen", "alpha"])
        self.assertEqual([option.ranking_pool for option in captured[0][1]], [47, 31])
        self.assertEqual(len(route_embedder.calls), 1)
        self.assertEqual(result.diagnostics["routing"]["strategy"], "hybrid_rrf")  # type: ignore[index]
        self.assertFalse(result.writes_occurred)
        self.assertEqual(client.write_calls, 0)
        self.assertNotIn(KEY, repr(result))

    def test_validation_and_missing_credentials_fail_before_clients_or_models(self) -> None:
        constructions: list[str] = []
        service = SearchService(
            environment={},
            client_factory=lambda **_kwargs: constructions.append("client"),  # type: ignore[arg-type]
            routing_embedder_factory=lambda: constructions.append("route-model"),  # type: ignore[arg-type]
            single_retriever_factory=lambda _config: constructions.append("content-model"),  # type: ignore[arg-type]
        )
        cases = [
            (SearchRequest(query=" "), "invalid_search_request"),
            (SearchRequest(query="x" * (MAX_QUERY_CHARS + 1)), "invalid_search_request"),
            (SearchRequest(query="query", namespaces=(1,)), "invalid_search_request"),  # type: ignore[arg-type]
            (SearchRequest(query="query", automatic=1), "invalid_search_request"),  # type: ignore[arg-type]
            (
                SearchRequest(
                    query="query",
                    namespaces=tuple(f"namespace-{index}" for index in range(MAX_EXPLICIT_NAMESPACES + 1)),
                ),
                "invalid_search_request",
            ),
            (SearchRequest(query="query", namespaces=("one",), automatic=True), "invalid_search_request"),
            (SearchRequest(query="query", automatic=False), "invalid_search_request"),
            (SearchRequest(query="query", candidates=MAX_CANDIDATES + 1, automatic=True), "invalid_search_request"),
            (SearchRequest(query="query", automatic=True), "remote_credentials_missing"),
        ]
        for request, code in cases:
            with self.subTest(code=code, request=request):
                result = service.execute(request)
                self.assertEqual(result.state, "error")
                self.assertEqual(result.error.code, code)  # type: ignore[union-attr]
                self.assertEqual(result.hits, ())
        self.assertEqual(constructions, [])

    def test_provider_call_activity_distinguishes_factory_embedding_and_query_failures(self) -> None:
        cases = (
            (lambda _config: (_ for _ in ()).throw(RuntimeError("local model unavailable")), False),
            (lambda _config: type("EmbeddingFailure", (), {"retrieve": lambda self, *_args: (_ for _ in ()).throw(RuntimeError("embedding failed"))})(), False),
            (lambda _config: type("ProviderFailure", (), {"retrieve": lambda self, *_args: (_ for _ in ()).throw(ProviderCallError("provider failed"))})(), True),
        )
        for factory, expected_calls in cases:
            with self.subTest(expected_calls=expected_calls):
                service = SearchService(
                    environment={"TURBOPUFFER_API_KEY": KEY},
                    single_retriever_factory=factory,
                )
                result = service.execute(SearchRequest(query="query", namespaces=("explicit",)))
                self.assertEqual(result.state, "error")
                self.assertEqual(result.api_calls_occurred, expected_calls)

    def test_post_response_normalization_failure_reports_provider_call_occurred(self) -> None:
        class MalformedNamespace:
            def __init__(self) -> None:
                self.calls = 0

            def multi_query(self, **_kwargs: object) -> dict[str, object]:
                self.calls += 1
                return {"rows": [{"id": "bad", "attributes": {"tags": "not-a-list"}}]}

        namespace = MalformedNamespace()
        service = SearchService(
            environment={"TURBOPUFFER_API_KEY": KEY},
            single_retriever_factory=lambda config: HybridRetriever(
                namespace=namespace,
                embedder=UnitEmbedder(),
                config=config,
            ),
        )

        result = service.execute(SearchRequest(query="query", namespaces=("explicit",)))

        self.assertEqual(result.state, "error")
        self.assertEqual(namespace.calls, 1)
        self.assertTrue(result.api_calls_occurred)
        self.assertEqual(result.error.code, "remote_search_failed")  # type: ignore[union-attr]
        self.assertNotIn("not-a-list", repr(result))

    def test_automatic_client_construction_failure_reports_no_provider_call(self) -> None:
        service = SearchService(
            environment={"TURBOPUFFER_API_KEY": KEY},
            client_factory=lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("client setup failed")),
        )
        result = service.execute(SearchRequest(query="query", automatic=True))
        self.assertFalse(result.api_calls_occurred)

    def test_result_content_and_diagnostics_are_bounded_and_private_paths_are_omitted(self) -> None:
        long_content = "x" * (MAX_CONTENT_PREVIEW_CHARS + 50)

        class SingleRetriever:
            def retrieve(self, _query: str, _options: object) -> RetrievalResult:
                result = retrieval_result("explicit", content=long_content)
                result.hits[0].url = "file:///Users/private/secret.txt"
                result.hits[0].score_info = {
                    "ranking": {"group_score": 1.0, "unsafe": "y" * 1_000},
                    "source_ranks": list(range(100)),
                    "provider_payload": KEY,
                }
                return result

        service = SearchService(
            environment={"TURBOPUFFER_API_KEY": KEY},
            single_retriever_factory=lambda _config: SingleRetriever(),
        )
        result = service.execute(SearchRequest(query="query", namespaces=("explicit",)))

        hit = result.hits[0]
        self.assertEqual(len(hit.content_preview), MAX_CONTENT_PREVIEW_CHARS)
        self.assertTrue(hit.content_truncated)
        self.assertEqual(hit.citation, "")
        self.assertEqual(hit.score["ranking"], {"group_score": 1.0})
        self.assertEqual(len(hit.score["source_ranks"]), 50)  # type: ignore[arg-type]
        self.assertNotIn("provider_payload", hit.score)
        self.assertNotIn(KEY, repr(result))
        self.assertNotIn("/private", repr(result))

    def test_explicit_search_preserves_generated_database_citations(self) -> None:
        expected = tuple(
            database_document_url(backend, "gong-calls", "call/1 ? ü")
            for backend in ("duckdb", "bigquery", "snowflake")
        )
        citations = iter(expected)

        class SingleRetriever:
            def retrieve(self, _query: str, _options: object) -> RetrievalResult:
                result = retrieval_result("explicit")
                result.hits[0].url = next(citations)
                return result

        service = SearchService(
            environment={"TURBOPUFFER_API_KEY": KEY},
            single_retriever_factory=lambda _config: SingleRetriever(),
        )
        results = [
            service.execute(SearchRequest(query="query", namespaces=("explicit",)))
            for _ in expected
        ]

        self.assertTrue(all(result.state == "success" and not result.automatic for result in results))
        self.assertEqual(tuple(result.hits[0].citation for result in results), expected)

    def test_citations_strip_fragments_and_reject_path_shaped_document_uris(self) -> None:
        citations = iter((
            "https://example.test/doc?access_token=top-secret#access_token=fragment-secret",
            "file://document-id/Users/private/secret.txt",
            "file://file-csv-notes-abc123/Research%20Notes.csv",
        ))

        class SingleRetriever:
            def retrieve(self, _query: str, _options: object) -> RetrievalResult:
                result = retrieval_result("explicit")
                result.hits[0].url = next(citations)
                return result

        service = SearchService(
            environment={"TURBOPUFFER_API_KEY": KEY},
            single_retriever_factory=lambda _config: SingleRetriever(),
        )
        results = [
            service.execute(SearchRequest(query="query", namespaces=("explicit",)))
            for _ in range(3)
        ]

        self.assertEqual(results[0].hits[0].citation, "https://example.test/doc")
        self.assertEqual(results[1].hits[0].citation, "")
        self.assertEqual(
            results[2].hits[0].citation,
            "file://file-csv-notes-abc123/Research%20Notes.csv",
        )
        self.assertNotIn("top-secret", repr(results))
        self.assertNotIn("fragment-secret", repr(results))
        self.assertNotIn("/Users/private", repr(results))


if __name__ == "__main__":
    unittest.main()
