Status: recorded
Created: 2026-08-29
Updated: 2026-08-29
Target: .10x/tickets/done/2026-08-28-implement-local-telemetry-v3-store-and-migration.md
Verdict: pass

# Local Telemetry V3 Store and Migration Review

## Target

Canonical telemetry-v3 queue, writer, normalized DuckDB schema/views, explicit v2-to-v3 migration, status/flush behavior, production v3 activation, documentation, packaging, and installed lifecycle.

## Findings and repairs

The first three-angle review found concrete P1/P2 gaps in backup-published retry ordering, immutable v1-backup subset handling, stale v3 receipt accounting, bounded normalized-row materialization, migration scratch WAL limits, production-v3 privacy/no-network evidence, stable-view scenario coverage, production-v3 timing coverage, and migrate help. All were repaired and independently rechecked.

Follow-up review found one remaining P1: v2-to-v3 migration could freeze/publish after a committed queue item failed terminal receipt/acknowledgement. The final repair added a bounded post-drain rescan and fail-closed receipt/claim gate while preserving the separate backup-published publication-first retry branch.

Final review confirmed:

- terminal drain blocks on receipt failure, unsafe/incomplete rescan, or remaining claims before migration publication;
- receipt-publication and acknowledgement failure fixtures preserve schema v2 and recoverable work, then retry replays/proves exactly once and migrates;
- late work after backup publication is not drained before canonical v3 publication;
- v1 backup is validated as an exact subset of later append-only v1 history;
- v3 receipt accounting, bounded normalized reads, database/WAL caps, crash/idempotency, replay/conflict, and global version routing are fail-closed;
- exact view matrices, production-v3 timing/CLI, end-to-end privacy, no-network management, help, packaging, and installed lifecycle execute the changed paths; and
- historical v1/v2 rows/views remain exact.

No P0, P1, or P2 issue remained. Final verdict: pass.

## Parent-observed validation

The parent reran on the reconciled worktree:

```text
git diff --check
uv run --python 3.13 --with pytest pytest -q \
  tests/telemetry/test_telemetry_v3_storage.py \
  tests/telemetry/test_telemetry_v2_storage.py
```

Result: `70 passed, 164 subtests passed`; diff check passed.

Recorded candidate evidence includes:

- full Python 3.13 and isolated Python 3.11: `1325 passed, 1406 subtests passed` after the broad repair set;
- final terminal-drain focused Python 3.13 and isolated Python 3.11: `96 passed, 169 subtests passed`;
- final Python 3.13 full: `1326 passed, 1408 subtests passed`;
- sdist/wheel build and offline installed-wheel v3 preview/flush/status/help lifecycle; and
- zero provider/model calls, real-store access, staged files, or writer survivors.

## Verdict

Pass. Every bounded ticket criterion maps to recorded evidence. Production retrieve telemetry now uses canonical v3 only after the matching inbox/writer/store support exists.

## Residual risk

The owner's real telemetry-v2 store was intentionally not migrated. Final aggregate integration and any separately frozen live Turbopuffer validation remain owned by the integration ticket. Public migrate output retains compatibility key `pending_v2` for the next-version queue snapshot.
