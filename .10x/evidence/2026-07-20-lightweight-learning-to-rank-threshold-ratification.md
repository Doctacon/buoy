Status: recorded
Created: 2026-07-20
Updated: 2026-07-20
Relates-To: .10x/specs/lightweight-learning-to-rank-stability-thresholds.md, .10x/tickets/2026-07-19-evaluate-lightweight-learning-to-rank.md, .10x/reviews/2026-07-20-lightweight-learning-to-rank-stability-thresholds-review.md

# Lightweight Learning-to-Rank Threshold Ratification

## What was observed

The user explicitly ratified the exact C7 threshold checkpoint for PR #63 after independent review passed head `4cb1649dae5c05707fbb91fcf28e02765e634c5f`. The ratification activates `.10x/specs/lightweight-learning-to-rank-stability-thresholds.md` exactly as reviewed.

The ratification preserves the reviewed behavioral contract unchanged: training-fold population standardization; inclusive `abs(w) >= ln(1.25)` fold materiality; inclusive `10/13` basket materiality; `12/13` nonzero sign stability; absolute-weight order with `ln(1.10)` deadband, inclusive `10/13` dominant relation, at most one direct strict reversal, and a consistent total preorder; equal repository voting; complete reporting; and insufficient/overfit or uninformative no-action outcomes without tuning.

## Procedure

1. Recorded the independent PASS at `.10x/reviews/2026-07-20-lightweight-learning-to-rank-stability-thresholds-review.md` against reviewed PR #63 head `4cb1649`.
2. Changed the specification status from `draft` to `active` and replaced only obsolete proposal/ratification-status prose. The exact reviewed thresholds, equality rules, fold handling, leakage constraints, reporting requirements, and outcomes were preserved.
3. Updated C7 to remove its threshold-ratification blocker while retaining `Status: blocked` and the incomplete C3 immutable-cache dependency.
4. Performed no fitting, scoring, cache creation, training, source/test change, live operation, label change, or product/default mutation.

## What this supports or challenges

This supports activation of the exact reviewed threshold contract and establishes that threshold ratification is no longer a C7 blocker. It challenges any inference that ratification makes C7 executable: C3 remains blocked and incomplete, C7 must consume its exact immutable compatible cache/hash, and any passing result would remain experiment-only evidence subject to later label-confidence and product-ownership checkpoints.

## Validation boundary

The reviewed head's hosted Python 3.11, Python 3.13, and distribution-build checks passed. Final record-only validation checks specification semantics, references, diff hygiene, branch ancestry, and exact-head hosted checks. No runtime model or retrieval test is evidence for this activation.

## Safety observation

No model fitting or scoring, cache generation or inspection, retrieval or embedding call, credential access, namespace/card/catalog/default operation, source/test/dependency/lockfile change, label edit, training artifact, or promotion occurred. The only external mutations required by this ratification task are its Git commit and branch push.

## Limits and residual risk

C3's compatible cache does not exist and remains blocked on the unapproved/unverified Buoy baseline and retrieval-only checkpoint. Feature mechanics still must be frozen and hashed before any later fit. The labels remain assistant-drafted and non-product-ratifying, the dependent folds are not a significance test, and no learned result or promotion eligibility has been observed.
