Status: open
Created: 2026-08-24
Updated: 2026-08-24
Parent: .10x/tickets/2026-08-24-implement-private-provider-invocation-receipts.md
Depends-On: .10x/tickets/2026-08-24-implement-private-provider-invocation-receipt-core.md
Decision: .10x/decisions/buoy-uses-private-canary-provider-invocation-receipts.md
Accounting: .10x/specs/provider-client-invocation-accounting.md
Lifecycle: .10x/specs/provider-client-invocation-receipt.md
Review: .10x/reviews/2026-08-24-provider-client-invocation-contract-review.md

# Instrument Catalog Provider Invocations

## Outcome

Instrument automatic retrieval's exact strong catalog-read operation and SDK
call expressions so the private ledger emits only aggregate category/outcome
counts with correct terminal 40,001/40,002 validation semantics.

## Scope

- Add one private observer/ledger keyword to `read_remote_catalog`, defaulting
  to `None`, and propagate only that explicit value through `_list_namespaces`,
  metadata observation, and `_read_card_pass`. Shared reader/helpers MUST NOT
  inspect receipt `ContextVar` state.
- Register/finalize the strong-read operation only when that explicit observer
  is non-null. Keep apply, catalog-management, direct-library, and all existing
  callers unobserved by their unchanged/default-`None` calls, even inside an
  active receipt scope.
- Observe both initial `client.namespaces(...)` calls and each reached
  `page.get_next_page()` as `namespace_list_page`.
- Observe the one reached `resource.metadata()` as `metadata` and each reached
  `resource.query(...)` in both card passes as `card_query_page`.
- Preserve `_call` sanitization, strong-read duplication, pagination order and
  bounds, normalization, fail-closed behavior, and automatic preview/live
  behavior.
- Add focused local-fake tests for aggregate counts, exact ordered-stage
  prerequisites, per-category maxima, interruption/error identity,
  post-return failure, default-`None` isolation, and observer faults. Do not wire
  the automatic-retrieve CLI in this child; that final source-receipt change is
  owned by the integration child.

## Acceptance criteria

- A minimum complete one-page strong read records five successful invocations:
  two list, one metadata, and two card query.
- Multipage list/card fakes record exact category/outcome aggregates across both
  passes without retaining pass, stage, cursor, namespace, card, response,
  billing, or error detail.
- Boundary tests prove successful list 2..20,000, metadata exactly 1, and card
  2..20,000; terminal list <=20,001, metadata <=1, and card <=20,000.
- Table tests reject metadata/card without completed L1, list >10,000 without
  successful metadata and two completed successful card passes, metadata/card
  terminal calls followed by later-stage evidence, mixed terminal calls,
  impossible pass decompositions, and every adjacent overflow.
- A successful operation validates through 40,001 and rejects 40,002. The
  all-success 40,002 terminal validates only at list=20,001, metadata=1,
  card=20,000; every other 40,002 composition and every higher total reject.
- SDK expression error/interruption counts once and stops the read; local
  post-return/normalization/bound error or interruption changes operation
  outcome without fabricating an invocation failure. Focused fakes prove both
  cancellation classes and representative control-flow/ordinary exceptions
  re-raise the identical object with exact outcome precedence.
- Client construction, `client.namespace(...)`, response processing,
  eligibility, management, and mutation calls count zero.
- Default-`None`, active-scope-without-argument, and injected observer faults
  preserve exact SDK arguments/count/order, original results/exceptions,
  strong-read and pagination behavior, preview/live behavior, output, and
  telemetry. A directly passed private fake observer is the only test path that
  records calls in this child.
- All tests use local fakes and exact receipt-byte privacy sentinels.

## Evidence expectations

Record exact commit/tree; targeted remote-catalog fake-test commands/output;
conditional-bound, privacy, interruption, and observer-fault results; and
focused diff/stat. State explicitly that no provider/network/model/store/
credential/canary operation ran.

## Explicit exclusions

Content instrumentation, catalog management/write accounting, core model
changes beyond a separately reviewed defect, CLI/env/public activation,
automatic persistence, telemetry-v2 modification, provider/network/canary
operation, pagination behavior change, release, and global-tool changes are
excluded.

## Blockers

The core child must be done at a reviewed exact commit, the governing contract
must have independent PASS review, and this child must be explicitly activated
before execution.

## Progress and notes

- 2026-08-24: Opened fully specified but inactive. Existing source/tests were
  inspected only for shaping; no implementation or test execution occurred.
- 2026-08-24: FAIL review `29dbeef6-82a2-43b1-8fd3-b572f0d83f40`
  proved the aggregate validator and shared-reader activation boundary were
  under-specified. Scope/tests now require exact ordered aggregate validation
  and an explicit default-`None` observer propagated through read helpers. CLI
  wiring remains excluded here and owned by integration. Ticket stays
  open/inactive pending repaired-contract rereview.
