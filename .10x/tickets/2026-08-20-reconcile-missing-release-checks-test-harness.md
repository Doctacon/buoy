Status: active
Created: 2026-08-20
Updated: 2026-08-21
Parent: None
Depends-On: None
Relates-To: .10x/tickets/done/2026-08-20-implement-local-telemetry-v2-storage-migration.md

# Reconcile Missing Release Checks Test Harness

## Scope

Remove the stale test surface left on current
`develop@0c669c5ea52a7dd1adf060c9197a395a2d05e21d`, which intentionally deleted
`scripts/release_checks.py` and its unsupported release automation while
retaining `tests/test_dynamic_version.py`'s unconditional import and assertions
for that deleted code. Restore collectable truthful tests without recreating
release automation. Retain a test from that file only if it independently
exercises live package-version behavior without reconstructing the deleted
helper.

This is an independent regression introduced by the release-cleanup commit. It
must be executed on its own `work/*` branch/worktree and integrated separately;
it is not part of telemetry v2 implementation.

## Acceptance criteria

- Inspect the cleanup commit, active package/version authority, current package
  configuration, and the complete dynamic-version test file; remove every test
  and import whose only subject was the intentionally deleted release-check
  helper.
- No removed release workflow/automation, package publication, tag, Release,
  installed-tool replacement, or hosted mutation is recreated without explicit
  authority.
- Every retained dynamic-version test has a live implementation dependency and
  remains behaviorally meaningful.
- Default test collection succeeds, focused dynamic-version tests pass, and the
  complete suite reaches execution rather than failing at import.
- Evidence and independent review map the chosen reconciliation to active
  package/version authority and disclose any removed coverage.

## Explicit exclusions

Telemetry behavior, release publication, workflow recreation, GitHub changes,
main mutation, tags, packages, and installed tools.

## Blockers

None. The user confirmed in the 2026-08-20 workstream that the release-check
module was intentionally deleted because it was unsupported/nonfunctional and
must not be restored. This ratifies removal of its stale dependent tests.

## Progress and notes

- 2026-08-20: Discovered while validating telemetry v2. `git show 0c669c5`
  proves the cleanup commit deleted `scripts/release_checks.py` and
  `scripts/release_automation.py`; current `tests/test_dynamic_version.py`
  still imports `scripts.release_checks`, so unmodified pytest exits during
  collection before telemetry tests run.
- 2026-08-20: User ratified that the deleted release-check implementation was
  unsupported/nonfunctional and must not be restored. The executable outcome
  is deletion of stale helper-dependent tests/imports while preserving only
  independently live package-version coverage, if any.
- 2026-08-23: Activated on `work/reconcile-missing-release-checks-test-harness`
  from current `develop@0c669c5e`. The user explicitly superseded the prior
  GitHub-change exclusion only for pushing, reviewing, and squash-merging this
  task PR and the dependent telemetry PR into `develop`. `main`, release,
  workflow, package-publication, and installed-tool effects remain excluded.
