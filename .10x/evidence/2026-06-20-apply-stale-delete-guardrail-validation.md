Status: recorded
Created: 2026-06-20
Updated: 2026-06-20
Relates-To: .loom/tickets/2026-06-20-apply-stale-delete-guardrail.md, .loom/specs/generic-site-rag-incremental-plan-apply.md

# Apply Stale Delete Guardrail Validation

## What was observed

Implemented explicit stale-row delete behavior for generic site apply behind `--delete-stale`.

Changed implementation/test/doc files for this ticket:

- `src/turbo_search/apply.py`
- `src/turbo_search/cli.py`
- `src/turbo_search/indexer.py`
- `tests/test_apply_cli.py`
- `README.md`
- `.loom/tickets/2026-06-20-apply-stale-delete-guardrail.md`

Key behavior added:

- `turbo-search apply` accepts `--delete-stale`.
- Apply preflight reports `delete_stale`, `delete_would_run`, `stale_rows_to_delete`, `stale_row_ids_to_delete`, `rows_deleted`, and `stale_rows_retained` without credentials, embeddings, or live API calls.
- Apply without `--delete-stale` performs no delete calls and keeps stale rows in local state as `retained_stale`.
- Approved apply with `--delete-stale` deletes the exact stale row IDs from the freshly recomputed diff using `TurbopufferWriter.delete_rows()`.
- `TurbopufferWriter.delete_rows()` uses the documented turbopuffer row delete shape: `write(deletes=[...])`.
- Local applied state is saved only after successful upsert/delete work. If a fake delete fails, prior local state remains unchanged.

No live credentials were accessed. No real embedding model was loaded in tests. No live turbopuffer API calls, writes, deletes, or evals were run.

## Procedure

Targeted apply CLI validation:

```bash
PYTHONPATH=src python3 -m unittest tests.test_apply_cli -v
```

Result: 12 tests ran OK.

Full local test suite:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Result: 70 tests ran OK.

Full uv test suite:

```bash
uv run python -m unittest discover -s tests -v
```

Result: 70 tests ran OK.

Compile check:

```bash
PYTHONPATH=src python3 -m compileall -q src tests
```

Result: passed with no output.

## What this supports

This supports the ticket acceptance criteria:

- `--delete-stale` is implemented and guarded behind apply preflight/approval semantics;
- preflight and apply without `--delete-stale` perform zero delete calls;
- approved apply with `--delete-stale` deletes exact stale row IDs from the recomputed diff;
- state updates only after successful fake delete;
- fake delete failure leaves previous local state intact;
- tests use fake writer/embedder behavior and no live credentials or turbopuffer calls.

## Limits

This evidence does not prove live turbopuffer delete compatibility because no live deletes were run. The writer uses the documented `ns.write(deletes=[ids])` shape, but a future explicitly approved live smoke would still be needed to validate SDK behavior against a disposable namespace.
