Status: done
Created: 2026-07-23
Updated: 2026-07-23
Parent: .10x/tickets/done/2026-07-23-command-center-phase-1-plan.md
Depends-On: .10x/tickets/done/2026-07-23-command-center-local-inventory-services.md

# Implement Command Center Remote Snapshot and Search Services

## Scope

Implement explicit, read-only remote snapshot and retrieval services governed by `.10x/specs/command-center-remote-and-search.md`, reusing current namespace, remote catalog, compatibility, routing, and retrieval functions.

## Acceptance criteria

- Explicit refresh combines live/catalog/local state using existing classifiers and performs no writes.
- Missing credentials and provider failures are sanitized and structured.
- Explicit, multi-namespace, and automatic retrieval preserve current compatibility/failure behavior.
- Inputs/results are bounded and secret-safe.
- Fake-client/retriever tests pass; startup/local inventory make no calls or model loads.

## Explicit exclusions

Catalog/namespace mutations, source-provider access, persistence, API/UI, and alternate ranking implementations.

## Evidence expectations

Record focused fake-based test results and exact reuse boundaries.

## References

- `.10x/specs/command-center-remote-and-search.md`
- `.10x/specs/remote-turbopuffer-routing-catalog.md`
- `.10x/specs/namespace-routing-card-contract.md`
- `.10x/decisions/production-routing-remote-catalog.md`

## Progress and notes

- 2026-07-23: Opened from user-ratified Phase 1 brief.
- 2026-07-23: Implemented explicit framework-independent remote snapshot and search services in `src/buoy_search/command_center_remote.py`, with fake-backed coverage in `tests/test_command_center_remote.py`. The services keep construction/local status inert, return structured missing-credential and sanitized provider failures, combine local inventory with the current stable remote catalog classifier, and delegate explicit, multi-namespace, and automatic searches to the current retrieval/routing paths.
- 2026-07-23: Verified 12 focused service tests and 108 namespace/catalog/routing/retrieval/local-inventory compatibility tests. Compilation, whitespace/diff hygiene, and no-staged-files checks passed. Evidence: `.10x/evidence/2026-07-23-command-center-remote-search-services.md`.
- 2026-07-23: Reuse boundaries are `read_remote_catalog`/`require_eligible` and its namespace/classification protocol, `hybrid_route` plus the pinned lazy routing embedder, `HybridRetriever`/`MultiNamespaceRetriever`, `RetrievalOptions`, and `ranking_defaults_for_namespace`; no alternate retrieval, ranking, mutation, API, CLI, server, frontend, or persistence path was introduced.

## Blockers

None.
