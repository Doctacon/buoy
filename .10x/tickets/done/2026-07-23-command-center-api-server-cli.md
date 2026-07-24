Status: done
Created: 2026-07-23
Updated: 2026-07-23
Parent: .10x/tickets/done/2026-07-23-command-center-phase-1-plan.md
Depends-On: .10x/tickets/done/2026-07-23-command-center-local-inventory-services.md, .10x/tickets/done/2026-07-23-command-center-remote-search-services.md

# Implement Command Center API, Server, and CLI

## Scope

Implement the lazy optional FastAPI/Uvicorn runtime, versioned read-only API, static fallback/security headers, loopback validation, and `buoy serve` command governed by `.10x/specs/command-center-local-api-and-server.md`.

## Acceptance criteria

- All specified API resources use application services and structured safe errors.
- Startup remains provider/model/source-adapter inert.
- `buoy serve` defaults/options/browser behavior work and reject every non-loopback host.
- Missing UI dependencies are actionable; ordinary commands remain import-compatible.
- API and CLI test matrix passes with temporary roots/fakes.
- No mutation endpoint exists.

## Explicit exclusions

Frontend implementation, hosting/auth/CORS, source/provider mutation, and packaging release.

## Evidence expectations

Record API/CLI tests and startup/import-isolation observations.

## References

- `.10x/specs/command-center-local-api-and-server.md`
- service tickets and their evidence
- `.10x/specs/buoy-local-compatibility.md`

## Progress and notes

- 2026-07-23: Opened from user-ratified Phase 1 brief.
- 2026-07-23: Implemented the lazy optional in-process FastAPI/Uvicorn runtime, versioned read-only API, safe structured errors, explicit remote refresh/search routes, static SPA fallback/security headers, strict loopback-only server validation, browser behavior, current state-root resolution, and `buoy serve` options. No frontend assets, dependency packaging, documentation/CI, subprocess architecture, or mutation routes were added.
- 2026-07-23: Added focused API/server and CLI coverage using temporary roots and injected services/runners, including every Phase 1 resource, safe failures, unknown API isolation, static fallback, browser behavior, missing dependency guidance, host rejection, and startup/import inertia. Focused API/CLI validation passed 14 tests; 107 relevant service/config/state/CLI/import-compatibility tests passed. Evidence: `.10x/evidence/2026-07-23-command-center-api-server-cli.md`.

## Blockers

None after dependencies complete.
