Status: open
Created: 2026-07-15
Updated: 2026-07-15
Parent: None
Depends-On: None

# Buoy v0.3.0 Release Plan

## Outcome

Release the integrated production semantic-routing work as GitHub-only Buoy v0.3.0. The user explicitly selected v0.3.0 and retained deprecated `turbo-search` / `TURBO_SEARCH_*` compatibility through 0.3, moving the announced removal target to 0.4.

## Child sequence

1. `.10x/tickets/done/2026-07-15-prepare-buoy-v0-3-0.md`
2. `.10x/tickets/2026-07-15-promote-develop-to-main-for-v0-3-0.md`
3. `.10x/tickets/2026-07-15-create-buoy-v0-3-0-github-release.md`
4. `.10x/tickets/2026-07-15-finalize-buoy-v0-3-0-changelog.md`

Children are strictly sequential. The parent is not executable.

## Aggregate acceptance criteria

- Project/module/lock/build metadata consistently report 0.3.0.
- Changelog describes the catalog, apply registration/recovery, automatic routing, and state-root/deprecation posture without claiming unsupported behavior.
- `develop` incorporates current `main` ancestry before the release merge.
- A passing release PR merges `develop` into `main` with a merge commit, never squash/rebase.
- Annotated `v0.3.0` points to the reviewed main commit and authoritative remote metadata reports a tag object.
- The approval-gated GitHub workflow publishes wheel/sdist, generated notes, and provenance successfully.
- No PyPI, branch-protection change, tag overwrite, force push, or Turbopuffer operation occurs.
- The post-release changelog finalization lands through a separately reviewed task PR after hosted release verification.
- Evidence and independent reviews support every child before closure.

## Explicit exclusions

- Removing deprecated command/environment aliases or `.turbo-search` compatibility.
- New product behavior beyond release metadata/docs necessary for 0.3.0.
- PyPI or other registry publication.
- Turbopuffer reads/writes.

## Progress and notes

- 2026-07-15: User selected v0.3.0 rather than merge-only or v0.2.2, and selected retaining deprecated command/environment aliases through 0.3 with removal target moved to 0.4.
- 2026-07-15: Current remote divergence is one main-only release merge commit and sixteen develop-only integration commits; release preparation must preserve ancestry rather than flatten it.

- 2026-07-15: Preparation child completed after local, independent, and hosted validation; PR #21 awaits integration. Promotion child is unblocked after integration.
