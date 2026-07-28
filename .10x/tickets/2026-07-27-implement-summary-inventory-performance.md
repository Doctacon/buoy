Status: open
Created: 2026-07-27
Updated: 2026-07-27
Parent: .10x/tickets/2026-07-27-command-center-inventory-performance-plan.md
Depends-On: .10x/tickets/done/2026-07-27-baseline-command-center-inventory-performance.md

# Implement Summary Inventory Performance

## Scope

Implement the complete local-summary core in `applied_state.py` and `command_center_local.py`: plan-directory traversal pruning, exact summary-only state inspection with aggregate SQL, and a locked per-service 1.0-second injectable-TTL snapshot cache with safe invalidation and one-refresh direct misses.

## Acceptance criteria

- Any directory containing `plan.json` clears `os.walk()` descendants before current-plan processing, regardless of plan validity/schema; sibling discovery, schema-1 inertness, malformed isolation, root containment, symlink fail-closed behavior, and zero delta opens remain intact.
- A separate applied-state summary model/reader uses exactly one read-only connection, exact schema/metadata/path/identity validation, aggregate allowed-status counts, pre/post file identity checks, reliable close, and no mutation.
- Inventory no longer calls `load_applied_state`, executes the full ordered row query, or constructs `AppliedStateRow` objects for summaries; 100,000-row structural tests prove O(1) Python result materialization and exact active/retained/deleted/total counts.
- One service-local cache uses default TTL 1.0 seconds, injectable clock/TTL, a lock around cache/rebuild, cached errors, safe non-raising `invalidate`, expiry refresh, no stampede, and exactly one forced refresh for direct plan/namespace misses.
- Cached records cannot bypass full selected-plan identity and payload verification; summary construction imports no remote/provider/model/source adapter.
- Focused traversal/state/cache tests cover every governing scenario without committing huge fixtures.

## Evidence expectations

Record focused commands/results, structural query/traversal/cache-spy observations, changed files, and safety limits. Do not close before independent downstream integration validation.

## Progress and notes

- 2026-07-27: Opened from the ratified performance contract; implementation waits on baseline evidence.

## Blockers

Dependency only.

## Exclusions

Managed-job callback wiring, API route threading, docs/package/full validation, schema changes, selected-verification caching/bypass, and unrelated refactors.

## References

- `.10x/specs/command-center-summary-inventory-performance.md`
- `.10x/specs/command-center-local-inventory.md`
- `.10x/specs/compact-duckdb-applied-state.md`
- `.10x/specs/compact-delta-plan-artifacts.md`
