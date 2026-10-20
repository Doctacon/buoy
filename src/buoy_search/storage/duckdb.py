"""Bounded, extension-free local search storage backed by DuckDB."""

from __future__ import annotations

import json
import math
import os
import re
import struct
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import duckdb
import portalocker

from buoy_search.local_models import BGE_MODEL, BGE_REVISION
from buoy_search.local_paths import default_buoy_home, prepare_default_buoy_home

VECTOR_DIMENSIONS = 384
DISTANCE_METRIC = "cosine_distance"
DEFAULT_LOCK_TIMEOUT = 30.0
_MAX_TOP_K = 10_000
_MAX_QUERIES = 64
_MAX_QUERY_TOKENS = 1_024
_TOKEN_RE = re.compile(r"\w+", re.UNICODE)
# Changing any persisted retrieval semantics requires a fresh index. Inference
# precision is already bound by each reviewed plan's embedding-text hash.
_STORAGE_CONTRACT = json.dumps(
    {
        "vectors": "float32-384-cosine-v1",
        "embedding_model": BGE_MODEL,
        "embedding_revision": BGE_REVISION,
        "tokenizer": "unicode-word-casefold-v1",
        "bm25": "k1=1.2;b=0.75;title=2;section=1.5;content=1;v1",
    },
    sort_keys=True,
    separators=(",", ":"),
)


class DuckDBStorageError(RuntimeError):
    """A local storage contract or database operation failed."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class NamespaceNotFoundError(DuckDBStorageError):
    """The requested local namespace does not exist."""

    def __init__(self, namespace: str) -> None:
        super().__init__(
            f"local namespace {namespace!r} does not exist",
            status_code=404,
        )


class DuckDBClient:
    """A small provider-compatible client for Buoy's local search database.

    Construction and namespace acquisition are inert. The database and its lock
    sidecar are created only by :meth:`DuckDBNamespace.write`.
    """

    def __init__(
        self, path: Path | None = None, *, timeout: float = DEFAULT_LOCK_TIMEOUT
    ) -> None:
        if (
            not isinstance(timeout, (int, float))
            or isinstance(timeout, bool)
            or timeout < 0
        ):
            raise ValueError("timeout must be a non-negative number")
        self.path = (
            default_buoy_home() / "search.duckdb" if path is None else Path(path)
        )
        self.lock_path = self.path.with_name(f"{self.path.name}.lock")
        self.timeout = float(timeout)
        self._uses_default_path = path is None

    def namespace(self, name: str) -> DuckDBNamespace:
        """Return an inert namespace resource without touching the filesystem."""

        return DuckDBNamespace(self, _validate_namespace(name))

    def namespaces(self, *, page_size: int = 1_000, **_: object) -> dict[str, object]:
        """Return every durable namespace ID in deterministic order."""

        if type(page_size) is not int or page_size <= 0:
            raise ValueError("page_size must be a positive integer")
        if not self.path.exists():
            return {"namespaces": []}
        with self._connection(write=False) as connection:
            _validate_database(connection)
            values = connection.execute(
                "SELECT namespace FROM buoy_namespaces ORDER BY namespace"
            ).fetchall()
        return {"namespaces": [{"id": str(value[0])} for value in values]}

    def source_row_fingerprints(self, namespace: str, site_id: str) -> dict[str, str]:
        """Read only source-owned row identities for apply baseline validation.

        Missing storage is an empty index, never permission to skip unchanged
        rows. Callers compare this snapshot while holding the namespace apply lock.
        """
        _validate_namespace(namespace)
        if not self.path.exists():
            return {}
        with self._connection(write=False) as connection:
            _validate_database(connection)
            rows = connection.execute(
                """SELECT id, json_extract_string(attributes_json, '$.embedding_text_hash')
                   FROM buoy_rows WHERE namespace = ?
                   AND json_extract_string(attributes_json, '$.site_id') = ?""",
                [namespace, site_id],
            ).fetchall()
        return {str(row_id): str(fingerprint) for row_id, fingerprint in rows}

    @contextmanager
    def _connection(self, *, write: bool) -> Iterator[duckdb.DuckDBPyConnection]:
        if not write and not self.path.exists():
            raise DuckDBStorageError(
                "local search database does not exist", status_code=404
            )
        if write:
            if self._uses_default_path:
                prepare_default_buoy_home(self.path.parent, require_resolved_home=True)
            self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with portalocker.Lock(
                str(self.lock_path),
                mode="a+",
                timeout=self.timeout,
                fail_when_locked=False,
            ):
                # A reader can have observed the database immediately before a
                # destructive external change. Fail clearly rather than allowing
                # DuckDB to create a replacement from a read operation.
                if not write and not self.path.exists():
                    raise DuckDBStorageError(
                        "local search database does not exist", status_code=404
                    )
                connection: duckdb.DuckDBPyConnection | None = None
                try:
                    connection = duckdb.connect(
                        str(self.path),
                        read_only=not write,
                        config=_safe_duckdb_config(),
                    )
                    yield connection
                finally:
                    if connection is not None:
                        connection.close()
        except portalocker.exceptions.LockException as exc:
            raise DuckDBStorageError(
                f"timed out acquiring local search database lock after {self.timeout:g}s"
            ) from exc
        except DuckDBStorageError:
            raise
        except duckdb.Error as exc:
            raise DuckDBStorageError(f"local DuckDB operation failed: {exc}") from exc


class DuckDBNamespace:
    """One inert namespace handle within a :class:`DuckDBClient`."""

    def __init__(self, client: DuckDBClient, name: str) -> None:
        self._client = client
        self.name = name

    def metadata(self, **_: object) -> dict[str, object]:
        if not self._client.path.exists():
            raise NamespaceNotFoundError(self.name)
        with self._client._connection(write=False) as connection:
            _validate_database(connection)
            schema, distance_metric = _namespace_metadata(connection, self.name)
        return {
            "schema": {"id": {"type": "string", "filterable": True}, **schema},
            "distance_metric": distance_metric,
        }

    def write(
        self,
        *,
        upsert_rows: Sequence[Mapping[str, object]] | None = None,
        rows: Sequence[Mapping[str, object]] | None = None,
        schema: Mapping[str, object] | None = None,
        distance_metric: str = DISTANCE_METRIC,
        deletes: Sequence[str] | None = None,
        upsert_condition: Sequence[object] | None = None,
        return_affected_ids: bool = False,
        **kwargs: object,
    ) -> dict[str, object]:
        """Atomically merge schema, delete IDs, and conditionally upsert rows."""

        if kwargs:
            unknown = ", ".join(sorted(kwargs))
            raise TypeError(f"unexpected write arguments: {unknown}")
        if rows is not None:
            if upsert_rows is not None:
                raise TypeError("pass either upsert_rows or rows, not both")
            upsert_rows = rows
        prepared_rows = _prepare_rows(upsert_rows or ())
        delete_ids = _validate_delete_ids(deletes or ())
        normalized_schema = _normalize_schema(schema) if schema is not None else None
        condition = _normalize_upsert_condition(upsert_condition)
        if distance_metric != DISTANCE_METRIC:
            raise DuckDBStorageError("local storage supports only cosine_distance")
        if not normalized_schema and not prepared_rows and not delete_ids:
            raise DuckDBStorageError("write requires schema, upsert rows, or deletes")

        with self._client._connection(write=True) as connection:
            connection.execute("BEGIN TRANSACTION")
            try:
                _initialize_database(connection)
                existing = connection.execute(
                    "SELECT schema_json, distance_metric FROM buoy_namespaces WHERE namespace = ?",
                    [self.name],
                ).fetchone()
                if existing is None:
                    if normalized_schema is None:
                        raise NamespaceNotFoundError(self.name)
                    merged_schema = normalized_schema
                    connection.execute(
                        "INSERT INTO buoy_namespaces VALUES (?, ?, ?)",
                        [
                            self.name,
                            _json_dumps(merged_schema),
                            DISTANCE_METRIC,
                        ],
                    )
                else:
                    if str(existing[1]) != DISTANCE_METRIC:
                        raise DuckDBStorageError(
                            "namespace has an unsupported distance metric"
                        )
                    stored_schema = _loaded_object(
                        existing[0], label="namespace schema"
                    )
                    merged_schema = _merge_schema(stored_schema, normalized_schema)
                    if merged_schema != stored_schema:
                        connection.execute(
                            "UPDATE buoy_namespaces SET schema_json = ? WHERE namespace = ?",
                            [_json_dumps(merged_schema), self.name],
                        )

                deleted_ids: list[str] = []
                for row_id in delete_ids:
                    affected = connection.execute(
                        "DELETE FROM buoy_rows WHERE namespace = ? AND id = ? RETURNING id",
                        [self.name, row_id],
                    ).fetchone()
                    if affected is None:
                        continue
                    deleted_ids.append(row_id)
                    connection.execute(
                        "DELETE FROM buoy_postings WHERE namespace = ? AND row_id = ?",
                        [self.name, row_id],
                    )
                    connection.execute(
                        "DELETE FROM buoy_lengths WHERE namespace = ? AND row_id = ?",
                        [self.name, row_id],
                    )

                upserted_ids: list[str] = []
                for row in prepared_rows:
                    row_id = row["id"]
                    current = connection.execute(
                        "SELECT attributes_json FROM buoy_rows WHERE namespace = ? AND id = ?",
                        [self.name, row_id],
                    ).fetchone()
                    if not _condition_matches(condition, current):
                        continue
                    if current is not None:
                        connection.execute(
                            "DELETE FROM buoy_postings WHERE namespace = ? AND row_id = ?",
                            [self.name, row_id],
                        )
                        connection.execute(
                            "DELETE FROM buoy_lengths WHERE namespace = ? AND row_id = ?",
                            [self.name, row_id],
                        )
                    attributes = row["attributes"]
                    connection.execute(
                        """
                        INSERT OR REPLACE INTO buoy_rows
                            (namespace, id, attributes_json, vector, doc_kind)
                        VALUES (?, ?, ?, ?::FLOAT[384], ?)
                        """,
                        [
                            self.name,
                            row_id,
                            row["attributes_json"],
                            row["vector"],
                            attributes.get("doc_kind")
                            if isinstance(attributes.get("doc_kind"), str)
                            else None,
                        ],
                    )
                    _insert_lexical_state(connection, self.name, row_id, attributes)
                    upserted_ids.append(row_id)
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise

        rows_affected = len(deleted_ids) + len(upserted_ids)
        if not prepared_rows and not delete_ids:
            return {"status": "OK", "rows_affected": 0}
        result: dict[str, object] = {
            "status": "OK",
            "rows_affected": rows_affected,
        }
        if prepared_rows:
            result["upserted_ids"] = (
                upserted_ids if return_affected_ids and upserted_ids else None
            )
        if delete_ids:
            result["deleted_ids"] = deleted_ids or None
        return result

    def query(
        self,
        *,
        rank_by: Sequence[object] = ("id", "asc"),
        top_k: int = 10,
        filters: Sequence[object] | None = None,
        include_attributes: Sequence[str] | None = None,
        vector_encoding: str = "float",
        consistency: object | None = None,
        **kwargs: object,
    ) -> dict[str, object]:
        """Query one namespace by ID, exact cosine distance, or BM25."""

        del consistency
        if kwargs:
            unknown = ", ".join(sorted(kwargs))
            raise TypeError(f"unexpected query arguments: {unknown}")
        options = _prepare_query(
            rank_by=rank_by,
            top_k=top_k,
            filters=filters,
            include_attributes=include_attributes,
            vector_encoding=vector_encoding,
        )
        if not self._client.path.exists():
            raise NamespaceNotFoundError(self.name)
        with self._client._connection(write=False) as connection:
            _validate_database(connection)
            _namespace_metadata(connection, self.name)
            connection.execute("BEGIN TRANSACTION")
            try:
                result = _query_connection(connection, self.name, options)
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise
        return {"rows": result}

    def multi_query(
        self,
        *,
        queries: Sequence[Mapping[str, object]],
        rerank_by: object | None = None,
    ) -> dict[str, object]:
        """Run every subquery against one locked DuckDB snapshot.

        ``rerank_by`` is intentionally accepted but ignored. Returning separate
        result lists activates the existing retriever's deterministic client RRF.
        """

        del rerank_by
        if not isinstance(queries, Sequence) or isinstance(queries, (str, bytes)):
            raise TypeError("queries must be a sequence")
        if len(queries) > _MAX_QUERIES:
            raise DuckDBStorageError(f"at most {_MAX_QUERIES} subqueries are allowed")
        prepared = []
        for query in queries:
            if not isinstance(query, Mapping):
                raise TypeError("each subquery must be a mapping")
            unknown = set(query) - {
                "rank_by",
                "limit",
                "top_k",
                "filters",
                "include_attributes",
                "vector_encoding",
                "consistency",
            }
            if unknown:
                raise TypeError(
                    f"unexpected subquery arguments: {', '.join(sorted(unknown))}"
                )
            prepared.append(
                _prepare_query(
                    rank_by=query.get("rank_by", ("id", "asc")),
                    top_k=query.get("limit", query.get("top_k", 10)),
                    filters=query.get("filters"),
                    include_attributes=query.get("include_attributes"),
                    vector_encoding=query.get("vector_encoding", "float"),
                )
            )
        if not self._client.path.exists():
            raise NamespaceNotFoundError(self.name)
        with self._client._connection(write=False) as connection:
            _validate_database(connection)
            _namespace_metadata(connection, self.name)
            connection.execute("BEGIN TRANSACTION")
            try:
                results = [
                    {"rows": _query_connection(connection, self.name, options)}
                    for options in prepared
                ]
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise
        return {"results": results}


def _safe_duckdb_config() -> dict[str, str]:
    memory_limit = os.environ.get("BUOY_DB_MEMORY_LIMIT", "4GB").strip()
    if not memory_limit or len(memory_limit) > 64:
        raise DuckDBStorageError("BUOY_DB_MEMORY_LIMIT is invalid")
    raw_threads = os.environ.get("BUOY_DB_THREADS", "4")
    try:
        threads = int(raw_threads)
    except ValueError:
        raise DuckDBStorageError("BUOY_DB_THREADS must be a positive integer") from None
    if threads <= 0 or threads > 256:
        raise DuckDBStorageError("BUOY_DB_THREADS must be between 1 and 256")
    return {
        "enable_external_access": "false",
        "autoinstall_known_extensions": "false",
        "autoload_known_extensions": "false",
        "allow_community_extensions": "false",
        "memory_limit": memory_limit,
        "threads": str(threads),
    }


def _initialize_database(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS buoy_storage_metadata (
            schema_version INTEGER PRIMARY KEY CHECK (schema_version = 1),
            retrieval_contract VARCHAR NOT NULL
        );
        """
    )
    connection.execute(
        "INSERT INTO buoy_storage_metadata SELECT 1, ? "
        "WHERE NOT EXISTS (SELECT 1 FROM buoy_storage_metadata)",
        [_STORAGE_CONTRACT],
    )
    _validate_database(connection)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS buoy_namespaces (
            namespace VARCHAR PRIMARY KEY,
            schema_json VARCHAR NOT NULL,
            distance_metric VARCHAR NOT NULL CHECK (distance_metric = 'cosine_distance')
        );
        CREATE TABLE IF NOT EXISTS buoy_rows (
            namespace VARCHAR NOT NULL,
            id VARCHAR NOT NULL,
            attributes_json VARCHAR NOT NULL,
            vector FLOAT[384] NOT NULL,
            doc_kind VARCHAR,
            PRIMARY KEY (namespace, id)
        );
        CREATE TABLE IF NOT EXISTS buoy_lengths (
            namespace VARCHAR NOT NULL,
            row_id VARCHAR NOT NULL,
            title_length UINTEGER NOT NULL,
            section_path_length UINTEGER NOT NULL,
            content_length UINTEGER NOT NULL,
            PRIMARY KEY (namespace, row_id)
        );
        CREATE TABLE IF NOT EXISTS buoy_postings (
            namespace VARCHAR NOT NULL,
            row_id VARCHAR NOT NULL,
            field VARCHAR NOT NULL,
            term VARCHAR NOT NULL,
            term_frequency UINTEGER NOT NULL,
            PRIMARY KEY (namespace, row_id, field, term)
        );
        """
    )
    _validate_database(connection)


def _validate_database(connection: duckdb.DuckDBPyConnection) -> None:
    try:
        versions = connection.execute(
            "SELECT schema_version, retrieval_contract FROM buoy_storage_metadata"
        ).fetchall()
    except duckdb.Error as exc:
        raise DuckDBStorageError(
            "local search database has an incompatible schema"
        ) from exc
    if versions != [(1, _STORAGE_CONTRACT)]:
        raise DuckDBStorageError(
            "local search database has an incompatible schema or retrieval contract; "
            "rebuild in a fresh BUOY_HOME rather than reusing old vectors/postings"
        )


def _namespace_metadata(
    connection: duckdb.DuckDBPyConnection, namespace: str
) -> tuple[dict[str, object], str]:
    value = connection.execute(
        "SELECT schema_json, distance_metric FROM buoy_namespaces WHERE namespace = ?",
        [namespace],
    ).fetchone()
    if value is None:
        raise NamespaceNotFoundError(namespace)
    return _loaded_object(value[0], label="namespace schema"), str(value[1])


def _normalize_schema(schema: Mapping[str, object]) -> dict[str, object]:
    if not isinstance(schema, Mapping):
        raise TypeError("schema must be a mapping")
    result: dict[str, object] = {}
    for name, config in schema.items():
        if not isinstance(name, str) or not name or name == "id":
            raise DuckDBStorageError(
                "schema attribute names must be non-empty strings other than id"
            )
        # JSON round-tripping both validates and makes caller mutation harmless.
        result[name] = json.loads(_json_dumps(config))
    return result


def _merge_schema(
    stored: dict[str, object], additions: dict[str, object] | None
) -> dict[str, object]:
    if additions is None:
        return stored
    merged = dict(stored)
    for name, config in additions.items():
        if name in merged and merged[name] != config:
            raise DuckDBStorageError(
                f"schema attribute {name!r} cannot be changed after namespace creation"
            )
        merged[name] = config
    return merged


def _prepare_rows(rows: Sequence[Mapping[str, object]]) -> list[dict[str, Any]]:
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise TypeError("upsert_rows must be a sequence")
    prepared: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in rows:
        if not isinstance(raw, Mapping):
            raise DuckDBStorageError("every upsert row must be a mapping")
        row_id = raw.get("id")
        if not isinstance(row_id, str) or not row_id:
            raise DuckDBStorageError("every upsert row requires a non-empty string id")
        if row_id in seen:
            raise DuckDBStorageError(f"duplicate upsert row id {row_id!r}")
        seen.add(row_id)
        vector = _validate_vector(raw.get("vector"), label=f"row {row_id!r} vector")
        if any(not isinstance(key, str) for key in raw):
            raise DuckDBStorageError("row attribute names must be strings")
        attributes = {key: value for key, value in raw.items() if key != "id"}
        attributes_json = _json_dumps(attributes)
        prepared.append(
            {
                "id": row_id,
                "vector": vector,
                "attributes": attributes,
                "attributes_json": attributes_json,
            }
        )
    return prepared


def _validate_vector(value: object, *, label: str) -> list[float]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise DuckDBStorageError(
            f"{label} must contain exactly {VECTOR_DIMENSIONS} numbers"
        )
    if len(value) != VECTOR_DIMENSIONS:
        raise DuckDBStorageError(
            f"{label} must contain exactly {VECTOR_DIMENSIONS} numbers"
        )
    vector: list[float] = []
    squared_norm = 0.0
    for index, item in enumerate(value):
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise DuckDBStorageError(f"{label}[{index}] must be a finite number")
        number = float(item)
        if not math.isfinite(number):
            raise DuckDBStorageError(f"{label}[{index}] must be a finite number")
        try:
            stored_number = struct.unpack("!f", struct.pack("!f", number))[0]
        except (OverflowError, struct.error):
            raise DuckDBStorageError(
                f"{label}[{index}] must be a finite float32 number"
            ) from None
        if not math.isfinite(stored_number):
            raise DuckDBStorageError(
                f"{label}[{index}] must be a finite float32 number"
            )
        vector.append(stored_number)
        squared_norm += stored_number * stored_number
    if not math.isfinite(squared_norm) or squared_norm == 0.0:
        raise DuckDBStorageError(f"{label} must be nonzero and have a finite norm")
    return vector


def _validate_delete_ids(values: Sequence[str]) -> list[str]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise TypeError("deletes must be a sequence")
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str) or not value:
            raise DuckDBStorageError("delete IDs must be non-empty strings")
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _normalize_upsert_condition(
    value: Sequence[object] | None,
) -> tuple[str, str, object] | None:
    if value is None:
        return None
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes))
        or len(value) != 3
    ):
        raise DuckDBStorageError("upsert_condition must be a three-item expression")
    field, operator, expected = value
    if operator != "Eq" or field not in {"id", "card_revision"}:
        raise DuckDBStorageError(
            "upsert_condition supports only id Eq or card_revision Eq"
        )
    if field == "id" and expected is not None:
        raise DuckDBStorageError("id upsert condition supports only Eq None")
    if field == "card_revision" and (not isinstance(expected, str) or not expected):
        raise DuckDBStorageError("card_revision condition requires a non-empty string")
    return str(field), "Eq", expected


def _condition_matches(
    condition: tuple[str, str, object] | None, current: tuple[object, ...] | None
) -> bool:
    if condition is None:
        return True
    field, _, expected = condition
    if field == "id":
        return current is None
    if current is None:
        return False
    attributes = _loaded_object(current[0], label="row attributes")
    return attributes.get("card_revision") == expected


def _insert_lexical_state(
    connection: duckdb.DuckDBPyConnection,
    namespace: str,
    row_id: str,
    attributes: Mapping[str, object],
) -> None:
    lengths: list[int] = []
    postings: list[tuple[object, ...]] = []
    for field in ("title", "section_path", "content"):
        raw = attributes.get(field)
        tokens = _tokens(raw if isinstance(raw, str) else "")
        lengths.append(len(tokens))
        postings.extend(
            (namespace, row_id, field, term, frequency)
            for term, frequency in Counter(tokens).items()
        )
    connection.execute(
        "INSERT INTO buoy_lengths VALUES (?, ?, ?, ?, ?)",
        [namespace, row_id, *lengths],
    )
    if postings:
        # One vectorized insert per chunk, not one Python/SQL round trip per
        # token. This matters for laptop-sized corpora with millions of terms.
        connection.execute(
            """INSERT INTO buoy_postings
               SELECT ?, ?, unnest(?::VARCHAR[]), unnest(?::VARCHAR[]),
                      unnest(?::UINTEGER[])""",
            [
                namespace,
                row_id,
                [row[2] for row in postings],
                [row[3] for row in postings],
                [row[4] for row in postings],
            ],
        )


def _prepare_query(
    *,
    rank_by: object,
    top_k: object,
    filters: object,
    include_attributes: object,
    vector_encoding: object,
) -> dict[str, object]:
    if type(top_k) is not int or not 0 < top_k <= _MAX_TOP_K:
        raise DuckDBStorageError(f"top_k must be between 1 and {_MAX_TOP_K}")
    if vector_encoding != "float":
        raise DuckDBStorageError("local storage supports only float vector encoding")
    if include_attributes is None:
        projection = None
    else:
        if not isinstance(include_attributes, Sequence) or isinstance(
            include_attributes, (str, bytes)
        ):
            raise TypeError("include_attributes must be a sequence")
        projection = []
        for name in include_attributes:
            if not isinstance(name, str) or not name:
                raise DuckDBStorageError(
                    "include attribute names must be non-empty strings"
                )
            if name != "id" and name not in projection:
                projection.append(name)
    return {
        "rank": _normalize_rank(rank_by),
        "top_k": top_k,
        "filter": _normalize_filter(filters),
        "projection": projection,
    }


def _normalize_rank(value: object) -> tuple[str, object]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        rank = list(value)
    else:
        raise DuckDBStorageError("rank_by is invalid")
    if rank == ["id", "asc"]:
        return "id", None
    if len(rank) == 3 and rank[0:2] == ["vector", "ANN"]:
        return "ann", _validate_vector(rank[2], label="query vector")
    terms = _bm25_terms(value)
    if terms is not None:
        return "bm25", terms
    raise DuckDBStorageError("unsupported rank_by expression")


def _bm25_terms(value: object) -> list[str] | None:
    try:
        operator, expressions = value  # type: ignore[misc]
        if (
            operator != "Sum"
            or not isinstance(expressions, Sequence)
            or len(expressions) != 3
        ):
            return None
        expected_fields = (("title", 2.0), ("section_path", 1.5), ("content", 1.0))
        queries: list[str] = []
        for expression, (expected_field, expected_weight) in zip(
            expressions, expected_fields, strict=True
        ):
            if expected_weight == 1.0:
                field, bm25, query = expression
            else:
                product, weight, inner = expression
                field, bm25, query = inner
                if product != "Product" or float(weight) != expected_weight:
                    return None
            if field != expected_field or bm25 != "BM25" or not isinstance(query, str):
                return None
            queries.append(query)
        if len(set(queries)) != 1:
            return None
    except (TypeError, ValueError):
        return None
    tokens = list(dict.fromkeys(_tokens(queries[0])))
    if len(tokens) > _MAX_QUERY_TOKENS:
        raise DuckDBStorageError(
            f"BM25 query contains more than {_MAX_QUERY_TOKENS} tokens"
        )
    return tokens


def _normalize_filter(value: object) -> tuple[str, str, object] | None:
    if value is None:
        return None
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes))
        or len(value) != 3
    ):
        raise DuckDBStorageError("filters must be a three-item expression")
    field, operator, expected = value
    if not isinstance(field, str) or operator not in {"Eq", "Gt"}:
        raise DuckDBStorageError("filters support only Eq and Gt")
    if operator == "Gt" and field != "id":
        raise DuckDBStorageError("Gt filters are supported only for id")
    if field == "id" and not isinstance(expected, str):
        raise DuckDBStorageError("id filters require a string value")
    return field, str(operator), expected


def _query_connection(
    connection: duckdb.DuckDBPyConnection,
    namespace: str,
    options: Mapping[str, object],
) -> list[dict[str, object]]:
    rank_kind, rank_value = options["rank"]  # type: ignore[misc]
    where_sql, where_params = _filter_sql(options["filter"])
    top_k = int(options["top_k"])
    if rank_kind == "id":
        values = connection.execute(
            f"""
            SELECT id, attributes_json, NULL::DOUBLE AS score
            FROM buoy_rows
            WHERE namespace = ? {where_sql}
            ORDER BY id ASC
            LIMIT ?
            """,
            [namespace, *where_params, top_k],
        ).fetchall()
        score_name = None
    elif rank_kind == "ann":
        values = connection.execute(
            f"""
            SELECT id, attributes_json,
                   array_cosine_distance(vector, ?::FLOAT[384]) AS score
            FROM buoy_rows
            WHERE namespace = ? {where_sql}
            ORDER BY score ASC, id ASC
            LIMIT ?
            """,
            [rank_value, namespace, *where_params, top_k],
        ).fetchall()
        score_name = "$dist"
    else:
        terms = rank_value
        if not terms:
            return []
        values = connection.execute(
            f"""
            WITH query_terms(term) AS (
                SELECT DISTINCT unnest(?::VARCHAR[])
            ),
            corpus AS (
                SELECT count(*)::DOUBLE AS document_count,
                       coalesce(avg(title_length), 0.0) AS avg_title,
                       coalesce(avg(section_path_length), 0.0) AS avg_section,
                       coalesce(avg(content_length), 0.0) AS avg_content
                FROM buoy_lengths
                WHERE namespace = ?
            ),
            document_frequency AS (
                SELECT p.field, p.term, count(*)::DOUBLE AS df
                FROM buoy_postings p
                JOIN query_terms q USING (term)
                WHERE p.namespace = ?
                GROUP BY p.field, p.term
            ),
            scores AS (
                SELECT p.row_id,
                       sum(
                           (CASE p.field
                               WHEN 'title' THEN 2.0
                               WHEN 'section_path' THEN 1.5
                               ELSE 1.0
                            END)
                           * ln(1.0 + ((c.document_count - d.df + 0.5) / (d.df + 0.5)))
                           * ((p.term_frequency * 2.2) /
                              (p.term_frequency + 1.2 *
                               (0.25 + 0.75 *
                                (CASE p.field
                                    WHEN 'title' THEN l.title_length /
                                        greatest(c.avg_title, 1.0)
                                    WHEN 'section_path' THEN l.section_path_length /
                                        greatest(c.avg_section, 1.0)
                                    ELSE l.content_length /
                                        greatest(c.avg_content, 1.0)
                                 END))))
                       ) AS score
                FROM buoy_postings p
                JOIN query_terms q USING (term)
                JOIN document_frequency d USING (field, term)
                JOIN buoy_lengths l
                  ON l.namespace = p.namespace AND l.row_id = p.row_id
                CROSS JOIN corpus c
                WHERE p.namespace = ?
                GROUP BY p.row_id
            )
            SELECT r.id, r.attributes_json, s.score
            FROM scores s
            JOIN buoy_rows r
              ON r.namespace = ? AND r.id = s.row_id
            WHERE TRUE {where_sql}
            ORDER BY s.score DESC, r.id ASC
            LIMIT ?
            """,
            [
                terms,
                namespace,
                namespace,
                namespace,
                namespace,
                *where_params,
                top_k,
            ],
        ).fetchall()
        score_name = "score"
    return [
        _project_row(
            str(row_id),
            attributes_json,
            projection=options["projection"],
            score_name=score_name,
            score=score,
        )
        for row_id, attributes_json, score in values
    ]


def _filter_sql(value: object) -> tuple[str, list[object]]:
    if value is None:
        return "", []
    field, operator, expected = value  # type: ignore[misc]
    sql_operator = "=" if operator == "Eq" else ">"
    if field == "id":
        return f" AND id {sql_operator} ?", [expected]
    if field == "doc_kind":
        return f" AND doc_kind {sql_operator} ?", [expected]
    path = '$."' + str(field).replace("\\", "\\\\").replace('"', '\\"') + '"'
    if operator != "Eq":  # guarded by _normalize_filter
        raise DuckDBStorageError("Gt filters are supported only for id")
    return " AND json_extract(attributes_json, ?) = ?::JSON", [
        path,
        _json_dumps(expected),
    ]


def _project_row(
    row_id: str,
    raw_attributes: object,
    *,
    projection: object,
    score_name: str | None,
    score: object,
) -> dict[str, object]:
    attributes = _loaded_object(raw_attributes, label="row attributes")
    result: dict[str, object] = {"id": row_id}
    names = attributes.keys() if projection is None else projection
    for name in names:  # type: ignore[union-attr]
        if name in attributes:
            result[str(name)] = attributes[name]
    if score_name is not None and score is not None:
        result[score_name] = float(score)
    return result


def _tokens(value: str) -> list[str]:
    return [match.group(0).casefold() for match in _TOKEN_RE.finditer(value)]


def _loaded_object(value: object, *, label: str) -> dict[str, object]:
    try:
        parsed = json.loads(str(value))
    except (TypeError, json.JSONDecodeError) as exc:
        raise DuckDBStorageError(f"stored {label} is invalid") from exc
    if not isinstance(parsed, dict):
        raise DuckDBStorageError(f"stored {label} is invalid")
    return parsed


def _json_dumps(value: object) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise DuckDBStorageError(
            "local storage values must be finite JSON data"
        ) from exc


def _validate_namespace(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > 256 or "\x00" in value:
        raise ValueError(
            "namespace must be a non-empty string of at most 256 characters"
        )
    return value
