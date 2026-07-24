Status: recorded
Created: 2026-07-23
Updated: 2026-07-23
Relates-To: .10x/tickets/done/2026-07-23-command-center-acceptance-gap.md, .10x/tickets/done/2026-07-23-command-center-phase-1-plan.md

# Command Center Original-Brief Acceptance Gap Validation

## What was observed

The bounded acceptance-gap implementation reuses saved plan summaries/manifests, local applied-state ledgers, safe source provenance, and the frontend's current in-memory explicit remote snapshot. It adds no source/provider reconnection, remote snapshot persistence, model load, mutation route, or arbitrary path input.

`/api/v1/capabilities` now returns boolean-only readiness for the configured artifact/state directories, turbopuffer credential environment presence, packaged UI index, and installed BigQuery/Snowflake distributions while retaining version/read-only fields. Capability evaluation constructed no client and imported no optional source adapter or remote service.

Dashboard output now includes pending-change namespace and artifact-error counts. Namespace output now includes stable local status, retained stale rows, latest planned upsert/stale counts, document/page and chunk counts, latest plan/apply identity, safe provenance, and persisted retrieval region when available. Unknown diff values remain unknown and do not count as pending. Plan summaries now carry recorded source credential/API activity for plan-history presentation.

The React UI renders these fields, filters the returned local/remote/catalog statuses, uses the current in-memory explicit remote snapshot on namespace detail (otherwise `Not checked`), and renders the exact namespace graph empty message. Existing escaped text, semantic tables/controls, explicit guarded POST behavior, pagination, citations, and read-only controls remain in place. Vite rebuilt the package-owned hashed assets.

## Procedure and results

1. `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests/test_command_center_local.py -q`
   - Passed after implementation: 17 tests in 1.396s; `OK`.
   - Covers pending derivation (including unknown values), artifact-error count, conflict status, retained stale/state counts, latest plan fields, persisted region, and recorded source activity.
2. `PYTHONDONTWRITEBYTECODE=1 uv run --extra ui --with 'httpx>=0.27,<1' python -m unittest tests/test_command_center_api.py tests/test_command_center_cli.py -q`
   - Passed: 16 tests in 0.678s; `OK`.
   - Includes sanitized readiness booleans/secret omission, capability/startup import inertia, API security boundaries, guarded POSTs, routes, and CLI behavior. The known Starlette TestClient/httpx deprecation warning and expected host-rejection argparse diagnostics were emitted.
3. `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests/test_command_center_remote.py tests/test_plan_artifacts.py tests/test_applied_state.py tests/test_plan_diff.py -q`
   - Passed: 62 tests in 1.523s; `OK`.
   - Confirms remote snapshot/search, persisted plan/state, and diff compatibility.
4. `cd web && npm test -- --run && npm run build`
   - Final result passed: 20 Vitest tests; TypeScript and Vite 7.3.6 transformed 42 modules and emitted `index.html`, `assets/index-BcWfZ-Sy.css`, and `assets/index-CIC4OLmw.js` into `src/buoy_search/command_center_static`.
   - Covers readiness/dashboard fields, actual status filters, namespace columns/detail, in-memory remote/catalog status, plan-history activity, exact graph empty message, accessibility boundaries, pagination, escaped content, and no mutation controls.
5. `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests/test_release_automation.py -q`
   - Passed: 30 tests in 2.213s; `OK`.
6. `uv sync --locked && PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover -s tests -p 'test_*.py' -q`
   - Passed: 661 tests in 61.712s; `OK (skipped=11)`.
   - Output included two established cleanup warnings, expected safe failure/host-rejection diagnostics, and one upstream lxml deprecation warning.
7. Final UI-extra focused suite: `PYTHONDONTWRITEBYTECODE=1 uv run --extra ui --with 'httpx>=0.27,<1' python -m unittest tests/test_command_center_local.py tests/test_command_center_remote.py tests/test_command_center_api.py tests/test_command_center_cli.py -q`
   - Passed: 50 tests in 1.888s; `OK`.
8. Default package-static/capability integration script using the real `create_app` default static root and FastAPI TestClient.
   - Passed with `packaged-static-and-capabilities-inert`; `/` and `/api/v1/capabilities` returned 200, `ui_build_available` was true, and remote/source adapter/provider modules remained absent from `sys.modules`.
9. `uv sync --locked` followed by a core import-isolation script.
   - Passed with `core-import-isolated`; FastAPI/Uvicorn were absent and ordinary package/CLI imports loaded no remote service, source adapter, or provider SDK.
10. `uv run python -m py_compile src/buoy_search/command_center_local.py src/buoy_search/command_center_api.py tests/test_command_center_local.py tests/test_command_center_api.py`
    - Passed.
11. `grep` over `web/src` for `dangerouslySetInnerHTML`, `innerHTML`, `localStorage`, and `sessionStorage`.
    - Passed with no matches.
12. `git diff --check && test -z "$(git diff --cached --name-only)"`
    - Passed before record updates; final hygiene was repeated after record updates.

## Corrected validation attempts

- An initial frontend run had 19 passing tests and one assertion-only failure because a new label intentionally appeared in multiple sections. The assertion was narrowed.
- The next production build exposed one TypeScript narrowing error for a possibly absent local status. Rendering now uses `Unknown` rather than inventing a status when a malformed/older response omits it; the final build passed.
- A later source-label coverage assertion initially used an exact text matcher even though the accessible table cell includes the kind and label together. The matcher was corrected to the rendered safe label; the final 20-test run and production build passed.

Neither corrected attempt changed dependencies, contacted a provider/source, or produced an accepted stale build.

## What this supports or challenges

This supports the implementation acceptance criteria in `.10x/tickets/done/2026-07-23-command-center-acceptance-gap.md` while preserving the active command-center specifications' loopback Host boundary, guarded explicit POST boundary, safe path/citation behavior, lazy startup, read-only endpoint/control surface, pagination, escaped rendering, and accessibility structure.

Independent review initially found one nullable catalog-state mismatch: a non-null remote row with `card_present=null` rendered and filtered as unknown instead of `Not checked`. The UI now classifies any nullable card presence as not checked, with a dedicated frontend regression. A non-empty service-through-FastAPI contract test also verifies the added dashboard, namespace, plan-activity, and retrieval-region fields. Final focused results were 21 frontend tests, 12 API tests, and 17 local-service tests, all passing; packaged static assets were rebuilt and synchronized. Independent re-review passed and is incorporated into `.10x/reviews/2026-07-23-command-center-phase-1.md`.

## Limits

- No live turbopuffer, source, warehouse, model, browser, screen reader, socket, commit, push, PR, merge, publish, or release operation ran.
- Remote/detail behavior used the already-reviewed explicit snapshot flow and frontend memory; no snapshot was persisted.
- Readiness proves environment/distribution/filesystem presence only, not successful external connectivity or source-extra operation.
- Automated accessibility coverage is not a manual screen-reader or graphical-browser audit.
