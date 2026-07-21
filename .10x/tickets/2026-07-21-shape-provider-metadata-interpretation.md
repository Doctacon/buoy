Status: open
Created: 2026-07-21
Updated: 2026-07-21
Parent: .10x/tickets/2026-06-28-repo-search-heavy-ranking-experiments.md
Depends-On: None

# Shape Provider Metadata Interpretation and Any Future Baseline Operation

## Outcome

Shape, without repairing or operating, the exact contract for interpreting provider namespace metadata after the consumed Approval A invocation returned `schema.vector.ann.distance_metric=cosine_distance` without a redundant top-level `distance_metric`. Identify what separately ratified specification, implementation, review, integration, preflight, and new exact operation approval would be required before any possible future baseline operation. This ticket itself grants none of those authorities.

## Scope

- Inspect only checked-in source, locked `turbopuffer==2.4.0` behavior or open-source authority available without querying the provider, the immutable execution JSON, and governing records.
- Distinguish provider-authoritative distance metadata from executor normalization or response-shape assumptions, including whether nested `schema.vector.ann.distance_metric` is the sole authoritative field and how absence, ambiguity, or conflicting nested/top-level values must fail closed.
- Shape the smallest candidate correction, deterministic no-live verification, evidence requirements, and compatibility semantics; do not implement or encode candidates in tests.
- Inventory the exact gates for any possible future new operation: explicit user ratification of the semantic contract, a separate bounded implementation ticket, independent review and protected integration, a fresh complete preflight, and a new exact single-operation approval.
- Preserve the completed invocation's raw JSON, fixed slots, effect classifications, consumed authority, lock/state-root observation, and no-compatible-baseline conclusion unchanged.

## Candidate semantics, not active behavior

The raw execution artifact is observational authority that this response contained `schema.vector.ann.distance_metric=cosine_distance` and no top-level `distance_metric`. It does not by itself ratify a general provider-metadata interpretation contract. Until shaping, independent review, and explicit user ratification are complete, all choices about nested-field authority, normalization, conflict handling, SDK-version scope, and executor repair remain unresolved candidates.

A future operation is also only a possible downstream subject. Approval A is irrevocably consumed. Unused slots cannot be reassigned or resumed. No replacement, renewed, or implied approval exists.

## Acceptance criteria

- The shaping output classifies each proposed metadata rule as raw-evidence-backed, open-source/SDK-source-observed, active-record-backed, user-ratified, or blocked.
- A user-legible confirm-or-correct checkpoint covers authoritative field location, missing/conflicting field handling, namespace-absence behavior, exact SDK/version scope, and evidence projection requirements.
- The output identifies the smallest possible implementation/test/spec change without making that change or silently treating a candidate as accepted behavior.
- Any future operation path explicitly requires its own bounded execution ticket and a new exact user approval only after ratified repair, deterministic validation, independent review, protected integration, and a fresh passing preflight.
- The original raw JSON, slots, effects, lock/state-root, and Approval A records remain byte-for-byte unchanged; no compatible baseline is claimed.
- Retry, resume, cleanup, executor invocation, provider query, Approval B, and C3 remain prohibited.

## Blockers

The authoritative general interpretation of provider metadata is not ratified. The checked-in raw response proves only the observed nested cosine field and absent top-level field. No implementation or future operation may proceed from this shaping ticket until the semantic contract is independently reviewed and explicitly ratified, and no operation may proceed without a separate new exact approval.

## Explicit exclusions

Executor/source/test/spec repair; modification of raw execution JSON, slot ledger, effects, lock/state-root, grant, plan, cache, dependency, or lockfile; credential access; model import/load/inference; provider or namespace/card/catalog query or mutation; retry, resume, cleanup, rollback, delete, recrawl/replan; Approval B; C3; compatible-baseline claim; opening or granting a new operation approval; ordinary apply/retrieval/default/promotion changes.

## Evidence expectations

A record-only shaping artifact with provenance classification, inspected open-source/SDK authority, options and tradeoffs, complete conflict/absence cases, an explicit confirm-or-correct checkpoint, independent review, and a no-operation attestation. No live evidence may be collected.

## References

- `.10x/evidence/2026-07-21-experimental-buoy-baseline-execution.md`
- `.10x/evidence/.storage/2026-07-21-experimental-buoy-baseline-execution.json`
- `.10x/reviews/2026-07-21-experimental-buoy-baseline-execution-review.md`
- `.10x/tickets/2026-07-20-source-pin-and-execute-experimental-buoy-baseline.md`
- `.10x/specs/experimental-buoy-baseline-executor.md`
- `src/buoy_search/experimental_baseline.py`

## Progress and notes

- 2026-07-21: Opened as the sole owner for provider-metadata interpretation and the prerequisites for any possible future new operation after PR #77 independent review. No repair, test, spec change, provider query, cleanup, retry, resume, new approval, Approval B, or C3 authority is implied. Approval A remains irrevocably consumed, the execution ticket remains blocked, and no compatible baseline exists.
