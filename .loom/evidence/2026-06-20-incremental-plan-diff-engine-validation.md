Status: recorded
Created: 2026-06-20
Updated: 2026-06-20
Relates-To: .loom/tickets/2026-06-20-incremental-plan-diff-engine.md, .loom/specs/generic-site-rag-incremental-plan-apply.md

# Incremental Plan Diff Engine Validation

## What was observed

Implemented a pure local incremental diff engine for generic site RAG plans.

Changed implementation/test files:

- `src/turbo_search/plan_diff.py`
- `tests/test_plan_diff.py`
- `.loom/tickets/2026-06-20-incremental-plan-diff-engine.md`

Key behavior added:

- `diff_manifest_against_state(manifest, state)` compares desired `ManifestDocument` chunks to local `AppliedState` rows.
- `diff_summary_for_plan(manifest, state)` returns compact summary fields suitable for future `plan.json` integration.
- Diff results include page counts: added, changed, unchanged, removed.
- Diff results include chunk/row counts: unchanged, chunks to embed, rows to upsert, stale rows, retained stale rows.
- Machine-readable lists are returned for future apply:
  - `unchanged_chunks`
  - `chunks_to_embed_records`
  - `rows_to_upsert_records`
  - `stale_row_records`
  - `retained_stale_row_records`
- Active rows absent from the desired manifest are classified as stale.
- Retained-stale rows absent from the desired manifest remain visible as retained stale.
- Retained-stale rows that become desired again are marked for reactivation/upsert.
- Deleted state rows are ignored by the diff.

No credentials were accessed. No embedding model was loaded. No crawl was run. No turbopuffer API calls or live writes/evals were run.

## Procedure

Targeted validation:

```bash
PYTHONPATH=src python3 -m unittest tests.test_plan_diff -v
```

Result: 8 tests ran OK.

Full local test suite:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Result: 52 tests ran OK.

Full uv test suite:

```bash
uv run python -m unittest discover -s tests -v
```

Result: 52 tests ran OK.

Compile check:

```bash
PYTHONPATH=src python3 -m compileall -q src tests
```

Result: passed with no output.

## What this supports

This supports the ticket acceptance criteria:

- first apply reports all desired chunks as needing embed/upsert and zero stale rows;
- no-change second plan reports zero embeddings/upserts and zero stale rows;
- changed chunk reports one upsert and the old row as stale;
- removed page reports its active rows as stale;
- retained-stale rows remain visible until deleted;
- diff output includes compact summary fields and machine-readable row/chunk lists for future apply;
- tests cover the required scenarios using hand-authored manifest/state fixtures.

## Limits

This evidence does not prove CLI integration, plan artifact integration, live apply behavior, or turbopuffer write/delete compatibility. Those are covered by later tickets. Page-level counts are best-effort based on active applied rows and desired page hashes; retained-stale rows are surfaced separately rather than counted as active removed pages.
