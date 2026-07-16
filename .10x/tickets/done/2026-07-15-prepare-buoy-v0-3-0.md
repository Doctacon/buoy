Status: done
Created: 2026-07-15
Updated: 2026-07-15
Parent: .10x/tickets/2026-07-15-buoy-v0-3-0-release-plan.md
Depends-On: None

# Prepare Buoy v0.3.0

## Scope

- Bump `pyproject.toml`, `src/buoy_search/__init__.py`, and lock metadata to 0.3.0.
- Move current release changes from Unreleased into a pending 0.3.0 changelog section covering production catalog, apply registration/recovery, opt-in auto-routing, and migration to the `.buoy` default.
- Update release documentation/examples to v0.3.0 where they describe the next release procedure.
- Retain deprecated `turbo-search` and `TURBO_SEARCH_*` aliases through 0.3 and update their announced removal target to 0.4; do not alter compatibility implementation.
- Run full CI-equivalent tests, build, tag/version dry checks, artifact inspection, docs/reference checks, and independent review.
- Land through a passing `work/* -> develop` pull request using squash merge.

## Acceptance criteria

- All authoritative version fields and built artifact names/metadata are exactly 0.3.0.
- Changelog is accurate, pending until hosted release verification, and retains valid compare links.
- Deprecated aliases still work and documentation consistently targets removal in 0.4.
- Python 3.11, Python 3.13, Build distributions, full local tests, and release dry checks pass.
- No tag, GitHub Release, main mutation, PyPI, or Turbopuffer operation occurs.

## Explicit exclusions

Alias removal, state-root compatibility removal, release tag creation, main promotion, unrelated cleanup.

## References

- `.10x/decisions/buoy-product-identity-and-compatibility-v0-3.md`
- `.10x/specs/buoy-package-and-cli-identity.md`
- `.10x/specs/buoy-local-compatibility.md`
- `.10x/specs/buoy-ci-and-github-releases.md`
- `.10x/specs/protected-github-branches.md`
- `docs/releasing.md`

## Evidence expectations

Exact version diffs, validation/build commands, artifact inventory, CI run/check URLs, compatibility checks, and independent review.

## Blockers

None.

## Progress and notes

- 2026-07-15: Marked active. Bumped project/module/lock metadata to 0.3.0; prepared the pending changelog; aligned release/migration docs, active identity/compatibility specs, warnings, and tests with retained aliases through 0.3 and removal target 0.4.
- 2026-07-15: Local preparation validation passed: 364 tests on Python 3.11 and 364 on Python 3.13, 48 focused release/CLI tests, exact tag/assets dry checks, lock/compile/reference/diff checks, two-artifact build and metadata/content inspection, and isolated wheel/legacy-alias checks. Evidence: `.10x/evidence/2026-07-15-buoy-v0-3-0-preparation.md`; artifact inventory: `.10x/evidence/.storage/2026-07-15-buoy-v0-3-0-preparation-artifacts.json`.
- 2026-07-15: Applied review corrections: aligned the migration guide's legacy-environment section, configuration docstring, and active precision spec on compatibility through 0.3/removal in 0.4; strengthened section-specific regression assertions; and completed pending notes from exact `v0.2.1..HEAD` product history for float16, single-pass planning, depth-one apply, namespace discovery, explicit multi-namespace retrieval, and apply/retrieval handoff. Revalidated 57 focused tests, 364 tests on each Python runtime, final artifacts, isolated install, tag/assets, lock, compile, reference, and diff checks. Ticket remains active for independent re-review and hosted PR checks.

- 2026-07-15: PR #21 hosted checks passed: Python 3.11, Python 3.13, and Build distributions. Independent preparation review passed after corrections: `.10x/reviews/2026-07-15-buoy-v0-3-0-preparation-review.md`.

## Closure mapping

- Version/module/lock/build metadata: exact 0.3.0.
- Pending changelog/docs: complete and source-backed; hosted date/link deliberately deferred.
- Compatibility: command/environment aliases retained through 0.3 with precise 0.4 warnings/tests.
- Validation: 364 tests on both supported Pythons, 57 focused tests, build/tag/assets/install/reference/diff checks, and all required hosted checks.
- Exclusions: no main/tag/Release/PyPI/Turbopuffer mutation.

## Retrospective

A release changelog must be derived from the full prior-tag range, not only the latest feature work. Compatibility schedule changes require section-specific tests; file-wide phrase checks can pass while authoritative text remains stale.
