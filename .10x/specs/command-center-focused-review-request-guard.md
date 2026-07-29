Status: active
Created: 2026-07-29
Updated: 2026-07-29

# Command Center Focused Review Request Guard

## Purpose and scope

Bound expensive focused plan-review requests initiated by one `/plans/:planId` browser screen while preserving one fresh complete verification for every accepted changed-chunk or stale-row payload request. This narrows `.10x/specs/command-center-coalesced-plan-review.md` and `.10x/specs/command-center-operator-interface.md` without adding cancellation, queuing, caching, or shared authority.

## Behavior

- One Plan screen instance MUST accept at most one focused request at a time across changed-chunk pagination, stale-row pagination, changed-chunk retry, and stale-row retry.
- The guard MUST include synchronous state (for example, a ref) so two invocations in one render interval cannot both pass.
- While a focused request is active, all changed/stale Previous, Next, and focused Retry controls MUST be disabled. Additional focused invocations MUST be ignored, not queued or replayed.
- The active section MUST clearly indicate loading. Existing detail and both already displayed windows MUST remain visible.
- Success or failure MUST clear the shared guard and re-enable both sections. Failure MUST preserve the relevant section window and permit exactly one subsequent retry.
- Plan-ID changes MUST invalidate old focused result handling, reset both windows, clear the UI guard for the new screen, and preserve generation/sequence stale-result protection. Finishing server work is not cancelled.
- Initial review remains one combined request and one complete verification.
- Every accepted focused request MUST continue to call one focused API endpoint and perform one fresh complete linear verification. No queue, frontend/backend result cache, cancellation contract, or cross-user/tab/process lock is permitted.

## Acceptance criteria

Frontend tests prove cross-section control disabling for either active request, same-render rapid-click exclusion, cross-section exclusion, retry exclusion, re-enable after success/failure, preserved detail/unaffected content, route-change stale-result protection, exactly one initial request, and exactly one request per accepted focused transition. A deterministic characterization records rapid interaction counts before and after.

## Operational truth

The guard bounds one screen's submitted work; it does not cancel a prior route's server request or coordinate tabs. Complete verification remains linear and may take several seconds.

## Exclusions

No backend cache or lock, trusted session/token, cancellation, schema change, apply/approval, deletion, graph extraction, provider work, or turbopuffer write.
