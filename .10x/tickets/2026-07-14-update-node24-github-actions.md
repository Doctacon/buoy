Status: open
Created: 2026-07-14
Updated: 2026-07-14
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

- Requires identifying released upstream Node.js 24-compatible action versions; do not guess or weaken full-SHA pinning.
