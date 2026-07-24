Status: recorded
Created: 2026-07-23
Updated: 2026-07-23
Relates-To: .10x/tickets/done/2026-07-23-phase-2a-durable-plan-jobs.md, .10x/specs/phase-2a-plan-job-lifecycle.md, .10x/specs/phase-2a-public-source-planning-service.md

# Phase 2A Durable Plan-Job Validation

## What was observed

The local plan-job store uses a record-first recoverable commit. Each schema-v1 record persists its committed `event_sequence`; after a fsynced temporary record is atomically installed and its directory is fsynced, the matching JSONL event is appended and fsynced. Reads and startup recovery reconcile exactly one missing or partial final event from the authoritative record, while event-ahead, multi-event gaps, malformed complete events, or payload mismatches fail closed. Directory and event/record fsync failures propagate as `JobDurabilityError` rather than being discarded.

Records and events are opened relative to a no-follow jobs-directory descriptor. Reads require private regular files, compare the post-read filename inode to the opened descriptor, reject hard links and symlinks, and bind record payload `job_id` to the requested filename. The implementation fails closed where `O_NOFOLLOW`, directory descriptors, or descriptor-relative operations are unsupported.

`PlanJobService` obtains a portalocker-backed exclusive lock through a safely opened lock-file descriptor before startup reconciliation and holds it through worker shutdown. A second same-process or subprocess service fails closed and cannot interrupt or relabel the live owner's job. The single owned executor remains concurrency one, and active-check/create occurs only under the service owner and in-process start lock.

The artifacts root plus fixed `command-center/plans` descendants and each job directory are created/opened with descriptor-relative mkdir and `O_NOFOLLOW`; existing symlinks/non-directories and final collisions are rejected. Managed planning carries the descriptor-observed device/inode identities for the artifacts root, fixed ancestors, and job directory and revalidates them before and between write phases. Tests cover root, fixed-ancestor, and final symlinks plus a captured-executor replacement boundary and observe no outside writes.

The original transition, sanitization, shared-planning, success-integrity, replay, and failure-preservation behavior remains covered. No API, frontend, live source/provider, applied-state, catalog, turbopuffer, or remote behavior was added.

## Procedure and results

1. `PYTHONPATH=src .venv/bin/python -W error::ResourceWarning -m unittest -q tests.test_command_center_jobs tests.test_planning_service`
   - Result: passed.
   - Output: 30 tests ran in 2.777s; `OK`.
   - Coverage includes 20 subprocess `os._exit` cases across create/progress/terminal/restart and record-temp-fsync, record-replace, record-directory-fsync, event-write, and event-fsync boundaries; reopen reconciliation/listing/interruption; injected directory/event durability errors; lock exclusion; and filesystem tamper cases.
2. `PYTHONPATH=src .venv/bin/python -m unittest -q tests.test_planning_service tests.test_cli tests.test_apply_cli tests.test_crawler tests.test_github_repo tests.test_database_relation tests.test_database_relation_cli tests.test_duckdb_relation tests.test_duckdb_relation_cli tests.test_bigquery_relation tests.test_snowflake_relation tests.test_command_center_jobs`
   - Result: passed.
   - Output: 265 tests ran in 16.636s; `OK`. Two established best-effort cleanup warnings were emitted.
3. `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -q`
   - Result: passed.
   - Output: 692 tests ran in 66.692s; `OK (skipped=12)`. Output contained established negative-path CLI/provider diagnostics, cleanup warnings, and one upstream lxml deprecation warning.
4. `PYTHONPATH=src .venv/bin/python -m compileall -q src tests/test_command_center_jobs.py && git diff --check && test -z "$(git diff --cached --name-only)"`
   - Result: passed with no output; no staged files.

## Acceptance mapping

- Crash-consistent record/event updates and startup reconciliation: sequence-bound record-first implementation plus fault-injection and 20 real subprocess kill/reopen cases.
- Propagated durability failure: injected record-directory and event-fsync errors raise `JobDurabilityError`; reopen repairs the committed record and keeps active work listable/interruptible.
- One live owner and one active worker: simultaneous two-store active-check/create serialization plus same-process and subprocess lifetime-lock regressions; second service never performs recovery and never changes the live owner's state.
- Symlink-safe managed artifact creation and containment: artifacts-root, `command-center`, `plans`, final-job symlink, and replacement tests; outside directories remain empty.
- Record identity and safe reads: mismatched payload/filename, record/event symlink and hard-link, and post-open replacement tests fail closed.
- Compatibility: focused shared planning/job tests, 265-test shared compatibility basket, and 692-test full offline suite.

## Final-review repair addendum

The managed worker now retains the precreated job-directory descriptor from creation through planning completion. `PlanningService` uses a descendant-capable descriptor alias as its physical crawl/write/verification root while artifact documents, summaries, and the returned result use the stable logical final directory. Alias support is tested before any planning write and unsupported platforms fail closed. On this Darwin validation host, `/dev/fd/<n>` cannot address descendants, so the real in-operation rename regression is retained but skipped and the unsupported-alias regression confirms no write occurs; procfs platforms execute the rename/symlink swap and assert the attempted write lands in the descriptor-held moved directory, never the outside target. Git commands preserve a `/dev/fd` descriptor when that supported alias form is used.

Managed-root opening now starts at the filesystem root and opens or creates each configured path component relative to the preceding no-follow directory descriptor. The new regression configures an already-existing `base/link/artifacts` through an intermediate symlink and observes construction fail without creating managed descendants outside.

All public store reads and mutations now acquire the same inter-instance mutation lock exactly once, then call private locked helpers for nested record/event work. The overlapping two-store regression pauses a writer after record installation, starts a reader, and observes the reader wait until the matching event append completes; reopen yields exactly sequences 1, 2, and 3 with no duplicate.

Final commands:

1. `PYTHONPATH=src .venv/bin/python -W error::ResourceWarning -m unittest -q tests.test_command_center_jobs tests.test_planning_service`
   - Result: passed; final rerun 34 tests in 2.696s, `OK (skipped=1)`.
2. `PYTHONPATH=src .venv/bin/python -m unittest -q tests.test_planning_service tests.test_cli tests.test_apply_cli tests.test_crawler tests.test_github_repo tests.test_database_relation tests.test_database_relation_cli tests.test_duckdb_relation tests.test_duckdb_relation_cli tests.test_bigquery_relation tests.test_snowflake_relation tests.test_command_center_jobs`
   - Result: passed; 270 tests in 15.580s, `OK (skipped=1)`, with the two established best-effort cleanup warnings.
3. `PYTHONPATH=src .venv/bin/python -m compileall -q src tests/test_command_center_jobs.py tests/test_planning_service.py tests/test_github_repo.py && git diff --check && test -z "$(git diff --cached --name-only)"`
   - Result: passed with no output; no staged files.

## Portability re-review repair addendum

Managed jobs no longer require procfs or descendant-capable descriptor aliases. Existing website and Git writers operate in a securely created mode-0700 private staging directory while plan and summary documents are constructed with the logical final job path. After the existing complete-artifact verifier passes against staging, only `plan.json`, `manifest.json`, `chunks.jsonl`, `summary.json`, and the ordinary `pages/` tree are copied into the already-held final job descriptor. Destination files use descriptor-relative no-follow/exclusive creation, regular/private-file checks, file and directory fsyncs, and a second full source/destination tree hash comparison. Checkout and other staging-only entries are excluded. On failure, the same bounded copier preserves available ordinary whitelisted artifacts when the final descriptor is still empty; unsafe entries fail preservation closed. The private staging directory is removed, and tests recursively reject staging, `/dev/fd`, and `/proc` path text in persisted artifacts.

Every durable-state reopen now starts at the filesystem anchor, opens every configured state-root component with `O_DIRECTORY | O_NOFOLLOW`, then opens `command-center/jobs` descriptor-relatively. Before any read, reconciliation, lock, or mutation proceeds, the reopened state root, `command-center`, and `jobs` device/inode identities must match those recorded at construction. Replacing an intermediate configured ancestor with a different real directory therefore fails closed before the substitute mutation lock or records can be touched.

Final commands for this repair:

1. `PYTHONPATH=src .venv/bin/python -W error::ResourceWarning -m unittest -q tests.test_planning_service tests.test_command_center_jobs tests.test_github_repo`
   - Result: passed; final rerun of 62 tests in 9.933s, `OK` with no skips.
2. `PYTHONPATH=src .venv/bin/python -W error::ResourceWarning -m unittest -q tests.test_planning_service.PlanningServiceTests.test_private_staged_managed_plan_persists_only_logical_artifact_paths tests.test_command_center_jobs.PlanJobServiceTests.test_offline_managed_website_succeeds_through_private_staging tests.test_command_center_jobs.PlanJobServiceTests.test_offline_managed_github_succeeds_and_excludes_checkout tests.test_command_center_jobs.PlanJobServiceTests.test_in_operation_output_replacement_cannot_redirect_planning_write tests.test_command_center_jobs.PlanJobStoreTests.test_post_construction_state_ancestor_replacement_blocks_reads_and_mutations`
   - Result: passed; final rerun of 5 portability/security regressions in 0.195s, `OK`.
3. `PYTHONPATH=src .venv/bin/python -m unittest -q tests.test_planning_service tests.test_cli tests.test_apply_cli tests.test_crawler tests.test_github_repo tests.test_database_relation tests.test_database_relation_cli tests.test_duckdb_relation tests.test_duckdb_relation_cli tests.test_bigquery_relation tests.test_snowflake_relation tests.test_command_center_jobs`
   - Result: passed; final rerun of 272 tests in 15.584s, `OK`, with two established best-effort cleanup warnings.
4. `PYTHONPATH=src .venv/bin/python -m compileall -q src/buoy_search/planning_service.py src/buoy_search/command_center_jobs.py tests/test_planning_service.py tests/test_command_center_jobs.py && git diff --check`
   - Result: passed with no output.

## Limits

- All source behavior used fakes or existing offline fixtures, including a local Git repository. No live website, GitHub, database, provider, model, turbopuffer, browser, server, socket, commit, push, merge, publish, or PR operation was performed.
- The worker remains deliberately in-process and is not resumed after process death; the next exclusive service owner marks persisted active jobs interrupted.
- Platforms without the required no-follow and descriptor-relative filesystem primitives fail closed for durable jobs. Portalocker supplies the supported inter/process ownership primitive. Procfs and descriptor-descendant aliases are not required.
- FastAPI/SSE transport and frontend behavior remain excluded for later Phase 2A tickets.
- Independent adversarial re-review is still required before this active ticket can close.
