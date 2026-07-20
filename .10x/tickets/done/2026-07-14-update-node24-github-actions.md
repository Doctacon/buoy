Status: done
Created: 2026-07-14
Updated: 2026-07-20
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
- 2026-07-19: Updated only the checkout/setup-uv pins and identifying major comments in CI/release workflows, plus the static workflow test's expected majors. Local Python 3.11 and 3.13 suites each passed all 422 tests; distribution build and `git diff --check` passed.
- 2026-07-19: Opened PR [#53](https://github.com/Doctacon/buoy-search/pull/53). Hosted CI run [29713297074](https://github.com/Doctacon/buoy-search/actions/runs/29713297074) passed Python 3.11, Python 3.13, and distribution-build jobs; all three check-run annotation lists were empty. Independent review remained required, so the ticket stayed active and the PR was not merged.
- 2026-07-20: Independent review passed for PR head `7f3225b8c964ffa035ad0c8d6f6679d47094bdd1`. Exact-head CI run [29713376040](https://github.com/Doctacon/buoy-search/actions/runs/29713376040) passed all three jobs, and each exact check-run annotation endpoint returned zero annotations. Review: `.10x/reviews/2026-07-20-node24-github-actions-review.md`.

## Closure mapping

- Upstream identity: GitHub release/ref APIs and independent upstream `git ls-remote` agree that `actions/checkout` v5.0.1 is `93cb6efe18208431cddfb8368fd83d5badbf9bfd` and `astral-sh/setup-uv` v7.6.0 is `37802adc94f370d6bfd71619e3f0bf239e1f3b78`; each commit-pinned `action.yml` declares Node.js 24.
- Workflow preservation: review confirmed that triggers, permissions, commands, matrices, action inputs, artifacts, and no-PyPI behavior are unchanged; only the two action pins/comments and matching static expectations changed.
- Validation: the recorded Python 3.11 and 3.13 full suites each passed 422 tests, distribution build and diff hygiene passed, and the independent focused release-automation suite passed all 11 tests.
- Hosted behavior: exact-head PR CI run `29713376040` passed Python 3.11 (`88261229854`), Python 3.13 (`88261229820`), and Build distributions (`88261311384`); all three annotation lists were empty.
- Review and exclusions: independent review passed; no tag, release, merge, PyPI, or live Turbopuffer operation occurred.

## Retrospective

A successful hosted job does not prove deprecation warnings are absent; query every exact check-run annotation endpoint and bind the result to the reviewed head SHA. For full-SHA action upgrades, corroborating GitHub release/ref metadata with upstream `git ls-remote` and inspecting `action.yml` at the immutable commit establishes both identity and runtime without trusting a mutable major tag. The tag-only release workflow remains intentionally unexecuted because creating a release tag would violate scope; the same runtime-bearing action commits, unchanged release-specific inputs, static release tests, and successful CI execution bound that non-blocking residual.
