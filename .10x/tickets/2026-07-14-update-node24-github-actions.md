Status: active
Created: 2026-07-14
Updated: 2026-07-19
Parent: None
Depends-On: .10x/tickets/done/2026-07-14-publish-buoy-rebrand-commit.md

# Update GitHub Actions for Native Node.js 24 Runtime

## Scope

Replace pinned `actions/checkout` and `astral-sh/setup-uv` revisions that declare the deprecated Node.js 20 action runtime with reviewed upstream revisions that natively support Node.js 24, preserving all CI/release semantics and full-SHA pinning.

## Acceptance criteria

- Upstream source/tag identity for each replacement SHA is independently verified.
- CI/release triggers, permissions, commands, matrices, artifacts, and no-PyPI boundary remain unchanged.
- Static workflow tests and full tests pass.
- Hosted CI completes without Node.js 20 action-runtime deprecation annotations.

## Explicit exclusions

Release tags/releases, dependency upgrades unrelated to action runtime, branch protection, PyPI, and live Turbopuffer operations.

## References

- CI run `29359814276`
- `.github/workflows/ci.yml`
- `.github/workflows/release.yml`

## Evidence expectations

Upstream SHA/tag lookup, workflow diff, local tests, hosted CI URL/annotations, and independent review.

## Blockers

None. Upstream release, tag, commit, and action-runtime provenance is recorded in `.10x/evidence/2026-07-19-node24-github-actions-validation.md`.

## Progress and notes

- 2026-07-19: Independently corroborated GitHub release/Git Data API results with upstream `git ls-remote`: `actions/checkout` v5.0.1 is commit `93cb6efe18208431cddfb8368fd83d5badbf9bfd`; `astral-sh/setup-uv` v7.6.0 is commit `37802adc94f370d6bfd71619e3f0bf239e1f3b78`; both commit-pinned `action.yml` files declare Node.js 24.
- 2026-07-19: Updated only the checkout/setup-uv pins and identifying major comments in CI/release workflows, plus the static workflow test's expected majors. Local Python 3.11 and 3.13 suites each passed all 422 tests; distribution build and `git diff --check` passed. Hosted CI and independent review remain required, so the ticket stays active.
