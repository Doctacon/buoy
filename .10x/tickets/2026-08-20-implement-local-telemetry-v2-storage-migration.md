Status: active
Created: 2026-08-20
Updated: 2026-08-20
Parent: .10x/tickets/2026-08-20-correct-retrieve-command-telemetry-latency.md
Depends-On: None
Decision: .10x/decisions/buoy-records-command-and-pipeline-retrieve-latency.md
Specification: .10x/specs/local-telemetry-v2-storage-and-migration.md

# Implement Local Telemetry V2 Storage and Migration

## Scope

Implement the version-2 envelope, separate inbox, dual-version writer,
additive exact DuckDB schema/views, read-only upgrade-required status, bounded
flush behavior, and explicit backed-up migration command. Use deterministic
content-free fixture traces; do not instrument production retrieve commands in
this ticket.

Owned modules are telemetry envelope, queue, store, writer, management CLI,
entry-point telemetry dispatch needed for `migrate`, focused tests, and the
minimum user documentation for migration mechanics.

## Required work

- Preserve exact v1 encoder/decoder, inbox, rows, views, and direct-library
  producer compatibility.
- Add canonical independently validated v2 command/retrieval-operation
  envelopes and fixed v2 queue/receipt names.
- Add exact schema-v2 command/operation tables and two canonical v2 views while
  retaining exact v1 view SQL and values.
- Make the writer safely drain v1/v2 under the specification's schema matrix.
- Expose read-only `upgrade_required` and versioned queue facts.
- Add `buoy telemetry migrate [--json]` with exact authority, output,
  backup/scratch, idempotency, atomicity, and no-deletion behavior.
- Keep status free of DuckDB imports/connections and keep all management paths
  provider/model/network inert.

## Acceptance criteria

1. Every envelope shape/value/graph and privacy requirement in the storage spec
   has direct positive and adversarial decoder coverage.
2. Existing v1 stores and envelopes remain accepted with byte/semantic
   equivalence and unchanged v1 view results.
3. Fresh initialization creates exact schema v2; deterministic v2 live,
   preview, and pre-pipeline-error fixtures persist atomically to exact v2
   views.
4. Status/flush cover absent, exact v1, upgrade-required with/without v2
   backlog, exact v2, incompatible, unsafe, busy, and mixed-version queues.
5. Migration covers absent/already-current/success/busy/blocked, v1 backlog,
   preexisting exact/mismatching backup, idempotent retry, and every specified
   crash point without changing an unproven canonical store.
6. Exact-byte privacy scans cover envelope, both queues, receipts, state,
   output, scratch, backup diagnostics, and database values.
7. Audit hooks prove zero socket/DNS/provider/model/catalog/retrieval calls.
8. Focused telemetry suites, existing v1 writer/store/queue suites, full tests,
   compilation, lock, distribution, clean-wheel management lifecycle, and diff
   hygiene pass on the ticket's required runtimes.

## Evidence expectations

Record exact commands, runtime/host identities, focused and full results,
schema/view identities, migration before/after counts, crash-injection matrix,
privacy sentinel result, no-network result, changed paths, and residual risks
in a new evidence record related to this ticket.

## Explicit exclusions

No changes to `cli.py` retrieve behavior, retriever trace nesting, routing,
ranking, evidence, provider calls, live credentials/namespaces, real
`~/.buoy`, automatic migration, backup deletion, release, installed tool,
`main`, or package publication.

## Assumption provenance

- Explicit migration, retained backup, all retrieve modes, and separate
  command/pipeline latency are user-ratified in the 2026-08-20 workstream.
- The exact v1 security/durability behavior is record-backed by
  `.10x/specs/local-telemetry-writer.md` and its evidence/reviews.
- No external service behavior is assumed or required.

## Blockers

Independent exact-commit review of `bbc1cbc` failed. The final bounded repair
covers trusted-time receipt rotation/recovery, fail-closed ordinary writer
incomplete scans, constant-memory scratch inventories, final `pending_v2`
snapshot facts, actual writer-state publication crash windows, and migration
documentation. See
`.10x/reviews/2026-08-20-local-telemetry-v2-storage-migration-final-review.md`.

The intentionally stale release-check collector separately blocks unfiltered
full-suite collection and is owned by
`.10x/tickets/2026-08-20-reconcile-missing-release-checks-test-harness.md`; it
must not widen this ticket.

## Progress and notes

- 2026-08-20: Opened after user ratification and source/record inspection.
  Implementation intentionally deferred to a later turn under the governing
  spec-first execution gate.
- 2026-08-20: Execution started on `work/retrieval-command-telemetry-v2` at
  governing commit `d116448`; mandatory branch/worktree checks passed. Scope
  remains storage/migration only, with production retrieve instrumentation
  excluded.
- 2026-08-20: Supervisor ratified the missing mechanical schema detail before
  implementation: append metadata columns `command_runs_view_sha256` and
  `command_stage_view_sha256`; add no secondary indexes beyond declared
  primary-key and `CHECK` constraints. The active storage spec now states this
  exact contract.
- 2026-08-20: Implemented the bounded storage/migration slice: canonical v2
  envelopes, separate v2 inbox/receipts, shared-capacity dual writer, exact
  additive schema/views, read-only upgrade status and blocked flush behavior,
  and explicit retained-backup migration. Production retrieve instrumentation
  remains untouched.
- 2026-08-20: Focused Python 3.13 validation passed 157 tests plus 121 subtests;
  focused Python 3.11 validation passed 138 tests plus 100 subtests. The full
  suite excluding the preexisting missing `scripts.release_checks` collector
  passed 1016 tests plus 903 subtests. Offline wheel status/flush/migrate
  lifecycle, compilation, lock check, ranking validator, diff check, privacy,
  no-network, exact-schema, migration retry, and crash matrix passed. Evidence:
  `.10x/evidence/2026-08-20-local-telemetry-v2-storage-migration.md`.
- 2026-08-20: Supervisor ratified the implemented exact status/migrate JSON
  names and nesting: flat versioned counts under `queue`, top-level
  `migration_backup_present`, and the eleven migration result keys now stated
  in the active storage spec. No further output keys or nesting were added.
- 2026-08-20: Implementation handoff is ready but ticket intentionally remains
  active pending independent exact-commit review and parent closure.
- 2026-08-20: Three independent fresh-context reviews plus parent inspection
  returned FAIL for exact commit `0989690`. Deterministic blockers include
  non-atomic backup creation, unrecovered post-publication scratch, semantic
  v1-row/privacy gaps, incomplete exact-object validation, invalid v2 graph
  acceptance, flush snapshot interference, and evidence overclaim. The complete
  accepted finding set and required repair tests are recorded at
  `.10x/reviews/2026-08-20-local-telemetry-v2-storage-migration-review.md`.
- 2026-08-20: Repair candidate `80d7562` attempted every accepted review finding:
  scratch-backed no-overwrite backup publication and interrupted-copy retry;
  pre/post-publication scratch reconciliation; bounded 128-trace semantic and
  privacy validation; database-wide user-object rejection; stricter v2 graph
  invariants; snapshot-isolated flush; migration preflight ordering; contained
  state-publication failure; append auxiliary-path checks; aggregate capacity;
  text/JSON parity; qualified status documentation; and expanded adversarial,
  replay/conflict, privacy, crash, and path tests. Production retrieve timing
  remains excluded.
- 2026-08-20: Repaired focused telemetry suites passed on Python 3.11 and 3.13
  with 173 tests and 142 subtests. The agreed filtered full suite passed 1034
  tests and 924 subtests; only obsolete `tests/test_dynamic_version.py` was
  excluded under its separate preexisting owner. The ticket stayed active for
  exact-commit re-review.
- 2026-08-20: Three fresh reviewers returned FAIL for `80d7562`. Most first-
  review defects were verified repaired, but backup-published retry can wedge
  on later v1 work, and fail-closed gaps remain for incomplete scans, v1/object
  inventory, edited v2 content, retained-backup identity, shared receipts, and
  orphan auxiliary state. The complete accepted findings are recorded at
  `.10x/reviews/2026-08-20-local-telemetry-v2-storage-migration-rereview.md`.
- 2026-08-20: The second bounded repair implements every accepted rereview
  finding: a proven published-backup retry skips intervening v1 queue work;
  incomplete scans block before store import; exact database-wide object and
  v1/v2 content validation is enforced; retained backup identity must match;
  receipt limits/rotation/reconciliation are shared; orphan auxiliary state is
  blocked and nonmutating; and all material migration hooks use no-cleanup
  process-death coverage. The ticket remains active pending fresh exact-commit
  review.
- 2026-08-20: Second-repair focused suites passed on Python 3.11 and 3.13 with
  181 tests and 167 subtests. The filtered full suite passed 1042 tests and 949
  subtests; the separately owned stale dynamic-version collector remains the
  sole exclusion. Targeted rereview/privacy/no-network/crash/capacity probes
  passed 11 tests and 35 subtests.
- 2026-08-20: Three fresh reviewers returned FAIL for `bbc1cbc`. They verified
  the second-review migration defects as repaired, then found one receipt
  recovery blocker plus adjacent fail-closed/boundedness/fact/attestation gaps:
  untrusted rotation time, ordinary-writer incomplete scans, unbounded scratch
  listing, stale `pending_v2`, uncovered writer-state publication windows, and
  stale docs. Full findings:
  `.10x/reviews/2026-08-20-local-telemetry-v2-storage-migration-final-review.md`.
- 2026-08-20: The final bounded repair uses queue-lock-held trusted current time
  for rotation; blocks incomplete ordinary-writer scans at startup, recovery,
  drain, and idle release; streams every fixed scratch inventory in constant
  memory; refreshes successful `pending_v2` after durable state publication;
  injects actual state temporary/rename/directory-sync deaths; and documents
  the backed-up retry ordering. The ticket remains active for fresh review.
- 2026-08-20: Final-repair focused suites passed on Python 3.11 and 3.13 with
  186 tests and 185 subtests. The filtered full suite passed 1047 tests and 967
  subtests; the targeted receipt/incomplete-scan/scratch/pending/state-crash/
  privacy/no-network command passed 7 tests and 18 subtests.
