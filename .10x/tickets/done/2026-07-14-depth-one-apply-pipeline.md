Status: done
Created: 2026-07-14
Updated: 2026-07-14
Parent: None
Depends-On: None

# Pipeline One Embed Batch Ahead of Apply Writes

## Scope

Implement `.10x/specs/depth-one-approved-apply-pipeline.md`: overlap main-thread embedding batch N+1 with a single ordered background remote write for batch N, with at most one prepared batch beyond the in-flight write.

## Acceptance criteria

- Main-thread embedding and exactly one background remote writer; no concurrent embeddings or writes.
- Stable batch/row order and memory bounded to one in-flight plus one prepared batch.
- On write failure, an already-running next encode may finish but is discarded and never written; no later work, stale delete, or state commit.
- On embedding failure, await the prior write before leaving the namespace lock; no later write/delete/commit.
- Progress counts only successful writes; independent stage timing remains accurate under overlap.
- Zero/one-batch behavior, preflight, plan integrity, deletion, and state semantics remain compatible.
- Deterministic ordering/concurrency/failure tests, full suite/build, no-live benchmark, and independent review pass.
- Live benchmark requires separate explicit namespace/write authorization.

## References

- `.10x/reviews/2026-07-14-post-optimization-performance-ux-review.md`
- `.10x/evidence/2026-07-13-live-dagster-throughput-benchmark.md`
- `.10x/specs/depth-one-approved-apply-pipeline.md`

## Progress and notes

- 2026-07-14: User authorized execution and ratified main-thread embedding with finish-then-discard behavior for the one already-running batch after a write failure.
- 2026-07-14: Implemented the depth-one executor, additive pipeline timing/text output, indexing documentation, and deterministic ordering/overlap/failure/zero/one-batch tests. Focused 38 tests, full 253 tests, build, lock, diff, and staged-diff checks pass. A five-run no-remote delayed-stage benchmark reduced median time from 1.190573s serial-equivalent to 0.792728s depth-one (33.42%). Evidence: `.10x/evidence/2026-07-14-depth-one-apply-pipeline.md`.
- 2026-07-14: Independent review passed with no blockers: `.10x/reviews/2026-07-14-depth-one-apply-pipeline-review.md`. Reviewer rerun measured a consistent 32.15% synthetic reduction. No live operation was run.

## Closure

Every acceptance criterion maps to deterministic tests and `.10x/evidence/2026-07-14-depth-one-apply-pipeline.md`; independent review passed. The active specification remains coherent with implementation.

## Retrospective

Keeping accelerator embedding on the coordinator while moving only remote writes to a single-worker executor provided overlap without adding model-thread or write-order risk. The important failure lesson is that cancellation is bounded rather than magical: one already-running encode may finish and must be discarded. That contract is captured in the focused specification and tests; no separate knowledge or skill record is needed. A live benchmark remains optional evidence requiring separate write authorization, not a closure requirement.

## Blockers

- None.
