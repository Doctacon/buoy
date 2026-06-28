Status: recorded
Created: 2026-06-20
Updated: 2026-06-20
Target: .loom/tickets/2026-06-20-generic-site-stable-row-ids-and-schema.md duplicate-row-id blocker
Verdict: pass

# Generic Site Row ID Duplicate Blocker Review

## Target

Review target: blocker resolution for `.loom/reviews/2026-06-20-generic-site-plan-apply-phase1-review.md`.

Reviewed files:

- `src/turbo_search/plan_artifacts.py`
- `src/turbo_search/plan_diff.py`
- `tests/test_plan_artifacts.py`
- `tests/test_plan_diff.py`
- `.loom/evidence/2026-06-20-generic-site-row-id-duplicate-blocker-resolution.md`

## Findings

- Pass: ordinary unique row IDs still use `site_id + canonical_url + section_path + chunk_hash` and do not include page hash.
- Pass: duplicate URL/section/content groups are disambiguated with deterministic duplicate ordinals.
- Pass: duplicate disambiguation is covered by tests and produces stable row IDs across repeated artifact builds.
- Pass: page-hash-only changes do not churn duplicate-disambiguated row IDs.
- Pass: `plan_diff` now fails clearly if a malformed desired manifest contains duplicate row IDs, preventing silent dictionary-collapse before apply.
- Pass: `PlanDocument` includes `created_at`, addressing the review's minor note.

## Verdict

Pass. The Phase 1 row ID collision blocker is resolved.

## Residual risk

Duplicate ordinals are order-based within a URL/section/content group. If a duplicate group changes cardinality or ordering, row identity for later duplicates in that group may shift. This is acceptable for rare identical repeated chunks and is preferable to page-hash-based churn; ordinary unique chunks remain stable.
