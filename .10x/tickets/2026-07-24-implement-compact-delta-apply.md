Status: open
Created: 2026-07-24
Updated: 2026-07-24
Parent: .10x/tickets/2026-07-24-compact-delta-plan-hard-cutover.md
Depends-On: .10x/tickets/2026-07-24-implement-compact-delta-planning.md

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

## Blockers

None.

## Exclusions

New remote/stale/catalog semantics, source reacquisition, automatic reconciliation, Command Center integration, real apply, and turbopuffer writes.
