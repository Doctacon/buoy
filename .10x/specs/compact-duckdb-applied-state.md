Status: active
Created: 2026-07-12
Updated: 2026-08-13
Amended-By: .10x/specs/automatic-multi-corpus-retrieval.md

# Compact DuckDB Applied State

## Bounded-retrieval amendment

This specification remains active for the exact local applied-state schema,
incremental diff baseline, apply-run history, locking, and atomic state commit.
The focused boundary's general removal of catalog registration is superseded
only for the post-commit routing-card behavior in
`.10x/specs/automatic-multi-corpus-retrieval.md`. Command Center inventory,
evidence streaming/summary APIs, and other cross-namespace consumers remain
outside the focused package.

## Purpose and scope

Define Buoy's compact, per-namespace embedded DuckDB applied-state ledger. This specification governs local incremental state, format authority, history retention, and concurrent confirmed applies.

It does not itself store pending plans, change crawl/chunk semantics, create or delete Turbopuffer namespaces, add Quack, or enable simultaneous applies to one namespace. Compact changed-only pending artifacts and exact applied-state baseline binding are governed by `.10x/specs/compact-delta-plan-artifacts.md`.

## Storage model

For `(site_id, namespace)`, active state MUST live at:

```text
<state-root>/state/<site-id>/<namespace>/state.duckdb
```

The database MUST contain:

- a current applied-row ledger sufficient to reproduce existing diff semantics: row ID, canonical URL, page hash, chunk hash, embedding-text hash, status, plan ID, and applied timestamp;
- lightweight `apply_runs` summaries containing at least apply ID, plan ID, timestamp, upsert/delete counts, and retained-stale count;
- schema metadata/versioning.

The backend MUST NOT write full per-apply copies of the row ledger. Apply summaries are retained indefinitely.

## Format authority and hard cutover

DuckDB is the only active applied-state format. The implementation MUST NOT discover, read, parse, validate, import, migrate, archive, delete, warn about, or otherwise act on `last-applied.json` or prior `legacy-json/` applied-state artifacts.

Obsolete JSON applied-state files are inert user-owned files. Their presence or contents MUST NOT affect plan, preflight, confirmation, apply, locking, output, or cleanup. The namespace MUST use normal first-apply behavior only when `state.duckdb` is absent or is a valid initialized empty ledger. An unreadable, corrupt, schema-incompatible, or identity-invalid DuckDB ledger MUST retain the existing fail-closed behavior.

## Plan behavior

`buoy plan` MUST read the DuckDB current ledger for the matching state location when it exists. When no DuckDB state exists, it MUST return first-apply semantics without creating a database. It MUST bind the exact canonical applied-row/metadata projection plus database-presence bit into the compact delta plan, and apply MUST fail and require replanning if that baseline changes, as specified by `.10x/specs/compact-delta-plan-artifacts.md`. Apply-run summaries are not part of this incremental projection; every successful apply already changes bound top-level lineage.

Given equivalent active rows, the DuckDB-backed diff MUST preserve the existing classifications: unchanged, new, changed, retained stale, and stale.

## Approved apply behavior

After apply confirmation and before embeddings, pending-state mutation, or remote writes, confirmed apply MUST attempt to acquire a non-blocking lock scoped to that `(site_id, namespace)`.

- If the lock is already held, the command MUST fail with a clear busy error and MUST perform no Turbopuffer mutation or local-state update.
- Applies for different namespace paths MUST be able to proceed concurrently.
- After all confirmed content-namespace upsert/delete operations succeed, the implementation MUST atomically update the local current ledger and append one apply summary in one DuckDB transaction.
- If content-namespace Turbopuffer work fails, the local active ledger and apply-run history MUST remain unchanged.
- Bounded routing-card registration occurs after the DuckDB commit and retains the explicit partial-success contract in `.10x/specs/automatic-multi-corpus-retrieval.md`; it creates no pending catalog state, and this specification MUST NOT move the ledger commit after card registration.

The local transaction does not include Turbopuffer. A crash after a remote write and before local commit may result in safe repeat upserts on the next explicitly confirmed apply.

## Constraints

- `duckdb` MUST be an open-source local dependency.
- The default backend MUST remain embedded DuckDB; no service, listener, token, or Quack extension is in scope.
- Existing plan/apply safety gates remain: `plan`, `apply --dry-run`, and interactive pre-prompt work are local-only; remote mutation requires either interactive `y`/`yes` confirmation or `--approve`, plus `TURBOPUFFER_API_KEY`.
- State paths remain gitignored; obsolete JSON files receive no special runtime handling.

## Acceptance criteria

1. When `state.duckdb` is absent or is a valid initialized empty ledger, plan and apply use identical first-apply behavior whether obsolete JSON applied-state files are present or absent; all such files remain byte-for-byte unchanged. Unreadable, corrupt, schema-incompatible, and identity-invalid DuckDB fixtures retain fail-closed behavior.
2. Equivalent DuckDB active data produces the established unchanged, new, changed, retained-stale, and stale classifications.
3. A confirmed apply records current rows and one summary only after mocked content-namespace upsert/delete success; a mocked content-namespace failure leaves the database unchanged. A subsequent routing-card failure preserves the committed DuckDB state and reports truthful partial success with a reviewed repair command under `.10x/specs/automatic-multi-corpus-retrieval.md`.
4. Two applies to different namespaces can acquire separate locks; a second apply to one locked namespace fails before the writer is called.
5. The state backend creates no full row-history snapshots and exposes an inspectable persistent DuckDB file.
