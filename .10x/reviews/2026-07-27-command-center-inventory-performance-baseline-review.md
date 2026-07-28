Status: recorded
Created: 2026-07-27
Updated: 2026-07-27
Target: c7fb4e9d036b3ec71d0600bfc8c5476a7dc3ab2a, a46977ae8f6b1495b84d615c0fdd2ded5e225c25
Verdict: pass

# Command Center Inventory Performance Baseline Review

## Target

Baseline driver, tests, evidence, and ticket in commits `c7fb4e9d` and `a46977a`.

## Findings

Initial independent review verified the full fixture and reproduced all timings/structural counts, but failed the harness because timed results were not semantically validated, event-loop output was hardcoded, delta-open instrumentation was incomplete, tests encoded behavior the implementation must remove, handler counting was inaccurate, and measured revision attribution was static.

The repair resolves every finding:

- every cold/warm operation validates its full-fixture result after timing;
- event-loop behavior is no longer emitted as a false dynamic measurement and is explicitly limited to source inspection;
- DuckDB, `os.open`, built-in `open`, and `io.open`/`Path.open` are instrumented and the zero-open result derives from every counter;
- permanent harness tests retain fixture/result/zero-delta invariants without requiring baseline-only repeated scans, row materialization, or legacy traversal;
- seven handlers versus eight operations is stated correctly; and
- fixed baseline attribution is separate from the actually measured checkout.

Runtime `src` remains byte/tree-identical to base `01f2d194`; the worktree was clean. Independent reduced-fixture reruns and injected-open checks passed.

## Verdict

Pass. The baseline is repeatable and suitable for the exact post-change comparison.

## Residual risk

Cold means process-cold rather than OS-cache-cold; RSS is process-wide; tracing is Python-level; five warm runs are a small sample; baseline event-loop behavior is source-structural rather than concurrent-load measured. These limits are recorded and do not block implementation.
