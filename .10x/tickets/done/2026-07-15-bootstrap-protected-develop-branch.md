Status: done
Created: 2026-07-15
Updated: 2026-07-15
Parent: .10x/tickets/done/2026-07-15-establish-protected-development-workflow.md
Depends-On: None

# Bootstrap Protected Develop Branch

## Scope

Create local and remote `develop` from exact `main` commit `78d255b6e54567018e4ea7ad565a67224ee9c4bf`, then configure matching GitHub protection for `main` and `develop`.

This ticket owns only branch bootstrap and GitHub configuration. It MUST preserve the current uncommitted shaping records in the root working tree without staging, committing, stashing, or discarding them.

## Acceptance criteria

- Preflight proves local `main` and `origin/main` still point to `78d255b6e54567018e4ea7ad565a67224ee9c4bf` and the only working-tree changes are the expected shaping records for this plan.
- Local and remote `develop` are created at that exact commit without switching the root worktree away from `main` or disturbing its uncommitted records.
- Protection on both branches requires pull requests.
- Required approving review count is zero.
- Required checks are exactly `Python 3.11`, `Python 3.13`, and `Build distributions`, associated with GitHub Actions where the API supports app binding.
- Strict/current-base status checking is enabled.
- Administrator enforcement is enabled with no bypass.
- Force pushes and deletions are disabled.
- GitHub API readback records the effective configuration for each branch.
- No source commit, merge, tag, release, environment/secret change, package publication, or Turbopuffer operation occurs.

## Explicit exclusions

- Root `AGENTS.md`.
- CI source or test changes.
- Pull-request creation or merge.
- Default-branch changes.
- Launcher, hook, or Pi extension installation.
- Release workflow changes.

## References

- `.10x/decisions/protected-development-and-github-release-governance.md`
- `.10x/specs/protected-github-branches.md`
- `.10x/tickets/done/2026-07-15-establish-protected-development-workflow.md`

## Evidence expectations

Record:

- exact local and remote commit IDs before branch creation;
- the branch creation/push result;
- sanitized GitHub API protection readback for both branches;
- confirmation that uncommitted shaping records are unchanged;
- limits, including that configuration readback does not itself prove every rejected-push scenario.

Never record tokens or credential material.

## Design notes

The direct creation/push of `develop` is the ratified one-time bootstrap exception. Protection should be configured through the smallest GitHub API surface that can express exact branch-specific administrator enforcement, PR requirements, strict required checks, force-push denial, and deletion denial. Do not add unrelated repository rules.

## Blockers

None.

## Progress and notes

- 2026-07-15: Ticket opened after exact policy ratification. No external mutation has occurred.
- 2026-07-15: Preflight confirmed `HEAD`, local `main`, and `origin/main` at ratified commit `78d255b6e54567018e4ea7ad565a67224ee9c4bf`; no local/remote `develop`, no existing branch protection, no staged files, and only the expected shaping-record changes.
- 2026-07-15: Created local and remote `develop` at exact ratified commit without switching the root worktree. Configured matching classic protection on `main` and `develop`: PR required, zero approvals, strict `Python 3.11` / `Python 3.13` / `Build distributions` checks bound to GitHub Actions app `15368`, administrator enforcement with no bypass allowance, and force-push/deletion denial. Independent API and digest assertions passed. Evidence: `.10x/evidence/2026-07-15-bootstrap-protected-develop-branch.md`.
- 2026-07-15: Independent review passed: `.10x/reviews/2026-07-15-bootstrap-protected-develop-branch-review.md`. Parent inspection independently confirmed refs and effective GitHub protection. Every acceptance criterion maps to the evidence and review; ticket closed.

## Retrospective

The generic subagent acceptance policy incorrectly required `tests-added` evidence for a configuration-only ticket, causing the worker run to report failure after successful execution. Direct API readback and independent review prevented harness status from being mistaken for product state. This is a runtime orchestration mismatch, not reusable repository procedure, so no project knowledge or skill record is warranted. The first live protected-PR exercise remains owned by the downstream integration ticket rather than widening this bootstrap ticket.