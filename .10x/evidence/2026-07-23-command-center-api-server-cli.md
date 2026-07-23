Status: recorded
Created: 2026-07-23
Updated: 2026-07-23
Relates-To: .10x/tickets/done/2026-07-23-command-center-api-server-cli.md, .10x/specs/command-center-local-api-and-server.md

# Command Center API, Server, and CLI Validation

## What was observed

The optional command-center runtime is loaded only by `buoy serve`. Its in-process FastAPI application exposes versioned local health, sanitized fixed capabilities, dashboard, namespace list/detail, plan list/detail, page list/detail, bounded paginated chunks, explicit remote snapshot, and search resources by delegating to the completed application services. Expected lookup, request-validation, missing-credential, unknown-route, method, and unexpected failures are projected as safe structured errors. No apply, delete, catalog-write, source-write, or other mutation route exists.

Static files use a package-local default root with an injectable static-root hook for focused tests and the later frontend/package ticket. Existing assets are served same-origin, client routes fall back to `index.html`, `/api` misses never fall through to the frontend, and all responses receive a restrictive CSP, frame denial, no-sniff, and no-referrer headers without permissive CORS. Missing assets return a structured response because frontend/package assets are intentionally owned by later tickets.

The server accepts only `127.0.0.1`, `localhost`, and `::1`, validates ports, defaults to `127.0.0.1:8765`, opens the browser unless `--no-browser` is supplied, uses the current implicit/explicit applied-state resolver, and supplies actionable `uv sync --extra ui` guidance when FastAPI/Uvicorn are absent. FastAPI, Uvicorn, provider SDKs, embedding packages, and BigQuery/Snowflake adapters remain absent from an ordinary CLI import. Creating the application did not import the remote command-center service, provider/model packages, or source adapters; the remote snapshot and search layers are instantiated only by their explicit endpoints.

## Procedure and results

1. `uv run --with 'fastapi>=0.115,<1' --with 'uvicorn>=0.30,<1' --with 'httpx>=0.27,<1' python -m unittest tests/test_command_center_api.py tests/test_command_center_cli.py -q`
   - Result: passed.
   - Output: 14 tests ran in 0.545s; `OK`.
   - Coverage included every Phase 1 API resource, temporary empty roots, injected inventory/remote/search services, pagination and preview parameters, structured lookup/request/provider errors, explicit-only remote activity, static asset and SPA fallback behavior, unknown API isolation, security headers/no CORS, missing static assets, no mutation resources, server browser/IPv6 behavior, CLI help/defaults/custom roots/no-browser, representative non-loopback rejection, dependency guidance, and clean ordinary-import/startup inertia.
   - The temporary `--with` environment reported a Starlette TestClient deprecation warning about its current httpx integration; it did not affect results or modify project dependency/lock files.
2. `uv run python -m unittest tests/test_command_center_local.py tests/test_command_center_remote.py tests/test_config.py tests/test_applied_state.py -q`
   - Result: passed.
   - Output: 54 tests ran in 1.652s; `OK`.
3. `uv run python -m unittest tests/test_cli.py -q`
   - Result: passed.
   - Output: 41 tests ran in 14.465s; `OK`.
   - Two existing advisory cleanup warnings were emitted by failure-path tests; the suite passed.
4. `uv run python -m unittest tests/test_database_relation_cli.py tests/test_cutover_isolation.py -q`
   - Result: passed.
   - Output: 12 tests ran in 0.246s; `OK`.
5. `uv run buoy serve --no-browser --state-root <temporary-root>/state` in the normal locked environment, with stdout/stderr and exit status asserted.
   - Result: passed.
   - Output: exited 2, kept stdout empty, and wrote `Command Center dependencies are missing. Run: uv sync --extra ui` to stderr.
6. `uv run python -m py_compile src/buoy_search/command_center_api.py src/buoy_search/command_center_server.py src/buoy_search/cli.py tests/test_command_center_api.py tests/test_command_center_cli.py && git diff --check && test -z "$(git diff --cached --name-only)"`
   - Result: passed.
   - Output: compilation and tracked-diff hygiene passed; no staged files.
7. `! grep -n '[[:blank:]]$' <new API/server/test/evidence/ticket files> && git diff --check && test -z "$(git diff --cached --name-only)"`
   - Result: passed.
   - Output: new-file whitespace, tracked-diff hygiene, and no-staged-files checks passed.

## What this supports or challenges

This supports every acceptance criterion in `.10x/tickets/done/2026-07-23-command-center-api-server-cli.md` and the server/API behavior in `.10x/specs/command-center-local-api-and-server.md`. It also supports compatibility with the completed local and remote services, current state-root rules, existing CLI behavior, and source-adapter import isolation.

## Limits

- FastAPI, Uvicorn, and httpx were supplied only to the focused test command through uv's temporary `--with` environment. Adding the `ui` optional dependency and lock/package metadata remains explicitly owned by the packaging ticket.
- No frontend implementation or packaged static asset exists yet. The API/server provides the default package-local location, injectable static-root hook, fallback, headers, and structured missing-asset behavior needed by the later frontend/package tickets.
- No live socket, browser, credential, provider, network, embedding model, source adapter, or source database was used. Uvicorn and browser behavior used injected fakes; remote/search behavior used injected application-service fakes.
