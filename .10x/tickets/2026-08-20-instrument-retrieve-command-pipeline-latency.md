Status: active
Created: 2026-08-20
Updated: 2026-08-20
Parent: .10x/tickets/2026-08-20-correct-retrieve-command-telemetry-latency.md
Depends-On: .10x/tickets/done/2026-08-20-implement-local-telemetry-v2-storage-migration.md
Decision: .10x/decisions/buoy-records-command-and-pipeline-retrieve-latency.md
Specification: .10x/specs/retrieve-command-telemetry.md
Storage: .10x/specs/local-telemetry-v2-storage-and-migration.md
Routing-Decision: .10x/decisions/buoy-recertifies-routing-cli-for-command-telemetry.md
Routing-Specification: .10x/specs/bounded-prototype-routing-activation.md

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
Because the active routing artifact certifies exact CLI bytes, this ticket also
owns the existing routing specification's dormant-source recertification and
artifact-only reactivation phases for the final instrumented CLI. It owns no
routing semantic change.

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
- Restore the exact collect-only routing artifact while final source is made
  clean, run and independently audit the exact 65-case read-only dormant
  certification, then reactivate only with measured source receipts.
- Preserve every frozen routing value and fail closed on drift, dirty source,
  unexpected call class, model download, content access, or provider mutation.

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
9. The exact final instrumented CLI is certified through the active routing
   specification's clean dormant report and independent audit; the reactivated
   artifact contains only measured receipts, and source/wheel/sdist/installed
   bytes reproduce them without changing any frozen routing result.

## Evidence expectations

Record exact changed boundaries, trace graphs for each mode/outcome, enabled
and disabled output/call equivalence, privacy scan, focused/full commands and
results, and any residual timing limitation. Also record dormant/final
commit/tree identities, report and artifact hashes, exact source receipts,
frozen-result equality, call accounting, no-mutation audit, and independent
report/final reviews. Do not claim external shell representativeness until the
dependent validation ticket observes it.

## Explicit exclusions

No plan/apply/crawl/eval/catalog telemetry, schema redesign beyond the active
storage spec, content-provider query/write or provider mutation, query/argv
collection, Collector/OTLP export, ranking/evidence/routing semantic changes,
installed-tool replacement, release, `main`, or publication. The sole live
exception is the owner-authorized, source-only 65-case routing certification:
complete routing-catalog reads and bounded routing-model inference under the
exact call accounting and stop gates in the active routing specification.

## Assumption provenance

- Trace scope and all retrieve modes are user-ratified.
- Existing pipeline semantics and private context behavior are record/source-
  backed.
- Exact shell identity is explicitly not claimed; the specified near-shell
  boundary is user-ratified and research-backed.

## Blockers

None before the dormant-source phase. The storage dependency passed review,
the escaping-exception value is ratified, and the owner explicitly chose the
existing clean recertification protocol after the CLI receipt conflict was
disclosed. Independent audit of the new dormant report is a mandatory stop gate
before artifact reactivation, not authority to skip or predict that gate.

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
  a handler return. Supervisor recommended `1` and correctly withheld source
  edits pending owner confirmation.
- 2026-08-21: The owner explicitly ratified stored `exit_code=1` for every
  exception escaping retrieve unchanged. Returned failures retain their actual
  code. The active spec now records that this is observation semantics only and
  cannot catch, convert, or replace the exception. Ticket reactivated.
- 2026-08-21: The first bounded producer/CLI candidate compiled and 143 focused
  tests plus 41 subtests passed, but five existing automatic-routing tests
  failed because the active loader correctly rejected changed `cli.py` bytes.
  Governing authority is the active routing decision/spec above; the exact
  packaged receipt is at
  `src/buoy_search/data/automatic_routing_confidence_calibration.json:57`, and
  runtime enforcement is at `src/buoy_search/routing_quality.py:2226-2235`.
  Failed tests were
  `MultiNamespaceCliTests::{test_missing_cli_namespace_enters_auto_mode_and_key_failure_precedes_client,test_environment_namespace_is_ignored_and_does_not_bypass_auto_credentials}`
  and
  `AutomaticRoutingCliTests::{test_catalog_resource_failure_cannot_leak_credentials,test_invalid_evidence_artifact_fails_before_provider_work,test_missing_key_fails_before_client_even_if_ambient_namespace_is_set}`.
  No artifact/hash boundary was altered or bypassed. Ticket blocked pending
  owner supersession/recertification authorization.
- 2026-08-21: The owner selected “Re-certify CLI” after disclosure that this
  retains the exact safety gate and requires the governed 65-case catalog/model
  read with zero content queries and zero writes. Decision
  `.10x/decisions/buoy-recertifies-routing-cli-for-command-telemetry.md`
  records the choice, alternatives, exact effects, and stop conditions. Ticket
  reactivated for final source completion under the collect-only dormant phase;
  independent report audit remains mandatory before artifact reactivation.
- 2026-08-21: Final dormant source now implements the entry/bootstrap command
  boundary, exact v2 producer conversion, nested live pipeline, all governed
  CLI stages/error categories, preview null-pipeline behavior, direct-v1
  compatibility, privacy/failure isolation, documentation, and deterministic
  acceptance tests. The exact certified collect artifact was restored. Focused
  suites passed 199 tests/197 subtests on Python 3.11 and 3.13; established
  suites passed 240/200; filtered full suites passed 1060/979 on both; compile,
  lock, Ruff, ranking, diff, and isolated wheel lifecycle passed. Evidence:
  `.10x/evidence/2026-08-21-retrieve-command-pipeline-telemetry.md`.
  Production source is ready for one clean dormant commit and MUST NOT change
  after that commit. The next authorized action is only the exact source-only
  65-case collector, followed by the mandatory independent report-audit stop.
