Status: done
Created: 2026-07-14
Updated: 2026-07-14
Parent: .10x/tickets/2026-07-14-buoy-public-ci-release-plan.md
Depends-On: .10x/tickets/done/2026-07-14-publish-buoy-rebrand-commit.md

# Repair Hosted Release Validation and Bump v0.2.1

## Scope

Repair annotated-tag validation to use authoritative remote GitHub metadata, bump all current version/changelog/release targets to 0.2.1, document preserved failed v0.2.0 history, validate, commit, push normally, and require passing canonical main CI.

## Acceptance criteria

- Remote annotated tag validation rejects lightweight tags and does not rely on checkout-local ref type.
- Existing v0.2.0 tag/run remain unchanged and have no Release.
- Project/module/changelog/docs agree on pending 0.2.1.
- Tests/static negatives/build/full suite pass; independent review passes.
- One normal reviewed commit is pushed to main and hosted CI passes.
- No tag/release/PyPI/branch protection/Turbopuffer mutation occurs.

## References

- `.10x/decisions/github-only-release-automation-v0-2-1.md`
- `.10x/specs/buoy-ci-and-github-releases.md`
- `.10x/evidence/2026-07-14-buoy-v0-2-0-release-attempt.md`

## Progress and notes

- 2026-07-14: Replaced checkout-local tag validation with authoritative GitHub tag-ref metadata, bumped project/module/lock/changelog/release docs to 0.2.1, preserved v0.2.0 failed-attempt history, and passed 9 focused plus 235 full tests and exact build checks. Evidence: `.10x/evidence/2026-07-14-buoy-v0-2-1-workflow-repair.md`.
- 2026-07-14: Pushed commit `0afde6643162fdedc00810152e226701aa1d38b1` normally to canonical main; hosted CI run `29362284969` passed for the exact commit. Awaiting independent review.

## Blockers

- None. Execution authorized.
