Status: active
Created: 2026-07-20
Updated: 2026-07-21
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

The bounded repair independently passed review and integrated at exact `develop` commit `0e6b97a0897ac7f7a82d073d851709951e0ea29e`. A fresh complete Step 2 preflight passed all 19 prescribed non-credential/non-model checks against that exact clean source, grant, retained plan/artifact/source/903-ID set, real canonical cache/README/license, absent local state, locked SDK, region, namespaces/card, cosine contract, fixed ledger, and evidence capacity.

The public `execute_experimental_baseline` entry point was then invoked exactly once. Approval A is consumed and MUST NOT be invoked again. The executor constructed the exact offline model and zero-retry provider, performed only target metadata slot 1 and catalog metadata slot 3, and failed closed because the catalog response omitted the required top-level `distance_metric` even though its returned vector schema projected `ann.distance_metric=cosine_distance`. Slots 2 and 4–26 remained unused; there were 2 reads, 0 writes, 0 deletes, 0 returned rows, 0 write-row positions, no pending record, and no DuckDB applied-state commit. The local state-root and persistent lock-file path were created by lock acquisition; the lock context exited and no forbidden cleanup occurred.

Complete evidence is at `.10x/evidence/2026-07-21-experimental-buoy-baseline-execution.md` and `.10x/evidence/.storage/2026-07-21-experimental-buoy-baseline-execution.json`. This ticket remains active pending independent evidence review. No retry, resume, cleanup, second invocation, or replacement approval is authorized. Approval B remains ungranted and C3 remains blocked.

## References

- `.10x/evidence/2026-07-20-experimental-buoy-baseline-approval-a-grant.md`
- `.10x/evidence/2026-07-20-experimental-buoy-baseline-source-pin.md`
- `.10x/evidence/2026-07-20-experimental-buoy-baseline-step-2-preflight.md`
- `.10x/evidence/.storage/2026-07-20-experimental-buoy-baseline-step-2-preflight.json`
- `.10x/evidence/2026-07-21-experimental-buoy-baseline-execution.md`
- `.10x/evidence/.storage/2026-07-21-experimental-buoy-baseline-execution.json`
- `.10x/reviews/2026-07-20-experimental-buoy-baseline-step-2-preflight-review.md`
- `.10x/reviews/2026-07-20-experimental-buoy-baseline-preflight-repair-review.md`
- `.10x/evidence/2026-07-20-experimental-buoy-baseline-repair-ratification.md`
- `.10x/evidence/.storage/2026-07-20-experimental-buoy-baseline-approval-a.json`
- `.10x/evidence/2026-07-20-c3-buoy-baseline-approval-checkpoint.md`
- `.10x/specs/experimental-buoy-baseline-executor.md`
- `.10x/tickets/done/2026-07-20-implement-experimental-buoy-baseline-executor.md`
- `.10x/evidence/2026-07-20-experimental-buoy-baseline-executor-implementation.md`
- `.10x/reviews/2026-07-20-experimental-buoy-baseline-executor-implementation-review.md`
- `.10x/tickets/2026-07-19-capture-current-repo-candidates-and-baselines.md`

## Progress and notes

- 2026-07-20: Opened after the user granted the exact prewritten Approval A contract via `Approve baseline write (Recommended)`. The immutable grant record/text hashes and truthful runtime-limited provenance are recorded. This record-only turn did not set source grant constants, read a credential or retained state, load/download a model, construct a provider client, make a live call, or mutate namespace/card/catalog/pending/DuckDB state. Step 1 awaits execution from an integrated record baseline; Step 2 remains gated on independent review and integration of Step 1. Approval B remains ungranted and C3 remains blocked.
- 2026-07-20: Step 1 implementation pinned only the exact 2,627-byte Approval A grant SHA-256 and its exact three-field provenance. Deterministic tests validate the checked-in record, reject each possible single-byte mutation across all 2,627 byte positions, and reject provenance/text mutations even with a substituted mutated-record hash. Local CPython 3.11 and 3.13 ranking validation and complete 495-test suites passed; CPython 3.13 distribution build and `git diff --check` passed. Evidence: `.10x/evidence/2026-07-20-experimental-buoy-baseline-source-pin.md`. No live entry point, credential, model, provider, retained plan/cache/state, or domain state was accessed.
- 2026-07-20: Independent Step 1 review passed exact head `f7694940d3b02e6a59d613270881e8fef29a0af5`; review: `.10x/reviews/2026-07-20-experimental-buoy-baseline-source-pin-review.md`. Step 2 remains blocked until this exact source-pin change integrates through a separate session.
- 2026-07-20: Step 1 integrated into `develop` at pinned commit `8c7750d84ebaf846ae519ccf164f2c7b72c9ec1c`. A fresh Step 2 non-credential/non-model preflight passed source/grant/plan/artifact/source/903-ID/local-state/SDK/region/namespace/card/fixed-slot/destination checks but found the exact cache manifest/license-literal mismatch and an inability to persist the specification's complete returned-row/applied-state-hash evidence from the public result. Per stop conditions, `execute_experimental_baseline` was not invoked: invocation count 0, credentials read 0, models loaded 0, provider clients/requests 0, and `/tmp/buoy-c1-state` remained absent. Evidence: `.10x/evidence/2026-07-20-experimental-buoy-baseline-step-2-preflight.md`. Ticket remains active pending independent evidence review and explicitly authorized repair; Approval B remains ungranted and C3 remains blocked.
- 2026-07-20: Independent review passed the mandatory pre-invocation stop and identified exactly three significant implementation defects: the cache-manifest algorithm does not reproduce the approved canonical pin; the literal license sentence rejects the exact pinned README's Markdown-linked MIT statement; and the public evidence omits immutable returned-row projections, observed schema/distance, and the applied-state hash needed without extra calls. Review: `.10x/reviews/2026-07-20-experimental-buoy-baseline-step-2-preflight-review.md`. The user explicitly ratified only the narrow repair of those three defects while preserving every existing identity, constant, operation ceiling, and safety boundary. Evidence: `.10x/evidence/2026-07-20-experimental-buoy-baseline-repair-ratification.md`. No repair or invocation occurred; Approval A remains exact, unchanged, and unspent, no new grant was created, the ticket remains active, Approval B remains ungranted, and C3 remains blocked.
- 2026-07-20: Implemented only the ratified repair: canonical path-sorted compact manifest entries now use `path`/`bytes`/`sha256` without changing the approved pin or cache; exact pinned README validation recognizes its Markdown-linked MIT statement while retaining the README hash and `license: mit`; and fixed-ledger evidence retains validated target/card projections, observed schemas/distances, and the reloaded applied-state hash without another request. Deterministic focused success/preflight/late-failure coverage passes 32 tests; after incorporating current `develop` commit `f85136659f7d9094f180b7da397c589d6f178ee8`, complete Python 3.11 and 3.13 suites pass 507 tests each; ranking/C6 validations, external distribution build, exact pin/budget assertions, and `git diff --check` pass. Evidence: `.10x/evidence/2026-07-20-experimental-buoy-baseline-preflight-repair-implementation.md`. No live entry point, credential, real model/cache, provider, or retained plan/state was accessed. Approval A remains exact and unspent; the ticket remains active pending independent review, hosted CI, protected integration, and a fresh complete preflight. Approval B remains ungranted and C3 remains blocked.
- 2026-07-21: Repaired only PR #75 review blockers. Added the actual compact 12-file/267,599,430-byte BGE cache authority whose exact canonical bytes reproduce the unchanged `5f783ebce23b6ac957d2741399b46e19502b1751acfd3c744b8c41103b138f35` pin; removed the test's patched expected manifest/README values; and changed evidence to hash the raw sanitized provider-returned target/card rows and retain raw provider schema/distance projections before any normalization/default injection. Success and final-card-failure tests compare evidence hashes to raw fake responses (including a provider-only `$dist` field), retain prior projections, and assert exact provider call counts with no evidence-only requests. Focused 32 tests and complete 507-test suites on Python 3.11/3.13, both ranking/C6 validators, external distribution build, authority hash check, and `git diff --check` pass. One read-only cache byte-hash inspection supplied the checked-in authority; no model was imported/loaded and no live entry point, credential, provider, retained plan/state, or domain state was accessed.
- 2026-07-21: Independent repair review passed exact head `8e146e2106841a90402c8ecbb34ea4ff71dc595e`; review: `.10x/reviews/2026-07-20-experimental-buoy-baseline-preflight-repair-review.md`. Approval A remains exact and unspent. A fresh preflight remains blocked until this reviewed repair integrates through a separate session.
- 2026-07-21: The reviewed repair integrated at pinned `develop` commit `0e6b97a0897ac7f7a82d073d851709951e0ea29e`. A fresh 19-check non-credential/non-model preflight passed exact clean source/grant/plan/artifact/source/903-ID/cache/README/license/local-state/SDK/region/namespace/card/cosine/ledger/evidence-capacity gates. The public executor was then invoked exactly once, consuming Approval A. It loaded the exact offline model, constructed the locked zero-retry provider, succeeded only target metadata slot 1 (unambiguous absence) and catalog metadata slot 3, then failed closed because catalog metadata omitted the required top-level `distance_metric`. Slots 2 and 4–26 were unused: 2 reads, 0 writes/deletes/returned rows/write-row positions, no pending, no DuckDB state, no retry/cleanup/resume/extra request. The state-root and persistent lock file were created; the lock context exited. Evidence: `.10x/evidence/2026-07-21-experimental-buoy-baseline-execution.md`. Approval A MUST NOT be invoked again; ticket remains active pending independent evidence review, Approval B is ungranted, and C3 remains blocked.
