Status: recorded
Created: 2026-06-20
Updated: 2026-06-20
Relates-To: .loom/tickets/2026-06-20-turbopuffer-jellyfish-rag-plan.md, .loom/specs/turbopuffer-jellyfish-rag.md

# Turbopuffer Jellyfish RAG plan completion evidence

## What was observed

The Loom plan for a turbopuffer-backed Jellyfish docs RAG prototype was executed through its child tickets.

Completed child tickets:

- `.loom/tickets/2026-06-20-proton-pass-turbopuffer-config.md`
- `.loom/tickets/2026-06-20-python-prototype-scaffold.md`
- `.loom/tickets/2026-06-20-jellyfish-markdown-indexer.md`
- `.loom/tickets/2026-06-20-turbopuffer-hybrid-retrieval-client.md`
- `.loom/tickets/2026-06-20-agent-answering-workflow.md`
- `.loom/tickets/2026-06-20-retrieval-smoke-evals.md`
- `.loom/tickets/2026-06-20-fix-index-missing-corpus-error.md`

Live system evidence:

- `jellyfish-site-docs/` indexed into turbopuffer namespace `jellyfish-site-docs-v1` in region `gcp-us-central1`.
- Indexing wrote `12721` chunk rows.
- Aggregate namespace count verified `12721` rows.
- Schema verified ANN on `vector` and BM25/full-text search on `content`, `title`, and `section_path`.
- Live retrieval succeeded for DORA metrics and developer productivity questions using `server_rrf`.
- Smoke evals ran 5 queries and passed 5/5.

## Procedure

Final local validation commands run after implementation and review fix:

```bash
uv run python -m unittest discover -s tests -v
uv run python -m compileall -q src tests
uv run turbo-search index --corpus-dir /tmp/turbo-search-missing-corpus-final
```

The first command passed 17 tests. The second command passed. The missing-corpus command returned exit status `2` with a friendly error:

```text
Corpus directory not found: /private/tmp/turbo-search-missing-corpus-final
```

A bounded review record was created at `.loom/reviews/2026-06-20-turbopuffer-rag-diff-review.md`. The review found one low-severity issue, tracked and fixed by `.loom/tickets/2026-06-20-fix-index-missing-corpus-error.md`.

## What this supports

This evidence supports closing the parent plan because:

- The indexed namespace exists and contains the expected number of chunk rows.
- The retrieval client can answer against the namespace with citation-bearing chunks.
- The agent answering workflow is documented.
- Smoke evals demonstrate basic relevance for representative Jellyfish docs questions.
- Tests pass after the review fix.
- No secret values were written to repository files.

## Limits

This does not prove production readiness, continuous synchronization, comprehensive retrieval quality, or long-term Hugging Face model availability. The eval set is a small smoke suite, not a benchmark.
