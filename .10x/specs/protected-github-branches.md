Status: active
Created: 2026-07-15
Updated: 2026-07-21

# Protected GitHub Branches

## Purpose and scope

Define GitHub and CI enforcement for the long-lived `develop` integration branch and `main` release branch in `Doctacon/buoy-search`.

## Completed branch bootstrap

- `develop` was created from exact then-current `main` commit `78d255b6e54567018e4ea7ad565a67224ee9c4bf` and pushed to `origin`.
- The initial direct-push bootstrap exception is consumed historical authority and MUST NOT be reused.
- Branch protection was installed before ordinary work merged.

## Required protection

Both `main` and `develop` MUST require pull requests, zero fixed approving reviews, administrator enforcement without bypass, and branch-deletion denial.

`develop` MUST require strict app-bound `Python 3.11`, `Python 3.13`, and `Build distributions`; disallow force pushes; and disable last-push approval.

`main` MUST require the four app-bound checks governed by `.10x/specs/develop-to-main-release-readiness.md`; use `strict=false`; allow force pushes under the user's retained hosted setting; and disable last-push approval. The force-push capability is not authorized for any agent/workflow/release path.

Protection MUST NOT require code-owner review, signed commits, linear history, deployment success, conversation resolution, or additional checks unless separately ratified.

## CI behavior

`.github/workflows/ci.yml` MUST run for:

- every pull request; and
- pushes to `main` and `develop`.

It MUST retain read-only permissions, locked dependencies, Python 3.11/3.13 tests, one build, pinned actions, concurrency, no secrets, and repository-native commands. Release PR and publication behavior are governed by `.10x/specs/develop-to-main-release-readiness.md` and `.10x/specs/main-push-automatic-github-release.md`.

Static tests MUST assert the exact push branch set so the checked-in workflow cannot silently stop validating either long-lived branch.

## Pull-request flows

### Task integration

Given a `work/*` branch based on `develop`, when its pull request targets `develop`, then GitHub MUST block merge until all required checks pass on a head that incorporates current `develop`. The integration session MUST squash-merge the task pull request.

The sole exception is the exact one-time v0.4 squash-topology bridge in `.10x/decisions/one-time-v0-4-squash-topology-bridge.md`. That protected, tree-identical bridge PR MUST use a merge commit so exact main ancestry survives integration. This exception is pinned, migration-only, and MUST NOT authorize merge commits for any other `work/* -> develop` task.

### Release integration

Given a `develop -> main` pull request, GitHub MUST block merge until all four readiness checks validate the exact prospective merge result. Main strict freshness and develop-as-ancestor are not required; no ancestry-sync operation or release-specific merge method is prescribed. The automatic main-push workflow revalidates the resulting exact main commit before mutation.

### Direct push

Given any ordinary or administrator credential, direct pushes to `develop` MUST be rejected mechanically. Agents and release procedures MUST NOT directly push or force-push `main` even though its retained hosted configuration permits force pushes; all main changes still arrive through reviewed pull requests.

## Release compatibility

- `main` is the source of automatic stable-SemVer release tags.
- `.github/workflows/release.yml` triggers only on main pushes and MAY create only the new annotated version tag governed by the active automatic-release specification.
- GitHub-only, provenance, no-PyPI, and immutable-tag constraints remain; the release-environment approval is removed.

## Acceptance criteria

- Remote `origin/develop` exists at the ratified bootstrap commit before ordinary integration.
- GitHub reports the ratified common protection plus exact branch-specific checks/freshness/force-push/last-push settings.
- Task integration uses squash merge except for the exact one-time v0.4 tree-identical bridge, whose merge-commit ancestry is independently verified; release integration otherwise relies on prospective-merge readiness plus exact-main revalidation, not ancestry ceremony.
- Develop strict checks and main non-strict four-check policy, pull requests, zero fixed approvals, administrator enforcement, deletion denial, develop force-push denial, retained main force-push allowance, and last-push approval disabled are observable.
- CI source and static tests include both push branches.
- A pull request from the implementation branch to `develop` runs all three required checks and cannot merge until they pass.
- No launcher, local hook, or Pi extension is added.

## External side effects

The historical bootstrap authority is consumed. The separately bounded simple-release implementation ticket may replace main's required checks, set `strict=false`, disable last-push approval, and delete the unused release environment only after repository workflow proof. Otherwise current authority permits bounded work-branch/PR operations only and does not authorize direct/force pushes, bypass, unrelated protection mutation, tags/releases outside the automatic workflow, package registries, transfer/rename, secrets, or Turbopuffer.