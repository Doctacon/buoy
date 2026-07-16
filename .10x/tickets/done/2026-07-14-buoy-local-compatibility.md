Status: done
Created: 2026-07-14
Updated: 2026-07-15
Parent: .10x/tickets/done/2026-07-14-buoy-rebrand-plan.md
Depends-On: .10x/tickets/done/2026-07-14-buoy-core-package-rename.md

# Implement Buoy Local Compatibility

## Scope

Implement `.10x/specs/buoy-local-compatibility.md` in the renamed codebase: `.buoy` defaults, in-place `.turbo-search` fallback, dual-root refusal, explicit-root precedence, old-plan compatibility, branded environment fallback/conflict behavior, exclusions, and warnings.

## Acceptance criteria

- Every state-root and environment scenario in the governing spec is tested.
- Tests prove no compatibility path copies, moves, merges, or deletes local state.
- Existing plan artifact hashes and deterministic row/namespace identity remain unchanged solely by branding.
- Warnings/errors use stderr and do not contaminate JSON stdout.
- No model loading, credentials, or remote call occurs in compatibility tests.
- Focused and complete suites pass with independent review.

## Explicit exclusions

Automatic state migration, DuckDB semantic redesign, remote changes, docs/logo/eval rewrite, and alias removal.

## References

- `.10x/decisions/superseded/buoy-product-identity-and-compatibility.md`
- `.10x/specs/buoy-local-compatibility.md`
- `.10x/tickets/done/2026-07-14-buoy-core-package-rename.md`

## Evidence expectations

Filesystem before/after observations for all root cases, old-plan preflight fixture, environment precedence/conflict tests, full suite, and independent review.

## Progress and notes

- 2026-07-14: Core package dependency closed; assigned to a single worker.
- 2026-07-14: Independent review found missing pre-rebrand golden assertions and evidence mislabeled intermediate `jf_*` chunk IDs as remote row identity. Repair must assert the exact preserved artifact hash, `ts_*` row ID, and namespace. Pre-existing staged documentation is outside this child's write boundary and must remain untouched.
- 2026-07-14: Implemented `.buoy` defaults, no-copy legacy fallback, dual-root refusal, explicit override, old-plan preflight compatibility, `BUOY_EMBEDDING_MODEL` with bounded old-variable warning/conflict handling, and dual-root source exclusions. Focused 141 tests and full 225 tests passed initially; identity and filesystem observations are recorded at `.10x/evidence/2026-07-14-buoy-local-compatibility.md`.
- 2026-07-14: Repaired the verification blocker with a committed pre-rebrand standard-fixture golden asserting the exact artifact hash, remote `ts_*` row ID, and namespace; corrected evidence that had mislabeled an intermediate `jf_*` chunk ID. Focused 142 tests and full 226 tests pass; lock and diff checks pass. Awaiting independent re-review.

- 2026-07-14: Final independent review passed after golden identity repair. Evidence: `.10x/evidence/2026-07-14-buoy-local-compatibility.md`; review: `.10x/reviews/2026-07-14-buoy-local-compatibility-review.md`.

## Blockers

- None.
