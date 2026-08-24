Status: recorded
Created: 2026-08-24
Updated: 2026-08-24
Relates-To: .10x/tickets/2026-08-24-run-local-telemetry-v2-canary.md, .10x/decisions/local-telemetry-canary-budgets-logical-namespace-operations.md, .10x/tickets/2026-08-24-define-physical-provider-attempt-accounting.md

# Local Telemetry V2 Canary Closure Authorization

## What was observed

After independent review blocked closure, the owner asked what the canary was
trying to prove and why a six-physical-call limit mattered. The parent explained
that the substantive objective was safe real-store migration plus correct,
private command/pipeline telemetry across four modes; those criteria passed.
The six-call bound had been introduced as a cost/side-effect guardrail based on
one explicit-single, two explicit-multi, and up to three automatic logical
namespace operations.

The parent explicitly distinguished two interpretations:

- at most six logical namespace operations, which the five retained spans prove;
- at most six physical provider attempts, which retained evidence cannot prove
  because a compatibility fallback may occur inside one span.

The parent recommended treating the operational canary as passed under the
logical-operation interpretation, performing no rerun, and separately tracking
physical transport-attempt counting for future cost/rate-limit observability.
The owner replied: “yes do that.”

## What this supports

The owner ratified all of the following together:

1. This canary's six-call acceptance unit is logical namespace operations, not
   lower-level physical transport attempts.
2. Five retained `buoy.namespace.query` spans satisfy that bounded criterion.
3. Closure may proceed through records-only reconciliation and fresh independent
   review without rerunning migration, retrieval, flush, provider/model, or
   telemetry-management operations.
4. Physical-attempt counting remains a separately tracked future concern rather
   than a blocker for this canary.

## Limits

This authorization does not establish the completed canary's physical provider
attempt count. It does not authorize implementation of the follow-up, another
canary, provider access, migration, telemetry mutation, global-tool change,
release work, or external state mutation. The original one-time execution
authority remains consumed.
