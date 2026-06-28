Status: done
Created: 2026-06-20
Updated: 2026-06-20
Parent: .loom/tickets/2026-06-20-turbopuffer-jellyfish-rag-plan.md
Depends-On: .loom/tickets/2026-06-20-jellyfish-markdown-indexer.md, .loom/tickets/2026-06-20-turbopuffer-hybrid-retrieval-client.md, .loom/specs/turbopuffer-jellyfish-rag.md

# Add retrieval smoke tests and lightweight evals

## Scope

Create a lightweight evaluation harness to confirm that turbopuffer hybrid retrieval works for representative questions about the Jellyfish docs corpus.

In scope:

- A small set of hand-authored smoke/eval questions.
- Expected URL/topic hints for each question.
- A command to run retrieval for all evals and summarize whether expected sources appear in top-k.
- Evidence capture after eval execution.
- Optional comparison of vector-only, BM25-only, and hybrid/RRF results.

Out of scope:

- A full production relevance benchmark.
- Automated LLM grading.
- Proprietary reranking services.

## Acceptance criteria

- At least 5 smoke questions run successfully against the indexed namespace.
- Results include relevant Jellyfish source URLs/titles in top-k for most smoke questions.
- The eval report makes failures visible and actionable.
- Evidence is recorded under `.loom/evidence/` after running evals.

## Candidate smoke questions

- "What does Jellyfish say about measuring developer productivity?"
- "What are DORA metrics according to Jellyfish?"
- "What does Jellyfish DevFinOps do?"
- "What integrations does Jellyfish mention for Claude Code or Cursor?"
- "What does Jellyfish say about AI coding tool adoption?"

## Progress and notes

- 2026-06-20: Ticket created only. No evals run.
- 2026-06-20: Activated for execution under `/loom-driver` after indexer and live retrieval tickets completed.
- 2026-06-20: Added built-in 5-question smoke eval dataset at `src/turbo_search/data/retrieval_smoke_evals.json` and `turbo-search evals` CLI with safe dry-run listing plus live execution against the existing hybrid retriever.
- 2026-06-20: Added no-credential tests for eval dataset loading, URL/topic scoring, and CLI dry-run listing. Validation passed: `PYTHONPATH=src python3 -m unittest discover -s tests -v` (16 tests) and `PYTHONPATH=src python3 -m compileall src tests`.
- 2026-06-20: Retrieved the turbopuffer API key from Proton Pass into shell memory only and ran live smoke evals against `TURBOPUFFER_REGION=gcp-us-central1`, `TURBOPUFFER_NAMESPACE=jellyfish-site-docs-v1` with `--top-k 5 --candidates 30`. Result: 5/5 passed, 100% pass rate. Evidence: `.loom/evidence/2026-06-20-retrieval-smoke-evals.md`.
- 2026-06-20: Acceptance met; ticket closed as done.

## Blockers

- None.
