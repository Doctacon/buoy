Status: cancelled
Created: 2026-08-27
Updated: 2026-08-27
Parent: None
Depends-On: .10x/tickets/done/2026-08-27-reorganize-buoy-search-subpackages.md

# Recertify routing receipts after the subpackage migration

## Cold-start context

The implementation in `.10x/tickets/done/2026-08-27-reorganize-buoy-search-subpackages.md` is structurally complete but blocked because the active routing-confidence artifact binds the old exact bytes of four moved modules. The owner explicitly approved narrow recertification on 2026-08-27 after the receipt purpose and scope were explained.

Historical governing authority: `.10x/decisions/superseded/buoy-recertifies-routing-receipts-for-subpackage-migration-field-correction.md`.

Required context:

- `.10x/specs/buoy-search-subpackage-layout.md`
- `.10x/decisions/buoy-activates-certified-bounded-prototype-routing.md`
- `.10x/decisions/superseded/buoy-recertifies-final-reviewed-cli-receipt.md`
- `.10x/evidence/2026-08-27-buoy-search-subpackage-reorganization-blocked-validation.md`

## Scope

- Verify that changes in the four receipt-bound modules are relocation-only and non-semantic.
- Measure their final exact SHA-256 values.
- Update exactly the four authorized receipt fields in `src/buoy_search/data/automatic_routing_confidence_calibration.json`.
- Prove parsed and textual artifact equality outside those four values.
- Run routing validation, full tests, CLI checks, wheel/package inventory, and installed-wheel validation.
- Obtain independent review of the structural migration and recertification delta.
- Record complete evidence and reconcile both tickets if all acceptance criteria are supported.

## Explicit exclusions

- Routing thresholds, policies, cases, reports, digests, projections, evaluator identities, revisions, or non-authorized receipts.
- Calibration regeneration or live collection/evaluation.
- Provider, catalog, card, content, namespace, credential, release, publication, or deployment operations.
- Compatibility forwarding modules.
- Any unrelated source or test cleanup.

## Acceptance criteria

1. Reviewable evidence proves the four source changes are relocation-required and do not alter routing semantics.
2. Exactly the four authorized artifact receipt strings change; every other parsed field and text line remains unchanged.
3. Production artifact validation accepts the four new installed-source identities.
4. Focused routing/certification tests pass.
5. The full repository test suite passes.
6. `python -m buoy_search --help` passes.
7. Wheel inventory contains all required subpackages and package data, and an isolated installed-wheel validation passes.
8. Independent review returns pass with no unresolved significant findings.
9. Durable evidence records commands, outputs, hashes, comparison method, package identity, review result, and limits.

## Evidence expectations

- Before/after artifact SHA-256 and exact four-field comparison.
- Four measured module SHA-256 values and path identities.
- Diff audit for each receipt-bound module.
- Focused and full test outputs.
- Source-tree, wheel, and installed-wheel validation outputs.
- Independent review record.
- Residual-risk statement.

## Blockers

None. Cancelled because the owner superseded raw Python-file receipt recertification with a semantic routing compatibility contract. The implemented temporary receipt values remain working-tree history until the replacement ticket removes that runtime mechanism.

## Progress and notes

- 2026-08-27: Opened after owner approval. No recertification or implementation was performed in this authority/ticket-authoring turn.
- 2026-08-27: Execution found that the first decision named a nonexistent `routing_quality_module_sha256` field. Inspected artifact authority proves the existing routing-quality receipt is `receipts.evaluator_scorer_sha256`. Superseded the mistaken decision with the exact field-correction decision before permitting mutation; scope remains the same four source receipts.
- 2026-08-27: Audited all four receipt-bound source deltas against their pre-migration `HEAD` bytes and confirmed only relocated imports, package-data paths, and exact receipt-source lookup paths changed. No routing/evidence semantics or call signatures changed.
- 2026-08-27: Rebound exactly `receipts.evaluator_scorer_sha256`, `routing_module_sha256`, `cli_module_sha256`, and `evidence_module_sha256`. Recursive parsed comparison found only those four changed paths; textual comparison found only their four old/new value lines. Production active-artifact validation and the focused routing suite (`135 passed, 148 subtests passed`) passed.
- 2026-08-27: Updated three static provider-receipt audit tests to the specified relocated source paths. Their focused basket passed (`37 passed, 74 subtests passed`) after restoring the immutable eval dataset bytes.
- 2026-08-27: Final full suite reached `1167 passed, 1213 subtests passed` with ten failing eval-judgment path-existence subtests, all caused by frozen old flat repo paths. No authority exists to revise the immutable dataset/derived contract, so package/installed-wheel validation and independent review were not continued. Marked blocked per supervisor direction. Evidence: `.10x/evidence/2026-08-27-routing-receipt-recertification-blocked-by-eval-path-contract.md`.
- 2026-08-27: After owner authorization of a narrow eval-path migration, dependency tracing found that judgment membership is also bound to a historical source-path manifest and corpus identity. Supervisor prohibited an inconsistent path-only rewrite and unapproved corpus regeneration. The receipt rebind remains preserved and locally valid, but closure remains blocked; no eval-contract files changed and no files were staged. Evidence: `.10x/evidence/2026-08-27-eval-path-migration-provenance-blocker.md`.
- 2026-08-27: Cancelled after the owner selected semantic routing compatibility instead of exact implementation-byte receipts. Replacement work is owned by the new semantic routing contract plan.
