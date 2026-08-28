Status: recorded
Created: 2026-08-27
Updated: 2026-08-27
Ticket: .10x/tickets/done/2026-08-27-build-dormant-local-embedding-worker-prototype.md
Decision: .10x/decisions/buoy-prototypes-a-dormant-local-embedding-worker.md
Specification: .10x/specs/dormant-local-embedding-worker-prototype.md

# Dormant Local Embedding Worker Prototype Evidence

## Implemented boundary

Added one otherwise-unreferenced internal module, `src/buoy_search/retrieval/embedding_worker.py`. It provides the explicit internal `encode` prototype client and a subprocess entry point but is not imported or called by any established production module.

The worker is fixed to protocol 1, `BAAI/bge-small-en-v1.5` revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, float32, 384 normalized dimensions, and POSIX Unix-domain sockets. It keeps only the exact local model resident. It has no provider, credential, namespace, result, retrieval, reranking, telemetry, CLI, configuration, or environment activation path.

The implementation includes:

- deterministic implementation/model identity and private `~/.buoy/inference/v1-<identity>` paths;
- current-user-owned mode-0700 directories, mode-0600 one-link locks/state, a mode-0600 socket, no-follow opens, inode revalidation, no-overwrite state publication, and bounded interrupted-publication recovery;
- start and lifetime flock election, one detached isolated current-interpreter worker, readiness greeting before query transmission, same-user peer checks where the OS exposes them, one request per connection, and serialized execution;
- exact duplicate-rejecting canonical JSON with unsigned 32-bit framing, 1 MiB frames, 1–16 nonempty texts, 65,536 UTF-8 bytes per text, exact fields, bounded error categories, and independent finite/normalized/shape checks;
- exact-revision local-only model loading, offline and telemetry-disabled minimal child environment with no provider credential names, no fallback, and a fixed 300-second idle exit;
- stale socket/state cleanup only under lifetime authority, process/source identity mismatch rejection, disconnect safety, and worker-owned inode cleanup; and
- a conservative 100-byte socket-path bound so unsupported Unix socket paths fail before filesystem creation, spawn, model load, or query transmission.

## Tests

Added `tests/retrieval/test_embedding_worker.py` with 31 tests covering:

- framing, canonical JSON, duplicate/unknown fields, exact identity, text/frame limits, error allowlist, dimensions, finite numbers, bool rejection, and normalization;
- peer UID acceptance/rejection and the documented no-peer-API fallback;
- validate-before-create/spawn, detached minimal environment, exact local model constructor and normalized encode arguments;
- one-spawn reuse, five-client first-start coalescing, serialization, stale socket recovery, interrupted state publication recovery, disconnect/no replay, bounded greeting/response timeout-reset-truncation races, post-request no-retry/no-fallback behavior, lifetime-authoritative shutdown cleanup, model failure/no fallback, and the 300-second fake-clock idle contract;
- symlink, wrong-mode, hardlinked-lock, hardlinked-socket cleanup, regular-file-as-socket, overlong-path, bounded spawn failure, and incompatible-greeting fail-closed behavior;
- absence of query/vector payloads from runtime files; and
- static and isolated-subprocess dormancy of established production entry points.

Final full suites after the last source/test edit:

- Python 3.11: `Ran 1222 tests in 109.253s` / `OK`.
- Python 3.13: `Ran 1222 tests in 101.421s` / `OK`.

The only suite output outside success was the established pair of plan-cleanup warnings and one upstream lxml deprecation warning per runtime.

## Provider-free exact-model validation

Added explicit harness `tests/fixtures/embedding_worker_validation.py`. It uses fixed content-free queries, the exact cached model revision, local-only/offline controls, an isolated mode-0700 home, a credential-name-free child environment, fresh client processes, source/model-cache manifests, parent-observed process identity and timing, RSS inspection, and bounded cleanup. It invokes no provider, retrieval, namespace, catalog, telemetry-store, download, release, or deployment path.

One completed Darwin arm64 run reported:

- direct model construction plus encode: 1,221.113 ms;
- worker startup through ready state: 9,520.027 ms;
- first fresh client request: 1,865.642 ms;
- second fresh client request: 27.635 ms;
- identical worker PID across fresh clients;
- fresh clients did not import `sentence_transformers`;
- maximum in-process/worker vector delta: 0.0;
- ordered cosine ranking equal: true;
- worker RSS: 417,316,864 bytes, below the 4 GiB harness bound;
- source manifest unchanged: true;
- exact model-cache manifest unchanged: true; and
- clean bounded worker/socket/private-home cleanup: true.

The real-model harness uses a 15-second worker idle bound solely so explicit validation cleans up promptly. Production prototype code remains fixed at 300 seconds, covered with the fake clock. No latency release threshold or percentile claim is made.

## Reconciliation correction

Parent reconciliation correctly identified two implementation gaps before independent acceptance:

1. Connect errors were mapped, but a socket timeout/reset after connect could escape `_connect_and_encode`, and a post-request truncated response reached only an internal protocol exception before `encode` converted it. The corrected client now divides transport authority at the request boundary. Before any query byte is sent, timeout/reset/truncated greeting is `_Unavailable` and may enter the existing start/reuse logic; a complete malformed greeting is incompatible. From the first request byte onward, timeout is the allowlisted `busy_timeout`, reset/OSError is `internal_worker_failure`, and malformed/truncated protocol is `protocol_error`. No post-request failure retries, spawns, or falls back, preventing replay.
2. `run_worker` released its lifetime flock before closing the listener and unlinking its inode-bound socket/state. Shutdown now closes the listener and performs validated cleanup while lifetime authority is still held, releasing the flock only afterward. A focused test wraps the real listener, proves close precedes unlink, proves a competing lifetime acquisition remains `busy_timeout` during cleanup, and proves acquisition succeeds after return.

Three focused tests were added for greeting reset, response timeout, truncated response, visible post-request no-fallback behavior, and shutdown lock ordering (one test has three transport subcases). Final focused suites passed 28 tests under Python 3.11 and 3.13. Final full suites and compile/diff checks passed as reported above.

A second exact-model provider-free run after the correction reported startup 9,715.838 ms, first fresh client 199.586 ms, second fresh client 30.332 ms, identical PID reuse, no Sentence Transformers import in clients, vector delta 0.0, equal ranking, 491,962,368-byte RSS, unchanged source/cache manifests, and complete cleanup. These are separate observations, not a distribution or threshold.

## Independent prerequisite review repair

The genuine independent prerequisite review then blocked on three additional P1 findings. All three were confirmed and repaired without retrieve or product integration:

1. `_spawn_worker` now converts `subprocess.Popen` `OSError` into value-redacted `EmbeddingWorkerError("internal_worker_failure")`. The public-path test forces both pre-spawn probes unavailable, injects a raw sensitive spawn error, and proves the bounded category, no raw detail, no in-process model fallback, no socket/state, and no persisted query.
2. `_safe_unlink_socket` now requires `st_nlink == 1`, matching initial socket verification. The cleanup test hard-links the governed socket, invokes stale cleanup under lifetime authority, and proves fail-closed behavior with both names and link count two unchanged.
3. `_serve_connection` now returns whether request parsing accepted one valid embedding request. `run_worker` updates `last_accepted` only for that result, not merely for `accept()`. Fake-clock subcases prove handshake-only, malformed, and immediately disconnected connections invoke no model, do not reset activity, and exit at the original 300-second boundary.

Final focused suites passed 31 tests under Python 3.11 and 3.13. Final full suites passed 1,222 tests under each runtime as reported above. Compilation, frozen validators, diff hygiene, and no-staged-files checks passed.

A third exact-model provider-free run after these repairs reported startup 8,346.984 ms, first fresh client 155.536 ms, second fresh client 16.404 ms, identical PID reuse, no Sentence Transformers import in clients, vector delta 0.0, equal ranking, 516,374,528-byte RSS, unchanged source/cache manifests, and complete cleanup. It is another bounded observation, not a distribution or latency gate.

Independent rereview of the corrected bytes passed at `.10x/reviews/2026-08-27-dormant-local-embedding-worker-independent-review.md` with no unresolved significant finding.

## Other validation

Passed after implementation:

- focused tests under Python 3.11 and 3.13;
- compileall/py_compile under Python 3.11 and 3.13;
- `scripts/validate_ranking_contract.py`;
- `scripts/validate_ranking_promotion.py`;
- `scripts/c6_syntax_forecast.py validate`;
- wheel and sdist builds;
- isolated Python 3.13 wheel install and `buoy --help` / `python -m buoy_search --help` smokes under isolated homes;
- isolated wheel import of the dormant worker and wheel/sdist inventory checks;
- `git diff --check`; and
- no staged files.

One compound packaging command returned 127 only after all build/install/help/import checks passed because its final inventory step invoked unavailable `python` rather than `uv run python`. The inventory step was rerun with `uv run --python 3.13 python`, passed, and all temporary distribution/install/home paths were removed.

## Acceptance mapping

1. Dormant worker/protocol/path/lifecycle implementation: satisfied by the internal module and focused tests.
2. Existing behavior/public imports unchanged: satisfied by no production references plus isolated CLI dormancy tests and full suites.
3. Vector and ranking parity: exact real-model delta 0.0 and equal order.
4. Fresh-process reuse: same PID, no Sentence Transformers import in clients, separately reported first/second timings.
5. Election/fault/race behavior: focused concurrent, stale, disconnect, model-error, incompatible, and idle tests.
6. Privacy/path/protocol controls: focused hostile-path and protocol tests plus content-free runtime inspection and sanitized environment.
7. Five-minute idle: fixed 300-second constant and fake-clock exit test; bounded real harness uses 15 seconds only for cleanup.
8. Dual runtime/package/CLI: passed as reported.
9. Provider-free integration: no provider path, offline/local-only exact revision, unchanged source/cache manifests, isolated private home, bounded RSS and cleanup.
10. Independent review: satisfied by the post-correction pass at `.10x/reviews/2026-08-27-dormant-local-embedding-worker-independent-review.md`; no unresolved significant finding remains.

## Residual limits

- One real-model run on one Darwin arm64 host; Linux behavior is unit/source-covered but not retained as real-model evidence, and Windows is intentionally unsupported.
- Unix permissions cannot exclude a malicious process already running as the same effective user. Exact protocol and identity checks reduce but do not eliminate that boundary.
- The harness enforces offline library controls and executes no network/provider code, but it is not an OS packet/syscall sandbox; its zero network/provider counters are procedure/source assertions rather than packet-trace evidence.
- The first fresh client remained materially slower than the second despite not importing Sentence Transformers. This prototype proves reuse and a large second-client improvement but does not attribute that remaining first-client interval.
- Product activation, fallback, rollout, and latency gates remain intentionally undecided.
