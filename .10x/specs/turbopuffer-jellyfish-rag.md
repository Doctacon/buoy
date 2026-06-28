Status: active
Created: 2026-06-20
Updated: 2026-06-20

# Turbopuffer-backed Jellyfish docs RAG

## Purpose and scope

This spec describes the desired behavior for a local prototype that indexes `jellyfish-site-docs/` into turbopuffer and lets the agent answer user questions using turbopuffer hybrid retrieval.

In scope:

- Local parsing of Markdown site-page exports.
- Chunk-level indexing into a turbopuffer namespace.
- Local open-source embeddings for the vector side of search.
- BM25 full-text search over chunk text and metadata fields.
- Hybrid retrieval using turbopuffer multi-query + RRF.
- Agent-facing retrieval output with enough context and citations to answer questions.
- Smoke/eval commands to confirm retrieval is working.

Out of scope for the first prototype:

- A web UI.
- Production auth/session management beyond environment variables.
- Continuous sync from the live Jellyfish website.
- Proprietary embedding or reranking services unless the user explicitly chooses them later.
- Storing the turbopuffer API key on disk.

## Behavior

### Ingestion

Given a corpus directory of Markdown files, the system should:

1. Discover `*.md` files recursively.
2. Parse YAML frontmatter for at least `url` and `title` when present.
3. Normalize page body text enough to reduce repeated scraped site chrome while preserving actual content.
4. Chunk Markdown with heading/section awareness, targeting roughly 300 tokens per chunk with overlap as a starting point.
5. Add title and heading path context to the text used for embeddings.
6. Generate deterministic chunk IDs so repeated indexing is stable.
7. Embed chunks locally with an open-source model.
8. Upsert chunks into a configured turbopuffer namespace in batches.
9. Write schema enabling:
   - ANN vector search over `vector`.
   - BM25 full-text search over `content`, `title`, and `section_path`.
   - Filtering/debug attributes such as `url`, `path`, `doc_kind`, and `source_hash`.

### Retrieval

Given a user question, the system should:

1. Embed the question with the same local model used for indexing.
2. Run turbopuffer hybrid retrieval with one ANN query and one BM25 query in the same multi-query request.
3. Fuse candidates with turbopuffer RRF if supported by the installed SDK; otherwise use a local RRF fallback.
4. Return top chunks with only needed attributes: `title`, `url`, `section_path`, `content`, `path`, and scores.
5. Include enough raw retrieved text for the agent to answer accurately.
6. Avoid returning vectors unless explicitly requested.

### Answering

When the agent answers a question using this retrieval layer, it should:

1. Run the retrieval command first.
2. Base claims on retrieved chunks.
3. Cite the source page title and URL for material claims.
4. Say when retrieved context is insufficient instead of inventing an answer.
5. Prefer concise synthesis over copying long source text.

## Acceptance criteria

- A fresh checkout can install dependencies with a documented command.
- The indexer can run against `jellyfish-site-docs/` and report counts for files, chunks, writes, skipped/empty files, and errors.
- The turbopuffer namespace metadata confirms the expected schema and row count after indexing.
- A retrieval command returns relevant chunks for at least 5 smoke queries, with URL/title citations.
- Hybrid search uses both vector and BM25 subqueries and fuses them with RRF.
- The API key is read from environment variables at runtime and is never committed or written to project files.
- Documentation explains how the agent should use the retrieval command before answering questions.

## Constraints

- Follow the project open-source-first principle: local open-source embeddings by default; no extra proprietary services for embeddings/reranking in the MVP.
- Use `uv` for Python dependency management unless the user chooses a different implementation language.
- Keep implementation small and inspectable; this is a turbopuffer evaluation prototype, not a production search service.
- Do not execute credential retrieval, indexing, or turbopuffer writes until the user approves.

## Resolved defaults

Recorded in `.loom/decisions/turbopuffer-jellyfish-rag-baseline.md`:

- Implementation language/tooling: Python with `uv`.
- Embeddings: local `BAAI/bge-small-en-v1.5` via `sentence-transformers`.
- Turbopuffer region: `gcp-us-central1`.
- Turbopuffer namespace: `jellyfish-site-docs-v1`.
- Proton Pass lookup: search accessible items for the turbopuffer credential when execution is approved.
- Reranker: defer; MVP should use hybrid ANN + BM25 + RRF first.
