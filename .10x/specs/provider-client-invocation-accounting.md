Status: active
Created: 2026-08-24
Updated: 2026-08-28
Decision: .10x/decisions/buoy-records-worker-and-provider-attempt-retrieval-telemetry-v3.md
Lifecycle: .10x/specs/provider-client-invocation-receipt.md
Research: .10x/research/2026-08-24-physical-provider-attempt-accounting-options.md
Prior-Review: .10x/reviews/2026-08-24-provider-client-invocation-contract-review.md
Review: .10x/reviews/2026-08-24-provider-client-invocation-contract-rereview.md

# Provider Client Invocation Accounting

## Purpose and scope

This specification defines the application-boundary unit
`provider_client_invocation`, every governed content and automatic-catalog call
site, terminal outcomes, and the two exact family objects carried by a private
canary receipt.

A `provider_client_invocation` is one attempt by Buoy to invoke a governed SDK
call expression. Buoy MUST increment the attempt immediately before evaluating
the expression and MUST finalize its outcome after the expression returns or
raises. A local Python signature rejection therefore counts even when SDK
method-body entry never occurs. The unit excludes unobserved SDK-internal
retries and MUST NOT be represented as an HTTP/wire send, provider-billed
request, or rate-limit unit.

The content and catalog families MUST remain separate. This contract does not
extend production telemetry v1/v2. Private receipt activation, authority, and
serialization are governed by
`.10x/specs/provider-client-invocation-receipt.md`; separately approved v3
normalization and persistence are governed by
`.10x/specs/retrieve-provider-invocation-telemetry-v3.md`.

## Common call and outcome behavior

For every governed expression:

- observer state is updated immediately before expression evaluation;
- normal return records attempt outcome `success`;
- `asyncio.CancelledError` and `concurrent.futures.CancelledError` record
  `interrupted`; this check MUST precede the generic `Exception` rule because
  `concurrent.futures.CancelledError` is an `Exception`;
- `KeyboardInterrupt`, `SystemExit`, `GeneratorExit`, and every other
  `BaseException` that is not an `Exception` record `interrupted`;
- every other `Exception` records `error`; and
- the original return value or the identical exception object is passed through
  without replacement or wrapping by the observer;
- argument construction, validation, model work, resource acquisition, and a
  future that never reaches the expression count zero;
- response parsing, ranking, normalization, and other post-return work add no
  invocation; and
- observer failure invalidates the receipt best effort and then evaluates the
  original expression exactly once.

Compatibility and optional-schema fallbacks are separate Buoy SDK call
attempts. Source contains no generic content retry. An SDK-internal retry is
invisible and is not inferred.

The fixed content error-category mapping is mechanical sanitization, in this
precedence order:

1. an exception whose exact local type name is `ProviderCallError` becomes
   `provider_call_error`;
2. any other `ValueError` becomes `value_error`;
3. any other `RuntimeError` becomes `runtime_error`; and
4. every other ordinary exception becomes `unexpected_error`.

No class/module name, message, status, traceback, or provider detail is kept.
`success` and `interrupted` attempts require a null error category; `error`
requires exactly one category above. Catalog data keeps no error category.

## Content-family boundary

The governed expressions are the two source forms in
`run_multi_query`:

- `namespace.multi_query(queries=..., rerank_by=("RRF",))`, request form
  `server_rrf`; and
- the compatibility fallback `namespace.multi_query(queries=...)`, request form
  `client_rrf`.

The two ANN/BM25 subqueries passed to one expression count as one invocation.
The first server-RRF attempt has trigger `initial`. A client-RRF attempt is
permitted only immediately after a classified unsupported-rerank `TypeError`
and has trigger `server_rrf_unsupported`. After one governed optional retrieval
attribute is removed, the next outer iteration's server-RRF attempt has trigger
`optional_schema_compatibility`. At most two such removals occur, one per new
iteration.

Each begun logical content operation is identified only by one-based route
rank. Explicit single uses route rank 1. A multi-namespace target uses its
existing route rank. An active receipt scope that reaches a governed content
expression without a registered route operation MUST become unavailable rather
than invent an identity; the SDK expression still runs unchanged.

One logical operation has zero attempts only when it terminates before its first
SDK expression. Once reached, it has one through three outer iterations and one
or two attempts per iteration, for at most six attempts. A route is not queried
twice by widening. CLI explicit-multi begins two or three routes; generic
`MultiNamespaceRetriever` and automatic retrieval begin one through three.
An authoritative receipt has at most three operations and eighteen content
invocations.

An operation outcome is `success`, `error`, or `interrupted`. A successful
operation requires a final successful invocation. A terminal invocation error
makes the operation an error unless the exact governed fallback follows. An
interrupted invocation makes the operation interrupted. After a successful SDK
return, post-response processing can still make the operation outcome `error`
or `interrupted` without adding another invocation.

## Exact content object

The `content` object has exactly:

```text
logical_operation_count   integer 0..3
invocation_count          integer 0..18
operations                array length 0..3
```

Each operation has exactly:

```text
route_rank                integer 1..3
outcome                   success | error | interrupted
attempts                  array length 0..6
```

Each attempt has exactly:

```text
attempt_index             integer 1..6
request_form              server_rrf | client_rrf
trigger                   initial | server_rrf_unsupported |
                          optional_schema_compatibility
outcome                   success | error | interrupted
error_category            null | provider_call_error | value_error |
                          runtime_error | unexpected_error
```

Operations serialize in increasing route rank and MUST use contiguous ranks
`1..logical_operation_count`. Attempts serialize in increasing contiguous
`attempt_index`. Counts equal array lengths and their sum. Attempt arrays MUST
match this grammar:

1. every outer iteration begins with `server_rrf`; the first trigger is
   `initial` and later triggers are `optional_schema_compatibility`;
2. a round MAY contain one immediately following `client_rrf` with trigger
   `server_rrf_unsupported` only when the server attempt is an `error` with
   `unexpected_error` (the sanitized local `TypeError` category);
3. another outer iteration MAY follow only an `error` that triggered removal of
   one governed optional attribute; at most two later rounds occur;
4. an invocation `success` or `interrupted` is final in the attempt array; and
5. a zero-attempt operation may be only `error` or `interrupted`; operation
   `success` requires a nonempty array whose final attempt is `success`.

If the final attempt is `error`, operation outcome MUST be `error`; if it is
`interrupted`, operation outcome MUST be `interrupted`. If it is `success`,
post-return work permits any terminal operation outcome.

These route and invocation maxima are validator reachability limits, not
operational budgets or permission for a canary to reach them.

## Automatic-retrieve-only catalog boundary

Only automatic retrieve's strong `read_remote_catalog` call is governed. The
shared reader is also called by apply and catalog-management code, so receipt
scope activation alone MUST NOT cause catalog observation.

`read_remote_catalog` MUST accept one private observer/ledger argument whose
default is `None`. It MUST propagate that exact explicit argument through both
namespace-list helpers, metadata observation, and both card-pass helpers. Those
shared remote-catalog functions MUST NOT read the receipt `ContextVar` or obtain
an active observer implicitly. Only the automatic-retrieve branch in
`src/buoy_search/cli.py` may obtain the active private observer from the receipt
scope and pass it. Apply, catalog CLI, direct-library, and every other caller
MUST omit the argument and remain unobserved even when a receipt scope is
active. The argument is an internal capability, not a public callback or new
enablement surface.

When that explicit observer is non-null, the governed expressions are:

- `namespace_list_page`: each initial `client.namespaces(...)` expression and
  each reached `page.get_next_page()` continuation across both list passes;
- `metadata`: the one reached `resource.metadata()` expression; and
- `card_query_page`: each reached `resource.query(...)` expression across both
  card-query passes.

Client construction, `client.namespace(...)` resource acquisition, response
normalization/iteration, eligibility work, catalog management calls, catalog
mutations, and every shared-reader call with the default `None` observer count
zero.

The source order is exact:

```text
L1: first namespace-list pass
M:  metadata call and schema validation
C1: first card-query pass
C2: second card-query pass
L2: second namespace-list pass
```

Each successfully completed list or card pass contains 1..10,000 successful
SDK expressions. `M` contains exactly one successful expression when complete.
A provider expression error/interruption terminates the read. Local
normalization, schema, consistency, or page-bound error/interruption can
terminate after a successful expression without changing that expression's
outcome.

A successful complete read therefore reaches:

- 2..20,000 successful `namespace_list_page` invocations, decomposable as
  completed `L1` and `L2`, each 1..10,000;
- exactly 1 successful `metadata` invocation; and
- 2..20,000 successful `card_query_page` invocations, decomposable as completed
  `C1` and `C2`, each 1..10,000.

Its total is 5..40,001. A terminal read has per-category maxima 20,001 list,
1 metadata, and 20,000 card invocations. The list maximum admits the final L2
continuation fetched after page 10,000 and before the next-loop bound check.
The 40,002 all-success terminal shape is exactly 20,001 list successes,
1 metadata success, and 20,000 card successes. These are validator reachability
limits, never operational budgets.

## Exact catalog object

The `catalog` object has exactly:

```text
outcome                   null | success | error | interrupted
invocation_count          integer 0..40,002
namespace_list_page       outcome-count object
metadata                  outcome-count object
card_query_page           outcome-count object
```

Each outcome-count object has exactly nonnegative integer keys:

```text
success
error
interrupted
```

Booleans are not integers. The nine counters MUST sum to `invocation_count`.
Across all three categories, the sum of `error` and `interrupted` MUST be at
most one. If one invocation is `error`, operation outcome MUST be `error`; if
one invocation is `interrupted`, operation outcome MUST be `interrupted`.
A terminal operation MAY contain only successful invocations when local work
fails or is interrupted after return.

Per-category cardinalities are:

| Category | Successful operation | Terminal operation |
| --- | --- | --- |
| `namespace_list_page` | success 2..20,000; error=interrupted=0 | total 0..20,001; error+interrupted at most 1 |
| `metadata` | success exactly 1; error=interrupted=0 | total 0..1 |
| `card_query_page` | success 2..20,000; error=interrupted=0 | total 0..20,000; error+interrupted at most 1 |

`outcome=null` means the catalog read was not begun and requires every counter
and `invocation_count` to be zero. A begun terminal read may have zero calls
only when it terminates before L1's first expression. `outcome=success` requires
all invocations successful, exact metadata success, both list/card minimums,
the two-pass decompositions above, and total at most 40,001.

## Aggregate source-order validator

Because the receipt intentionally retains no pass IDs, the validator MUST
accept an aggregate only when its counters admit the ordered source execution
`L1 -> M -> C1 -> C2 -> L2` under all rules below. It MUST reject an ambiguous
or impossible aggregate rather than infer private stage identity; rejection
makes the receipt unknown without affecting retrieval.

1. Any metadata invocation requires a completed successful L1 of 1..10,000
   list successes. Any card invocation requires that completed L1 and exactly
   one successful metadata invocation.
2. Aggregate list total greater than 10,000 is accepted as second-list reach
   only when metadata succeeded and card successes can be decomposed into two
   completed passes C1/C2, each 1..10,000. Thus list >10,000 with missing,
   failed, interrupted, or fewer than two successful card calls is invalid.
3. A metadata `error` or `interrupted` invocation is terminal: list calls MUST
   all be successful with total 1..10,000, and every card counter MUST be zero.
4. A card `error` or `interrupted` invocation is terminal: list calls MUST all
   be successful with total 1..10,000, metadata MUST be one success, card total
   MUST be 1..20,000, and no L2 call may be represented.
5. A list `error` or `interrupted` with no metadata/card calls is an L1 terminal
   and list total MUST be 1..10,000. A list `error` or `interrupted` after later
   categories is an L2 terminal: metadata MUST be one success, cards MUST be
   2..20,000 successes decomposable into completed C1/C2, and list total MUST be
   2..20,001. No other category may contain a terminal invocation.
6. With no invocation error/interruption, category presence still obeys the
   same prerequisites: metadata cannot appear without 1..10,000 prior L1
   successes; cards cannot appear without successful metadata; and list total
   >10,000 cannot appear without two completed successful card passes.
   Operation `error` or `interrupted` then represents local terminal work at or
   after the last source-reachable stage.
7. A success aggregate MUST be decomposable into L1/L2 list counts and C1/C2
   card counts, each 1..10,000, with metadata exactly one success. A terminal
   aggregate at the absolute 40,002 maximum MUST be exactly list 20,001,
   metadata 1, card 20,000; any other composition totaling 40,002 is invalid.
8. Mixed terminal invocations, a terminal invocation followed by evidence of a
   later stage, metadata/card without prerequisites, successful operation with
   a terminal invocation, any category overflow, and every total above 40,002
   are invalid.

The aggregate contract deliberately cannot authenticate an all-success 10,001-
call L1 page-bound failure without retaining pass identity: rule 2 rejects that
ambiguous shape unless successful metadata and two completed card passes prove
L2 reach. Such a source-reachable but non-authoritative aggregate yields unknown
rather than weakening source-order validation or adding pass IDs.

Catalog aggregation MUST NOT retain pass number, stage marker, cursor,
namespace/card/provider identifier, page content, response, billing, URL, error
detail, or timing.

## Concurrency and failure isolation

Concurrent route operations share only the explicitly propagated private
ledger. Each route receives an independent contiguous attempt sequence;
interleaving MUST NOT affect canonical route/attempt ordering. A submitted
worker that does not run makes final receipt authority unavailable rather than
fabricating a zero-attempt terminal operation.

Instrumentation MUST preserve SDK call arguments and order, fallback
classification, pagination and strong-read duplication, exception identity,
result identity, thread scheduling decisions, routing/widening, telemetry,
output, and provider/model work. It MUST NOT add retries, resubmit/cancel a
route, skip/repeat a page, or turn a processing failure into an invocation
failure.

## Acceptance scenarios

1. One server-RRF return produces one successful content attempt.
2. Unsupported local signature `TypeError` plus client-RRF return produces two
   attempts even if SDK method-body entry did not occur for the first.
3. One and two optional-schema fallbacks, with and without client-RRF fallback,
   validate the exact round grammar and 1..6 bound.
4. `asyncio.CancelledError`, `concurrent.futures.CancelledError`,
   `KeyboardInterrupt`, `SystemExit`, `GeneratorExit`, and another custom
   non-`Exception` `BaseException` are interrupted; representative remaining
   `Exception` types are errors; every case re-raises the identical object.
5. Unrelated error, post-response failure, zero-attempt begun operation,
   explicit/automatic fanout, and concurrent route ordering preserve exact
   outcomes without provider access.
6. A minimum complete catalog read produces five successes; multipage fakes
   produce exact aggregate categories and two-pass decompositions.
7. Validator tables cover every per-category boundary and reject metadata/card
   without prerequisites, second-list-scale counts without successful metadata
   and two completed card passes, terminal calls followed by later-stage
   evidence, mixed terminal calls, and impossible 40,002 compositions.
8. A successful catalog outcome validates through 40,001. The exact
   list=20,001/metadata=1/card=20,000 all-success terminal shape validates at
   40,002; a successful 40,002 and every total above 40,002 reject.
9. Only automatic retrieve with an explicitly passed private observer records
   catalog calls. Apply, catalog-management, direct-library, and default-`None`
   calls remain zero even inside an active receipt scope.
10. Constructor/resource acquisition and response processing add zero.
11. Exact-key, type, enum, count, sequence, privacy, disabled, and observer-fault
    tests use local fakes only.

## Explicit exclusions

Physical wire/cost/rate-limit accounting, SDK-internal retry accounting,
production telemetry v1/v2, public diagnostics, changed provider/network
operations, catalog writes/management accounting, generic content retries,
routing changes, release, and canary execution are excluded. Separately
specified v3 normalization/persistence of these exact validated fields is not
governed here.
