Status: active
Created: 2026-06-20
Updated: 2026-06-20

# Generic Website RAG Dry-Run Crawl

## Purpose and scope

This spec covers the first productionizing step for the generic website-to-RAG workflow: a first-class `turbo-search crawl` dry-run CLI that can take a public base URL, crawl a small capped set of same-site pages with Scrapling, extract clean Markdown, chunk it with the existing Markdown indexer, and report the namespace/indexing plan without reading credentials or contacting turbopuffer.

This spec does **not** cover live turbopuffer writes, namespace deletion/replacement, browser-rendered crawling, arbitrary-namespace live retrieval, or incremental recrawls. Those require separate approval and tickets.

## Behavior

### Command shape

The CLI provides a new command:

```bash
turbo-search crawl --base-url <url> [options]
```

The command is dry-run/local-only by design. It must report:

- `dry_run: true`
- `credentials_required: false`
- `turbopuffer_api_calls: false`
- `api_calls_occurred: false`

### Inputs

Minimum required input:

- `--base-url`: absolute `http` or `https` URL.

Supported dry-run controls:

- `--out-dir`: local generated artifact directory, default under `artifacts/`.
- `--max-pages`: cap on pages to scrape.
- `--max-chunks`: cap on generated chunks.
- `--concurrent-requests`: global Scrapling concurrency.
- `--concurrent-requests-per-domain`: per-domain concurrency.
- `--download-delay`: polite crawl delay.
- `--css-selector`: optional site-specific main-content selector.
- `--target-tokens`: chunk target token count.
- `--overlap-sentences`: chunk overlap.
- `--json`: print JSON summary. Text output may be added, but JSON should be available for tests/automation.

### Crawl strategy

The first implementation should be sitemap-first:

1. Try to discover sitemap URLs from `robots.txt` and conventional sitemap locations.
2. Crawl pages listed in sitemap(s), restricted to the base host/domain and caps.
3. If sitemap discovery yields no pages, fall back to capped same-domain link crawling from the base URL.

The crawler must use Scrapling for fetch/parse/extraction mechanics. It must obey robots.txt and use conservative concurrency/delay defaults.

### Extraction behavior

Scrapling handles content extraction/conversion. The product decision here is not whether to implement extraction ourselves; it is how much control to expose over Scrapling extraction for RAG quality.

Default behavior:

- Use Scrapling to fetch and parse pages.
- Use Scrapling's Markdown conversion / AI-targeted body cleanup path where available.
- Preserve title, URL, status, content type, source hash, crawl timestamp, and fetcher/mode metadata.

Optional selector behavior:

- If `--css-selector` is supplied, pass it through to Scrapling extraction to scope content to the site’s main content wrapper.
- This is important because Scrapling can convert a page to Markdown, but it cannot always know which page regions are semantically useful for RAG on every arbitrary website.

### Output artifacts

The command writes a generated Markdown corpus under the output directory, e.g.:

```text
artifacts/site-crawls/<host>/pages/*.md
artifacts/site-crawls/<host>/summary.json
```

Each generated Markdown file includes frontmatter with at least:

- `url`
- `title`
- `status`
- `content_type`
- `source_hash`
- `crawl_timestamp`
- `fetcher`

The generated Markdown corpus is then chunked with the existing `turbo_search.indexer.process_corpus` flow.

### Namespace planning

The command reports a deterministic namespace candidate from the base URL:

```text
site-<host-slug>-v1
```

Example:

```text
https://scrapling.readthedocs.io/en/latest/ -> site-scrapling-readthedocs-io-v1
```

The dry-run command must not create this namespace.

## Acceptance criteria

- `turbo-search crawl --base-url ... --max-pages ... --max-chunks ... --json` exists.
- The command validates that `--base-url` is absolute HTTP(S).
- The command performs no credential reads and no turbopuffer API calls.
- The command writes a local Markdown corpus and `summary.json` under `--out-dir`.
- The command chunks the generated Markdown using the existing indexer.
- Summary includes crawl counts, chunk counts, namespace candidate, safety booleans, and sample chunks.
- Tests cover namespace slugging, base URL validation, generated Markdown frontmatter, CLI dry-run output, and no-credentials/no-turbopuffer safety fields.
- Existing tests continue to pass.

## Constraints

- Use Scrapling for crawling/fetching/extraction rather than building an independent web scraper.
- Keep live writes out of scope.
- Keep secrets out of files and test output.
- Follow project open-source preference.
