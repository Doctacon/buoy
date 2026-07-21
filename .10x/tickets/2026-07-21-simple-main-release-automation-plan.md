Status: open
Created: 2026-07-21
Updated: 2026-07-21
Parent: None
Depends-On: .10x/tickets/done/2026-07-21-shape-simple-main-release-automation.md

# Simple Main Release Automation Plan

## Outcome

Replace release ceremony with required prospective-merge readiness checks and serialized fully automatic main-push GitHub releases, then align hosted main protection and remove the unused release environment.

This parent is non-executable.

## Child sequence

1. `.10x/tickets/2026-07-21-implement-simple-main-release-automation.md`
2. `.10x/tickets/2026-07-21-configure-simple-main-release-governance.md`

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

- 2026-07-21: Repository implementation and local validation are complete on `work/implement-simple-release`, including the exact approved v0.4.0 provenance transition. Evidence: `.10x/evidence/2026-07-21-simple-main-release-automation-implementation.md`. Hosted CI and independent review remain before the implementation child can close; hosted configuration remains sequenced after reviewed integration.

## Blockers

None for repository implementation. Hosted configuration remains blocked on integrated reviewed repository automation.
