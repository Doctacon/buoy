Status: done
Created: 2026-07-14
Updated: 2026-07-14
Parent: .10x/tickets/done/2026-07-14-buoy-rebrand-plan.md
Depends-On: None

# Rename Core Package and CLI to Buoy

## Scope

Implement `.10x/specs/buoy-package-and-cli-identity.md`: Apache-2.0/0.2.0 project metadata, `src/buoy_search`, `buoy` primary CLI/module identity, bounded legacy console entry point, user agents, internal imports/tests/mocks, lockfile, and bundled data paths required for a working renamed package.

## Acceptance criteria

- Every behavior and scenario in the governing package/CLI spec is implemented.
- No blind rewrite changes deterministic row IDs, namespace algorithms, plan/apply IDs, or historical `.10x` prose.
- Tests and package configuration use `buoy_search`; no old implementation package remains in build inputs.
- `buoy` and the legacy console entry point have focused tests including deprecation stderr and JSON stdout separation.
- `uv sync`, focused tests, complete tests, and package metadata/build smoke checks pass.

## Explicit exclusions

State-root/env fallback implementation, README/logo/migration docs, GitHub mutation, PyPI publication, live Turbopuffer work, and float16 inference.

## References

- `.10x/decisions/buoy-product-identity-and-compatibility.md`
- `.10x/specs/buoy-package-and-cli-identity.md`
- `.10x/tickets/done/2026-07-14-buoy-rebrand-plan.md`

## Evidence expectations

Rename inventory, diff review against semantic identifiers, focused/full tests, CLI stdout/stderr tests, build metadata inspection, and independent review.

## Progress and notes

- 2026-07-14: Assigned to a single worker after plan execution authorization.
- 2026-07-14: Independent review found one semantic-identity blocker: the existing applied live autoresearch namespace was mechanically rebranded. Repair must restore `github-doctacon-turbo-search-v1` and protect it with a regression.
- 2026-07-14: Implemented `buoy-search` 0.2.0 / `buoy_search` / `buoy`, Apache-2.0 licensing, dedicated 0.2 legacy console entry point, user-agent/runner/self-search identity updates, lockfile refresh, and package rename across source/tests. Focused 72 tests and full 208 tests pass; built artifacts and isolated install verify package contents, primary/module commands, legacy stderr with clean stdout, and no old Python package. Evidence: `.10x/evidence/2026-07-14-buoy-core-package-rename.md`.
- 2026-07-14: Repaired the review blocker by restoring the established `github-doctacon-turbo-search-v1` live experiment namespace, correcting coupled wording, and adding a preservation regression. Focused 73 tests and full 209 tests pass; build/lock/diff checks pass.
- 2026-07-14: Final independent review passed. Evidence: `.10x/evidence/2026-07-14-buoy-core-package-rename.md`; review: `.10x/reviews/2026-07-14-buoy-core-package-rename-review.md`.

## Blockers

- None.
