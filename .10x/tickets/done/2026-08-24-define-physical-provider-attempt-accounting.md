Status: done
Created: 2026-08-24
Updated: 2026-08-24
Parent: .10x/tickets/done/2026-08-24-improve-retrieval-telemetry-actionability.md
Depends-On: .10x/tickets/done/2026-08-24-run-local-telemetry-v2-canary.md
Knowledge: .10x/knowledge/provider-budgets-distinguish-logical-operations-and-transport-attempts.md
Research: .10x/research/2026-08-24-physical-provider-attempt-accounting-options.md
Prior-Review: .10x/reviews/2026-08-24-physical-provider-attempt-accounting-shaping-rereview.md
Authorization: .10x/evidence/2026-08-24-provider-client-invocation-receipt-authorization.md
Decision: .10x/decisions/buoy-uses-private-canary-provider-invocation-receipts.md
Accounting: .10x/specs/provider-client-invocation-accounting.md
Lifecycle: .10x/specs/provider-client-invocation-receipt.md
Implementation-Plan: .10x/tickets/2026-08-24-implement-private-provider-invocation-receipts.md
Prior-Contract-Review: .10x/reviews/2026-08-24-provider-client-invocation-contract-review.md
Contract-Review: .10x/reviews/2026-08-24-provider-client-invocation-contract-rereview.md

# Define Physical Provider Attempt Accounting

## Outcome

Record and independently review the owner-ratified privacy-safe contract for
counting Buoy SDK call attempts (`provider_client_invocation`) separately from
logical namespace operations, without misrepresenting that application-boundary
count as physical wire sends, provider cost, or rate-limit usage. Actual wire
accounting remains unresolved.

## Scope

- Enumerate every Buoy SDK call-attempt path reachable from retrieval, including
  the initial request, server-side-fusion compatibility fallback, optional-
  schema fallback, and any governed retry path.
- Decide whether the count belongs in recurring production telemetry under a
  separately specified compatible schema, a canary-only receipt/harness,
  provider-client diagnostics, or another focused surface. Active telemetry v2
  is exact and non-extensible.
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

None. The owner-ratified semantics are active, all five shaping criteria map to
durable records, and independent rereview
`.10x/reviews/2026-08-24-provider-client-invocation-contract-rereview.md`
passed exact repair commit `cb4a76b97f68fcdfc2816c49c33b5b23e9b5f899`.
Implementation remains separate open/inactive work and is not a closure blocker.

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
- 2026-08-24: Independent rereview
  `e91d4f44-e594-4d62-a282-d63236cd0581` returned PASS for repaired commit
  `0ed20c4d2d68a4a823f689b372095e777a48d459`. The prior FAIL remains truthful
  for its original candidate, and all four findings are repaired. Rereview is
  recorded at
  `.10x/reviews/2026-08-24-physical-provider-attempt-accounting-shaping-rereview.md`.
  Closure reconciliation corrected the candidate-surface wording: active v2 is
  exact/non-extensible, so the alternative is recurring production telemetry
  only under a separately specified compatible schema. The ticket remained
  blocked on exactly the five owner decisions above; no specification or
  executable ticket was active at that checkpoint.
- 2026-08-24: The owner explicitly ratified all five reviewed decisions plus the
  private activation/delivery boundary. Exact authority is recorded in
  `.10x/evidence/2026-08-24-provider-client-invocation-receipt-authorization.md`.
  The active ADR selects a default-off private in-process scope returning only a
  validated canonical receipt to an authorized harness, with no CLI/env/public
  API, automatic persistence, telemetry-v2 extension, or recurring retention
  change. Two active focused specs now separate call-attempt accounting from
  private receipt lifecycle. A non-executable implementation parent and four
  bounded open/inactive children own core/scope, content, catalog, and integrated
  validation. This shaping ticket is active pending independent review of the
  exact records-only contract commit; no source/test or operational work ran.
- 2026-08-24: Independent contract review
  `29dbeef6-82a2-43b1-8fd3-b572f0d83f40` returned FAIL for candidate
  `a458aeba95844230271ad50d4364281f4462ad5e`. The review is recorded at
  `.10x/reviews/2026-08-24-provider-client-invocation-contract-review.md` and
  found three significant mechanical gaps: weak aggregate catalog source-order
  validation, ambiguous cancellation precedence, and ambient widening risk in
  the shared catalog reader. The active specs now require per-category maxima
  plus exact L1 -> metadata -> card1 -> card2 -> L2 prerequisites; explicit
  cancellation/control-flow precedence with identical-exception tests; and a
  default-null private observer propagated only by automatic retrieve. The
  integration child owns final CLI-byte review and exact schema-v3 CLI-hash-only
  recertification. Owner semantics are unchanged. Ticket remains active pending
  fresh independent rereview; no source/test or operational work ran.
- 2026-08-24: Independent rereview
  `a4331cfc-d12b-4209-8e5a-8cb66655cf76` returned PASS for exact repair commit
  `cb4a76b97f68fcdfc2816c49c33b5b23e9b5f899`, tree
  `d0aa9598cbcc28bb35c16dd51d614980321abaad`. The historical FAIL remains
  truthful for `a458aeba`; all three significant findings are repaired. Closure
  reconciliation mapped all five criteria, confirmed active specs and the open/
  inactive implementation graph, and moved this ticket to `done`. No source,
  test, build, provider/model/catalog/content, store, telemetry, network,
  credential, canary, release, CLI-recertification, or global-tool operation
  occurred.

## Acceptance mapping

1. **Unit and paths — satisfied.** Reviewed research
   `.10x/research/2026-08-24-physical-provider-attempt-accounting-options.md`
   and active `.10x/specs/provider-client-invocation-accounting.md` define
   logical operations and every governed SDK-call expression, including
   compatibility/schema fallback, exact cancellation precedence, failure, and
   the absence of a generic content retry, while excluding wire/cost/rate-limit
   claims.
2. **Increment boundary — satisfied.** The accounting spec requires one
   increment immediately before call-expression evaluation and counts local
   signature rejection even without SDK method-body entry. Independent PASS
   rereview confirms the repaired contract is regeneration-grade.
3. **Privacy — satisfied.** Both active specs use exact bounded, content-free
   models and prohibit query, argv, namespace/provider/card identity,
   credentials, content/payload, URL/path, billing, raw error/stack, timestamp,
   and ambient context. Catalog retains aggregates only; content identity is
   route rank only.
4. **Provider-free verification contract — satisfied.** The open/inactive core,
   content, catalog, and integration children define fake-only tests for one-call
   success, two-call compatibility fallback, optional-schema fallback, exact
   error/interruption identity, source-order catalog validation, retries/fanout,
   privacy, and observer failure without live provider dependence.
5. **Future canary authority — satisfied.** The receipt spec makes absent,
   incomplete, invalid, or observer-failed receipt unknown; permits indefinite
   retention only of canonical sanitized bytes bound to durable canary evidence;
   requires raw-artifact deletion; and requires separate authority/budget for
   any canary. Actual transport evidence remains a separately excluded boundary.

## Retrospective

- Aggregate maxima are insufficient when privacy removes stage IDs; a validator
  must encode an ordered source-reachable state machine and reject ambiguous
  aggregates as unknown.
- A shared provider helper must receive observation as an explicit default-None
  capability from the authorized caller; ambient scope lookup silently widens
  product semantics.
- Exception taxonomy must account for inheritance: cancellation classes are
  named before generic `Exception`, and identical-object propagation is an
  acceptance requirement.
- Two focused specs are the minimal durable split: accounting owns unit/data/
  source order, while receipt lifecycle owns activation/authority/retention.
- Actual wire, billing, and rate-limit evidence remains intentionally excluded.
  No follow-up is opened because the owner ratified the SDK-call unit and has
  not requested transport-boundary work; such work requires new shaping and
  authority.

## References

- `.10x/decisions/local-telemetry-canary-budgets-logical-namespace-operations.md`
- `.10x/evidence/2026-08-24-local-telemetry-v2-canary.md`
- `.10x/reviews/2026-08-24-local-telemetry-v2-canary-final-review.md`
- `src/buoy_search/retriever.py`
- `src/buoy_search/remote_catalog.py`
- `tests/test_retriever.py`
- `tests/test_multi_namespace_retrieval.py`
- `tests/test_remote_catalog.py`
- `.10x/evidence/2026-08-24-provider-client-invocation-receipt-authorization.md`
- `.10x/decisions/buoy-uses-private-canary-provider-invocation-receipts.md`
- `.10x/specs/provider-client-invocation-accounting.md`
- `.10x/specs/provider-client-invocation-receipt.md`
- `.10x/tickets/2026-08-24-implement-private-provider-invocation-receipts.md`
