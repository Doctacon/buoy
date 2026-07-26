Status: active
Created: 2026-07-12
Updated: 2026-07-24

# Plan Artifact Lifecycle Cleanup

## Purpose and scope

Define prospective automatic cleanup for schema-v2 Buoy plan artifact directories. It covers valid schema-v2 artifacts created under the chosen `--out-dir` or default plan path.

It does not inspect or delete schema-v1/legacy artifact directories, historical artifact backlogs, active DuckDB state, obsolete JSON applied-state files, remote Turbopuffer data, or user-managed copies outside the plan artifact directory.

## Artifact lifecycle

A newly completed plan directory is **pending** until one of these events:

- its confirmed apply (interactive `y`/`yes` or `--approve`) succeeds; or
- a newer plan for the same namespace successfully writes its own review artifacts.

A pending plan MUST remain available for review, apply preflight, retry after an apply failure, and diagnostics.

## Successful approved apply

Given an approved apply whose remote work and local DuckDB state transaction both succeed, the command MUST remove the exact plan directory it used before reporting successful completion.

Given remote failure, local-state failure, lock contention, `--dry-run`, interactive cancellation, or any other unsuccessful apply, the command MUST retain the plan directory.

## Superseded plans

After a new schema-v2 plan successfully writes its artifacts, the command MUST fully verify each older schema-v2 candidate and remove only fully verified plan directories for the same namespace. It MUST not remove the newly written directory, plans for other namespaces, schema-v1/legacy directories, summary-qualified directories whose delta is corrupt or unverifiable, or a directory whose namespace cannot be established safely. Cleanup may open schema-v2 delta payloads solely for this destructive verification; Command Center inventory remains payload-independent.

## Failure handling

Plan cleanup is local-only. A cleanup failure after a successful apply MUST NOT alter remote rows, local DuckDB state, or the successful status of that apply. It MUST emit a clear warning containing the retained path and leave the path available for later explicit reconciliation.

## Constraints

- Automatic cleanup applies only to future schema-v2 lifecycle events; legacy/historical artifacts remain inert user-owned files and no reconciliation/GC workflow is authorized by this specification.
- The command MUST not follow symlinks outside the selected artifact root.
- The command MUST not delete `.buoy/state/**` or legacy `.turbo-search/state/**`, credentials, user-managed copies, or Turbopuffer data.
- No additional confirmation flag is required for these ratified automatic lifecycle events.

## Acceptance criteria

1. A successful approved apply removes exactly its plan directory after local-state commit; failed/contended/preflight applies retain it.
2. A successful new plan removes only older fully verified schema-v2 plan directories with the same namespace.
3. Plans for other namespaces, schema-v1 directories, summary-qualified but payload-corrupt plans, and other malformed/unverifiable plan directories remain untouched.
4. Cleanup exceptions leave the successful apply result intact and report the retained path.
5. Tests cover all lifecycle cases without live Turbopuffer calls.
