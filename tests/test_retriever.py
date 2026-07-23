from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from buoy_search.config import RuntimeConfig
from buoy_search.evals import hit_summary
from buoy_search.retriever import (
    RETRIEVAL_ATTRIBUTES,
    HybridRetriever,
    ProviderCallError,
    RetrievalOptions,
    SearchHit,
    bm25_rank_by,
    build_multi_query_subqueries,
    is_source_path,
    rank_hits,
    ranking_defaults_for_namespace,
    ranking_profile_multiplier,
    row_to_hit,
)


class FakeEmbedder:
    def __init__(self) -> None:
        self.texts: list[list[str]] = []

    def encode(self, texts: list[str]) -> list[list[float]]:
        self.texts.append(texts)
        return [[0.1, 0.2, 0.3]]


class PrecisionCapturingEmbedder(FakeEmbedder):
    init_calls: list[tuple[str, str]] = []

    def __init__(self, model_name: str, *, precision: str) -> None:
        super().__init__()
        self.init_calls.append((model_name, precision))


class CapturingNamespace:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def multi_query(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(kwargs)
        return {
            "rows": [
                {
                    "id": "chunk-1",
                    "score": 0.42,
                    "attributes": {
                        "title": "Fetchers basics",
                        "url": "https://scrapling.readthedocs.io/en/latest/fetching/choosing.html",
                        "section_path": "Fetcher choices",
                        "content": "Choose Fetcher, DynamicFetcher, or StealthyFetcher based on the target site.",
                        "path": "fetching/choosing.md",
                        "repo_path": "src/buoy_search/retriever.py",
                        "tags": ["library", "guide"],
                        "doc_kind": "docs",
                        "chunk_index": 3,
                        "vector": [9.0, 9.0],
                    },
                }
            ]
        }


class RerankUnsupportedNamespace:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def multi_query(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(kwargs)
        if "rerank_by" in kwargs:
            raise TypeError("multi_query() got an unexpected keyword argument 'rerank_by'")
        return {
            "results": [
                {
                    "rows": [
                        {"id": "ann-only", "attributes": {"title": "ANN", "content": "semantic match"}},
                        {"id": "both", "attributes": {"title": "Both", "content": "hybrid match"}},
                    ]
                },
                {
                    "rows": [
                        {"id": "both", "attributes": {"title": "Both", "content": "hybrid match"}},
                        {"id": "bm25-only", "attributes": {"title": "BM25", "content": "lexical match"}},
                    ]
                },
            ]
        }


class DuplicateRepoPathNamespace:
    def multi_query(self, **kwargs: object) -> dict[str, object]:
        return {
            "rows": [
                {"id": "docs-1", "attributes": {"title": "Docs", "repo_path": "docs/guide.md", "path": "docs/guide.md"}},
                {"id": "src-1", "attributes": {"title": "Code A", "repo_path": "src/module.py", "path": "src/module.py"}},
                {"id": "src-2", "attributes": {"title": "Code B", "repo_path": "src/module.py", "path": "src/module.py"}},
                {"id": "skill-1", "attributes": {"title": "Skill", "repo_path": ".pi/skills/tool/SKILL.md", "path": ".pi/skills/tool/SKILL.md"}},
                {"id": "test-1", "attributes": {"title": "Tests", "repo_path": "tests/test_module.py", "path": "tests/test_module.py"}},
            ]
        }


class MissingOptionalAttributesNamespace:
    def __init__(self, missing_order: list[str], *, list_requested_attributes: bool = False) -> None:
        self.missing_order = list(missing_order)
        self.list_requested_attributes = list_requested_attributes
        self.calls: list[dict[str, object]] = []

    def multi_query(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(kwargs)
        include_attributes = kwargs["queries"][0]["include_attributes"]
        for attribute in self.missing_order:
            if attribute in include_attributes:
                self.missing_order.remove(attribute)
                context = (
                    f"requested attributes: {include_attributes}; "
                    if self.list_requested_attributes
                    else ""
                )
                raise RuntimeError(
                    f'{context}attribute "{attribute}" not found in schema'
                )
        attributes: dict[str, object] = {
            "title": "Page",
            "url": "https://example.com/docs",
            "content": "Docs",
        }
        if "repo_path" in include_attributes:
            attributes["repo_path"] = "docs/page.md"
        if "tags" in include_attributes:
            attributes["tags"] = ["library", "guide"]
        return {"rows": [{"id": "page-1", "attributes": attributes}]}


class UnrelatedSchemaErrorNamespace:
    def __init__(self, attribute: str = "content") -> None:
        self.attribute = attribute
        self.calls: list[dict[str, object]] = []

    def multi_query(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(kwargs)
        raise RuntimeError(f'attribute "{self.attribute}" not found in schema')


class MalformedTagsNamespace:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def multi_query(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(kwargs)
        return {"rows": [{"id": "bad", "attributes": {"tags": "not-a-list"}}]}


class DuplicateUrlNamespace:
    def multi_query(self, **kwargs: object) -> dict[str, object]:
        return {
            "rows": [
                {"id": "docs-a", "attributes": {"title": "Docs A", "url": "https://example.com/docs#intro", "content": "first docs chunk"}},
                {"id": "docs-b", "attributes": {"title": "Docs B", "url": "https://example.com/docs", "content": "second docs chunk"}},
                {"id": "api-a", "attributes": {"title": "API", "url": "https://example.com/api", "content": "api chunk"}},
            ]
        }


class PageAggregationNamespace:
    def multi_query(self, **kwargs: object) -> dict[str, object]:
        return {
            "rows": [
                {"id": "api-a", "attributes": {"title": "API", "url": "https://example.com/api", "content": "api chunk"}},
                {"id": "docs-a", "attributes": {"title": "Docs A", "url": "https://example.com/docs#one", "content": "first docs chunk"}},
                {"id": "docs-b", "attributes": {"title": "Docs B", "url": "https://example.com/docs#two", "content": "second docs chunk"}},
                {"id": "docs-c", "attributes": {"title": "Docs C", "url": "https://example.com/docs#three", "content": "third docs chunk"}},
            ]
        }


class RetrieverTests(unittest.TestCase):
    def test_from_config_uses_float16_for_query_embedding(self) -> None:
        PrecisionCapturingEmbedder.init_calls.clear()
        namespace = CapturingNamespace()
        config = RuntimeConfig(namespace="site-example-v1", embedding_precision="float16")
        with patch.dict(os.environ, {"TURBOPUFFER_API_KEY": "test-key"}, clear=False), patch(
            "buoy_search.retriever.SentenceTransformerEmbedder", PrecisionCapturingEmbedder
        ), patch("buoy_search.retriever.build_namespace", return_value=namespace):
            retriever = HybridRetriever.from_config(config)
            retriever.retrieve("precision query", RetrievalOptions())

        self.assertEqual(
            PrecisionCapturingEmbedder.init_calls,
            [(config.embedding_model, "float16")],
        )
        self.assertEqual(retriever._embedder.texts, [["precision query"]])

    def test_builds_ann_and_boosted_bm25_subqueries_without_vectors_in_attributes(self) -> None:
        queries = build_multi_query_subqueries(
            query="link extraction",
            query_vector=[0.1, 0.2],
            candidates=25,
            doc_kind="docs",
        )

        self.assertEqual(len(queries), 2)
        self.assertEqual(queries[0]["rank_by"], ("vector", "ANN", [0.1, 0.2]))
        self.assertEqual(queries[1]["rank_by"], bm25_rank_by("link extraction"))
        self.assertEqual(
            bm25_rank_by("link extraction"),
            (
                "Sum",
                [
                    ("Product", 2.0, ("title", "BM25", "link extraction")),
                    ("Product", 1.5, ("section_path", "BM25", "link extraction")),
                    ("content", "BM25", "link extraction"),
                ],
            ),
        )
        for query in queries:
            self.assertEqual(query["limit"], 25)
            self.assertEqual(query["filters"], ("doc_kind", "Eq", "docs"))
            self.assertEqual(query["include_attributes"], RETRIEVAL_ATTRIBUTES)
            self.assertNotIn("vector", query["include_attributes"])

    def test_live_retriever_uses_single_multi_query_with_server_rrf(self) -> None:
        namespace = CapturingNamespace()
        embedder = FakeEmbedder()
        retriever = HybridRetriever(
            namespace=namespace,
            embedder=embedder,
            config=RuntimeConfig(),
        )

        result = retriever.retrieve(
            "How should I choose a Scrapling fetcher?",
            RetrievalOptions(top_k=5, candidates=10),
        )

        self.assertEqual(embedder.texts, [["How should I choose a Scrapling fetcher?"]])
        self.assertEqual(len(namespace.calls), 1)
        self.assertEqual(namespace.calls[0]["rerank_by"], ("RRF",))
        self.assertEqual(len(namespace.calls[0]["queries"]), 2)
        self.assertEqual(result.fusion, "server_rrf")
        self.assertEqual(result.hits[0].title, "Fetchers basics")
        payload = result.to_dict()
        self.assertNotIn("vector", str(payload))
        self.assertEqual(payload["hits"][0]["url"], "https://scrapling.readthedocs.io/en/latest/fetching/choosing.html")
        self.assertEqual(payload["hits"][0]["section_path"], "Fetcher choices")
        self.assertEqual(payload["hits"][0]["repo_path"], "src/buoy_search/retriever.py")
        self.assertEqual(payload["hits"][0]["tags"], ["library", "guide"])
        self.assertEqual(result.hits[0].repo_path, "src/buoy_search/retriever.py")
        self.assertEqual(hit_summary(result.hits[0], 1)["repo_path"], "src/buoy_search/retriever.py")
        self.assertIn("score_info", payload["hits"][0])

    def test_search_hit_and_row_conversion_always_serialize_tags_as_lists(self) -> None:
        tagged = row_to_hit(
            {"id": "tagged", "attributes": {"tags": ["library", "guide"]}}
        )
        empty = row_to_hit({"id": "empty", "attributes": {"tags": []}})
        missing = row_to_hit({"id": "missing", "attributes": {}})

        self.assertEqual(tagged.tags, ["library", "guide"])
        self.assertEqual(tagged.to_dict()["tags"], ["library", "guide"])
        self.assertEqual(empty.to_dict()["tags"], [])
        self.assertEqual(missing.to_dict()["tags"], [])
        self.assertEqual(SearchHit(id="default").to_dict()["tags"], [])

    def test_client_side_rrf_fallback_when_server_rerank_unsupported(self) -> None:
        namespace = RerankUnsupportedNamespace()
        retriever = HybridRetriever(
            namespace=namespace,
            embedder=FakeEmbedder(),
            config=RuntimeConfig(),
        )

        result = retriever.retrieve("hybrid search", RetrievalOptions(top_k=3, candidates=10))

        self.assertEqual(len(namespace.calls), 2)
        self.assertIn("rerank_by", namespace.calls[0])
        self.assertNotIn("rerank_by", namespace.calls[1])
        self.assertEqual(result.fusion, "client_rrf")
        self.assertEqual(result.hits[0].id, "both")
        self.assertEqual(result.hits[0].score_info["fusion"], "client_rrf")
        self.assertIn("ann", result.hits[0].score_info["source_ranks"])
        self.assertIn("bm25", result.hits[0].score_info["source_ranks"])

    def test_database_namespaces_and_verified_source_kinds_use_document_page_defaults(self) -> None:
        document_defaults = ranking_defaults_for_namespace("site-example-v1")
        for namespace in (
            "duckdb-gong-calls-v1",
            "bigquery-gong-calls-v1",
            "snowflake-gong-calls-v1",
            "pdf-notes-v1",
            "file-md-notes-v1",
        ):
            with self.subTest(namespace=namespace):
                self.assertEqual(ranking_defaults_for_namespace(namespace), document_defaults)
        self.assertEqual(
            ranking_defaults_for_namespace(
                "customer-conversations", source_kind="database"
            ),
            document_defaults,
        )
        repo_defaults = {
            "ranking_mode": "file",
            "ranking_profile": "repo_code",
            "ranking_pool": 100,
            "ranking_aggregation": "adaptive_sum_3",
        }
        self.assertEqual(ranking_defaults_for_namespace("github-owner-repo-v1"), repo_defaults)
        self.assertEqual(
            ranking_defaults_for_namespace("site-misleading", source_kind="github_repo"),
            repo_defaults,
        )

    def test_default_file_ranking_deduplicates_repo_paths_and_demotes_process_docs(self) -> None:
        retriever = HybridRetriever(
            namespace=DuplicateRepoPathNamespace(),
            embedder=FakeEmbedder(),
            config=RuntimeConfig(),
        )

        result = retriever.retrieve("repo code", RetrievalOptions(top_k=3, candidates=10, ranking_pool=10))

        self.assertEqual([hit.repo_path for hit in result.hits], ["src/module.py", "tests/test_module.py", "docs/guide.md"])
        self.assertEqual(len({hit.repo_path for hit in result.hits}), 3)
        self.assertEqual(result.ranking_mode, "file")
        self.assertEqual(result.ranking_profile, "repo_code")
        self.assertEqual(result.ranking_aggregation, "adaptive_sum_3")
        self.assertEqual(result.hits[0].score_info["ranking"]["file_hit_count"], 2)

    def test_repo_code_profile_demotes_artifacts_and_boosts_tests(self) -> None:
        self.assertEqual(
            ranking_profile_multiplier(SearchHit(id="memory", repo_path=".10x/evidence/finding.md"), "repo_code"),
            0.20,
        )
        self.assertEqual(
            ranking_profile_multiplier(
                SearchHit(id="nested-agent", repo_path="typer/.agents/skills/typer/SKILL.md"),
                "repo_code",
            ),
            0.20,
        )
        self.assertEqual(
            ranking_profile_multiplier(
                SearchHit(id="eval-data", repo_path="src/buoy_search/data/repo_search_seed_evals.json"),
                "repo_code",
            ),
            0.20,
        )
        self.assertEqual(
            ranking_profile_multiplier(SearchHit(id="test", repo_path="tests/test_retriever.py"), "repo_code"),
            1.10,
        )
        self.assertEqual(
            ranking_profile_multiplier(
                SearchHit(id="example", repo_path="examples/termui/app.py"),
                "repo_code",
                query="Where is terminal prompt behavior implemented?",
            ),
            0.70,
        )
        self.assertAlmostEqual(
            ranking_profile_multiplier(
                SearchHit(id="docs-src", repo_path="docs_src/testing/app01.py"),
                "repo_code",
                query="Where is CliRunner testing support implemented?",
            ),
            0.56,
        )
        self.assertAlmostEqual(
            ranking_profile_multiplier(
                SearchHit(id="tutorial-test", repo_path="tests/test_tutorial/test_typer_app/test_tutorial001.py"),
                "repo_code",
                query="Where is Typer app registration implemented?",
            ),
            0.88,
        )
        self.assertEqual(
            ranking_profile_multiplier(
                SearchHit(id="example", repo_path="examples/termui/app.py"),
                "repo_code",
                query="Where is the terminal prompt example?",
            ),
            1.0,
        )
        self.assertEqual(
            ranking_profile_multiplier(
                SearchHit(id="tutorial-test", repo_path="tests/test_tutorial/test_typer_app/test_tutorial001.py"),
                "repo_code",
                query="Where is the Typer app tutorial?",
            ),
            1.10,
        )
        self.assertEqual(
            ranking_profile_multiplier(
                SearchHit(id="doc", repo_path="doc/en/how-to/logging.rst"),
                "repo_code",
                query="Where is logging capture implemented?",
            ),
            0.80,
        )
        self.assertEqual(
            ranking_profile_multiplier(
                SearchHit(id="doc", repo_path="doc/en/how-to/logging.rst"),
                "repo_code",
                query="Where is logging capture documented?",
            ),
            1.0,
        )
        self.assertAlmostEqual(
            ranking_profile_multiplier(
                SearchHit(id="doc-example", repo_path="doc/en/example/markers.rst"),
                "repo_code",
                query="Where is marker behavior implemented?",
            ),
            0.56,
        )
        self.assertEqual(
            ranking_profile_multiplier(
                SearchHit(id="doc-example", repo_path="doc/en/example/markers.rst"),
                "repo_code",
                query="Where is the marker example?",
            ),
            1.0,
        )
        self.assertAlmostEqual(
            ranking_profile_multiplier(
                SearchHit(id="tutorial", repo_path="docs/tutorial/commands/index.md"),
                "repo_code",
                query="Where is command runtime implemented?",
            ),
            0.84,
        )
        self.assertAlmostEqual(
            ranking_profile_multiplier(
                SearchHit(id="tutorial", repo_path="docs/tutorial/commands/index.md"),
                "repo_code",
                query="Where is the command tutorial?",
            ),
            1.05,
        )
        self.assertAlmostEqual(
            ranking_profile_multiplier(
                SearchHit(id="tutorial", repo_path="docs/tutorial/commands/index.md"),
                "repo_code",
                query="Where is the command example?",
            ),
            1.05,
        )
        self.assertEqual(
            ranking_profile_multiplier(
                SearchHit(id="private-topic", repo_path="typer/_click/core.py"),
                "repo_code",
                query="Where is completion implemented?",
            ),
            0.80,
        )
        self.assertEqual(
            ranking_profile_multiplier(
                SearchHit(id="private-topic", repo_path="typer/_click/core.py"),
                "repo_code",
                query="Where is Click command conversion implemented?",
            ),
            1.20,
        )
        self.assertEqual(
            ranking_profile_multiplier(
                SearchHit(id="private-topic", repo_path="typer/_click/termui.py"),
                "repo_code",
                query="Where are Click terminal prompt helpers implemented?",
            ),
            1.20,
        )
        self.assertEqual(
            ranking_profile_multiplier(
                SearchHit(id="private-package-root", repo_path="src/_pytest/logging.py"),
                "repo_code",
                query="pytest logging capture",
            ),
            1.04,
        )
        self.assertAlmostEqual(
            ranking_profile_multiplier(
                SearchHit(id="internal-match", repo_path="pydantic/_internal/_model_construction.py"),
                "repo_code",
                query="Where does Pydantic collect model fields and construct model classes?",
            ),
            1.04,
        )
        self.assertEqual(
            ranking_profile_multiplier(
                SearchHit(id="internal-miss", repo_path="pydantic/_internal/_model_construction.py"),
                "repo_code",
                query="Where is validation implemented?",
            ),
            0.80,
        )
        self.assertEqual(
            ranking_profile_multiplier(
                SearchHit(id="core", repo_path="typer/core.py"),
                "repo_code",
                query="Where is command group runtime implemented?",
            ),
            1.20,
        )
        self.assertEqual(
            ranking_profile_multiplier(
                SearchHit(id="models", repo_path="typer/models.py"),
                "repo_code",
                query="Where are option and argument parameter metadata defined?",
            ),
            1.20,
        )
        self.assertEqual(
            ranking_profile_multiplier(
                SearchHit(id="utils", repo_path="typer/utils.py"),
                "repo_code",
                query="Where are option and argument parameter metadata defined?",
            ),
            0.75,
        )
        self.assertAlmostEqual(
            ranking_profile_multiplier(
                SearchHit(id="utils", repo_path="src/requests/utils.py"),
                "repo_code",
                query="Where are Requests utility helpers implemented?",
            ),
            1.1648,
        )
        self.assertAlmostEqual(
            ranking_profile_multiplier(
                SearchHit(id="cli", repo_path="src/buoy_search/cli.py"),
                "repo_code",
                query="Where is local planning implemented?",
            ),
            1.008,
        )
        self.assertAlmostEqual(
            ranking_profile_multiplier(
                SearchHit(id="cli", repo_path="src/buoy_search/cli.py"),
                "repo_code",
                query="Where is the CLI command runner implemented?",
            ),
            1.1648,
        )
        self.assertAlmostEqual(
            ranking_profile_multiplier(
                SearchHit(id="fixture", repo_path="crates/ruff/tests/cli/snapshots/lint.snap"),
                "repo_code",
                query="Where is Ruff lint command output implemented?",
            ),
            0.8,
        )
        self.assertEqual(
            ranking_profile_multiplier(
                SearchHit(id="fixture", repo_path="crates/ruff/tests/cli/snapshots/lint.snap"),
                "repo_code",
                query="Where is the lint snapshot fixture?",
            ),
            1.0,
        )
        self.assertEqual(
            ranking_profile_multiplier(
                SearchHit(id="rust-root", repo_path="crates/ruff_python_formatter/src/lib.rs"),
                "repo_code",
                query="Where does Ruff implement Python formatter options?",
            ),
            1.35,
        )
        self.assertAlmostEqual(
            ranking_profile_multiplier(
                SearchHit(id="docs-source", repo_path="docs/source/text.rst"),
                "repo_code",
                query="Where are Text styling spans implemented?",
            ),
            0.728,
        )
        self.assertEqual(
            ranking_profile_multiplier(
                SearchHit(id="dunder-init", repo_path="django/http/__init__.py"),
                "repo_code",
                query="Where are HttpRequest and HttpResponse implemented?",
            ),
            0.82,
        )

    def test_source_path_recognizes_package_roots_without_fixture_noise(self) -> None:
        self.assertTrue(is_source_path("django/http/request.py"))
        self.assertTrue(is_source_path("rich/text.py"))
        self.assertTrue(is_source_path("src/black/resources/black.schema.json"))
        self.assertFalse(is_source_path("docs/source/text.rst"))
        self.assertFalse(is_source_path("tests/test_text.py"))
        self.assertFalse(is_source_path("crates/ruff/tests/cli/snapshots/lint.snap"))

    def test_repo_code_profile_uses_query_intent_for_implementation_vs_experiment_files(self) -> None:
        implementation_query = "Where is the repository search composite eval metric implemented and validated?"

        self.assertGreater(
            ranking_profile_multiplier(
                SearchHit(id="evals", repo_path="src/buoy_search/evals.py"),
                "repo_code",
                query=implementation_query,
            ),
            1.0,
        )
        self.assertLess(
            ranking_profile_multiplier(
                SearchHit(id="autoresearch", repo_path="src/buoy_search/autoresearch.py"),
                "repo_code",
                query=implementation_query,
            ),
            1.0,
        )
        self.assertGreaterEqual(
            ranking_profile_multiplier(
                SearchHit(id="autoresearch", repo_path="src/buoy_search/autoresearch.py"),
                "repo_code",
                query="Where is the autoresearch experiment runner implemented?",
            ),
            1.0,
        )

    def test_repo_code_profile_boosts_precise_source_file_and_symbol_matches(self) -> None:
        self.assertGreater(
            ranking_profile_multiplier(
                SearchHit(
                    id="hooks",
                    repo_path="src/requests/hooks.py",
                    content="def default_hooks(): pass\n\ndef dispatch_hook(key, hooks, hook_data): pass\n",
                ),
                "repo_code",
                query="Where does Requests implement the hook dispatch system for response hooks?",
            ),
            1.0,
        )
        self.assertAlmostEqual(
            ranking_profile_multiplier(
                SearchHit(id="plan-diff", repo_path="src/buoy_search/plan_diff.py", content="def build_plan_diff(): pass"),
                "repo_code",
                query="Which code propagates GitHub repo metadata into plan manifests and chunk rows?",
            ),
            1.12,
        )
        self.assertEqual(
            ranking_profile_multiplier(
                SearchHit(id="test-hooks", repo_path="tests/test_hooks.py", content="def test_dispatch_hook(): pass"),
                "repo_code",
                query="Where does Requests implement the hook dispatch system for response hooks?",
            ),
            1.10,
        )
        self.assertAlmostEqual(
            ranking_profile_multiplier(
                SearchHit(id="docs-api", repo_path="docs/api.rst"),
                "repo_code",
                query="Where are the top-level request API helpers implemented?",
            ),
            0.91,
        )

    def test_file_card_groups_need_precise_path_match_to_outrank_code_hits(self) -> None:
        hits = [
            SearchHit(
                id="generic-card",
                title="tests/test_github_repo.py file metadata",
                section_path="File metadata: tests/testgithubrepo.py",
                repo_path="tests/test_github_repo.py",
                content="Path tokens: tests test github repo Symbols: metadata helper",
            ),
            SearchHit(id="cli-code", repo_path="src/buoy_search/cli.py", content="def plan_crawl_options(): pass"),
            SearchHit(
                id="plan-card",
                title="src/buoy_search/plan_artifacts.py file metadata",
                section_path="File metadata: src/turbosearch/planartifacts.py",
                repo_path="src/buoy_search/plan_artifacts.py",
                content="Path tokens: src turbo search plan artifacts Symbols: build_plan_artifacts build_chunk_record",
            ),
        ]

        ranked = rank_hits(
            hits,
            options=RetrievalOptions(top_k=3, ranking_pool=3),
            query="Which code in plan artifacts propagates GitHub repo metadata into chunk rows?",
        )

        self.assertEqual(ranked[0].repo_path, "src/buoy_search/plan_artifacts.py")

    def test_file_ranking_can_use_symbol_matches_from_later_chunks_in_group(self) -> None:
        hits = [
            SearchHit(id="models", repo_path="src/requests/models.py"),
            SearchHit(id="structures-header", repo_path="src/requests/structures.py"),
            SearchHit(
                id="structures-class",
                repo_path="src/requests/structures.py",
                content="class CaseInsensitiveDict(MutableMapping): pass",
            ),
        ]

        ranked = rank_hits(hits, options=RetrievalOptions(top_k=2, ranking_pool=3), query="CaseInsensitiveDict lookup")

        self.assertEqual(ranked[0].repo_path, "src/requests/structures.py")
        self.assertEqual(ranked[0].score_info["ranking"]["file_hit_count"], 2)

    def test_repo_role_diversification_promotes_matching_test_companion(self) -> None:
        hits = [
            SearchHit(id="utils", repo_path="src/requests/utils.py"),
            SearchHit(id="internal", repo_path="src/requests/_internal_utils.py"),
            SearchHit(id="types", repo_path="src/requests/_types.py"),
            SearchHit(id="sessions", repo_path="src/requests/sessions.py"),
            SearchHit(id="models", repo_path="src/requests/models.py"),
            SearchHit(id="auth", repo_path="src/requests/auth.py"),
            SearchHit(id="adapters", repo_path="src/requests/adapters.py"),
            SearchHit(id="api", repo_path="src/requests/api.py"),
            SearchHit(id="cookies", repo_path="src/requests/cookies.py"),
            SearchHit(id="hooks", repo_path="src/requests/hooks.py"),
            SearchHit(id="compat", repo_path="src/requests/compat.py"),
            SearchHit(id="test-utils", repo_path="tests/test_utils.py"),
        ]

        ranked = rank_hits(
            hits,
            options=RetrievalOptions(top_k=5, ranking_pool=12),
            query="Where are Requests utility helpers implemented for proxies and URI parsing?",
        )

        self.assertEqual(ranked[0].repo_path, "src/requests/utils.py")
        self.assertEqual(ranked[4].repo_path, "tests/test_utils.py")

    def test_repo_role_diversification_promotes_matching_doc_companion(self) -> None:
        hits = [
            SearchHit(id="exceptions", repo_path="src/requests/exceptions.py"),
            SearchHit(id="adapters", repo_path="src/requests/adapters.py"),
            SearchHit(id="init", repo_path="src/requests/__init__.py"),
            SearchHit(id="models", repo_path="src/requests/models.py"),
            SearchHit(id="types", repo_path="src/requests/_types.py"),
            SearchHit(id="cookies", repo_path="src/requests/cookies.py"),
            SearchHit(id="status", repo_path="src/requests/status_codes.py"),
            SearchHit(
                id="docs-api",
                repo_path="docs/api.rst",
                content=(
                    "Exceptions RequestException HTTPError ConnectionError Timeout "
                    "TooManyRedirects RequestsWarning warning classes"
                ),
            ),
        ]

        ranked = rank_hits(
            hits,
            options=RetrievalOptions(top_k=5, ranking_pool=8),
            query="Where are exception and warning classes such as RequestException and HTTPError defined?",
        )

        self.assertEqual(ranked[0].repo_path, "src/requests/exceptions.py")
        self.assertEqual(ranked[4].repo_path, "docs/api.rst")

    def test_chunk_ranking_preserves_raw_fused_order(self) -> None:
        retriever = HybridRetriever(
            namespace=DuplicateRepoPathNamespace(),
            embedder=FakeEmbedder(),
            config=RuntimeConfig(),
        )

        result = retriever.retrieve(
            "repo code",
            RetrievalOptions(top_k=3, candidates=10, ranking_mode="chunk", ranking_profile="none"),
        )

        self.assertEqual([hit.id for hit in result.hits], ["docs-1", "src-1", "src-2"])
        self.assertEqual(result.ranking_mode, "chunk")

    def test_page_ranking_deduplicates_website_urls_only_when_requested(self) -> None:
        retriever = HybridRetriever(
            namespace=DuplicateUrlNamespace(),
            embedder=FakeEmbedder(),
            config=RuntimeConfig(),
        )

        default_result = retriever.retrieve("website docs", RetrievalOptions(top_k=3, candidates=10, ranking_pool=10))
        page_result = retriever.retrieve(
            "website docs",
            RetrievalOptions(top_k=3, candidates=10, ranking_mode="page", ranking_profile="none", ranking_pool=10),
        )

        self.assertEqual([hit.id for hit in default_result.hits], ["docs-a", "docs-b", "api-a"])
        self.assertEqual([hit.id for hit in page_result.hits], ["docs-a", "api-a"])
        self.assertEqual(page_result.ranking_mode, "page")

    def test_page_ranking_still_groups_repo_rows_by_repo_path(self) -> None:
        retriever = HybridRetriever(
            namespace=DuplicateRepoPathNamespace(),
            embedder=FakeEmbedder(),
            config=RuntimeConfig(),
        )

        result = retriever.retrieve(
            "repo code",
            RetrievalOptions(
                top_k=3,
                candidates=10,
                ranking_mode="page",
                ranking_profile="none",
                ranking_pool=10,
                ranking_aggregation="max",
            ),
        )

        self.assertEqual([hit.repo_path for hit in result.hits], ["docs/guide.md", "src/module.py", ".pi/skills/tool/SKILL.md"])
        self.assertEqual(len({hit.repo_path for hit in result.hits}), 3)

    def test_grouping_preserves_representative_hit_tags_and_order(self) -> None:
        hits = [
            SearchHit(
                id="representative",
                url="https://example.com/docs#first",
                tags=["library", "guide"],
            ),
            SearchHit(
                id="other",
                url="https://example.com/docs#second",
                tags=["reference"],
            ),
        ]

        ranked = rank_hits(
            hits,
            options=RetrievalOptions(
                ranking_mode="page",
                ranking_profile="none",
                ranking_aggregation="max",
            ),
        )

        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0].id, "representative")
        self.assertEqual(ranked[0].tags, ["library", "guide"])

    def test_page_ranking_capped_sum_3_rewards_multi_chunk_page_evidence(self) -> None:
        retriever = HybridRetriever(
            namespace=PageAggregationNamespace(),
            embedder=FakeEmbedder(),
            config=RuntimeConfig(),
        )

        default_result = retriever.retrieve(
            "website docs",
            RetrievalOptions(
                top_k=2,
                candidates=10,
                ranking_mode="page",
                ranking_profile="none",
                ranking_pool=4,
                ranking_aggregation="max",
            ),
        )
        aggregated_result = retriever.retrieve(
            "website docs",
            RetrievalOptions(
                top_k=2,
                candidates=10,
                ranking_mode="page",
                ranking_profile="none",
                ranking_pool=4,
                ranking_aggregation="capped_sum_3",
            ),
        )

        self.assertEqual([hit.id for hit in default_result.hits], ["api-a", "docs-a"])
        self.assertEqual([hit.id for hit in aggregated_result.hits], ["docs-a", "api-a"])
        ranking_info = aggregated_result.hits[0].score_info["ranking"]
        self.assertEqual(ranking_info["aggregation"], "capped_sum_3")
        self.assertEqual(ranking_info["group_hit_count"], 3)
        self.assertEqual(ranking_info["source_ranks"], [2, 3, 4])

    def test_adaptive_sum_3_adds_small_bonus_for_close_same_file_chunks(self) -> None:
        retriever = HybridRetriever(
            namespace=PageAggregationNamespace(),
            embedder=FakeEmbedder(),
            config=RuntimeConfig(),
        )

        result = retriever.retrieve(
            "website docs",
            RetrievalOptions(
                top_k=2,
                candidates=10,
                ranking_mode="page",
                ranking_profile="none",
                ranking_pool=4,
                ranking_aggregation="adaptive_sum_3",
            ),
        )

        self.assertEqual([hit.id for hit in result.hits], ["docs-a", "api-a"])
        ranking_info = result.hits[0].score_info["ranking"]
        self.assertEqual(ranking_info["aggregation"], "adaptive_sum_3")
        self.assertEqual(ranking_info["group_hit_count"], 3)
        self.assertLess(ranking_info["group_score"], 0.02)

    def test_invalid_ranking_aggregation_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "ranking_aggregation"):
            RetrievalOptions(ranking_aggregation="sum")

    def test_capped_sum_3_preserves_repo_path_grouping(self) -> None:
        retriever = HybridRetriever(
            namespace=DuplicateRepoPathNamespace(),
            embedder=FakeEmbedder(),
            config=RuntimeConfig(),
        )

        result = retriever.retrieve(
            "repo code",
            RetrievalOptions(
                top_k=3,
                candidates=10,
                ranking_mode="page",
                ranking_profile="none",
                ranking_pool=10,
                ranking_aggregation="capped_sum_3",
            ),
        )

        self.assertEqual(result.hits[0].repo_path, "src/module.py")
        self.assertEqual(len({hit.repo_path for hit in result.hits}), 3)

    def test_live_retriever_bounded_optional_schema_fallback_in_either_order(self) -> None:
        cases = [
            (["tags"], [(True, True), (True, False)], "docs/page.md", []),
            (["repo_path"], [(True, True), (False, True)], "", ["library", "guide"]),
            (
                ["tags", "repo_path"],
                [(True, True), (True, False), (False, False)],
                "",
                [],
            ),
            (
                ["repo_path", "tags"],
                [(True, True), (False, True), (False, False)],
                "",
                [],
            ),
        ]
        for missing_order, expected_attempts, expected_repo_path, expected_tags in cases:
            with self.subTest(missing_order=missing_order):
                namespace = MissingOptionalAttributesNamespace(missing_order)
                retriever = HybridRetriever(
                    namespace=namespace,
                    embedder=FakeEmbedder(),
                    config=RuntimeConfig(),
                )

                result = retriever.retrieve(
                    "website docs", RetrievalOptions(top_k=1, candidates=10)
                )

                attempts: list[tuple[bool, bool]] = []
                for call in namespace.calls:
                    query_attributes = [
                        query["include_attributes"] for query in call["queries"]
                    ]
                    self.assertEqual(query_attributes[0], query_attributes[1])
                    attempts.append(
                        (
                            "repo_path" in query_attributes[0],
                            "tags" in query_attributes[0],
                        )
                    )
                self.assertEqual(attempts, expected_attempts)
                self.assertEqual(result.hits[0].repo_path, expected_repo_path)
                self.assertEqual(result.hits[0].tags, expected_tags)

    def test_live_retriever_omits_only_diagnostic_attribute_when_request_is_listed(self) -> None:
        cases = [
            (
                ["tags", "repo_path"],
                [(True, True), (True, False), (False, False)],
            ),
            (
                ["repo_path", "tags"],
                [(True, True), (False, True), (False, False)],
            ),
        ]
        for missing_order, expected_attempts in cases:
            with self.subTest(missing_order=missing_order):
                namespace = MissingOptionalAttributesNamespace(
                    missing_order,
                    list_requested_attributes=True,
                )
                retriever = HybridRetriever(
                    namespace=namespace,
                    embedder=FakeEmbedder(),
                    config=RuntimeConfig(),
                )

                retriever.retrieve(
                    "website docs", RetrievalOptions(top_k=1, candidates=10)
                )

                attempts = [
                    (
                        "repo_path" in call["queries"][0]["include_attributes"],
                        "tags" in call["queries"][0]["include_attributes"],
                    )
                    for call in namespace.calls
                ]
                self.assertEqual(attempts, expected_attempts)

    def test_live_retriever_does_not_fallback_for_unrelated_errors(self) -> None:
        for attribute in ("content", "repo_tags"):
            with self.subTest(attribute=attribute):
                namespace = UnrelatedSchemaErrorNamespace(attribute)
                retriever = HybridRetriever(
                    namespace=namespace,
                    embedder=FakeEmbedder(),
                    config=RuntimeConfig(),
                )

                with self.assertRaisesRegex(RuntimeError, attribute):
                    retriever.retrieve(
                        "website docs", RetrievalOptions(top_k=1, candidates=10)
                    )

                self.assertEqual(len(namespace.calls), 1)

    def test_live_retriever_marks_post_response_normalization_failure_as_provider_call(self) -> None:
        namespace = MalformedTagsNamespace()
        retriever = HybridRetriever(
            namespace=namespace,
            embedder=FakeEmbedder(),
            config=RuntimeConfig(),
        )

        with self.assertRaisesRegex(ProviderCallError, "tags must be a list of strings"):
            retriever.retrieve("website docs", RetrievalOptions(top_k=1, candidates=10))

        self.assertEqual(len(namespace.calls), 1)


if __name__ == "__main__":
    unittest.main()
