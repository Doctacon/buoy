Status: recorded
Created: 2026-06-20
Updated: 2026-06-20
Relates-To: .loom/tickets/2026-06-20-apply-cli-incremental-upsert.md, .loom/specs/generic-site-rag-incremental-plan-apply.md

# Apply CLI Incremental Upsert Validation

## What was observed

Implemented the generic-site `turbo-search apply` preflight and approved incremental upsert path.

Changed implementation/test/doc files for this ticket:

- `src/turbo_search/apply.py`
- `src/turbo_search/cli.py`
- `src/turbo_search/indexer.py`
- `tests/test_apply_cli.py`
- `README.md`
- `.loom/tickets/2026-06-20-apply-cli-incremental-upsert.md`

Key behavior added:

- `turbo-search apply --plan <plan.json> --namespace <namespace>` verifies saved plan artifacts and recomputes the local diff without credentials, embeddings, or turbopuffer calls.
- `--approve` gates the live path and requires `TURBOPUFFER_API_KEY` from the environment.
- Approved apply embeds/upserts only rows selected by a freshly recomputed diff, not editable plan diff fields.
- Plan verification reads co-located `manifest.json` and `chunks.jsonl`, verifies namespace/schema/state compatibility, checks `chunks.jsonl` against `manifest.json`, recomputes embedding-text hashes, and recomputes the plan artifact hash from manifest/options/model inputs.
- State is saved only after successful fake upsert in tests.
- Stale active rows are retained in local state as `retained_stale` when apply succeeds without delete support; deletion remains out of scope for the later stale-delete ticket.
- `TurbopufferWriter` now accepts an optional schema argument so generic rows can use the generic site schema while existing Jellyfish writes keep the default schema.

No live credentials were accessed. No real embedding model was loaded in tests. No live turbopuffer API calls or writes/evals were run.

## Procedure

Targeted apply CLI validation:

```bash
PYTHONPATH=src python3 -m unittest tests.test_apply_cli -v
```

Result: 8 tests ran OK.

Full local test suite:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Result: 66 tests ran OK.

Full uv test suite:

```bash
uv run python -m unittest discover -s tests -v
```

Result: 66 tests ran OK.

Compile check:

```bash
PYTHONPATH=src python3 -m compileall -q src tests
```

Result: passed with no output.

No staging was performed. `git status --short --untracked-files=all` showed modified/untracked files only and no staged entries.

## What this supports

This supports the ticket acceptance criteria:

- apply preflight prints JSON/text summaries and performs no credential reads, embedding loads, or live calls;
- apply preflight fails before live work on artifact/namespace/state verification errors;
- approved apply fails clearly when `TURBOPUFFER_API_KEY` is absent;
- approved apply uses fake embedder/writer tests to prove only diff rows are embedded/upserted;
- local state is not updated when fake upsert fails;
- local state is updated after successful fake upsert;
- stale rows are retained in state without delete behavior.

## Limits

This evidence does not verify live turbopuffer SDK compatibility for generic rows because live writes are intentionally out of scope. Stale-row deletion remains out of scope and is tracked by `.loom/tickets/2026-06-20-apply-stale-delete-guardrail.md`.
