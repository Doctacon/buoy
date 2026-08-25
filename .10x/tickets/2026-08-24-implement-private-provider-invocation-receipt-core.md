Status: open
Created: 2026-08-24
Updated: 2026-08-24
Parent: .10x/tickets/2026-08-24-implement-private-provider-invocation-receipts.md
Depends-On: None
Decision: .10x/decisions/buoy-uses-private-canary-provider-invocation-receipts.md
Accounting: .10x/specs/provider-client-invocation-accounting.md
Lifecycle: .10x/specs/provider-client-invocation-receipt.md
Prior-Review: .10x/reviews/2026-08-24-provider-client-invocation-contract-review.md
Review: .10x/reviews/2026-08-24-provider-client-invocation-contract-rereview.md

# Implement Private Provider Invocation Receipt Core

## Outcome

Implement the private, default-off receipt scope and the exact thread-safe
ledger/model/validator/canonical serialization core without instrumenting any
provider call site.

## Scope

- Add the smallest private internal module for the underscore-prefixed scope,
  handle, receipt-private `ContextVar`, thread-safe ledger, operation/attempt
  registration/completion, explicit worker-lease binder, and a ledger-bound
  private catalog-observer capability that shared readers cannot discover
  implicitly.
- Implement no-op nested activation, independent top-level contexts, sealing,
  repeatable `bytes | None` handoff, and null-on-incomplete/fault behavior.
- Implement exact content/catalog/top-level models, content sequence grammar,
  fixed generic error mapping, and the catalog aggregate state machine with
  per-category successful/terminal maxima and ordered L1 -> metadata -> card1
  -> card2 -> L2 prerequisites.
- Implement interruption precedence before generic `Exception` handling:
  `asyncio.CancelledError`, `concurrent.futures.CancelledError`, all other
  non-`Exception` `BaseException` values, and named control-flow exceptions are
  interrupted; every remaining `Exception` is error; preserve the identical
  object.
- Implement strict duplicate-key JSON decode, canonical encode/re-encode
  validation, byte limit, and generic non-echoing validation errors.
- Add focused provider-free unit tests for the lifecycle and validator through
  direct private test seams only.

## Acceptance criteria

- Default-off and activation-fault paths allocate no active ledger and return
  null without side effects.
- Active empty scope returns one canonical zero-count receipt only after exit;
  nested scope returns null and leaves the outer ledger authoritative.
- Separate contexts and explicitly bound workers remain isolated; leases,
  in-flight calls, late use, premature exit, and synchronization faults obey the
  no-wait unknown-receipt contract.
- Exact object keys/types/enums/counts/order/sequence and canonical bytes
  validate; unknown/duplicate/noncanonical/prohibited sentinel data reject
  without echo.
- Exhaustive boundary tables prove successful list 2..20,000, metadata exactly
  1, card 2..20,000; terminal list <=20,001, metadata <=1, card <=20,000;
  every source-order prerequisite; mixed/later-stage impossibilities; exact
  all-success 40,002 composition; ambiguous L1 10,001 rejection; and every
  adjacent over-bound value.
- Focused identity tests cover both cancellation classes, `KeyboardInterrupt`,
  `SystemExit`, `GeneratorExit`, a custom non-`Exception` `BaseException`, and
  representative remaining `Exception` values; every case has exact outcome
  precedence and re-raises the identical object.
- A private catalog capability is available only from a live active handle,
  becomes unusable at sealing, and is never a package-public callback. Every
  injected observer/encode/decode fault returns null.
- No package-public export, CLI/env trigger, telemetry import dependency,
  automatic filesystem/database/network write, or provider call is introduced.

## Evidence expectations

Record the exact commit/tree, targeted unit-test commands and outputs, static
public-export/trigger/persistence inspection, privacy-sentinel results, and
diff/stat. Evidence must state that tests use no provider/network/model/store or
credential.

## Explicit exclusions

Content/catalog source instrumentation, retriever worker-seam edits, provider or
canary execution, public API, CLI/env enablement, automatic persistence,
telemetry-v2 change, database/store/migration, recurring retention, release, and
global-tool changes are excluded.

## Blockers

The governing records-contract review gate is satisfied by PASS rereview
`.10x/reviews/2026-08-24-provider-client-invocation-contract-rereview.md`.
Explicit activation of this child is still required before execution; this
open ticket remains inactive.

## Progress and notes

- 2026-08-24: Opened fully specified but inactive. No implementation is
  authorized by ticket creation.
- 2026-08-24: FAIL review `29dbeef6-82a2-43b1-8fd3-b572f0d83f40`
  required regeneration-grade aggregate catalog validation and exact
  cancellation precedence/identity coverage. Scope and acceptance now own
  those repairs plus the private non-ambient catalog capability. Ticket remains
  open/inactive pending repaired-contract rereview.
- 2026-08-24: PASS rereview
  `a4331cfc-d12b-4209-8e5a-8cb66655cf76` accepted exact repaired contract
  commit `cb4a76b97f68fcdfc2816c49c33b5b23e9b5f899`. The review blocker is
  resolved; explicit activation remains required. Ticket stays open/inactive,
  and no implementation or validation ran.
