Status: open
Created: 2026-07-27
Updated: 2026-07-27
Parent: .10x/tickets/2026-07-27-command-center-inventory-performance-plan.md
Depends-On: None

# Baseline Command Center Inventory Performance

## Scope

From untouched base source `01f2d19432c4bc77e9d6bd7ab8a657b5f4583521`, create a disposable temporary synthetic fixture and reproducible benchmark harness/method that can be rerun after implementation. Measure existing behavior before source changes.

Fixture: 1,000 near-131,072-byte valid schema-v2 plan summaries with sibling delta sentinels that summary inventory must not open; one deeply nested/high-file-count schema-v1 pages tree; one 100,000+-row applied-state database plus several smaller databases; and one fully valid selected schema-v2 delta with changed and stale rows suitable for early/later/near-end pages. Generated artifacts remain outside the repository and are deleted after measurement.

## Acceptance criteria

- Record base commit, OS/architecture, Python/DuckDB versions, exact fixture counts, fixture construction/reuse method, and peak RSS when practical.
- Record cold plus at least five warm repetitions and median/p50 for Dashboard, Plans, Namespaces, namespace detail, plan detail, changed page 1/later page, and near-end stale page.
- Separate summary inventory from selected full-verification timing.
- Capture structural baseline observations: descendant traversal, plan/state scan frequency, delta opens, applied-row materialization, and endpoint event-loop behavior where safely observable.
- Preserve exact commands/fixture parameters so the final child can rerun the same measurement.
- Commit no generated plan, delta, state, legacy tree, browser profile, raw log, or private path.

## Evidence expectations

Create a bounded baseline evidence/research artifact under `.10x/evidence/` or `.10x/research/` with observational limits and no private paths.

## Progress and notes

- 2026-07-27: Opened from the ratified performance brief; no benchmark executed yet.
- 2026-07-27: Added the bounded reusable disposable driver `scripts/benchmark_command_center_inventory.py` and its focused test. The driver creates the exact synthetic plan/state/legacy fixture in a system temporary directory, validates the selected delta, measures process-cold plus five same-service warm calls in isolated workers, emits machine-readable JSON, and removes the fixture. It invokes no provider, source, plan, or apply operation.
- 2026-07-27: Recorded the unchanged-base host baseline and structural observations in `.10x/evidence/2026-07-27-command-center-inventory-performance-baseline.md`. Warm p50 was 678.291 ms Dashboard, 688.501 ms Plans, 685.911 ms Namespaces, 671.639 ms namespace detail; selected full-verification p50 was 3,323.781 ms plan detail, 3,338.170 ms changed page 1, 3,335.544 ms later changed page, and 3,374.436 ms near-end stale page. The ticket remains open for parent verification and reconciliation as requested.

## Blockers

None.

## Exclusions

Implementation changes, private user artifacts, live crawls/clones/providers/search/apply, and permanent benchmark fixture files.

## References

- `.10x/specs/command-center-summary-inventory-performance.md`
- `.10x/tickets/2026-07-27-command-center-inventory-performance-plan.md`
