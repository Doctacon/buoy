Status: recorded
Created: 2026-06-20
Updated: 2026-06-20
Target: .loom/tickets/2026-06-20-apply-stale-delete-guardrail.md
Verdict: pass

# Apply Stale Delete Guardrail Review

## Target

Reviewed implementation for `.loom/tickets/2026-06-20-apply-stale-delete-guardrail.md`.

Files reviewed:

- `src/turbo_search/apply.py`
- `src/turbo_search/cli.py`
- `src/turbo_search/indexer.py`
- `tests/test_apply_cli.py`
- `README.md`
- `.loom/evidence/2026-06-20-apply-stale-delete-guardrail-validation.md`

## Findings

- Pass: `--delete-stale` is a separate CLI flag and does not imply approval by itself.
- Pass: apply preflight reports delete intent and exact stale row IDs while remaining local-only.
- Pass: approved apply without `--delete-stale` retains stale rows and performs no delete calls in fake-writer tests.
- Pass: approved apply with `--delete-stale` calls `delete_rows()` with exact stale row IDs from the recomputed diff.
- Pass: `TurbopufferWriter.delete_rows()` uses the documented `write(deletes=[...])` shape.
- Pass: local state is updated only after successful fake delete; fake delete failure leaves previous state intact.
- Pass: no live credentials, live writes, or live deletes were used in tests/evidence.

## Verdict

Pass.

## Residual risk

Live turbopuffer delete compatibility remains unverified until a future explicitly approved disposable-namespace live smoke. Partial-live failure after earlier upsert batches but before delete still leaves local state unchanged; that is conservative but may require manual reconciliation in a real run.
