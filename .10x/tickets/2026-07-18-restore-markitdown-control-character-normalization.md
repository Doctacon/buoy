Status: open
Created: 2026-07-18
Updated: 2026-07-18
Parent: .10x/tickets/2026-07-18-repository-cleanup-plan.md
Depends-On: None

# Restore MarkItDown Control-Character Normalization

## Scope

Restore the narrow product-neutral behavior from unique historical commit `b48f13c6286af65781e82327eea4deffd471c8a7` in current `src/buoy_search/crawler.py`: before local MarkItDown output is written or chunked, remove Unicode `Cc` control characters except ordinary Markdown whitespace (`\n`, `\r`, `\t`).

## Acceptance criteria

- PDF and non-PDF local document ingestion strip embedded NUL and other `Cc` controls before generated page artifacts and chunks.
- Newlines, carriage returns, tabs, valid Unicode, and Markdown structure remain.
- Empty-output handling remains after normalization.
- Focused current-package tests cover PDF and non-PDF paths; full non-live validation passes.

## Evidence expectations

Focused control-character fixtures, full checks, diff check, and independent review.

## Blockers

None. The exact behavior was user-requested, implemented, evidenced, and independently reviewed on the historical branch. The old records are indexed as non-authoritative provenance in `.10x/research/2026-07-18-thistle-qdrant-dead-end-disposition.md`.

## Explicit exclusions

OCR, semantic cleanup, table/page repair, heading rewriting, converter changes, citation/namespace changes, or live apply.

## References

- `.10x/specs/local-markitdown-document-source-ingestion.md`
- `.10x/specs/local-pdf-source-ingestion.md`
- `.10x/research/2026-07-18-thistle-qdrant-dead-end-disposition.md`

## Progress and notes

- 2026-07-18: Current source inspection confirmed `crawl_local_document()` directly calls `.strip()` on converted output and has no control-character normalization.
