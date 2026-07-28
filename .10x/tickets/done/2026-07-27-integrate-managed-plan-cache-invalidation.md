Status: done
Created: 2026-07-27
Updated: 2026-07-27
Parent: .10x/tickets/done/2026-07-27-command-center-inventory-performance-plan.md
Depends-On: .10x/tickets/done/2026-07-27-implement-summary-inventory-performance.md

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
- 2026-07-27: Implemented the optional framework-independent successful-publication callback and default Command Center wiring to the process-local inventory invalidator. Deterministic tests prove exact post-durable-success ordering, one call, no failure/incomplete/interruption calls, type-only isolation of callback exceptions, retained succeeded artifacts/job state, unchanged zero-argument injected factory construction, and immediate discovery from a previously cached empty inventory. All 79 focused job/API tests and 14 shared-planning/Command Center CLI tests pass; evidence is recorded at `.10x/evidence/2026-07-27-managed-plan-cache-invalidation.md`.
- 2026-07-27: Independent review passed with no blocker at `.10x/reviews/2026-07-27-managed-plan-cache-invalidation-review.md`. Every child criterion is supported; final aggregate validation remains downstream. This child is closed.

## Blockers

Dependency only.

## Exclusions

Cross-process cache coordination, watcher, callback persistence/replay, job semantic changes, and API threading.

## References

- `.10x/specs/command-center-managed-plan-cache-invalidation.md`
- `.10x/specs/phase-2a-plan-job-lifecycle.md`
- `.10x/specs/phase-2a-public-source-planning-service.md`
