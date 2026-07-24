Status: recorded
Created: 2026-07-23
Updated: 2026-07-23
Relates-To: .10x/tickets/done/2026-07-23-phase-2a-shared-planning-service.md, .10x/specs/phase-2a-public-source-planning-service.md

# Phase 2A Shared Planning Service Validation

## What was observed

The reusable planning service now owns source dispatch, acquisition orchestration, plan/artifact construction, applied-state diffing, catalog preview, summary writing, integrity verification, cleanup, and bounded progress projection. The CLI delegates its plan workflow to the service while retaining its existing argument and output adapters.

Managed requests accept only bounded public HTTP(S) website or GitHub repository-root sources. Validation enforces the ratified 2048-character URL maximum, rejects URL userinfo and GitHub tree/blob forms, requires an absent output path including dangling symlinks, and retains current website query/fragment canonicalization rather than adding a blanket rejection. Progress stages and messages are sanitized and capped at 64 and 500 characters respectively.

Focused tests observed verified ordinary artifacts with the unchanged plan schema, namespace overrides, current website/GitHub defaults, progress counts and bounds, existing-output rejection, chunk and persisted-page-content integrity failures, CLI typed delegation/JSON output, one-time database source construction through authoritative service default dispatch, no applied-state mutation, no model construction, no subprocess planning, and no managed import of database/local-document adapters. The complete default Python test suite also passed before the review repair; the repair was revalidated with the focused service and 243-test compatibility sets.

## Procedure and results

1. `uv run pytest -q tests/test_planning_service.py`
   - Result: not used for acceptance because this worktree's locked environment has no `pytest` executable; uv reported `Failed to spawn: pytest`.
2. `PYTHONPATH=src .venv/bin/python -m unittest -q tests.test_planning_service`
   - Result: passed after the final bound/canonicalization changes.
   - Output: 6 tests ran; `OK`.
3. `PYTHONPATH=src .venv/bin/python -m unittest -q tests.test_planning_service tests.test_cli tests.test_apply_cli tests.test_crawler tests.test_github_repo tests.test_database_relation tests.test_database_relation_cli tests.test_duckdb_relation tests.test_duckdb_relation_cli tests.test_bigquery_relation tests.test_snowflake_relation`
   - Result: passed.
   - Output: 241 tests ran; `OK`. Two established best-effort cleanup warnings were emitted.
4. `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -q`
   - Result: passed.
   - Output: 668 tests ran in 66.484s; `OK (skipped=12)`. Output included expected argparse/failure-path diagnostics, two established cleanup warnings, and one upstream lxml deprecation warning.
5. Clean-process managed request/import assertion using `ManagedPublicPlanningRequest(...).to_planning_request()` for `https://example.com/docs?language=en#install`.
   - Result: passed.
   - Output: the source canonicalized to `https://example.com/docs?language=en`; no DuckDB, BigQuery, Snowflake, or MarkItDown adapter module was imported.
6. `PYTHONPATH=src .venv/bin/python -m compileall -q src tests/test_planning_service.py && git diff --check`
   - Result: passed with no output.
7. `git diff --cached --name-only`
   - Result: passed with no output; no files are staged.
8. `PYTHONPATH=src .venv/bin/python -m unittest -q tests.test_planning_service`
   - Review-repair result: passed.
   - Output: 8 tests ran; `OK`.
9. `PYTHONPATH=src .venv/bin/python -m unittest -q tests.test_planning_service tests.test_cli tests.test_apply_cli tests.test_crawler tests.test_github_repo tests.test_database_relation tests.test_database_relation_cli tests.test_duckdb_relation tests.test_duckdb_relation_cli tests.test_bigquery_relation tests.test_snowflake_relation`
   - First review-repair run exposed three CLI error-compatibility regressions in explicit empty column mappings and the `--source-id` flag name. The service was corrected to preserve `None`-only defaults and exact legacy flag labels.
   - Final review-repair result: passed.
   - Output: 243 tests ran; `OK`. Two established best-effort cleanup warnings were emitted.
10. `git diff --check && git diff --stat && git diff --name-only && git diff --cached --name-only && git status --short --branch`
   - Review-repair result: passed; no whitespace errors or staged files.
11. `PYTHONPATH=src .venv/bin/python -m compileall -q src tests/test_planning_service.py tests/test_cli.py`
   - Review-repair result: passed with no output.

## What this supports or challenges

This supports the implementation and compatibility criteria in `.10x/tickets/done/2026-07-23-phase-2a-shared-planning-service.md` and the service, request, progress, artifact, CLI, and exclusion contracts in `.10x/specs/phase-2a-public-source-planning-service.md`.

## Limits

- All source acquisition used fakes or existing offline test fixtures. No live website crawl, GitHub clone/API operation, database connection, turbopuffer call, credential read, model load, apply mutation, browser, server, socket, commit, push, merge, publish, or PR operation was performed.
- Independent adversarial review is still required before the implementation ticket can move to `done`.
