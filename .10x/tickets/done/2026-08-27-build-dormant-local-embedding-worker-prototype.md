Status: done
Created: 2026-08-27
Updated: 2026-08-27
Parent: None
Depends-On: .10x/tickets/done/2026-08-27-measure-current-provider-free-retriever-construction.md
Decision: .10x/decisions/buoy-prototypes-a-dormant-local-embedding-worker.md
Specification: .10x/specs/dormant-local-embedding-worker-prototype.md
Research: .10x/research/2026-08-27-persistent-local-embedding-worker.md
Evidence: .10x/evidence/2026-08-27-dormant-local-embedding-worker-prototype.md

# Build the Dormant Local Embedding Worker Prototype

## Cold-start context

Retrieval preparation repeatedly pays 7.63–7.84 seconds of Sentence Transformers import/runtime initialization in short-lived processes. The owner asked to try keeping the process alive, selected a five-minute idle lifetime, visible worker failures, and embedder-only scope, and deferred all CLI/product activation decisions until after prototype testing.

The governing specification requires a dormant POSIX Unix-socket worker that owns only the exact pinned local embedder. Existing CLI/retrieval behavior MUST remain unchanged.

## Scope

- Implement the private internal worker protocol, path validation, client, detached lifecycle, startup election, readiness/identity handshake, serialized encoding, visible errors, and five-minute idle exit.
- Reuse established project patterns where they fit, without coupling inference to telemetry storage or creating a durable request queue.
- Add unit tests for framing, exact schema/bounds, vectors, paths, permissions, peer identity, spawn coalescing, stale/hostile state, crash/timeout/disconnect, idle races, privacy, and dormancy.
- Add a provider-free explicit validation harness for exact cached-model vector/ranking parity, fresh-process reuse, process/RSS bounds, cache/source equality, and separate first/second-client timing.
- Update focused internal documentation and durable evidence only as required by the governing records.

## Explicit exclusions

- Any CLI flag, environment activation, default, or dispatch integration.
- Product fallback behavior.
- Provider credentials/clients, namespace queries, retrieval results, routing service, reranker residency, apply/indexing activation, or telemetry transport.
- Multiple models/precisions, Windows, TCP/HTTP/gRPC, batching, pools, durable queues, dependency additions, downloads, installation, release, or deployment.

## Acceptance criteria

1. The implementation exactly satisfies `.10x/specs/dormant-local-embedding-worker-prototype.md`.
2. Existing CLI/retrieval/routing/apply behavior and public imports remain unchanged; dormancy audits prove no worker side effect outside explicit internal invocation.
3. Exact in-process and worker embeddings preserve shape, numerical parity, normalization, and ordered ranking behavior for bounded provider-free fixtures.
4. A fresh second client reuses the same worker identity without another target import/model construction; first and second timing are reported separately without a threshold claim.
5. Concurrent first clients elect one worker; startup, request, disconnect, crash, stale socket, incompatible worker, and idle races fail visibly and safely.
6. Private path ownership/type/mode/link checks and exact bounded protocol prevent unverified deletion/signaling, arbitrary payloads, persistence, raw errors, and provider/credential exposure.
7. Five-minute idle semantics pass under fake clock and bounded real-process validation.
8. Python 3.11 and 3.13 full suites, validators, compilation/static checks, wheel/sdist, isolated install, CLI/help smoke, and no-worker package dormancy pass.
9. Provider-free integration proves no provider/network/telemetry/download/cache/source/global-tool/ref/release/deployment mutation.
10. Independent review passes with no unresolved significant findings.

## Evidence expectations

- Exact changed paths and architecture map.
- Protocol/path/lifecycle/fault/privacy test mapping.
- Full dual-runtime outputs and exact test counts.
- Provider-free parity/reuse/timing/process/RSS/cache/source/dormancy observations with limits.
- Package and isolated-install inventory/smoke.
- No-staged-files and diff hygiene.
- Independent review, residual risks, closure mapping, and retrospective.

## Blockers

None. Independent post-correction rereview passed at `.10x/reviews/2026-08-27-dormant-local-embedding-worker-independent-review.md`. Product activation remains governed separately.

## Progress and notes

- 2026-08-27: Researched current source/records and open-source persistent model-serving/Unix-socket patterns. Owner selected five-minute idle, visible failure, and embedder-only scope, and deferred activation until after testing. Activated the focused decision/spec and opened this bounded executable ticket. No implementation occurred in this decision/spec/ticket-authoring turn.
- 2026-08-27: Owner explicitly authorized execution. Ticket moved to active and assigned to an implementation subagent with the governing decision, specification, research, and ticket.
- 2026-08-27: Implemented the dormant internal POSIX embedder worker, 25 focused tests, and the explicit provider-free exact-model harness. No CLI/config/retrieval/provider activation or fallback was added. Exact-model validation reused one 417,316,864-byte-RSS worker across fresh clients, produced vector delta 0.0 and equal ranking order, and measured 9,520.027 ms startup, 1,865.642 ms first fresh client, and 27.635 ms second fresh client with unchanged source/cache manifests and complete cleanup. Initial Python 3.11 and 3.13 suites each passed 1,216 tests; validators, compile checks, package builds, isolated wheel/help/import smokes, inventory, diff hygiene, and no-staged-files checks passed. Evidence is recorded at `.10x/evidence/2026-08-27-dormant-local-embedding-worker-prototype.md`. Independent review remains pending; ticket intentionally remains active and unmoved.
- 2026-08-27: Parent reconciliation found two confirmed pre-acceptance defects: post-connect timeout/reset could escape the bounded public error vocabulary, and normal worker shutdown released lifetime authority before listener/socket/state cleanup. Corrected the client to retry only pre-query greeting transport races and to convert every post-request timeout/reset/truncation to allowlisted visible errors without replay/fallback. Moved listener close and inode-bound cleanup inside lifetime authority. Added three focused tests (including three transport race subcases) proving bounded errors, no post-request fallback, close-before-unlink, lock exclusion through cleanup, and post-cleanup acquisition. Final focused suites passed 28 tests on Python 3.11/3.13; final full suites passed 1,219 tests on each runtime. A second exact-model run retained vector delta 0.0/equal ranking/same PID/no client model import, measured 9,715.838 ms startup, 199.586 ms first and 30.332 ms second fresh clients, observed 491,962,368-byte RSS, and left source/cache unchanged with complete cleanup. Ticket remains active for independent review.
- 2026-08-27: Parent independently reran the 28-test Python 3.13 focused suite and diff hygiene, inspected the corrected lifecycle/transport boundary, and recorded `.10x/reviews/2026-08-27-dormant-local-embedding-worker-parent-reconciliation-review.md`. The scheduled independent reviewer never started because the containing workflow exhausted its reported-token hard budget after implementation. Closure remained blocked on a genuinely independent post-correction review.
- 2026-08-27: The genuine independent prerequisite review ran and returned concerns on three P1 findings: raw `Popen` `OSError`, linked-socket cleanup, and invalid connections resetting idle activity. Confirmed and repaired all three without retrieve integration. Spawn `OSError` is now bounded/redacted with no fallback or persisted query; socket unlink requires link count one and preserves both hard links on failure; connection serving reports valid request acceptance and only that resets idle activity. Added three focused tests with handshake-only/malformed/disconnected fake-clock subcases. Focused suites passed 31 tests on Python 3.11/3.13; full suites passed 1,222 tests on each. A third provider-free exact-model run retained delta 0.0/equal ranking/same PID/no client model import, measured 8,346.984 ms startup, 155.536 ms first and 16.404 ms second fresh clients, observed 516,374,528-byte RSS, and left source/cache unchanged with complete cleanup.
- 2026-08-27: Independent rereview passed with no unresolved significant finding at `.10x/reviews/2026-08-27-dormant-local-embedding-worker-independent-review.md`. Acceptance criteria map to `.10x/evidence/2026-08-27-dormant-local-embedding-worker-prototype.md`; product activation remains a separate governed ticket.
- 2026-08-27: Retrospective: process-lifecycle safety depends on treating spawn errors as protocol failures, validating link count again at deletion time, advancing idle lifetime only for semantically accepted work, and keeping cleanup under lifetime authority. These invariants are preserved in the active prototype specification and focused regression tests; no generalized skill is warranted before a second independent worker implementation exists.
