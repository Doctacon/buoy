Status: active
Created: 2026-07-12
Updated: 2026-08-17
Amended-By: .10x/specs/automatic-routing-after-apply.md, .10x/specs/user-global-buoy-home-defaults.md

# Plan Artifact Lifecycle Cleanup

## User-global managed-root amendment

The user-global-home specification adds one narrow exception to the historical
whole-state-root deletion guard: an exact verified plan strictly below the
canonical `~/.buoy/artifacts/site-crawls/` root retains this specification's
success-only cleanup lifecycle. The application-home root,
`~/.buoy/state/**`, every other home subtree, noncanonical state-root targets,
and malformed/replaced/symlinked artifacts remain protected.

The cleanup threat boundary matches the existing portable implementation:
no-follow descriptor binding, exact plan-directory identity, a private random
quarantine name, re-verification, and only a platform-reported symlink-safe
recursive remover. This covers cooperative concurrent Buoy activity plus
ancestor, symlink, and whole-plan replacement before final removal begins. It
does not claim a portable compare-and-unlink guarantee against an actively
malicious same-UID process that discovers and mutates child names inside the
private random quarantine after final binding; such a process already has
direct authority to mutate this user's files.

## Purpose and scope

Define prospective automatic cleanup for schema-v3/delta-v2 Buoy plan artifact
directories. It covers valid schema-v3 artifacts created under the chosen
`--out-dir` or default plan path.

It does not delete schema-v1/v2 legacy artifact directories, historical
artifact backlogs, active DuckDB state, obsolete JSON applied-state files,
remote Turbopuffer data, or user-managed copies outside the plan artifact
directory.

## Artifact lifecycle

A newly completed plan directory is **pending** until one of these events:

- its confirmed apply (interactive `y`/`yes` or `--approve`) fully succeeds
  through content, local state, and catalog-card registration; or
- a newer plan for the same namespace successfully writes its own review artifacts.

A pending plan MUST remain available for review, apply preflight, retry after an apply failure, and diagnostics.

## Successful approved apply

Given an approved apply whose content work, local DuckDB state transaction, and
catalog-card registration all succeed, the command MUST remove the exact plan
directory it used before reporting successful completion.

Given content failure, local-state failure, catalog partial success, lock
contention, `--dry-run`, interactive cancellation, or any other unsuccessful
apply, the command MUST retain the plan directory. A post-content catalog
partial retains the exact plan as authority for its emitted repair command even
though its baseline is no longer valid for ordinary apply.
`catalog repair-apply --inspect-current` is read-only and MUST NOT remove that
plan. Only a subsequently successful, fully verified bound repair may perform
the exact applied-plan cleanup.

## Superseded plans

After a new schema-v3 plan successfully writes its artifacts, the command MUST
fully verify each older schema-v3 candidate and remove only fully verified plan
directories for the same namespace. This includes a retained catalog-partial
plan once a newer baseline-bound plan replaces its repair path. It MUST not
remove the newly written directory, plans for other namespaces, schema-v1/v2
legacy directories, summary-qualified directories whose delta is corrupt or
unverifiable, or a directory whose namespace cannot be established safely.
Cleanup may open schema-v3/delta-v2 payloads solely for this destructive
verification.

## Failure handling

Plan cleanup is local-only. A cleanup failure after a successful apply MUST NOT alter remote rows, local DuckDB state, or the successful status of that apply. It MUST emit a clear warning containing the retained path and leave the path available for later explicit reconciliation.

## Constraints

- Automatic cleanup applies only to future schema-v3 lifecycle events;
  schema-v1/v2 and other historical artifacts remain inert user-owned files and
  no reconciliation/GC workflow is authorized by this specification.
- The command MUST not follow symlinks outside the selected artifact root.
- The command MUST not delete `.buoy/state/**` or legacy `.turbo-search/state/**`, credentials, user-managed copies, or Turbopuffer data.
- No additional confirmation flag is required for these ratified automatic lifecycle events.

## Acceptance criteria

1. A fully successful approved apply removes exactly its plan directory after
   content, local-state, and catalog-card commit; catalog-partial,
   failed/contended, and preflight applies retain it.
2. A successful new plan removes only older fully verified schema-v3 plan
   directories with the same namespace.
3. Plans for other namespaces, schema-v1/v2 directories, summary-qualified but
   payload-corrupt plans, and other malformed/unverifiable plan directories
   remain untouched.
4. Cleanup exceptions leave the successful apply result intact and report the retained path.
5. Tests cover all lifecycle cases without live Turbopuffer calls.
