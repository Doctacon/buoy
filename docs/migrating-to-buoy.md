# Migrating to focused Buoy

Buoy's indexing contract remains one source to one reviewed Turbopuffer
namespace. Retrieval may search one explicit namespace or an automatically
selected set of at most three compatible namespaces.
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
catalog
```

`serve`, `namespaces`, `evidence`, `--auto-route`, `--route-top-k`, and
retrieval's no-op `--live` option remain outside Buoy. The bounded `catalog`
surface and automatic multi-corpus retrieval have returned; the Command Center,
evidence lifecycle, and general account orchestration remain in Kite.

Omit `--namespace` to route automatically, or repeat it up to three times for a
deterministic override:

```bash
buoy retrieve "question"
buoy retrieve "question" --namespace site-example-docs-v1
buoy retrieve "comparison" \
  --namespace site-example-docs-v1 \
  --namespace site-another-corpus-v1
buoy evals --namespace site-example-docs-v1 --dry-run
```

`TURBOPUFFER_NAMESPACE` no longer supplies a default. Region, embedding model,
and embedding precision environment settings remain supported.

After content and local state commit, approved apply conditionally registers or
refreshes the namespace's routing card and reports the outcome in its
`receipt_schema_version=1` summary. A catalog failure is explicit partial
success and includes a reviewed repair command; it never rolls content back.

## Existing state

Buoy continues to use:

```text
.buoy/state/<source-id>/<namespace>/state.duckdb
```

Existing `.turbo-search` state remains available through the established
in-place fallback. Obsolete JSON state is ignored and left unchanged.

The split leaves these legacy artifacts untouched:

- local catalog and catalog-pending files;
- old local catalog files and pending-recovery artifacts;
- `buoy-evidence-*` namespaces;
- Command Center job/event history;
- historical plans and `.10x` records.

`buoy-routing-catalog-v1` is again active, bounded Buoy routing authority. The
other artifacts remain historical or Kite-owned and are not automatically
repaired or deleted. See [Buoy and Kite](kite-split.md) before proposing any
cleanup.

## Package changes

The Buoy distribution includes the small routing-card, catalog, and bounded
retrieval modules. It still excludes FastAPI/Uvicorn UI dependencies, Command
Center assets/source, evidence modules, and their CLI commands.

Website, repository, local-document, DuckDB, BigQuery, and Snowflake relation
support remains. BigQuery and Snowflake continue as optional dependencies.

## Removed turbo-search aliases

The earlier `turbo-search` executable and
`TURBO_SEARCH_EMBEDDING_MODEL`/`TURBO_SEARCH_EMBEDDING_PRECISION` variables
remain unsupported. Use `buoy`, `BUOY_EMBEDDING_MODEL`, and
`BUOY_EMBEDDING_PRECISION`.
