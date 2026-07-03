Status: recorded
Created: 2026-07-02
Updated: 2026-07-02
Relates-To: .10x/tickets/done/2026-07-02-website-docs-version-policy.md, .10x/specs/website-docs-version-policy.md

# Website Docs Version Policy Validation

## What was observed

Implemented website docs-version policy support for `turbo-search crawl` and `turbo-search plan`:

- default `--docs-version-policy warn` detects repeated sitemap docs families and reports a suggestion without filtering;
- `latest`, `stable-latest`, and `latest-nightly` add effective exclude-path filters for non-selected docs versions;
- `all` keeps all versions and skips automatic analysis/filtering;
- plan artifacts record the effective `docs_version_policy` and effective include/exclude filters.

## Procedure

Commands run:

```bash
uv run python -m unittest tests.test_crawler tests.test_cli
uv run python -m unittest discover -s tests
uv run turbo-search plan --help | rg -n "docs-version|websites=|max-pages|max-chunks"
```

Observed output:

```text
Ran 47 tests in 0.571s
OK

Ran 154 tests in 2.959s
OK

3:                         [--max-pages MAX_PAGES] [--max-chunks MAX_CHUNKS]
11:                         [--docs-version-policy {warn,all,latest,stable-latest,latest-nightly}]
40:  --max-pages MAX_PAGES
42:                        websites=3000, GitHub repos=5000.
43:  --max-chunks MAX_CHUNKS
44:                        Maximum chunks to generate. Defaults: websites=120000,
68:  --docs-version-policy {warn,all,latest,stable-latest,latest-nightly}
69:                        Website sitemap docs-version handling. Default: warn
```

A read-only sitemap analysis was run for `https://iceberg.apache.org/` without crawling pages or calling turbopuffer:

```bash
uv run python - <<'PY'
from pathlib import Path
from turbo_search.crawler import CrawlOptions, discover_sitemap_page_urls, analyze_docs_version_urls, apply_docs_version_policy, url_allowed_by_path_filters
base = CrawlOptions(base_url='https://iceberg.apache.org/', out_dir=Path('unused'), docs_version_policy='warn')
urls = discover_sitemap_page_urls(base)
report = analyze_docs_version_urls(urls, policy='warn')
print('urls', len(urls))
print('detected', report.get('detected'))
print('root', report.get('root_path'))
print('versions', report.get('version_count'))
print('versioned_urls', report.get('versioned_url_count'))
print('suggested', report.get('suggested_policy'))
for policy in ['latest','stable-latest','latest-nightly']:
    effective, report = apply_docs_version_policy(CrawlOptions(base_url='https://iceberg.apache.org/', out_dir=Path('unused'), docs_version_policy=policy))
    kept = [u for u in urls if url_allowed_by_path_filters(u, include_paths=effective.include_paths, exclude_paths=effective.exclude_paths)]
    print(policy, 'selected', report.get('selected_versions'), 'kept', len(kept), 'excluded_versions', len(report.get('excluded_versions', [])))
PY
```

Observed output:

```text
urls 915
detected True
root /docs
versions 22
versioned_urls 837
suggested latest
latest selected ['latest'] kept 118 excluded_versions 21
stable-latest selected ['1.10.2'] kept 119 excluded_versions 21
latest-nightly selected ['latest', 'nightly'] kept 158 excluded_versions 20
```

## What this supports or challenges

Supports:

- Iceberg-style `/docs/{version}/...` duplication is detected from sitemap URLs.
- The default warning policy would keep all pages while suggesting a current-docs policy.
- `latest` keeps `/docs/latest/**` and prunes 21 older/other version prefixes while preserving non-versioned site pages.
- `stable-latest` selects the highest semantic version observed in the sitemap.
- `latest-nightly` keeps current and preview docs aliases.
- Full unit coverage still passes.

Limits:

- The Iceberg check fetched sitemap/robots candidates only; it did not run a full page crawl or write to turbopuffer.
- Link-only crawls still cannot know a total page count or version family before discovering links dynamically.
