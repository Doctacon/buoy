from __future__ import annotations

import json
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import duckdb
import pytest

from buoy_search.catalog.remote import (
    DISTANCE_METRIC,
    REMOTE_CATALOG_SCHEMA,
    validate_remote_schema,
)
from buoy_search.retrieval.retriever import bm25_rank_by, build_multi_query_subqueries
from buoy_search.storage import DuckDBClient, DuckDBStorageError, NamespaceNotFoundError

UNIT = [1.0] + [0.0] * 383
ORTHOGONAL = [0.0, 1.0] + [0.0] * 382
CONTENT_SCHEMA = {
    "vector": {"type": "[384]f16", "ann": True},
    "title": {"type": "string", "full_text_search": True},
    "section_path": {"type": "string", "full_text_search": True},
    "content": {"type": "string", "full_text_search": True},
    "doc_kind": {"type": "string"},
}


def row(
    row_id: str, vector: list[float] | None = None, **attributes: object
) -> dict[str, object]:
    return {"id": row_id, "vector": list(vector or UNIT), **attributes}


def _process_write(path: str, row_id: str) -> None:
    DuckDBClient(Path(path), timeout=10).namespace("shared").write(
        schema=CONTENT_SCHEMA,
        upsert_rows=[row(row_id, title=row_id, content="concurrent")],
    )


def test_construction_and_absent_reads_do_not_create_files(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "search.duckdb"
    client = DuckDBClient(path)
    namespace = client.namespace("missing")

    assert not path.parent.exists()
    assert client.namespaces() == {"namespaces": []}
    assert not path.parent.exists()
    with pytest.raises(NamespaceNotFoundError) as raised:
        namespace.metadata()
    assert raised.value.status_code == 404
    with pytest.raises(NamespaceNotFoundError) as raised:
        namespace.query()
    assert raised.value.status_code == 404
    assert not path.parent.exists()


def test_schema_write_persists_reopens_and_lists_isolated_namespaces(
    tmp_path: Path,
) -> None:
    path = tmp_path / "search.duckdb"
    client = DuckDBClient(path)
    assert client.namespace("zeta").write(schema=CONTENT_SCHEMA) == {
        "status": "OK",
        "rows_affected": 0,
    }
    client.namespace("alpha").write(
        schema=CONTENT_SCHEMA,
        upsert_rows=[row("alpha-row", title="Alpha", content="first")],
    )
    client.namespace("zeta").write(
        upsert_rows=[row("zeta-row", title="Zeta", content="second")]
    )

    reopened = DuckDBClient(path)
    assert reopened.namespaces(page_size=1) == {
        "namespaces": [{"id": "alpha"}, {"id": "zeta"}]
    }
    assert [
        item["id"] for item in reopened.namespace("alpha").query(top_k=10)["rows"]
    ] == ["alpha-row"]
    assert [
        item["id"] for item in reopened.namespace("zeta").query(top_k=10)["rows"]
    ] == ["zeta-row"]


def test_catalog_metadata_round_trips_exact_schema_and_additive_merge(
    tmp_path: Path,
) -> None:
    namespace = DuckDBClient(tmp_path / "search.duckdb").namespace("catalog")
    namespace.write(schema=REMOTE_CATALOG_SCHEMA, distance_metric=DISTANCE_METRIC)
    metadata = namespace.metadata()

    assert metadata["distance_metric"] == DISTANCE_METRIC
    assert validate_remote_schema(metadata) == REMOTE_CATALOG_SCHEMA
    addition = {"future": {"type": "string", "filterable": False}}
    namespace.write(schema={**REMOTE_CATALOG_SCHEMA, **addition})
    assert namespace.metadata()["schema"]["future"] == addition["future"]
    with pytest.raises(DuckDBStorageError, match="cannot be changed"):
        namespace.write(schema={"future": {"type": "uint", "filterable": False}})


def test_native_cosine_ranking_and_projection_omit_vector_unless_requested(
    tmp_path: Path,
) -> None:
    path = tmp_path / "search.duckdb"
    namespace = DuckDBClient(path).namespace("vectors")
    namespace.write(
        schema=CONTENT_SCHEMA,
        upsert_rows=[
            row("b", ORTHOGONAL, title="far", content="text"),
            row("a", UNIT, title="near", content="text"),
        ],
    )

    response = namespace.query(
        rank_by=("vector", "ANN", UNIT),
        top_k=2,
        include_attributes=["title"],
    )
    assert [item["id"] for item in response["rows"]] == ["a", "b"]
    assert response["rows"][0]["$dist"] == pytest.approx(0.0)
    assert "vector" not in response["rows"][0]
    projected = namespace.query(
        rank_by=("id", "asc"), top_k=1, include_attributes=["vector"]
    )["rows"][0]
    assert projected["vector"] == UNIT

    # Assert that ranking is executed with DuckDB's native fixed-array column.
    with duckdb.connect(str(path), read_only=True) as connection:
        assert connection.execute(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name='buoy_rows' AND column_name='vector'"
        ).fetchone() == ("FLOAT[384]",)


def test_bm25_boosts_title_filters_before_limit_and_multi_query_returns_lists(
    tmp_path: Path,
) -> None:
    namespace = DuckDBClient(tmp_path / "search.duckdb").namespace("content")
    namespace.write(
        schema=CONTENT_SCHEMA,
        upsert_rows=[
            row(
                "a-title", title="anchor", section_path="", content="", doc_kind="docs"
            ),
            row(
                "b-content",
                title="",
                section_path="",
                content="anchor",
                doc_kind="docs",
            ),
            row("c-filtered", title="anchor anchor", content="anchor", doc_kind="blog"),
        ],
    )

    lexical = namespace.query(
        rank_by=bm25_rank_by("anchor"),
        top_k=2,
        filters=("doc_kind", "Eq", "docs"),
        include_attributes=["title", "doc_kind"],
    )["rows"]
    assert [item["id"] for item in lexical] == ["a-title", "b-content"]
    assert all(item["doc_kind"] == "docs" for item in lexical)

    queries = build_multi_query_subqueries(
        query="anchor",
        query_vector=UNIT,
        candidates=2,
        doc_kind="docs",
        include_attributes=["title", "content", "doc_kind"],
    )
    result = namespace.multi_query(queries=queries, rerank_by=("RRF",))
    assert list(result) == ["results"]
    assert len(result["results"]) == 2
    assert all("rows" in item for item in result["results"])


def test_replacement_and_delete_prune_lexical_postings(tmp_path: Path) -> None:
    namespace = DuckDBClient(tmp_path / "search.duckdb").namespace("content")
    namespace.write(
        schema=CONTENT_SCHEMA,
        upsert_rows=[row("item", title="", content="obsolete obsolete")],
    )
    assert namespace.query(rank_by=bm25_rank_by("obsolete"), top_k=5)["rows"]

    namespace.write(upsert_rows=[row("item", title="", content="current")])
    assert namespace.query(rank_by=bm25_rank_by("obsolete"), top_k=5)["rows"] == []
    assert [
        item["id"]
        for item in namespace.query(rank_by=bm25_rank_by("current"), top_k=5)["rows"]
    ] == ["item"]
    assert namespace.write(deletes=["item", "already-missing"])["rows_affected"] == 1
    assert namespace.write(deletes=["item"])["rows_affected"] == 0
    assert namespace.query(rank_by=bm25_rank_by("current"), top_k=5)["rows"] == []


def test_conditional_create_and_revision_update_are_atomic(tmp_path: Path) -> None:
    namespace = DuckDBClient(tmp_path / "search.duckdb").namespace("catalog")
    namespace.write(schema=CONTENT_SCHEMA)
    created = namespace.write(
        upsert_rows=[row("card", card_revision="r1", title="first")],
        upsert_condition=("id", "Eq", None),
        return_affected_ids=True,
    )
    assert created["rows_affected"] == 1
    assert created["upserted_ids"] == ["card"]
    conflict = namespace.write(
        upsert_rows=[row("card", card_revision="bad", title="wrong")],
        upsert_condition=("id", "Eq", None),
        return_affected_ids=True,
    )
    assert conflict == {"status": "OK", "rows_affected": 0, "upserted_ids": None}

    stale = namespace.write(
        upsert_rows=[row("card", card_revision="r2", title="wrong")],
        upsert_condition=("card_revision", "Eq", "stale"),
        return_affected_ids=True,
    )
    assert stale["rows_affected"] == 0
    updated = namespace.write(
        upsert_rows=[row("card", card_revision="r2", title="second")],
        upsert_condition=("card_revision", "Eq", "r1"),
        return_affected_ids=True,
    )
    assert updated["upserted_ids"] == ["card"]
    assert namespace.query(include_attributes=["card_revision", "title"])["rows"] == [
        {"id": "card", "card_revision": "r2", "title": "second"}
    ]


def test_invalid_batch_and_duplicate_ids_leave_existing_state_unchanged(
    tmp_path: Path,
) -> None:
    namespace = DuckDBClient(tmp_path / "search.duckdb").namespace("atomic")
    namespace.write(
        schema=CONTENT_SCHEMA, upsert_rows=[row("original", content="safe")]
    )
    invalid = [row("would-write", content="unsafe"), row("invalid", [0.0] * 384)]
    with pytest.raises(DuckDBStorageError, match="nonzero"):
        namespace.write(upsert_rows=invalid)
    with pytest.raises(DuckDBStorageError, match="finite float32"):
        namespace.write(upsert_rows=[row("overflow", [3.5e38] + [0.0] * 383)])
    with pytest.raises(DuckDBStorageError, match="nonzero"):
        namespace.write(upsert_rows=[row("underflow", [1e-100] + [0.0] * 383)])
    with pytest.raises(DuckDBStorageError, match="duplicate"):
        namespace.write(upsert_rows=[row("duplicate"), row("duplicate")])
    assert namespace.query(top_k=10, include_attributes=["content"])["rows"] == [
        {"id": "original", "content": "safe"}
    ]


def test_json_retains_full_precision_vector_and_arbitrary_attributes(
    tmp_path: Path,
) -> None:
    namespace = DuckDBClient(tmp_path / "search.duckdb").namespace("catalog")
    vector = [0.12345678901234566] + [0.0] * 383
    routing_vector = [0.9876543210123456, -0.12345678901234566]
    namespace.write(
        schema=CONTENT_SCHEMA,
        upsert_rows=[
            row(
                "card",
                vector,
                routing_prototype_vector=routing_vector,
                nested={"kept": [1, "two", None]},
            )
        ],
    )
    result = namespace.query(
        include_attributes=["vector", "routing_prototype_vector", "nested"]
    )["rows"][0]
    assert result["vector"] == vector
    assert result["routing_prototype_vector"] == routing_vector
    assert result["nested"] == {"kept": [1, "two", None]}

    with duckdb.connect(str(namespace._client.path), read_only=True) as connection:
        raw = connection.execute(
            "SELECT attributes_json FROM buoy_rows WHERE id='card'"
        ).fetchone()[0]
    assert json.loads(raw)["vector"] == vector


def test_thread_and_process_writes_are_serialized(tmp_path: Path) -> None:
    path = tmp_path / "search.duckdb"
    DuckDBClient(path).namespace("shared").write(schema=CONTENT_SCHEMA)

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(_process_write, str(path), f"thread-{index}")
            for index in range(4)
        ]
        for future in futures:
            future.result(timeout=20)

    context = multiprocessing.get_context("spawn")
    processes = [
        context.Process(target=_process_write, args=(str(path), f"process-{index}"))
        for index in range(2)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(30)
        assert process.exitcode == 0

    ids = [
        item["id"]
        for item in DuckDBClient(path).namespace("shared").query(top_k=20)["rows"]
    ]
    assert ids == [
        "process-0",
        "process-1",
        "thread-0",
        "thread-1",
        "thread-2",
        "thread-3",
    ]
