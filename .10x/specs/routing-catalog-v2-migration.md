Status: active
Date: 2026-08-15
Decision: .10x/decisions/routing-catalog-v2-migration-is-reader-first-and-revision-bound.md

# Routing Catalog V2 Migration

## Commands

```text
buoy catalog migrate-routing-v2 \
  [--expected-snapshot-revision SHA256] \
  [--expected-projection-sha256 SHA256] [--approve] [--json]

buoy catalog set-routing-examples NAMESPACE \
  --routing-example QUESTION ... \
  [--expected-card-revision SHA256] [--approve] [--json]
```

`--approve` requires every corresponding expected value. Preview omits those
values, emits them for review, and performs zero writes. `--json` changes only
presentation. Errors are bounded and never include questions, vectors,
credentials, provider payloads, exception text, paths, or tracebacks.

## Schema migration preview

Strong-read exact schema v1 or exact schema v2. Emit and bind:

- region and `buoy-routing-catalog-v1`;
- observed schema and exact schema fingerprint;
- snapshot revision and vector-inclusive catalog projection SHA-256;
- row count and sorted namespace/card-revision identities;
- the exact additions `routing_examples:[]string`,
  `routing_prototype_hash:string`, `routing_prototype_vector:[]float`, and
  `routing_prototype_vector_hash:string`, all nonfilterable and without ANN;
- `schema_writes`, `card_writes`, `content_writes`, and `deletes` budgets;
- an explicit warning that exact-v1 readers fail closed after migration.

Preview never loads an embedding or reranking model and never calls a provider
write method.

## Schema migration approval

Require 64-lowercase-hex expected snapshot and projection values. Repeat the
strong read and compare exact values before exposing a write method. Exact v2
returns an idempotent zero-write result only if every row has a coherent full
or reconstructable all-null prototype bundle.

For exact v1, perform one schema-only write using cosine distance and the exact
v2 schema. Send no rows. Then perform a complete v2 strong read and require:

- identical live inventory, row IDs/count, namespace/card revisions, enabled
  states, base semantic hashes/vectors/vector hashes, and complete v1 card
  projection;
- reconstructed empty examples and prototype hash/vector/vector hash exactly
  equal to their base counterparts for every row;
- zero missing, stale, or incompatible cards introduced by the operation.

The command reports one attempted schema write truthfully even if verification
fails. It never attempts schema rollback.

## Reviewed-example preview and approval

Strong-read exact v2 and find exactly one eligible or disabled non-stale target
card. Normalize one through eight unique reviewed questions under the existing
512-character and canonical-order contract. Empty replacement is excluded from
this ticket.

Project the observed card into `CardFields`, changing only routing examples.
Prepare the candidate through the pinned local BGE model. Require the candidate
to preserve every base and non-prototype field. Preview emits no vector or raw
model diagnostics; it reports normalized questions, current/intended revisions,
prototype hashes, and the exact one-card/one-write budget.

Approval requires the exact current card revision supplied by the operator,
repeats the strong read before model work, and conditionally writes on that
revision. Exactly one deterministic card ID must be affected. Two exact
verification reads must reproduce the candidate and unchanged full-catalog
invariants. Drift or a zero/multiple-row result is failure, not success.

## Request and safety accounting

Every result reports strong-read calls, model inferences, schema writes, card
writes, content operations, and deletes. Content resources and content mutation
methods are never acquired. Provider/model failures are redacted. Questions may
appear in explicit operator preview output but never in generic failure text.

## Ordinary apply persistence

Once a card contains reviewed routing examples, every later ordinary apply
preserves those examples whether the card's base semantic origin is `manual`
or `generated`. The apply may continue to refresh verified source, retrieval,
plan, and apply-lineage fields under its existing contract. It must not infer,
replace, or clear routing examples from a URL, source title, generated summary,
or indexed content. A generated card with no prior reviewed examples remains
empty.

## Production boundary

Neither command imports, packages, writes, or approves an active routing
confidence artifact. Ordinary automatic retrieval continues to call only the
legacy production route. Schema v2 and examples are inert storage until a
separate activation change is integrated and deployed.
