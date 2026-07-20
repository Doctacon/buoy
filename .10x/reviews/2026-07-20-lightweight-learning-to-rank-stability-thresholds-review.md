Status: recorded
Created: 2026-07-20
Updated: 2026-07-20
Target: PR #63 at commit `4cb1649dae5c05707fbb91fcf28e02765e634c5f`
Verdict: pass

# Lightweight Learning-to-Rank Stability Thresholds Review

## Target and method

Independent adversarial review of PR #63 head `4cb1649` against `origin/develop` at `16bcbb2`. The review inspected C7 and its parent graph, the draft focused threshold specification, the active promotion policy, the current 13-repository/90-composite-identity/369-judgment contract and evidence, the record-only diff, and hosted checks.

## Findings

- Materiality is exact and computable before outcomes are inspected: each training fold uses population standardization over its 12 training repositories, zero-variance features are absent, fold materiality is inclusive at `abs(w) >= ln(1.25)`, and basket materiality is inclusive at `10/13` folds.
- Sign stability requires one nonzero direction in at least `12/13` folds. Zero, absent, and opposite-sign outcomes are handled explicitly and cannot count as agreement.
- Order stability uses absolute standardized weights, deadband `ln(1.10)`, at least `10/13` matching strict-or-tied relations, at most one direct reversal of a dominant strict relation, and a consistent total preorder across all basket-material pairs.
- Repository folds receive equal votes. Pooled, case-weighted, or favorable-subset aggregation cannot replace the 13-fold gate.
- Feature mechanics must be frozen before fitting, held-out inputs and repository identity are prohibited, and scaling uses training repositories only.
- Threshold failure produces an insufficient/overfit or uninformative result, retains the current default, prohibits tuning or re-fitting under the same preregistration, and takes no product action.
- The active five-part distribution policy remains separate and applicable under `.10x/decisions/repo-ranking-promotion-policy.md`.
- C3 remains blocked on the unapproved/unverified Buoy baseline and retrieval-only checkpoint. C7 therefore remains blocked even if the threshold specification is ratified.
- Current validation reports 13 repositories, 90 composite identities, 13 folds, and 369 judgments, consistent with `.10x/evidence/2026-07-20-remove-buoy-internal-ranking-judgment.md`.
- The reviewed diff contains only the draft specification and C7 ticket update; no source, tests, training, cache, dataset, or live-operation change was made.
- Hosted checks passed on reviewed head `4cb1649` for Python 3.11, Python 3.13, and distribution build.

### Blockers

None for exact threshold ratification and specification activation. C3 cache completion and C7's other declared execution dependencies remain unresolved and outside the reviewed shaping scope.

## Verdict

Pass. The focused threshold specification may be activated without changing its exact materiality, standardization, fold aggregation, sign/order, leakage, stop, or no-action contract. This pass does not authorize C7 execution, training, fitting, scoring, cache creation, source changes, live calls, or promotion.

## Exact reviewed user checkpoint

> Confirm or correct this C7 preregistration: standardize each feature from the 12 training repositories before fitting; define a fold-material coefficient as `abs(w) >= ln(1.25)` and basket-material as at least `10/13` folds; require one nonzero sign in at least `12/13` folds; and require every basket-material feature pair to have the same strict-or-tied absolute-weight relation, using deadband `ln(1.10)`, in at least `10/13` folds with at most one direct reversal of a dominant strict order. Equality passes the named cutoff; `abs(w) <= 1e-12` and zero-variance/absent features do not count as sign or order agreement. Threshold failure means insufficient/overfit and no tuning or product action.

## Residual risk

These thresholds are ratified operational policy, not an empirical claim, statistical significance test, or confidence interval. The 13 leave-one-repository-out fits have overlapping training sets, and the labels remain assistant-drafted experiment-only calibration evidence. Runtime results and C3 cache compatibility remain unobserved.
