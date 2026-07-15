Status: active
Created: 2026-07-15
Updated: 2026-07-15

# Protected Development and GitHub Release Governance

## Context

Buoy previously used one Pi session directly on unprotected `main`. The active release decision deliberately omitted branch protection. The maintainer is moving to concurrent Pi sessions in Git worktrees, with a long-lived integration branch and periodic releases to `main`. Concurrent integration makes direct writes to shared branches and CI results from stale branch bases materially riskier.

At ratification time:

- local and remote `main` are clean and point to `78d255b6e54567018e4ea7ad565a67224ee9c4bf`;
- no `develop` branch exists;
- GitHub reports no protection on `main` and no repository rulesets;
- the authenticated maintainer has repository administration permission;
- current CI check names are `Python 3.11`, `Python 3.13`, and `Build distributions`.

The maintainer explicitly selected protection on both long-lived branches, pull requests with all three CI checks, zero human approvals, strict base freshness, no administrator bypass, and no launcher, Git hook, or Pi extension. Task pull requests are squash-merged into `develop`; release pull requests use merge commits from `develop` into `main` so release ancestry remains coherent.

## Decision

### Branch roles

- `main` is the release branch. Ordinary implementation MUST NOT occur directly on it.
- `develop` is the integration branch for the next release. Ordinary implementation MUST NOT occur directly on it.
- Normal Pi implementation sessions use one `work/<ticket-or-task>` branch and worktree based on current `develop`.
- Regular task sessions prepare and validate work but do not merge themselves. A dedicated integration session reviews and merges pull requests into `develop`.
- Task pull requests from `work/*` are squash-merged into `develop`.
- A release is prepared through reviewed `develop` state, merged to `main` by pull request using a merge commit, and tagged from the resulting reviewed `main` commit.

### GitHub enforcement

- Create `develop` from exact current `main` commit `78d255b6e54567018e4ea7ad565a67224ee9c4bf`.
- Protect both `main` and `develop`.
- Both branches require a pull request before merge.
- Required approving review count is zero because this is currently a solo-maintained repository.
- The `Python 3.11`, `Python 3.13`, and `Build distributions` GitHub Actions checks must pass.
- Required checks use strict base freshness: a pull request must incorporate the current target branch before merge.
- Protection applies to administrators with no bypass.
- Force pushes and branch deletion remain disallowed.
- CI runs for all pull requests and pushes to both `main` and `develop`.

The unavoidable initial creation/push of `develop` from current `main` occurs before protection is installed. This is a one-time bootstrap operation, not an ongoing direct-push exception.

### Pi enforcement posture

A tracked root `AGENTS.md` is the always-loaded behavioral instruction for Pi sessions. No standard launcher, Git hook, or Pi extension is added. GitHub protection is the hard merge boundary; `AGENTS.md` supplies local session discipline.

### Release contract retained

- Preserve public annotated `v0.2.0` and failed run `29360369610` as immutable failed-attempt history; never create a GitHub Release for that tag.
- Retain GitHub-only publication, the protected `release` environment approval, build-once artifacts, provenance attestation, generated notes, least privileges, pinned actions, and no PyPI publication.
- Release tags remain annotated `v<project version>` tags created from reviewed `main` commits.
- The tag-triggered release workflow continues to validate authoritative remote annotated-tag metadata and exact package/module versions before mutation.

## Alternatives considered

### Continue direct work on main

Rejected because concurrent Pi sessions would share one integration boundary without isolation or mechanical merge control.

### Protect main only

Rejected because direct writes to `develop` would bypass the same integration and CI guarantees intended for concurrent worktrees.

### Require one approval

Rejected for now because the repository has one maintainer and self-authored pull requests cannot provide an independent approval. CI remains mandatory.

### Permit administrator bypass

Rejected because it would preserve the accidental direct-push path the protection is intended to remove. Emergency recovery requires deliberately changing the rule first.

### Add a launcher, Git hook, or Pi extension

Rejected by explicit maintainer choice. These add local setup or runtime machinery while GitHub protection already supplies the durable merge boundary.

### Merge commits for every task

Rejected because preserving every temporary task branch would add history noise without improving release ancestry.

### Rebase task commits into develop

Rejected in favor of one bounded squash commit per task.

### Full GitFlow release and hotfix branches

Not selected. No release-stabilization or hotfix behavior was ratified, so those branches are not introduced speculatively.

## Consequences

Concurrent tasks gain isolated worktrees and a serialized, tested integration path. Pull requests may need updating after another task lands, increasing merge friction in exchange for stronger integration assurance. The maintainer cannot bypass protections without first changing GitHub configuration. `main` remains compatible with the existing tag-triggered GitHub-only release process.

This decision supersedes `.10x/decisions/superseded/github-only-release-automation-v0-2-1.md`; all retained release constraints are restated here.