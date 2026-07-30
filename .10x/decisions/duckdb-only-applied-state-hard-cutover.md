Status: active
Created: 2026-07-18
Updated: 2026-07-18
Amended-By: .10x/specs/focused-buoy-boundary.md

# DuckDB-Only Applied-State Hard Cutover

## Focused-boundary amendment

This record remains active only for Buoy's local DuckDB applied-state
authority, migration safety, locking, and content-apply ordering. Any clause
requiring pending catalog state, catalog recovery, or a post-commit remote
catalog write is superseded. Focused Buoy writes one content namespace and its
local applied state only.

## Context

Buoy replaced its JSON applied-state ledger with a compact per-namespace DuckDB ledger. The current source still recognizes `last-applied.json` and contains migration/deletion behavior. While shaping interactive apply confirmation, that compatibility path created mutation and failure-ordering complexity unrelated to the intended command flow.

The operator explicitly requires a hard cutover for JSON applied state only. Unrelated compatibility surfaces—including the legacy CLI alias, old environment-variable aliases, state-root fallback, old-plan compatibility, and retained command flags—remain governed by their existing records.

## Decision

DuckDB is the only active applied-state format. Buoy MUST NOT discover, read, parse, validate, import, migrate, archive, delete, or otherwise act on `last-applied.json` or prior `legacy-json/` applied-state artifacts.

If obsolete JSON applied-state files remain on disk, Buoy MUST ignore them. Their presence MUST NOT change planning, preflight, confirmation, apply, locking, output, or cleanup behavior. Buoy uses normal first-apply semantics only when `state.duckdb` is absent or is a valid initialized empty ledger. An unreadable, corrupt, schema-incompatible, or identity-invalid DuckDB ledger retains the existing fail-closed behavior.

Each `(site_id, namespace)` continues to own one embedded `state.duckdb`, one current row ledger, indefinitely retained lightweight apply summaries, and a non-blocking same-namespace apply lock. Different namespaces may apply concurrently. Only successful confirmed content-namespace upsert/delete work commits current rows and an apply summary atomically to DuckDB. Remote catalog registration occurs afterward and retains the partial-success and pending-recovery contract in `.10x/specs/approved-apply-remote-catalog-registration.md`.

## Alternatives considered

- **Migrate and delete obsolete JSON before remote work:** rejected because compatibility migration adds destructive ordering and failure semantics the operator no longer wants.
- **Delete obsolete JSON after successful apply:** rejected because it still requires product code to recognize and manage the retired format.
- **Fail when obsolete JSON exists:** rejected because it lets a retired file block otherwise valid DuckDB-only operation.
- **Import JSON rows:** rejected because JSON is no longer an active state authority and importing it could suppress required upserts.

## Consequences

- Source, tests, and active documentation must remove JSON applied-state recognition and migration contracts.
- Existing obsolete files remain user-owned inert files; Buoy neither cleans them up nor warns about them.
- A namespace with no `state.duckdb`, or with a valid initialized empty ledger, is a first apply even when obsolete JSON is present; invalid DuckDB state still fails closed.
- This decision does not remove `.turbo-search` state-root fallback or any non-applied-state compatibility behavior.
- The existing embedded DuckDB storage, compact retention, locking, and post-remote-success commit contracts remain unchanged.

## Supersedes

`.10x/decisions/superseded/duckdb-applied-state-concurrency-and-retention.md`
