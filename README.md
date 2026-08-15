<p align="center">
  <img src="images/buoy.svg" alt="Buoy" width="160">
</p>

# Buoy

*Search that stays anchored to the source.* [![CI](https://github.com/Doctacon/buoy/actions/workflows/ci.yml/badge.svg)](https://github.com/Doctacon/buoy/actions/workflows/ci.yml) [![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

Buoy turns trusted sources into reviewed Turbopuffer search indexes, then finds
the right indexed corpus for a question and returns anchored citations. It can
acquire a website, public GitHub repository, local document, or one
document-shaped DuckDB, BigQuery, or Snowflake relation; create a compact local
plan; apply the approved delta to one namespace; and search up to three
cataloged namespaces in one request.

Buoy owns this bounded index-and-retrieve loop. Broader evidence systems,
taxonomy, policy, and cross-plan operations remain in
[Kite](https://github.com/Doctacon/kite).

## Install

Buoy requires Python 3.11 or newer. Install the released wheel directly from
GitHub:

```bash
uv tool install "https://github.com/Doctacon/buoy/releases/download/v0.5.1/buoy_search-0.5.1-py3-none-any.whl"
buoy --version
```

The v0.5.1 wheel is the current published security release. It predates the
automatic multi-corpus and `catalog` behavior in this branch, so v0.5.1
retrieval requires one explicit `--namespace`. Sections marked **Unreleased**
below describe the next-release source tree, not the v0.5.1 wheel.

## First GitHub repository index

```bash
# 1. Create reviewable plan.json + delta.duckdb artifacts.
buoy plan https://github.com/Doctacon/buoy \
  --namespace github-doctacon-buoy-v1 \
  --out-dir artifacts/buoy-repo

# 2. Verify the exact plan and preview its changes locally.
buoy apply --plan artifacts/buoy-repo/plan.json --dry-run

# 3. Apply only after review.
export TURBOPUFFER_API_KEY=...
buoy apply --plan artifacts/buoy-repo/plan.json --approve --json

# 4. Search the reviewed namespace (works in released v0.5.1 and development).
buoy retrieve "How does repository indexing work?" \
  --namespace github-doctacon-buoy-v1
```

**Unreleased:** after a development build successfully registers the catalog
card, the same search may omit `--namespace` and let Buoy select the corpus.

Plain interactive `apply` shows the same local preflight and accepts only exact
`y`/`yes` before live work. Automation must request `--json` to receive the
versioned receipt and shell-safe preview/live retrieval commands; that receipt
is Kite's integration boundary.

Buoy reads credentials only from the process environment; it never loads
`.env` automatically. `TURBOPUFFER_NAMESPACE` is not routing authority.

## Retrieval and catalog (Unreleased)

With no `--namespace`, retrieval checks the live namespace inventory and the
remote routing catalog, selects one to three compatible corpora, and searches
them. Preview the route without querying content:

```bash
export TURBOPUFFER_API_KEY=...
buoy retrieve "How is vector recall evaluated?" --dry-run
buoy retrieve "How is vector recall evaluated?"
```

Repeat `--namespace` to bypass automatic routing and search a known set of at
most three corpora:

```bash
buoy retrieve "Compare the two approaches" \
  --namespace site-example-one-v1 \
  --namespace site-example-two-v1
```

Live text is compact and citation-first by default:

```text
Found 1 passage.

1. Retry behavior
   https://docs.example.com/retries · Backoff
   Requests use bounded exponential backoff and stop after the configured...
```

Each excerpt is whitespace-collapsed and capped at 320 characters. Use
`--explain` for the existing detailed text diagnostics, or `--json` for the
unchanged structured result; the two flags cannot be combined. Dry-run and
plan output remain detailed. These modes render the same retrieval result:
routing, ranking, per-corpus coverage promotion, evidence assessment, and
provider calls do not change. Partial-failure and evidence-assessment-failure
warnings remain prominent, and abstention/inconclusive messages are unchanged.
Compact retrieval returns passages and citations; it does not synthesize an
answer.

An approved apply registers or refreshes that namespace's routing card after
content and local state commit. Catalog inspection is read-only; mutations are
previews until separately approved:

```bash
buoy catalog list
buoy catalog show site-example-one-v1
buoy catalog disable site-example-one-v1       # preview
buoy catalog disable site-example-one-v1 --approve
```

Multi-corpus results are deduplicated and locally reranked. Automatic retrieval
also checks the relevance of its best final result with the same pinned MiniLM
model. This check runs for both normal text and JSON output. A single explicit
`--namespace` keeps the established raw-search path and bypasses this automatic
evidence check.
Successful corpora are still returned if another selected namespace fails,
with the result marked `incomplete`; failure of every attempted namespace fails
the request.

The provisional cutoff is `-8.0`. This is a raw model score, not a percentage
or probability. In the first 50-question diagnostic, it separated the five
questions labeled `no_answer` (`-11.2867` to `-9.6270`) from the 45 labeled
`answer_expected` (`-5.8328` and above). Those labels describe the questions,
not whether the returned passages were actually relevant. One known
counterexample scored `-5.8328` and was accepted despite returning unrelated
Dagster, Oscilar, and Thistle passages for a Turbopuffer vector-recall question.
The project owner explicitly approved packaged revision
`owner-approved-provisional-minus-8-v1` on 2026-08-14 despite this limitation.
There is no command-line, environment, or runtime threshold override. The
cutoff must be monitored and may change only through a new reviewed packaged
revision as broader passage-level judgments are collected.

If a confident one-corpus result is below the cutoff, Buoy widens once to the
next two likely corpora. If the final result is still weak and every search
succeeded, Buoy returns no hits and says that it found no sufficiently relevant
evidence in the indexed corpora. If any selected corpus failed, it reports the
result as inconclusive instead of making that claim. Buoy never claims that no
answer exists.

Multi-corpus ordering uses the exact cached
`cross-encoder/ms-marco-MiniLM-L-6-v2` revision documented in
[`docs/retrieval.md`](docs/retrieval.md). Buoy never downloads or substitutes a
model during retrieval. The snapshot is about 88 MB and is already cached on
the development Mac; with the routing model already loaded, reranking 24
candidates measured about 0.58 seconds and 151 MiB of additional peak memory.
A missing cache produces an explicit error before Buoy presents a blended
result.

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
- Apply acquires a namespace lock, writes only the plan's content namespace,
  commits local DuckDB state after content writes succeed, then registers its
  routing card; stale IDs are deleted only when explicitly requested.
- Explicit retrieval previews are local and credential-free. Automatic
  previews require credentials because they read live inventory and routing
  cards, but they do not query content or write provider state.
- Automatic retrieval considers only complete, enabled, compatible routing
  cards and queries at most three content namespaces.
- Catalog mutations preview by default and require `--approve`; they never
  delete or alter a content namespace.

## Contributor setup

Clone the repository only when developing Buoy itself:

```bash
git clone https://github.com/Doctacon/buoy.git
cd buoy
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
- [Automatic and explicit retrieval](docs/retrieval.md)
- [Evaluation](docs/evaluation.md)
- [Buoy/Kite split and legacy-state handling](docs/kite-split.md)
- [Migration](docs/migrating-to-buoy.md)
- [Release process](docs/releasing.md)

Buoy is licensed under Apache-2.0.
