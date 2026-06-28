Status: open
Created: 2026-06-20
Updated: 2026-06-20
Parent: .loom/tickets/2026-06-20-minimize-turbopuffer-rag-cost-plan.md
Depends-On: .loom/tickets/2026-06-20-cost-optimized-index-design.md, .loom/tickets/2026-06-20-cost-optimized-local-chunk-store.md

# Cost-optimized turbopuffer schema and retrieval

## Scope

Implement the minimized turbopuffer-side schema and retrieval behavior selected by the design ticket.

Likely in scope:

- Replace the MVP schema with a cost-first schema variant for a new namespace.
- Explicitly set `filterable: False` for every metadata field unless required.
- Remove `content` from turbopuffer rows, or make it local-only, depending on selected design.
- If BM25 remains in turbopuffer, use one compact `search_text` field rather than separate `content`, `title`, and `section_path` full-text indexes.
- Consider `[384]i8` vector support if selected by design; otherwise keep `[384]f16`.
- Reduce live retrieval defaults for cost-sensitive use.
- Ensure `include_attributes` returns only IDs and tiny metadata; hydrate content locally.
- Add write preflight output that estimates rows, logical bytes, and write batch sizes.
- Increase default live write batch sizing or add auto-batch sizing near the documented discount knee.

Out of scope:

- Running the live reindex.
- Deleting the old namespace.
- Credential access.

## Acceptance criteria

- Unit tests prove full `content` is not requested from turbopuffer by default.
- Unit tests prove generated schema has explicit filterability settings.
- Unit tests cover any i8/f16 vector type selection logic if added.
- Dry-run/preflight output shows estimated rows, bytes, and batch count.
- Retrieval still returns answer-ready hydrated hits using the local store.
- README/docs explain the difference between MVP namespace and cost-first namespace.

## Progress and notes

- 2026-06-20: Ticket opened only.

## Blockers

- Depends on selected target design and local chunk-store implementation.
