Status: done
Created: 2026-08-24
Updated: 2026-08-24
Parent: None
Depends-On: None
Decision: .10x/decisions/buoy-uses-private-canary-provider-invocation-receipts.md
Authorization-Evidence: .10x/evidence/2026-08-24-provider-client-invocation-receipt-authorization.md, .10x/evidence/2026-08-24-provider-invocation-probe-and-live-canary-authorization.md
Accounting: .10x/specs/provider-client-invocation-accounting.md
Lifecycle: .10x/specs/provider-client-invocation-receipt.md
Prior-Review: .10x/reviews/2026-08-24-provider-client-invocation-contract-review.md
Contract-Review: .10x/reviews/2026-08-24-provider-client-invocation-contract-rereview.md
Activation-Review: .10x/reviews/2026-08-24-provider-invocation-execution-activation-review.md
CLI-Receipt-Decision: .10x/decisions/buoy-recertifies-final-reviewed-cli-receipt.md
Evidence: .10x/evidence/2026-08-24-provider-invocation-receipt-integration-closure.md
Review: .10x/reviews/2026-08-24-provider-invocation-receipt-integration-review.md
Reviewed-Source: commit 0b27c4eaa2449493125f4040af3cd1f7c926b531, tree 9017c4a335938faca80cdded54545df8b79c12f8
Reviewed-Records: commit 327bcf43b73b5941a0c94ab9fb4aa294456ea498, tree 0c187238d8abe09cf0d99aa8fdb53f1a5112900e

# Implement Private Provider Invocation Receipts

## Aggregate outcome

Implement the default-off, private in-process canary receipt specified by the
two governing active specifications, instrument the exact source-owned content
and automatic-catalog SDK call expressions, and prove the integrated receipt is
strict, content-free, failure-isolated, and independent of telemetry v2.

This parent is a non-executable implementation plan. It does not authorize
source work, provider access, canary execution, or activation of a child.

## Child sequence and dependencies

1. `.10x/tickets/done/2026-08-24-implement-private-provider-invocation-receipt-core.md`
   implements the private scope, ledger, immutable model, strict validator, and
   canonical in-process serialization with no call-site instrumentation. It is
   done at independently reviewed source commit
   `8953e9336354f2a2e0604a54be9cd882a97a7985`, tree
   `66fb2d0dcca5d397132f60eb0be6d22a5b69479b`.
2. After child 1:
   - `.10x/tickets/done/2026-08-24-instrument-content-provider-invocations.md`
     instruments content logical-operation/call boundaries and worker
     propagation. It is done at independently reviewed source commit
     `e72841d2c4553c66f99be9f57efc1cd137fd543d`, tree
     `8fea9db249214a6d633a7d34d2c014fbcd6e816b`; and
   - `.10x/tickets/done/2026-08-24-instrument-catalog-provider-invocations.md`
     instruments the strong automatic-catalog read boundary. It is done at
     independently reviewed source commit
     `d9399e86e121e00f403f5f3a1d674f70c2d75aa4`, tree
     `1359284ad942224c6873ca810f7de93fd188ad9c`.
   These two children executed independently after the core was reviewed.
3. After children 1-3,
   `.10x/tickets/done/2026-08-24-validate-provider-invocation-receipt-integration.md`
   performed integrated strict-model, privacy, concurrency, observer-fault, and
   no-telemetry-v2 validation. It is done at independently reviewed exact source
   commit `0b27c4eaa2449493125f4040af3cd1f7c926b531`, tree
   `9017c4a335938faca80cdded54545df8b79c12f8`, with validation records commit
   `327bcf43b73b5941a0c94ab9fb4aa294456ea498`, tree
   `0c187238d8abe09cf0d99aa8fdb53f1a5112900e`.

Only one implementation child was active in a writer worktree at a time. Each
child incorporated the reviewed predecessor state named by its `Depends-On`
graph. All four children are done at independently reviewed exact source
commits/trees.

The separate one-time live canary at
`.10x/tickets/2026-08-24-run-one-time-live-provider-invocation-receipt-canary.md`
is not a fifth implementation child. Its reviewed fake-only dependency is now
satisfied. The canary remains open/inactive and still requires its own explicit
later activation; this records-only closure runs no canary or external operation.

## Integration and coherence requirements

- One unit spelling is used everywhere: `provider_client_invocation`.
- Content route detail and catalog aggregates remain separate in one exact
  receipt.
- The private scope remains default-off and internal; no CLI/environment/public
  or automatic persistence surface appears.
- Existing telemetry v1/v2 files, schemas, graphs, enablement, and retention
  remain unchanged.
- Observer faults make the receipt unknown without changing retrieval,
  provider, routing, output, or exception behavior.
- Regeneration-grade aggregate validation enforces per-category bounds and the
  exact L1 -> metadata -> card1 -> card2 -> L2 source prerequisites; the
  all-success 40,002 shape is exactly list=20,001, metadata=1, card=20,000.
- Interruption precedence names both cancellation classes and all non-
  `Exception` `BaseException` values, while every other `Exception` is error;
  observation preserves the identical exception.
- Shared catalog readers use an explicit private observer argument defaulting to
  null. Only automatic retrieve passes it; apply/catalog/direct callers remain
  unobserved. Final CLI wiring recertifies only the governed CLI hash in the
  otherwise frozen schema-v3 routing artifact.
- No child performs live provider/model/catalog/content, canary, migration,
  release, installed-tool, or global-state operations.

## Aggregate acceptance criteria

- Every child criterion maps to durable evidence at an exact commit.
- Focused fake-only tests prove all governed call boundaries, fallback paths,
  exact cancellation identity, aggregate source-order tables, conditional
  bounds, nested/concurrent lifecycle, strict canonical validation, privacy,
  caller isolation, and observer failure isolation.
- Exact diff inspection proves no CLI/env/public API, automatic disk write,
  telemetry-v2 extension, production retention change, or unrelated source
  mutation.
- Full repository validation required by the final child passes without live
  provider/network/model/store/global-tool effects.
- Independent review passes the exact integrated commit and confirms governing
  specs still match implementation before any implementation ticket closes.

## Explicit exclusions

Live canary/provider/model/catalog/content/network/credential operations,
telemetry/store/database commands, migration, production telemetry schema,
public diagnostics, automatic persistence, retention/purge change, wire/cost/
rate-limit claims, release, deployment, installed/global-tool changes, and
main/develop integration are excluded.

## Blockers

None.

## Progress and notes

- 2026-08-24: Opened as a non-executable parent after explicit owner
  ratification. The four bounded children are open but inactive. No source/test,
  build/test, telemetry/store, provider/model/network, migration, canary,
  release, or global-tool operation occurred in this records-only turn.
- 2026-08-24: The FAIL review is recorded at
  `.10x/reviews/2026-08-24-provider-client-invocation-contract-review.md`.
  Governing specs/tickets now require an exact aggregate catalog state machine,
  exact interruption precedence/identity, and automatic-retrieve-only explicit
  catalog observer wiring with bounded final CLI receipt recertification. The
  plan and every child remain open/inactive pending rereview; no implementation
  or external operation ran.
- 2026-08-24: Independent rereview
  `a4331cfc-d12b-4209-8e5a-8cb66655cf76` passed repaired contract commit
  `cb4a76b97f68fcdfc2816c49c33b5b23e9b5f899`. Historical FAIL remains
  attached as prior review; current PASS is the governing review. The parent and
  all four children remain open/inactive. Dependency and explicit-activation
  gates remain unchanged; no implementation or operational work ran.
- 2026-08-24: Current owner authorization is linked. Core is the next eligible
  source child but remains open/inactive; content/catalog still require reviewed
  core, integration still requires all predecessors, and the separate live
  canary requires reviewed final integration. No child or canary activated and
  no source/test or operational command ran in this records-only turn.
- 2026-08-24: Independent activation review passed exact authorization commit
  `21f6a7b21d950f086ac6dfd7ab4f633883d6e066`, tree
  `4d044b44d492757dad80466968809aebdb76f161`, with no findings. The parent and
  four children remain open/inactive. Core is the next executable ticket but
  requires explicit later activation; no implementation or operation ran.
- 2026-08-24: Core closed at independently reviewed source commit
  `8953e9336354f2a2e0604a54be9cd882a97a7985`, tree
  `66fb2d0dcca5d397132f60eb0be6d22a5b69479b`; its done ticket, evidence, and
  PASS review are linked in the child sequence. Content and catalog are now
  dependency-eligible but remain open/inactive pending separate explicit
  activation. Integration remains blocked on both instrumentation children.
- 2026-08-24: Content closed independently at reviewed source commit
  `e72841d2c4553c66f99be9f57efc1cd137fd543d`, tree
  `8fea9db249214a6d633a7d34d2c014fbcd6e816b`. Its done ticket, focused closure
  evidence, and PASS review are linked in the child sequence. Catalog remains
  open/inactive pending separate explicit activation; integration remains
  blocked only on catalog.
- 2026-08-24: Catalog closed independently at reviewed source commit
  `d9399e86e121e00f403f5f3a1d674f70c2d75aa4`, tree
  `1359284ad942224c6873ca810f7de93fd188ad9c`. Its done ticket, focused closure
  evidence, and PASS review are linked in the child sequence. All three
  implementation predecessors are now done; integration is dependency-eligible
  but remains open/inactive pending separate explicit activation. No integration
  source/test, CLI receipt, routing artifact, validation, or operational work
  ran in this records-only closure.
- 2026-08-24: Integration closed independently at exact source commit
  `0b27c4eaa2449493125f4040af3cd1f7c926b531`, tree
  `9017c4a335938faca80cdded54545df8b79c12f8`, with validation records commit
  `327bcf43b73b5941a0c94ab9fb4aa294456ea498`, tree
  `0c187238d8abe09cf0d99aa8fdb53f1a5112900e`. Focused evidence maps every child
  and aggregate criterion and preserves exact dual-runtime 91/535/1,167 counts,
  artifact-only equality, full package identities, and review history. Fresh
  final review passed both active specs with no finding or repair. All four
  children are done, aggregate blockers are none, and this non-executable parent
  moves to `tickets/done`. The downstream live canary remains separate,
  inactive, and unexecuted.

## Retrospective

- Splitting core, content, catalog, and integration kept lifecycle authority,
  exact SDK boundaries, shared-reader capability, and aggregate coherence
  independently reviewable while still converging on one exact receipt.
- Narrow transformed-cancellation repairs discovered by content and catalog
  execution show why child review must reconcile the outer sanitized exception
  with the already-observed invocation outcome instead of assuming exception
  class alone remains authoritative across layers.
- The integration stage correctly owned the only shared-caller CLI wiring and
  one-leaf source-receipt recertification. Keeping those out of earlier children
  preserved their closure identities and made final scope containment exact.
- Independent review at every child plus a fresh aggregate review prevented
  predecessor PASS verdicts and raw test counts from substituting for integrated
  acceptance and active-spec drift checks.
- No new spec, decision, skill, or implementation ticket is needed from plan
  closure. Live empirical limits remain durably isolated in the existing
  one-time canary ticket, whose explicit activation and operational gates are
  unchanged.
