from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stderr, redirect_stdout
from contextvars import ContextVar
from datetime import datetime, timedelta
from io import StringIO
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import threading
import textwrap
import unittest
from unittest.mock import patch

import duckdb
from opentelemetry import propagate, trace as otel_trace
import portalocker

from buoy_search import telemetry as telemetry_module
from buoy_search.config import RuntimeConfig
from buoy_search.retriever import (
    EvidenceRouteContext,
    HybridRetriever,
    MultiNamespaceRetriever,
    ProviderCallError,
    RetrievalOptions,
)
from buoy_search.telemetry import (
    QUERY_EMBED_SPAN_NAME,
    WIDENED_EVENT_NAME,
    copied_context_callable,
    local_telemetry_enabled,
    retrieval_trace,
    telemetry_span,
    telemetry_paths,
)


class RecordingEmbedder:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def encode(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        return [[0.1, 0.2, 0.3]]


class StaticNamespace:
    def __init__(
        self,
        rows: list[dict[str, object]] | None = None,
        *,
        barrier: threading.Barrier | None = None,
        error: BaseException | None = None,
    ) -> None:
        self._rows = list(rows or [])
        self._barrier = barrier
        self._error = error
        self.calls = 0

    def multi_query(self, **_kwargs: object) -> dict[str, object]:
        self.calls += 1
        if self._barrier is not None:
            self._barrier.wait(timeout=5)
        if self._error is not None:
            raise self._error
        return {"rows": list(self._rows)}


class FixedReranker:
    def score(self, _query: str, passages: list[str]) -> list[float]:
        return [float(len(passages) - index) for index in range(len(passages))]


class AmbientInspectingNamespace(StaticNamespace):
    def __init__(self, rows: list[dict[str, object]]) -> None:
        super().__init__(rows)
        self.ambient_span_is_valid: bool | None = None
        self.injected_carrier: dict[str, str] | None = None

    def multi_query(self, **kwargs: object) -> dict[str, object]:
        self.ambient_span_is_valid = (
            otel_trace.get_current_span().get_span_context().is_valid
        )
        carrier: dict[str, str] = {}
        propagate.inject(carrier)
        self.injected_carrier = carrier
        return super().multi_query(**kwargs)


class CollectDecision:
    status = "unassessed"
    is_weak = None

    def to_dict(self) -> dict[str, object]:
        return {"status": self.status}


class CollectAssessor:
    mode = "collect"

    def assess(self, **_kwargs: object) -> CollectDecision:
        return CollectDecision()


def _row(
    row_id: str,
    *,
    title: str = "Title",
    url: str = "https://example.test/page",
    content: str = "Useful content",
    path: str = "docs/page.md",
) -> dict[str, object]:
    return {
        "id": row_id,
        "attributes": {
            "title": title,
            "url": url,
            "section_path": "Section",
            "content": content,
            "path": path,
            "repo_path": path,
            "tags": ["documentation"],
        },
    }


class LocalRetrievalTelemetryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.home = Path(self._temporary.name)
        self._home_patch = patch(
            "buoy_search.local_paths.Path.home",
            return_value=self.home,
        )
        self._environment_patch = patch.dict(os.environ, {}, clear=True)
        self._home_patch.start()
        self._environment_patch.start()

    def tearDown(self) -> None:
        self._environment_patch.stop()
        self._home_patch.stop()
        self._temporary.cleanup()

    def enable_telemetry(self) -> None:
        os.environ["BUOY_TELEMETRY"] = "local"

    def single_retriever(
        self,
        namespace: StaticNamespace | None = None,
        *,
        config: RuntimeConfig | None = None,
    ) -> HybridRetriever:
        return HybridRetriever(
            namespace=namespace or StaticNamespace([_row("one")]),
            embedder=RecordingEmbedder(),
            config=config or RuntimeConfig(namespace="test-namespace"),
        )

    def multi_retriever(
        self,
        namespaces: list[StaticNamespace],
        *,
        namespace_names: list[str] | None = None,
    ) -> MultiNamespaceRetriever:
        names = namespace_names or [
            f"test-namespace-{index}" for index in range(len(namespaces))
        ]
        embedder = RecordingEmbedder()
        retrievers = [
            HybridRetriever(
                namespace=namespace,
                embedder=embedder,
                config=RuntimeConfig(namespace=name),
            )
            for namespace, name in zip(namespaces, names, strict=True)
        ]
        return MultiNamespaceRetriever(
            retrievers=retrievers,
            embedder=embedder,
            reranker_loader=FixedReranker,
        )

    @staticmethod
    def options(count: int = 1) -> list[RetrievalOptions]:
        return [
            RetrievalOptions(
                top_k=3,
                candidates=12,
                ranking_mode="chunk",
                ranking_profile="none",
            )
            for _ in range(count)
        ]

    def test_disabled_and_global_otel_disable_create_no_telemetry_files(self) -> None:
        for value in ("local", "LOCAL", " local", "local "):
            with self.subTest(buoy_value=value):
                self.assertTrue(
                    local_telemetry_enabled({"BUOY_TELEMETRY": value})
                )
        for value in ("", "true"):
            with self.subTest(disabled_buoy_value=value):
                self.assertFalse(
                    local_telemetry_enabled({"BUOY_TELEMETRY": value})
                )
        self.assertFalse(
            local_telemetry_enabled(
                {"BUOY_TELEMETRY": "local", "OTEL_SDK_DISABLED": "TRUE"}
            )
        )
        variants = (
            {},
            {"BUOY_TELEMETRY": "true"},
            {"BUOY_TELEMETRY": "local", "OTEL_SDK_DISABLED": "true"},
        )
        for environment in variants:
            with self.subTest(environment=environment):
                os.environ.clear()
                os.environ.update(environment)
                result = self.single_retriever().retrieve(
                    "query",
                    self.options()[0],
                )
                self.assertEqual([hit.id for hit in result.hits], ["one"])
                self.assertFalse(local_telemetry_enabled())
                self.assertFalse((self.home / ".buoy").exists())

    def test_opt_in_writes_private_duckdb_schema_and_useful_rows(self) -> None:
        self.enable_telemetry()

        result = self.single_retriever().retrieve(
            "  useful query  ",
            self.options()[0],
        )

        self.assertEqual(result.query, "useful query")
        paths = telemetry_paths()
        self.assertEqual(
            paths.database_path,
            self.home / ".buoy" / "telemetry" / "telemetry.duckdb",
        )
        self.assertTrue(paths.database_path.is_file())
        with duckdb.connect(str(paths.database_path), read_only=True) as connection:
            objects = set(
                connection.execute(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'main'
                    """
                ).fetchall()
            )
            self.assertEqual(
                objects,
                {
                    ("telemetry_metadata",),
                    ("trace_runs",),
                    ("spans",),
                    ("span_events",),
                    ("retrieval_runs_v1",),
                    ("retrieval_stage_latency_v1",),
                },
            )
            self.assertEqual(
                connection.execute(
                    "SELECT singleton, schema_version FROM telemetry_metadata"
                ).fetchall(),
                [(True, 1)],
            )
            run = connection.execute(
                """
                SELECT
                    retrieval_mode,
                    outcome,
                    hit_count,
                    namespace_count,
                    initial_fanout,
                    final_fanout,
                    failure_count,
                    incomplete,
                    widened,
                    embedding_model,
                    embedding_precision,
                    top_k,
                    candidates,
                    observation_schema_version,
                    duration_ms
                FROM retrieval_runs_v1
                """
            ).fetchone()
            self.assertIsNotNone(run)
            assert run is not None
            self.assertEqual(
                run[:-1],
                (
                    "explicit_single",
                    "success",
                    1,
                    1,
                    1,
                    1,
                    0,
                    False,
                    False,
                    "BAAI/bge-small-en-v1.5",
                    "float32",
                    3,
                    12,
                    1,
                ),
            )
            self.assertGreaterEqual(run[-1], 0.0)
            spans = connection.execute(
                """
                SELECT name, status_code, duration_ms
                FROM spans
                ORDER BY started_at, name
                """
            ).fetchall()
            self.assertEqual(
                {name for name, _status, _duration in spans},
                {"buoy.retrieve", "buoy.query.embed", "buoy.namespace.query"},
            )
            self.assertTrue(
                all(status == "OK" and duration >= 0 for _name, status, duration in spans)
            )
            self.assertEqual(
                connection.execute(
                    "SELECT count(*) FROM retrieval_stage_latency_v1"
                ).fetchone(),
                (2,),
            )
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(paths.directory.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(paths.database_path.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(paths.lock_path.stat().st_mode), 0o600)

    def test_privacy_allowlist_drops_queries_content_locations_ids_and_errors(self) -> None:
        self.enable_telemetry()
        query_secret = "QUERY_SENTINEL_40f2ad"
        namespace_secret = "NAMESPACE_SENTINEL_7a1fd8"
        model_secret = "MODEL_PATH_SENTINEL_911bd2"
        precision_secret = "PRECISION_SENTINEL_04262c"
        content_secret = "CONTENT_SENTINEL_f4eb80"
        url_secret = "URL_SENTINEL_1a830d"
        path_secret = "PATH_SENTINEL_06ac77"
        id_secret = "ID_SENTINEL_86ee3f"
        raw_error_secret = "RAW_PROVIDER_ERROR_SENTINEL_f85024"
        injected_secret = "INJECTED_ATTRIBUTE_SENTINEL_f4a6c3"
        credential_secret = "CREDENTIAL_SENTINEL_3859f1"
        command_arg_secret = "COMMAND_ARG_SENTINEL_aec48d"
        os.environ["TURBOPUFFER_API_KEY"] = credential_secret
        config = RuntimeConfig(
            namespace=namespace_secret,
            embedding_model=model_secret,
            embedding_precision=precision_secret,
        )
        retriever = self.single_retriever(
            StaticNamespace(
                [
                    _row(
                        id_secret,
                        title=content_secret,
                        url=f"https://example.test/{url_secret}",
                        content=content_secret,
                        path=f"private/{path_secret}.md",
                    )
                ]
            ),
            config=config,
        )

        with patch.object(sys, "argv", ["buoy", command_arg_secret]):
            result = retriever.retrieve(query_secret, self.options()[0])
        self.assertEqual(result.hits[0].id, id_secret)
        with self.assertRaises(ProviderCallError):
            self.single_retriever(
                StaticNamespace(error=RuntimeError(raw_error_secret)),
                config=config,
            ).retrieve(query_secret, self.options()[0])

        with retrieval_trace(
            mode="explicit_single",
            embedding_model=model_secret,
            embedding_precision=precision_secret,
            top_k=1,
            candidates=1,
            namespace_count=1,
            initial_fanout=1,
            routing_selection_reason=injected_secret,
        ) as root_span:
            root_span.set_attribute("private.query", injected_secret)
            root_span.set_attribute("buoy.retrieval.mode", injected_secret)
            root_span.add_event(
                f"private.{injected_secret}",
                {"private.query": injected_secret},
            )
            root_span.add_event(
                WIDENED_EVENT_NAME,
                {"private.query": injected_secret},
            )
            root_span.set_attributes(
                {
                    "buoy.retrieval.outcome": "success",
                    "buoy.retrieval.hit_count": 0,
                }
            )
            root_span.mark_ok()

        paths = telemetry_paths()
        with duckdb.connect(str(paths.database_path), read_only=True) as connection:
            persisted = []
            for table_name in (
                "telemetry_metadata",
                "trace_runs",
                "spans",
                "span_events",
            ):
                persisted.extend(connection.execute(f"SELECT * FROM {table_name}").fetchall())
            encoded = json.dumps(persisted, default=str, sort_keys=True)
            custom_labels = connection.execute(
                """
                SELECT DISTINCT embedding_model, embedding_precision
                FROM trace_runs
                """
            ).fetchall()
        for sentinel in (
            query_secret,
            namespace_secret,
            model_secret,
            precision_secret,
            content_secret,
            url_secret,
            path_secret,
            id_secret,
            raw_error_secret,
            injected_secret,
            credential_secret,
            command_arg_secret,
        ):
            with self.subTest(sentinel=sentinel):
                self.assertNotIn(sentinel, encoded)
        self.assertEqual(custom_labels, [("custom", "custom")])

    def test_parallel_namespace_spans_keep_the_retrieval_root_parent(self) -> None:
        self.enable_telemetry()
        barrier = threading.Barrier(2)
        retriever = self.multi_retriever(
            [
                StaticNamespace(
                    [
                        _row(
                            "one",
                            url="https://example.test/one",
                            content="First content",
                            path="docs/one.md",
                        )
                    ],
                    barrier=barrier,
                ),
                StaticNamespace(
                    [
                        _row(
                            "two",
                            url="https://example.test/two",
                            content="Second content",
                            path="docs/two.md",
                        )
                    ],
                    barrier=barrier,
                ),
            ]
        )

        result = retriever.retrieve("parallel query", self.options(2))

        self.assertEqual(len(result.hits), 2)
        with duckdb.connect(
            str(telemetry_paths().database_path),
            read_only=True,
        ) as connection:
            trace_id, root_span_id = connection.execute(
                "SELECT trace_id, root_span_id FROM trace_runs"
            ).fetchone()
            namespace_spans = connection.execute(
                """
                SELECT trace_id, span_id, parent_span_id, attributes
                FROM spans
                WHERE name = 'buoy.namespace.query'
                ORDER BY span_id
                """
            ).fetchall()
        self.assertEqual(len(namespace_spans), 2)
        self.assertEqual({row[0] for row in namespace_spans}, {trace_id})
        self.assertEqual({row[2] for row in namespace_spans}, {root_span_id})
        self.assertEqual(len({row[1] for row in namespace_spans}), 2)
        self.assertEqual(
            {json.loads(row[3])["buoy.route.rank"] for row in namespace_spans},
            {1, 2},
        )

    def test_private_trace_never_becomes_ambient_provider_context(self) -> None:
        self.enable_telemetry()
        namespace = AmbientInspectingNamespace([_row("one")])

        result = self.single_retriever(namespace).retrieve(
            "context query",
            self.options()[0],
        )

        self.assertEqual([hit.id for hit in result.hits], ["one"])
        self.assertFalse(namespace.ambient_span_is_valid)
        self.assertIsNotNone(namespace.injected_carrier)
        assert namespace.injected_carrier is not None
        self.assertNotIn("traceparent", namespace.injected_carrier)
        with duckdb.connect(
            str(telemetry_paths().database_path),
            read_only=True,
        ) as connection:
            self.assertEqual(
                connection.execute("SELECT count(*) FROM trace_runs").fetchone(),
                (1,),
            )

    def test_executor_wrapper_never_copies_unrelated_contextvars(self) -> None:
        unrelated: ContextVar[str] = ContextVar(
            "test_unrelated_context",
            default="worker-default",
        )
        caller_token = unrelated.set("caller-secret")
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                disabled_value = executor.submit(
                    copied_context_callable(unrelated.get)
                ).result(timeout=5)
            self.assertEqual(disabled_value, "worker-default")

            self.enable_telemetry()
            with retrieval_trace(
                mode="explicit_single",
                embedding_model="BAAI/bge-small-en-v1.5",
                embedding_precision="float32",
                top_k=1,
                candidates=1,
                namespace_count=1,
                initial_fanout=1,
            ) as root_span:
                def observe_worker_context() -> tuple[str, bool]:
                    observed = unrelated.get()
                    with telemetry_span(QUERY_EMBED_SPAN_NAME) as child_span:
                        enabled = child_span.enabled
                        child_span.mark_ok()
                    return observed, enabled

                with ThreadPoolExecutor(max_workers=1) as executor:
                    enabled_value, child_enabled = executor.submit(
                        copied_context_callable(observe_worker_context)
                    ).result(timeout=5)
                root_span.set_attributes(
                    {
                        "buoy.retrieval.outcome": "success",
                        "buoy.retrieval.hit_count": 0,
                    }
                )
                root_span.mark_ok()
        finally:
            unrelated.reset(caller_token)

        self.assertEqual(enabled_value, "worker-default")
        self.assertTrue(child_enabled)
        with duckdb.connect(
            str(telemetry_paths().database_path),
            read_only=True,
        ) as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT count(*) FROM spans WHERE name = 'buoy.query.embed'"
                ).fetchone(),
                (1,),
            )

    def test_invalid_otel_environment_cannot_break_import_or_retrieval(self) -> None:
        script = textwrap.dedent(
            """
            import buoy_search.telemetry
            from buoy_search.config import RuntimeConfig
            from buoy_search.retriever import HybridRetriever, RetrievalOptions

            class Embedder:
                def encode(self, _texts):
                    return [[0.1, 0.2, 0.3]]

            class Namespace:
                def multi_query(self, **_kwargs):
                    return {
                        "rows": [
                            {
                                "id": "one",
                                "attributes": {
                                    "title": "Title",
                                    "url": "https://example.test/one",
                                    "content": "Content",
                                },
                            }
                        ]
                    }

            result = HybridRetriever(
                namespace=Namespace(),
                embedder=Embedder(),
                config=RuntimeConfig(namespace="test"),
            ).retrieve(
                "query",
                RetrievalOptions(ranking_mode="chunk", ranking_profile="none"),
            )
            assert [hit.id for hit in result.hits] == ["one"]
            """
        )
        environment = dict(os.environ)
        environment.update(
            {
                "HOME": str(self.home),
                "BUOY_TELEMETRY": "local",
                "OTEL_SDK_DISABLED": "not-a-boolean",
                "OTEL_TRACES_SAMPLER": "not-a-sampler",
                "OTEL_ATTRIBUTE_COUNT_LIMIT": "not-an-integer",
                "OTEL_SPAN_EVENT_COUNT_LIMIT": "also-not-an-integer",
            }
        )

        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=Path(__file__).resolve().parents[1],
            env=environment,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

        self.assertEqual(
            completed.returncode,
            0,
            msg=f"stdout={completed.stdout!r} stderr={completed.stderr!r}",
        )
        self.assertEqual(completed.stdout, "")
        self.assertEqual(completed.stderr, "")
        self.assertTrue(
            (self.home / ".buoy" / "telemetry" / "telemetry.duckdb").is_file()
        )

        sdk_failure_home = self.home / "sdk-import-failure"
        sdk_failure_environment = dict(environment)
        sdk_failure_environment.update(
            {
                "HOME": str(sdk_failure_home),
                "OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT": "not-an-integer",
            }
        )
        sdk_failure = subprocess.run(
            [sys.executable, "-c", script],
            cwd=Path(__file__).resolve().parents[1],
            env=sdk_failure_environment,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(
            sdk_failure.returncode,
            0,
            msg=(
                f"stdout={sdk_failure.stdout!r} "
                f"stderr={sdk_failure.stderr!r}"
            ),
        )
        self.assertEqual(sdk_failure.stdout, "")
        self.assertEqual(sdk_failure.stderr, "")
        self.assertFalse((sdk_failure_home / ".buoy").exists())

    def test_incompatible_database_is_byte_unchanged_and_best_effort(self) -> None:
        baseline = self.single_retriever().retrieve(
            "same query",
            self.options()[0],
        ).to_dict()
        self.enable_telemetry()
        paths = telemetry_paths()
        paths.directory.mkdir(parents=True, mode=0o700)
        with duckdb.connect(str(paths.database_path)) as connection:
            connection.execute("CREATE TABLE incompatible(secret VARCHAR)")
            connection.execute("INSERT INTO incompatible VALUES ('owned')")
        before = paths.database_path.read_bytes()
        stdout = StringIO()
        stderr = StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            observed = (
                self.single_retriever()
                .retrieve("same query", self.options()[0])
                .to_dict()
            )

        self.assertEqual(observed, baseline)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(paths.database_path.read_bytes(), before)
        with duckdb.connect(str(paths.database_path), read_only=True) as connection:
            self.assertEqual(
                connection.execute("SELECT * FROM incompatible").fetchall(),
                [("owned",)],
            )

    def test_counterfeit_exact_layout_view_and_digest_cannot_authorize_append(
        self,
    ) -> None:
        self.enable_telemetry()
        baseline = self.single_retriever().retrieve(
            "first query",
            self.options()[0],
        ).to_dict()
        paths = telemetry_paths()
        with duckdb.connect(str(paths.database_path)) as connection:
            connection.execute("DROP VIEW retrieval_stage_latency_v1")
            connection.execute("DROP VIEW retrieval_runs_v1")
            connection.execute(
                """
                CREATE VIEW retrieval_runs_v1 AS
                    SELECT *
                    FROM trace_runs
                    WHERE false
                """
            )
            connection.execute(telemetry_module._STAGE_VIEW_DDL)
            counterfeit_digests = telemetry_module._view_sql_digests(
                connection
            )
            connection.execute(
                """
                UPDATE telemetry_metadata
                SET runs_view_sha256 = ?, stage_view_sha256 = ?
                """,
                (
                    counterfeit_digests["retrieval_runs_v1"],
                    counterfeit_digests["retrieval_stage_latency_v1"],
                ),
            )
            before_count = connection.execute(
                "SELECT count(*) FROM trace_runs"
            ).fetchone()
        self.assertNotEqual(
            counterfeit_digests,
            telemetry_module._expected_view_sql_digests(),
        )
        stdout = StringIO()
        stderr = StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            observed = self.single_retriever().retrieve(
                "first query",
                self.options()[0],
            ).to_dict()

        self.assertEqual(observed, baseline)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")
        with duckdb.connect(str(paths.database_path), read_only=True) as connection:
            self.assertEqual(
                connection.execute("SELECT count(*) FROM trace_runs").fetchone(),
                before_count,
            )
            self.assertEqual(
                connection.execute(
                    """
                    SELECT runs_view_sha256, stage_view_sha256
                    FROM telemetry_metadata
                    """
                ).fetchone(),
                (
                    counterfeit_digests["retrieval_runs_v1"],
                    counterfeit_digests["retrieval_stage_latency_v1"],
                ),
            )

    def test_persisted_catalog_shadow_macros_cannot_redirect_validation(
        self,
    ) -> None:
        self.enable_telemetry()
        self.single_retriever().retrieve("first query", self.options()[0])
        paths = telemetry_paths()
        shadow_macros = (
            "CREATE MACRO current_database() "
            "AS error('shadow current_database invoked')",
            "CREATE MACRO duckdb_tables() AS TABLE "
            "SELECT error('shadow duckdb_tables invoked') AS poisoned",
            "CREATE MACRO duckdb_views() AS TABLE "
            "SELECT error('shadow duckdb_views invoked') AS poisoned",
            "CREATE MACRO duckdb_columns() AS TABLE "
            "SELECT error('shadow duckdb_columns invoked') AS poisoned",
            "CREATE MACRO pragma_table_info(name) AS TABLE "
            "SELECT error('shadow pragma_table_info invoked') AS poisoned",
        )
        with duckdb.connect(str(paths.database_path)) as connection:
            for statement in shadow_macros:
                connection.execute(statement)

        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = self.single_retriever().retrieve(
                "second query",
                self.options()[0],
            )

        self.assertEqual([hit.id for hit in result.hits], ["one"])
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")
        with duckdb.connect(str(paths.database_path), read_only=True) as connection:
            self.assertEqual(
                connection.execute("SELECT count(*) FROM trace_runs").fetchone(),
                (2,),
            )
            persisted_names = {
                str(name)
                for (name,) in connection.execute(
                    """
                    SELECT function_name
                    FROM system.duckdb_functions()
                    WHERE function_name IN (
                        'current_database',
                        'duckdb_tables',
                        'duckdb_views',
                        'duckdb_columns',
                        'pragma_table_info'
                    )
                      AND function_type IN ('macro', 'table_macro')
                    """
                ).fetchall()
            }
        self.assertEqual(
            persisted_names,
            {
                "current_database",
                "duckdb_tables",
                "duckdb_views",
                "duckdb_columns",
                "pragma_table_info",
            },
        )

    def test_external_file_view_validation_does_not_bind_removed_path(self) -> None:
        self.enable_telemetry()
        self.single_retriever().retrieve("first query", self.options()[0])
        paths = telemetry_paths()
        external_path = paths.directory / "REMOVED_EXTERNAL_SENTINEL.parquet"
        escaped_external_path = str(external_path).replace("'", "''")
        with duckdb.connect(str(paths.database_path)) as connection:
            connection.execute(
                f"COPY trace_runs TO '{escaped_external_path}' (FORMAT PARQUET)"
            )
            connection.execute("DROP VIEW retrieval_stage_latency_v1")
            connection.execute("DROP VIEW retrieval_runs_v1")
            connection.execute(
                f"""
                CREATE VIEW retrieval_runs_v1 AS
                    SELECT * FROM read_parquet('{escaped_external_path}')
                """
            )
            connection.execute(telemetry_module._STAGE_VIEW_DDL)
        external_path.unlink()
        self.assertFalse(external_path.exists())

        with telemetry_module._connect_database(
            paths.database_path,
            read_only=True,
        ) as connection:
            with self.assertRaisesRegex(ValueError, "incompatible") as raised:
                telemetry_module._validate_schema(connection)

        message = str(raised.exception)
        self.assertNotIn(str(external_path), message)
        self.assertNotIn("I/O", message)
        self.assertNotIn("IO Error", message)

    def test_non_utc_duckdb_timezone_preserves_controlled_utc_epoch(self) -> None:
        self.enable_telemetry()
        controlled_time_ns = 1_704_067_200_123_456_789
        expected_utc_timestamp = datetime(1970, 1, 1) + timedelta(
            microseconds=controlled_time_ns // 1_000
        )
        original_connect = telemetry_module._connect_database

        def connect_in_non_utc_timezone(
            path: Path | str,
            *,
            read_only: bool = False,
        ) -> duckdb.DuckDBPyConnection:
            connection = original_connect(path, read_only=read_only)
            connection.execute("SET TimeZone = 'Pacific/Honolulu'")
            return connection

        with patch.object(
            telemetry_module,
            "_connect_database",
            side_effect=connect_in_non_utc_timezone,
        ), patch.object(
            telemetry_module,
            "_time_ns",
            return_value=controlled_time_ns,
        ):
            result = self.single_retriever().retrieve(
                "time query",
                self.options()[0],
            )

        self.assertEqual([hit.id for hit in result.hits], ["one"])
        with duckdb.connect(
            str(telemetry_paths().database_path),
            read_only=True,
        ) as connection:
            connection.execute("SET TimeZone = 'Pacific/Honolulu'")
            timezone_name = connection.execute(
                "SELECT current_setting('TimeZone')"
            ).fetchone()[0]
            started_at, ended_at, started_epoch_us = connection.execute(
                """
                SELECT started_at, ended_at, epoch_us(started_at)
                FROM trace_runs
                """
            ).fetchone()
        self.assertEqual(timezone_name, "Pacific/Honolulu")
        self.assertEqual(started_at, expected_utc_timestamp)
        self.assertEqual(ended_at, expected_utc_timestamp)
        self.assertEqual(started_epoch_us, controlled_time_ns // 1_000)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks are unavailable")
    def test_symlinked_telemetry_directory_is_rejected_without_side_effects(
        self,
    ) -> None:
        baseline = self.single_retriever().retrieve(
            "same query",
            self.options()[0],
        ).to_dict()
        buoy_home = self.home / ".buoy"
        buoy_home.mkdir(mode=0o700)
        redirected = self.home / "redirected"
        redirected.mkdir(mode=0o700)
        telemetry_directory = buoy_home / "telemetry"
        try:
            telemetry_directory.symlink_to(redirected, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"could not create test symlink: {exc}")
        self.enable_telemetry()
        stdout = StringIO()
        stderr = StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            observed = (
                self.single_retriever()
                .retrieve("same query", self.options()[0])
                .to_dict()
            )

        self.assertEqual(observed, baseline)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")
        self.assertTrue(telemetry_directory.is_symlink())
        self.assertEqual(list(redirected.iterdir()), [])

    def test_failed_first_transaction_publishes_no_database_or_temp_store(
        self,
    ) -> None:
        baseline = self.single_retriever().retrieve(
            "same query",
            self.options()[0],
        ).to_dict()
        self.enable_telemetry()
        stdout = StringIO()
        stderr = StringIO()

        with patch(
            "buoy_search.telemetry._insert_trace_transaction",
            side_effect=RuntimeError("injected transaction failure"),
        ), redirect_stdout(stdout), redirect_stderr(stderr):
            observed = (
                self.single_retriever()
                .retrieve("same query", self.options()[0])
                .to_dict()
            )

        paths = telemetry_paths()
        self.assertEqual(observed, baseline)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")
        self.assertFalse(paths.database_path.exists())
        self.assertEqual(
            [path.name for path in paths.directory.iterdir()],
            [paths.lock_path.name],
        )

    def test_mid_insert_failure_rolls_back_the_complete_trace(self) -> None:
        self.enable_telemetry()
        self.single_retriever().retrieve("query", self.options()[0])
        paths = telemetry_paths()

        with duckdb.connect(str(paths.database_path)) as connection:
            run = connection.execute("SELECT * FROM trace_runs").fetchone()
            span = connection.execute("SELECT * FROM spans LIMIT 1").fetchone()
            self.assertIsNotNone(run)
            self.assertIsNotNone(span)
            assert run is not None
            assert span is not None
            before = tuple(
                connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                for table in ("trace_runs", "spans", "span_events")
            )
            duplicate_trace_id = "f" * 32
            duplicate_span_id = "e" * 16
            duplicate_run = (
                duplicate_trace_id,
                duplicate_span_id,
                *run[2:],
            )
            duplicate_span = (
                duplicate_trace_id,
                duplicate_span_id,
                *span[2:],
            )
            rows = telemetry_module._TraceRows(
                run=duplicate_run,
                spans=(duplicate_span, duplicate_span),
                events=(),
            )

            with self.assertRaises(duckdb.ConstraintException):
                telemetry_module._insert_trace_transaction(
                    connection,
                    rows,
                    initialize=False,
                )
            after = tuple(
                connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                for table in ("trace_runs", "spans", "span_events")
            )

        self.assertEqual(after, before)

    def test_one_success_one_failure_records_partial_outcome(self) -> None:
        self.enable_telemetry()
        retriever = self.multi_retriever(
            [
                StaticNamespace([_row("success")]),
                StaticNamespace(error=RuntimeError("private provider detail")),
            ]
        )

        result = retriever.retrieve("partial query", self.options(2))

        self.assertEqual([hit.id for hit in result.hits], ["success"])
        self.assertTrue(result.incomplete)
        self.assertEqual(len(result.failures), 1)
        with duckdb.connect(
            str(telemetry_paths().database_path),
            read_only=True,
        ) as connection:
            run = connection.execute(
                """
                SELECT outcome, hit_count, failure_count, incomplete, final_fanout
                FROM trace_runs
                """
            ).fetchone()
            namespace_attributes = [
                json.loads(row[0])
                for row in connection.execute(
                    """
                    SELECT attributes
                    FROM spans
                    WHERE name = 'buoy.namespace.query'
                    """
                ).fetchall()
            ]
        self.assertEqual(run, ("partial", 1, 1, True, 2))
        self.assertEqual(
            {attributes["buoy.namespace.status"] for attributes in namespace_attributes},
            {"ok", "failed"},
        )

    def test_automatic_singleton_records_evidence_mode_and_status(self) -> None:
        self.enable_telemetry()
        retriever = self.multi_retriever(
            [StaticNamespace([_row("supported")])]
        )

        result = retriever.retrieve(
            "automatic query",
            self.options(),
            evidence_assessor=CollectAssessor(),
            evidence_route_context=EvidenceRouteContext(
                selection_reason="high_confidence_semantic",
                semantic_score=0.9,
                semantic_margin=0.2,
            ),
        )

        self.assertEqual([hit.id for hit in result.hits], ["supported"])
        self.assertEqual(result.evidence["mode"], "collect")
        self.assertEqual(result.evidence["status"], "unassessed")
        with duckdb.connect(
            str(telemetry_paths().database_path),
            read_only=True,
        ) as connection:
            run = connection.execute(
                """
                SELECT retrieval_mode, outcome, evidence_status, namespace_count
                FROM trace_runs
                """
            ).fetchone()
            evidence_attributes = connection.execute(
                """
                SELECT attributes
                FROM spans
                WHERE name = 'buoy.evidence.assess'
                """
            ).fetchone()
        self.assertEqual(run, ("automatic", "success", "unassessed", 1))
        self.assertIsNotNone(evidence_attributes)
        assert evidence_attributes is not None
        self.assertEqual(
            json.loads(evidence_attributes[0]),
            {
                "buoy.evidence.mode": "collect",
                "buoy.evidence.status": "unassessed",
            },
        )

    def test_empty_top_route_records_widening_event_and_final_fanout(self) -> None:
        self.enable_telemetry()
        first = StaticNamespace()
        second = StaticNamespace([_row("fallback-hit")])
        retriever = self.multi_retriever([first, second])

        result = retriever.retrieve(
            "fallback query",
            self.options(2),
            initial_fanout=1,
        )

        self.assertEqual([hit.id for hit in result.hits], ["fallback-hit"])
        self.assertTrue(result.fallback.widened)
        self.assertEqual(result.fallback.reason, "empty_top1")
        self.assertEqual(first.calls, 1)
        self.assertEqual(second.calls, 1)
        with duckdb.connect(
            str(telemetry_paths().database_path),
            read_only=True,
        ) as connection:
            run = connection.execute(
                """
                SELECT
                    outcome,
                    hit_count,
                    initial_fanout,
                    final_fanout,
                    failure_count,
                    incomplete,
                    widened,
                    fallback_reason
                FROM trace_runs
                """
            ).fetchone()
            event = connection.execute(
                "SELECT name, attributes FROM span_events"
            ).fetchone()
        self.assertEqual(
            run,
            ("success", 1, 1, 2, 0, False, True, "empty_top1"),
        )
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event[0], WIDENED_EVENT_NAME)
        self.assertEqual(
            json.loads(event[1]),
            {
                "buoy.retrieval.fallback_reason": "empty_top1",
                "buoy.retrieval.final_fanout": 2,
                "buoy.retrieval.initial_fanout": 1,
            },
        )

    def test_all_provider_failure_preserves_exception_and_records_redacted_error(self) -> None:
        raw_error = "RAW_FAILURE_DETAIL_SENTINEL_dfe958"
        options = self.options(2)
        disabled = self.multi_retriever(
            [
                StaticNamespace(error=RuntimeError(raw_error)),
                StaticNamespace(error=RuntimeError(raw_error)),
            ]
        )
        with self.assertRaises(ProviderCallError) as disabled_error:
            disabled.retrieve("failing query", options)

        self.enable_telemetry()
        enabled = self.multi_retriever(
            [
                StaticNamespace(error=RuntimeError(raw_error)),
                StaticNamespace(error=RuntimeError(raw_error)),
            ]
        )
        with self.assertRaises(ProviderCallError) as enabled_error:
            enabled.retrieve("failing query", options)

        self.assertEqual(str(enabled_error.exception), str(disabled_error.exception))
        self.assertNotIn(raw_error, str(enabled_error.exception))
        with duckdb.connect(
            str(telemetry_paths().database_path),
            read_only=True,
        ) as connection:
            run = connection.execute(
                """
                SELECT outcome, failure_count, incomplete, hit_count
                FROM trace_runs
                """
            ).fetchone()
            attributes = [
                row[0]
                for row in connection.execute(
                    "SELECT attributes FROM spans"
                ).fetchall()
            ]
        self.assertEqual(run, ("error", 2, True, 0))
        self.assertNotIn(raw_error, json.dumps(attributes))
        self.assertTrue(
            any(
                json.loads(value).get("buoy.error.type") == "provider_call_error"
                for value in attributes
            )
        )

    def test_sink_failure_does_not_change_retrieval_result(self) -> None:
        baseline = self.single_retriever().retrieve(
            "same query",
            self.options()[0],
        ).to_dict()
        self.enable_telemetry()

        stdout = StringIO()
        stderr = StringIO()
        with patch(
            "buoy_search.telemetry._write_trace",
            side_effect=RuntimeError("sink unavailable"),
        ), redirect_stdout(stdout), redirect_stderr(stderr):
            observed = (
                self.single_retriever()
                .retrieve("same query", self.options()[0])
                .to_dict()
            )

        self.assertEqual(observed, baseline)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")
        self.assertFalse(telemetry_paths().database_path.exists())

    def test_lock_contention_drops_trace_without_changing_retrieval_result(self) -> None:
        baseline = self.single_retriever().retrieve(
            "same query",
            self.options()[0],
        ).to_dict()
        self.enable_telemetry()
        paths = telemetry_paths()
        paths.directory.mkdir(parents=True, mode=0o700)

        stdout = StringIO()
        stderr = StringIO()
        with portalocker.Lock(
            str(paths.lock_path),
            mode="a+",
            timeout=0,
            fail_when_locked=True,
        ), redirect_stdout(stdout), redirect_stderr(stderr):
            observed = (
                self.single_retriever()
                .retrieve("same query", self.options()[0])
                .to_dict()
            )

        self.assertEqual(observed, baseline)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")
        self.assertFalse(paths.database_path.exists())


if __name__ == "__main__":
    unittest.main()
