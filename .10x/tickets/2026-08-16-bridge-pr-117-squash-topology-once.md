Status: active
Created: 2026-08-16
Updated: 2026-08-16
Depends-On: .10x/tickets/done/2026-08-16-govern-pr-117-squash-topology-repair.md
Decision: .10x/decisions/one-time-pr-117-squash-topology-repair.md
Specification: .10x/specs/one-time-pr-117-squash-topology-repair.md
Evidence: .10x/evidence/2026-08-16-pr-117-squash-topology-repair.md

# Bridge PR #117 Squash Topology Once

## Outcome

After the governance/content-alignment prerequisite is independently reviewed
and squash-integrated, make exact PR #117 squash `M` an ancestor of then-current
`develop` through one reviewed, CI-gated, content-neutral, non-repeatable
bridge.

## Preconditions

- The dependency ticket is closed with passing governance review and exact
  four-blob alignment evidence.
- The decision, active specification, and narrow branch-flow exception are
  present on `origin/develop` before bridge creation.
- A fresh fetch proves `origin/main` still equals
  `0db802ec1a895f289c7600b19c80603986839873` (`M`).
- The executor binds exact post-prerequisite `origin/develop` as `D`, records
  `tree(D)`, and proves all required aligned/governance/reader-fix paths.
- No bridge commit, branch, PR, review pass, hosted CI result, or integration is
  presumed by this ticket's creation.

## Execution scope

1. Perform the specification's exact preflight and stop on any ref, blob,
   inventory, ancestry, hosted-state, or tree mismatch.
2. Create isolated branch/worktree
   `work/bridge-pr-117-squash-topology-once` from exact `D`.
3. Create one true merge commit `C` whose ordered parents are `[D, M]` and whose
   tree is byte-identical to `D`; edit and stage no file.
4. Push only the bridge branch and open one PR to `develop`. Require zero
   changed files/additions/deletions and exact-head hosted CI. These are
   behavioral gates; current hosted protection is intentionally absent.
5. Obtain independent review of the exact bridge commit and hosted state. The
   review contract is established now; the review itself must occur later and
   pass before integration.
6. In a dedicated integration session, merge the bridge PR with a merge commit,
   not squash/rebase. Require integration `I` ordered parents `[D, C]`,
   `tree(I) == tree(D)`, and `M` ancestry.
7. Record post-integration evidence/review and close this ticket through an
   ordinary reviewed closure task. Demonstrate that the ordinary future
   `develop -> main` PR can construct its candidate, but do not merge it here.

## Acceptance

- All preconditions and exact stop-on-drift assertions pass.
- `C` has exact ordered parents `[D, M]` and exact first-parent tree.
- The bridge PR is content-empty and all three exact-head develop checks pass
  as behavioral gates before integration.
- Independent read-only review passes before integration.
- `I` uses merge-commit integration with exact ordered parents `[D, C]` and the
  unchanged `D` tree; both `M` and `C` are ancestors.
- Long-lived refs, intentionally absent protection, release/publication state,
  provider state, and repository content remain within the exact specification.
- Final evidence is recorded, the exception is marked consumed, and no retry or
  generalized merge-commit authority remains.

## Evidence expectations

Exact fetch time and refs; commit parents and trees; merge base/divergence;
four imported blob identities; content allowlist and zero-diff hashes; bridge
PR identity; exact check names/run/job IDs and conclusions; independent review
target/verdict; integration method/SHA/parents/tree; ancestry checks; unchanged
main/protection/tag/Release/provider observations; provider request/write count
zero.

## External effects

Only after every precondition passes, this ticket permits a bridge-branch push,
one PR, hosted read-only CI/review, and merge-commit integration into
`develop`. It authorizes no direct/force push, bypass, protection change, main
merge, tag, Release, package publication, provider request/write, catalog
migration, content-index mutation, credential access/change, or other branch.

## Explicit exclusions

Any file/content change in the bridge; importing additional main paths;
squash/rebase integration; reusing the v0.4 exception; executing before the
dependency is integrated; assuming GitHub can represent a zero-diff PR;
continuing after drift; merging `develop -> main`; publication/provider work.

## Progress

- 2026-08-16: Opened as an executable future child of the governance/content-
  alignment task. No bridge worktree, commit, branch, PR, CI, review verdict,
  merge, provider call, protection change, or publication occurred.
