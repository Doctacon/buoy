Status: recorded
Created: 2026-08-20
Updated: 2026-08-20
Relates-To: .10x/tickets/2026-08-20-implement-local-telemetry-v2-storage-migration.md, .10x/specs/local-telemetry-v2-storage-and-migration.md

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

This supports every ticket acceptance criterion at focused source/runtime
level and supports repository compatibility outside the preexisting
`test_dynamic_version.py` collection defect. It does not constitute the
required independent review or parent-ticket closure.

## Limits and residual risks

- Python 3.11/3.13 were exercised on one macOS arm64 host, not CI's complete OS
  matrix.
- The complete suite cannot collect until the independently missing
  `scripts/release_checks.py` harness is restored by its owning release scope;
  1016 other tests pass when that one collector is excluded.
- Crash injection is process-exception simulation around each publication
  phase, not power-loss or filesystem-fault hardware testing.
- Exact schema/view hashes are DuckDB-1.5.4 identities and remain intentionally
  version-sensitive.
- Independent exact-commit review and parent closure remain pending, so the
  implementation ticket remains active.
