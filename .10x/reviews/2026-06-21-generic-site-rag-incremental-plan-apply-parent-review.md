Status: recorded
Created: 2026-06-21
Updated: 2026-06-21
Target: .loom/tickets/2026-06-20-generic-site-rag-incremental-plan-apply.md
Verdict: concerns

# Generic Site RAG Incremental Plan/Apply Parent Review

## Target

Final parent review before closure for `.loom/tickets/2026-06-20-generic-site-rag-incremental-plan-apply.md`.

Reviewed against:

- `.loom/specs/generic-site-rag-incremental-plan-apply.md`
- parent ticket acceptance criteria
- `.loom/evidence/2026-06-21-generic-site-rag-incremental-plan-apply-parent-validation.md`
- implementation files under `src/turbo_search/`
- tests and docs records

## Findings

### Positive findings

- All child tickets are marked done.
- Safety model is strong: plan is local-only, apply preflight verifies without credentials/embeddings/writer calls, and approved apply reads `TURBOPUFFER_API_KEY` only after artifact/state/namespace verification.
- Incremental behavior is covered by the diff engine and tests for first apply, unchanged chunks, changed chunks, removed/stale rows, retained-stale rows, and reactivation.
- Stale delete guardrail is mostly correct: `--approve` and `--delete-stale` are separate, deletes use exact stale row IDs, and tests cover explicit delete/failure behavior.
- Parent evidence records 75 tests passing, compile checks, apply preflight smoke, retrieval/eval dry-runs, secret checks, and no staged files.

### Blocker found and fixed after this review

The spec says apply must fail before live work when delete is requested but the plan does not include stale rows. The implementation initially treated `--approve --delete-stale` with zero stale rows as a no-op and saved state.

Resolution performed after this review:

- `src/turbo_search/apply.py` now rejects approved `--delete-stale` when the recomputed diff has no stale rows.
- The failure happens before credential access, embedding, writer construction, or state update.
- `tests/test_apply_cli.py` now covers this case.
- `.loom/tickets/2026-06-20-apply-stale-delete-guardrail.md` was updated with the fix note.

## Verdict

Concerns at the time of review, with the blocking issue subsequently fixed. A final validation/review should confirm closure.

## Residual risk

Live turbopuffer upsert/delete compatibility remains unverified by design. Partial live failures can still require manual reconciliation because local state is conservatively not updated when live work fails.
