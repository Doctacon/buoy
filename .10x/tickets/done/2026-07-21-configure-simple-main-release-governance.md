Status: done
Created: 2026-07-21
Updated: 2026-07-21
Parent: .10x/tickets/done/2026-07-21-simple-main-release-automation-plan.md
Depends-On: .10x/tickets/done/2026-07-21-implement-simple-main-release-automation.md

# Configure Simple Main Release Governance

## Scope

After reviewed repository automation integrates to develop:

- prove exact workflow files contain no release-environment reference and GitHub has zero active/pending deployments for `release`;
- delete the unused GitHub `release` environment and verify absence;
- update `main` protection to require exactly the four GitHub-Actions contexts, `strict=false`, last-push approval false, zero fixed approvals, administrator enforcement, deletion denial, PR requirement, and retained force-push allowance;
- leave `develop` protection unchanged and verify complete API readback;
- close obsolete unmerged PR #87 without deleting its branch until recorded evidence integrates;
- record all external mutations and no-product/no-release boundaries.

## Acceptance criteria

- Repository automation's integrated commit and hosted CI are exact and reviewed before mutation.
- No active/pending release deployment exists at environment deletion.
- Environment readback returns absent after deletion.
- Main/develop protection exactly matches active specs; no required context is added to develop.
- PR #87 closes unmerged as superseded; no branch force/deletion occurs.
- No version/tag/Release/asset/provenance/PyPI/Turbopuffer/user-state mutation occurs.
- Independent review verifies hosted state before closure.

## Explicit exclusions

Workflow/source edits; version bump; main merge; triggering a release; changing force-push allowance; develop protection mutation; tag/Release/PyPI/Turbopuffer operations.

## References

- `.10x/specs/develop-to-main-release-readiness.md`
- `.10x/specs/main-push-automatic-github-release.md`
- `.10x/specs/protected-github-branches.md`
- `.10x/decisions/simple-main-release-governance.md`

## Evidence expectations

Exact before/after environment/deployment/protection/PR API state, mutation requests, integrated workflow identity, no-live boundaries, and independent review.

## Blockers

None.

## Progress and notes

- 2026-07-21: PR #89 integrated reviewed automation as develop `7fa4bd726d09a671b76d408e7383e9fbc58c41de`; push CI `29864439022` passed and integrated workflows contain zero environment references.
- 2026-07-21: GitHub classified completed v0.4 deployment `5542522847` as active while its latest state was `success`. After exact release/run revalidation, authorization was narrowed to posting `inactive` only to that deployment; no other deployment or release state changed.
- 2026-07-21: Deleted environment `release`; installed the exact four app-bound main readiness checks with strict=false; disabled last-push approval; retained existing main force-push allowance/admin/deletion settings; proved develop protection unchanged; closed PR #87 unmerged without branch deletion. API readback passed. Evidence: `.10x/evidence/2026-07-21-simple-main-release-governance-configuration.md`.
- 2026-07-21: An initial review-policy PATCH failed with HTTP 422 because user-owned repositories do not support dismissal restrictions; it made no policy change. Retrying only supported exact fields succeeded.
- 2026-07-21: Independent read-only review passed all hosted state and non-mutation checks. Its sole record-path finding was repaired mechanically and rechecked. Review: `.10x/reviews/2026-07-21-simple-main-release-governance-configuration-review.md`.

## Closure mapping

- Preconditions and exact mutations/readback: `.10x/evidence/2026-07-21-simple-main-release-governance-configuration.md`.
- Independent hosted verification: `.10x/reviews/2026-07-21-simple-main-release-governance-configuration-review.md`.
- Repository automation authority: `.10x/tickets/done/2026-07-21-implement-simple-main-release-automation.md`.

## Retrospective

GitHub deployment `success` remains active until explicitly retired, and user-owned repositories reject organization-only dismissal restrictions. Future environment retirement should account for both mechanics.
