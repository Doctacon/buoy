Status: recorded
Created: 2026-08-24
Updated: 2026-08-24
Target: commit e72841d2c4553c66f99be9f57efc1cd137fd543d, tree 8fea9db249214a6d633a7d34d2c014fbcd6e816b, src/buoy_search/_provider_invocation_receipt.py, src/buoy_search/retriever.py, tests/test_provider_invocation_receipt_content.py
Verdict: pass

# Provider Invocation Receipt Content Review

## Target and provenance

This durable record preserves the supplied independent PASS review of exact
source commit `e72841d2c4553c66f99be9f57efc1cd137fd543d`, tree
`8fea9db249214a6d633a7d34d2c014fbcd6e816b`.

The review inspected the content instrumentation, bounded core
transformed-cancellation repair, 23 focused content tests, both active provider-
invocation specifications, privacy/public/scope boundaries, and the attested
validation results. It was read-only and did not rerun the test suite.

## Historical review lineage

This PASS applies only to the final exact target and does not rewrite prior
verdicts or defect history:

- the historical contract FAIL remains at
  `.10x/reviews/2026-08-24-provider-client-invocation-contract-review.md` for
  exact records candidate `a458aeba95844230271ad50d4364281f4462ad5e`;
- the governing repaired-contract PASS remains separately recorded at
  `.10x/reviews/2026-08-24-provider-client-invocation-contract-rereview.md` for
  exact contract commit `cb4a76b97f68fcdfc2816c49c33b5b23e9b5f899`;
- the independently reviewed core predecessor remains separately closed at
  exact commit `8953e9336354f2a2e0604a54be9cd882a97a7985`, tree
  `66fb2d0dcca5d397132f60eb0be6d22a5b69479b`; and
- execution's discovery and authorized repair of transformed cancellation is
  preserved in the owning content ticket's append-only progress. It is not
  retroactively folded into or erased from the predecessor's review.

No earlier content-candidate review artifact exists in the record graph, so
this record does not invent or overwrite one.

## Findings

### Logical boundaries and invocation accounting

- `HybridRetriever.retrieve` begins route 1 only around the content operation at
  `src/buoy_search/retriever.py:718-725`; workers begin their ranked operation at
  `_retrieve_target` at lines 1322-1329. Pre-call failures therefore create
  zero-attempt terminal operations without counting embedding/model work.
- `_invoke_content_expression` registers before evaluating either exact SDK
  expression at lines 1855-1909, including local signature rejection. Server
  RRF preserves `rerank_by=("RRF",)`, client fallback omits it, and the two
  subqueries remain one invocation.
- Optional-schema trigger threading at lines 760-792, together with the two
  governed optional attributes, limits each route to three rounds and six
  attempts. Tests at
  `tests/test_provider_invocation_receipt_content.py:190-278,515-551` cover all
  lengths 1..6, one/two removals with and without client fallback, and the
  eighteen-attempt three-route maximum.

### Routes, outcomes, and transformed cancellation

- Focused tests cover explicit routes, CLI fanout, top-1 stopping, empty/failed
  widening without route repetition, reranker failures before first/later
  calls, partial/all failures, post-response failure, and zero-attempt failure
  at test lines 488-690.
- The bounded core change overrides outer exception classification only when the
  already-recorded final attempt is `interrupted` at
  `src/buoy_search/_provider_invocation_receipt.py:624-632`.
- The focused regression at test lines 449-484 proves the external sanitized
  `ProviderCallError` type, message, cause/context behavior, and one-call count
  remain baseline-equivalent while both attempt and operation are authoritative
  `interrupted`. Ordinary errors remain `error` at lines 300-341, 591-638, and
  673-690. The repair is the exact authorized core defect and does not widen
  other exception classification.

### Worker and observer failure isolation

- Receipt lease binding is composed with, not substituted for, the existing
  telemetry callable at source lines 1277-1284.
- Tests at lines 515-551 and 757-846 cover concurrent deterministic route
  ordering, non-copying of unrelated context, submission failure, lease
  registration/claim/release faults, bind/reset faults, and identical worker
  interruption propagation.
- Missing operation registration and observer-access/ledger faults execute the
  original expression once and invalidate only receipt authority at source
  lines 1855-1878 and test lines 342-390, 700-829.

### Privacy and scope

- Receipt bytes contain only fixed route/attempt enums and sanitized categories.
  Sentinel tests at lines 392-414 exclude query, namespace, content, path,
  provider detail, raw error, schema attribute, and SDK keyword data.
- Inspection found no catalog, CLI activation, environment, package-public API,
  persistence, telemetry schema, provider/model/store, routing, or ranking
  widening.

### Acceptance and spec coherence

All seven owning-ticket acceptance criteria map to exact source and focused
tests in
`.10x/evidence/2026-08-24-provider-invocation-receipt-content-closure.md`,
including the separately authorized transformed-cancellation core defect.

Both active provider-invocation specifications match the reviewed
implementation. Exact content expression boundaries, route/attempt grammar,
operation outcomes, explicit worker propagation, private lifecycle, privacy,
and observer-failure isolation are neither narrowed nor contradicted.

## Verdict

**PASS.** Exact commit `e72841d2c4553c66f99be9f57efc1cd137fd543d`,
tree `8fea9db249214a6d633a7d34d2c014fbcd6e816b`, satisfies every content-ticket
acceptance criterion. Blocker: none. Exact repairs required: none.

## Residual risk and limits

Validation is attested in the owning ticket. Its counts are internally
consistent: 45 core plus 23 content tests equals 68. Exact shell commands and raw
output were not retained, and this independent review did not rerun them.

The PASS is fake-only and application-boundary-only. It does not prove live SDK
or provider behavior, SDK-internal retries, physical wire sends, billing, cost,
or rate-limit use. Catalog instrumentation, integrated CLI wiring/final
repository validation, and the separately authorized live canary remain outside
this ticket and under their own gates.
