Status: done
Created: 2026-06-20
Updated: 2026-06-21
Parent: none
Depends-On: .loom/specs/generic-site-rag-incremental-plan-apply.md, .loom/decisions/generic-site-rag-incremental-state.md, .loom/research/2026-06-20-incremental-rag-state-backend-research.md, .loom/knowledge/generic-site-rag-plan-apply-vocabulary.md, .loom/specs/generic-website-rag-dry-run-crawl.md

# Generic Site RAG Incremental Plan/Apply

## Scope

This parent ticket orchestrates the polished Terraform-like generic website-to-RAG workflow.

The desired end state is:

```bash
turbo-search plan --base-url <site> --out-dir <plan-dir> --json
# review Markdown/JSON artifacts

turbo-search apply --plan <plan-dir>/plan.json --namespace <stable-namespace>
# preflight only, no writes

turbo-search apply --plan <plan-dir>/plan.json --namespace <stable-namespace> --approve [--delete-stale]
# live apply, explicitly approved
```

The workflow must support incremental apply via a local applied-state manifest. Repeated applies should embed/upsert only new or changed chunks and should report stale rows. Stale rows are deleted only with an explicit delete flag.

This parent is an orchestration record only. Implementation should be done by child tickets.

## Product decisions already resolved

- State backend: local applied-state manifest first.
- State path direction: `.turbo-search/state/<site-id>/<namespace>/last-applied.json` plus history.
- State backend should be abstractable for future remote/shared state.
- Namespace strategy: stable namespace per site.
- Delete behavior: report stale rows by default; delete only with explicit `--delete-stale`.
- Content storage: store chunk text in turbopuffer for MVP retrieval/citation ergonomics.
- Review mode: Markdown/JSON artifacts first; no UI/TUI required for this plan.
- Live writes remain blocked unless the user explicitly approves the apply command in the current conversation.

## Child tickets and sequencing

### Phase 1 — Local data model and diff foundation

1. `.loom/tickets/2026-06-20-plan-artifact-manifest-model.md`
   - Define and implement plan/manifest/chunk JSON models.
   - Establish deterministic artifact hashing.

2. `.loom/tickets/2026-06-20-generic-site-stable-row-ids-and-schema.md`
   - Add generic-site row identity and schema metadata needed for incremental state/recovery.
   - Avoid page-source-hash-based IDs for generic site rows.

3. `.loom/tickets/2026-06-20-local-applied-state-store.md`
   - Implement local state load/save/history/atomic-update behavior.
   - Keep state separate from review artifacts.

4. `.loom/tickets/2026-06-20-incremental-plan-diff-engine.md`
   - Compare desired manifest to local state.
   - Classify first apply, unchanged, new, changed, stale, and retained-stale rows.

These four can be developed with fakes/no network and should land before any live apply work.

### Phase 2 — CLI surface

5. `.loom/tickets/2026-06-20-plan-cli-artifact-workflow.md`
   - Add `turbo-search plan` or equivalent plan artifact mode using existing Scrapling crawl code.
   - Ensure plan remains local-only.

6. `.loom/tickets/2026-06-20-apply-cli-incremental-upsert.md`
   - Add `turbo-search apply` preflight and approved live upsert path.
   - Embed/upsert only new/changed chunks.

7. `.loom/tickets/2026-06-20-apply-stale-delete-guardrail.md`
   - Add explicit stale-row delete behavior behind `--delete-stale`.
   - Ensure retained stale rows stay visible in future state/diffs.

### Phase 3 — Product hardening

8. `.loom/tickets/2026-06-20-plan-apply-docs-validation-review.md`
   - Update README/docs/skill guidance.
   - Add no-secret/no-live-call tests.
   - Add a small Scrapling docs plan smoke and mocked apply validation.
   - Perform adversarial review before marking this parent done.

9. `.loom/tickets/2026-06-20-generic-site-retrieval-smoke-evals.md`
   - Add or adapt retrieval/eval workflow for a generic applied site namespace.
   - This can follow apply implementation; it is not required before the first apply command exists, but it is required before calling the product polished end-to-end.

## Acceptance criteria

The parent is done when:

- All child tickets above are either done or explicitly cancelled/deferred with reason.
- The spec `.loom/specs/generic-site-rag-incremental-plan-apply.md` matches the implemented behavior.
- A no-live-call plan test passes for a local/faked crawl and for a small real Scrapling docs preview when network is allowed.
- Apply preflight can verify a plan without credentials and without turbopuffer calls.
- Approved apply uses environment credentials only and never records secret values.
- Mocked approved apply embeds/upserts only new/changed chunks.
- Mocked stale delete requires `--delete-stale`.
- Local applied state records active and retained-stale rows correctly.
- Existing Jellyfish retrieval/indexing tests continue to pass.
- Documentation clearly distinguishes plan, apply preflight, approved apply, and stale delete.

## Out of scope

- Running a live generic apply without explicit user approval.
- Deleting any existing turbopuffer namespace.
- Remote/shared state backend.
- Browser-rendered crawling/stealth crawling.
- Visual review UI or TUI.
- Local-content hydration cost optimization.

## Progress and notes

- 2026-06-20: User asked for a Loom plan and child tickets after choosing local applied-state manifest first.
- 2026-06-20: Research, decision, vocabulary, spec, parent ticket, and child tickets were created. No code implementation, credentials, embeddings, or turbopuffer calls were performed.
- 2026-06-21: All child tickets were implemented and marked done. The workflow now includes local plan artifacts, local applied state, incremental diffing, `turbo-search plan`, `turbo-search apply` preflight, approved incremental upsert, explicit `--delete-stale`, docs/skill guidance, and generic retrieval/eval dry-run support.
- 2026-06-21: Parent validation passed with 76 tests under both direct Python and uv, compile checks, apply preflight smoke, generic eval/retrieve dry-runs, secret-adjacent grep checks, and no staged files. Evidence: `.loom/evidence/2026-06-21-generic-site-rag-incremental-plan-apply-parent-validation.md`.
- 2026-06-21: Final parent review initially found one spec mismatch: approved `--delete-stale` with no stale rows did not fail. The implementation was fixed to reject this before credential access/live work and test coverage was added. Reviews: `.loom/reviews/2026-06-21-generic-site-rag-incremental-plan-apply-parent-review.md`, `.loom/reviews/2026-06-21-generic-site-rag-incremental-plan-apply-final-blocker-review.md`.

## Blockers

None for the local plan/apply workflow.

Live generic applies/deletes remain authority-gated and require explicit user approval for a specific site/namespace. Live turbopuffer SDK compatibility for generic upserts/deletes remains unverified by design.
