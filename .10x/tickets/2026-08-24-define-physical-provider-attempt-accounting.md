Status: blocked
Created: 2026-08-24
Updated: 2026-08-24
Parent: None
Depends-On: .10x/tickets/2026-08-24-run-local-telemetry-v2-canary.md
Knowledge: .10x/knowledge/provider-budgets-distinguish-logical-operations-and-transport-attempts.md

# Define Physical Provider Attempt Accounting

## Outcome

Shape a privacy-safe, testable contract for counting physical provider transport
attempts separately from logical namespace operations so future cost,
rate-limit, retry, and canary budgets can be proven without retaining query or
content data.

## Scope

- Enumerate every provider-attempt path reachable from retrieval, including the
  initial request, server-side-fusion compatibility fallback, optional-schema
  fallback, and any governed retry path.
- Decide whether the count belongs in production telemetry v2, a canary-only
  receipt/harness, provider-client diagnostics, or another focused surface.
- Define exact count semantics, lifecycle, failure handling, privacy fields,
  retention, and evidence requirements.
- Derive a focused specification and bounded executable implementation ticket
  before changing source or performing provider access.

## Acceptance criteria for shaping

- An active focused specification defines logical operations and physical
  attempts, including initial, fallback, retry, cancellation, and failure
  semantics.
- The selected observation boundary counts one attempt per provider client
  invocation and cannot silently collapse multiple attempts into one logical
  span.
- The contract persists or emits only content-free counts and governed reason
  categories; it excludes queries, argv, namespaces, credentials, content,
  provider responses, URLs, raw errors, stack traces, and private paths.
- Verification covers one-attempt success, two-attempt compatibility fallback,
  optional-schema fallback, error/cancellation behavior, and any reachable retry
  path without live provider dependence.
- Any future live canary defines and retains its physical-attempt receipt before
  consuming one-time authority or deleting temporary artifacts.

## Explicit exclusions

No implementation, schema change, live provider call, migration, retry of the
completed canary, global-tool change, release, or provider/catalog/content write
is authorized by this ticket.

## Blockers

- The owner has not selected the durable product surface: production telemetry,
  canary-only evidence, or provider-client diagnostics.
- Persistence/retention and compatibility requirements for a new count or
  receipt are not yet ratified.
- A focused specification does not yet exist.

## Progress and notes

- 2026-08-24: Opened from the local telemetry-v2 canary closure. Independent
  review proved that logical namespace spans cannot establish physical request
  count when compatibility or schema fallback is reachable. The owner directed
  closure under the logical-operation budget and separate tracking of this
  future observability work. No implementation or external operation is
  authorized.

## References

- `.10x/decisions/local-telemetry-canary-budgets-logical-namespace-operations.md`
- `.10x/evidence/2026-08-24-local-telemetry-v2-canary.md`
- `.10x/reviews/2026-08-24-local-telemetry-v2-canary-final-review.md`
- `src/buoy_search/retriever.py`
- `tests/test_retriever.py`
