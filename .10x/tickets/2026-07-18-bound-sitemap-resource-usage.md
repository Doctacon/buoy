Status: open
Created: 2026-07-18
Updated: 2026-07-18
Parent: .10x/tickets/2026-07-18-repository-cleanup-plan.md
Depends-On: None

# Restore Bounded Sitemap Resource Usage

## Scope

Implement `.10x/specs/sitemap-resource-limits.md` in current `src/buoy_search/crawler.py`. Replace unbounded robots/sitemap reads and gzip expansion with incremental bounded processing and fail-closed errors.

## Acceptance criteria

- Meets `.10x/specs/sitemap-resource-limits.md`.
- The current `fetch_url_bytes()` and gzip handling no longer perform unbounded whole-body work.
- Oversize or malformed declared/detected gzip cannot silently appear empty and trigger broader link fallback.
- Focused boundary/bomb fixtures and full non-live validation pass.

## Evidence expectations

Exact-boundary and over-limit fixtures, gzip-bomb/malformed-gzip proof, focused/full checks, and independent review.

## Blockers

None. Exact limits and failure behavior were user-ratified on historical commit `d7a37d7` and are preserved in the active current spec.

## Explicit exclusions

Live crawling, page-body limits, service-grade SSRF, and changes to exact-host semantics beyond compatible integration.

## References

- `.10x/specs/sitemap-resource-limits.md`
- `.10x/research/2026-07-18-thistle-qdrant-dead-end-disposition.md`

## Progress and notes

- 2026-07-18: Current source inspection found `fetch_url_bytes()` calls `response.read()` and `maybe_decompress_sitemap()` expands gzip without byte ceilings; opened the smallest current repair owner.
