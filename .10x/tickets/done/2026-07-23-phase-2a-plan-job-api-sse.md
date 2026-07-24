Status: done
Created: 2026-07-23
Updated: 2026-07-23
Parent: .10x/tickets/done/2026-07-23-phase-2a-public-plan-workflow.md
Depends-On: .10x/tickets/done/2026-07-23-phase-2a-durable-plan-jobs.md

# Implement Plan-Job API, CSRF, and SSE

## Scope

Implement `.10x/specs/phase-2a-plan-job-api-security.md` over the durable job service: server-process CSRF issuance/validation, bounded JSON creation, list/detail, structured conflicts/errors, and persisted-plus-live SSE replay/reconnect/closure.

## Acceptance criteria

- Same-origin Host/Origin/CSRF/content-type/size/URL/source validation is fail-closed and tested.
- Creation, 409 active conflict, list/detail/404/bounds, historical replay, Last-Event-ID, live completion, terminal closure, startup interruption, and non-duplication are tested.
- Startup stays source/provider/model inert and no prohibited endpoint appears.
- Existing Phase 1 API/security tests pass.

## Evidence expectations

Record focused API/SSE/security results and startup/import isolation.

## References

- `.10x/specs/phase-2a-plan-job-api-security.md`
- `.10x/specs/phase-2a-plan-job-lifecycle.md`
- Phase 1 security knowledge/specs

## Progress and notes

- 2026-07-23: Opened from ratified Phase 2A scope.
- 2026-07-23: Implemented lifespan-owned lazy plan-job service startup/shutdown, process-local CSRF issuance, bounded same-origin JSON creation, job list/detail, structured conflict/errors, and bounded persisted-plus-live SSE with reconnect IDs and terminal closure. Hardened safe failure logging and added fake/offline API security, lifecycle interruption, replay/live, route-surface, and compatibility coverage. Focused 18-test API and 290-test Phase 1/job/service compatibility suites pass. Evidence: `.10x/evidence/2026-07-23-phase-2a-plan-job-api-sse.md`. Ticket remains active for required independent review.
- 2026-07-23: Repaired every API/SSE adversarial-review finding: terminal snapshot plus durable final drain, source/planning import-inert startup, Last-Event-ID precedence, API-boundary job-ID validation, incremental 1,000-event replay windows, tail-only list/detail reconciliation, and direct ASGI/iterator security/backpressure/disconnect coverage. Focused 55-test API/job suite and expanded compatibility basket pass. Evidence updated at `.10x/evidence/2026-07-23-phase-2a-plan-job-api-sse.md`. Ticket remains active for the required follow-up review gate.
- 2026-07-23: Completed the ratified bounded-list repair: record `mtime_ns` descending with descending job-ID ties, 1,000 maximum offset, no-follow/private regular single-link metadata scanning, an `offset + limit` bounded heap, total counting without full decode, selected device/inode revalidation, and selected-only reconciliation. Many-job, deterministic-order, offset-bound, and metadata/identity tamper tests pass in the focused 56-test API/job suite.
- 2026-07-23: Independent final acceptance review passed with no blockers/significant findings. Closed after CSRF, origin/size, lifecycle ownership, startup inertia, Last-Event-ID, SSE race/replay/closure, bounded list/replay, and route-surface criteria mapped to evidence.

## Blockers

None after dependency completion.
