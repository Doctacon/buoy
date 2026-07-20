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
- Stop before selector scoring until the oracle-gap measure and exact minimum materially-closed threshold are pre-registered and user-ratified.
- After ratification, stop on C3 replay mismatch, missing/duplicate composite identity, cache/schema drift, identity leakage, held-out policy failure, oracle-gap threshold failure, or evidence showing only oracle/static assignment.
- Do not recapture candidates, productize a benchmark map, or invent a selector surface/fallback.

## Evidence expectations

Threshold ratification provenance; cache/hash and 90-composite-identity provenance; exact formula reconstruction; frozen selector experiment definition; leakage checks; held-out results/oracle gap; deterministic rerun; policy and ratified-threshold mapping; review; explicit productization disposition.

## Blockers

- C1 is complete with Buoy explicitly insufficient; C3 remains blocked and incomplete.
- The oracle-gap measure and exact minimum materially-closed threshold are not pre-registered or user-ratified.
- C1 cannot infer these values or make C8 executable. Product semantics remain intentionally deferred to C9.

## Explicit exclusions

Live calls/writes; source/product implementation; static benchmark map as generalization; public selector/profile surface; catalog/default changes; promotion.

## References

- `.10x/research/2026-07-19-repo-search-heavy-ranking-experiment-decomposition.md`
- `.10x/tickets/2026-07-19-capture-current-repo-candidates-and-baselines.md`
- `.10x/evidence/2026-07-01-repo-portfolio-routing-validation.md`
- `.10x/evidence/2026-07-02-repo-routed-profile-portfolio-validation.md`
- `.10x/decisions/repo-ranking-promotion-policy.md`

## Progress and notes

- 2026-07-19: Opened as an offline dependency-gated child. No selector semantics, profile surface, cache, source, tests, live operations, or promotion were created.
- 2026-07-20: Marked explicitly blocked because an oracle-gap measure/threshold was never pre-registered or user-ratified; C1 completion alone cannot activate this child.
- 2026-07-20: C1 closed with Buoy explicitly insufficient. C8 remains blocked on C3 and its independent oracle-gap ratification; no selector scoring was authorized.
