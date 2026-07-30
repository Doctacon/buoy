<p align="center">
  <img src="images/buoy.svg" alt="Buoy" width="160">
</p>

# Buoy

*Search that stays anchored to the source.* [![CI](https://github.com/Doctacon/buoy/actions/workflows/ci.yml/badge.svg)](https://github.com/Doctacon/buoy/actions/workflows/ci.yml) [![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

Buoy turns one source into one reviewed Turbopuffer search index. It can
acquire a website, public GitHub repository, local document, or one
document-shaped DuckDB, BigQuery, or Snowflake relation; create a compact local
plan; apply the approved delta to one namespace; and search that namespace with
anchored citations.

Buoy is deliberately not an account-wide catalog, semantic router, ontology
engine, or operator console. Those cross-source capabilities now belong to
[Kite](https://github.com/Doctacon/kite).

## Workflow

```bash
# 1. Inspect one source without writing to Turbopuffer.
buoy crawl --base-url https://example.com/docs --json

# 2. Create reviewable plan.json + delta.duckdb artifacts.
buoy plan https://example.com/docs \
  --namespace site-example-docs-v1 \
  --out-dir artifacts/example-plan

# 3. Review locally.
buoy apply --plan artifacts/example-plan/plan.json --dry-run

# 4. Apply only after review.
export TURBOPUFFER_API_KEY=...
buoy apply --plan artifacts/example-plan/plan.json --approve --json

# 5. Search the one explicit index.
buoy retrieve "How does authentication work?" \
  --namespace site-example-docs-v1
```

Plain interactive `apply` shows the same local preflight and accepts only exact
`y`/`yes` before live work. Automation must request `--json` to receive the
versioned receipt and shell-safe preview/live retrieval commands; that receipt
is Kite's integration boundary.

`retrieve` and `evals` require one singular `--namespace`.
`TURBOPUFFER_NAMESPACE` is intentionally not routing authority.

## Source support

- HTTP(S) websites through Scrapling, with exact-host, sitemap, language,
  docs-version, path, and resource limits;
- public GitHub repositories through a bounded shallow clone;
- local PDF, DOCX, PPTX, XLS/XLSX, and other MarkItDown-supported documents;
- one document-shaped DuckDB, BigQuery, or Snowflake table/view.

Database ingestion expects an already-shaped relation with stable ID and
content columns. Upstream extraction, transformation, replay, and warehouse
orchestration stay outside Buoy.

## Safety model

- Planning never reads Turbopuffer credentials or writes to Turbopuffer.
- Plans are content-addressed, baseline-bound, and fully reverified before
  apply.
- Apply acquires a namespace lock, writes only the plan's namespace, commits
  local DuckDB state after remote success, and deletes stale IDs only when
  explicitly requested.
- Retrieval previews are local and credential-free.
- Buoy performs no namespace listing, routing-catalog read/write, evidence
  snapshot, or cross-namespace fusion.

## Install and develop

Buoy requires Python 3.11 or newer.

```bash
uv sync --locked --python 3.13
uv run buoy --help
PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover -s tests -p 'test_*.py' -q
```

Optional warehouse adapters:

```bash
uv sync --locked --extra bigquery
uv sync --locked --extra snowflake
```

## Documentation

- [Indexing and applying](docs/indexing.md)
- [Single-namespace retrieval](docs/retrieval.md)
- [Evaluation](docs/evaluation.md)
- [Buoy/Kite split and legacy-state handling](docs/kite-split.md)
- [Migration](docs/migrating-to-buoy.md)
- [Release process](docs/releasing.md)

Buoy is licensed under Apache-2.0.
