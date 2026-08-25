Status: active
Created: 2026-08-24
Updated: 2026-08-24
Decision: .10x/decisions/buoy-uses-private-canary-provider-invocation-receipts.md
Lifecycle: .10x/specs/provider-client-invocation-receipt.md
Research: .10x/research/2026-08-24-physical-provider-attempt-accounting-options.md

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
extend production telemetry v2; receipt activation, authority, serialization,
and retention are governed by
`.10x/specs/provider-client-invocation-receipt.md`.

## Common call and outcome behavior

For every governed expression:

- observer state is updated immediately before expression evaluation;
- normal return records attempt outcome `success`;
- a raised ordinary exception records `error`, except that a cancellation or
  control-flow interruption records `interrupted`;
- `KeyboardInterrupt`, `SystemExit`, `GeneratorExit`, and cancellation
  exceptions are interruptions; other `Exception` instances are errors;
- the original return value or the identical exception is passed through;
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

## Catalog-family boundary

Only automatic retrieval's strong `read_remote_catalog` path is governed:

- `namespace_list_page`: each initial `client.namespaces(...)` expression and
  each reached `page.get_next_page()` continuation across both list passes;
- `metadata`: the one reached `resource.metadata()` expression; and
- `card_query_page`: each reached `resource.query(...)` expression across both
  card-query passes.

Client construction, `client.namespace(...)` resource acquisition, response
normalization/iteration, eligibility work, catalog management calls, and
catalog mutations count zero.

A successful complete strong read processes at most 10,000 pages in each of
four passes and one metadata expression, so its validator limit is 40,001. A
terminal `error` or `interrupted` read may reach 40,002: the second namespace-
list pass can successfully fetch the continuation after page 10,000 before the
next-loop bound check fails. Therefore 40,002 may consist entirely of successful
SDK expressions. The operation outcome, not invocation outcome totals, selects
the 40,001 versus 40,002 validator bound. Neither value is an operational
budget.

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

The nine counters sum to `invocation_count`; booleans are not integers.
`metadata` totals zero or one. Across the family at most one invocation may be
`error` or `interrupted`, because either stops the strong read. If an invocation
is `error`, operation outcome MUST be `error`; if an invocation is
`interrupted`, operation outcome MUST be `interrupted`.

`outcome=null` means the catalog read was not begun and requires all counters
and `invocation_count` to be zero. A begun read has a non-null outcome and may
have zero calls only if it terminates before the first governed expression. A
`success` read requires at least two successful namespace-list calls, exactly
one successful metadata call, at least two successful card-query calls, no
error/interrupted calls, and at most 40,001 total invocations. An `error` or
`interrupted` read permits zero through 40,002 invocations, including successful
calls followed by local post-return or page-bound failure/interruption.

Catalog aggregation MUST NOT retain pass number, cursor, namespace/card/provider
identifier, page content, response, billing, URL, error detail, or timing.

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
4. Unrelated error, cancellation/control-flow interruption, post-response
   failure, zero-attempt begun operation, explicit/automatic fanout, and
   concurrent route ordering preserve exact outcomes without provider access.
5. A minimum complete catalog read produces five successes; multipage fakes
   produce exact aggregate categories.
6. A successful catalog outcome validates through 40,001. A terminal local
   page-bound failure with 40,002 successful expressions validates, while a
   successful 40,002 and every total above 40,002 reject.
7. Constructor/resource acquisition and response processing add zero.
8. Exact-key, type, enum, count, sequence, privacy, disabled, and observer-fault
   tests use local fakes only.

## Explicit exclusions

Physical wire/cost/rate-limit accounting, SDK-internal retry accounting,
production telemetry, public diagnostics, provider/network operations, catalog
writes/management accounting, generic content retries, routing changes,
telemetry-v2 changes, release, and canary execution are excluded.
