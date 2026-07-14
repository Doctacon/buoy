Status: recorded
Created: 2026-07-14
Updated: 2026-07-14
Target: .10x/tickets/done/2026-07-14-depth-one-apply-pipeline.md
Verdict: pass

# Depth-One Apply Pipeline Review

## Findings

Independent review verified main-thread embedding, one background writer, bounded depth, stable submission order, finish-then-discard behavior after a write failure, waiting for an in-flight write after embedding failure, executor shutdown inside the namespace lock, and no stale deletion or state commit after failure. Timing and progress count only confirmed writes and expose pipeline mode additively. Zero/one-batch, preflight, plan, model, deletion, and state behavior remain compatible.

Focused 38 tests and the full 253-test suite passed. Wheel/sdist build, lock, diff, and staged-file checks passed. The reviewer reran the no-live delayed-stage benchmark and observed a 32.15% median reduction, consistent with the recorded 33.42%; this proves overlap mechanics only.

## Verdict

Pass. No blockers.

## Residual risk

No live Turbopuffer/Torch benchmark was authorized. Real service and accelerator improvement remains unmeasured; the implementation does not claim the synthetic percentage as production performance.
