Status: done
Created: 2026-07-24
Updated: 2026-07-25
Parent: .10x/tickets/done/2026-07-24-compact-delta-plan-hard-cutover.md
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
- 2026-07-24: Started implementation on `work/compact-delta-plan-artifacts`; read the governing decision/specification and began mapping shared planning, artifact, diff, applied-state, and source-specific contracts.
- 2026-07-24: Implemented schema-v2 `plan.json` plus exact three-table `delta.duckdb`, presence-bound baseline hashing, deterministic logical/artifact identities, all source variants, changed/stale-only rows, full logical verification, managed two-file publication, source-staging removal, and schema-v2 prospective cleanup verification. Removed schema-v1 writer behavior.
- 2026-07-24: Added/updated compact artifact, planning service, CLI, GitHub, and database source tests. Combined focused planning/source basket passed 179 tests; evidence recorded at `.10x/evidence/2026-07-24-compact-delta-planning.md`. Ticket remains active pending required independent review; dependent apply/Command Center tests are intentionally not repaired in this child.
- 2026-07-24: Independent review failed the initial verifier: logical hashing renamed SQL contract keys, and re-signed deltas could bypass canonical ordering/JSON, row/hash/path/source/stale/diff invariants or add macros. Repaired exact logical serialization and full verification, added direct golden/privacy and deterministic re-signed tamper tests, and passed the expanded 183-test planning/source basket.
- 2026-07-24: Second rereview found extra application objects outside `main` were accepted, source metadata values could hide credential-bearing URIs, document filename/URI authority and variant consistency were incomplete, first-apply verification incorrectly inferred pages from upserts, and tag ordering was not enforced. Repaired every finding, narrowed the spec to independently derivable operation counts while identity-binding omitted page/unchanged counts, added cross-schema object/privacy/source/tag/diff/zero-chunk tests, and passed an expanded 186-test planning/source basket plus compilation and diff checks.
- 2026-07-25: Final rereview found re-signed foreign canonical URLs, incomplete metadata-alias checks, non-derived plan identities, and narrower privacy markers. Bound upsert/stale URLs to all seven source authorities, enforced all present PDF/DuckDB aliases, recomputed site/candidate/schema identity, expanded privacy denials while allowing safe ranking/tokenizer fields, made every zero-upsert source fixture write/full-verify, and added re-signed regressions. Focused module passed 15 tests; expanded planning/source basket passed 188 tests; compilation and diff checks passed.
- 2026-07-25: Privacy/source-authority review found open-ended metadata and URI query/fragment gaps. Replaced metadata acceptance with exact per-source-kind allowlists, classified all current/legacy fields including `duckdb_document_id`, rejected unknown/cross-kind/provider metadata and secret/connection URIs, required canonical stored website source normalization, and preserved legitimate nonsecret website query/fragment behavior. Re-signed adversarial/positive regressions raised the focused module to 17 tests and expanded basket to 190 passing tests.
- 2026-07-25: Final nested-URI review found repeated percent encoding could hide userinfo or PostgreSQL URIs inside safe outer HTTP query/fragment values. Added one bounded recursive JSON/string privacy validator across plan options, source values, tags, row metadata, and canonical URLs; opaque/database schemes are authorized only in exact source/row URL contexts. Fully re-signed nested negative and safe-public positive regressions passed; expanded planning/source basket reached 191 tests.
- 2026-07-25: Further review found over-depth percent encoding and generic POSIX paths outside selected home/temp prefixes. Decoding now fails closed if unstable at the bound, and platform-independent POSIX/Windows/UNC absolute paths are rejected while validated source URIs remain allowed. Expanded planning/source basket passed 193 tests.
- 2026-07-25: Independent final review passed with no blocker at `.10x/reviews/2026-07-25-compact-delta-planning.md`. Acceptance criteria map to `.10x/evidence/2026-07-24-compact-delta-planning.md`; the child is closed.

## Blockers

None.

## Exclusions

Apply execution, Command Center UI/API integration, legacy cleanup/migration, row/chunk identity changes, and unrelated source refactors.
