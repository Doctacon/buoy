Status: active
Created: 2026-08-24
Updated: 2026-08-24
Parent: .10x/tickets/2026-08-24-implement-private-provider-invocation-receipts.md
Depends-On: None
Decision: .10x/decisions/buoy-uses-private-canary-provider-invocation-receipts.md
Authorization-Evidence: .10x/evidence/2026-08-24-provider-client-invocation-receipt-authorization.md, .10x/evidence/2026-08-24-provider-invocation-probe-and-live-canary-authorization.md
Accounting: .10x/specs/provider-client-invocation-accounting.md
Lifecycle: .10x/specs/provider-client-invocation-receipt.md
Prior-Review: .10x/reviews/2026-08-24-provider-client-invocation-contract-review.md
Review: .10x/reviews/2026-08-24-provider-client-invocation-contract-rereview.md
Activation-Review: .10x/reviews/2026-08-24-provider-invocation-execution-activation-review.md

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

None. The governing records-contract review gate is satisfied by PASS rereview
`.10x/reviews/2026-08-24-provider-client-invocation-contract-rereview.md`, and
the owner explicitly activated only this core child for execution at clean HEAD
`022095ed4c3fe606a1744f3818c6ec1ecdf3d085`.

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
- 2026-08-24: Current owner authorization is linked. This core is the next
  eligible source child, but it remains open/inactive and cannot activate in
  this records-only turn. No source/test or operational command ran.
- 2026-08-24: Independent activation review passed exact authorization commit
  `21f6a7b21d950f086ac6dfd7ab4f633883d6e066`, tree
  `4d044b44d492757dad80466968809aebdb76f161`, with no findings. Core is the
  next executable ticket but remains open/inactive pending explicit activation
  in a later implementation turn; no implementation or operation ran.
- 2026-08-24: Owner explicitly activated only this core child for implementation
  from clean HEAD `022095ed4c3fe606a1744f3818c6ec1ecdf3d085`. The separate
  provider-free latency probe remains blocked and MUST NOT be rerun or repaired.
  Source work has not begun; this activation record is committed separately.
- 2026-08-24: Implemented the private core in
  `src/buoy_search/_provider_invocation_receipt.py` and focused direct-seam tests
  in `tests/test_provider_invocation_receipt_core.py`. Final credential-removed,
  offline runs passed all 40 tests on Python 3.11 and 3.13. A static AST/scope
  inspection passed 42 private definitions, standard-library-only imports, no
  package/CLI exposure, and exactly the two intended uncommitted source/test
  paths before this progress update. Both repository frozen-contract static
  validators also passed. No provider, model, network, content,
  catalog, store, telemetry, persistence, routing-artifact, or latency-probe
  operation ran. The ticket remains active pending independent review; exact
  candidate commit/tree and diff are reported in the implementation handoff.
- 2026-08-24: Repaired only the independent core review's fault-isolation
  findings. A separate receipt-private scope fault target now makes transient
  governed active-ledger lookup failure permanently unknown without weakening
  nested-scope read-failure isolation. Active handle, content observer, and
  catalog-operation observer construction faults now use preallocated disabled
  fallbacks that preserve body/callback result and exception identity. Focused
  credential-free offline tests passed 45/45 on Python 3.11 and 3.13 using only
  direct private seams and an in-memory generated-version stub; static checks
  passed 44 private definitions, standard-library-only imports, unchanged
  package/CLI/telemetry boundaries, and current-develop ancestry. No provider,
  model, network, content, catalog, store, telemetry, persistence, routing,
  canary, or latency-probe operation ran. Ticket remains active pending fresh
  independent review of the repaired commit.
