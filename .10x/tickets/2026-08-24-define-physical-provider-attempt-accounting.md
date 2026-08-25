Status: blocked
Created: 2026-08-24
Updated: 2026-08-24
Parent: .10x/tickets/2026-08-24-improve-retrieval-telemetry-actionability.md
Depends-On: .10x/tickets/done/2026-08-24-run-local-telemetry-v2-canary.md
Knowledge: .10x/knowledge/provider-budgets-distinguish-logical-operations-and-transport-attempts.md
Research: .10x/research/2026-08-24-physical-provider-attempt-accounting-options.md

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

Source-only shaping is complete, but the semantic contract is not ratified.
The owner must confirm or correct:

1. whether the governed unit is each entered Buoy-to-SDK request method
   invocation (including local SDK rejection, excluding unknown SDK-internal
   retries) or actual HTTP sends;
2. whether the first product surface is the recommended canary-only terminal
   receipt or recurring production telemetry;
3. whether separately categorized automatic-catalog invocations are included
   alongside content invocations;
4. route-rank-only bounded content detail, aggregate catalog detail,
   count-before-entry, `success|error|interrupted`, and absent/incomplete
   receipt meaning unknown; and
5. indefinite retention of only the sanitized canary receipt with durable
   evidence, deletion of raw artifacts, and no recurring production retention
   or purge change.

No focused specification may become active and no executable implementation
ticket may open until these cost, lifecycle, privacy, and compatibility choices
are explicit.

## Progress and notes

- 2026-08-24: Opened from the local telemetry-v2 canary closure. Independent
  review proved that logical namespace spans cannot establish physical request
  count when compatibility or schema fallback is reachable. The owner directed
  closure under the logical-operation budget and separate tracking of this
  future observability work. No implementation or external operation is
  authorized.
- 2026-08-24: The outer-latency child closed after independent PASS review, so
  the parent sequence now permits source-only attempt-path and contract-option
  shaping. Product-surface, persistence, retention, compatibility,
  specification, implementation, and external-operation authority remain
  blocked.
- 2026-08-24: Completed source-only shaping at
  `.10x/research/2026-08-24-physical-provider-attempt-accounting-options.md`.
  One logical content operation can make 1..6 Buoy-to-SDK `multi_query`
  invocations; explicit/automatic fanout can reach three logical operations and
  therefore 1..18 content client invocations. Automatic routing also makes a
  separate bounded strong-read family: namespace-list pages, one metadata
  request, and two card-query passes. Repository source has no generic content
  retry, but locked SDK-internal HTTP retries remain unobservable. Recommended
  candidate: count source-owned SDK request-method entries, keep catalog/content
  separate, and emit a private canary-only sanitized terminal receipt first.
  Ticket remains blocked on the five explicit semantic decisions above; no
  specification, implementation, source/test edit, or external operation was
  authorized.

## References

- `.10x/decisions/local-telemetry-canary-budgets-logical-namespace-operations.md`
- `.10x/evidence/2026-08-24-local-telemetry-v2-canary.md`
- `.10x/reviews/2026-08-24-local-telemetry-v2-canary-final-review.md`
- `src/buoy_search/retriever.py`
- `tests/test_retriever.py`
