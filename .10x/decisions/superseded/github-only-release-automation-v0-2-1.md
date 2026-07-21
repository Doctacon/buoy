Status: superseded
Created: 2026-07-14
Updated: 2026-07-15

# GitHub-Only Release Automation with v0.2.1 Recovery

## Context

The original GitHub-only release decision targeted annotated `v0.2.0`. The public annotated tag was created at reviewed commit `d846d2b2e965e7f62ff180442724d02705688a1a`, but hosted run `29360369610` failed before build or release mutation because checkout materialized the ref as a commit and the workflow tested the local object type. No release, assets, attestation, or package publication occurred.

Moving or deleting the public tag would weaken tag immutability. The user selected a new patch release.

## Decision

- Preserve public annotated `v0.2.0` and failed run as immutable failed-attempt history; never create a GitHub Release for that tag.
- Fix hosted annotated-tag validation by inspecting the remote GitHub tag ref/object through the GitHub API (or equivalently authoritative remote metadata), not checkout's dereferenced local ref.
- Bump project/module/changelog target to `0.2.1` in a reviewed commit and pass canonical main CI.
- Create only new annotated tag `v0.2.1` at that reviewed commit.
- Retain GitHub-only publication, protected `release` environment approval, build-once artifacts, provenance attestation, generated notes, least privileges, pinned actions, no PyPI, and no branch protection.
- README release badge may be activated only after v0.2.1 succeeds.

## Alternatives considered

- Delete/recreate v0.2.0: rejected because it rewrites a public ref.
- Stop without release: rejected because the hosted defect is bounded and repairable.

## Consequences

Version 0.2.0 remains an annotated tag without a Release. Version 0.2.1 becomes the first GitHub Release. Release docs/changelog must explain the skipped release. The original decision is superseded by this complete recovery contract.

## Supersession

Superseded by `.10x/decisions/superseded/protected-development-and-github-release-governance.md`, which retains the release contract but replaces the no-branch-protection choice with the ratified protected `develop`/`main` workflow.
