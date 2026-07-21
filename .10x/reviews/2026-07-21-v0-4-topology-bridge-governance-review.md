Status: recorded
Created: 2026-07-21
Updated: 2026-07-21
Target: PR #94 one-time v0.4 topology bridge governance
Verdict: concerns

# v0.4 Topology Bridge Governance Review

## Findings

Independent review confirmed the PR #93 diagnosis, exact merge base, pinned/content-neutral bridge concept, hosted merge-commit support, force-push denial, and non-repeatable/no-live-mutation boundary.

It found two blockers:

1. `.10x/specs/protected-github-branches.md` required every `work/* -> develop` PR to squash, which would discard bridge ancestry.
2. No executable child ticket owned bridge creation/integration, while the release parent excluded ancestry sync.

It also noted that `.10x/decisions/simple-main-release-governance.md` should acknowledge the pinned migration exception.

## Response

- Added the sole exact merge-commit exception to protected-branch behavior and acceptance criteria without generalizing task merge methods.
- Opened `.10x/tickets/2026-07-21-bridge-v0-4-squash-topology-once.md` with exact parents/tree, protected checks, independent review, merge method, ancestry/tree verification, non-mutation, and non-repeatability criteria.
- Updated the release parent to delegate only this exception and to use the repository-required merge commit for `develop -> main` promotion.
- Updated simple release governance to distinguish the pinned inherited migration from prohibited recurring sync ceremony.

## Verdict

Concerns are addressed in the PR branch but require final independent rereview before integration.

## Residual risk

GitHub handling of a zero-content bridge PR is not assumed as proof; execution must stop if the host cannot represent or protect the exact commit topology.
