Status: recorded
Created: 2026-08-29
Updated: 2026-08-29
Ticket: .10x/tickets/done/2026-08-28-implement-local-telemetry-v3-store-and-migration.md
Spec: .10x/specs/local-telemetry-v3-storage-and-migration.md
Review: .10x/reviews/2026-08-29-local-telemetry-v3-store-and-migration-review.md

# Local Telemetry V3 Store and Migration Implementation Evidence

## Scope

Implemented the storage/transport activation slice for retrieval telemetry v3 without opening or mutating the owner's real telemetry store and without provider/model calls or provider writes.

Production command telemetry now switches atomically to canonical v3 only after the same source state gained a distinct inbox-v3, v3 receipt handling, a writer that consumes v1/v2/v3, exact schema-v3 storage/views, and explicit v2-to-v3 migration.

## Contradiction repair

Implementation exposed one exact storage-spec contradiction: a validated complete provider receipt always has a catalog object, but its `outcome` is null when catalog was not begun, while the physical table declared that column `NOT NULL`.

The supervisor approved the semantics-preserving repair. `retrieve_provider_catalog_v3.outcome` is nullable, a complete null-outcome catalog row is required, every catalog counter and invocation count must be zero, and `retrieval_provider_summary_v3.catalog_outcome` remains null. No `not_started` enum or row omission was introduced. The active storage spec and ticket progress record the correction.

## Implemented behavior

### Queue, producer, and writer

- Added exact `v3-<32hex>.json`, `.part`, `r3-<32hex>.json`, and receipt-temporary validation plus `telemetry_paths_v3`.
- Added fixed `inbox-v3`, `database-migrate-v3`, and `telemetry-v2-backup.duckdb` paths.
- Shared pending/temporary/receipt capacity and receipt rotation now account across all three inbox versions.
- Writer scans, recovers, claims, decodes, commits, receipts, and reconciles v1/v2/v3 under one election/state/accounting boundary.
- V1 drains into schema 1/2/3, v2 into 2/3, and v3 only into 3; unsupported work returns to ready and reports upgrade required.
- Status and flush expose exact v3 ready/claimed facts. Status remains database-nonopening; flush keeps fixed-snapshot semantics.
- Production `retrieve_command_trace` defaults to schema 3 and publishes only canonical v3 bytes through inbox-v3. Historical v2 tests explicitly select the retained v2 producer.

### Exact schema and atomic insertion

Fresh stores initialize directly at exact schema 3 while retaining exact v1/v2 objects/views and putting new commands only in v3 tables.

Added normalized tables:

- `retrieve_command_runs_v3`;
- `retrieval_operations_v3`;
- `retrieve_inference_requests_v3`;
- `retrieve_provider_accounting_v3`;
- `retrieve_provider_content_operations_v3`;
- `retrieve_provider_content_invocations_v3`; and
- `retrieve_provider_catalog_v3`.

Added stable views:

- `retrieval_command_runs_v3`;
- `retrieval_stage_latency_v3`;
- `retrieval_inference_requests_v3`;
- `retrieval_provider_summary_v3`; and
- `retrieval_provider_content_invocations_v3`.

Metadata owns canonical SQL hashes for all nine retained/new views. Exact table/view/column/constraint/object inventories cover schema 3. One transaction inserts the command, optional operation, normalized inference/provider rows, shared spans, and events. Replay/conflict identity is global across all versions and compares normalized provider/inference rows as part of v3 identity.

Existing retained backups are validated as exact source-history subsets, allowing later append-only v1/v2 envelopes without allowing historical row mutation or mismatch.

### Explicit migration

- Fresh stores do not migrate; they initialize at v3.
- `buoy telemetry migrate` advances exactly one supported version: v1 to v2, then v2 to v3 on a later invocation; exact v3 is already current.
- V2-to-v3 migration validates all v1/v2 traces through canonical encoders, drains the compatible v1/v2 snapshot, copies and validates fixed scratch database/backup candidates, upgrades only the scratch transaction, proves old rows/views unchanged, publishes the immutable v2 backup, then atomically publishes v3.
- The existing immutable v1 backup is preserved and revalidated.
- Prepublication faults leave schema v2 authoritative and clean recognized scratch; postpublication retry reconciles exact v3 and empty scratch without recopying.
- Hostile/mismatching v2 backup blocks without changing the source.

## Changed files owned by this slice

Source and docs:

- `src/buoy_search/telemetry/queue.py`
- `src/buoy_search/telemetry/store.py`
- `src/buoy_search/telemetry/writer.py`
- `src/buoy_search/telemetry/producer.py`
- `docs/telemetry.md`
- `.10x/specs/local-telemetry-v3-storage-and-migration.md` (approved nullability correction only)

Tests/fixtures:

- `tests/telemetry/test_telemetry_v3_storage.py` (new)
- `tests/telemetry/test_telemetry_v2_storage.py`
- `tests/telemetry/test_telemetry_store.py`
- `tests/telemetry/test_retrieve_command_telemetry.py`
- `tests/fixtures/retrieve_command_timing_probe.py`

The broader diff also contains the already reviewed inference/provider child changes; this slice did not revert or recharacterize them.

## Deterministic provider-free coverage

New v3 storage tests prove:

- distinct v3 paths/names and three-inbox status;
- shared capacity across v1/v2/v3;
- default command publication through canonical inbox-v3;
- fresh exact v3 creation;
- atomic normalized command/provider/catalog rows including truthful null catalog;
- inference rows and command aggregates;
- unavailable accounting inserts only its status row;
- one writer drains all three inboxes;
- exact v2-to-v3 history/view preservation and both retained backups;
- v3 pending behind schema2 remains recoverable and blocked;
- global cross-version conflict cannot partially insert;
- hostile v2 backup fail-closed behavior; and
- prepublication and postpublication migration crash/retry behavior.

Historical v2 command tests explicitly construct v2 observations, so their envelope/view semantics remain exact while current production defaults to v3.

## Validation

### Full suites

```text
uv run --python 3.13 --with pytest pytest -q
1315 passed, 57 warnings, 1401 subtests passed

uv run --isolated --python 3.11 --with pytest pytest -q
1315 passed, 57 warnings, 1401 subtests passed
```

Warnings were the pre-existing lxml `strip_cdata` deprecation warnings.

### Focused schema/migration suites after final backup-subset repair

```text
uv run --python 3.13 --with pytest pytest -q \
  tests/telemetry/test_telemetry_store.py \
  tests/telemetry/test_telemetry_v2_storage.py \
  tests/telemetry/test_telemetry_v3_storage.py
83 passed, 165 subtests passed
```

Final v3 file alone: `13 passed, 6 subtests passed`.

### Static, packaging, and installed lifecycle

- `python -m compileall` over changed telemetry/CLI modules: pass.
- `git diff --check`: pass.
- `uv build --out-dir /tmp/buoy-telemetry-v3-dist`: sdist and wheel built.
- Local wheel installed into a temporary Python 3.11 environment with `UV_OFFLINE=1` and offline model controls.
- Installed explicit preview published inbox-v3 work; the short 10-second flush observation timed out immediately before the writer completed, then read-only status showed schema 3, one persisted run, empty queue, one v3 receipt, and overall healthy. Natural writer idle exit and temporary-home cleanup completed with no survivor.

The earlier ordinary local-wheel install was not used as no-network evidence; the governed rerun used `UV_OFFLINE=1`. No telemetry command exported over a network.

## Side effects and safety

- Turbopuffer/provider calls: 0
- Provider/catalog/content writes: 0
- Model construction/inference/download: 0
- Real `~/.buoy/telemetry` database opens/mutations: 0
- Commits/staging/push/release: 0
- Staged files after validation: 0
- Temporary writer survivors after cleanup: 0

All store/migration tests used temporary roots and synthetic schema fixtures. Package lifecycle used a temporary HOME and removed it after writer exit.

## Parent-accepted review repairs

A subsequent independent review identified bounded recovery and acceptance-coverage gaps. All parent-accepted fixes were applied without changing retrieval, provider, output, or v1/v2 view semantics:

- A new exact v2 source/backup probe detects retry after final v2-backup publication. Public migrate then completes canonical v3 publication before touching v1/v2 work published later; the late snapshot flushes exactly once afterward.
- Immutable v1 backup validation is streamed graph-by-graph as an exact subset of later append-only v1 history during v2-to-v3 migration and schema-v2 reconciliation.
- Status supplements stale durable accounting from unaccounted v3 rejected, conflict, and replay receipts and marks unreadable receipt accounting incomplete.
- Exact-schema v3 validation preflights normalized per-trace inference/provider cardinalities and all normalized materialization queries carry explicit governed limits.
- Status and migration validate migration-v3 candidate database/WAL byte caps before classification or cleanup; oversized files remain untouched and block.
- Production-default v3 privacy tests scan queue, receipt, writer state, normalized store, management output, v3 migration scratch, and both backups; socket/DNS hooks prove v3 management does not attempt network access.
- Exact ordered-column and semantic fixtures now cover preview, pre-pipeline failure, live success/failure, worker spawn/reuse, fallback, catalog-only, content-only, and automatic combined observations.
- The controlled timing probe and a representative explicit CLI flow now use the production-default v3 producer/encoder/queue path. The broad historical command suite keeps its explicit v2 seam for compatibility evidence.
- Public migrate help now truthfully says it advances an exact local store by one supported schema version.

### Review-repair validation

```text
Focused adversarial/storage/writer/queue/CLI matrix:
189 passed, 226 subtests passed

Python 3.13 full suite:
1325 passed, 57 warnings, 1406 subtests passed

Python 3.11 isolated full suite:
1325 passed, 57 warnings, 1406 subtests passed
```

The 57 warnings remained the pre-existing lxml `strip_cdata` deprecation warning. Compileall and `git diff --check` passed. A rebuilt wheel installed with `UV_OFFLINE=1`; an installed preview flushed one v3 trace in 11,199 ms and status reported healthy schema 3, empty queue, one receipt, and complete accounting. The revised migrate help appeared in the installed CLI. Temporary home/venv cleanup left no writer survivor.

## Final terminal-drain P1 repair

Ordinary v2-to-v3 migration now proves each compatible v1/v2 drain pass terminal before creating or publishing migration artifacts. After processing the fixed pass snapshot, it performs one bounded queue rescan and returns blocked if runtime receipt publication failed or if the queue is unsafe, unreadable, scan-incomplete, or retains any claim. This mirrors the established v1-to-v2 prepublication invariant. The already-proven v2-backup retry branch still performs no late compatible drain and therefore preserves publication-first late-work semantics.

A two-case fault fixture injects failure after the schema-v2 store commit:

1. terminal receipt publication raises, leaving the committed trace and its claim recoverable; retry appends no duplicate, classifies the store result as one replay, publishes one replay receipt, acknowledges it, and migrates;
2. acknowledgement returns false after the committed receipt is durable, leaving the claim recoverable; retry proves the receipt against the committed store, acknowledges it without replay/conflict, and migrates.

Both blocked attempts leave schema v2 authoritative, no v3 table published, and exactly one claim. Both retries leave exactly one v2 command row, zero v3 command rows, one terminal receipt, zero conflicts, complete accounting, and canonical schema v3.

Validation:

```text
Python 3.13 focused v2/v3 migration and writer suites:
96 passed, 169 subtests passed

Python 3.11 isolated focused v2/v3 migration and writer suites:
96 passed, 169 subtests passed

Python 3.13 full suite:
1326 passed, 57 warnings, 1408 subtests passed
```

The final-snapshot concurrency fixture was narrowed to label only the scan inside the final queue lock; the new required pre-migration bounded rescan remains separately observable and does not weaken final snapshot linearization.

## Residual risks

- Independent acceptance review passed after the final terminal-drain repair. Parent-observed reconciled validation passed with `70 passed, 164 subtests passed`; see `.10x/reviews/2026-08-29-local-telemetry-v3-store-and-migration-review.md`.
- The integration child still owns final aggregate documentation/packaging/privacy review and any separately frozen live Turbopuffer validation.
- Migration's public output retains the historical key `pending_v2`; during v2-to-v3 completion it reports the next-version v3 queue snapshot under that compatibility key, as required by the unchanged output shape.
