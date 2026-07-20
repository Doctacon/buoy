Status: done
Created: 2026-07-20
Updated: 2026-07-20
Parent: .10x/tickets/2026-06-28-repo-search-heavy-ranking-experiments.md
Depends-On: .10x/tickets/done/2026-07-20-shape-dynamic-content-vector-dimensions.md

# Phase 2: Bootstrap Crow-Plus Immutable Cache

## Outcome

Completed the separately approved checkpoint for downloading and verifying the exact immutable Crow-Plus revision into one dedicated cache. Approval provenance was recorded before manifest retrieval or transfer, the bootstrap completed within every approved bound, and independent review passed PR #66 execution/evidence head `d6e13ac4c6e4c4255981162d55bb82548df2fe46`. Phase 1 specification ratification alone did not authorize this operation, and phase 2 success grants no phase 3 authority.

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

## Approval and review state

The user separately approved this exact phase 2 operation and its immutable revision/cache/transfer/cache-allocation/disk/telemetry/no-remote-code boundaries. That approval was recorded in the progress log before the first manifest request or transfer. Execution evidence is recorded at `.10x/evidence/2026-07-20-crow-plus-phase-2-immutable-cache-bootstrap.md`.

Independent review passed PR #66 execution/evidence head `d6e13ac4c6e4c4255981162d55bb82548df2fe46`; review is recorded at `.10x/reviews/2026-07-20-crow-plus-phase-2-immutable-cache-bootstrap-review.md`. Phase 3 bounded measurement is owned only as a blocked future approval checkpoint at `.10x/tickets/2026-07-20-measure-crow-plus-bounded-runtime.md`. It remains unauthorized. Phase 4 implementation/source changes and phase 5 indexing/write also remain blocked under the active specifications. No downstream operation has transitive authority from phase 2 success.

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
- `.10x/reviews/2026-07-20-crow-plus-phase-2-immutable-cache-bootstrap-review.md`
- `.10x/tickets/2026-07-20-measure-crow-plus-bounded-runtime.md`

## Progress and notes

- 2026-07-20: Opened blocked after phase 1 ratification as the smallest next durable owner. No phase 2 approval exists. No download, model import/load/inference, source/test/lockfile change, credential access, live operation, namespace/card/catalog/default operation, indexing, or write occurred.
- 2026-07-20: The user explicitly approved execution of this exact phase 2 ticket for `Shuu12121/CodeSearch-ModernBERT-Crow-Plus@96ff525a7aa3bf8bfa90d77337c2b24bd45229af`, including the dedicated absent cache root, exact 611,525,163-byte manifest/transfer ceiling, 805,306,368-byte allocated-cache ceiling, 5-GiB pre/4-GiB post free-disk floors, public no-token/no-credential access, telemetry/update controls, complete regular-file hashing, failure cleanup limited to the dedicated incomplete cache, and all phase 2 exclusions. Ticket activated before any manifest request or transfer. Phase 3 remains unauthorized.
- 2026-07-20: Reproduced the complete 14-file immutable manifest before transfer at exactly 611,525,163 bytes, then transferred and twice hashed every regular file in the previously absent dedicated cache. Observed 34,815,438,848 free bytes at transfer start, exactly 611,525,163 received bytes, 626,688,000 final allocated cache bytes, and 34,192,142,336 post-transfer free bytes. Public raw HTTPS used no authorization header or Hub/model import; telemetry/update controls were set and token variables removed without reading them. No dependency, model load/inference, source/test/lockfile, credential, Turbopuffer, namespace/card/catalog/default/state, staging, indexing, delete, or write operation occurred. Evidence: `.10x/evidence/2026-07-20-crow-plus-phase-2-immutable-cache-bootstrap.md`. Ticket remains active pending required independent review; phase 3 remains unauthorized.
- 2026-07-20: Independent review passed PR #66 execution/evidence head `d6e13ac`; manifest and transfer artifacts, all resource bounds, bounded diff, no-downstream-authority statement, and hosted Python 3.11/Python 3.13/distribution checks were coherent. The review records the residual attestation limit that artifact/diff inspection cannot retroactively prove absence of every unlogged external or runtime action. Closed phase 2 and opened only blocked phase 3 owner `.10x/tickets/2026-07-20-measure-crow-plus-bounded-runtime.md`; no model import, construction, load, tokenization, inference, source/test/lockfile change, or live operation occurred during finalization.

## Closure mapping

- **Separate approval before transfer:** the approval provenance and pre-transfer activation entry above, plus `.10x/evidence/2026-07-20-crow-plus-phase-2-immutable-cache-bootstrap.md`, establish that the exact phase 2 operation was authorized and recorded before manifest retrieval or transfer.
- **Exact manifest and file verification:** the evidence and `.10x/evidence/.storage/2026-07-20-crow-plus-phase2-immutable-manifest.json` bind 14 regular files totaling exactly 611,525,163 bytes; `.10x/evidence/.storage/2026-07-20-crow-plus-phase2-transfer-audit.json` records matching transfer-time and post-transfer hashes/sizes for all 14.
- **Transfer, allocation, and disk bounds:** the audit records exactly 611,525,163 received bytes, 626,688,000 allocated cache bytes, 34,815,438,848 free bytes at transfer start, and 34,192,142,336 free bytes afterward, satisfying all approved ceilings and floors.
- **Dedicated-cache and safety boundaries:** the evidence records only `/Users/crlough/Library/Caches/buoy/models/crow-plus-96ff525a7aa3bf8bfa90d77337c2b24bd45229af` as the model filesystem target, public no-token transfer, telemetry/update controls, no remote code, and no model/source/live operation.
- **Failure evidence:** the stopped Python TLS attempt received no manifest and created no cache; the successful system-curl path retained certificate verification. No incomplete-cache cleanup was needed.
- **Independent review and hosted checks:** `.10x/reviews/2026-07-20-crow-plus-phase-2-immutable-cache-bootstrap-review.md` records PASS at `d6e13ac`; PR #66 Python 3.11, Python 3.13, and Build distributions checks passed.
- **No phase 3 authority:** `.10x/tickets/2026-07-20-measure-crow-plus-bounded-runtime.md` is blocked pending separate approval and explicitly prohibits model import, construction, load, tokenization, inference, or monitoring execution before approval.

## Retrospective

Immutable bootstrap evidence is reviewable when the pre-transfer manifest has its own canonical identity, the transfer audit binds every final file through a second complete hash pass, filesystem allocation is measured separately from regular-file bytes, and approval timing is recorded before network work. The independent review also makes the attestation boundary explicit: tracked artifacts can substantiate recorded state but cannot prove the absence of every unlogged external action. Those lessons are captured in the evidence/review chain and the exact blocked phase 3 ticket; no separate knowledge or skill record is warranted.
