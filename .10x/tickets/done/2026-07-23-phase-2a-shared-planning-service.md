Status: done
Created: 2026-07-23
Updated: 2026-07-23
Parent: .10x/tickets/done/2026-07-23-phase-2a-public-plan-workflow.md
Depends-On: None

# Extract Shared Planning Service

## Scope

Implement `.10x/specs/phase-2a-public-source-planning-service.md`: move only the necessary `_run_plan` orchestration into a typed reusable service with progress callbacks and make the CLI delegate to it without output/behavior drift.

## Acceptance criteria

- Website/GitHub/public managed request construction, namespace override, output root, progress, artifact integrity, and safe no-remote/model/database-adapter boundaries are tested.
- Existing local-file/database CLI plan modes remain compatible through lazy source dispatch.
- Existing plan, apply, crawler, GitHub, database-source, and CLI regression tests pass.
- No job/API/frontend behavior is implemented in this child.

## Evidence expectations

Record focused/shared-service and CLI compatibility commands/results plus import/activity limits.

## References

- `.10x/specs/phase-2a-public-source-planning-service.md`
- current active source/planning/apply specifications and Phase 1 records

## Progress and notes

- 2026-07-23: Opened from ratified Phase 2A scope.
- 2026-07-23: Extracted the typed shared planning service and delegated CLI planning to it. Added managed website/GitHub request validation, bounded progress callbacks, absent-output enforcement, artifact verification, lazy source dispatch, and focused compatibility coverage. Recorded validation at `.10x/evidence/2026-07-23-phase-2a-shared-planning-service.md`; 6 focused tests, 241 plan/apply/source compatibility tests, and the complete 668-test default suite passed.
- 2026-07-23: Implementation and evidence are complete. Ticket remains active until the required independent review is recorded and closure coherence is checked.
- 2026-07-23: Repaired both significant findings from `.pi-subagents/artifacts/outputs/77fea6e5-1e3d-495c-b348-25dd88727c47/phase2a-reviews/planning-service.md`. CLI planning now uses the service-owned source construction and default acquisition dispatch without a duplicate CLI preflight/dispatcher; page verification now rejects unsafe/symlinked paths and persisted content whose normalized hash differs from the manifest. Added duplicate-constructor/default-dispatch and page-corruption regressions; 8 focused service tests and the 243-test planning/apply/source compatibility set pass.
- 2026-07-23: Independent re-review passed with no blocker/significant finding. Closed after acceptance mapping and evidence reconciliation.

## Blockers

None.
