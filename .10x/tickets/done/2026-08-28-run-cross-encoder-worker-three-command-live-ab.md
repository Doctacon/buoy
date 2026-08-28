Status: done
Created: 2026-08-28
Updated: 2026-08-28
Parent: None
Depends-On: .10x/tickets/done/2026-08-28-extend-default-worker-with-cross-encoder-scoring.md
Specification: .10x/specs/cross-encoder-worker-three-command-live-ab.md
Decision: .10x/decisions/buoy-runs-one-three-command-cross-encoder-worker-live-ab.md
Prior-Evidence: .10x/evidence/2026-08-27-experimental-retrieve-embedding-worker-ab.md, .10x/evidence/2026-08-28-default-worker-cross-encoder-scoring.md
Execution-Evidence: .10x/evidence/2026-08-28-cross-encoder-worker-three-command-live-ab.md
Research: .10x/research/2026-08-28-cross-encoder-worker-live-ab-findings.md
Review: .10x/reviews/2026-08-28-cross-encoder-worker-three-command-live-ab-review.md

# Run Cross-Encoder Worker Three-Command Live A/B

## Outcome

Build and validate a privacy-bounded successor live harness, then execute exactly one baseline/cold-worker/warm-worker automatic retrieval sequence using the fixed prior query and record redacted end-to-end parity, timing, worker reuse/RSS/cleanup, and source/cache integrity evidence.

## Scope

1. Create a new successor harness; do not reactivate or rewrite the retired historical experimental harness.
2. Implement exact preflight, source/runtime/package and dual-model-cache identity binding, compatible-worker absence, credential-name-only validation, telemetry/model-offline controls, private output modes, redaction, hashing, stop accounting, and cleanup.
3. Prove harness parsing, privacy, command accounting, no-fourth-call behavior, and failure stops with provider-free synthetic subprocesses.
4. Run focused schema-v2 worker/retrieve/fallback/provider-count/privacy tests, harness compile/self-test, diff hygiene, and zero-staged checks before live authority.
5. Execute exactly the specification's three fresh CLI processes in order with query `How is approximate vector recall evaluated?`:
   - in-process baseline with `--no-embedding-worker`;
   - default cold schema-v2 worker;
   - default warm schema-v2 worker.
6. Reduce/delete raw data after every command, retain only approved redacted values, release decoded objects before the next command and idle wait, and never retain credential/PID/path/content.
7. Verify within-campaign output/route/shape/count parity, worker identity/reuse/RSS/natural idle cleanup, source/cache equality, and exact external call accounting.
8. Write dated evidence and research with bounded interpretation, obtain independent review, and reconcile closure without authorizing another campaign or release action.

## Acceptance criteria

1. The successor harness and provider-free self-tests satisfy every preflight, privacy, command-ledger, stop, timeout, redaction, deletion, identity, and cleanup requirement before live authority starts.
2. Exactly three live automatic read-only commands run once each in baseline/cold/warm order; no retry, replacement, reorder, or fourth command occurs.
3. The baseline activates no worker. Cold/warm use one exact schema-v2 worker identity and warm reuses the resident embedding plus cross-encoder runtime.
4. Three zero exits, empty stderr, equal stdout/payload/route/shape hashes and lengths, five-hit/namespace-count parity are observed, or the exact mismatch/failure is retained and later commands stop as specified.
5. Provider operations remain established read-only catalog/content calls with no write, mutation, fallback duplication, or harness-side provider access.
6. Raw stdout/stderr and decoded provider-derived objects are destroyed after reduction at every command boundary; retained artifacts contain only specification-allowed redacted values.
7. Current source/lock/runtime/package and both exact model-cache identities remain equal before/after; telemetry/store, bytecode, download/cache-repair, build/install, staging, release, and deployment effects remain absent.
8. Worker reuse, bounded RSS, validated natural idle cleanup, external temporary-directory deletion, and zero surviving compatible worker state/process are recorded without PID/path retention.
9. Evidence/research report exact observations, mismatches, command consumption, provider/network/order confounding, and limits without percentile/SLA/causality/release claims.
10. Independent review passes command count/order, source-backed behavior, privacy, no-effects, identity equality, cleanup, evidence accuracy, diff hygiene, and zero staged files.

## Evidence expectations

- Preflight and provider-free harness self-test outputs.
- Exact immutable three-command ledger with consumed/not-started statuses.
- Redacted per-command timings/counts/hashes and parity booleans.
- Credential-name presence only; telemetry/offline controls; provider read-only operation accounting.
- Source/lock/runtime/package and embedding/reranker cache before/after digest equality.
- Content-free worker schema/reuse/RSS/idle-cleanup observations.
- Raw-file/decoded-object/external-directory deletion evidence.
- Independent review and final no-staged/diff checks.

## Explicit exclusions

Historical harness mutation; more/fewer/retried/reordered/replaced live calls after authority starts; new query; explicit namespaces; live telemetry; provider writes or management; retained result content; packet tracing; production behavior change; additional instrumentation; model/protocol/ranking/routing/evidence/output change; global install; release/deploy/publication; automatic further campaign.

## Assumption provenance

- **Record-backed:** prior fixed query/harness lessons, current default/opt-out behavior, schema-v2 scoring worker, exact provider-free parity, five-minute idle lifecycle, private IPC/no-persistence controls, and prior live output reduction fields.
- **Owner-ratified:** exactly three live read-only automatic commands; baseline/cold/warm order; reuse the exact prior query; no fourth call; separately bounded live evidence after implementation.
- **Blocked:** None before preflight. Any failed preflight stops with zero live calls; any post-authority failure consumes its ordinal and stops remaining calls.

## Blockers

None.

## Progress and notes

- 2026-08-28: Opened after the scoring-capable worker passed implementation, exact 1/24/49/108 parity, dual-runtime suites, packaging, isolated activation, and independent review. The owner selected the prior query and authorized the exact three-run successor campaign. No harness implementation or live provider call ran in this shaping turn.
- 2026-08-28: Added the new successor harness `tests/fixtures/cross_encoder_worker_live_ab.py` without modifying/reactivating the retired experimental harness. Added source-named tests for exact query/order/count, provider-free synthetic redaction/raw cleanup/stop classification, and final consumed-authority dormancy.
- 2026-08-28: Provider-free harness self-test, compilation, exact credential-name/dual-cache/runtime/source preflight, schema-v2 worker absence, `git diff --check`, zero staged files, and 196 focused worker/retrieval/provider-count/fallback/privacy tests passed before live authority.
- 2026-08-28: Exactly three live read-only automatic retrieve commands ran once each in baseline/cold/warm order. All completed with exit zero, empty stderr, five hits, three namespaces, five logical catalog reads, three namespace results, and identical stdout/payload/route/shape hashes. No retry, replacement, reorder, fourth command, fallback warning, or provider write occurred.
- 2026-08-28: Wall observations were 16,101.925875 ms baseline, 6,752.035625 ms cold worker, and 2,853.658708 ms warm worker. Cold/warm reused one matching schema-v2 worker; one post-command RSS observation was 691,650,560 bytes. Natural idle cleanup completed after 300,607.889708 ms without signaling.
- 2026-08-28: Source/changed-path/lock/runtime/package, both exact model-cache, and telemetry-store identities remained equal. Raw stdout/stderr and decoded objects were destroyed at each command boundary; external wrapper/harness directories were deleted; no compatible worker survived. Evidence: `.10x/evidence/2026-08-28-cross-encoder-worker-three-command-live-ab.md`. Research: `.10x/research/2026-08-28-cross-encoder-worker-live-ab-findings.md`.
- 2026-08-28: Retired the successor live entry point immediately after the consumed campaign. No post-campaign live command ran. The retired harness/provider-free self-test recompiled and passed; the focused suite passed 196 tests in 7.786 seconds; `git diff --check`, historical-harness no-diff, zero staged files, zero compatible workers, and external campaign-directory absence passed. Ticket remained active pending independent review; no files were staged or committed.
- 2026-08-28: Independent review inspected the governing records, harness, executor transcript/result, current source and dual-cache identities, privacy/no-effect boundary, worker cleanup, and Git state without running a live/provider command. It passed all ten criteria with merge/closure verdict OK: `.10x/reviews/2026-08-28-cross-encoder-worker-three-command-live-ab-review.md`.
- 2026-08-28: Closure reconciliation reran only provider-free harness self-tests/source-named tests, record/link checks, worker/external-artifact absence, historical-harness no-diff, `git diff --check`, and zero-staged checks. Exact authority remains consumed at three completed commands, all active references now use the done ticket path, and the ticket is closed.

## Closure mapping

1. **Provider-free preflight/self-test:** `.10x/evidence/2026-08-28-cross-encoder-worker-three-command-live-ab.md` records the pre-authority self-test, 196 focused tests, exact identity/cache/credential-name/worker-absence gates, private modes, diff hygiene, and zero staged files; independent review confirmed transcript ordering.
2. **Exactly three fixed commands:** The evidence immutable ledger and executor transcript record baseline, cold worker, and warm worker once each, all completed, with no retry, replacement, reorder, or fourth entry; `LIVE_AUTHORITY_CONSUMED = True` and source-named dormancy coverage prevent reuse.
3. **Baseline dormancy and worker reuse:** Evidence and review confirm no baseline worker, one matching schema-v2 cold worker, and warm reuse of its transient process/model residency without retaining PID/path.
4. **Exit/output parity:** Evidence records three zero exits, empty stderr, 20,738-byte identical stdout, five hits, three namespaces, and equal stdout/payload/route/shape/count identities; review mechanically matched the sanitized executor result.
5. **Read-only provider behavior:** The public retrieve-only harness, equal five logical catalog reads and three namespace results, empty fallback stderr, zero provider-write count, and reviewed fallback/provider-count contract support the specified logical boundary; physical SDK attempts remain explicitly unclaimed.
6. **Privacy and deletion:** Harness source, provider-free sentinel tests, sanitized transcript result, evidence, and review support per-command raw-file deletion, decoded-object release, approved redacted-only retention, outer-directory deletion, and absence of credential/content/PID/path leakage.
7. **Identity equality/no mutation:** Evidence and independent recreation confirm source, changed-path, lock, runtime/package/worker, embedding cache, reranker cache, and telemetry-store equality with no download, install, staging, release, deployment, or telemetry effect.
8. **Lifecycle cleanup:** Evidence and review confirm one reused worker, a bounded 691,650,560-byte RSS observation, natural 300,607.889708 ms idle cleanup without signaling, deleted external artifacts, and zero surviving worker state/process.
9. **Bounded interpretation:** `.10x/research/2026-08-28-cross-encoder-worker-live-ab-findings.md` preserves exact observations and network/order/RSS/physical-attempt limits without percentile, SLA, causal provider-adjustment, release, or follow-up authority.
10. **Independent review:** `.10x/reviews/2026-08-28-cross-encoder-worker-three-command-live-ab-review.md` passes command accounting, source-backed behavior, privacy, no-effects, identities, cleanup, evidence accuracy, diff hygiene, and staged state.

## Retrospective

The new campaign fixed the prior harness's source-manifest and decoded-object-lifetime weaknesses before consuming authority, then retired itself immediately after the exact three calls. Keeping live telemetry disabled preserved the no-store privacy boundary but leaves provider/network stages unattributed. The observed warm latency benefit is paired with approximately 691.7 MB of post-command worker RSS; both remain bounded single-sequence observations rather than targets. No additional live campaign or release action is authorized.
