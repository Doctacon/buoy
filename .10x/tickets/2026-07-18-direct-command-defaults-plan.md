Status: open
Created: 2026-07-18
Updated: 2026-07-18
Parent: None
Depends-On: None

# Direct Command Defaults Plan

## Outcome

Make retrieval execute live by default and make interactive apply prompt after preflight, so normal commands perform their named action without weakening explicit preview, automation, stale-deletion, or recovery boundaries.

## Child sequence

1. `.10x/tickets/done/2026-07-18-make-retrieval-live-by-default.md`
2. `.10x/tickets/done/2026-07-18-remove-legacy-json-applied-state.md`
3. `.10x/tickets/2026-07-18-add-interactive-apply-confirmation.md`

The sequence prevents overlapping edits to CLI help, generated retrieval commands, README, applied-state handling, and apply output. The parent is not executable.

## Aggregate acceptance criteria

- Plain automatic and explicit retrieval execute live; `--dry-run`/`--plan` preview; `--live` remains a compatibility no-op.
- Interactive plain apply shows complete local preflight and prompts `[y/N]`; exact yes confirms and every other/absent input cancels safely with exit 0.
- `apply --dry-run` is the explicit local preflight; `--approve` remains non-interactive confirmation; plain non-TTY apply fails before plan work.
- Applied state is DuckDB-only; obsolete JSON state is ignored byte-for-byte and never read, migrated, deleted, or allowed to affect behavior.
- Preflight and cancellation perform no local mutation; only confirmed apply enters approved state and remote work.
- Existing route selection, all-or-nothing retrieval, apply sequencing, locks, pending recovery, catalog registration, stale deletion, JSON cleanliness, compatibility aliases, and safety rails remain unchanged.
- Generated commands, help, README/docs/changelog, focused/full Python 3.11/3.13 tests, distribution builds, independent reviews, and hosted checks agree.

## Explicit exclusions

Default catalog mutations; removed `--live`/`--approve` flags; automatic apply approval; piped approval; changed stale deletion; concurrent content retrieval/writes; new configuration; telemetry; release/version publication.

## References

- `.10x/decisions/direct-commands-execute-by-default.md`
- `.10x/decisions/duckdb-only-applied-state-hard-cutover.md`
- `.10x/specs/default-remote-namespace-routing.md`
- `.10x/specs/compact-duckdb-applied-state.md`
- `.10x/specs/interactive-apply-confirmation.md`
- `.10x/specs/approved-apply-remote-catalog-registration.md`
- `.10x/specs/apply-to-retrieval-handoff.md`

## Progress and notes

- 2026-07-18: User ratified live-by-default retrieval and interactive prompt-before-write apply. Safe cancellation, explicit `--dry-run`, and non-interactive `--approve` behavior were confirmed separately.
- 2026-07-18: User superseded JSON migration with a JSON-applied-state-only hard cutover: DuckDB is sole authority and obsolete JSON files are ignored without reads, mutation, warnings, or errors. Unrelated compatibility remains in scope.
- 2026-07-18: Independent shaping review passed after correcting child dependency coverage, invalid-DuckDB fail-closed semantics, ledger-before-catalog sequencing, and record references. Review: `.10x/reviews/2026-07-18-direct-command-defaults-shaping-review.md`.
