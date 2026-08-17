Status: active
Created: 2026-07-15
Updated: 2026-08-16

# Protected GitHub Branches

## Purpose and scope

Define the repository's behavioral pull-request, CI, review, and merge-method
gates for the long-lived `develop` integration branch and `main` release branch
in `Doctacon/buoy`, including the truthfully observed hosted posture.

## Completed branch bootstrap

- `develop` was created from exact then-current `main` commit `78d255b6e54567018e4ea7ad565a67224ee9c4bf` and pushed to `origin`.
- The initial direct-push bootstrap exception is consumed historical authority and MUST NOT be reused.
- Branch protection was installed historically before ordinary work merged;
  that observation is not a claim about current hosted state.

## Current hosted posture and behavioral gates

Readback on 2026-08-16 established that `main` and `develop` currently have no
hosted branch-protection rules. The owner explicitly chose to retain that
absence. No agent, workflow, integration session, or release session may create,
restore, weaken, or otherwise change branch protection under this specification.

Hosted absence is not merge or push authority. Pull requests, exact-head CI,
independent review, branch roles, and merge methods below remain mandatory
behavioral stop gates. The responsible integration or release session must
read and verify those gates and must stop rather than merge when any is absent,
failed, stale, ambiguous, or mismatched.

No agent, workflow, integration session, or release session may directly push
or force-push either long-lived branch, bypass a pull request, or treat
administrator capability as authority.

## CI behavior

`.github/workflows/ci.yml` MUST run for:

- every pull request; and
- pushes to `main` and `develop`.

It MUST retain read-only permissions, locked dependencies, Python 3.11/3.13
tests, one build, pinned actions, concurrency, no secrets, and
repository-native commands. Release publication is paused and main-push
behavior is governed by
`.10x/decisions/release-publication-is-paused.md`.

Static tests MUST assert the exact push branch set so the checked-in workflow cannot silently stop validating either long-lived branch.

## Pull-request flows

### Task integration

Given a `work/*` branch based on current `develop`, the integration session MUST
NOT merge its pull request until the exact current head incorporates current
`develop`, the app-bound `Python 3.11`, `Python 3.13`, and
`Build distributions` checks pass for that exact head, and required independent
review passes. The integration session MUST squash-merge the ordinary task pull
request.

The exact v0.4 and PR #117 squash-topology bridges are consumed historical
exceptions and grant no current authority. PR #117 bridge PR #121 completed as
integration `33e7a52d85ed28a637090cedfa470c5ed9e8196b` under
`.10x/tickets/done/2026-08-16-bridge-pr-117-squash-topology-once.md`; its
decision and specification are superseded, and its evidence and independent
review record the exact non-repeatable result. No pending exception authorizes
merge-commit integration for any `work/* -> develop` task. Current hosted
branch protection remains intentionally absent under the user's retained
choice, and no completed exception authorizes restoring or changing it.

### Release integration

Given a same-repository `develop -> main` pull request, the dedicated release
session MUST NOT merge until all four exact-head readiness checks and required
independent release review pass. It MUST use a merge commit, never squash or
rebase. Passing those behavioral gates does not authorize an automated merge,
tag, or Release; publication remains separately paused.

### Direct push

Agents, workflows, integration sessions, and release sessions MUST NOT directly
push or force-push `develop` or `main`. Because current hosted settings do not
reject such a push mechanically, every session must treat that capability as
forbidden and route long-lived-branch changes through the reviewed pull-request
flows above.

## Release compatibility

- `.github/workflows/release.yml` triggers only on main pushes and performs
  read-only paused-publication validation.
- No workflow may create a tag, Release, package, attestation, or retained
  distribution artifact until a later reviewed decision resumes publication.

## Acceptance criteria

- Remote `origin/develop` retains the ratified bootstrap commit in its ancestry.
- GitHub reports no branch-protection rules for `main` or `develop`, matching
  the owner's retained choice, and this task leaves that state unchanged.
- Task integration uses squash merge. The completed v0.4 and PR #117
  content-empty bridges are consumed historical exceptions; neither grants
  current merge-commit, protection-mutation, or automatic-release authority.
- CI source and static tests include both push branches.
- An ordinary task pull request runs the three exact-head develop checks and is
  not merged by the integration session until they and independent review pass.
- A release pull request runs the four exact-head readiness checks and is not
  merged by the release session until they and independent review pass; its
  merge method is merge commit.
- No direct/force push or branch-protection mutation occurs despite the absence
  of mechanical hosted enforcement.
- No launcher, local hook, or Pi extension is added.

## External side effects

The historical bootstrap authority is consumed. Current authority permits
bounded work-branch and pull-request operations only and does not authorize
direct/force pushes, bypass, protection creation/restoration/mutation, tags,
Releases, package registries, transfer/rename, secrets, or Turbopuffer mutation.
