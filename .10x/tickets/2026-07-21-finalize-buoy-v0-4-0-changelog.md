Status: open
Created: 2026-07-21
Updated: 2026-07-21
Parent: .10x/tickets/2026-07-21-buoy-v0-4-0-release-plan.md
Depends-On: .10x/tickets/done/2026-07-21-create-buoy-v0-4-0-github-release.md

# Finalize Buoy v0.4.0 Changelog

## Scope

After the GitHub Release is verified, update the pending 0.4.0 changelog section with the authoritative hosted release date and links, restore an empty Unreleased section, validate links/version history, and integrate through a separate reviewed task PR to `develop`.

## Acceptance criteria

- Changelog date and release/compare links match the observed GitHub Release and tag.
- Unreleased compares from v0.4.0 to HEAD; 0.4.0 links to the immutable Release.
- No release claims precede hosted verification.
- Focused/full required checks and independent review pass before squash integration to develop.
- No tag, Release, artifact, branch protection, PyPI, or Turbopuffer mutation occurs.

## Explicit exclusions

Changing released main/tag contents; amending/replacing the Release; new product behavior; PyPI; Turbopuffer.

## References

- `CHANGELOG.md`
- `docs/releasing.md`
- `.10x/tickets/done/2026-07-15-finalize-buoy-v0-3-0-changelog.md`

## Evidence expectations

Authoritative hosted date/URL/tag observations, exact changelog diff, link/version checks, hosted CI, independent review, and integration identity.

## Blockers

None. Verified v0.4.0 GitHub Release publication is complete.

## Progress and notes

- 2026-07-21: Opened prospectively. No changelog finalization or release mutation occurred.
- 2026-07-21: Source finalization is included in the simple-release implementation worktree: hosted date `2026-07-21`, v0.4.0 Release link, and Unreleased compare link match `.10x/evidence/2026-07-21-buoy-v0-4-0-github-release.md`. Focused checks, complete Python 3.11/3.13 suites, links, deterministic artifacts, and diff checks passed without live release mutation. Implementation evidence: `.10x/evidence/2026-07-21-simple-main-release-automation-implementation.md`. Ticket remains open until PR review/integration evidence satisfies its explicit review gate.
