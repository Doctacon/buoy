Status: done
Created: 2026-07-24
Updated: 2026-07-25
Parent: .10x/tickets/done/2026-07-24-compact-delta-plan-hard-cutover.md
Depends-On: .10x/tickets/done/2026-07-24-implement-compact-delta-planning.md, .10x/tickets/done/2026-07-24-implement-compact-delta-apply.md

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
- 2026-07-25: Both dependencies are done with passing evidence/review. Started final Command Center, managed-job, frontend, docs/package, performance, and integrated validation work on the compact-delta branch.
- 2026-07-25: Implemented summary-qualified schema-v2 inventory, fully verified changed/stale detail routes, schema-v1 page-route/UI removal, two-file managed-job expectations, synchronized frontend/static assets, and docs. Added exact 1,000 × 131,072-byte summary and 100,000-row selected-delta structural tests. UI-extra 149-test basket, 37 frontend tests/build, 764-test default full suite, ranking/C6, temporary installed-wheel checks, default restoration/import isolation, compile, and diff checks passed.
- 2026-07-25: Independent review found summary qualification did not recompute plan identity or distinguish unsupported schema 3, selected payload routes were not bound to the inventory record across replacement/ABA, and performance proof tested a query helper rather than the production connection path. Repaired full plan-only identity/count validation, exact schema1 inertness versus malformed-version errors, directory/plan/delta identity plus logical record binding for detail/chunks/stale, deterministic replacement/ABA coverage, and a forwarding production connection/query spy proving LIMIT/OFFSET and ten-row materialization. Post-review local/API/jobs passed 88 tests; full UI-extra discovery passed 766; structural tests ran in 5.80 seconds / 212,959,232 bytes RSS. Evidence updated at `.10x/evidence/2026-07-25-compact-delta-command-center.md`.
- 2026-07-25: Independent final review passed with no blocker at `.10x/reviews/2026-07-25-compact-delta-command-center.md`. Acceptance criteria map to the evidence record; the child is closed.

## Blockers

None.

## Exclusions

Browser apply authority, automatic legacy cleanup/migration, remote-first inventory redesign, new source kinds, real turbopuffer writes, push/PR/merge/publish/release.
