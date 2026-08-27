Status: done
Created: 2026-08-27
Updated: 2026-08-27
Parent: None
Depends-On: .10x/tickets/done/2026-08-27-decouple-evidence-from-source-layout-plan.md

# Reorganize the test suite by concern

## Cold-start context

After the production package was reorganized into concern subpackages, `tests/` still contains 62 Python files directly at its root, including modules over 3,000 lines and cross-test imports between flat modules. The user requested a similar organization pass and selected folders-only scope: move modules intact without splitting them.

Governing contract: `.10x/specs/buoy-test-suite-layout.md`.

Pre-move observed baseline: full pytest `1191 passed, 57 warnings, 1292 subtests passed`; dual-runtime standard-library discovery reports 1,191 tests.

## Scope

- Create the exact concern packages in the governing specification.
- Move every root test/support/benchmark module according to the exact mapping.
- Update cross-test imports and active workflow/script/documentation references.
- Preserve recursive pytest and unittest discovery on Python 3.11 and 3.13.
- Add narrowly targeted structural/discovery checks only when needed to prevent regression.
- Repair durable pointers to moved active files while preserving explicitly historical prose.

## Explicit exclusions

- Splitting, merging, renaming, or behaviorally refactoring test modules.
- Extracting helpers from test modules.
- Assertion, fixture-value, test-name, test-count, or coverage changes beyond mechanically required path/discovery and approved v3 identity updates.
- Production behavior changes or unrelated cleanup.
- Compatibility forwarding modules at old test paths.

## Acceptance criteria

1. Test layout exactly matches `.10x/specs/buoy-test-suite-layout.md`.
2. No test implementation or benchmark remains directly under `tests/`.
3. No active executable reference uses an old root test-module path.
4. Cross-test imports and helper consumers resolve from their new locations.
5. Pytest retains exactly 1,191 tests and 1,292 subtests.
6. Standard-library discovery retains exactly 1,191 tests on Python 3.11 and 3.13.
7. Existing validators, workflow tests, CLI/import checks, wheel/sdist, and isolated-install checks pass.
8. Semantic diff audit proves only relocation-required imports/path references changed inside moved modules.
9. No compatibility shims, unrelated formatting, assertion changes, or staged files exist.
10. Independent review passes with no unresolved significant findings.

## Evidence expectations

- Before/after tree and exact mapping audit.
- Old-root file and stale-import search.
- Semantic module-diff audit excluding approved relocation lines.
- Pytest and Python 3.11/3.13 unittest outputs with counts.
- Validator, workflow, package, and isolated-install outputs.
- No-staged-files and diff-hygiene results.
- Independent review, residual risks, and closure mapping.

## Blockers

None.

## Progress and notes

- 2026-08-27: Inspected the complete test tree, file sizes, cross-test imports, active path-sensitive references, package configuration, CI discovery, and related records. No existing active test-layout owner was found.
- 2026-08-27: User selected folders-only reorganization. Opened this executable ticket after activating the focused layout specification. No implementation occurred in this specification/ticket-authoring turn.
- 2026-08-27: Execution found five moved test paths referenced by immutable active repo-eval v2 and stopped before eval mutation. Owner approved a path-only v3 successor preserving v2 and all judgment semantics; authority is `.10x/decisions/buoy-advances-repo-eval-for-test-layout.md`.
- 2026-08-27: Moved all 62 modules into the exact eleven concern packages, added empty package initializers, updated cross-test imports and relocation-dependent root/fixture paths, and retained no flat shims. Pytest collection remained exactly 1,191 tests.
- 2026-08-27: Preserved exact v2 bytes and activated path-only v3 with exactly five approved mappings, unchanged judgment semantics, pending baseline, and promotion disabled. Updated active experiment/docs pointers and strict validator coverage; production promotion registry remains empty.
- 2026-08-27: Full pytest passed `1191 tests, 1292 subtests`; Python 3.11 and 3.13 unittest discovery each passed 1,191 tests. Ranking/promotion/C6/workflow/compile validators, exact layout/stale-import audits, 93-entry wheel/189-entry sdist, isolated Python 3.13 install/CLI/v2-v3 checks, diff hygiene, and no-staged-files checks passed. Evidence: `.10x/evidence/2026-08-27-test-suite-concern-layout-implementation.md`.
- 2026-08-27: Independent review passed with no findings: `.10x/reviews/2026-08-27-test-suite-concern-layout-review.md`. Parent directly re-observed exact tree/initializer state, ranking validation, full `1191 passed / 1292 subtests`, diff hygiene, and no staged files before closure.

## Closure mapping

The exact mapping, empty initializers, no root modules/shims, updated imports, immutable v2/path-only v3 contract, unchanged test counts, dual-runtime discovery, validators, workflow/package/isolated checks, semantic move audit, and no-staged-files criterion are supported by `.10x/evidence/2026-08-27-test-suite-concern-layout-implementation.md` and the passing independent review.

## Retrospective

Mirroring production concerns makes the test suite easier to navigate without requiring risky large-file decomposition. Active evaluation paths must advance through immutable successor versions rather than rewriting prior artifacts; path-only successors keep that cost bounded and truthful.
