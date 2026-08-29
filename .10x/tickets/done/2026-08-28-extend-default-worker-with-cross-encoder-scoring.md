Status: done
Created: 2026-08-28
Updated: 2026-08-28
Parent: None
Depends-On: .10x/tickets/done/2026-08-28-measure-provider-free-cross-encoder-boundaries.md, .10x/tickets/done/2026-08-27-default-compatible-retrieve-embeddings-to-worker.md
Specification: .10x/specs/default-retrieve-cross-encoder-worker-residency.md, .10x/specs/default-retrieve-embedding-worker.md
Decision: .10x/decisions/buoy-keeps-the-pinned-cross-encoder-resident-in-the-existing-local-worker.md, .10x/decisions/buoy-defaults-compatible-retrieve-embeddings-to-the-local-worker.md
Research: .10x/research/2026-08-28-provider-free-cross-encoder-boundaries-findings.md
Execution-Evidence: .10x/evidence/2026-08-28-default-worker-cross-encoder-scoring.md
Review: .10x/reviews/2026-08-28-cross-encoder-worker-scoring-implementation-review.md, .10x/reviews/2026-08-28-cross-encoder-worker-scoring-final-review.md

# Extend Default Worker with Cross-Encoder Scoring

## Outcome

Extend the existing exact-compatible default retrieve worker with protocol-versioned, lazy, bounded cross-encoder scoring and route every eligible production retrieve cross-encoder seam through one command-scoped worker adapter with exact in-process parity and command-wide fallback.

## Scope

1. Version the worker protocol/readiness/path identity so embedding-only workers cannot satisfy the scoring-capable handshake.
2. Add a strict `score` request/response schema alongside unchanged encode semantics, with the specification's 108-pair, per-value, 8,388,608-byte aggregate-frame, finite-score, timeout, and redacted-error bounds.
3. Lazily load and retain the exact pinned CPU MiniLM cross-encoder inside the existing serial worker; do not load it for encode-only commands.
4. Preserve private Unix-socket, same-user, permission, election, lock, stale-state, credential-free/offline child environment, five-minute idle, accepted-request, and no-persistence controls.
5. Add one command-scoped worker-backed `CrossEncoderReranker` adapter and shared embed/score failure latch.
6. Inject the adapter into automatic prototype routing, automatic evidence assessment when scores are absent, and multi-namespace reranking/widening.
7. Add the smallest optional reranker-loader injection to `MultiNamespaceRetriever.from_configs` without changing omitted-argument library behavior.
8. Preserve exact in-process behavior for opt-out, custom embedding model, float16, unsupported platform, incompatible protocol, and fallback.
9. Update retrieve documentation for bounded local scoring, transient provider-derived passage IPC, lazy model residency, memory lifetime, opt-out, and fallback.
10. Add focused protocol, lifecycle, parity, integration, fallback, privacy/dormancy, packaging, and isolated-install tests.

## Acceptance criteria

1. **Protocol identity:** A new exact protocol and identity directory bind both embedding and cross-encoder identities. Old/malformed/mixed workers fail before query/passage IPC. Encode vectors remain numerically identical.
2. **Strict score framing:** Score requests accept exactly 1–108 ordered passages and enforce all schema, UTF-8, per-value, 8,388,608-byte aggregate-frame, model/revision, duplicate/unknown-field, timeout, truncation, and no-post-request-retry rules. Responses contain exactly one finite ordered score per passage or one bounded error.
3. **Lazy residency:** Worker startup/encode-only paths construct no CrossEncoder. First valid score constructs it once; later valid score requests reuse it in the same process. Both valid operations refresh the existing five-minute idle timer; invalid requests do not.
4. **Parity:** Provider-free 1-, 24-, 49-, and 108-pair worker scores match unchanged in-process scores within the existing numeric representation, and downstream routing selections, margins, rankings, evidence decisions, result order, serialized output, and telemetry semantics are unchanged. The source-governed exact-108 automatic-routing case remains worker-resident without warning or fallback.
5. **Complete integration:** Eligible automatic prototype routing, evidence fallback scoring, explicit/automatic multi-namespace reranking, and widening all use one command-scoped worker adapter. No-score paths issue no score request.
6. **Opt-out/ineligibility:** `--no-embedding-worker`, custom model, float16, unsupported platform, and incompatible identity keep both embeddings and reranking in-process. Expected ineligibility emits no warning and creates no worker state.
7. **Fallback:** First encode or score worker failure emits the existing warning exactly once, switches every later local inference operation in the command in-process, never retries IPC after request start, never repeats provider catalog/content operations, and preserves established double-failure taxonomy.
8. **Privacy/security:** The worker receives only bounded formatted texts, retains no request/response data, persists/logs none of it, exposes no values in state/errors, remains credential-free/offline, imports no provider/catalog/orchestration/telemetry-store module, and preserves same-user private path/socket controls.
9. **Lifecycle:** Existing election, stale cleanup, serial serving, five-minute lifetime, accepted-request semantics, timeout behavior, and complete socket/state/process cleanup continue passing under encode and score operations.
10. **Documentation:** Help compatibility remains unchanged; retrieval docs accurately describe the scoring extension, transient same-user IPC, lazy memory residency, opt-out, and visible fallback without promising an SLA.
11. **Validation:** Focused tests, complete Python 3.11 and 3.13 suites, packaging/build, isolated-install dormancy/activation, validators, diff hygiene, no-staged-files check, and independent review pass.
12. **No live effects:** No live provider command, provider write, model download/cache mutation, release, deployment, publication, global installation, or telemetry schema migration occurs.

## Evidence expectations

- Changed-file/diff summary mapped to this ticket and both governing specs.
- Protocol request/response and adversarial validation output.
- Lazy-load/reuse/idle/cleanup and no-persistence evidence.
- Exact provider-free score and downstream semantic parity results.
- Integration/fallback call-count and warning/taxonomy matrices.
- Credential/module/socket/path/state privacy inspection.
- Python 3.11/3.13 full-suite output, package build/contents, isolated-install checks, validators, diff hygiene, and zero staged files.
- Independent review with findings, verdict, and residual memory/privacy/platform risk.

## Explicit exclusions

Changing model/revision/device/precision/max length/batch size; changing candidate generation, route thresholds, fusion, coverage, evidence behavior, ranking, provider calls, output, warning text, telemetry schema, or idle duration; custom/float16/Windows worker support; separate service; eager reranker load; pools/concurrency; persistent caches/queues; provider credentials/clients or orchestration in worker; apply/index/evals activation; live A/B; performance target/SLA; global install; release/deploy/publication.

## Assumption provenance

- **Record-backed:** exact model/runtime costs, worker security/lifecycle, existing eligibility/fallback, maximum 108 routing score pairs, maximum 24 retrieval score pairs, current three cross-encoder seams, and in-process scoring contract.
- **Owner-ratified:** reuse the existing worker; lazy load; at most 108 passages per worker request to match the existing governed routing maximum; 8,388,608-byte aggregate frame; transient/no-log/no-persistence data handling; exact semantics; command-wide in-process fallback; opt-out entirely in-process; provider-free parity before any live work.
- **Blocked:** None. The owner selected one 108-passage request with an exact 8,388,608-byte canonical frame ceiling; chunking, routing-cardinality changes, and accepted fallback remain excluded.

## Blockers

None. After independent review established the source-governed 108-passage routing maximum, the owner explicitly chose one 108-passage worker request with an 8,388,608-byte aggregate frame rather than chunking or accepted fallback.

## Progress and notes

- 2026-08-28: Opened after the owner approved the focused same-worker residency design. Governing decision and specification are active. No implementation, model execution, provider call, build, or test ran in this shaping turn.
- 2026-08-28: Implemented schema-v2 scoring in the existing worker with complete embedding/reranker handshake identity, strict bounded frames, lazy exact MiniLM residency, serial reuse, finite score validation, redacted errors, unchanged encode semantics, and no request persistence.
- 2026-08-28: Added one command-scoped worker reranker and shared embed/score failure latch. Wired automatic prototype routing, evidence assessment, explicit/automatic multi-namespace reranking, and widening while preserving omitted in-process behavior and the existing warning.
- 2026-08-28: Added protocol/lifecycle/parity/integration/fallback/privacy tests and retrieval documentation. Provider-free exact cached-model worker parity passed for 1/24/49 pairs with maximum score delta 0.0, equal cache identity, complete cleanup, and no provider operation.
- 2026-08-28: Focused suites passed. Complete Python 3.11 and 3.13 suites each passed 1,265 tests. Offline package build/contents, isolated-wheel dormancy/activation, ranking contract/promotion validators, C6 forecast, diff hygiene, and no-prohibited-effect checks passed. No live command ran. Evidence: `.10x/evidence/2026-08-28-default-worker-cross-encoder-scoring.md`.
- 2026-08-28: Implementation is complete and remains active pending independent review; no files were staged or committed.
- 2026-08-28: Independent review found one blocker: source-governed automatic routing can produce 108 score passages, while the ratified worker request ceiling is 49, causing valid eligible routes to warn and fall back in-process. The review also found stale missing-model/provider-order documentation.
- 2026-08-28: Repaired the documentation to distinguish lazy worker scoring boundaries from in-process loading and to state that fallback never repeats provider operations. No runtime behavior changed. Marked the ticket blocked rather than silently widening the protocol, inventing chunking semantics, changing routing cardinality, or narrowing acceptance. Evidence was corrected; the original review record remains unchanged.
- 2026-08-28: Repair validation passed the source-named exact-108 routing test, a provider-free static check proving routing bound 108 versus worker request bound 49 plus corrected documentation, `git diff --check`, and zero staged files. Full runtime/package/isolated-install results were not invalidated because repair changed only docs and records.
- 2026-08-28: Owner confirmed that 108 is existing bounded routing work, not additional retrieval or scoring semantics, and ratified raising the worker request ceiling to 108 with an 8,388,608-byte aggregate frame. The ticket returned to open for runtime/test/evidence repair and fresh review.
- 2026-08-28: Raised only the strict worker score ceiling from 49 to 108 and canonical frame ceiling from 4,194,304 to 8,388,608 bytes. Updated strict 1/108/109 and inclusive-frame tests plus a source-named automatic-route integration proving all 108 passages remain on the worker with no warning or in-process fallback. Routing cardinality, batching, ranking, provider, output, telemetry, retry, privacy, and fallback behavior are unchanged.
- 2026-08-28: Provider-free exact cached-model parity passed for 1/24/49/108 with maximum absolute delta 0.0 at every cardinality, equal embedding/reranker cache manifests, zero provider/credential operations, complete worker-lineage cleanup, and external-harness deletion. Two earlier harness-debug attempts failed before a retained result because of an overlong private socket path and a transient startup/socket observation; their temporary artifacts and process lineages were removed.
- 2026-08-28: Focused suites passed 193 tests. Sequential Python 3.11 and 3.13 full suites each passed 1,268 tests. Offline build/package contents, isolated-wheel dormancy and fake-model 108-score activation, ranking validators, C6 forecast, compile, diff hygiene, and zero staged files passed. No live/provider command, download/cache mutation, global install, release, deployment, commit, or staging ran. Ticket remained open for fresh final review.
- 2026-08-28: Fresh independent final review reran focused and full dual-runtime suites, exact cached-model 1/24/49/108 parity, package/isolated-install checks, validators, compilation, privacy/cleanup checks, diff hygiene, and staged-state inspection. It confirmed both initial findings resolved and passed all twelve criteria with merge/closure verdict OK: `.10x/reviews/2026-08-28-cross-encoder-worker-scoring-final-review.md`.
- 2026-08-28: Closure reconciliation verified governing specs match schema-v2/108-passage/8,388,608-byte implementation, durable evidence maps every criterion, active references use the done path, `git diff --check` passes, and no files are staged. Ticket closed.

## Closure mapping

1. **Protocol identity:** `.10x/evidence/2026-08-28-default-worker-cross-encoder-scoring.md` records schema 2, distinct `v2-*` identity, complete embedding/reranker handshake binding, adversarial identity tests, and unchanged encode parity; final review independently passed criterion 1.
2. **Strict score framing:** Execution evidence and focused tests cover 1/108/109 cardinalities, 65,536-byte values, inclusive 8,388,608-byte canonical framing, finite ordered scores, malformed/truncated/timeout cases, and no replay; final review passed criterion 2.
3. **Lazy residency:** Worker lifecycle tests and isolated activation prove encode-only zero reranker loads, first-score one-time load, serial reuse, valid-request idle refresh, malformed-request non-refresh, and cleanup; final review passed criterion 3.
4. **Parity:** Provider-free exact cached-model observations show maximum score delta `0.0` for 1/24/49/108 pairs, equal cache identity, and exact-108 routing residency; complete semantic suites and final review pass criterion 4.
5. **Complete integration:** Source and tests bind one command adapter to prototype routing, evidence assessment, explicit/automatic multi-namespace reranking, and widening, while no-score paths stay dormant; final review passed criterion 5.
6. **Opt-out/ineligibility:** CLI matrix coverage preserves in-process behavior without worker state/warning for opt-out, custom model, float16, unsupported/incompatible paths; final review passed criterion 6.
7. **Fallback:** Focused and complete suites prove one existing warning, shared command latch, in-process continuation, no post-request IPC replay, no provider-operation duplication, and redacted `model_error` double failure; final review passed criterion 7.
8. **Privacy/security:** Evidence, no-persistence tests, exact parity inspection, private IPC controls, minimal child environment, content-free state, cache equality, and cleanup support criterion 8; final review passed.
9. **Lifecycle:** Existing and added election, serialization, stale cleanup, timeout, five-minute accepted-request idle, socket/state cleanup, and zero-survivor checks pass; final review passed criterion 9.
10. **Documentation:** `docs/retrieval.md` accurately describes lazy scoring, transient same-user IPC, provider ordering, no-repeat fallback, memory lifetime, opt-out, and no SLA; the initial documentation finding is resolved and final review passed criterion 10.
11. **Validation:** Execution and final-review records contain passing focused 193-test runs, full 1,268-test Python 3.11 and 3.13 runs, offline build/package and isolated-wheel checks, ranking validators, C6 forecast, compilation, diff hygiene, cleanup, and zero staged files; criterion 11 passed.
12. **No live effects:** Execution and both reviews record zero live/provider command, download/cache mutation, global installation, telemetry migration, release, deployment, publication, commit, or staging effect; criterion 12 passed.

## Retrospective

The original 49-passage assumption came from a measured scoring workload rather than the source-governed routing contract. Independent review correctly caught the existing 108-passage maximum before closure. Binding protocol limits to source-named invariants and testing the exact maximum prevented valid automatic routes from falsely warning and falling back in-process. The repaired implementation keeps existing scoring semantics intact while moving only bounded local inference into the resident worker. The separate lazy-load documentation finding also showed that provider-order claims must distinguish prototype routing from post-retrieval reranking.
