Status: active
Created: 2026-08-24
Updated: 2026-08-24
Parent: .10x/tickets/done/2026-08-20-correct-retrieve-command-telemetry-latency.md
Depends-On: .10x/tickets/done/2026-08-20-reconcile-missing-release-checks-test-harness.md, .10x/tickets/done/2026-08-23-reconcile-stale-ci-release-automation-calls.md
Decision: .10x/decisions/buoy-records-command-and-pipeline-retrieve-latency.md
Specifications: .10x/specs/retrieve-command-telemetry.md, .10x/specs/local-telemetry-v2-storage-and-migration.md

# Integrate Retrieve Command Telemetry Into Develop

## Scope

Incorporate exact current `develop@3eabedd6b1e2c60a2a8be2489327b014d04130fc`
into `work/retrieval-command-telemetry-v2` without rewriting the already reviewed
telemetry implementation history. Reconcile the now-done stale-test/CI record
graph, run complete unfiltered local and package validation at the combined
head, push one telemetry PR to `develop`, require exact-head hosted CI and
independent review, then hand the authorized squash merge to a dedicated
integration session.

The production telemetry runtime remains implementation
`6bfd0d4cec784cec18e9050bef4a8d0787f354e7`; later product commits change only
README/changelog and timing tests. Incorporating `develop` adds the reviewed
orphan-test deletion and exact two-line CI cleanup from squash commit
`3eabedd6`. No new telemetry or cleanup behavior is authorized here.

## Acceptance criteria

- The task branch incorporates exact current `origin/develop` without rebase or
  history rewriting; the merge base after incorporation is the current develop
  commit.
- The duplicate active stale-test ticket is removed, all live references use
  the done path, and both cleanup tickets remain done and coherent.
- Production CLI, telemetry envelope, and routing-artifact bytes retain their
  accepted SHA-256 identities; the active routing receipt still loads.
- Complete unfiltered Python 3.11 and 3.13 suites pass, including all retained
  dynamic-version and telemetry-v2 tests.
- Lock, ranking, C6, Ruff `F,E9`, compilation, diff hygiene, focused integrated
  telemetry, and controlled timing checks pass.
- A clean exact combined-head wheel/sdist build, archive inspection, isolated
  install, disabled preview, telemetry management help/status, and active
  routing smoke pass without using the owner's real home or installed tool.
- One integrated evidence record maps inherited telemetry acceptance, cleanup
  integration, exact identities, commands/results, package hashes, and limits.
- Fresh independent review passes with no unresolved concern.
- The exact PR head passes hosted Python 3.11, Python 3.13, and distribution
  build/smoke checks against current `develop`.
- A dedicated integration session rechecks head/base/checks/mergeability and
  squash-merges only the reviewed PR into `develop`.

## Explicit exclusions

No `main`, tag, Release, package publication, installed-tool replacement,
provider/model/content/credential/catalog/namespace operation, real telemetry
migration, workflow change beyond the already integrated cleanup, new runtime
behavior, automatic migration/deletion, or history rewrite.

## Evidence expectations

Create `.10x/evidence/2026-08-24-retrieve-command-telemetry-develop-integration.md`
with exact develop/task identities, merge and record reconciliation, unfiltered
test/static/package results, source/package hashes, PR/check URLs and IDs, and
external-effect limits. Create separate implementation and final integration
reviews. Treat the GitHub PR as canonical for hosted check and merge state.

## Blockers

None. The user explicitly authorized the cleanup and telemetry PRs into
`develop` while retaining every exclusion above. Cleanup PR #144 is squash-
merged at `3eabedd6` and its post-merge CI passed.

## Progress and notes

- 2026-08-24: Opened after cleanup PR #144 merged into `develop` and post-merge
  GitHub Actions run `32756975414` passed. Current local and remote `develop`
  both resolve to `3eabedd6`; telemetry task branch is clean at `ef756020`.
  This is the sole remaining unit authorized by the user's “do all of that”
  instruction.
- 2026-08-24: Activated after exact local preflight. Before mutation,
  `git status --short --branch` reported clean branch
  `work/retrieval-command-telemetry-v2`; `git worktree list` confirmed this
  task worktree and integration-only `develop` worktree roles. After
  `git fetch origin`, ticket-opening HEAD was exactly
  `88553279099cadde8588fd390ba645da5a1903ab` with sole parent
  `ef756020aab8811e5ac60dde79c2894451683501`; local `develop` and
  `origin/develop` were both exactly
  `3eabedd6b1e2c60a2a8be2489327b014d04130fc`; immutable production runtime
  `6bfd0d4cec784cec18e9050bef4a8d0787f354e7` remained present. Porcelain was
  empty and no identity differed or had advanced. The governing decision,
  both specifications, prior integrated telemetry evidence/reviews, both done
  cleanup ticket/evidence/review sequences, and repository instructions were
  read in full before activation.
