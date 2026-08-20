Status: recorded
Created: 2026-08-20
Updated: 2026-08-20
Target: 09896908f654b2993cf05e67d53cef94c00cbd9d
Verdict: fail
Ticket: .10x/tickets/2026-08-20-implement-local-telemetry-v2-storage-migration.md
Evidence: .10x/evidence/2026-08-20-local-telemetry-v2-storage-migration.md
Specifications: .10x/specs/local-telemetry-v2-storage-and-migration.md, .10x/specs/local-telemetry-writer.md

# Local Telemetry V2 Storage and Migration Review

## Target

Three independent fresh-context reviewers and the parent inspected exact
implementation commit `09896908f654b2993cf05e67d53cef94c00cbd9d`, tree
`282503bf7dd0a1942b40ad76fc0d47cde714d7f6`, against governing base
`d11644854dcaa1af2b9afc221324b5977d07ebf5` and the complete active storage,
trace, privacy, and version-1 compatibility contracts.

The review was source/test/evidence inspection. Reviewers did not edit files or
independently execute tests. Their three reports agreed that v1 compatibility,
private descriptor-relative queue mechanics, DuckDB external-access controls,
child-process isolation, and the new CLI surface are directionally sound, but
all three returned fail because the migration crash/retry contract is not met.

## Findings

### Critical: interrupted backup creation poisons retry

Migration copies directly into final
`telemetry-v1-backup.duckdb`. A write/fsync/process failure can leave a partial
safe-looking canonical backup. Retry treats its size/hash mismatch as
incompatible and permanently blocks without manual deletion. Backup bytes must
be completed, fsynced, validated, and only then atomically published from a
private scratch identity. Tests must inject failure during the copy itself and
prove safe retry.

### Critical: post-publication interruption leaves unrecoverable scratch

After canonical v2 rename, migration marks the database published before
scratch removal/state publication. Exceptions skip cleanup. Status then reports
`present_unverified`, while migrate sees schema 2 and returns
`already_current` without recovering the safe stale scratch. The
already-current path must validate and remove only exact safe stale migration
scratch and reconcile state; tests must exercise every post-publication phase
through status, retry, append, and flush.

### Significant: migration can preserve semantically invalid/prohibited v1 rows

Exact schema validation authenticates objects and view definitions but does not
validate every stored v1 run/span/event value and graph. Migration copies those
values into backup and v2 even if an edited exact-shape store contains invalid
enums, prohibited JSON, raw content, or broken trace relationships. Migration
must stream every v1 graph through the canonical v1 semantic/privacy validator
before creating backup or publishing v2. Tests must use non-vacuous stored and
raw-error sentinels.

### Significant: migration validation is unbounded in memory

The implementation materializes five complete sorted table/view result sets in
Python and repeats them for source, scratch, backup, and final. Existing
telemetry has no retention cap. Replace whole-store `fetchall()` retention with
fixed-size streaming comparison/digests and bounded per-trace semantic
validation. Duration may remain proportional to the explicitly selected local
store; retries/waits and memory admission remain bounded.

### Significant: exact object inventory ignores non-main schemas

Table, view, function, constraint, and index inventories filter to `main`.
Additional user schemas and their tables/views/macros/functions survive exact
validation and migration. Exact validation must reject every non-internal
user-defined schema object outside the canonical `main` inventory and retain
qualified non-binding catalog inspection.

### Significant: invalid v2 graphs are accepted

A widened v2 retrieval may carry a null fallback reason because the event and
graph validators compare null values rather than requiring the governed enum.
The validator also needs explicit live-success/pipeline consistency and
command/pipeline retrieval-mode agreement. Add a comprehensive v2 negative
matrix for IDs, parents/cycles, ordering/containment, summaries, status/outcome,
pipeline presence/mode, event ownership, widening, and prohibited values.

### Significant: flush is not isolated to its invocation snapshot

Flush snapshots both queues, then consults global status. A v2 envelope
published after a v1-only snapshot can make global status blocked behind schema
v1 and incorrectly block the earlier snapshot. Later publications must not
change the requested snapshot's terminal result; genuine unsafe/incompatible
state still blocks.

### Significant: migration opens DuckDB before inbox validation

The command inspects DuckDB schema before proving both inbox trees safe. The
active precondition requires root/store/inboxes/backup/scratch validation
before DuckDB use. Reorder preflight and add an audit that a hostile inbox
prevents `duckdb.connect`.

### Significant: state publication failure escapes exact command outcomes

The final writer-state write is unguarded after canonical migration. A local
state failure can raise rather than returning one exact migrate outcome. Treat
canonical store/backup publication as authoritative, contain state-write
failure without raw output, and test the resulting status/retry behavior.

### Significant: normal append ignores hostile migration/backup paths

Normal append validates initialization scratch/database/WAL but not the fixed
migration scratch or retained backup. A hostile backup/scratch can coexist with
continued mutation despite the active fail-closed path contract. Validate those
fixed paths before append; allow only the exact safe retained backup and defined
recoverable scratch state.

### Moderate: combined queue capacity status is wrong

Publication enforces shared v1/v2 entry/byte capacity, but status ORs each
queue's independent full flag. Split occupancy can reach the shared limit while
status reports `capacity_full=false`. Compute aggregate entry/byte/temp bounds
and cover exact split boundaries.

### Moderate: migrate text omits JSON facts

JSON includes `schema_version` and `database_path`; text omits them despite the
contract requiring the same facts. Render exact parity without adding keys.

### Moderate: upgrade-required documentation overstates stateless status

Read-only status can identify schema v1 only from matching safe writer-state
metadata; absent/stale state is intentionally `present_unverified` because
status opens no DuckDB. Documentation must state this bound rather than promise
unconditional `upgrade_required`.

### Significant: evidence and tests overclaim coverage

The v2 adversarial envelope test has four mutations, no same/cross-version
replay/conflict tests exist, crash hooks miss mid-copy and recovery, and one
migration privacy assertion never introduces its sentinel. Evidence must be
revised to distinguish the failed first candidate from repaired observations.
Required additions include:

- atomic backup-copy failure and retry;
- post-publication status/retry/append/flush recovery;
- streamed semantic row/privacy validation;
- non-main object rejection;
- v2 graph/value mutation matrix;
- same/cross-version replay/conflict;
- post-snapshot v2 publication during v1 flush;
- split entry/byte capacity;
- hostile inbox before DuckDB open;
- hostile backup/scratch append rejection;
- final state-publication failure;
- exact text/JSON fact parity; and
- absent/stale/mismatched writer-state documentation/tests.

## Separate preexisting test-harness issue

The unmodified suite cannot collect because current develop deleted
`scripts/release_checks.py` while retaining `tests/test_dynamic_version.py`'s
module import. This predates the telemetry branch and does not explain the
findings above. It has a separate durable owner at
`.10x/tickets/2026-08-20-reconcile-missing-release-checks-test-harness.md` and
must not be repaired by widening this telemetry ticket.

## Verdict

FAIL. The exact candidate is not eligible for ticket closure or dependent
instrumentation work. Repair the complete accepted finding set surgically,
update evidence honestly, rerun focused compatibility and available full
validation, and obtain a fresh exact-commit review.

## Residual risk

Even after repair, process-exception crash injection is not a hardware power-
loss test, validation is currently one macOS arm64 host, and canonical DuckDB
view identities remain intentionally version-sensitive. Those disclosed limits
do not excuse the deterministic blockers above.
