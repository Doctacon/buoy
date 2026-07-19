Status: open
Created: 2026-07-18
Updated: 2026-07-18
Parent: .10x/tickets/2026-07-18-repository-cleanup-plan.md
Depends-On: None

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
