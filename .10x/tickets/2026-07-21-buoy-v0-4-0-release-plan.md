Status: open
Created: 2026-07-21
Updated: 2026-07-21
Parent: None
Depends-On: None

# Buoy v0.4.0 Release Plan

## Outcome

Release reviewed `develop` as GitHub-only Buoy v0.4.0 while preserving protected branch ancestry, exact candidate validation, annotated-tag authority, approval-gated publication, provenance, and no-PyPI/no-Turbopuffer boundaries. This parent is an aggregate plan and is not executable.

## Child sequence

0. `.10x/tickets/done/2026-07-21-reconcile-main-protection-governance.md` (completed record-only release-governance reconciliation)
1. `.10x/tickets/done/2026-07-21-validate-buoy-v0-4-0-release-candidate.md`
2. `.10x/tickets/2026-07-21-promote-develop-to-main-for-v0-4-0.md`
3. `.10x/tickets/2026-07-21-create-buoy-v0-4-0-github-release.md`
4. `.10x/tickets/2026-07-21-finalize-buoy-v0-4-0-changelog.md`

Children are strictly sequential. No child may infer completion from a later child.

## Aggregate acceptance criteria

- Project, module, lock, wheel, and sdist metadata consistently identify 0.4.0.
- The changelog has a pending 0.4.0 section derived from the complete v0.3.0-to-candidate range before release.
- Candidate distributions pass `.10x/specs/buoy-release-validation.md`, including clean install, digest-verified 0.3.0 upgrade, removed launcher/environment aliases, retained compatibility, complete Python 3.11/3.13 tests, eval validation, links, inventory, and independent review.
- Current `main` ancestry is incorporated into release-ready `develop` through a protected ancestry-only sync PR with content-neutral merge commit; protection is not weakened.
- Historical PR #80 remains closed as stale/conflicting; one replacement `develop -> main` PR passes all required checks and any mechanically required approval, then merges using a merge commit, never squash/rebase.
- Annotated `v0.4.0` points to the exact reviewed `main` commit and authoritative remote metadata reports a tag object.
- The exact approval-gated workflow publishes the wheel/sdist, generated notes, and verifiable provenance; no PyPI publication occurs.
- Changelog release date/links are finalized only after hosted Release verification, through a separate reviewed task PR.
- Evidence and independent reviews support each child; no tag overwrite, release replacement, force push, protection change, Turbopuffer operation, or user-data mutation occurs.

## Explicit exclusions

New product behavior; reopening C3/C4/C6-C9; retrying Approval A or Crow-Plus; Turbopuffer reads/writes; PyPI; replacing tags/releases; weakening branch/environment protection; direct pushes to `main` or `develop`.

## References

- `.10x/decisions/protected-development-and-github-release-governance-v2.md`
- `.10x/specs/protected-github-branches.md`
- `.10x/specs/buoy-release-validation.md`
- `.10x/specs/buoy-ci-and-github-releases.md`
- `docs/releasing.md`
- `.10x/tickets/done/2026-07-19-buoy-v0-4-compatibility-removal-plan.md`
- PR #80: `https://github.com/Doctacon/buoy-search/pull/80`

## Progress and notes

- 2026-07-21: User explicitly requested merging the current `develop` additions into `main` and releasing them. Read-only preflight found project/module/lock at 0.4.0, no v0.4.0 tag or Release, configured approval-gated `release` environment, current `main` `820b8abba4308481eace728203d98f3365154956`, current `develop` `ce262d45bcb9315aa967b50e3faa06c1cebd8976`, and PR #80 conflicting because main has two release-history commits absent from develop. The existing v0.3.0 release records establish the protected ancestry-only sync mechanism. No ancestry, tag, release, environment, source, or external product state changed in this planning turn.

## Blockers

None for starting candidate validation. Promotion remains dependent on completed candidate validation; tag/publication remains dependent on completed promotion and passing exact-main CI.
