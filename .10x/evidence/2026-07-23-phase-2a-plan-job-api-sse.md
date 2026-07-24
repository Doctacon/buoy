Status: recorded
Created: 2026-07-23
Updated: 2026-07-23
Relates-To: .10x/tickets/done/2026-07-23-phase-2a-plan-job-api-sse.md, .10x/specs/phase-2a-plan-job-api-security.md, .10x/specs/phase-2a-plan-job-lifecycle.md

# Phase 2A Plan-Job API and SSE Validation

## What was observed

The FastAPI lifespan now lazily imports and constructs one `PlanJobService`, allowing its existing owner-only startup recovery to interrupt persisted queued/running jobs, and shuts the owned worker down on server lifecycle exit. App construction remains worker/provider/model inert. A clean-process lifespan test observed no remote service, database source adapter, turbopuffer, sentence-transformers, transformers, BigQuery, or Snowflake import. A real durable queued record became `interrupted` at startup while an injected planning service received zero calls.

The local API issues one unpersisted, no-store CSRF token per app/server process. Plan-job creation requires exactly one loopback Host, same-origin Origin, process token, JSON content type, and acceptable fetch-site signal. It rejects duplicate/conflicting security headers, checks declared and streamed body size before JSON parsing, rejects duplicate/unknown JSON fields, and bounds counts, namespace, and include/exclude lists. Managed-service validation retains the HTTP(S), no-userinfo, supported public website/GitHub-root boundary before worker submission.

The API exposes only bounded plan creation in addition to the two existing guarded Phase 1 read-only POSTs. List/detail responses are structured and paginated; list offset is capped at 1,000 and order follows record `mtime_ns` descending with descending job-ID ties while retaining `created_at` as audit output only. Active conflict is HTTP 409 with the active job ID; unknown jobs are structured 404s. SSE validates query/header sequence state, emits persisted events with stable numeric IDs, observes live completion without starting work, suppresses duplicates after reconnect, closes at terminal state, and caps each connection at 1,000 events. Failure logs contain only safe job ID and exception class, never raw exception text.

## Procedure and results

1. `PYTHONPATH=src .venv/bin/python -W error::ResourceWarning -m unittest -q tests.test_command_center_api`
   - Result: passed.
   - Output: final rerun 18 tests in 0.478s; `OK`.
   - Coverage includes CSRF issuance/lifecycle, valid website creation, missing/invalid token, missing/conflicting/cross-origin Origin, hostile Host, cross-site fetch, wrong content type, pre-parse oversized rejection, unsupported/credential-bearing/GitHub subtree URLs, request bounds, conflict ID, list/detail/404/pagination, persisted and live SSE, Last-Event-ID/query reconnect, terminal closure, startup interruption/no work, route exclusions, retained Phase 1 guards, and clean-process import isolation.
2. `PYTHONPATH=src .venv/bin/python -m unittest -q tests.test_command_center_api tests.test_command_center_jobs tests.test_planning_service tests.test_cli tests.test_apply_cli tests.test_crawler tests.test_github_repo tests.test_database_relation tests.test_database_relation_cli tests.test_duckdb_relation tests.test_duckdb_relation_cli tests.test_bigquery_relation tests.test_snowflake_relation`
   - Result: passed.
   - Output: final rerun 290 tests in 15.237s; `OK`.
   - This combines Phase 1 API/security behavior with durable jobs, shared planning, CLI, apply, crawler, GitHub, and database-source compatibility. Two established best-effort cleanup warnings were emitted.
3. `PYTHONPATH=src .venv/bin/python -m compileall -q src/buoy_search/command_center_api.py src/buoy_search/command_center_jobs.py tests/test_command_center_api.py tests/test_command_center_jobs.py && git diff --check && test -z "$(git diff --cached --name-only)"`
   - Result: passed with no output; no staged files.

## Acceptance mapping

- Same-origin/security/body/source validation: middleware and fake-backed rejection matrix, including duplicate/conflicting headers and oversized streamed input before JSON parsing.
- Creation/conflict/list/detail/errors: valid typed request projection, explicit 202, 409 active ID, bounded pagination, detail, structured 404/422/503/500 handling, and exact method-surface assertion.
- Replay/reconnect/live closure: SSE assertions cover ordered IDs 1/2, persisted replay, Last-Event-ID and `after_sequence`, conflict/invalid sequence rejection, no duplicate IDs, live terminal success, empty terminal reconnect, and one creation only.
- Startup and no hidden work: real durable-store recovery through FastAPI lifespan marks a queued job interrupted while injected planning receives no call; clean-process module inventory remains provider/model/database-adapter inert.
- Compatibility and safe logging: 290-test shared basket passes; the durable failure regression captures an exception containing a fake secret/private path and confirms logs and records contain neither.

## Adversarial-review repair validation

The terminal timeout race is closed by taking a terminal-state snapshot only after timed observation and then draining durable events before closure; a barrier-controlled iterator test commits the terminal record/event in the former timeout-to-state-check window and observes the terminal SSE frame. A direct ASGI disconnect test confirms stream iteration is cancelled before exhausting the producer, while direct iterator tests prove send-driven laziness and the exact 1,000-frame connection cap.

API import and lifespan startup are now source/planning inert. Applied-state URL normalization uses the new lightweight `buoy_search.source_url` module instead of importing `crawler`; `command_center_jobs` type-imports planning contracts only and imports/constructs managed planning on `start`/worker execution. The clean-process watched set now includes crawler, database-relation, planning-service, and GitHub acquisition modules.

A valid `Last-Event-ID` now overrides any query cursor. Malformed external job IDs return structured 404s before service access, while a valid ID that reaches corrupt durable storage retains structured 503 behavior. Event replay scans JSONL incrementally into at most a 1,000-event result window, validates complete sequence integrity, and repairs record-first commits without loading the full log. Detail/list reconciliation reads only a bounded tail/latest event; paginated listing reconciles only selected records rather than every event log.

Direct coverage now includes an oversized multi-chunk ASGI body with no `Content-Length`, bracketed IPv6 and explicit/default port origin comparisons, `Origin: null`, CSRF nonlogging, disconnect, slow iteration, terminal race, cursor precedence, malformed IDs, valid-ID corruption, the 1,000 SSE cap, an over-1,000 durable replay window, and bounded list reconciliation.

Validation:

- `PYTHONPATH=src .venv/bin/python -W error::ResourceWarning -m unittest -q tests.test_command_center_api tests.test_command_center_jobs`: 55 tests passed in the final focused run.
- `PYTHONPATH=src .venv/bin/python -m unittest -q tests.test_command_center_api tests.test_command_center_jobs tests.test_planning_service tests.test_cli tests.test_apply_cli tests.test_crawler tests.test_github_repo tests.test_database_relation tests.test_database_relation_cli tests.test_duckdb_relation tests.test_duckdb_relation_cli tests.test_bigquery_relation tests.test_snowflake_relation`: 299-test expanded compatibility basket passed in 17.131s.
- Compile, diff-check, and no-staged-files checks passed.

## Bounded-list repair validation

The store now enumerates job records with `os.scandir` and no-follow metadata, rejects non-regular, group/world-accessible, or multiply linked matching records, counts total matching records without JSON decode, and uses a min-heap capped at `offset + limit`. It decodes and reconciles only the selected window and compares each opened record device/inode to the selected metadata before decode. Both bounded and full store list surfaces use record `mtime_ns` descending with descending job-ID ties; neither uses `created_at` for order.

A 20-job test assigned deterministic nanosecond mtimes, including an exact tie and ordering deliberately opposed to creation order. A `limit=1` call returned total 20 while invoking one record decode, one event-tail reconciliation, and zero full event scans. Additional tests exercised the inclusive 1,000 store/API offset boundary and fail-closed symlink, hardlink, public-mode, and selection-to-decode replacement tampering.

Validation:

- `PYTHONPATH=src .venv/bin/python -W error::ResourceWarning -m unittest -q tests.test_command_center_api tests.test_command_center_jobs`: 56 tests passed in 3.638s; `OK`. The established optional TestClient deprecation warning was the only warning.
- `PYTHONPATH=src .venv/bin/python -m compileall -q src/buoy_search/command_center_api.py src/buoy_search/command_center_jobs.py tests/test_command_center_api.py tests/test_command_center_jobs.py && git diff --check && test -z "$(git diff --cached --name-only)"`: passed with no output; syntax compilation and diff hygiene succeeded and no files were staged.

## Limits

- All HTTP behavior used FastAPI TestClient, fakes, temporary durable state, and existing offline fixtures. No live source, GitHub, provider, database, model, turbopuffer, browser, server socket, commit, push, merge, publish, or PR operation occurred.
- SSE transport was exercised in-process through TestClient rather than a real network proxy. Each connection deliberately closes after 1,000 events so a client must reconnect with the last received ID for unusually long jobs.
- The known upstream FastAPI TestClient/httpx deprecation warning remains non-failing.
- Independent adversarial review is still required before the ticket can close.
