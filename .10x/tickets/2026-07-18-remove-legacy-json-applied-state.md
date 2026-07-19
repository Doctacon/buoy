Status: open
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
