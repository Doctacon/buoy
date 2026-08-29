Status: active
Created: 2026-08-28
Updated: 2026-08-28
Decision: .10x/decisions/buoy-records-worker-and-provider-attempt-retrieval-telemetry-v3.md
Accounting: .10x/specs/provider-client-invocation-accounting.md
Canary-Lifecycle: .10x/specs/provider-client-invocation-receipt.md
Storage: .10x/specs/local-telemetry-v3-storage-and-migration.md

# Retrieve Provider Invocation Telemetry V3

## Purpose and scope

This specification persists privacy-safe `provider_client_invocation` accounting for effective schema-v3 `buoy retrieve` command telemetry. It reuses the established governed call sites, unit, outcomes, bounds, concurrency, and canonical validation in `.10x/specs/provider-client-invocation-accounting.md` without changing provider behavior.

A provider client invocation is one Buoy SDK call-expression attempt. It includes local signature rejection and excludes invisible SDK-internal retries. V3 MUST NOT describe it as an HTTP request, wire send, billed operation, or rate-limit unit.

## Activation and authority

When and only when command telemetry is effective and the dispatched handler is `retrieve`, the command enters one private provider-receipt scope before any automatic catalog or live content call and exits it after the handler's provider work is terminal. The scope is not entered for disabled telemetry, parser/help/non-retrieve commands, or direct-library v1 traces.

The existing capability-explicit automatic-catalog observer and thread-worker lease propagation remain exact. Apply, catalog-management, crawl, plan, eval, direct catalog reads, and direct retriever calls remain unobserved by this production surface.

After the scope seals, the producer obtains canonical validated receipt bytes from the existing handle and converts them into the exact v3 provider summary. The receipt itself is not written as a separate file. Missing, incomplete, observer-failed, or invalid receipt records accounting status `unavailable`; it MUST NOT invent zero counts. A valid receipt with no reached provider expression records `complete` with exact zeros.

Instrumentation failure cannot change SDK arguments/order/cardinality, result/exception identity, routing, fallback, output, telemetry-independent receipt behavior, or provider/model work.

## Envelope provider summary

The v3 envelope contains required object `provider_accounting` with exact keys:

```text
status          complete | unavailable
unit            provider_client_invocation
content         null | validated content object
catalog         null | validated catalog object
```

`unit` is always the literal above. `status=complete` requires `content` and `catalog` to be the exact validated objects from receipt schema 1. `status=unavailable` requires both null. The complete objects retain only fields already ratified in `.10x/specs/provider-client-invocation-accounting.md`:

- content: logical operation count, total invocation count, route-rank-only operations, ordered attempt index, request form, fallback trigger, outcome, and bounded error category;
- catalog: operation outcome, total invocation count, and aggregate success/error/interrupted counts for namespace-list pages, metadata, and card-query pages.

All existing maxima and source-order validation remain exact: at most three content operations, six attempts per operation, eighteen total content attempts, 40,001 successful complete catalog attempts, and 40,002 terminal catalog attempts.

Command success does not imply accounting complete. Accounting complete does not imply provider success. The command's original outcome remains authoritative for product behavior.

## Storage rows and analytical views

A valid complete summary inserts in the same transaction as its command trace:

1. one `retrieve_provider_accounting_v3` row per command;
2. zero through three `retrieve_provider_content_operations_v3` rows;
3. zero through eighteen `retrieve_provider_content_invocations_v3` rows; and
4. one `retrieve_provider_catalog_v3` row.

An unavailable summary inserts only its one accounting row with `status=unavailable`; no operation/invocation/catalog row is allowed.

The stable `retrieval_provider_summary_v3` view exposes one command row with:

```text
trace_id
command_started_at
execution_mode
retrieval_mode
command_outcome
accounting_status
unit
content_logical_operation_count
content_invocation_count
content_success_count
content_error_count
content_interrupted_count
server_rrf_count
client_rrf_count
optional_schema_compatibility_count
catalog_outcome
catalog_invocation_count
catalog_namespace_list_page_count
catalog_metadata_count
catalog_card_query_page_count
catalog_success_count
catalog_error_count
catalog_interrupted_count
```

Counts are null when accounting is unavailable and nonnegative when complete.

`retrieval_provider_content_invocations_v3` exposes one row per validated content attempt with command identity, route rank, attempt index, request form, trigger, outcome, and nullable bounded error category. It contains no namespace identity or provider timing.

No separate per-attempt span is created. The receipt proves cardinality/outcome, not timestamps; fabricating attempt timings would be false precision. Existing `buoy.namespace.query` and `buoy.routing.catalog` spans remain the logical timing boundaries.

## Privacy and retention

The strict retrieval telemetry privacy contract applies to every provider object and row. In particular, provider telemetry MUST NOT retain namespace/provider/resource identity, request/response payload, query/subquery, vector, content, optional attribute name, page cursor, URL, status code, billing/rate-limit data, retry header, credential, raw error, traceback, SDK class/module, timing inferred for individual attempts, or canary authorization data.

Rows follow the local telemetry store's existing indefinite user-owned retention until a separately approved purge policy exists. The private standalone canary receipt lifecycle remains unchanged; ordinary telemetry does not create evidence files or raw archives.

## Acceptance scenarios

1. Explicit single success with one server-RRF call persists one route-rank-1 successful attempt and zero catalog calls.
2. Server-RRF signature fallback persists server/client attempts with exact trigger/outcome while provider call count and output remain unchanged.
3. Optional-schema fallback persists exact ordered rounds through the six-attempt bound.
4. Explicit multi and automatic concurrency persist contiguous route/attempt order independent of thread interleaving.
5. Automatic preview persists catalog calls and zero content operations; explicit preview persists exact zeros.
6. Automatic live persists separate catalog and content families; minimum complete fake catalog read has five attempts.
7. Provider/local processing failure and interruption preserve exact receipt semantics; unavailable authority records unknown rather than zero.
8. Disabled telemetry creates no receipt scope, observer, lease, callback, row, queue artifact, process, filesystem, output, or provider change.
9. Apply/catalog/direct-library calls remain unobserved even if a private canary scope exists elsewhere.
10. Producer and writer independently reject unknown keys, impossible source order, overflows, booleans-as-integers, mixed terminal attempts, content/catalog mismatches, and noncanonical encoding before store mutation.
11. Privacy sentinels are absent byte-for-byte from envelope, inbox, receipt, writer state, scratch/backup, database scalars/JSON, status/migrate output, and diagnostics.
12. Provider-free fakes prove all call forms and failure paths before any live validation. Any live validation is read-only, uses a separately fixed lower budget within the owner's 20-call ceiling, and permits no provider write or automatic retry.

## Explicit exclusions

SDK-internal retries, HTTP/wire sends, billing/rate-limit accounting, DNS/TLS timing, provider identifiers, request/response capture, provider mutation, catalog-management accounting, public diagnostics callbacks, automatic canaries, default-on telemetry, v1/v2 observation changes, release, and publication are excluded.
