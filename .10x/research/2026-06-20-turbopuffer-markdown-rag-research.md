Status: done
Created: 2026-06-20
Updated: 2026-06-20

# Turbopuffer Markdown RAG research for Jellyfish site docs

## Question

How should this repository test turbopuffer on `jellyfish-site-docs/` so that the agent can answer user questions using turbopuffer hybrid retrieval over the exported Markdown pages?

## Sources and methods

Project/corpus inspection:

- `.loom/evidence/2026-06-20-jellyfish-site-docs-inventory.md`
- Local directory: `jellyfish-site-docs/`

Turbopuffer documentation consulted on 2026-06-20:

- Documentation index: https://turbopuffer.com/llms.txt
- Hybrid search: https://turbopuffer.com/docs/hybrid.md
- Chunking: https://turbopuffer.com/docs/chunking.md
- Query API: https://turbopuffer.com/docs/query.md
- Write API: https://turbopuffer.com/docs/write.md
- Full-text search: https://turbopuffer.com/docs/fts.md
- Ingestion: https://turbopuffer.com/docs/ingestion.md
- Limits: https://turbopuffer.com/docs/limits.md
- Performance: https://turbopuffer.com/docs/performance.md
- Regions: https://turbopuffer.com/docs/regions.md

Open-source reranker/chunking research:

- BAAI BGE reranker docs/model cards: https://huggingface.co/BAAI/bge-reranker-base and https://github.com/FlagOpen/FlagEmbedding
- Qwen3 reranker model family: https://qwenlm.github.io/blog/qwen3-embedding/
- Chonkie open-source chunking library: https://github.com/chonkie-inc/chonkie and https://docs.chonkie.ai/common/open-source
- LlamaIndex Markdown parser references: https://developers.llamaindex.ai/python/framework-api-reference/node_parsers/markdown/ and https://github.com/run-llama/llama_index/blob/main/llama-index-core/llama_index/core/node_parser/file/markdown.py
- `structchunk` Markdown chunker: https://pypi.org/project/structchunk/

## Findings

### Corpus shape

`jellyfish-site-docs/` contains 1124 Markdown files and is about 12 MB. Files are exported site pages with YAML frontmatter carrying at least `url` and `title` on inspected samples. Body text may contain repeated website chrome/boilerplate, so ingestion should normalize content before chunking.

### Turbopuffer primitives relevant to this prototype

- Namespaces are isolated document spaces and are implicitly created on first write. Namespace names must match `[A-Za-z0-9-_.]{1,128}`.
- Documents/rows have an `id` plus typed attributes. IDs can be unsigned 64-bit integers, UUIDs, or strings up to 64 bytes.
- Vector attributes can be `f32`, `f16`, or `i8`; smaller vector precision can improve performance/cost. A namespace can currently have up to 2 vector columns fixed at creation.
- Full-text/BM25 search is enabled per string or `[]string` attribute in schema with `full_text_search`.
- Large attributes that are not filtered/sorted should be marked `filterable: false` to avoid unnecessary indexing cost. This is relevant for chunk `content`, while still enabling `full_text_search` for BM25.
- Write requests can be batched up to 512 MB. Batching improves throughput and can reduce write cost.
- Query `include_attributes` should return only needed fields for performance.
- Multi-query supports up to 16 subqueries per request and is intended for hybrid workflows.
- Query docs currently support server-side RRF via `rerank_by=("RRF",)` on `ns.multi_query(...)`; hybrid guide also shows client-side RRF. The implementation should prefer built-in RRF and keep a small fallback if SDK response shape differs.
- `limit.total` max is 10,000. First-stage retrieval should usually pull roughly 100-1000 candidates before any second-stage reranker.
- Strong consistency is the default. Eventual consistency can increase throughput but is unnecessary for a small local test unless bulk ingest hits write/indexing pressure.

### Chunking guidance

Turbopuffer's chunking guide says chunking is the ceiling for recall. Key guidance:

- Do not make chunks too long because embeddings compress many tokens lossy.
- Do not make chunks too short because standalone context is lost.
- Respect obvious document boundaries; Markdown should be split with a Markdown-aware splitter.
- For traditional embedding models, start around 300-token chunks with about two-sentence overlap and iterate based on eval results.
- Contextual embedding models can improve recall but add provider/model complexity. For this open-source-first prototype, start with local non-contextual embeddings and good Markdown chunking.

### Embeddings and reranking under the project's open-source-first rule

The project instructions require open-source/self-hosted choices before proprietary managed services. Turbopuffer itself is already the target service for this test, but surrounding components should avoid extra proprietary dependencies unless explicitly chosen later.

Recommended defaults:

- Embeddings: `sentence-transformers` with `BAAI/bge-small-en-v1.5` for the first prototype. This matches turbopuffer examples, is local, avoids an embedding API key, and is small enough for local testing.
- Reranking: not required for the first successful hybrid prototype. If quality needs a second stage, use a local open-source reranker such as `BAAI/bge-reranker-base` or a Qwen3 reranker before considering proprietary rerankers like Cohere/Voyage/ZeroEntropy.
- Chunking: use a small Markdown-aware implementation or an open-source library. Chonkie, LlamaIndex, and `structchunk` are viable references; avoid heavy dependencies unless they materially reduce implementation risk.

### Proposed turbopuffer row model

One row per chunk:

- `id`: deterministic UUID/string derived from source path + chunk index + content hash, <=64 bytes.
- `vector`: BGE embedding for a chunk input string that includes title and section path context.
- `content`: normalized chunk text; full-text indexed; not filterable.
- `title`: page title; full-text indexed and returned for citations.
- `url`: source URL; filterable and returned for citations.
- `path`: local file path; filterable and returned for debugging.
- `section_path`: Markdown heading path; full-text indexed or returned for context.
- `chunk_index`: numeric chunk order within page.
- `source_hash`: hash of normalized source or chunk for incremental reindexing.
- `doc_kind` / `tags`: derived categories from URL path or filename, e.g. `blog`, `library`, `integration`, `platform`, `solutions`, `events-and-webinars`, `newsroom`.

Initial schema direction:

```python
schema = {
    "vector": {"type": "[384]f16", "ann": True},
    "content": {
        "type": "string",
        "full_text_search": True,
        "filterable": False,
    },
    "title": {"type": "string", "full_text_search": True},
    "section_path": {"type": "string", "full_text_search": True},
    "url": {"type": "string"},
    "path": {"type": "string"},
    "doc_kind": {"type": "string"},
    "tags": {"type": "[]string"},
    "source_hash": {"type": "string"},
}
```

The exact SDK syntax should be verified during implementation because turbopuffer docs show both `distance_metric="cosine_distance"` and explicit vector schema patterns.

### Proposed hybrid search method

For a user question:

1. Embed query with the same local BGE model.
2. Send a turbopuffer multi-query with at least:
   - ANN vector search over `vector`.
   - BM25 search over content/title/section fields, with title/section boosts.
3. Use server-side RRF (`rerank_by=("RRF",)`) where supported; otherwise fuse returned result lists client-side.
4. Return top chunks with `title`, `url`, `section_path`, `content`, and scores.
5. The agent answers using retrieved chunks and cites URLs/titles. If retrieval is weak, say so instead of guessing.

Candidate BM25 ranker:

```python
("Sum", [
    ("Product", 2.0, ("title", "BM25", query)),
    ("Product", 1.5, ("section_path", "BM25", query)),
    ("content", "BM25", query),
])
```

### Testing and evals

Turbopuffer docs recommend building query/ideal-result evals and measuring ranking quality (e.g. NDCG). For this small prototype, start with smoke tests and a hand-authored eval file of 10-20 questions tied to expected URLs/topics.

Suggested smoke questions:

- "What does Jellyfish say about measuring developer productivity?"
- "What integrations does Jellyfish mention for Claude Code or Cursor?"
- "What are DORA metrics according to Jellyfish?"
- "What does Jellyfish DevFinOps do?"
- "What does Jellyfish say about AI coding tool adoption?"

## Conclusions

Recommended plan:

1. Build a Python/uv prototype because turbopuffer's Python SDK and sentence-transformers examples are first-class, and Python is the simplest path for local BGE embeddings.
2. Use local open-source BGE embeddings initially; do not add proprietary embedding/reranking APIs.
3. Create a deterministic Markdown ingestion/indexing pipeline over `jellyfish-site-docs/`.
4. Store chunk-level rows in a dedicated turbopuffer namespace such as `jellyfish-site-docs-v1` (overridable with `TURBOPUFFER_NAMESPACE`).
5. Implement hybrid retrieval with turbopuffer multi-query and RRF.
6. Add smoke/eval commands before relying on the index for answer generation.
7. Do not retrieve or persist the turbopuffer API key until the user explicitly approves execution; when approved, retrieve it from Proton Pass into an environment variable only.

## Resolved after research

The user resolved the main planning defaults on 2026-06-20. See `.loom/decisions/turbopuffer-jellyfish-rag-baseline.md`.

- Region: `gcp-us-central1`.
- Namespace: `jellyfish-site-docs-v1`.
- Proton Pass lookup: search accessible Proton Pass items for the turbopuffer credential when execution is approved.
- Implementation baseline: Python/uv + local `BAAI/bge-small-en-v1.5` embeddings.
- Answering workflow remains in scope as a child ticket after retrieval client output is stable.
