Status: blocked
Created: 2026-08-24
Updated: 2026-08-24
Parent: None
Depends-On: .10x/tickets/done/2026-08-24-install-v0-6-3-and-run-telemetry-pilot.md
Evidence: .10x/evidence/2026-08-24-v0-6-3-installed-telemetry-pilot.md
Review: .10x/reviews/2026-08-24-v0-6-3-installed-telemetry-pilot-review.md

# Investigate Retrieve Command Outer Latency

## Outcome

Determine which command-level phases account for the large observed gap between
near-shell command duration and nested pipeline duration, distinguish cold-start
from steady-state behavior, and decide whether a bounded performance change is
warranted without weakening telemetry, routing, privacy, or model correctness.

## Context

The installed `v0.6.3` production-style pilot measured pipeline shares of only
3.3%, 11.4%, and 7.9% for explicit-single, explicit-multi, and automatic modes.
Outside-pipeline time was 46.3 s, 8.8 s, and 10.2 s respectively. The earlier
real-store canary showed the same broad shape, but neither three pilot rows nor
the combined small sample is a latency distribution.

## Scope

- Begin with read-only analysis of existing v2 command/stage rows; do not issue
  new retrievals merely to inspect retained data.
- Attribute elapsed time among bootstrap, preparation/retriever construction,
  automatic routing, rendering, ungoverned process boundaries, and known lazy
  model/runtime initialization.
- Separate first-process/cold-cache effects from warm repeated-command effects.
- If existing rows cannot answer the question, shape an explicit repeatable
  measurement campaign with sample count, workload identities, model/cache
  state, provider-read budget, raw timing evidence, and privacy/retention rules
  before any live command.
- Produce a research record with findings, uncertainty, and a recommendation.
  Open an implementation ticket only for a proven, bounded optimization.

## Acceptance criteria

- Existing content-free stage evidence is mapped without adding nested stage
  durations to estimate total command time.
- The analysis identifies measured and unmeasured portions of command duration
  and does not attribute residual time by assumption.
- Cold/warm state, host/runtime identity, mode, model/cache conditions, and
  sample limits are explicit.
- Any proposed additional campaign is separately user-ratified before provider,
  model, telemetry, or cache effects.
- Any optimization recommendation names the responsible boundary, expected
  benefit, preserved safety/behavior invariants, and independent verification
  path.

## Explicit exclusions

No code change, model change/download, provider access, retrieval rerun, cache
clear/warm mutation, telemetry purge/migration, release/global reinstall, or
performance target is authorized by this shaping ticket.

## Blockers

- The owner has not prioritized latency investigation or ratified further
  measurement effects/sample size.
- Existing retained stage rows have not yet been assessed for sufficient
  attribution coverage.

## Progress and notes

- 2026-08-24: Opened from the independently reviewed installed-release pilot so
  the material outside-pipeline latency finding has a durable owner. No further
  performance experiment or optimization is authorized.
