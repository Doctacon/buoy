Status: open
Created: 2026-07-18
Updated: 2026-07-18
Parent: .10x/tickets/2026-07-18-remote-semantic-routing-plan.md
Depends-On: None

# Build Remote Routing Catalog

## Scope

Implement `.10x/specs/remote-turbopuffer-routing-catalog.md`: exact schema/card serializer, deterministic hashed IDs, paginated namespace/card reads, validation/intersection diagnostics, optimistic conditional mutations, and authenticated remote `buoy catalog` CLI. Keep existing retrieval/apply local integration temporarily so migration and later children can proceed safely; do not delete the local file/module yet.

The final remote CLI replaces local catalog path behavior. Add injected SDK fakes and complete tests for pagination, schema/card corruption, collisions, optimistic conflicts, redaction, permissions/errors, and cross-directory behavior.

## Acceptance criteria

- Remote catalog primitives and CLI satisfy every spec scenario.
- `--catalog`/`BUOY_CATALOG_PATH` are rejected/removed for catalog CLI while existing retrieval/apply code remains temporarily isolated on local internals.
- Reads never write; mutations are conditional and revalidated.
- No live Turbopuffer call occurs in tests.
- Focused/full tests, compilation, docs, diff, CI, evidence, and independent review pass.

## Explicit exclusions

Live catalog creation/migration, apply cutover, retrieval cutover, local file deletion, content namespace mutation, ID fallback, unrelated cleanup.

## References

- `.10x/specs/remote-turbopuffer-routing-catalog.md`
- `.10x/research/2026-07-18-turbopuffer-remote-routing-catalog.md`

## Evidence expectations

Schema golden fixtures, pagination/collision/conditional-write tests, CLI credential/side-effect sentinels, cross-directory fakes, full/hosted checks, and independent review.

## Blockers

None.

## Progress and notes
