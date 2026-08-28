Status: done
Created: 2026-08-28
Updated: 2026-08-28
Parent: None
Depends-On: .10x/tickets/done/2026-08-27-default-compatible-retrieve-embeddings-to-worker.md
Research: .10x/research/2026-08-28-post-worker-retrieval-latency-residuals.md, .10x/research/2026-08-28-provider-free-cross-encoder-boundaries-no-result.md, .10x/research/2026-08-28-provider-free-cross-encoder-boundaries-continuation-no-result.md, .10x/research/2026-08-28-provider-free-cross-encoder-boundaries-findings.md
Decision: .10x/decisions/provider-free-local-diagnostics-separate-debugging-from-measurement.md
Execution-Evidence: .10x/evidence/2026-08-28-provider-free-cross-encoder-boundaries-no-result.md, .10x/evidence/2026-08-28-provider-free-cross-encoder-boundaries-continuation-no-result.md, .10x/evidence/2026-08-28-provider-free-cross-encoder-boundaries.md
Review: .10x/reviews/2026-08-28-provider-free-cross-encoder-boundaries-review.md

# Measure Provider-Free Cross-Encoder Boundaries

## Cold-start context

Compatible query embeddings now run in a persistent worker, but the pinned local cross-encoder remains lazy in each short-lived CLI process. Old 295–397 ms rerank spans were collected after the same process had already imported Sentence Transformers/Torch for query embedding, so they cannot establish current process-cold reranker cost. The owner selected measurement before extending worker residency.

## Outcome

Measure the current exact production cross-encoder's provider-free process-cold/host-warm boundaries separately:

1. `sentence_transformers.CrossEncoder` import/runtime initialization;
2. pinned production reranker construction after import;
3. first one-pair production `score` call;
4. warmed bounded 24-pair retrieval score call; and
5. warmed bounded 49-pair routing score call.

The intervals remain separate and MUST NOT be summed into a production command total.

## Measurement identity

- Current working-tree source.
- `cross-encoder/ms-marco-MiniLM-L-6-v2`.
- Revision `c5ee24cb16019beea0893ab7796b1df96625c6b8`.
- Production CPU device, max length 512, batch size 8, local-only safetensors, no remote code.
- Fixed content-free synthetic query/passages with a recorded deterministic byte/token-shape identity. No provider-derived or retrieved content is used.
- One Darwin arm64 host unless execution records otherwise.

## Preflight and debugging

Before measurement authority begins:

1. Bind current source/lock/runtime/dependency/model/cache identities and changed-path manifest.
2. Verify the exact pinned model cache is complete/readable with no download, repair, clearing, or mutation.
3. Remove exact known credential keys from child environments, disable telemetry, enforce offline controls, and deny child network operations without changing the production CPU/model path.
4. Place harness/runtime artifacts in a mode-private temporary directory outside the repository.
5. Debug the exact target child and parser until one full dry observation succeeds reliably under `.10x/decisions/provider-free-local-diagnostics-separate-debugging-from-measurement.md`.
6. Run a non-model self-test for protocol parsing, interval ordering, watchdog, RSS, descendant, prohibited-operation, and cleanup checks.

Debug observations are discarded and do not consume the sequence below.

## Governed sequence

- Run exactly one discarded full model warm-up in a fresh process.
- Then run exactly five retained fresh processes in fixed order.
- No retained child may be retried, replaced, or reordered.
- Each child has a 120-second elapsed limit and 4,294,967,296-byte RSS limit.
- Timeout, nonzero exit, malformed output, interval overlap/order failure, identity drift, source/cache mutation, prohibited operation, failed process-group containment, failed process-group cleanup, or any surviving process aborts remaining children.
- Runtime-created descendant processes are permitted. The harness MUST keep the complete model-child lineage inside the monitored process group, apply the same network-denial and credential-free environment boundary to inherited descendants, kill the complete group on timeout or limit failure, and verify zero lineage processes survive after every sample.
- Descendant executable/module identity and cardinality are not acceptance constraints. The campaign measures the unchanged production runtime rather than attempting to allowlist implementation-detail helper processes.

Each child imports, constructs, and scores in the five exact non-overlapping intervals above. It validates score count/finiteness but retains no score value.

The 24-pair and 49-pair cardinalities represent current maximum retrieval and routing batches. Synthetic text shape makes these bounded compute observations, not production-content latency claims. The single-pair call intentionally captures first-inference initialization before warmed batch observations.

## Privacy and side-effect boundary

Retain only interval timings, fixed bounded runtime/model/device/text-shape identities, cardinalities, score-validation booleans, RSS bounds, source/lock/cache manifest digests, generic failure categories, and cleanup outcomes.

Do not retain raw stdout/stderr, environment values, credential names/values, PIDs, private paths, host/user names, stack traces, model/cache paths, token IDs, logits/scores, or unrelated cache identities.

No provider/catalog/namespace/content operation, query retrieval, embedding-worker operation, telemetry/store operation, model download/cache mutation, source/test edit, build/install, global tool operation, Git ref mutation, live campaign, release, deployment, or publication is authorized.

## Acceptance criteria

1. Exact preflight, debug separation, and non-model self-test pass before measurement authority.
2. One discarded warm-up and five retained fresh processes complete in order under both limits without retry.
3. Every retained row has five separate ordered non-overlapping intervals and valid score counts/finiteness for 1, 24, and 49 pairs.
4. Current source/lock/runtime/model/device/text-shape/cache identities remain exact before, between, and after observations.
5. Provider, credential, network, telemetry, worker, cache, repository, install, live, release, and deployment effect counts remain zero; each complete model-child process group is contained and leaves zero surviving lineage processes.
6. A dated research record states bounded findings and whether import/construction/first-inference or warmed scoring is the strongest candidate for residency, without authorizing implementation.
7. External raw/runtime artifacts are deleted and absence verified.
8. Independent review passes method, identities, privacy, sequence, cleanup, and no-effect claims.

## Evidence expectations

- Preflight/self-test and exact target debug completion.
- Six-process start/terminal ledger without PIDs.
- Five five-interval timing rows.
- Runtime/model/cache/text-shape identities and RSS observations.
- Prohibited-effect counts, source/cache equality, and cleanup.
- Bounded research interpretation and independent review.

## Explicit exclusions

Production instrumentation or optimization; worker protocol extension; reranker behavior/model/cardinality change; provider/network/live command; production-content benchmark; forced non-production device; cache/model/source mutation; telemetry database access; percentile/SLA/target; build/install/release/deploy.

## Blockers

None.

## Progress and notes

- 2026-08-28: Opened after post-worker residual analysis identified cross-encoder startup as the highest-priority unmeasured local candidate. Owner selected provider-free measurement before any worker extension. No model process or implementation ran in this ticket-authoring turn.
- 2026-08-28: Bound exact source, lock, runtime, model, CPU, synthetic-text, and 26-entry model-cache identities. Credential removal, offline controls, telemetry disablement, local-only asset completeness, private external harness placement, and network denial passed.
- 2026-08-28: Kept debugging separate from governed measurement. Two early debug launches tripped descendant detection; three later complete dry observations succeeded and were discarded. Temporary stack attribution proved the exact production first-score path creates a standard-library resource tracker through tqdm's multiprocessing lock even with `show_progress_bar=False`.
- 2026-08-28: Corrected a self-test-only cleanup probe that counted its own process-table helper. The final non-model parser, malformed-protocol, watchdog, descendant, denied-network, RSS, and cleanup self-test passed. Source and cache identities remained exact.
- 2026-08-28: Stopped fail-closed before the governed warm-up because the first governed process would knowingly violate the unqualified no-descendant contract. Zero governed processes started and no timing or score was retained. No provider/live/telemetry/cache/source/install/release effect occurred. External raw/runtime artifacts and the runtime helper were deleted and absence verified. Evidence: `.10x/evidence/2026-08-28-provider-free-cross-encoder-boundaries-no-result.md`. Research: `.10x/research/2026-08-28-provider-free-cross-encoder-boundaries-no-result.md`.
- 2026-08-28: Owner explicitly selected continuation with a narrow exception: each model child may create at most one exactly attributed standard-library `multiprocessing.resource_tracker` companion under the same CPython executable, provided it exits with its owner. Every other, extra, ambiguous, abnormal, or lingering descendant remains abort-worthy. The ticket returned to open before measurement authority; the original sequence remained entirely unconsumed.
- 2026-08-28: Continuation preflight re-bound exact current source/lock/runtime/model/cache/synthetic-fixture identities; credential removal, offline controls, network denial, no-staged-files, and the non-model protocol/watchdog/descendant/RSS/cleanup self-test passed. Debugging corrected monitor handling for process-table quoting and CPython's inherited `-B` flag without consuming model authority.
- 2026-08-28: The next exact-target debug launch exposed another direct child outside the sole permitted resource-tracker identity. The monitor rejected it and execution stopped fail-closed. Zero governed processes started; no timing or score was retained. Terminal source/cache identity equality, no staged files, process cleanup, and external artifact deletion passed. Evidence: `.10x/evidence/2026-08-28-provider-free-cross-encoder-boundaries-continuation-no-result.md`. Research: `.10x/research/2026-08-28-provider-free-cross-encoder-boundaries-continuation-no-result.md`. Ticket returned to blocked.
- 2026-08-28: Closure reconciliation confirmed that both retained campaigns are truthful no-results, criteria 2, 3, and 6 are unsatisfied, and the required independent review artifact is absent, leaving criterion 8 unsatisfied. The ticket remained active and blocked; it was not moved to `done`, and no active references required repair.
- 2026-08-28: Owner rejected descendant executable/module/cardinality allowlisting as immaterial overconstraint for this provider-free local benchmark. The contract now permits runtime-created descendants while requiring complete process-group containment, inherited network/credential boundaries, whole-group termination on timeout or limit failure, and zero surviving lineage processes after each sample. Both prior debug campaigns remain immutable no-results; the governed warm-up and five retained samples remained entirely unconsumed.
- 2026-08-28: Recreated a private external harness. An initial debug-only cleanup probe exposed and corrected a macOS process-group `PermissionError`; no measurement authority was consumed. The corrected preflight, non-model parser/watchdog/descendant/RSS/network/cleanup self-test, and exact-target debug command passed before the governed sequence.
- 2026-08-28: Exactly one discarded fresh-process warm-up and five retained fresh processes completed in order without retry, replacement, timeout, limit, identity, score, prohibited-effect, containment, or cleanup failure. Import/runtime measured 7,460.980291–7,928.117125 ms; post-import construction 72.913000–88.451625 ms; first one-pair score 24.548709–30.563000 ms; warm 24-pair score 45.996500–53.246459 ms; warm 49-pair score 88.842917–103.686750 ms. Intervals are not summed. Evidence: `.10x/evidence/2026-08-28-provider-free-cross-encoder-boundaries.md`. Research: `.10x/research/2026-08-28-provider-free-cross-encoder-boundaries-findings.md`.
- 2026-08-28: Source/cache identities remained exact before, between, and after observations; all prohibited-effect counts were zero; no staged files existed; complete process groups left zero survivors. External harness, result, raw/runtime, marker, and temporary directory artifacts were deleted and absence verified.
- 2026-08-28: Independent acceptance review inspected the executor transcript's final harness and sanitized success result, mechanically matched all retained timing rows, rechecked current source/cache identities and cleanup, and passed all eight criteria with merge/closure verdict OK: `.10x/reviews/2026-08-28-provider-free-cross-encoder-boundaries-review.md`.
- 2026-08-28: Closure reconciliation finalized the successful evidence/research records, preserved both prior no-result campaigns as immutable history, repaired ticket references to the done path, verified diff hygiene and zero staged files, and closed the ticket.

## Closure mapping

1. Preflight, debug separation, and the non-model self-test are supported by `.10x/evidence/2026-08-28-provider-free-cross-encoder-boundaries.md` and independently confirmed by the review.
2. The exact discarded warm-up plus five retained fresh-process sequence, limits, no-retry order, and cleanup are recorded in the evidence ledger and passed review.
3. Five separate adjacent-checkpoint timing intervals plus score count/finiteness checks are recorded in evidence/research and mechanically matched to the executor result by review.
4. Source, lock, runtime, model, device, fixture, and cache identity equality before, between, and after observations is supported by evidence and independent hash/cache checks.
5. Zero prohibited effects, inherited credential/network controls, complete process-group containment, and zero surviving lineage are supported by evidence and review.
6. `.10x/research/2026-08-28-provider-free-cross-encoder-boundaries-findings.md` records the bounded conclusion without authorizing optimization.
7. External artifact deletion and absence are recorded by evidence and independently checked by review.
8. `.10x/reviews/2026-08-28-provider-free-cross-encoder-boundaries-review.md` passes method, identities, privacy, sequence, cleanup, and no-effect claims.

## Retrospective

Descendant executable/module allowlisting was an unnecessary implementation-detail constraint for this provider-free local diagnostic. Process-group containment, inherited no-effect controls, whole-group termination on failure, and terminal zero-survivor checks provided the relevant safety boundary. Keeping the final harness and sanitized result inspectable in the executor transcript also allowed independent verification while honoring required deletion of raw external runtime artifacts.
