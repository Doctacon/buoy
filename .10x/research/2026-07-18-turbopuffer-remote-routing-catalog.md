Status: done
Created: 2026-07-18
Updated: 2026-07-18

# Turbopuffer Remote Routing Catalog

## Question

Can Buoy remove its working-directory `.buoy/catalog.json`, discover actual Turbopuffer namespaces from any directory, and retain semantic routing cards and compatibility gating without N+1 namespace queries?

## Sources and methods

- Official namespace listing: https://turbopuffer.com/docs/namespaces
- Official namespace metadata: https://turbopuffer.com/docs/metadata
- Official query API: https://turbopuffer.com/docs/query
- Official write/schema/conditional-write API: https://turbopuffer.com/docs/write
- Official export/pagination guidance: https://turbopuffer.com/docs/export
- Turbopuffer Python SDK: https://github.com/turbopuffer/turbopuffer-python
- Inspected installed SDK 2.4.0 signatures for `Turbopuffer.namespaces`, namespace `query`, `write`, and `metadata`.
- Inspected Buoy `src/buoy_search/namespaces.py`, catalog, apply, routing, retrieval, and tests.

No Turbopuffer call or mutation was made during this research.

## Findings

### Namespace discovery supplies identity only

`GET /v1/namespaces` is paginated and returns namespace objects containing only `id`. The Python iterator auto-paginates. API keys need list or admin permission.

### Namespace metadata is not arbitrary application metadata

`GET /v1/namespaces/:namespace/metadata` returns schema, approximate counts/bytes, timestamps, encryption, index state, branching, and pinning. PATCH currently configures pinning. It cannot store Buoy titles, summaries, aliases, ranking contracts, lineage, or routing vectors.

### Semantic routing therefore needs documents

Turbopuffer documents can carry typed attributes and vectors. Queries can fetch ordered/filterable documents with selected attributes, including vectors when requested. Documents can be paged deterministically by `id`. Writes support schemas, upserts, conditions, and affected-row reporting.

A dedicated catalog namespace avoids one card query per content namespace. Buoy can list actual namespaces, query all cards from one reserved namespace, validate/paginate them locally, intersect target IDs with the live listing, and reuse the established deterministic lexical/semantic/RRF algorithm.

### Schema and identity limits matter

Namespace names allow up to 128 characters, but string document IDs allow only 64 bytes. Card IDs therefore cannot safely equal arbitrary target namespace IDs. Use a deterministic hash-derived ID and store the exact target namespace separately, rejecting collisions/duplicates.

The reserved catalog namespace itself appears in listing and must be excluded from candidates. It needs a fixed 384-dimensional float32 routing vector schema matching the pinned BGE routing projection, not each content namespace's storage precision.

Installed SDK 2.4.0 exposes `consistency={"level":"strong"}`, `vector_encoding="float"`, ordered `rank_by=("id","asc")`, ID filters, selected attributes, conditional upsert/delete, `return_affected_ids`, and write responses with exact affected-ID lists. SDK defaults are four bounded retries with 5-second connect and 60-second read/write/pool timeouts.

### Consistency is intersection-based, not transactional

Namespace listing and catalog-card query are separate snapshots. Safe behavior is:

- listed target without valid card: exclude and count;
- card whose target is not listed: stale, exclude and count;
- duplicate target cards, hash/schema corruption, or catalog contract mismatch: fail closed;
- zero valid live cards: fail before content retrieval.

This does not infer semantics from namespace IDs.

### Remote preview changes the safety boundary

With no local catalog or cache, automatic dry preview must read `TURBOPUFFER_API_KEY` and perform read-only namespace-list and catalog-query calls. Explicit CLI namespace dry preview can remain local because it bypasses routing. Offline automatic preview is impossible by design.

### Remote mutation needs optimistic concurrency

The local catalog used `portalocker`; a remote shared catalog must use card revisions and conditional writes. Manual edits and apply registration must bind an expected revision and treat zero affected rows as a conflict. Existing local apply pending artifacts can still record cross-system recovery state; removing the catalog file does not require removing plan/applied/pending state.

## Conclusions

Use one reserved namespace per region named `buoy-routing-catalog-v1`. Store one complete validated routing-card document per target namespace. On automatic retrieval, list live namespace IDs and query/paginate remote cards, then intersect and route locally. Preserve explicit CLI namespace retrieval as the only routing bypass.

Migrate the two validated Oscilar/Dagster cards into the remote catalog, leave the other two live namespaces excluded as missing-card diagnostics, verify remote routing, and delete `.buoy/catalog.json` only during the final cutover. Do not cache cards to disk or fall back to IDs.

This architecture introduces authenticated read-only network work for every automatic preview and remote card writes for catalog/apply operations. It removes working-directory authority and makes routing consistent across directories and machines using the same region/account credentials.

The user explicitly accepted that preview keys need list/query permission and can read complete cards, while mutation/apply keys additionally need write permission. The existing proprietary Turbopuffer dependency is extended by explicit user requirement; provider-neutral canonical serialization/export and local embeddings remain portability boundaries.
