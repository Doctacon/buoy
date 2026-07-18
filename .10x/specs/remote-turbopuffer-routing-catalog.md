Status: active
Created: 2026-07-18
Updated: 2026-07-18

# Remote Turbopuffer Routing Catalog

## Purpose and scope

Define the exact remote namespace-card schema, stable read protocol, validation/intersection classifications, optimistic mutations, permission/cost boundaries, and backend primitives. Public CLI authority switches only in the atomic cutover specification.

## Authority and location

- Reserved namespace: exact `buoy-routing-catalog-v1` in the resolved region.
- Automatic authority is the intersection of paginated live namespace IDs and valid card targets.
- `TURBOPUFFER_API_KEY` is process-environment-only. No `.env` parsing or secret persistence.
- No catalog path, `BUOY_CATALOG_PATH`, state-root fallback, local JSON mirror, or disk cache exists after cutover.
- The reserved namespace is always a control-plane exclusion, never a target.

## Exact document identity

For target namespace UTF-8 bytes, document `id` is `bc_` plus the first 61 lowercase hex characters of SHA-256. This is exactly 64 ASCII bytes. Every row stores the exact target as `namespace`. Loaders recompute IDs and reject mismatch, duplicate target, or hash collision.

## Exact schema

The namespace distance metric is `cosine_distance`. Schema equality is evaluated after normalizing server defaults: omitted `filterable` means `true`; omitted false index flags mean false; vector ANN `true` is equivalent only to ANN config with `distance_metric=cosine_distance`. Extra/missing attributes or indexes fail.

Turbopuffer's implicit `id` attribute MUST be `string`; it is not repeated in the supplied schema map. All listed attributes are application-required and non-null except `last_plan_id` and `last_apply_id`, which are nullable strings. Turbopuffer attributes are nullable at storage level; Buoy enforces this row contract.

| Attribute | Turbopuffer type | filterable | Other index |
| --- | --- | --- | --- |
| `vector` | `[384]f32` | false | `ann={distance_metric:"cosine_distance"}` |
| `namespace` | `string` | true | none |
| `enabled` | `bool` | true | none |
| `created_at` | `string` | false | none |
| `updated_at` | `string` | false | none |
| `card_revision` | `string` | true | none |
| `last_plan_id` | `string` | false | none |
| `last_apply_id` | `string` | false | none |
| `source_kind` | `string` | false | none |
| `source_uri` | `string` | false | none |
| `site_id` | `string` | false | none |
| `title` | `string` | false | none |
| `summary` | `string` | false | none |
| `aliases` | `[]string` | false | none |
| `tags` | `[]string` | false | none |
| `semantic_origin` | `string` | false | none |
| `region` | `string` | true | none |
| `embedding_model` | `string` | false | none |
| `embedding_precision` | `string` | true | none |
| `vector_dimensions` | `uint` | false | none |
| `plan_schema_version` | `uint` | false | none |
| `ranking_mode` | `string` | false | none |
| `ranking_profile` | `string` | false | none |
| `ranking_pool` | `uint` | false | none |
| `ranking_aggregation` | `string` | false | none |
| `routing_model` | `string` | false | none |
| `routing_model_revision` | `string` | false | none |
| `semantic_hash` | `string` | false | none |
| `vector_hash` | `string` | false | none |

No full-text, regex, glob, fuzzy, embed, sparse, or second vector index exists. Canonical card/revision/hash/timestamp/URI/type/vector validation is fully restated by implementation tests from the superseded local contract; unknown fields, bool-as-int, non-finite/non-unit vectors, stale hashes, or unsupported values fail.

The provider-neutral canonical card serializer/hash contract remains independent of the SDK and has JSON golden fixtures. No hosted embedding is used. `catalog list --json` redacts vectors; explicit `show --include-vector --json` is the operator export path.

## Exact client and read protocol

Use installed Turbopuffer SDK-compatible calls with default bounded transport policy: maximum four SDK retries; connect timeout 5 seconds; read/write/pool timeout 60 seconds; no enclosing unbounded retry loop. 429/timeout/API errors fail after SDK exhaustion with phase diagnostics.

1. First `client.namespaces(page_size=1000)` pass auto-paginates all IDs.
2. Require reserved namespace in listed IDs.
3. `client.namespace(CATALOG).metadata()` validates exact normalized schema.
4. Read cards in pages of 100 using:
   - `rank_by=("id", "asc")`;
   - `top_k=100`;
   - first page no filter, later `filters=("id", "Gt", last_id)`;
   - `include_attributes` exact full attribute list including `vector`;
   - `vector_encoding="float"`;
   - `consistency={"level":"strong"}`.
5. Reject more than 100 rows, non-increasing IDs, repeated IDs, or a full page whose last ID does not advance.
6. Perform two complete strong-consistency card passes. Ordered `(id, card_revision)` sequences and computed canonical snapshot revisions must match exactly.
7. Perform a second complete namespace-list pass and require its sorted ID set to equal the first pass. Any list/card instability fails with no retry/model/content query.

Capture page/request counts and query billing when returned. One automatic read costs twice the namespace-list page count, one metadata query, and twice the card-page count. Ordinary output reports counts/billing summaries without secrets/vectors.

## Count and classification contract

Classifications are mutually exclusive in this order:

1. `control_plane`: exact reserved namespace from total listed IDs;
2. `stale_target`: valid card target absent from content-live IDs;
3. `missing_card`: content-live ID with no valid card;
4. `disabled`: live card with `enabled=false`;
5. `incompatible`: enabled live card failing runtime compatibility;
6. `eligible`: enabled compatible live card.

Metrics distinguish `listed_total`, `control_plane_count`, `content_live_count`, `card_count`, `stale_target_count`, `missing_card_count`, `disabled_count`, `incompatible_count`, and `eligible_count`. Example after seed: five listed IDs, one control plane, four content-live, two cards, zero stale, two missing, zero disabled/incompatible, two eligible.

Duplicate/corrupt/unsupported rows/schema are fatal rather than classification. Zero eligible cards fails with actionable guidance. Namespace IDs never supply semantics.

## Exact mutation requests

All mutations precompute/validate locally before credentials/write and use `distance_metric="cosine_distance"`, `return_affected_ids=True`, exact affected IDs, then two identical strong re-reads.

### Create

Use one row and `upsert_condition=("id", "Eq", None)`. Success requires `rows_affected=1` and `upserted_ids=[expected_id]`. Existing identical state is idempotent only after strong re-read; conflicting state fails.

### Update

Use full replacement row and `upsert_condition=("card_revision", "Eq", expected_revision)`. Zero affected is conflict. Success requires exact affected ID and re-read revision.

### Delete

Preview strongly reads exact card and reports expected revision. Approved delete uses `deletes=[id]`, `delete_condition=("card_revision", "Eq", expected_revision)`, and exact `deleted_ids`. Zero affected is conflict. Strong re-read must prove absence. It never deletes target namespace/content.

### Initial namespace/seed

An absent namespace is created by the first conditional write with the exact schema; there is no separate create call. Migration behavior:

- absent/empty: one two-row conditional-create request; require both affected IDs;
- exact one-card partial: validate byte/hash-equivalence and conditionally create only missing card;
- exact two-card state: idempotent success with zero writes;
- conflicting card, incompatible schema, stale/extra row: fail before writes.

If a race yields partial affected IDs, fail and strong re-read; the next invocation follows the partial-state rule. Final proof requires exactly the two intended cards and no extras.

## Permission and exposure contract

The user explicitly accepted on 2026-07-18:

- automatic preview/catalog list/show: key with namespace-list plus reserved-catalog query permission;
- automatic live: additionally query permission on selected content namespaces;
- catalog mutation: reserved-catalog write plus list/query;
- approved apply: content write/query plus reserved-catalog list/query/write.

Any key able to query the reserved namespace can read complete cards, including source URI, semantics, retrieval settings, lineage, and vectors when requested. These fields must contain no secrets/private credentials. This managed-provider use is user-required and extends the existing Turbopuffer dependency; provider-neutral serialization/export and local embeddings limit lock-in.

## Backend/public boundary

The first implementation child adds these remote backend primitives and injected-client tests only. Existing public local catalog CLI, apply, and retrieval remain unchanged until one atomic cutover. No temporary public command or split authority is introduced.

## Acceptance scenarios

Exact schema normalization, two-pass pagination stability, all count classes, cross-directory equality, create/update/delete conditional conflicts, migration preconditions/races, redaction, permission/error/timeout mapping, request/billing counts, and zero local catalog IO are covered with fakes. No live call occurs before the separately authorized cutover ticket.
