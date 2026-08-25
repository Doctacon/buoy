Status: active
Created: 2026-08-24
Updated: 2026-08-24
Parent: .10x/tickets/2026-08-24-implement-private-provider-invocation-receipts.md
Depends-On: .10x/tickets/done/2026-08-24-implement-private-provider-invocation-receipt-core.md, .10x/tickets/done/2026-08-24-instrument-content-provider-invocations.md, .10x/tickets/done/2026-08-24-instrument-catalog-provider-invocations.md
Decision: .10x/decisions/buoy-uses-private-canary-provider-invocation-receipts.md
Authorization-Evidence: .10x/evidence/2026-08-24-provider-client-invocation-receipt-authorization.md, .10x/evidence/2026-08-24-provider-invocation-probe-and-live-canary-authorization.md
Downstream-Canary: .10x/tickets/2026-08-24-run-one-time-live-provider-invocation-receipt-canary.md
Accounting: .10x/specs/provider-client-invocation-accounting.md
Lifecycle: .10x/specs/provider-client-invocation-receipt.md
Prior-Review: .10x/reviews/2026-08-24-provider-client-invocation-contract-review.md
Review: .10x/reviews/2026-08-24-provider-client-invocation-contract-rereview.md
Activation-Review: .10x/reviews/2026-08-24-provider-invocation-execution-activation-review.md
CLI-Receipt-Decision: .10x/decisions/buoy-recertifies-final-reviewed-cli-receipt.md

# Validate Provider Invocation Receipt Integration

## Outcome

Prove the integrated private receipt is regeneration-grade, strict,
privacy-safe, observer-failure-isolated, default-off, and independent of
telemetry v2, without live provider/model/store/network or canary operations.

## Scope

- Add only missing cross-family/lifecycle tests not owned by predecessor
  tickets; do not rewrite implementation merely to centralize tests.
- Wire only the automatic-retrieve CLI branch to obtain the active private
  catalog observer and pass it explicitly to `read_remote_catalog`. Do not add
  observer arguments to apply, catalog-management, or any other caller.
- Validate explicit live/preview and automatic live/preview fake command paths,
  including catalog-only preview, catalog-plus-content live, pre-call failure,
  partial/all content failure, nested/concurrent scope use, and terminal body
  exception handoff.
- Inventory every shared `read_remote_catalog` caller and prove apply,
  catalog-management, direct-library, and default-`None` calls remain unobserved
  even when a receipt scope is active.
- Run adversarial canonical model/byte validation and exact-byte privacy
  sentinels across in-memory ledger, returned receipt, errors, and test artifacts.
- Inject failures at every observer phase and compare call/result/exception/
  telemetry/output behavior with the observer disabled.
- Inspect public exports, CLI parser, environment reads, filesystem/database/
  telemetry writes, and telemetry-v2 envelope/store definitions for forbidden
  activation, persistence, or schema drift.
- Run the exhaustive aggregate-state and interruption-identity matrices across
  canonical decoding and integrated automatic-retrieve fakes.
- Treat the CLI wiring as a routing source-receipt change. After `cli.py` bytes
  are final and independently reviewed, measure their SHA-256, restore the
  exact active schema-v3 artifact
  `src/buoy_search/data/automatic_routing_confidence_calibration.json`, and
  change only `receipts.cli_module_sha256` to that measured value. Prove every
  other parsed field and text line unchanged, including the frozen seven-
  namespace anchor, schema/revision, provisional policy, models, thresholds,
  suite, projection, calibration, reports, evaluator, routing, evidence, and
  collect-artifact receipts.
- Run focused/full, routing-artifact, strict old/new receipt, dual-runtime,
  source/wheel/install, and provider-free repository validation required by
  `.10x/decisions/buoy-recertifies-final-reviewed-cli-receipt.md`, then obtain
  fresh independent review of the exact final commit.

## Acceptance criteria

- Integrated automatic preview returns a terminal catalog-only receipt and makes
  no content call; integrated automatic live keeps catalog/content families
  separate; explicit retrieval has `catalog.outcome=null` and zero catalog
  counters. Automatic retrieve is the only shared-reader caller that passes the
  private observer.
- Apply, every catalog-management path, and direct/default-`None` reader calls
  produce zero catalog accounting even inside an active receipt scope.
- Missing/incomplete/invalid/observer-failed receipts are always unknown and
  cannot satisfy a receipt acceptance gate; a validated receipt is handed off
  only after terminal finalization.
- Nested and concurrent contexts and worker propagation/leasing match both
  specs. Identity tests cover `asyncio.CancelledError`,
  `concurrent.futures.CancelledError`, `KeyboardInterrupt`, `SystemExit`,
  `GeneratorExit`, a custom non-`Exception` `BaseException`, and representative
  other exceptions with exact interrupted/error precedence.
- Integrated validator tests cover every per-category boundary, ordered-stage
  prerequisite, impossible aggregate, exact all-success 40,002 composition, and
  adjacent overflow required by the accounting spec.
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
- The final CLI SHA-256 equals the sole changed artifact receipt field; exact
  artifact comparison and package copies preserve all other schema-v3 authority.
- Independent review passes the exact integrated commit with specifications,
  routing artifact, source receipt, and ticket graph coherent.

## Evidence expectations

Record exact commit/tree; every focused/full command and complete result;
privacy/audit/fault-injection and aggregate-state evidence; shared-caller
inventory; changed-path/public-surface inspection; final `cli.py` SHA-256;
byte/parsed equality proving only `receipts.cli_module_sha256` changed in the
schema-v3 artifact; package receipt reproduction; and both final-CLI-bytes and
exact-final-commit independent review references. Limits must state that
fake-only validation does not prove a live provider receipt, physical wire
count, billing, or rate-limit use.

## Explicit exclusions

Live canary/provider/model/catalog/content/network/credential operation, real
telemetry/store/database/migration command, source widening beyond automatic-
retrieve observer wiring and the exact governed CLI-hash recertification,
public/CLI/env activation, automatic persistence, retention/purge change,
telemetry-v2 extension, routing-semantic/artifact change beyond the one hash,
wire/cost/rate-limit claim, release, deployment, and installed/global-tool
changes are excluded.

## Blockers

None.

Core, content, and catalog predecessors are done at independently reviewed exact
commits/trees. This child remains open/inactive and must be explicitly activated
in a later turn before execution. Its exact final fake-only commit must pass
independent integration review before the separate downstream live-canary ticket
may activate.

## Progress and notes

- 2026-08-24: Opened fully specified but inactive. This records-only turn ran no
  validation command or external operation.
- 2026-08-24: FAIL review `29dbeef6-82a2-43b1-8fd3-b572f0d83f40`
  required automatic-retrieve-only explicit observer wiring, caller isolation,
  exact state/identity matrices, and final CLI receipt recertification. This
  ticket now owns that bounded integration work under the active recertification
  decision. It remains open/inactive pending repaired-contract rereview.
- 2026-08-24: PASS rereview
  `a4331cfc-d12b-4209-8e5a-8cb66655cf76` accepted exact repaired contract
  commit `cb4a76b97f68fcdfc2816c49c33b5b23e9b5f899`. Contract review is no longer
  a blocker; all predecessor dependencies and explicit activation remain. No
  CLI wiring, source/test implementation, validation, or CLI receipt
  recertification ran.
- 2026-08-24: Current owner authorization links the separately bounded one-time
  live canary as a downstream dependent. This integration child and canary both
  remain open/inactive; canary activation requires this exact final fake-only
  commit to pass independent review. No source/test or operational command ran.
- 2026-08-24: Independent activation review passed exact authorization commit
  `21f6a7b21d950f086ac6dfd7ab4f633883d6e066`, tree
  `4d044b44d492757dad80466968809aebdb76f161`, with no findings. Integration
  remains open/inactive behind all three reviewed predecessors; the canary
  remains downstream and inactive. No implementation or operation ran.
- 2026-08-24: Core predecessor satisfied by
  `.10x/tickets/done/2026-08-24-implement-private-provider-invocation-receipt-core.md`
  at reviewed source commit `8953e9336354f2a2e0604a54be9cd882a97a7985`,
  tree `66fb2d0dcca5d397132f60eb0be6d22a5b69479b`. Integration remains
  open/inactive behind the content and catalog children; no integration
  source/test, CLI receipt, artifact, or operational work ran in this
  records-only closure.
- 2026-08-24: Content predecessor satisfied by
  `.10x/tickets/done/2026-08-24-instrument-content-provider-invocations.md` at
  reviewed source commit `e72841d2c4553c66f99be9f57efc1cd137fd543d`, tree
  `8fea9db249214a6d633a7d34d2c014fbcd6e816b`. Integration remains open/inactive
  behind only catalog and still requires separate explicit activation; no
  integration source/test, CLI receipt, routing artifact, validation, or
  operational work ran in this records-only closure.
- 2026-08-24: Catalog predecessor satisfied by
  `.10x/tickets/done/2026-08-24-instrument-catalog-provider-invocations.md` at
  reviewed source commit `d9399e86e121e00f403f5f3a1d674f70c2d75aa4`, tree
  `1359284ad942224c6873ca810f7de93fd188ad9c`. All predecessor dependencies are
  now satisfied and blockers are none. Integration remains open/inactive until
  separately activated; no integration source/test, CLI receipt, routing
  artifact, validation, provider/network, canary, or operational work ran in
  this records-only closure.
- 2026-08-24: Owner explicitly activated only this integration child for the
  source/test staging portion from clean HEAD
  `68a2d84a87c454d2d7dbea43fb6a1f7e67de6b8b`. CLI wiring and integrated local-
  fake tests may proceed; routing calibration artifact mutation, provider,
  network, credential, model, store, telemetry, canary, release, and global-
  tool operations remain excluded. Source/test work has not begun.
