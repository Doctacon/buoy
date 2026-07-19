Status: cancelled
Created: 2026-07-18
Updated: 2026-07-18
Parent: .10x/tickets/2026-07-18-repository-cleanup-plan.md
Depends-On: None

# Reconcile Website Exact-Chunk Deduplication — No Action

## Historical candidate

The dirty `thistle-site-test` worktree contains an untracked exact-chunk dedup specification, implementation, tests, evidence, and pass review built for the retired `turbo_search`/Qdrant/schema-v2/SQLite architecture. It grouped website chunks by exact content hash, chose a deterministic primary URL, stored citation aliases, extended applied-state equality, and required deletion handling for stale duplicate rows.

Exact paths and SHA-256 hashes are preserved in:

- `.10x/evidence/.storage/2026-07-18-thistle-qdrant-dead-end/dirty-path-inventory.tsv`;
- `.10x/evidence/.storage/2026-07-18-thistle-qdrant-dead-end/dirty-content-manifest-before.txt`;
- `.10x/research/2026-07-18-thistle-qdrant-dead-end-disposition.md`.

Those records are historical provenance only. The old review establishes only that the old implementation matched the old contract; it is not evidence for current Buoy behavior.

## Cancellation and no-action rationale

The user explicitly ratified retirement of the old exact-chunk dedup implementation and directed that dedup behavior not be activated or ported. Current Turbopuffer row identity, DuckDB applied state, plan schema, stale-row lifecycle, and retrieval citation shape also differ from the historical implementation.

Accordingly:

- no current dedup specification is active or retained as a draft;
- no implementation ticket is executable or blocked awaiting a checkpoint;
- no alias field, payload hash, row-identity change, stale-deletion rule, citation change, metric, source, or test is ported;
- the historical implementation/evidence remains non-authoritative and may be deleted with the dirty worktree after this preservation PR is merged.

A future dedup request would be net-new shaping and must be ratified against then-current architecture; this cancelled record grants it no authority.

## Explicit exclusions

No source edit, test port, crawl, apply, retrieval, remote write/delete, or dirty-worktree mutation occurred.

## Progress and notes

- 2026-07-18: Prior worker drafted current-architecture semantics and a blocked reconciliation ticket.
- 2026-07-18: Final user direction retired the behavior. The draft spec was discarded and this ticket was cancelled with historical provenance preserved.
