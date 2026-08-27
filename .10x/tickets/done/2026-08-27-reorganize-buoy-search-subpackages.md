Status: done
Created: 2026-08-27
Updated: 2026-08-27
Parent: .10x/tickets/done/2026-08-27-decouple-evidence-from-source-layout-plan.md
Depends-On: .10x/tickets/done/2026-08-27-implement-routing-semantic-compatibility.md, .10x/tickets/done/2026-08-27-version-buoy-repository-evaluations.md, .10x/tickets/done/2026-08-27-add-ranking-default-promotion-gate.md

# Reorganize Buoy Search into concern-oriented subpackages

## Cold-start context

`src/buoy_search/` currently contains more than forty implementation modules at one level. The user requested a first-pass concern-based reorganization and explicitly selected a breaking cleanup: downstream flat imports do not need compatibility forwarding modules.

The governing behavioral and layout contract is `.10x/specs/buoy-search-subpackage-layout.md`.

## Scope

- Create the subpackages and move modules according to the governing specification.
- Update all imports in `src/` and `tests/` to the new paths.
- Update package and command entrypoints as needed to preserve command behavior.
- Update packaging configuration only if required for recursive subpackage/data inclusion.
- Add or adjust narrowly targeted import/package checks when existing coverage does not establish the acceptance criteria.

## Explicit exclusions

- Compatibility modules for old flat paths.
- Symbol renaming, API redesign, behavior changes, or module splitting.
- Refactoring internals while files are being moved.
- Moving the cross-cutting root modules listed in the specification.
- Reorganizing tests into matching directories in this pass.

## Acceptance criteria

1. Module placement exactly matches `.10x/specs/buoy-search-subpackage-layout.md`.
2. No tracked source or test file imports an old flat path for a moved module.
3. All new module paths import successfully.
4. Existing test behavior passes after path-only test updates.
5. `python -m buoy_search --help` succeeds.
6. A built wheel contains all new subpackages and existing package data.
7. The diff contains no unrelated cleanup or behavioral redesign.

## Evidence expectations

- File-tree inventory after the move.
- Search output demonstrating absence of old moved-module imports.
- Import smoke-check output.
- Full test-suite command and result.
- CLI help command and result.
- Wheel build command and archive inventory showing subpackages and data.
- Final diff summary and explicit residual risks.

## Blockers

None.

## Progress and notes

- 2026-08-27: Inspected the package tree, module sizes, internal/test import usage, package configuration, and existing 10x records. No existing ticket, specification, decision, or knowledge record was found for this reorganization.
- 2026-08-27: User selected a breaking cleanup rather than compatibility forwarding modules.
- 2026-08-27: Opened this executable ticket after activating the focused layout specification. No implementation performed in the specification/ticket-authoring turn.
- 2026-08-27: Created all specified concern subpackages, moved the implementation modules without forwarding modules, and updated imports across package source, tests, executable scripts, `pyproject.toml`, package-relative data lookups, source-receipt lookup paths, and repository-eval path judgments.
- 2026-08-27: Compilation and all-new-path import smoke checks passed. `python -m buoy_search --help` passed. Wheel build/inventory passed with all subpackages and package data present. Searches found no old moved-module imports. No files were staged.
- 2026-08-27: The repository-aware full suite initially reached 1127 passing tests and exposed relocation lookup fixes plus exact routing receipt rejection. After fixing path-only lookup expectations, a focused rerun reached 129 passing tests and 148 passing subtests with six duplicate failures, all caused by the packaged active routing artifact rejecting changed production-module hashes.
- 2026-08-27: Escalated the required four-hash artifact rebind. Supervisor denied recertification under this structural-only ticket, prohibited compatibility copies, and directed preservation of the blocked work. Marked the ticket blocked without changing artifact hashes. Durable command output, results, blocker analysis, and limits are recorded in `.10x/evidence/2026-08-27-buoy-search-subpackage-reorganization-blocked-validation.md`.
- 2026-08-27: The owner subsequently authorized a separately governed narrow routing-receipt recertification. Exactly four receipt values were rebound after source-delta audit; active artifact validation and focused routing tests passed. The full suite then exposed the immutable repository-eval path contract described in the updated blocker. Final stopped validation reached `1167 passed, 1213 subtests passed` with ten old-path existence failures. No eval-contract mutation was authorized. Evidence: `.10x/evidence/2026-08-27-routing-receipt-recertification-blocked-by-eval-path-contract.md`.
- 2026-08-27: Owner later authorized dataset/fixture path migration and mechanically derived hashes. Pre-mutation tracing found the validator also requires judgment membership in a historical source-path manifest pinned to an old source commit and corpus artifact. Updating its paths alone would falsify that provenance, while corpus regeneration remained unauthorized. Supervisor directed stopping; no eval-contract files changed and no validation rerun. Evidence: `.10x/evidence/2026-08-27-eval-path-migration-provenance-blocker.md`.
- 2026-08-27: Owner superseded both brittle mechanisms with semantic routing compatibility, immutable versioned eval history/current data, `baseline_pending`, and a single authority-file promotion gate. Attached this ticket to `.10x/tickets/done/2026-08-27-decouple-evidence-from-source-layout-plan.md`; final integration now depends on its three bounded implementation children.
- 2026-08-27: Resumed after all three dependencies. Exact root/subpackage inventories, old-import/no-shim audits, compilation and local validators, CLI parity, 1176-test Python 3.11/3.13 suites, wheel/sdist inventory, all-37-module isolated imports, semantic routing/default parity, explicit-namespace bypass, and diff/no-staged hygiene passed. No integration source fix was required. Evidence: `.10x/evidence/2026-08-27-buoy-search-subpackage-final-integration.md`. Ticket remains active pending independent review.
- 2026-08-27: Aggregate review failed because hosted clean-wheel Python still imported removed flat modules; it also identified eval/promotion authority gaps owned across dependencies. Updated hosted imports to `indexing.treatment_token_budget` and `evals.routing_quality`, and added static plus executable workflow-heredoc coverage in `tests/test_ci_workflow.py`. Integrated the repaired pending path-membership and recorded-basket promotion interfaces. Exact validators and 1186-test suites passed on Python 3.11/3.13; wheel/sdist, isolated exact workflow smoke, 38 imports, CLI/layout/shim audits, and hygiene passed. Updated evidence: `.10x/evidence/2026-08-27-buoy-search-subpackage-final-integration.md`.
- 2026-08-27: Integrated the completed 13-repository basket-registry repair without adding a benchmark. Packaging and hosted clean-wheel smoke include and assert the exact zero-basket registry; source CI validates it and reports zero registered baskets. Exact Python 3.11/3.13 validators and 1189-test suites, workflow coverage, 91-entry wheel/175-entry sdist, isolated exact workflow execution, all 38 imports, CLI/layout/no-shim audits, and hygiene passed.
- 2026-08-27: Integrated strict registered dataset/corpus semantic validation after provenance review. Future nonempty baskets must validate exact dataset identity/cases/judgments and corpus source/document inventory semantics even after consistent rehashing; production remains empty. Exact Python 3.11/3.13 validators and 1191-test suites, focused workflow/promotion tests, wheel/sdist, isolated workflow/registry smoke, imports/layout/no-shim audits, and hygiene passed. Updated evidence: `.10x/evidence/2026-08-27-buoy-search-subpackage-final-integration.md`.
- 2026-08-27: Fresh independent aggregate review passed with no findings: `.10x/reviews/2026-08-27-evidence-layout-final-review.md`. Closed after exact layout, imports, CLI, distributions, tests, and no-shim criteria were rechecked.

## Closure mapping

The final tree matches the specified concern directories; old flat modules and imports are absent; all 38 current module imports, CLI parity, 1,191-test Python 3.11/3.13 suites, validators, wheel/sdist, isolated install, hosted workflow smoke, and hygiene checks pass. `.10x/evidence/2026-08-27-buoy-search-subpackage-final-integration.md` and the final review support closure.

## Retrospective

A package move exposed hidden coupling between source layout and evidence authority. Decoupling those contracts before finalizing the move produced a cleaner public package without compatibility shims or historical-evidence rewrites.
