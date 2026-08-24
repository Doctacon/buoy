Status: active
Created: 2026-08-23
Updated: 2026-08-23
Parent: None
Depends-On: .10x/tickets/done/2026-08-20-reconcile-missing-release-checks-test-harness.md

# Reconcile Stale CI Release-Automation Calls

## Scope

Remove exactly the two `.github/workflows/ci.yml` command invocations of the
intentionally deleted `scripts/release_automation.py`: `validate-source` in the
test job and `validate-distribution dist` in the build job. Preserve every
other CI trigger, permission, concurrency rule, matrix entry, action pin,
ranking/C6 validation, unfiltered test command, distribution build, isolated
wheel install, and smoke assertion byte-for-byte where YAML structure permits.

The cleanup commit `0c669c5e` intentionally deleted unsupported release
automation but left these two consumers. The current workflow therefore cannot
pass at any PR head even after the separately owned stale dynamic-version test
is repaired. This ticket removes dead consumers; it does not recreate or
replace release validation.

## Acceptance criteria

- CI contains no reference to absent `scripts/release_automation.py` or
  `scripts/release_checks.py`.
- The source-validation step still runs ranking-contract and C6 validation.
- Python 3.11/3.13 unfiltered tests, distribution build, clean-wheel install,
  CLI/module help, tokenizer, routing-canary, and active-routing smoke remain.
- The workflow diff removes only the two stale invocations and the minimum
  shell-block syntax made redundant by those deletions.
- YAML parses, static workflow inspection passes, and the aggregate cleanup PR
  receives exact-head CI PASS on both Python versions plus the build job.
- Evidence and independent review disclose that deleted release source/
  distribution invariants are not replaced by this ticket.

## Explicit exclusions

No restored release script/test/workflow, replacement validation framework,
new CI job/action/permission/trigger, dependency or package change, runtime or
telemetry change, `main`, tag, Release, package publication, installed-tool
replacement, provider/model/content/credential operation, or unrelated cleanup.

## Blockers

None for local implementation. The stale dynamic-version test ticket is done
and its reviewed branch has been incorporated into this aggregate cleanup
branch. Required independent review and hosted exact-head CI remain parent-owned
acceptance gates, so this ticket remains active.

## Progress and notes

- 2026-08-23: Inspection after the user's hosted-integration authorization found
  `.github/workflows/ci.yml` still invokes the intentionally deleted
  `scripts/release_automation.py` in its test and build jobs. No existing ticket
  owns this workflow drift.
- 2026-08-23: The user selected removal of only those two dead invocations while
  retaining ranking, C6, tests, build, and wheel smoke. They did not authorize
  restoring/replacing release validation or changing `main`, release,
  publication, permissions, actions, triggers, or other workflow behavior.
- 2026-08-23: Opened this bounded dependent ticket on
  `work/reconcile-stale-ci-release-automation-calls` from current
  `develop@0c669c5e`. Because stale CI calls and the stale dynamic test fail
  independently, their reviewed commits will be assembled into one cleanup PR
  before the telemetry PR.
- 2026-08-23: Reviewed stale-test closure commit `a46cbaa8` was incorporated by
  merge commit `aa884666`; its ticket is now under `.10x/tickets/done/` and
  dual-runtime unfiltered suites pass locally. Activated this dependent CI
  ticket for its exact two-call workflow deletion.
- 2026-08-23: Workflow-only implementation commit
  `33a6d8eb60319f074ee0a5139957cd8353b174c0` (tree
  `6fe239332c866613acd7185df1124744639fd1e7`) removed exactly the two dead
  `scripts/release_automation.py` invocations. It changed only
  `.github/workflows/ci.yml`, with zero additions and two deletions; no shell
  syntax became redundant and no deleted validation was restored or replaced.
- 2026-08-23: Fresh disposable offline/frozen Python 3.11 and 3.13 environments
  each passed ranking-contract and C6 validation plus the complete unfiltered
  `1009/1009` suite. A clean Python 3.13 wheel/sdist build, isolated offline
  wheel install, and the unchanged help/tokenizer/routing smoke passed. Strict
  inventory, exact-byte/YAML equivalence, lock, Ruff `F,E9`, changed-file
  compilation, and diff hygiene also passed. Exact commands, hashes, coverage
  disclosure, and limits are recorded in
  `.10x/evidence/2026-08-23-stale-ci-release-automation-call-reconciliation.md`.
- 2026-08-23: Local implementation and evidence are complete. Fresh independent
  implementation review returned PASS with no findings and approved draft-PR
  handoff; it is recorded in
  `.10x/reviews/2026-08-23-stale-ci-release-automation-call-implementation-review.md`.
  The ticket remains active only for parent-owned hosted exact-head CI, final
  acceptance reconciliation, and integration.
