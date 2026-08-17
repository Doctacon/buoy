<p align="center">
  <img src="images/buoy.svg" alt="Buoy" width="160">
</p>

# Buoy

*Search that stays anchored to the source.* [![CI](https://github.com/Doctacon/buoy/actions/workflows/ci.yml/badge.svg)](https://github.com/Doctacon/buoy/actions/workflows/ci.yml) [![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

Buoy is a command-line tool that turns knowledge you trust into search your
apps and agents can use. Point it at a website, public GitHub repository, local
document, or prepared database table or view. Buoy builds a search index in
Turbopuffer, then returns relevant passages with citations to their sources.

Use Buoy to help an internal tool search trusted information, give an AI
assistant relevant source material, or explore documentation while keeping
links to the originals.

## What you get

- One workflow for indexing documentation, code, files, and prepared data.
- A review step before anything is added to your live search index.
- Incremental updates, so you can inspect what changed between runs.
- Ranked passages with citations back to the original source.

Buoy retrieves evidence; it does not generate an answer or run the rest of
your data or AI stack.

## How it works

1. **Plan:** Buoy reads a source, breaks it into searchable passages, and
   prepares a local summary of what would change.
2. **Review and apply:** You inspect that plan and explicitly approve the
   changes before Buoy writes them to Turbopuffer.
3. **Search:** Ask a question and get the most relevant source passages with
   citations.

Run the same flow again when a source changes. Buoy compares it with the last
applied version so you can review the update instead of starting over blindly.

## Quick start

For this example, you need Python 3.11 or newer, `uv`, Git, and a Turbopuffer
account with an API key. Install the published wheel from GitHub:

```bash
uv tool install "https://github.com/Doctacon/buoy/releases/download/v0.5.1/buoy_search-0.5.1-py3-none-any.whl"
buoy --version
```

Create a plan for a source:

```bash
buoy plan https://github.com/Doctacon/buoy \
  --namespace github-doctacon-buoy-v1
```

Buoy prints the saved plan path under
`~/.buoy/artifacts/site-crawls/`. When that directory contains exactly one
supported pending plan, `apply` can select it without a path.

Verify the saved plan and preview its change summary without touching
Turbopuffer:

```bash
buoy apply --dry-run
```

When the plan looks right, apply it and search the result:

```bash
export TURBOPUFFER_API_KEY=...
buoy apply --approve
buoy retrieve "How does repository indexing work?" \
  --namespace github-doctacon-buoy-v1
```

If more than one pending plan exists, Buoy refuses to guess; pass the exact
printed `plan.json` path with `--plan`.

Planning may fetch or query the source itself. In the walkthrough above,
`plan` and `apply --dry-run` do not connect to Turbopuffer; the approved
`apply` writes to it, and `retrieve` reads from it.

## Local storage

A `uv tool` installation makes the `buoy` command available across your
computer. Buoy's own mutable files also use one user-global default rather
than whichever directory you happen to run it from:

- applied-state databases live under `~/.buoy/state/`;
- crawl output and pending plans live under
  `~/.buoy/artifacts/site-crawls/`.

Existing project-local `.buoy`, `.turbo-search`, and
`artifacts/site-crawls` paths are not implicitly scanned, moved, backfilled, or
deleted. You can continue using supported old state and plans by passing their
exact paths with `--state-root`, `--out-dir`, and `--plan`. Once selected, an
old state root receives normal state writes and a successfully applied old plan
retains the normal verified cleanup lifecycle.

This Buoy home does not relocate package-manager or model-download caches.
`uv`, Hugging Face, and Sentence Transformers continue to use their own cache
locations.

## Supported sources

- Websites
- Public GitHub repositories
- Local documents such as PDFs, Word files, presentations, and spreadsheets
- Prepared document tables or views in DuckDB, BigQuery, or Snowflake

## Learn more

- [Index a source and safely apply updates](docs/indexing.md)
- [Understand retrieval in the current source tree](docs/retrieval.md)
- [Evaluate search quality](docs/evaluation.md)
- [Migrate from earlier versions](docs/migrating-to-buoy.md)
- [Contribute to Buoy](CONTRIBUTING.md)
- [Release Buoy](docs/releasing.md)

Buoy is licensed under the [Apache License 2.0](LICENSE).
