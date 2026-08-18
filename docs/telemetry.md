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

When enabled, Buoy writes to:

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
current trace, then appends the completed retrieval to the local database.

Telemetry is best-effort and never controls retrieval. If the database is
locked, unavailable, incompatible, or cannot accept a complete trace, Buoy
silently drops that trace and preserves the retrieval result or error. Writes
are serialized and committed as one transaction, so readers see complete
retrievals rather than partially written traces.

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
Buoy validates the versioned schema and view definitions before each append;
editing those database objects makes the store incompatible and causes later
traces to be dropped rather than modifying an unknown layout.

## Storage lifecycle

Version 1 has no automatic retention or purge policy. The database grows with
each recorded live retrieval until you manage the file yourself. Disable new
records by unsetting `BUOY_TELEMETRY`, setting it to a value other than
`local`, or setting `OTEL_SDK_DISABLED=true`.
