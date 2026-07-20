Status: blocked
Created: 2026-07-20
Updated: 2026-07-20
Parent: .10x/tickets/2026-06-28-repo-search-heavy-ranking-experiments.md
Depends-On: .10x/tickets/done/2026-07-20-bootstrap-crow-plus-immutable-cache.md

# Phase 3: Measure Crow-Plus Bounded Runtime

## Outcome

Own the smallest eligible phase 3 checkpoint for one separately approved, bounded load and two fixed inference observations using the already verified immutable Crow-Plus cache. This ticket is blocked pending separate phase 3 approval. Phase 2 success grants no model-load authority, and opening this owner authorizes no execution.

## Scope only after separate approval

- Use exactly `Shuu12121/CodeSearch-ModernBERT-Crow-Plus@96ff525a7aa3bf8bfa90d77337c2b24bd45229af` from `/Users/crlough/Library/Caches/buoy/models/crow-plus-96ff525a7aa3bf8bfa90d77337c2b24bd45229af`, bound to phase 2 manifest identity hash `99aa6f73b5baf87adcb80c1383e784f5ec2457ec61eb9e75e7bb7dfd7d98e2cb`.
- Require the exact observed host: `Mac14,9`, Apple M2 Pro, 17,179,869,184-byte unified memory, and macOS 26.5.1 (`25F80`). Use Apple MPS only; prohibit CPU fallback and CUDA.
- Keep exactly `sentence-transformers==5.6.0`, `transformers==5.12.1`, `torch==2.12.1`, and `huggingface-hub==1.20.1`; no dependency install, update, resolution, or lock change.
- Before imports, set `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `HF_HUB_DISABLE_TELEMETRY=1`, `DO_NOT_TRACK=1`, and `HF_HUB_DISABLE_UPDATE_CHECK=1`. Require `local_files_only=True`, the exact cache/revision, and remote code disabled.
- In one fresh child process, construct in float32 and cast once to float16, then perform exactly two sequential encode calls: query first, code/document second. Each call receives a one-element input list with embedding batch size exactly 1. Do not use quantization, direct-dtype construction, concurrent encode, or a remote/client thread.

## Exact workload and output contract

- Query bytes are exactly `Where does Buoy validate content vector dimensions?`, with no prefix, BOM, surrounding whitespace, or final newline: 51 UTF-8 bytes, SHA-256 `4f51d3b93aea75b1f2f58ae55eda6a74b112bb2d1e236549569d64132379d8cc`.
- Code/document bytes are exactly `def validate_vector(vector: list[float]) -> None:\n    if len(vector) != 768:\n        raise ValueError("expected 768 dimensions")\n`: 129 UTF-8 bytes with four U+0020 indentation spaces and an LF after every line, SHA-256 `a89366d7ffbd3e7816a58e297ebc2605d24dd4c98ae0f92627fc0c6cf2981260`.
- Record pinned token IDs and counts before inference; both inputs MUST fit the pinned 1,024-token maximum without truncation or stop before inference.
- Each call MUST independently return `[1,768]`, finite values only, and L2 norm in `[0.999, 1.001]`. Record configuration confirming empty query/document prefixes and CLS pooling.

## Exact resource, observation, and abort contract

- Start only when one recorded `vm_stat` snapshot computes `(free + inactive + speculative) * page_size` at or above 8,589,934,592 bytes.
- Hard ceilings: child RSS 4,294,967,296 bytes; MPS current allocation 2,147,483,648 bytes; MPS driver allocation 3,221,225,472 bytes; construction/load 120.000 seconds; total child runtime 300.000 seconds.
- Qualification ceilings: peak RSS 3,221,225,472 bytes; peak MPS current allocation 1,610,612,736 bytes; peak MPS driver allocation 2,415,919,104 bytes; load 90.000 seconds; total 225.000 seconds.
- From child start through MPS synchronization after the second encode, an external watchdog MUST sample child RSS and elapsed time at intervals of at most 100 ms, and an in-process monitor MUST emit monotonic MPS current/driver observations at intervals of at most 100 ms.
- The watchdog MUST send `SIGKILL` immediately at any hard memory ceiling or deadline. The child MUST self-terminate on an in-process hard-bound observation. A sample gap over 200 ms, monitor failure, unavailable MPS counter, process escape, network attempt, cache/revision drift, or output mismatch fails measurement.
- Exceeding only a qualification ceiling completes evidence collection but fails qualification. A failed measurement MUST NOT be worked around by changing a bound, device, precision, batch, input, dependency, or fallback path.

## Acceptance criteria

- Separate phase 3 approval provenance is recorded before any import, construction, load, tokenization, or inference.
- Cache/revision, host/runtime, offline/no-remote-code, dependency, device, precision, literal-input, call-order, output, monitoring, hard-abort, and qualification conditions exactly match `.10x/specs/crow-plus-resource-verification-checkpoint.md`.
- Evidence preserves raw timestamped samples, exact secret-free command/environment, cache manifest hash, input hashes/token IDs/counts, output hashes/statistics, exit/signal, load/total elapsed times, peaks, and pass/fail against every hard and qualification bound.
- No source/test/lockfile mutation, dependency operation, credential lookup, Turbopuffer or other live-service access, namespace/card/catalog/default operation, staging, indexing, delete, or write occurs.
- Closure states that phase 3 success grants no phase 4 implementation/source-change authority.

## Approval gate and blockers

Blocked pending explicit, separate user approval of this exact phase 3 operation. No model import, construction, load, tokenization, inference, watchdog/monitor execution, or output observation may occur before that approval is durably recorded. Phase 2 approval and success are non-transitive.

## Explicit exclusions

Any execution before separate approval; any input beyond the two exact literals; dependency install/update/resolve; source, test, configuration, or lockfile changes; CPU fallback; CUDA; remote code; credentials; Turbopuffer or other live-service access; namespace/card/catalog/default reads or writes; staging; indexing; deletes; phase 4 implementation/source changes; phase 5 indexing/write.

## Evidence expectations

Separate approval provenance; pre-import cache/host/runtime/dependency/offline validation; exact command and secret-free environment; raw watchdog and in-process samples; token IDs/counts; separate output hashes/shapes/finite/norm checks; configuration values; abort/failure detail; exact hard/qualification mapping; and a no-source/no-live/no-downstream-authority statement.

## References

- `.10x/specs/crow-plus-resource-verification-checkpoint.md`
- `.10x/specs/crow-plus-explicit-namespace-pilot.md`
- `.10x/tickets/done/2026-07-20-bootstrap-crow-plus-immutable-cache.md`
- `.10x/evidence/2026-07-20-crow-plus-phase-2-immutable-cache-bootstrap.md`
- `.10x/reviews/2026-07-20-crow-plus-phase-2-immutable-cache-bootstrap-review.md`

## Progress and notes

- 2026-07-20: Opened blocked only after phase 2 evidence received independent PASS and the bootstrap ticket closed. This owner mirrors the active exact phase 3 checkpoint without authorizing it. No model or Hub library import, construction, load, tokenization, inference, watchdog/monitor execution, dependency operation, source/test/lockfile mutation, credential or live-service access, namespace/card/catalog/default operation, staging, indexing, delete, or write occurred.
