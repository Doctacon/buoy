Status: open
Created: 2026-08-24
Updated: 2026-08-24
Parent: .10x/tickets/2026-08-24-implement-private-provider-invocation-receipts.md
Depends-On: .10x/tickets/2026-08-24-implement-private-provider-invocation-receipt-core.md
Decision: .10x/decisions/buoy-uses-private-canary-provider-invocation-receipts.md
Accounting: .10x/specs/provider-client-invocation-accounting.md
Lifecycle: .10x/specs/provider-client-invocation-receipt.md
Prior-Review: .10x/reviews/2026-08-24-provider-client-invocation-contract-review.md
Review: .10x/reviews/2026-08-24-provider-client-invocation-contract-rereview.md

# Instrument Content Provider Invocations

## Outcome

Instrument exact content logical-operation and `namespace.multi_query`
call-expression boundaries so the private ledger records route-rank-only
fallback-aware attempts while disabled and observer-fault behavior remains
call-equivalent.

## Scope

- Register route rank 1 around the existing explicit-single
  `HybridRetriever.retrieve` content operation and each existing route rank
  around `MultiNamespaceRetriever._retrieve_target`.
- Pass only mechanical request form/trigger information needed by the private
  observer into the exact server-RRF and client-RRF expressions in
  `run_multi_query`.
- Compose receipt-ledger propagation with the existing Buoy private worker
  callable seam without copying ambient context or changing telemetry state.
- Finalize logical operation outcomes across success, ordinary error,
  cancellation/control-flow interruption, zero-attempt pre-call failure, and
  post-response failure.
- Add focused local-fake tests for exact attempt sequences, fanout, concurrency,
  propagation, and observer-fault equivalence.

## Acceptance criteria

- One server-RRF call produces one attempt; unsupported local signature
  `TypeError` plus client fallback produces two, including the pre-method-entry
  first attempt.
- One/two optional-schema removals, with and without client-RRF fallback, produce
  the exact 1..6 sequence grammar; unrelated error adds no retry.
- Explicit single uses route 1; CLI 2/3-route and generic/automatic 1..3-route
  operation sets serialize deterministically with at most 18 attempts.
- Top-1 stop, empty/failed widening, missing reranker before later calls,
  partial/all failure, zero-attempt begun operation, post-response error, and
  interruption preserve existing outcomes and exact reached counts.
- A governed content expression reached without a registered logical operation
  invalidates only the receipt and still runs unchanged.
- Disabled and every injected observer/propagation fault preserve original call
  arguments/count/order, fallback classification, results, identical
  exceptions, thread behavior, routing, output, and telemetry.
- Tests use fakes only and inspect receipt bytes for absence of query, namespace,
  content, path, provider detail, and raw error sentinels.

## Evidence expectations

Record exact commit/tree; targeted retriever and multi-namespace fake-test
commands/output; call-sequence, concurrency, privacy, and fault-injection
results; and focused diff/stat. State explicitly that no provider/network/model/
store/credential/canary operation ran.

## Explicit exclusions

Catalog instrumentation, core model changes beyond a separately reviewed defect,
CLI/env/public activation, automatic persistence, telemetry-v2 modification,
provider/model/network/canary operation, routing/ranking behavior change,
generic retry, release, and global-tool changes are excluded.

## Blockers

The governing contract has independent PASS rereview at
`.10x/reviews/2026-08-24-provider-client-invocation-contract-rereview.md`.
The core child must still be done at a reviewed exact commit, and this child
must be explicitly activated before execution. Ticket remains open/inactive.

## Progress and notes

- 2026-08-24: Opened fully specified but inactive. Existing source/tests were
  inspected only for shaping; no implementation or test execution occurred.
- 2026-08-24: PASS rereview
  `a4331cfc-d12b-4209-8e5a-8cb66655cf76` accepted exact repaired contract
  commit `cb4a76b97f68fcdfc2816c49c33b5b23e9b5f899`. Contract review is no longer
  a blocker; the reviewed-core dependency and explicit-activation gate remain.
  Ticket stays open/inactive, and no implementation or validation ran.
