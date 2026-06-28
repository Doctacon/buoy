Status: done
Created: 2026-06-20
Updated: 2026-06-20
Depends-On: .loom/research/2026-06-20-turbopuffer-markdown-rag-research.md, .loom/specs/turbopuffer-jellyfish-rag.md, .loom/evidence/2026-06-20-jellyfish-site-docs-inventory.md, .loom/decisions/turbopuffer-jellyfish-rag-baseline.md

# Plan: turbopuffer hybrid RAG over Jellyfish site docs

## Scope

Create a local prototype that indexes `jellyfish-site-docs/` into turbopuffer and lets the agent answer questions by first retrieving relevant chunks through turbopuffer hybrid search.

This parent ticket is an orchestration plan only. It should not be executed directly. Child tickets are the executable units and are currently blocked until the user approves implementation.

## Recommended architecture

- Language/tooling: Python with `uv`.
- Embeddings: local `sentence-transformers` model `BAAI/bge-small-en-v1.5`.
- Corpus: Markdown files under `jellyfish-site-docs/`.
- Index shape: one turbopuffer row per chunk.
- Namespace: configurable with `TURBOPUFFER_NAMESPACE`, recommended default `jellyfish-site-docs-v1`.
- Region: configurable with `TURBOPUFFER_REGION`, default `gcp-us-central1` unless user chooses otherwise.
- Retrieval: turbopuffer `multi_query` with ANN + BM25, fused by `rerank_by=("RRF",)` with local RRF fallback.
- Answering: agent runs a retrieval command, reads returned chunk text, then answers with citations.

## Child tickets and sequencing

1. `.loom/tickets/2026-06-20-proton-pass-turbopuffer-config.md`
   - Retrieve or document runtime configuration for `TURBOPUFFER_API_KEY`, region, and namespace.
   - Must run before any turbopuffer API calls.

2. `.loom/tickets/2026-06-20-python-prototype-scaffold.md`
   - Create minimal Python/uv project structure and dependencies.
   - Can run after approval without API credentials.

3. `.loom/tickets/2026-06-20-jellyfish-markdown-indexer.md`
   - Implement parsing, normalization, chunking, embeddings, and turbopuffer batch writes.
   - Depends on scaffold and config.

4. `.loom/tickets/2026-06-20-turbopuffer-hybrid-retrieval-client.md`
   - Implement retrieval CLI/library with ANN + BM25 + RRF.
   - Depends on scaffold and config; can be tested after a namespace has data.

5. `.loom/tickets/2026-06-20-agent-answering-workflow.md`
   - Document and/or implement the agent-facing answer workflow using retrieval results.
   - Depends on retrieval client.

6. `.loom/tickets/2026-06-20-retrieval-smoke-evals.md`
   - Add smoke tests/evals to validate retrieval quality and prevent regressions.
   - Depends on indexer and retrieval client.

7. `.loom/tickets/2026-06-20-fix-index-missing-corpus-error.md`
   - Follow-up fix opened from review to make missing corpus paths fail clearly.
   - Depends on `.loom/reviews/2026-06-20-turbopuffer-rag-diff-review.md`.

## Parallelization

After approval:

- Scaffold and config can proceed first.
- Indexer and retrieval client can be developed in parallel after scaffold, but retrieval cannot be fully validated until data is indexed.
- Answering workflow and smoke evals should wait until retrieval output shape is stable.

## Acceptance criteria

- All child tickets have been completed or explicitly cancelled.
- The corpus can be indexed into turbopuffer without committing secrets.
- Retrieval returns relevant chunks with titles/URLs for representative Jellyfish docs questions.
- The agent has a documented procedure for answering future questions using the retrieval command.
- Smoke/eval evidence exists showing the retrieval loop works.

## Current State

Done. The Jellyfish Markdown corpus has been indexed into turbopuffer namespace `jellyfish-site-docs-v1` in `gcp-us-central1`, and the local Python/uv CLI can index, retrieve, and run smoke evals. Future agents should use `docs/agent-answering-workflow.md` before answering Jellyfish-docs questions.

## Journal

- 2026-06-20: Created plan and child tickets only. No credentials accessed. No code written. No turbopuffer API calls made.
- 2026-06-20: Research captured in `.loom/research/2026-06-20-turbopuffer-markdown-rag-research.md`.
- 2026-06-20: User resolved planning defaults via question tool: `gcp-us-central1`, `jellyfish-site-docs-v1`, Proton Pass item search when execution is approved, and Python/uv + local BGE.
- 2026-06-20: Completed config, scaffold, indexer, retrieval, answering workflow, and smoke-eval child tickets.
- 2026-06-20: Live indexing wrote and verified `12721` rows. Evidence: `.loom/evidence/2026-06-20-jellyfish-live-indexing.md`.
- 2026-06-20: Live retrieval validated citation-bearing `server_rrf` results. Evidence: `.loom/evidence/2026-06-20-jellyfish-live-retrieval.md`.
- 2026-06-20: Smoke evals passed 5/5. Evidence: `.loom/evidence/2026-06-20-retrieval-smoke-evals.md`.
- 2026-06-20: Bounded review found one low-severity missing-corpus behavior issue. Fixed under `.loom/tickets/2026-06-20-fix-index-missing-corpus-error.md`.
- 2026-06-20: Final local validation passed 17 tests, compileall, and missing-corpus exit-status check. Evidence: `.loom/evidence/2026-06-20-turbopuffer-jellyfish-rag-plan-completion.md`.

## Blockers

- None.
