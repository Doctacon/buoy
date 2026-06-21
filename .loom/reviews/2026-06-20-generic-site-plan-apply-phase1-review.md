Status: recorded
Created: 2026-06-20
Updated: 2026-06-20
Target: .loom/tickets/2026-06-20-generic-site-rag-incremental-plan-apply.md Phase 1
Verdict: concerns

# Generic Site Plan/Apply Phase 1 Review

## Target

Phase 1 foundation tickets:

- `.loom/tickets/2026-06-20-plan-artifact-manifest-model.md`
- `.loom/tickets/2026-06-20-generic-site-stable-row-ids-and-schema.md`
- `.loom/tickets/2026-06-20-local-applied-state-store.md`
- `.loom/tickets/2026-06-20-incremental-plan-diff-engine.md`

Reviewed implementation files:

- `src/turbo_search/plan_artifacts.py`
- `src/turbo_search/applied_state.py`
- `src/turbo_search/plan_diff.py`
- `tests/test_plan_artifacts.py`
- `tests/test_applied_state.py`
- `tests/test_plan_diff.py`

## Findings

### Blocker: duplicate row IDs are possible for repeated identical chunks

`generic_site_row_id()` hashes only:

```text
site_id + canonical_url + section_path + chunk_hash
```

If a page produces two chunks with identical content in the same URL and section, both chunks can get the same `row_id`. The diff engine keys desired and active rows by `row_id`, so duplicates could collapse and cause apply/upsert/delete accounting to be wrong.

This must be fixed before continuing to CLI/apply work by adding either:

- a stable uniqueness strategy; or
- duplicate row ID detection that fails plan generation safely before apply.

### Minor: `PlanDocument` currently lacks `created_at`

The spec sketch includes `created_at`. This is not a blocker for Phase 1, but should be reconciled before polished plan output.

## Positive findings

- Deterministic artifact model exists and is tested.
- Local applied state store follows the local manifest decision.
- Diff engine is pure/local and covers first apply, unchanged, changed, stale, retained-stale, reactivation, and deleted-row-ignore behavior.
- No credential or live API behavior was found in Phase 1 implementation.

## Verdict

Concerns. Phase 1 is blocked for apply/CLI continuation until row ID collision handling is fixed.

## Residual risk

After the duplicate row ID fix, the next review should re-check that the chosen fix does not reintroduce page-hash-based churn and still keeps incremental behavior stable.
