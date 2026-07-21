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

Both `main` and `develop` MUST:

- require changes to arrive through a pull request;
- require zero approving reviews;
- require `Python 3.11`, `Python 3.13`, and `Build distributions` checks from GitHub Actions;
- require the pull request branch to incorporate the latest target branch before merge;
- apply protection to repository administrators without bypass;
- disallow branch deletion.

`develop` MUST disallow force pushes and MUST NOT require last-push approval. `main` retains the user-ratified hosted exceptions: force pushes are allowed and last-push approval is required. Neither exception authorizes a release or agent workflow to use force push or bypass a pull request.

Protection MUST NOT require code-owner review, signed commits, linear history, deployment success, conversation resolution, or additional checks unless separately ratified.

## CI behavior

`.github/workflows/ci.yml` MUST run for:

- every pull request; and
- pushes to `main` and `develop`.

It MUST retain the existing read-only permissions, locked dependency installation, Python 3.11 and 3.13 test jobs, single build job, pinned actions, concurrency behavior, no-secret boundary, and repository-native commands governed by `.10x/specs/buoy-ci-and-github-releases.md`.

Static tests MUST assert the exact push branch set so the checked-in workflow cannot silently stop validating either long-lived branch.

## Pull-request flows

### Task integration

Given a `work/*` branch based on `develop`, when its pull request targets `develop`, then GitHub MUST block merge until all required checks pass on a head that incorporates current `develop`. The integration session MUST squash-merge the task pull request.

### Release integration

Given reviewed release-ready `develop`, when its pull request targets `main`, then GitHub MUST block merge until all required checks pass on a head that incorporates current `main`. The release session MUST use a merge commit rather than squash or rebase so `develop` remains an ancestor of released `main`.

### Direct push

Given any ordinary or administrator credential, direct pushes to `develop` MUST be rejected mechanically. Agents and release procedures MUST NOT directly push or force-push `main` even though its retained hosted configuration permits force pushes; all main changes still arrive through reviewed pull requests.

## Release compatibility

- `main` remains the source of reviewed release tags.
- `.github/workflows/release.yml` remains tag-only and MUST NOT gain branch mutation behavior.
- Existing GitHub-only, annotated-tag, protected-environment, provenance, no-PyPI, and immutable-tag constraints remain unchanged.

## Acceptance criteria

- Remote `origin/develop` exists at the ratified bootstrap commit before ordinary integration.
- GitHub reports the ratified common protection plus the exact branch-specific force-push/last-push settings.
- Task integration uses squash merge; release integration uses a merge commit.
- Required status checks, strict base freshness, pull-request requirement, zero approvals, administrator enforcement, and deletion denial are observable on both branches; develop force-push denial and main force-push allowance/last-push approval are also observable.
- CI source and static tests include both push branches.
- A pull request from the implementation branch to `develop` runs all three required checks and cannot merge until they pass.
- No launcher, local hook, or Pi extension is added.

## External side effects

The historical bootstrap authority to create/push `develop` and configure initial protection is consumed. Current authority permits only bounded `work/*` branch pushes and creation/merge of governing pull requests under the active branch-specific settings. It does not authorize direct or force pushes to long-lived branches, protection mutation, bypass, tags, releases, package publication, repository transfer/rename, secrets, environment changes, or Turbopuffer operations.