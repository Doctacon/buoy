Status: open
Created: 2026-07-24
Updated: 2026-07-24
Parent: None
Depends-On: None

# Compact Delta Plan Hard Cutover

## Scope

Coordinate the schema-v2 compact-delta hard cutover from current `develop` on `work/compact-delta-plan-artifacts`, governed by `.10x/decisions/compact-delta-plan-storage.md` and `.10x/specs/compact-delta-plan-artifacts.md`.

## Child work

1. `.10x/tickets/done/2026-07-24-implement-compact-delta-planning.md`
2. `.10x/tickets/2026-07-24-implement-compact-delta-apply.md`
3. `.10x/tickets/2026-07-24-integrate-compact-delta-command-center.md`

Planning establishes schema-v2 artifacts and source coverage. Apply consumes only that format and enforces baseline drift. Command Center/managed jobs then adopt the new artifacts, remove payload-heavy inventory behavior, update docs/static/package surfaces, and run integrated validation.

## Aggregate acceptance criteria

- Every current source kind emits exactly `plan.json` and `delta.duckdb` with no unchanged content or retained source staging.
- Dry-run and approved apply verify the exact delta, fail before side effects on state drift, preserve current approval/stale/catalog recovery semantics, and never reacquire sources.
- Schema-1 artifacts receive no runtime discovery/support/migration/deletion; explicit apply rejects safely.
- Command Center list/dashboard requests do not open delta payloads; selected-plan review is bounded and changed-content-only.
- Managed jobs, docs, packaging, static assets, and tests agree with schema 2.
- Independent review has no unresolved blocking finding and evidence maps all acceptance scenarios.
- The branch is committed for handoff without push, PR, merge, publish, release, real apply, turbopuffer write, or user-artifact deletion.

## Progress and notes

- 2026-07-24: User ratified local DuckDB as the credential-free incremental baseline, exact compact changed/stale delta persistence, changed-content-only review, fail-and-replan state drift, all-source hard cutover, no schema-1 support, and no automatic legacy/upgrade deletion. User separately removed current ignored artifact contents. Existing prospective cleanup of successfully applied or superseded new-format plans remains active.
- 2026-07-24: Created active decision/specification set and bounded executable child tickets, then corrected the ordinary work branch to current `origin/develop` `d2d83eb741c7cac2bb1b708f903db4bdbeca0258` before implementation.
- 2026-07-24: Independent shaping review initially failed on regeneration detail, no-change provenance, catalog lineage, cleanup scope, inventory validity levels, baseline projection, no-change apply, route conflicts, performance bounds, and branch governance. Records were hardened to exact schema/hash/source contracts and active authorities reconciled; implementation remains unstarted.
- 2026-07-24: Subsequent reviews exposed and resolved remaining catalog source-authority, database schema-1 compatibility, removed page-route, and destructive cleanup verification conflicts. Final shaping review passed with no blocker at `.10x/reviews/2026-07-24-compact-delta-plan-shaping.md`.
- 2026-07-25: Planning child closed after exact schema-v2 writer/verifier implementation, 193-test focused validation, and adversarial review closure at `.10x/reviews/2026-07-25-compact-delta-planning.md`.

## Blockers

None.

## Exclusions

No automatic legacy cleanup/migration, remote planning baseline, source reacquisition during apply, new source/stale semantics, bulk catalog migration, browser mutation authority, real provider writes, or release/integration side effects.
