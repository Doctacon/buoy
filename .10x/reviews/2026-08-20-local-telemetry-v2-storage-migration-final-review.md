Status: recorded
Created: 2026-08-20
Updated: 2026-08-20
Target: bbc1cbc22cb89b7de0cfac8b30e417b53fcb24f1
Verdict: fail
Ticket: .10x/tickets/2026-08-20-implement-local-telemetry-v2-storage-migration.md
Prior-Review: .10x/reviews/2026-08-20-local-telemetry-v2-storage-migration-rereview.md
Evidence: .10x/evidence/2026-08-20-local-telemetry-v2-storage-migration.md

# Local Telemetry V2 Storage and Migration Final Review

## Target and method

Three independent fresh-context reviewers inspected exact candidate
`bbc1cbc22cb89b7de0cfac8b30e417b53fcb24f1`, the complete
`d116448..bbc1cbc` candidate, focused `80d7562..bbc1cbc` repair, current source,
tests, active specifications, prior failed reviews, and additive evidence.
Immutable full/repair diffs were supplied outside the project. No reviewer
edited files or independently executed tests.

All reviewers returned FAIL. They verified that the entire accepted second-
review set is materially repaired: backup-published retry with later v1 work,
migration-specific incomplete scans, exact objects/metadata, bounded v2
semantic/privacy validation, retained-backup identity, ordinary shared receipt
capacity, orphan auxiliary state, and no-cleanup database/backup hooks. They
found the remaining adjacent defects below.

## Findings

### Significant: receipt rotation uses an untrusted/stale payload timestamp

Shared rotation derives its age cutoff from `receipt.recorded_at_unix_ms`.
Receipt temporaries are explicitly untrusted and may carry arbitrary
nonnegative ancient or future timestamps. A future value can make fresh
receipts immediately eligible; an old recovered temporary can leave the cutoff
permanently stale so no now-old receipt is eligible, wedging recovery at full
capacity. Either outcome violates the 121-second filesystem-mtime observation
window and can erase flush evidence or strand a claim.

Rotation eligibility MUST use trusted current time sampled by the queue code
while the shared queue lock is held, never a receipt payload timestamp. Preserve
the payload timestamp only as validated content-free receipt data. Add
future/ancient recovered-temporary tests at split v1/v2 count and byte capacity
that prove young receipts are retained, now-old receipts rotate by
`(mtime_ns, basename)`, and recovery terminates.

### Significant: ordinary writer lifecycle treats incomplete scans as empty

Migration now blocks incomplete scans, but writer startup, main draining,
claim recovery, and final idle transition still check only unsafe/unreadable.
A bounded scan may observe zero ready names and `scan_incomplete=true`; the
writer can publish stopped state and release lifetime while a producer's start
request was suppressed, leaving accepted work pending indefinitely until
unrelated activity.

Every writer scan used to establish absence, recover claims, select work, or
release lifetime MUST treat incomplete as fail-closed, never empty. Add v1 and
v2 startup/main-loop/recovery/final-idle tests proving incomplete scans cannot
publish a clean stopped state or strand a ready/claimed envelope.

### Significant: migration scratch inventory is materialized without a bound

Status inspection, migration preparation, reconciliation, and cleanup call
`set(os.listdir(scratch_fd))`, materializing attacker-controlled directory
contents before rejecting unknown entries. The fixed scratch inventory has
only three allowed names; inspection MUST stream descriptor-relative entries
and reject on the first unknown or fourth distinct entry with constant bounded
memory. Tests must demonstrate the bounded helper is used across every scratch
path and blocks a large hostile inventory without DuckDB access or mutation.

### Moderate: successful migration can report a stale `pending_v2`

`pending_v2` is captured before store validation/draining/copying and is not
refreshed before a successful return, although v2 publication is explicitly
allowed during migration. Take one final complete v2 queue snapshot after
canonical/state publication while lifetime authority remains held; report that
snapshot. A publication after that queue-lock snapshot is outside the command
fact boundary. If the final scan is unsafe/unreadable/incomplete, return
`blocked` rather than a successful stale fact. Add a concurrent publication
phase test.

### Moderate: no-cleanup coverage stops before real writer-state publication

The store hook named `state_publication_ready` runs before the actual writer-
state temporary write, rename, and directory fsync in the writer layer. The
mocked state-failure test does not leave real no-cleanup state in those windows.
Add an internal test-only fault seam or filesystem injection covering state
temporary durability, canonical state rename, and directory sync with
`BaseException`-style no-cleanup interruption, then prove content-free blocked
facts and successful already-current reconciliation. Hardware power loss
remains an explicit limit.

### Minor: migration documentation is stale

`docs/telemetry.md` says every migration drains its v1 snapshot first. It must
state the backed-up retry exception: when an immutable exact backup already
matches canonical v1, retry completes v2 first and leaves later v1 work queued
for schema-v2 draining.

## Evidence disposition

Candidate `bbc1cbc` retains useful passing observations but is another failed
candidate. Additive evidence must qualify its shared-receipt, writer-scan,
bounded-scratch, pending-count, and state-publication claims before closure.

## Correct behavior retained

- Prior migration crash/idempotency and privacy findings are materially fixed.
- Direct-library v1 production telemetry and v1 analytical views remain
  preserved.
- Production retrieve command instrumentation remains untouched.
- Backups are not overwritten or automatically deleted.
- Management outputs remain content-free and provider/network inert.
- The intentionally deleted unsupported release-check module remains absent.

## Verdict

FAIL. Receipt temporary recovery can either rotate receipts too early or wedge
at capacity; incomplete writer scans can strand accepted work; scratch
inventory handling is not resource-bounded. The moderate fact/attestation and
minor documentation gaps are also required before a fresh exact-commit review.

## Residual risk

Review was static. Runtime evidence remains one macOS arm64 host with DuckDB
1.5.4. Simulated no-cleanup interruption is not hardware power-loss testing,
and view/catalog identities remain version-sensitive.
