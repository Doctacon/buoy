Status: blocked
Created: 2026-07-20
Updated: 2026-07-20
Parent: .10x/tickets/2026-06-28-repo-search-heavy-ranking-experiments.md
Depends-On: .10x/tickets/done/2026-07-20-shape-dynamic-content-vector-dimensions.md

# Phase 2: Bootstrap Crow-Plus Immutable Cache

## Outcome

Own the next separate approval checkpoint for downloading and verifying the exact immutable Crow-Plus revision into one dedicated cache. This ticket is **blocked and not executable until the user separately approves phase 2**. Phase 1 specification ratification does not authorize any transfer or operation.

## Scope after separate approval

- Bootstrap exactly `Shuu12121/CodeSearch-ModernBERT-Crow-Plus@96ff525a7aa3bf8bfa90d77337c2b24bd45229af`.
- Require the cache root `/Users/crlough/Library/Caches/buoy/models/crow-plus-96ff525a7aa3bf8bfa90d77337c2b24bd45229af` to be absent before bootstrap. Do not use a default/global cache or pre-existing blobs.
- Before transfer, reproduce and record the complete regular-file manifest for that immutable revision. It MUST bind every path and advertised size and total exactly 611,525,163 bytes.
- Enforce an exact 611,525,163-byte transfer ceiling and an 805,306,368-byte (768 MiB) allocated-size ceiling for the final dedicated cache, including metadata, locks, and filesystem allocation overhead.
- Start only with at least 5,368,709,120 bytes (5 GiB) free on the cache volume and leave at least 4,294,967,296 bytes (4 GiB) free after bootstrap.
- Record pre/post free bytes, per-file path/size/hash, transferred bytes, and final allocated cache bytes. Abort before the next file if its advertised size would exceed the transfer or free-disk bounds. On failure, record evidence and delete only the dedicated incomplete cache root.

## Network, offline, telemetry, and code boundaries

- The separately approved immutable snapshot transfer is the only network-enabled model operation in this phase. It MUST use the exact repository/revision and public no-token/no-credential access.
- Before importing Hub code, set `HF_HUB_DISABLE_TELEMETRY=1`, `DO_NOT_TRACK=1`, and `HF_HUB_DISABLE_UPDATE_CHECK=1`. No telemetry, update check, credential lookup, token, dependency install/update/resolution, or remote code is permitted.
- Bootstrap MUST NOT import, construct, load, or run the model. It MUST NOT execute repository code.
- Any later model consumer remains a separate phase and MUST set `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `HF_HUB_DISABLE_TELEMETRY=1`, `DO_NOT_TRACK=1`, and `HF_HUB_DISABLE_UPDATE_CHECK=1` before imports, use `local_files_only=True`, bind the exact revision and dedicated cache, and keep remote code disabled. Phase 2 success does not authorize that consumer.

## Acceptance criteria

- Separate phase 2 approval provenance is recorded before any transfer.
- The exact immutable manifest totals 611,525,163 bytes before transfer and the final verified per-file hashes/sizes match it.
- Transferred bytes do not exceed 611,525,163; final allocated cache size does not exceed 805,306,368 bytes (768 MiB).
- Free disk is at least 5,368,709,120 bytes (5 GiB) before bootstrap and at least 4,294,967,296 bytes (4 GiB) afterward.
- The dedicated cache is the only model filesystem target; offline/telemetry/no-remote-code boundaries are preserved.
- Evidence records success or exact failure without model import/load/inference, source/test/lockfile mutation, credential access, live service access, namespace/card/catalog/default operation, indexing, or write.
- Closure states explicitly that bootstrap success grants no phase 3 bounded-measurement-load authority.

## Approval gate and blockers

Blocked on one explicit user approval of this exact phase 2 operation and its immutable revision/cache/transfer/cache-allocation/disk/telemetry/no-remote-code boundaries. The ticket MUST remain non-executable until that approval is separately given and recorded.

Phase 3 bounded measurement load, phase 4 implementation/source changes, and phase 5 indexing/write remain blocked under the active specifications. They have no executable owners because no prior phase has made their approval checkpoint eligible.

## Explicit exclusions

Model import, construction, load, inference, or output observation; dependency install/update/resolve or lockfile changes; source, test, configuration, or runtime changes; measurement watchdog/monitor execution; credentials; Turbopuffer or other live-service access; namespace/card/catalog/default reads or writes; staging; indexing; deletes; phase 3–5 approval or execution.

## Evidence expectations

Approval provenance; pre-transfer immutable manifest; exact command/environment with secrets absent; pre/post disk observations; transferred-byte count; final allocated cache bytes; per-file path/size/hash; abort/failure details; and a no-load/no-inference/no-source/no-live-operation statement.

## References

- `.10x/specs/crow-plus-explicit-namespace-pilot.md`
- `.10x/specs/crow-plus-resource-verification-checkpoint.md`
- `.10x/tickets/done/2026-07-20-shape-dynamic-content-vector-dimensions.md`
- `.10x/evidence/2026-07-20-crow-plus-phase-1-specification-ratification.md`
- `.10x/reviews/2026-07-20-dynamic-content-vector-dimensions-shaping-review.md`

## Progress and notes

- 2026-07-20: Opened blocked after phase 1 ratification as the smallest next durable owner. No phase 2 approval exists. No download, model import/load/inference, source/test/lockfile change, credential access, live operation, namespace/card/catalog/default operation, indexing, or write occurred.
