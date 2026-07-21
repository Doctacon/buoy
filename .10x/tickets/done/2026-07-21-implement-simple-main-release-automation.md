Status: done
Created: 2026-07-21
Updated: 2026-07-21
Parent: .10x/tickets/done/2026-07-21-simple-main-release-automation-plan.md
Depends-On: None

# Implement Simple Main Release Automation

## Scope

- Add `.github/workflows/release-readiness.yml` with the exact four check names and prospective-merge behavior.
- Replace `.github/workflows/release.yml` with serialized main-push automatic validation/build/state-machine/tag/attestation/Release behavior.
- Implement repository-local standard-Python/shell version, changelog, deterministic artifact, GitHub-state, collision, and dry-run helpers rather than burying logic in YAML.
- Add exhaustive deterministic tests for every active-spec branch, permissions/trigger/action pins, forbidden operations, and v0.4 transition.
- Update `docs/releasing.md` to the simple version-bump/develop-PR flow and self-hosted migration mapping.
- Finalize the already-published v0.4.0 changelog date/links from recorded hosted authority; close its finalization and aggregate release records truthfully.
- Supersede/remove active manual-tag/environment/ancestry ceremony while preserving historical evidence.

## Acceptance criteria

- Every criterion in both active simple-release specs has source/tests.
- Existing complete Python 3.11/3.13 suites, validators, workflow static checks, dry state-machine tests, deterministic two-build digest comparison, normal clean-wheel tokenizer smoke, and distribution inspection pass.
- Workflow write permissions exist only on the final publication job, which installs no dependency and executes no repository code.
- No workflow references `environment: release`, tag triggers, manual dispatch, PyPI, Turbopuffer, overwrite/delete/move/force-push operations, or ancestry sync.
- Existing v0.4.0 exact complete state dry-runs as no-op only at its exact released SHA; a different SHA with 0.4.0 fails.
- Exact-head hosted CI and independent review pass before squash integration to develop.

## Explicit exclusions

Hosted protection/environment/PR mutation; choosing or bumping a future version; main merge; live workflow release; tag/Release mutation; PyPI; Turbopuffer; product changes.

## References

- `.10x/specs/develop-to-main-release-readiness.md`
- `.10x/specs/main-push-automatic-github-release.md`
- `.10x/decisions/simple-main-release-governance.md`
- `.10x/evidence/2026-07-21-simple-main-release-automation-ratification.md`
- `.10x/tickets/done/2026-07-21-finalize-buoy-v0-4-0-changelog.md`
- `.10x/tickets/done/2026-07-21-buoy-v0-4-0-release-plan.md`
- `.10x/reviews/2026-07-21-simple-main-release-automation-final-review.md`

## Evidence expectations

Changed paths; exact workflow/check/state mechanics; deterministic artifacts; tests/validators/clean install; docs/migration; no-live attestation; hosted checks; independent review.

## Blockers

None.

## Progress and notes

- 2026-07-21: Implemented the prospective-main release-readiness workflow, serialized main-push state machine, standard-Python policy/artifact/GitHub-state helpers, fail-closed publication adapter, deterministic build/smoke checks, simple-flow and self-hosted migration documentation, and v0.4.0 changelog finalization. No live configuration, environment, tag, Release, main, registry, or Turbopuffer state was accessed or mutated.
- 2026-07-21: Applied the approved sole legacy no-op provenance exception for exact published v0.4.0. The exception pins tag, peeled commit, both subject names/digests, Release identity, repository, workflow, source commit, and historical `refs/tags/v0.4.0`; all future versions require `refs/heads/main`.
- 2026-07-21: Focused release automation tests passed (24 tests). Final complete locked Python 3.11 and 3.13 validators and suites passed (531 tests on each interpreter). Two deterministic builds produced identical wheel/sdist digests, artifact inspection passed, and a normal clean-wheel install passed CLI/help and exact bundled-tokenizer smoke. Static YAML/state/forbidden-operation, lock, diff, and current-develop ref checks passed. Evidence: `.10x/evidence/2026-07-21-simple-main-release-automation-implementation.md`.
- 2026-07-21: Pushed implementation commit `af7841a` and opened develop PR #89. Exact implementation-head CI run `29860668978` passed Python 3.11, Python 3.13, and Build distributions. The following evidence-only commit must pass the same checks; independent review remains before closure.
- 2026-07-21: Repaired only PR #89's four review blockers: strict no-leading-zero SemVer and real calendar dates; exact complete-only full 422 reinspection; unconditional downloaded-asset digest/provenance final verification; and bounded repository-wide release-behavior Policy enforcement. Executable workflow-shell fixtures cover exact and partial 422 states plus both final-verification entries. Focused 27-test and full locked 534-test suites on Python 3.11/3.13, validators, two-build determinism, artifact inspection, clean-wheel smoke, policy scan, YAML parse, compilation, and diff checks passed.
- 2026-07-21: Independent final rereview passed exact head `a8c86cd46bc2d0d6a5ca81497fa5f5f843eebe48`; review: `.10x/reviews/2026-07-21-simple-main-release-automation-final-review.md`. PR #89 squash-integrated as develop `7fa4bd726d09a671b76d408e7383e9fbc58c41de`; develop push CI `29864439022` passed. Repository implementation is complete.

## Closure mapping

- Workflow/tooling/docs/tests and local validation: `.10x/evidence/2026-07-21-simple-main-release-automation-implementation.md`.
- Initial concerns and exact repaired PASS: `.10x/reviews/2026-07-21-simple-main-release-automation-implementation-review.md` and `.10x/reviews/2026-07-21-simple-main-release-automation-final-review.md`.
- Integration: PR #89 / `7fa4bd726d09a671b76d408e7383e9fbc58c41de` with passing push CI.

## Retrospective

Release state machines require executable race fixtures and artifact-level verification; static YAML assertions alone do not prove mutation suppression.
