Status: done
Created: 2026-06-20
Updated: 2026-06-20
Parent: .loom/tickets/2026-06-20-generic-site-rag-incremental-plan-apply.md
Depends-On: .loom/tickets/2026-06-20-plan-cli-artifact-workflow.md, .loom/tickets/2026-06-20-local-applied-state-store.md, .loom/specs/generic-site-rag-incremental-plan-apply.md

# Apply CLI Incremental Upsert

## Scope

Add the `turbo-search apply` preflight and approved live upsert path for generic site plans.

In scope:

- Add `turbo-search apply --plan <plan.json> --namespace <namespace>` preflight mode.
- Add `--approve` to permit live embedding/upsert.
- Verify plan schema, namespace, state compatibility, and artifact hash before live work.
- In preflight mode, do not read credentials, load embeddings, or call turbopuffer.
- In approved mode, require `TURBOPUFFER_API_KEY` from the environment.
- Embed only chunks classified by the plan diff as new/changed/needs upsert.
- Upsert only those rows.
- Update local applied state only after successful live operations.
- Write clear output with embeddings count, rows upserted, stale rows retained/deleted, namespace, region, and state path.
- Use fakes/mocks for tests; do not run live writes.

Out of scope:

- Stale-row deletion; that is tracked by `.loom/tickets/2026-06-20-apply-stale-delete-guardrail.md`.
- Live generic apply unless explicitly approved by the user in the current conversation.
- Remote state.
- Namespace deletion or replacement.

## Command sketch

Preflight only:

```bash
turbo-search apply \
  --plan artifacts/site-crawls/scrapling-readthedocs-io-plan/plan.json \
  --namespace site-scrapling-readthedocs-io-v1
```

Approved live upsert:

```bash
turbo-search apply \
  --plan artifacts/site-crawls/scrapling-readthedocs-io-plan/plan.json \
  --namespace site-scrapling-readthedocs-io-v1 \
  --approve
```

## Acceptance criteria

- Apply preflight prints a clear plan summary and exits without credentials or live calls.
- Apply preflight fails before live work if artifact hash verification fails.
- Approved apply fails clearly if `TURBOPUFFER_API_KEY` is missing.
- Approved apply embeds only rows marked for upsert in the plan diff.
- Approved apply writes only rows marked for upsert.
- Local state is not updated if live upsert fails.
- Local state is updated atomically if live upsert succeeds.
- Tests use fake embedder/writer/state and verify exact embedding/upsert counts.
- No secret values are printed or written.

## Progress and notes

- 2026-06-20: Ticket opened for Phase 2 apply upsert behavior.
- 2026-06-20: Implemented `src/turbo_search/apply.py` with local-only saved-plan verification, artifact hash checking, namespace/state compatibility checks, chunks JSONL vs manifest verification, embedding-text hash verification, recomputed local diff, approved incremental upsert, and post-success state update.
- 2026-06-20: Added `turbo-search apply --plan <plan.json> --namespace <namespace>` preflight and `--approve` live path in `src/turbo_search/cli.py`.
- 2026-06-20: Extended `TurbopufferWriter` to accept an optional schema so generic site rows can use the generic-site schema while existing Jellyfish writes continue using the default schema.
- 2026-06-20: Added `tests/test_apply_cli.py` with fake embedder/writer coverage for preflight no-credential/no-live-call behavior, missing credential gate, incremental upsert row selection, state update after success only, artifact hash mismatch, namespace mismatch, incompatible state, and stale-row retention without delete.
- 2026-06-20: Updated README with apply preflight and approved apply usage.
- 2026-06-20: Validation passed. Evidence: `.loom/evidence/2026-06-20-apply-cli-incremental-upsert-validation.md`.

## Blockers

None.

## Residual risks

- Exact live turbopuffer SDK compatibility for the generic-site schema is still unverified because this ticket intentionally used fakes/mocks and did not run live writes.
- Stale-row deletion remains out of scope for this ticket and is tracked by `.loom/tickets/2026-06-20-apply-stale-delete-guardrail.md`.
