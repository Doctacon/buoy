Status: recorded
Created: 2026-07-18
Updated: 2026-07-18
Target: `work/atomic-remote-catalog-cutover` through `1ff74c8`
Verdict: pass

# Atomic Remote Catalog Cutover Implementation Review

## Findings and repairs

Independent adversarial reviews initially rejected implementation for:

- misleading automatic preview and live retrieval flags;
- pre-delete and pre-migration outputs presented as final proof;
- migration source path reopening without inode binding;
- incomplete request/billing summaries;
- card mutation success misreported when a later snapshot failed;
- recovery outputs missing common snapshot/accounting fields;
- reconcile partial failures presenting undercounted totals as complete;
- test harnesses that initially skipped superseded suites or could instantiate a real client.

All findings were repaired. The final implementation:

- distinguishes preview from content retrieval truthfully;
- performs post-mutation stable reads and reports final revisions/counts/state;
- holds and revalidates migration source descriptor/device/inode/bytes before writes;
- aggregates known requests and available billing, using null plus `complete=false` when a failed read makes totals unknowable;
- preserves `catalog_updated=true` after verified mutation even if later snapshot/cleanup fails, retaining pending recovery;
- uses two independent strong reads for exact operator `accept-remote`;
- replaces every temporary skipped suite with remote-contract fakes and hard no-real-client sentinels.

Final targeted reviewer rechecks passed, including 138 focused tests and the 22-test pending suite. Full Python 3.11/3.13 matrices each passed 392 tests and distributions built.

## Verdict

Pass for hosted checks and fail-closed live preflight. No live migration or local deletion has occurred.

## Residual risk

Provider schema normalization, permissions, namespace-list consistency, and conditional writes remain fake-tested until the authorized live phase. The mutation freeze, exact two-card migration, branch/integrated previews, five-ID classification, exact file identity deletion, and post-deletion proof remain open acceptance criteria of the active ticket.
