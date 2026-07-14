Status: done
Created: 2026-07-14
Updated: 2026-07-14
Parent: .10x/tickets/done/2026-07-14-buoy-rebrand-plan.md
Depends-On: .10x/tickets/done/2026-07-14-buoy-release-integration-validation.md

# Rename GitHub Repository to buoy-search

## Scope

After code-level integration passes, rename the external repository exactly from `Doctacon/turbo-search` to `Doctacon/buoy-search`, confirm redirect/remote behavior, update the local `origin`, and repair current canonical repository links that cannot be updated before the external action.

The user's current-workstream authorization covers this exact repository rename. If the target is unavailable, authentication is unavailable, or the source repository identity differs, stop and mark this ticket blocked; do not choose another name or owner.

## Acceptance criteria

- Preflight confirms current authenticated repository is `Doctacon/turbo-search` and target `Doctacon/buoy-search` is available.
- Rename occurs only after the release-integration ticket is done.
- The repository is reachable at the new canonical URL and the old GitHub URL redirects as observed.
- Local `origin` fetch/push URLs use the new canonical repository.
- Current docs/package metadata use the canonical URL; historical records remain unchanged.
- No release, package publication, branch deletion, issue mutation, or Turbopuffer operation occurs.
- Durable evidence records exact before/after repository and remote observations without credentials.

## Explicit exclusions

PyPI publication, GitHub release creation, domain/social-handle changes, organization transfer, branch/tag mutation, and package deletion.

## References

- `.10x/decisions/buoy-product-identity-and-compatibility.md`
- `.10x/tickets/done/2026-07-14-buoy-release-integration-validation.md`

## Evidence expectations

Read-only preflight, exact rename command/API result, canonical/redirect checks, `git remote -v`, link scan, and independent review.

## Progress and notes

- 2026-07-14: Release integration dependency closed; exact external rename assigned after authorization.
- 2026-07-14: Preflight confirmed authenticated source `Doctacon/turbo-search` and available `Doctacon/buoy-search`; exact rename completed. New endpoint returns 200, old endpoint redirects 301 to the new canonical URL, both local origin URLs use `Doctacon/buoy-search`, canonical package URLs and repository description were updated, and a fresh wheel exposes the new project URLs. Evidence: `.10x/evidence/2026-07-14-buoy-github-repository-rename.md`.

- 2026-07-14: Independent read-only review passed. Review: `.10x/reviews/2026-07-14-buoy-github-repository-rename-review.md`.

## Blockers

- None.
