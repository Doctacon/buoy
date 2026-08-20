Status: accepted
Created: 2026-08-19
Updated: 2026-08-19
Amends: .10x/decisions/buoy-records-opt-in-local-retrieval-telemetry.md

# Buoy Uses a Private Local Telemetry Writer

## Context

The first local retrieval-telemetry slice synchronously opens, validates, and
writes DuckDB in every short-lived Buoy process. A 100-scenario validation
campaign preserved retrieval behavior, privacy, and database integrity, but
found two material operational limits:

- a fresh Python process paid roughly 0.9 seconds after environment warmup and
  11--16.6 seconds on first environment use before its first parameterized
  DuckDB operation; and
- the nonblocking database lock preserved retrieval but persisted only 1 of 12
  synchronized thread traces and 1 of 8 synchronized process traces.

The owner wants to keep personal telemetry local and queryable in DuckDB. The
reviewed Adobe, Mastodon, and Skyscanner OpenTelemetry reference deployments
all use network OTLP collectors and remote observability backends. None is a
precedent for a private single-user DuckDB sink. Mastodon's one-collector
topology supports centralizing ownership, while Adobe's chained-collector
experience reinforces the need to distinguish accepted telemetry from data
that reached its final destination.

## Evidence and references

The diagnostic campaign and its limitations are recorded at
`.10x/evidence/2026-08-19-local-telemetry-100-scenario-findings.md`. Its exact
subject was `develop@3787e0eabd2720732fb5c68ca168f926342ae454`.

The external comparisons use only the official OpenTelemetry reference pages:

- [Adobe: architecture](https://opentelemetry.io/docs/guidance/reference-implementations/adobe/#architecture);
- [Mastodon: one Collector per namespace](https://opentelemetry.io/docs/guidance/reference-implementations/mastodon/#collector-architecture-one-per-namespace-no-more); and
- [Skyscanner: centralized routing, distributed collection](https://opentelemetry.io/docs/guidance/reference-implementations/skyscanner/#architecture-centralized-routing-distributed-collection).

Those pages support centralized processing and lifecycle ownership. They do
not claim a durable local filesystem handoff, a DuckDB sink, or this ticket's
process-crash delivery guarantees.

## Decision

Buoy keeps its private in-process OpenTelemetry trace model and its exact
content-free allowlists. After a retrieval completes, Buoy converts the trace
to a versioned typed envelope only after sink-side sanitization, then
atomically publishes that envelope beneath:

```text
~/.buoy/telemetry/inbox-v1/
```

Publication is the retrieval process's final telemetry responsibility. The
retrieval process never opens DuckDB, waits for a DuckDB writer lock, sends an
OTLP request, or waits for a database acknowledgement.

One Buoy-owned local writer drains published envelopes into the existing
canonical database:

```text
~/.buoy/telemetry/telemetry.duckdb
```

The writer is a bounded-idle, bounded-work-admission detached Buoy process, not a generic
OpenTelemetry Collector, permanent service, or network listener. A lifetime
lock elects one writer per telemetry home. Producers best-effort start it
after publishing; an explicit bounded `buoy telemetry flush` command can wait
for pending work. The writer closes DuckDB when not actively draining and
exits after a bounded idle interval. Its no-new-claim deadline does not claim
unsafe cancellation of an in-flight DuckDB filesystem call.

The envelope is a private internal transport, not raw OTLP. It contains only
the already-governed typed run, span, and event values. The writer treats the
file as untrusted and independently revalidates its exact version, structure,
types, bounds, trace graph, and allowlists before touching DuckDB. Unknown or
malformed fields, raw spans, resources, baggage, links, exception details,
query/content fields, and payload-selected paths are prohibited.

An envelope is acknowledged and removed only after its complete trace is
committed. Replay after a crash is idempotent by trace ID: an exact existing
trace acknowledges the envelope, while conflicting data is not allowed to
overwrite or delete the existing trace. Incompatible or unavailable stores
leave valid envelopes recoverable. A bounded inbox drops the newest
observation at capacity rather than deleting older pending work.

`buoy telemetry status` is a read-only local diagnostic. It reports effective
enablement, store compatibility, pending counts/bytes, persisted runs,
writer state, and content-free lower-bound drop/rejection/failure accounting.
It never creates, repairs, migrates, drains, starts, or deletes anything.

## Explicit non-decisions

This is not an OpenTelemetry Collector deployment. It adds no OTLP exporter or
receiver, TCP/HTTP/gRPC/Unix-socket listener, Collector distribution, remote
backend, cloud fan-out, generic auto-instrumentation, or secondary telemetry
destination. A genuine interoperable Collector path remains a separate future
decision if multiple producers or remote backends become requirements.

It also adds no telemetry schema migration, query fingerprint, raw content,
retention policy, automatic purge, analytics UI, subjective feedback, or new
instrumented product surface.

## Consequences

Normal retrieval pays only bounded envelope serialization and private local
file publication. DuckDB initialization, validation, batching, and retry move
off the retrieval critical path. Concurrent retrieval processes publish
independent durable envelopes instead of competing for the database lock.

Persistence becomes eventual. Successfully publishing an envelope means
"accepted locally for processing," not "committed to DuckDB." Status and
flush make that distinction visible. Total filesystem failure or process death
before publication remains inherently unobservable, and reported producer
drops are explicitly a lower bound.

The filesystem queue introduces additional private local files and a
best-effort bounded child process only when telemetry is enabled. Disabled
telemetry retains its existing zero-side-effect contract.

## Authorization boundary

On 2026-08-19 the repository owner reviewed the distinction between a generic
OpenTelemetry Collector and the proposed Buoy-local writer, approved the local
writer recommendation, and directed execution. This authorizes the isolated
`work/local-telemetry-writer` branch/worktree, governing records, bounded
source/tests/docs changes, local temporary validation, and a bounded task
commit. Hosted push, pull-request creation, and integration remain later
handoff actions and are not inferred from this local implementation approval.

It does not authorize `main` mutation, release/publication, installed-tool
replacement, provider/catalog/namespace/content mutation, credential access,
remote telemetry export, existing telemetry deletion/migration, or a generic
Collector/network endpoint.
