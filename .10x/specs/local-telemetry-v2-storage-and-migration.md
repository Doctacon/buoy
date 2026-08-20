Status: active
Created: 2026-08-20
Updated: 2026-08-20
Decision: .10x/decisions/buoy-records-command-and-pipeline-retrieve-latency.md
Trace: .10x/specs/retrieve-command-telemetry.md
Amends: .10x/specs/local-telemetry-writer.md

# Local Telemetry Version 2 Storage and Migration

## Purpose and scope

This specification adds a private version-2 command-trace transport, exact
DuckDB schema version 2, and an explicit version-1-to-version-2 migration while
retaining the active local writer's security, queue durability,
failure-isolation, status/flush, and no-network architecture.

It governs:

- canonical version-2 envelopes;
- a separate private version-2 inbox;
- one writer that understands version-1 and version-2 work;
- an additive DuckDB schema with immutable version-1 analytical views;
- read-only upgrade-required status;
- bounded explicit migration with a retained backup; and
- replay, crash, path, permission, and compatibility behavior across upgrade.

All exact version-1 envelope, queue, receipt, producer-accounting, writer
lifetime, path-safety, DuckDB hardening, and analytical-view requirements in
`.10x/specs/local-telemetry-writer.md` remain active unless this specification
explicitly replaces them for version 2.

## Canonical paths

Version-1 paths remain unchanged. Version 2 adds:

```text
~/.buoy/telemetry/
  inbox-v1/                         existing version-1 queue
  inbox-v2/                         version-2 queue
  telemetry.duckdb                 canonical store, schema v1 or v2
  telemetry-v1-backup.duckdb       retained migration backup when migrated
  database-migrate-v2/             private bounded migration scratch
    telemetry.duckdb               version-2 candidate
    telemetry-v1-backup.duckdb     version-1 backup candidate
```

The backup and scratch names are fixed. Payloads never select a path. Every
new directory/file obeys the existing real-UID, no-follow, descriptor-relative,
private-mode, link-count, regular-file, bounded-size, fsync, and replacement
rules. The telemetry root and inbox directories are mode `0700`; files are mode
`0600` where POSIX modes are available.

An old writer sees only `inbox-v1` and therefore cannot claim or reject a
version-2 envelope. A new writer scans both inboxes under their independent
versioned validators and one shared capacity/accounting policy.

## Version-2 envelope

### Encoding and bounds

`trace-envelope/v2` uses the same canonical JSON encoding, duplicate-key,
UTF-8, finite-number, timestamp, ID, size, span/event-count, string-length, and
graph bounds as version 1 unless a tighter bound is stated here.

Top-level keys are exactly:

```text
envelope_schema_version       integer exactly 2
observation_schema_version    integer exactly 2
command                       command summary object
retrieval_operation           null or retrieval-operation summary object
spans                         array of governed version-2 spans
events                        array of governed version-2 events
```

Unknown or missing keys are invalid. The envelope is at most 65,536 bytes, has
one command, zero or one retrieval operation, 1 through 256 spans, and zero or
one widening event. It contains no raw OpenTelemetry resource/scope/span,
baggage, link, exception event, arbitrary JSON extension, or payload-selected
path.

The producer encodes only after converting completed private spans through the
version-2 trace allowlist. The writer treats every envelope as untrusted and
independently canonical-decodes and validates the complete value and graph
before opening DuckDB. A successful live command MUST have one pipeline; the
pipeline retrieval-mode attribute MUST equal the command retrieval mode. A
widened operation MUST have one governed non-null fallback reason and matching
event.

### Command summary

The command object keys are exactly:

| Key | Type and constraint |
| --- | --- |
| `trace_id` | 32 lowercase hex, nonzero |
| `root_span_id` | 16 lowercase hex, nonzero |
| `started_at_unix_us` | governed timestamp |
| `ended_at_unix_us` | governed timestamp not before start |
| `command_duration_ms` | finite nonnegative number matching timestamps |
| `execution_mode` | `live` or `preview` |
| `retrieval_mode` | `explicit_single`, `explicit_multi`, or `automatic` |
| `outcome` | `success` or `error` |
| `exit_code` | integer 0 through 255 |
| `error_type` | null or governed command error category |
| `pipeline_present` | boolean |
| `buoy_version` | existing bounded version pattern |
| `observation_schema_version` | integer exactly 2 |

Outcome, exit code, status, and error type must agree: success requires exit 0,
no error type, and root status `OK`; error requires nonzero exit or an escaping
exception, a governed error type, and root status `ERROR`.

### Retrieval-operation summary

When present, the object keys are exactly the version-1 run's retrieval fields
with `root_span_id` replaced by `span_id`, duration named
`pipeline_duration_ms`, and timestamps named as pipeline timestamps:

- trace ID and pipeline span ID;
- pipeline start/end and duration;
- retrieval outcome;
- hit, namespace, initial/final fanout, and failure counts;
- incomplete, widened, fallback reason, and evidence status;
- bounded embedding model and precision labels;
- top-k and candidates;
- Buoy version; and
- observation schema version exactly 2.

It must match the single `buoy.retrieve.pipeline` span byte-semantically and by
timestamps/duration. It is required exactly when `pipeline_present` is true
and prohibited otherwise. Preview commands must not contain it.

### Span/event graph

The command root is the only parentless span and matches the command summary.
The optional pipeline span is a descendant of the root and matches the
retrieval-operation summary. Existing retrieval child spans descend from the
pipeline. The widening event, when present, belongs to the pipeline. All other
version-2 child names and relationships follow
`.10x/specs/retrieve-command-telemetry.md`.

Every span/event timestamp is within the root interval. Parent intervals
contain descendants except that concurrent siblings may overlap. Command and
pipeline duration values match rounded timestamp deltas under the same
version-1 microsecond/millisecond tolerance.

### Filenames and receipts

Version-2 ready/claimed envelope names use a distinct fixed `v2-` filename
contract with 128 bits of producer randomness and `.json` suffix. Version-2
terminal receipts use a distinct fixed `r2-` contract and record the same
content-free digest/byte-count/kind/reason facts as v1. Version-1 and version-2
names can never collide.

Receipt reasons retain the version-1 bounded set and add only
`unsupported_envelope_version` where applicable. Unknown-version work is never
moved into another version's queue or reinterpreted.

## DuckDB schema version 2

### Retained objects

Schema version 2 retains the exact version-1 columns, constraints, and SQL of:

- `trace_runs`;
- `spans`;
- `span_events`;
- `retrieval_runs_v1`; and
- `retrieval_stage_latency_v1`.

Existing version-1 rows remain value-equivalent and visible through the exact
same version-1 views. Version-2 rows are not inserted into `trace_runs`; the
old table remains a version-1 retrieval-run authority.

The `spans` and `span_events` tables store both validated versions. Their
existing physical columns and constraints are sufficient; schema-version-
specific graph validation occurs before insertion. Trace IDs remain globally
unique across command and legacy traces. A conflicting trace ID is never
partially inserted or overwritten.

### Command table

Schema version 2 adds `retrieve_command_runs` with exact columns:

```text
trace_id                    VARCHAR primary key
root_span_id                VARCHAR not null
started_at                  TIMESTAMP not null
ended_at                    TIMESTAMP not null
command_duration_ms         DOUBLE not null, nonnegative
execution_mode              VARCHAR not null
retrieval_mode              VARCHAR not null
outcome                     VARCHAR not null
exit_code                   INTEGER not null, 0..255
error_type                  VARCHAR nullable
pipeline_present            BOOLEAN not null
buoy_version                VARCHAR not null
observation_schema_version  INTEGER not null
```

### Retrieval-operation table

Schema version 2 adds `retrieval_operations` with exact columns:

```text
trace_id                    VARCHAR primary key
span_id                     VARCHAR not null
started_at                  TIMESTAMP not null
ended_at                    TIMESTAMP not null
pipeline_duration_ms        DOUBLE not null, nonnegative
outcome                     VARCHAR not null
hit_count                   INTEGER not null, nonnegative
namespace_count             INTEGER not null, nonnegative
initial_fanout              INTEGER not null, nonnegative
final_fanout                INTEGER not null, nonnegative
failure_count               INTEGER not null, nonnegative
incomplete                  BOOLEAN not null
widened                     BOOLEAN not null
fallback_reason             VARCHAR nullable
evidence_status             VARCHAR nullable
embedding_model             VARCHAR not null
embedding_precision         VARCHAR not null
top_k                       INTEGER not null, nonnegative
candidates                  INTEGER not null, nonnegative
buoy_version                VARCHAR not null
observation_schema_version  INTEGER not null
```

`retrieval_operations.trace_id` must match one command row with
`pipeline_present=true`; absence must match false. The writer enforces this in
one transaction rather than relying on deferred cross-table repair.

### Version-2 views

`retrieval_command_runs_v2` has exact columns, in order:

```text
trace_id
root_span_id
started_at
ended_at
command_duration_ms
execution_mode
retrieval_mode
command_outcome
exit_code
command_error_type
pipeline_span_id
pipeline_started_at
pipeline_ended_at
pipeline_duration_ms
retrieval_outcome
hit_count
namespace_count
initial_fanout
final_fanout
failure_count
incomplete
widened
fallback_reason
evidence_status
embedding_model
embedding_precision
top_k
candidates
buoy_version
observation_schema_version
```

It selects version-2 command rows and left joins the optional operation by
trace ID. Pipeline-derived columns are null when no operation exists.

`retrieval_stage_latency_v2` has exact columns, in order:

```text
trace_id
command_started_at
execution_mode
retrieval_mode
command_outcome
span_id
parent_span_id
stage
started_at
ended_at
duration_ms
status_code
attributes
```

It joins version-2 command rows to every non-root span for that trace. View SQL,
ordered types/nullability, and SHA-256 identities are canonical schema
metadata, validated without binding untrusted persisted views.

### Metadata and object inventory

Schema version 2 appends `command_runs_view_sha256` and
`command_stage_view_sha256` after the retained `runs_view_sha256` and
`stage_view_sha256` columns in `telemetry_metadata`. It has one exact metadata
row identifying schema version 2, creation/migration timestamp, and canonical
SHA-256 values for all four versioned views. The declared primary-key and
`CHECK` constraints are the complete index/constraint contract; schema version
2 adds no secondary indexes. The code owns an exact database-wide table/view/
schema/object inventory for both schema versions. Unknown user schemas or
objects in any schema, functions/macros, sequences, non-internal custom types,
altered defaults/comments/tags, altered views, columns, constraints, metadata,
external references, attached databases, unsafe WAL/scratch, or shadowed
catalog functions make the store incompatible or unsafe under existing rules.
Internal DuckDB catalog objects are excluded only by fixed engine-owned
identity, never merely because an object is outside `main` or because the store
is schema version 1.

Every version-2 command trace inserts its command row, optional retrieval
operation, complete span graph, and event in one DuckDB transaction. Readers
never observe a partial command trace.

## Writer behavior across versions

A version-2-capable writer:

1. independently scans and validates both private inboxes;
2. may drain v1 work into an exact schema-v1 or schema-v2 store;
3. drains v2 work only into an exact schema-v2 store;
4. leaves valid v2 work pending when the canonical store is exact schema v1;
5. reports `upgrade_required` rather than rejecting, moving, or deleting that
   work;
6. keeps replay/conflict identity global across both versions; and
7. retains the established bounded retries, deadlines, lifetime election,
   receipts, crash recovery, accounting, and no-network child boundary.

Pending, temporary, and receipt entry/byte limits are shared across both inbox
versions. Receipt rotation examines both versioned receipt directories while
the shared queue lock is held, and the combined terminal receipt identity set
MUST remain within the single writer-state bound of 4,096 names.

On an absent canonical store, the new writer initializes schema version 2 even
when the first accepted envelope is v1. This avoids creating a store that
immediately requires migration. A v1 envelope is inserted only into the
retained v1 tables/views; a v2 envelope is inserted only into the v2 command/
operation tables and shared span/event tables.

A v2-capable writer encountering schema v1 may continue draining valid v1
work. It MUST NOT automatically migrate. Once no claim is in flight, it leaves
v2 work recoverable, writes bounded `upgrade_required` state, and exits or
idles under existing bounds. Before any append, the writer validates the fixed
migration-scratch and backup entries: the exact safe retained backup may
coexist, while any hostile/unrecognized backup or any unresolved migration
scratch blocks mutation until explicit migration recovery proves it safe.
When a backup exists beside schema v2, append and reconciliation MUST stream-
validate the backup's complete v1 semantics/privacy and prove its v1 content
identity equals the canonical v2 store's retained v1 history before mutation.
Existing schema-v1 and schema-v2 rows are likewise semantically/privacy
validated before an existing store is treated as compatible or mutated.

## Read-only status and flush

`buoy telemetry status` remains read-only and opens no DuckDB connection. It
recognizes exact schema version from verified writer metadata and fixed-file
facts.

When an exact v1 store coexists with a v2-capable installation or pending v2
work, status reports:

- store state `upgrade_required`;
- schema version 1;
- separate content-free v1/v2 ready and claimed counts;
- total bounded pending bytes;
- effective enablement unchanged; and
- overall `blocked` only when v2 work is pending, otherwise `degraded` to make
  the required one-time action visible.

Status JSON increments its own output schema version and preserves all old
facts under stable keys. It adds the flat keys `queue.v1_ready`,
`queue.v1_claimed`, `queue.v2_ready`, and `queue.v2_claimed`, plus top-level
`migration_backup_present`. Text renders the same facts without paths beyond
the existing canonical display path. It never reads envelope contents.

`buoy telemetry flush` may drain v1 work against schema v1. If its invocation
snapshot contains v2 work while the store is v1, that work remains pending and
the flush outcome is `blocked` with no rejection. Against schema v2, flush
handles both versions under the existing exact-snapshot terminal rule. Work
published after the invocation snapshot MUST NOT change that snapshot's
terminal outcome, including by changing aggregate status to upgrade-required;
only unsafe/incompatible state that prevents proving a snapshotted item's
terminal condition may block it.

## Explicit migration command

### Interface

The sole new management command is:

```text
buoy telemetry migrate [--json]
```

It accepts no source/destination/path/version/repair/force/delete option. It
uses only the canonical private telemetry home. It performs no provider,
model, retrieval, catalog, credential, network, external extension, database
repair, retention, or deletion operation.

Migrate JSON keys are exactly `schema_version`, `database_path`,
`source_schema_version`, `target_schema_version`, `outcome`,
`migrated_v1_runs`, `migrated_v1_spans`, `migrated_v1_events`, `pending_v2`,
`backup_present`, and `elapsed_ms`. Text renders the same facts. Output contains
no trace IDs, envelope names/digests, raw errors, paths beyond the canonical
display path, or stored values.

Outcomes are exactly `absent`, `already_current`, `migrated`, `busy`, or
`blocked`. `absent`, `already_current`, and `migrated` exit 0; `busy` exits 1;
`blocked` exits 2.

### Preconditions and authority

Migration first proves POSIX capability and acquires the same writer lifetime
authority with a bounded nonblocking attempt. A live writer produces `busy`;
the command never signals or kills it. The command validates telemetry root,
v1/v2 inboxes, canonical store metadata, backup, and scratch paths before any
DuckDB import/connection. A hostile, unreadable, or incomplete bounded inbox
scan therefore blocks without importing the store module or opening the
database.

- No canonical database and no auxiliary store artifacts returns `absent`
  without creating any path. A missing canonical database with a backup, WAL,
  initialization scratch, or migration scratch is unprovable and returns
  `blocked`; `backup_present` still reports the exact safe backup fact.
- Exact schema v2 returns `already_current` without creating a backup.
- Unsafe, unreadable, incompatible, unknown-version, or unprovable state
  returns `blocked` without changing canonical data.
- Exact schema v1 proceeds.

The migration owns writer lifetime until canonical publication and final state
are durable. Producers may continue atomically publishing independent v2
envelopes; migration never snapshots or deletes them. Before copying the v1
store, migration drains already-published valid v1 work under existing writer
rules so the backup and migrated store contain every v1 envelope accepted
before migration's bounded v1 snapshot. New v1 publications after that
snapshot remain queue-recoverable for the v2 writer. If retry finds a final
exact backup already published beside the matching exact canonical v1 source,
it MUST NOT drain later v1 queue work first: it completes publication of v2
from that proven source/backup, then leaves the later v1 work recoverable for
schema-v2 draining. This prevents a crash between backup and canonical
publication from wedging migration or rewriting retained history.

### Backup and atomic upgrade

Migration performs these ordered phases:

1. validate the exact closed schema-v1 store, then stream every stored v1 trace
   through the canonical v1 semantic/graph/privacy validator before recording
   content-free row/span/event counts;
2. safely drain the bounded v1 snapshot or return blocked without migration;
3. revalidate the exact store, semantics, and counts;
4. create private fixed scratch candidates for the v2 database and v1 backup
   without following links;
5. copy, fsync, hash, and exact-v1-validate the complete backup candidate before
   any final backup name is created;
6. open only the v2 scratch candidate with DuckDB's existing hardened
   configuration;
7. transactionally add schema-v2 metadata, tables, views, and the declared
   primary-key/`CHECK` constraints without changing v1 rows or v1 view
   definitions;
8. validate the complete v2 scratch as exact schema v2 and prove v1 counts and
   streamed ordered values/digests match the source;
9. atomically publish the fully validated backup candidate at
   `telemetry-v1-backup.duckdb`, never streaming bytes directly into the final
   backup name;
10. atomically publish the validated v2 scratch at the canonical database path
    while lifetime authority is held; and
11. fsync the containing directory and publish exact schema-v2 writer state.

The backup is never modified, migrated, automatically removed, compacted, or
used as a writer target. If it already exists, migration proceeds only if it
is a safe regular private file and byte-for-byte identical to the exact final
v1 source; otherwise it blocks. A partial backup candidate remains scratch and
is safely recoverable; it can never poison the fixed final backup name. This
makes retry idempotent without overwriting history. Once schema v2 is
canonical, the backup's streamed v1 content identity MUST equal the canonical
store's retained v1 content identity; internal validity alone is insufficient.

Before canonical publication, any failure leaves the original canonical v1
file authoritative. Safe incomplete scratch is removed only after proving its
fixed identity; unsafe/unprovable scratch blocks. After canonical publication,
the exact v2 validator and DuckDB crash/WAL rules determine database success;
the v1 backup remains available for manual recovery, but migration never
performs an automatic rollback. An already-current retry MUST validate and
remove only a recognized safe stale migration scratch left after canonical
publication, reconcile writer state, and then return `already_current`.

Failure to publish final writer state never escapes as a raw exception. If the
canonical v2 store and backup are durable but state publication cannot be
proven, the command returns exact `blocked` facts; a later already-current retry
may reconcile state and succeed.

The migration does not automatically drain pending v2 envelopes after success.
It reports their count; the next producer-started writer or explicit flush
drains them.

## Privacy, limits, and no deletion

The version-1 and version-2 prohibited-data contracts apply to migration
scratch, backup, output, state, diagnostics, and exceptions. Raw DuckDB errors
are never printed or persisted in command state. The backup contains only the
already-governed local v1 database.

There is no automatic backup retention or purge. Documentation tells the owner
what the backup is and that Buoy never deletes it. Adding a safe deletion
command or policy requires separate authorization.

Migration memory is bounded independently of store size: trace IDs and ordered
row/value comparisons are consumed in batches of at most 128, no complete
store/table/view result is retained in Python, every scalar/JSON length is
preflight-bounded before value materialization, and each trace is independently
validated. Runtime and I/O are finite and proportional to the explicitly
selected closed local store; there is no artificial elapsed deadline that
could strand a valid large history midway through an explicit migration.

## Acceptance scenarios

1. **Absent home/store:** status and migrate remain non-creating; first v2
   envelope creates exact schema v2 through the writer.
2. **Exact v1 with no pending work:** status reports upgrade required; migrate
   creates one exact private backup, atomically publishes schema v2, preserves
   every v1 row/span/event and exact v1 view result, and returns migrated.
3. **V1 backlog:** migrate drains its bounded v1 snapshot before backup and
   proves those traces exist in both backup and migrated store.
4. **V2 backlog before migration:** old writer cannot see/reject v2; new writer
   leaves it pending against v1; migration preserves it; later flush commits it
   exactly once against v2.
5. **Already current:** repeated migrate is a read-only successful no-op and
   neither changes nor duplicates the backup.
6. **Hostile backup/scratch/store:** symlink, hardlink mismatch, FIFO, wrong
   owner/mode, path replacement, unsafe WAL, unknown object, altered view,
   forged metadata, or mismatching preexisting backup blocks without changing
   canonical v1 or deleting pending work.
7. **Crash table:** no-cleanup faults before/after scratch creation, transaction
   commit, backup creation/fsync, canonical publication, directory fsync, and
   state publication leave one provable canonical version and preserve the
   backup/queue recovery contract. A fault after backup publication followed by
   new v1 publication retries to v2 without draining or losing that later work;
   subsequent flush commits it exactly once.
8. **Replay/conflict:** v1 and v2 exact replays acknowledge; same-version or
   cross-version conflicting trace IDs never overwrite or partially insert.
9. **View compatibility:** old v1 SQL returns exactly the pre-migration rows and
   meanings; v2 live/preview/error fixtures return exact command/pipeline null
   semantics through the new views.
10. **Privacy:** exact-byte sentinels are absent from v2 envelope, both queues,
    receipts, state, scratch/backup diagnostics, command output, and all new
    database scalar/JSON values.
11. **No network/provider:** audit hooks prove status, flush, migrate, producer,
    and writer make zero socket/DNS calls and migration imports/calls no
    provider/model/catalog/retrieval code.
12. **Compatibility:** established v1 queue/writer/store adversarial tests,
    command behavior tests, Python 3.11/3.13 full suites, distribution and
    clean-wheel telemetry lifecycle all pass.

## Exclusions

Automatic migration, a user-selected store/backup path, automatic backup
deletion, downgrade/rollback command, retention/purge, database compaction,
raw export, secondary store, Collector/OTLP/network transport, external
extension, query/content additions, plan/apply telemetry, provider/model work,
installed-tool replacement, release, publication, and main-branch mutation are
excluded.
