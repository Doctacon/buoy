Status: blocked
Created: 2026-07-20
Updated: 2026-07-20
Parent: .10x/tickets/2026-06-28-repo-search-heavy-ranking-experiments.md
Depends-On: .10x/tickets/done/2026-07-20-bootstrap-crow-plus-immutable-cache.md

# Phase 3: Measure Crow-Plus Bounded Runtime

## Outcome

Own the smallest eligible phase 3 checkpoint for one separately approved, bounded load and two fixed inference observations using the already verified immutable Crow-Plus cache. Separate phase 3 approval was recorded before operation, but the approved attempt stopped at the available-memory start floor before cache/dependency verification or any model/Hub import, child process, tokenization, load, monitoring, or inference. Independent review passed the failed-attempt evidence, not the measurement acceptance criteria. The ticket remains blocked: phase 3 measurement acceptance is unfulfilled, the original approval grants no retry, and any later attempt requires a fresh revised checkpoint and new separate approval.

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

## Retry-1 revised checkpoint (draft only; blocked pending new approval)

This checkpoint is the only proposed retry. It does not reuse or extend the approval spent by the stopped first attempt. Retry-1 MUST remain blocked until the user gives new explicit, separate approval after reviewing this exact checkpoint. Preparing, reviewing, committing, pushing, or opening a pull request for this record MUST NOT start preflight, import or load a dependency/model, create the measurement child, or authorize phase 4–5.

### Fresh read-only eligibility capture

A secret-free, read-only shell capture began at machine time `2026-07-20T18:30:03Z` (epoch `1784572203`) and ended at `2026-07-20T18:30:05Z` (epoch `1784572205`). It used only `/bin/date`, `sysctl`, `sw_vers`, `uname`, `df`, `vm_stat`, `find`, `sort`, `stat`, `shasum`, `awk`, `wc`, and `tr`; it performed no model/dependency import or load and made no source, test, lock, live-service, or cache mutation.

- Exact host/OS remained `Mac14,9`, Apple M2 Pro, 17,179,869,184-byte unified memory, macOS 26.5.1 (`25F80`), with Darwin 25.5.0 arm64 kernel `Darwin Kernel Version 25.5.0: Mon Apr 27 20:39:09 PDT 2026; root:xnu-12377.121.6~2/RELEASE_ARM64_T6020`.
- The cache filesystem `/dev/disk3s5`, mounted at `/System/Volumes/Data`, reported 33,228,080 available 1,024-byte blocks, or 34,025,553,920 available bytes. This is an informational current filesystem observation, not a substitute for any runtime memory precondition.
- The one raw `vm_stat` snapshot reported a 16,384-byte page size, 5,202 free pages, 178,557 inactive pages, and 752 speculative pages. The fixed formula computes `(5,202 + 178,557 + 752) * 16,384 = 3,023,028,224` available bytes, which is 5,566,906,368 bytes below the unchanged 8,589,934,592-byte start floor. This draft capture is not an approved retry preflight and MUST NOT be reused as one.

  ```text
  Mach Virtual Memory Statistics: (page size of 16384 bytes)
  Pages free:                                     5202.
  Pages active:                                 180192.
  Pages inactive:                               178557.
  Pages speculative:                               752.
  Pages throttled:                                   0.
  Pages wired down:                             352923.
  Pages purgeable:                                  46.
  "Translation faults":                    45211033679.
  Pages copy-on-write:                      7866333969.
  Pages zero filled:                       11192261022.
  Pages reactivated:                        1261356420.
  Pages purged:                              172659340.
  File-backed pages:                             99167.
  Anonymous pages:                              260334.
  Pages stored in compressor:                  1800003.
  Pages occupied by compressor:                 291038.
  Decompressions:                           1921125571.
  Compressions:                             2033411955.
  Pageins:                                   682975519.
  Pageouts:                                    5280987.
  Swapins:                                   156638285.
  Swapouts:                                  165532288.
  ```

- Read-only hashing of the dedicated cache found exactly the same 14 regular paths, 611,525,163 total bytes, and per-file SHA-256 values recorded by `.10x/evidence/2026-07-20-crow-plus-phase-2-immutable-cache-bootstrap.md`; it found no symlink. The freshly rendered sorted `path<TAB>bytes<TAB>sha256<LF>` content manifest hashes to `109657fe21f88596d2f186b1adcdcc81580f82fbe61f0117b89ba221adb9d39c`. This confirms the local byte set remains bound to the phase 2 canonical repository/revision manifest identity `99aa6f73b5baf87adcb80c1383e784f5ec2457ec61eb9e75e7bb7dfd7d98e2cb`; the latter covers `Shuu12121/CodeSearch-ModernBERT-Crow-Plus`, revision `96ff525a7aa3bf8bfa90d77337c2b24bd45229af`, sorted paths, advertised sizes, Git object IDs, and LFS metadata.

The current memory observation is ineligible. Before any separately approved retry-1 import, tokenization, load, child creation, monitoring, or inference, one newly timestamped `vm_stat` snapshot MUST independently meet `(free + inactive + speculative) * page_size >= 8,589,934,592` bytes. Failure MUST stop retry-1 immediately and spend that approval; it MUST NOT trigger another snapshot or attempt.

Cleanup is not a workaround for the memory bound. If repository cleanup is performed before seeking retry-1 approval, it MUST be limited to worktrees whose work is already completed and integrated, after separately verifying they have no uncommitted work; such cleanup can recover filesystem space only. It MUST NOT remove an active worktree, alter or delete the immutable cache, raise any bound, change workload/runtime conditions, or itself authorize retry-1. No cleanup was performed while preparing this checkpoint.

### Unchanged retry-1 operation contract

Retry-1 changes no active model, host, dependency, device, precision, batch, input, time, RSS, MPS, watchdog, output, or failure bound:

- **Identity and host:** use only `Shuu12121/CodeSearch-ModernBERT-Crow-Plus@96ff525a7aa3bf8bfa90d77337c2b24bd45229af` at `/Users/crlough/Library/Caches/buoy/models/crow-plus-96ff525a7aa3bf8bfa90d77337c2b24bd45229af`, canonical manifest identity `99aa6f73b5baf87adcb80c1383e784f5ec2457ec61eb9e75e7bb7dfd7d98e2cb`, on exactly `Mac14,9` / Apple M2 Pro / 17,179,869,184-byte unified memory / macOS 26.5.1 (`25F80`). Cache/revision drift stops before load.
- **Dependencies and offline boundary:** retain exactly `sentence-transformers==5.6.0`, `transformers==5.12.1`, `torch==2.12.1`, and `huggingface-hub==1.20.1`, with no install, update, resolution, or lock change. Before imports set `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `HF_HUB_DISABLE_TELEMETRY=1`, `DO_NOT_TRACK=1`, and `HF_HUB_DISABLE_UPDATE_CHECK=1`; require `local_files_only=True`, the exact cache/revision, and remote code disabled.
- **Device, precision, process, and batch:** Apple MPS only, with CPU fallback and CUDA prohibited. In exactly one fresh child, construct/load once in float32 and cast once to float16 before inference. No quantization or direct-dtype construction. Perform exactly two sequential encode calls—query first, code/document second—each with a one-element input list and embedding batch size exactly 1; no combined/concurrent encode or remote/client thread.
- **Exact inputs:** query is exactly the 51 UTF-8 bytes `Where does Buoy validate content vector dimensions?`, SHA-256 `4f51d3b93aea75b1f2f58ae55eda6a74b112bb2d1e236549569d64132379d8cc`, with no prefix, BOM, surrounding whitespace, or final newline. Code/document is exactly the 129 UTF-8 bytes `def validate_vector(vector: list[float]) -> None:\n    if len(vector) != 768:\n        raise ValueError("expected 768 dimensions")\n`, SHA-256 `a89366d7ffbd3e7816a58e297ebc2605d24dd4c98ae0f92627fc0c6cf2981260`, with four U+0020 indentation spaces and LF after every line. Record pinned token IDs/counts before inference; either input exceeding 1,024 tokens without truncation stops before inference.
- **Outputs:** each call independently MUST return shape `[1,768]`, finite values only, and L2 norm in `[0.999, 1.001]`. Record separate output hashes/statistics and configuration confirming empty query/document prefixes and CLS pooling. Any mismatch fails measurement.
- **Hard bounds:** child RSS 4,294,967,296 bytes; MPS current allocation 2,147,483,648 bytes; MPS driver allocation 3,221,225,472 bytes; construction/load 120.000 seconds from child start; total child runtime 300.000 seconds. Contacting a hard ceiling or deadline aborts immediately.
- **Qualification bounds:** peak RSS 3,221,225,472 bytes; peak MPS current allocation 1,610,612,736 bytes; peak MPS driver allocation 2,415,919,104 bytes; construction/load 90.000 seconds; total runtime 225.000 seconds. Exceeding only a qualification bound completes bounded evidence collection but fails qualification.
- **Watchdog and monitor:** from child start through MPS synchronization after the second encode, the external watchdog samples child RSS and elapsed time at intervals of at most 100 ms, while the in-process monitor emits monotonic MPS current/driver observations at intervals of at most 100 ms. The watchdog sends `SIGKILL` immediately at any hard memory ceiling or deadline, and the child self-terminates on an in-process hard-bound observation. A gap over 200 ms, monitor failure, unavailable MPS counter, process escape, network attempt, cache/revision drift, or output mismatch fails measurement.
- **Evidence and stop boundary:** preserve raw timestamped samples, exact secret-free command/environment, fresh host/runtime/dependency/cache checks, cache manifest identity, input hashes/token IDs/counts, separate output hashes/shapes/finite/norm statistics, configuration, exit/signal, load/total elapsed times, peaks, and pass/fail against every hard and qualification bound. A failure MUST NOT be worked around by raising a bound, changing device/precision/batch/input/dependency/fallback, or proceeding downstream.

All prior exclusions remain unchanged: no source/test/configuration/lock mutation, dependency operation, credential lookup, Turbopuffer or other live-service access, namespace/card/catalog/default/state operation, staging, indexing, delete, write, phase 4 implementation/source change, or phase 5 indexing/write. Passing retry-1 would establish only the exact bounded phase 3 observation and would grant no downstream authority.

## Acceptance criteria

- Separate phase 3 approval provenance is recorded before any import, construction, load, tokenization, or inference.
- Cache/revision, host/runtime, offline/no-remote-code, dependency, device, precision, literal-input, call-order, output, monitoring, hard-abort, and qualification conditions exactly match `.10x/specs/crow-plus-resource-verification-checkpoint.md`.
- Evidence preserves raw timestamped samples, exact secret-free command/environment, cache manifest hash, input hashes/token IDs/counts, output hashes/statistics, exit/signal, load/total elapsed times, peaks, and pass/fail against every hard and qualification bound.
- No source/test/lockfile mutation, dependency operation, credential lookup, Turbopuffer or other live-service access, namespace/card/catalog/default operation, staging, indexing, delete, or write occurs.
- Closure states that phase 3 success grants no phase 4 implementation/source-change authority.

These measurement acceptance criteria remain unfulfilled because the child never started and no cache/dependency, tokenizer, model-runtime, output, monitoring, hard-bound, or qualification observation was produced. Independent PASS applies only to the accuracy and boundedness of the failed-attempt evidence.

## Approval gate and blockers

The user's explicit, separate approval of this exact phase 3 operation was durably recorded before preflight and before any model/Hub import, construction, load, tokenization, inference, watchdog/monitor execution, or output observation. The approved attempt then failed the 8,589,934,592-byte available-memory start floor and stopped immediately without starting a child process. Independent review passed the evidence for that failed attempt but did not satisfy measurement acceptance. No retry is authorized under the spent original approval; a later attempt requires a fresh revised checkpoint and new separate approval. Phase 2 approval and success remain non-transitive, and phase 4–5 remain unauthorized.

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
- `.10x/evidence/2026-07-20-crow-plus-phase-3-bounded-runtime-preflight-failure.md`
- `.10x/reviews/2026-07-20-crow-plus-phase-3-bounded-runtime-preflight-failure-review.md`

## Progress and notes

- 2026-07-20: Opened blocked only after phase 2 evidence received independent PASS and the bootstrap ticket closed. This owner mirrors the active exact phase 3 checkpoint without authorizing it. No model or Hub library import, construction, load, tokenization, inference, watchdog/monitor execution, dependency operation, source/test/lockfile mutation, credential or live-service access, namespace/card/catalog/default operation, staging, indexing, delete, or write occurred.
- 2026-07-20: Before any model or Hub import, construction, load, tokenization, inference, watchdog/monitor execution, or output observation, recorded the user's separate explicit approval to execute this exact phase 3 ticket. The approval repeats the immutable manifest/cache identity, exact Mac14,9 M2 Pro/macOS host and locked dependencies, pre-import offline/telemetry/no-remote-code controls, MPS-only float32-construction-then-single-float16-cast batch-1 workload, exact ordered 51-byte query and 129-byte LF document, tokenizer/output requirements, dual-monitor sampling and immediate-abort bounds, qualification thresholds, and all no-source/no-live/no-downstream exclusions. Ticket activated for phase 3 only; phase 4 implementation/source changes and phase 5 indexing/write remain unauthorized.
- 2026-07-20: Preflight matched `Mac14,9`, Apple M2 Pro, 17,179,869,184-byte memory, and macOS 26.5.1 (`25F80`), with all required offline/telemetry/update controls set before any possible model-library import. The first recorded `vm_stat` snapshot computed `(3,720 + 178,757 + 4,285) * 16,384 = 3,059,908,608` available bytes, 5,530,025,984 below the mandatory 8,589,934,592-byte start floor. Stopped immediately without retry and before cache/dependency verification, model/Hub import, child creation, tokenization, load, monitoring, inference, or output. No dependency/source/test/lock, credential, network/live-service, Turbopuffer, namespace/catalog/state, staging, indexing, delete, or write operation occurred. Raw artifact: `.10x/evidence/.storage/2026-07-20-crow-plus-phase3-preflight-failure.json`; evidence: `.10x/evidence/2026-07-20-crow-plus-phase-3-bounded-runtime-preflight-failure.md`. No retry or phase 4 authority exists.
- 2026-07-20: Independent review passed PR #67 head `a547040` as accurate failed-attempt evidence, including the arithmetic, immediate stop, bounded scope, and explicit timestamp/attestation limits. This PASS does not satisfy phase 3 measurement acceptance. Returned the ticket to `blocked`; a future attempt requires a fresh revised checkpoint and new separate approval, and no retry is authorized.
- 2026-07-20: Prepared retry-1 as a record-only blocked checkpoint. A machine-timestamped read-only capture reconfirmed the exact host/OS and the complete immutable cache byte set without model/dependency import or load, observed 34,025,553,920 filesystem bytes free, and computed only 3,023,028,224 available-memory bytes—still below the unchanged 8,589,934,592-byte floor. No cleanup, retry, child, source/test/lock/live/cache mutation, or downstream operation occurred. The original approval remains spent; retry-1 requires new explicit separate approval after independent review of this exact checkpoint.
