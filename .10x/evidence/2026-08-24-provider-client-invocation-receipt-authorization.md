Status: recorded
Created: 2026-08-24
Updated: 2026-08-24
Relates-To: .10x/tickets/done/2026-08-24-define-physical-provider-attempt-accounting.md, .10x/decisions/superseded/buoy-uses-private-canary-provider-invocation-receipts.md, .10x/specs/provider-client-invocation-accounting.md, .10x/specs/provider-client-invocation-receipt.md

# Provider Client Invocation Receipt Authorization

## What was observed

After source-only shaping and independent PASS rereview, the owner explicitly
ratified the complete application-boundary contract and authorized this Outer
Loop turn to record evidence, an ADR, active focused specifications, and a
bounded implementation ticket graph. The owner did not authorize
implementation or any operational action.

## Exact owner-ratified contract

> `provider_client_invocation` is one Buoy SDK call attempt incremented
> immediately before call-expression evaluation, not wire/cost/rate-limit;
> canary-only terminal receipt first; content and catalog families separate;
> route-rank-only content detail; aggregate catalog detail;
> 40,001-success/40,002-terminal-failure are validator reachability bounds,
> never operational budgets; outcomes `success|error|interrupted`;
> absent/incomplete receipt unknown; retain sanitized receipts indefinitely with
> durable canary evidence; delete raw artifacts; no recurring production
> retention change; activation/delivery is a private in-process scope returning
> the sanitized receipt to an explicitly authorized harness, default off, with
> no CLI flag, environment trigger, public API, automatic disk write, or
> telemetry-v2 extension.

The owner further directed the records to fully specify bounded shapes, fixed
privacy-safe categories, call/error/interruption behavior, observer isolation,
receipt authority, activation/finalization, nested/concurrent behavior,
serialization handoff, validation, and retention. Fixed internal names and
enums are mechanical only where they preserve the semantics above.

## Authorized scope for this turn

Authorized:

- this exact evidence record;
- one focused ADR with alternatives and consequences;
- the smallest regeneration-grade active specification set;
- one non-executable implementation parent plan and bounded executable child
  tickets left open/inactive pending independent review; and
- coherent shaping-ticket references and progress.

Not authorized:

- source or test edits;
- imports, builds, tests, database/store/telemetry commands, or migrations;
- provider, model, catalog, content, network, credential, or canary operations;
- raw artifact creation/retention, global-tool changes, release, or deployment;
- CLI/environment/public enablement, automatic persistence, or telemetry-v2
  changes; or
- activation/execution of an implementation child.

## What this supports

This evidence supports owner authority for the exact application-boundary
semantics and records-only graph. It does not prove implementation, receipt
validity, transport sends, provider billing, rate-limit use, canary execution,
or independent review of the new graph.

## Limits

The 40,001 and 40,002 values are validation reachability bounds established by
reviewed source, not permission to consume that many provider calls. Every live
canary still requires its own explicit operational authority and budget. The
new contract graph remains pending independent review before implementation may
activate.
