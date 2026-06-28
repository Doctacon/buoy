Status: recorded
Created: 2026-06-20
Updated: 2026-06-20
Relates-To: .loom/tickets/2026-06-20-fix-index-missing-corpus-error.md, .loom/reviews/2026-06-20-turbopuffer-rag-diff-review.md

# Missing corpus index command validation

## Scope validated

Fixed and validated `turbo-search index --corpus-dir <missing>` so a nonexistent corpus path returns a non-zero exit with a friendly stderr error instead of a successful empty dry-run summary.

Safety boundaries maintained:

- No secrets accessed.
- No Proton Pass access.
- No live turbopuffer writes or queries.

## Changed files

- `src/turbo_search/indexer.py`
- `src/turbo_search/cli.py`
- `tests/test_cli.py`
- `.loom/tickets/2026-06-20-fix-index-missing-corpus-error.md`
- `.loom/evidence/2026-06-20-fix-index-missing-corpus-error.md`

## Tests added

- Added `tests/test_cli.py::CliTests::test_index_command_missing_corpus_exits_nonzero` covering non-zero exit, empty stdout, and friendly missing-corpus stderr.

## Commands run

### Unit tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Result: passed.

```text
test_evals_command_dry_run_lists_cases_without_credentials (test_cli.CliTests.test_evals_command_dry_run_lists_cases_without_credentials) ... ok
test_help_mentions_safe_index_options (test_cli.CliTests.test_help_mentions_safe_index_options) ... ok
test_index_command_is_dry_run_and_needs_no_credentials (test_cli.CliTests.test_index_command_is_dry_run_and_needs_no_credentials) ... ok
test_index_command_missing_corpus_exits_nonzero (test_cli.CliTests.test_index_command_missing_corpus_exits_nonzero) ... ok
test_index_command_supports_limits (test_cli.CliTests.test_index_command_supports_limits) ... ok
test_retrieve_command_dry_run_plan_needs_no_credentials (test_cli.CliTests.test_retrieve_command_dry_run_plan_needs_no_credentials) ... ok
test_load_eval_cases_rejects_missing_expected_hints (test_evals.EvalHarnessTests.test_load_eval_cases_rejects_missing_expected_hints) ... ok
test_loads_builtin_smoke_eval_dataset (test_evals.EvalHarnessTests.test_loads_builtin_smoke_eval_dataset) ... ok
test_score_hits_passes_on_expected_topic_in_title_or_content (test_evals.EvalHarnessTests.test_score_hits_passes_on_expected_topic_in_title_or_content) ... ok
test_score_hits_passes_on_expected_url_in_top_k (test_evals.EvalHarnessTests.test_score_hits_passes_on_expected_url_in_top_k) ... ok
test_chunking_is_heading_aware_and_deterministic (test_indexer.MarkdownIndexerTests.test_chunking_is_heading_aware_and_deterministic) ... ok
test_frontmatter_normalization_and_doc_tags (test_indexer.MarkdownIndexerTests.test_frontmatter_normalization_and_doc_tags) ... ok
test_process_corpus_handles_empty_files_and_limits (test_indexer.MarkdownIndexerTests.test_process_corpus_handles_empty_files_and_limits) ... ok
test_row_construction_contains_expected_attributes (test_indexer.MarkdownIndexerTests.test_row_construction_contains_expected_attributes) ... ok
test_builds_ann_and_boosted_bm25_subqueries_without_vectors_in_attributes (test_retriever.RetrieverTests.test_builds_ann_and_boosted_bm25_subqueries_without_vectors_in_attributes) ... ok
test_client_side_rrf_fallback_when_server_rerank_unsupported (test_retriever.RetrieverTests.test_client_side_rrf_fallback_when_server_rerank_unsupported) ... ok
test_live_retriever_uses_single_multi_query_with_server_rrf (test_retriever.RetrieverTests.test_live_retriever_uses_single_multi_query_with_server_rrf) ... ok

----------------------------------------------------------------------
Ran 17 tests in 0.010s

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
Compiling 'src/turbo_search/cli.py'...
Listing 'src/turbo_search/data'...
Compiling 'src/turbo_search/indexer.py'...
Listing 'tests'...
Compiling 'tests/test_cli.py'...
```

### Missing corpus CLI validation

```bash
set +e
PYTHONPATH=src python3 -m turbo_search index --corpus-dir /tmp/turbo-search-missing-corpus-loom
status=$?
echo "exit_status=$status"
exit 0
```

Result: passed; command returned non-zero from the CLI under test (`exit_status=2`).

```text
Corpus directory not found: /private/tmp/turbo-search-missing-corpus-loom
exit_status=2
```

### No staged files

```bash
git diff --cached --name-only
```

Result: passed.

```text

```

## Validation output

- Missing corpus path is rejected before Markdown discovery.
- CLI returns exit code `2` for a missing corpus path.
- stderr contains `Corpus directory not found` and the missing path.
- stdout remains empty, so the command no longer emits a misleading success JSON summary.
- Full unit suite and `compileall` passed.

## Residual risks

- Validation was limited to local dry-run/error paths; no live turbopuffer or Proton Pass commands were run by design.
