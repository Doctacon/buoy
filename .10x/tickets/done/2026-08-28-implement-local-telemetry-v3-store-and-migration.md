Status: done
Created: 2026-08-28
Updated: 2026-08-29
Parent: .10x/tickets/done/2026-08-28-retrieval-telemetry-v3-plan.md
Depends-On: .10x/tickets/done/2026-08-28-integrate-provider-accounting-into-telemetry-v3.md

# Implement Local Telemetry V3 Store and Migration

## Scope

Implement inbox/receipt/writer/store/status/flush/migrate support for canonical v3 envelopes and the exact normalized schema/views in `.10x/specs/local-telemetry-v3-storage-and-migration.md`.

## Acceptance criteria

- V3 has distinct inbox/ready/claimed/receipt filename validation; old writers cannot consume it.
- New writers safely process v1/v2/v3 with one global replay/conflict identity and leave unsupported newer work pending.
- Fresh stores initialize exact schema 3.
- Existing schema v2 remains non-mutated until explicit migrate; status/flush report exact v3 pending and upgrade-required facts.
- V2-to-v3 migration creates and validates a fixed immutable v2 backup, preserves the existing v1 backup, and proves all v1/v2 rows and old view results value-equivalent.
- Command, operation, inference, provider, spans, and events commit atomically.
- New stable views have exact ordered columns/types/SQL hashes and correct preview/failure/fallback/null/count semantics.
- Exact object inventory, backup/source identity, crash/retry, replay/conflict, unsafe path/object, and queue bounds fail closed without loss.
- Status/flush/migrate/producer/writer perform zero provider/model/network work.
- Privacy sentinels are absent from envelope, queues, receipts, state, scratch/backup diagnostics, database values, and command output.
- Focused storage/writer/migration tests pass on Python 3.11 and 3.13 without touching the owner's real telemetry store.

## Evidence expectations

Use temporary telemetry homes and copied synthetic v2 fixtures only. Record migration content identities, old/new view comparisons, crash-table coverage, status/flush snapshots, privacy scans, and changed files. Do not open or mutate the real `~/.buoy/telemetry` store.

## Explicit exclusions

Real-store migration, live retrieval/provider calls, retention/purge/backup deletion, automatic migration, user-selected paths, dashboard/UI, default-on telemetry, release, and unrelated cleanup.

## References

- `.10x/specs/local-telemetry-v3-storage-and-migration.md`
- `.10x/specs/local-telemetry-v2-storage-and-migration.md`
- `.10x/specs/local-telemetry-writer.md`
- `.10x/tickets/done/2026-08-28-integrate-provider-accounting-into-telemetry-v3.md`

## Progress and notes

- 2026-08-28: Opened after ratification; waits for final canonical v3 envelope shape.
- 2026-08-28: Activated as the third dependency in the integrated v3 milestone after the repaired sequential provider-free baseline passed on Python 3.13 and 3.11. Real telemetry storage remains prohibited.
- 2026-08-28: Source implementation exposed an exact storage-spec contradiction: complete provider accounting requires a catalog row whose receipt outcome is nullable when catalog was not begun, while the table declared `outcome NOT NULL`. Supervisor approved the semantics-preserving repair: physical outcome is nullable, null requires all catalog counters and invocation count zero, the row remains required, and the stable view preserves null. No `not_started` enum or row omission is permitted.
- 2026-08-29: Implemented distinct inbox-v3/receipt handling, three-version writer/status/flush behavior, exact normalized schema/views, global replay/conflict, fresh schema-v3 initialization, v2-to-v3 backup/atomic migration, retained-history subset validation, and the final production command v3 publication switch. Updated user telemetry documentation and preserved explicit historical v2 tests.
- 2026-08-29: Added adversarial v3 storage coverage for three-inbox capacity, default publication, atomic normalized rows, null catalog, unavailable accounting, inference/provider aggregates, all-version draining, old-view preservation, both backups, upgrade-required pending work, cross-version conflict, hostile backup, and crash/retry phases.
- 2026-08-29: Provider-free validation passed on Python 3.13 and isolated Python 3.11: each full suite reported `1315 passed, 1401 subtests passed` with only 57 pre-existing lxml deprecation warnings. Final schema/migration matrix reported `83 passed, 165 subtests passed`; v3 storage file reported `13 passed, 6 subtests passed`. Compileall and `git diff --check` passed.
- 2026-08-29: Sdist/wheel build passed. A temporary-home offline installed-wheel preview produced inbox-v3 work; status after eventual writer completion was healthy schema 3 with one persisted run, empty queue, and one v3 receipt. Writer idle cleanup left no survivor. Candidate evidence: `.10x/evidence/2026-08-29-local-telemetry-v3-store-and-migration.md`.
- 2026-08-29: No Turbopuffer/provider/model call, provider write, real telemetry-store open/mutation, staging, commit, push, release, or retained temporary asset occurred. Ticket remains active only for required independent review.
- 2026-08-29: Applied all parent-accepted review repairs: v2-backup-published retry now proves source/backup equality and publishes v3 before late v1/v2 drain; retained v1 backup is validated as an exact subset of later v1 history; status reconciles all unaccounted v3 terminal receipts; normalized inference/provider validation preflights cardinality and uses governed fetch limits; migration-v3 database/WAL caps are checked before classification/cleanup; and migrate help describes one supported next-version step.
- 2026-08-29: Added crash-after-v2-backup plus late-publication migrate/flush coverage, post-v1-backup append migration, v3 receipt accounting/incomplete cases, hostile normalized cardinality, bounded fetch limits, oversized scratch preservation, production-default artifact privacy, v3 management no-network, exact ordered view matrix, production-default representative CLI, and production-v3 subprocess timing coverage. Historical v2 command tests remain explicit.
- 2026-08-29: Review-repair validation passed: focused adversarial matrix `189 passed, 226 subtests passed`; full Python 3.13 and isolated 3.11 suites each `1325 passed, 1406 subtests passed`; build and offline installed-wheel preview/flush/status/help passed. Installed flush committed one v3 observation and healthy status showed an empty queue and complete accounting. No provider/model operation, real-store access, staged file, release action, or surviving writer occurred.
- 2026-08-29: Applied the final accepted P1 terminal-drain repair. During ordinary v2-to-v3 migration, each compatible v1/v2 drain pass now performs a bounded rescan and blocks before backup/canonical publication when receipt publication failed or the queue is unsafe, unreadable, incomplete, or still has a claim. Backup-published retry still skips late v1/v2 draining and therefore retains its previously reviewed publication-first semantics.
- 2026-08-29: Added receipt-publication-exception and acknowledgement-false fault cases after a schema-v2 store commit. Both first attempts return blocked with schema v2 authoritative and one recoverable claim. Retry either emits one replay receipt or proves the already-published committed receipt, leaves one persisted command, zero conflicts/incomplete accounting, and migrates to schema v3. Updated the final-snapshot concurrency test to distinguish the new pre-migration rescan from the queue-lock-linearized final snapshot.
- 2026-08-29: Final P1 validation passed on Python 3.13 and isolated 3.11 (`96 passed, 169 subtests passed` each) for v2/v3 migration and writer suites. The broader Python 3.13 suite passed (`1326 passed, 1408 subtests passed`) with only 57 pre-existing lxml warnings. No provider/network/model, real store, staging, commit, or unrelated action occurred.
- 2026-08-29: Final independent acceptance review mapped transport, multi-version writer, exact schema/views, migration/history, atomic normalized insertion, bounds/security, privacy/no-network, compatibility, packaging, and terminal-drain behavior to evidence; no P0/P1/P2 issue remained. Parent reran `git diff --check` and current v2/v3 storage tests: `70 passed, 164 subtests passed`. Review: `.10x/reviews/2026-08-29-local-telemetry-v3-store-and-migration-review.md`.
- 2026-08-29: Closure reconciliation confirmed real-store migration remains an explicit exclusion, not unsupported acceptance. Retrospective extracted `.10x/knowledge/telemetry-migration-freezes-only-terminal-drained-snapshots.md`; no additional defect or follow-up was found.

## Blockers

None.
