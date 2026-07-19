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

## Remaining summary-leak blocker remediation

The website summary sanitizer was extended with a deterministic URL scanner rather than another destination regex. It consumes the already-supported Markdown destination grammar, then redacts HTTP(S), protocol-relative, angle-autolink, and URL-like visible text while preserving surrounding non-URL content. The website-only call site is unchanged, so PDF and local-file previews retain their pre-PR behavior.

A new two-loopback-server regression records the crawler's raw Markdown to prove the fixture produced escaped angle autolinks, visible-text-equals-destination autolinks, and a URL-like visible label with a distinct destination fragment. It proves both blocked destination paths received zero requests, serialized JSON and rendered text omitted the destination host, userinfo, nested path, query, fragment, and sentinels, and useful fixture prose remained in the JSON summary. A focused scanner regression separately covers nested/escaped parentheses and protocol-relative visible text.

Validation after this remediation:

- Python 3.11 focused: 52 tests passed.
- Python 3.11 full: 424 tests passed.
- Python 3.13 focused: 52 tests passed.
- Python 3.13 full: 424 tests passed.
- Wheel and source distribution built successfully under `/tmp/buoy-exact-host-summary-dist`.
- All 45 `src`/`tests` Python files parsed successfully and `git diff --check` passed.
- Hosted GitHub Actions run `29698186044` passed Python 3.11 (43s), Python 3.13 (43s), and distribution build (8s) for remediation commit `810ec28`.

## IPv6 visible-URL leakage blocker remediation

The visible-URL scanner was narrowed to genuinely safe termination boundaries (whitespace, quotes, angle delimiters, and Markdown backticks). It now conservatively consumes square, round, and curly brackets plus attached punctuation for both HTTP(S) and protocol-relative visible URLs. This is a generic boundary change rather than an IPv6-literal branch; Markdown destination parsing and angle-autolink handling remain separate and unchanged, and the website-only call site still preserves local PDF/file behavior.

The new regression first failed against the previous scanner because `https://IPV6_USER_A@[2001:db8::1]/PATH_A?...` left the bracketed address, path, query, fragment, and sentinel in serialized `sample_chunks`. After the change it passed IPv6 literals with userinfo, IPv4-mapped addresses, zone identifiers, ports, path brackets/parentheses/braces, punctuation both before and after query data, protocol-relative bracketed addresses, angle autolinks, visible Markdown labels with distinct destinations, and quoted boundaries. Raw previews plus JSON and text `sample_chunks` retained useful surrounding prose while containing none of the asserted users, addresses, paths, queries, fragments, or sentinels.

Validation after this remediation:

- Python 3.11 focused: 53 tests passed.
- Python 3.11 full: 425 tests passed.
- Python 3.13 focused: 53 tests passed.
- Python 3.13 full: 425 tests passed.
- Wheel and source distribution built successfully under `/tmp/buoy-exact-host-ipv6-dist`.
- All 45 `src`/`tests` Python files parsed successfully and `git diff --check` passed.
- Remediation commit `9178e7d` was pushed; hosted GitHub Actions run `29698625563` passed Python 3.11 (48s), Python 3.13 (43s), and distribution build (10s).
- Independent rereview remains pending.

## Fail-closed blocked-summary policy remediation

The representation-scanning website sanitizer was removed. Website `sample_chunks` now preserve their normal title and content preview only when both boundary counts are zero. If either `blocked_discovery_count` or `blocked_redirect_count` is nonzero, all sampled website titles and content previews use the fixed value `[redacted: blocked website crawl boundary]`; safe structural sample fields and count-only boundary reporting remain.

Regression coverage proves the fixed replacement cannot expose unsanitized titles, literal URLs, userinfo, bare IPv4 or IPv6 labels, percent-encoded labels, Markdown links, angle autolinks, or arbitrary path/query/fragment text. Separate cases exercise discovery-only and redirect-only counts. JSON serialization and text rendering contain no fixture secrets. The existing two-server autolink fixture still proves destination-side zero requests and now proves every sampled title/preview is fixed. A zero-count regression proves useful normal website titles/previews are unchanged. Existing PDF/local-file tests prove their summary counters and link-bearing title/preview behavior remain outside the website policy.

Validation after this remediation:

- Python 3.11 focused: 52 tests passed.
- Python 3.11 full: 424 tests passed.
- Python 3.13 focused: 52 tests passed.
- Python 3.13 full: 424 tests passed.
- Wheel and source distribution built successfully under `/tmp/buoy-exact-host-fail-closed-dist`.
- All 45 `src`/`tests` Python files parsed successfully; `git diff --check` passed; static search found no remaining custom summary-scanner symbols.
- Remediation commit `e7f9d02` was pushed; hosted GitHub Actions run `29699075735` passed Python 3.11 (48s), Python 3.13 (44s), and distribution build (7s).
- Independent rereview remains pending.

## Empty blocked-sample policy remediation

The final PR #42 review found that heading-derived `section_path` remained untrusted content under the fixed-field policy. The website summary boundary is now representation-independent: when either `blocked_discovery_count` or `blocked_redirect_count` is nonzero, `sample_chunks` is an empty list. No sample entry exists, so title, URL, heading-derived section path, preview, ID, or future sample fields can leak through selective redaction. When both counts are zero, the prior complete website sample dictionaries are preserved. The shared sample summarizer and local PDF/file summaries retain their prior behavior, and the obsolete fixed replacement constant and redaction parameter were removed.

The regression fixture includes a heading-derived URL with userinfo, path, query, and fragment sentinels and proves the crawled Markdown contains that untrusted heading while blocked JSON/text output contains none of it. Separate discovery-only and redirect-only cases assert an empty `sample_chunks` list and absence of every sample-entry field in JSON/text. Zero-block coverage asserts the complete prior website sample dictionary, and the existing PDF/local-file output regressions remain passing.

Validation after this remediation:

- Python 3.11 focused: 52 tests passed.
- Python 3.11 full: 424 tests passed.
- Python 3.13 focused: 52 tests passed.
- Python 3.13 full: 424 tests passed.
- Wheel and source distribution built successfully under `/tmp/buoy-exact-host-final-dist`.
- Python compilation and `git diff --check` passed; static search found no obsolete fixed-redaction symbols.
- Remediation commit `f79416f` was pushed; hosted GitHub Actions run `29699524145` passed Python 3.11 (47s), Python 3.13 (42s), and distribution build (11s).
- Independent rereview remains pending.

## Limits

- Fixtures contacted loopback servers only; no live site, model, Turbopuffer service, or other remote service was used.
- Independent rereview remains a separate gate; this evidence does not review or close the ticket.
- The redirect-safe robots integration remains private Scrapling API usage, bounded to exact version 0.4.9 and guarded to fail closed when the version or required runtime shape differs.
- Hosted GitHub Actions run `29697655401` passed Python 3.11 (44s), Python 3.13 (45s), and distribution build (10s) for remediation commit `5862708`.
