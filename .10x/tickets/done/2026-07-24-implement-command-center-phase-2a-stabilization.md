Status: done
Created: 2026-07-24
Updated: 2026-07-24
Parent: .10x/tickets/done/2026-07-24-command-center-phase-2a-stabilization.md
Depends-On: None

# Implement Command Center Phase 2A Stabilization

## Scope

Implement `.10x/specs/phase-2a-stabilization.md` surgically across the durable job store/service, FastAPI lifecycle/capabilities/routes, React UI/types/tests, terminology/help/docs/spec clarifications, shutdown logging, router-mode regression guard, packaged static assets, and validation. Integrate the source-backed conclusion from `.10x/tickets/done/2026-07-24-review-react-router-advisory.md` without expanding authority.

## Acceptance criteria

- Dedicated platform-unsupported exception catches only missing primitives; integrity, permissions/durability, malformed state, lock conflicts, and artifact failures remain fail-closed.
- Unsupported lifespan starts read-only services without constructing a worker or creating managed roots and returns sanitized capabilities/503 responses.
- Frontend uses capabilities to render explicit read-only fallback, no submission form/history request, and no CSRF/POST.
- New progress appends cap at 5,000 with exactly one coalescing event, no mutation/notification for skipped callbacks, terminal retention, contiguous sequences, SSE/reconnect behavior, and over-limit legacy readability.
- Website terminology consistently states credential-free HTTP(S), no public-routability/SSRF firewall, and loopback operator boundary.
- Active graceful shutdown logs only safe job ID/state and preserves `wait=True`/no-cancellation semantics.
- Advisory disposition has a narrow durable regression guard and no blind dependency churn or broad audit suppression.
- Existing tests and required validation/package checks pass; synchronized static assets are included.

## Evidence expectations

Record focused and full command outputs/results, unsupported import/root observations, event-bound invariants, frontend behavior, advisory sources/version/mode/reevaluation condition, package inventories/static synchronization, and validation limits in `.10x/evidence/`.

## References

- `.10x/specs/phase-2a-stabilization.md`
- `.10x/specs/phase-2a-plan-job-lifecycle.md`
- `.10x/specs/phase-2a-plan-job-api-security.md`
- `.10x/specs/phase-2a-plan-job-interface.md`
- `.10x/specs/phase-2a-public-source-planning-service.md`
- `.10x/knowledge/managed-plan-job-durability.md`
- `.10x/knowledge/loopback-command-center-security.md`
- `.10x/tickets/done/2026-07-24-review-react-router-advisory.md`

## Progress and notes

- 2026-07-24: Ticket activated from the exact user-ratified stabilization request; no execution-critical semantic blockers remain.
- 2026-07-24: Implemented the dedicated platform-unsupported probe/fallback, sanitized capabilities and uniform 503s, inert frontend managed-route fallback, 5,000-event coalescing/terminal reservation, terminology correction, safe non-cancellable shutdown log, declarative-router advisory guard/no-action evidence, synchronized assets, tests, docs, and active spec clarifications. Validation passed: ranking/C6, 730 core tests (29 optional-UI skips), 149 UI-extra focused tests, 40 Vitest tests, frontend build, wheel/sdist inventories, and installed-wheel supported/unsupported checks. `npm audit` remains expected nonzero only for the source-backed unreachable RSC advisory. Evidence: `.10x/evidence/2026-07-24-command-center-phase-2a-stabilization.md` and `.10x/evidence/2026-07-24-react-router-advisory-no-action.md`.
- 2026-07-24: Repaired all accepted independent-review findings: middleware now returns the uniform unavailable 503 before managed-route parameter validation; shutdown/start share a race-safe gate and state-lookup failure cannot bypass wait/ownership cleanup; import isolation is asserted before explicitly allowed remote/search imports; the router guard scans nested `web/src`; and unavailable routes retain an accessible page heading. Post-repair validation passed: 1 isolated unsupported API test, 3 shutdown regressions, 102 API/jobs/release tests, 40 Vitest tests, recursive router guard, and a synchronized production frontend rebuild.
- 2026-07-24: Repaired the sole rereview blocker: `_closed` still closes the start gate, while a dedicated completion event makes every concurrent `shutdown(wait=True)` caller wait through worker completion and ownership/resource cleanup. Completion signals even if cleanup raises; `wait=False` remains non-cancelling. The new two-caller regression, all four focused shutdown tests, the full 41-test durable-job module, `git diff --check`, and no-staged-files check passed.
- 2026-07-24: Repaired the final cleanup-isolation review blocker. Shutdown now attempts every artifact descriptor close, owner unlock, owner-handle close, and observer notification independently; clears retained descriptor state before close attempts; stores and raises the first cleanup failure; signals completion only after all cleanup attempts; and makes later `wait=True` callers re-raise the stored failure. Fault-injection tests proved both an early artifact-close failure and an unlock failure still close/release ownership and permit replacement service acquisition. All 43 durable-job tests, `git diff --check`, and the no-staged-files check passed.
- 2026-07-24: Repaired the final acceptance blocker for repeated lifespans of one FastAPI app. Every supported lifespan now restores managed-planning availability and clears `platform_unsupported` before exposing the service. The same-app unsupported-then-supported regression proves unavailable capabilities/503 with no construction first, then available capabilities plus working plan-job list/create and clean shutdown. The focused regression and all 30 API tests passed; diff, no-staged-files, lock, and default-environment restoration checks passed.
- 2026-07-24: Final parent-observed validation passed: 736 core tests (30 optional-UI skips), 155 UI-extra focused tests, 40 Vitest tests and production build, ranking/C6 validators, wheel/sdist inventories (68/155 entries), lock/diff checks, and default-environment restoration. Independent closure review passed with no blockers: `.10x/reviews/2026-07-24-command-center-phase-2a-stabilization-review.md`.

## Retrospective

The stabilization exposed reusable shutdown mechanics: separate start prohibition from cleanup completion, make cleanup failure-isolated, propagate the first failure, and test concurrent callers and repeated app lifespans. Those mechanics are now embodied in focused tests and the updated durability records; no new general skill is warranted. No unfinished implementation or newly discovered Phase 2 authority remains.

## Blockers

None.

## Exclusions

No Phase 2B, apply, deletion, cancellation, retry endpoint, source definitions, database UI planning, credentials/private GitHub, catalog/namespace mutations, graph features, auth, queue/database/daemon redesign, SSRF policy, router migration unless the verified advisory requires it, or unrelated refactor.
