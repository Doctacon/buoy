Status: done
Created: 2026-08-27
Updated: 2026-08-27
Parent: None
Depends-On: None

# Decouple evidence authority from source layout

## Aggregate outcome

Replace raw Python-byte routing compatibility and current-checkout-coupled historical ranking evidence with semantic routing compatibility, immutable versioned repository evaluations, and a mechanically identifiable promotion-only benchmark gate. Then complete the approved Buoy package reorganization without compatibility shims.

## Governing records

- `.10x/decisions/buoy-validates-routing-semantics-not-python-bytes.md`
- `.10x/decisions/buoy-versions-repo-evals-and-gates-only-default-promotion.md`
- `.10x/specs/routing-semantic-compatibility.md`
- `.10x/specs/versioned-repository-evaluations-and-promotion-gate.md`
- `.10x/specs/buoy-search-subpackage-layout.md`

## Child sequence

1. `.10x/tickets/done/2026-08-27-implement-routing-semantic-compatibility.md`
2. `.10x/tickets/done/2026-08-27-version-buoy-repository-evaluations.md`
3. `.10x/tickets/done/2026-08-27-add-ranking-default-promotion-gate.md` (depends on child 2; may proceed in parallel with child 1)
4. `.10x/tickets/done/2026-08-27-reorganize-buoy-search-subpackages.md` (resume final integration only after children 1–3)

Children 1 and 2 are independent and may execute in parallel in isolated worktrees only if their integration is coordinated; the existing dirty structural migration makes sequential execution in the shared worktree safer. Child 3 builds on the versioned evaluation validator. Child 4 performs aggregate reconciliation, complete validation, packaging, and review rather than widening earlier child scope.

## Integration points

- Routing schema-v4 migration removes the temporary four-receipt rebind currently present in the working tree.
- Evaluation v1 is preserved as history; v2 resolves reorganized paths without rewriting v1.
- The promotion gate introduces active defaults without changing their values.
- Final structural validation must prove all three contracts coexist in source, tests, wheel, sdist, and isolated installation.

## Aggregate acceptance criteria

- Ordinary package refactors do not require routing source-hash recertification or historical dataset rewriting.
- Routing still fails closed on semantic incompatibility and preserves established behavior.
- Historical repo eval evidence is immutable; current v2 semantics and paths validate with `baseline_status=pending`.
- All PRs run the same fast local suite; only authority-file changes require a supplied passing promotion artifact.
- Existing ranking defaults and routing behavior remain unchanged.
- The concern-oriented package layout ships with no flat compatibility modules.
- Full tests, package checks, independent review, evidence, and record graph all pass coherently.

## Explicit exclusions

- New ranking defaults, labels, benchmarks, routing thresholds, models, or provider operations.
- Live evaluation, release, publication, deployment, or branch integration.

## Progress and notes

- 2026-08-27: Opened after the owner selected semantic compatibility, immutable versioned evals, `baseline_pending`, and promotion-only benchmarking identified by a single authority-file diff. Superseded and cancelled the narrower receipt/path/corpus rewrite approaches before opening implementation children.
- 2026-08-27: All four implementation children completed their source work and initial aggregate integration validation. Python 3.11/3.13 suites, source validators, CLI/import/shim checks, wheel/sdist, isolated installation, semantic routing, versioned eval, promotion authority, and diff hygiene passed. Evidence: `.10x/evidence/2026-08-27-buoy-search-subpackage-final-integration.md`. Parent and children remained active pending independent review.
- 2026-08-27: Independent aggregate review failed with stale hosted clean-wheel imports and eval/promotion authority findings. Repaired those findings across the amended versioning/promotion interfaces and final integration: hosted imports now use subpackages, workflow Python snippets have static/dynamic regression coverage, pending v2 cannot claim corpus/promotion authority, promotion requires a recorded content-addressed 13-repository basket with exact experiment isolation, and PR/push comparison fails closed. Exact 1186-test Python 3.11/3.13 suites, validators, wheel/sdist, isolated exact workflow smoke, CLI/import/layout/shim audits, and hygiene passed.
- 2026-08-27: A later review retained one P1 because 12 basket members remained self-declared. Integrated the completed registry repair across parent/package/CI: promotion requires an exact registered basket whose 39 member artifacts are byte-verified; production truthfully packages zero baskets and claims no benchmark. Hosted wheel smoke asserts the zero registry. Exact Python 3.11/3.13 validators and 1189-test suites, 91-entry wheel/175-entry sdist, isolated exact workflow/registry validation, imports/layout/no-shim audits, and hygiene passed.
- 2026-08-27: Provenance review then found byte-verified dataset/corpus files could remain semantically arbitrary. Integrated strict schema, identity, canonical path, judgment-to-inventory, source commit, document/content hash, and inventory count/hash validation plus consistently rehashed invalid-fixture rejection. Exact Python 3.11/3.13 validators and 1191-test suites, 58-test focused basket, package/isolated workflow, layout/no-shim, and hygiene checks passed. Production remains zero-basket with no benchmark claim. Updated evidence: `.10x/evidence/2026-08-27-buoy-search-subpackage-final-integration.md`.
- 2026-08-27: Final independent review passed with no findings and merge verdict OK: `.10x/reviews/2026-08-27-evidence-layout-final-review.md`. Closed all children and this parent after graph, evidence, specs, exclusions, and residual-risk dispositions were reconciled.

## Closure mapping

Every aggregate criterion is supported by the three implementation evidence records, final integration evidence, dual-runtime full suites, distribution/isolated checks, and passing final review. Existing defaults, routing semantics, and judgments remain unchanged; historical v1 is immutable; v2 is pending; production has no promotion basket; the package layout contains no flat shims.

## Retrospective

The broad lesson is to bind evidence to semantic contracts and immutable artifacts rather than implementation bytes or the current checkout. Activation should be explicit and mechanically narrow; historical evidence should remain immutable; expensive validation should be paid only at promotion.
