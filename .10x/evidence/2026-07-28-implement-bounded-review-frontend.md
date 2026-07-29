Status: recorded
Created: 2026-07-28
Updated: 2026-07-28
Relates-To: .10x/tickets/done/2026-07-28-implement-bounded-review-frontend.md, .10x/specs/command-center-bounded-inventory-transport.md, .10x/specs/command-center-coalesced-plan-review.md

# Bounded Review Frontend Implementation Evidence

## What was observed

The retained partial frontend implementation was completed without discarding sound work after the prior worker ended with a transport-level `fetch failed`. Initial validation of that partial state found 35 passing and 2 failing RTL tests plus one unhandled namespace-detail render error; TypeScript build also rejected a widened test fixture type. The failures exposed stale test routing/filter-fixture assumptions rather than a need to revert the bounded implementation. They were repaired, and request/race coverage was expanded before final validation.

Plans and local Namespaces now request one URL-backed 50-row page. Exact request assertions cover initial URL restoration, page transitions, filter offset reset, filters sent to the server, one request per action, and stale-response suppression for both inventories. A 1,000-record fixture renders only the current 50 records and observes no all-page helper or 1,000-row DOM.

The Namespaces screen keeps the local server page separate from an explicitly refreshed remote snapshot. Only `local_present=true` namespace matches enrich current local rows; only `local_present=false` rows enter the separately labeled remote-only section. That section has scoped labels, independent client-side 50-row pagination and filter reset, and its interactions issue no local inventory requests. Namespace detail requests exactly `plan_offset=0&plan_limit=20` and exposes the URL-backed `/plans?namespace=...` link when history is truncated.

Plan detail initially issues one combined review request. Changed-chunk and stale-row pagination each issue only their focused endpoint, retain detail and the unaffected section during loading/error, and retry only the failed window. Per-plan generation plus per-section sequence checks reject slower combined/focused responses. Tests cover reverse-order chunk and stale races, plan-ID changes during a focused request, zero-window reset from the next combined response, exact retry shapes, escaped content, and absence of mutation controls.

The Vite build replaced the prior packaged JavaScript and CSS assets. The packaged index references exactly the two files present in the asset directory; the old `index-D34KCjuB.js` and `index-Amu9gKyT.css` files are absent.

A bounded frontend rereview repair changed incremental Plans/Namespaces text-filter URL writes to history replacement while retaining pushed history entries for select and page actions. A new MemoryRouter/RTL scenario walks Back and Forward through both screens and proves intermediate keystrokes are coalesced while final text, select, and offset state restore correctly. Local and remote-only inventory pagination now expose separately named `navigation` landmarks; their duplicate Previous/Next controls are tested within those contexts. The no-mutation-control matcher now rejects prohibited action terms within longer accessible names, including labels shaped like `Apply plan` and `Delete namespace`.

## Procedure and results

```bash
cd web && npm test -- --run && npm run build
```

Final frontend validation passed 45 RTL/Vitest tests, including the explicit Plans/Namespaces Back/Forward history scenario. TypeScript compilation passed, Vite transformed 42 modules, and the production build wrote:

- `src/buoy_search/command_center_static/assets/index-DAM_87xf.js` (285.74 kB; 86.69 kB gzip)
- `src/buoy_search/command_center_static/assets/index-0ugYq-Qa.css` (11.19 kB; 3.34 kB gzip)

The frontend test set includes exact request arrays for bounded inventories, combined review, focused page transitions, section retries, reverse-order races, plan reset, practical history restoration, named pagination landmarks, and stronger mutation-label rejection. It also includes 1,000-record local inventories and a 120-record remote-only snapshot to prove rendered bounds and independent pagination.

A temporary ignored version shim was used only because this worktree lacks the hatch-generated ignored `_version.py`; the trap removed it after validation.

```bash
printf '__version__ = "0.0.0+frontend-validation"\n' > src/buoy_search/_version.py
PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest \
  tests.test_command_center_api.CommandCenterApiTests.test_bounded_filters_namespace_history_and_review_api_contracts \
  tests.test_command_center_api.CommandCenterApiTests.test_static_assets_spa_fallback_and_security_headers \
  tests.test_command_center_api.CommandCenterApiTests.test_missing_static_assets_return_structured_response \
  tests.test_release_automation.ReleaseAutomationTests.test_command_center_metadata_describes_local_planning_and_assets_resolve \
  -v
rm -f src/buoy_search/_version.py
```

All 4 original focused API/release/static tests passed in 1.145 seconds. After the rereview repair and asset rebuild, `tests.test_command_center_api.CommandCenterApiTests.test_static_assets_spa_fallback_and_security_headers` was rerun alone and passed in 0.030 seconds. The only diagnostic was the existing Starlette TestClient/httpx deprecation warning.

```bash
uv run python <static-reference-and-orphan-asset check>
test ! -e web/dist
test ! -e src/buoy_search/_version.py
test -z "$(find src tests scripts -type d -name __pycache__ -print -quit)"
test -z "$(find src tests scripts -type f \( -name '*.pyc' -o -name '*.pyo' \) -print -quit)"
test -z "$(git diff --cached --name-only)"
git diff --check
```

The static check observed exactly `index-DAM_87xf.js` and `index-0ugYq-Qa.css`, both referenced by packaged `index.html`, with no extra or legacy assets. No `web/dist`, temporary version shim, source/test/script bytecode, staged file, or diff-whitespace error remains.

`web/node_modules` is intentionally retained for the immediate required independent review. It is ignored and is not a packaged or staged artifact.

## Changed frontend files

- `web/src/App.tsx`
- `web/src/api.ts`
- `web/src/types.ts`
- `web/src/styles.css`
- `web/src/App.test.tsx`
- `src/buoy_search/command_center_static/index.html`
- `src/buoy_search/command_center_static/assets/index-DAM_87xf.js`
- `src/buoy_search/command_center_static/assets/index-0ugYq-Qa.css`
- removed legacy `src/buoy_search/command_center_static/assets/index-D34KCjuB.js`
- removed legacy `src/buoy_search/command_center_static/assets/index-Amu9gKyT.css`

## Limits

This is implementation evidence, not the required independent frontend review, final performance benchmark, documentation pass, full Python package/suite validation, or commit. TestClient/RTL are not a live graphical-browser acceptance run. The ticket remains active pending independent review.
