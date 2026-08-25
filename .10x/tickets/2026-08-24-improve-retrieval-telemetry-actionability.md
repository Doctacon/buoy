Status: active
Created: 2026-08-24
Updated: 2026-08-24
Parent: None
Depends-On: None
Authorization: .10x/evidence/2026-08-24-provider-client-invocation-receipt-authorization.md
Decision: .10x/decisions/buoy-uses-private-canary-provider-invocation-receipts.md
Accounting: .10x/specs/provider-client-invocation-accounting.md
Lifecycle: .10x/specs/provider-client-invocation-receipt.md
Implementation-Plan: .10x/tickets/2026-08-24-implement-private-provider-invocation-receipts.md
Contract-Review: .10x/reviews/2026-08-24-provider-client-invocation-contract-review.md

# Improve Retrieval Telemetry Actionability

## Aggregate outcome

Turn the completed `v0.6.3` production-style telemetry findings into two
truthful, bounded outcomes: explain the dominant command time outside the nested
pipeline, then define privacy-safe Buoy SDK call-attempt accounting without
conflating it with unresolved physical wire, provider-cost, or rate-limit use.

## Child sequence

1. `.10x/tickets/done/2026-08-24-investigate-retrieve-command-outer-latency.md`
   performs read-only attribution from existing evidence first. Any new live
   measurement requires a separate owner checkpoint.
2. `.10x/tickets/2026-08-24-define-physical-provider-attempt-accounting.md`
   starts only after the latency investigation reaches a reviewed conclusion.
   It inspected source, shaped options, and now owns the explicitly ratified
   records/specification graph pending independent review. Its separate
   implementation plan remains open and non-executable.

The children are sequential. Neither child grants provider/model operations,
telemetry mutation, implementation, migration, release, or global-tool change.

## Integration and coherence

- The latency child must distinguish measured stage time from unmeasured command
  residual and must not turn three production samples into a distribution.
- The attempt-accounting child must preserve the distinction among logical
  namespace operations, Buoy SDK call attempts (`provider_client_invocation`),
  and unresolved physical wire sends/provider accounting.
- Findings, source authority, and unresolved choices must be durable before the
  next child advances.
- The ratified implementation outcome is governed by two focused active specs
  and a separate open non-executable parent with four bounded open/inactive
  children. No implementation child activates under this shaping parent.

## Aggregate acceptance criteria

- The first child has independently reviewed research that either attributes the
  existing latency gap or precisely defines the missing observation boundary.
- The second child records a source-complete, owner-ratified privacy-safe
  contract with explicit product-surface, lifecycle, and retention choices, and
  receives independent review before implementation may activate.
- No external operation or source mutation occurs under the parent plan.
- Child statuses, evidence/research, reviews, dependencies, and follow-ups are
  coherent at closure.

## Progress and notes

- 2026-08-24: The owner directed execution of the two existing tickets in the
  recommended order. This authorizes the first child's existing read-only
  analysis. It does not silently ratify new live samples or the second child's
  unresolved persistence/product-surface semantics.
- 2026-08-24: Child 1 produced a records-only research candidate from all seven
  retained command-v2 rows. The coarse gap is attributable to prepare; no new
  live measurement is recommended before provider-free sub-boundary
  attribution. Independent child review is pending before child 2 may start.
- 2026-08-24: Independent review passed child 1 at exact candidate
  `8fe2b06ed907460c2858f6e3779bc29e56c657ef`. The child moved to `done`; its
  recommended model/client sub-boundary is separately owned by blocked ticket
  `.10x/tickets/2026-08-24-measure-provider-free-retriever-construction.md`.
  Child 2 may now perform source-only shaping. No product-surface, persistence,
  retention, implementation, provider, model, or telemetry authority is implied.
- 2026-08-24: Child 2 completed source-only attempt-path and product-surface
  shaping in
  `.10x/research/2026-08-24-physical-provider-attempt-accounting-options.md`.
  The candidate recommends counting Buoy SDK call attempts immediately before
  call-expression evaluation in a canary-only sanitized terminal receipt, with
  content and catalog families separate. Exact wire sends, provider cost, and
  rate-limit usage remain unprovable at that boundary. Child 2 stays blocked
  pending owner decisions and independent review of this candidate.
- 2026-08-24: Independent review run
  `f17899d7-59f5-43c0-b8f9-66e68f844887` returned FAIL on catalog failure
  cardinality, CLI-versus-generic fanout, method-entry wording, and wire-unit
  overstatement. The records-only candidate was repaired to record 40,001
  successful/40,002 terminal-failure catalog bounds, explicit-multi CLI 2..3
  versus generic 1..3 fanout, increment-before-call-expression semantics, and
  the non-wire `provider_client_invocation` unit. Child 2 remains blocked and
  requires fresh independent review.
- 2026-08-24: Independent rereview
  `e91d4f44-e594-4d62-a282-d63236cd0581` passed repaired child 2 commit
  `0ed20c4d2d68a4a823f689b372095e777a48d459`; the historical FAIL remains
  truthful and all four findings are repaired. The minor candidate-surface
  wording now reflects that active v2 is exact/non-extensible: recurring
  production telemetry is possible only under a separately specified
  compatible schema. Child 2 remained blocked on exactly five owner decisions
  at that checkpoint.
- 2026-08-24: The owner explicitly ratified the complete reviewed package and a
  default-off private in-process activation/delivery scope. Exact authorization,
  one active ADR, two active focused specifications, and an open implementation
  graph now record the contract. The accounting spec owns both separate family
  shapes because they share one call-attempt unit/outcome boundary; the lifecycle
  spec independently owns private activation, finalization, canonical handoff,
  authority, privacy, and retention. The implementation parent is
  non-executable; its core, content, catalog, and integrated-validation children
  are open/inactive. Child 2 and this parent remain active pending independent
  review of the exact records-only commit. No source/test or operational work
  ran.
- 2026-08-24: Independent run
  `29dbeef6-82a2-43b1-8fd3-b572f0d83f40` failed the contract candidate on
  aggregate catalog source-order validation, exact interruption precedence,
  and shared-reader activation containment. The repaired active specs now make
  the catalog aggregate state machine regeneration-grade, classify both
  cancellation classes and all remaining non-`Exception` `BaseException`
  values exactly, and require default-null explicit catalog observation from
  automatic retrieve only. The integration child also owns frozen schema-v3
  CLI receipt recertification. Both shaping tickets remain active and all
  implementation tickets open/inactive pending fresh rereview. No source/test
  or operational work ran.

## Blockers

- Independent review `29dbeef6-82a2-43b1-8fd3-b572f0d83f40` failed candidate
  `a458aeba95844230271ad50d4364281f4462ad5e`; fresh rereview of the repaired
  records-only contract is pending.
- No implementation child may activate or execute until that rereview passes
  and the selected child is explicitly activated. The parent remains active
  until review and child-2 shaping coherence are recorded.
