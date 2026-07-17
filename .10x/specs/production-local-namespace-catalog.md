Status: active
Created: 2026-07-15
Updated: 2026-07-16

# Production Local Namespace Catalog

## Purpose and scope

Define the canonical local catalog that production automatic routing reads and approved apply updates. The catalog owns namespace-card semantics, enabled state, retrieval compatibility, persisted routing vectors, revisions, and local lifecycle commands.

This specification implements the catalog/apply choices preserved by `.10x/decisions/production-routing-default-local-catalog.md`. It does not make the catalog an authorization system, remote namespace registry, taxonomy, graph, or source of truth for Turbopuffer contents.

## Authority and location

- The canonical default path MUST be `<resolved-state-root>/catalog.json`, normally `.buoy/catalog.json`.
- Existing `.buoy` versus `.turbo-search` state-root resolution MUST follow `resolve_state_root`; ambiguity MUST fail closed.
- `BUOY_CATALOG_PATH` MAY override the default path. If set, it MUST contain a non-whitespace path or configuration fails.
- A command-level `--catalog PATH` MUST override `BUOY_CATALOG_PATH`; an explicit empty path is invalid.
- Apply MUST expose `--catalog PATH` and otherwise use `BUOY_CATALOG_PATH`, then the catalog under its resolved `--state-root`, in that precedence order.
- Catalog and retrieve commands MUST use the same CLI → environment → resolved/default state-root precedence. Warnings always go to stderr so JSON stdout remains clean.
- The catalog MUST be canonical local JSON. No Turbopuffer catalog namespace or hosted service is part of this release.
- Missing catalog state represents an empty catalog for catalog-management commands. Automatic routing MUST report that no enabled compatible cards exist rather than inventing cards from namespace IDs.
- Malformed, unsupported, contradictory, or partially written catalog state MUST fail closed with its path and actionable recovery guidance.

## Storage and concurrency

The catalog document MUST contain:

- `schema_version = 1`;
- non-empty `catalog_revision`;
- `updated_at` as UTC ISO-8601;
- `cards` ordered by namespace ID.

All catalog hashes MUST use UTF-8 bytes of the existing `stable_json_dumps(value)` compact contract: recursively normalized JSON objects, keys sorted lexicographically, `ensure_ascii=False`, separators `(",", ":")`, JSON booleans/null, and no trailing newline. Catalog persistence MAY use two-space indentation plus one trailing newline, but hashes MUST use the compact form.

`catalog_revision` MUST be the SHA-256 of that compact canonical JSON for the ordered cards, excluding document timestamps and `catalog_revision` itself. Identical cards therefore produce the same revision.

Mutations MUST:

1. acquire an exclusive non-blocking `portalocker` lock adjacent to the catalog;
2. load and validate current state under the lock;
3. write canonical JSON to a same-directory temporary file;
4. flush and `fsync` the file;
5. atomically replace the catalog;
6. best-effort `fsync` the parent directory;
7. release the lock.

A concurrent mutation MUST fail clearly rather than wait indefinitely. Read commands MAY read without the mutation lock but MUST only observe complete old or new files.

## Card contract

Each card MUST contain exactly these behaviorally relevant groups.

### Identity and lifecycle

- `namespace`: non-empty exact Turbopuffer namespace ID;
- `enabled`: boolean;
- `created_at` and `updated_at`: UTC ISO-8601;
- `card_revision`: SHA-256 of canonical card content excluding its timestamps and `card_revision`;
- `last_plan_id`: non-empty string for apply-generated/system-updated cards or `null` for fully manual cards;
- `last_apply_id`: non-empty string after approved apply registration or `null` for manual/unapplied cards.

Namespace IDs MUST be unique and cards MUST be sorted by namespace. Unknown fields MUST be rejected so typos cannot silently change routing intent.

### Source identity

- `source_kind`: one of `github_repo`, `website`, or `document`;
- `source_uri`: non-empty absolute source URL/URI;
- `site_id`: non-empty stable local source identity.

`manual` is semantic provenance, not a source kind. Manual upsert MUST select one of the three real source kinds.

Catalog state does not prove that a remote namespace exists or is fresh.

### Semantic fields

- `title`: non-empty string;
- `summary`: non-empty string;
- `aliases`: sorted unique non-empty strings;
- `tags`: sorted unique non-empty strings;
- `semantic_origin`: `generated` or `manual`.

Canonical normalization for duplicate detection MUST apply Unicode NFKC, `casefold()`, maximal non-alphanumeric runs to one ASCII space, whitespace collapse, and trim. Duplicate normalized aliases/tags MUST be rejected. A normalized alias equal to the title MUST be rejected.

A manual catalog upsert sets `semantic_origin=manual`. Approved apply MUST preserve all semantic fields when that origin is manual. For generated cards, approved apply MAY regenerate semantic fields from the latest verified plan. Approved apply MUST preserve the current `enabled` state for every existing card, generated or manual, including a concurrent disable after precompute.

### Retrieval contract

- `region`: non-empty string;
- `embedding_model`: non-empty string;
- `embedding_precision`: `float32` or `float16`;
- `vector_dimensions`: exactly `384` for this release, matching the current fixed Turbopuffer vector schema;
- `plan_schema_version`: exactly the current supported value `1` in this release; unsupported future/legacy schemas fail closed until explicitly added;
- `ranking_mode`: `file`, `page`, or `chunk`;
- `ranking_profile`: `repo_code` or `none`;
- `ranking_pool`: positive integer;
- `ranking_aggregation`: `max`, `adaptive_sum_3`, or `capped_sum_3`.

Approved apply owns these system fields and MUST refresh them from the verified plan plus apply-resolved region/current namespace ranking defaults even when semantic fields are manual. Manual upsert MUST provide a complete contract; dimensions remain fixed at 384 and it MUST NOT infer remote settings from a namespace ID.

### Routing projection

The first production routing projection is fixed to:

- model `BAAI/bge-small-en-v1.5`;
- revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`;
- precision `float32`;
- dimensions `384`;
- normalized vectors;
- BGE query prefix `Represent this sentence for searching relevant passages: `;
- exact passage text, with no trailing newline:

```text
Title: <title>
Summary: <summary>
Aliases: <sorted aliases joined by "; ", or "none">
Tags: <sorted tags joined by "; ", or "none">
```

Each card MUST store:

- `routing_model` and `routing_model_revision` matching the fixed contract;
- `semantic_hash`: `stable_hash({"passage_text": <exact text>, "routing_contract": <exact object below>})`;

```json
{"dimensions":384,"model":"BAAI/bge-small-en-v1.5","normalized":true,"precision":"float32","revision":"5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"}
```
- `vector`: exactly 384 finite JSON numbers;
- `vector_hash`: `stable_hash(vector)` using the compact serializer above.

Golden fixture:

- title `Example`, summary `Example source.`, aliases `example docs`, `example project`, tags `docs`, `python` produce semantic hash `94093fa7c81ea1549f6ef7005110dbc9adc4defa2d8fc4b60043fd231986a85f` under the fixed routing contract;
- the injected normalized vector `[1.0, 0.0, ...]` with 383 zeroes produces vector hash `ba682adfaa5fe942ba23457dbe6188c5ebd9f2fb0fa009e7a8cab5773452fae8`.

Tests MUST preserve these golden hashes; a deliberate format change requires a schema/revision change.

The vector norm MUST be within `1e-4` of `1.0` and MUST be non-zero. Loaders MUST reject stale hashes, incompatible model contracts, booleans, NaN/infinity, wrong dimensions, or non-normalized vectors before routing.

A vector MUST be recomputed only when the semantic hash or fixed routing contract changes. Enabling/disabling a card or refreshing only retrieval/system fields MUST preserve the existing valid vector.

Model construction for catalog mutation and route preview MUST pass the exact revision and `local_files_only=True`. Missing local model state MUST fail with an actionable message and MUST NOT download or substitute a model.

## Deterministic generated semantics

For first successful apply, or later apply when `semantic_origin=generated`, generation MUST use only verified plan/source metadata:

1. Collect non-empty `source_kind` values from verified page/chunk source metadata. More than one distinct value is contradictory and MUST fail before catalog/model/remote work.
2. Map `github_repo → github_repo`, `pdf` or `local_file → document`, and absent kind by verified URI: a `github.com/<owner>/<repo>` repository root → `github_repo`, other HTTP(S) → `website`, supported canonical `file://<source-id>` or current source-backed `pdf://<source-id>` document URI → `document`. Any contradictory or unsupported value fails closed.
3. `source_uri` is verified plan `base_url`; repository metadata MUST agree with that repository root, while document/website sources retain the verified absolute URI.
4. For repositories use one consistent non-empty metadata `repo_full_name`; when absent on a supported schema-v1 plan, derive exactly `<owner>/<repo>` from the verified canonical `https://github.com/<owner>/<repo>` repository-root URL. Contradictory metadata/URL identities fail closed.
5. For documents use one consistent non-empty `pdf_filename` when source kind is `pdf`, or `file_filename` when `local_file`. Current PDF plans use canonical `pdf://<source-id>` and local-file plans use canonical `file://<source-id>`; each requires a non-empty opaque identifier and rejects whitespace or path/query/fragment forms. When filename metadata is absent on a supported legacy `file:` document plan, use verified `site_id` as the generated title authority. Contradictory filenames fail closed. Opaque document source IDs are never decoded or treated as filenames.
6. `title`: resolved repository full name for repositories; normalized source hostname for websites; verified document filename when present, otherwise the explicitly permitted legacy document `site_id` fallback.
7. `summary`: `Public GitHub repository <repo_full_name> indexed from <base_url>.` for repositories; `Indexed document <filename-or-site-id> from <base_url>.` for documents; otherwise `Indexed knowledge source at <base_url>.`.
8. `aliases`: repository short/full name, website hostname, or document filename stem when verified metadata exists; legacy site-ID fallback adds no fabricated filename alias; remove values equal to the title after normalization.
9. `tags`: `github` and `repository` for repository sources; `website` for website sources; `document` for PDF/local-file sources.

Generated fields MUST be deterministic for the same verified plan inputs. They are editable defaults, not human-approved descriptions.

## Catalog CLI

Buoy MUST add one `catalog` command group with these operations.

### List and show

- `buoy catalog list [SEARCH] [--all] [--json] [--catalog PATH]`
  - defaults to enabled cards only;
  - `--all` includes disabled cards;
  - `SEARCH` matches namespace, title, summary, aliases, and tags after canonical normalization;
  - output is deterministic by namespace.
- `buoy catalog show NAMESPACE [--include-vector] [--json] [--catalog PATH]`
  - fails when absent;
  - text output MUST not print the 384-number vector; JSON includes it only with explicit `--include-vector`.

Read commands MUST NOT load an embedding model, read credentials, or contact Turbopuffer.

### Manual upsert

`buoy catalog upsert NAMESPACE [OPTIONS] [--json] [--catalog PATH]` MUST require complete source, semantic, and retrieval values:

- `--source-kind`, `--source-uri`, `--site-id`;
- `--title`, `--summary`;
- repeatable `--alias` and `--tag`;
- `--region`, `--embedding-model`, `--embedding-precision`, `--plan-schema-version`; vector dimensions are the fixed current value 384;
- `--ranking-mode`, `--ranking-profile`, `--ranking-pool`, `--ranking-aggregation`;
- optional `--disabled`; default enabled for a new card and preserve current enabled state for an existing card unless explicitly changed.

Upsert MUST validate all non-vector fields, build/reuse the persisted routing vector, set semantic origin manual, preserve `created_at`, update `updated_at`, clear neither apply IDs nor source lineage accidentally, and atomically save.

### Enable, disable, and remove

- `buoy catalog enable NAMESPACE [--json] [--catalog PATH]` and `buoy catalog disable NAMESPACE [--json] [--catalog PATH]` MUST be idempotent and preserve vector/card semantics.
- `buoy catalog remove NAMESPACE [--approve] [--json] [--catalog PATH]` MUST require explicit approval for mutation, remove only local catalog state, and clearly state that remote Turbopuffer data and applied state are untouched.
- Remove without `--approve` MUST be a dry-run preview with exit success and no mutation.

Mutation commands MUST NOT read Turbopuffer credentials or contact Turbopuffer.

### Reconcile pending apply registration

`buoy catalog reconcile --pending PATH --catalog PATH [--json]` and `buoy catalog abandon-pending --pending PATH --catalog PATH [--approve] [--json]` MUST be implemented by the apply integration specification; `--catalog` MUST equal the normalized target bound into the pending artifact. The catalog layer MUST expose validated reconcile/abandon primitives and an idempotent commit that preserves manual semantic fields and enabled state.

## Output and error behavior

- Every JSON output MUST include command, catalog path, and catalog revision. Mutation/show outputs also include affected namespace, mutation status where applicable, and the card without its vector unless explicitly requested. List output instead includes search/filter values, count, and ordered cards.
- Text errors MUST identify the catalog path and offending namespace/field.
- Mutation failure MUST leave the previous complete catalog byte-for-byte intact.
- Card removal/disable MUST take effect on the next route invocation.
- No command may silently infer cards from `buoy namespaces` results.

## Acceptance scenarios

### New manual card

Given a complete valid manual upsert and cached routing model, when no catalog exists, then an enabled manual card with a persisted normalized vector is atomically created.

### Manual preservation

Given a manual card, when an approved apply system update is committed, then title, summary, aliases, tags, semantic origin, enabled state, and valid unchanged vector remain unchanged while source/retrieval/apply fields refresh.

### Generated refresh

Given a generated card, when source metadata changes on a later successful apply, then deterministic generated semantics and vector refresh only when their semantic hash changes.

### Corruption

Given a stale vector hash, wrong dimension, unsupported schema, duplicate namespace, or malformed JSON, when any route or mutation loads the catalog, then it fails closed before model, credential, or Turbopuffer work.

### Concurrent mutation

Given one process holds the catalog lock, when another mutation starts, then it fails clearly and the existing catalog remains valid.

### Remove preview

Given an existing card, when remove runs without approval, then it reports the planned local-only removal and performs no mutation.

## Explicit exclusions

- remote catalog storage or synchronization;
- automatic import from remote namespace IDs;
- multi-user principals, groups, or ACL authorization;
- freshness auto-disable or remote existence polling;
- taxonomy governance or inferred concept tags;
- retrieval chunk tag output/filter/boost behavior;
- graph, ontology, concept, or relationship storage;
- remote namespace deletion;
- hosted embedding APIs or model substitution.
