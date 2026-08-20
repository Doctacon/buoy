Status: recorded
Created: 2026-08-20
Updated: 2026-08-20
Target: 80d75620eb49283d957586930db419ac68165ebb
Verdict: fail
Ticket: .10x/tickets/2026-08-20-implement-local-telemetry-v2-storage-migration.md
Prior-Review: .10x/reviews/2026-08-20-local-telemetry-v2-storage-migration-review.md
Evidence: .10x/evidence/2026-08-20-local-telemetry-v2-storage-migration.md

# Local Telemetry V2 Storage and Migration Re-review

## Target and method

Three independent fresh-context reviewers inspected exact candidate commit
`80d75620eb49283d957586930db419ac68165ebb`, including the complete
`d116448..80d7562` candidate, focused `0989690..80d7562` repair, current source,
tests, specifications, prior review, and worker-recorded evidence. The parent
provided immutable diff files outside the project when one read-only reviewer
lacked a Git command tool. No reviewer edited files or independently executed
tests.

All three reviewers returned FAIL. They agreed that most first-review findings
were materially repaired: scratch-backed backup creation, post-publication
recovery, bounded v1 semantic validation, principal v2 graph invariants,
snapshot-isolated flush, ordinary hostile-inbox preflight, state-error
containment, aggregate pending capacity, text/JSON parity, and documentation.
The remaining and newly exposed gaps below are accepted.

## Findings

### Critical: published-backup crash plus later v1 work can wedge retry

The final immutable backup is published before canonical v2. If the process
dies in that window, canonical remains exact v1 and the backup matches it.
Subsequent v1 envelopes remain publishable but append correctly fails closed
because a backup beside schema v1 is unresolved. Current migrate retry attempts
to drain that new v1 snapshot before completing migration, so it blocks before
it can publish v2 and can never consume the queued work.

A retry that proves an existing exact backup matches the current canonical v1
MUST skip pre-migration queue draining, complete v2 publication from that exact
source/backup, and leave post-snapshot v1 envelopes recoverable for the schema-v2
writer. Add a crash-at-backup-publication test, publish intervening v1 work,
retry migration, then flush and prove exactly-once persistence.

### Significant: incomplete queue scans can reach DuckDB

Migration checks `unsafe`/`unreadable` but not `scan_incomplete`. Entry/time
bounds can therefore leave one inbox only partially validated while migration
opens DuckDB and underreports pending work. Every preflight and post-lock queue
scan used for migration MUST treat incomplete state as blocked before any store
module import/connection. Test both inbox versions and the connector zero-call
audit.

### Significant: exact object inventory remains incomplete

Schema-v1 functions/macros are checked only for schema v2, and the retained v1
test explicitly accepts shadow catalog macros contrary to the active contract.
Sequences and user-defined types are not inventoried. Exact validation MUST
reject user functions/macros for both versions, sequences, non-internal custom
types, and other persistent user object metadata not in the governed inventory.
The qualified system catalog path must remain non-binding and shadow-resistant.
Tests MUST cover v1/v2 macros, sequences, custom types, and altered defaults or
comments/tags where DuckDB persists them.

### Significant: exact-layout v2 content is not semantically validated

`already_current` validates v2 structure and a run count but not stored v2
command/operation/span/event values and graphs. An edited exact-layout v2 store
can contain prohibited JSON or an inconsistent command graph and still be
published as compatible. Implement bounded streaming v2 semantic/graph/privacy
validation through the canonical v2 encoder/decoder. Run it before
`already_current`, schema-version success, and mutation of an existing v2
store. Tests MUST insert an exact-layout prohibited sentinel and graph
mismatch, then prove blocked content-free behavior.

### Significant: retained backup is not proved semantically safe or matching

Normal append invokes retained-backup validation without content validation.
Already-current validates backup v1 content internally but does not compare it
to the canonical v2 store's retained v1 history. A semantically hostile backup
or a different valid exact-v1 history can coexist with continued mutation.
Every append/reconciliation with a backup MUST validate its complete bounded v1
content and compare the resulting v1 content identity to the canonical store's
retained v1 identity. Tests MUST cover prohibited-content, invalid-graph, and
valid-but-mismatching exact-schema backups.

### Significant: receipt capacity/accounting is not shared across versions

Pending and temporary capacity is shared, but receipt rotation enforces the
4,096-file/4-MiB bounds independently per inbox while writer state stores one
maximum-4,096 global accounted-name tuple. Split v1/v2 receipt histories can
exceed state bounds and make reconciliation fail. Receipt final/temporary
capacity and age-based rotation MUST be computed across both inboxes while the
shared queue lock is held. Add split count/byte boundary, rotation, and writer-
state reconciliation tests.

### Moderate: absent canonical store can misreport or ignore auxiliary state

Store inspection discovers a safe retained backup and migration scratch but
the database-absent branch can return `absent`; migrate then reports
`backup_present=false`. A missing canonical database with any backup or
migration scratch is unprovable, not clean absence. It MUST return blocked,
report the safe backup fact accurately, create/delete nothing, and reject
hostile auxiliary state. Test safe orphan backup, safe scratch, and hostile
variants.

### Moderate: abrupt-crash coverage remains narrower than the claim

Most phase tests raise caught `RuntimeError`; only selected copy/link paths use
a `BaseException`-style process-death simulation. Extend the no-cleanup crash
matrix across every material pre/post-publication phase. Keep hardware power
loss and cross-platform filesystem behavior as explicit residual limits rather
than claims.

### Evidence overclaim

The repaired evidence says every accepted finding was addressed. This exact
re-review disproves that statement. Preserve the successful observations but
mark `80d7562` as a failed candidate; additive evidence must map each finding
above to new tests and exact commands before another review.

## Correct behavior retained

- Production retrieve timing and direct-library v1 producer semantics remain
  untouched.
- Existing backup bytes are never overwritten or automatically deleted.
- Migration, status, receipts, and errors remain content-free in inspected
  paths.
- No provider/model/network dependency was introduced.
- The intentionally deleted unsupported release-check module was not restored
  and its stale collector was correctly treated as separate test debt.

## Verdict

FAIL. The backup-publication retry state is release-blocking. Incomplete
preflight, v1/object inventory, v2 semantic validation, backup identity,
shared receipt capacity, and orphan auxiliary handling also violate active
fail-closed, privacy, and exact-state contracts. The ticket remains active and
dependent retrieve instrumentation remains blocked.

## Residual risk

Review was static and did not independently execute tests. Reported runtime
coverage remains one macOS arm64 host. Exception/BaseException crash simulation
is not hardware power-loss testing, and DuckDB 1.5.4 view identities remain
version-sensitive.
