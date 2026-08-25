Status: blocked
Created: 2026-08-24
Updated: 2026-08-24
Parent: None
Depends-On: .10x/tickets/done/2026-08-24-investigate-retrieve-command-outer-latency.md
Research: .10x/research/2026-08-24-retrieve-command-outer-latency-attribution.md
Review: .10x/reviews/2026-08-24-retrieve-command-outer-latency-attribution-review.md

# Measure Provider-Free Retriever Construction

## Outcome

Separate local model import/construction time from provider-client, retriever,
and configuration construction inside explicit `buoy.retrieve.prepare`, using a
provider-free and content-free measurement design, before considering any
performance optimization.

## Context

Reviewed retained telemetry establishes that prepare owns 96.18%–99.27% of
measured live command time outside the pipeline. Explicit-mode telemetry stops
at one coarse retriever-construction boundary: 41.3–45.9 seconds for the two
single observations and 8.4–9.0 seconds for the two multi observations. Source
shows synchronous local model construction followed by namespace-client
construction, but retained evidence cannot assign those durations to one
component. Mode and campaign order are confounded.

## Candidate design requiring ratification

The reviewed research recommends a temporary test-only probe that would:

- use exact reviewed source, pinned local model assets, enforced offline
  settings, and a fake/injected provider client;
- measure sentence-transformer import, local model construction, and
  provider-client/retriever construction independently without summing nested
  intervals;
- run each observation in a fresh process while binding runtime, host, model,
  and cache-manifest identity;
- retain only content-free component timings; and
- prohibit provider/network access, model download, and cache mutation.

One discarded host warm-up followed by five ordered process-cold/host-warm
observations is a research recommendation, not an active acceptance criterion.
No cache-clearing or synthetic cold-host procedure is proposed.

## Acceptance criteria for shaping

Before this ticket may become executable:

- The owner explicitly authorizes local model construction and its cache/device
  effects, exact observation count/order, and temporary test-only harness.
- Exact offline, no-download, fake-provider, cache-integrity, privacy, cleanup,
  and raw-evidence rules are active and testable.
- The measurement identifies independent component intervals and does not infer
  total time by summing nested spans.
- The output is a research record with limits and a recommendation; it does not
  become optimization authority.
- Any later optimization has its own focused behavioral contract and bounded
  implementation ticket.

## Explicit exclusions

No model construction, cache effect, model download, provider/network call,
credential use, live retrieval, telemetry mutation, production instrumentation,
source/test change, performance target, optimization, release, or global-tool
operation is authorized by this blocked ticket.

## Blockers

- Local model execution and cache/device effects are not owner-ratified.
- Observation count/order and the temporary test-only probe shape are not
  owner-ratified.
- Exact retained raw-evidence and cleanup rules are not active.

## Progress and notes

- 2026-08-24: Opened from the independently reviewed outer-latency attribution
  as the durable owner for the unfinished explicit prepare sub-boundary. No
  provider-free probe or other operation has run.
