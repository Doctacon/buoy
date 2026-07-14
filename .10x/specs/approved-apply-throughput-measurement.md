Status: active
Created: 2026-07-12
Updated: 2026-07-12

# Approved Apply Throughput Measurement

## Purpose and scope

Make an approved apply's local embedding and Turbopuffer-write costs observable, while keeping their batch controls independent. This enables evidence-based tuning before any write concurrency is introduced.

## Behavior

- `buoy apply --approve` MUST retain `--batch-size` as the Turbopuffer write-batch size, with its current default of 64.
- It MUST add a positive `--embedding-batch-size` option, defaulting to 32 to preserve the documented Sentence Transformers computation default currently used implicitly.
- For each write batch, the embedder MUST receive the selected embedding batch size. A larger write batch MAY therefore contain multiple encoder computation batches.
- Approved apply progress MUST report cumulative embedding time, write time, completed/total rows, and completed/total write batches after each successful write.
- Final text and JSON apply summaries MUST include elapsed, embedding, and write durations plus the effective batch settings. Timing values are diagnostic observations, not guarantees or an ETA.
- Preflight MUST remain local-only, MUST not load the embedder, and MUST report no embedding or write timing.

## Constraints

- No change to model identity recorded in a plan.
- No parallel embedding, parallel remote writes, retry policy, remote service behavior, state-commit ordering, or deletion behavior.
- Existing `--batch-size` callers remain compatible.
- Timing/progress failures remain best-effort and cannot change apply outcome.

## Acceptance scenarios

### Approved apply

Given an approved plan with rows to upsert, when the user selects write and embedding batch sizes, then each encode call receives the selected encoder batch size, writes remain serial, and the final summary exposes measured totals and both batch sizes.

### Compatibility

Given no new option, when approved apply runs, then it retains a 64-row write batch and a 32-item embedding computation batch.

### Preflight

Given apply without `--approve`, when it runs, then no model or Turbopuffer writer is instantiated and no live timing values are emitted.
