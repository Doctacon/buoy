Status: active
Created: 2026-08-24
Updated: 2026-08-24
Authorization: .10x/evidence/2026-08-24-provider-client-invocation-receipt-authorization.md
Accounting: .10x/specs/provider-client-invocation-accounting.md
Lifecycle: .10x/specs/provider-client-invocation-receipt.md
Review: .10x/reviews/2026-08-24-provider-client-invocation-contract-review.md

# Buoy Uses Private Canary Provider Invocation Receipts

## Context

Logical `buoy.namespace.query` spans prove one namespace operation but cannot
prove how many Buoy-to-SDK calls occur inside server-RRF compatibility or
optional-schema fallbacks. Automatic retrieval also performs a separate strong
catalog-read family. Reviewed source establishes a deterministic call-expression
boundary, while SDK-internal retries, physical HTTP sends, provider billing, and
rate-limit consumption remain unobservable.

Active telemetry v2 has an exact non-extensible envelope/store contract and no
retention policy for this data. The owner authorized a bounded evidence
mechanism for explicitly authorized canaries, not recurring production
telemetry or a public diagnostics surface. Exact authorization is recorded at
`.10x/evidence/2026-08-24-provider-client-invocation-receipt-authorization.md`.

## Decision

Buoy will count `provider_client_invocation`: one Buoy SDK call attempt,
incremented immediately before evaluating each governed SDK call expression.
A local signature rejection counts even if SDK method-body entry never occurs.
The unit excludes unknown SDK-internal retries and MUST NOT be described as a
wire send, provider cost, or rate-limit unit.

The first observation surface will be an explicitly entered private in-process
canary scope. It is default-off, context-local, non-public, and returns one
validated immutable sanitized terminal receipt to the authorized harness. It
adds no CLI or environment trigger, public API, automatic canary, automatic
disk write, telemetry-v2 field/span/envelope/store row, network export,
migration, or recurring retention.

The receipt keeps content and automatic-catalog families separate. Content
detail is route-rank-only; catalog detail is aggregate. Content uses fixed
request-form, fallback-trigger, outcome, and generic error categories. Catalog
uses fixed call categories and aggregate `success|error|interrupted` counts. A
successful complete catalog read validates through 40,001 calls; a terminal
error/interruption validates through 40,002 because the final second-list
continuation can return before the page-bound recheck fails. Those values are
validator reachability limits, never operational budgets.

An absent, incomplete, invalid, process-killed, or observer-failed receipt means
unknown. Observer setup, counting, propagation, finalization, validation, or
serialization failure MUST NOT alter SDK calls, retrieval behavior, original
results/exceptions, routing, output, or existing telemetry. Only canonical
validated receipt bytes bound to a known terminal canary result may be retained
indefinitely with durable evidence. The authorized harness deletes raw runtime
artifacts; production code neither writes the receipt nor changes recurring
retention/purge behavior.

The regeneration-grade contract is split into exactly two focused active
specifications:

- `.10x/specs/provider-client-invocation-accounting.md` owns the unit, governed
  content/catalog call boundaries, outcomes, privacy-safe categories,
  conditional bounds, and exact family shapes; and
- `.10x/specs/provider-client-invocation-receipt.md` owns private activation,
  nested/concurrent scope behavior, worker leases, finalization, receipt
  authority, canonical serialization/handoff, privacy, and retention.

## Source-backed private-scope mechanics

Implementation will follow established private telemetry conventions without
joining the products: one receipt-private `ContextVar`, explicit propagation of
only Buoy private state through the existing worker-callable seam, no general or
ambient context copy, a no-op nested activation that leaves the outer scope
authoritative, and best-effort failure isolation. A thread-safe ledger and
worker leases make finalization authoritative only when all begun operations,
propagated callbacks, and in-flight calls are terminal. Finalization does not
wait, retry, cancel, or infer.

Catalog observation is additionally capability-explicit. The shared
`read_remote_catalog` reader and its helpers receive a private observer argument
defaulting to `None` and never discover it from ambient receipt scope. Only the
automatic-retrieve CLI branch passes the active capability; apply, catalog
management, and direct callers remain unobserved. Final CLI wiring must follow
`.10x/decisions/buoy-recertifies-final-reviewed-cli-receipt.md`: preserve the
exact schema-v3 routing artifact and change only its final reviewed
`receipts.cli_module_sha256` value.

These are mechanical lifecycle rules needed to preserve the owner-approved
private/default-off semantics. They do not authorize a broader diagnostics,
telemetry, or persistence surface.

## Alternatives considered

### Recurring production telemetry

Rejected for the first surface. It would require a separately specified
compatible schema, storage/migration/retention behavior, and permanent product
maintenance. Active v2 is exact and non-extensible.

### Public provider diagnostics API or callback

Rejected. There is no ratified consumer beyond authorized canaries, and a
public callback would create lifecycle, compatibility, misuse, and privacy
obligations.

### SDK transport or packet boundary

Rejected for this contract. Those boundaries may prove wire sends but are
SDK-version-specific and carry credential, payload, interception, and
operational risk. Separate research and authorization are required if
wire/cost/rate-limit evidence becomes a requirement.

### Content-only or combined-family accounting

Rejected. Automatic retrieval performs a distinct bounded catalog read family.
Omitting it would leave canary provider activity incomplete; combining it with
content would make route fanout and catalog consistency work uninterpretable.

### Three family/lifecycle specifications

Rejected as unnecessary fragmentation. Content and catalog differ in detail
shape but share one unit, outcome model, privacy boundary, and instrumentation
contract, so one accounting spec keeps their required separation without
splitting common semantics. The private receipt lifecycle is independently
cohesive and reusable by both families, so it remains a second spec.

### Automatic persistence by production code

Rejected. Returning canonical bytes in process to the authorized harness is the
smallest delivery mechanism. Production persistence would add path, permission,
retention, and accidental enablement obligations with no approved recurring
consumer.

## Consequences

Canaries can retain content-free evidence of Buoy-issued SDK call attempts while
preserving logical-operation telemetry and existing behavior. The receipt can
represent content fallback attempts and aggregate automatic-catalog work, but
cannot support physical-transport, billing, or rate-limit claims.

The implementation must introduce a small private observer/validator surface
and instrument exact content/catalog call expressions plus the existing worker
propagation seam. Observer faults deliberately sacrifice receipt availability
rather than retrieval correctness. A missing receipt therefore cannot pass a
canary accounting gate.

There is no ordinary user enablement, automatic persistence, or production
retention change. Implementation remains gated by the focused specifications,
bounded child tickets, and independent review of this records-only contract
graph.
