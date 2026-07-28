Status: recorded
Created: 2026-07-27
Updated: 2026-07-27
Relates-To: .10x/tickets/2026-07-27-move-blocking-command-center-routes-off-event-loop.md, .10x/specs/command-center-blocking-route-threading.md

# Command Center Blocking Route Threading

## What was observed

FastAPI now classifies the synchronous-service dashboard, namespace list/detail, plan list/detail/chunks/stale rows, plan-job list/detail, remote snapshot, and search endpoints as normal synchronous route handlers. Starlette therefore dispatches those endpoint functions through its bounded worker-thread capacity. Plan-job creation and the plan-job SSE endpoint remain asynchronous; bounded creation-body reading, the existing synchronous SSE generator, replay, terminal drain, disconnect, and connection-cap behavior are unchanged. No executor or route schema was added.

Two event-coordinated concurrency tests use one shared `TestClient` lifespan/event loop:

1. A fake dashboard call enters a worker and waits on a `threading.Event`. Before the release event is set, health returns `200`, a concurrent missing-namespace lookup returns the exact structured `namespace_not_found` `404`, and the dashboard request remains blocked. After release it returns its own exact dashboard payload; no client thread receives a raw exception.
2. A fake plan inventory call waits on a `threading.Event` while a durable fake plan job remains `queued`. Before release, plan-job detail returns `200` with that active job ID and state while the plan request remains blocked. After release the plan response returns normally.

A structural route test also confirms the complete required sync route set and confirms plan-job `POST` creation plus plan-job event `GET` remain coroutine endpoints.

## Procedure and results

```bash
uv run python -m unittest \
  tests.test_command_center_api.CommandCenterApiTests.test_blocking_service_routes_are_sync_with_async_creation_and_sse_boundaries \
  tests.test_command_center_api.CommandCenterApiTests.test_blocked_dashboard_does_not_block_health_or_corrupt_structured_errors \
  tests.test_command_center_api.CommandCenterApiTests.test_active_plan_job_detail_is_observable_while_plan_inventory_is_blocked -v
```

Passed 3 synchronization/route-boundary tests.

```bash
uv run python -m unittest tests.test_command_center_api tests.test_command_center_jobs tests.test_command_center_remote -v
```

Passed 99 focused API, managed-job/store/SSE, security-boundary, remote snapshot, and search tests. This includes Host and same-origin/CSRF/explicit-POST guards, bounded job creation, structured errors, list/detail bounds and integrity mapping, SSE replay/live completion/terminal drain/disconnect/cap behavior, startup laziness, provider credential boundaries, remote no-write behavior, and search validation.

```bash
uv run python -m compileall -q src/buoy_search/command_center_api.py tests/test_command_center_api.py
git diff --check
```

Both passed.

`uv run ruff check src/buoy_search/command_center_api.py tests/test_command_center_api.py` could not run because this environment does not install a `ruff` executable; it made no repository changes. Compile, focused tests, and diff checks passed independently.

## Design evidence

- Only endpoint declaration mode changed in production source: eleven blocking service endpoint functions changed from `async def` to `def`.
- Middleware remains asynchronous, including the exact bounded `request.stream()` body reader used before plan-job creation.
- Plan-job event setup and `_sse_events` were not edited. The existing synchronous streaming iterator remains eligible for Starlette's streaming thread-pool iteration without changing durable observation semantics.
- Local service calls, selected-plan verification calls, job-store calls, remote snapshot/search construction and execution, response serialization, exception handlers, and request models are byte-for-byte unchanged within the production diff.
- No `run_in_executor`, custom `ThreadPoolExecutor`, executor configuration, schema, middleware, credential, provider, frontend, startup, package, documentation, benchmark, summary-core, or invalidation code was added or changed.

## Limits

This child does not claim behavior under complete exhaustion of Starlette's bounded worker capacity; the ratified criterion is that one slow inventory request alone does not stall unrelated health or active plan-job observation. Timing benchmarks, package/frontend/full-suite validation, and independent adversarial review remain downstream. The ticket intentionally remains open and unmoved for the required review gate.

The first concurrency-only test execution passed the route-boundary and plan-observation cases but hit a test-setup `JobIntegrityError` before the dashboard case: entering a lifespan with the default durable service used the unresolved platform temporary path. The dashboard concurrency test was narrowed to its intended API boundary by injecting the existing fake plan-job service, avoiding unrelated durable-root construction; the identical three-test command then passed, followed by the 99-test focused basket above.
