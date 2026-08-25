Status: recorded
Created: 2026-08-24
Updated: 2026-08-24
Target: .10x/tickets/done/2026-08-24-install-v0-6-3-and-run-telemetry-pilot.md, .10x/evidence/2026-08-24-v0-6-3-installed-telemetry-pilot.md, commit 084664c1c4c34400e768c840ff5c5bd8733ea5db
Verdict: pass

# V0.6.3 Installed Telemetry Pilot Review

## Target and method

Two independent reviewers (runs `476ab4ba-d2ba-4609-8e91-d9dd860572f0` and
`5ccb2ec9-b438-4878-8029-3d635e3dc264`) reviewed exact execution commit
`084664c1c4c34400e768c840ff5c5bd8733ea5db`, tree
`10f62f341f47282d2978600dcccd634fc06e96f5`, all governing records/specs,
preparation and execution evidence, exact source/tests, and records-only Git
diff. Neither reviewer reran installation, telemetry status/database queries,
retrieval, flush, provider/model, credential, or mutating operations.

The parent subsequently observed only the public version surface—global
`buoy 0.6.3` and uv-managed `buoy-search v0.6.3`—and clean Git/ref state. Parent
workflow-output artifacts were removed. No operational acceptance step was
repeated.

## Findings

### Installation and boundaries

One forward uv-tool replacement exited zero and installed the exact reviewed
`v0.6.3` candidate from tagged commit
`4c0a04a443ddf792db9089242bca4d1e141db03d`. Version, Python runtime, sole
entry point, installed source identities, dependencies, and uv provenance
matched. Immediate acceptance passed, so rollback correctly did not run.
Non-Buoy tools remained unchanged.

The real store passed its provider-access gate at compatible schema v2,
snapshot 16, empty queues, retained immutable backup, idle writer, and zero
recorded durability failures. Exact refs, release state, model cache, and
credential boundaries remained intact.

### Three-command telemetry result

Exactly three authorized live commands began once, in order, with no retry or
substitution. All exited zero and persisted exactly three new successful v2
command rows.

| Mode | Command ms | Pipeline ms | Outside pipeline ms | Pipeline share | Hits | Fanout | Failures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Explicit single | 47,845.827 | 1,572.189 | 46,273.638 | 3.3% | 5 | 1 | 0 |
| Explicit multi | 9,887.648 | 1,130.154 | 8,757.494 | 11.4% | 5 | 2 | 0 |
| Automatic | 11,067.981 | 874.174 | 10,193.807 | 7.9% | 5 | 2 | 0 |

All rows had nonnegative enclosed command/pipeline intervals, one governed
pipeline, source-reachable stage graphs, truthful success/zero exit, no
widening, and zero namespace failure. Automatic evidence was supported. Five
logical namespace spans remained below the maximum six. Physical transport
attempts remain explicitly unknown.

The installed release captured 88.6%–96.7% of observed command latency outside
the nested pipeline. The three samples are not a latency distribution, but they
consistently show that inner provider/retrieval pipeline time is not the dominant
near-shell latency on this host.

### Persistence, privacy, and cleanup

The sole flush returned `empty` because detached writers had already committed
the rows. Final snapshot and receipt counts were 19 with empty queues, idle
writer, 12 preserved v1 runs, byte-identical backup, and zero conflicts,
rejections, replays, write failures, or durability degradation.

Privacy validation checked 87 private literals, five changed telemetry
artifacts totaling 5,781,571 bytes, and 488 exact new-trace scalar values with
zero prohibited matches. The corrected binary check excluded only generic
values capable of coincidental DuckDB byte matches while retaining all values
in exact scalar checks; it required no operational rerun.

Temporary candidate, rollback, source, environment, raw-output, analysis, and
parent workflow-output artifacts were removed. The exact installed release,
three content-free rows, and immutable backup remain as authorized.

## Acceptance mapping

Every ticket criterion is supported: exact release/CI; safe candidate and
rollback preparation; one accepted replacement and zero rollback; compatible
real-store gate; three once-only successful commands; truthful telemetry and
logical-operation bound; one healthy flush; privacy; no provider writes/model
download/credential/ref/release/unrelated mutation; cleanup; and independent
review.

## Verdict

**PASS.** Exact released `v0.6.3` is installed globally, all three production-
style commands succeeded, telemetry persisted truthful private observations,
and terminal durability and side-effect boundaries passed. The ticket may
close through records-only reconciliation; no operational rerun is needed or
authorized.

## Residual risk

- Three observations do not establish a latency distribution. Investigation of
  the consistently dominant outside-pipeline time is owned by
  `.10x/tickets/2026-08-24-investigate-retrieve-command-outer-latency.md`.
- Physical transport-attempt count remains unknown and is owned by
  `.10x/tickets/2026-08-24-define-physical-provider-attempt-accounting.md`.
- Automatic catalog accounting remains source-bounded rather than packet-
  observed.
- This review grants no recurring collection, retention-policy change, provider
  operation, reinstall, rollback, or release action.
