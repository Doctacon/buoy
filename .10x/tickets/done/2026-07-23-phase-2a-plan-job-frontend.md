Status: done
Created: 2026-07-23
Updated: 2026-07-24
Parent: .10x/tickets/done/2026-07-23-phase-2a-public-plan-workflow.md
Depends-On: .10x/tickets/done/2026-07-23-phase-2a-plan-job-api-sse.md

# Implement Phase 2A Plan-Job Frontend

## Scope

Implement `.10x/specs/phase-2a-plan-job-interface.md`: navigation, start form, job history/detail/progress, CSRF-aware submission, SSE with polling fallback, terminal behavior, plan-review/origin links, and rebuilt package assets.

## Acceptance criteria

- Website/GitHub submission, validation, CSRF use, 409 conflict, timeline/history, live success, fallback/error, success review link, failed/interrupted new-plan link, escaped messages, plan-origin display, navigation, and no prohibited controls are tested.
- Existing Phase 1 routes/tests remain compatible.
- Production assets build into the package root with no new heavy client dependency.

## Evidence expectations

Record frontend tests/build/static synchronization and accessibility/read-only inspection.

## References

- `.10x/specs/phase-2a-plan-job-interface.md`
- API/SSE ticket implementation and schemas

## Progress and notes

- 2026-07-23: Opened from ratified Phase 2A scope.
- 2026-07-24: Implemented navigation and the managed start/history/detail routes; process-local CSRF submission; bounded form/history/timeline behavior; native EventSource reconnect with browser-managed Last-Event-ID and polling fallback; terminal review/new-plan links; and safe originating-job display on plan review. Added website/GitHub, validation/conflict, SSE/polling/terminal, escaping, origin, accessibility, storage, and route-exclusion coverage. Rebuilt packaged static assets. Frontend 28-test suite, TypeScript/Vite build, focused 30-test API/CLI compatibility basket, static-reference synchronization, diff hygiene, and no-staged-files checks pass. Evidence: `.10x/evidence/2026-07-23-phase-2a-plan-job-frontend.md`. Ticket remains active for the required independent review gate.
- 2026-07-24: Repaired frontend review findings: clarified read-only GET reload versus prohibited plan-job replay; enforced the 16 KiB UTF-8 advisory bound before CSRF retrieval; moved originating-job linkage into validated managed `summary.json` metadata and local/API plan detail; generation/AbortController-guarded previews; guarded stale EventSource callbacks; separated persistent stream notices from recoverable polling errors; and added managed-route error, deferred preview, durable origin, duplicate event, old-source, interval cleanup, and polling recovery coverage. Frontend 36-test suite, focused 83-test planning/local/API/job suite, compile checks, and rebuilt Vite assets pass.
- 2026-07-24: Independent final review passed with no blockers/significant findings. Closed after form/CSRF/conflict, SSE/polling, terminal/origin, race, accessibility/escaping, Phase1 regression, static synchronization, and prohibited-control criteria mapped to evidence. React Router advisory remains separately owned.

## Blockers

None after dependency completion.
