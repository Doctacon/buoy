Status: active
Created: 2026-07-20
Updated: 2026-07-20

# Experimental Buoy Baseline Executor

## Authority boundary

This is the focused, ratified specification for one future experimental baseline operation. It authorizes no credential read, model load/download, provider call, namespace/catalog/local-state mutation, or approval. `.10x/tickets/2026-07-20-implement-experimental-buoy-baseline-executor.md` authorizes only bounded source/test implementation. Implementation, independent implementation review, and a separately granted Approval A are all required before execution.

## Purpose and exact scope

A future executor would populate only the missing current-default Buoy baseline needed by C3, using these immutable inputs:

- region: `gcp-us-central1`;
- retained plan: `plan_b6c5d128295f442f`;
- selected-corpus artifact: `b6c5d128295f442fcae21472c9bcb037ecb44101ca648115e8f666ba59a6f0ce`;
- source: `Doctacon/buoy-search@fcb7abbe1652d2eab4ee23816b6d992d893603ac`;
- target namespace: `github-doctacon-buoy-search-v1`;
- rows: exactly 903, written in 14 batches of 64 and one batch of 7;
- content model: `BAAI/bge-small-en-v1.5@5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, MIT license, float32 inference, normalized 384-dimensional CLS-token output, and cosine namespace distance;
- cache manifest SHA-256: `5f783ebce23b6ac957d2741399b46e19502b1751acfd3c744b8c41103b138f35`;
- catalog namespace: `buoy-routing-catalog-v1`, with only the one generated card for the target namespace eligible for a conditional create or revision-bound update;
- local state: only the plan-bound lock, pending record, and DuckDB applied-state needed for this one baseline.

The immutable cached model README at that revision has SHA-256 `ddb964361a55c6e5dfca6361615854b260c9c960205d04c7520151aaa1d75837`; its front matter declares `license: mit`, and its License section states that FlagEmbedding is MIT-licensed. The executor MUST revalidate the revision, full cache manifest, and this README hash before model construction.

A recrawl, replan, model substitution, other namespace/card, C3 retrieval, default change, promotion, and every delete are outside scope.

## Fail-closed preconditions

Before reading `TURBOPUFFER_API_KEY`, the executor MUST validate the exact plan/artifact/source/model/cache values above, verify 903 unique intended row IDs, prove the local applied-state ledger has no active or retained rows for this namespace, and reject any stale/delete intent. It MUST set `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` before model import/construction and MUST NOT use a model credential or network fallback.

For every provider resource, the locked `turbopuffer==2.4.0` client MUST be constructed with `max_retries=0`. The executor MUST stop before the first provider call unless it can attest that SDK retries, wrapper retries, schema/signature fallbacks, pagination, and repeated calls outside the ledger below are disabled. Each initiated HTTP operation counts as one physical attempt whether it succeeds, returns an error response, times out, or has an indeterminate outcome.

Immediately before content writes, the executor MUST establish one of these states for `github-doctacon-buoy-search-v1`:

1. metadata returns the provider's namespace-absent result; or
2. metadata validates the exact expected schema and `cosine_distance`, and one strong ordered `id` query with `top_k=1` returns zero rows.

Any returned row, incompatible schema/distance, ambiguous absence, unbounded pagination requirement, or inability to prove emptiness MUST abort before writes. The catalog metadata and two strong exact-ID reads MUST likewise establish a stable compatible existing card revision or an absent card before content writes.

## Exact physical request ceilings

The implementation MUST enforce the following per-operation ceilings and a global ceiling of **26 physical provider attempts**. An unused conditional attempt cannot be reassigned to another operation.

| Phase | Maximum attempts | Exact bounded operation | Maximum returned row positions |
|---|---:|---|---:|
| target preflight metadata | 1 | target namespace metadata | 0 |
| target empty check | 1 | strong `id` ascending query, `top_k=1`; skipped only when absence is unambiguous | 1 |
| catalog preflight metadata | 1 | exact catalog metadata/schema read | 0 |
| catalog card preflight | 2 | two strong `id == <generated-card-id>` queries, each `top_k=2` | 4 |
| content writes | 15 | exactly 14 upserts of 64 rows and one upsert of 7 rows | 0 |
| target post-write metadata | 1 | target namespace metadata/schema read | 0 |
| target post-write verification | 2 | two strong `id` ascending queries, each `top_k=904` | 1,808 |
| catalog conditional write | 1 | one card create or revision-bound update | 0 |
| catalog post-write verification | 2 | two strong exact-ID queries, each `top_k=2` | 4 |
| **Total ceiling** | **26** | **10 reads plus 16 writes** | **1,817** |

The corresponding maximum write exposure is exactly 904 attempted row positions: 903 content-row upserts and one catalog-card upsert. There are zero delete attempts. Provider/account dollar pricing is unknown and MUST remain reported as unknown; the enforceable cost boundary is 26 physical attempts, 904 write-row positions, 1,817 returned-row positions, `max_retries=0`, and the billing objects actually returned by the provider. Approval MUST NOT imply a dollar ceiling.

## Response and accounting contract

The executor MUST append an accounting entry before each physical attempt and finalize it from the response or error. Every content or catalog attempt MUST record:

- phase, resource/namespace, sequential global request number, and operation-local number;
- attempted/succeeded/failed/indeterminate status;
- requested row count or query `top_k`;
- `rows_affected` as the exact non-negative provider value, or explicit `null` plus `rows_affected_present=false` when the response has no such field;
- returned-row count for reads;
- a redacted provider `billing` object, or explicit `null` plus `billing_present=false`;
- cumulative physical-attempt, write-row-position, and returned-row-position counts.

A missing or malformed `rows_affected` on a successful write is a mismatch. Every successful content write MUST report `rows_affected` equal to its exact batch size. The card write MUST report `rows_affected=1` and the one expected affected ID. The executor MUST preserve accounting for partial success and failed/indeterminate responses; it MUST NOT retry to fill a missing response or billing value. Credentials, tokens, headers, account identifiers, and raw request objects MUST NOT be persisted.

## Post-write verification and commit order

After all 15 content responses match, the executor MUST perform the bounded target metadata read and two `top_k=904` strong reads. Both reads MUST return exactly the 903 intended IDs, no 904th row, identical provider order, the exact expected non-vector attributes, finite 384-dimensional vectors, and the expected schema/distance. Any missing, extra, duplicate, changed, malformed, or unstable row is a mismatch.

On a content response or target verification mismatch, the executor MUST abort before the catalog-card mutation and before committing local DuckDB applied state. It MUST leave the pending record for reconciliation, report every known/unknown partial effect, and perform zero cleanup deletes.

Only after content verification succeeds may the executor issue the single conditional card write. Two bounded exact-ID reads MUST then match the complete intended card and stable revision. Only after that verification succeeds may the executor commit the exact 903-row local applied-state ledger and remove the pending record. A catalog response/verification mismatch MUST abort the local-state commit and report that the remote card may already be partially committed; it MUST perform zero rollback deletes and MUST NOT claim card success.

No state/card success commit may be reported unless every preceding response, count, billing-presence marker, content verification, card verification, and global request-budget invariant matches this contract.

## Acceptance scenarios

### Absent or verified-empty target

Given the exact local inputs and an enforceable zero-retry client, when target metadata proves absence or exact metadata plus the one-row probe proves emptiness, then content writes may begin only while the operation-specific and global counters remain within the ledger.

### Existing target row

Given target metadata succeeds, when the `top_k=1` query returns any row, then the executor aborts with zero writes, zero deletes, and no state/card commit.

### Partial or ambiguous response

Given any provider attempt fails, times out, omits required write accounting, or yields an indeterminate result, then the executor records the attempt and known billing, performs no retry/fallback/delete, aborts later phases, preserves the pending reconciliation record, and does not claim success.

### Post-write mismatch

Given one or more content rows may already exist, when either bounded verification read differs from the expected 903-row projection, then the executor performs no catalog mutation, no local-state commit, and no cleanup delete.

## Evidence required after any separately approved run

Evidence MUST map every one of the 26 possible attempt slots to attempted or unused; include redacted per-response `rows_affected`/billing presence and values; attest `max_retries=0`; prove zero deletes; reproduce exact target IDs/attributes/schema/distance and the card revision; record the local applied-state hash; and state dollar cost as unknown unless separately authoritative account pricing is supplied. Partial success remains a failure and cannot establish Buoy compatibility.
