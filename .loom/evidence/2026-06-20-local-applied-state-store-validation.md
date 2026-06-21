Status: recorded
Created: 2026-06-20
Updated: 2026-06-20
Relates-To: .loom/tickets/2026-06-20-local-applied-state-store.md, .loom/specs/generic-site-rag-incremental-plan-apply.md

# Local Applied State Store Validation

## What was observed

Implemented the local applied-state backend for generic site RAG incremental plan/apply state.

Changed implementation/test files:

- `src/turbo_search/applied_state.py`
- `tests/test_applied_state.py`
- `.gitignore`
- `.loom/tickets/2026-06-20-local-applied-state-store.md`

Key behavior added:

- Default local state paths:
  - `.turbo-search/state/<site-id>/<namespace>/last-applied.json`
  - `.turbo-search/state/<site-id>/<namespace>/history/<apply-id>.json`
- Missing state loads as an explicit `first_apply=True` empty state.
- Existing state validates schema version, site ID, namespace, and normalized base URL.
- Row ledger supports `active`, `retained_stale`, and `deleted` statuses.
- Saves write history and atomically replace `last-applied.json` using a temp file in the target directory plus `os.replace`.
- `.turbo-search/` is ignored so local applied state is not committed by default.

No credentials were accessed. No embedding model was loaded. No turbopuffer API calls, live writes, namespace changes, or live evals were run.

## Procedure

Targeted validation:

```bash
PYTHONPATH=src python3 -m unittest tests.test_applied_state -v
```

Result: 8 tests ran OK.

Full local test suite:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Result: 44 tests ran OK.

Full uv test suite:

```bash
uv run python -m unittest discover -s tests -v
```

Result: 44 tests ran OK.

Compile check:

```bash
PYTHONPATH=src python3 -m compileall -q src tests
```

Result: passed with no output.

## What this supports

This supports the ticket acceptance criteria:

- missing state loads as explicit first-apply/empty state;
- existing state loads and validates identity compatibility;
- invalid schema version and conflicting state fail clearly;
- saving state writes history and atomically replaces last-applied state;
- retained stale rows are representable and persist after reload;
- tests use temporary directories and no live services;
- `.turbo-search/` is excluded from default commits.

## Limits

This evidence does not prove the future diff engine, plan CLI, apply CLI, embeddings, or turbopuffer write/delete behavior. Those remain in later child tickets.
