Status: active
Created: 2026-07-24
Updated: 2026-07-24
Amended-By: .10x/specs/focused-buoy-boundary.md

# Compact Delta Plan Artifacts

## Focused-boundary amendment

This specification remains active for compact artifact identity, review,
baseline binding, verification, and one-namespace apply. Catalog
staging/recovery, routing-card writes, Command Center readers, managed jobs,
and frontend presentation are superseded. A no-change apply performs no
catalog write.

## Purpose and scope

Define schema-v2 plan output, incremental baseline binding, exact apply behavior, hard-cutover compatibility, and bounded local review for every current `buoy plan` source: credential-free HTTP(S) websites, public GitHub repositories, local Markdown/PDF documents, DuckDB relations, BigQuery relations, and Snowflake relations.

This specification supersedes schema-v1 artifact-shape and local compatibility clauses in active source, planning, apply, managed-job, and Command Center specifications. Existing source acquisition, chunk identity, embedding identity, diff classification, stale retention/deletion policy, approval, prospective cleanup, remote catalog recovery, privacy, and provider boundaries remain unchanged unless explicitly replaced here.

## Successful output

A successful plan MUST retain exactly two ordinary regular files in its output directory:

```text
plan.json
delta.duckdb
```

Private acquisition/staging files MUST be removed before success. The plan MUST NOT retain or require `manifest.json`, `chunks.jsonl`, `summary.json`, `pages/`, a source clone, source credentials, connection settings, absolute private source paths, or unchanged chunk content.

`PLAN_SCHEMA_VERSION` is 2. `DELTA_SCHEMA_VERSION` is 1. The UTF-8 encoded `plan.json` MUST be at most 131,072 bytes. Unknown fields, wrong JSON types, booleans used as integers, non-finite numbers, and unsafe or over-limit strings MUST fail validation.

## Exact `plan.json` contract

The top-level object contains exactly these required fields except `originating_job_id`, which is present only for a managed job:

- `schema_version`: integer `2`;
- `command`: string `plan`;
- `plan_id`: `plan_` plus the first 16 lowercase hexadecimal characters of `artifact_hash`;
- `created_at`: UTC ISO-8601 timestamp; excluded from identity;
- `artifact_hash`: lowercase SHA-256 defined below;
- `source`: exact source object below;
- `site_id`, `namespace`, `namespace_candidate`: current validated non-empty safe identities;
- `crawl_options`, `chunk_options`: recursively JSON-normalized objects using current deterministic option semantics;
- `embedding_model`: current non-empty model identity;
- `embedding_precision`: `float32` or `float16`;
- `applied_state`: exact baseline object below;
- `delta`: exact delta descriptor below;
- `diff`: exact diff summary below;
- optional `originating_job_id`: safe managed job ID, excluded from identity.

No absolute state path, artifact path, source file path, credential, profile, connection setting, or provider diagnostic is allowed.

### Source object

`source` contains exactly `kind`, `uri`, `title`, and `attributes`. `uri` is the current safe canonical source URI; `title` is non-empty safe display text. `kind` and the exact `attributes` object are:

- `website`: `{}`;
- `github_repo`: `repo_full_name`, `repo_owner`, `repo_name`, `repo_ref`, `commit_sha` as non-empty strings and `repo_subdir` as string or JSON null;
- `local_file`: `filename`, `extension`, `sha256`, `source_id` as non-empty strings;
- `pdf`: `filename`, `sha256`, `source_id` as non-empty strings;
- `duckdb_relation`, `bigquery_relation`, or `snowflake_relation`: `database_backend`, `database_source_id`, `database_relation` as non-empty strings.

No other source attribute is allowed. URI/kind/attribute consistency MUST preserve current source validation: repository root and metadata agree; local document URI is opaque and contains no absolute path; database URI scheme, backend, source ID, and relation agree. This plan-level source object is the authority for provenance and generated catalog semantics even when the delta has zero upserts.

Every upsert row also retains current row-specific source metadata. Invariant row metadata, when present, MUST agree with the plan-level source object. Variant fields such as repository path/language and database document ID remain row-level only.

### Applied-state baseline object

`applied_state` contains exactly:

- `present`: boolean indicating whether matching `state.duckdb` existed when loaded;
- `schema_version`: current applied-state schema integer;
- `hash`: lowercase SHA-256 of the canonical baseline projection below.

The baseline projection is:

```json
{
  "present": "<boolean>",
  "schema_version": "<integer>",
  "site_id": "<string>",
  "namespace": "<string>",
  "base_url": "<string>",
  "updated_at": "<string>",
  "last_plan_id": "<string>",
  "last_apply_id": "<string>",
  "rows": ["<canonical applied rows sorted by row_id>"]
}
```

Each canonical applied row contains exactly `row_id`, `canonical_url`, `page_hash`, `chunk_hash`, `embedding_text_hash`, `plan_id`, `applied_at`, and `status`. `first_apply` is runtime metadata and excluded. `apply_runs` summaries are excluded because they do not affect incremental row state; every successful approved apply already changes top-level lineage/timestamps. `present=false` uses the existing deterministic empty first-apply values. A subsequently created valid empty database has `present=true` and therefore counts as drift.

Canonical hashing everywhere in this spec means SHA-256 over UTF-8 `stable_json_dumps`: recursive JSON normalization, lexicographically sorted object keys, `ensure_ascii=False`, separators `(",", ":")`, JSON booleans/null, and no trailing newline.

### Delta descriptor

`delta` contains exactly:

- `filename`: `delta.duckdb`;
- `schema_version`: integer `1`;
- `logical_hash`: lowercase SHA-256 defined below;
- `upsert_count`, `stale_count`, `retained_stale_count`: non-negative integers.

### Diff summary

`diff` contains exactly the current non-negative fields: `first_apply` boolean, `pages_added`, `pages_changed`, `pages_unchanged`, `pages_removed`, `chunks_unchanged`, `chunks_to_embed`, `rows_to_upsert`, `stale_rows`, and `retained_stale_rows`. Planning MUST compute every field from the complete in-memory desired diff before discarding unchanged content. Full artifact verification MUST independently reconcile the derivable operation fields: `chunks_to_embed` and `rows_to_upsert` equal delta upserts; `stale_rows` and `retained_stale_rows` equal delta categories; first apply has zero changed/unchanged/removed pages, zero unchanged chunks, and zero stale records. Page counts and later `chunks_unchanged` are deliberately not independently derivable after unchanged content is omitted; they remain artifact-identity-bound summary claims covered by planner/diff tests. An empty acquired page may therefore produce `pages_added=1` with zero delta rows.

## Exact `delta.duckdb` contract

The database contains exactly the application-owned tables `delta_metadata`, `upsert_rows`, and `stale_rows`; ordinary DuckDB internal objects are excluded from this count. Readers reject extra application tables/views/macros, missing constraints, duplicate identities, or schema drift.

### `delta_metadata`

Exactly one row:

```sql
CREATE TABLE delta_metadata (
  schema_version INTEGER NOT NULL CHECK (schema_version = 1),
  plan_id VARCHAR PRIMARY KEY,
  site_id VARCHAR NOT NULL,
  namespace VARCHAR NOT NULL,
  source_kind VARCHAR NOT NULL,
  source_uri VARCHAR NOT NULL,
  applied_state_hash VARCHAR NOT NULL,
  logical_hash VARCHAR NOT NULL,
  upsert_count UBIGINT NOT NULL,
  stale_count UBIGINT NOT NULL,
  retained_stale_count UBIGINT NOT NULL
)
```

Every value MUST equal `plan.json`.

### `upsert_rows`

```sql
CREATE TABLE upsert_rows (
  ordinal UBIGINT PRIMARY KEY,
  action VARCHAR NOT NULL CHECK (action IN ('new','changed','reactivate_retained_stale')),
  row_id VARCHAR NOT NULL UNIQUE,
  row_id_candidate VARCHAR NOT NULL,
  site_id VARCHAR NOT NULL,
  duplicate_ordinal UINTEGER NOT NULL,
  canonical_url VARCHAR NOT NULL,
  source_path VARCHAR NOT NULL,
  page_hash VARCHAR NOT NULL,
  chunk_hash VARCHAR NOT NULL,
  embedding_text_hash VARCHAR NOT NULL,
  title VARCHAR NOT NULL,
  section_path VARCHAR NOT NULL,
  chunk_index UINTEGER NOT NULL,
  content VARCHAR NOT NULL,
  doc_kind VARCHAR NOT NULL,
  tags_json VARCHAR NOT NULL,
  source_metadata_json VARCHAR NOT NULL
)
```

`ordinal` is contiguous from zero in sort order `(canonical_url, section_path, chunk_index, row_id)`. `tags_json` is canonical JSON for a lexicographically sorted unique string array. `source_metadata_json` is canonical JSON for the current string-to-string metadata object. Empty content or identity fields fail according to current chunk rules. `embedding_text_hash` is recomputed from the exact current embedding text projection and plan precision.

### `stale_rows`

```sql
CREATE TABLE stale_rows (
  ordinal UBIGINT PRIMARY KEY,
  category VARCHAR NOT NULL CHECK (category IN ('stale','retained_stale')),
  row_id VARCHAR NOT NULL UNIQUE,
  canonical_url VARCHAR NOT NULL,
  page_hash VARCHAR NOT NULL,
  chunk_hash VARCHAR NOT NULL,
  embedding_text_hash VARCHAR NOT NULL,
  prior_plan_id VARCHAR NOT NULL,
  prior_applied_at VARCHAR NOT NULL,
  prior_status VARCHAR NOT NULL CHECK (prior_status IN ('active','retained_stale')),
  reason VARCHAR NOT NULL CHECK (reason IN ('not_in_desired_source','retained_stale_not_in_desired_source'))
)
```

`ordinal` is contiguous from zero in sort order `(canonical_url, row_id)`. `category`, `prior_status`, and reason MUST correspond: stale/active/not-in-desired, or retained-stale/retained-stale/retained-not-in-desired.

### Logical delta hash

Reconstruct canonical upsert objects with exactly every `upsert_rows` field except `ordinal`, parsing `tags_json` and `source_metadata_json` into JSON values. Reconstruct canonical stale objects with exactly every `stale_rows` field except `ordinal`. Then hash:

```json
{
  "schema_version": 1,
  "upsert_rows": ["<objects in ordinal order>"],
  "stale_rows": ["<objects in ordinal order>"]
}
```

No plan ID, timestamp, filesystem path, or DuckDB binary byte layout enters this logical hash.

### Artifact hash and plan ID

`artifact_hash` hashes the exact object:

```json
{
  "schema_version": 2,
  "source": "<exact source object>",
  "site_id": "<string>",
  "namespace": "<string>",
  "namespace_candidate": "<string>",
  "crawl_options": "<object>",
  "chunk_options": "<object>",
  "embedding_model": "<string>",
  "embedding_precision": "<string>",
  "applied_state": "<exact baseline object>",
  "delta": "<exact delta descriptor>",
  "diff": "<exact diff object>"
}
```

`created_at`, `plan_id`, and `originating_job_id` are excluded. `plan_id` is then derived from `artifact_hash`. After derivation, `delta_metadata.plan_id` binds the database to the plan without creating a hash cycle.

## Validation levels

A **summary-qualified plan** has a regular no-follow `plan.json` within the artifact root, is within the size bound, passes the complete schema-2 metadata validation above, and has a sibling `delta.duckdb` that is a regular no-follow file. This level does not open the database and is sufficient only for Command Center list/dashboard/namespace summaries. It MUST be reported internally as payload verification `not_checked`, never as apply-valid.

A **fully verified plan** additionally opens the selected database read-only and validates exact SQL schema/constraints across every non-internal schema, absence of extra application tables/views/macros, metadata identity, derivable operation counts above, ordinals, uniqueness, source consistency, embedding hashes, logical hash, artifact hash, and plan ID. Non-derivable compact summary counts remain identity-bound rather than reconstructed from omitted unchanged content. Apply and selected plan detail require this level. Tamper or corruption in one selected plan MUST not break unrelated summary-qualified inventory.

## Planning behavior

Planning MUST acquire and process the complete bounded source in private temporary storage to determine desired identity, page counts, and removals. It MUST load matching applied state without turbopuffer credentials or remote calls, compute the baseline projection, and compute existing incremental classifications.

Absence of `state.duckdb` MUST NOT create an applied-state database. First apply stores every desired row once as an upsert. Later plans store only new/changed/reactivated rows. A no-change plan has empty operation tables and complete plan-level source metadata. No unchanged content is retained.

Planning remains turbopuffer/model/write inert. Existing database-source planning may use its explicitly configured source credentials/API calls only during source acquisition, unchanged from governing source specs.

## Preflight and approved apply

Dry-run and pre-confirmation apply MUST fully verify schema-2 artifacts, reload matching applied state, recompute the exact baseline projection including `present`, and compare its hash. A mismatch fails with `Applied state changed after this plan was created; run buoy plan again.` before source reacquisition, credential reads, model load, provider calls, pending-state changes, or writes.

Approved apply MUST acquire the namespace lock and repeat full artifact and baseline verification under lock before any remote or local mutation. It embeds/upserts only verified `upsert_rows`. Existing `--delete-stale` behavior acts only on verified stale IDs; otherwise stale rows become/remain retained stale. Next state combines unchanged baseline rows with delta operations and preserves current atomic commit and remote-catalog recovery.

Apply MUST NOT crawl, clone, open source documents/databases, or require source credentials. It uploads exactly reviewed changed/new content.

An approved no-change plan preserves current approved-apply semantics: it performs no content namespace upsert/delete, but still requires approval and turbopuffer credentials, validates/updates the remote catalog through current pending recovery, commits new plan/apply lineage plus one zero-row apply summary, and then performs prospective plan cleanup. This behavior changes the next baseline hash.

## Remote catalog lineage

Remote catalog `plan_schema_version` remains lineage, not authorization to read a local artifact. Existing remote cards with value `1` remain readable/routable. Catalog validators accept exact integers `1` or `2`; new schema-2 approved applies write `2`. Existing cards upgrade individually on their next successful apply; no bulk remote migration or write is authorized. Accepting card lineage `1` does not provide schema-1 local artifact support.

## Hard cutover and lifecycle cleanup

Runtime local artifact readers support schema 2 only. Implicit latest-plan discovery skips schema-1 and malformed candidates without reading legacy payloads and selects the newest summary-qualified schema-2 plan; if none exists, it reports that no supported plan exists. Explicit schema-1 apply rejects safely without reading manifest/chunks/pages and performs no mutation.

Command Center ignores schema-1 directories without legacy payload inspection or warning. Buoy does not migrate, rewrite, archive, or delete legacy/upgrade artifacts. Existing files remain inert user-owned data.

Prospective schema-2 lifecycle cleanup remains active: successful approved apply removes its exact fully verified plan directory, and a newly successful schema-2 plan removes only older fully verified schema-2 plans for the same namespace. Destructive cleanup MUST fully verify each candidate delta first; a summary-qualified but payload-corrupt/unverifiable directory remains untouched with the existing safe warning behavior. Cleanup MUST never inspect legacy payloads or delete schema-1 directories. Existing cleanup failure and safety behavior remains unchanged.

## Command Center API and interface

Dashboard, plan history, and namespace inventory use summary-qualified `plan.json` metadata and compact applied state only. They MUST NOT open `delta.duckdb`.

The selected plan detail endpoint fully verifies one plan. Existing `/api/v1/plans/{plan_id}/chunks` returns bounded/paginated changed/new upsert rows only. New `/api/v1/plans/{plan_id}/stale-rows` returns bounded/paginated stale identities. Schema-v1 page list/detail endpoints are removed; no arbitrary path or SQL endpoint replaces them.

The UI shows safe provenance, baseline identity, diff counts, changed/new content, stale identities, and the statement `Unchanged content is omitted because it already matches applied state.` It exposes no full-page preview and no unchanged content. Existing read-only and escaped-text boundaries remain.

Managed planning success requires exactly `plan.json` and `delta.duckdb`. Job ID remains audit/storage identity only. Managed staging, no-follow, fsync, ownership, interruption, and sanitized progress remain unchanged.

## Structural performance bounds

- `plan.json` is at most 131,072 bytes.
- Inventory API pages remain at most 100 plans/namespaces and read no delta database bytes.
- Changed/stale detail pages accept `limit` from 1 through 100; changed content preview is at most 20,000 characters per row and response construction selects only the requested rows in SQL.
- Automated tests use at least 1,000 maximum-size summary-qualified plan files plus a selected delta sentinel with at least 100,000 rows. Dashboard/list tests MUST prove zero DuckDB connections and zero delta-file opens. Detail tests MUST prove one selected read-only connection, SQL `LIMIT`/`OFFSET`, at most the requested rows materialized, and no other delta opened.
- Validation evidence records wall time and peak resident memory for that fixture on the actual host; these measurements are observational, while the I/O/query bounds above are required and deterministic.

## Acceptance scenarios

- **Incremental:** unchanged A is absent; changed B appears once as a complete upsert; counts agree; no turbopuffer activity occurs.
- **Removal:** absent active C appears once as stale; current retain/delete flags affect only verified C.
- **No changes:** operation tables are empty, source metadata remains complete, dry-run reports zero content writes, and approved no-change semantics above remain intact.
- **State drift:** absent-to-empty creation or any metadata/row/lineage change alters the baseline and blocks before side effects.
- **First apply:** no state database is created by plan; every desired row appears once; no duplicate payload exists.
- **Old format:** implicit discovery and Command Center ignore schema 1; explicit apply rejects; no file is modified or deleted.
- **No-change source kinds:** website, GitHub, document, and each database backend retain sufficient plan-level provenance/catalog semantics with zero upserts.

## Acceptance criteria

- All current source kinds emit and verify schema-v2 compact deltas with exact safe plan-level provenance.
- First/no-change/incremental/reactivated/stale retain/delete, drift/race, tamper/integrity, source isolation, no-change approved apply, catalog lineage 1/2, cleanup, and hard-cutover tests pass.
- No unchanged content is persisted; plan/apply identities and state transitions are deterministic.
- Command Center inventory is summary-qualified and payload-independent; detail review is fully verified and bounded.
- Managed planning/package/static behavior uses only the two artifacts.
- Existing approval, provider-write, catalog recovery, filesystem, CSRF, loopback, credential, privacy, and prospective cleanup protections are not weakened.

## Exclusions

No legacy/upgrade artifact deletion or migration, live turbopuffer planning baseline, source reacquisition during apply, automatic diff recalculation, simultaneous same-namespace apply, new stale policy, new source kind, browser apply/mutation, bulk remote-card migration, or change to row/chunk/embedding identity.
