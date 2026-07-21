Status: done
Created: 2026-07-21
Updated: 2026-07-21
Parent: .10x/tickets/2026-07-21-buoy-v0-4-0-release-plan.md
Depends-On: None

# Validate Buoy v0.4.0 Release Candidate

## Scope

- Reconcile the complete `v0.3.0..develop` release range into an accurate pending 0.4.0 changelog section without claiming blocked experiments or failed live baselines as shipped successes.
- Validate exact project/module/lock/distribution version 0.4.0 and all requirements in `.10x/specs/buoy-release-validation.md`.
- Build once in a clean temporary output, inspect wheel/sdist contents and entry points, test clean install, and test digest-verified same-environment upgrade from released 0.3.0.
- Run primary CLI checks, retained local-state/plan compatibility checks, fixture autoresearch and repository-search eval validation, local links, distribution inventory, diff hygiene, and complete Python 3.11/3.13 suites.
- Preserve all external-state boundaries and obtain independent review before closure.

## Acceptance criteria

- Pending changelog content is complete, truthful, and versioned 0.4.0 without release date/compare link.
- Every required validation in the active release-validation specification passes with reproducible evidence.
- Built artifacts contain no `.10x/**`, old console entry point, package-owned `turbo-search` launcher, or `legacy_main`; required package/data/CLI surfaces work.
- Upgrade validation verifies the immutable 0.3.0 digest and package-manager removal of only its obsolete package-owned launcher.
- No tag, Release, PyPI publication, branch merge, Turbopuffer operation, user-state mutation, or external cleanup occurs.
- Independent review passes and exact-head hosted checks pass before the child closes.

## Explicit exclusions

Main/develop ancestry changes; PR #80 merge; tag/Release creation; publication; new product behavior; live retrieval/apply/evals; user-owned launcher or state deletion.

## References

- `.10x/specs/buoy-release-validation.md`
- `.10x/specs/buoy-ci-and-github-releases.md`
- `docs/releasing.md`
- `CHANGELOG.md`
- `.10x/evidence/2026-07-21-buoy-v0-4-0-release-candidate.md`
- `.10x/reviews/2026-07-21-buoy-v0-4-0-release-candidate-review.md`
- `.10x/reviews/2026-07-21-buoy-v0-4-0-release-candidate-final-review.md`

## Evidence expectations

Exact source commit; changelog range method; command matrix and exits; Python 3.11/3.13 results; artifact names/digests/inventory/metadata; clean-install and 0.3.0-upgrade observations; compatibility/eval/link results; side-effect limits; hosted checks; independent review.

## Blockers

None. The initial artifact-resolution blocker was repaired and independent final review passed exact head `278400909596b5644431bd03fe526e600153f152`.

## Progress and notes

- 2026-07-21: Opened from the user's explicit v0.4.0 release request. Read-only preflight found version metadata already at 0.4.0 and the changelog still under Unreleased. No validation workflow, artifact build, source edit, tag, release, merge, or external product operation occurred.
- 2026-07-21: Prepared the pending 0.4.0 changelog from the complete post-0.3.0 range and added focused release-note assertions. Separate locked CPython 3.11.5 and 3.13.0 suites passed 518 tests each; ranking/C6 validators, lock/diff checks, clean build/inventory, tag/assets dry checks, clean install, and digest-verified released-0.3.0 same-environment upgrade passed. Evidence: `.10x/evidence/2026-07-21-buoy-v0-4-0-release-candidate.md`. No tag, Release, branch ancestry, PyPI, Turbopuffer, live product, or user-state operation occurred.
- 2026-07-21: Independent review failed initial head `ac1c51be2c251ff2f4d0ff2114094e6d1b455c72`: normal artifact installation resolved Transformers 5.14.1, so the exact bundled tokenizer could not load despite locked-source CI passing. Review: `.10x/reviews/2026-07-21-buoy-v0-4-0-release-candidate-review.md`. Repaired distributable metadata with exact `transformers==5.12.1`, refreshed `uv.lock`, added static metadata coverage, rebuilt artifacts, and reran complete 518-test suites/validators on Python 3.11/3.13. Clean and 0.3-upgraded normal artifact environments now resolve 5.12.1 and actually load/exercise the exact bundled tokenizer. Evidence was corrected with final digests. No tag, Release, ancestry, PyPI, Turbopuffer, or user-state operation occurred.
- 2026-07-21: Independent final review passed exact head `278400909596b5644431bd03fe526e600153f152`; review: `.10x/reviews/2026-07-21-buoy-v0-4-0-release-candidate-final-review.md`. Exact-head hosted Python 3.11, Python 3.13, and distribution checks passed. Candidate validation is complete and eligible for separate integration; no promotion or publication authority is implied.

## Closure mapping

- Version/changelog: `CHANGELOG.md`, project/module/lock metadata, and release automation tests.
- Complete source validation and candidate artifacts: `.10x/evidence/2026-07-21-buoy-v0-4-0-release-candidate.md`.
- Initial defect and repaired final acceptance: `.10x/reviews/2026-07-21-buoy-v0-4-0-release-candidate-review.md` and `.10x/reviews/2026-07-21-buoy-v0-4-0-release-candidate-final-review.md`.
- External boundary: no main/develop promotion, tag, Release, PyPI, Turbopuffer, or user-state mutation occurred.

## Retrospective

Locked-source CI does not prove distributable dependency resolution. Release validation must install the built wheel normally and exercise runtime features whose loaders enforce exact dependency versions.
