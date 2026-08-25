Status: open
Created: 2026-08-24
Updated: 2026-08-24
Parent: .10x/tickets/2026-08-24-implement-private-provider-invocation-receipts.md
Depends-On: .10x/tickets/2026-08-24-implement-private-provider-invocation-receipt-core.md, .10x/tickets/2026-08-24-instrument-content-provider-invocations.md, .10x/tickets/2026-08-24-instrument-catalog-provider-invocations.md
Decision: .10x/decisions/buoy-uses-private-canary-provider-invocation-receipts.md
Accounting: .10x/specs/provider-client-invocation-accounting.md
Lifecycle: .10x/specs/provider-client-invocation-receipt.md

# Validate Provider Invocation Receipt Integration

## Outcome

Prove the integrated private receipt is regeneration-grade, strict,
privacy-safe, observer-failure-isolated, default-off, and independent of
telemetry v2, without live provider/model/store/network or canary operations.

## Scope

- Add only missing cross-family/lifecycle tests not owned by predecessor
  tickets; do not rewrite implementation merely to centralize tests.
- Validate explicit live/preview and automatic live/preview fake command paths,
  including catalog-only preview, catalog-plus-content live, pre-call failure,
  partial/all content failure, nested/concurrent scope use, and terminal body
  exception handoff.
- Run adversarial canonical model/byte validation and exact-byte privacy
  sentinels across in-memory ledger, returned receipt, errors, and test artifacts.
- Inject failures at every observer phase and compare call/result/exception/
  telemetry/output behavior with the observer disabled.
- Inspect public exports, CLI parser, environment reads, filesystem/database/
  telemetry writes, and telemetry-v2 envelope/store definitions for forbidden
  activation, persistence, or schema drift.
- Run focused and full provider-free repository validation required for handoff,
  then obtain independent exact-commit review.

## Acceptance criteria

- Integrated automatic preview returns a terminal catalog-only receipt and makes
  no content call; integrated automatic live keeps catalog/content families
  separate; explicit retrieval has `catalog.outcome=null` and zero catalog
  counters.
- Missing/incomplete/invalid/observer-failed receipts are always unknown and
  cannot satisfy a receipt acceptance gate; a validated receipt is handed off
  only after terminal finalization.
- Nested and concurrent contexts, worker propagation/leasing, interruption, and
  original-exception identity match both specs under deterministic tests.
- Exact-byte sentinels for query, argv, namespace/provider/card identifiers,
  content, paths, credentials, URL, payload, billing, raw errors/stacks,
  timestamps, IDs, and ambient context appear nowhere in canonical receipt
  bytes or validator diagnostics.
- Audit/inspection proves no CLI flag, environment trigger, package-public API,
  automatic file/database/network write, telemetry-v2 field/span/envelope/store
  change, production retention change, or automatic canary.
- Focused and full tests pass on required Python versions without provider,
  network, credential, model asset, real telemetry store, migration, or global
  tool state.
- Independent review passes the exact integrated commit with specifications and
  ticket graph coherent.

## Evidence expectations

Record exact commit/tree; every focused/full command and complete result;
privacy/audit/fault-injection evidence; changed-path and public-surface
inspection; and independent review reference. Limits must state that fake-only
validation does not prove a live provider receipt, physical wire count, billing,
or rate-limit use.

## Explicit exclusions

Live canary/provider/model/catalog/content/network/credential operation, real
telemetry/store/database/migration command, source widening beyond integration
blockers, public/CLI/env activation, automatic persistence, retention/purge
change, telemetry-v2 extension, wire/cost/rate-limit claim, release, deployment,
and installed/global-tool changes are excluded.

## Blockers

All three implementation predecessors must be done at reviewed exact commits,
the governing contract must have independent PASS review, and this child must
be explicitly activated before execution.

## Progress and notes

- 2026-08-24: Opened fully specified but inactive. This records-only turn ran no
  validation command or external operation.
