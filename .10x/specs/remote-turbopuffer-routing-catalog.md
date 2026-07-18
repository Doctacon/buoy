Status: active
Created: 2026-07-18
Updated: 2026-07-18

# Remote Turbopuffer Routing Catalog

## Purpose and scope

Define the canonical remote namespace-card store, read/write contracts, validation, CLI lifecycle, optimistic concurrency, and actual-namespace intersection primitives. Routing and apply sequencing are governed separately.

## Authority and location

- The exact reserved namespace MUST be `buoy-routing-catalog-v1` in the resolved `TURBOPUFFER_REGION`/CLI region.
- `TURBOPUFFER_API_KEY` MUST be read from the process environment only. Buoy does not parse or persist `.env` secrets.
- There is no catalog path, `BUOY_CATALOG_PATH`, state-root catalog fallback, local JSON mirror, or on-disk routing-card cache.
- Namespace listing MUST use the paginated Turbopuffer API and collect exact IDs deterministically.
- The reserved catalog ID MUST be excluded from target namespace candidates.
- Listing and card reads are separate snapshots; intersection semantics below are authoritative.

## Remote schema

The catalog namespace MUST use cosine distance and one 384-dimensional float32 `vector` column matching the pinned routing projection. One document represents one target namespace.

Document `id` MUST be deterministic, at most 64 bytes, and derived as `bc_` plus the first 61 lowercase hexadecimal characters of SHA-256 over UTF-8 target namespace ID. The document MUST also store the exact `namespace`. Loaders MUST recompute the ID, reject a mismatch, duplicate target namespace, or hash collision, and sort by target namespace.

Each document MUST preserve the complete established card groups:

- lifecycle: enabled, created/updated timestamps, card revision, last plan/apply IDs;
- source: source kind/URI/site ID;
- semantics: title, summary, aliases, tags, semantic origin;
- retrieval: region, embedding model/precision, dimensions, plan schema, ranking mode/profile/pool/aggregation;
- routing: fixed model/revision, semantic hash, normalized 384-number vector, vector hash.

Unknown or missing attributes, invalid scalar types (including booleans where integers are required), unsafe timestamps/URIs, stale hashes/revisions, non-finite or non-unit vectors, unsupported enums, or region/model contract contradictions MUST fail closed. The reserved namespace schema itself MUST be validated before cards are accepted.

Attributes used only for returned card state SHOULD be non-filterable where supported; `namespace`, `enabled`, revision, and identifiers MAY remain filterable for conditional operations. Schema changes outside the exact current contract fail closed rather than self-repair during reads.

## Reading and pagination

A catalog read MUST:

1. create one authenticated Turbopuffer client for the resolved region;
2. auto-paginate the complete live namespace listing;
3. require the reserved catalog namespace to exist;
4. query catalog documents ordered by `id`, requesting all card attributes including vector;
5. page by advancing an `id` filter until exhausted, with a fixed bounded page size and duplicate/non-advancing cursor protection;
6. validate all rows and compute a deterministic snapshot revision from sorted canonical cards;
7. intersect target IDs with the live namespace set.

Classifications:

- live + valid card: eligible for later compatibility filtering;
- live without card: `missing_card`, excluded and counted;
- valid card without live target: `stale_target`, excluded and counted;
- reserved catalog namespace: excluded control plane;
- duplicate/corrupt/unsupported card or schema: fatal catalog error, not exclusion.

Zero live valid cards MUST fail with actionable catalog commands. Ordinary output MUST expose bounded counts and snapshot revision but never vectors or credentials.

## Writes and optimistic concurrency

Mutations MUST precompute and fully validate the new card before credential lookup/write. Remote writes MUST use the exact schema and conditional revision semantics:

- create expects absence and fails if a target card already exists;
- update binds the exact observed `card_revision` and succeeds only if it still matches;
- idempotent identical writes MAY report unchanged without mutation;
- zero affected rows under a conditional update is a conflict, never success;
- mutation responses are re-read and validated before success is reported.

Card revision/hash canonicalization remains the compact stable JSON contract from the superseded local specification. Timestamps are excluded exactly as before. Manual semantic ownership and enabled-state preservation remain mandatory.

## Catalog CLI

`buoy catalog list/show/upsert/enable/disable/remove/reconcile/abandon-pending` remain the public lifecycle surface but become authenticated remote operations.

- All commands resolve region, require credentials, and contact Turbopuffer.
- Local `--catalog` options and `BUOY_CATALOG_PATH` behavior MUST be removed and rejected if encountered.
- `list` defaults to enabled cards and reports live/missing/stale counts; `--all` includes disabled/stale cards.
- `show` redacts vectors unless explicitly requested.
- manual upsert requires the complete card contract and local cached routing model for vector generation; no remote model service is used.
- enable/disable preserve all other state with conditional revision writes.
- remove requires approval and deletes only the remote card, never the target content namespace.
- reconcile/abandon semantics are defined by the apply specification.

JSON remains machine-readable; stderr carries diagnostics. Secrets/vectors are never logged by default.

## Failure and side-effect boundaries

- Reads never mutate namespace/card/content state.
- A missing key, list permission, catalog query permission, reserved namespace, or catalog schema fails clearly.
- No read path creates or repairs the catalog namespace/cards.
- Remote API errors name the phase without exposing keys.
- The implementation MUST use injected clients for tests; no live Turbopuffer validation occurs without a separately authorized migration ticket.

## Acceptance scenarios

- Listing four live namespaces plus two valid cards yields two live cards and two `missing_card` exclusions.
- A stale card is counted but cannot route.
- Corrupt or duplicate rows fail the entire read.
- Conditional concurrent update affects zero rows and reports conflict without overwrite.
- The same credentials/region return the same cards from unrelated current working directories.
- No `.buoy/catalog.json` is read or written.
