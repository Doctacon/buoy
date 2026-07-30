# Migrating to focused Buoy

Buoy's current contract is one source to one reviewed Turbopuffer namespace.
The change is forward-only: repository history, release tags, existing content
namespaces, schema-v2 plans, and local DuckDB applied state are preserved.

## CLI changes

The public commands are:

```text
crawl
plan
apply
retrieve
evals
```

`serve`, `namespaces`, `catalog`, `evidence`, automatic routing,
multi-namespace retrieval, `--auto-route`, `--route-top-k`, and retrieval's
no-op `--live` option have moved out of Buoy.

Update retrieval scripts to provide one singular target:

```bash
buoy retrieve "question" --namespace site-example-docs-v1
buoy retrieve "question" --namespace site-example-docs-v1 --dry-run
buoy evals --namespace site-example-docs-v1 --dry-run
```

`TURBOPUFFER_NAMESPACE` no longer supplies a default. Region, embedding model,
and embedding precision environment settings remain supported.

Approved apply no longer registers or repairs a routing card. It emits
`receipt_schema_version=1`; pass that successful JSON summary to Kite when the
index should enter a cross-source catalog.

## Existing state

Buoy continues to use:

```text
.buoy/state/<source-id>/<namespace>/state.duckdb
```

Existing `.turbo-search` state remains available through the established
in-place fallback. Obsolete JSON state is ignored and left unchanged.

The split leaves these legacy artifacts untouched:

- local catalog and catalog-pending files;
- `buoy-routing-catalog-v1`;
- `buoy-evidence-*` namespaces;
- Command Center job/event history;
- historical plans and `.10x` records.

They are no longer active Buoy authority. See [Buoy and
Kite](kite-split.md) before proposing any migration or cleanup.

## Package changes

The Buoy distribution no longer includes FastAPI/Uvicorn UI dependencies,
Command Center static assets, frontend source, account-wide catalog/routing
modules, evidence modules, or their CLI commands.

Website, repository, local-document, DuckDB, BigQuery, and Snowflake relation
support remains. BigQuery and Snowflake continue as optional dependencies.

## Removed turbo-search aliases

The earlier `turbo-search` executable and
`TURBO_SEARCH_EMBEDDING_MODEL`/`TURBO_SEARCH_EMBEDDING_PRECISION` variables
remain unsupported. Use `buoy`, `BUOY_EMBEDDING_MODEL`, and
`BUOY_EMBEDDING_PRECISION`.
