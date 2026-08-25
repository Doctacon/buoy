Status: blocked
Created: 2026-08-24
Updated: 2026-08-24
Parent: .10x/tickets/2026-08-24-improve-retrieval-telemetry-actionability.md
Depends-On: .10x/tickets/done/2026-08-24-run-local-telemetry-v2-canary.md
Knowledge: .10x/knowledge/provider-budgets-distinguish-logical-operations-and-transport-attempts.md
Research: .10x/research/2026-08-24-physical-provider-attempt-accounting-options.md

# Define Physical Provider Attempt Accounting

## Outcome

Shape a privacy-safe, testable contract for counting Buoy SDK call attempts
(`provider_client_invocation`) separately from logical namespace operations,
without misrepresenting that application-boundary count as physical wire sends,
provider cost, or rate-limit usage. Actual wire accounting remains unresolved.

## Scope

- Enumerate every Buoy SDK call-attempt path reachable from retrieval, including
  the initial request, server-side-fusion compatibility fallback, optional-
  schema fallback, and any governed retry path.
- Decide whether the count belongs in production telemetry v2, a canary-only
  receipt/harness, provider-client diagnostics, or another focused surface.
- Define exact count semantics, lifecycle, failure handling, privacy fields,
  retention, and evidence requirements.
- Derive a focused specification and bounded executable implementation ticket
  before changing source or performing provider access.

## Acceptance criteria for shaping

- An active focused specification defines logical operations and
  `provider_client_invocation` SDK call attempts, including initial, fallback,
  retry, cancellation, and failure semantics, while excluding physical-wire,
  cost, and rate-limit claims.
- The selected observation boundary increments once immediately before Buoy
  evaluates each governed SDK call expression and cannot silently collapse
  multiple attempts into one logical span. A local signature `TypeError` after
  increment counts even if SDK method-body entry never occurs.
- The contract persists or emits only content-free counts and governed reason
  categories; it excludes queries, argv, namespaces, credentials, content,
  provider responses, URLs, raw errors, stack traces, and private paths.
- Verification covers one-attempt success, two-attempt compatibility fallback,
  optional-schema fallback, error/cancellation behavior, and any reachable retry
  path without live provider dependence.
- Any future live canary defines and retains its
  `provider_client_invocation` receipt before consuming one-time authority or
  deleting temporary artifacts. A physical wire-send budget requires separate
  transport-boundary evidence.

## Explicit exclusions

No implementation, schema change, live provider call, migration, retry of the
completed canary, global-tool change, release, or provider/catalog/content write
is authorized by this ticket.

## Blockers

Source-only shaping is complete, but the semantic contract is not ratified.
The owner must confirm or correct:

1. whether the governed unit is `provider_client_invocation`: each Buoy SDK call
   attempt counted immediately before call-expression evaluation, including
   local signature rejection and excluding unknown SDK-internal retries; if the
   requirement is actual HTTP sends, provider cost, or rate-limit usage, whether
   to authorize separate transport-boundary research instead;
2. whether the first product surface is the recommended canary-only terminal
   receipt or recurring production telemetry;
3. whether separately categorized automatic-catalog invocations are included
   alongside content invocations;
4. route-rank-only bounded content detail, aggregate catalog detail, the
   40,001-success/40,002-terminal-failure catalog bounds, increment-before-call-
   expression semantics, `success|error|interrupted`, and absent/incomplete
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
  One logical content operation can make 1..6 Buoy-to-SDK `multi_query` call
  attempts. CLI explicit-multi fanout is 2..3 (2..18 attempts); generic
  `MultiNamespaceRetriever` and automatic contexts are 1..3 (1..18 attempts).
  Automatic routing also makes a separate bounded strong-read family:
  namespace-list pages, one metadata request, and two card-query passes.
  Repository source has no generic content retry, but locked SDK-internal HTTP
  retries remain unobservable. Recommended candidate: increment a
  `provider_client_invocation` immediately before each source-owned SDK call
  expression, keep catalog/content separate, and emit a private canary-only
  sanitized terminal receipt first. Ticket remains blocked on the five explicit
  semantic decisions above; no specification, implementation, source/test edit,
  or external operation was authorized.
- 2026-08-24: Independent review run
  `f17899d7-59f5-43c0-b8f9-66e68f844887` returned FAIL on four source/semantic
  inaccuracies. Records-only repair now distinguishes the 40,001 maximum
  successful catalog read from the 40,002 terminal bounded-failure path,
  explicit-multi CLI fanout 2..3 from generic 1..3 retriever context, call-
  expression increment from SDK method-body entry, and Buoy SDK call attempts
  from unproven wire sends/cost/rate-limit usage. Ticket remains blocked pending
  fresh independent review and owner decisions; no specification or executable
  ticket exists.

## References

- `.10x/decisions/local-telemetry-canary-budgets-logical-namespace-operations.md`
- `.10x/evidence/2026-08-24-local-telemetry-v2-canary.md`
- `.10x/reviews/2026-08-24-local-telemetry-v2-canary-final-review.md`
- `src/buoy_search/retriever.py`
- `tests/test_retriever.py`
