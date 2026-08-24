Status: done
Created: 2026-08-20
Updated: 2026-08-23
Parent: .10x/tickets/done/2026-08-20-correct-retrieve-command-telemetry-latency.md
Depends-On: .10x/tickets/done/2026-08-20-implement-local-telemetry-v2-storage-migration.md, .10x/tickets/done/2026-08-20-instrument-retrieve-command-pipeline-latency.md
Decision: .10x/decisions/buoy-records-command-and-pipeline-retrieve-latency.md
Specifications: .10x/specs/retrieve-command-telemetry.md, .10x/specs/local-telemetry-v2-storage-and-migration.md

# Validate Retrieve Command Telemetry V2

## Scope

Independently validate the integrated exact commit against both active focused
specifications. Produce parent-observed subprocess timing evidence, complete
migration/privacy/no-network evidence, reconcile public documentation and SQL,
and perform an adversarial review. This ticket may repair only defects that
block its specified acceptance; unrelated findings require separate ownership.

Validation uses isolated temporary homes, deterministic fake providers/models,
and built distributions. It must not read or migrate the owner's real
`~/.buoy`, access credentials, contact Turbopuffer, mutate namespaces/catalogs,
or replace the installed tool.

## Acceptance criteria

1. Re-read every material scenario and criterion in both focused specs and map
   each to a test or recorded bounded observation.
2. On the reference host, five warm controlled subprocesses with the specified
   two-second pre-pipeline delay satisfy median shell-minus-command <=250 ms
   and median command/shell >=95%; raw values, host, Python, package, order,
   and method are recorded.
3. Controlled delays independently prove bootstrap, routing, initialization,
   pipeline, and rendering attribution without summing nested spans.
4. A fixture schema-v1 database with v1 queue work migrates through the built
   console command; exact backup identity, v1 query equivalence, v2 schema/view
   identities, pending-v2 recovery, and idempotent rerun are proven.
5. Crash/fault, hostile-path/schema, replay/conflict, status/flush/migrate,
   privacy, context-isolation, zero-network, and no-provider management paths
   pass at the integrated commit.
6. Existing retrieval/CLI output and call-count suites pass with telemetry
   disabled and forcibly enabled; direct library v1 compatibility passes.
7. Full Python 3.11 and 3.13 tests, lock, source/ranking validators,
   compilation, distribution inspection, clean-wheel console lifecycle, and
   diff hygiene pass as applicable to the repository.
8. `docs/telemetry.md`, README, changelog, status/migrate help, and SQL examples
   distinguish command from pipeline duration, explain enabled preview
   observations and explicit migration, retain privacy wording, and make no
   exact-shell claim.
9. An independent review record has verdict pass, or every concern is repaired
   and re-reviewed. Residual limitations are explicit.

## Evidence expectations

Create one integrated evidence record containing exact commit/tree, changed
paths, all commands/results, raw subprocess durations, schema/view/backup
identities, migration counts, privacy/no-network findings, distribution facts,
and limits. Create a separate adversarial review record targeting the exact
commit.

## Explicit exclusions

No live provider/model download/credential/namespace/catalog operation, real
telemetry migration, installed-tool replacement, release/publication, `main`,
automatic migration, backup deletion, or out-of-scope product fix.

## Blockers

None. All nine criteria are supported by durable evidence, and two fresh
independent rereviews passed with no findings.

## Progress and notes

- 2026-08-20: Opened as the final dependent acceptance unit. No validation or
  repair begins before both implementation dependencies complete.
- 2026-08-23: Storage/migration and command/pipeline instrumentation dependencies
  are closed. Exact command implementation `6bfd0d4c` passed final review and
  package acceptance; this integrated validation ticket is unblocked.
- 2026-08-23: Activated for independent integrated validation. A validation
  worker owns the spec/evidence/documentation/migration/adversarial matrix; the
  parent retains the explicitly parent-observed five-run reference-host timing
  measurement and final evidence/closure reconciliation.
- 2026-08-23: Fresh isolated/offline integrated validation passed 212 tests and
  289 subtests, including controlled attribution, command compatibility,
  storage/migration fault, privacy/context, no-network, management, replay, and
  direct-v1 matrices. Exact parent package hashes were independently verified
  before the accepted wheel was used for a console migration rehearsal: two v1
  rows remained query-equivalent in the immutable v1 backup and v2 canonical
  store, pending-v2 was 1 at migration, flush committed it once, exact view
  identities matched, and the already-current rerun preserved backup and
  canonical hashes.
- 2026-08-23: Independent criterion-8 inspection found README and Unreleased
  changelog omissions. Bounded documentation-only commit `c9f0f44` now states
  separate near-shell command/pipeline durations, enabled-preview observation,
  explicit migration, and the privacy boundary. Detailed docs, installed help,
  status/migrate text, and all SQL examples passed inspection/execution.
  Integrated evidence is
  `.10x/evidence/2026-08-23-retrieve-command-telemetry-v2-validation.md`.
- 2026-08-23: The parent ran one discarded warm-up and five ordered two-second
  initialization-delay subprocesses from the accepted wheel. Median shell minus
  command was 117.155667 ms and median command/shell was
  0.9500946372682385, passing criterion 2 without rounding. A clean exact build
  of documentation commit `c9f0f44` also proved repaired README/changelog wheel
  metadata and sdist content while preserving runtime hashes and disabled
  installed-preview behavior.
- 2026-08-23: Parallel fresh review produced one PASS and one controlling FAIL.
  The FAIL found that controlled delay comparisons cover initialization,
  routing, and rendering but not bootstrap or pipeline; fixed fake-clock
  assertions do not satisfy criterion 3's delay requirement. The composite
  review is
  `.10x/reviews/2026-08-23-retrieve-command-telemetry-v2-integrated-review.md`.
  Ticket remains active for that bounded test/evidence repair and fresh
  rereview; no production runtime defect is currently indicated.
- 2026-08-23: Test-only commit `7eb6b393` repaired criterion 3 without changing
  production runtime. Five consecutive focused runs, the fresh 212-test/289-
  subtest integrated suite, and filtered 1,073-test/1,071-subtest full suites
  on Python 3.11 and 3.13 passed. Exact-commit raw baseline-versus-500 ms values
  now prove bootstrap increases command and bootstrap-span duration without
  increasing pipeline duration, while pipeline delay increases both
  authoritative command and pipeline durations. A clean detached offline build
  and isolated install preserved runtime/routing hashes, repaired packaged
  documentation, provider/model-free disabled preview, and no `.buoy` creation.
  Integrated evidence was appended. The parent independently reran the repaired
  focused test once in a fresh isolated Python 3.11 environment; it passed.
- 2026-08-23: Two fresh independent rereviews recalculated the controlled-delay
  and reference-host timing arithmetic, inspected the exact test/package
  provenance, and rechecked all nine criteria. Both returned PASS with no
  findings. The durable verdict is
  `.10x/reviews/2026-08-23-retrieve-command-telemetry-v2-integrated-rereview.md`.
  Every acceptance criterion maps to
  `.10x/evidence/2026-08-23-retrieve-command-telemetry-v2-validation.md`; the
  ticket is complete.

## Retrospective

The first integrated review exposed an evidence-category mistake: fixed
fake-clock timestamps proved bootstrap and pipeline boundaries, but did not
satisfy a criterion requiring controlled baseline-versus-delay observations at
every named seam. Treating adjacent delay coverage as sufficient would have
closed a literal acceptance gap despite correct production runtime behavior.

The bounded repair kept production bytes immutable, added real delays only to a
provider/model-free test fixture, consumed authoritative command and pipeline
columns directly, and rebuilt the exact test target because changed tests and
fixtures are source-distribution content. Independent raw-value recalculation,
five repeated worker runs, one parent run, dual-runtime full suites, and two
fresh PASS rereviews removed the blocker without broadening product scope.

Reusable timing-test procedure is preserved in
`.10x/knowledge/timing-attribution-tests-delay-each-named-seam.md`. The
separately owned stale dynamic-version collector remains outside this ticket at
`.10x/tickets/done/2026-08-20-reconcile-missing-release-checks-test-harness.md`.
No additional implementation, specification, decision, skill, or follow-up
record is required.
