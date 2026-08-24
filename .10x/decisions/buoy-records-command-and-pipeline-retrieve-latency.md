Status: active
Created: 2026-08-20
Updated: 2026-08-20
Amends: .10x/decisions/buoy-records-opt-in-local-retrieval-telemetry.md, .10x/decisions/buoy-uses-a-private-local-telemetry-writer.md

# Buoy Records Command and Pipeline Retrieve Latency Separately

## Context

Buoy's first local OpenTelemetry slice deliberately starts its root
`buoy.retrieve` span at the retriever boundary. That boundary measures query
embedding, namespace requests, reranking, evidence assessment, and widening,
but it excludes work performed by the short-lived CLI before the retriever is
called. Explicit retrieval constructs the embedding model and namespace client
before entering the span. Automatic retrieval additionally reads the routing
catalog, loads routing components, and selects routes before entering it. CLI
imports, argument handling, and output rendering are also outside the span.

A 2026-08-20 user-run diagnostic on the installed `buoy
0.6.2.dev2+g796f7384e` reported explicit-single telemetry median latency of
about 0.46 seconds against about 13.37 seconds observed around the process,
and automatic telemetry median latency of about 0.72 seconds against about
15.65 seconds. The source confirms the boundary mismatch. The user wants
telemetry that represents ordinary `buoy retrieve` latency while retaining the
existing inner-pipeline measurement for diagnosis and historical comparison.

OpenTelemetry records the duration of the operation enclosed by a span; it
does not infer work outside an instrumented boundary. Its Trace API permits an
explicit start timestamp when the logical operation began before span
construction. The OpenTelemetry CLI semantic convention describes one
low-cardinality execution span for a short-lived CLI and warns that command
arguments may contain sensitive data and should not be collected by default.

The existing local telemetry database contains version-1 observations. Its
versioned views and the meaning of `retrieval_runs_v1.duration_ms` are already
published behavior and must not be reinterpreted.

## Decision

When local telemetry is enabled, every successfully parsed `buoy retrieve`
invocation that reaches the retrieve handler records a version-2 command trace.
This includes explicit-single, explicit-multi, and automatic routing in both
live and preview (`--dry-run` or `--plan`) execution modes, including sanitized
command failures. Help and argument-parser failures that do not dispatch the
retrieve handler are not observations.

The version-2 trace records two distinct latency scopes:

- **command duration** begins at the earliest timestamp captured by Buoy's
  lightweight console entry point before the legacy CLI import and ends after
  the retrieve handler has rendered its normal result or error;
- **pipeline duration** retains the existing retriever-boundary operation that
  measures query embedding, namespace queries, reranking, evidence assessment,
  and widening. It is absent for previews and for failures before a live
  retriever begins.

Command duration is a near-shell Buoy measurement, not a claim to include time
before Python reaches Buoy's entry point or time after Buoy returns to
interpreter/process teardown. Documentation and column names must state this
boundary. No generic `duration_ms` may be presented as both meanings.

Version-1 observations, tables, and views retain their exact historical
semantics. Version 2 uses separate command and retrieval-operation records and
stable version-2 views exposing `command_duration_ms` and nullable
`pipeline_duration_ms` explicitly. Direct Python callers that invoke the
retriever without the Buoy console entry point retain the version-1
pipeline-only trace contract.

The command root and all stage spans remain private OpenTelemetry spans. The
root is low-cardinality and contains no query, command argument, namespace,
path, content, citation, credential, raw error, or stack trace. Existing
content-free allowlists, ambient-context isolation, no-network behavior, and
failure isolation remain mandatory.

Preview retrieval may publish local telemetry only when
`BUOY_TELEMETRY=local` is effective. This is the sole deliberate change to the
old statement that preview creates no telemetry assets. With telemetry absent
or disabled, preview and live behavior remain zero-side-effect with respect to
telemetry.

The existing store upgrades only through an explicit, user-invoked migration.
Read-only status reports an upgrade requirement without mutation. The
migration validates and backs up the exact version-1 store, performs a bounded
atomic version-2 upgrade, preserves version-1 rows and views, and never deletes
the backup automatically. A missing store is created directly at version 2 by
the version-2 writer.

## Alternatives considered

### Keep the implementation and clarify documentation

Rejected. Documentation would prevent one interpretation error but would not
measure the dominant per-command cost or automatic preview latency.

### Replace pipeline duration with command duration

Rejected. It would silently change an established metric, erase useful stage
comparison, and make historical rows incomparable.

### Instrument plan, apply, and retrieve together

Rejected for this slice. The user selected all retrieve modes. Plan and apply
have different lifecycle, side effects, stages, and data contracts and require
separate shaping if later authorized.

### Automatically migrate the existing store

Rejected. It would silently mutate a user-owned operational history file from
a detached writer. The user selected an explicit migration checkpoint.

### Write version 2 to a second permanent database

Rejected. It avoids migration but fragments one local history across files and
complicates every analysis.

## Consequences

Users can compare near-shell command latency with the inner retrieval pipeline
and attribute the difference to bootstrap, routing, initialization, and
rendering stages. Preview latency becomes observable when telemetry is
explicitly enabled. Existing version-1 SQL retains its meaning.

The trace producer, private envelope, writer, DuckDB schema, status/flush
behavior, and documentation must evolve together. The writer must understand
both pending version-1 and version-2 envelopes. Older writers must not be able
to reject version-2 envelopes, so version 2 uses a distinct private inbox.

An existing user must run the explicit migration before version-2 envelopes
can be committed. Valid version-2 envelopes remain pending and recoverable
until migration. Migration creates one retained private backup; no automatic
retention or purge policy is introduced.

The command measurement will remain slightly lower than an external shell
measurement by unavoidable Python pre-entry and post-return time. Acceptance
therefore verifies a bounded documented gap instead of claiming identity.

## Sources

- `.10x/evidence/2026-08-20-retrieve-command-latency-gap.md`
- `.10x/research/2026-08-20-opentelemetry-cli-span-boundaries.md`
- `src/buoy_search/entrypoint.py`
- `src/buoy_search/cli.py`
- `src/buoy_search/retriever.py`
- `.10x/specs/local-telemetry-writer.md`
