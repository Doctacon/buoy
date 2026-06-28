Status: recorded
Created: 2026-06-20
Updated: 2026-06-20
Relates-To: .loom/tickets/2026-06-20-jellyfish-markdown-indexer.md, .loom/specs/turbopuffer-jellyfish-rag.md

# Jellyfish Markdown indexer implementation validation

## Scope validated

Implemented and validated the Markdown indexing pipeline and CLI wiring for `jellyfish-site-docs/` with safe defaults.

Safety boundaries maintained:

- No Proton Pass access.
- No secret access.
- No live turbopuffer writes or queries.
- Dry-run mode did not load embeddings or create a turbopuffer client.
- Write mode is present but gated behind explicit `--write` and runtime `TURBOPUFFER_API_KEY` from the environment.

## Changed implementation files

- `src/turbo_search/indexer.py`
- `src/turbo_search/cli.py`
- `tests/test_indexer.py`
- `tests/test_cli.py`
- `README.md`
- `.loom/tickets/2026-06-20-jellyfish-markdown-indexer.md`
- `.loom/evidence/2026-06-20-jellyfish-markdown-indexer-validation.md`

## Tests added or updated

- Added `tests/test_indexer.py` for frontmatter parsing, normalization, doc kind/tags, heading-aware chunking, deterministic IDs, row construction, and corpus empty-file handling.
- Updated `tests/test_cli.py` for index dry-run behavior and limit arguments.

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
test_chunking_is_heading_aware_and_deterministic (test_indexer.MarkdownIndexerTests.test_chunking_is_heading_aware_and_deterministic) ... ok
test_frontmatter_normalization_and_doc_tags (test_indexer.MarkdownIndexerTests.test_frontmatter_normalization_and_doc_tags) ... ok
test_process_corpus_handles_empty_files_and_limits (test_indexer.MarkdownIndexerTests.test_process_corpus_handles_empty_files_and_limits) ... ok
test_row_construction_contains_expected_attributes (test_indexer.MarkdownIndexerTests.test_row_construction_contains_expected_attributes) ... ok

----------------------------------------------------------------------
Ran 7 tests in 0.005s

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
Compiling 'src/turbo_search/indexer.py'...
Listing 'tests'...
```

### Small dry-run validation

```bash
PYTHONPATH=src python3 -m turbo_search index --corpus-dir jellyfish-site-docs --max-files 5 --limit-chunks 20
```

Result: passed, no API calls.

```json
{
  "api_calls_occurred": false,
  "batch_size": 64,
  "chunks_generated": 20,
  "command": "index",
  "corpus_dir": "<repo-root>/jellyfish-site-docs",
  "corpus_dir_exists": true,
  "credentials_required": false,
  "dry_run": true,
  "embedding_model": "BAAI/bge-small-en-v1.5",
  "errors": [],
  "files_discovered": 1124,
  "files_error": 0,
  "files_seen": 1,
  "files_skipped_empty": 0,
  "limit_chunks": 20,
  "limit_reached": true,
  "max_files": 5,
  "namespace": "jellyfish-site-docs-v1",
  "overlap_sentences": 2,
  "region": "gcp-us-central1",
  "rows_written": 0,
  "target_tokens": 300,
  "turbopuffer_api_calls": false
}
```

### Full corpus dry-run validation

```bash
PYTHONPATH=src python3 -m turbo_search index --corpus-dir jellyfish-site-docs
```

Result: passed, no API calls.

```json
{
  "api_calls_occurred": false,
  "batch_size": 64,
  "chunks_generated": 12721,
  "command": "index",
  "corpus_dir": "<repo-root>/jellyfish-site-docs",
  "corpus_dir_exists": true,
  "credentials_required": false,
  "dry_run": true,
  "embedding_model": "BAAI/bge-small-en-v1.5",
  "errors": [],
  "files_discovered": 1124,
  "files_error": 0,
  "files_seen": 1124,
  "files_skipped_empty": 1,
  "limit_chunks": null,
  "limit_reached": false,
  "max_files": null,
  "namespace": "jellyfish-site-docs-v1",
  "overlap_sentences": 2,
  "region": "gcp-us-central1",
  "rows_written": 0,
  "target_tokens": 300,
  "turbopuffer_api_calls": false
}
```

## Final git check

```bash
git diff --cached --name-only
```

Result: passed; no staged files were present (command produced no output).

## Residual risks and remaining validation

- Live turbopuffer write validation was intentionally not run. Parent must run an approved `--write` execution with `TURBOPUFFER_API_KEY` supplied from the environment only.
- Installed turbopuffer SDK write method shape should be verified during the approved live write; implementation includes a local fallback for common `upsert_rows`/`rows` variants.
- Embedding model download/load was not exercised because no write mode was run.
- The ticket remains active until live write evidence confirms namespace schema and row count.
