Status: recorded
Created: 2026-07-02
Updated: 2026-07-02
Relates-To: .10x/tickets/done/2026-07-02-docs-version-default-stop.md, .10x/specs/website-docs-version-policy.md

# Docs Version Default Stop Validation

## What was observed

Default `--docs-version-policy warn` now stops before page crawling when sitemap analysis detects a large versioned docs family. The user must choose an explicit policy:

- `latest`, `stable-latest`, or `latest-nightly` to filter duplicated version docs;
- `all` to keep every version.

## Procedure

Commands run:

```bash
uv run python -m unittest tests.test_crawler tests.test_cli
uv run python -m unittest discover -s tests

tmpdir=$(mktemp -d)
uv run turbo-search plan "https://iceberg.apache.org/" \
  --out-dir "$tmpdir/plan" \
  --state-root "$tmpdir/state" \
  --no-progress >"$tmpdir/stdout" 2>"$tmpdir/stderr"
status=$?
echo "status=$status"
echo "stdout_lines=$(wc -l < "$tmpdir/stdout")"
sed -n '1,6p' "$tmpdir/stderr"

tmpdir=$(mktemp -d)
uv run turbo-search plan "https://iceberg.apache.org/" \
  --docs-version-policy latest \
  --crawl-strategy sitemap \
  --max-pages 1 \
  --max-chunks 1 \
  --out-dir "$tmpdir/plan" \
  --state-root "$tmpdir/state" \
  --no-progress 2>&1 | sed -n '1,14p'
```

Observed output:

```text
Ran 50 tests in 0.571s
OK

Ran 157 tests in 2.952s
OK

status=2
stdout_lines=       0
detected versioned docs under /docs (22 versions, 837 sitemap URLs); stopping before page crawl. Rerun with --docs-version-policy latest to keep current docs and prune old versions, or --docs-version-policy all to keep every version.

Source RAG plan (local-only; no credentials, embeddings, or turbopuffer API calls):
  source_kind: website
  base_url: https://iceberg.apache.org/
  namespace: site-iceberg-apache-org-v1
  plan_id: plan_6069433de462ec80
  pages_scraped: 1; chunks_generated: 1
  caps: max_pages=1; max_chunks=1; chunk_limit_reached=True
  warning: reached page cap, chunk cap; this is probably capped/incomplete. Increase --max-pages and/or --max-chunks and rerun.
  filters: include=[]; exclude=['/docs/1.4.0/**', '/docs/1.4.1/**', '/docs/1.4.2/**', '/docs/1.4.3/**', '/docs/1.5.0/**', '/docs/1.5.1/**', '/docs/1.5.2/**', '/docs/1.6.0/**', '/docs/1.6.1/**', '/docs/1.7.0/**', '/docs/1.7.1/**', '/docs/1.7.2/**', '/docs/1.8.0/**', '/docs/1.8.1/**', '/docs/1.9.0/**', '/docs/1.9.1/**', '/docs/1.9.2/**', '/docs/1.10.0/**', '/docs/1.10.1/**', '/docs/1.10.2/**', '/docs/nightly/**']; strip_trailing_slash=True
  docs_versions: policy=latest; root=/docs; versions=22; versioned_urls=837; selected=['latest']; excluded_versions=21
  diff: first_apply=True, upsert=1, unchanged=0, stale=0, retained_stale=0
```

## What this supports or challenges

Supports:

- A plain Iceberg plan now exits with status `2` before crawling pages.
- The default stop emits only an explanatory stderr message and no stdout plan summary.
- `--docs-version-policy latest` proceeds and records effective exclude filters for old versions.
- Unit tests cover stop-before-crawl behavior at crawler and CLI levels.

Limits:

- Live validation used temporary local plan/state directories and a one-page explicit-policy crawl.
- No live turbopuffer writes were run.
