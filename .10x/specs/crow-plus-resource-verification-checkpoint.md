Status: active
Created: 2026-07-20
Updated: 2026-07-20

# Crow-Plus Resource-Verification Checkpoint

## Active phase 1 status

This exact conservative checkpoint is ratified as the phase 1 resource contract, not as an approved budget or operation. It resolves the sequencing ambiguity: every cache, hardware, precision, input, load-time, host/device, batch, observation, and abort value is fixed before bounded measurement begins; the resulting measured values then gate later implementation/source changes and indexing/write.

The five phases are fixed in this order and require five independent, non-transitive approvals: (1) specification, (2) bootstrap/download, (3) bounded measurement load, (4) implementation/source changes, and (5) indexing/write. Approval or success of one phase does not authorize, approve, or imply the next phase.

Phase 1 activation authorizes records only. No executable bootstrap/download, load, inference, implementation/evaluation, source/test change, or remote operation is authorized without its later separate phase approval.

## Observed host and immutable candidate inputs

Read-only host inspection on 2026-07-20 observed:

- Apple MacBook Pro `Mac14,9`, Apple M2 Pro, 10 CPU cores and 16 GPU cores;
- 17,179,869,184 bytes (16 GiB) unified memory;
- macOS 26.5.1 (`25F80`);
- 34,890,539,008 bytes (32.494 GiB) available on the data volume at observation time.

C2's immutable snapshot records Crow-Plus revision `96ff525a7aa3bf8bfa90d77337c2b24bd45229af`, 606,681,112 listed weight bytes and 611,525,163 total listed repository bytes. These are source facts, not measured cache or runtime values.

This checkpoint is host-specific. A different model identifier, chip, memory size, OS build, accelerator, dependency lock, or candidate revision requires a new proposed checkpoint and approval.

## Phase 2 bootstrap checkpoint (separate approval required)

- Repository/revision: exactly `Shuu12121/CodeSearch-ModernBERT-Crow-Plus@96ff525a7aa3bf8bfa90d77337c2b24bd45229af`.
- Cache root: exactly `/Users/crlough/Library/Caches/buoy/models/crow-plus-96ff525a7aa3bf8bfa90d77337c2b24bd45229af`; it MUST be absent before bootstrap. No default/global cache fallback or pre-existing blob reuse is allowed.
- Allowlist: the complete regular-file tree of that immutable revision and no other repository/revision. The pre-transfer manifest MUST bind every immutable path and advertised size and MUST total exactly 611,525,163 bytes. Any inability to reproduce that exact manifest stops before transfer.
- Transfer ceiling: 611,525,163 bytes. Cache-root allocated-size ceiling after bootstrap: 805,306,368 bytes (768 MiB), including Hub metadata, lock, and filesystem allocation overhead.
- Free-disk start floor: 5,368,709,120 bytes (5 GiB) on the cache volume; free disk after bootstrap MUST remain at least 4,294,967,296 bytes (4 GiB).
- Dependencies: existing lock only; no install, update, resolver, remote code, credential, or token.
- Observation: record pre/post free bytes, per-file path/size/hash, transferred bytes, and final allocated cache bytes. Abort before the next file if the next advertised size would exceed transfer or free-disk bounds; delete only the dedicated incomplete cache root after recording failure.
- Bootstrap success authorizes no model import, construction, load, or inference.

## Phase 3 bounded-measurement checkpoint (separate approval required after bootstrap)

### Hardware and runtime

- Host MUST exactly match the observed `Mac14,9` / Apple M2 Pro / 17,179,869,184-byte unified-memory / macOS 26.5.1 (`25F80`) contract.
- Accelerator: Apple MPS only; CPU fallback and CUDA are prohibited for this measurement.
- Dependency versions MUST remain `sentence-transformers==5.6.0`, `transformers==5.12.1`, `torch==2.12.1`, and `huggingface-hub==1.20.1`; no install or lock change.
- Construction: create from the exact dedicated cache in float32, then cast once to float16 before inference, matching the currently observed construct-then-`.half()` strategy. Stored/output validation uses float16-compatible values; no quantization or direct-dtype alternate path.
- Environment MUST be set before imports: `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `HF_HUB_DISABLE_TELEMETRY=1`, `DO_NOT_TRACK=1`, and `HF_HUB_DISABLE_UPDATE_CHECK=1`; `local_files_only=True`, exact revision/cache root, and remote code disabled are mandatory.

### Exact workload and output checks

- One fresh child process, one model construction/load, and exactly two sequential encode calls in this order: query, then code/document. Each call MUST receive a one-element input list and use embedding batch size exactly 1. No concurrent encode and no remote/client thread.
- Query input: UTF-8 encoding of exactly `Where does Buoy validate content vector dimensions?`, with no prefix, no BOM, no leading/trailing whitespace, and no trailing newline. It is 51 bytes and has SHA-256 `4f51d3b93aea75b1f2f58ae55eda6a74b112bb2d1e236549569d64132379d8cc`.
- Code/document input: UTF-8 encoding of exactly the following 129 bytes, with four U+0020 spaces for each indentation, LF (`U+000A`, byte `0a`) after every displayed line including the final line, no BOM, and no other leading/trailing bytes:

  ```python
  def validate_vector(vector: list[float]) -> None:
      if len(vector) != 768:
          raise ValueError("expected 768 dimensions")
  ```

  Its exact escaped form is `def validate_vector(vector: list[float]) -> None:\n    if len(vector) != 768:\n        raise ValueError("expected 768 dimensions")\n` and its SHA-256 is `a89366d7ffbd3e7816a58e297ebc2605d24dd4c98ae0f92627fc0c6cf2981260`.
- The pinned tokenizer's token IDs and token counts need not be known before bootstrap/download. After bootstrap and before inference, evidence MUST record both without changing either input; each input MUST fit within the pinned 1,024-token maximum without truncation, or measurement stops before inference.
- The query call and code/document call MUST each independently return shape `[1,768]`—a combined `[2,768]` call or output is prohibited. Each output MUST contain only finite values and have L2 norm in `[0.999, 1.001]`. The recorded model/module config MUST confirm empty query/document prefixes and CLS pooling.
- No credential lookup, Turbopuffer import/client/read/write, namespace operation, card/catalog/default operation, source/test mutation, or indexing is permitted.

### Exact resource and time bounds

- Start only when system available memory, computed from one recorded `vm_stat` snapshot as `(free + inactive + speculative) * page_size`, is at least 8,589,934,592 bytes (8 GiB).
- Child-process resident-set hard ceiling: 4,294,967,296 bytes (4 GiB).
- MPS current-allocated hard ceiling: 2,147,483,648 bytes (2 GiB).
- MPS driver-allocated hard ceiling: 3,221,225,472 bytes (3 GiB).
- Model construction/load deadline: 120.000 seconds from child start to ready-for-first-encode.
- End-to-end child deadline: 300.000 seconds.
- Sampling interval: at most 100 milliseconds from child start through synchronization after the second encode.
- Qualification headroom: measured peak RSS MUST be at most 3,221,225,472 bytes (3 GiB), measured peak MPS current allocation at most 1,610,612,736 bytes (1.5 GiB), measured peak MPS driver allocation at most 2,415,919,104 bytes (2.25 GiB), load time at most 90.000 seconds, and total time at most 225.000 seconds. Contacting a hard ceiling aborts; exceeding only a qualification threshold completes evidence collection but fails qualification.

### Observation and immediate abort

- An external watchdog MUST sample child RSS and elapsed time at least every 100 ms.
- An in-process monitor MUST sample `torch.mps.current_allocated_memory()` and `torch.mps.driver_allocated_memory()` at least every 100 ms and emit monotonic timestamped observations to the watchdog.
- The watchdog MUST send `SIGKILL` immediately when a sample is greater than or equal to any hard memory ceiling or when either deadline is reached. The child MUST also self-terminate on an in-process hard-bound observation. Any missing sample interval over 200 ms, monitor failure, MPS counter unavailability, process escape, network attempt, cache/revision drift, or output mismatch is a failed measurement.
- Evidence MUST preserve raw samples, exact commands/environment with secrets absent, cache manifest hash, input/token IDs, output hashes/statistics, exit/signal, load and total elapsed values, peaks, and pass/fail against every hard and qualification bound.

## Gate after measurement

A bounded measurement passes only when all identity, offline, workload, output, hard-bound, sampling, and qualification conditions pass. Passing proves compatibility only for this exact host/runtime/workload. It does not approve the next implementation/source-changes phase, larger batch/input/corpus work, staging, indexing, or remote writes.

Measured values MUST be copied into the later implementation checkpoint. Any implementation plan must stay within the measured batch/device/precision path and retain at least the qualification headroom above. The implementation/source-changes phase requires its own approval and bounded executable ticket. Exact local staging evidence must then precede the independent indexing/write approval under `.10x/specs/crow-plus-explicit-namespace-pilot.md`.

A failure requires a revised draft checkpoint and new approval; it MUST NOT be worked around by raising a bound, changing device/precision/batch, falling back to CPU, installing dependencies, or proceeding to implementation/indexing.

## Ratified checkpoint and remaining approvals

Phase 1 ratification fixed this exact checkpoint: dedicated empty cache root; 611,525,163-byte transfer and 768-MiB cache ceilings; 5-GiB/4-GiB disk floors; exact observed Mac/MPS host; float32 construction then float16 inference; exactly two sequential batch-1 calls using the fixed 51-byte query (`4f51d3b9…d8cc`) then fixed 129-byte LF-terminated code/document (`a89366d7…1260`), each yielding a separate `[1,768]` finite normalized output; 120-second load and 300-second total hard deadlines; 4-GiB RSS, 2-GiB MPS-current, and 3-GiB MPS-driver hard ceilings; 100-ms dual monitoring; stated qualification headroom; and immediate abort.

That approval authorized only phase 1 record activation. Phases 2–5—bootstrap/download, bounded measurement load, implementation/source changes, and indexing/write—each still require their own later approval; no phase approval or success implies the next.
