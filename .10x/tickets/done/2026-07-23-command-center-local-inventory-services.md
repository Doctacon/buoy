Status: done
Created: 2026-07-23
Updated: 2026-07-23
Parent: .10x/tickets/done/2026-07-23-command-center-phase-1-plan.md
Depends-On: None

# Implement Command Center Local Inventory Services

## Scope

Implement typed, framework-independent local plan/state/namespace/dashboard/artifact-query services governed by `.10x/specs/command-center-local-inventory.md`. Reuse current domain parsers and state/diff models where safe.

## Acceptance criteria

- Discovery, dedupe, ordering, malformed isolation, aggregation, all supported source mappings, private-path behavior, safe IDs/previews, and bounded pagination are implemented.
- Local inventory neither imports source adapters nor accesses remote providers/models/databases.
- Focused service tests pass without credentials, network, model cache, or browser.

## Explicit exclusions

Remote snapshot/search, FastAPI/server/CLI, frontend, packaging/docs/CI, and all mutations.

## Evidence expectations

Record focused test commands/results, inspected compatibility points, and limits in a related evidence record.

## References

- `.10x/specs/command-center-local-inventory.md`
- `.10x/specs/database-document-relation-indexing.md`
- `.10x/decisions/plan-artifact-immediate-lifecycle-retention.md`

## Progress and notes

- 2026-07-23: Opened from user-ratified Phase 1 brief after source/record inventory.
- 2026-07-23: Implemented the typed, framework-independent local inventory/application-service layer in `src/buoy_search/command_center_local.py` with focused coverage in `tests/test_command_center_local.py`.
- 2026-07-23: Verified discovery, deduplication, timestamp ordering, malformed isolation, plan/state aggregation, all supported source mappings, private-path/provider-detail redaction, safe IDs, symlink/traversal rejection, preview and pagination bounds, current plan/state/diff compatibility, and clean-import isolation. Evidence: `.10x/evidence/2026-07-23-command-center-local-inventory-services.md`.
- 2026-07-23: Focused validation passed: 14 local-inventory tests and 45 current plan/state/diff compatibility tests. No credentials, network, model cache, browser, provider SDK, or source adapter was used.

## Blockers

None.
