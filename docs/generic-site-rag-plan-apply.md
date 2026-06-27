# Generic site/repository RAG plan/apply workflow

This workflow is the Terraform-like path for turning a public website crawl or public GitHub repository into a reviewed, incremental turbopuffer index.

## Safety model

There are three distinct modes:

1. **Plan**: local-only preview. Crawls, extracts, chunks, compares with local applied state, and writes review artifacts. It does not read credentials, load embeddings, create namespaces, or call turbopuffer.
2. **Apply preflight**: local-only verification of a saved plan. It recomputes artifact hashes and local diff state. It does not read credentials, load embeddings, or call turbopuffer.
3. **Approved apply**: explicit live mutation. It requires `--approve` and `TURBOPUFFER_API_KEY` in the environment. It embeds/upserts only new or changed chunks from the recomputed diff.

Stale deletes have an additional guardrail: stale rows are retained by default. Live stale deletion requires both `--approve` and `--delete-stale`.

## Plan

Website example:

```bash
uv run turbo-search plan \
  "https://scrapling.readthedocs.io/en/latest/" \
  --out-dir artifacts/site-crawls/scrapling-readthedocs-io-plan \
  --css-selector ".md-content__inner"
```

GitHub repository example:

```bash
uv run turbo-search plan https://github.com/Doctacon/open-streaming-lab
```

GitHub repository URLs are detected automatically and ingested from git-tracked repository contents, not rendered GitHub UI pages. The default namespace is repo-specific, e.g. `github-doctacon-open-streaming-lab-v1`.

Plan artifacts:

```text
plan.json
summary.json
manifest.json
chunks.jsonl
pages/*.md
```

The plan compares generated chunks to local applied state under `.turbo-search/state/...` unless `--state-root` is supplied. `.turbo-search/` is local state and is gitignored.

### Crawl discovery strategy

`plan` and `crawl` support `--crawl-strategy`:

- `hybrid` (default): merge robots/sitemap pages with same-site link crawling from the base URL. This is best for RAG completeness and catches partial sitemaps.
- `sitemap`: use robots/sitemap discovery; fall back to link crawling only when the sitemap path yields no pages. Use this for a lighter, sitemap-trusting crawl.
- `link`: ignore sitemap URLs and crawl same-site links from the base URL.

Hybrid/link crawling still obeys robots.txt, host restrictions, page caps, concurrency, and delay settings. Default website planning caps are `250` pages and `10000` chunks; default GitHub repository caps are `5000` repo files and `100000` chunks. Lower them for smoke tests or raise them for unusually large sources.

### Path filters and URL canonicalization

Use repeatable path globs to shape the local corpus before a live apply:

```bash
uv run turbo-search plan https://turbopuffer.com/ \
  --exclude-path /llms-full.txt
```

For websites:

- `--include-path /docs/**` includes only matching URL paths; `/docs/**` also matches `/docs`.
- `--exclude-path /llms-full.txt` removes matching URL paths from sitemap and link discovery.
- trailing slashes are stripped by default so `/docs/query` and `/docs/query/` canonicalize to one page.
- `--keep-trailing-slash` preserves trailing-slash variants when a site needs that behavior.

For GitHub repositories, `--include-path` and `--exclude-path` match repo-relative file paths:

```bash
uv run turbo-search plan https://github.com/owner/repo --include-path 'docs/**'
uv run turbo-search plan https://github.com/owner/repo --exclude-path 'dist/**'
```

## Apply preflight

```bash
uv run turbo-search apply
```

By default, `apply` selects the newest `artifacts/site-crawls/**/plan.json` and uses the namespace recorded in that plan. Pass `--json` for scripts/automation. Pass `--plan <plan.json>` or `--namespace <namespace>` only when you want to override those defaults.

Preflight verifies:

- plan schema and namespace;
- `manifest.json` and `chunks.jsonl` match;
- embedding-text hashes are still valid;
- artifact hash matches reviewed content/options;
- local applied state is compatible.

Preflight makes no live calls and does not read `TURBOPUFFER_API_KEY`.

## Approved apply

Only after reviewing plan artifacts and accepting the namespace shown by preflight:

```bash
uv run turbo-search apply --approve
```

Approved apply:

- requires `TURBOPUFFER_API_KEY` from the environment;
- embeds only rows selected by the freshly recomputed diff;
- upserts only those rows;
- updates local applied state only after successful live work;
- retains stale rows by default as `retained_stale` in local state.

Do not store API keys, private vault names, item titles, share IDs, or token values in files.

## Stale delete guardrail

Preview exact stale deletes without live calls:

```bash
uv run turbo-search apply --delete-stale
```

Actually delete stale rows only with both flags:

```bash
uv run turbo-search apply --approve --delete-stale
```

`--delete-stale` deletes exact stale row IDs from the recomputed diff. It does not delete namespaces.

## Retrieval and eval validation

After a site has been applied with explicit approval, retrieval and eval commands can target that generic namespace with CLI overrides. Dry-run retrieval planning remains local-only:

```bash
uv run turbo-search retrieve \
  "How does Scrapling LinkExtractor filter links?" \
  --dry-run \
  --namespace site-scrapling-readthedocs-io-v1 \
  --region gcp-us-central1 \
  --json
```

List the Scrapling docs eval cases without credentials or live calls:

```bash
uv run turbo-search evals \
  --dry-run \
  --dataset src/turbo_search/data/scrapling_retrieval_smoke_evals.json \
  --namespace site-scrapling-readthedocs-io-v1 \
  --json
```

Live generic retrieval/evals remain explicitly gated by `--live` and `TURBOPUFFER_API_KEY` in the environment:

```bash
uv run turbo-search evals \
  --live \
  --dataset src/turbo_search/data/scrapling_retrieval_smoke_evals.json \
  --namespace site-scrapling-readthedocs-io-v1 \
  --json
```

Do not run live retrieval/evals unless the namespace has been applied and the user explicitly approves live validation.

## What is still not automatic

- Remote/shared state is not implemented; state is local-first.
- Live generic applies/deletes/retrievals/evals should only be run when explicitly approved for the current site/namespace.
- Live SDK compatibility should be validated on a disposable namespace before relying on generic apply for production use.
