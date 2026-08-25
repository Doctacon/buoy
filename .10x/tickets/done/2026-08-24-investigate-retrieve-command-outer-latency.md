Status: done
Created: 2026-08-24
Updated: 2026-08-24
Parent: .10x/tickets/2026-08-24-improve-retrieval-telemetry-actionability.md
Depends-On: .10x/tickets/done/2026-08-24-install-v0-6-3-and-run-telemetry-pilot.md
Evidence: .10x/evidence/2026-08-24-v0-6-3-installed-telemetry-pilot.md
Review: .10x/reviews/2026-08-24-v0-6-3-installed-telemetry-pilot-review.md, .10x/reviews/2026-08-24-retrieve-command-outer-latency-attribution-review.md
Research: .10x/research/2026-08-24-retrieve-command-outer-latency-attribution.md
Follow-Up: .10x/tickets/2026-08-24-measure-provider-free-retriever-construction.md

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

None. The read-only attribution and independent review satisfy every criterion.
The provider-free construction probe is distinct unfinished work owned by
`.10x/tickets/2026-08-24-measure-provider-free-retriever-construction.md` and
remains blocked pending separate owner ratification.

## Progress and notes

- 2026-08-24: Opened from the independently reviewed installed-release pilot so
  the material outside-pipeline latency finding has a durable owner. No further
  performance experiment or optimization is authorized.
- 2026-08-24: The owner prioritized and directed this investigation first.
  Activated for source and existing-store read-only attribution only; no new
  command sample, provider access, telemetry mutation, or optimization is
  authorized.
- 2026-08-24: Read-only analysis of all seven retained command-v2 rows found
  that `buoy.retrieve.prepare` explains 96.18%–99.27% of measured live command
  time outside the pipeline. Direct-root interval-union residual is only
  22.064–48.295 ms. Automatic preparation is further attributable to routing-
  model construction and catalog reading; explicit preparation lacks a child
  boundary separating model load from client/config construction. Research is
  recorded at
  `.10x/research/2026-08-24-retrieve-command-outer-latency-attribution.md`.
  No additional live campaign is recommended before a separately authorized
  provider-free attribution probe. Ticket remains active for independent
  review.
- 2026-08-24: Independent review of exact candidate
  `8fe2b06ed907460c2858f6e3779bc29e56c657ef` returned PASS with no critical or
  significant findings. It confirmed interval-union arithmetic, source and
  store-schema attribution, privacy, measured/unmeasured separation, limits,
  and all five acceptance criteria. Review is recorded at
  `.10x/reviews/2026-08-24-retrieve-command-outer-latency-attribution-review.md`.
- 2026-08-24: Opened the separately blocked provider-free construction probe
  owner, closed this investigation, and released child 2 of the parent plan for
  source-only shaping. No model/cache operation, new retrieval, provider call,
  telemetry mutation, optimization, or live campaign is authorized.

## Retrospective

- Direct-root interval unions gave truthful coverage without double-counting
  nested stages; the 22–48 ms residual rules out missing in-root telemetry as
  the multi-second gap.
- Existing command telemetry was sufficient to locate the dominant boundary:
  prepare explains 96.18%–99.27% of command-minus-pipeline time.
- Automatic preparation is actionable at current granularity, while explicit
  preparation needs one provider-free model/client construction boundary before
  an optimization can be justified.
- Repeating the ordered live workload would preserve mode/cache confounding and
  add provider effects without resolving the question, so no live rerun was
  opened.
