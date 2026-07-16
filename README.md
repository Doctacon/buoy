# Buoy

[![CI](https://github.com/Doctacon/buoy-search/actions/workflows/ci.yml/badge.svg)](https://github.com/Doctacon/buoy-search/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/github/license/Doctacon/buoy-search)](LICENSE)

<img src="images/buoy.svg" height="120" alt="Buoy navigation marker logo" />

Turn a public website, GitHub repository, or local document into a reviewed, incremental [turbopuffer](https://turbopuffer.com/) search index.

**Search that stays anchored to the source.**

## Quick start

Requires [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

Build and search a website index:

```bash
# 1. Fetch, chunk, and plan locally. No Turbopuffer credentials, embeddings, or calls.
uv run buoy plan https://example.com/

# 2. Verify the plan and preview its diff. Still local-only.
uv run buoy apply

# 3. Approve the reviewed diff and write it to turbopuffer.
export TURBOPUFFER_API_KEY="..."
uv run buoy apply --approve

# 4. Search the resulting namespace.
uv run buoy retrieve \
  "How does this feature work?" \
  --live \
  --namespace site-example-com-v1
```

`plan` may fetch a public source, but it does not read Turbopuffer credentials, load embeddings, or contact Turbopuffer. Writes and searches require `--approve` or `--live` plus `TURBOPUFFER_API_KEY`; preflight and retrieval previews remain local-only.

## Choose a source

The same workflow accepts three source types:

```bash
# Website
uv run buoy plan https://example.com/

# Public GitHub repository
uv run buoy plan https://github.com/owner/repository

# Local document
uv run buoy plan ./research-notes.pdf
```

Source type and namespace are detected automatically. Use `uv run buoy plan --help` to shape a crawl, filter repository paths, or inspect supported options.

## What happens

1. **Plan** — Scrapling, git, or MarkItDown produces local Markdown and deterministic chunks.
2. **Preflight** — `apply` verifies artifacts and compares them with the local DuckDB ledger.
3. **Approved apply** — the local BGE model embeds only new or changed chunks, then turbopuffer upserts them.
4. **Retrieve** — hybrid ANN + BM25 search returns ranked, citable source chunks.

Plans live under `artifacts/`; new applied state lives under `.buoy/`. Both are generated, local, and gitignored. Existing users should read [Migrating from turbo-search](docs/migrating-to-buoy.md).

## Details on demand

- [Index sources safely](docs/indexing.md) — source support, crawl controls, plan artifacts, incremental state, approved apply, and stale deletion.
- [Retrieve and rank results](docs/retrieval.md) — dry runs, live search, citations, and namespace-aware ranking.
- [Manage the local namespace catalog](docs/catalog.md) — manual cards, local vectors, lifecycle commands, and path precedence.
- [Evaluate search quality](docs/evaluation.md) — smoke datasets, repository metrics, and one-shot autoresearch.
- [Migrate to Buoy 0.2](docs/migrating-to-buoy.md) — command, import, environment, state, and plan compatibility.
- [Contribute](CONTRIBUTING.md) or [prepare a GitHub release](docs/releasing.md).

The CLI is the exhaustive option reference:

```bash
uv run buoy --help
uv run buoy plan --help
```

## Optional global command

```bash
uv tool install --editable . --force
buoy --help
```

Generated artifacts and state are created in the directory where the installed command runs.

## Development

```bash
uv run python -m unittest discover -s tests -p 'test_*.py'
```

Licensed under [Apache-2.0](LICENSE).
