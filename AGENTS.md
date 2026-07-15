# Buoy Repository Instructions

## Start every implementation session

Before mutating source or project behavior, run:

```bash
git status --short --branch
git worktree list
```

Identify the session role and current branch. A branch/worktree never bypasses the repository's 10x execution gate: implementation still requires an executable ticket, its governing records, bounded scope, evidence, review, and coherent closure.

## Branch and worktree roles

- Ordinary implementation belongs on a `work/<ticket-or-task>` branch based on current `develop` and checked out in its own worktree.
- `develop` is integration-only. `main` is release-only.
- An ordinary task session started on `main` or `develop` must stop before implementation and move to an appropriate task worktree.
- A task session must not merge its own pull request into `develop` or `main`.
- A dedicated integration session may review and squash-merge a passing task pull request into `develop`.
- A dedicated release session may perform explicitly authorized release work involving `main`; release pull requests from `develop` use merge commits, not squash or rebase.

## Task handoff

Before handing a task to integration:

1. incorporate current `develop`;
2. run the ticket's required validation;
3. commit only the bounded change on the `work/*` branch;
4. report the branch, commit, validation, compatibility risks, and external-side-effect risks.

If `develop` advances before merge, incorporate the new target state and re-run required validation. GitHub branch protection is the mechanical merge boundary; these instructions are behavioral guidance.