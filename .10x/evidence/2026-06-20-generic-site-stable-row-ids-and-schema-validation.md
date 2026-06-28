Status: recorded
Created: 2026-06-20
Updated: 2026-06-20
Relates-To: .loom/tickets/2026-06-20-generic-site-stable-row-ids-and-schema.md, .loom/specs/generic-site-rag-incremental-plan-apply.md

# Generic Site Stable Row IDs and Schema Validation

## What was observed

Implemented/refined generic-site stable row identity and row metadata helpers for incremental apply planning.

Changed implementation/test files:

- `src/turbo_search/plan_artifacts.py`
- `tests/test_plan_artifacts.py`
- `.loom/tickets/2026-06-20-generic-site-stable-row-ids-and-schema.md`

Key behavior added/refined:

- Generic site row IDs now use `site_id + canonical_url + section_path + chunk_hash` and intentionally exclude page hash, page path, and chunk index from identity.
- Chunk manifest records include `row_id`, `row_id_candidate`, `site_id`, `canonical_url`, `page_hash`, `chunk_hash`, and `embedding_text_hash`.
- Added `GENERIC_SITE_TURBOPUFFER_SCHEMA` extending the existing Jellyfish schema with generic incremental metadata fields.
- Added `build_generic_site_row()` to construct generic rows with `site_id`, `canonical_url`, `page_hash`, `chunk_hash`, `embedding_text_hash`, `plan_id`, and `applied_at` for future apply code.
- Existing Jellyfish `MarkdownChunk` ID generation and `build_row()` behavior remain unchanged.

No credentials were accessed. No embedding model was loaded. No turbopuffer API calls or live writes/evals were run.

## Procedure

Targeted validation:

```bash
PYTHONPATH=src python3 -m unittest tests.test_plan_artifacts tests.test_indexer tests.test_retriever -v
```

Result: 16 tests ran OK.

Full local test suite:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Result: 36 tests ran OK.

Full uv test suite:

```bash
uv run python -m unittest discover -s tests -v
```

Result: 36 tests ran OK.

Compile check:

```bash
PYTHONPATH=src python3 -m compileall -q src tests
```

Result: passed with no output.

## What this supports

This supports the ticket acceptance criteria:

- generic site row IDs are deterministic and short (`ts_` plus 32 hex chars);
- unrelated page-section changes do not change row IDs for unchanged chunks elsewhere on the page;
- chunk content changes do change row IDs;
- generic row/schema metadata includes local-state and future-recovery fields;
- existing Jellyfish indexer/retriever tests continue to pass;
- tests use local temp files and fakes only, with no live API calls.

## Limits

This evidence does not verify live turbopuffer writes or final SDK schema compatibility. Exact write/delete SDK behavior remains a later apply-ticket responsibility.
