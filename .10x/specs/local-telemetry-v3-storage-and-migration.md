Status: active
Created: 2026-08-28
Updated: 2026-08-28
Decision: .10x/decisions/buoy-records-worker-and-provider-attempt-retrieval-telemetry-v3.md
Inference: .10x/specs/retrieve-inference-telemetry-v3.md
Provider: .10x/specs/retrieve-provider-invocation-telemetry-v3.md
Amends: .10x/specs/local-telemetry-v2-storage-and-migration.md

# Local Telemetry V3 Storage and Migration

## Purpose and scope

This specification adds canonical observation envelope v3, inbox v3, exact DuckDB schema v3, versioned analytical views, and explicit schema-v2-to-v3 migration while preserving the complete v1/v2 queue, writer, security, durability, privacy, backup, and view contracts.

## Canonical paths

V1 and v2 paths remain unchanged. V3 adds only:

```text
~/.buoy/telemetry/
  inbox-v3/
  telemetry-v2-backup.duckdb
  database-migrate-v3/
    telemetry.duckdb
    telemetry-v2-backup.duckdb
```

All path ownership, mode, no-follow, descriptor-relative, link-count, size, fsync, replacement, fixed-name, scratch recovery, and no-payload-selected-path rules from v2 apply. The existing `telemetry-v1-backup.duckdb` remains immutable and, when present, must be exact schema v1 whose complete validated trace graphs are an exact subset of the canonical store's later append-only retained v1 history. V1 traces appended after v1-backup publication are permitted and do not rewrite the backup. V3 migration never replaces or deletes it.

## Envelope v3

`trace-envelope/v3` uses canonical JSON and the v2 bounds unless tightened below. Top-level keys are exactly:

```text
envelope_schema_version       integer exactly 3
observation_schema_version    integer exactly 3
command                       command summary object
retrieval_operation           null or retrieval-operation summary object
provider_accounting           provider-accounting object
spans                         governed span array
events                        governed event array
```

The envelope remains at most 65,536 bytes, contains 1..256 spans and 0..1 widening event, and never carries raw OpenTelemetry resource/scope/link/context data. Command and retrieval-operation summaries retain v2 fields and constraints, except observation version is 3 and command adds exact `inference_policy`.

The graph and attributes follow `.10x/specs/retrieve-inference-telemetry-v3.md`. Provider accounting follows `.10x/specs/retrieve-provider-invocation-telemetry-v3.md`. Producer and writer independently canonical-decode and validate exact keys, types, enums, counts, graph, timestamps, summary/span agreement, inference relationships, provider source order, and prohibited-data bounds.

V3 queue names use distinct `v3-<32 lowercase hex>.json`; terminal receipts use `r3-<32 lowercase hex>.json`. V1/v2 names and inboxes remain exact. A writer never reinterprets one version as another.

## DuckDB schema v3

### Retained objects

Schema v3 retains byte-semantic v1/v2 tables, constraints, metadata identities, and analytical views. Existing v1/v2 rows remain value-equivalent. New v3 commands are not inserted into v1 `trace_runs` or v2 `retrieve_command_runs`/`retrieval_operations`, so old views cannot acquire v3 rows.

The shared `spans` and `span_events` tables continue to hold all versions after version-specific validation. Trace IDs remain globally unique.

### V3 command and operation tables

`retrieve_command_runs_v3` has v2 command columns in the same order plus final required column:

```text
inference_policy VARCHAR NOT NULL
```

Every row requires observation schema version 3 and a valid policy enum.

`retrieval_operations_v3` has the exact v2 retrieval-operation columns and constraints, with observation schema version exactly 3.

### Inference table

`retrieve_inference_requests_v3` columns are exactly:

```text
trace_id             VARCHAR NOT NULL
span_id              VARCHAR PRIMARY KEY
parent_span_id       VARCHAR NOT NULL
started_at           TIMESTAMP NOT NULL
ended_at             TIMESTAMP NOT NULL
duration_ms          DOUBLE NOT NULL CHECK >= 0
operation            VARCHAR NOT NULL
backend              VARCHAR NOT NULL
role                 VARCHAR NOT NULL
item_count            INTEGER NOT NULL CHECK 1..108
worker_state         VARCHAR NULL
outcome              VARCHAR NOT NULL
error_type           VARCHAR NULL
```

Rows must match the corresponding validated generic span exactly. Encode rows require item count <=16. Backend/state, outcome/error, parent, operation, and role combinations must satisfy the inference specification.

### Provider tables

`retrieve_provider_accounting_v3`:

```text
trace_id             VARCHAR PRIMARY KEY
status               VARCHAR NOT NULL
unit                 VARCHAR NOT NULL
```

`retrieve_provider_content_operations_v3`:

```text
trace_id             VARCHAR NOT NULL
route_rank           INTEGER NOT NULL CHECK 1..3
outcome              VARCHAR NOT NULL
invocation_count     INTEGER NOT NULL CHECK 0..6
PRIMARY KEY (trace_id, route_rank)
```

`retrieve_provider_content_invocations_v3`:

```text
trace_id             VARCHAR NOT NULL
route_rank           INTEGER NOT NULL CHECK 1..3
attempt_index        INTEGER NOT NULL CHECK 1..6
request_form         VARCHAR NOT NULL
trigger              VARCHAR NOT NULL
outcome              VARCHAR NOT NULL
error_category       VARCHAR NULL
PRIMARY KEY (trace_id, route_rank, attempt_index)
```

`retrieve_provider_catalog_v3`:

```text
trace_id                         VARCHAR PRIMARY KEY
outcome                          VARCHAR NULL
invocation_count                 INTEGER NOT NULL CHECK 0..40002
namespace_list_page_success      INTEGER NOT NULL CHECK >= 0
namespace_list_page_error        INTEGER NOT NULL CHECK >= 0
namespace_list_page_interrupted  INTEGER NOT NULL CHECK >= 0
metadata_success                 INTEGER NOT NULL CHECK >= 0
metadata_error                   INTEGER NOT NULL CHECK >= 0
metadata_interrupted             INTEGER NOT NULL CHECK >= 0
card_query_page_success          INTEGER NOT NULL CHECK >= 0
card_query_page_error            INTEGER NOT NULL CHECK >= 0
card_query_page_interrupted      INTEGER NOT NULL CHECK >= 0
```

Cross-row cardinality, contiguous ordering, source order, unavailable/complete behavior, and aggregate equality are enforced by writer validation and transaction assembly; database checks are defense in depth, not authority. A complete receipt whose catalog read was not begun inserts the required catalog row with `outcome=NULL` and every catalog counter plus `invocation_count` exactly zero. The stable `catalog_outcome` remains null; storage MUST NOT invent a `not_started` enum or omit the row.

### Stable views

Schema v3 preserves existing view names and SQL identities and adds:

- `retrieval_command_runs_v3`: v2 command/operation columns plus `inference_policy` and the eight aggregate inference request counts defined by the inference spec;
- `retrieval_stage_latency_v3`: v2 stage columns for v3 commands, including inference spans;
- `retrieval_inference_requests_v3`: command mode/outcome joined to every normalized inference row;
- `retrieval_provider_summary_v3`: exact summary columns in the provider spec; and
- `retrieval_provider_content_invocations_v3`: command identity plus route-rank-only attempt detail.

View SQL and ordered layouts have canonical SHA-256 identities in metadata. The metadata table is additively extended only with the five v3 view hashes. Exact object inventory rejects unknown or modified tables, views, schemas, constraints, indexes, macros/functions, sequences, external references, attached databases, comments/tags, or unsafe scratch/WAL state under the established rules.

Every v3 command inserts command, optional operation, provider accounting, normalized inference/provider rows, complete spans, and events in one transaction. Readers never observe a partial command.

## Writer behavior

A v3 writer scans all three versioned inboxes under independent validators and one shared bounded accounting policy.

- V1 work may drain into schema v1/v2/v3 as previously permitted.
- V2 work may drain into schema v2/v3.
- V3 work drains only into schema v3.
- A fresh absent store initializes directly at v3.
- Schema v1/v2 is never auto-migrated; unsupported newer work remains pending and status reports upgrade required.
- Replays/conflicts remain globally content-identified across versions.

Status and flush add exact v3 ready/claimed counts and recognize store schema 3. Status remains database-nonopening and noncreating. Flush preserves snapshot semantics and leaves unsupported-version work pending rather than rejecting it.

## Explicit migration

The existing command remains:

```text
buoy telemetry migrate [--json]
```

It chooses the sole next supported upgrade based on the exact canonical store: v1 to v2 under the active v2 contract, or v2 to v3 under this contract. Exact v3 returns `already_current`; absent remains noncreating. Output keeps existing fields, reporting source 2 and target 3 for this migration and adding no new path or stored values.

V2-to-v3 migration repeats the hardened v1-to-v2 sequence with these substitutions:

1. validate exact closed schema v2 and stream every retained v1 and v2 trace through its canonical validator;
2. drain the bounded compatible v1/v2 snapshot before source freeze;
3. create and exact-validate private v3 store and v2-backup scratch candidates;
4. prove the backup candidate is byte-for-byte equal to the final validated v2 source;
5. transactionally add only v3 metadata/tables/views/constraints to the v3 candidate;
6. prove retained v1/v2 ordered content identities and view results are unchanged;
7. atomically publish fixed `telemetry-v2-backup.duckdb`, then the canonical v3 store, with directory durability; and
8. publish exact schema-v3 writer state while lifetime authority remains held.

Crash/retry, preexisting-backup, late-publication, stale-scratch, state-publication, queue-snapshot, backup/coexisting-history, memory-bound, and no-rollback rules are identical to v2 migration. A preexisting v2 backup must be safe and byte-identical to the exact source or migration blocks. When retry proves that final v2-backup publication already froze the exact still-canonical v2 source, retry completes v3 publication before draining any v1/v2 envelopes published later; that later work remains queued for the schema-v3 writer. Neither backup is automatically deleted, migrated, compacted, or used as writer target.

## Privacy and no-network behavior

All v1/v2 prohibited-data and no-network rules apply to v3 envelope, queue, receipts, state, store, migration scratch/backup, outputs, and diagnostics. Telemetry status/flush/migrate/writer/producer MUST perform zero provider/model/catalog/retrieval/network operations. Migration never opens credentials or loads model/provider code.

## Acceptance scenarios

1. Fresh enabled retrieval creates exact schema v3 and one complete v3 trace; disabled behavior remains zero side effect.
2. Exact schema v2 reports upgrade required with v3 work pending; explicit migrate preserves all v1/v2 rows and view results and creates one exact immutable v2 backup.
3. Exact schema v3 drains v1/v2/v3 queues and preserves global replay/conflict behavior.
4. Old writers cannot see/reject v3 work; new writers never reinterpret versioned filenames.
5. Every v3 trace commits command, operation, inference, provider, spans, and events atomically.
6. Unavailable provider accounting creates only its status row; complete zero accounting creates valid zero-family rows.
7. View fixtures prove exact null/count semantics for preview, pre-pipeline failure, live success/failure, worker/in-process/fallback, catalog-only, content-only, and automatic combined cases.
8. Schema inventory, forged metadata/view, path replacement, symlink/hardlink/FIFO, hostile backup/scratch, WAL, crash-table, replay/conflict, and bounded streaming tests fail closed without data loss.
9. Exact-byte privacy sentinels are absent from every v3 artifact and migration output.
10. Status/migrate/flush are non-networking; dual-runtime full suites, distribution build, and isolated-wheel lifecycle pass.

## Explicit exclusions

Automatic migration, rollback/downgrade, backup deletion, retention/purge, compaction, raw export, OTLP/Collector/network transport, UI/dashboard, user-selected paths, v1/v2 view changes, query/corpus/result identity, provider writes, release, and publication are excluded.
