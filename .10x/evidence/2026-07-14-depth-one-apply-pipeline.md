Status: recorded
Created: 2026-07-14
Updated: 2026-07-14
Relates-To: .10x/tickets/done/2026-07-14-depth-one-apply-pipeline.md, .10x/specs/depth-one-approved-apply-pipeline.md

# Depth-One Approved Apply Pipeline Validation

## What was observed

Approved apply now embeds on the coordinator thread while exactly one single-worker future performs the prior Turbopuffer upsert. Before submitting a prepared batch, the coordinator confirms the previous future succeeded. Successful progress counts only confirmed rows. Final timing adds `pipeline_mode: depth_one`; text output renders `pipeline=depth_one`.

Deterministic tests establish:

- three batches preserve row order, every encode runs on the calling thread, every upsert runs off that thread, and maximum active remote writes is one;
- a late first-write failure allows only the already-running second encode to finish, then discards it, starts no third encode/write, emits no successful-row progress, and does not commit state;
- a second-encode failure waits for the prior write to settle before returning and does not commit state;
- executor creation failure occurs before encoding, remote writes, or state mutation;
- zero- and one-batch applies preserve behavior and expose pipeline mode;
- stale deletion remains after successful upserts and existing delete/state/lock tests remain green.

## No-remote benchmark

A deterministic delayed-stage benchmark compared the production pipeline against the same code with a synchronous executor, reproducing prior serial ordering. It used 16 one-row batches, 40 ms embedding delay, 20 ms write delay, and five runs per mode. Fake embedder/writer classes prevented external calls.

- serial median: 1.190573s;
- depth-one median: 0.792728s;
- median reduction: 0.397845s / 33.42%;
- remote calls: zero.

This validates overlap mechanics and the expected ceiling under controlled stage ratios. It is not a claim about live Turbopuffer latency, Torch/MPS throughput, or the Dagster workload. No live namespace operation was authorized or run.

Raw output: `.10x/evidence/.storage/2026-07-14-depth-one-apply-pipeline-benchmark.json`.
Reproduction script: `.10x/evidence/.storage/2026-07-14-depth-one-apply-pipeline-benchmark.py`.

## Validation

```text
PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests.test_apply_cli -q
Ran 38 tests; OK

PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover -s tests -p 'test_*.py' -q
Ran 253 tests; OK

uv build --out-dir /tmp/buoy-depth-one-build
Built buoy_search-0.2.1 wheel and sdist

uv lock --check
git diff --check
git diff --cached --quiet
All passed
```

## Limits

The controlled benchmark uses delays and fake local writers. The real improvement remains unmeasured; a live benchmark requires separate explicit namespace/write authorization. A remote batch can succeed before a later failure while local state intentionally remains uncommitted, matching pre-existing partial-apply semantics; resumable journaling is explicitly out of scope.
