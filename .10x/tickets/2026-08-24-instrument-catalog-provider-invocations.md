Status: open
Created: 2026-08-24
Updated: 2026-08-24
Parent: .10x/tickets/2026-08-24-implement-private-provider-invocation-receipts.md
Depends-On: .10x/tickets/2026-08-24-implement-private-provider-invocation-receipt-core.md
Decision: .10x/decisions/buoy-uses-private-canary-provider-invocation-receipts.md
Accounting: .10x/specs/provider-client-invocation-accounting.md
Lifecycle: .10x/specs/provider-client-invocation-receipt.md

# Instrument Catalog Provider Invocations

## Outcome

Instrument automatic retrieval's exact strong catalog-read operation and SDK
call expressions so the private ledger emits only aggregate category/outcome
counts with correct terminal 40,001/40,002 validation semantics.

## Scope

- Register/finalize the existing `read_remote_catalog` strong-read operation.
- Observe both initial `client.namespaces(...)` calls and each reached
  `page.get_next_page()` as `namespace_list_page`.
- Observe the one reached `resource.metadata()` as `metadata` and each reached
  `resource.query(...)` in both card passes as `card_query_page`.
- Preserve `_call` sanitization, strong-read duplication, pagination order and
  bounds, normalization, fail-closed behavior, and automatic preview/live
  behavior.
- Add focused local-fake tests for aggregate counts, operation outcomes,
  conditional maxima, interruption, post-return failure, and observer faults.

## Acceptance criteria

- A minimum complete one-page strong read records five successful invocations:
  two list, one metadata, and two card query.
- Multipage list/card fakes record exact category/outcome aggregates across both
  passes without pass, cursor, namespace, card, response, billing, or error
  detail.
- A successful operation validates through 40,001 and rejects 40,002.
- The second-list post-page-10,000 bound failure validates at 40,002 even when
  all reached SDK expressions returned successfully; every total above 40,002
  rejects.
- SDK expression error/interruption counts once and stops the read; local
  post-return/normalization/bound error or interruption changes operation
  outcome without fabricating an invocation failure.
- Client construction, `client.namespace(...)`, response processing,
  eligibility, management, and mutation calls count zero.
- Disabled and injected observer faults preserve exact SDK arguments/count/order,
  original results/exceptions, strong-read and pagination behavior, preview/live
  behavior, output, and telemetry.
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
