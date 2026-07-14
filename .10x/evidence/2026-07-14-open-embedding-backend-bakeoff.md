Status: recorded
Created: 2026-07-14
Updated: 2026-07-14
Relates-To: .10x/tickets/done/2026-07-14-benchmark-open-embedding-backends.md, .10x/research/2026-07-14-open-embedding-backend-bakeoff-roster.md

# Open Embedding Backend Bake-off

## What was observed

On an Apple M2 Pro / 16 GB host, the current Sentence Transformers Torch/MPS float32 path remained the fastest viable lane over the same 1,024 retained Iceberg chunks, batch 32, and query used by the float16 work.

| Lane | Median | Rows/s | Min document cosine | Exact ordered top-10 | Outcome |
|---|---:|---:|---:|---|---|
| Torch/MPS float32 | 16.857s | 60.75 | baseline | yes | retain |
| Sentence Transformers ONNX CPU | 73.515s | 13.93 | 0.9999999 | yes | reject: 77% lower throughput |
| Sentence Transformers OpenVINO CPU | 42.075s | 24.34 | 0.9999563 | no | reject: 60% lower throughput and ordered-rank gate failed |
| MLX Embeddings bf16 | 51.082s | 20.05 | 0.9999415 | no | reject: 67% lower throughput, unstable runs, ordered-rank gate failed |
| ONNX CoreML EP | no run | — | — | — | failed: process terminated during warmup |
| FastEmbed ONNX CPU | no run | — | — | — | failed: default-thread and threads=4 attempts each exceeded the five-minute lane bound |

Torch/MPS load was 14.974s. ONNX CPU loaded in 12.911s but peaked at roughly 2.87 GB observed RSS. OpenVINO loaded in 18.653s. MLX loaded in 14.391s, and its three runs degraded from 38.667s to 67.359s. RSS numbers are observational only because unified accelerator/runtime allocations are not fully represented by process RSS.

## Procedure

Web research first selected five in-process open-source lanes and conditionally admitted ONNX CoreML EP. Server wrappers (TEI and Infinity), Rust/Candle, and direct community CoreML conversions were excluded because they introduce service, IPC, language-boundary, or conversion variables rather than a drop-in local runtime comparison.

The benchmark normalized each 384-dimensional vector, ran a 32-row warmup, measured three warm full passes, measured one cold model-load duration, embedded the same query, and compared document-vector cosine and exact ordered top-10 equality to Torch/MPS. “Exact” therefore means the same IDs in the same rank order; OpenVINO returned the same set but swapped ranks 9 and 10. Query-vector cosine was not retained and is a stated limit. Candidate dependencies and model exports lived in an ephemeral `/tmp` virtual environment; project source, `pyproject.toml`, and `uv.lock` were unchanged. The temporary environment was removed afterward.

Raw results: `.10x/evidence/.storage/2026-07-14-open-embedding-backend-bakeoff.json`.
Lane harness: `.10x/evidence/.storage/2026-07-14-open-embedding-backend-bakeoff.py`.
Setup, export, bounded invocation, and future stdout/stderr/process capture wrapper: `.10x/evidence/.storage/2026-07-14-open-embedding-backend-bakeoff-run.sh`. The wrapper does not claim byte-for-byte regeneration of the canonical JSON.

## What this supports

No tested backend should be integrated. Current Torch/MPS remains the best observed Apple Silicon path. ONNX CPU alone met numerical and retrieval parity but was far slower. The result closes this backend bake-off with a null promotion decision rather than turning an attractive backend name into a dependency without evidence.

Corpus SHA-256 and ordered row-ID SHA-256 are retained in raw evidence. This was a no-write benchmark: no Turbopuffer request, namespace operation, plan mutation, or remote state change occurred.

## Limits

This is one Apple M2 Pro, one 1,024-chunk workload, one query, one batch size, three warm passes, and one cold load measurement—not repeated cold-process throughput. It does not evaluate CUDA/Linux, Intel systems, other models, quantized-quality tradeoffs, server amortization, or conversion engineering. Baseline used the project environment (`sentence-transformers 5.6.0`, Torch 2.12.1); candidate lanes used an ephemeral environment. The top-level raw environment version block describes the candidate environment and must not be read as the baseline Torch version. FastEmbed and CoreML produced bounded failures rather than comparable medians. Canonical failure claims are limited to facts retained from the original observation; exact CoreML stderr diagnostics and original termination-code normalization are not claimed. Query cosine, package/build portability, fallback integration, and plan compatibility were not evaluated because no candidate passed the earlier repeated-median performance gate. No end-to-end live apply was warranted because no candidate beat the local embedding baseline.
