"""Local storage adapters."""

from buoy_search.storage.duckdb import (
    DuckDBClient,
    DuckDBNamespace,
    DuckDBStorageError,
    NamespaceNotFoundError,
)

__all__ = [
    "DuckDBClient",
    "DuckDBNamespace",
    "DuckDBStorageError",
    "NamespaceNotFoundError",
]
