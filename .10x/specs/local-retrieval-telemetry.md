Status: active
Created: 2026-08-18
Updated: 2026-08-18
Decision: .10x/decisions/buoy-records-opt-in-local-retrieval-telemetry.md

# Local Retrieval Telemetry

## Scope and compatibility

This contract adds opt-in operational traces only to live retrieval library
execution. It preserves retrieval ranking, routing, evidence decisions,
provider calls, result objects, CLI output, exception wording, exit codes,
dry-run behavior, applied-state schemas, and remote state.

The exact current `src/buoy_search/cli.py`, `routing.py`, `evidence.py`, and
`routing_quality.py` source receipts MUST remain byte-identical. Consequently,
the first slice begins after route selection for automatic retrieval and does
not claim catalog or selector latency.

## Enablement and location

Telemetry is enabled only when the stripped, case-insensitive value of
`BUOY_TELEMETRY` is `local` and `OTEL_SDK_DISABLED` is not a standard true
value. It is otherwise a zero-side-effect no-op.

Enabled traces are buffered in memory for one retrieval call and then written
to the absolute canonical path:

```text
~/.buoy/telemetry/telemetry.duckdb
```

The canonical home and telemetry directory MUST be real directories rather
than symlinks or other files. Newly created directories are user-private and
new database/lock files are mode `0600` where POSIX modes are available. The
telemetry store is not nested in, attached to, or migrated from any source
applied-state database.

## Trace contract

Every persisted observation uses `buoy.observation.schema_version=1` and one
root `buoy.retrieve` span. The permitted child spans are:

- `buoy.query.embed`;
- `buoy.namespace.query`;
- `buoy.rerank`; and
- `buoy.evidence.assess`.

The permitted root event is `retrieval.widened`. Namespace spans identify a
target only by one-based route rank. The persistence boundary MUST discard any
span, event, or attribute outside the exact governed name/key allowlists even
if future instrumentation accidentally supplies it.

The allowlist may include only operational values in these classes:

- observation and Buoy package version;
- explicit-single, explicit-multi, or automatic mode;
- embedding and reranker model/revision/precision;
- requested top-k/candidate counts;
- route selection reason and finite score/margin;
- initial/final fanout, route rank, and namespace/failure/hit counts;
- widening state and one of `empty_top1`, `failed_top1`, or `weak_top1`;
- rerank candidate/deduplication counts;
- evidence mode/status and finite top/second/gap observations;
- incomplete/success/partial/error outcomes; and
- sanitized exception class with no message or traceback.

The following are prohibited in every table, JSON value, event, resource, and
identifier: query text or hashes, `process.command_args`, content, title,
citation, URL, local/repository path, tag, namespace/source/site/document/row
identifier, embedding vector, API key, credential, header, environment value,
provider response, raw exception message, and stack trace.

Span exception auto-recording MUST be disabled. Error spans record only a
bounded status and sanitized exception class.

## DuckDB contract

Schema version 1 contains:

- `telemetry_metadata`: exactly one schema-version row;
- `trace_runs`: one typed summary row per completed retrieval trace;
- `spans`: one row per allowlisted span with trace hierarchy, timestamps,
  duration, status, and allowlisted attributes as JSON;
- `span_events`: one row per allowlisted event with allowlisted attributes as
  JSON; and
- `retrieval_runs_v1` and `retrieval_stage_latency_v1` read-only views.

Trace and span IDs are lowercase hexadecimal OpenTelemetry IDs. Timestamps are
UTC and durations are finite, nonnegative milliseconds. Inserts for one trace
are atomic. Existing schema metadata is validated before append; an unknown or
malformed schema drops the new observation without altering the existing file
or retrieval behavior.

Validation MUST use DuckDB's qualified system catalog functions without
binding stored views. Every telemetry connection disables external access,
extension autoinstall/autoload, and community extensions. Ordered table
types/nullability/keys, view column types, and the code-owned canonical view
definitions are all part of schema compatibility; stored objects or macros
cannot redirect validation to a file, URL, extension, or shadow catalog
function.

Buoy opens the database only after acquiring the dedicated telemetry lock,
writes one transaction, closes it, and releases the lock. Lock acquisition is
nonblocking. There is no automatic update/delete, retention, compaction,
upload, replication, or external connection in this slice.

## Failure isolation

Telemetry setup, span creation, context propagation, span completion,
serialization, directory/file validation, locking, DuckDB initialization,
schema validation, or insert failure MUST NOT:

- change or hide the retrieval return value or original exception;
- add stdout/stderr output;
- add a provider/model call;
- delay on a contended lock;
- leave a partial trace transaction; or
- create local assets while telemetry is disabled.

Only Buoy's private telemetry session and parent span MAY be propagated into a
namespace executor submission, so concurrent namespace spans remain children
of the same retrieval trace. Buoy MUST NOT copy unrelated application
`ContextVar` values, attach its span as the process-wide OpenTelemetry current
span, inherit an ambient trace, or make its trace eligible for automatic
outbound trace-header propagation.

## Acceptance criteria

1. Disabled explicit and automatic retrieval remains byte-for-byte compatible
   at the public output boundary and creates no telemetry path.
2. Enabled successful explicit-single, explicit-multi, automatic-singleton,
   widened automatic, partial-failure, no-evidence, and all-failed retrievals
   produce the governed typed summary/span/event shape without changing their
   established behavior.
3. Concurrent namespace spans share the root trace ID and parent relationship;
   route ranks remain correct and no namespace identifier is persisted.
4. Sentinel tests prove that queries, content, URLs, paths, namespaces,
   document IDs, credentials, raw errors, and command arguments are absent
   from all persisted scalar and JSON values.
5. Persistence, permission, incompatible-schema, and lock-contention failures
   preserve the original result/exception and output, with no partial insert.
6. The telemetry directory/database/lock privacy and symlink/file rejection
   boundaries pass under isolated temporary homes.
7. The exact certified CLI/routing/evidence/routing-quality hashes stay equal
   to the `develop` base.
8. Focused and complete tests on Python 3.11 and 3.13, dependency lock, source,
   ranking, C6, compile, distribution, clean-wheel, privacy inspection, and
   diff-hygiene checks pass without provider, credential, model-download,
   installed-tool, publication, or remote telemetry effects.
