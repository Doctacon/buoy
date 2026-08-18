Status: accepted
Created: 2026-08-18
Updated: 2026-08-18
Amends: .10x/decisions/buoy-defaults-local-assets-to-one-user-home.md

# Buoy Records Opt-In Local Retrieval Telemetry

## Context

Buoy's retrieval path exposes routing, fallback, reranking, and evidence
diagnostics in individual command results, but it has no durable operational
history for comparing latency and outcomes across versions. The repository
owner wants personally controlled usage traces that can support later Buoy
improvements without sending queries or content to a third party.

OpenTelemetry defines the trace model and instrumentation API, but it does not
require a hosted service or Collector. The stock Collector has no maintained
DuckDB exporter, while Buoy already ships DuckDB and a cooperative process-lock
pattern for private local state.

## Decision

Buoy owns one opt-in, local-only retrieval trace sink at:

```text
~/.buoy/telemetry/telemetry.duckdb
```

Setting `BUOY_TELEMETRY=local` enables the sink. Every other value, absence of
the variable, and the standard `OTEL_SDK_DISABLED` switch leave it disabled.
Disabled telemetry creates no home, directory, lock, database, thread, network
request, stdout text, or stderr text.

An enabled live retrieval creates OpenTelemetry spans in memory and attempts
one short, portalocker-serialized DuckDB transaction after the retrieval trace
ends. Persistence is best-effort: lock contention, an unavailable or
incompatible database, OpenTelemetry failure, or any local filesystem error
may drop that observation but MUST NOT change the retrieval result, exception,
exit behavior, stdout, or stderr.

The private span tree is never installed as ambient process OpenTelemetry
context. Buoy propagates only its own parent/session state to namespace worker
threads, so unrelated application context is unchanged and automatic client
instrumentation cannot export or inject headers for the local trace.

The database is an append-only operational observation store, separate from
per-source applied state. It contains a typed row per retrieval, generic span
rows, span-event rows, schema metadata, and versioned analytical views. The
first schema is content-free and permits only an explicit attribute allowlist.
It never stores query text, command arguments, content, titles, citations,
URLs, paths, namespace/source/document/row identifiers, vectors, credentials,
headers, raw provider responses, raw exception messages, or stack traces.

The first slice covers live explicit-single, explicit-multi, and automatic
content retrieval from the retriever boundary. It records query embedding,
per-route-rank namespace query, cross-namespace reranking, evidence assessment,
and widening events. It does not modify the currently certified CLI, routing,
evidence, or routing-quality modules, so catalog-read and route-selection
latency remain future work.

The local DuckDB sink is the canonical first destination. A Collector, OTLP
export, Jaeger, Tempo, hosted backend, telemetry UI, raw JSONL archive, and
cloud fan-out are not enabled or configured by this decision. A later reviewed
ticket may add an explicitly configured secondary OTLP destination without
changing the local privacy contract.

## Consequences

The owner can query retrieval history with DuckDB SQL and compare stage
latency, widening, failures, evidence outcomes, and version/model revisions.
The history cannot answer whether a result was subjectively useful because the
first slice records neither query text nor feedback.

Because DuckDB's stable local concurrency model is one writer process, Buoy
buffers one short-lived trace in memory and opens the database only while
holding its dedicated process lock. A contended observation is dropped rather
than blocking or failing retrieval. A hard process termination before the
final transaction can lose that command's trace.

The first slice performs no automatic pruning. The database is user-owned,
contains only allowlisted operational metadata, and is expected to remain
small at personal CLI volume. Retention controls and an explicit purge command
require a later reviewed decision.

## Authorization boundary

On 2026-08-18 the repository owner explicitly authorized this bounded
implementation and requested that a passing, independently reviewed change be
integrated into `develop`. That authority includes the task worktree/branch,
governing records, dependency lock, local source/tests/docs, offline and local
validation, bounded commits, branch push, pull request, independent review,
and a separate integration session's squash merge into `develop`.

It does not authorize `main` mutation, release publication, package upload,
tag or GitHub Release creation, provider/catalog/content mutation, credential
access, remote telemetry export, installed-tool replacement, collection of
prohibited content, or deletion of any existing local asset.
