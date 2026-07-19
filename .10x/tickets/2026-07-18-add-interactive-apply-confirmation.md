Status: active
Created: 2026-07-18
Updated: 2026-07-18
Parent: .10x/tickets/2026-07-18-direct-command-defaults-plan.md
Depends-On: .10x/tickets/done/2026-07-18-remove-legacy-json-applied-state.md

# Add Interactive Apply Confirmation

## Scope

Implement `.10x/specs/interactive-apply-confirmation.md` after the retrieval-default child integrates:

- add explicit `apply --dry-run` preflight;
- make interactive plain apply display complete preflight then prompt `Apply this plan? [y/N] `;
- exact `y`/`yes` enters the existing approved path with full revalidation;
- every other input/EOF safely cancels exit 0 with zero side effects;
- retain `--approve` as non-interactive/automation confirmation;
- fail plain non-TTY apply before plan work;
- use the DuckDB-only non-mutating preflight path established by the preceding hard-cutover child;
- update apply help, output, README/docs/changelog, workflow knowledge, and examples.

## Acceptance criteria

- Mode precedence proves `--dry-run --approve` fails before plan selection or side effects.
- TTY fakes cover `y`, `yes`, case/whitespace, Enter, no, arbitrary input, EOF, and prompt I/O failure.
- Prompt ordering proves complete visible preflight occurs before prompt and every approved-only constructor/read/write occurs after confirmation.
- Confirmation re-enters the same approved pipeline and revalidates plan/artifact/state/lock/pending/remote invariants.
- Cancellation text/JSON (`dry_run=false`, `cancelled=true`), exit 0, plan retention, zero model/credential/API/pending/state/catalog/content effects, and clean JSON stdout are proven.
- Obsolete-JSON fixtures prove `--dry-run`, cancellation, and confirmed apply ignore it byte-for-byte; no compatibility read, migration, deletion, warning, or error occurs.
- Non-TTY plain apply fails before plan selection and names `--dry-run`/`--approve`; piped yes cannot confirm.
- `--dry-run` remains local/model/credential/API-free and works non-interactively; `--approve` remains prompt-free and compatible.
- Existing stale deletion, batching/timing, lock, pending recovery, catalog registration, cleanup, and failure tests remain protective.
- Focused/full Python 3.11/3.13 tests, distributions, evidence, independent review, and hosted checks pass.

## Evidence expectations

Captured TTY/non-TTY call ordering and streams; exact side-effect sentinels; text/JSON snapshots; compatibility suites; full/hosted check identities.

## Blockers

The DuckDB-only hard-cutover child must integrate after retrieval defaults and before this ticket so applied-state handling plus shared help/docs each have one writer and one final authority.

## Explicit exclusions

Catalog command prompts/defaults; immediate non-interactive writes; config/env auto-confirm; piped approval; changed stale deletion or remote recovery semantics; release.

## References

- `.10x/tickets/2026-07-18-direct-command-defaults-plan.md`
- `.10x/decisions/direct-commands-execute-by-default.md`
- `.10x/decisions/duckdb-only-applied-state-hard-cutover.md`
- `.10x/specs/interactive-apply-confirmation.md`
- `.10x/specs/approved-apply-remote-catalog-registration.md`
- `.10x/specs/compact-duckdb-applied-state.md`
- `.10x/specs/approved-apply-throughput-measurement.md`
- `.10x/specs/plan-artifact-lifecycle-cleanup.md`
- `.10x/knowledge/buoy-site-planning-workflow.md`

## Progress and notes

- 2026-07-18: Dependency `.10x/tickets/done/2026-07-18-remove-legacy-json-applied-state.md` is integrated at `686435c`; implementation started on `work/add-interactive-apply-confirmation` from the matching `develop` head.
- 2026-07-18: Implemented apply mode gating, explicit prompt-free dry-run, exact TTY confirmation, safe cancellation/prompt failure, clean JSON/text output, and confirmation entry into the unchanged approved pipeline with locked revalidation. Updated help, README, indexing guide, changelog, workflow skill/reference, and focused tests.
- 2026-07-18: Focused 109-test and full 413-test suites passed on Python 3.11 and 3.13; wheel/sdist build, exact asset validation, compile, diff, staged-file, and obsolete-JSON production-source checks passed. Evidence: `.10x/evidence/2026-07-18-interactive-apply-confirmation.md`.
