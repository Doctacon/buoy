Status: active
Created: 2026-07-22
Updated: 2026-07-24

# DuckDB Document Relation Indexing

## Purpose and scope

Buoy MUST accept one already-shaped DuckDB table or view as a local indexing source during `plan` and `crawl`. Upstream extraction and transformation remain owned by dlt, dbt, SQLMesh, or SQL. Buoy owns validation, reviewable Markdown materialization, chunking, diffing, embedding planning, and synchronization through the existing saved-plan apply path.

This specification governs source identity, validation, deterministic acquisition, CLI behavior, review artifacts, and the plan/apply safety boundary.

## Input contract

- One row MUST represent one logical document.
- The default required columns are `document_id` and `content`; `title` is optional.
- `--id-column`, `--content-column`, and `--title-column` MAY map ordinary identifier columns.
- When no title override is supplied, Buoy MUST auto-detect `title`; absent, null, or blank title MUST fall back to the text document ID.
- Null or blank content MUST be skipped and counted. A relation with no nonblank documents MUST fail.
- Null, blank-after-text-conversion, or duplicate-after-text-conversion IDs MUST fail the whole operation.
- Tables and views MUST be supported.
- Arbitrary SQL, metadata, source URLs, timestamps, CDC, watermarks, joins inside Buoy, and non-DuckDB databases are excluded.

## CLI contract

`buoy plan DATABASE --relation RELATION --source-id SOURCE_ID` is canonical. `crawl` MUST accept the same database arguments. `--table` MAY alias `--relation`.

Database mode is activated only by `--relation`. `--source-id` is required in database mode. Database-only flags without `--relation` MUST produce actionable argument errors. Existing website, GitHub, and local-document commands MUST remain compatible. Existing `--max-pages` caps source documents and its help MUST say pages/files/documents; `--max-chunks` retains existing semantics.

## Identity and deterministic behavior

For source ID `gong-calls`:

- Base URI: `duckdb://gong-calls`
- Source/state ID: `duckdb-gong-calls`
- Default namespace: `duckdb-gong-calls-v1`
- Default output: `artifacts/site-crawls/duckdb-gong-calls`
- Document URI: `duckdb://gong-calls/<percent-encoded-document-id>`

Source IDs MUST match the lowercase ASCII slug regex `^[a-z0-9]+(?:-[a-z0-9]+)*$`; lossy normalization is forbidden. Database path, absolute path, file hash, physical row order, and database contents MUST NOT affect source identity. Document IDs MUST be ordered by their text conversion and MUST determine stable hash-based page filenames and URIs. Changing content or title MUST NOT change the logical document URI.

## SQL and filesystem safety

The path MUST exist, be a regular file, and open with one read-only DuckDB connection. Before relation access, that connection MUST disable external access, known-extension autoinstall and autoload, and community extensions. Relation names MUST contain one to three ordinary identifier components. Column names MUST be ordinary single identifiers. Each relation component and column name MUST match `^[A-Za-z_][A-Za-z0-9_]*$`. Every identifier MUST be validated before SQL execution and safely quoted. Extensions MUST NOT be installed or loaded. Scans SHOULD use bounded batches and a single consistent connection/snapshot. Text conversion, including `TIMESTAMPTZ` document IDs, MUST use UTC rather than host or ambient session timezone.

## Materialization and shared processing

Each selected row MUST become one Markdown file in `pages/`, with stable hash-derived filename, body equal to content, and scalar frontmatter containing synthetic URL, title, status, content type, `source_kind: duckdb_relation`, logical source ID, relation, logical document ID, content hash, UTC timestamp, and `fetcher: duckdb-read-only`. Quoted and backslash-containing titles and document IDs MUST round-trip through generated frontmatter and the shared Markdown parser without loss. The database filepath MUST NOT be serialized.

The adapter MUST call the existing shared `process_corpus()` path and MUST NOT implement custom chunking, embeddings, turbopuffer rows, plans, or apply behavior. Summaries MUST retain generic fields and add database counts/metadata without paths. Plan/crawl remain credential-free and local-only.

## Plan/apply boundary

Only `plan` and `crawl` MAY read the source DuckDB. `apply`, including dry-run, MUST consume fully verified schema-v2 compact delta artifacts only. Deleting, renaming, moving, or changing the source database after planning MUST NOT affect saved-plan verification or application. Schema-v1 saved plans are unsupported and inert.

## Acceptance scenarios

1. Given a valid table or view, planning uses deterministic temporary Markdown pages and emits exactly schema-v2 `plan.json` plus changed-only `delta.duckdb`; temporary pages are removed before success.
2. Given invalid paths, relations, mappings, IDs, or all-empty content, acquisition fails clearly before partial successful planning.
3. Given different insertion order or file path with the same source ID and contents, logical identities and artifact content (apart from established temporal fields) remain stable.
4. Given a saved plan whose source database is removed, `apply --dry-run --plan` verifies without accessing DuckDB.
5. Existing website, GitHub, and local-document source/chunk identities remain passing through the shared schema-v2 plan/apply contract.
