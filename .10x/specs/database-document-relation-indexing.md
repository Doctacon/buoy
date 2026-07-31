Status: active
Created: 2026-07-22
Updated: 2026-07-24
Amended-By: .10x/specs/focused-buoy-boundary.md

# Database Document Relation Indexing

## Focused-boundary amendment

This specification remains active for one document-shaped database relation,
its source identity, bounded planning, content indexing, and document/page
retrieval defaults. Routing-card and catalog semantics are superseded; the
versioned Buoy apply receipt is the only cross-product handoff to Kite.

## Purpose and scope

Buoy MUST consume one already-shaped document table or view from DuckDB, BigQuery, or Snowflake during `plan` and `crawl`. Upstream API extraction and transformations remain owned by dlt, dbt, SQLMesh, or SQL. The backend changes only safe row acquisition; shared Markdown materialization, chunking, plan, diff, embedding, apply, and turbopuffer behavior remain backend-independent.

## Document contract

Each row is one logical document. `document_id` and `content` are required; `title` is optional. Existing `--id-column`, `--content-column`, and `--title-column` mappings remain supported and MUST be ordinary single identifiers. IDs are converted to text and MUST be globally non-null, nonblank, and unique after conversion. Content is converted to text; null/blank content is skipped and counted, and an all-empty relation fails. Missing/null/blank title falls back to text ID. Selection MUST be deterministic by converted ID. `--max-pages` limits documents returned to Python; Buoy MAY split each selected document into chunks.

## Identity and provenance

For backend `<backend>` and source ID `<slug>`, base URI is `<backend>://<slug>`, site/state ID is `<backend>-<slug>`, default namespace is `<backend>-<slug>-v1`, output is `artifacts/site-crawls/<backend>-<slug>`, and document URI appends the percent-encoded text ID. Identity MUST NOT depend on credentials, connection settings, paths, query/job IDs, row order, counts, or contents. Source IDs retain `^[a-z0-9]+(?:-[a-z0-9]+)*$` validation without normalization.

Temporary materialized pages, schema-v2 plan-level source metadata, changed/new delta rows, and turbopuffer content rows MUST preserve `database_backend`, `database_source_id`, and `database_relation`; delta/content rows also preserve `database_document_id`. DuckDB MAY retain `duckdb_*` row metadata in addition to required generic fields. Schema-v1 saved plans, including DuckDB plans lacking generic fields, are inert and unsupported under `.10x/specs/compact-delta-plan-artifacts.md`; no compatibility reader or migration remains.

## Shared materialization and summaries

A shared internal relation layer MUST own logical documents/counts, stable filenames, scalar-safe frontmatter, corpus writing, summary generation, and `process_corpus()` handoff. Low-level source kinds are `duckdb_relation`, `bigquery_relation`, and `snowflake_relation`; catalog high-level kind remains `database`. Frontmatter fetchers are `<backend>-read-only`.

Summaries MUST distinguish `rows_discovered`, `documents_selected`, `documents_skipped_empty`, `documents_skipped_limit`, `document_limit_reached`, `chunks_generated`, `chunk_limit_reached`, and `limit_reached`. DuckDB reports source credentials/API activity false; BigQuery/Snowflake true. Turbopuffer credentials/API activity remain false during plan/crawl. Generic legacy summary fields MUST be truthful for the complete command.

## Plan/apply boundary

Only `plan` and `crawl` MAY connect to source databases. `apply`, including dry-run, MUST use integrity-verified saved artifacts only and MUST remain independent of source files, credentials, profiles, connection settings, and changed relation contents. Source connection/credential details and volatile operational diagnostics MUST NOT enter deterministic identity or artifact hashes. All database sources emit `PLAN_SCHEMA_VERSION=2` compact deltas with the exact source variant and hard-cutover behavior in `.10x/specs/compact-delta-plan-artifacts.md`.

## CLI and safety

`--database-backend {duckdb,bigquery,snowflake}` selects a backend; implicit DuckDB via the existing positional path plus relation remains compatible. Every database command requires relation and source ID. DuckDB requires a local file; remote backends reject a local path. Backend-specific flags MUST fail with other backends, and explicit empty mappings MUST fail. Remote optional SDKs are lazy imports and ordinary installs remain unaffected.

All relation/column inputs are identifiers, never SQL. Reject expressions, comments, semicolons, wildcards, calls, quoted fragments, and whitespace fragments. DuckDB retains one-to-three ordinary relation components and its read-only external/extension restrictions. BigQuery requires a safe fully-qualified `project.dataset.object` with project hyphens supported. Snowflake requires exactly three ordinary unquoted identifiers canonicalized to uppercase and safely quoted.

## Retrieval and catalog

Database base URIs accept only `duckdb`, `bigquery`, and `snowflake` schemes with a safe host-only source ID and no credentials, port, path, query, or fragment. Database schemes are invalid for other source kinds and vice versa. Generated semantics MUST derive deterministic title/summary/aliases/tags from verified logical metadata, with tags `database` plus backend; manual semantics retain precedence. Database plans, including custom namespaces, use page/none/pool20/max defaults based on verified source kind; prefix fallback remains for explicit retrieval without catalog context.

## Explicit exclusions

No API extraction, orchestration, arbitrary SQL, Buoy-configured joins, multiple relations, CDC/watermarks, dynamic metadata/schema, source-specific transcript logic/chunking, broad plugin framework, additional databases, credential CLI arguments, BigQuery Storage API, or Snowflake pandas/Arrow ingestion.

## Acceptance criteria

1. Existing DuckDB command names and source/row identities remain compatible while every newly generated plan uses schema 2; schema-1 saved plans are unsupported and inert. Global validation uses backend SQL rather than retaining all IDs in Python.
2. BigQuery and Snowflake tables/views satisfy the same contract through official lazy clients/connectors and bounded deterministic acquisition.
3. Generic provenance survives temporary materialized pages into plan-level source metadata, changed/new delta rows, and turbopuffer rows without credential/connection leakage.
4. Invalid identifiers/combinations fail clearly before successful page/plan output.
5. Saved-plan apply never imports/connects to source adapters.
6. Catalog and ranking behavior supports all three backends and custom namespaces without changing other source categories.
7. Default tests run without cloud SDKs, credentials, network, or live warehouse/turbopuffer calls.
