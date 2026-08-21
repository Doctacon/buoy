Status: blocked
Created: 2026-08-20
Updated: 2026-08-20
Parent: .10x/tickets/2026-08-20-correct-retrieve-command-telemetry-latency.md
Depends-On: .10x/tickets/done/2026-08-20-implement-local-telemetry-v2-storage-migration.md
Decision: .10x/decisions/buoy-records-command-and-pipeline-retrieve-latency.md
Specification: .10x/specs/retrieve-command-telemetry.md
Storage: .10x/specs/local-telemetry-v2-storage-and-migration.md

# Instrument Retrieve Command and Pipeline Latency

## Scope

After the version-2 storage substrate is complete, instrument all successfully
parsed live and preview `buoy retrieve` modes with one private command root,
governed stage spans, and a distinct nested live pipeline operation. Preserve
direct-library version-1 traces and all established command behavior.

Owned modules are the lightweight entry point, CLI retrieve orchestration,
retriever/telemetry session integration, focused command/retrieval tests, and
retrieve telemetry user documentation. Storage changes are limited to repairs
required by proven integration defects and must remain inside the storage spec.

## Required work

- Capture the earliest per-invocation Buoy timestamp before legacy CLI import.
- Materialize one v2 command trace only after retrieve-handler dispatch.
- Cover explicit single/multi and automatic, live/preview, success/error.
- Add only the governed bootstrap, preparation, routing, pipeline, and rendering
  stages that actually occur.
- Make existing `retrieval_trace` create one pipeline child under an active
  command trace and preserve standalone v1 behavior otherwise.
- Publish once at command completion; never publish the nested pipeline
  separately.
- Preserve output, validation order, call counts, exceptions, routing,
  ranking, evidence, preview safety, private context, and no-network behavior.

## Acceptance criteria

1. All eleven acceptance scenarios in
   `.10x/specs/retrieve-command-telemetry.md` pass with deterministic tests.
2. Explicit/automatic live success and failure produce exact command plus
   nullable/non-null pipeline rows and governed parentage.
3. Explicit/automatic previews produce command observations only when enabled,
   contain no pipeline/content stages, and add no provider/model operation.
4. Missing credential, catalog/routing/model failure, provider failure, render
   failure, and unexpected exception retain exact established command
   behavior while recording only governed categories best effort.
5. Direct retriever calls retain byte/semantic v1 observations; active command
   calls emit exactly one v2 envelope.
6. Sentinel and ambient-context tests prove the complete privacy and isolation
   boundary.
7. Fake-clock tests prove exact start/end semantics; controlled delayed
   subprocesses are implemented for the child validation ticket without live
   provider work.
8. Existing CLI, routing, retrieval, evidence, telemetry, full-suite,
   compilation, distribution, clean-wheel, and diff checks pass.

## Evidence expectations

Record exact changed boundaries, trace graphs for each mode/outcome, enabled
and disabled output/call equivalence, privacy scan, focused/full commands and
results, and any residual timing limitation. Do not claim external shell
representativeness until the dependent validation ticket observes it.

## Explicit exclusions

No plan/apply/crawl/eval/catalog telemetry, schema redesign beyond the active
storage spec, live provider/credential/namespace use, query/argv collection,
Collector/OTLP/network export, ranking/evidence changes, installed-tool
replacement, release, `main`, or publication.

## Assumption provenance

- Trace scope and all retrieve modes are user-ratified.
- Existing pipeline semantics and private context behavior are record/source-
  backed.
- Exact shell identity is explicitly not claimed; the specified near-shell
  boundary is user-ratified and research-backed.

## Blockers

The storage dependency is done with passing exact-commit review at
`.10x/tickets/done/2026-08-20-implement-local-telemetry-v2-storage-migration.md`.

The active command telemetry spec requires every command summary to contain an
integer `exit_code`, including when an unexpected exception escapes the
retrieve handler unchanged, but it does not define the stored value when no
handler return code exists. The v2 validator permits zero, while the
recommended user-legible contract is `1`, matching generic process failure.
This telemetry semantic requires owner ratification before source or tests can
encode it. Render failures that are converted to a returned code would retain
that actual returned code; only escaping exceptions are blocked.

## Progress and notes

- 2026-08-20: Opened after user ratification and source/record inspection.
- 2026-08-21: Storage/migration dependency closed with passing review at exact
  commit `3119375`; command/pipeline instrumentation is unblocked and remains
  the sole implementation scope of this ticket.
- 2026-08-21: Execution assigned sequentially from clean governing commit
  `8113fb6` on the isolated task branch. Production retrieve instrumentation,
  focused tests, and retrieve telemetry documentation are the only permitted
  behavior changes; storage repair requires a proven integration defect.
- 2026-08-21: Source/spec inspection found one unratified command-summary
  semantic: the stored integer exit code for an exception that escapes without
  a handler return. Supervisor recommends `1` but correctly withheld authority
  pending owner confirmation. Ticket marked blocked before source/test edits;
  the worktree otherwise remains at the governing implementation state.
