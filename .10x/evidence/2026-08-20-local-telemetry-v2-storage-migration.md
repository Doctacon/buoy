Status: recorded
Created: 2026-08-20
Updated: 2026-08-21
Relates-To: .10x/tickets/done/2026-08-20-implement-local-telemetry-v2-storage-migration.md, .10x/specs/local-telemetry-v2-storage-and-migration.md, .10x/reviews/2026-08-20-local-telemetry-v2-storage-migration-review.md, .10x/reviews/2026-08-20-local-telemetry-v2-storage-migration-rereview.md, .10x/reviews/2026-08-20-local-telemetry-v2-storage-migration-final-review.md, .10x/reviews/2026-08-21-local-telemetry-v2-storage-migration-acceptance-review.md, .10x/reviews/2026-08-21-local-telemetry-v2-storage-migration-post-fix-review.md, .10x/reviews/2026-08-21-local-telemetry-v2-storage-migration-final-acceptance-review.md

# Local Telemetry V2 Storage and Migration Validation

## What was observed

Ticket 1 now provides a canonical version-2 command envelope, separate
`inbox-v2`, dual-version queue/writer/store behavior, exact additive DuckDB
schema version 2, versioned read-only status/flush behavior, and explicit
backed-up migration. Production retrieve command and pipeline instrumentation
were not changed.

The supervisor ratified two mechanical clarifications. Metadata appends
`command_runs_view_sha256` and `command_stage_view_sha256`, with no secondary
indexes beyond specified primary-key and `CHECK` constraints. The exact flat
status queue keys, top-level backup key, and eleven migration JSON keys were
also ratified as implemented. The active storage spec records both exact
contracts.

Host/runtime observed:

- Darwin 25.5.0 arm64 (`Mountain-Quail.local`);
- Python 3.11.5 and 3.13.0;
- DuckDB 1.5.4; and
- governing source commit `d116448` on
  `work/retrieval-command-telemetry-v2`.

Canonical schema-v2 view SHA-256 values observed from a fresh in-memory exact
schema were:

- `retrieval_runs_v1`:
  `192e912beff4dd19d9367942ac89fcfdf03bfae49c85987fbf794a90befb3f13`;
- `retrieval_stage_latency_v1`:
  `8aaf49161023810a1b2dbd715a8f3c4ae960cc4f0fb6666845bf90438e0e6c3b`;
- `retrieval_command_runs_v2`:
  `68af0f43a4906431f7b30ea8d87c61190f048eca32b87e4bf089347ba03ed200`;
- `retrieval_stage_latency_v2`:
  `be9f2be5ed95736ab5ebb47edfa7d52a8cac42572abfe6de1f88b37d52ea8453`.

## Procedure and results

### Acceptance-criterion mapping

1. **Envelope shape/value/graph/privacy:**
   `tests/test_telemetry_v2_storage.py::Version2EnvelopeTests` exercises
   deterministic live, preview, and pre-pipeline-error round trips plus
   unknown keys, wrong versions, duration/summary mismatches, prohibited
   attributes, and content-free rejection reasons. The established v1
   envelope suite remained green.
2. **V1 compatibility:** established envelope/queue/store/writer/producer/local
   telemetry tests passed on both focused runtimes. Schema v2 retains the
   exact v1 tables and view DDL/digests; migration compares ordered v1 table
   and view values before publication. Direct v1 append is supported against
   exact v1 and v2 stores.
3. **Fresh exact v2 and deterministic fixtures:** focused tests commit live,
   preview, and pre-pipeline-error `CommandTraceRows` atomically. They assert
   schema 2, `(6.0, null, null)` pipeline-duration semantics, one non-root live
   stage, and zero v1 rows. Exact layouts, constraints, no-secondary-index
   inventory, function/macro inventory, view layout/nullability, SQL digests,
   and metadata are validated.
4. **Status/flush matrix:** established suites plus focused upgrade tests cover
   absent, compatible, incompatible, unsafe, busy, backlog, timeout, and
   classified paths. New tests prove exact-v1 status is degraded without v2
   work, blocked with v2 work, reports separate v1/v2 counts, opens no DuckDB,
   and leaves v2 work pending on blocked flush. The dual writer drains v1 and
   recovers a v2 claim to ready behind schema v1.
5. **Migration:** focused tests cover absent, exact-v1 success, v1 backlog,
   already-current retry, busy lifetime authority, mismatching backup,
   preexisting exact backup retry, and injected faults at validated source,
   scratch creation/copy, transaction commit, scratch validation, backup
   create/fsync, canonical publication, directory fsync, and state-publication
   readiness. Every fault leaves canonical schema 1 or 2 provable; retry after
   exact backup creation succeeds.
6. **Privacy:** a prohibited exact-byte sentinel is present in a forged v2
   payload, independently rejected, and absent after terminal handling from
   receipts, state, status/migration output, and every remaining file beneath
   the isolated telemetry root. Canonical envelopes and database fixtures use
   only governed values; migration diagnostics never include DuckDB errors or
   stored values.
7. **No external calls:** focused audit patches socket/DNS to fail and blocks
   imports of `buoy_search.cli`, `buoy_search.retriever`, and
   `buoy_search.routing` while exercising v2 publication, status, flush,
   writer persistence, and already-current migration. A separate backed-up
   migration test applies the same socket/DNS fail hooks to exact-v1 success.
8. **Validation/tooling:** results follow.

### Commands

- `uv run --offline --python 3.13 --with pytest python -m pytest
  tests/test_local_retrieval_telemetry.py tests/test_telemetry_envelope.py
  tests/test_telemetry_producer.py tests/test_telemetry_queue.py
  tests/test_telemetry_store.py tests/test_telemetry_writer.py
  tests/test_telemetry_cli.py tests/test_telemetry_v2_storage.py -q`
  exited 0: **157 passed, 121 subtests passed**.
- `uv run --offline --python 3.11 --with pytest python -m pytest
  tests/test_telemetry_v2_storage.py tests/test_telemetry_envelope.py
  tests/test_telemetry_queue.py tests/test_telemetry_store.py
  tests/test_telemetry_writer.py tests/test_telemetry_cli.py -q`
  exited 0: **138 passed, 100 subtests passed**.
- `uv run --offline --python 3.13 --with pytest python -m pytest -q
  --ignore=tests/test_dynamic_version.py` exited 0:
  **1016 passed, 903 subtests passed, 57 preexisting lxml warnings**.
- Unmodified `uv run --with pytest python -m pytest -q` exited 2 during
  collection because `tests/test_dynamic_version.py` imports absent
  `scripts.release_checks`. `git cat-file -e
  d116448:scripts/release_checks.py` exited 128, proving that file was already
  absent at the governing commit. This ticket did not invent or repair the
  unrelated release-check harness.
- `python3 -m py_compile src/buoy_search/telemetry_*.py` and
  `uv run python -m compileall -q src tests/test_telemetry_v2_storage.py`
  exited 0.
- `uv lock --check --offline` exited 0: **Resolved 157 packages** with no lock
  change.
- `python3 scripts/validate_ranking_contract.py` exited 0 and emitted the
  governed dataset/inventory hashes.
- `git diff --check` exited 0.
- `git diff --quiet -- src/buoy_search/cli.py
  src/buoy_search/retriever.py` exited 0, confirming the dependent production
  instrumentation surface is untouched.
- Offline distribution lifecycle in a temporary directory:
  `uv build --offline --out-dir <temp>/dist`; create a temporary venv; install
  the wheel with `uv pip install --no-deps`; run installed `buoy telemetry
  status --json`, `flush --timeout 0 --json`, and `migrate --json` with an
  isolated empty `HOME`; inspect the wheel module inventory. The command
  exited 0, produced `disabled`, `empty`, and `absent`, included all six
  telemetry runtime modules, and created no `<temp>/home/.buoy`.

## Migration fixture counts and crash matrix

The deterministic v1-backlog migration observed one v1 run, one span, and zero
events in both the retained backup and migrated canonical store. Empty exact-v1
migration observed `(0, 0, 0)`. Deterministic v2 fixtures observed three
command rows, one retrieval-operation row, two null operation joins, and one
non-root stage row.

Injected phase outcomes:

| Fault phase | Canonical after fault |
| --- | --- |
| validated source | exact v1 |
| scratch created | exact v1 |
| scratch copied | exact v1 |
| transaction committed | exact v1 |
| scratch validated | exact v1 |
| backup created | exact v1; exact-backup retry succeeds |
| backup fsynced | exact v1 |
| canonical published | exact v2 |
| directory fsynced | exact v2 |
| state-publication ready | exact v2 |

Every row also asserted no canonical WAL remained.

## What this supports or challenges

This records the first implementation candidate's claimed focused command
results and demonstrates substantial v1/v2 fixture behavior. It does **not**
support every ticket acceptance criterion. Independent exact-commit review at
`.10x/reviews/2026-08-20-local-telemetry-v2-storage-migration-review.md`
identified deterministic crash/retry, semantic/privacy, exact-object,
snapshot-isolation, boundedness, and adversarial-test gaps not exercised by
these commands and returned FAIL. This evidence remains useful as a baseline;
a repaired candidate requires additive evidence and fresh review before ticket
closure.

## Limits and residual risks

- Python 3.11/3.13 were exercised on one macOS arm64 host, not CI's complete OS
  matrix.
- The complete suite cannot collect until the independently stale
  `tests/test_dynamic_version.py` release-check surface is removed by its
  separate owner; the user confirmed `scripts/release_checks.py` was
  intentionally deleted as unsupported/nonfunctional. The telemetry candidate
  did not restore it, and 1016 other tests passed when that collector was
  excluded.
- Crash injection is process-exception simulation around each publication
  phase, not power-loss or filesystem-fault hardware testing.
- Exact schema/view hashes are DuckDB-1.5.4 identities and remain intentionally
  version-sensitive.
- Independent exact-commit review and parent closure remain pending, so the
  implementation ticket remains active.

## Repaired candidate observations

The failed `0989690` observations above remain the first-candidate baseline.
The following are worker-observed results for candidate `80d7562`; they are not
closure claims and are qualified by the failed exact-commit re-review below.
The repair based on
`.10x/reviews/2026-08-20-local-telemetry-v2-storage-migration-review.md`
produced the following additional source-observed and executed evidence.

### Accepted-finding mapping

- Backup bytes now stream only into fixed private
  `database-migrate-v2/telemetry-v1-backup.duckdb`; the complete candidate is
  fsynced, hashed, exact-v1/schema/semantic validated, and atomically published
  without overwriting an existing final backup. Injected mid-copy process death
  leaves no final backup, and retry safely removes the recognized partial
  candidate, drains a newly published v1 envelope, and migrates both traces.
  A separate injected death in the hard-link publication window proves the
  same-inode two-link state is recognized and retry restores one-link final
  history.
- An exception after canonical v2 publication leaves a provable exact v2 store
  and recognized empty scratch. Status reports `present_unverified`; append
  fails closed; already-current migrate removes only that exact scratch,
  publishes matching state, and subsequent append/flush succeed.
- Exact-v1 migration preflight and every source/scratch/backup/final comparison
  now stream trace IDs in batches of at most 128, preflight every base-table
  scalar/JSON byte length, cap each fetched graph at 256 spans/one event, and
  canonical-encode each trace through the v1 semantic/graph/privacy validator.
  No whole-store/table/view result is retained. A 129-trace fixture crosses the
  batch boundary, while an exact-shape store containing
  `PRIVATE_RAW_ERROR_CONTENT_SENTINEL` is blocked before backup/scratch creation
  or canonical mutation and never emits the sentinel.
- Exact schema validation rejects attached non-internal databases, every user
  schema outside canonical `main`, unknown tables/views/indexes/constraints,
  and v2 user functions/macros using qualified, bounded catalog reads. A hidden
  schema/table blocks both append and migration.
- The v2 adversarial matrix now directly covers wrong versions/shape/private
  keys, root/trace/span IDs, duplicates, missing parents/cycles, ordering,
  containment, duration/summary mismatches, root/pipeline status/outcome,
  live-success pipeline presence, command/pipeline retrieval-mode equality,
  error-category consistency, widening fallback, and event owner/interval.
- Fixed-snapshot flush ignores a later v2 publication that blocks the global
  writer behind exact schema v1; its original v1 snapshot still returns
  `flushed` and the v2 envelope remains recoverable.
- Migration structurally scans both inboxes plus root/store/backup/scratch
  before loading the store or making any DuckDB connection. Hostile v1/v2
  inboxes, backup symlinks, and unknown scratch entries all prove zero calls to
  the patched database connector.
- Final writer-state failure returns exact `blocked` JSON with source version 1,
  target version 2, migrated counts, and backup-present facts; no injected raw
  state error escapes. Canonical v2 remains authoritative and a later
  already-current invocation reconciles state and succeeds. Healthy repeated
  already-current migration leaves backup and writer-state bytes unchanged.
- Normal append rejects every migration scratch and hostile/malformed retained
  backup before mutation, while allowing an exact safe v1 retained backup next
  to exact schema v2.
- Status computes shared entry/byte/temp capacity from aggregate v1+v2
  occupancy. Exact split entry and byte boundaries report `capacity_full=true`.
- Migrate text now renders exactly the same eleven facts as JSON, including
  `schema_version` and `database_path`. Documentation now states the read-only
  stateless/mismatched-state `present_unverified` limit.
- Store and writer tests now prove exact v1/v2 replay, valid same-version
  conflicts, global cross-version conflicts, atomic unchanged graphs, and
  replay/conflict terminal receipts.

### Repaired validation commands and results

- `uv run --offline --python 3.11 --with pytest python -m pytest
  tests/test_local_retrieval_telemetry.py tests/test_telemetry_envelope.py
  tests/test_telemetry_producer.py tests/test_telemetry_queue.py
  tests/test_telemetry_store.py tests/test_telemetry_writer.py
  tests/test_telemetry_cli.py tests/test_telemetry_v2_storage.py -q` exited 0:
  **173 passed, 142 subtests passed**.
- The same focused command with `--python 3.13` exited 0:
  **173 passed, 142 subtests passed**.
- `uv run --offline --python 3.13 --with pytest python -m pytest -q
  --ignore=tests/test_dynamic_version.py` exited 0:
  **1034 passed, 924 subtests passed, 57 preexisting lxml warnings**.
  `scripts/release_checks.py` was intentionally deleted because that release
  check was unsupported/nonfunctional. Only the obsolete separately owned
  `tests/test_dynamic_version.py` collector is excluded; this ticket neither
  restores the script nor alters that test debt.
- The exact seven-test privacy/no-network/semantic/mid-copy/post-publication/
  inbox/backup/scratch probe exited 0: **7 passed, 4 subtests passed**.
- `uv lock --check --offline`, py_compile/compileall, `git diff --check`, focused
  Ruff `F,E9`, and `python3 scripts/validate_ranking_contract.py` exited 0.
- Offline sdist/wheel build, no-dependency install in a temporary Python 3.13
  environment, module inventory, and installed `telemetry status`, `flush`, and
  `migrate` against an isolated empty `HOME` exited 0 with outcomes
  `disabled`, `empty`, and `absent`; no isolated `.buoy` was created.
- `git diff --quiet -- src/buoy_search/cli.py
  src/buoy_search/retriever.py` exited 0. Dependent production instrumentation
  remains untouched.

### Repaired evidence limits

- Process-death/failure injection is deterministic exception and filesystem
  publication-window simulation, not hardware power-loss testing.
- Python 3.11/3.13 ran on one macOS arm64 host.
- DuckDB 1.5.4 canonical view SQL identities remain intentionally
  version-sensitive.

## Exact-commit re-review challenge

Three fresh reviewers returned FAIL for `80d7562`; see
`.10x/reviews/2026-08-20-local-telemetry-v2-storage-migration-rereview.md`.
They found that the successful commands above do not exercise a backup-
published crash followed by later v1 work, incomplete queue scans, schema-v1
macros plus sequences/types, edited v2 semantic/privacy content, semantically
hostile or valid-but-mismatching retained backups, split-version receipt
capacity, or orphan backup/scratch facts. The evidence therefore does not yet
support ticket closure. A later candidate must record additive tests and exact
results while preserving both failed-candidate histories.

## Second rereview repair observations

The `0989690` and `80d7562` histories above remain failed-candidate evidence.
The following observations apply only to the bounded repair of the accepted
findings in
`.10x/reviews/2026-08-20-local-telemetry-v2-storage-migration-rereview.md`.
They do not close the ticket; fresh exact-commit review remains mandatory.

### Finding-to-test mapping

- `test_backup_published_retry_skips_later_v1_then_flushes_once` injects a
  no-cleanup death after immutable backup publication, publishes a later v1
  envelope, proves retry migrates only the backup-matching canonical source,
  preserves the queued envelope and exact backup bytes, then flushes that
  envelope exactly once into schema v2.
- `test_incomplete_migration_scans_block_before_store_import` covers v1 and v2
  incomplete initial scans plus the post-lifetime-lock scan. All return exact
  blocked output and assert zero store-module loads/connections.
- `test_exact_object_inventory_rejects_all_user_metadata_v1_and_v2` covers
  macros/functions, sequences, custom types, column defaults, and comments for
  both schema versions. The retained v1 shadow-macro test now proves fail-
  closed behavior while qualified system-catalog queries remain uninvoked and
  safe.
- `test_exact_v2_content_privacy_and_graph_edits_block` covers prohibited JSON,
  over-bound scalar content, graph mismatch, and over-256 span cardinality in
  exact-layout v2 stores. Existing v1/v2 stores now stream in 128-trace batches
  through their canonical encoder/graph/privacy validators before compatible,
  already-current, replay/conflict, or mutation decisions.
- `test_retained_backup_must_be_valid_and_match_canonical_v1_history` covers
  prohibited backup content, invalid backup graph, and internally valid but
  different v1 history. Append and already-current reconciliation compare the
  backup's bounded v1 content identity with canonical schema-v2 retained v1
  identity before mutation.
- `test_receipt_capacity_rotation_and_reconciliation_are_shared` and
  `test_shared_receipt_byte_and_temporary_boundaries` prove combined v1/v2
  final and temporary receipt count/byte enforcement, globally ordered age
  rotation under the shared lock, and a combined writer-state identity set
  that remains within the single bound.
- `test_orphan_auxiliary_store_state_is_blocked_and_nonmutating` covers safe
  orphan backup, migration scratch, initialization scratch, and hostile backup
  variants. Safe backup presence remains accurately reported; all variants
  leave the exact directory inventory unchanged.
- `test_every_migration_fault_keeps_one_provable_canonical_version` now uses an
  uncaught `BaseException`-style process-death class at every material source,
  scratch, backup candidate, transaction, backup publication/validation,
  canonical publication, directory-sync, and state-ready hook, then proves a
  successful recovery to exact schema v2. Mid-copy and hard-link publication
  windows retain their separate no-cleanup tests.

### Second-repair commands and exact results

- Focused Python 3.11 telemetry command exited 0: **181 passed, 167 subtests
  passed**.
- The identical focused command on Python 3.13 exited 0: **181 passed, 167
  subtests passed**.
- `uv run --offline --python 3.13 --with pytest python -m pytest -q
  --ignore=tests/test_dynamic_version.py` exited 0: **1042 passed, 949
  subtests passed, 57 preexisting lxml warnings**. The excluded stale collector
  remains owned by
  `.10x/tickets/2026-08-20-reconcile-missing-release-checks-test-harness.md`;
  this repair did not restore or change that surface.
- The exact targeted rereview plus privacy/no-network/crash/shared-capacity
  command exited 0: **11 passed, 35 subtests passed**.
- `uv lock --check --offline`, py_compile/compileall, focused Ruff `F,E9`,
  `git diff --check`, and `python3 scripts/validate_ranking_contract.py` exited
  0. The dependency lock and ranking inventories were unchanged.
- `git diff --quiet -- src/buoy_search/cli.py
  src/buoy_search/retriever.py` exited 0. Production retrieve instrumentation
  remains outside this ticket.
- Exact-candidate offline sdist/wheel build, no-dependency Python 3.13 install,
  required telemetry module inventory, and installed `status`, `flush`, and
  `migrate` lifecycle in an isolated empty `HOME` exited 0. Outcomes were
  `disabled`, `empty`, and `absent`; no isolated `.buoy` path was created.

### Second-repair limits

- No-cleanup `BaseException` injection simulates abrupt process death at each
  store-layer hook but is not hardware power-loss testing.
- Filesystem and runtime validation remains one macOS arm64 host with DuckDB
  1.5.4; cross-platform power-loss/filesystem behavior is unverified.

## Final-review challenge to candidate bbc1cbc

Three fresh reviewers returned FAIL; see
`.10x/reviews/2026-08-20-local-telemetry-v2-storage-migration-final-review.md`.
They verified the accepted second-review migration findings as materially fixed
but found that recovered receipt rotation trusts stale/untrusted payload time,
ordinary writer paths treat incomplete scans as empty, scratch inventories use
unbounded `listdir`, successful `pending_v2` can be stale, actual writer-state
publication windows lack no-cleanup coverage, and migration documentation omits
the backed-up retry exception. Candidate `bbc1cbc` is therefore preserved as a
failed candidate, not closure evidence.

## Final-review repair observations

The `0989690`, `80d7562`, and `bbc1cbc` sections remain failed-candidate
history. The observations below apply only to the bounded repair of
`.10x/reviews/2026-08-20-local-telemetry-v2-storage-migration-final-review.md`.
They are implementation evidence, not ticket closure; fresh exact-commit review
is still required.

### Final-finding mapping

- `test_receipt_recovery_uses_trusted_time_for_split_capacity` fills combined
  v1/v2 final count and byte capacity, then recovers canonical receipt
  temporaries carrying future and ancient payload timestamps. Queue rotation
  samples `time.time_ns()` while the shared lock is held: future payload time
  cannot remove fresh receipts, while two currently old equal-mtime receipts
  rotate by basename and recovery publishes the terminal receipt. The retained
  receipt remains directly readable as flush evidence.
- `test_writer_lifecycle_blocks_every_incomplete_scan_phase` injects bounded
  incomplete v1 and v2 scans at startup, receipt/claim recovery, main work
  selection, and final idle-stop. Every path publishes `blocked/queue_unsafe`,
  never clean `stopped`; accepted ready/claimed work remains visible, and a
  fresh blocked state explicitly suppresses redundant start rather than
  silently claiming an empty queue.
- `test_large_hostile_scratch_inventory_is_bounded_and_nonmutating` places 512
  hostile fixed-mode files in migration scratch and exercises writer status,
  migrate preflight, store already-current reconciliation, preparation, and
  cleanup. The shared descriptor-relative helper retains at most the three
  governed names, rejects the first unknown/fourth distinct entry, opens no
  DuckDB connection, emits no sentinel, and changes no entry.
- `test_final_pending_v2_snapshot_includes_only_preboundary_publications`
  publishes v2 work immediately before and after the final queue-lock snapshot
  for migrated success and before already-current success. Pre-boundary work is
  reported; post-boundary work is correctly outside the fact. An incomplete
  final scan changes the outcome to blocked.
- `test_writer_state_publication_no_cleanup_crashes_reconcile` injects uncaught
  process death after actual writer-state temporary fsync/verification, final
  rename, and directory fsync. Canonical schema v2 and backup remain exact,
  exception sentinels reach no file, and already-current retry removes a safe
  temporary or re-fsyncs the final rename. A caught temporary-durability
  `OSError` returns content-free blocked source/target/backup facts and retries
  successfully.
- `docs/telemetry.md` now documents the proven published-backup retry exception:
  v2 completes before later v1 work is drained, and that work stays queued for
  the v2 writer without modifying retained history.

### Final-repair commands and exact results

- Focused telemetry suites on Python 3.11 exited 0: **186 passed, 185 subtests
  passed**.
- The identical focused command on Python 3.13 exited 0: **186 passed, 185
  subtests passed**.
- `uv run --offline --python 3.13 --with pytest python -m pytest -q
  --ignore=tests/test_dynamic_version.py` exited 0: **1047 passed, 967
  subtests passed, 57 preexisting lxml warnings**. Only the independently owned
  stale dynamic-version collector was excluded; this ticket did not change it.
- The exact targeted receipt/incomplete-scan/scratch/pending/state-crash/
  privacy/no-network command exited 0: **7 passed, 18 subtests passed**.
- `uv lock --check --offline`, py_compile/compileall, focused Ruff `F,E9`,
  `git diff --check`, and `python3 scripts/validate_ranking_contract.py` exited
  0. The dependency lock and ranking identities were unchanged.
- `git diff --quiet -- src/buoy_search/cli.py
  src/buoy_search/retriever.py` exited 0. Production retrieve instrumentation
  remains untouched.

### Final-repair limits

- The writer-state and store faults are deterministic process-death simulation,
  not hardware power-loss testing.
- Validation remains on one macOS arm64 host with DuckDB 1.5.4; other OS and
  filesystem behavior remains unverified.

## Acceptance-review challenge to candidate 18b3a56

Two fresh reviewers verified every prior final-review finding as repaired but
returned FAIL for one moderate acceptance blocker; see
`.10x/reviews/2026-08-21-local-telemetry-v2-storage-migration-acceptance-review.md`.
The final `pending_v2` count uses the non-locking read-only scanner, so its
claimed queue-lock snapshot boundary is unsupported under an in-progress v2
publication. Candidate `18b3a56` remains failed evidence pending the narrow
queue-authority correction and fresh review.

Exact-candidate offline sdist/wheel build, no-dependency Python 3.13 install,
required telemetry module inventory, and installed `status`, `flush`, and
`migrate` lifecycle in an isolated empty `HOME` exited 0. Outcomes were
`disabled`, `empty`, and `absent`; no isolated `.buoy` path was created.

## Acceptance-review queue-authority correction

Candidates `0989690`, `80d7562`, `bbc1cbc`, and `18b3a56` remain preserved as
failed history. This narrow correction addresses only the sole blocker in
`.10x/reviews/2026-08-21-local-telemetry-v2-storage-migration-acceptance-review.md`;
it is implementation evidence pending fresh exact-commit review.

### Finding-to-test mapping

- `_finish_successful_migration` now acquires the shared bounded `queue.lock`
  before calling the complete read-only v2 tree scanner and holds it through
  unsafe/unreadable/incomplete validation and ready-plus-claimed capture. Both
  migrated and already-current success paths call this one helper; no duplicate
  unlocked final-success path was found.
- `test_final_pending_v2_snapshot_is_queue_lock_linearized` pauses a real v2
  producer at the last descriptor/name verification before its atomic
  temporary-to-ready rename, while the producer holds `queue.lock`. Candidate
  `2c7e5ed` signals immediately before the migration's real lock call, not after
  observed contention; therefore the current ordering assertion is not yet
  deterministic and is challenged by
  `.10x/reviews/2026-08-21-local-telemetry-v2-storage-migration-post-fix-review.md`.
- `test_final_pending_v2_snapshot_blocks_on_timeout_or_incomplete` retains both
  required failure cases: final bounded lock timeout and final incomplete tree
  scan each return content-free `blocked` with exit 2.
- `test_publication_after_final_snapshot_release_is_outside_fact` publishes
  immediately after the final snapshot context releases `queue.lock`; migrated
  success correctly reports `pending_v2=0`, while the publication remains ready
  for later writer processing.

### Validation observations

- The exact three final-boundary tests on Python 3.11 exited 0: **3 passed, 2
  subtests passed**.
- Focused telemetry suites on Python 3.11 exited 0: **188 passed, 185 subtests
  passed**. The identical Python 3.13 command exited 0 with the same totals.
- `uv run --offline --python 3.13 --with pytest python -m pytest -q
  --ignore=tests/test_dynamic_version.py` exited 0: **1049 passed, 967 subtests
  passed, 57 preexisting lxml warnings**. The independently owned stale
  dynamic-version collector was the sole exclusion.
- The final-boundary tests plus exact-byte privacy and no-network probes exited
  0: **5 passed, 2 subtests passed**.
- `uv lock --check --offline`, py_compile/compileall, focused Ruff `F,E9`,
  `git diff --check`, `python3 scripts/validate_ranking_contract.py`, and the
  production retrieve-file diff check exited 0.

### Limits

- Static review verified the runtime queue-authority blocker closed and found no
  implementation regression, but deterministic acceptance evidence remains
  blocked until the test observes an actual failed nonblocking `flock` attempt
  before producer release.
- The interleaving exercises process/thread queue authority, not hardware power
  loss or non-macOS filesystem behavior.
- Offline exact-candidate sdist/wheel build, no-dependency Python 3.13 install,
  required telemetry module inventory, and installed `status`, `flush`, and
  `migrate` lifecycle in an isolated empty `HOME` exited 0. Outcomes were
  `disabled`, `empty`, and `absent`; no isolated `.buoy` path was created.

## Post-fix deterministic contention evidence

The prior `2c7e5ed` runtime implementation remains statically accepted, but its
pre-context-manager event did not prove actual contention. This additive section
corrects that overclaim without changing runtime source.

`test_final_pending_v2_snapshot_is_queue_lock_linearized` now wraps the real
low-level `fcntl.flock`. Only after the migration thread's actual
`LOCK_EX | LOCK_NB` call raises `BlockingIOError` does the wrapper record
`snapshot_queue_lock_contended` and release the producer; the exception is
re-raised so the real bounded queue-lock loop remains under test. Before release,
the test proves neither migration lock acquisition nor final scan occurred. It
also wraps the real descriptor-relative `os.rename` and proves this exact order:
failed migration flock, producer temporary-to-ready rename, successful migration
lock acquisition, final v2 scan. The migration then returns already-current with
`pending_v2=1`.

### Post-fix validation observations

- A shell loop executed the exact interleaving test in 25 separate Python 3.11
  pytest invocations: **25/25 passed**, with no sleep-based synchronization.
- Focused telemetry suites on Python 3.11 and Python 3.13 each exited 0:
  **188 passed, 185 subtests passed**.
- The filtered Python 3.13 full suite excluding only the separately owned stale
  `tests/test_dynamic_version.py` collector exited 0: **1049 passed, 967
  subtests passed, 57 preexisting lxml warnings**.
- py_compile/compileall, `uv lock --check --offline`, focused Ruff `F,E9`,
  `git diff --check`, and the runtime-source diff check exited 0. Runtime
  telemetry source, retrieve instrumentation, and release-check scope are
  unchanged.

### Post-fix limits

- The test proves process/thread flock ordering on this macOS arm64 host; it is
  not hardware power-loss or cross-filesystem evidence.

## Final exact-commit acceptance

A fresh independent reviewer returned PASS for exact commit
`3119375bc7125331b8b18c6f670815bb2c560c03`, tree
`501d6313a3f168a9529209f23666b14dfaf3acb1`. The reviewer verified the real
contention handshake, preserved bounded retry, real rename observation, causal
ordering, fixture lock inventory, context-scoped monkeypatches, and the
continued applicability of prior runtime acceptance. No blocker or other
finding remains. Review:
`.10x/reviews/2026-08-21-local-telemetry-v2-storage-migration-final-acceptance-review.md`.

The parent independently ran the exact repaired interleaving test under Python
3.13 with bytecode/cache writes disabled: **1 passed in 1.28 seconds**. Git
identity/status inspection confirmed the exact commit/tree, clean worktree, and
no runtime-source change since accepted candidate `2c7e5ed`.

One initial parent verification command omitted the intended temporary-worktree
`cd`; `uv` consequently recreated the ignored `.venv` in the clean `develop`
checkout and then failed to find the test. No tracked file, branch, remote,
credential, provider, network service, or real telemetry home changed. The
environment is derived and functional at Python 3.13, so no compensating
mutation was attempted. The test was rerun from the required worktree and
passed. This operational error contributes no acceptance evidence.

Residual limits remain one macOS arm64 host, DuckDB 1.5.4, deterministic crash
injection rather than hardware power loss, and no claim for unrelated
filesystem implementations.
