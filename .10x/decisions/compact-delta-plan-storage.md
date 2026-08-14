Status: active
Created: 2026-07-24
Updated: 2026-08-13
Amended-By: .10x/decisions/buoy-owns-bounded-multi-corpus-retrieval.md

# Compact Delta Plan Storage

## Bounded-retrieval amendment

This record remains active for compact, reviewable, baseline-bound
`plan.json`/`delta.duckdb` storage and apply verification. Command Center,
managed-job, and cross-plan inventory consequences remain outside Buoy. The
later bounded-retrieval decision restores only the existing routing catalog
and its post-commit card lineage; broader catalog/control-plane consequences
remain with Kite or historical provenance.

## Context

Buoy's schema-v1 plan artifact duplicates the complete desired chunk corpus in `manifest.json` and `chunks.jsonl` and retains generated page files. Local Command Center inventory recursively reparses those payloads. Real local data reached 4.6 GB across 83,259 files, with individual manifests above 250 MB, even though incremental apply needs only changed/new rows, stale identities, and a proof of the applied baseline.

The user requires credential-free incremental planning from compact per-site DuckDB applied state, exact later application of reviewed content, changed-content-only local review, a fail-and-replan rule after applied-state drift, one format for every current source kind, and a hard cutover with no old-format runtime support. Existing old files are user-deleted; Buoy must not add automatic deletion or migration behavior.

## Decision

Plan schema v2 uses two local artifacts:

- `plan.json`: small deterministic identity, source/provenance, options, diff counts, applied-state baseline hash, delta logical hash/counts, embedding/retrieval contract, and creation metadata.
- `delta.duckdb`: one embedded DuckDB containing exact changed/new upsert rows and exact stale-row records. Upsert rows contain the complete content and metadata required for review, embedding, row construction, and apply. Stale records contain the existing row identity and prior hashes/status needed to review and execute current stale-retention/deletion behavior.

No `manifest.json`, `chunks.jsonl`, `summary.json`, or retained `pages/` directory is part of schema v2. Source acquisition may use private temporary files during planning, but successful output retains only the two artifacts.

The artifact and plan identity bind the canonical logical delta, baseline hash, source/provenance, options, namespace, and embedding contract rather than DuckDB's binary byte layout. Readers validate the DuckDB schema, identities, counts, and a recomputed canonical logical hash before use.

`state.duckdb` remains the credential-free applied baseline. Planning records `applied_state_hash` over the loaded ledger. Preflight and approved apply reload state and require an exact hash match; drift fails before credentials, embeddings, provider calls, pending-state mutation, or writes and instructs the operator to replan.

`PLAN_SCHEMA_VERSION` becomes 2. Runtime local artifact readers accept only schema 2. Schema-1 plans are unsupported, ignored by Command Center inventory and implicit apply discovery, and rejected clearly when passed explicitly to apply. Buoy never migrates, rewrites, archives, or deletes old-format files. Existing prospective cleanup remains active only for schema-2 pending plans after successful approved apply or supersession.

## Alternatives considered

### Keep full manifests but cache inventory

Rejected. Caching masks repeated load but retains the initial multi-gigabyte parse, persistent memory pressure, and duplicate full-corpus storage.

### Changed-only JSONL

Rejected in favor of DuckDB. JSONL is simple and streamable but lacks efficient indexed pagination for plan review and requires repeated scans for later pages. DuckDB is already an open-source required dependency and provides compact storage, bounded queries, schema checks, and direct pagination.

### Query turbopuffer for every plan baseline

Rejected. It would require credentials and remote API activity for planning and would remove the current local-only incremental-plan safety boundary.

### Regenerate source content during apply

Rejected. Apply could execute content different from what the operator reviewed.

### Store pending plans inside applied `state.duckdb`

Rejected. Planning would mutate the applied-state ledger, complicate first-apply behavior and concurrent plan history, and blur proposal versus applied authority.

## Consequences

First apply necessarily stores every desired row because every row is new, but each row is stored once. Incremental plans retain only changed/new rows and stale identities. Unchanged rows remain represented only by applied state and remote content.

Command Center summary screens summary-qualify only small `plan.json` files plus sibling file type/presence. Opening one plan performs complete verification and bounded queries against its `delta.duckdb`; no inventory route loads payloads. Full unchanged-source previews and schema-1 local compatibility are intentionally removed.

Remote catalog cards retain lineage compatibility separately: existing cards marked plan schema 1 remain routable, while new approved applies write lineage 2. This does not authorize reading schema-1 local artifacts.

This is a breaking local artifact cutover and requires coordinated planner, apply, managed-job, Command Center, documentation, test, and package changes.
