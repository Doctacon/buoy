Status: open
Created: 2026-08-24
Updated: 2026-08-24
Parent: None
Depends-On: None
Decision: .10x/decisions/buoy-uses-private-canary-provider-invocation-receipts.md
Authorization-Evidence: .10x/evidence/2026-08-24-provider-client-invocation-receipt-authorization.md, .10x/evidence/2026-08-24-provider-invocation-probe-and-live-canary-authorization.md
Accounting: .10x/specs/provider-client-invocation-accounting.md
Lifecycle: .10x/specs/provider-client-invocation-receipt.md
Prior-Review: .10x/reviews/2026-08-24-provider-client-invocation-contract-review.md
Review: .10x/reviews/2026-08-24-provider-client-invocation-contract-rereview.md
Activation-Review: .10x/reviews/2026-08-24-provider-invocation-execution-activation-review.md
CLI-Receipt-Decision: .10x/decisions/buoy-recertifies-final-reviewed-cli-receipt.md

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
   - `.10x/tickets/2026-08-24-instrument-content-provider-invocations.md`
     instruments content logical-operation/call boundaries and worker
     propagation; and
   - `.10x/tickets/2026-08-24-instrument-catalog-provider-invocations.md`
     instruments the strong automatic-catalog read boundary.
   These two children may execute independently after the core is reviewed.
3. After children 1-3,
   `.10x/tickets/2026-08-24-validate-provider-invocation-receipt-integration.md`
   performs integrated strict-model, privacy, concurrency, observer-fault, and
   no-telemetry-v2 validation.

Only one implementation child may be active in a writer worktree at a time.
Each child must incorporate the reviewed predecessor state named by its
`Depends-On` graph. The core dependency is satisfied by its done ticket and
independently reviewed exact source commit/tree. Content and catalog are now the
next dependency-eligible children, but each remains open/inactive and MUST be
explicitly activated in a later implementation turn. Integration may begin only
after all three predecessors are done at reviewed exact commits.

The separate one-time live canary at
`.10x/tickets/2026-08-24-run-one-time-live-provider-invocation-receipt-canary.md`
is not a fifth implementation child. It depends on this plan's final integration
child and may activate only after the exact integrated fake-only commit passes
independent review. No implementation or canary may activate in this
records-only authorization turn.

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

The records-contract review gate is satisfied by independent PASS rereview
`.10x/reviews/2026-08-24-provider-client-invocation-contract-rereview.md` for
exact commit `cb4a76b97f68fcdfc2816c49c33b5b23e9b5f899`. The core child is done at
independently reviewed source commit `8953e9336354f2a2e0604a54be9cd882a97a7985`,
tree `66fb2d0dcca5d397132f60eb0be6d22a5b69479b`. This parent remains
non-executable and open. A remaining child may move to `active` or execute only
when its `Depends-On` graph is satisfied and the owner/integration session
explicitly activates that selected child.

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
