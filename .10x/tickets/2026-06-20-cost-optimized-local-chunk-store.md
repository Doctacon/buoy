Status: open
Created: 2026-06-20
Updated: 2026-06-20
Parent: .loom/tickets/2026-06-20-minimize-turbopuffer-rag-cost-plan.md
Depends-On: .loom/tickets/2026-06-20-cost-optimized-index-design.md

# Cost-optimized local chunk store

## Scope

Implement deterministic local content and citation hydration so live turbopuffer retrieval does not need to return full chunk content.

In scope:

- Add a local chunk-store artifact format, likely JSONL or SQLite, keyed by deterministic chunk ID.
- Store full `content`, `title`, `url`, `section_path`, `path`, `doc_kind`, and chunk metadata locally.
- Add CLI command(s) to build/validate the local store without credentials.
- Add lookup utilities so retrieval can hydrate final hits by ID.
- If local-first hybrid is selected, add local BM25/FTS over this store using open-source/local tooling.
- Add tests for deterministic IDs, lookup, missing IDs, and citation hydration.

Out of scope:

- Live turbopuffer writes or queries.
- Proprietary hosted search/reranking.

## Acceptance criteria

- The local store can be built from `jellyfish-site-docs/` without credentials or network calls.
- Retrieval code can hydrate content for a list of turbopuffer-returned IDs.
- Turbopuffer retrieval attributes no longer need to include full `content` for answer generation.
- Tests pass and cover the store builder and hydration path.
- Evidence records local build size, row count, and representative hydrated citation output.

## Progress and notes

- 2026-06-20: Ticket opened only.

## Blockers

- Target architecture must be selected first.
