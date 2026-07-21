Status: active
Created: 2026-07-21
Updated: 2026-07-21

# Protected Development and GitHub Release Governance v2

## Context

Buoy uses concurrent Pi sessions in Git worktrees, a protected long-lived `develop` integration branch, and periodic releases to protected `main`. The original governance decision required identical protection details on both long-lived branches.

During the v0.4.0 release, hosted inspection found that `develop` still matched that contract while `main` allowed force pushes and required approval from someone other than the last pusher. The user explicitly chose `Keep current rules` after being shown the exact consequences and later clarified that release execution should proceed without restoring the old settings.

This decision retains protected pull requests, all three CI checks, strict base freshness, administrator enforcement, deletion denial, branch roles, task squash merges, release merge commits, and GitHub-only annotated-tag publication. It ratifies only the two observed `main` exceptions: force pushes remain enabled and last-push approval remains enabled. `develop` retains force-push denial and no last-push approval requirement.

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
- Required approving review count is zero.
- The `Python 3.11`, `Python 3.13`, and `Build distributions` GitHub Actions checks must pass.
- Required checks use strict base freshness: a pull request must incorporate the current target branch before merge.
- Protection applies to administrators with no bypass.
- Branch deletion remains disallowed on both branches.
- `develop` disallows force pushes and does not require last-push approval.
- `main` retains its observed settings: force pushes are allowed and last-push approval is required.
- CI runs for all pull requests and pushes to both `main` and `develop`.

No direct push, force push, protection mutation, or bypass is authorized by this decision. Allowing force pushes on `main` records hosted configuration; release work still proceeds only by protected pull request.

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

### Require a fixed approving-review count of one

Rejected because the repository remains configured with zero fixed approving reviews. Main's separately retained last-push approval may still require one eligible reviewer who did not make the latest push; that hosted rule is narrower than a fixed approval count and may mechanically block a solo-authored release PR.

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

Concurrent tasks retain isolated worktrees and a serialized, tested integration path. `main`'s last-push approval may require an eligible reviewer before a release PR can merge; if no eligible reviewer exists, release remains mechanically blocked rather than weakening the setting. Enabled force pushes increase destructive-history risk, but this decision does not authorize using them. `main` remains compatible with the existing tag-triggered GitHub-only release process.

This decision supersedes `.10x/decisions/superseded/protected-development-and-github-release-governance.md`. The older GitHub-only release decision remains superseded history at `.10x/decisions/superseded/github-only-release-automation-v0-2-1.md`.