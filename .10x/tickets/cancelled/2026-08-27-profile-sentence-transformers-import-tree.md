Status: cancelled
Created: 2026-08-27
Updated: 2026-08-27
Parent: None
Depends-On: .10x/tickets/done/2026-08-27-measure-current-provider-free-retriever-construction.md
Research: .10x/research/2026-08-27-current-provider-free-retriever-construction-findings.md, .10x/research/superseded/2026-08-27-sentence-transformers-import-profile-no-result.md
Execution-Evidence: .10x/evidence/2026-08-27-sentence-transformers-import-profile-failure.md, .10x/evidence/2026-08-27-ordinary-sentence-transformers-import-diagnostic.md
Review: .10x/reviews/2026-08-27-sentence-transformers-import-profile-failure-review.md

# Profile the Sentence Transformers Import Tree

## Outcome

Explain which transitive import/runtime-initialization components account for the current provider-free `sentence_transformers` import boundary observed at 7,633.771–7,840.623 ms. Produce bounded content-free attribution that can distinguish a narrow import fix from a persistent-process lifecycle decision.

This ticket measures imports only. It does not construct a model or retriever and does not authorize a production optimization.

## Execution contract

Use the current reorganized working tree and locked Python 3.13 environment. Bind exact source, lock, Python executable, package versions, platform/architecture, and automatic device environment identities before execution. Preserve the prior experiment's strict credential-free, telemetry-free, offline/network-denied, no-cache-mutation, external-temporary-harness, privacy, watchdog, descendant, cleanup, and no-retry controls.

The profiler MUST use only Python's standard-library `-X importtime` facility plus parent monotonic timing. No new dependency or production instrumentation is allowed.

## Preflight

Before consuming import observations:

1. Bind deterministic worktree/status and relevant source/lock manifests.
2. Bind Python and exact `sentence-transformers`, `transformers`, `torch`, numerical-library, and provider package versions without retaining paths.
3. Construct a minimal child environment by exact approved-key allowlist and exact known credential-key denylist intersection; inspect names only, never values.
4. Disable telemetry, force offline/local-only behavior, and enforce process-level network denial.
5. Verify repository, model-cache, and telemetry filesystem manifests before execution.
6. Run a non-import protocol self-test for launch, importtime parser behavior, malformed-row rejection, watchdog timeout, descendant termination, network denial, and cleanup. It MUST NOT import `sentence_transformers`, `torch`, or `transformers`.

Any failure stops before the import sequence.

## Observation sequence

Run exactly six fresh child processes in fixed order:

1. one discarded host warm-up; then
2. five retained import-profile observations.

Each child MUST execute exactly one `import sentence_transformers` under `python -X importtime`, with a parent monotonic interval around the complete child. It MUST NOT construct a model, retriever, provider client, query, embedding, or telemetry object.

Every child remains below 120.000 seconds elapsed and 4,294,967,296 bytes RSS. Timeout, limit hit, nonzero exit, malformed profile, descendant, network attempt, source/cache/telemetry drift, or uncertain cleanup aborts remaining observations. A failed child cannot be retried, replaced, or reordered.

## Attribution method

For each retained observation, record separately:

- parent-observed complete child duration;
- profiler-reported complete `sentence_transformers` cumulative import interval;
- exclusive/self import time for each public module name; and
- exact import row count.

Analysis MUST:

- rank exclusive/self time without summing cumulative intervals;
- aggregate exclusive/self time by top-level public module family while preserving an explicit `stdlib`, `native/other`, and unclassified bucket;
- retain all five observations rather than converting them into percentile or performance-target claims;
- report top contributors by range and consistency across observations;
- distinguish Python import attribution from CPU, I/O, dynamic-loader, device-runtime, or causal resource attribution; and
- avoid claiming that profiler-instrumented absolute duration equals the prior uninstrumented boundary.

Public module names and content-free timings may be retained. Raw stderr ordering, paths, environment values, process identifiers, private host/user data, and raw harness output MUST NOT be retained.

## Acceptance criteria

1. Preflight and non-import self-tests pass before warm-up authority is consumed.
2. Exactly one discarded warm-up and five retained fresh import profiles complete without retry under both limits.
3. Every retained profile parses completely and has one valid `sentence_transformers` root interval.
4. Five separate parent/root/import-row observations and bounded exclusive-time family attribution are retained without cumulative-time summation.
5. No model/retriever/provider/query/encode/retrieval/network/telemetry operation or source/cache/store mutation occurs.
6. Source/runtime/package/cache/telemetry identities remain exact before, between, and after children.
7. A dated research record states the dominant import boundaries, decision implications, and limits without authorizing implementation.
8. External harness/raw/profile artifacts are deleted and absence verified.
9. Independent review passes the method, parser, accounting, identities, privacy, cleanup, and interpretation.

## Evidence expectations

Record bounded identities; preflight/self-test results; six-process ledger; per-observation parent/root durations and row counts; exclusive-time module-family attribution; top public contributors; no-effect/source/cache equality; cleanup; and independent review.

## Explicit exclusions

Model or retriever construction; provider/client/catalog/content/network/credential operation; query or embedding; production instrumentation/change; dependency change; cache clearing/repair/download; telemetry/store access; forced device; cumulative-time sums; percentile/target claims; live retrieval; persistent-worker design or implementation; build/install; release/deployment.

## Blockers

None. This campaign is cancelled rather than resumed. Its one-shot harness methodology is superseded by `.10x/decisions/provider-free-local-diagnostics-separate-debugging-from-measurement.md`, and the successful ordinary diagnostic is current authority at `.10x/research/2026-08-27-ordinary-sentence-transformers-import-diagnostic.md`.

## Progress and notes

- 2026-08-27: Opened from the completed finding that process-cold, host-warm `sentence_transformers` import/runtime initialization measured 7.63–7.84 seconds while post-import model construction measured 0.31–0.44 seconds and fake wrapper construction remained below one millisecond. No profiling or import child ran in this ticket-authoring turn.
- 2026-08-27: Bound current source/lock/runtime/package/cache/telemetry state and passed exact-key credential environment, offline/network denial, standard-library importtime parser, malformed-input rejection, watchdog, descendant termination, cleanup, and state-equality self-tests before target execution.
- 2026-08-27: The discarded target warm-up then ended `child_nonzero_exit`. Execution stopped immediately with zero retained observations and no retry/replacement. No raw output, profile row, partial timing, RSS, or failure detail was retained. External artifacts were deleted and verified absent; protected roots were sandbox write-denied; diff hygiene passed and no files were staged. Evidence: `.10x/evidence/2026-08-27-sentence-transformers-import-profile-failure.md`. Research disposition: `.10x/research/superseded/2026-08-27-sentence-transformers-import-profile-no-result.md`. Ticket remains blocked and unclosed.
- 2026-08-27: Independent review passed the truthful fail-closed disposition but failed experiment acceptance and identified that the target statement was not contractually identical to production's exported-symbol import: `.10x/reviews/2026-08-27-sentence-transformers-import-profile-failure-review.md`. Sanitized follow-up confirmed the exact cause is unrecoverable under required artifact deletion; no dependency or sandbox cause is claimed.
- 2026-08-27: At explicit owner request, the parent ran exactly one ordinary provider-free diagnostic using production's exact `from sentence_transformers import SentenceTransformer` statement under `-X importtime`, resolving but not instantiating the symbol. It exited zero with 3,763 rows and a 9,444.291 ms profiler root; the largest individual exclusive rows were broad Transformers import machinery and `torch._C`. Raw output was deleted after sanitized parsing. Evidence: `.10x/evidence/2026-08-27-ordinary-sentence-transformers-import-diagnostic.md`.
- 2026-08-27: Owner directed that the blocking one-shot diagnostic machinery be superseded. Cancelled this campaign. Historical failure evidence/review remain truthful; current method authority is `.10x/decisions/provider-free-local-diagnostics-separate-debugging-from-measurement.md`, and current bounded attribution is `.10x/research/2026-08-27-ordinary-sentence-transformers-import-diagnostic.md`.

## Cancellation rationale

The campaign's failed five-profile acceptance criteria are intentionally abandoned, not waived or claimed complete. The ordinary diagnostic answered the immediate blocking question, while the active decision prevents local harness debugging from consuming future measurement authority. No product optimization is authorized by cancellation.
