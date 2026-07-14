Status: recorded
Created: 2026-07-14
Updated: 2026-07-14
Target: current post-optimization Buoy codebase
Verdict: concerns

# Post-Optimization Performance and UX Review

## Top three

1. **Benchmark an open-source embedding backend.** Embedding remains 73.7% of measured Dagster apply time, while float16 parity succeeded but repeated throughput was neutral. Compare current PyTorch against viable MLX/ONNX paths using the same real-chunk parity/top-10/load/memory benchmark; promote nothing without a repeated-median win. Owner: `.10x/tickets/done/2026-07-14-benchmark-open-embedding-backends.md`.

2. **Pipeline one embedding batch ahead of one ordered write.** Current apply serializes 521.829 seconds embedding and 165.997 seconds writes. Keep exactly one remote write in flight and one prepared batch, preserving order, lock, failure cancellation, stale deletion, and final state commit. The theoretical workload ceiling is about 166 seconds; actual gain requires benchmark. Owner: `.10x/tickets/done/2026-07-14-depth-one-apply-pipeline.md`.

3. **Complete the explicit plan-to-retrieval handoff.** Live retrieval can silently use the demo namespace; preflight text omits selected plan/source and documented review fields. After float16, copy-ready commands must carry region, namespace, model, and precision. Owner: `.10x/tickets/2026-07-14-explicit-plan-to-retrieval-handoff.md`.

## Not promoted

Float16 and single-pass planning are complete. Conditional crawl caching, partial-apply journals, atomic corpus publication, applied-config persistence, and schema-capability caching are credible later candidates but rank below the three above on current evidence, breadth, or frequency of benefit.

## Limits

Performance evidence remains one M2 Pro and selected Dagster/retained-corpus workloads. No live retrieval latency or post-change live crawl timing was collected.
