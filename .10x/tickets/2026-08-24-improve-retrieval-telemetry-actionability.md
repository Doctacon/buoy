Status: active
Created: 2026-08-24
Updated: 2026-08-24
Parent: None
Depends-On: None

# Improve Retrieval Telemetry Actionability

## Aggregate outcome

Turn the completed `v0.6.3` production-style telemetry findings into two
truthful, bounded outcomes: explain the dominant command time outside the nested
pipeline, then define privacy-safe physical provider-attempt accounting so
future performance, cost, retry, and rate-limit decisions are evidence-backed.

## Child sequence

1. `.10x/tickets/2026-08-24-investigate-retrieve-command-outer-latency.md`
   performs read-only attribution from existing evidence first. Any new live
   measurement requires a separate owner checkpoint.
2. `.10x/tickets/2026-08-24-define-physical-provider-attempt-accounting.md`
   starts only after the latency investigation reaches a reviewed conclusion.
   It may inspect source and shape options, but product-surface, persistence,
   retention, and compatibility semantics remain blocked until explicitly
   ratified.

The children are sequential. Neither child grants provider/model operations,
telemetry mutation, implementation, migration, release, or global-tool change.

## Integration and coherence

- The latency child must distinguish measured stage time from unmeasured command
  residual and must not turn three production samples into a distribution.
- The attempt-accounting child must preserve the established distinction between
  logical namespace operations and physical client invocations.
- Findings, source authority, and unresolved choices must be durable before the
  next child advances.
- Any implementation outcome requires its own focused specification and bounded
  executable ticket after semantics are ratified.

## Aggregate acceptance criteria

- The first child has independently reviewed research that either attributes the
  existing latency gap or precisely defines the missing observation boundary.
- The second child presents a source-complete, privacy-safe semantic contract
  with explicit product-surface and retention choices; it becomes executable
  only after the owner ratifies those choices.
- No external operation or source mutation occurs under the parent plan.
- Child statuses, evidence/research, reviews, dependencies, and follow-ups are
  coherent at closure.

## Progress and notes

- 2026-08-24: The owner directed execution of the two existing tickets in the
  recommended order. This authorizes the first child's existing read-only
  analysis. It does not silently ratify new live samples or the second child's
  unresolved persistence/product-surface semantics.
- 2026-08-24: Child 1 produced a records-only research candidate from all seven
  retained command-v2 rows. The coarse gap is attributable to prepare; no new
  live measurement is recommended before provider-free sub-boundary
  attribution. Independent child review is pending before child 2 may start.

## Blockers

None for starting child 1. Parent completion depends on both children reaching
truthful terminal states.
