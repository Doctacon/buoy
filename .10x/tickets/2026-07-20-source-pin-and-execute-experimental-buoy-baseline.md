Status: open
Created: 2026-07-20
Updated: 2026-07-20
Parent: .10x/tickets/2026-06-28-repo-search-heavy-ranking-experiments.md
Depends-On: .10x/tickets/done/2026-07-20-implement-experimental-buoy-baseline-executor.md, .10x/evidence/2026-07-20-experimental-buoy-baseline-approval-a-grant.md

# Source-Pin and Execute the Approved Experimental Buoy Baseline

## Outcome

From the exact durable Approval A grant, first make the smallest independently reviewed and integrated source-pin change; then, from that exact reviewed commit after integration into `develop`, invoke the fail-closed executor exactly once and preserve complete success, failure, indeterminate, slot-accounting, and local/remote partial-state evidence. This ticket owns those two sequential steps as one baseline-compatibility outcome. Neither step authorizes Approval B or C3 retrieval.

## Scope

### Step 1 — source-pin, independently review, and integrate

- In a new `work/*` worktree based on current `develop` after the grant-record PR is integrated, set only `APPROVAL_A_GRANTED_RECORD_SHA256` and `APPROVAL_A_GRANTED_PROVENANCE` in `src/buoy_search/experimental_baseline.py` to the exact immutable grant pins:
  - record SHA-256: `46a44e9440425ef73c66e69d64d7e83a7c098ce0fa3f85f2caf7f8d7685cc5ec`;
  - provenance: `{"source_system":"pi","conversation_id":"runtime-id-not-exposed","message_id":"sha256:4b066f19c3331b0074d4548b691b293072a50406df6f0557fcdba8e3d3f25d74"}`.
- Keep `APPROVAL_A_TEXT`, `APPROVAL_A_TEXT_SHA256`, the grant JSON bytes, executor behavior, operation budgets, ordinary paths, dependencies, and defaults unchanged.
- Add or update only deterministic no-live tests needed to prove the exact checked-in grant record validates under those source pins and every changed byte/provenance/text mutation still fails closed.
- Run focused/full CI-equivalent validation without invoking the live entry point, reading credentials, loading a model, contacting the provider, or touching retained plan/state.
- Commit and push the bounded source/test/record diff, open a PR, obtain independent implementation review at the exact head, incorporate then-current `develop` if needed, rerun required CI, and have a separate integration session merge it into `develop`. The source-pin branch MUST NOT execute the live operation or merge its own PR.

### Step 2 — one live invocation from reviewed integrated source

- Start a fresh execution session from the exact `develop` commit that contains the independently reviewed source-pin merge. Record the integrated commit, source file bytes/hash, grant record bytes/hash, and exact provenance before any invocation.
- Before invoking live, use only non-model/non-credential inspection to confirm the exact grant record, source pins, retained plan/artifact/source/903-ID contract, cache ref/manifest/README/license hashes, local-state precondition, exact paths, locked `turbopuffer==2.4.0`, region, namespace/card identities, offline controls, and ability to persist secret-free complete evidence. Stop before invocation on any mismatch.
- Invoke `execute_experimental_baseline` exactly once with only the exact durable grant, retained plan, immutable cache, and local state paths. The invocation is the one authorized live operation even if it stops before the first provider attempt. Do not invoke it again under this grant.
- Preserve the executor's complete secret-free result or attached error evidence immediately. Record all 26 physical-attempt slots as attempted or unused, all counters, each exact/absent `rows_affected` marker/value, each redacted/absent billing marker/value, returned rows/counts, statuses, errors, and every known or indeterminate local/remote partial effect.
- Re-observe only the exact target namespace, exact generated catalog card, pending record, and DuckDB applied state as the executor contract allows and only within remaining fixed slots. Do not issue an extra provider request for evidence. Record exact applied-state/card revisions and compatibility only if the contract's success conditions prove them.
- Submit the resulting record-only evidence/ticket updates for independent review. C3 remains blocked until that review supports exact compatible-baseline evidence; success does not grant Approval B.

## Acceptance criteria

### Step 1 gate

- The checked-in immutable JSON grant remains exactly 2,627 UTF-8 bytes with SHA-256 `46a44e9440425ef73c66e69d64d7e83a7c098ce0fa3f85f2caf7f8d7685cc5ec`; its exact 2,206-byte Approval A text hashes to `bafc2500292bc8fcfc4aa806873782d43689330c704620f8981684a3796bfa10`.
- Only the exact record hash and exact three-field provenance are source-pinned; no caller-controlled authority, live CLI, alternate record, approval text, executor behavior, budget, fallback, dependency, ordinary path, or default is introduced.
- Focused exactness/mutation tests, full tests, ranking-contract validation, static/type/lint checks used by the repository, distribution build, and `git diff --check` pass without live/model/credential/domain-state activity.
- Independent review records PASS at the exact source-pin head, hosted CI passes that head, current `develop` is incorporated, and a separate integration session merges the reviewed change into `develop` before any live invocation.

### Step 2 gate and evidence

- The one invocation runs only from the exact reviewed integrated `develop` commit with the exact grant file and provenance pins; invocation count is exactly one, including any pre-provider abort.
- The operation never exceeds 26 fixed physical attempts, 10 reads, 16 writes, 904 attempted write-row positions, or 1,817 returned-row positions; unused slots are never reassigned.
- There are exactly 15 fixed content upsert slots (`14 × 64 + 1 × 7`) and at most one exact conditional card-upsert slot. There are zero retries, pagination calls, schema/signature fallbacks, cleanup/rollback calls, or row/namespace/card deletes.
- Evidence maps every slot to attempted or unused and preserves exact request/response accounting, redacted billing presence/value, actual or explicitly absent `rows_affected`, returned-row positions, all partial/indeterminate outcomes, and the unknown-dollar-price limit.
- On content mismatch there is no catalog mutation or local applied-state commit. On catalog mismatch there is no local applied-state or card-success commit. Pending and every possible remote/local partial effect are preserved and reported without cleanup or retry.
- Compatible-baseline success is claimed only if both bounded target reads match exactly all 903 intended rows, both exact-card reads match the intended stable card revision, exact schema/cosine/source/model/license compatibility holds, the 903-row local applied state commits, the pending record is removed in the specified order, and independent review passes the complete evidence.
- Approval B remains explicitly ungranted and C3 remains blocked after this ticket unless and until the separate Approval B checkpoint is granted.

## Stop conditions

- Stop Step 1 if the grant record bytes, text hash, timestamp/actor/provenance, governing spec, implementation, or reviewed implementation head differs from the recorded authority. Do not rewrite or normalize the grant JSON to make it fit.
- Stop before live invocation unless the source-pin PR independently passed review and CI and was merged by a separate integration session into `develop`; a PR head, unreviewed branch, local patch, merge candidate, or self-merge is not executable authority.
- Stop before invocation on any source/grant/plan/artifact/source/model/revision/license/cache/local-state/schema/distance/row/card/count/budget/path mismatch, missing evidence destination, dirty executable source, or inability to enforce the exact fixed-slot ledger and `max_retries=0`.
- Once the live entry point is invoked, the one-operation authority is consumed regardless of whether it stops before credential access, model construction, the first provider attempt, or later. Do not rerun, retry, resume, compensate, roll back, clean up, or spend unused slots without a new exact approval.
- On any failed, timed-out, malformed, ambiguous, missing-accounting, partial, or indeterminate attempt, record the evidence and stop exactly as the executor contract requires. Never infer failure as absence of remote effect.
- Never delete a row, namespace, card, pending record, or applied state except the executor's success-only pending removal already mandated by the active contract. Never operate on another namespace/card or use another model, region, plan, artifact, source commit, SDK version, or state root.
- Stop if evidence cannot remain secret-free. Never persist credentials, tokens, headers, account identifiers, or raw request objects.
- Do not perform Approval B/C3 retrieval, recrawl/replan, another baseline attempt, default/catalog promotion, or any follow-on operation under this ticket.

## Explicit exclusions

Approval B; C3 raw-candidate retrieval; any ANN/BM25 capture; a second invocation; retry/resume; deletion/cleanup/rollback; other namespace/card/model/region/source/plan/artifact/state; recrawl/replan; dependency/lockfile/default/product/promotion changes; ordinary apply/retrieval changes; dollar-price inference; self-review or self-merge.

## Evidence expectations

- Step 1: exact changed files/diff; source and grant SHA-256 values; focused mutation/full/ranking/build/diff validation; no-live attestation; PR/head/hosted CI; independent review; separate integration commit on `develop`.
- Step 2: invocation timestamp/actor/host and exact integrated commit; clean-source and grant pins; non-secret preflight results; one-invocation attestation; full 26-slot attempted/unused ledger; request/write/read/delete counters; all redacted response/error/billing/`rows_affected` fields; target/card verification; pending and DuckDB state; all partial/indeterminate effects; unknown-dollar-price limit; no-delete/no-retry/no-other-namespace proof; independent evidence review.

## Blockers

No semantic blocker remains for Step 1 after `.10x/evidence/2026-07-20-experimental-buoy-baseline-approval-a-grant.md` is reviewed and integrated. Step 2 is mechanically blocked until Step 1 independently passes review and CI and a separate integration session merges the exact reviewed pins into `develop`. Approval B remains ungranted and is outside this ticket.

## References

- `.10x/evidence/2026-07-20-experimental-buoy-baseline-approval-a-grant.md`
- `.10x/evidence/.storage/2026-07-20-experimental-buoy-baseline-approval-a.json`
- `.10x/evidence/2026-07-20-c3-buoy-baseline-approval-checkpoint.md`
- `.10x/specs/experimental-buoy-baseline-executor.md`
- `.10x/tickets/done/2026-07-20-implement-experimental-buoy-baseline-executor.md`
- `.10x/evidence/2026-07-20-experimental-buoy-baseline-executor-implementation.md`
- `.10x/reviews/2026-07-20-experimental-buoy-baseline-executor-implementation-review.md`
- `.10x/tickets/2026-07-19-capture-current-repo-candidates-and-baselines.md`

## Progress and notes

- 2026-07-20: Opened after the user granted the exact prewritten Approval A contract via `Approve baseline write (Recommended)`. The immutable grant record/text hashes and truthful runtime-limited provenance are recorded. This record-only turn did not set source grant constants, read a credential or retained state, load/download a model, construct a provider client, make a live call, or mutate namespace/card/catalog/pending/DuckDB state. Step 1 awaits execution from an integrated record baseline; Step 2 remains gated on independent review and integration of Step 1. Approval B remains ungranted and C3 remains blocked.
