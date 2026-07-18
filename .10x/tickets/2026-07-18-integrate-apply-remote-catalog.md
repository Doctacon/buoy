Status: blocked
Created: 2026-07-18
Updated: 2026-07-18
Parent: .10x/tickets/2026-07-18-remote-semantic-routing-plan.md
Depends-On: .10x/tickets/2026-07-18-seed-remote-routing-catalog.md

# Integrate Approved Apply with Remote Catalog

## Scope

Implement `.10x/specs/approved-apply-remote-catalog-registration.md`: remote existing-card read/merge, revision-bound pending artifacts, content/state/card sequencing, conditional card commit, truthful partial success, remote reconcile, approved abandonment, and CLI/docs/tests. Remove local catalog commit behavior from apply while retaining local pending/applied state.

## Acceptance criteria

- Every sequencing, preservation, concurrency, replay, partial-success, reconciliation, and cleanup scenario in the spec is tested.
- Apply reads/writes only the reserved remote catalog for card operations and never `.buoy/catalog.json`.
- Content pipeline and compact applied-state semantics remain unchanged.
- Missing credentials/schema/card conflict fails at the specified phase without content writes or silent overwrite.
- No live Turbopuffer call occurs in tests or implementation validation.
- Focused/full/hosted checks, evidence, and independent review pass.

## Explicit exclusions

Retrieval cutover, local catalog file deletion, live apply/content writes, migration of additional cards, distributed locks, automatic conflict merge.

## References

- `.10x/specs/approved-apply-remote-catalog-registration.md`
- `.10x/specs/remote-turbopuffer-routing-catalog.md`

## Evidence expectations

Phase-order and credential sentinels, pending golden fixtures, concurrency/replay/failure injection, legacy plan/source compatibility, full/hosted checks, independent review.

## Blockers

Remote catalog implementation and seed dependencies.

## Progress and notes
