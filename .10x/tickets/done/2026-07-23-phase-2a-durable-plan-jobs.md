Status: done
Created: 2026-07-23
Updated: 2026-07-23
Parent: .10x/tickets/done/2026-07-23-phase-2a-public-plan-workflow.md
Depends-On: .10x/tickets/done/2026-07-23-phase-2a-shared-planning-service.md

# Implement Durable Single-Worker Plan Jobs

## Scope

Implement `.10x/specs/phase-2a-plan-job-lifecycle.md`: safe job/event models, atomic store, transition enforcement, restart interruption, one-active in-process execution, progress sanitization, event observation/replay, and shared-service integration.

## Acceptance criteria

- All allowed/invalid transitions, terminal immutability, success/failure/interruption, restart conversion, conflict, new-ID retry, atomic persistence, event sequences/replay, sanitization, unique output directories, integrity-before-success, and no duplicate execution are tested.
- Job records contain only ratified safe fields and relative paths.
- No API/frontend or excluded authority is added.

## Evidence expectations

Record lifecycle/durability/concurrency tests and failure/restart limits.

## References

- `.10x/specs/phase-2a-plan-job-lifecycle.md`
- `.10x/specs/phase-2a-public-source-planning-service.md`
- completed shared-service ticket/evidence

## Progress and notes

- 2026-07-23: Opened from ratified Phase 2A scope.
- 2026-07-23: Implemented typed safe job/event records, strict state transitions, atomic JSON plus append-only JSONL durability, startup interruption, a concurrency-one in-process executor, bounded progress projection, unique managed output binding, shared planning-service execution, and historical/live event observation. Added 13 offline lifecycle/durability/concurrency/integrity tests; focused, 256-test shared compatibility, and 683-test full validation passed. Evidence is recorded at `.10x/evidence/2026-07-23-phase-2a-durable-plan-jobs.md`. Ticket remains active pending the required independent review.
- 2026-07-23: Repaired all four durable-job review findings: record-first sequence-bound commits now reconcile missing/partial final events after crashes and propagate fsync failures; service-lifetime portalocker ownership prevents cross-instance/process recovery or execution overlap; managed artifact directories are descriptor-created/no-follow with inode ancestry and final-output replacement checks; record/event reads are no-follow, identity-bound, hard-link rejecting, and replacement detecting. Added fault-injection plus 20 subprocess kill-boundary cases, cross-store/process locks, symlink/escape/replacement, and record/event tamper regressions. Focused 30-test, shared 265-test, and full 692-test validation passed. Ticket remains active for independent re-review.
- 2026-07-23: Repaired the three final-review findings. Managed planning now writes through a held job-directory descriptor alias while building persisted artifacts with stable logical final paths, retains the descriptor through the worker operation, and fails closed where descendant-capable aliases are unavailable. Configured managed roots are traversed from the filesystem root one no-follow descriptor-relative component at a time. All record/event reads, reconciliation, and mutations now share one inter-instance mutation lock through non-reentrant locked helpers. Added intermediate-ancestor symlink, in-operation replacement, logical-path persistence/unsupported-alias, Git descriptor inheritance, and overlapping cross-store reconcile/writer regressions. Focused/shared offline validation passed; ticket remains active for required independent review.
- 2026-07-23: Repaired the two portability re-review blockers. Managed website/Git writers now use a securely created private staging directory on every supported platform; verified whitelisted artifacts are copied into the held final descriptor with no-follow/exclusive ordinary-file operations, fsyncs, and post-copy hashes, while safe incomplete whitelisted artifacts are preserved when possible and staging/descriptor paths do not persist. Durable state reopens now traverse every configured component without following links and compare stored state-root/command-center/jobs inode identities before every read or mutation. Added Darwin-capable offline website/Git success, final-path replacement/no-outside-write, recursive path-leak, and post-construction state-ancestor read/mutation regressions. Focused 62-test, targeted 5-test, and shared 272-test offline validation passed.
- 2026-07-23: Independent final acceptance review passed on Darwin with no blockers. Closed after all prior durability, containment, ownership, identity, recovery, portability, transition, and event findings mapped to tests/evidence.

## Blockers

None after dependency completion.
