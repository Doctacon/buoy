Status: done
Created: 2026-07-18
Updated: 2026-07-18
Parent: .10x/tickets/2026-07-18-direct-command-defaults-plan.md
Depends-On: .10x/tickets/done/2026-07-18-make-retrieval-live-by-default.md

# Remove Legacy JSON Applied-State Compatibility

## Scope

Implement the DuckDB-only hard cutover defined by `.10x/decisions/duckdb-only-applied-state-hard-cutover.md` and `.10x/specs/compact-duckdb-applied-state.md`:

- remove source paths that recognize, parse, migrate, archive, or delete `last-applied.json` and prior `legacy-json/` applied-state artifacts;
- make DuckDB the sole applied-state authority;
- ensure obsolete JSON files are inert and ignored;
- preserve first-apply behavior only when `state.duckdb` is absent or is a valid initialized empty ledger, while retaining fail-closed handling for invalid DuckDB state;
- update focused tests and active user/developer documentation that promises JSON applied-state migration.

## Acceptance criteria

- Applied-state production code has no `last-applied.json` or `legacy-json/` discovery, parsing, migration, archive, deletion, or warning path.
- Plan, existing apply preflight, and existing confirmed apply produce byte-equivalent state classification and side-effect behavior with an obsolete JSON file present versus absent.
- Obsolete JSON inode and bytes remain unchanged through successful and failed plan/apply paths.
- A valid DuckDB ledger remains authoritative; absent or valid initialized empty DuckDB state remains first-apply state; unreadable, corrupt, schema-incompatible, or identity-invalid DuckDB state retains existing fail-closed behavior.
- Per-namespace DuckDB storage, compact apply summaries, locking, content-failure preservation, successful content-write commit, and later catalog-failure pending recovery remain unchanged.
- Unrelated compatibility surfaces—legacy CLI/environment aliases, state-root fallback, old-plan support, and retained flags—remain unchanged.
- Focused/full Python 3.11/3.13 tests, distribution builds, evidence, independent review, and hosted checks pass.

## Evidence expectations

Source search proving removal; obsolete-file present/absent equivalence tests for behavior available before interactive confirmation is introduced; exact filesystem snapshots; invalid-DuckDB fail-closed tests; existing DuckDB state/lock/failure suites; full and hosted check identities.

## Blockers

None.

## Explicit exclusions

Deleting obsolete user files; importing JSON rows; changing state-root fallback; changing remote namespace data; changing apply confirmation behavior; removing unrelated compatibility aliases or flags; release.

## References

- `.10x/tickets/2026-07-18-direct-command-defaults-plan.md`
- `.10x/decisions/duckdb-only-applied-state-hard-cutover.md`
- `.10x/specs/compact-duckdb-applied-state.md`

## Progress and notes

- 2026-07-18: User ratified a JSON-applied-state-only hard cutover. Obsolete files are ignored, not migrated, deleted, or treated as errors.
- 2026-07-18: Removed JSON path discovery, parsing, migration, archive cleanup, and deletion from production applied state; updated active migration guidance and added inode/byte-preservation regressions across plan, preflight, successful/failed confirmed apply, missing/empty/populated DuckDB, and invalid DuckDB paths.
- 2026-07-18: Focused suites passed on Python 3.11/3.13 (99 tests each); full suites passed on Python 3.11/3.13 (407 tests each); wheel/sdist build, release asset validation, source search, and diff checks passed. Evidence: `.10x/evidence/2026-07-18-remove-legacy-json-applied-state.md`.
- 2026-07-18: Opened PR #36; hosted Python 3.11, Python 3.13, and distribution-build checks passed in Actions run `29691090597`. Implementation session left the ticket active pending independent review.
- 2026-07-18: Rebased linearly onto cleanup-plan integration `6f28123`; reran 99 focused and 407 full tests on Python 3.11/3.13 plus build and hosted run `29691158672` successfully.
- 2026-07-18: Independent review passed at implementation head `67f47630993db1db6384b9f97354e37afd70628b`. Parent-observed corrupt and permission-denied DuckDB probes also failed closed with `AppliedStateError`. Review: `.10x/reviews/2026-07-18-remove-legacy-json-applied-state-review.md`; evidence: `.10x/evidence/2026-07-18-remove-legacy-json-applied-state.md`.

## Closure mapping

- No JSON applied-state runtime path: production source search and bounded diff inspection recorded in evidence and independent review.
- Obsolete-file behavioral equivalence and preservation: committed plan/preflight/success/failure fixtures snapshot output plus device/inode/size/mtime/bytes.
- DuckDB authority and fail-closed behavior: populated/empty/missing/schema/identity regressions plus parent-observed corrupt/unreadable probes.
- State-root and unrelated compatibility: retained focused fallback/CLI tests and independent diff review.
- Lock/content/state/catalog sequencing: unchanged apply/catalog source and passing protective suites, independently inspected.
- Validation: focused/full Python 3.11/3.13 suites, distributions, release assets, hosted checks, evidence, and pass review.

## Retrospective

The rejected compatibility path was more complex and less safe than a hard format boundary. Removing recognition entirely made obsolete files inert without introducing cleanup ordering or rollback semantics. Keep future format retirements separate from unrelated path/name compatibility so a narrow hard cutover does not accidentally remove still-supported surfaces.
