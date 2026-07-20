Status: active
Created: 2026-07-18
Updated: 2026-07-19
Parent: None
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
- 2026-07-19: Bounded incremental readers and declared/detected gzip fail-closed handling are integrated with exact-host discovery. Focused crawler/exact-host and full 428-test suites pass on Python 3.11 and 3.13; evidence is recorded at `.10x/evidence/2026-07-19-sitemap-resource-limits.md`. Independent review remains, so this ticket stays active.
- 2026-07-19: PR #54 review blockers repaired: corrupt-DEFLATE `zlib.error` is wrapped as URL-specific malformed gzip, and validated final redirect URLs now drive declared-gzip detection and relative parsing. Focused 61-test and full 431-test suites pass on Python 3.11 and 3.13. The ticket remains active for independent rereview; no closure or merge was performed.
