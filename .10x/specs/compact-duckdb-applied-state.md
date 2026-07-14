Status: active
Created: 2026-07-12
Updated: 2026-07-12

# Compact DuckDB Applied State

## Purpose and scope

Replace the JSON applied-state ledger for Buoy with a compact, per-namespace embedded DuckDB ledger. This specification governs local incremental state, migration, history retention, and concurrent approved applies.

It does not compact plan artifacts, change crawl/chunk semantics, create or delete Turbopuffer namespaces, add Quack, or enable simultaneous applies to one namespace.

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

## Migration

Given a legacy `last-applied.json` for a state location, the implementation MUST delete it and MUST initialize the matching DuckDB ledger empty. It MUST NOT archive or import legacy rows into active state.

This migration policy is intentional for the current Turbopuffer account, which has no matching remote namespaces. The next plan/apply MUST therefore identify every desired row as needing an upsert.

Migration MUST NOT contact Turbopuffer or load embeddings. Existing `legacy-json/` artifacts from the superseded archive behavior are not active state and are eligible for deletion.

## Plan behavior

`buoy plan` MUST read the DuckDB current ledger for the matching state location when it exists. When no DuckDB state exists, it MUST return first-apply semantics without creating a database.

Given equivalent active rows, the DuckDB-backed diff MUST preserve the existing classifications: unchanged, new, changed, retained stale, and stale.

## Approved apply behavior

Before an approved apply performs embeddings or remote writes, it MUST attempt to acquire a non-blocking lock scoped to that `(site_id, namespace)`.

- If the lock is already held, the command MUST fail with a clear busy error and MUST perform no Turbopuffer mutation or local-state update.
- Applies for different namespace paths MUST be able to proceed concurrently.
- After all approved Turbopuffer operations succeed, the implementation MUST atomically update the local current ledger and append one apply summary in one DuckDB transaction.
- If Turbopuffer work fails, the local active ledger and apply-run history MUST remain unchanged.

The local transaction does not include Turbopuffer. A crash after a remote write and before local commit may result in safe repeat upserts on the next explicitly approved apply.

## Constraints

- `duckdb` MUST be an open-source local dependency.
- The default backend MUST remain embedded DuckDB; no service, listener, token, or Quack extension is in scope.
- Existing plan/apply safety gates remain: `plan` and preflight are local-only; remote mutation requires `--approve` and `TURBOPUFFER_API_KEY`.
- State paths and any legacy state paths remain gitignored.

## Acceptance criteria

1. A legacy JSON state is deleted, the resulting DuckDB state is empty, and the next plan reports first-apply/upsert behavior without a Turbopuffer call.
2. Equivalent active data produces the same diff classification and counts as the existing JSON backend tests.
3. An approved apply records current rows and one summary only after mocked remote success; a mocked remote failure leaves the database unchanged.
4. Two applies to different namespaces can acquire separate locks; a second apply to one locked namespace fails before the writer is called.
5. The state backend creates no full row-history snapshots and exposes an inspectable persistent DuckDB file.
