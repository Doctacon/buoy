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
- 2026-07-19: Added local two-server focused coverage for off-host discovery shapes, same-host and off-host redirects, different-port same-host behavior, robots denial, sitemap/robots declarations and redirects, the pre-crawl policy path, unexpected final hosts, hop limits, and summary leakage. Focused suites passed 46 tests and full suites passed 418 tests on both locked Python 3.11 and 3.13; wheel/sdist build and static checks passed. Evidence: `.10x/evidence/2026-07-19-website-exact-host-crawl-boundary.md`. Independent review and closure remain pending.
