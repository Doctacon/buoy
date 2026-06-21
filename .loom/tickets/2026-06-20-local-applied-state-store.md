Status: done
Created: 2026-06-20
Updated: 2026-06-20
Parent: .loom/tickets/2026-06-20-generic-site-rag-incremental-plan-apply.md
Depends-On: .loom/specs/generic-site-rag-incremental-plan-apply.md, .loom/decisions/generic-site-rag-incremental-state.md, .loom/research/2026-06-20-incremental-rag-state-backend-research.md

# Local Applied State Store

## Scope

Implement the local applied-state backend used for incremental generic site plans and applies.

In scope:

- Default state path calculation:
  - `.turbo-search/state/<site-id>/<namespace>/last-applied.json`
  - `.turbo-search/state/<site-id>/<namespace>/history/<apply-id>.json`
- Load state when it exists.
- Return empty/first-apply state when it does not exist.
- Validate schema version, site ID, namespace, and base URL compatibility.
- Atomic write behavior for `last-applied.json`.
- History writes for successful applies.
- Representation of active rows, retained-stale rows, and deleted rows if needed.
- Tests using temporary directories.

Out of scope:

- Remote/shared state backend.
- Live turbopuffer inspection.
- State locking across multiple concurrent processes unless a trivial local lock naturally falls out of implementation.

## Implementation notes

State is the diff baseline, not the reviewed plan artifact. It should be separate from `artifacts/site-crawls/...`.

The MVP may keep state out of git by documenting `.turbo-search/` as generated local state. If `.gitignore` does not already exclude it, a later docs/validation ticket should address that.

If an apply fails after live work starts, this ticket's primitives should make it possible to avoid overwriting `last-applied.json` as if the apply fully succeeded.

## Acceptance criteria

- Missing state loads as an explicit first-apply/empty state.
- Existing state loads and validates site ID/namespace/base URL compatibility.
- Invalid schema version or conflicting state fails clearly.
- Saving state writes history and updates `last-applied.json` atomically.
- Retained stale rows can be represented and loaded again.
- Tests cover missing state, valid state, invalid state, atomic save, and retained-stale persistence.
- No credentials, embeddings, or turbopuffer calls are used.

## Progress and notes

- 2026-06-20: Ticket opened after choosing local applied-state manifest first.
- 2026-06-20: Implemented `src/turbo_search/applied_state.py` with typed local state rows/state objects, default path helpers, missing-state first-apply loading, schema/site/namespace/base URL validation, active/retained-stale/deleted row statuses, history writes, and atomic `last-applied.json` replacement.
- 2026-06-20: Added `.turbo-search/` to `.gitignore` so local applied state is not committed by default.
- 2026-06-20: Added `tests/test_applied_state.py` covering default paths, missing state, valid load/save, invalid schema, conflicting state, invalid row status, retained-stale/deleted persistence, and atomic save behavior using temporary directories.
- 2026-06-20: Validation passed. Evidence: `.loom/evidence/2026-06-20-local-applied-state-store-validation.md`.

## Blockers

None.
