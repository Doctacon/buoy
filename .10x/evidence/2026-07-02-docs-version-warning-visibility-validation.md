Status: recorded
Created: 2026-07-02
Updated: 2026-07-02
Relates-To: .10x/tickets/done/2026-07-02-docs-version-warning-visibility.md, .10x/specs/website-docs-version-policy.md

# Docs Version Warning Visibility Validation

## What was observed

The original default `warn` policy was easy to miss during long plans because detection was recorded in the final summary and transient one-line progress. A persistent early stderr warning now prints after sitemap docs-version analysis and before page crawling for text-mode `crawl`/`plan` runs. JSON stdout remains clean; JSON summaries still carry `docs_version_report`.

## Procedure

Commands run:

```bash
uv run python -m unittest tests.test_crawler tests.test_cli
uv run python -m unittest discover -s tests

tmpdir=$(mktemp -d)
uv run turbo-search plan "https://iceberg.apache.org/" \
  --crawl-strategy sitemap \
  --max-pages 1 \
  --max-chunks 1 \
  --out-dir "$tmpdir/plan" \
  --state-root "$tmpdir/state" \
  --no-progress 2>&1 | sed -n '1,12p'
```

Observed output:

```text
Ran 49 tests in 0.650s
OK

Ran 156 tests in 2.984s
OK

warning: detected versioned docs under /docs (22 versions, 837 sitemap URLs). Rerun with --docs-version-policy latest to keep current docs and prune old versions, or --docs-version-policy all to keep every version.
Source RAG plan (local-only; no credentials, embeddings, or turbopuffer API calls):
  source_kind: website
  base_url: https://iceberg.apache.org/
  namespace: site-iceberg-apache-org-v1
  plan_id: plan_fb50dfc10a79c453
  pages_scraped: 1; chunks_generated: 1
  caps: max_pages=1; max_chunks=1; chunk_limit_reached=True
  warning: reached page cap, chunk cap; this is probably capped/incomplete. Increase --max-pages and/or --max-chunks and rerun.
  filters: include=[]; exclude=[]; strip_trailing_slash=True
  docs_versions: detected root=/docs; versions=22; versioned_urls=837; policy=warn
  suggestion: rerun with --docs-version-policy latest to keep current docs and prune old versions, or --docs-version-policy all to keep/suppress this warning.
```

## What this supports or challenges

Supports:

- Text-mode Iceberg-like plans now show an immediate persistent warning before final plan output.
- The warning names the detected docs root, version count, versioned sitemap URL count, and explicit next commands.
- Unit tests cover warning message generation and warning emission before page crawling.

Limits:

- The live command used a one-page sitemap crawl into a temporary output directory; no live turbopuffer writes were run.
