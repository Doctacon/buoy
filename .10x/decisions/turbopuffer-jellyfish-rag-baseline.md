Status: active
Created: 2026-06-20
Updated: 2026-06-20

# Baseline for Jellyfish docs turbopuffer RAG prototype

## Context

The user wants to test a new turbopuffer subscription on `jellyfish-site-docs/`, a local corpus of exported Jellyfish site pages as Markdown. The project has an open-source-first principle, so surrounding RAG components should avoid proprietary embedding/reranking services unless explicitly chosen later.

Research in `.loom/research/2026-06-20-turbopuffer-markdown-rag-research.md` found that turbopuffer's Python SDK examples are first-class, local BGE embeddings are used in turbopuffer docs, and hybrid retrieval should use multi-query with ANN + BM25 and RRF.

The user answered the planning questions on 2026-06-20.

## Decision

Use the following defaults for the first implementation pass:

- Turbopuffer region: `gcp-us-central1`
- Turbopuffer namespace: `jellyfish-site-docs-v1`
- Credential discovery: search accessible Proton Pass items for the turbopuffer API key when execution is approved, without exposing the secret in Loom records or project files.
- Implementation stack: Python with `uv`, turbopuffer Python SDK, and local `BAAI/bge-small-en-v1.5` embeddings via `sentence-transformers`.

## Alternatives considered

- **Subscription-specific region**: Deferred because the user accepted `gcp-us-central1` as the baseline.
- **Timestamped test namespace**: Rejected for the baseline because a stable versioned namespace is easier for repeated queries and deterministic reindexing.
- **User-provided Proton Pass item title**: Rejected for now because the user approved item search.
- **Python dry-run first**: Rejected as the primary baseline; dry-run mode should still exist, but the implementation can assume local BGE embeddings.
- **TypeScript baseline**: Rejected because Python has simpler local embedding and turbopuffer examples for this prototype.

## Consequences

- Tickets should assume Python/uv and local model download are acceptable.
- Indexing and retrieval commands should default to `gcp-us-central1` and `jellyfish-site-docs-v1`, while still allowing environment variable overrides.
- Proton Pass access remains forbidden until the user explicitly approves execution; when approved, item search is permitted.
- No additional proprietary reranking or embedding services should be introduced in the MVP.
