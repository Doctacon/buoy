Status: open
Created: 2026-08-20
Updated: 2026-08-20
Parent: None
Depends-On: None
Relates-To: .10x/tickets/2026-08-20-implement-local-telemetry-v2-storage-migration.md

# Reconcile Missing Release Checks Test Harness

## Scope

Determine and implement the smallest record-backed reconciliation for current
`develop@0c669c5ea52a7dd1adf060c9197a395a2d05e21d`, which deleted
`scripts/release_checks.py` and the release automation while retaining
`tests/test_dynamic_version.py`'s unconditional `from scripts import
release_checks`. Restore a collectable truthful test suite without recreating
unapproved release automation or weakening still-active dynamic-version
behavior.

This is an independent regression introduced by the release-cleanup commit. It
must be executed on its own `work/*` branch/worktree and integrated separately;
it is not part of telemetry v2 implementation.

## Acceptance criteria

- Inspect the cleanup commit, active release/package specifications and
  decisions, current package configuration, terminal release records, and the
  complete dynamic-version test file before choosing deletion, replacement, or
  a narrowed retained helper.
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

The intended post-cleanup dynamic-version/release-check boundary is not yet
classified from active records. This ticket begins in shaping/research state
and is not executable until that authority is resolved without guessing.

## Progress and notes

- 2026-08-20: Discovered while validating telemetry v2. `git show 0c669c5`
  proves the cleanup commit deleted `scripts/release_checks.py` and
  `scripts/release_automation.py`; current `tests/test_dynamic_version.py`
  still imports `scripts.release_checks`, so unmodified pytest exits during
  collection before telemetry tests run.
