Status: done
Created: 2026-06-20
Updated: 2026-06-20
Parent: .loom/tickets/2026-06-20-turbopuffer-jellyfish-rag-plan.md
Depends-On: .loom/tickets/2026-06-20-python-prototype-scaffold.md, .loom/tickets/2026-06-20-proton-pass-turbopuffer-config.md, .loom/specs/turbopuffer-jellyfish-rag.md, .loom/research/2026-06-20-turbopuffer-markdown-rag-research.md, .loom/evidence/2026-06-20-jellyfish-site-docs-inventory.md, .loom/decisions/turbopuffer-jellyfish-rag-baseline.md

# Implement Jellyfish Markdown indexer

## Scope

Implement the pipeline that reads `jellyfish-site-docs/`, chunks pages, embeds chunks, and writes them to turbopuffer.

In scope:

- Recursive Markdown discovery.
- YAML frontmatter parsing for `url`, `title`, and future metadata if present.
- Content normalization to reduce repeated site chrome/boilerplate.
- Markdown-aware chunking with title/heading context and overlap.
- Deterministic chunk ID generation.
- Local BGE embeddings with `BAAI/bge-small-en-v1.5` unless user chooses otherwise.
- Turbopuffer batched upserts with schema for vector + BM25 + citation/debug attributes.
- Dry-run mode that reports files/chunks without writing.
- Index summary output: files seen, files skipped, chunks generated, rows written, errors.

Out of scope:

- Answer synthesis.
- Production continuous sync.
- Proprietary embedding providers.
- Reranking.

## Acceptance criteria

- Dry run can process all 1124 observed Markdown files and report a chunk count.
- Real run can write chunks to the configured namespace using `TURBOPUFFER_API_KEY` without exposing the key.
- Namespace schema enables ANN on `vector` and full-text search on `content`, `title`, and `section_path`.
- Chunk rows include citation fields `title`, `url`, `section_path`, and local `path`.
- Re-running the indexer is deterministic and does not create duplicate logical chunks.
- The indexer handles empty/malformed files gracefully and reports them.

## Implementation notes

Recommended row attributes:

- `id`
- `vector`
- `content`
- `title`
- `url`
- `path`
- `section_path`
- `chunk_index`
- `doc_kind`
- `tags`
- `source_hash`

Start with approximately 300-token chunks and two-sentence overlap, respecting Markdown headings and avoiding splits inside obvious blocks where practical.

## Progress and notes

- 2026-06-20: Ticket created only. No indexing run. No turbopuffer writes.
- 2026-06-20: Baseline decisions resolved: Python/uv + BGE, region `gcp-us-central1`, namespace `jellyfish-site-docs-v1`.
- 2026-06-20: Activated for execution under `/loom-driver` after config and scaffold tickets completed.
- 2026-06-20: Implemented Markdown discovery, frontmatter parsing, conservative chrome normalization, heading-aware chunking, deterministic chunk IDs, doc kind/tags, row construction, local BGE write-mode embedding, and batched turbopuffer upserts behind explicit `--write`.
- 2026-06-20: Validated unit tests, syntax compilation, small dry-run, and full-corpus dry-run over all 1124 Markdown files. Full dry-run generated 12721 chunks, skipped 1 empty file, reported 0 file errors, wrote 0 rows, and made 0 API calls. Evidence: `.loom/evidence/2026-06-20-jellyfish-markdown-indexer-validation.md`.
- 2026-06-20: Ticket intentionally remained active after dry-run implementation because live turbopuffer writes/schema/row-count validation had not yet been run.
- 2026-06-20: Ran approved live write with the turbopuffer API key retrieved from Proton Pass into shell memory only. Target: `TURBOPUFFER_REGION=gcp-us-central1`, `TURBOPUFFER_NAMESPACE=jellyfish-site-docs-v1`, batch size 128. Live run processed 1124 discovered Markdown files, skipped 1 empty file, generated 12721 chunks, wrote 12721 rows, and reported 0 file errors.
- 2026-06-20: Verified target namespace with non-secret turbopuffer SDK calls. Aggregate row count returned 12721 rows, matching `rows_written`; schema confirmed ANN on `vector` and full-text search on `content`, `title`, and `section_path`. Evidence: `.loom/evidence/2026-06-20-jellyfish-live-indexing.md`.

## Blockers

- None.
