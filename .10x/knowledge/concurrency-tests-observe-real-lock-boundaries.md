Status: active
Created: 2026-08-21
Updated: 2026-08-21

# Concurrency Tests Must Observe Real Lock Boundaries

A signal emitted immediately before calling a lock API does not prove the call
was attempted or blocked. The signaling thread can be descheduled between the
signal and the lock operation, allowing a controller to release the competing
owner and produce scheduler-dependent ordering that looks correct.

For deterministic lock-contention tests:

- hold the real production lock in one actor;
- observe the contender at the lowest practical real boundary, such as a
  failed nonblocking `flock` acquisition;
- signal only after that real operation reports contention;
- preserve production retry semantics by re-raising or returning the real
  contention result;
- before releasing the owner, assert that acquisition and protected work have
  not occurred;
- observe the real publication or mutation after it succeeds, not merely the
  code path immediately before it; and
- assert the complete causal order from contention through owner mutation,
  contender acquisition, and protected observation.

A pre-call event may show intent, but it is not evidence of contention.
Repeated passing runs help detect flakiness; they do not repair an invalid
synchronization boundary.
