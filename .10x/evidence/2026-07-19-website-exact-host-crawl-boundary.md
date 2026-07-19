Status: recorded
Created: 2026-07-19
Updated: 2026-07-19
Relates-To: .10x/tickets/2026-07-18-enforce-website-exact-host-crawl-boundary.md, .10x/specs/website-exact-host-crawl-boundary.md

# Website Exact-Host Crawl Boundary Implementation Evidence

## What was observed

Current Buoy exact-host enforcement was implemented without a live or external-network crawl. Focused local fixtures used two loopback HTTP servers and proved:

- sibling-subdomain, external-host, protocol-relative, OAuth-shaped, chained, and open-redirect destinations were rejected before the destination path received a request;
- a same-host redirect to a different port continued, confirming port is not hostname identity;
- same-host one-hop, multi-hop, and exactly-20-hop redirects completed, while the 21st destination in an over-limit chain received zero requests;
- a robots-denied same-host target received zero requests, including when reached through a same-host redirect;
- same-host sitemap and robots redirects continued, while off-host robots/sitemap declarations, page declarations, child sitemaps, and redirect targets received zero destination requests;
- the pre-crawl sitemap-policy analysis path applied the same declaration and per-hop redirect checks;
- an unexpected off-host final response was rejected;
- JSON and text summaries exposed only `blocked_discovery_count` and `blocked_redirect_count`, with blocked link destinations removed from summary previews and no fixture query/credential values present.

## Procedure

1. Ran focused crawler tests under locked Python 3.11:
   `PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 python -m unittest tests.test_crawler tests.test_crawler_exact_host -q`
2. Ran the full non-live suite under locked Python 3.11:
   `PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 python -m unittest discover -s tests -p 'test_*.py' -q`
3. Repeated focused and full suites under locked Python 3.13.
4. Built wheel and source distribution outside the repository:
   `uv build --out-dir /tmp/buoy-exact-host-dist`
5. Ran Python compilation, `git diff --check`, and a static search for blocked URL/query-bearing output fields.
6. Pushed commit `1b64bc3`, opened PR #42, and observed GitHub Actions run `29696972955` to completion.

## Validation results

- Python 3.11 focused: 46 tests passed.
- Python 3.11 full: 418 tests passed.
- Python 3.13 focused: 46 tests passed.
- Python 3.13 full: 418 tests passed.
- Build: `buoy_search-0.3.0-py3-none-any.whl` and `buoy_search-0.3.0.tar.gz` built successfully under `/tmp/buoy-exact-host-dist`.
- Compilation and whitespace checks passed; the static blocked-detail field search returned no matches.
- Hosted CI passed: Python 3.11 (43s), Python 3.13 (39s), and distribution build (11s).

## What this supports

This supports the executable ticket's implementation and local-validation acceptance criteria. It does not provide independent review or ticket closure.

## Independent-review blocker remediation

A later independent review found three blockers. The implementation was revised and locally revalidated:

- Website summary destination removal now parses complete valid inline Markdown destinations with balanced or escaped parentheses, angle brackets, optional titles, and suffix text. Adversarial fixtures assert blocked host/path details, query values, OAuth-shaped userinfo, and sentinels are absent from serialized JSON and rendered text summaries.
- Scrapling is now declared and locked at exactly 0.4.9. Runtime checks validate the pinned version, lifecycle order, robots callback usage, request processing, session fetch path, disabled automatic redirects, empty prefetch cache, and installed robots fetch binding. Shape/version failures abort during spider initialization or `on_start`, before robots or page requests. A redirected same-host robots fixture proves the redirected denial prevents the page request.
- Destination sanitization and exact-host counter fields are website-only. PDF/local-file regressions prove their summary fields omit boundary counters and their `content_preview` retains Markdown destinations exactly as before this PR.

Validation after remediation:

- Python 3.11 focused: 50 tests passed.
- Python 3.11 full: 422 tests passed.
- Python 3.13 focused: 50 tests passed.
- Python 3.13 full: 422 tests passed.
- Wheel and source distribution rebuilt successfully under `/tmp/buoy-exact-host-review-dist`.
- All `src`/`tests` Python files parsed successfully; `git diff --check`, exact dependency/lock/version checks, and the blocked-detail output-field diff search passed.

## Limits

- Fixtures contacted loopback servers only; no live site, model, Turbopuffer service, or other remote service was used.
- Independent rereview remains a separate gate; this evidence does not review or close the ticket.
- The redirect-safe robots integration remains private Scrapling API usage, bounded to exact version 0.4.9 and guarded to fail closed when the version or required runtime shape differs.
- Hosted GitHub Actions run `29697655401` passed Python 3.11 (44s), Python 3.13 (45s), and distribution build (10s) for remediation commit `5862708`.
