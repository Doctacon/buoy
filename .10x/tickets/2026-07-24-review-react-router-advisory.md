Status: open
Created: 2026-07-24
Updated: 2026-07-24
Parent: None
Depends-On: None

# Review React Router RSC CSRF Advisory

## Scope

Assess GHSA-qwww-vcr4-c8h2 against the Command Center Vite SPA and select a compatible non-vulnerable `react-router-dom` version if the advisory affects this build. Upgrade and validate only if needed.

## Acceptance criteria

- Document whether the application uses the affected React Server Components/action-execution mode.
- If affected, update to a compatible patched release and pass the frontend test/build basket.
- If unaffected, record the source-backed no-action rationale and the condition that requires re-evaluation.

## Evidence expectations

Record the installed dependency graph, advisory applicability, selected action, and frontend test/build results for any dependency change.

## References

- `web/package.json`
- `web/package-lock.json`
- GHSA-qwww-vcr4-c8h2
- `.10x/evidence/2026-07-23-phase-2a-plan-job-frontend.md`

## Progress and notes

- 2026-07-24: Opened after `npm audit --omit=dev --audit-level=high` reported the advisory in the existing React Router dependency. Phase 2A uses a Vite SPA and does not intentionally add RSC/action routing, but applicability and a compatible patch path require focused verification outside the frontend feature ticket.

## Blockers

None.

## Exclusions

No forced downgrade or dependency change without compatibility and applicability review.
