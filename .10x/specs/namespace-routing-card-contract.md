Status: superseded
Created: 2026-07-18
Updated: 2026-08-15
Amended-By: .10x/specs/scalable-routing-quality.md

# Namespace Routing Card Contract

## Purpose and scope

Define the complete provider-neutral semantic, retrieval, lineage, serialization, hashing, generated-default, and vector contract used by remote catalog rows, routing, manual edits, migration, and approved apply.

## Canonical serialization and revisions

All hashes use SHA-256 over UTF-8 bytes of `stable_json_dumps(value)`: recursively JSON-normalized objects, lexicographically sorted object keys, `ensure_ascii=False`, separators `(",", ":")`, JSON booleans/null, and no trailing newline.

`card_revision` hashes the complete canonical card including vector but excluding `created_at`, `updated_at`, and `card_revision`. A remote snapshot revision hashes the list of complete canonical cards including vectors sorted by namespace. Timestamps are UTC ISO-8601 strings with timezone; naive/non-UTC/unparseable values fail.

Unknown/missing card fields fail. Integers must be exact JSON integers, not booleans. Strings required non-empty must remain non-empty after trim.

## Complete card fields

### Identity and lifecycle

- `namespace`: exact non-empty Turbopuffer namespace ID;
- `enabled`: boolean;
- `created_at`, `updated_at`: UTC ISO-8601;
- `card_revision`: canonical revision above;
- `last_plan_id`: non-empty string for apply-managed cards or null;
- `last_apply_id`: non-empty string after apply registration or null.

Target namespaces are unique in a snapshot. Remote card document ID is governed by the remote catalog spec and is not part of `card_revision`.

### Source identity

- `source_kind`: exactly `github_repo`, `website`, or `document`;
- `source_uri`: non-empty absolute URI. HTTP(S) requires hostname and no credentials. GitHub repository roots, canonical `file://<opaque-id>`, and `pdf://<opaque-id>` follow the validated plan rules below;
- `site_id`: non-empty stable source identity.

`manual` is semantic provenance, not source kind. Card state does not prove remote target existence; live intersection does.

### Semantic fields

- `title`, `summary`: non-empty strings;
- `aliases`, `tags`: sorted unique non-empty string arrays;
- `semantic_origin`: `generated` or `manual`.

Duplicate normalization applies Unicode NFKC, `casefold()`, maximal non-alphanumeric/underscore runs to one ASCII space, whitespace collapse, and trim. Duplicate normalized aliases/tags fail. Alias equal to normalized title fails.

Manual upsert sets `semantic_origin=manual`. Approved apply preserves manual title/summary/aliases/tags/origin and every existing enabled state. Generated semantics may refresh deterministically.

The scalable-routing amendment adds an exact four-field prototype bundle to
the same card row under remote schema v2: zero-to-eight canonical
`routing_examples`, `routing_prototype_hash`, an ordinary non-ANN
`routing_prototype_vector`, and `routing_prototype_vector_hash`. New readers
reconstruct all four from the base projection for schema-v1/provider-null rows
and reject partial state; manual apply preservation extends to the bundle.
Examples are not aliases or tags. Exact schema compatibility, projection,
hashing, activation, and migration rules are defined by
`.10x/specs/scalable-routing-quality.md`.

### Retrieval contract

- `region`: non-empty and equal to remote catalog region;
- `embedding_model`: non-empty;
- `embedding_precision`: `float32` or `float16`;
- `vector_dimensions`: exact integer 384;
- `plan_schema_version`: exact integer `1` or `2`; value `1` remains readable/routable lineage for existing cards, while every new schema-v2 approved apply writes `2`. This compatibility does not authorize schema-1 local plan artifacts;
- `ranking_mode`: `file`, `page`, or `chunk`;
- `ranking_profile`: `repo_code` or `none`;
- `ranking_pool`: positive exact integer;
- `ranking_aggregation`: `max`, `adaptive_sum_3`, or `capped_sum_3`.

Apply owns source/retrieval/lineage fields from verified plan plus resolved region/current ranking defaults even when semantics are manual. Manual upsert provides the complete contract and never infers it from namespace ID.

## Routing projection

Fixed contract:

```json
{"dimensions":384,"model":"BAAI/bge-small-en-v1.5","normalized":true,"precision":"float32","revision":"5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"}
```

BGE query prefix is exactly `Represent this sentence for searching relevant passages: `.

Passage text has no trailing newline:

```text
Title: <title>
Summary: <summary>
Aliases: <sorted aliases joined by "; ", or "none">
Tags: <sorted tags joined by "; ", or "none">
```

Stored fields:

- `routing_model=BAAI/bge-small-en-v1.5`;
- `routing_model_revision=5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`;
- `semantic_hash=stable_hash({"passage_text": exact_text, "routing_contract": exact_object})`;
- `vector`: exactly 384 finite JSON numbers, booleans forbidden;
- `vector_hash=stable_hash(vector)`.

Vector norm must be non-zero and within `1e-4` of 1.0. Stale hashes/model, NaN/infinity, wrong dimensions, or non-normalization fail before routing/write. Recompute only when semantic hash or fixed routing contract changes. Enabled/retrieval/lineage-only edits preserve a valid vector.

Model construction uses exact model/revision, float32 normalized output, and `local_files_only=True`; no download/substitution/hosted embedding.

This passage, `semantic_hash`, ANN-indexed `vector`, and `vector_hash` remain
byte-for-byte the legacy projection even when `routing_examples` is non-empty.
Examples affect only the separate prototype hash/vector/hash bundle defined in
`.10x/specs/scalable-routing-quality.md`.

Golden fixtures:

- title `Example`, summary `Example source.`, aliases `example docs`, `example project`, tags `docs`, `python` produce semantic hash `94093fa7c81ea1549f6ef7005110dbc9adc4defa2d8fc4b60043fd231986a85f`;
- vector `[1.0, 0.0, ...]` with 383 zeros produces vector hash `ba682adfaa5fe942ba23457dbe6188c5ebd9f2fb0fa009e7a8cab5773452fae8`.

## Deterministic generated semantics

For every schema-v2 first/later generated apply card, the fully verified plan-level `source` object from `.10x/specs/compact-delta-plan-artifacts.md` is the sole source authority. Apply MUST NOT derive catalog semantics from delta row presence, page/chunk metadata, namespace text, or schema-v1 artifacts. This remains complete for a no-change plan with zero upserts.

1. `source.uri` becomes `source_uri`; its exact low-level kind/URI/attributes consistency is already integrity-bound and is revalidated before model/remote work.
2. Map `github_repo` to catalog `github_repo`; `website` to `website`; `pdf`/`local_file` to `document`; and `duckdb_relation`/`bigquery_relation`/`snowflake_relation` to `database`.
3. Repository identity uses exact `repo_full_name`, owner, name, ref, and commit attributes agreeing with the canonical repository root. Title is full name; summary is `Public GitHub repository <full-name> indexed from <uri>.`; aliases are repository short/full name with title duplicates removed; tags are `github`,`repository`.
4. Website title is the normalized hostname; summary is `Indexed knowledge source at <uri>.`; aliases are empty; tags are `website`.
5. PDF/local-file title is exact verified filename; summary is `Indexed document <filename> from <uri>.`; aliases contain the filename stem when not a title duplicate; tags are `document`. The opaque URI ID is never decoded as a filename.
6. Database title, summary, aliases, and tags use exact backend/source/relation attributes under the existing database generated-semantics formulas.

Existing remote cards with lineage `plan_schema_version=1` remain readable/routable as specified above, but no new generated semantics are derived from a schema-1 local plan. Same verified schema-v2 source inputs produce identical fields. Generated semantics are editable defaults, not human-approved descriptions.

## Apply identity parsing

Apply IDs retain their exact existing format but wall-clock ordering is not causal across machines. No recovery decision may infer supersession from timestamps alone. Explicit accept-remote binds an exact observed remote revision and operator acknowledgement under the apply recovery spec.

## Acceptance criteria

Golden hashes, normalization/URI/timestamp/enums/exact-integer/vector failures, provider-neutral row round-trip, manual/generated ownership, source compatibility, recompute/reuse, and apply-ID non-ordering are fully tested.
