Status: blocked
Created: 2026-07-19
Updated: 2026-07-20
Parent: .10x/tickets/2026-06-28-repo-search-heavy-ranking-experiments.md
Depends-On: .10x/tickets/done/2026-07-19-freeze-repo-ranking-experiment-contract.md, .10x/tickets/2026-07-19-capture-current-repo-candidates-and-baselines.md

# C7: Evaluate Lightweight Learning to Rank

## Scope

After the required thresholds are pre-registered and user-ratified, fit and evaluate one transparent lightweight ranker entirely offline from C3's immutable shared raw-candidate cache and the existing assistant-drafted graded paths. Use repository-held-out validation; do not query or write namespaces again.

## Required threshold checkpoint

Before fitting or scoring, pre-register and obtain explicit user ratification for:

- the exact definition that makes a learned weight "material";
- the exact permitted sign-stability behavior across held-out folds;
- the exact permitted order-stability behavior across held-out folds; and
- how threshold equality and folds with absent/zero weights are handled.

No threshold, sign rule, order rule, or materiality value may be inferred by C1 or this ticket. C1 may freeze shared schema/folds but cannot make C7 executable.

## Acceptance criteria after threshold ratification

- Consume the exact frozen C3 cache/hash and C1 folds, and validate that all 90 composite `repo_key:case_id` identities are present while the dataset-local `case_id` and labels remain unchanged. Cache joins use the composite identity. No retrieval, embedding, namespace, catalog, or credential call occurs.
- Before fitting, freeze/hash the feature definitions, label transformation, splits, normalization/scales, seed, model form, and tie-breaking.
- Candidate features are limited to retrieval-time-observable signals from the cache/current scorer, such as ANN/BM25/RRF rank/score, file hit count, path role, filename/query overlap, path-token overlap, available Python symbol overlap, and current `repo_code` multiplier components.
- Repository/namespace identity, eval-case ID, answer text, hand-selected per-repo weights, and any held-out repo outcomes are forbidden features.
- Each repository is scored only by a model trained on the other 12 repositories; report fold membership and prove no leakage.
- Replay the current default from the same candidates. Publish fold weights, feature scales, all 13 held-out repo score/P@5 deltas, component metrics, and results against the exact user-ratified material-weight/sign/order thresholds.
- Keep gate is the active full-basket distribution policy plus the pre-registered user-ratified C7 thresholds. Otherwise classify the result as insufficient/overfit.
- A pass is experiment evidence only. Default promotion remains blocked pending the later label-confidence checkpoint and a separate product owner.

## Stop conditions

- Stop before fitting/scoring until the material-weight/sign/order definitions and exact thresholds are pre-registered and user-ratified.
- After ratification, stop on C3 replay mismatch, missing/duplicate composite identity, cache/schema drift, label leakage, fewer than 12 training repos in a fold, repository identity dependence, any repo score/P@5 regression, or failure of the ratified thresholds.
- Do not recapture candidates or issue live calls to repair an offline result.
- Do not add a runtime dependency or production ranking surface under this ticket.

## Evidence expectations

Threshold ratification provenance; cache/hash and 90-composite-identity provenance; frozen experiment definition; leakage checks; fold results/weights/scales; deterministic rerun; active-policy and ratified-threshold mapping; review; explicit experiment-only conclusion.

## Blockers

- C1 is complete with Buoy explicitly insufficient; C3 remains blocked and incomplete.
- The definition of a material weight and exact sign/order stability thresholds are not pre-registered or user-ratified.
- C1 cannot infer these values or make C7 executable. The labels remain assistant-drafted and non-product-ratifying.

## Explicit exclusions

Live calls/writes; label review/editing; repository identity features; production ranker implementation; selector/catalog/default changes; promotion.

## References

- `.10x/research/2026-07-19-repo-search-heavy-ranking-experiment-decomposition.md`
- `.10x/tickets/done/2026-07-19-freeze-repo-ranking-experiment-contract.md`
- `.10x/tickets/2026-07-19-capture-current-repo-candidates-and-baselines.md`
- `.10x/decisions/repo-ranking-promotion-policy.md`

## Progress and notes

- 2026-07-19: Opened as an offline dependency-gated child. No features, labels, model weights, cache, source, tests, or product behavior were created.
- 2026-07-20: Marked explicitly blocked because material-weight/sign/order thresholds were never pre-registered or user-ratified; C1 completion alone cannot activate this child.
- 2026-07-20: C1 closed with Buoy explicitly insufficient. C7 remains blocked on C3 and its independent threshold ratification; no fitting or scoring was authorized.
