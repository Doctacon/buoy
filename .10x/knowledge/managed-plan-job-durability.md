Status: active
Created: 2026-07-24
Updated: 2026-07-24

# Managed Plan-Job Durability and Artifact Publication

Buoy managed planning separates logical plan identity from safe physical production.

- CLI and managed jobs share one planning orchestration service; callers adapt output/progress, not source semantics.
- Durable state uses exact transition tables, record-first sequence commits, append-only events, recovery reconciliation, one inter-instance mutation lock, and one lifetime service-owner lock.
- Every persisted record is bound to its filename/job ID and opened no-follow with private regular single-link and inode checks.
- Configured state/artifact roots are reopened component-by-component and compared to initialized inode identities; one-shot absolute-path `O_NOFOLLOW` does not protect intermediate components.
- Managed source work occurs in a private staging directory. After complete normal artifact verification, only `plan.json`, `manifest.json`, `chunks.jsonl`, `summary.json`, and `pages/` are copied into the held final job-directory descriptor using exclusive no-follow regular-file operations, fsyncs, and source/destination hashes.
- Persisted artifacts contain logical final paths; temporary staging or descriptor aliases never enter logical source, namespace, document, chunk, or plan identity.
- One-active enforcement must cover multiple service/store instances, not just one Python object.
- SSE observes durable events and never owns execution. Terminal closure requires a final durable drain after the terminal state snapshot.
- Browser polling, previews, and stream callbacks need monotonic request generations and sticky terminal state so stale asynchronous completions cannot regress operator truth.
- Platform incapability is a dedicated pre-construction result, never a generic integrity or `OSError` fallback. Probe mandatory descriptor primitives before creating stores, roots, workers, adapters, providers, or models; all tamper, malformed-state, permission, durability, ownership, and artifact failures remain fail-closed.
- Bounded append-only progress reserves one coalescing marker and one terminal slot. Skipped callbacks do not touch records, timestamps, sequences, event logs, or observer conditions; legacy over-limit histories remain readable.
- Graceful shutdown separates the start-prohibiting gate from completion. Concurrent waiters block through active work and cleanup; every descriptor/lock/handle/notification cleanup is attempted independently, the first failure is propagated, and repeated application lifespans must reset capability state from current platform evidence.

Use these patterns for future local managed workflows; do not weaken them into pathname-only preflight checks, in-memory-only locks, generic-error degradation, lossy audit rewriting, or resume/retry behavior without a new lifecycle specification.
