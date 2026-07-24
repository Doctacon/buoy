Status: done
Created: 2026-07-23
Updated: 2026-07-23
Parent: None
Depends-On: .10x/tickets/done/2026-07-23-command-center-phase-1-plan.md

# Phase 2A Public-Source Plan Workflow

## Aggregate outcome

Allow one local operator to start one public website or GitHub plan, observe durable progress, receive ordinary verified artifacts, and open the existing read-only plan review screen—without any apply, deletion, catalog, credential, source-definition, namespace, local-file, database, or graph authority.

## Governing specifications

- `.10x/specs/phase-2a-public-source-planning-service.md`
- `.10x/specs/phase-2a-plan-job-lifecycle.md`
- `.10x/specs/phase-2a-plan-job-api-security.md`
- `.10x/specs/phase-2a-plan-job-interface.md`
- All active Phase 1 command-center and current planning/apply/source specifications remain authoritative where not explicitly extended.

## Child sequence

1. Extract shared planning service and preserve CLI behavior.
2. Implement durable single-worker job records/events/state machine against the shared service.
3. Add guarded job API and SSE.
4. Add operator routes and packaged frontend assets.
5. Reconcile docs/CI/packaging, run complete validation, adversarially review, and close records.

Children are sequential executable units with one writer in a stacked `work/command-center-phase-2a` worktree based on Phase 1 commit `d716eba` (which already contains current `develop`). This parent is orchestration-only.

## Aggregate acceptance criteria

Every governing scenario is implemented; CLI plan/apply and Phase 1 behavior remain compatible; job durability/restart/concurrency/SSE/CSRF are proven; final wheel contains synchronized assets; full required validation and independent review pass; no excluded authority is added.

## Explicit exclusions

All broader Phase 2 and graph capabilities listed in the user ratification, plus push, merge, PR, release, publish, and unapproved live crawl/clone/provider operations.

## Progress and notes

- 2026-07-23: User ratified the exact Phase 2A workflow and authorized implementation. Repository inspection confirmed `_run_plan` owns reusable orchestration and crawler progress callbacks already exist. Focused specification/ticket graph created.
- 2026-07-24: Shared planning service, durable single-worker jobs, CSRF/API/SSE, frontend routes, docs/CI/package validation, and all repair/review rounds completed. Every child ticket is done.
- 2026-07-24: Final-state validation passed: 721 core tests (26 skipped), 277 compatibility tests, 108 UI-extra tests, 39 frontend tests/build, ranking/C6, wheel/sdist/installed-wheel checks, core restoration, and hygiene. Evidence: `.10x/evidence/2026-07-24-phase-2a-final-validation-packaging.md`.
- 2026-07-24: Independent final review verdict is pass with no unresolved blocker/significant finding: `.10x/reviews/2026-07-24-phase-2a-public-plan-workflow.md`. Retrospective: `.10x/knowledge/managed-plan-job-durability.md`. React Router advisory remains separately owned and does not expand Phase 2A authority.

## Blockers

None. Phase 2A remains intentionally stacked on unintegrated Phase 1; integration sequencing is external to this completed implementation ticket.
