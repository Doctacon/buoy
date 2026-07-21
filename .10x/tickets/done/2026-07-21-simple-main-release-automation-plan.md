Status: done
Created: 2026-07-21
Updated: 2026-07-21
Parent: None
Depends-On: .10x/tickets/done/2026-07-21-shape-simple-main-release-automation.md

# Simple Main Release Automation Plan

## Outcome

Replace release ceremony with required prospective-merge readiness checks and serialized fully automatic main-push GitHub releases, then align hosted main protection and remove the unused release environment.

This parent is non-executable.

## Child sequence

1. `.10x/tickets/done/2026-07-21-implement-simple-main-release-automation.md`
2. `.10x/tickets/done/2026-07-21-configure-simple-main-release-governance.md`

The configuration child depends on reviewed integration of repository automation. The first real passing release-readiness run remains deferred to a future explicitly version-bumped release PR; no next version is invented here.

## Aggregate acceptance criteria

- Repository workflows/scripts/tests/docs implement both active focused specs exactly.
- Current v0.4 changelog and temporal records are truthfully finalized without changing the released tag/Release.
- Old active ceremony authorities are superseded; historical evidence remains.
- Main protection requires exact four non-strict readiness contexts with last-push approval off; develop protection remains unchanged.
- The unused release environment and obsolete unmerged PR #87 are removed/closed only after proof.
- No version bump, main merge, automatic release invocation, PyPI, Turbopuffer, tag/Release overwrite, force push, or user-state mutation occurs.
- Each child has evidence, exact-head CI, independent review, and coherent closure.

## References

- `.10x/decisions/simple-main-release-governance.md`
- `.10x/specs/develop-to-main-release-readiness.md`
- `.10x/specs/main-push-automatic-github-release.md`
- `.10x/evidence/2026-07-21-simple-main-release-automation-ratification.md`

## Progress and notes

- 2026-07-21: Repository implementation passed independent final review, integrated through PR #89 as `7fa4bd726d09a671b76d408e7383e9fbc58c41de`, and passed develop push CI `29864439022`. Evidence: `.10x/evidence/2026-07-21-simple-main-release-automation-implementation.md`; review: `.10x/reviews/2026-07-21-simple-main-release-automation-final-review.md`.
- 2026-07-21: Hosted configuration completed with exact main readback, unchanged develop protection, retired completed deployment, deleted release environment, and PR #87 closed unmerged. Evidence: `.10x/evidence/2026-07-21-simple-main-release-governance-configuration.md`.
- 2026-07-21: Independent hosted-state review passed after one stale record path was mechanically repaired. All children and aggregate criteria are complete. Review: `.10x/reviews/2026-07-21-simple-main-release-governance-configuration-review.md`.

## Blockers

None.

## Closure mapping

- Repository implementation: `.10x/tickets/done/2026-07-21-implement-simple-main-release-automation.md`.
- Hosted configuration: `.10x/tickets/done/2026-07-21-configure-simple-main-release-governance.md`.
- Implementation review: `.10x/reviews/2026-07-21-simple-main-release-automation-final-review.md`.
- Hosted review: `.10x/reviews/2026-07-21-simple-main-release-governance-configuration-review.md`.

## Retrospective

The release process is now reduced to explicit version/changelog preparation on develop, four merge-readiness checks, and automatic main-push publication. The first real release remains intentionally deferred until an explicit future version bump.
