# Scrapling site workflow for turbopuffer RAG

## Goal

Turn an arbitrary public website into a cost-conscious searchable RAG namespace:

```text
base URL
  -> namespace candidate
  -> Scrapling crawl
  -> clean Markdown/text + metadata
  -> chunks
  -> local embeddings
  -> turbopuffer namespace
  -> hybrid retrieval with citations
```

## Default crawl policy

- Default to sitemap/robots discovery, with same-domain link crawling only when sitemap discovery yields no pages.
- Use `--crawl-strategy hybrid` for explicit exhaustive sitemap plus same-domain link discovery.
- Use `--crawl-strategy link` to ignore sitemaps.
- Use repeatable `--include-path` / `--exclude-path` globs to shape the corpus before apply, e.g. `--exclude-path /llms-full.txt`.
- Strip trailing slashes by default so `/docs/query` and `/docs/query/` canonicalize to one page; use `--keep-trailing-slash` only when variants must be preserved.
- Obey robots.txt by default.
- Restrict to the base URL host/domain unless the user approves otherwise.
- Default planning caps are intentionally useful for larger docs sites: `3000` pages and `120000` chunks.
- Default docs-version policy is `warn`: detect repeated `/docs/{version}/...` sitemap families and stop before page crawling so the user chooses intentionally. Use `--docs-version-policy latest`, `stable-latest`, `latest-nightly`, or `all` when a site has duplicated version docs.
- Lower caps for smoke tests when needed:
  - `--max-pages 10` or `25`
  - `--max-chunks 100` or `200`
  - low concurrency, e.g. `2`
  - crawl delay, e.g. `0.25` to `1.0` seconds
- Use static HTTP fetching first. Escalate to browser rendering only when pages are empty or clearly JavaScript-dependent.

## Preview and plan CLI

Use `crawl` for a simple local crawl/chunk preview:

```bash
uv run buoy crawl \
  --base-url "https://scrapling.readthedocs.io/en/latest/" \
  --max-pages 10 \
  --max-chunks 100 \
  --css-selector ".md-content__inner" \
  --json
```

Use `plan` for Terraform-like review/apply artifacts and incremental diffing against local state:

```bash
uv run buoy plan \
  "https://scrapling.readthedocs.io/en/latest/" \
  --out-dir artifacts/site-crawls/scrapling-readthedocs-io-plan \
  --css-selector ".md-content__inner"
```

Interactive text-mode `crawl` and `plan` runs show a one-line stderr progress indicator by default. It is suppressed for `--json`, non-TTY stderr, and `--no-progress`. Progress labels use explicit `cap=` wording for crawl limits; sitemap crawl labels include a sitemap-derived page estimate after matching sitemap URLs are discovered.

Expected safety fields for crawl/plan:

```json
{
  "dry_run": true,
  "turbopuffer_api_calls": false,
  "credentials_required": false
}
```

The CLI writes local generated Markdown pages under the requested `artifacts/...` output directory and chunks them with the existing `buoy_search.chunker` Markdown pipeline. `artifacts/` is gitignored. Plan also writes `plan.json`, `summary.json`, `manifest.json`, and `chunks.jsonl`. New projects use gitignored `.buoy/` state; an existing lone `.turbo-search/` root remains in-place compatible under the 0.2 migration contract. Use `--css-selector` when a docs site has clear main-content wrappers; this reduces nav/sponsor/sidebar noise before chunking.

## Metadata to preserve per page

At minimum:

- `url`
- `title`
- `status`
- `content_type`
- `source_hash`
- `crawl_timestamp`
- `fetcher` / crawl mode

Future production indexing should also consider:

- canonical URL
- final redirected URL
- HTTP headers relevant to cache validation, e.g. `etag` and `last-modified`
- sitemap source URL if discovered from sitemap
- crawl depth
- language

## Namespace naming

Use a deterministic, URL-derived candidate with a version suffix:

```text
site-<host-slug>-v1
```

Examples:

- `https://example.com/` -> `site-example-com-v1`
- `https://scrapling.readthedocs.io/en/latest/` -> `site-scrapling-readthedocs-io-v1`

Ask before creating/writing a namespace. Never delete or overwrite an existing namespace unless the user explicitly approves deletion/replacement.

## Apply sequence

Apply has explicit prompt-free preflight, normal interactive confirmation, and prompt-free automation modes.

Preflight, no credentials or live calls:

```bash
uv run buoy apply --dry-run
```

By default, apply uses the newest `artifacts/site-crawls/**/plan.json` and the namespace recorded in that plan. Pass `--json --dry-run` for scripts. Pass `--plan` or `--namespace` only when overriding those defaults.

Normal interactive apply, only after explicit user approval and after `TURBOPUFFER_API_KEY` is already in the environment:

```bash
uv run buoy apply
```

It displays complete preflight and prompts `Apply this plan? [y/N]`; only exact `y`/`yes` proceeds. Use `uv run buoy apply --approve` only for separately authorized non-interactive automation.

Stale row deletion is off by default. Preflight with `--dry-run --delete-stale` reports exact stale row IDs without live calls. Live stale deletion requires interactive confirmation with `--delete-stale`, or both `--approve` and `--delete-stale` for automation:

```bash
uv run buoy apply --approve --delete-stale
```

Only after explicit user approval:

1. Run `plan` and inspect page/chunk counts, samples, and diff.
2. Run apply preflight and confirm namespace, rows to upsert, embeddings to generate, stale rows, and local state path.
3. Retrieve `TURBOPUFFER_API_KEY` into shell memory only.
4. Set `TURBOPUFFER_REGION` and `TURBOPUFFER_NAMESPACE` in shell only.
5. Run approved apply; it embeds/upserts only new or changed chunks.
6. Delete stale rows only with `--delete-stale`; this deletes row IDs only, not namespaces.
7. Record evidence without secret values or private credential identifiers.

## Retrieval validation

After an explicitly approved apply, generic retrieval/eval commands can target the site namespace without code changes:

```bash
uv run buoy retrieve \
  "How does Scrapling LinkExtractor filter links?" \
  --dry-run \
  --namespace site-scrapling-readthedocs-io-v1 \
  --json

uv run buoy evals \
  --dry-run \
  --dataset src/buoy_search/data/scrapling_retrieval_smoke_evals.json \
  --namespace site-scrapling-readthedocs-io-v1 \
  --json
```

Dry-run/list mode is credential-free and turbopuffer-free. Live retrieval/evals require `--live` and `TURBOPUFFER_API_KEY` in the environment; do not run them without explicit user approval.

## Known gaps before productionizing

The current implementation has a local-first plan/apply workflow but still needs:

- remote/shared state backend for multi-machine workflows
- resumable crawl manifests
- HTTP cache metadata such as `etag`/`last-modified` for crawl efficiency
- local content store for cost-optimized turbopuffer rows
- namespace lifecycle commands with explicit safety prompts
