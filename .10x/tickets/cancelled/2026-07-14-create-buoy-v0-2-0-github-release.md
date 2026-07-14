Status: cancelled
Created: 2026-07-14
Updated: 2026-07-14
Parent: .10x/tickets/2026-07-14-buoy-public-ci-release-plan.md
Depends-On: .10x/tickets/done/2026-07-14-publish-buoy-rebrand-commit.md

# Create the Buoy v0.2.0 GitHub Release

## Scope

After the complete tree is pushed and main CI passes, configure the `release` GitHub environment with the ratified approval gate, create and push the annotated `v0.2.0` tag at the reviewed main commit, approve the pending deployment, and verify the GitHub-only release artifacts and provenance.

## Acceptance criteria

- Preflight confirms canonical repository, main commit, passing CI, project version 0.2.0, no existing conflicting tag/release, and no PyPI project/publication.
- `release` environment is configured with required approval and self-review behavior explicitly observed.
- Exactly annotated tag `v0.2.0` is created/pushed at the reviewed commit.
- Release workflow pauses for the environment and proceeds only after approval.
- GitHub Release contains wheel, sdist, generated notes, and verifiable provenance/attestation tied to the tag commit.
- README latest-release badge is added only if governed by a separately reviewed commit; the release itself does not mutate source.
- No PyPI, branch protection, force push, package token, Turbopuffer call, or unrelated GitHub mutation occurs.
- Durable evidence and independent read-only review support closure.

## Explicit exclusions

PyPI, branch protection, additional tags/releases, source changes during release, and live product operations.

## References

- `.10x/decisions/github-only-release-automation-v0-2-1.md`
- `.10x/specs/buoy-ci-and-github-releases.md`
- `.10x/tickets/done/2026-07-14-publish-buoy-rebrand-commit.md`

## Evidence expectations

Preflight, environment configuration, CI/deployment/run IDs, tag object/commit, release/assets/checksums/attestation, no-PyPI observation, and independent review.

## Progress and notes

- 2026-07-14: Commit/push dependency closed with passing canonical main CI; assigned for exact external release.
- 2026-07-14: Preflight passed. Configured required-reviewer `release` environment with self-review allowed, created/pushed exact annotated `v0.2.0` at `d846d2b2e965e7f62ff180442724d02705688a1a`, and observed hosted run `29360369610`.
- 2026-07-14: Hosted validation failed before build/deployment because `actions/checkout` exposed the tag ref as Git object type `commit` in the runner while the remote tag is correctly annotated. No artifacts, approval, release, attestation, PyPI, branch protection, source, or Turbopuffer mutation followed. Evidence: `.10x/evidence/2026-07-14-buoy-v0-2-0-release-attempt.md`.
- 2026-07-14: Supervisor directed preservation of the failed run, source, environment, and tag pending explicit user ratification of recovery semantics.
- 2026-07-14: User selected immutable-tag recovery through a new v0.2.1 patch release. This v0.2.0 release ticket is cancelled; evidence remains authoritative for the failed attempt.

## Blockers

- Superseded by `.10x/tickets/2026-07-14-create-buoy-v0-2-1-github-release.md`.
