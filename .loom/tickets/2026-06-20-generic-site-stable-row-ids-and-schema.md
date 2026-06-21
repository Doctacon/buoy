Status: active
Created: 2026-06-20
Updated: 2026-06-20
Parent: .loom/tickets/2026-06-20-generic-site-rag-incremental-plan-apply.md
Depends-On: .loom/specs/generic-site-rag-incremental-plan-apply.md, .loom/decisions/generic-site-rag-incremental-state.md

# Generic Site Stable Row IDs and Schema

## Scope

Add the row identity and schema metadata needed for incremental generic site applies.

In scope:

- Design/implement a generic-site row ID function that does not include whole-page source hash.
- Recommended row ID input: `site_id + canonical_url + section_path + chunk_hash`.
- Recommended row ID shape: `ts_<32 hex chars>` or another short deterministic string acceptable to turbopuffer.
- Add manifest/row metadata fields: `site_id`, `canonical_url`, `page_hash`, `chunk_hash`, `embedding_text_hash`, `plan_id`, and `applied_at`.
- Ensure existing Jellyfish prototype behavior is not broken unexpectedly.
- Tests for row ID stability across unrelated page changes and row ID changes when chunk content changes.

Out of scope:

- Reindexing existing Jellyfish rows.
- Live turbopuffer writes.
- Changing retrieval ranking logic.
- Remote state reconstruction.

## Implementation notes

The current Jellyfish chunk ID includes source hash and content. That was adequate for one-time indexing, but for generic incremental site workflows it can cause too many row IDs to churn when a page changes.

The generic workflow can add a new row-ID path without retroactively changing the existing Jellyfish namespace. Avoid breaking current tests that assume `jf_` chunk IDs unless those tests are explicitly updated for generic-site-only paths.

The schema should continue storing `content` in turbopuffer for MVP retrieval ergonomics.

## Acceptance criteria

- Generic site row IDs are deterministic and shorter than turbopuffer row ID limits.
- A changed page section does not force unchanged chunks elsewhere on the same page to receive new IDs solely because the page hash changed.
- Row metadata includes enough information for local state diffing and future recovery inspection.
- Existing indexer/retriever tests continue to pass.
- New tests cover stable ID behavior and metadata row construction.
- No live API calls are used in tests.

## Progress and notes

- 2026-06-20: Ticket opened as Phase 1 foundation for incremental generic applies.
- 2026-06-20: Implemented generic-site row identity in `src/turbo_search/plan_artifacts.py` as `ts_<32 hex>` derived from `site_id + canonical_url + section_path + chunk_hash`, explicitly excluding page hash, page path, and chunk index from the ID hash.
- 2026-06-20: Added generic manifest row metadata fields (`row_id`, `site_id`, `canonical_url`, `page_hash`, `chunk_hash`, `embedding_text_hash`) and a `build_generic_site_row()` helper that adds `plan_id` and `applied_at` for future apply writes.
- 2026-06-20: Added `GENERIC_SITE_TURBOPUFFER_SCHEMA` extending the existing Jellyfish schema with incremental metadata fields while leaving existing Jellyfish `build_row()` behavior untouched.
- 2026-06-20: Added tests for stable row IDs across unrelated page-section changes, row ID changes when chunk content changes, and generic row metadata/schema construction.
- 2026-06-20: Validation passed. Evidence: `.loom/evidence/2026-06-20-generic-site-stable-row-ids-and-schema-validation.md`.
- 2026-06-20: Phase 1 review found a blocker: repeated identical chunks within the same URL and section can collide because row IDs use `site_id + canonical_url + section_path + chunk_hash`. Review: `.loom/reviews/2026-06-20-generic-site-plan-apply-phase1-review.md`.

## Blockers

- Row ID collision handling must be fixed before apply/CLI continuation.

## Residual risks

- Exact final turbopuffer SDK schema/write compatibility for generic rows still needs verification before live apply. That remains in scope for later apply tickets.
