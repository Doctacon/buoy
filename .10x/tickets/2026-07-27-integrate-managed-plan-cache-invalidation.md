Status: open
Created: 2026-07-27
Updated: 2026-07-27
Parent: .10x/tickets/2026-07-27-command-center-inventory-performance-plan.md
Depends-On: .10x/tickets/2026-07-27-implement-summary-inventory-performance.md

# Integrate Managed Plan Cache Invalidation

## Scope

Add an optional framework-independent successful-publication callback to `PlanJobService` and wire the Command Center's inventory invalidation callback through default application construction.

## Acceptance criteria

- Callback runs exactly once only after verified publication and durable transition to `succeeded`.
- Successful managed plans become immediately discoverable from the cached inventory.
- Failed/interrupted/incomplete jobs do not announce successful publication.
- Callback failure is safely caught/logged and cannot fail the completed job or alter artifacts.
- Job service imports no FastAPI/local-inventory implementation and ordinary CLI behavior is unchanged.
- Existing lifecycle, one-active, durability, descriptor/publication, shutdown, progress/SSE, credential, and provider boundaries pass focused regression coverage.

## Evidence expectations

Focused jobs/API tests with exact success/failure/callback-order observations and no provider/source work.

## Progress and notes

- 2026-07-27: Opened; dependency not yet executed.

## Blockers

Dependency only.

## Exclusions

Cross-process cache coordination, watcher, callback persistence/replay, job semantic changes, and API threading.

## References

- `.10x/specs/command-center-managed-plan-cache-invalidation.md`
- `.10x/specs/phase-2a-plan-job-lifecycle.md`
- `.10x/specs/phase-2a-public-source-planning-service.md`
