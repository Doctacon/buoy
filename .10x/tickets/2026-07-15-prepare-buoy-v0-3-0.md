Status: open
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

- `.10x/specs/buoy-ci-and-github-releases.md`
- `.10x/specs/protected-github-branches.md`
- `docs/releasing.md`

## Evidence expectations

Exact version diffs, validation/build commands, artifact inventory, CI run/check URLs, compatibility checks, and independent review.

## Blockers

None.

## Progress and notes
