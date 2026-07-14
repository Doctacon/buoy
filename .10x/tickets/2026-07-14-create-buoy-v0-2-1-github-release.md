Status: open
Created: 2026-07-14
Updated: 2026-07-14
Parent: .10x/tickets/2026-07-14-buoy-public-ci-release-plan.md
Depends-On: .10x/tickets/2026-07-14-repair-release-workflow-and-bump-v0-2-1.md

# Create the Buoy v0.2.1 GitHub Release

## Scope

After repaired main CI passes, preflight preserved v0.2.0 history and absent v0.2.1 conflicts, create/push annotated v0.2.1 at reviewed main, observe authoritative tag validation and release-environment pause, approve, and verify the GitHub-only Release, wheel/sdist, notes, and provenance.

## Acceptance criteria

- v0.2.0 tag/run remain unchanged with no Release.
- Canonical main/version/CI and release environment pass preflight; no PyPI project exists.
- Annotated v0.2.1 points to reviewed main and remote metadata reports object type `tag`.
- Approval gate is observed before release mutation.
- GitHub Release assets and provenance verify; workflow is terminal-success.
- No PyPI, branch protection, force/moved tag, source change, or Turbopuffer operation occurs.
- Durable evidence and independent review pass.

## References

- `.10x/decisions/github-only-release-automation-v0-2-1.md`
- `.10x/specs/buoy-ci-and-github-releases.md`
- `.10x/tickets/2026-07-14-repair-release-workflow-and-bump-v0-2-1.md`

## Blockers

- Depends on repaired workflow/version commit and passing main CI.
