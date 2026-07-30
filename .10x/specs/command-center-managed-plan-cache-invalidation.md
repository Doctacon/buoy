Status: superseded
Created: 2026-07-27
Updated: 2026-07-27

# Command Center Managed Plan Cache Invalidation

## Purpose and scope

Define the one-way notification from successful in-process managed plan publication to the process-local Command Center summary cache. This augments `.10x/specs/phase-2a-plan-job-lifecycle.md`, `.10x/specs/phase-2a-public-source-planning-service.md`, and `.10x/specs/command-center-summary-inventory-performance.md` without changing managed-job authority, artifact publication, or ordinary CLI behavior.

## Behavior

- `PlanJobService` MAY accept an optional framework-independent callback such as `on_plan_published`.
- The Command Center application MUST supply the local inventory service's safe `invalidate()` callback to the default managed job service.
- The callback MUST run only after planning has returned the expected output, complete schema-v2 artifacts have passed normal verification/publication checks, the successful result has a valid plan ID/namespace, and the durable job has transitioned successfully to `succeeded`.
- Failed, interrupted, rejected, or incomplete jobs MUST NOT issue successful-publication notification.
- Callback failure MUST be caught and safely logged by type only; it MUST NOT turn a valid completed plan/job into failure, alter artifacts, or expose untrusted data.
- The job service MUST NOT import or depend on FastAPI or the local inventory implementation.
- Ordinary CLI planning and external processes remain unchanged; external changes become visible through the bounded summary TTL.

## Acceptance criteria

1. Successful managed publication invokes invalidation once after durable success and makes the new plan immediately discoverable.
2. Failed/interrupted/incomplete planning does not announce successful publication.
3. A raising callback leaves the verified artifacts and succeeded job valid.
4. Existing one-active, lifecycle, durability, descriptor, publication, interruption, shutdown, and source/provider boundaries remain unchanged.

## Exclusions

No cross-process coordination, filesystem watcher, callback persistence/replay, job retry/cancellation, apply/cache authority, or dependency from jobs to FastAPI.
