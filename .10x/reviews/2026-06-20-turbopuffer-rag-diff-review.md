Status: recorded
Created: 2026-06-20
Updated: 2026-06-20
Target: current repository diff for turbopuffer Jellyfish docs RAG implementation
Verdict: concerns

# Review: turbopuffer Jellyfish docs RAG diff

## Target

Current repository diff after executing the Loom child tickets for `.loom/tickets/2026-06-20-turbopuffer-jellyfish-rag-plan.md`.

## Findings

### Low severity: nonexistent corpus path exits successfully

`turbo-search index --corpus-dir <missing>` returns exit code 0 with `"corpus_dir_exists": false` instead of failing. The CLI appears to expect a `FileNotFoundError` in `_run_index`, but `process_corpus` resolves the path and calls `rglob` without checking existence.

References from reviewer:

- `src/turbo_search/cli.py` around `_run_index` exception handling.
- `src/turbo_search/indexer.py` around `process_corpus` path resolution/discovery.

Impact: not blocking the successful live index, but a typo in a future indexing run could appear to succeed with zero files/chunks.

Tracking ticket: `.loom/tickets/2026-06-20-fix-index-missing-corpus-error.md`

## Positive findings

- No blockers found.
- Dry-run defaults are implemented for retrieval/evals.
- Secret handling is sound: config does not read `TURBOPUFFER_API_KEY`, live paths read it from environment only.
- Retrieval excludes vectors by default and tests assert vectors are absent.
- Tests cover CLI dry-run behavior, chunking/index rows, hybrid retrieval/RRF fallback, and eval scoring.
- Live evidence coherently records 12,721 indexed rows, successful live retrieval, and 5/5 smoke evals.
- Secret scan of changed/untracked files found no literal key values and no `.env*` files outside ignored `.venv`.

## Verdict

Concerns raised. The missing-corpus behavior should be fixed before final closure/commit because the fix is small and within existing scope.

## Residual risk

This was a bounded diff review, not a full production readiness audit. Retrieval quality is validated only by smoke evals, not a comprehensive benchmark.
