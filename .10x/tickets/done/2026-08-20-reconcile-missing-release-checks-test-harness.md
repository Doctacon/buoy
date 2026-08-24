Status: done
Created: 2026-08-20
Updated: 2026-08-23
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

None. The user confirmed the deleted release-check module must not be restored;
implementation, dual-runtime validation, evidence, and independent review all
pass.

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
- 2026-08-23: Implemented the bounded repair in
  `b212ebb69052820b4c74caeebe49fdb6c0fcbfc2`: removed the unconditional
  `scripts.release_checks` import, its sole helper-dependent legacy-checker
  test, and the now-unused `unittest.mock.patch` import. The three retained
  tests independently exercise live Hatch-VCS, package metadata, generated
  module, archive, installation, and CLI version behavior.
- 2026-08-23: In separate offline/frozen disposable environments, Python 3.11
  and 3.13 each passed `3/3` focused dynamic-version tests, collected `1009`
  tests without an import failure, and passed the complete `1009/1009` suite.
  Ruff `F,E9`, changed-file compilation on both interpreters, lock check, and
  diff checks also passed. Exact commands, output hashes, environment limits,
  and removed-versus-retained coverage are recorded in
  `.10x/evidence/2026-08-23-missing-release-checks-test-harness-reconciliation.md`.
- 2026-08-23: No execution blockers remained after implementation. Fresh
  independent review returned PASS with no findings and is recorded in
  `.10x/reviews/2026-08-23-missing-release-checks-test-harness-review.md`.
  Every acceptance criterion maps to
  `.10x/evidence/2026-08-23-missing-release-checks-test-harness-reconciliation.md`;
  the ticket is complete.

## Retrospective

The failure was an incomplete deletion: release automation and its primary test
surface were removed, but one consumer remained in a broader dynamic-version
test module. Import-time failure then hid three still-valuable live Hatch-VCS
checks from default collection.

The effective repair classified each test by its live implementation dependency
before deleting anything. This removed only the orphaned helper test and its two
imports while preserving package/module/CLI version coherence coverage. The
separate stale CI consumer was not folded into this ticket; it has its own
bounded owner at
`.10x/tickets/2026-08-23-reconcile-stale-ci-release-automation-calls.md`.
No additional knowledge, skill, specification, decision, or follow-up record is
required.
