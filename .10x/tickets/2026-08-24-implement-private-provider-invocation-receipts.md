Status: open
Created: 2026-08-24
Updated: 2026-08-24
Parent: None
Depends-On: None
Decision: .10x/decisions/buoy-uses-private-canary-provider-invocation-receipts.md
Accounting: .10x/specs/provider-client-invocation-accounting.md
Lifecycle: .10x/specs/provider-client-invocation-receipt.md

# Implement Private Provider Invocation Receipts

## Aggregate outcome

Implement the default-off, private in-process canary receipt specified by the
two governing active specifications, instrument the exact source-owned content
and automatic-catalog SDK call expressions, and prove the integrated receipt is
strict, content-free, failure-isolated, and independent of telemetry v2.

This parent is a non-executable implementation plan. It does not authorize
source work, provider access, canary execution, or activation of a child.

## Child sequence and dependencies

1. `.10x/tickets/2026-08-24-implement-private-provider-invocation-receipt-core.md`
   implements the private scope, ledger, immutable model, strict validator, and
   canonical in-process serialization with no call-site instrumentation.
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
`Depends-On` graph.

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
- Validation distinguishes a 40,001 successful catalog operation from a 40,002
  terminal failure even when all reached SDK expressions returned successfully.
- No child performs live provider/model/catalog/content, canary, migration,
  release, installed-tool, or global-state operations.

## Aggregate acceptance criteria

- Every child criterion maps to durable evidence at an exact commit.
- Focused fake-only tests prove all governed call boundaries, fallback paths,
  outcomes, conditional bounds, nested/concurrent lifecycle, strict canonical
  validation, privacy, and observer failure isolation.
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

Independent review of the records-only ratified-contract candidate is pending.
No child may move to `active` or execute until that review passes the exact
contract commit and the owner/integration session activates the selected child.

## Progress and notes

- 2026-08-24: Opened as a non-executable parent after explicit owner
  ratification. The four bounded children are open but inactive. No source/test,
  build/test, telemetry/store, provider/model/network, migration, canary,
  release, or global-tool operation occurred in this records-only turn.
