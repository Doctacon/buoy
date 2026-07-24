Status: recorded
Created: 2026-07-23
Updated: 2026-07-24
Relates-To: .10x/tickets/done/2026-07-23-phase-2a-plan-job-frontend.md, .10x/specs/phase-2a-plan-job-interface.md

# Phase 2A Plan-Job Frontend Validation

## What was observed

The existing React/Vite Command Center now exposes `Start plan` and `Plan jobs` navigation plus `/plans/new`, `/plan-jobs`, and `/plan-jobs/:jobId`. The start form accepts one public HTTP(S) website or public GitHub repository root and bounded optional page/file, chunk, namespace, and include/exclude path inputs. It states the no-embed/no-turbopuffer/no-namespace-mutation boundary. Each valid submission fetches a process-local CSRF token into function scope and sends same-origin JSON with `X-Buoy-CSRF-Token`; no browser storage is used. Structured 409 responses link to the active job.

The history route requests only the 50 most recent durable records. Job detail consumes persisted-plus-live named SSE events through one native `EventSource`, preserving browser-managed `Last-Event-ID` reconnect behavior. A repeated stream failure closes the source and polls detail every two seconds; terminal states close streaming/polling. All callbacks are ignored after cleanup/job switch, polling intervals are cleared, duplicate sequences remain de-duplicated, and transient polling errors clear on recovery while malformed-stream notices remain distinct. The client timeline retains at most 200 ordered sequence entries. Success links to read-only plan review; failed and interrupted states link to `Start a new plan` without replay controls. Managed plan creation now writes the validated job ID only into `summary.json` audit metadata; local `PlanDetail` and the API expose it independently of bounded job history, while absent/unsafe metadata yields no link.

React text rendering keeps source, progress, and error strings escaped. Existing skip navigation, native labels/controls, focus behavior, read-only Phase 1 notices, responsive table/form/timeline layout, and Phase 1 routes remain present. The shared `Retry` control remains available only to repeat idempotent read loads; managed-route error and terminal tests find no plan-job retry/replay/resume or other prohibited apply/approve/cancel/delete/catalog/source/namespace controls. Client validation measures the exact UTF-8 `JSON.stringify` body and rejects requests above the API's 16 KiB bound before fetching CSRF. No browser-storage writes occur.

## Procedure and results

1. `cd web && npm test -- --run`
   - Result: passed.
   - Output: 36 Vitest/RTL tests passed in the final run.
   - Added coverage includes UTF-8 body size before CSRF, managed-route read errors without job replay, out-of-order page clicks, plan-route preview cleanup, duplicate SSE sequence, old-source callbacks, polling interval cleanup, polling-error recovery, durable origin without a history lookup, and unavailable origin. All prior Phase 1 and Phase 2A frontend cases remain in the passing suite.
2. `cd web && npm run build`
   - Result: passed.
   - Output: TypeScript build and Vite production build completed; 42 modules transformed. Generated `index.html`, `assets/index--BMBnGvJ.js` (277.52 kB; 85.00 kB gzip), and `assets/index-Amu9gKyT.css` (10.66 kB; 3.24 kB gzip).
3. `PYTHONPATH=src .venv/bin/python -m unittest -q tests.test_planning_service tests.test_command_center_local tests.test_command_center_api tests.test_command_center_jobs`
   - Result: passed.
   - Output: 83 tests in 5.125s; `OK`. The established FastAPI TestClient deprecation warning was emitted.
4. `PYTHONPATH=src .venv/bin/python -m compileall -q src/buoy_search/planning_service.py src/buoy_search/command_center_local.py src/buoy_search/command_center_jobs.py`
   - Result: passed with no output.
5. Static reference check using `.venv/bin/python` against `src/buoy_search/command_center_static/index.html`.
   - Result: passed.
   - Output: `/buoy.svg`, `/assets/index--BMBnGvJ.js`, and `/assets/index-Amu9gKyT.css` all resolve to rebuilt package files; missing references: none.
6. `git diff --check && test -z "$(git diff --cached --name-only)"`
   - Result: passed.
   - Output: diff check passed; no staged files.
7. `cd web && npm audit --omit=dev --audit-level=high`
   - Result: failed.
   - Output: the existing React Router 7.18.1 graph is reported under GHSA-qwww-vcr4-c8h2 (RSC-mode action execution); npm proposes a forced incompatible downgrade. This feature adds no RSC/action routing and made no dependency change. Applicability and patch selection are owned by `.10x/tickets/2026-07-24-review-react-router-advisory.md`.

## Acceptance mapping

- Start and security contract: valid website/GitHub requests prove exact JSON projection, per-submission token fetch, non-simple CSRF header, and same-origin API paths; invalid scheme/count requests prove no token/network activity; conflict proves active-job routing.
- History/detail/progress: a 72-record response renders only the bounded 50-item API window supplied, job metadata and links; ordered SSE events render persisted/live messages and counts; the same EventSource remains open for the first reconnect so native Last-Event-ID behavior is retained; repeated errors switch to polling; terminal events close the source.
- Terminal/origin behavior: success exposes plan review, failed and interrupted expose only new-plan entry, and validated artifact metadata establishes the origin link without any bounded history lookup.
- Safety and compatibility: hostile markup remains literal text, no executable nodes appear, no browser storage writes occur, prohibited controls are absent across all routes, and all prior frontend plus focused planning/local/API/job tests pass.

## Limits

- All frontend behavior used Vitest/jsdom, Testing Library, fake fetch, and a fake EventSource; no browser, server socket, live source, GitHub, turbopuffer, provider, database, model, commit, push, merge, publish, or PR operation occurred.
- Native EventSource owns the actual `Last-Event-ID` header, which browser JavaScript cannot set or inspect. The test proves the client retains the same source for initial automatic reconnect and does not replace it with a cursor-less source; server-side Last-Event-ID replay remains covered by `.10x/evidence/2026-07-23-phase-2a-plan-job-api-sse.md`.
- Origin metadata is available only for newly created managed plans whose validated job ID was written to `summary.json`; older/unmanaged artifacts correctly expose no origin.
- Independent adversarial review is required before this ticket can close.
