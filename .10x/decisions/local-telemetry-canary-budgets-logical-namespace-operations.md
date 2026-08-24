Status: active
Created: 2026-08-24
Updated: 2026-08-24

# Local Telemetry Canary Budgets Logical Namespace Operations

## Context

The one-time local telemetry-v2 canary authorized at most six content-namespace
query calls across the live workload. The execution persisted five
`buoy.namespace.query` spans: one for explicit-single, two for explicit-multi,
and two for automatic retrieval.

Independent review correctly found that these spans do not prove the number of
lower-level provider transport attempts. Exact integrated source may make a
compatibility fallback attempt within one logical operation, and the telemetry
schema does not retain that attempt count. Review therefore treated the
six-call criterion as a physical-attempt ceiling and blocked closure.

The owner subsequently clarified the intended acceptance meaning in the current
workstream: assess this canary against at most six logical namespace operations,
treat the operational canary as passed, do not rerun it, and track physical
transport-attempt accounting separately for future work. Authorization evidence
is recorded at
`.10x/evidence/2026-08-24-local-telemetry-v2-canary-closure-authorization.md`.

## Decision

For `.10x/tickets/done/2026-08-24-run-local-telemetry-v2-canary.md`, the at-most-six
content-namespace limit means **logical namespace query operations**. One
`buoy.namespace.query` span represents one such operation. Lower-level initial,
compatibility-fallback, optional-schema-fallback, or retry transport attempts
within that operation are not this canary's budget or acceptance unit.

The five retained namespace spans therefore satisfy the ratified six-operation
limit. This decision does not claim, infer, or retroactively establish the
number of physical provider attempts. That separate observability gap is owned
by `.10x/tickets/2026-08-24-define-physical-provider-attempt-accounting.md`.

This is an acceptance clarification only. It grants no migration, retrieval,
flush, provider/model access, credential operation, global-tool change, release,
or other external operation. The original one-time execution authority remains
fully consumed and historical at
`.10x/decisions/superseded/one-time-local-telemetry-v2-canary.md`.

For future work, any cost, rate-limit, retry, or physical-network-request budget
must explicitly say **physical transport attempts** and must define evidence at
the transport boundary. A logical operation/span count must not be presented as
physical-attempt evidence.

## Alternatives considered

### Keep physical attempts as the canary criterion

Rejected by the owner for this closure. The original operational budget was
intended to bound logical namespace work, the exact canary cannot reconstruct
physical attempts, and the owner explicitly preferred closure plus separate
future accounting over a rerun.

### Rerun an instrumented canary

Rejected for this ticket. The one-time authority is consumed, the substantive
migration/telemetry behavior passed, and a rerun would add provider effects
without repairing the historical observation.

### Ignore the distinction

Rejected. Logical operations and physical attempts answer different questions.
Keeping the distinction explicit prevents future cost and rate-limit assertions
from relying on the wrong evidence.

## Consequences

The five observed logical namespace operations satisfy this canary's bounded
provider-read criterion, allowing fresh closure review without any operational
rerun. Historical FAIL reviews remain accurate under the prior physical-attempt
interpretation and are not rewritten; a new review must evaluate this explicit
owner-ratified contract.

Physical provider-attempt count remains unknown for the completed canary. The
separate blocked shaping ticket preserves that gap and must establish semantics,
privacy, evidence, and implementation scope before any code or new external
operation is authorized.
