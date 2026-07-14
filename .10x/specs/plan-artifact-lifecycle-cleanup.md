Status: active
Created: 2026-07-12
Updated: 2026-07-12

# Plan Artifact Lifecycle Cleanup

## Purpose and scope

Define prospective automatic cleanup for Buoy plan artifact directories. It covers artifacts created under the chosen `--out-dir` or default plan path.

It does not delete historical artifact backlogs, active DuckDB state, legacy-state cleanup, remote Turbopuffer data, or user-managed copies outside the plan artifact directory.

## Artifact lifecycle

A newly completed plan directory is **pending** until one of these events:

- its `apply --approve` succeeds; or
- a newer plan for the same namespace successfully writes its own review artifacts.

A pending plan MUST remain available for review, apply preflight, retry after an apply failure, and diagnostics.

## Successful approved apply

Given an approved apply whose remote work and local DuckDB state transaction both succeed, the command MUST remove the exact plan directory it used before reporting successful completion.

Given remote failure, local-state failure, lock contention, preflight-only execution, or any other unsuccessful apply, the command MUST retain the plan directory.

## Superseded plans

After a new plan successfully writes its artifacts, the command MUST remove older plan directories for the same namespace. It MUST not remove the newly written directory, plans for other namespaces, or a directory whose namespace cannot be verified from its `plan.json`.

## Failure handling

Plan cleanup is local-only. A cleanup failure after a successful apply MUST NOT alter remote rows, local DuckDB state, or the successful status of that apply. It MUST emit a clear warning containing the retained path and leave the path available for later explicit reconciliation.

## Constraints

- Automatic cleanup applies only to future lifecycle events; historical artifacts require a separate explicit reconciliation/GC workflow.
- The command MUST not follow symlinks outside the selected artifact root.
- The command MUST not delete `.buoy/state/**` or legacy `.turbo-search/state/**`, credentials, user-managed copies, or Turbopuffer data.
- No additional confirmation flag is required for these ratified automatic lifecycle events.

## Acceptance criteria

1. A successful approved apply removes exactly its plan directory after local-state commit; failed/contended/preflight applies retain it.
2. A successful new plan removes only older verified plan directories with the same namespace.
3. Plans for other namespaces and malformed/unverifiable plan directories remain untouched.
4. Cleanup exceptions leave the successful apply result intact and report the retained path.
5. Tests cover all lifecycle cases without live Turbopuffer calls.
