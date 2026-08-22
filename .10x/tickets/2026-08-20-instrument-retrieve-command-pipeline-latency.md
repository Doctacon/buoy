Status: active
Created: 2026-08-20
Updated: 2026-08-22
Parent: .10x/tickets/2026-08-20-correct-retrieve-command-telemetry-latency.md
Depends-On: .10x/tickets/done/2026-08-20-implement-local-telemetry-v2-storage-migration.md
Decision: .10x/decisions/buoy-records-command-and-pipeline-retrieve-latency.md
Specification: .10x/specs/retrieve-command-telemetry.md
Storage: .10x/specs/local-telemetry-v2-storage-and-migration.md
Routing-Decision: .10x/decisions/buoy-recertifies-final-reviewed-cli-receipt.md
Routing-Specification: .10x/specs/automatic-routing-after-apply.md

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
owns local recertification of only the final CLI receipt under the existing
schema-v3 provisional-routing policy. It owns no routing semantic or live
catalog change.

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
- Restore the exact schema-v3 active artifact while changing only its measured
  `cli_module_sha256`; preserve every other semantic and receipt exactly.
- Prove source/wheel/sdist/installed bytes, automatic behavior, and strict
  rejection/acceptance reproduce the new receipt under independent review.

## Acceptance criteria

1. Scenarios 1-9 and 11 plus scenario 10's exact fake-clock and controlled-
   delay implementation tests pass here. The dependent validation ticket owns
   scenario 10's five-run parent-observed reference-host measurement and final
   external shell representativeness claim before parent closure.
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
7. Fake-clock tests prove exact start/end and delay-attribution semantics;
   controlled delayed subprocess seams are implemented for the child validation
   ticket without live provider work.
8. Existing CLI, routing, retrieval, evidence, telemetry, full-suite,
   compilation, distribution, clean-wheel, and diff checks pass.
9. The exact final instrumented CLI receipt is the sole active-artifact field
   changed; source/wheel/sdist/installed bytes reproduce it, every frozen
   anchor/provisional-routing value remains exact, and independent review finds
   no routing-semantic change.

## Evidence expectations

Record exact changed boundaries, trace graphs for each mode/outcome, enabled
and disabled output/call equivalence, privacy scan, focused/full commands and
results, and any residual timing limitation. Also record dormant/final
commit/tree identities, stopped-collector facts, before/after artifact hashes,
exact source/package receipts, non-CLI field equality, no-mutation audit, and
independent final review. Do not claim external shell representativeness until
the dependent validation ticket observes it.

## Explicit exclusions

No plan/apply/crawl/eval/catalog telemetry, schema redesign beyond the active
storage spec, provider/catalog/content query or mutation, query/argv collection,
Collector/OTLP export, ranking/evidence/routing semantic changes, installed-
tool replacement, release, `main`, or publication. The stopped complete-
catalog read is historical evidence; no further live run is authorized.

## Assumption provenance

- Trace scope and all retrieve modes are user-ratified.
- Existing pipeline semantics and private context behavior are record/source-
  backed.
- Exact shell identity is explicitly not claimed; the specified near-shell
  boundary is user-ratified and research-backed.

## Blockers

The final-review source/test findings are repaired at immutable implementation
`d4c336c8`, tree `08863bae`. Fresh independent exact-commit review and parent-
observed offline wheel/sdist/archive/isolated-install reproduction remain
required before closure. The dependent ticket still owns the separate five-run
reference-host timing gate.

No live card repair, report, or further provider run is required or authorized.

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
  `.10x/decisions/superseded/buoy-recertifies-routing-cli-for-command-telemetry.md`
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
- 2026-08-21: Final production source and exact collect artifact committed clean
  at `369c5d461f616e89df492b497175312f36b5dcc9`, tree
  `ba5c3933d835e5b9d2c7f3664f4847721e880c78`. The authorized collector then
  stopped on complete-catalog drift before any of 65 query/reranker inferences
  and before report publication: live namespace `site-docs-aurelio-ai-v1` has
  no matching card. No content/provider write, content query/resource, model
  download, artifact change, or source change occurred. Evidence and private
  log identity are recorded at
  `.10x/evidence/2026-08-21-retrieve-command-pipeline-telemetry.md`. No report
  exists and none is claimed.
- 2026-08-21: Inspection reconciled the stop against the newer active
  provisional-routing decision/spec: missing cards are diagnostics, not a
  global routing stop, and the schema-v3 artifact already supports local source
  receipt revision while preserving the frozen certified anchor. The owner
  selected local CLI receipt recertification and rejected implicit card
  backfill. Decision
  `.10x/decisions/superseded/buoy-recertifies-routing-cli-receipt-under-provisional-policy.md`
  supersedes the inapplicable full-live-report path. Ticket reactivated for the
  one-field artifact update, package/behavior validation, and final review.
- 2026-08-22: Reactivated the exact schema-v3 artifact with only
  `receipts.cli_module_sha256` changed to measured final CLI hash `6a92ec38...`;
  parsed equality proves every other field identical to pre-instrumentation
  authority. The new artifact hash is `c66d0beb...`; old receipt rejection and
  new receipt acceptance passed. Combined focused suites passed 417 tests/374
  subtests and filtered full suites passed 1060 tests/979 subtests on both
  Python 3.11 and 3.13. Offline lock/compile/Ruff/ranking/diff, source equality,
  wheel/sdist byte agreement, and isolated installed-wheel authority/preview
  checks passed. No production Python byte changed after dormant `369c5d4` and
  no external/provider operation occurred. Evidence is additive at
  `.10x/evidence/2026-08-21-retrieve-command-pipeline-telemetry.md`; ticket
  remained active for independent exact-commit review.
- 2026-08-22: Three fresh reviewers returned FAIL for exact commit `40ef5f74`.
  Routing receipt compatibility and the core command/pipeline architecture were
  accepted, but writer validation admits impossible graphs and error+zero,
  broken stderr regressed for caught runtime configuration failures, and the
  scenario/privacy/failure evidence matrix is incomplete. The complete bounded
  repair set and timing-phase allocation are recorded at
  `.10x/reviews/2026-08-22-retrieve-command-pipeline-telemetry-review.md`.
- 2026-08-22: Bounded review repairs now independently reject impossible v2
  graphs and error-plus-zero before writer mutation, restore broken-stderr
  result behavior, contain private exporter diagnostics, and expand exact
  graph/timing/equivalence/failure/privacy coverage through real isolated
  queue/writer/store seams. Dual-runtime focused suites passed 403 tests each;
  filtered full suites passed 1068 each; lock, compilation, Ruff, ranking,
  one-field artifact, old/new receipt, source/wheel/sdist/install, and disabled
  installed-preview checks passed. Final CLI/artifact hashes are `90e7b2dd...`
  and `62ec1fe8...`. Additive evidence is at
  `.10x/evidence/2026-08-21-retrieve-command-pipeline-telemetry.md`. Ticket
  remained active for fresh independent exact-commit review; the dependent
  validation ticket still owns the five-run parent-observed timing gate.
- 2026-08-22: Fresh rereview of exact commit `d8e0008c` returned FAIL. Accepted
  remaining gaps are command-success/error-pipeline inconsistency, missing
  controlled routing-delay subprocess coverage, filename/path privacy scans,
  and durable parent-observed exact-commit package evidence. Most first-round
  repairs passed static adversarial inspection. The second bounded repair set
  is `.10x/reviews/2026-08-22-retrieve-command-pipeline-telemetry-rereview.md`.
- 2026-08-22: Immutable implementation `5945b047`, tree `c38e5cd2`, closes the
  three rereview findings: success plus error pipeline is rejected before writer
  mutation; the local-only subprocess probe includes automatic routing delay;
  and the real privacy path scans every observed relative name/component.
  Focused suites passed 404 tests/370 subtests and filtered full suites passed
  1069 tests/1017 subtests on both Python 3.11 and 3.13. Clean exact-commit
  offline package evidence is recorded additively. Parent independently reran
  the four repaired tests, which passed in 52.28 seconds.
- 2026-08-22: Fresh final review of `5945b047` returned FAIL. The decoder rejects
  truthful two-assessment weak-evidence widening, accepts namespace count/rank
  disagreement, and the subprocess test does not compare delayed observations
  to zero-delay baselines. Worker package evidence is durable but still requires
  parent reproduction after final repair. Findings are bounded at
  `.10x/reviews/2026-08-22-retrieve-command-pipeline-telemetry-final-review.md`;
  the separate five-run reference-host gate remains with the dependent ticket.
- 2026-08-22: Immutable implementation `d4c336c8`, tree `08863bae`, repairs the
  final source/test findings. Independent validation now accepts the truthful
  automatic two-assessment `weak_top1` widening graph, enforces exact namespace
  count/ranks and source-backed rerank/evidence cardinalities, and rejects the
  same malformed envelopes before writer mutation. The real automatic CLI
  regression performs three local namespace calls, one rerank, two assessments,
  widening, publication, and decoding. Controlled initialization/routing/render
  subprocesses compare zero to 500 ms delay; observed command deltas were
  510.064/506.673/509.487 ms while pipeline deltas were at most 0.975 ms.
  Fifteen affected modules passed 411 tests/383 subtests and the filtered full
  suite passed 1071 tests/1031 subtests on both Python 3.11 and 3.13; offline
  lock, compile, changed-file Ruff, ranking, and diff checks passed. CLI and
  routing artifact hashes remain `90e7b2dd...` and `62ec1fe8...`. Additive
  evidence is in `.10x/evidence/2026-08-21-retrieve-command-pipeline-telemetry.md`.
  Ticket remains active for parent package reproduction and fresh review.
