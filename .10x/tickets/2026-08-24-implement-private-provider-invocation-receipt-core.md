Status: open
Created: 2026-08-24
Updated: 2026-08-24
Parent: .10x/tickets/2026-08-24-implement-private-provider-invocation-receipts.md
Depends-On: None
Decision: .10x/decisions/buoy-uses-private-canary-provider-invocation-receipts.md
Accounting: .10x/specs/provider-client-invocation-accounting.md
Lifecycle: .10x/specs/provider-client-invocation-receipt.md

# Implement Private Provider Invocation Receipt Core

## Outcome

Implement the private, default-off receipt scope and the exact thread-safe
ledger/model/validator/canonical serialization core without instrumenting any
provider call site.

## Scope

- Add the smallest private internal module for the underscore-prefixed scope,
  handle, receipt-private `ContextVar`, thread-safe ledger, operation/attempt
  registration/completion, and explicit worker-lease binder.
- Implement no-op nested activation, independent top-level contexts, sealing,
  repeatable `bytes | None` handoff, and null-on-incomplete/fault behavior.
- Implement exact content/catalog/top-level models, conditional bounds, sequence
  grammar, fixed generic content error mapping, strict duplicate-key JSON
  decode, canonical encode/re-encode validation, byte limit, and generic
  non-echoing validation errors.
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
- Exact object keys/types/enums/counts/order/sequence/conditional 40,001/40,002
  bounds and canonical bytes validate; unknown/duplicate/noncanonical/
  prohibited sentinel data reject without echo.
- Error and interruption classification preserves the original exception
  identity; every injected observer/encode/decode fault returns null.
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

Independent PASS review of the governing records-only contract commit and
explicit activation of this child are required before execution.

## Progress and notes

- 2026-08-24: Opened fully specified but inactive. No implementation is
  authorized by ticket creation.
