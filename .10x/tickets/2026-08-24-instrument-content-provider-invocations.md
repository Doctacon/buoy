Status: active
Created: 2026-08-24
Updated: 2026-08-24
Parent: .10x/tickets/2026-08-24-implement-private-provider-invocation-receipts.md
Depends-On: .10x/tickets/done/2026-08-24-implement-private-provider-invocation-receipt-core.md
Decision: .10x/decisions/buoy-uses-private-canary-provider-invocation-receipts.md
Authorization-Evidence: .10x/evidence/2026-08-24-provider-client-invocation-receipt-authorization.md, .10x/evidence/2026-08-24-provider-invocation-probe-and-live-canary-authorization.md
Accounting: .10x/specs/provider-client-invocation-accounting.md
Lifecycle: .10x/specs/provider-client-invocation-receipt.md
Prior-Review: .10x/reviews/2026-08-24-provider-client-invocation-contract-review.md
Review: .10x/reviews/2026-08-24-provider-client-invocation-contract-rereview.md
Activation-Review: .10x/reviews/2026-08-24-provider-invocation-execution-activation-review.md

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
The core dependency is satisfied by its done ticket at independently reviewed
source commit `8953e9336354f2a2e0604a54be9cd882a97a7985`, tree
`66fb2d0dcca5d397132f60eb0be6d22a5b69479b`. This child must still be
explicitly activated in a later turn before execution. Ticket remains
open/inactive.

## Progress and notes

- 2026-08-24: Opened fully specified but inactive. Existing source/tests were
  inspected only for shaping; no implementation or test execution occurred.
- 2026-08-24: PASS rereview
  `a4331cfc-d12b-4209-8e5a-8cb66655cf76` accepted exact repaired contract
  commit `cb4a76b97f68fcdfc2816c49c33b5b23e9b5f899`. Contract review is no longer
  a blocker; the reviewed-core dependency and explicit-activation gate remain.
  Ticket stays open/inactive, and no implementation or validation ran.
- 2026-08-24: Independent activation review passed exact authorization commit
  `21f6a7b21d950f086ac6dfd7ab4f633883d6e066`, tree
  `4d044b44d492757dad80466968809aebdb76f161`, with no findings. This child
  remains open/inactive behind independently reviewed core; no implementation
  or operation ran.
- 2026-08-24: Core dependency satisfied by
  `.10x/tickets/done/2026-08-24-implement-private-provider-invocation-receipt-core.md`
  at reviewed source commit `8953e9336354f2a2e0604a54be9cd882a97a7985`,
  tree `66fb2d0dcca5d397132f60eb0be6d22a5b69479b`. This child remains
  open/inactive pending separate explicit activation; no content source/test or
  operational work ran in the records-only core closure.
- 2026-08-24: Owner explicitly activated only this content child for
  implementation from clean HEAD `54a19f705c7bccd1ee50b27485bda6ec30db1361`.
  Content source/test work has not begun; catalog, integration, and operational
  children remain inactive and excluded.
- 2026-08-24: Implemented route-rank content operation registration at exact
  `HybridRetriever.retrieve` and `MultiNamespaceRetriever._retrieve_target`
  boundaries, exact server/client `namespace.multi_query` expression
  observation, optional-schema trigger threading, and receipt-only worker lease
  composition with the unchanged private telemetry callable. Added 23 local-
  fake content tests covering exact 1..6 grammar, one/two schema removals,
  1..3 routes and 18 attempts, CLI explicit multi, automatic top-1/widening,
  reranker pre-call stops, partial/all failure, concurrency, privacy,
  cancellation/control flow, and observer/submission/bind/reset/lease faults.
- 2026-08-24: Execution proved one blocking reviewed-core defect allowed by this
  ticket's exclusion boundary: a final `concurrent.futures.CancelledError`
  attempt was interrupted, but pre-existing `HybridRetriever` wrapping made the
  outer exception an error and therefore made the receipt invalid. Supervisor
  approved the minimal spec-required repair: exceptional operation completion
  now prefers an already recorded final interrupted attempt while every other
  outer-exception classification is unchanged. Focused regression proves the
  caller still receives the existing sanitized `ProviderCallError` behavior
  and exception chain while the authoritative attempt/operation are both
  interrupted; unrelated errors remain errors.
- 2026-08-24: Final credential-removed, telemetry-disabled, strict-offline
  validation passed core+content 68/68 on Python 3.11 and 68/68 on Python 3.13,
  retriever+multi 57/57, local retrieval telemetry 15/15, both frozen-contract
  validators, AST exact-boundary/context-copy inspection, `git diff --check`,
  and generated-version cleanup. Tests used local fakes only. No provider,
  network, credential, model, content store, telemetry store, database,
  persistence, canary, catalog, routing/ranking, release, or global-tool
  operation ran. Ticket remains active pending independent content review.
