Status: done
Created: 2026-06-20
Updated: 2026-06-20
Parent: .loom/tickets/2026-06-20-generic-site-rag-incremental-plan-apply.md
Depends-On: .loom/tickets/2026-06-20-apply-cli-incremental-upsert.md, .loom/specs/generic-site-rag-incremental-plan-apply.md, .loom/decisions/generic-site-rag-incremental-state.md

# Apply Stale Delete Guardrail

## Scope

Add explicit stale-row delete behavior to generic site apply.

In scope:

- Ensure plans report stale rows from local applied state.
- Ensure apply without `--delete-stale` never deletes rows.
- Preserve stale rows in local state as retained stale rows when not deleted.
- Add `--delete-stale` for approved apply.
- Delete exact stale row IDs only after artifact verification, namespace verification, and explicit approval.
- Update local state to remove or mark deleted rows after successful delete.
- Tests with a fake turbopuffer writer/deleter.

Out of scope:

- Namespace deletion.
- Automatic deletes by default.
- Live delete execution without explicit user approval.
- Remote state reconciliation.

## Command sketch

Approved upsert while retaining stale rows:

```bash
turbo-search apply --plan <plan.json> --namespace <namespace> --approve
```

Approved upsert and delete stale rows:

```bash
turbo-search apply --plan <plan.json> --namespace <namespace> --approve --delete-stale
```

## Acceptance criteria

- Plans show stale row count and row IDs/details needed for deletion.
- Apply preflight shows whether stale rows would be retained or deleted depending on flags.
- Apply without `--delete-stale` performs zero delete calls.
- Apply without `--delete-stale` keeps stale rows visible in local state as retained stale rows.
- Apply with `--delete-stale` deletes only stale row IDs from the plan.
- If delete fails, local state is not updated as if the delete succeeded.
- Tests cover retained stale rows, explicit delete, delete failure, and no accidental deletes in preflight.

## Progress and notes

- 2026-06-20: Ticket opened because user explicitly chose delete-by-flag behavior.
- 2026-06-20: Implemented `--delete-stale` on `turbo-search apply` and passed the flag through preflight and approved apply.
- 2026-06-20: Added apply summaries for `delete_stale`, `delete_would_run`, `stale_rows_to_delete`, `stale_row_ids_to_delete`, `rows_deleted`, and retained stale counts.
- 2026-06-20: Added `TurbopufferWriter.delete_rows()` using the documented `write(deletes=[...])` row-delete shape.
- 2026-06-20: Approved apply now deletes exact stale row IDs only when both `--approve` and `--delete-stale` are supplied; otherwise stale rows are retained in local state as `retained_stale`.
- 2026-06-20: State is saved only after successful upsert/delete work. Fake delete failure coverage confirms previous state remains intact when delete fails.
- 2026-06-20: Updated README with stale delete preflight/live usage.
- 2026-06-20: Validation passed. Evidence: `.loom/evidence/2026-06-20-apply-stale-delete-guardrail-validation.md`.
- 2026-06-21: Final parent review found a spec mismatch: approved apply with `--delete-stale` and zero stale rows should fail before live work. Fixed `run_approved_apply()` to reject that case before credential access, embedding, writer construction, or state update. Added targeted test coverage in `tests/test_apply_cli.py`.

## Blockers

None.

## Residual risks

- Exact live turbopuffer delete compatibility remains unverified because this ticket intentionally used fakes/mocks and did not run live deletes. The writer uses the documented `ns.write(deletes=[ids])` shape.
