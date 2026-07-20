Status: blocked
Created: 2026-07-19
Updated: 2026-07-20
Parent: .10x/tickets/2026-06-28-repo-search-heavy-ranking-experiments.md
Depends-On: .10x/tickets/done/2026-07-19-freeze-repo-ranking-experiment-contract.md, .10x/tickets/2026-07-19-capture-current-repo-candidates-and-baselines.md

# C8: Reproduce and Generalize Routed Profile Selection

## Scope

After the required oracle-gap contract is pre-registered and user-ratified, use only C3's immutable shared raw-candidate cache to reproduce the documented July routed-profile formulas, then distinguish oracle/static per-repo assignment from a selector that uses only runtime-observable non-identity features and is evaluated repository-held-out.

## Required threshold checkpoint

Before selector scoring, pre-register and obtain explicit user ratification for the exact oracle-gap measure and exact minimum threshold that counts as materially closing that gap, including boundary handling. No measure or threshold may be inferred by C1 or this ticket. C1 may freeze shared schema/folds but cannot make C8 executable.

The following contract was pre-registered at commit `b9780495adfbc8ebee37be9a92525cbd4a0e9511` before a C3 cache or any future selector result existed, reviewed, and explicitly user-ratified unchanged on 2026-07-20. It is active authority for C8 and MUST NOT be changed after results are visible. A user correction requires a new committed pre-registration before any scoring. Ratification satisfies only this threshold checkpoint: C8 remains blocked and MUST NOT execute until C3 and every pre-scoring protocol prerequisite below are satisfied.

### Ratified comparison definitions

Let `R` be the exact 13-repository basket and fold order frozen by C1. All means below are equal-weight macro means over those 13 repositories; repositories and cases MUST NOT be dropped, substituted, or case-weighted. A missing or insufficient repository stops the run.

For one finite, deduplicated profile action set `P`, frozen and hashed before scoring:

- `d_r` and `q^D_r` are repository `r`'s composite score and Precision@5 under C1's current promoted default: `candidates=200`, `ranking_mode=file`, `ranking_profile=repo_code`, `ranking_pool=100`, and `ranking_aggregation=adaptive_sum_3` on the frozen compatible corpus. The historical `77.761` routed namespace/config portfolio is not this default.
- `P` MUST contain that default/no-op action and only the exact reconstructed durable profile primitives allowed by this ticket. The held-out selector and oracle MUST choose from the same `P`; no post-result arm may be added or removed.
- A safe oracle action for repository `r` is any `p in P` with `score(r,p) >= d_r - 1e-12` and `P@5(r,p) >= q^D_r - 1e-12`. The default makes this set non-empty. The oracle chooses the safe action with highest composite score, then highest Precision@5, then the default action, then ascending canonical profile ID. Score and Precision@5 values within absolute `1e-12` are ties. Call its metrics `o_r` and `q^O_r`, and call all actions tied with both oracle metrics the oracle-equivalent set `E_r`.
- The oracle may inspect held-out labels only to compute a post-hoc upper bound. It is not a deployable selector. The July `80.316` result is evidence of a static/oracle per-repository assignment selected against labels, not evidence of held-out generalization, and MUST be independently reproduced from formulas rather than copied.
- `s_r`, `q^S_r`, and `p^S_r` are the metrics and chosen action from the selector for fold `r`. That choice MUST be frozen before scoring repository `r` and may use only the other 12 repositories plus pre-registered runtime-observable, non-identity features. Repository/namespace identity, benchmark lookup, held-out cases, labels, candidates, derived aggregates, feature scaling, tuning, early stopping, and profile outcomes are forbidden selector inputs for that fold. The selector's pre-registered fallback is the default action.

### Ratified oracle-gap formula and denominator handling

For every repository:

```text
oracle_gain_r   = o_r - d_r
selector_gain_r = s_r - d_r
remaining_gap_r = o_r - s_r
```

Aggregate before taking a ratio:

```text
G_oracle   = (1 / 13) * sum_r(oracle_gain_r)
G_selector = (1 / 13) * sum_r(selector_gain_r)
G_remaining = (1 / 13) * sum_r(remaining_gap_r)

oracle_gap_closure = G_selector / G_oracle
                   = 1 - (G_remaining / G_oracle)
```

There is no per-repository ratio and no micro/case weighting. Repositories with zero oracle gain remain in both sums with zero oracle gain; they are not removed from the denominator population. The ratio is not clipped, so a negative or greater-than-one value remains visible and triggers the applicable gates rather than being hidden.

If `G_oracle <= 1e-12`, report `oracle_gap_closure = undefined_zero_gap` and record the explicit no-action outcome: the basket shows no measurable safe oracle score headroom for an automatic selector. This condition cannot pass by treating `0/0` as zero or one. If a selector from the same frozen action set reports a safe positive gain while `G_oracle <= 1e-12`, stop for an action-set, oracle, or arithmetic mismatch.

### Ratified materially-closed and stop gates

A held-out selector passes only if every gate below passes; there is no compensating trade between gates.

1. **Minimum closure:** `G_oracle > 1e-12` and `G_selector + 1e-12 >= 0.50 * G_oracle`. Equivalently, at least **50%** oracle-gap closure is required; the exact `0.50` boundary passes.
2. **Per-repository no regression:** for every repository, `s_r - d_r >= -1e-12` and `q^S_r - q^D_r >= -1e-12`.
3. **Active full-basket policy:** selector-minus-default score gain is positive on at least 3 repositories (`> 1e-12`); the equal-weight average score gain is positive (`G_selector > 1e-12`); and `max_r(max(0, selector_gain_r)) / sum_r(max(0, selector_gain_r)) <= 0.70 + 1e-12`. The denominator MUST be positive. These checks supplement rather than replace the per-repository score and Precision@5 gates above.
4. **Misselection:** report exact oracle-profile mismatches `p^S_r not in E_r`, opportunity misses where the selector uses default but default is not oracle-equivalent, and false-positive routing where the selector uses a non-default action while default is oracle-equivalent. Exact oracle-profile mismatch is diagnostic because multiple actions can be safely non-regressive without being oracle-equivalent. The stop gates are zero selector-vs-default score regressions, zero selector-vs-default Precision@5 regressions, and zero false-positive routings; any count greater than zero fails.
5. **Protocol integrity:** stop on any incomplete fold, held-out or identity leakage, post-freeze action/feature/rule/tie/fallback change, cache/hash mismatch, default replay mismatch, or inability to reproduce the historical formulas independently.

The 50% threshold is intentionally a relative recovery requirement rather than a fit to the displayed historical result. For scale only, the rounded July figures `77.761 -> 80.316` describe `2.555` points of static/oracle headroom; applying the pre-registered 50% formula to those rounded figures would require at least `1.2775` points and an average of `79.0385`. Those numbers are an arithmetic illustration, not the future denominator, a reproduced result, or permission to score before ratification and C3.

### Ratified disposition

Failure of any gate records: `automatic routed-profile selection: no action; current default unchanged; profiles remain experiment-only evidence`. It does not authorize a benchmark-repository map, selector/profile product surface, catalog or namespace change, or C9 automatic productization. Passing all gates creates held-out promotion-candidate evidence only; it still changes no product behavior and leaves the separate C9 product checkpoint in force.

## Acceptance criteria after threshold ratification

- Consume the exact frozen C3 cache/hash and validate that all 90 composite `repo_key:case_id` identities are present while dataset-local `case_id` values and labels remain unchanged. Cache joins use the composite identity. Do not issue retrieval, embedding, namespace, catalog, credential, or write calls.
- Encode the exact durable profile primitives from `.10x/evidence/2026-07-02-repo-routed-profile-portfolio-validation.md` and either reproduce them independently or declare the historical result unreproducible.
- Report separate rows for current default, oracle per-repo assignment, and a pre-registered held-out selector. Never label the historical benchmark namespace/profile map as an automatic/general selector.
- Freeze/hash selector inputs, training/selection rule, folds, seed, fallback, and tie-breaking before scoring. Repository/namespace identity and benchmark-repo hard-coding are forbidden.
- Report all 13 held-out repo score/P@5 deltas, component metrics, the oracle gap under the exact user-ratified measure, no-op rate, chosen-profile explanations, and mis-selection regressions.
- Keep gate: held-out selections pass the active full-basket distribution policy and meet the pre-registered user-ratified oracle-gap threshold. Otherwise record no action for automatic selection and retain profiles as experiment-only evidence.
- No source default, product selector/profile, CLI/config surface, namespace, or catalog is changed.

## Stop conditions

- Stop if historical formulas cannot be reconstructed from durable evidence; do not claim `80.316` by copying the result table.
- The oracle-gap measure and exact minimum materially-closed threshold checkpoint is satisfied by the unchanged ratified contract above; this does not authorize selector scoring.
- Stop before selector scoring until C3 supplies its exact immutable cache/hash and all required action-set, selector-input, fold, seed, fallback, tie-breaking, leakage, and replay protocol prerequisites are frozen and validated. Then stop on C3 replay mismatch, missing/duplicate composite identity, cache/schema drift, identity leakage, held-out policy failure, oracle-gap threshold failure, or evidence showing only oracle/static assignment.
- Do not recapture candidates, productize a benchmark map, or invent a selector surface/fallback.

## Evidence expectations

Threshold ratification provenance; cache/hash and 90-composite-identity provenance; exact formula reconstruction; frozen selector experiment definition; leakage checks; held-out results/oracle gap; deterministic rerun; policy and ratified-threshold mapping; review; explicit productization disposition.

## Blockers

- C1 is complete with Buoy explicitly insufficient; C3 remains blocked and incomplete, so no immutable shared cache/hash exists for C8.
- The threshold checkpoint is satisfied by the unchanged user-ratified oracle-gap measure, inclusive 50% materially-closed threshold, and stop gates above. It is no longer a blocker and does not make C8 executable.
- C8 remains blocked on C3 and its frozen-cache, complete-basket, default-replay, action-set, selector-input, fold, seed, fallback, tie-breaking, and leakage prerequisites. Product semantics remain intentionally deferred to C9.

## Explicit exclusions

Live calls/writes; source/product implementation; static benchmark map as generalization; public selector/profile surface; catalog/default changes; promotion.

## References

- `.10x/research/2026-07-19-repo-search-heavy-ranking-experiment-decomposition.md`
- `.10x/tickets/2026-07-19-capture-current-repo-candidates-and-baselines.md`
- `.10x/evidence/2026-07-01-repo-portfolio-routing-validation.md`
- `.10x/evidence/2026-07-02-repo-routed-profile-portfolio-validation.md`
- `.10x/decisions/repo-ranking-promotion-policy.md`
- `.10x/evidence/2026-07-20-c8-selector-threshold-ratification.md`
- `.10x/reviews/2026-07-20-c8-selector-threshold-preregistration-review.md`

## Progress and notes

- 2026-07-19: Opened as an offline dependency-gated child. No selector semantics, profile surface, cache, source, tests, live operations, or promotion were created.
- 2026-07-20: Marked explicitly blocked because an oracle-gap measure/threshold was never pre-registered or user-ratified; C1 completion alone cannot activate this child.
- 2026-07-20: C1 closed with Buoy explicitly insufficient. C8 remains blocked on C3 and its independent oracle-gap ratification; no selector scoring was authorized.
- 2026-07-20: Before C3 cache availability or future selector results, pre-registered for user ratification an equal-repository safe-oracle score-gap formula, explicit zero-gap handling, a 50% inclusive minimum closure threshold, active-policy/no-regression/false-positive-misselection stop gates, and an automatic-selection no-action outcome. C8 remains blocked; no source, tests, cache, formulas execution, live calls, or product/default state changed.
- 2026-07-20: The user explicitly ratified the reviewed pre-registration at `b9780495adfbc8ebee37be9a92525cbd4a0e9511` exactly as written. The formula, denominator/boundary handling, gates, and disposition are unchanged and now active C8 authority. Only the threshold blocker was removed: C8 remains blocked on C3/cache and all pre-scoring protocol prerequisites, and C9 remains separately blocked. Evidence: `.10x/evidence/2026-07-20-c8-selector-threshold-ratification.md`; review: `.10x/reviews/2026-07-20-c8-selector-threshold-preregistration-review.md`.
