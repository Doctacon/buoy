Status: done
Created: 2026-08-20
Updated: 2026-08-20

# OpenTelemetry CLI Span Boundaries

## Question

How should Buoy use OpenTelemetry to measure user-relevant latency for a
short-lived CLI without losing its existing inner retrieval trace or collecting
sensitive command data?

## Sources and methods

The investigation compared Buoy's current source and active records with
official OpenTelemetry documentation:

- OpenTelemetry Trace API specification:
  https://opentelemetry.io/docs/specs/otel/trace/api/
- OpenTelemetry Python manual instrumentation guide:
  https://opentelemetry.io/docs/languages/python/instrumentation/
- OpenTelemetry CLI span semantic conventions (Development status):
  https://opentelemetry.io/docs/specs/semconv/cli/cli-spans/
- `src/buoy_search/entrypoint.py`
- `src/buoy_search/cli.py`
- `src/buoy_search/retriever.py`
- `src/buoy_search/telemetry.py`
- `.10x/specs/local-telemetry-writer.md`

The external sources were inspected on 2026-08-20. No OpenTelemetry Collector,
provider, model, namespace, credential, or network telemetry destination was
used.

## Findings

### Spans measure only their explicit logical operation

The Trace API defines start and end timestamps around a logical operation.
Start defaults to span creation and end defaults to the time `End` is called.
OpenTelemetry does not discover work performed before a span begins. Buoy's
large discrepancy is therefore expected from the current boundary rather than
evidence that the SDK computes span duration incorrectly.

### A past logical start may be supplied explicitly

The Trace API says a custom start timestamp is appropriate when the logical
start has already passed. Buoy's lightweight entry point can capture an epoch
timestamp before importing the heavyweight CLI, then construct the private
span provider and root span with that timestamp. This includes Buoy-owned
import/bootstrap time without requiring eager global instrumentation.

### Nested manual spans are the normal Python pattern

The Python manual instrumentation guide demonstrates a root span with nested
child spans whose context-manager boundaries define their operations. Buoy can
retain its private provider and context propagation while making the existing
retrieval operation a child of a command root.

### CLI conventions support a low-cardinality execution root

The CLI semantic convention is explicitly marked Development. It recommends
one execution span for a short-lived CLI, an `INTERNAL` callee span kind, a
low-cardinality name, exit status, and low-cardinality error classification.
It recommends command arguments only with sanitization and warns they can
contain sensitive data. Buoy should continue prohibiting argv entirely rather
than weakening its existing privacy boundary.

### In-process command time cannot equal shell time exactly

A Buoy-created span cannot observe time before Python imports/calls Buoy or
after Buoy returns into interpreter and process teardown. Capturing the first
Buoy-owned timestamp and ending after rendering should include the material
work identified in the diagnostic, but the result must be named and documented
as Buoy command duration with a measured shell gap.

### Historical pipeline duration must not be relabeled

`retrieval_runs_v1.duration_ms` currently means the inner retriever operation.
Changing its meaning in place would mix incomparable observations. A command
root and version-2 views should expose command and pipeline duration under
distinct names while leaving v1 immutable.

## Conclusions

Buoy should create one private version-2 command root for dispatched retrieve
commands, backdated only to the earliest Buoy-owned entry timestamp, and nest
the existing retrieval pipeline beneath it. It should instrument only bounded,
content-free stages needed to explain the command/pipeline gap. It should not
collect argv, query text, process paths, ambient resources, or network-exported
telemetry.

A controlled subprocess comparison is required because unit tests can prove
span boundaries but cannot establish how closely the Buoy command span follows
parent-observed process time. The acceptance comparison must disclose the
unobservable pre-entry/post-return gap.

The CLI semantic convention's Development status means Buoy should document
its stable private names rather than claim full conformance to a convention
that may still change.
