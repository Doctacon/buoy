Status: open
Created: 2026-07-24
Updated: 2026-07-24
Parent: .10x/tickets/2026-07-24-compact-delta-plan-hard-cutover.md
Depends-On: .10x/tickets/2026-07-24-implement-compact-delta-planning.md, .10x/tickets/2026-07-24-implement-compact-delta-apply.md

# Integrate Compact Delta Command Center and Validation

## Scope

Adopt schema-v2 artifacts in Command Center local inventory, managed plan jobs, frontend review, docs, packaging/static assets, and integrated validation.

## Acceptance criteria

- Dashboard, plan history, and namespace inventory summary-qualify schema-v2 plans from bounded `plan.json` plus sibling delta file type/presence, label payload verification `not_checked` internally, and never open `delta.duckdb`; schema-1 directories are inert and ignored without payload reads or warnings.
- Selected plan detail fully verifies one delta and exposes existing `/chunks` as bounded changed/new rows plus new bounded `/stale-rows`; schema-v1 page routes are removed and no arbitrary replacement appears.
- No arbitrary filesystem path/SQL, apply, delete, retry/resume/cancel, credential, catalog, namespace, or graph mutation control is added.
- Managed jobs stage, verify, publish, and report success for exactly `plan.json` and `delta.duckdb`; restart/shutdown/job identity/security behavior remains intact.
- CLI help, README/guide, source-specific docs, active specs/knowledge, package inventories, and tests no longer claim schema-v1 artifacts or compatibility.
- Frontend tests/build/static synchronization and installed-wheel behavior pass.
- Performance tests use at least 1,000 maximum-size plan summaries plus a 100,000-row selected delta sentinel and enforce the spec's exact zero-payload inventory, one-selected-connection, SQL limit/offset, response bound, and materialized-row limits; evidence records host wall time and peak RSS.
- Active API/operator/source/catalog/cleanup/docs/knowledge records are coherent with schema 2, catalog lineage 1/2, removed page routes, and prospective schema-2-only cleanup.
- Full Python, focused UI-extra, frontend, ranking/C6 contract, package build, and default-environment restoration checks pass.
- Independent review maps all active-spec criteria and finds no unresolved blocker; evidence and terminal ticket graph are coherent.

## Evidence expectations

Create durable evidence for API/UI behavior, managed jobs, schema-1 inertness, payload-open spies, bounded pagination, packaging, exact test counts, and residual platform limits. No real source/provider mutation is required.

## Progress and notes

- 2026-07-24: Opened from the user-ratified hard-cutover contract. Depends on planning and apply children.

## Blockers

None.

## Exclusions

Browser apply authority, automatic legacy cleanup/migration, remote-first inventory redesign, new source kinds, real turbopuffer writes, push/PR/merge/publish/release.
