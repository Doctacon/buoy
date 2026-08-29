Status: done
Created: 2026-08-24
Updated: 2026-08-24
Parent: .10x/tickets/done/2026-08-24-implement-private-provider-invocation-receipts.md
Depends-On: .10x/tickets/done/2026-08-24-implement-private-provider-invocation-receipt-core.md
Decision: .10x/decisions/superseded/buoy-uses-private-canary-provider-invocation-receipts.md
Authorization-Evidence: .10x/evidence/2026-08-24-provider-client-invocation-receipt-authorization.md, .10x/evidence/2026-08-24-provider-invocation-probe-and-live-canary-authorization.md
Accounting: .10x/specs/provider-client-invocation-accounting.md
Lifecycle: .10x/specs/provider-client-invocation-receipt.md
Prior-Review: .10x/reviews/2026-08-24-provider-client-invocation-contract-review.md
Contract-Review: .10x/reviews/2026-08-24-provider-client-invocation-contract-rereview.md
Activation-Review: .10x/reviews/2026-08-24-provider-invocation-execution-activation-review.md
Evidence: .10x/evidence/2026-08-24-provider-invocation-receipt-catalog-closure.md
Review: .10x/reviews/2026-08-24-provider-invocation-receipt-catalog-review.md
Reviewed-Source: commit d9399e86e121e00f403f5f3a1d674f70c2d75aa4, tree 1359284ad942224c6873ca810f7de93fd188ad9c

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

None.

## Progress and notes

- 2026-08-24: Opened fully specified but inactive. Existing source/tests were
  inspected only for shaping; no implementation or test execution occurred.
- 2026-08-24: FAIL review `29dbeef6-82a2-43b1-8fd3-b572f0d83f40`
  proved the aggregate validator and shared-reader activation boundary were
  under-specified. Scope/tests now require exact ordered aggregate validation
  and an explicit default-`None` observer propagated through read helpers. CLI
  wiring remains excluded here and owned by integration. Ticket stays
  open/inactive pending repaired-contract rereview.
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
  open/inactive pending separate explicit activation; no catalog source/test or
  operational work ran in the records-only core closure.
- 2026-08-24: Owner explicitly activated only this catalog child for
  implementation from clean HEAD `9273afe0a5ff8495c48a2ffa057e2240d128a57c`.
  Catalog source/test work has not begun; integration, CLI wiring, and
  operational children remain inactive and excluded.
- 2026-08-24: Implemented the one private default-`None` catalog observer
  keyword and propagated only its explicit operation capability through the
  two namespace-list passes, metadata expression, and both card-query passes.
  Observation wraps only initial/continuation list, metadata, and card-query SDK
  expressions; source order, `_call` sanitization, strong duplication,
  pagination, caller defaults, and all processing remain unchanged. Added 12
  focused local-fake tests covering minimum/multipage aggregates, exhaustive
  conditional bounds and ordered prerequisites, 40,001/40,002, SDK and local
  terminal outcomes, both cancellation classes, control-flow identity,
  observer faults, default/active-scope isolation, exact bytes, and caller
  containment.
- 2026-08-24: Execution proved one blocking reviewed-core defect allowed by
  this ticket's exclusion boundary. A catalog SDK
  `concurrent.futures.CancelledError` was recorded as an interrupted invocation,
  but existing `_call` sanitization made the outer exception a
  `RemoteCatalogError`, so catalog operation completion incorrectly became
  `error` and invalidated the receipt. Supervisor approved the mirrored minimal
  repair: exceptional catalog completion now prefers an already recorded
  interrupted invocation; all other outer-exception classification and caller-
  visible sanitization remain unchanged. Focused regression proves the receipt
  is authoritative interrupted while caller type/message behavior is baseline-
  equivalent and unrelated ordinary errors remain error.
- 2026-08-24: Final credential-removed, telemetry-independent strict-offline
  validation passed remote-catalog plus core/content/catalog receipt tests
  130/130 on Python 3.13 and 130/130 on Python 3.11, exact AST/default/caller/
  source-order static checks, both frozen-contract validators, and
  `git diff --check`. Tests used local fakes; generated version and isolated
  environment artifacts were removed. No provider, network, credential, model,
  catalog/content operation, store, telemetry, database, persistence, canary,
  CLI wiring, routing, release, or global-tool operation ran. Ticket remains
  active pending independent review.
- 2026-08-24: Independent review passed exact source commit
  `d9399e86e121e00f403f5f3a1d674f70c2d75aa4`, tree
  `1359284ad942224c6873ca810f7de93fd188ad9c`, with no blocker or required
  repair. Focused closure evidence maps all nine acceptance criteria, including
  the approved transformed-cancellation core defect; confirms both active specs
  remain coherent; preserves the historical contract FAIL and repair lineage;
  and records the no-rerun/raw-output limit. This records-only closure preserves
  reviewed source/test blobs, sets blockers to none, and moves the ticket to
  `tickets/done`.

## Retrospective

- Shared catalog readers required an explicit default-`None` operation
  capability. Activating a receipt scope alone must never observe apply,
  catalog-management, CLI, evaluation, or direct-library reads; this keeps the
  instrumentation boundary mechanically auditable and avoids ambient authority.
- The aggregate-only privacy constraint makes exact source-order validation a
  decomposition problem. Rejecting ambiguous 10,001-call L1 shapes is safer
  than inferring pass identity or retaining pass/stage data that the receipt is
  forbidden to store.
- Existing `_call` sanitization can transform a reached SDK cancellation after
  the invocation has already recorded authoritative interruption. The narrow
  repair is to prefer only an already-recorded interrupted catalog invocation
  for operation accounting while preserving external exception type/message and
  leaving ordinary errors unchanged.
- A focused 12-test local-fake matrix, together with the existing core boundary
  tables, made source order, maxima, cancellation, privacy, containment, and
  observer-fault equivalence independently reviewable without provider access.
- No new reusable skill, specification change, or follow-up ticket is needed.
  The closure evidence and PASS review retain exact source identity, criterion
  mapping, historical FAIL/repair lineage, and evidence limits. Integrated CLI
  wiring/final validation and the live canary remain correctly isolated in
  existing downstream tickets.
