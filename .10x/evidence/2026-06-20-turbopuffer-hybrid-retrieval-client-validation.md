Status: recorded
Created: 2026-06-20
Updated: 2026-06-20
Relates-To: .loom/tickets/2026-06-20-turbopuffer-hybrid-retrieval-client.md, .loom/specs/turbopuffer-jellyfish-rag.md

# Turbopuffer hybrid retrieval client implementation validation

## Scope validated

Implemented and validated the local hybrid retrieval CLI/library for the Jellyfish docs turbopuffer prototype.

Safety boundaries maintained:

- No Proton Pass access.
- No secret access.
- No live turbopuffer queries.
- Default/`--dry-run` retrieval did not load the embedding model, read `TURBOPUFFER_API_KEY`, or create a turbopuffer client.
- Live retrieval is present but gated behind `--live` and reads `TURBOPUFFER_API_KEY` from the environment only.

## Changed implementation files

- `src/turbo_search/retriever.py`
- `src/turbo_search/cli.py`
- `tests/test_retriever.py`
- `tests/test_cli.py`
- `README.md`
- `.loom/tickets/2026-06-20-turbopuffer-hybrid-retrieval-client.md`
- `.loom/evidence/2026-06-20-turbopuffer-hybrid-retrieval-client-validation.md`

## Tests added or updated

- Added `tests/test_retriever.py` for ANN + boosted BM25 subquery construction, no-vector include attributes, server-side RRF `multi_query` parameters, no-vector output, and client-side RRF fallback when `rerank_by` is unsupported.
- Updated `tests/test_cli.py` for no-credential retrieval dry-run/plan JSON output.

## Commands run

### Unit tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Result: passed.

```text
test_help_mentions_safe_index_options (test_cli.CliTests.test_help_mentions_safe_index_options) ... ok
test_index_command_is_dry_run_and_needs_no_credentials (test_cli.CliTests.test_index_command_is_dry_run_and_needs_no_credentials) ... ok
test_index_command_supports_limits (test_cli.CliTests.test_index_command_supports_limits) ... ok
test_retrieve_command_dry_run_plan_needs_no_credentials (test_cli.CliTests.test_retrieve_command_dry_run_plan_needs_no_credentials) ... ok
test_chunking_is_heading_aware_and_deterministic (test_indexer.MarkdownIndexerTests.test_chunking_is_heading_aware_and_deterministic) ... ok
test_frontmatter_normalization_and_doc_tags (test_indexer.MarkdownIndexerTests.test_frontmatter_normalization_and_doc_tags) ... ok
test_process_corpus_handles_empty_files_and_limits (test_indexer.MarkdownIndexerTests.test_process_corpus_handles_empty_files_and_limits) ... ok
test_row_construction_contains_expected_attributes (test_indexer.MarkdownIndexerTests.test_row_construction_contains_expected_attributes) ... ok
test_builds_ann_and_boosted_bm25_subqueries_without_vectors_in_attributes (test_retriever.RetrieverTests.test_builds_ann_and_boosted_bm25_subqueries_without_vectors_in_attributes) ... ok
test_client_side_rrf_fallback_when_server_rerank_unsupported (test_retriever.RetrieverTests.test_client_side_rrf_fallback_when_server_rerank_unsupported) ... ok
test_live_retriever_uses_single_multi_query_with_server_rrf (test_retriever.RetrieverTests.test_live_retriever_uses_single_multi_query_with_server_rrf) ... ok

----------------------------------------------------------------------
Ran 11 tests in 0.008s

OK
```

### Syntax compile

```bash
PYTHONPATH=src python3 -m compileall src tests
```

Result: passed.

```text
Listing 'src'...
Listing 'src/turbo_search'...
Compiling 'src/turbo_search/retriever.py'...
Listing 'tests'...
```

### Retrieval dry-run validation

```bash
PYTHONPATH=src python3 -m turbo_search retrieve "What are DORA metrics?" --dry-run --top-k 3 --candidates 20 --doc-kind library --json
```

Result: passed, no credentials and no API calls.

```json
{
  "api_calls_occurred": false,
  "candidates": 20,
  "command": "retrieve",
  "credentials_required": false,
  "doc_kind": "library",
  "dry_run": true,
  "embedding_model": "BAAI/bge-small-en-v1.5",
  "live_execution": "pass --live to embed the query and call turbopuffer",
  "namespace": "jellyfish-site-docs-v1",
  "plan": true,
  "query": "What are DORA metrics?",
  "region": "gcp-us-central1",
  "retrieval": {
    "fallback": "client-side reciprocal-rank fusion if server RRF is unsupported or separate lists are returned",
    "request": "turbopuffer multi_query",
    "rerank_by": [
      "RRF"
    ],
    "subqueries": [
      {
        "filters": [
          "doc_kind",
          "Eq",
          "library"
        ],
        "include_attributes": [
          "title",
          "url",
          "section_path",
          "content",
          "path",
          "doc_kind",
          "chunk_index"
        ],
        "limit": 20,
        "name": "ann",
        "rank_by": [
          "vector",
          "ANN",
          "<query embedding>"
        ]
      },
      {
        "filters": [
          "doc_kind",
          "Eq",
          "library"
        ],
        "include_attributes": [
          "title",
          "url",
          "section_path",
          "content",
          "path",
          "doc_kind",
          "chunk_index"
        ],
        "limit": 20,
        "name": "bm25",
        "rank_by": [
          "Sum",
          [
            [
              "Product",
              2.0,
              [
                "title",
                "BM25",
                "What are DORA metrics?"
              ]
            ],
            [
              "Product",
              1.5,
              [
                "section_path",
                "BM25",
                "What are DORA metrics?"
              ]
            ],
            [
              "content",
              "BM25",
              "What are DORA metrics?"
            ]
          ]
        ]
      }
    ]
  },
  "top_k": 3,
  "turbopuffer_api_calls": false
}
```

### Final git check

```bash
git diff --cached --name-only
```

Result: passed; no staged files were present (command produced no output).

## Residual risks and remaining validation

- Live turbopuffer retrieval was intentionally not run. Parent must run approved live retrieval after the namespace is indexed, with `TURBOPUFFER_API_KEY` supplied from the environment only.
- Installed turbopuffer SDK live response shapes and filter syntax should be confirmed during approved live validation; the implementation includes tested fallbacks for common `rerank_by` unsupported and separate-result-list cases.
- Embedding model download/load was not exercised in this worker because no live retrieval was run.
- The ticket remains active until live retrieval evidence confirms relevant chunks/citations from the indexed namespace.
