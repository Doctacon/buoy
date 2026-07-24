Status: recorded
Created: 2026-07-23
Updated: 2026-07-23
Relates-To: .10x/tickets/done/2026-07-23-command-center-frontend.md, .10x/specs/command-center-operator-interface.md

# Command Center Frontend Validation

## What was observed

The new `web/` React 19 + TypeScript + Vite application consumes only same-origin `/api/v1` resources through browser `fetch`. React Router exposes dashboard, namespace list/detail, plan list/detail, search, and graph-placeholder routes under one persistent Buoy-branded read-only shell. The Vite production output is written directly to the server's existing default `src/buoy_search/command_center_static` location and contains hashed JavaScript and CSS assets plus the existing Buoy SVG.

The interface initializes remote state as `Not checked` and makes no remote request until the operator activates `Refresh remote status`. Refresh and search notices separately disclose whether credentials were required, API calls occurred, and writes occurred; pre-execution notices identify potential remote/model activity. Namespace filtering covers ID, source kind, local status, refreshed remote classification, and catalog-card status. Review surfaces expose local provenance, retrieval contracts, recorded source activity, diffs, pages, bounded paginated chunks, warnings, citations, and remote-warehouse review independence without mutation controls.

All Markdown, chunk content, search content, tags, and titles are rendered through React text nodes, including `<pre>` for plain text. No `dangerouslySetInnerHTML`, `innerHTML`, local storage, or session storage use exists under `web/src`. External HTTP(S) links use a new-tab accessibility announcement and `rel="noreferrer"`; non-HTTP provenance/citations remain text. Controls use native buttons, links, labels, fieldsets, inputs, selects, textareas, tables, headings, alert/status regions, disabled states, and visible keyboard focus. Project-owned CSS supplies responsive layouts at 900px and 620px, contrast-oriented status treatments, horizontal table overflow, and reduced-motion handling.

## Procedure and results

1. `cd web && npm ci`
   - Result: passed.
   - Output: 214 packages installed from `package-lock.json`; 215 packages audited; 0 vulnerabilities.
2. `cd web && npm test -- --run`
   - Result: passed.
   - Output: 1 test file and 13 tests passed in 1.21s.
   - Coverage includes dashboard loading/empty/error/retry, explicit-only remote refresh and exact activity, namespace filtering and refreshed remote/catalog state, namespace detail, plan history/empty state, plan detail and remote-warehouse notice, escaped Markdown/chunks, bounded chunk pagination, search validation/results/escaping/missing credentials/activity, graph placeholder, and absence of mutation controls.
3. `cd web && npm run build`
   - Result: passed.
   - Output: TypeScript build and Vite 7.3.6 production build completed; 42 modules transformed. Generated `index.html` (0.61 kB), `assets/index-BTsfTtCu.css` (9.63 kB), and `assets/index-BT1xFvs2.js` (257.41 kB), with hashed JS/CSS names.
4. `uv run --with 'fastapi>=0.115,<1' --with 'httpx>=0.27,<1' python - <default-static-root integration script>`
   - Result: passed.
   - Output: the actual default application static root served `/`, the `/plans/example` SPA fallback, and `assets/index-BT1xFvs2.js` with HTTP 200; the index root and security headers were asserted.
   - A known Starlette TestClient deprecation warning about its current httpx integration was emitted; it did not affect the result or project dependencies.
5. `cd web && npm audit --audit-level=high`
   - Result: passed.
   - Output: 0 vulnerabilities.
6. `grep` checks over `web/src` for `dangerouslySetInnerHTML`, `innerHTML`, `localStorage`, and `sessionStorage`.
   - Result: passed.
   - Output: no matches.
7. `git diff --check && test -z "$(git diff --cached --name-only)"`
   - Result: passed.
   - Output: tracked-diff hygiene passed and no files were staged. New frontend/evidence files were also inspected for trailing whitespace.

## Acceptance mapping

- Dashboard, namespace list/detail, plan list/detail, search, and graph placeholder: exercised by route-specific tests and the successful TypeScript production build.
- Accurate remote/search disclosure: tests prove no automatic refresh, explicit POST activation, exact returned activity fields, pre-search impact notice, successful search activity, and missing-credential no-call state.
- Escaped content: malicious-looking Markdown, chunk, and search strings remain literal text and create no script or image elements; source contains no HTML injection API.
- Loading/empty/actionable-error/success states: dashboard, inventory, detail, preview, search, and graph scenarios exercise semantic status/alert/empty output and retry guidance.
- Accessible, responsive, read-only behavior: native semantic controls/tables, labels, fieldsets, focus styles, status regions, two responsive breakpoints, reduced-motion CSS, and the no-mutation-control assertion were inspected and tested.
- Packaged static target: the production build exists at the exact default root imported by `command_center_api.py`, and an in-process application served both assets and client-route fallback.

## Limits

- Automated accessibility coverage verifies semantic structure and keyboard-capable native controls but is not a substitute for a manual screen-reader, browser keyboard, or color-contrast audit.
- Browser behavior was exercised in jsdom and the built bundle was exercised through the in-process FastAPI static route. No live provider, credential, model, source adapter, source database, or graphical browser was used.
- Python optional dependency declarations, wheel/sdist inclusion, documentation, and CI remain excluded and owned by `.10x/tickets/done/2026-07-23-command-center-packaging-docs-ci-validation.md`.
