Status: active
Created: 2026-07-18
Updated: 2026-07-19
Parent: .10x/tickets/2026-07-18-repository-cleanup-plan.md
Depends-On: .10x/tickets/done/2026-07-18-triage-thistle-qdrant-dead-end.md

# Enforce Website Exact-Host Crawl Boundary

## Scope

Implement `.10x/specs/website-exact-host-crawl-boundary.md` in current `src/buoy_search/crawler.py` and current tests. Guard discovered links, sitemap/robots declarations and redirects, every page redirect hop, and final response URLs before any unreviewed-host request can occur.

## Acceptance criteria

- Meets every requirement and fixture scenario in `.10x/specs/website-exact-host-crawl-boundary.md`.
- Current automatic redirect behavior is replaced or wrapped so redirect targets are checked before request.
- Count-only blocked-discovery and blocked-redirect fields reach JSON/text summaries without URL/query leakage.
- Existing robots, resource-limit, strategy, filter, cap, timing, and canonicalization behavior remains intact.
- Focused crawler and full non-live tests pass; no live crawl or remote service is used.

## Evidence expectations

Local destination-side zero-request proof, focused/full test output, static/diff checks, and independent review.

## Blockers

None. Semantics are record-backed by the current active spec and the historical user-ratified exact-host ticket indexed in `.10x/research/2026-07-18-thistle-qdrant-dead-end-disposition.md`.

## Explicit exclusions

Live Thistle/Mercury crawling, remote mutation, general SSRF policy, subdomain expansion, or deduplication.

## References

- `.10x/specs/website-exact-host-crawl-boundary.md`
- `.10x/research/2026-07-18-thistle-qdrant-dead-end-disposition.md`
- `.10x/evidence/2026-07-18-thistle-qdrant-dead-end-disposition.md`

## Progress and notes

- 2026-07-18: Opened from read-only dead-end triage after current source inspection confirmed final response and redirect targets are not exact-host enforced.
- 2026-07-19: Disabled automatic Scrapling/urllib redirects for website crawling and added exact-host validation before discovered or redirected requests, including robots/sitemap policy acquisition, spider sitemap/robots declarations, every redirect hop, final responses, and the 20-hop ceiling. Added separate count-only boundary stats and summary rendering without blocked destination details.
- 2026-07-19: Added local two-server focused coverage for off-host discovery shapes, same-host and off-host redirects, different-port same-host behavior, robots denial, sitemap/robots declarations and redirects, the pre-crawl policy path, unexpected final hosts, hop limits, and summary leakage. Focused suites passed 46 tests and full suites passed 418 tests on both locked Python 3.11 and 3.13; wheel/sdist build and static checks passed. Hosted PR #42 checks also passed for Python 3.11, Python 3.13, and distribution build. Evidence: `.10x/evidence/2026-07-19-website-exact-host-crawl-boundary.md`. Independent review and closure remain pending.
- 2026-07-19: Remediated independent-review blockers without widening the crawl contract: the website-only Markdown preview sanitizer now consumes valid balanced, escaped, angle-bracketed, and titled destinations; local PDF/file previews and fields retain pre-change behavior; Scrapling is pinned to locked 0.4.9 with fail-closed version, lifecycle, robots-manager, session, and fetch-path guards. Added focused leakage, redirected-robots denial, private-shape failure, and local-source scope regressions. Local focused Python 3.11/3.13 suites passed 50 tests, full suites passed 422 tests on each version, distribution build and source/diff checks passed. Remediation commit `5862708` was pushed and hosted GitHub Actions run `29697655401` passed Python 3.11, Python 3.13, and distribution build. Independent rereview remains pending; the ticket stays active.
- 2026-07-19: Fixed the remaining PR #42 summary-leak review blocker with a website-only deterministic scanner that retains non-URL text while redacting HTTP(S), protocol-relative, angle-autolink, and URL-like visible-label content after consuming Markdown destinations. Added an adversarial two-loopback-server regression proving destination-side zero requests, actual autolink/URL-label Markdown shapes, removal of host/userinfo/path/query/fragment sentinels from JSON/text, and retention of useful content. Focused suites passed 52 tests and full suites passed 424 tests on both Python 3.11 and 3.13; distribution build, Python parse, and diff checks passed. Remediation commit `810ec28` was pushed and hosted GitHub Actions run `29698186044` passed Python 3.11, Python 3.13, and distribution build. Independent rereview remains pending; the ticket stays active.
- 2026-07-19: Remediated the IPv6 visible-URL leakage rereview blocker generically: visible HTTP(S) and protocol-relative URL scanning now treats only whitespace, quotes, angle delimiters, and backticks as safe boundaries, consuming square/round/curly brackets and attached RFC-style punctuation rather than stopping early. Added adversarial IPv6 userinfo/address/path/query/fragment/sentinel coverage across raw previews and JSON/text `sample_chunks`, including Markdown destination/angle-autolink, quoted, IPv4-mapped, zone-identifier, protocol-relative, and attached bracket/punctuation shapes. The new regression failed against the prior scanner and passes after the change. Focused suites passed 53 tests and full suites passed 425 tests on both Python 3.11 and 3.13; distribution build, parse, and diff checks passed. Remediation commit `9178e7d` was pushed and hosted GitHub Actions run `29698625563` passed Python 3.11, Python 3.13, and distribution build. Independent rereview remains pending; the ticket stays active.
- 2026-07-19: Replaced the representation-scanning summary sanitizer with a fail-closed website policy: when either blocked count is nonzero, every website sample title and content preview is replaced by one fixed secret-free value; when both counts are zero, the original title and preview are preserved. Removed the custom Markdown/URL scanner. Regressions cover title content, literals, autolinks, Markdown, userinfo, bare IPv4/IPv6, percent encoding, arbitrary path/query/fragment labels, either blocked-count trigger, JSON/text output, zero-block useful samples, and unchanged local PDF/file behavior. Focused suites passed 52 tests and full suites passed 424 tests on Python 3.11 and 3.13; distribution build, parse, and diff checks passed. Hosted checks and independent rereview remain pending; the ticket stays active.
