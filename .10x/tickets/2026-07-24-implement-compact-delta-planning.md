Status: open
Created: 2026-07-24
Updated: 2026-07-24
Parent: .10x/tickets/2026-07-24-compact-delta-plan-hard-cutover.md
Depends-On: None

# Implement Compact Delta Planning

## Scope

Implement schema-v2 plan construction and output for every current source kind according to `.10x/decisions/compact-delta-plan-storage.md` and `.10x/specs/compact-delta-plan-artifacts.md`.

Replace the schema-v1 full manifest/chunks/page output model with size-bounded deterministic `plan.json` plus changed-only `delta.duckdb`. Implement the exact fields, source variants, SQL columns/types/constraints, canonical logical serialization, hash formulas, baseline projection/presence bit, and validity levels in the governing spec. Reuse current acquisition, chunk identity, source metadata, and incremental diff semantics; do not reuse the catalog-pending state hash by name without implementing the specified plan-baseline projection. Build complete desired rows only in temporary execution state; retain only upsert/stale records and remove staging before success.

## Acceptance criteria

- `PLAN_SCHEMA_VERSION` is 2, `DELTA_SCHEMA_VERSION` is 1, and builders expose the exact typed schema-v2 plan/source/diff descriptors and exact three-table DuckDB schema.
- Artifact identity follows the spec's exact canonical upsert/stale reconstruction and exact artifact projection; it is independent of timestamps, absolute paths, output directory, DuckDB binary layout, and managed job ID.
- Planning loads compact applied state and records its deterministic complete hash without creating first-apply state.
- `upsert_rows` contains complete rows only for new/changed/reactivated chunks; `stale_rows` contains exact absent active/retained identities; unchanged content is absent.
- First apply, no-change, changed, reactivated, stale, retained-stale, duplicate-row, and deterministic-identity tests pass.
- Website, GitHub, local Markdown/PDF, DuckDB, BigQuery, and Snowflake planning emit the exact plan-level source variant even with zero upserts; row-level invariant metadata agrees and variant path/document metadata remains row-level.
- Successful output contains exactly `plan.json` and `delta.duckdb`; no manifest, chunks JSONL, summary sidecar, pages, checkout, source staging, credentials, or private paths remain.
- Planning remains turbopuffer/model/write inert and existing source-specific credential/API boundaries are unchanged.

## Evidence expectations

Record focused tests and representative first/no-change/incremental artifact file/row/byte counts, proving unchanged content is not persisted and logical verification catches count/hash/schema/identity tampering.

## Design notes

Use DuckDB's open-source embedded API already required by the project. Prefer a small fixed SQL schema and deterministic ordered logical hashing over abstractions or binary-format assumptions. Update shared planning-service result objects only as required by the new contract.

## Progress and notes

- 2026-07-24: Opened from the user-ratified hard-cutover contract. No implementation started.

## Blockers

None.

## Exclusions

Apply execution, Command Center UI/API integration, legacy cleanup/migration, row/chunk identity changes, and unrelated source refactors.
