Status: done
Created: 2026-08-27
Updated: 2026-08-27
Parent: .10x/tickets/done/2026-08-27-decouple-evidence-from-source-layout-plan.md
Depends-On: .10x/tickets/done/2026-08-27-version-buoy-repository-evaluations.md

# Add the ranking-default promotion gate

## Scope

Implement the single packaged ranking-default authority and mechanical promotion gate from `.10x/specs/versioned-repository-evaluations-and-promotion-gate.md`. Move current default values without changing them, make authority-file changes mechanically identifiable against the merge base, and validate supplied immutable promotion artifacts without running benchmarks in CI.

## Acceptance criteria

- `src/buoy_search/data/ranking_defaults.json` is the sole independently editable authority for current website/repository defaults.
- Runtime behavior exactly reproduces current defaults.
- CI/validator distinguishes promotion solely by authority-file merge-base diff.
- No-change and implementation-only changes use fast checks.
- Authority changes fail without a matching valid same-corpus artifact and passing promotion-policy result.
- A valid fixture artifact passes without live/model/provider work.
- Current authority introduction is non-promotional and changes no active value.
- Focused, full, package, and installed-package tests pass.

## Explicit exclusions

Changing defaults, generating a real benchmark, promoting experimental behavior, provider/model calls, releases, or unrelated CI redesign.

## Evidence expectations

Old/new default parity, authority schema/hash, merge-base classification matrix, promotion artifact validation matrix, focused/full/package outputs, no-external-effect evidence, and residual risks.

## Blockers

None.

## Progress and notes

- 2026-08-27: Opened from the ratified promotion-only gate contract. No implementation occurred in this record-authoring turn.
- 2026-08-27: Added strict packaged `ranking_defaults.json` authority and runtime loader; derived all established retriever default constants/mappings from it without changing values. Added merge-base-only promotion classification, automatic immutable artifact discovery, strict same-corpus baseline/candidate validation, recomputed distribution-aware policy, secret-key rejection, CI base-SHA wiring, documentation, and a complete offline fixture matrix.
- 2026-08-27: Focused pytest passed (`43 passed, 13 subtests`); full pytest passed (`1176 passed, 1232 subtests`, 57 existing warnings); ranking/versioned-eval and promotion validators, compileall, focused unittest, C6 validation, wheel/sdist build and inventory, isolated Python 3.13 wheel runtime parity, and diff hygiene passed. No files are staged. No benchmark, retrieval, model, provider, credential, namespace, catalog, release, publication, or deployment operation occurred. Evidence: `.10x/evidence/2026-08-27-ranking-default-promotion-gate-implementation.md`. Ticket remains active pending independent review and parent integration.
- 2026-08-27: Aggregate integration passed authority/promotion validators, unchanged default parity, 1176 tests on Python 3.11 and 3.13, package/isolated authority loading, CLI/import audits, and diff hygiene. Evidence: `.10x/evidence/2026-08-27-buoy-search-subpackage-final-integration.md`. Ticket remains active pending independent review.
- 2026-08-27: Aggregate review failed because pending/path-only Buoy v2 could authorize promotion, evidence bound only Buoy rather than a recorded 13-repository basket, baseline/candidate non-authority inputs could differ, retrieval options were free-form and credential value checks incomplete, and push/no-base CI could bypass comparison. Review: `.10x/reviews/2026-08-27-evidence-layout-aggregate-review.md`.
- 2026-08-27: Repaired every promotion-gate finding under the amended spec. Artifact schema v2 now requires a content-addressed recorded 13-repository basket, per-repository dataset/corpus/recorded-benchmark identities, registered recorded/promotion-eligible Buoy authority, exact non-authority input equality, strict bounded options and safe model/contract identifiers, aggregate/per-repo benchmark rehashing, PR merge-base and push previous-SHA modes, fail-closed missing bases, and explicit exact-hash introduction proof. Expanded mutation coverage passed (`51 passed, 21 subtests` focused); full suite passed (`1184 passed, 1240 subtests`); contract/CI-mode/C6/compile, package, isolated-install, and hygiene checks passed. No files are staged and no real benchmark/external operation occurred. Evidence: `.10x/evidence/2026-08-27-ranking-default-promotion-gate-review-repair.md`. Ticket remains active pending fresh independent review.
- 2026-08-27: Final aggregate reconciliation exercised repaired PR and push authority comparison, required missing-base failure, versioned path-membership validation, and the recorded-basket fixture alongside hosted workflow repair. Exact Python 3.11/3.13 suites each passed 1186 tests; package and isolated checks passed. Evidence: `.10x/evidence/2026-08-27-buoy-search-subpackage-final-integration.md`.
- 2026-08-27: Latest review retained one P1: only Buoy was checked against repository authority while the other 12 basket members could self-declare hashes. Added packaged versioned `repo_ranking_promotion_baskets.json`; production truthfully contains zero baskets while Buoy v2 is pending. Promotion artifacts now reference exact registered basket ID/version/hash only. Every registered 13-repository member resolves actual regular dataset, corpus-manifest, and recorded-benchmark JSON files under the repository root and reproduces their raw hashes; benchmark identity/config/result linkage is strict. Passing tests build all 39 real temporary files plus complete registries; tampered/missing/unregistered member cases fail. Focused tests passed (`53 passed, 21 subtests`), full pytest passed (`1188 passed, 1276 subtests`), exact CI-style unittest passed 1188 tests, and contract/compile/C6/package/isolated/hygiene checks passed. No files are staged and no real benchmark/external operation occurred. Evidence: `.10x/evidence/2026-08-27-ranking-promotion-basket-registry-review-repair.md`.
- 2026-08-27: Integrated the zero-basket registry through parent package/CI validation. Hosted clean-wheel smoke now reads the packaged resource and asserts exact `{baskets: [], schema_version: 1}`; source CI promotion validation reports `registered_baskets=0`. Exact Python 3.11/3.13 validators and 1189-test suites, 91-entry wheel/175-entry sdist, isolated exact workflow smoke, imports/layout/no-shim audits, and hygiene passed. Aggregate evidence: `.10x/evidence/2026-08-27-buoy-search-subpackage-final-integration.md`. No benchmark/external operation occurred; ticket remains active pending fresh independent review.
- 2026-08-27: Provenance review failed because consistently rehashed arbitrary dataset/corpus JSON could still register. Added exact schema/identity validation for every dataset's ID/version/repository/cases/judgments and every corpus's repository/full Git source identity/nonempty canonical document inventory/path/content hashes, including basket-member count/inventory binding and judgment-to-corpus membership. Recorded benchmarks now repeat repository/source identity. Mutation tests consistently rehash and re-register semantically invalid files and still reject. Focused tests passed (`55 passed, 37 subtests`); full pytest passed (`1191 passed, 1292 subtests`); exact unittest, contract/C6/compile, package/isolated, and hygiene checks passed. Production registry remains empty; no files are staged and no real benchmark/external operation occurred. Evidence: `.10x/evidence/2026-08-27-promotion-basket-provenance-semantic-validation-repair.md`.
- 2026-08-27: Integrated strict dataset/corpus semantics through aggregate CI/package validation. Exact Python 3.11/3.13 validators and 1191-test suites, 58-test focused workflow/promotion basket, 91-entry wheel/175-entry sdist, isolated exact workflow/registry smoke, all 38 imports, CLI/layout/no-shim audits, and hygiene passed. Production remains a truthful packaged zero-basket registry; no external operation occurred. Aggregate evidence: `.10x/evidence/2026-08-27-buoy-search-subpackage-final-integration.md`.
- 2026-08-27: Fresh independent review found no issues and passed the aggregate implementation: `.10x/reviews/2026-08-27-evidence-layout-final-review.md`. Closed after all prior significant findings and acceptance criteria were rechecked.

## Closure mapping

The packaged authority exactly preserves existing defaults. PR/push classification, fail-closed missing-base handling, pending rejection, strict safe options, equal experiment inputs, registered 13-repository byte and semantic provenance, policy checks, empty production registry, and package/CI behavior are covered by focused mutation tests, dual-runtime full suites, distribution evidence, and final review.

## Retrospective

Promotion is easiest to govern when activation has one mechanically identifiable authority file. Expensive benchmark evidence belongs at default promotion, while strict registries and semantic validation prevent self-consistent but fabricated artifacts from becoming authority.
