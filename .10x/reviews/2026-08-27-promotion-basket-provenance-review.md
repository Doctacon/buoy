Status: recorded
Created: 2026-08-27
Updated: 2026-08-27
Target: .10x/tickets/done/2026-08-27-add-ranking-default-promotion-gate.md
Verdict: fail

# Promotion basket provenance review

## Target

Basket-registry repair and aggregate integration after `.10x/reviews/2026-08-27-evidence-layout-aggregate-review.md`.

Independent review run: `37b71e16-d3dd-4282-be1b-04026d1341f8`.

## Findings

### Significant: registered dataset and corpus files lack semantic validation

The validator verifies registered dataset/corpus raw hashes but accepts each file as an arbitrary JSON object. A future registry could therefore bind `{}` or unrelated JSON, recompute member/basket hashes, and pass. Recorded dataset identity/version/repository and corpus manifest repository/source identity, nonempty canonical document inventory, paths, and content hashes must be strictly validated against each basket member. Tests must reject semantically invalid files even after their hashes and registry identities are consistently recomputed.

## Correct behavior retained

The review confirmed all prior findings were materially repaired: hosted imports, pending-v2 rejection, empty production registry, complete 13-member registration, benchmark linkage, equal baseline/candidate inputs, safe options, PR/push comparison, semantic routing, and no-shim package layout.

## Verdict

Fail pending strict registered dataset/corpus schema and semantic validation.

## Residual risk

No real promotion basket or hosted Actions run exists. Fresh independent review is required after repair.
