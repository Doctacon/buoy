Status: active
Date: 2026-08-15
Ticket: .10x/tickets/2026-08-15-migrate-routing-catalog-v2-and-examples.md

# Routing Catalog V2 Migration Is Reader-First and Revision-Bound

## Decision

Deploy the exact v1/v2-compatible reader before changing the one shared routing
catalog. Migrate only by adding the four governed nonfilterable attributes in
one schema-only request. Existing rows remain provider-null for those fields
and the v2 reader reconstructs their complete empty-example projection from
the unchanged base projection. Partial prototype state is invalid.

Every live operation is preview-first and optimistic-concurrency-bound. The
schema migration binds the full snapshot revision and vector-inclusive catalog
projection; an example update binds the exact card revision. Approval repeats
the strong read and stops on any difference. No raw SDK mutation or complete
card upsert is an approved operational substitute.

Production routing continues to use the legacy base vector until a separate
quality/activation ticket passes. V2 storage capability is not routing
activation.

## Consequences

- Old exact-v1 readers must not remain deployed when the schema changes because
  they correctly reject v2.
- The additive schema change is not rolled back by deleting attributes. A
  provider failure after the schema request is handled by a fresh exact read;
  exact v2 is idempotent, while every other state fails closed.
- Reviewed examples affect only the separate prototype projection. Their edit
  cannot alter the base projection or unrelated card authority.
- Reviewed examples are operator-owned independently of whether base card
  semantics are manual or generated. A normal apply preserves them while
  refreshing its already-authorized source, retrieval, and lineage fields;
  automated source generation cannot create or clear them.
- Schema and example operations remain separately reviewable, attributable,
  and bounded to one provider request each.
