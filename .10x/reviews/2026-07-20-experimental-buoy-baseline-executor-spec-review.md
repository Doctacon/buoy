Status: recorded
Created: 2026-07-20
Updated: 2026-07-20
Target: PR #65 draft executor contract at commit `539f32c236a6c1179cdcfed958f33e19c75a2579`
Verdict: pass

# Experimental Buoy Baseline Executor Specification Review

## Target and method

Independent adversarial review of `.10x/specs/experimental-buoy-baseline-executor.md` as committed at PR #65 head `539f32c`. The reviewed file SHA-256 is `2511b6908727d0e3f5a2f6dfc28885beacd9b0af9abbcc4a0f1d9075634364d6`.

The review compared the contract with the retained-plan and current-source findings in `.10x/evidence/2026-07-20-c3-buoy-baseline-approval-checkpoint.md`, the C1 freeze, current apply/catalog/pending/applied-state boundaries, the locked `turbopuffer==2.4.0` dependency, C3's approval gate, and the exact arithmetic and phase ordering in the draft. It reviews only the specification, not an implementation or live operation.

## Findings

- The operation is bound to one exact region, retained plan/artifact/source, target namespace, 903-row corpus, immutable MIT model revision/cache/README, catalog namespace/card, and plan-bound local state. Re-crawl, re-plan, substitution, other resources, retrieval, defaults, promotion, and deletes are excluded.
- Preconditions are ordered before credential access and model/provider construction: exact local identities, 903 unique row IDs, no active/retained target ledger rows, no stale/delete intent, offline controls, and immutable cache/license validation must all pass first.
- Every provider resource uses the locked SDK with `max_retries=0`. SDK/wrapper retries, signature/schema fallback, unbounded pagination, repeated calls, and reassignment of unused request slots are forbidden.
- The pre-write target and catalog checks are fail-closed. Absence must be unambiguous; otherwise exact schema/distance plus a bounded empty probe is required. Any target row, incompatible state, unstable card, ambiguous response, or inability to prove the bounded state stops writes.
- The request ledger arithmetic is internally consistent: 10 reads plus 16 writes equals 26 physical attempts; 15 content writes cover exactly `14 × 64 + 7 = 903` rows; the conditional card write raises maximum write-row exposure to 904; and bounded read positions total `1 + 4 + 1,808 + 4 = 1,817`.
- Accounting is appended before each physical attempt and retained through failed or indeterminate outcomes. Exact or explicitly absent `rows_affected` and billing markers, status, returned-row counts, operation/global numbering, and cumulative ceilings are required without persisting secrets or raw requests.
- Successful write responses are not enough. Two bounded target reads must independently and stably prove the exact 903 IDs, attributes, vectors, schema, and distance before the card write; two exact-card reads must then prove the complete stable revision before the 903-row DuckDB applied-state commit and pending-record removal.
- Failure ordering is conservative and explicit: content mismatch prevents catalog/local-state commit; catalog mismatch prevents local-state/card-success commit; partial effects remain pending for reconciliation; no retry, rollback delete, cleanup delete, or success claim is permitted.
- Evidence after any separately approved run must map all 26 slots and preserve exact provider/accounting, remote identity, local-state, zero-delete, and partial-effect observations. Unknown dollar pricing remains unknown rather than being inferred from request counts.

### Blockers

None for specification ratification or for opening a bounded source/test implementation ticket.

## Verdict

PASS. The draft is precise, internally consistent, fail-closed, and sufficiently complete to activate unchanged as the behavioral contract for a separately reviewed implementation. Activation does not grant Approval A, Approval B, credential/model/provider access, baseline execution, C3 retrieval, or any remote/local domain mutation.

## Residual risk

- No executor exists yet, so the SDK retry setting, attempt interception, response accounting, bounded reads, exact comparisons, and commit ordering are unimplemented and untested.
- No remote namespace/card/account state or provider response shape was inspected by this review.
- The retained `/tmp` plan and immutable cache must still be present and revalidated at any later approved execution.
- Independent implementation review and separately granted Approval A remain mandatory before baseline execution. C3 remains blocked, and Approval B remains separate and ungranted.
