Status: done
Created: 2026-08-24
Updated: 2026-08-24

# Physical Provider Attempt Accounting Options

## Question

Which source-reachable provider calls can one retrieval make, what boundary can
Buoy truthfully count without retaining private retrieval data, and where
should that count live?

## Sources and methods

This source-only investigation used exact task commit
`f386074bb0ae2e9dc6354be0d1937e394d8b3dfb`, tree
`1f4fed94445c67275a24106ed43f91f5bcf9c21a`. It inspected:

- `src/buoy_search/retriever.py` and `src/buoy_search/cli.py`;
- `src/buoy_search/remote_catalog.py`;
- `src/buoy_search/telemetry.py`, `telemetry_envelope.py`, and
  `telemetry_store.py`;
- focused retriever, multi-namespace, remote-catalog, and telemetry tests;
- locked provider SDK identity `turbopuffer==2.4.0` at `uv.lock:3665-3667`;
- active telemetry specifications and the completed canary evidence/reviews;
  and
- `.10x/knowledge/provider-budgets-distinguish-logical-operations-and-transport-attempts.md`.

No source/test file was edited. No test, build, import, SDK call, real-store
read, telemetry command, provider/model/credential/network operation, or
external operation ran. The locked SDK implementation is not vendored, so its
internal HTTP sends/retries were not treated as source-proven.

## Terminology finding: client invocation is not necessarily a wire send

Buoy can completely observe each call it makes to a provider SDK method. It
cannot currently prove how many HTTP transmissions that SDK performs internally
for one method call. Conversely, the server-RRF compatibility call may raise a
local argument `TypeError` before any network send. Therefore the smallest
source-owned, deterministic unit is **provider client invocation**:

> One entry into a governed provider request method made by Buoy, counted before
> the method returns or raises.

This is a conservative application-boundary attempt count. It includes local
SDK rejection and excludes invisible SDK-internal retries. It MUST NOT be
reported as exact HTTP/wire-request count unless a separately verified SDK
transport boundary proves one-to-one behavior.

The completed canary has neither unit: its `buoy.namespace.query` spans prove
logical operations only.

## Complete content-query invocation inventory

### One logical namespace operation

Every content operation reaches `HybridRetriever.retrieve_embedded` and its
bounded loop at `src/buoy_search/retriever.py:744-775`.

1. Each loop iteration builds the same two-subquery ANN/BM25 request shape and
   calls `run_multi_query` (`retriever.py:752-763`, `1792-1817`).
2. `run_multi_query` first invokes
   `namespace.multi_query(..., rerank_by=("RRF",))`
   (`retriever.py:1833-1836`). This is one provider client invocation with
   request form `server_rrf`.
3. Only a `TypeError` classified as unsupported server reranking causes the
   second invocation `namespace.multi_query(queries=...)`
   (`retriever.py:1837-1841`). This has request form `client_rrf` and trigger
   `server_rrf_unsupported`. Any other `TypeError` escapes after the first
   invocation.
4. Any exception from either form is examined for one missing optional
   retrieval attribute (`retriever.py:764-775`). Only the two governed optional
   attributes at `retriever.py:117` can be removed, one per retry. Unrelated,
   repeated, or required-attribute errors terminate the logical operation.
5. Consequently one logical namespace operation has one through three outer
   request iterations; each iteration has one or two SDK invocations. The
   source-reachable bound is **1 through 6 provider client invocations per
   logical namespace operation**. Six is possible when both optional fields are
   rejected in separate iterations and server RRF is unsupported in every
   iteration. This is an SDK-invocation bound, not a proven wire-send bound.

Focused tests establish the branches:

- one server-RRF invocation: `tests/test_retriever.py:246-264`;
- two invocations for server-RRF compatibility fallback:
  `tests/test_retriever.py:289-302`;
- two or three outer iterations for one/two missing optional attributes:
  `tests/test_retriever.py:948-1028`; and
- one invocation then failure for unrelated schema errors:
  `tests/test_retriever.py:1030-1048`.

The two ANN/BM25 subqueries are one `multi_query` invocation, not two physical
client invocations.

### Explicit single

The CLI constructs one `HybridRetriever` only for live explicit-single
(`src/buoy_search/cli.py:1557-1597`). The single namespace span encloses one
call to `retrieve_embedded` (`retriever.py:687-742`). Therefore:

- preview: zero content invocations;
- live preflight/model/client failure: zero content invocations; and
- reached live content query: one logical operation and 1..6 client
  invocations.

### Explicit multi

Live explicit-multi constructs `MultiNamespaceRetriever`; at most three unique
namespace configs are allowed (`retriever.py:62`, `887-924`). `_retrieve_batch`
submits one target task per selected namespace and no namespace twice
(`retriever.py:1234-1289`). Each target invokes `retrieve_embedded` once inside
one logical `buoy.namespace.query` span (`retriever.py:1291-1310`). Therefore:

- preview: zero content invocations;
- reranker/model failure before batch: zero content invocations
  (`tests/test_multi_namespace_retrieval.py:587-606`);
- live fanout `N` (1..3): exactly `N` logical operations, concurrent where
  `N>1`, with `N..6N` client invocations; and
- provider failure does not cause a generic namespace retry. The failed target
  is retained as one failed logical outcome while other targets finish.

Concurrency is proven by `tests/test_multi_namespace_retrieval.py:140-165`;
partial/all failure behavior by lines 558-585 and 632-650.

### Automatic live and preview

Automatic routing first performs catalog reads, local model work, and route
selection (`src/buoy_search/cli.py:1600-1747`). Automatic preview stops after
that preparation and makes no content query (`cli.py:1748-1758`). Live
automatic constructs at most three namespace retrievers and passes the selected
initial fanout into `MultiNamespaceRetriever.retrieve`
(`cli.py:1759-1793`).

- Initial fanout 2 or 3 queries those targets once each; no route-level retry or
  widening branch runs.
- Initial fanout 1 queries the top target once logically. Success with adequate
  evidence stops there (`retriever.py:1042-1090`). Empty, failed, or weak top-1
  may widen once to the remaining targets (`retriever.py:1091-1120`). Each
  added namespace is queried once logically.
- Thus automatic live reaches 1..3 logical namespace operations and 1..18
  provider client invocations. A namespace is never queried twice by routing
  widening, but its one logical operation may still contain compatibility and
  optional-schema attempts.
- Missing reranker after top-1 can stop before added targets; the first logical
  operation remains the only one reached
  (`tests/test_multi_namespace_retrieval.py:608-630`).

Successful top-1 stop and one-time empty/failure widening are exercised at
`tests/test_multi_namespace_retrieval.py:440-468`, `503-556`.

## Catalog provider calls are a separate family

Explicit retrieval bypasses catalog reads. Automatic live and preview both call
`read_remote_catalog` before content access (`src/buoy_search/cli.py:1633-1647`).
The strong catalog read at `src/buoy_search/remote_catalog.py:570-618` performs:

- two namespace-list passes. Each pass begins with one
  `client.namespaces(...)` invocation (`remote_catalog.py:922-926`); every
  reached `page.get_next_page()` is one SDK pagination-continuation invocation
  (`remote_catalog.py:973-990`);
- one `resource.metadata()` invocation (`remote_catalog.py:582-584`); and
- two card-query passes, each invoking `resource.query(...)` once per page
  (`remote_catalog.py:592-597`, `993-1070`).

The source bounds each pass to 10,000 pages and reports successful-read counts
as `namespace_list_pages`, `metadata_requests`, and `card_query_pages`
(`remote_catalog.py:35-40`, `611-615`). The minimum complete one-page read is
five catalog request-method invocations: two list pages, one metadata, and two
card-query pages. The source maximum is 40,001 across the four bounded passes
plus metadata. These are deliberate strong reads, not retries.

`client` construction and `client.namespace(...)` resource acquisition are not
classified as request attempts: source calls the SDK constructor inert for
2.4 and does not establish that resource acquisition sends transport
(`remote_catalog.py:247-266`). They should be counted only if a lower transport
boundary later proves a request.

Tests verify two strong passes and exact successful metrics at
`tests/test_remote_catalog.py:1092-1130`, multi-page card counts at lines
1178-1190, and fail-closed pagination bounds at lines 1216-1274. Current metrics
are created only after a successful complete snapshot; failed reads need
call-boundary instrumentation to retain reached counts.

Catalog calls MUST remain separate from content calls. Combining them would
make content fanout/cost and automatic-routing consistency work impossible to
interpret.

## Error, interruption, cancellation, and retry semantics

- A client invocation is counted immediately before entering the governed SDK
  request method. Return, governed exception, `TypeError`, or interruption does
  not erase it.
- Validation/model/configuration failure before method entry counts zero.
- Response parsing/ranking failure after a returned response adds no attempt.
- Compatibility and optional-schema paths are **fallbacks**, each counted as a
  new invocation; repository source has no generic content retry loop.
- `_retrieve_batch` catches only `ProviderCallError` and `RuntimeError` as
  per-namespace failures (`retriever.py:1270-1287`). Other interruption escapes.
  No source-reachable call invokes `Future.cancel` or resubmits a target.
- An invocation interrupted after entry counts with terminal outcome
  `interrupted`. A future that never begins provider method entry counts zero.
- Process death before a terminal receipt makes the receipt incomplete or
  absent; a canary must report the attempt count as unknown rather than infer a
  bound.
- The locked SDK may retry internally or reject locally. Neither event is
  distinguishable at Buoy's current method-call boundary. Exact wire attempts
  therefore require SDK HTTP-transport instrumentation, not merely retriever
  wrapping.

## Current telemetry compatibility constraints

Existing v1/v2 namespace spans allow only route rank, namespace success/failure,
hit count, and governed error category
(`src/buoy_search/telemetry_envelope.py:187-197`, `1310-1317`). Version-2
envelope shape, graph, attribute allowlists, DuckDB schema/views, and migration
are exact. Old writers reject unknown attributes rather than ignoring them.

Therefore adding attempt attributes/spans to production telemetry is not a
small compatible v2 extension. It requires a focused new observation/envelope
contract and an explicit storage/inbox/migration compatibility decision
(presumptively v3). Direct-library v1 tracing must remain unchanged unless a
separate compatibility decision says otherwise. Existing telemetry also has no
retention/purge policy, so permanent production persistence cannot be inferred.

## Candidate observation boundaries

### A. Buoy SDK-method boundary

Wrap the exact content `namespace.multi_query` calls and catalog request-method
calls listed above. This is source-complete, deterministic, fake-testable, and
can be content-free. It counts local SDK rejection and cannot see SDK-internal
HTTP retries. This boundary supports conservative Buoy-issued invocation
budgets but not exact wire-cost claims.

### B. SDK HTTP transport boundary

Instrument the locked SDK's actual request sender. This can count real HTTP
send attempts and internal retries, but the repository does not own or vendor
that boundary. It is SDK-version-specific, risks observing URLs/headers/body,
and requires separate dependency research and a privacy-safe interception
contract. It is the correct boundary only if the owner requires exact wire
attempts.

### C. Packet/proxy boundary

A canary-only network proxy or packet audit can observe wire traffic externally.
It has the strongest network claim but the largest credential/privacy,
certificate, host, and operational burden. It is unsuitable as the first
production implementation and remains external evidence rather than command
telemetry.

## Product-surface alternatives

### Production telemetry

Persist governed attempt spans/attributes for every opted-in command. This
supports longitudinal analysis but requires a new strict telemetry contract,
compatibility/migration work, storage validation, documentation, and a
retention decision. It would make a narrow canary accounting requirement carry
the largest permanent maintenance cost.

### Canary-only terminal receipt

Use a private, bounded in-process ledger at the selected call boundary and
retain one sanitized terminal receipt only for explicitly authorized canaries.
It avoids production schema/migration and recurring retention. Missing or
incomplete receipt means unknown. This is the smallest surface that repairs the
historical evidence gap, but it does not provide ongoing production analytics.

### Provider-client diagnostics

Expose the ledger through a diagnostic callback or structured local diagnostic
surface. It is reusable beyond canaries but adds an API/lifecycle surface and
can become accidental ungoverned telemetry. No current requirement justifies a
public callback before a concrete consumer exists.

## Recommended candidate contract (unratified)

Use **Boundary A** and name the unit `provider_client_invocation`, not exact
wire request. Start with a **canary-only terminal receipt**, not production
telemetry. Count content and catalog families separately.

For content, retain at most three route-rank-only logical entries and at most
six attempts per entry. Each attempt contains only:

- one-based `route_rank` and `attempt_index`;
- request form `server_rrf` or `client_rrf`;
- trigger `initial`, `server_rrf_unsupported`, or
  `optional_schema_compatibility`;
- outcome `success`, `error`, or `interrupted`; and
- nullable governed generic error category.

The receipt also records logical-operation count and total content client
invocations. It never records namespace, optional attribute name, query, argv,
credential, URL, request/response payload, raw error, stack, path, or provider
identifier.

For catalog, retain only aggregate reached invocation counts by
`namespace_list_page`, `metadata`, and `card_query_page`, plus aggregate
success/error/interrupted totals. Do not retain cards, namespaces, cursors,
billing payload, URLs, or page contents.

Increment before method entry; finalize outcome after return/raise. A terminal
receipt is authoritative only when internal totals equal its bounded entries
and the command result is known. Missing/incomplete receipt means unknown and
cannot satisfy a physical-attempt acceptance gate. Observer failure must not
change retrieval behavior; it only makes the accounting receipt unavailable.
Retain the sanitized receipt with durable canary evidence and delete raw
runtime logs/artifacts. Do not add recurring production retention.

If the owner requires exact HTTP/wire sends rather than conservative SDK
invocations, reject this recommendation and first investigate Boundary B; no
current record can truthfully specify it.

## Exact decisions still required

1. **Unit:** Is one entered Buoy-to-SDK request method the accepted attempt
   unit, explicitly including local SDK rejection and excluding unknown
   SDK-internal retries, or must the count mean actual HTTP sends?
2. **Surface:** Is the first implementation a canary-only terminal receipt, or
   must ordinary opted-in production telemetry persist it?
3. **Families:** Must the receipt include separate content and automatic-catalog
   invocation families, or content only?
4. **Detail and failure semantics:** Confirm route-rank-only bounded content
   attempts, aggregate catalog categories, count-before-entry, terminal
   `success|error|interrupted`, and absent/incomplete receipt => unknown.
5. **Retention:** Confirm indefinite retention of only the sanitized canary
   receipt with evidence, deletion of raw artifacts, and no recurring
   production retention/purge change.

Until these are ratified, an active focused specification or executable source
ticket would encode unapproved cost, lifecycle, privacy, and compatibility
semantics.
