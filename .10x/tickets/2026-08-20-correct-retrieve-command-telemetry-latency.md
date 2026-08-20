Status: open
Created: 2026-08-20
Updated: 2026-08-20
Parent: None
Depends-On: None
Decision: .10x/decisions/buoy-records-command-and-pipeline-retrieve-latency.md
Specifications: .10x/specs/retrieve-command-telemetry.md, .10x/specs/local-telemetry-v2-storage-and-migration.md

# Correct Retrieve Command Telemetry Latency

## Plan status

This is a parent plan, not an executable ticket. Its child tickets own the
bounded implementation and validation units.

## Aggregate outcome

Buoy records near-shell command duration and retained inner-pipeline duration
under distinct version-2 fields for all successfully parsed live and preview
retrieve modes, while preserving version-1 history, privacy, local-only
operation, failure isolation, and direct-library compatibility.

## Child sequence

1. `.10x/tickets/2026-08-20-implement-local-telemetry-v2-storage-migration.md`
   implements the envelope/inbox/store/status/flush/migrate substrate using
   deterministic fixture traces. It is the first dependency and owns no CLI
   retrieval instrumentation.
2. `.10x/tickets/2026-08-20-instrument-retrieve-command-pipeline-latency.md`
   depends on child 1 and wires entry-point, CLI-stage, and nested pipeline
   traces into that substrate.
3. `.10x/tickets/2026-08-20-validate-retrieve-command-telemetry-v2.md` depends
   on both implementation children and owns independent end-to-end acceptance,
   migration rehearsal, documentation reconciliation, and final review input.

Children are sequential because they modify shared telemetry modules and one
governed schema. They must use one task worktree/branch at a time; no parallel
writers may edit the same worktree.

## Integration points

- `src/buoy_search/entrypoint.py` owns earliest Buoy timestamp and top-level
  telemetry command dispatch.
- `src/buoy_search/telemetry.py` owns private trace/session behavior.
- `src/buoy_search/telemetry_envelope.py` owns exact v1/v2 transport validation.
- `src/buoy_search/telemetry_queue.py` owns separate versioned inboxes.
- `src/buoy_search/telemetry_store.py` owns exact DuckDB schemas/views and
  atomic append/migration helpers.
- `src/buoy_search/telemetry_writer.py` owns dual-version drain plus status,
  flush, and explicit migration orchestration.
- `src/buoy_search/cli.py` and `src/buoy_search/retriever.py` own command-stage
  and pipeline boundaries without behavior changes.

## Aggregate acceptance criteria

- Every acceptance criterion in both governing specifications maps to durable
  evidence or an explicitly documented limit.
- Version-1 rows and exact v1 views retain their old meaning after migration.
- Live and preview command traces expose command duration; live traces expose a
  distinct pipeline duration when the pipeline begins.
- Controlled parent-observed subprocess evidence passes the governing timing
  gate on the reference host.
- Privacy, path safety, crash/replay, no-network, disabled behavior, call-count,
  output, and full compatibility suites pass.
- An independent adversarial review passes or every concern is resolved or
  explicitly accepted in a durable decision.
- No installed tool, provider asset, namespace, credential, package release,
  `main`, or existing real telemetry store is changed by implementation or
  validation.

## Explicit exclusions

Plan/apply/crawl/eval/catalog telemetry, ranking/evidence changes, query or argv
collection, Collector/OTLP/network export, automatic migration, automatic
backup deletion, installed-tool replacement, release/publication, and live
provider validation are outside this plan.

## Dependencies

The implementation branch is
`work/retrieval-command-telemetry-v2`, based on exact
`develop@0c669c5ea52a7dd1adf060c9197a395a2d05e21d` in
`/private/tmp/buoy-retrieval-command-telemetry-v2`.

## Blockers

None for the specified local implementation. Hosted integration, release, and
installed-tool replacement are not authorized by this plan and are not needed
for its completion.

## Progress and notes

- 2026-08-20: The owner supplied a live diagnostic showing a material
  command/pipeline latency gap. Source and active records confirmed the omitted
  boundary mechanism.
- 2026-08-20: The owner selected all retrieve modes, separate command and
  pipeline latency, and an explicit backed-up store migration, then switched
  to build mode and directed execution.
- 2026-08-20: The parent session created the governing decision, research,
  user-reported evidence, focused specifications, parent plan, and bounded
  child tickets on the isolated task branch. Targeted header/reference checks
  and `git diff --check` passed. Under the 10x execution gate, implementation
  does not begin in the same turn that opens the first executable tickets.
