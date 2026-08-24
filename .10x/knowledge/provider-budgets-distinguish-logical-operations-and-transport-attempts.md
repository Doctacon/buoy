Status: active
Created: 2026-08-24
Updated: 2026-08-24

# Provider Budgets Distinguish Logical Operations and Transport Attempts

## Purpose

Provider-facing work has two different count units. Treating them as equivalent
can make a correct logical trace unable to prove cost, retry, or rate-limit
bounds.

## Definitions

- **Logical namespace operation:** one application-level retrieval operation for
  one namespace. In retrieve-command telemetry v2, one
  `buoy.namespace.query` span represents this unit.
- **Physical transport attempt:** one lower-level provider request attempt.
  Initial calls, compatibility fallbacks, optional-schema fallbacks, retries,
  and hedged requests each count separately when they reach the provider
  boundary.

A logical operation may contain more than one physical transport attempt.

## Rules for future tickets and canaries

1. Name the budget unit explicitly. Use “logical namespace operations” for
   fanout/workload shape and “physical transport attempts” for cost, rate-limit,
   retry, or network-effect bounds.
2. Never use logical span cardinality as proof of physical attempts unless exact
   source and tests establish a one-to-one invariant for every reachable path.
3. If physical attempts are acceptance-critical, observe at the provider client
   boundary and retain a content-free count receipt before deleting temporary
   artifacts.
4. Count initial and fallback/retry attempts separately. Record only governed
   reason categories, never queries, namespaces, credentials, content, raw
   errors, URLs, or private paths.
5. Verify the evidence artifact and acceptance mapping before consuming or
   deleting the only source of call-count evidence.
6. A historical operation with only logical spans may establish workload shape
   but must report physical-attempt count as unknown.

## Application to the local telemetry-v2 canary

The completed canary recorded five logical namespace operations. Its physical
attempt count is unknown because compatibility fallback can occur inside one
span and no transport-boundary receipt was retained. The owner ratified logical
operations as that canary's budget unit; physical-attempt observability remains
separate future work.
