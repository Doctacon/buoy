Status: recorded
Created: 2026-08-21
Updated: 2026-08-21
Target: 2c7e5ed517169ea49b97b3b31158691c44de3b36
Verdict: concerns
Ticket: .10x/tickets/done/2026-08-20-implement-local-telemetry-v2-storage-migration.md
Prior-Review: .10x/reviews/2026-08-21-local-telemetry-v2-storage-migration-acceptance-review.md
Evidence: .10x/evidence/2026-08-20-local-telemetry-v2-storage-migration.md

# Local Telemetry V2 Storage Post-fix Review

## Target and result

One fresh independent reviewer inspected exact commit `2c7e5ed`, its complete
`18b3a56..2c7e5ed` repair diff, current implementation/tests, active contracts,
prior reviews, and evidence.

The reviewer verified that the production blocker is closed: both migrated and
already-current success paths share one bounded final helper that holds the
shared `queue.lock` across complete v2 tree inspection and count capture;
timeout and unsafe/unreadable/incomplete scans block; publication holds that
same lock through temporary verification and ready rename; no inspected
unlocked duplicate or deadlock remains. No prior repaired behavior regressed.

## Finding

### Significant evidence concern: interleaving test signals before contention

The deterministic test sets `snapshot_lock_attempted` immediately before
calling the real lock context manager. The controller releases the producer as
soon as that event fires. The migration thread can be descheduled between the
event and its actual `flock` call, so the test may pass without proving the
migration actually contended on the producer-held queue lock. Ordering
assertions can then be scheduler-produced rather than lock-produced.

Replace the pre-call signal with observation of an actual failed nonblocking
`flock` attempt from the migration thread (or an equivalent lower-level lock
handshake). Release the producer only after that contention event, assert no
final scan occurred, then prove producer rename precedes migration lock
acquisition and scan. Update evidence to describe only the proven boundary.

## Verdict

CONCERNS. Runtime implementation is accepted by static inspection; no runtime
blocker remains. Ticket closure is withheld solely because the required
deterministic concurrency evidence has a synchronization gap.

## Residual risk

The review was static. Hardware power loss, non-macOS filesystems, and DuckDB
versions beyond 1.5.4 remain unverified.
