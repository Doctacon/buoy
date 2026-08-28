Status: done
Created: 2026-08-27
Updated: 2026-08-27
Parent: None
Depends-On: .10x/tickets/2026-08-24-measure-provider-free-retriever-construction.md
Research: .10x/research/2026-08-24-retrieve-command-outer-latency-attribution.md, .10x/research/2026-08-27-current-provider-free-retriever-construction-no-result.md, .10x/research/2026-08-27-current-provider-free-retriever-construction-findings.md
Execution-Evidence: .10x/evidence/2026-08-27-current-provider-free-retriever-construction-preflight-failure.md, .10x/evidence/2026-08-27-current-provider-free-retriever-construction.md
Review: .10x/reviews/2026-08-27-current-provider-free-retriever-construction-preflight-review.md, .10x/reviews/2026-08-27-current-provider-free-retriever-construction-review.md

# Measure Current Provider-Free Retriever Construction

## Outcome

Measure the current reorganized working tree's explicit retrieval preparation boundary without provider, credential, network, telemetry, query, embedding encode, or repository mutation. Separate three non-overlapping intervals: `sentence_transformers` import, production `SentenceTransformerEmbedder` construction, and fake-provider retriever/configuration construction.

This is a separately authorized successor to the consumed failed 2026-08-24 campaign. It MUST NOT reopen, retry, replace, or reinterpret the failed warm-up under the prior ticket.

## Owner-ratified execution contract

On 2026-08-27 the owner selected:

- current reorganized source rather than installed v0.6.3;
- exact before/after source and lock content identities rather than a historical release identity;
- production automatic device selection;
- one discarded warm-up followed by five retained fresh processes;
- a 120-second elapsed limit and 4,294,967,296-byte RSS limit per process; and
- strict provider-free, credential-free, telemetry-free, offline/network-denied execution.

## Preflight

Before model execution, the executor MUST:

1. Bind current tracked/untracked source state with `git status`, exact relevant source/lock hashes, and a deterministic changed-path/content manifest. Any source drift during the campaign fails execution.
2. Bind Python, platform/architecture, dependency versions, model identity/revision, precision, production automatic device class, and complete relevant local model-cache manifest without retaining private paths.
3. Prove the exact model assets are complete and readable under offline/local-only controls. No download, cache repair, cache clearing, or cache mutation is allowed.
4. Remove real provider credentials from child environments, disable telemetry, and enforce process-level network denial.
5. Create all harness/runtime artifacts under an owner-private temporary directory outside the repository.
6. Run a lightweight, non-model protocol self-test that proves child launch, sanitized JSON parsing, interval validation, watchdog enforcement, descendant detection, cleanup, and failure reporting. The self-test MUST NOT import or construct the model and does not consume warm-up/sample authority.

A failed preflight or self-test stops before the model sequence.

## Measurement method

Each model child is a fresh process and performs exactly these non-overlapping operations in source order:

1. Time import evaluation of `sentence_transformers`.
2. Time construction of the unchanged production `SentenceTransformerEmbedder` using the current configured model/revision/precision and automatic device behavior.
3. Time construction of current runtime configuration plus an injected fake provider boundary and retriever around the existing embedder.

The third operation MUST NOT call a real provider SDK/client factory, `HybridRetriever.from_config`, namespace builder, catalog/content operation, or network seam. No query, encode, retrieval, routing, reranking, evidence assessment, or output operation follows construction.

Retain the three intervals separately for each accepted sample. Do not add them, infer an end-to-end total, create a percentile claim, or establish a performance target.

## Sequence and limits

- Run exactly one discarded warm-up model child.
- If it succeeds, run exactly five retained model children in order.
- Every child MUST remain below 120.000 seconds elapsed and 4,294,967,296 bytes RSS.
- Timeout, RSS limit, nonzero exit, malformed output, descendant process, identity drift, cache mutation, or prohibited effect aborts all remaining children.
- No failed child may be retried, replaced, or reordered under this ticket.

## Privacy and side-effect boundary

Retain only content-free component timings, order, bounded runtime/model/device identities, source/lock/cache manifest digests, generic failure categories, and cleanup outcomes. Do not retain raw stdout/stderr, environment values, credentials, process IDs, private paths, host/user names, stack traces, model/cache paths, or unrelated cache identities.

No provider/catalog/namespace/content access, credential read, network attempt, telemetry/store operation, model download, cache mutation, source/test edit, build/install, global-tool operation, Git ref mutation, release, or deployment is authorized.

## Acceptance criteria

1. Preflight and non-model protocol self-test pass before model authority is consumed.
2. One discarded warm-up and five retained fresh model processes complete in order under both limits without retry.
3. Five rows contain three separate, non-overlapping content-free intervals.
4. Current source/lock/runtime/model/device/cache identities remain exact before, between, and after observations.
5. No provider, credential, network, telemetry/store, query/encode/retrieval, cache, repository, install, release, or deployment effect occurs.
6. A dated research record states bounded findings and limitations without becoming optimization authority.
7. External harness/raw/runtime artifacts are deleted and absence verified.
8. Independent review passes the execution method, identities, privacy, cleanup, and no-effect claims.

## Evidence expectations

Record source/lock/runtime/model/device/cache identities; preflight/self-test result; six-process start/terminal ledger without process identifiers; five three-interval rows; watchdog and prohibited-effect checks; cache/source equality; cleanup; and independent review.

## Explicit exclusions

Production instrumentation or optimization; provider/client/network call; query/embedding encode/retrieval; forced device; model/cache change; telemetry/database access; mode comparison; cold-host or percentile claim; live campaign; build/install; release or deployment.

## Blockers

None.

## Progress and notes

- 2026-08-27: Opened as a distinct successor after current trace analysis identified preparation as the dominant latency boundary and the prior no-retry campaign remained consumed and blocked. Added a non-model protocol self-test so harness defects stop before consuming model observations.
- 2026-08-27: Execution bound current source/lock/runtime/model/cache identities, then stopped in credential-removal preflight before launching even the non-model self-test. Zero model children started and no timing was retained. External harness artifacts were deleted and absence verified; no staged files exist. Evidence: `.10x/evidence/2026-08-27-current-provider-free-retriever-construction-preflight-failure.md`. Research disposition: `.10x/research/2026-08-27-current-provider-free-retriever-construction-no-result.md`.
- 2026-08-27: Independent review passed the truthful fail-closed/no-result disposition but found experiment acceptance unsatisfied and required the ticket to remain blocked: `.10x/reviews/2026-08-27-current-provider-free-retriever-construction-preflight-review.md`. Parent observed diff hygiene and no staged files.
- 2026-08-27: Sanitized diagnosis established a temporary-harness false positive: broad substring matching rejected an approved runtime-control key, not an observed credential. The owner explicitly authorized a narrowly corrected continuation using exact allowlist equality and exact known credential-key denylist intersection. No model authority had been consumed; all other controls remain unchanged.
- 2026-08-27: Corrected preflight and the complete non-model protocol/network/watchdog/descendant self-test passed. Exact source, runtime, model revision, automatic `mps` device, and 44-entry cache manifest were bound before model execution.
- 2026-08-27: Exactly one discarded warm-up and five retained fresh model processes completed in order with no retry, replacement, descendant, timeout, or 4 GiB limit hit. The five separate import/model/retriever intervals were retained without sums; source/cache/telemetry state remained equal after every child and terminally. Provider/query/encode/retrieval/telemetry/allowed-network counts were zero. External artifacts were deleted and verified absent. Evidence: `.10x/evidence/2026-08-27-current-provider-free-retriever-construction.md`. Research: `.10x/research/2026-08-27-current-provider-free-retriever-construction-findings.md`.
- 2026-08-27: Independent acceptance review passed with no findings and merge verdict OK: `.10x/reviews/2026-08-27-current-provider-free-retriever-construction-review.md`. Parent re-read all records, confirmed diff hygiene and no staged files, and closed the bounded research ticket.

## Closure mapping

Preflight/self-test, exact six-process sequence, limits, five independent timing rows, source/runtime/model/device/cache equality, prohibited-effect counts, bounded research interpretation, cleanup, and independent review are supported by `.10x/evidence/2026-08-27-current-provider-free-retriever-construction.md`, `.10x/research/2026-08-27-current-provider-free-retriever-construction-findings.md`, and the passing final review.

## Retrospective

Credential environment checks should compare exact approved and denied key identities; broad substring matching creates false positives without improving secrecy. The experiment narrowed explicit preparation from a coarse retriever constructor to transitive import/runtime initialization while proving direct wrapper construction negligible in this controlled provider-free seam.
