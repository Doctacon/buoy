Status: blocked
Created: 2026-07-18
Updated: 2026-07-18
Parent: .10x/tickets/2026-07-18-remote-semantic-routing-plan.md
Depends-On: .10x/tickets/2026-07-18-build-remote-routing-catalog.md

# Seed Remote Routing Catalog

## Scope

Using the integrated, reviewed remote catalog CLI:

- preflight exact account/region/live namespace inventory and absent/compatible reserved catalog state;
- create `buoy-routing-catalog-v1` with the exact schema if absent;
- migrate the two byte/hash-validated local cards for `site-oscilar-com-v1` and `site-dagster-io-benchmark-v1` with conditional create semantics;
- verify remote re-read, vectors/hashes/revisions, live intersection, and missing-card classification for `site-dagster-io-v1` and `site-www-thistle-co-v1`;
- retain `.buoy/catalog.json` temporarily as rollback evidence until final retrieval cutover; do not mutate it;
- record every remote write/read and side-effect limit without secrets/vectors.

The user explicitly authorized these reserved-catalog writes on 2026-07-18.

## Acceptance criteria

- Exactly one reserved catalog namespace exists in `gcp-us-central1` with exact schema.
- Exactly two validated enabled cards are created and re-read identically.
- Actual live inventory intersection yields two routable and two missing-card exclusions; reserved namespace is excluded.
- No content namespace row/schema/state is queried beyond listing or mutated.
- No local catalog deletion occurs.
- Durable evidence and independent review pass.

## Explicit exclusions

Content retrieval/evals, content namespace writes/deletes, cards for unsupported live namespaces, local catalog deletion, apply/retrieval cutover, cross-region work.

## References

- `.10x/specs/remote-turbopuffer-routing-catalog.md`
- `.10x/evidence/2026-07-15-live-namespace-catalog-backfill.md`

## Evidence expectations

Preflight/live IDs, exact command shapes, remote catalog schema/metadata, affected-row counts, card revisions/hashes without vectors, intersection classifications, no-content-mutation attestation, independent review.

## Blockers

Remote catalog implementation dependency only.

## Progress and notes
