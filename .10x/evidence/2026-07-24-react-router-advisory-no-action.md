Status: recorded
Created: 2026-07-24
Updated: 2026-07-24
Relates-To: .10x/tickets/done/2026-07-24-review-react-router-advisory.md, .10x/specs/phase-2a-stabilization.md

# React Router GHSA-qwww-vcr4-c8h2 No-Action Disposition

## What was observed

`web/package.json` pins `react-router-dom@7.18.1`; `web/package-lock.json` resolves `react-router-dom@7.18.1 -> react-router@7.18.1`. `npm ls react-router react-router-dom --all` confirmed that exact runtime graph.

The official reviewed advisory and maintainer advisory state that GHSA-qwww-vcr4-c8h2 affects React Router's unstable React Server Components request-handling modes. The fixed upstream regression sends a cross-origin RSC document POST to a route with an `action` and proves that the action must not execute before the request returns 400.

Buoy's inspected frontend is a Vite SPA. `web/src/main.tsx` initializes declarative `<BrowserRouter>` beneath `createRoot`; `web/src/App.tsx` uses declarative `<Routes>/<Route>` elements and client event handlers that call Buoy's separate FastAPI client. `web/vite.config.ts` uses only `@vitejs/plugin-react`. The project has no React Router framework plugin, RSC plugin/server entry, server action, route-module action execution, `createBrowserRouter`/`RouterProvider`, or unstable RSC API import.

`npm audit --omit=dev --audit-level=high` exited 1 and reported two high findings through the same dependency edge. Its suggested force fix would install `react-router-dom@7.11.0`, a breaking downgrade, while the official advisory's first patched `react-router` version is 8.3.0. Neither forced dependency change is justified solely for an unreachable RSC code path.

## Procedure

1. Inspected `web/package.json`, `web/package-lock.json`, `web/src/main.tsx`, `web/src/App.tsx`, `web/vite.config.ts`, and `web/index.html`.
2. Consulted:
   - https://github.com/advisories/GHSA-qwww-vcr4-c8h2
   - https://github.com/remix-run/react-router/security/advisories/GHSA-qwww-vcr4-c8h2
   - https://github.com/remix-run/react-router/commit/7a71c728ad116bd78699a258b2014ce9585729f5
   - https://reactrouter.com/start/modes
   - https://reactrouter.com/main/how-to/react-server-components
   - https://github.com/remix-run/react-router/blob/main/CHANGELOG.md#v830
3. Ran `npm ls react-router react-router-dom --all` and `npm audit --omit=dev --audit-level=high` from `web/`.
4. Added and ran `tests/test_release_automation.py::ReleaseAutomationTests.test_command_center_router_remains_declarative_without_rsc_entrypoints` as a narrow architecture guard; post-review repair made its `web/src` inspection recursive so nested route modules cannot bypass it.
5. Ran all 40 Vitest tests and the production frontend build successfully.

## What this supports or challenges

This supports a source-backed no-action disposition: the installed package is numerically in the advisory range, but Buoy does not construct or serve the affected RSC/action-execution path. No dependency or lockfile change and no broad audit suppression is appropriate.

Reevaluate before adopting React Router framework mode, React Server Components, server actions, `@vitejs/plugin-rsc`, `@react-router/dev`, unstable RSC APIs/server entries, or if the official advisory broadens its scope. A routine supported router migration may independently select a non-vulnerable release.

## Limits

The audit remains nonzero because scanners classify installed version ranges without application-mode reachability. GitHub's global reviewed advisory reports High/CVSS 7.1 while the repository endpoint reports Medium; this severity-label discrepancy does not change reachability. This evidence covers the checked-in frontend architecture and dependency graph, not deployment code outside the repository or future router changes.
