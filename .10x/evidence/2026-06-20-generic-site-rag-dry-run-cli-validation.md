Status: recorded
Created: 2026-06-20
Updated: 2026-06-20
Relates-To: .loom/tickets/2026-06-20-generic-site-rag-dry-run-cli.md, .loom/specs/generic-website-rag-dry-run-crawl.md

# Generic Site RAG Dry-Run CLI Validation

## What was observed

The first-class `turbo-search crawl` CLI was implemented and validated. The command is dry-run/local-only and reports no credential requirement or turbopuffer API activity.

Successful live-network smoke summary against Scrapling docs after final parent review:

```json
{
  "command": "crawl",
  "dry_run": true,
  "credentials_required": false,
  "turbopuffer_api_calls": false,
  "api_calls_occurred": false,
  "base_url": "https://scrapling.readthedocs.io/en/latest/",
  "allowed_host": "scrapling.readthedocs.io",
  "namespace_candidate": "site-scrapling-readthedocs-io-v1",
  "crawl_strategy": "sitemap",
  "max_pages": 3,
  "max_chunks": 15,
  "pages_scraped": 3,
  "requests_count": 6,
  "robots_disallowed_count": 0,
  "blocked_requests_count": 0,
  "failed_requests_count": 0,
  "chunks_generated": 15,
  "files_discovered": 3,
  "files_seen": 1,
  "files_error": 0,
  "limit_reached": true,
  "css_selector": ".md-content__inner"
}
```

Generated artifacts were written under:

- `artifacts/site-crawls/scrapling-readthedocs-io-cli-smoke-final/`

`artifacts/` is gitignored.

## Procedure

Unit tests for new crawl helpers:

```bash
PYTHONPATH=src python3 -m unittest tests.test_crawler -v
```

Result: 8 tests ran OK after adding stale generated page cleanup and host/netloc domain coverage.

Full test suite:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Result: 27 tests ran OK.

Full test suite through uv environment:

```bash
uv run python -m unittest discover -s tests -v
```

Result: 27 tests ran OK.

Compile checks:

```bash
PYTHONPATH=src python3 -m compileall -q src tests .pi/skills/turbopuffer-site-rag/scripts/scrapling_dry_crawl.py
uv run python -m compileall -q src tests
```

Result: both passed with no output.

Live-network dry-run smoke, no turbopuffer writes:

```bash
rm -rf artifacts/site-crawls/scrapling-readthedocs-io-cli-smoke-final && \
uv run turbo-search crawl \
  --base-url "https://scrapling.readthedocs.io/en/latest/" \
  --out-dir artifacts/site-crawls/scrapling-readthedocs-io-cli-smoke-final \
  --max-pages 3 \
  --max-chunks 15 \
  --css-selector ".md-content__inner" \
  --json
```

Result: passed, emitted valid JSON summary with `dry_run: true`, `credentials_required: false`, `turbopuffer_api_calls: false`, and `api_calls_occurred: false`.

Invalid URL validation:

```bash
uv run turbo-search crawl --base-url /relative --json
```

Result: exited `2` and printed `base URL must be an absolute http(s) URL`.

## What this supports

- `turbo-search crawl --base-url <url> --json` exists.
- The crawl command validates URL shape, performs a sitemap-first Scrapling crawl with fallback implementation present, writes local Markdown, chunks with the existing indexer, and reports a namespace candidate.
- The crawl path does not read `TURBOPUFFER_API_KEY`, instantiate turbopuffer SDK clients, embed text, or write rows.

## Limits

- Tests mock CLI crawl execution to avoid network; only the smoke command used network.
- Browser-rendered crawling is intentionally out of scope.
- Chunk IDs still use the existing `jf_` prefix from the Markdown indexer.
- Content quality still depends on site structure and may need `--css-selector` for noisy sites.
