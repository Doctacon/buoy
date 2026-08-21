Status: open
Created: 2026-08-20
Updated: 2026-08-20
Parent: .10x/tickets/2026-08-20-correct-retrieve-command-telemetry-latency.md
Depends-On: .10x/tickets/done/2026-08-20-implement-local-telemetry-v2-storage-migration.md, .10x/tickets/2026-08-20-instrument-retrieve-command-pipeline-latency.md
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

Both implementation child tickets must be done with evidence and no unresolved
spec conflict.

## Progress and notes

- 2026-08-20: Opened as the final dependent acceptance unit. No validation or
  repair begins before both implementation dependencies complete.
