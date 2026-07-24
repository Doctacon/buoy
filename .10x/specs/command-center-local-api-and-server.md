Status: active
Created: 2026-07-23
Updated: 2026-07-23

# Command Center Local API and Server

## Purpose and scope

Expose command-center services through a same-origin FastAPI application and a lazy `buoy serve` command suitable only for a local operator.

## Behavior

- `buoy serve` MUST default to `127.0.0.1:8765`, open a browser by default, support `--no-browser`, `--host`, `--port`, `--artifacts-root`, and `--state-root`, and use the current default applied-state resolver.
- Only `127.0.0.1`, `localhost`, and `::1` are accepted hosts. All other IPs/hostnames MUST be rejected before startup.
- FastAPI/Uvicorn imports MUST be lazy so ordinary CLI imports and commands do not require the UI extra.
- Missing UI dependencies MUST fail with the actionable command `uv sync --extra ui`.
- Startup MUST NOT inspect remote credentials unnecessarily, call providers, load routing/content embedding models, import BigQuery/Snowflake adapters, or access source databases.
- The versioned `/api/v1` API MUST include local health, sanitized capabilities, dashboard, namespace list/detail, plan list/detail, page list/detail, paginated chunks, explicit remote snapshot, and search.
- Unknown API routes MUST return structured errors; frontend fallback MUST not swallow `/api/*` misses.
- Static packaged frontend assets MUST be served same-origin with practical security headers and no permissive CORS.
- Errors MUST use safe `code`, `message`, and optional safe `details` fields.

## Acceptance criteria

1. FastAPI tests cover all Phase 1 endpoints, structured failures, static fallback, and unknown API behavior using temporary roots and fakes.
2. CLI tests cover help, defaults, no-browser, custom roots, host rejection, missing dependency guidance, and ordinary-command import isolation.
3. Tests prove startup performs no remote calls or embedding/source-adapter loads.
4. No mutation endpoint exists.

## Security constraints

No auth or remote hosting in Phase 1. No CORS relaxation, arbitrary filesystem path input, secret output, raw provider exception output, source database access, apply/delete/catalog mutation, or unbounded preview/search input.
