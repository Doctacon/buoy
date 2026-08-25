Status: recorded
Created: 2026-08-24
Updated: 2026-08-24
Target: commit cb4a76b97f68fcdfc2816c49c33b5b23e9b5f899, tree d0aa9598cbcc28bb35c16dd51d614980321abaad, .10x/specs/provider-client-invocation-accounting.md, .10x/specs/provider-client-invocation-receipt.md, .10x/tickets/2026-08-24-implement-private-provider-invocation-receipts.md
Verdict: pass

# Provider Client Invocation Contract Rereview

## Target and method

Independent rereview run `a4331cfc-d12b-4209-8e5a-8cb66655cf76` inspected
records-only repair commit
`cb4a76b97f68fcdfc2816c49c33b5b23e9b5f899`, tree
`d0aa9598cbcc28bb35c16dd51d614980321abaad`, against the ratified owner
contract, exact catalog source order and caller inventory, interruption
precedence, active routing CLI-receipt authority, two active specifications, and
open implementation graph.

The historical FAIL at
`.10x/reviews/2026-08-24-provider-client-invocation-contract-review.md` remains
truthful for candidate `a458aeba95844230271ad50d4364281f4462ad5e`. This
rereview does not rewrite that verdict; it evaluates the repaired exact commit.

## Prior FAIL resolution

1. **Aggregate catalog validation — repaired.** The accounting specification
   now gives per-category successful and terminal maxima and an exact aggregate
   state machine for `L1 -> metadata -> card pass 1 -> card pass 2 -> L2`.
   Metadata/card prerequisites, terminal-order exclusion, two-pass
   decompositions, mixed terminal rejection, adjacent overflows, ambiguous L1
   10,001 rejection, and the exact all-success 40,002 composition are explicit.
   No pass ID or operational budget was added.
2. **Interruption precedence — repaired.** Both `asyncio.CancelledError` and
   `concurrent.futures.CancelledError` precede generic `Exception`; every other
   non-`Exception` `BaseException` is interrupted; every remaining `Exception`
   is error; and core/catalog/integration tickets require identical-object
   tests.
3. **Automatic-retrieve containment — repaired.** The shared catalog reader and
   helpers take an explicit private observer argument defaulting to `None` and
   never discover receipt context implicitly. Only automatic retrieve may pass
   it. Apply, catalog management, direct callers, and default calls remain
   unobserved. Final CLI wiring and exact CLI-hash-only schema-v3 routing
   recertification are bounded to the integration child under the active
   recertification decision.

## Contract and privacy assessment

The unit remains one Buoy SDK call attempt counted immediately before call-
expression evaluation, not a wire, billing, cost, or rate-limit unit. Content
and catalog remain separate; content retains route-rank-only detail and catalog
retains fixed aggregates. Missing/incomplete/invalid receipt remains unknown.
The private scope remains default-off with no CLI/environment/public activation,
automatic disk write, telemetry-v2 extension, or recurring production retention
change.

The fixed models exclude query, argv, namespace/provider/card identity,
credentials, payload/content, URL/path, billing, raw error/stack, timestamp, and
ambient context. The 40,001/40,002 and per-category maxima remain validator
reachability bounds, not operational budgets.

## Ticket-graph assessment

The implementation parent is correctly non-executable and open. Receipt core,
content instrumentation, catalog instrumentation, and integrated validation are
bounded open/inactive children with dependency and explicit-activation gates.
The final child owns routing CLI receipt recertification without changing other
schema-v3 authority. No source, test, provider/model/catalog/content, store,
telemetry, migration, network, credential, canary, release, or global-tool
operation is authorized by this review.

## Verdict

**PASS.** Commit `cb4a76b` is a regeneration-grade, owner-ratified contract and
implementation graph. The three prior significant findings are repaired. The
physical-attempt shaping ticket may close, and its actionability parent may
close after exact status/reference reconciliation. This PASS does not activate
or implement any open child.

## Residual risk

Implementation and fake-only verification have not occurred. Actual physical
wire sends, provider billing, and rate-limit accounting remain unresolved and
out of scope. The distinct provider-free retriever-construction probe remains
blocked pending its own owner ratification.
