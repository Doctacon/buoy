Status: done
Created: 2026-07-14
Updated: 2026-07-14
Parent: .10x/tickets/2026-07-14-buoy-public-ci-release-plan.md
Depends-On: .10x/tickets/done/2026-07-14-repair-release-workflow-and-bump-v0-2-1.md

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
- `.10x/tickets/done/2026-07-14-repair-release-workflow-and-bump-v0-2-1.md`

## Progress and notes

- 2026-07-14: Preflight passed at reviewed main `0afde6643162fdedc00810152e226701aa1d38b1` with CI success, preserved v0.2.0/no Release, configured approval gate, no v0.2.1 conflict, no PyPI, and no branch protection.
- 2026-07-14: Created/pushed annotated v0.2.1; remote object type was `tag`. Release run `29362749172` passed validation/build, was observed waiting on the `release` environment, proceeded only after approval, and completed successfully. GitHub Release contains verified wheel/sdist digests and provenance attestations. Evidence: `.10x/evidence/2026-07-14-buoy-v0-2-1-github-release.md`.
- 2026-07-14: Independent review passed. Review: `.10x/reviews/2026-07-14-buoy-v0-2-1-github-release-review.md`.

## Blockers

- None.
