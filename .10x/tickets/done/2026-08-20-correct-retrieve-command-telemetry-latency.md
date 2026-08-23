Status: done
Created: 2026-08-20
Updated: 2026-08-23
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

1. `.10x/tickets/done/2026-08-20-implement-local-telemetry-v2-storage-migration.md`
   implements the envelope/inbox/store/status/flush/migrate substrate using
   deterministic fixture traces. It is the first dependency and owns no CLI
   retrieval instrumentation.
2. `.10x/tickets/done/2026-08-20-instrument-retrieve-command-pipeline-latency.md`
   depends on child 1 and wires entry-point, CLI-stage, and nested pipeline
   traces into that substrate. Because the CLI is an active routing receipt,
   this child also locally recertifies the final CLI hash under the newer
   provisional-routing policy, with package-byte and independent review gates
   and no routing semantic or live catalog change.
3. `.10x/tickets/done/2026-08-20-validate-retrieve-command-telemetry-v2.md`
   depends on both implementation children and owns independent end-to-end
   acceptance, migration rehearsal, documentation reconciliation, and final
   review input.

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
- The active bounded-routing artifact owns exact CLI source authority; final
  instrumented bytes must pass the unchanged dormant-report and measured-
  receipt protocol before automatic routing is accepted.

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

Plan/apply/crawl/eval/catalog telemetry, ranking/evidence/routing semantic
changes, query or argv collection, Collector/OTLP export, automatic migration,
automatic backup deletion, installed-tool replacement, release/publication,
and further live provider/catalog validation are outside this plan. The
stopped stable catalog read is historical evidence and authorizes no retry or
card repair.

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
- 2026-08-20: Storage/migration candidate `0989690` passed its worker-reported
  focused suites but failed three independent reviews and parent inspection.
  Child 1 remained active for the bounded repair set recorded in
  `.10x/reviews/2026-08-20-local-telemetry-v2-storage-migration-review.md`;
  dependent command instrumentation did not start.
- 2026-08-20: Repair candidate `80d7562` materially resolved most first-review
  findings and passed expanded worker validation, but three fresh reviewers
  again returned FAIL. Child 1 remained active for the narrower exact-state
  repair in
  `.10x/reviews/2026-08-20-local-telemetry-v2-storage-migration-rereview.md`;
  dependent instrumentation remained blocked.
- 2026-08-20: Candidate `bbc1cbc` repaired that complete set and passed further
  worker validation, but fresh review found a receipt-recovery blocker and five
  narrower adjacent gaps. Child 1 remained active under
  `.10x/reviews/2026-08-20-local-telemetry-v2-storage-migration-final-review.md`;
  instrumentation stayed blocked.
- 2026-08-21: Candidate `18b3a56` repaired those findings; acceptance review
  verified them and found only one remaining moderate queue-authority gap in
  final `pending_v2` reporting. Candidate `2c7e5ed` closed that runtime gap;
  review then isolated one synchronization gap in its deterministic test.
- 2026-08-21: Candidate `3119375` observes actual failed nonblocking `flock`
  contention before producer release and preserves the real rename/retry/scan
  sequence. Fresh exact-commit review returned PASS with no findings. Child 1
  is closed at
  `.10x/tickets/done/2026-08-20-implement-local-telemetry-v2-storage-migration.md`;
  Child 2 command/pipeline instrumentation is now unblocked.
- 2026-08-21: Child 2 inspection exposed one undefined command-summary value.
  The owner ratified `exit_code=1` when an exception escapes retrieve without a
  handler return; the original exception must still escape unchanged. The
  active command telemetry spec now records this exact semantic.
- 2026-08-21: The first command producer candidate correctly tripped automatic
  routing's exact CLI-source receipt. The owner first selected the disclosed
  live dormant-certification path; its stable catalog read stopped before
  inference on the known missing Aurelio docs card, with zero writes/content
  calls and no report.
- 2026-08-21: Reconciliation found the newer active provisional-routing policy
  explicitly makes missing cards diagnostic rather than a global stop and
  provides precedent for local source-receipt revision while preserving the
  frozen anchor. The owner selected local CLI receipt recertification and no
  card backfill. Current authority is
  `.10x/decisions/buoy-recertifies-final-reviewed-cli-receipt.md`.
- 2026-08-22: Candidate `40ef5f74` locally reactivated the exact schema-v3
  artifact with only the final CLI receipt changed and passed worker-reported
  dual-runtime/full/package validation. Three fresh reviews nevertheless
  returned FAIL for independent writer graph/exit validation, one broken-
  stderr regression, and incomplete deterministic scenario/privacy/failure
  evidence. Child 2 remained active under
  `.10x/reviews/2026-08-22-retrieve-command-pipeline-telemetry-review.md`.
- 2026-08-22: First repair candidate `d8e0008c` closed most review findings and
  retained exact one-field routing receipt compatibility, but fresh rereview
  found command-success/error-pipeline inconsistency, missing controlled
  routing-delay coverage, missing filename privacy scans, and non-durable
  exact-commit package evidence. Child 2 remained active under
  `.10x/reviews/2026-08-22-retrieve-command-pipeline-telemetry-rereview.md`.
- 2026-08-22: Second repair implementation `5945b047` closed those rereview
  findings and added clean exact-commit package records, but final review found
  one truthful weak-evidence widening graph rejected, namespace count/rank
  disagreement accepted, and delayed subprocesses lacking zero-delay baselines.
  Child 2 remained active under
  `.10x/reviews/2026-08-22-retrieve-command-pipeline-telemetry-final-review.md`.
- 2026-08-23: Implementation `d4c336c8` closed those findings and passed parent
  exact package reproduction, but acceptance review found automatic pipeline
  graphs can omit mandatory routing and failed/out-of-order prerequisites can
  persist. Prior cardinality/timing/privacy/package findings were accepted.
  Child 2 remained active under
  `.10x/reviews/2026-08-23-retrieve-command-pipeline-telemetry-acceptance-review.md`.
- 2026-08-23: Final child-2 implementation `6bfd0d4c`, tree `26931097`, passed
  source-reachability and final acceptance review, dual-runtime filtered full
  suites, static/ranking checks, and parent exact source/wheel/sdist/install
  reproduction. Child 2 is closed; child 3 integrated validation and its
  parent-observed five-run reference-host timing gate are now unblocked.
- 2026-08-23: Child 3 completed integrated migration/privacy/no-network,
  documentation/help/SQL, package, dual-runtime, and reference-host timing
  validation. Its first closure review found missing controlled bootstrap and
  pipeline delay comparisons; test-only commit `7eb6b393` repaired that literal
  gap without changing production source. Two fresh independent rereviews
  passed with no findings. All three child tickets are done.
- 2026-08-23: Fresh aggregate closure review mapped every parent criterion to
  durable evidence, checked specification and graph coherence, and returned
  PASS with no findings. The verdict is
  `.10x/reviews/2026-08-23-retrieve-command-telemetry-latency-parent-closure-review.md`.
  The parent outcome is complete.

## Retrospective

The original latency discrepancy was correctly isolated as an instrumentation-
boundary defect rather than an OpenTelemetry clock defect. Splitting storage,
command instrumentation, and integrated validation kept schema migration,
runtime behavior, and acceptance ownership distinct. Exact source-reachable
graph validation and repeated adversarial review prevented locally plausible
but impossible routing/evidence envelopes from becoming durable data.

The main execution mistakes were evidentiary rather than architectural:
concurrency intent was initially confused with observed lock contention, an
isolated privacy test inherited an unstated lazy model dependency, and fixed
fake-clock timing was initially treated as equivalent to controlled delay at
every named seam. Each was repaired at the narrowest boundary without weakening
specifications or altering unrelated runtime behavior.

Reusable lessons are preserved in:

- `.10x/knowledge/concurrency-tests-observe-real-lock-boundaries.md`;
- `.10x/knowledge/isolated-tests-own-lazy-model-dependencies.md`; and
- `.10x/knowledge/timing-attribution-tests-delay-each-named-seam.md`.

The active specifications still describe implemented behavior. All child
reviews and evidence are coherent, every residual limit is explicit, and the
separately owned stale dynamic-version collector remains at
`.10x/tickets/2026-08-20-reconcile-missing-release-checks-test-harness.md`.
No further telemetry implementation, specification, decision, skill, or
follow-up record is required.
