Status: recorded
Created: 2026-07-23
Updated: 2026-07-23
Relates-To: .10x/tickets/done/2026-07-23-command-center-packaging-docs-ci-validation.md, .10x/specs/command-center-packaging-documentation-ci.md

# Command Center Packaging, Documentation, and CI Validation

## What was observed

The `ui` extra resolves bounded `fastapi>=0.115,<1` and `uvicorn>=0.30,<1` dependencies while the restored core environment contains neither package. Ordinary `buoy_search` and CLI imports passed in that core environment without Node. Hatch explicitly retains packaged static assets and frontend build inputs while excluding `web/node_modules`.

The built wheel contains the production index, Buoy SVG, and hashed JavaScript/CSS. The sdist contains those static files plus all intended React/TypeScript source, tests, npm lock/manifest, TypeScript configs, and Vite config; it contains no `node_modules`. A wheel installed without dependencies into a temporary target and executed with the validated project environment served its packaged root, SPA fallback, and hashed JavaScript through the real default static lookup.

README, `docs/command-center.md`, and CONTRIBUTING now cover installation, local-only/read-only behavior, explicit remote activity, credentials, screens, roots, security, troubleshooting, contributor asset synchronization, non-goals, and the Phase 2–4 roadmap. CI retains the Python 3.11/3.13 checks and adds exact Node 24.18.0 frontend install/test/build/static-sync checks plus locked UI-extra Python tests and wheel/sdist content validation.

## Procedure and results

1. `git status --short --branch && git worktree list`
   - Passed. Work ran on `work/command-center-phase-1` in its dedicated worktree; existing Phase 1 changes were preserved.
2. `uv lock`
   - Passed. Resolved 157 packages and added FastAPI 0.139.2, Starlette 1.3.1, and Uvicorn 0.51.0 behind the `ui` extra.
3. `uv lock --check && PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests.test_release_automation -q`
   - Passed. Lock check succeeded; 28 workflow/public-surface/package-metadata tests passed in 2.203s.
4. `uv sync --locked`
   - Passed. Resolved 157 packages and checked the 106-package core environment.
5. Core import-isolation script importing `buoy_search` and `buoy_search.cli` and asserting `find_spec("fastapi")` and `find_spec("uvicorn")` are `None`.
   - Passed. Ordinary imports used neither optional web dependency.
6. `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/validate_ranking_contract.py`
   - Passed. Reported 13 datasets/folds, 90 composite identities, 369 judgments, dataset bundle SHA-256 `5a79f58aaca87a2d4f7cbec68fdcfbbcbf041131821587f8aba74a86daca99d9`; Buoy remains pending baseline approval as expected.
7. `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/c6_syntax_forecast.py validate`
   - Passed. Forecast SHA-256 `d5199276c19ae89779287eaa90824ce1e1cc684a3f060899f02f65d976016243`; tokenizer readiness remained false at the expected checkpoint.
8. `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover -s tests -p 'test_*.py' -q`
   - Passed. 649 tests ran in 65.220s; `OK (skipped=9)`. Output contained two established cleanup warnings, expected argparse diagnostics from host-rejection tests, and one upstream lxml deprecation warning.
9. `uv sync --locked --extra ui`
   - Passed. Installed FastAPI 0.139.2, Starlette 1.3.1, and Uvicorn 0.51.0.
10. `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests/test_command_center_local.py tests/test_command_center_remote.py tests/test_command_center_api.py tests/test_command_center_cli.py -q`
    - Passed. 40 tests ran in 2.118s; `OK`. Starlette emitted its known TestClient/httpx deprecation warning.
11. `uv run buoy serve --help`
    - Passed. Help showed the loopback host, port, artifacts root, state root, and no-browser options.
12. `cd web && npm ci`
    - Passed under local Node 24.6.0/npm 11.5.1. Installed 214 packages, audited 215, and found 0 vulnerabilities; one upstream deprecated `whatwg-encoding` notice was emitted.
13. `cd web && npm test -- --run`
    - Passed. One file and all 13 frontend tests passed in 1.14s.
14. `cd web && npm run build`
    - Passed. TypeScript and Vite 7.3.6 transformed 42 modules and produced `index.html` (0.61 kB), `assets/index-BTsfTtCu.css` (9.63 kB), and `assets/index-BT1xFvs2.js` (257.41 kB).
15. SHA-256 inventory before and after the frontend build.
    - Passed with no diff. The committed/generated static output was synchronized byte-for-byte.
16. `uv build`
    - Passed. Built `buoy_search-0.4.1.dev78+gee3b927ab.d20260723-py3-none-any.whl` and `buoy_search-0.4.1.dev78+gee3b927ab.d20260723.tar.gz`.
17. Standard-library wheel/sdist inventory assertions.
    - Passed. The wheel had 65 entries; the sdist had 150 entries. Required index/hashed assets and all frontend inputs were present; no `web/node_modules` entry existed.
18. Wheel metadata inspection.
    - Passed after matching Hatch's normalized single-quoted marker format. Metadata provides `ui` and declares `fastapi<1,>=0.115` and `uvicorn<1,>=0.30` only when `extra == 'ui'`.
19. Temporary-target wheel install plus FastAPI TestClient lookup using the installed package's actual `DEFAULT_STATIC_ROOT`.
    - Passed. `/`, `/plans/packaged-check`, and `/assets/index-BT1xFvs2.js` each returned HTTP 200 with security headers; package and static paths came from `/tmp/buoy-command-center-wheel-target`, not the checkout.
20. Parsed `.github/workflows/ci.yml` and executed its package-verification here-document against the built artifacts.
    - Passed. YAML exposed `test`, `frontend`, `command-center-package`, and `build`; Node was exactly `24.18.0`; the CI archive assertions passed.
21. Final `rm -rf dist && uv sync --locked && uv lock --check`, core import-isolation assertion, `git diff --check`, and `test -z "$(git diff --cached --name-only)"`.
    - Passed. Removed FastAPI, Starlette, and Uvicorn; restored the 106-package core environment; ordinary imports still passed; lock/diff checks passed; no files were staged.

## Final package inventories

Wheel static entries:

```text
buoy_search/command_center_static/assets/index-5RmbL4VH.js
buoy_search/command_center_static/assets/index-BcWfZ-Sy.css
buoy_search/command_center_static/buoy.svg
buoy_search/command_center_static/index.html
```

Sdist frontend/static entries:

```text
src/buoy_search/command_center_static/assets/index-5RmbL4VH.js
src/buoy_search/command_center_static/assets/index-BcWfZ-Sy.css
src/buoy_search/command_center_static/buoy.svg
src/buoy_search/command_center_static/index.html
images/buoy.svg
web/index.html
web/package-lock.json
web/package.json
web/src/App.test.tsx
web/src/App.tsx
web/src/api.ts
web/src/main.tsx
web/src/setupTests.ts
web/src/styles.css
web/src/types.ts
web/tsconfig.app.json
web/tsconfig.json
web/tsconfig.node.json
web/vite.config.ts
```

Static SHA-256 values after the reproducible frontend build:

```text
8278d85a39d543f2db5491a2c978e8eccb8aad29390555b9561a3aad2126e7ea  assets/index-5RmbL4VH.js
eb1e3e2ece2e56a81a4e93e0528168fcf7b954dea87c3d4e7b178ebb3b0e3a03  assets/index-BcWfZ-Sy.css
f791c77f25e202a0556d2688ec9180e7d78c983f220f84b097c1fdc8894edcef  buoy.svg
b685db871296a5b27f3d02dedae93d0a5d8741f2f14999733209a45b3d811e7b  index.html
```

## Deviations and limits

- The local frontend checks used the available Node 24.6.0 rather than CI's exact current LTS 24.18.0. The workflow pins Node 24.18.0 and immutable `actions/setup-node` SHA `249970729cb0ef3589644e2896645e5dc5ba9c38`; no hosted workflow was run in this no-push/no-PR task.
- One exploratory wheel-metadata assertion expected double quotes around the extra marker and failed. Direct inspection showed standards-equivalent Hatch output with single quotes; the corrected exact assertion passed. No artifact or source change was required.
- A pre-configuration exploratory sdist build revealed 5,171 `web/node_modules` entries because the directory was not ignored. The final Hatch exclusion and `.gitignore` remove them; the accepted final sdist has 150 total entries and zero `node_modules` entries.
- No live turbopuffer, website, GitHub source crawl, document conversion, DuckDB source, BigQuery, Snowflake, model, browser, or socket operation ran. Remote/search tests used fakes; server lookup was in-process.
- Independent adversarial review and parent-plan closure remain parent-owned and were not performed here.

## Review repair validation

The three Phase 1 review artifacts were reconciled on 2026-07-23. Every named blocker/significant/moderate finding and bounded minor frontend/docs/CI finding was repaired. Regression coverage now exercises hostile Host and forged POST rejection, tokenized citation query stripping, state-root symlink rejection, duplicate namespace-state conflicts with unknown counts, exact explicit/automatic mode selection, pre-call versus provider-call failures, search score/diagnostic rendering, remote-only inventory, inventories/pages beyond 100, palette contrast, failed-latest-refresh and truncation disclosure, stale preview clearing, skip navigation, activated chunk/page pagination, route-wide no-mutation controls, contributor UI-extra/static synchronization commands, and the complete sdist frontend input list.

Observed commands and results:

- `PYTHONDONTWRITEBYTECODE=1 uv run --extra ui --with 'httpx>=0.27,<1' python -m unittest tests/test_command_center_local.py tests/test_command_center_remote.py tests/test_command_center_api.py tests/test_command_center_cli.py tests/test_release_automation.py -q`: passed, 77 tests.
- `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests/test_plan_artifacts.py tests/test_applied_state.py tests/test_plan_diff.py tests/test_remote_catalog.py tests/test_automatic_routing.py tests/test_multi_namespace_retrieval.py tests/test_retriever.py -q`: passed, 132 compatibility tests.
- `cd web && npm test -- --run && npm run build`: passed, 18 frontend tests; TypeScript and Vite rebuilt synchronized hashed assets `assets/index-5RmbL4VH.js` and `assets/index-BcWfZ-Sy.css`.
- `uv build --out-dir /tmp/buoy-command-center-repair-dist` plus archive assertions: passed; wheel had 65 entries, sdist had 150 entries, all 15 required frontend/public build inputs were present, and no `web/node_modules` entry existed.
- `git diff --check`: passed.

The full Python suite was deliberately not rerun at this checkpoint per parent steering; final aggregate validation remains parent-owned. No live provider/source/model call, server socket, commit, push, PR, merge, publish, or release occurred.

## Final product/security finding repair validation

The four findings remaining in the final product/security review were repaired on 2026-07-23 without changing the read-only/local-only boundary. A real `HybridRetriever` regression proves that a malformed provider response received after one fake `multi_query` call becomes `ProviderCallError`, and the command-center response truthfully reports `api_calls_occurred=True` while retaining its generic public error. Local page/chunk and remote search citation regressions prove that HTTP query strings and all fragments are removed, path-shaped `file://document-id/Users/private/secret.txt` citations are redacted, and the persisted one-segment percent-encoded document citation remains visible. Frontend regressions prove that duplicate applied-state identity conflicts are not called absent state and that selecting page 21 remains page 21 after advancing chunk pagination.

Observed commands and results:

- `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests/test_retriever.py tests/test_command_center_remote.py tests/test_command_center_local.py -q`: passed, 60 tests.
- `PYTHONDONTWRITEBYTECODE=1 uv run --with fastapi --with uvicorn --with httpx python -m unittest tests/test_command_center_local.py tests/test_command_center_remote.py tests/test_command_center_api.py tests/test_command_center_cli.py tests/test_release_automation.py -q`: passed, 79 tests. Output included expected safe failure log lines, argparse host-rejection diagnostics, and the known Starlette TestClient/httpx deprecation warning.
- `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests/test_plan_artifacts.py tests/test_applied_state.py tests/test_plan_diff.py tests/test_remote_catalog.py tests/test_automatic_routing.py tests/test_multi_namespace_retrieval.py tests/test_retriever.py -q`: passed, 132 compatibility tests.
- `cd web && npm test -- --run`: passed, one file and 20 tests.
- `cd web && npm run build`: passed; TypeScript and Vite 7.3.6 transformed 42 modules and rebuilt `index.html` (0.61 kB), `assets/index-BcWfZ-Sy.css` (9.82 kB), and `assets/index-CdLxZlZF.js` (260.27 kB). The packaged index references the new hashed JavaScript asset.
- `git diff --check` and `test -z "$(git diff --cached --name-only)"`: passed; no staged files.

No full-suite, package-archive, live provider/source/model, browser, socket, commit, push, PR, merge, publish, or release operation was run for this bounded final repair. The active closure ticket and parent remain open for independent final review.

## Remaining database citation finding repair validation

The final acceptance finding was repaired on 2026-07-23 without widening the Command Center surface. Local and remote sanitizers now recognize the actual `database_document_url()` persistence shape for DuckDB, BigQuery, and Snowflake: a validated source-ID authority followed by exactly one canonical percent-encoded document-ID segment, within the existing 2,000-character citation response bound. Raw path hierarchies such as `<backend>://gong-calls/Users/private/secret.txt` are omitted. Generated values for document ID `call/1 ? ü` remain visible from both sanitizers, including the encoded slash, space, question mark, and Unicode bytes.

Regression coverage adds all-three-scheme local page/chunk leakage cases and an all-three-scheme fake-backed explicit-search test using `database_document_url()` as the expected-value authority.

Observed commands and results:

- `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests/test_command_center_local.py tests/test_command_center_remote.py tests/test_retriever.py -q`: passed, 61 tests. Expected sanitized failure log lines from fake failure-path tests were emitted.
- `uv run python` direct local/remote sanitizer reproduction for generated and raw path-shaped DuckDB, BigQuery, and Snowflake citations: passed. Both sanitizers preserved each generated citation; local returned `None` and remote returned `""` for each raw hierarchy.
- `git diff --check` plus trailing-whitespace checks across the six changed source/test/record files and `test -z "$(git diff --cached --name-only)"`: passed; no files are staged.

An initial direct-reproduction attempt invoked unavailable bare `python` and made no project change; the corrected `uv run python` command passed. No full suite, live provider/source/model, browser, socket, commit, push, PR, merge, publish, or release operation was run at that repair checkpoint.

## Parent-observed final aggregate validation

After all review repairs, the parent observed:

- `git diff --check`: passed.
- `uv sync --locked`: passed with the 106-package core environment.
- `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/validate_ranking_contract.py`: passed with 13 datasets/folds, 90 composite identities, and 369 judgments.
- `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/c6_syntax_forecast.py validate`: passed at forecast `d5199276c19ae89779287eaa90824ce1e1cc684a3f060899f02f65d976016243`.
- Final `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover -s tests -p 'test_*.py' -q`: passed, 660 tests with 11 skips.
- `uv sync --locked --extra ui` followed by command-center discovery: passed, 49 tests.
- `cd web && npm ci`: passed under Node 24.6.0/npm 11.5.1; 214 packages installed, 0 vulnerabilities.
- Final `npm test -- --run`: passed, 20 tests.
- Final `npm run build`: passed; 42 modules produced synchronized hashed CSS `index-BcWfZ-Sy.css` and JavaScript `index-CdLxZlZF.js`.
- `uv build --out-dir dist`: passed. Wheel had 65 entries including index and hashed assets; sdist had 150 entries including required frontend inputs and no `node_modules`.
- A temporary-target installed wheel served its package-owned static root through the real FastAPI application with HTTP 200.
- Final `uv sync --locked`, `uv lock --check`, core import isolation, no-staged-files check, and diff hygiene: passed; FastAPI/Uvicorn were absent from the restored core environment.

Two exploratory validation commands used unavailable bare `python` or an initially non-isolated import path and failed without changing project files; corrected `uv run python`/isolated-path commands passed. Independent review is recorded at `.10x/reviews/2026-07-23-command-center-phase-1.md` with verdict `pass`.
