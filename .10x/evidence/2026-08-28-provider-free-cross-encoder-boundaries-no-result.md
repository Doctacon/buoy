Status: no-result
Created: 2026-08-28
Updated: 2026-08-28
Ticket: .10x/tickets/done/2026-08-28-measure-provider-free-cross-encoder-boundaries.md
Decision: .10x/decisions/provider-free-local-diagnostics-separate-debugging-from-measurement.md
Research: .10x/research/2026-08-28-provider-free-cross-encoder-boundaries-no-result.md

# Provider-Free Cross-Encoder Boundary Measurement: No Result

## Disposition

The campaign stopped fail-closed during the separately authorized harness-debugging phase. No governed warm-up and no retained measurement process started. No timing row is retained or claimed.

The exact production `score()` path inherently created one standard-library `multiprocessing.resource_tracker` child. The ticket's governed contract says any descendant process aborts the sequence. Because debugging established that the first governed process would necessarily violate that condition, execution did not knowingly consume the one-shot governed sequence.

## Bound preflight identity

Preflight completed before model debugging and bound the following content identities:

- source manifest: SHA-256 `46bc5c1229579a651eceef8edbc00a05c1d5a1e96d295aedaa49cb0e4216fe1f`, 1,266 files;
- changed-path manifest: SHA-256 `a8af64b7eb3ec9d49a4ae39888a4bcb26ed2f9fe8cc0bd7edf4c3b414ce786e3`, two entries;
- `src/buoy_search/retrieval/cross_encoder.py`: SHA-256 `ed963371948f9c51fdbc7d25df4193613e7b2616f34ba18e7b7b2e01d2ba1674`;
- `pyproject.toml`: SHA-256 `29c69a012a4374b4a4f81328382fd42bb5662e5d14d378b74c7463dd7a5b500b`;
- `uv.lock`: SHA-256 `ad7508159bc00271b21fc598bad07b56045329c938ed4fbd37a5a18d71c4c254`;
- exact reranker-cache manifest: SHA-256 `2718f5e56aa65e85d7962f5adfc7e4454bbe91bffa82e79250e1cb57af89013d`, 26 entries, including six readable exact-revision snapshot entries; and
- model `cross-encoder/ms-marco-MiniLM-L-6-v2` revision `c5ee24cb16019beea0893ab7796b1df96625c6b8`, production CPU, max length 512, batch size 8, local-only safetensors, and remote code disabled.

Runtime identity was CPython 3.13.0 on Darwin arm64 with sentence-transformers 5.6.0, torch 2.12.1, transformers 5.12.1, and NumPy 2.4.6.

The child inherited the ordinary runtime environment after removing an exact 12-key credential denylist, removing Buoy telemetry activation, and adding offline and telemetry-disable controls. No credential value was inspected, printed, or retained. The harness and raw debugging material lived under one mode-private external temporary directory.

## Debugging and exact blocker attribution

Debugging and governed measurement authority were separate as required by the active diagnostic decision.

Two early debugging launches correctly tripped descendant detection before completing. The external harness was then diagnosed under debugging authority. Three complete dry observations of the exact import, construction, one-pair score, 24-pair score, and 49-pair score path succeeded and were discarded. They established stable synthetic input identity without retaining timings or scores:

- text identity SHA-256 `c60d42ee12dcaf48077d5e880ad11a8564d6384b9cfe3b0d9370b47ad4825b9f`;
- 13,229 deterministic UTF-8 bytes in the complete query/passage fixture;
- query/passage whitespace shape 9/33 words;
- pinned-tokenizer shape SHA-256 `98ac80f569de0d4bd3929d1cadf7b2aa7fdd64321d89e5bf2c67bbea5354ada6`; and
- paired token length 58 for the fixed synthetic passages.

Temporary stack attribution identified the descendant chain precisely:

1. production `_PinnedMiniLMReranker.score()` calls `sentence_transformers.CrossEncoder.predict(..., show_progress_bar=False)`;
2. `CrossEncoder.predict()` still constructs a disabled `tqdm.trange`;
3. tqdm constructs `TqdmDefaultWriteLock` and a multiprocessing `RLock`;
4. Python registers that semaphore and launches its standard `multiprocessing.resource_tracker` helper.

The helper was the only observed model-child descendant and exited with the model process. That bounded fact does not waive the ticket's unqualified no-descendant contract. Temporary command lines, process identifiers, stack traces, and paths were deleted and are not retained.

## Non-model self-test

The first self-test debug exposed a harness-only cleanup false positive: its process-table probe counted the probe itself when checking the orchestrator. The probe was corrected to exclude its own process before acceptance authority; this did not import or construct a model.

The final non-model self-test passed all checks:

- valid schema/parser acceptance;
- malformed protocol rejection;
- watchdog termination;
- descendant detection and process-group cleanup;
- synthetic loopback denial by the network guard;
- RSS-limit validation; and
- terminal child cleanup.

The synthetic loopback attempt was denied before connection; zero network operation was allowed.

## Governed sequence ledger

| Governed order | Role | Status |
| ---: | --- | --- |
| 1 | discarded warm-up | not started |
| 2 | retained 1 | not started |
| 3 | retained 2 | not started |
| 4 | retained 3 | not started |
| 5 | retained 4 | not started |
| 6 | retained 5 | not started |

There was no retry, replacement, reordering, timing retention, percentile, total, target, or optimization claim.

## Identity, effects, and cleanup

Source and exact cache manifests were equal before and after every completed dry observation and after the passing self-test. The failed early debug launches were followed by the same exact identity checks before later debugging. No source/test/model/cache mutation occurred during the external campaign.

The model-debug children observed:

- zero provider, catalog, namespace, content-retrieval, embedding-worker, telemetry, or allowed-network operation;
- zero loaded provider, catalog, embedding-worker, or Buoy telemetry module;
- zero credential key present from the exact denylist; and
- zero model download, cache repair, or remote-code path.

No live command, provider SDK/client, telemetry store, build/install, global tool mutation, Git ref mutation, release, deployment, or publication ran.

The runtime-owned resource tracker exited. The complete external harness, raw stderr/stdout, temporary stack material, identities file, and debug outputs were deleted. External directory absence and absence of a surviving resource tracker were verified.

## Acceptance disposition

Criteria requiring five retained rows, a six-process accepted ledger, and an independent performance conclusion are unsatisfied. Criteria for fail-closed behavior, truthful no-result retention, source/cache preservation, no prohibited external effect, and cleanup are satisfied. The ticket remains blocked pending an owner-approved descendant policy; this evidence does not authorize such a change.
