Status: blocked
Created: 2026-06-20
Updated: 2026-06-20
Parent: .loom/tickets/2026-06-20-minimize-turbopuffer-rag-cost-plan.md
Depends-On: .loom/tickets/2026-06-20-cost-optimized-turbopuffer-schema-and-retrieval.md, .loom/tickets/2026-06-20-query-and-eval-cost-guardrails.md

# Cost-optimized live reindex and cutover

## Scope

If explicitly approved, write a cheaper replacement namespace and cut over retrieval to it.

In scope after approval:

- Present final preflight estimate: namespace name, rows, estimated logical bytes, batch count, max validation queries, and rollback/delete plan.
- Retrieve API key into shell memory only.
- Write the replacement namespace with optimized schema and batch sizing.
- Verify row count/schema with the minimum necessary non-secret calls.
- Run no more than the approved number of live validation queries.
- Update docs/config defaults to point at the replacement namespace if accepted.
- Delete or retain the old namespace according to the user's explicit choice.

Out of scope unless separately approved:

- Multiple eval sweeps.
- Repeated tuning writes.
- Namespace copies.
- Persisting credentials.

## Acceptance criteria

- The ticket contains the user's explicit approval and budget before any live action.
- Evidence records sanitized write/query verification and observed dashboard deltas if available.
- The old namespace state is intentional: either deleted or retained with reason.
- No secrets are committed or written to Loom.

## Progress and notes

- 2026-06-20: Ticket opened blocked. No live calls made.

## Blockers

- User must approve live reindex/cutover budget and namespace strategy.
