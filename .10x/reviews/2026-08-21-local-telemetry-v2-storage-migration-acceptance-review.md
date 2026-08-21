Status: recorded
Created: 2026-08-21
Updated: 2026-08-21
Target: 18b3a5671b6b07e1d78151e5f32df421e79422be
Verdict: fail
Ticket: .10x/tickets/2026-08-20-implement-local-telemetry-v2-storage-migration.md
Prior-Review: .10x/reviews/2026-08-20-local-telemetry-v2-storage-migration-final-review.md
Evidence: .10x/evidence/2026-08-20-local-telemetry-v2-storage-migration.md

# Local Telemetry V2 Storage and Migration Acceptance Review

## Target and method

Two independent fresh-context reviewers inspected exact candidate
`18b3a5671b6b07e1d78151e5f32df421e79422be`, complete and focused immutable
diffs, current source/tests, all active telemetry specifications, the ticket,
three failed reviews, and additive evidence. Neither edited files or
independently executed tests.

Both reviewers verified every finding in the prior final review as materially
fixed: trusted receipt time, fail-closed ordinary writer scans, bounded scratch
inventory, actual writer-state publication crash seams, retry documentation,
and all earlier migration/privacy/compatibility findings. Both found one exact
remaining acceptance blocker.

## Finding

### Moderate acceptance blocker: final pending-v2 scan lacks queue authority

`_finish_successful_migration()` calls the explicitly non-locking
`scan_queue_read_only()` for its final `pending_v2` fact. That scanner visits
v2 temporary, ready, claimed, and receipt directories independently. A
concurrent producer may linearize temporary-to-ready publication during the
scan, producing a mixed observation or transient partial-tree failure. The
command can report success with a stale count or return blocked despite a
normal in-lock publication transition. This violates the active requirement
that the final fact be one queue-lock-linearized snapshot.

Acquire the shared bounded `queue.lock` across the complete final v2 scan,
including directory-tree observation. On lock timeout or unsafe/unreadable/
incomplete scan, return `blocked`; otherwise use the locked ready-plus-claimed
count. Add an interleaving test that pauses a producer before its atomic ready
rename, proves migration cannot scan through the in-progress transition, then
proves the final count includes the publication. Assert queue-lock acquisition,
not merely publication wholly before/after an unlocked scan.

## Verified repairs

- Receipt publication and temporary recovery use trusted queue-lock-held time.
- Writer startup, drain, claim recovery, and final idle scans reject incomplete
  observations.
- All migration scratch inventories use constant-memory bounded streaming.
- Actual writer-state temporary/rename/directory-sync no-cleanup seams recover.
- Backed-up retry documentation matches implementation.
- Prior crash/idempotency, exact-object/content/privacy, retained-backup,
  replay/capacity, v1 compatibility, output, and no-network repairs show no
  inspected regression.

## Verdict

FAIL only for the missing queue authority around the final `pending_v2`
snapshot. No other blocking or significant finding remains from this review.
The storage ticket remains active until the narrow correction passes focused
validation and fresh exact-commit acceptance review.

## Residual risk

Static review did not independently run tests. Hardware power-loss,
non-macOS filesystem behavior, and DuckDB versions beyond 1.5.4 remain
unverified and are not presented as blockers.
