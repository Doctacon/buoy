Status: done
Created: 2026-07-24
Updated: 2026-07-25
Parent: .10x/tickets/done/2026-07-24-compact-delta-plan-hard-cutover.md
Depends-On: .10x/tickets/done/2026-07-24-implement-compact-delta-planning.md

# Implement Compact Delta Apply

## Scope

Replace schema-v1 manifest apply with schema-v2 compact-delta verification, preflight, approved execution, and applied-state transition governed by `.10x/specs/compact-delta-plan-artifacts.md`.

## Acceptance criteria

- Explicit apply accepts schema 2 only and rejects schema 1 without legacy payload reads or mutation. Implicit latest-plan discovery skips schema-1/malformed candidates and selects the newest summary-qualified schema-2 plan, or reports no supported plan.
- Verification enforces regular/no-follow artifact boundaries, fixed DuckDB schema, plan/delta identity, unique rows, counts, embedding hashes, source metadata safety, logical delta hash, artifact hash, and plan ID.
- Dry-run reloads state, compares the exact presence-bound baseline projection, reports exact upsert/stale effects, and performs no credentials/model/source/provider/state activity.
- Approved apply acquires the namespace lock, rechecks baseline under lock, and fails with replan guidance before every side effect if state drifted.
- Apply embeds/upserts only verified delta upserts, applies current `--delete-stale` behavior only to verified stale IDs, and computes next state by combining the unchanged verified baseline with delta operations.
- Exact changed content is applied without crawl, clone, local document access, database connection, source credentials, or source API calls.
- Current batching, progress, interactive/`--approve` gates, float precision, pending catalog recovery, atomic DuckDB state commit, prospective schema-2 cleanup, and failure ordering remain correct. Approved no-change apply preserves the exact lineage/catalog/zero-row apply-run behavior in the spec.
- Tests cover first/no-change/changed/reactivated/stale retain/delete, absent-to-empty and other drift before preflight, drift between preflight and lock, tampering, interrupted/failed provider work, catalog partial success, schema-1/2 card lineage, schema-2 cleanup, and no old local-format support.

## Evidence expectations

Record focused preflight/apply tests and side-effect spies proving drift/tamper/old-schema failures occur before credential reads, model loads, remote calls, pending writes, or state mutation.

## Progress and notes

- 2026-07-24: Opened from the user-ratified hard-cutover contract. Depends on the schema-v2 planning child.
- 2026-07-25: Planning dependency and its evidence/review are done. Started schema-v2 apply implementation after reading the governing apply, catalog, state, pending, cleanup, and interaction contracts.
- 2026-07-25: Replaced manifest/chunks apply with full compact-delta verification and presence-bound state checks before preflight and under lock; implemented baseline-plus-delta next state, plan-level catalog semantics, schema-1 explicit rejection/implicit skip, catalog lineage 1/2 compatibility, and schema-v2 cleanup continuity without source reacquisition.
- 2026-07-25: Added drift/ordering/hard-cutover/no-change assertions and updated apply/catalog fixtures to build against their real state baseline. Focused apply suite passed 53 tests; combined apply/catalog/pending/remote/state/cleanup/planning/CLI basket passed 225 tests. Evidence is `.10x/evidence/2026-07-25-compact-delta-apply.md`.
- 2026-07-25: Independent review found applied-state load/presence TOCTOU, cleanup replacement races, incomplete delta action-to-baseline classification, and missing reactivation/zero-row ledger coverage. Added stable no-follow state identity observation around every preflight/under-lock load; exact action lineage checks; atomic descriptor-relative quarantine, reverify, and fd-safe deletion bound to plan ID/hash/namespace/directory identity; applied/supersession race, schema-1, corrupt, reactivation, and zero-row ledger regressions. Expanded focused basket passed 232 tests.
- 2026-07-25: Rereview found state-path ABA remained possible, supersession did not compare validated plan creation order, CLI cleanup used preflight rather than under-lock identity, and `changed` accepted an unchanged same row. State now loads an inode-bound private snapshot and detects swap/read/restore through parent identity; cleanup retains equal/newer plans and same-namespace race replacements; exact changed classification rejects unchanged rows. Focused apply/cleanup passed 67 tests and the expanded basket passed 234.
- 2026-07-25: Final review found logical plan ID/hash/namespace could not distinguish an A→B→A swap when A and B were identical. Added a typed internal cleanup binding captured by successful under-lock full verification, carrying exact directory device/inode to CLI cleanup without public output. The identical-artifact A→B→A regression proves B applies while restored A and B remain with a warning. Focused 67 and expanded 234 tests pass; compilation and diff checks pass.
- 2026-07-25: Independent final review passed with no blocker at `.10x/reviews/2026-07-25-compact-delta-apply.md`. Acceptance criteria map to `.10x/evidence/2026-07-25-compact-delta-apply.md`; the child is closed.

## Blockers

None.

## Exclusions

New remote/stale/catalog semantics, source reacquisition, automatic reconciliation, Command Center integration, real apply, and turbopuffer writes.
