"""Credential-free plan/apply/search acceptance tests using real DuckDB files.

Only model inference is replaced; planning, state, catalog, search, and CLI
serialization cross their real production interfaces. Network is forbidden.
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

import duckdb
import pytest

from buoy_search.cli.main import main
from buoy_search.storage.duckdb import DuckDBClient


class LocalTestEmbedder:
    def __init__(self, *_args, **_kwargs):
        pass

    def encode(self, texts, **_kwargs):
        return [[1.0] + [0.0] * 383 for _ in texts]


class LocalTestReranker:
    def score(self, _query, passages):
        return [10.0 for _ in passages]


def cli(*args: str) -> dict:
    stdout, stderr = StringIO(), StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        result = main([*args, "--json"])
    assert result == 0, stderr.getvalue() or stdout.getvalue()
    return json.loads(stdout.getvalue())


@pytest.fixture
def local_install(tmp_path, monkeypatch):
    home = tmp_path / "buoy"
    monkeypatch.setenv("BUOY_HOME", str(home))
    monkeypatch.setenv("BUOY_TELEMETRY", "off")
    monkeypatch.delenv("BUOY_ALLOW_NETWORK", raising=False)
    for key in ("TURBOPUFFER_API_KEY", "TURBOPUFFER_REGION", "TURBOPUFFER_NAMESPACE"):
        monkeypatch.delenv(key, raising=False)

    def no_network(*_args, **_kwargs):
        raise AssertionError("network access is forbidden in the local workflow")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)
    monkeypatch.setattr(
        "buoy_search.planning.apply.SentenceTransformerEmbedder", LocalTestEmbedder
    )
    monkeypatch.setattr(
        "buoy_search.retrieval.retriever.SentenceTransformerEmbedder", LocalTestEmbedder
    )
    monkeypatch.setattr(
        "buoy_search.catalog.local.load_routing_embedder", LocalTestEmbedder
    )
    monkeypatch.setattr(
        "buoy_search.cli.main.ROUTING_EMBEDDER_FACTORY", LocalTestEmbedder
    )
    monkeypatch.setattr(
        "buoy_search.cli.main.ROUTING_RERANKER_FACTORY", LocalTestReranker
    )
    source = tmp_path / "source.duckdb"
    with duckdb.connect(str(source)) as connection:
        connection.execute(
            "CREATE TABLE documents(document_id VARCHAR, title VARCHAR, content VARCHAR)"
        )
        connection.execute(
            "INSERT INTO documents VALUES ('deploy', 'Deployment', 'Deploy the app with a blue green rollout.'), ('food', 'Lunch', 'The kitchen serves lunch at noon.')"
        )
    return home, source


def plan(source: Path, namespace: str = "work-docs") -> dict:
    return cli(
        "plan",
        str(source),
        "--relation",
        "documents",
        "--source-id",
        "work",
        "--namespace",
        namespace,
    )


def test_fresh_offline_apply_bootstraps_catalog_and_searches_after_reopen(
    local_install,
):
    home, source = local_install
    plan(source)
    assert not (home / "search.duckdb").exists()
    preview = cli("apply", "--dry-run")
    assert preview["credentials_required_for_approved_apply"] is False
    assert not (home / "search.duckdb").exists()
    applied = cli("apply", "--approve")
    assert applied["catalog_registered"] is True
    assert applied["credentials_required"] is False
    assert applied["rows_upserted"] == 2

    explicit = cli(
        "retrieve",
        "blue green rollout",
        "--namespace",
        "work-docs",
        "--no-embedding-worker",
    )
    assert explicit["hits"]
    assert "blue green" in explicit["hits"][0]["content"]
    assert explicit["hits"][0]["url"].startswith("duckdb://work/")
    assert explicit["fusion"] == "client_rrf"
    assert explicit["credentials_required"] is False
    automatic = cli("retrieve", "blue green rollout", "--no-embedding-worker")
    assert automatic["hits"]
    assert automatic["routing"]["selected_cards"][0]["namespace"] == "work-docs"
    catalog = cli("catalog", "list", "--all")
    assert [card["namespace"] for card in catalog["cards"]] == ["work-docs"]

    # A separate interpreter can read the persistent catalog without weights,
    # API keys or an in-process DuckDB connection shared with this test.
    completed = subprocess.run(
        [sys.executable, "-m", "buoy_search", "catalog", "list", "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(completed.stdout)["cards"][0]["namespace"] == "work-docs"
    reopened = DuckDBClient()
    assert len(reopened.namespace("work-docs").query(top_k=20)["rows"]) == 2


def test_incremental_noop_replace_and_exact_stale_deletion(local_install):
    _home, source = local_install
    plan(source)
    cli("apply", "--approve")
    plan(source)
    assert cli("apply", "--approve")["rows_upserted"] == 0

    with duckdb.connect(str(source)) as connection:
        connection.execute("DELETE FROM documents WHERE document_id = 'food'")
        connection.execute(
            "UPDATE documents SET content = 'Deploy with canary validation instead.' WHERE document_id = 'deploy'"
        )
    plan(source)
    applied = cli("apply", "--approve", "--delete-stale")
    assert applied["rows_upserted"] == 1
    assert applied["rows_deleted"] == 2
    rows = DuckDBClient().namespace("work-docs").query(top_k=20)["rows"]
    assert len(rows) == 1
    assert "canary validation" in rows[0]["content"]
    result = cli(
        "retrieve",
        "canary validation",
        "--namespace",
        "work-docs",
        "--no-embedding-worker",
    )
    assert "canary validation" in result["hits"][0]["content"]


def test_buoy_home_isolates_index_and_incremental_state(
    local_install, monkeypatch, tmp_path
):
    first_home, source = local_install
    plan(source)
    cli("apply", "--approve")
    monkeypatch.setenv("BUOY_HOME", str(tmp_path / "second-home"))
    assert DuckDBClient().namespaces() == {"namespaces": []}
    plan(source)
    assert cli("apply", "--approve")["rows_upserted"] == 2
    assert (first_home / "search.duckdb").is_file()


def test_network_sources_fail_before_acquisition_by_default(local_install, monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("source acquisition must not run")

    monkeypatch.setattr("buoy_search.cli.main.crawl_site", forbidden)
    monkeypatch.setattr(
        "buoy_search.planning.planning_service.crawl_source_with_plan", forbidden
    )
    for command in ("plan", "crawl"):
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            source_args = (
                ["https://example.com"]
                if command == "plan"
                else ["--base-url", "https://example.com"]
            )
            result = main([command, *source_args, "--json"])
        assert result == 2
        assert "Network source acquisition is disabled" in stderr.getvalue()
    assert "BUOY_ALLOW_NETWORK=1" in stderr.getvalue()


@pytest.mark.parametrize(
    "damage", ["database_removed", "row_removed", "row_changed", "unexpected_row"]
)
def test_noop_apply_refuses_index_ledger_mismatch(local_install, monkeypatch, damage):
    home, source = local_install
    plan(source)
    cli("apply", "--approve")
    plan(source)  # A genuine zero-upsert delta based on the committed ledger.
    state_files = list((home / "state").rglob("state.duckdb"))
    state_before = {path: path.read_bytes() for path in state_files}
    namespace = DuckDBClient().namespace("work-docs")
    rows = namespace.query(top_k=20)["rows"]
    if damage == "database_removed":
        (home / "search.duckdb").unlink()
    elif damage == "row_removed":
        namespace.write(deletes=[rows[0]["id"]])
    elif damage == "row_changed":
        namespace.write(upsert_rows=[{**rows[0], "embedding_text_hash": "changed"}])
    else:
        namespace.write(upsert_rows=[{**rows[0], "id": "unexpected"}])

    def forbidden(*_args, **_kwargs):
        raise AssertionError(
            "mismatch must fail before inference or catalog registration"
        )

    monkeypatch.setattr(
        "buoy_search.planning.apply.SentenceTransformerEmbedder", forbidden
    )
    monkeypatch.setattr(
        "buoy_search.planning.apply.register_apply_catalog_card", forbidden
    )
    stdout, stderr = StringIO(), StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        result = main(["apply", "--approve", "--json"])
    assert result == 2
    assert "Local index and applied-state baseline do not match" in stderr.getvalue()
    assert all(path.read_bytes() == value for path, value in state_before.items())
    if damage == "database_removed":
        assert not (home / "search.duckdb").exists()


def test_partial_batch_retry_is_allowed_by_index_guard(local_install, monkeypatch):
    from buoy_search.indexing.chunker import DuckDBWriter

    _home, source = local_install
    plan(source)
    original = DuckDBWriter.upsert_rows
    calls = 0

    def fail_second(self, rows):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("injected second batch failure")
        return original(self, rows)

    with monkeypatch.context() as context:
        context.setattr(DuckDBWriter, "upsert_rows", fail_second)
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            assert main(["apply", "--approve", "--batch-size", "1", "--json"]) == 2
    assert len(DuckDBClient().namespace("work-docs").query(top_k=20)["rows"]) == 1
    assert cli("apply", "--approve")["rows_upserted"] == 2


def test_global_namespace_lock_prevents_same_target_apply_from_other_thread(
    local_install,
):
    from concurrent.futures import ThreadPoolExecutor

    from buoy_search.storage.apply_guard import local_namespace_apply_lock
    from buoy_search.storage.duckdb import DuckDBStorageError

    def contend():
        with (
            pytest.raises(DuckDBStorageError, match="another local apply"),
            local_namespace_apply_lock("same-namespace"),
        ):
            raise AssertionError("concurrent namespace lock acquired")

    with local_namespace_apply_lock("same-namespace"):
        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(contend).result(timeout=5)
        with local_namespace_apply_lock("different-namespace"):
            pass
