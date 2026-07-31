Status: superseded
Created: 2026-07-22
Updated: 2026-07-22

# Database Catalog and Retrieval Semantics

## Purpose and scope

This specification defines catalog representation and retrieval defaults for DuckDB document-relation namespaces without changing existing source categories.

## Behavior

- Generated low-level source metadata MUST identify `duckdb_relation`; generated namespace catalog semantics MUST expose high-level `source_kind: database`.
- `database` MUST be an allowed catalog source kind alongside existing kinds.
- A database card MUST use a base source URI `duckdb://<source-id>` with non-empty safe authority, no credentials, port, query, fragment, or document path.
- `duckdb://` MUST be rejected for non-database cards, and database cards MUST reject unsupported URI schemes.
- Generated database title, summary, aliases, and tags MUST be stable and derived from source ID and relation. Manual catalog semantics MUST retain existing precedence and MUST NOT be overwritten.
- Namespaces beginning `duckdb-` MUST use the existing document/page ranking family, pool, and aggregation defaults, never repository-code defaults.
- Existing website, GitHub, PDF, and file cards and namespace defaults MUST remain unchanged.

## Acceptance criteria

1. Verified DuckDB plan metadata produces a valid generated database card with deterministic semantics.
2. Valid base `duckdb://` URIs pass only for database cards; credentials, ports, paths, queries, fragments, unsafe IDs, and scheme/kind mismatches fail closed.
3. `duckdb-` namespace defaults equal the established page/document defaults.
4. Existing catalog and retrieval tests pass unchanged except for additive expectations.
