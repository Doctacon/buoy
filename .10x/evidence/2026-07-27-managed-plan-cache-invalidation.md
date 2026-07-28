Status: recorded
Created: 2026-07-27
Updated: 2026-07-27
Relates-To: .10x/tickets/2026-07-27-integrate-managed-plan-cache-invalidation.md, .10x/specs/command-center-managed-plan-cache-invalidation.md

# Managed Plan Cache Invalidation Integration

## What was observed

`PlanJobService` now accepts one optional zero-argument publication callback. A deterministic executor test observed the callback exactly once with the durable record already in `succeeded`, its verified `plan_id` present, and the durable terminal event already readable. Unverified and failing planning services issued no callback; startup recovery of a queued record to `interrupted` issued no callback.

A callback that raised `RuntimeError("RAW-CALLBACK-SECRET /private/callback")` left the job and terminal event succeeded. The log contained only the exception type and contained neither the callback message nor private path. Separate offline managed-publication coverage verified that a raising callback ran once while the succeeded job retained exactly its valid `plan.json` and `delta.duckdb` artifacts.

Default Command Center construction supplies its process-local inventory `invalidate()` method. An API integration test first cached an empty plan inventory, published a valid schema-v2 plan through the default managed job service, observed durable success, and immediately read the new plan from `/api/v1/plans` without waiting for the 1.0-second TTL.

## Procedure and results

```bash
PYTHONPATH=src .venv/bin/python -m unittest \
  tests.test_command_center_jobs.PlanJobServiceTests.test_publication_callback_runs_once_after_durable_success \
  tests.test_command_center_jobs.PlanJobServiceTests.test_raising_publication_callback_is_logged_by_type_and_cannot_fail_success \
  tests.test_command_center_jobs.PlanJobServiceTests.test_restart_interruption_does_not_call_publication_callback \
  tests.test_command_center_jobs.PlanJobServiceTests.test_unverified_result_cannot_transition_to_success \
  tests.test_command_center_jobs.PlanJobServiceTests.test_failure_preserves_safe_record_without_plan_id_or_raw_exception
```

Passed 5 tests.

```bash
uv run --extra ui python -m unittest \
  tests.test_command_center_api.CommandCenterApiTests.test_default_managed_job_publication_is_immediately_discoverable \
  tests.test_command_center_api.CommandCenterApiTests.test_csrf_issuance_valid_creation_and_service_lifecycle
```

Passed 2 tests. The second test retains the zero-argument injected fake factory contract.

```bash
uv run --extra ui python -m unittest tests.test_command_center_jobs tests.test_command_center_api
```

Passed all 79 job/API tests, covering lifecycle, one-active, publication, recovery/interruption, SSE, shutdown, security, provider/source, and application construction boundaries.

```bash
uv run --extra ui python -m unittest tests.test_planning_service tests.test_command_center_cli
```

Passed all 14 shared-planning and Command Center CLI tests.

```bash
.venv/bin/python -m py_compile src/buoy_search/command_center_jobs.py src/buoy_search/command_center_api.py tests/test_command_center_jobs.py tests/test_command_center_api.py
git diff --check
grep -nE 'FastAPI|command_center_local' src/buoy_search/command_center_jobs.py || true
```

Compilation and diff checks passed. The import-boundary grep produced no matches.

## Design evidence

- Result plan ID, namespace, requested namespace, output path, and held precreated output are checked before the durable succeeded transition.
- The callback runs only after `PlanJobStore.transition(..., "succeeded")` returns; callback exceptions are caught outside planning failure handling and logged by type only.
- The normal success notification follows the callback, so observers awakened for terminal success see the invalidated inventory cache.
- Injected `plan_job_service_factory` remains invoked with zero arguments; only default construction supplies `inventory.invalidate`.
- `command_center_jobs.py` imports neither FastAPI nor `command_center_local`; ordinary CLI construction supplies no callback and is unchanged.

## Limits

Invalidation is intentionally process-local, non-persistent, and not replayed after restart. External-process publication remains bounded by the summary TTL, as specified. No API route threading, documentation, packaging, benchmark timing, or cross-process coordination was changed or validated by this child.
