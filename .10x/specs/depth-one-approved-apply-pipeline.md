Status: active
Created: 2026-07-14
Updated: 2026-07-14

# Depth-One Approved Apply Pipeline

## Purpose and scope

Overlap one ordered Turbopuffer upsert with preparation of the immediately following embedding batch, reducing successful approved-apply wall time without changing row identity, write order, deletion, state commit, locking, or preflight behavior.

This specification extends `.10x/specs/approved-apply-throughput-measurement.md`. “No parallel embedding” continues to mean only one encoder call may run; “no parallel remote writes” continues to mean only one writer operation may run. The new overlap is one encoder call concurrent with one remote upsert.

## Behavior

- Approved apply MUST retain one namespace lock across model creation, all embedding/upsert work, optional stale deletion, and local state commit.
- Embedding MUST stay on the coordinator/main thread so Torch MPS/CUDA execution is not moved to a background worker.
- A single-worker executor MUST perform remote upserts. At most one remote upsert may be running.
- The coordinator MAY embed only the batch immediately following the running upsert. Therefore memory is bounded to one in-flight write batch plus at most one newly prepared batch.
- Batch row order and remote upsert call order MUST match the existing serial implementation.
- Before submitting prepared batch N+1, the coordinator MUST await and confirm successful completion of upsert N.
- If upsert N fails while N+1 is embedding, that already-running encode MAY finish before the failure is observed. Its vectors MUST be discarded, N+1 MUST NOT be written, no later encode or write may start, stale deletion MUST NOT run, and local state/apply history MUST NOT be committed.
- If embedding fails, the implementation MUST await the already-running prior upsert so no executor work escapes the namespace-lock lifetime, then propagate the embedding failure. No later write, stale deletion, or local commit may occur.
- Stale deletion MUST remain serial and MUST begin only after every upsert future has completed successfully.
- Local state and apply history MUST remain one final commit after all remote upserts and optional stale deletion succeed.
- Zero-row and one-batch applies MUST behave equivalently to the serial path; they need not create overlap.

## Timing and progress

- Embedding and write durations MUST measure stage work independently; because stages overlap, their sum MAY exceed wall elapsed time.
- Final JSON/text timing MUST expose that depth-one pipelining was active and MUST retain existing timing fields and batch settings additively.
- Progress MUST count a batch/rows only after its remote upsert succeeds. Advisory timing/progress failures MUST NOT affect apply outcome.

## Serial fallback

- If executor creation fails before any remote operation, approved apply MUST fail without writes or state mutation; it MUST NOT silently change execution semantics.
- A private serial execution path MAY be retained for deterministic comparison/tests, but no new public flag is required unless implementation evidence establishes an operational need.

## Acceptance scenarios

### Ordered overlap

Given three write batches, when batch 1 is writing, batch 2 may encode; batch 2 is submitted only after batch 1 succeeds. The observed write order remains 1, 2, 3 and maximum simultaneous remote writes is one.

### Late write failure

Given batch 1 is writing while batch 2 encodes, when batch 1 fails, batch 2 may have completed encoding but is never submitted. No batch 3 encode, stale deletion, state commit, or apply-history commit occurs.

### Embedding failure with prior write

Given batch 1 is writing while batch 2 encoding fails, the coordinator waits for batch 1 to settle before leaving the lock, then reports the embedding failure. Batch 2 and later batches are never written and local state remains unchanged.

### Success

Given all upserts succeed, optional stale deletion runs afterward, local state commits once, and the summary reports completed rows, independent stage durations, wall elapsed time, and pipeline mode.

## Explicit exclusions

Concurrent remote writes, multiple queued prepared batches, multiple simultaneous encoder calls, retries, resumable partial-apply journaling, batch-size default changes, model/precision changes, deletion-policy changes, and remote operations during preflight.
