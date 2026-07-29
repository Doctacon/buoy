Status: recorded
Created: 2026-07-28
Updated: 2026-07-28
Relates-To: .10x/tickets/done/2026-07-28-implement-bounded-review-backend.md, .10x/specs/command-center-bounded-inventory-transport.md, .10x/specs/command-center-coalesced-plan-review.md

# Bounded Review Backend Implementation Evidence

## What was observed

The backend now filters the one cached plan/namespace summary snapshot before pagination, returns filtered totals without rebuilding for filter changes, bounds namespace plan history to a default 20 and maximum 100, and exposes a typed combined plan review plus synchronous `GET /api/v1/plans/{plan_id}/review`.

Instrumented service and API tests observed exactly one complete verifier invocation for combined review with `materialize=False`, `upsert_window=(0, 1)`, and `stale_window=(1, 1)`. The additive detail, chunks, and stale operations each added exactly one invocation. Invalid combined windows added zero invocations. Combined output detail, changed chunks, and stale rows came from the one verifier result.

A 1,000-plan/1,000-namespace maximum-summary structural regression observed one plan scan across unfiltered and filtered requests; filtered totals and deterministic filtered pagination were exact, and no delta verifier, delta open, or DuckDB connection occurred. A separate 125-plan namespace regression returned 20 plans by default, no more than 100 for explicit windows, and exact total/offset/limit/truncation metadata.

Existing replacement and A→B→A regressions now include the combined operation. Corrupt delta and invalid-window regressions include combined review. A fresh-process combined-review regression observed no provider/model/source-specific adapter modules, and existing startup/summary inertness regressions remained passing.

## Procedure and results

A temporary ignored `src/buoy_search/_version.py` validation shim was needed because this worktree does not contain the hatch-generated ignored version module. It was removed after validation, along with bytecode.

```bash
uv sync --locked --extra ui
printf '__version__ = "0.0.0+validation"\n' > src/buoy_search/_version.py
PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests.test_command_center_local tests.test_command_center_api tests.test_plan_artifacts tests.test_command_center_inventory_benchmark tests.test_command_center_bounded_review_benchmark -v
rm -f src/buoy_search/_version.py
```

Final rerun passed 87 tests in 9.640 seconds. The basket covers service/API filter contracts, 1,000-plan structural bounds, namespace history, exact verifier counts, simultaneous verifier windows, invalid inputs, corrupt/replaced/ABA artifacts, provider/model/source-specific adapter inertness, existing schema-v2 verification, API security/threading, and synchronized benchmark fixture contracts.

```bash
PYTHONDONTWRITEBYTECODE=1 uv run python -m compileall -q -f -b src/buoy_search/command_center_local.py src/buoy_search/command_center_api.py scripts/benchmark_command_center_inventory.py tests/test_command_center_local.py tests/test_command_center_api.py
find src tests scripts -type f -name '*.pyc' -delete
git diff --check
git status --short
```

Compilation and diff hygiene passed. No file is staged. The status contains the expected inherited baseline/spec/ticket/frontend-characterization changes plus this ticket's backend source, focused tests, benchmark contract, ticket progress, and evidence; no generated version module or bytecode remains.

## Verifier counts

- Combined service review: 1 request operation → exactly 1 complete verifier call.
- Combined API review: 1 HTTP request → exactly 1 complete verifier call.
- Standalone detail: 1 request → exactly 1 complete verifier call.
- Standalone chunks: 1 request → exactly 1 complete verifier call.
- Standalone stale rows: 1 request → exactly 1 complete verifier call.
- Invalid combined window: 0 verifier calls.

## Independent-review repair evidence

The selected-plan seam now takes descriptor/no-follow bounded `plan.json` snapshots before and after the complete verifier, compares the complete verified document (including identity-excluded `created_at` and `originating_job_id`), and compares directory/plan/delta inode plus size/mtime/ctime observations across verification. Adversarial regressions swap only the identity-excluded metadata during verification, restore it before postcheck, and prove that combined review plus all three standalone payload operations fail closed. A compatibility regression rewrites those fields before an operation without replacing the inode and proves standalone detail and combined review return the current stable metadata.

Namespace `local_status=error` is now derived only from malformed or unsafe state artifacts at the canonical `state/<safe-site-id>/<safe-namespace>/state.duckdb` ownership path. Malformed plans, noncanonical state paths, and process capability failures remain isolated errors and do not manufacture namespace rows. Service and API regressions prove the error filter is reachable. Source-kind filter coverage now uses seven distinct namespaces and observes website 1, GitHub repository 1, document 2, database 3, and unknown 0 for both plans and namespaces.

```bash
PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests.test_command_center_local tests.test_command_center_api tests.test_plan_artifacts tests.test_command_center_inventory_benchmark tests.test_command_center_bounded_review_benchmark -v
```

The repaired focused basket passed 89 tests in 10.398 seconds. It includes the new transient-metadata ABA, stable pre-operation metadata rewrite, attributable namespace error, malformed-item isolation, API error-filter, and distinct-namespace source-kind regressions alongside the prior verifier-count, artifact, API, and benchmark-contract coverage.

```bash
PYTHONDONTWRITEBYTECODE=1 uv run python -m compileall -q -f -b src/buoy_search/command_center_local.py src/buoy_search/command_center_api.py scripts/benchmark_command_center_inventory.py tests/test_command_center_local.py tests/test_command_center_api.py
find src tests scripts -type f -name '*.pyc' -delete
rm -rf src/buoy_search/__pycache__
git diff --check
test -z "$(git diff --cached --name-only)"
test ! -e src/buoy_search/_version.py
test -z "$(find src/buoy_search -type d -name __pycache__ -print -quit)"
```

Compilation, diff hygiene, no-staged-file, temporary-version-shim removal, and reviewer-created `src/buoy_search/__pycache__` removal checks passed.

## Limits

This is focused backend validation and repair evidence, not rereview, frontend implementation, final benchmark timing, documentation, full-suite validation, or package validation. Complete delta verification remains intentionally linear. The ticket remains active pending required independent rereview.
