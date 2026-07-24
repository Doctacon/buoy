Status: done
Created: 2026-07-24
Updated: 2026-07-24
Parent: None
Depends-On: .10x/tickets/done/2026-07-24-command-center-phase-2a-stabilization.md

# Command Center Phase 2A Live Acceptance

## Scope

Execute the user-ratified Phase 2A release-candidate acceptance contract from latest `main` on `work/command-center-phase-2a-acceptance`. Use isolated temporary artifact/state/log roots, a real browser engine, bounded credential-free website and public GitHub sources, deterministic loopback fixtures, and the existing CLI dry-run preflight. Record sanitized evidence and repair only deterministic product defects that violate the active Phase 1, Phase 2A, or stabilization specifications.

## Acceptance criteria

- Validate startup/help/build packaging and every Command Center navigation route in a real browser without automatic remote refresh, search, embedding, plan creation, or turbopuffer activity.
- Produce and review bounded website and public GitHub plans through the browser; reload during active progress without duplicate execution/events; inspect ordinary safe artifacts.
- Verify one UI-produced `plan.json` with `buoy apply --dry-run` and no source reacquisition, remote call, or mutation.
- Observe one-active-job conflict through the UI using a delayed loopback fixture.
- Observe graceful shutdown waiting for a running non-cancellable job, safe logging, restart readability, and preserved terminal state.
- Observe abrupt kill followed by restart-to-`interrupted`, no resume/retry/plan ID, and successful subsequent ownership/job creation.
- Inspect the browser product authority and security boundaries named in the user contract, including hostile Host rejection, CSRF handling, loopback-only binding, text rendering, and absence of prohibited controls/inputs.
- Run the requested focused Python tests, frontend tests, production build, lock/sync checks, and diff checks; run the full matrix only if implementation/frontend source changes for a real defect.
- Create `.10x/evidence/2026-07-24-command-center-phase-2a-live-acceptance.md`, clean temporary processes/artifacts, commit the bounded evidence (and any authorized defect repair), and leave the branch ready for handoff without push, PR, merge, publish, release, real apply, or turbopuffer write.

## Evidence expectations

Record host/tool/browser versions, tested commit, sanitized server invocation/root layout, exact sources, resolved GitHub commit when available, job/plan IDs and terminal states, artifact-relative paths, browser/network/reload observations, lifecycle tests, security/product-authority inspection, commands and exact outcomes, defect classification, and environmental limits. Do not commit raw logs, screenshots, browser profiles, generated plans/jobs, cloned source, external content, or secrets.

## Governing records

- `.10x/specs/phase-2a-stabilization.md`
- `.10x/specs/phase-2a-plan-job-lifecycle.md`
- `.10x/specs/phase-2a-plan-job-api-security.md`
- `.10x/specs/phase-2a-plan-job-interface.md`
- `.10x/specs/phase-2a-public-source-planning-service.md`
- `.10x/specs/command-center-local-api-and-server.md`
- `.10x/specs/command-center-operator-interface.md`
- `.10x/evidence/2026-07-24-command-center-phase-2a-stabilization.md`

## Exclusions

No real/approved apply, turbopuffer write, explicit remote refresh/search, managed database planning, private source/credentials, Phase 2B authority, architecture redesign, permanent browser dependency, push, PR, merge, publish, or release.

## Progress and notes

- 2026-07-24: Fetched `origin/main` at `6910ec7b9c1cebefead105de64135965a27cdb2e`, confirmed stabilization records, created the requested clean worktree branch, and activated this executable acceptance ticket from the fully specified user contract.
- 2026-07-24: Initial focused validation passed (122 backend tests, 40 frontend tests, production build). Real Chromium exposed two deterministic contract defects: GitHub jobs omitted acquisition/processing progress, and live Uvicorn SIGTERM waited safely behind SSE but emitted no active-job warning.
- 2026-07-24: Added fixed sanitized GitHub acquisition/processing/chunk callbacks plus durable-stage regression coverage. Added a default-server shutdown signal announcement, a single bounded job-log sink, warning deduplication, and signal/service regression coverage. Repeat live Chromium acceptance passed website, GitHub, reload, review, conflict, graceful shutdown, abrupt interruption/restart, CLI dry-run, authority, and security checks.
- 2026-07-24: Recorded sanitized evidence at `.10x/evidence/2026-07-24-command-center-phase-2a-live-acceptance.md`; removed all temporary processes, fixtures, roots, artifacts, state, logs, clones, and profiles. Final validation passed: 737 full Python tests, 156 UI-extra focused tests, 40 frontend tests, production build, ranking contract, C6 forecast, package build, lock restoration, and diff checks.
- 2026-07-24: Independent review found shutdown-warning deduplication remained sticky after a rejected `shutdown(wait=False)`: a later job in the same still-open service could be awaited without its own warning. Replaced the service-lifetime boolean with active-job-ID deduplication and added a deterministic two-job regression proving one warning per job and that the second shutdown waits. Targeted regression passed; the jobs/API modules passed 75 tests with the UI extra and no skips; default dependencies and lock state were restored; diff checks passed.
- 2026-07-24: Independent rereview passed with no remaining finding. Review recorded at `.10x/reviews/2026-07-24-command-center-phase-2a-live-acceptance.md`; acceptance evidence, tests, specifications, and ticket status are coherent, so the ticket is closed.

## Retrospective

Live acceptance found two gaps that isolated unit tests could not establish: source-specific progress requires exercising the real acquisition implementation, and Uvicorn waits for open SSE connections before application lifespan shutdown. The fixes preserve Phase 2A authority by adding only fixed safe progress and an early deduplicated shutdown observation; no cancellation, retry, mutation, or new source authority was introduced. Future managed-job acceptance should continue to include a real server signal with an open progress stream and at least one source-specific stage assertion.

## Blockers

None.
