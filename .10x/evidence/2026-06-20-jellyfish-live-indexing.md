Status: recorded
Created: 2026-06-20
Updated: 2026-06-20
Relates-To: .loom/tickets/2026-06-20-jellyfish-markdown-indexer.md, .loom/tickets/2026-06-20-proton-pass-turbopuffer-config.md

# Jellyfish live turbopuffer indexing validation

## Scope validated

Ran the approved live write for `jellyfish-site-docs/` into turbopuffer with non-secret runtime configuration:

- `TURBOPUFFER_REGION=gcp-us-central1`
- `TURBOPUFFER_NAMESPACE=jellyfish-site-docs-v1`
- Embedding model: `BAAI/bge-small-en-v1.5`
- Batch size: `128`

Secret handling boundaries maintained:

- The turbopuffer API key was retrieved from Proton Pass into shell memory only.
- The API key value was not printed.
- The API key value was not written to repository files or a project `.env`.
- Command output was checked/redacted before printing if it contained the in-memory key value.

## Commands and procedure

1. Verified dependencies and unit tests:

```bash
uv sync && uv run python -m unittest discover -s tests -v
```

Result: passed, 11 tests.

2. Followed the Proton Pass session check rule before `pass-cli` access. An isolated session at `/tmp/pass-agent-turbo-search-live-indexing` was used. The active accessible vault was `<private Proton Pass vault>`, and the credential item title was `<private turbopuffer credential item>`.

3. Retrieved only the `API Key` field into shell memory without printing it:

```bash
pass-cli info >/dev/null
TURBOPUFFER_API_KEY="$(PROTON_PASS_AGENT_REASON="Live index approved Jellyfish docs into turbopuffer namespace jellyfish-site-docs-v1" \
  pass-cli item view --vault-name "<private Proton Pass vault>" --item-title "<private turbopuffer credential item>" --field "API Key")"
```

4. Ran the approved live index command with the key in shell memory only:

```bash
TURBOPUFFER_REGION=gcp-us-central1 \
TURBOPUFFER_NAMESPACE=jellyfish-site-docs-v1 \
uv run turbo-search index --corpus-dir jellyfish-site-docs --write --batch-size 128
```

5. Verified the namespace with non-secret turbopuffer SDK calls:

- `ns.query(aggregate_by={"row_count": ("Count",)})`
- `ns.schema()` with only attribute names, types, ANN flags, full-text flags/config, and filterability recorded.

## Sanitized live index output

The live index completed successfully.

```json
{
  "api_calls_occurred": true,
  "batch_size": 128,
  "chunks_generated": 12721,
  "command": "index",
  "corpus_dir": "<repo-root>/jellyfish-site-docs",
  "corpus_dir_exists": true,
  "credentials_required": true,
  "dry_run": false,
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
  "rows_written": 12721,
  "target_tokens": 300,
  "turbopuffer_api_calls": true
}
```

Non-secret note: the local embedding model emitted a Hugging Face Hub warning about unauthenticated downloads/rate limits and loaded successfully.

## Sanitized verification output

### Aggregate row count

```json
{
  "aggregations": {
    "row_count": 12721
  },
  "rows": null
}
```

The verified aggregate count matched the indexer's `rows_written` count: `12721`.

### Schema keys and types/index flags

```json
{
  "chunk_index": {
    "filterable": true,
    "type": "uint"
  },
  "content": {
    "filterable": false,
    "full_text_search": "enabled",
    "type": "string"
  },
  "doc_kind": {
    "filterable": true,
    "type": "string"
  },
  "id": {
    "type": "string"
  },
  "path": {
    "filterable": true,
    "type": "string"
  },
  "section_path": {
    "filterable": false,
    "full_text_search": "enabled",
    "type": "string"
  },
  "source_hash": {
    "filterable": true,
    "type": "string"
  },
  "tags": {
    "filterable": true,
    "type": "[]string"
  },
  "title": {
    "filterable": false,
    "full_text_search": "enabled",
    "type": "string"
  },
  "url": {
    "filterable": true,
    "type": "string"
  },
  "vector": {
    "ann": true,
    "type": "[384]f16"
  }
}
```

The schema confirms ANN on `vector` and full-text search on `content`, `title`, and `section_path`.

## What this supports

- The full observed corpus was processed: 1124 Markdown files discovered and seen.
- The indexer generated and wrote 12721 deterministic chunk rows.
- The target namespace `jellyfish-site-docs-v1` in `gcp-us-central1` contains 12721 rows by aggregate count.
- Required citation/debug attributes are present in the namespace schema: `title`, `url`, `section_path`, `path`, `chunk_index`, `doc_kind`, `tags`, and `source_hash`.
- No file errors were reported; one empty file was skipped as expected from dry-run validation.

## Limits and residual risks

- `ns.metadata()` was attempted, but the local evidence script failed to JSON-serialize a datetime in the metadata object. This did not affect aggregate row-count or schema verification.
- This evidence validates a point-in-time live write, not continuous sync or future source changes.
- Re-run determinism is supported by deterministic chunk IDs and matching dry-run/live counts, but a second live write was not run because acceptance required one approved live write and destructive/redundant retries were avoided.
