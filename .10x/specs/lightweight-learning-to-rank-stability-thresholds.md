Status: active
Created: 2026-07-20
Updated: 2026-07-20

# Lightweight Learning-to-Rank Stability Thresholds

## Purpose and authority

This active specification defines the exact material-weight, sign-stability, and order-stability contract required before C7 may fit or score a model. The user ratified the exact pre-registered contract after independent review passed PR #63 head `4cb1649dae5c05707fbb91fcf28e02765e634c5f`. C7 remains blocked until C3 supplies its immutable compatible cache.

The current contract after the ratified Buoy judgment removal still contains 13 repositories and 90 composite `repo_key:case_id` cases; only the judgment count changed, from 370 to 369. The frozen leave-one-repository-out order remains `black`, `buoy`, `click`, `django`, `flask`, `httpx`, `mkdocs`, `pydantic`, `pytest`, `requests`, `rich`, `ruff`, and `typer`. Each fold trains on the other 12 repositories. One repository is one fold vote regardless of whether it has five or ten cases.

These thresholds are an operational stability screen over 13 strongly overlapping fits, not a statistical significance test or confidence interval. The folds are dependent because their training sets overlap, and the assistant-drafted labels are experiment-only calibration evidence.

## Substrate assumed by the contract

The contract applies only to C7's already-bounded transparent ranker direction: one deterministic linear scoring function fitted with a deterministic pairwise logistic objective, using only the retrieval-time-observable feature families allowed by the C7 ticket. Candidate families include ANN/BM25/RRF ranks or scores, file-hit count, path role, filename/query overlap, path-token overlap, available Python symbol overlap, and current `repo_code` multiplier components.

Before any fit, C7 MUST separately freeze and hash the exact feature columns, orientations, categorical reference coding, missing-value treatment, pair construction, grade-to-preference rule, regularization, solver/version, seed, convergence rule, and tie-breaking. Feature columns MUST have stable semantics across all folds. Repository or namespace identity, case ID, answer text, per-repository weights, and held-out outcomes remain forbidden. This contract does not ratify those still-to-be-frozen mechanics or add a production ranker.

The intercept, if the frozen pairwise formulation retains one, is excluded from all materiality and stability tests because it does not order candidates from the same query.

## Pre-fit coefficient scale

Raw coefficients are not comparable when feature units differ. Therefore every fold MUST derive scale from feature values before fitting and without labels or held-out rows:

1. For feature column `j`, use all candidate rows from that fold's 12 training repositories after the frozen deterministic feature transformation and missing-value treatment.
2. Compute the population mean `mu_j = sum(x_j) / N` and population standard deviation `s_j = sqrt(sum((x_j - mu_j)^2) / N)`.
3. If `s_j <= 1e-12`, mark the feature `absent` for that fold, do not fit it, and serialize its coefficient as exact `0` plus `absent: true`.
4. Otherwise fit `(x_j - mu_j) / s_j`. Publish `N`, `mu_j`, and `s_j` for every feature and fold.

These operations are computable from the frozen cache before fitting. They may not be recomputed from the held-out repository or changed after outcomes are inspected. A non-finite value is a hard stop.

Let `w[f,j]` be the resulting finite standardized coefficient for fold `f` and feature `j`. A fitted coefficient with `abs(w[f,j]) <= 1e-12` is `zero`; it is not positive or negative. An absent feature is also unavailable for sign and order agreement even though its serialized coefficient is zero.

## Exact ratified thresholds

### Fold-level material weight

Define the fixed material-effect cutoff:

```text
M = ln(1.25) = 0.22314355131420976
```

A feature is material in fold `f` exactly when it is not absent and `abs(w[f,j]) >= M`. Equality is material. Under the ratified pairwise logistic contract, `M` means that a one-training-standard-deviation feature change changes fitted preference odds by at least 25%, holding other columns fixed.

A feature is **basket-material** exactly when it is material in at least 10 of the 13 folds. Equality at 10 passes. Nine or fewer does not pass. The cutoff is absolute and may not be replaced with a percentile, top-k weights, fitted-weight standard deviation, or any other result-dependent rule.

The threshold `10/13` is a predeclared supermajority that allows at most three repository-sensitive materiality exceptions while refusing to call an effect general from a simple majority.

### Sign stability

For every basket-material feature, count its positive, negative, and unavailable fold outcomes across all 13 folds. `w > 1e-12` is positive; `w < -1e-12` is negative; exact/numerical zero or absence is unavailable.

A basket-material feature is **sign-stable** exactly when either its positive count or its negative count is at least 12 of 13. Equality at 12 passes. Zero/absent folds do not agree with either sign, and an opposite sign counts as disagreement regardless of whether that opposite coefficient is fold-material.

Thus at most one fold may be zero, absent, or opposite to the dominant sign. This deliberately stronger threshold prevents a weight from being called interpretable when its direction depends on which repository is withheld.

### Order stability

Order compares absolute standardized effect sizes only among basket-material features. Define the fixed order deadband:

```text
O = ln(1.10) = 0.09531017980432493
```

For each unordered pair of basket-material features `(a, b)` and each fold where neither is absent, let `d = abs(w[f,a]) - abs(w[f,b])` and classify exactly one relation:

- `a > b` when `d >= O`;
- `b > a` when `d <= -O`;
- `tie` when `-O < d < O`.

Equality at `+O` or `-O` is a strict order, not a tie. A fold where either feature is absent is unavailable and agrees with no relation. Zero fitted coefficients remain available unless the feature was absent.

A pair is **order-stable** exactly when one relation occurs in at least 10 of the 13 folds and, when the dominant relation is strict, the reverse strict relation occurs in at most one fold. Equality at 10 passes. Ties may occupy the remaining folds. When `tie` is dominant, at least 10 ties are sufficient; the other at most three folds may be split between either strict direction.

The complete material-weight order is stable only when every unordered pair of basket-material features is order-stable **and** the dominant pair relations form one consistent total preorder: dominant ties are transitive equivalence tiers, strict relations between tiers are acyclic, and every strict relation agrees with the resulting tier order. Any cycle or non-transitive tie pattern fails order stability even when each pair separately meets its count threshold. A stable dominant tie means the pair occupies the same effect-size tier; it does not authorize inventing an order inside that tier. `O` prevents floating-point noise or operationally tiny magnitude differences from creating a claimed hierarchy.

If exactly one feature is basket-material, pairwise order stability is `not applicable` and passes, but materiality and sign stability still must pass. If no feature is basket-material, the model fails the stability gate as uninformative; order stability is not vacuously passing.

## Fold aggregation and reporting

C7 MUST report, in frozen fold order:

- all standardized coefficients, absent/zero flags, and pre-fit scales;
- the 13-bit fold-material mask and count for every feature;
- positive, negative, zero, and absent counts for every basket-material feature;
- all pair relation counts and unavailable counts for basket-material features;
- a deterministic ordered-tier rendering derived only from passing pair relations; and
- explicit pass/fail mapping for materiality, sign, order, and the separate active promotion-policy metrics.

No pooled refit, case-weighted fold vote, average coefficient, median coefficient, bootstrap, or favorable subset of repositories may replace the 13-fold gate. Such values may be diagnostics only if preregistered before fitting. Coefficients and relation classifications MUST reproduce exactly on a deterministic rerun; C1's `1e-12` offline floating-point tolerance applies only to numeric reproduction, not to changing the inclusive threshold rules above.

## Outcomes and no-tuning rule

Before a complete compatible C3 cache exists: **stop without fitting or scoring; C7 remains blocked**.

After ratification and an otherwise valid execution:

- Zero basket-material features: classify `insufficient/uninformative`; retain the current default and take no product action.
- Any basket-material feature failing `12/13` sign stability: classify `insufficient/overfit`; retain the current default and take no product action.
- Any basket-material pair failing the `10/13` order rule: classify `insufficient/overfit`; retain the current default and take no product action.
- Any active full-basket policy failure, including any repository score or Precision@5 regression: stop and classify `insufficient/overfit`, regardless of weight stability.
- All stability thresholds and the active policy pass: record experiment-only promotion-candidate evidence. Default promotion remains blocked on the later label-confidence checkpoint and a separate product owner.

A failure MUST NOT trigger threshold relaxation, feature deletion, regularization changes, alternate scaling, fold deletion, model substitution, or a second fit under the same preregistration. Any such change is a new experiment requiring a new frozen definition and threshold ratification before fitting. Non-basket-material features may be reported but receive no sign/order interpretation and do not independently fail the gate.

## Explicit exclusions

Training, fitting, scoring, cache creation, retrieval, model loading, live calls, namespace/catalog/default changes, source or test implementation, label changes or review, production ranker design, and promotion.

## Ratified checkpoint

The user explicitly confirmed this exact C7 preregistration after independent review:

> Confirm or correct this C7 preregistration: standardize each feature from the 12 training repositories before fitting; define a fold-material coefficient as `abs(w) >= ln(1.25)` and basket-material as at least `10/13` folds; require one nonzero sign in at least `12/13` folds; and require every basket-material feature pair to have the same strict-or-tied absolute-weight relation, using deadband `ln(1.10)`, in at least `10/13` folds with at most one direct reversal of a dominant strict order. Equality passes the named cutoff; `abs(w) <= 1e-12` and zero-variance/absent features do not count as sign or order agreement. Threshold failure means insufficient/overfit and no tuning or product action.

This active contract removes only C7's threshold-ratification blocker. It does not authorize fitting, scoring, cache creation, source changes, live work, or promotion; C7 remains blocked on C3 and its existing downstream product/label-confidence gates.

## References

- `.10x/tickets/2026-07-19-evaluate-lightweight-learning-to-rank.md`
- `.10x/tickets/2026-07-19-capture-current-repo-candidates-and-baselines.md`
- `.10x/tickets/done/2026-07-19-freeze-repo-ranking-experiment-contract.md`
- `.10x/tickets/done/2026-07-20-remove-buoy-internal-ranking-judgment.md`
- `.10x/evidence/2026-07-20-remove-buoy-internal-ranking-judgment.md`
- `.10x/research/2026-06-28-expanded-validation-ranking-hypotheses.md`
- `.10x/decisions/repo-ranking-promotion-policy.md`
- `.10x/reviews/2026-07-20-lightweight-learning-to-rank-stability-thresholds-review.md`
- `.10x/evidence/2026-07-20-lightweight-learning-to-rank-threshold-ratification.md`
