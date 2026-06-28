Status: open
Created: 2026-06-20
Updated: 2026-06-20
Parent: .loom/tickets/2026-06-20-minimize-turbopuffer-rag-cost-plan.md
Depends-On: .loom/evidence/2026-06-20-turbopuffer-billing-cost-signal.md, .loom/knowledge/turbopuffer-cost-model.md

# Turbopuffer cost audit and estimator

## Scope

Build a local-only understanding of the current turbopuffer cost drivers and implement or document a repeatable cost-estimation workflow.

In scope:

- Analyze current schema in `src/turbo_search/indexer.py` and retrieval attributes in `src/turbo_search/retriever.py`.
- Estimate logical bytes for current rows using local corpus/chunks only.
- Compare current MVP shape against cheaper alternatives:
  - existing schema with metadata filterability disabled;
  - no full `content` returned from turbopuffer;
  - local chunk store plus turbopuffer vector-only;
  - compact single `search_text` turbopuffer BM25;
  - larger chunks/fewer rows;
  - possible i8 vector storage if feasible.
- Estimate write batch sizes needed to approach the documented `3.2MB` write-discount knee.
- Produce evidence explaining top cost drivers.

Out of scope:

- Live turbopuffer queries.
- Live turbopuffer writes.
- Namespace deletion.
- Credential access.

## Acceptance criteria

- A command or documented script can compute current local chunk/row logical sizes without credentials.
- The audit records estimated storage/write/returned-byte impact for at least three alternate designs.
- The audit identifies which attributes are indexed/filterable today and which can be removed or made unindexed.
- The audit recommends one or two cheapest viable designs for implementation.
- Unit tests cover any estimator code that is added.
- Evidence is recorded under `.loom/evidence/` and references this ticket.

## Progress and notes

- 2026-06-20: Ticket opened only. No live calls made.

## Blockers

- None for local audit.
