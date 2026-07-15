Status: active
Created: 2026-07-15
Updated: 2026-07-15

# Protected GitHub Branches

## Purpose and scope

Define GitHub and CI enforcement for the long-lived `develop` integration branch and `main` release branch in `Doctacon/buoy-search`.

## Branch bootstrap

- `develop` MUST be created from exact current `main` commit `78d255b6e54567018e4ea7ad565a67224ee9c4bf` and pushed to `origin`.
- The initial branch creation is the only direct-push bootstrap exception.
- Branch protection MUST be installed before ordinary work is merged.

## Required protection

Both `main` and `develop` MUST:

- require changes to arrive through a pull request;
- require zero approving reviews;
- require `Python 3.11`, `Python 3.13`, and `Build distributions` checks from GitHub Actions;
- require the pull request branch to incorporate the latest target branch before merge;
- apply protection to repository administrators without bypass;
- disallow force pushes;
- disallow branch deletion.

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

Given any ordinary or administrator credential, when it attempts to push a new commit directly to `main` or `develop`, then GitHub MUST reject the update while protection remains active.

## Release compatibility

- `main` remains the source of reviewed release tags.
- `.github/workflows/release.yml` remains tag-only and MUST NOT gain branch mutation behavior.
- Existing GitHub-only, annotated-tag, protected-environment, provenance, no-PyPI, and immutable-tag constraints remain unchanged.

## Acceptance criteria

- Remote `origin/develop` exists at the ratified bootstrap commit before ordinary integration.
- GitHub reports matching active protection for both `main` and `develop`.
- Task integration uses squash merge; release integration uses a merge commit.
- Required status checks, strict base freshness, pull-request requirement, zero approvals, administrator enforcement, force-push denial, and deletion denial are observable through GitHub's API.
- CI source and static tests include both push branches.
- A pull request from the implementation branch to `develop` runs all three required checks and cannot merge until they pass.
- No launcher, local hook, or Pi extension is added.

## External side effects

This specification authorizes only the following repository mutations:

- create and push `develop` at the ratified commit;
- configure protection on `main` and `develop`;
- push bounded `work/*` branches and create/merge the governing pull requests.

It does not authorize tags, releases, package publication, repository transfer/rename, secrets, environment changes, or Turbopuffer operations.