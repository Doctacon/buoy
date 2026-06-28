Status: recorded
Created: 2026-06-20
Updated: 2026-06-20
Relates-To: .pi/skills/turbopuffer-site-rag/SKILL.md, .loom/knowledge/turbopuffer-site-rag-skill.md

# Scrapling Site RAG Dry Crawl Smoke Test

## What was observed

A local-only Scrapling dry crawl was run against the Scrapling documentation site using the new skill helper script. No turbopuffer credentials were read, no namespace was created, and no API calls to turbopuffer occurred.

Summary fields from the successful run:

```json
{
  "command": "scrapling-dry-crawl",
  "dry_run": true,
  "credentials_required": false,
  "turbopuffer_api_calls": false,
  "api_calls_occurred": false,
  "base_url": "https://scrapling.readthedocs.io/en/latest/",
  "allowed_host": "scrapling.readthedocs.io",
  "namespace_candidate": "site-scrapling-readthedocs-io-v1",
  "max_pages": 5,
  "pages_scraped": 5,
  "requests_count": 5,
  "robots_disallowed_count": 0,
  "blocked_requests_count": 0,
  "failed_requests_count": 0,
  "chunks_generated": 25,
  "files_error": 0,
  "limit_reached": true,
  "css_selector": ".md-content__inner"
}
```

Output directory:

- `artifacts/scrapling-dry-crawl/scrapling-docs-smoke-selector/`

`artifacts/` is ignored by git.

## Procedure

Compile check:

```bash
PYTHONPATH=src python3 -m py_compile \
  .pi/skills/turbopuffer-site-rag/scripts/scrapling_dry_crawl.py
```

Dry crawl command:

```bash
PYTHONPATH=src uv run \
  --with "scrapling[fetchers]>=0.4.9" \
  --with "markdownify>=1.2.0" \
  python .pi/skills/turbopuffer-site-rag/scripts/scrapling_dry_crawl.py \
    --base-url "https://scrapling.readthedocs.io/en/latest/" \
    --max-pages 5 \
    --max-chunks 25 \
    --css-selector ".md-content__inner" \
    --out-dir artifacts/scrapling-dry-crawl/scrapling-docs-smoke-selector
```

A first attempt without `--css-selector` also succeeded but produced noisier chunks containing navigation/sponsor material near the front of the page. Adding `.md-content__inner` improved content focus, though the Scrapling index page still includes sponsor content inside the main documentation content.

## What this supports

- Scrapling can crawl a small public docs site and feed the existing Markdown chunking pipeline without live turbopuffer writes.
- The skill helper emits a namespace candidate and safety fields suitable for a pre-write review.
- Site-specific main-content selectors are important for content quality.

## Limits

- This was a 5-page smoke test, not a production crawl.
- It did not create or write a turbopuffer namespace.
- It did not test browser-rendered pages or anti-bot/protected sites.
- It used the existing Markdown chunker, whose deterministic chunk IDs still use the legacy `jf_` prefix.
