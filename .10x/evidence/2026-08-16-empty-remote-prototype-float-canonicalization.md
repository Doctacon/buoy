Status: provisional
Created: 2026-08-16
Updated: 2026-08-16
Ticket: .10x/tickets/2026-08-16-canonicalize-empty-remote-prototype-floats.md
Specification: .10x/specs/remote-empty-prototype-float-canonicalization.md

# Empty Remote Prototype Float Canonicalization Evidence

## Live trigger

With exact main reader `0.5.2.dev19+g0db802ec1`, both zero-write migration
previews failed before binding. A sanitized direct read identified
`site-www-aurelio-ai-v1`; a separate stable two-pass raw audit proved exact
schema v2, 13 cards, 17 namespaces, and only that malformed row. It has zero
routing examples, and both its stored prototype-vector hash and card revision
already equal the float32-canonical intended values. The row parses when the
provider-returned prototype vector is locally canonicalized; therefore a
two-scalar live patch would be a no-op and is not authorized.

All diagnosis was read-only: two migration preview attempts plus bounded
strong-read diagnostics; zero schema/card/content writes, deletes, or model
inferences occurred. No vector, example, credential, provider payload, or raw
source content is recorded.

The stable raw audit covered 13 catalog rows and 17 live namespaces with digest
`0bf681d931f2358b295aac50e1ad7cb597b4e2872080079770e7a0e34d3d2bad`.
It used two namespace-list pages, one metadata request, and two strong catalog
query pages with zero writes, deletes, or model work.

## Implementation and validation

- `card_from_remote_row` now applies the existing finite IEEE-754 binary32
  round trip to every provider-returned prototype coordinate before calling
  the strict local parser. No local parser, writer, schema, model, routing,
  request, or content code changed.
- Remote regressions cover empty schema-v2 and schema-v3 same-bucket recovery
  and adjacent-bucket rejection. A direct local regression proves the same
  decimal drift remains invalid outside the remote transport boundary.
- The focused catalog/remote/catalog-CLI/apply-to-routing basket passed
  `102/102`; the exact remote suite passed `50/50` under Python 3.11 and 3.13.
- Complete discovery passed `851/851` under Python 3.11 and `851/851` under
  Python 3.13. Source, ranking, C6, lock, compilation, and diff validators
  passed; the active routing authority/module receipts remained valid.
- A diagnostic 69-file wheel and 142-file source archive passed distribution
  validation without publication. Their pre-commit SHA-256 values were
  `b2d4a1e642e83d9f50237f57e7681954268b2a04d3a0b9f06b559a48f740321d`
  and `14eff81f183f2a4fcca7a965a6177c9ed8d4f0e07c1d38738e4a8ac98aeca4e0`.
- Independent review found no blocker: same-bucket provider transport is
  normalized, adjacent buckets still fail, local/schema-v1 identity remains
  strict, and compatibility/privacy/request/write behavior is unchanged.
- Validation used local fixtures, isolated environments, and dependency cache.
  It made no provider call, live mutation, model inference, publication, tag,
  Release, push, or merge.

## Remaining handoff evidence

Append the final task commit, PR, and hosted-check identities before source-task
closure. Installed fixed-reader identity and successful live read-only preview
belong to `.10x/evidence/2026-08-16-routing-catalog-v3-migration.md`; provider
mutation remains governed only by that separate live migration ticket.
