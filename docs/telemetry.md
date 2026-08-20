# Inspect local retrieval telemetry

Buoy can record timing and outcome metadata for live retrievals in a local
DuckDB database. Telemetry is off by default. Enable it for one command:

```bash
BUOY_TELEMETRY=local buoy retrieve "How are retries configured?" \
  --namespace github-example-service-v1
```

Or export the setting for a longer local session:

```bash
export BUOY_TELEMETRY=local
```

The opt-in is the named `local` mode rather than a boolean switch.
`BUOY_TELEMETRY=1`, `true`, and other values do not enable recording.
`OTEL_SDK_DISABLED=true` overrides the Buoy setting and disables telemetry.

This first version records live retrieval only. Dry-run and plan operations do
not create telemetry.

## What is stored

When enabled, Buoy publishes a sanitized private envelope beneath
`~/.buoy/telemetry/inbox-v1/`. One short-lived Buoy writer drains those
envelopes into:

```text
~/.buoy/telemetry/telemetry.duckdb
```

The database contains one row per retrieval plus OpenTelemetry spans for
query embedding, namespace queries, reranking, and evidence assessment when
those stages occur. Recorded fields are limited to operational metadata such
as timing, retrieval mode, fanout, hit and failure counts, widening and
fallback outcomes, model family, precision, and generic error categories.

Buoy does not store the query, returned content, citations, URLs, file paths,
namespace or source identifiers, document identifiers, vectors, credentials,
command arguments, raw error messages, or stack traces.

This local mode does not start or contact an OpenTelemetry Collector. It does
not send telemetry over the network or to a cloud service. Buoy uses a private
in-process OpenTelemetry provider that is not installed as the process-wide
current trace, sanitizes the completed trace before it touches disk, and asks
a Buoy-owned local writer to persist it. The handoff is a private filesystem
queue, not OTLP.

Telemetry never controls retrieval. Once an envelope is published, database
contention or writer absence leaves it recoverable instead of discarding it.
The queue has strict private size limits; a full or unsafe queue drops only the
newest observation and still preserves the retrieval result or error. The
single writer commits each trace as one transaction, so readers see complete
retrievals rather than partially written traces. Persistence is eventual: a
successful retrieval can return before its row appears in DuckDB.

## Check or flush telemetry

Inspect enablement, pending work, writer health, and the last compatible store
snapshot without creating or changing anything:

```bash
buoy telemetry status
buoy telemetry status --json
```

Ask the local writer to drain the envelopes that are pending at command start,
waiting at most 30 seconds by default:

```bash
buoy telemetry flush
buoy telemetry flush --timeout 120 --json
```

`status` never starts the writer or opens DuckDB. `flush` is bounded and can
drain existing work even after collection has been disabled. Neither command
contacts a provider, model, Collector, or network service. A degraded or
blocked result uses a nonzero exit code and contains only operational counts
and reason codes, not envelope contents or raw errors.

The private writer currently requires the POSIX no-follow, ownership, and
descriptor-relative filesystem safeguards available on macOS and Linux. If
those primitives are unavailable, telemetry fails closed without affecting
retrieval and `status` reports `platform_unsupported`.

## Upgrade an existing telemetry database

A version-2-capable Buoy installation creates new telemetry databases directly
at schema version 2. It never upgrades an existing schema-version-1 database
automatically. When safe matching writer-state metadata proves an existing
schema-version-1 store, `buoy telemetry status` reports `upgrade_required`;
without that state proof it intentionally reports `present_unverified` because
status never opens DuckDB. Version-1 work can still drain, while version-2
envelopes remain pending.

Run the explicit local migration when you are ready:

```bash
buoy telemetry migrate
buoy telemetry migrate --json
```

Migration first drains its bounded version-1 queue snapshot, validates the
exact closed database, builds and validates a private scratch copy, and keeps a
byte-for-byte version-1 backup at:

```text
~/.buoy/telemetry/telemetry-v1-backup.duckdb
```

Buoy then atomically publishes the validated schema-version-2 database. The
migration accepts no alternate path, force, repair, or delete option; it does
not contact a provider, model, catalog, Collector, or network service. A
mismatching or unsafe preexisting backup blocks the migration rather than
overwriting history. Repeating a completed migration is a successful
read-only no-op. Buoy never deletes the retained backup automatically.

Schema version 2 preserves `retrieval_runs_v1` and
`retrieval_stage_latency_v1` exactly. The separate version-2 command views are
populated only by version-2 command envelopes; production command timing is a
separate instrumentation change from this storage upgrade.

## Query the database

The versioned views are the stable starting point for analysis. Open the
database read-only with the DuckDB command-line client:

```bash
duckdb -readonly ~/.buoy/telemetry/telemetry.duckdb
```

Summarize retrieval volume, latency, and outcomes by day:

```sql
SELECT
    CAST(started_at AS DATE) AS day,
    count(*) AS retrievals,
    round(avg(duration_ms), 1) AS average_ms,
    count_if(outcome = 'success') AS successful,
    count_if(incomplete) AS incomplete
FROM retrieval_runs_v1
GROUP BY day
ORDER BY day DESC;
```

Compare latency by retrieval stage:

```sql
SELECT
    stage,
    count(*) AS calls,
    round(avg(duration_ms), 1) AS average_ms,
    round(quantile_cont(duration_ms, 0.95), 1) AS p95_ms
FROM retrieval_stage_latency_v1
GROUP BY stage
ORDER BY p95_ms DESC;
```

Inspect widening and partial-failure behavior without exposing source names:

```sql
SELECT
    retrieval_mode,
    widened,
    fallback_reason,
    failure_count,
    count(*) AS retrievals
FROM retrieval_runs_v1
GROUP BY ALL
ORDER BY retrievals DESC;
```

The underlying `spans` and `span_events` tables are available for deeper local
analysis, but their JSON attributes are implementation details. Prefer
`retrieval_runs_v1` and `retrieval_stage_latency_v1` for saved queries.
Buoy validates the versioned schema and view definitions in the writer;
editing those database objects makes the store incompatible and leaves later
envelopes pending rather than modifying an unknown layout.

## Storage lifecycle

Local telemetry has no database retention or purge policy. The database grows with
each recorded live retrieval until you manage the file yourself. Content-free
terminal receipts rotate within a fixed bound; pending envelopes are never
evicted to make room for newer ones. Disable new records by unsetting
`BUOY_TELEMETRY`, setting it to a value other than `local`, or setting
`OTEL_SDK_DISABLED=true`. Use `buoy telemetry flush` before inspecting or
backing up the database when you need all currently accepted envelopes
persisted.
