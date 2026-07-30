Status: superseded
Created: 2026-07-27
Updated: 2026-07-27

# Command Center Blocking Route Threading

## Purpose and scope

Keep synchronous filesystem, DuckDB, artifact verification, job-store, remote-client, and retrieval/model work off the FastAPI event loop by declaring compatible route handlers as normal synchronous functions so Starlette uses its bounded thread pool.

## Behavior

The following handlers MUST be synchronous unless current request/stream semantics prove otherwise:

- Dashboard, namespace list/detail, plan list/detail, changed chunks, and stale rows;
- plan-job list and detail;
- explicit remote snapshot and search.

Health, capabilities, and other handlers MAY remain async when they perform no blocking service work. Plan-job creation MUST retain the existing bounded async body-reading boundary. SSE MUST retain its streaming/replay/terminal semantics and MUST NOT be converted in a way that blocks the event loop or changes durable observation.

The implementation MUST use FastAPI/Starlette's normal sync-route thread-pool behavior, not an unbounded custom executor.

## Acceptance criteria

1. A deterministic concurrency test blocks a sync inventory call on a threading event, proves `/api/v1/health` responds before release, and observes no raw exception or request-state corruption.
2. An active SSE stream or plan job is not stalled solely by another client's blocked local inventory request.
3. Response schemas, structured errors, middleware, loopback Host validation, CSRF/same-origin behavior, request bounds, startup laziness, credential boundaries, and frontend routes remain unchanged.
4. Remote snapshot/search remain explicit POST operations and gain no new authority.

## Exclusions

No custom executor, endpoint/schema redesign, cancellation, remote-operation semantic change, browser apply, or SSE lifecycle change.
