Status: recorded
Created: 2026-07-24
Updated: 2026-07-24
Relates-To: .10x/tickets/done/2026-07-23-phase-2a-validation-docs-review.md, .10x/tickets/done/2026-07-23-phase-2a-public-plan-workflow.md, .10x/specs/phase-2a-public-source-planning-service.md, .10x/specs/phase-2a-plan-job-lifecycle.md, .10x/specs/phase-2a-plan-job-api-security.md, .10x/specs/phase-2a-plan-job-interface.md

# Phase 2A Final Documentation, CI, Package, and Validation Evidence

## What was observed

README, the Command Center guide, and `buoy serve --help` now distinguish read-only review from the implemented bounded public-source planning workflow. They document public HTTP(S) websites and public GitHub repository roots only; one active queued/running managed job; durable local records/events; restart conversion to `interrupted` without resume; no cancel/pause/resume/automatic or endpoint retry; no source definitions, credentials, private repositories, local-file/document, or database UI; loopback/Host/same-origin/CSRF protection; ordinary verified plan artifacts; and the exact explicit `buoy apply --plan` CLI handoff. The roadmap identifies Phase 2A as implemented and broader Phase 2 as unratified.

Contributor and CI Command Center baskets now include shared planning and durable-job tests. Release-automation tests enforce that CI/contributor coverage and the Phase 2A documentation boundary. CLI-help coverage enforces one-active public website/GitHub planning, explicit CLI apply, and the managed artifact/job roots.

All required offline core, UI-extra, frontend, static synchronization, package, installed-wheel, and restoration validation passed. The final wheel contains the new planning/job/source modules and synchronized production assets. The sdist contains the documentation, Python sources, static output, and all intended frontend inputs without `node_modules`. The installed wheel served its package-owned API health endpoint, root, SPA fallback, and hashed JavaScript through the real FastAPI application.

## Procedure and exact results

1. `git diff --check`
   - Passed before validation and again after final restoration; no whitespace errors.
2. `uv sync --locked` and `uv lock --check`
   - Passed for the initial core environment. The sync removed FastAPI 0.139.2, Starlette 1.3.1, and Uvicorn 0.51.0.
3. `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/validate_ranking_contract.py`
   - Passed: 13 datasets/folds, 90 composite identities, 369 judgments, dataset bundle SHA-256 `5a79f58aaca87a2d4f7cbec68fdcfbbcbf041131821587f8aba74a86daca99d9`; Buoy remains pending baseline approval at the established checkpoint.
4. `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/c6_syntax_forecast.py validate`
   - Passed: forecast SHA-256 `d5199276c19ae89779287eaa90824ce1e1cc684a3f060899f02f65d976016243`; tokenizer readiness remained false at the expected checkpoint.
5. `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover -s tests -p 'test_*.py' -q`
   - Passed: 717 tests in 70.065s; `OK (skipped=25)`.
   - Output contained two established best-effort cleanup warnings, expected hostile-host/parser and fake-provider failure-path diagnostics, and one upstream lxml deprecation warning.
6. `uv sync --locked --extra ui`
   - Passed: installed FastAPI 0.139.2, Starlette 1.3.1, and Uvicorn 0.51.0.
7. `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests/test_planning_service.py tests/test_command_center_jobs.py tests/test_command_center_local.py tests/test_command_center_remote.py tests/test_command_center_api.py tests/test_command_center_cli.py -q`
   - Passed: 105 tests in 5.292s; `OK`.
   - The known FastAPI TestClient/httpx deprecation warning plus expected safe fake-provider and hostile-host diagnostics were emitted.
8. `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests/test_cli.py tests/test_apply_cli.py tests/test_crawler.py tests/test_github_repo.py tests/test_database_relation.py tests/test_database_relation_cli.py tests/test_duckdb_relation.py tests/test_duckdb_relation_cli.py tests/test_bigquery_relation.py tests/test_snowflake_relation.py -q`
   - Passed: 235 CLI plan/apply/crawler/GitHub/database compatibility tests in 13.200s; `OK`. Two established best-effort cleanup warnings were emitted.
9. `uv run buoy serve --help`
   - Passed. Help states loopback-only operation, one managed public website/GitHub job, local plan artifacts, explicit CLI apply, and `command-center/plans`/`command-center/jobs` roots.
10. `cd web && npm ci`
    - Passed under the locally available Node/npm environment: 214 packages installed and 215 audited. npm reported the existing deprecated `whatwg-encoding` notice and two high-severity audit findings detailed below.
11. `cd web && npm test -- --run`
    - Passed: one Vitest file and all 36 tests passed in 2.25s.
12. SHA-256 inventory before and after `cd web && npm run build`
    - Build passed: TypeScript plus Vite 7.3.6 transformed 42 modules and emitted `index.html` (0.61 kB), `assets/index--BMBnGvJ.js` (277.52 kB; 85.00 kB gzip), and `assets/index-Amu9gKyT.css` (10.66 kB; 3.24 kB gzip).
    - Pre/post inventories were byte-identical. Final hashes:
      - JavaScript: `5d62a1bdb5bc192389cba50f60b551b801271e0990c5487038f9c704c55594aa`
      - CSS: `fd57c4f2b1319313451571398931ad5b20c8707cdc3f931cd88d993d3c1bd815`
      - SVG: `f791c77f25e202a0556d2688ec9180e7d78c983f220f84b097c1fdc8894edcef`
      - index: `34c9255956fc902181c5a7ea67b80ae8c0aa33d88a49c3fd6fd4e87d0c7cf5da`
13. Static-reference script against `src/buoy_search/command_center_static/index.html`
    - Passed. `/buoy.svg`, `/assets/index--BMBnGvJ.js`, and `/assets/index-Amu9gKyT.css` all resolve; missing references: none.
14. `uv build --out-dir /tmp/buoy-phase2a-dist`
    - Passed. Built `buoy_search-0.4.1.dev79+gd716eba19.d20260724-py3-none-any.whl` and `buoy_search-0.4.1.dev79+gd716eba19.d20260724.tar.gz`.
15. Standard-library wheel/sdist inventory assertions
    - Passed. Wheel: 68 entries, including `command_center_jobs.py`, `planning_service.py`, `source_url.py`, index, SVG, and exactly one hashed JavaScript/CSS asset. Sdist: 155 entries, all 20 asserted documentation/Python/static/frontend inputs, and zero `web/node_modules` entries.
16. `uv pip install --no-deps --target /tmp/buoy-phase2a-wheel-target <wheel>`
    - Passed. Installed the built wheel into an isolated temporary target.
17. Corrected isolated installed-wheel TestClient lookup with `base_url='http://127.0.0.1'`
    - Passed. Both package and static roots resolved under `/private/tmp/buoy-phase2a-wheel-target`, and `/api/v1/health`, `/`, `/plan-jobs/packaged-check`, and `/assets/index--BMBnGvJ.js` returned HTTP 200.
18. Final `uv sync --locked && uv lock --check`
    - Passed. FastAPI, Starlette, and Uvicorn were removed and the locked core environment was restored.
19. Core import-isolation script importing `buoy_search` and `buoy_search.cli`
    - Passed. `fastapi` and `uvicorn` were unavailable. Neither they nor turbopuffer, sentence-transformers, transformers, Command Center API/job modules, BigQuery/Snowflake adapters, or provider SDKs were loaded.
20. Final `git diff --check && test -z "$(git diff --cached --name-only)" && git status --short --branch`
    - Passed. No files are staged. The worktree contains only the expected Phase 2A implementation/records and this ticket's docs/CLI/contributor/CI/test changes.
21. Focused documentation/CLI checks: `PYTHONDONTWRITEBYTECODE=1 uv run --extra ui python -m unittest tests.test_command_center_cli tests.test_release_automation -q`
    - Final focused run passed: 36 tests in 2.067s; `OK`.

## Dependency advisory owner

`cd web && npm audit --omit=dev --audit-level=high` exited 1 and reported two high-severity dependency findings in the existing `react-router-dom` 7.18.1 / `react-router` graph for GHSA-qwww-vcr4-c8h2, “RSC Mode CSRF Bypass Allows Action Execution Before 400 Response.” npm's automated fix proposes forced `react-router-dom@7.11.0`, which it labels breaking. Phase 2A added no dependency and uses a Vite SPA rather than intentional React Server Components/action routing. Applicability and compatible remediation are separately owned by `.10x/tickets/2026-07-24-review-react-router-advisory.md`; this validation ticket did not make an unreviewed forced dependency change.

## Deviations and corrected exploratory checks

- The first focused documentation/CLI run passed 35 tests but failed one new assertion because argparse line-wrapped `command-center/plans` at its hyphen. The test was corrected to inspect the parser action's raw help contract rather than presentation wrapping; the final 36-test run passed.
- The first installed-wheel assertion compared an unresolved `/tmp` static path to Darwin's resolved `/private/tmp` target and failed without changing the repository. Resolving both paths corrected the assertion.
- The next installed-wheel request used TestClient's default `testserver` Host, which correctly received the Command Center's hostile-Host HTTP 400 response, so the script could not locate the HTML asset reference. The accepted rerun used the required loopback base URL and all static/API lookups passed.
- `npm audit` remains non-passing by design pending its separate advisory ticket; required npm install/test/build commands all passed.

## Acceptance mapping

- Documentation/public boundary: README, detailed guide, CLI help, and focused documentation tests cover only public website/GitHub managed planning, one-active durability/restart semantics, exclusions, CSRF/loopback controls, ordinary artifacts, and explicit CLI apply.
- Lifecycle/security/API/UI: the 105-test UI-extra basket plus the 717-test full suite cover durable state, interruption, one-active conflict, same-origin/CSRF/Host/body validation, SSE/polling, prohibited controls, and Phase 1 compatibility.
- CLI/apply/database compatibility: the explicit 235-test basket passed.
- Frontend/static/package: 36 frontend tests, reproducible Vite output, reference validation, 68-entry wheel, 155-entry sdist, and installed-wheel API/static lookups passed.
- Core restoration: final locked sync, lock check, import isolation, diff hygiene, and no-staged-files checks passed.

## Final-review finding repair validation

The three independent final-review artifacts identified malformed managed HTTP authorities, ambiguous capability/global read-only signals, out-of-order polling regressions, and inaccurate HTML metadata. The bounded repair added one shared `validate_http_url_authority()` path for managed-request and persisted-record validation; exact capability fields; monotonic `event_sequence`/request ordering with sticky terminal polling state; accurate local-command-center UI/HTML language; synchronized static assets; and focused regressions. No private-network/SSRF policy, live integration, broader mutation authority, or React Router advisory work was added.

Exact repair validation:

1. `PYTHONDONTWRITEBYTECODE=1 uv run --extra ui python -m unittest tests.test_planning_service tests.test_command_center_jobs tests.test_command_center_api tests.test_command_center_cli tests.test_release_automation -q`
   - Passed: 105 tests in 6.103s; `OK`.
   - Tests prove malformed/missing hosts, invalid/empty/zero/out-of-range ports, invalid DNS labels, and surrounding/embedded whitespace return HTTP 422 before job record/event creation, job-specific output creation, or executor submission. Valid IP, IDNA, and ports 1/65535 remain accepted, preserving the exclusion of private-network policy.
2. `cd web && npm test -- --run`
   - Passed: one Vitest file and all 37 tests in 1.738s.
   - Deferred promises resolved a newer terminal poll before older running/error polls; the terminal plan link/message and closed state remained sticky and neither stale result was rendered.
3. `cd web && npm run build`
   - Passed: TypeScript and Vite transformed 42 modules and emitted synchronized `index.html`, `assets/index-D9CN3CEt.js`, and `assets/index-Amu9gKyT.css`.
   - Current SHA-256 values supersede the pre-review build inventory above: index `b7bbdbac928332e50c652b3415646f060d21fd9ca7d07f58782c2dceb1a55e43`; JavaScript `ec1ff4d1cf50da92c2ba9fe041e7d3dc5afa26ea987a457df67b6bd87deab9c4`; CSS unchanged at `fd57c4f2b1319313451571398931ad5b20c8707cdc3f931cd88d993d3c1bd815`.
4. Static metadata/reference inspection
   - Passed: packaged description is `Buoy local operator console for review and bounded public-source planning`; `/buoy.svg`, `/assets/index-D9CN3CEt.js`, and `/assets/index-Amu9gKyT.css` all resolve.
5. `uv build --out-dir /tmp/buoy-phase2a-repair-dist` plus standard-library wheel/sdist assertions
   - Passed: 68-entry wheel and 155-entry sdist; the wheel has exactly one referenced JavaScript/CSS asset, accurate packaged metadata, and `source_url.py`; the sdist retains `web/index.html` and excludes `web/node_modules`.
6. Shared-validator direct valid/invalid authority check
   - Passed: accepted ordinary DNS, IDNA DNS, IPv4 port 1, and IPv6 port 65535; rejected ten malformed host/port/whitespace authorities.
7. Final `git diff --check` and staged-file inspection
   - Passed: no whitespace errors and no staged files.

Corrected exploratory checks were preserved: the first new deferred frontend test used fake async timer advancement while intentionally unresolved requests were outstanding and timed out; it was corrected to capture and invoke the interval callback directly, after which all 37 tests passed. The first post-repair TypeScript build exposed an overly narrow inferred `() => undefined` test callback type; adding the explicit `() => void` annotation corrected it. An initial static inspection invoked unavailable bare `python`; the accepted rerun used `uv run python` and passed. These were harness/test issues, not product validation failures.

## Remaining implementation finding repair chronology

After the prior final-review repairs, the last polling and API-metadata findings were repaired without repeating the full suite, package inventory, installed-wheel check, or core-environment restoration reserved for parent final-state validation.

1. Poll completion ordering now uses one monotonic accepted-request marker for both successful and failed nonterminal refreshes. Reverse-ordered deferred tests prove a newer error cannot be replaced by an older error or an older higher-event-sequence success. The existing terminal deferred test continues to prove terminal state, plan link, message, and closed status remain sticky.
2. `command_center_api.py` now describes the surface consistently in both its module docstring and FastAPI application metadata: a local command center with read-only reviews plus bounded local public-source planning. The focused API test asserts the application title and description.
3. `PYTHONDONTWRITEBYTECODE=1 uv run --extra ui python -m unittest tests.test_command_center_api -q`
   - Passed: 26 tests in 0.580s; `OK`.
   - The known FastAPI TestClient/Starlette deprecation warning was non-failing.
4. `cd web && npm test -- --run`
   - Passed: one Vitest file and all 39 tests in 2.54s.
   - The first invocation accidentally ran `npm test -- --run` from the repository root and failed because no root `package.json` exists; the corrected `web` invocation above is the accepted result and did not mutate project dependencies.
5. `cd web && npm run build`
   - Passed: TypeScript and Vite transformed 42 modules and emitted synchronized `index.html`, `assets/index-D1JLQG_N.js`, and `assets/index-Amu9gKyT.css`.
6. Static reference and SHA-256 inspection with `uv run python`
   - Passed: `/buoy.svg`, `/assets/index-D1JLQG_N.js`, and `/assets/index-Amu9gKyT.css` all resolve; missing references: none.
   - Current hashes: index `e2db18e546de8eac7c7796e235f950928a14ce6c7a89834eb6fb29acc888c7b6`; JavaScript `ec01ad2a64d20555da6a167fe81c21ba7ca9db5cfd9a7ec179e1c8cf21e71693`; CSS `fd57c4f2b1319313451571398931ad5b20c8707cdc3f931cd88d993d3c1bd815`.
7. Final `git diff --check` and staged-file inspection
   - Passed: no whitespace errors and no staged files.

## Parent-observed final-state validation

After the final monotonic polling/API metadata repair, the parent reran the complete required matrix against the final source:

- `git diff --check`: passed.
- `uv sync --locked`: passed in the core environment.
- Ranking contract validator: passed with 13 datasets/folds, 90 composite identities, and 369 judgments.
- C6 syntax forecast validator: passed at forecast `d5199276c19ae89779287eaa90824ce1e1cc684a3f060899f02f65d976016243`.
- Full unittest discovery: passed, **721 tests with 26 skips**.
- Explicit planning/CLI/apply/crawler/GitHub/database/job compatibility basket: passed, **277 tests**.
- `uv sync --locked --extra ui` and final Command Center/job/planning basket: passed, **108 tests**.
- `npm ci`: passed with 214 packages installed; the separately owned React Router advisory remains as recorded above.
- Final Vitest suite: passed, **39 tests**.
- Final TypeScript/Vite build: passed; a separate temporary Vite build was byte-identical to packaged static output.
- `uv build --out-dir dist`: passed. Final wheel contained **68 entries** and four command-center static entries; final sdist contained **155 entries**, all asserted Phase 2A/frontend/docs inputs, and no `node_modules`.
- A temporary-target installation of the final wheel served `/`, sanitized capabilities, and CSRF issuance with HTTP 200 through the real package-owned static/API application.
- Final `uv sync --locked`, `uv lock --check`, and corrected core import-isolation check passed: FastAPI/Uvicorn were absent and ordinary imports loaded no Command Center API/job module, optional database adapter, turbopuffer, or model SDK.
- Final diff/no-staged-files checks passed.

One attempted static synchronization command used `git diff --exit-code` against intentionally changed generated assets and therefore exited 1 after all Python/frontend tests had passed; synchronization was then correctly attested by rebuilding to a temporary directory and obtaining a byte-identical recursive comparison. One initial core-isolation assertion incorrectly required `planning_service` to be absent after importing the CLI, although the CLI now intentionally shares that service; the corrected contract checks UI/job modules and optional adapters/providers, and passed. Neither exploratory assertion changed project files.

Independent final implementation review passed with no blocker or significant finding. Review is recorded at `.10x/reviews/2026-07-24-phase-2a-public-plan-workflow.md`.

## Limits

- No live website crawl, GitHub clone/API operation, warehouse/provider call, model load, turbopuffer call, browser, server socket, apply, catalog/namespace mutation, commit, push, merge, PR, publish, or release operation ran. Source/provider behavior used existing offline fixtures and fakes.
- UI behavior used Vitest/jsdom and API behavior used in-process TestClient. A real graphical browser, proxy, and network transport were not exercised.
- The known Starlette TestClient/httpx and lxml warnings remain upstream and non-failing.
- Required independent final review is not supplied by executor evidence. The validation child and parent remain open for parent-owned independent review and graph reconciliation.
