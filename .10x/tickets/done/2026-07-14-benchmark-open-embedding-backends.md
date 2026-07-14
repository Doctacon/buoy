Status: done
Created: 2026-07-14
Updated: 2026-07-14
Parent: None
Depends-On: None

# Benchmark Open Embedding Backends

## Scope

Run a no-write bake-off of the five lanes ratified in `.10x/research/2026-07-14-open-embedding-backend-bakeoff-roster.md`: current Torch/MPS, Sentence Transformers ONNX, Sentence Transformers OpenVINO, FastEmbed ONNX, and MLX Embeddings. Use the retained real chunks and query parity; attempt ONNX CoreML EP only when exposed by a supported install.

## Candidate acceptance

Measure three warm full-corpus runs, one cold model-load duration, observational memory, normalized document-vector minimum cosine >=0.999, and exact ordered top-10 equality. A candidate reaches integration/package/fallback/plan-compatibility evaluation only if it first demonstrates a repeated-median embedding win. Promote no backend without passing both stages.

## References

- `.10x/reviews/2026-07-14-post-optimization-performance-ux-review.md`
- `.10x/research/2026-07-14-open-embedding-backend-bakeoff-roster.md`
- `.10x/evidence/2026-07-14-float16-embedding-inference.md`

## Progress and notes

- 2026-07-14: Web research completed and roster ratified by the user's explicit authorization to run the bake-off. Research intentionally excludes server wrappers and Rust/CoreML conversion projects from this first in-process comparison.
- 2026-07-14: Bake-off completed with no promotable candidate. Torch/MPS measured 60.75 rows/s; ONNX CPU 13.93; OpenVINO 24.34 and failed exact ordered top-10; MLX 20.05 and failed exact ordered top-10; CoreML terminated during warmup; FastEmbed exceeded the bounded runtime twice. Evidence: `.10x/evidence/2026-07-14-open-embedding-backend-bakeoff.md`.

## Closure

- Null promotion: retain Torch/MPS on this host/workload; no dependency or implementation change warranted.
- Evidence: `.10x/evidence/2026-07-14-open-embedding-backend-bakeoff.md`.
- Review: `.10x/reviews/2026-07-14-open-embedding-backend-bakeoff-review.md`.
- Retrospective: research expanded the roster before measurement; bounded failed lanes and strict provenance wording prevented unsupported backend and failure claims. Reusable methodology is retained in the evidence harness/wrapper; no additional skill or knowledge record is warranted.

## Blockers

- None.
