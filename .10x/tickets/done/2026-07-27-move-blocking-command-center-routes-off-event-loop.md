Status: done
Created: 2026-07-27
Updated: 2026-07-27
Parent: .10x/tickets/done/2026-07-27-command-center-inventory-performance-plan.md
Depends-On: .10x/tickets/done/2026-07-27-implement-summary-inventory-performance.md

# Move Blocking Command Center Routes Off Event Loop

## Scope

Convert compatible synchronous-service FastAPI handlers to normal `def` routes so Starlette runs blocking local inventory, selected verification, job-store, remote snapshot, and search work in its bounded thread pool. Preserve async bounded body reading and SSE streaming semantics.

## Acceptance criteria

- Dashboard, namespace list/detail, plan list/detail, chunk/stale pages, plan-job list/detail, remote snapshot, and search are sync handlers unless inspected semantics require a documented narrower exception.
- Plan-job creation retains bounded async body handling; SSE remains correct and nonblocking.
- Deterministic threading-event tests prove a blocked inventory request does not prevent health response and does not corrupt request/error state.
- Active SSE/plan-job observation is not stalled merely by a slow local inventory route.
- API contracts, structured errors, middleware, Host validation, CSRF/same-origin, bounds, startup laziness, credential boundaries, and frontend routes remain unchanged.
- No custom/unbounded executor is added.

## Evidence expectations

Focused API concurrency and compatibility results with synchronization-based proof rather than brittle timing thresholds.

## Progress and notes

- 2026-07-27: Opened; dependency not yet executed.
- 2026-07-27: Dependency is complete. Converted all required synchronous-service endpoints to normal `def` handlers while retaining async bounded plan-job creation and the existing async SSE route/synchronous generator boundary. Added event-coordinated shared-event-loop regressions proving health and exact structured inventory errors complete while dashboard inventory is blocked, and active plan-job detail remains observable while plan inventory is blocked. The structural route-boundary test and 99 focused API/job/SSE/security/remote tests pass; evidence is recorded at `.10x/evidence/2026-07-27-command-center-blocking-route-threading.md`.
- 2026-07-27: Independent review passed with no defect at `.10x/reviews/2026-07-27-command-center-blocking-route-threading-review.md`, including repeated event-coordinated tests and confirmation of bounded Starlette/AnyIO dispatch. This child is closed; final aggregate validation is unblocked.

## Blockers

Dependency only.

## Exclusions

SSE redesign, request/response schema change, custom executors, cancellation, or new remote authority.

## References

- `.10x/specs/command-center-blocking-route-threading.md`
- `.10x/specs/command-center-local-api-and-server.md`
- `.10x/specs/phase-2a-plan-job-api-security.md`
