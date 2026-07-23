# Buoy

[![CI](https://github.com/Doctacon/buoy/actions/workflows/ci.yml/badge.svg)](https://github.com/Doctacon/buoy/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/github/license/Doctacon/buoy)](LICENSE)

<img src="images/buoy.svg" height="120" alt="Buoy navigation marker logo" />

Turn a public website, GitHub repository, local document, or already-shaped DuckDB, BigQuery, or Snowflake relation into a reviewed, incremental [turbopuffer](https://turbopuffer.com/) search index.

**Search that stays anchored to the source.**

## Quick start

Requires [uv](https://docs.astral.sh/uv/): `uv sync`

Build and search a website index:

```bash
# 1. Fetch, chunk, and plan locally. No Turbopuffer credentials, embeddings, or calls.
uv run buoy plan https://example.com/
# 2. Verify the plan and preview its diff. Still local-only and prompt-free.
uv run buoy apply --dry-run
# 3. Run the normal interactive flow: preflight, then exact [y/N] confirmation.
export TURBOPUFFER_API_KEY="..."
uv run buoy apply
# 4. Search through authenticated automatic remote routing.
uv run buoy retrieve "How does this feature work?"
```

`plan` may fetch a public source, but it does not read Turbopuffer credentials, load embeddings, or contact Turbopuffer. Plain interactive `apply` displays that local preflight and writes only after exact `y`/`yes`; use `apply --dry-run` for prompt-free preflight or `apply --approve` for non-interactive automation. Retrieval is live by default and requires `TURBOPUFFER_API_KEY`; use `retrieve --dry-run` (or `--plan`) for preview. Explicit `--namespace` retrieval previews remain local-only, while automatic previews perform read-only remote discovery and catalog reads. Compatibility flag `retrieve --live` remains accepted as a no-op.

## Choose a source

The same workflow accepts websites, repositories, documents, and database relations:

```bash
# Website
uv run buoy plan https://example.com/
# Public GitHub repository
uv run buoy plan https://github.com/owner/repository
# Local document
uv run buoy plan ./research-notes.pdf
# DuckDB table or view (backend is inferred for this compatible form)
uv run buoy plan ./knowledge.duckdb --relation main.documents --source-id product-docs
# BigQuery table or view (Application Default Credentials)
uv run buoy plan --database-backend bigquery \
  --relation source-project.corpus.documents --source-id product-docs
# Snowflake table or view (named connector connection)
uv run buoy plan --database-backend snowflake \
  --relation ANALYTICS.CORPUS.DOCUMENTS --source-id product-docs \
  --snowflake-connection analytics
```

Install remote warehouse support only when needed:

```bash
uv sync --extra bigquery
uv sync --extra snowflake
```

Buoy does not run dlt, dbt, SQLMesh, API extraction, or upstream transformations. Any number of normalized upstream tables may feed one final document-shaped table or view, but each Buoy command reads exactly one final relation. One row is one logical document with `document_id` and `content`, plus optional `title`; a long row may become multiple chunks and vector rows. Ordinary mappings remain available through `--id-column`, `--content-column`, and `--title-column`.

Remote `plan` and `crawl` authenticate only to the selected source warehouse and make source API calls. They do not read turbopuffer credentials or write to turbopuffer. `apply`, including `apply --dry-run`, reads only the integrity-verified saved plan and never reconnects to DuckDB, BigQuery, or Snowflake. Logical identities depend only on backend and `--source-id`, not paths, billing projects, connection profiles, credentials, job IDs, or relation contents. See [Index sources safely](docs/indexing.md) for the complete contract, BigQuery cost controls, Snowflake timeout behavior, provenance, and v1 exclusions.

## What happens

1. **Plan** — Scrapling, git, MarkItDown, or a read-only DuckDB/BigQuery/Snowflake relation scan produces local Markdown and deterministic chunks.
2. **Preflight** — `apply --dry-run` verifies artifacts and compares them with the local DuckDB ledger.
3. **Confirmed apply** — plain interactive `apply` prompts after preflight; the local BGE model then embeds only new or changed chunks and turbopuffer upserts them.
4. **Retrieve** — hybrid ANN + BM25 search returns ranked, citable source chunks.

Plans live under `artifacts/`; new applied state lives under `.buoy/`. Both are generated, local, and gitignored. Existing users should read [Migrating from turbo-search](docs/migrating-to-buoy.md).

## Optional Command Center

Run `uv sync --extra ui && uv run buoy serve` for a loopback-only, read-only console. It inspects local plans and state without reconnecting to sources; remote refresh and search run only when explicitly requested. It cannot apply, delete, mutate catalogs, or extract graphs. See the [Command Center guide](docs/command-center.md).

## Details on demand

- [Index sources safely](docs/indexing.md) — source support, crawl controls, plan artifacts, incremental state, approved apply, and stale deletion.
- [Retrieve and rank results](docs/retrieval.md) — dry runs, live search, citations, and namespace-aware ranking.
- [Manage the remote namespace catalog](docs/catalog.md) — authenticated cards, lifecycle commands, permissions, migration, and recovery.
- [Evaluate search quality](docs/evaluation.md) — smoke datasets, repository metrics, and one-shot autoresearch.
- [Migrate to Buoy 0.2](docs/migrating-to-buoy.md) — command, import, environment, state, and plan compatibility.
- [Contribute](CONTRIBUTING.md) or [prepare a GitHub release](docs/releasing.md).

The CLI is the exhaustive option reference: `uv run buoy --help` and `uv run buoy plan --help`.

## Optional global command

Run `uv tool install --editable . --force`, then `buoy --help`. Generated artifacts and state are created in the command's working directory.

## Development

Run `uv run python -m unittest discover -s tests -p 'test_*.py'`.

Licensed under [Apache-2.0](LICENSE).
