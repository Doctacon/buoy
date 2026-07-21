Status: done
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
2. `.10x/tickets/done/2026-07-21-promote-develop-to-main-for-v0-4-0.md`
3. `.10x/tickets/done/2026-07-21-create-buoy-v0-4-0-github-release.md`
4. `.10x/tickets/done/2026-07-21-finalize-buoy-v0-4-0-changelog.md`

Children are strictly sequential. No child may infer completion from a later child.

## Aggregate acceptance criteria

- Project, module, lock, wheel, and sdist metadata consistently identify 0.4.0.
- The changelog has a pending 0.4.0 section derived from the complete v0.3.0-to-candidate range before release.
- Candidate distributions pass `.10x/specs/buoy-release-validation.md`, including clean install, digest-verified 0.3.0 upgrade, removed launcher/environment aliases, retained compatibility, complete Python 3.11/3.13 tests, eval validation, links, inventory, and independent review.
- Current `main` ancestry is incorporated into release-ready `develop` through a protected ancestry-only sync PR with content-neutral merge commit; protection is not weakened.
- Historical PR #80 remains closed. Replacement PR #85 passed required checks and promoted the exact reviewed tree under the user's explicit squash-topology exception; exact-main CI passed and released-main ancestry is synchronized back into develop.
- Annotated `v0.4.0` points to the exact reviewed `main` commit and authoritative remote metadata reports a tag object.
- The exact approval-gated workflow publishes the wheel/sdist, generated notes, and verifiable provenance; no PyPI publication occurs.
- Changelog release date/links are finalized only after hosted Release verification, through a separate reviewed task PR.
- Evidence and independent reviews support each child; no tag overwrite, release replacement, force push, protection change, Turbopuffer operation, or user-data mutation occurs.

## Explicit exclusions

New product behavior; reopening C3/C4/C6-C9; retrying Approval A or Crow-Plus; Turbopuffer reads/writes; PyPI; replacing tags/releases; weakening branch/environment protection; direct pushes to `main` or `develop`.

## References

- `.10x/decisions/superseded/protected-development-and-github-release-governance-v2.md`
- `.10x/specs/protected-github-branches.md`
- `.10x/specs/buoy-release-validation.md`
- `.10x/specs/superseded/buoy-ci-and-github-releases.md`
- `docs/releasing.md`
- `.10x/tickets/done/2026-07-19-buoy-v0-4-compatibility-removal-plan.md`
- PR #80: `https://github.com/Doctacon/buoy-search/pull/80`

## Progress and notes

- 2026-07-21: User explicitly requested merging the current `develop` additions into `main` and releasing them. Read-only preflight found project/module/lock at 0.4.0, no v0.4.0 tag or Release, configured approval-gated `release` environment, current `main` `820b8abba4308481eace728203d98f3365154956`, current `develop` `ce262d45bcb9315aa967b50e3faa06c1cebd8976`, and PR #80 conflicting because main has two release-history commits absent from develop. The existing v0.3.0 release records establish the protected ancestry-only sync mechanism. No ancestry, tag, release, environment, source, or external product state changed in this planning turn.
- 2026-07-21: Candidate validation closed after repair of a clean-install Transformers pin defect. Protected ancestry/governance work integrated. The user promoted exact reviewed content through PR #85 and explicitly accepted its squash topology; exact-main CI passed and content-neutral post-release ancestry repair is prepared. Evidence: `.10x/evidence/2026-07-21-buoy-v0-4-0-main-promotion.md`.
- 2026-07-21: Annotated v0.4.0 and approval-gated GitHub Release completed at `https://github.com/Doctacon/buoy-search/releases/tag/v0.4.0`. Exact assets/digests/provenance passed and PyPI remains absent. Evidence: `.10x/evidence/2026-07-21-buoy-v0-4-0-github-release.md`. Changelog finalization is unblocked.
- 2026-07-21: PR #89 integrated the truthful hosted date/link finalization after independent PASS and complete validation. `.10x/tickets/done/2026-07-21-finalize-buoy-v0-4-0-changelog.md` is done. All release children and aggregate criteria are complete; no released tag, Release, or main content changed during finalization.

## Blockers

None.

## Closure mapping

- Candidate: `.10x/tickets/done/2026-07-21-validate-buoy-v0-4-0-release-candidate.md`.
- Promotion: `.10x/tickets/done/2026-07-21-promote-develop-to-main-for-v0-4-0.md`.
- Publication: `.10x/tickets/done/2026-07-21-create-buoy-v0-4-0-github-release.md`.
- Changelog: `.10x/tickets/done/2026-07-21-finalize-buoy-v0-4-0-changelog.md`.
- Aggregate release audit: `.10x/reviews/2026-07-21-buoy-v0-4-0-release-review.md`.

## Retrospective

Release publication succeeded, but its manual ceremony was disproportionate. The separately ratified simple-release plan replaces future process without altering immutable v0.4 evidence.
