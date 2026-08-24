Status: recorded
Created: 2026-08-20
Updated: 2026-08-20
Relates-To: .10x/decisions/buoy-records-command-and-pipeline-retrieve-latency.md, .10x/specs/retrieve-command-telemetry.md

# User-Reported Retrieve Command Latency Gap

## What was reported

On 2026-08-20 the repository owner supplied the report of another LLM-run
diagnostic against installed `buoy 0.6.2.dev2+g796f7384e`. The report stated
that it exercised ordinary plan, apply, preview, and live retrieve workflows,
flushed 12 local telemetry rows, and compared telemetry duration with elapsed
time observed around CLI processes.

The reported medians were:

| Retrieval mode | Telemetry median | Process-observed median | Reported ratio |
| --- | ---: | ---: | ---: |
| Explicit single | 0.458 s | 13.37 s | about 29x |
| Explicit multi | 0.83 s | 13.92 s | about 17x |
| Automatic | 0.718 s | 15.65 s | about 22x |

The report also stated that an automatic preview took 11.45 seconds and
produced no retrieval telemetry.

## Source inspection procedure

The parent session inspected the exact governing records and current source on
`develop@0c669c5ea52a7dd1adf060c9197a395a2d05e21d`:

- `.10x/decisions/buoy-records-opt-in-local-retrieval-telemetry.md`
- `.10x/specs/local-telemetry-writer.md`
- `src/buoy_search/entrypoint.py`
- `src/buoy_search/cli.py`
- `src/buoy_search/retriever.py`
- `src/buoy_search/telemetry.py`

Git inspection established that reported installed commit
`796f7384e2c86f6fb9e10f9099dbec589f8e47e6` is the tagged v0.6.2 merge whose
second parent is the release-side develop commit; current develop descends from
that release line.

Source inspection found:

- explicit CLI retrieval constructs `HybridRetriever` or
  `MultiNamespaceRetriever` before calling `.retrieve()`;
- those constructors load the retrieval embedding model before the current
  `retrieval_trace()` context begins;
- automatic retrieval reads and validates the remote routing catalog, loads
  routing components, and selects a route before constructing/calling the
  content retriever;
- the current trace begins inside the retriever method and ends before CLI
  output rendering; and
- the active performance specification explicitly times only immediately
  before the retrieval call through its return/exception and excludes process
  startup/import.

## What this supports

The inspected source and records support the qualitative claim that current
`retrieval_runs_v1.duration_ms` is inner-pipeline latency and cannot represent
end-to-end CLI latency. They support that model/retriever initialization,
automatic catalog/routing work, CLI bootstrap, and output occur outside the
current root span.

They also support that preview intentionally creates no version-1 retrieval
trace, so a slow automatic preview is invisible to the current telemetry
surface.

## Limits

The parent session did not reproduce the supplied live commands, query the
owner's real telemetry database, inspect the other LLM's raw shell-timing
artifacts, access credentials, or contact Turbopuffer. The exact numeric
medians, row counts, namespace state, and scenario classifications remain
user-reported rather than independently verified by this record.

Source structure establishes an omitted-work mechanism, not the exact amount
of time each omitted stage consumed. New controlled and parent-observed
subprocess evidence is required after implementation.
