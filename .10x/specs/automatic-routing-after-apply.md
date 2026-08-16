Status: active
Created: 2026-08-16
Updated: 2026-08-16
Decision: .10x/decisions/buoy-derives-routing-prototypes-from-reviewed-plans.md
Amends: .10x/specs/compact-delta-plan-artifacts.md, .10x/specs/namespace-routing-card-contract.md, .10x/specs/automatic-multi-corpus-retrieval.md, .10x/specs/scalable-routing-quality.md, .10x/specs/bounded-prototype-routing-activation.md, .10x/specs/plan-artifact-lifecycle-cleanup.md

# Automatic Routing after Apply

## Product contract

A fully successful approved schema-v3 apply MUST leave its live content
namespace represented by one compatible routing card. Unless an operator has
deliberately kept an existing card disabled, it MUST report
`automatic_retrieval_ready=true`. The immediately following namespace-free
retrieval may select that namespace from source-derived evidence without a
catalog command, source reacquisition, artifact regeneration, or evaluation
run. A preserved disabled state or registration failure reports readiness
false; registration failure remains truthful partial success.

## Reviewed plan prototypes

`PLAN_SCHEMA_VERSION` becomes `3` and `DELTA_SCHEMA_VERSION` becomes `2`.
Successful output remains exactly `plan.json` and `delta.duckdb`.

`plan.json` adds exactly:

```json
"routing_prototypes": {
  "strategy": "diverse-content-passages-v1",
  "count": 0,
  "logical_hash": "<sha256>"
}
```

The descriptor participates in artifact identity. The database adds exactly
one `routing_prototypes` table with contiguous ordinal plus exact source row
ID, canonical URL, source path, section path, chunk hash, passage text, and
passage hash. The logical delta hash covers this table in addition to content
upserts and stale rows. Readers validate its exact schema, bounds, ordering,
source references, passage reconstruction contract, and hashes before any
credentials, model load, provider read, or mutation.

Planning selects zero through eight passages from the complete desired chunk
manifest, including unchanged chunks. It never selects a stale/removed chunk.
Selection is deterministic and model-free: canonical duplicate passages are
collapsed; candidates prefer distinct canonical documents before repeats;
stable token-overlap diversity and source order break ties. Passage text is a
bounded title/section/source excerpt, not a generated question. Exact selected
passages and provenance are reviewable. Plan remains Turbopuffer-, routing-
model-, and provider-write-inert.

## Card and projection contract

Remote schema v3 is exact schema v2 plus three non-filterable fields:
`routing_passages: []string`, `routing_evidence_vectors: []float`, and
`routing_evidence_vectors_hash: string`. The vector array is the flattened
float32-canonical sequence of non-base evidence vectors in exact manual-example
then generated-passage order. Schema-v1/v2 readers normalize the three-field
bank to empty; schema-v3 writes always include it. The bank is system-owned.
`routing_examples` remains operator-owned. Both lists are canonical, bounded,
and satisfy:

```text
len(routing_examples) + len(routing_passages) <= 8
```

`routing_passages` is system-owned authority. Generic `catalog upsert` MUST NOT
accept an option to set, clear, or replace it and MUST preserve the existing
bank. Only approved apply, retained-plan repair, or a separately governed
migration/backfill may mutate those passages.

The base passage remains unchanged. Manual example passages retain their
current format. Each generated passage is paired with the card title and
summary under a distinct `Routing source passage:` label. Empty generated
passages preserve the exact existing prototype hash/vector/hash contract.
Nonempty generated passages use a new projection identity over base, manual
examples, and generated passages, embedding each passage separately, retaining
the exact non-base vectors, and continuing to store the normalized arithmetic
mean in the existing ordinary `routing_prototype_vector`. The flat bank length,
hash, individual normalized vectors, and recomputed mean must all validate.

Apply preserves manual title, summary, aliases, tags, enabled state, semantic
origin, and routing examples. Manual examples consume slots first; the exact
approved generated passages fill the remaining slots in plan order. New or
changed effective evidence uses at most one local BGE batch. An identical
effective profile/model reuses vectors and loads no routing model. Apply does
not run the cross-encoder, canaries, calibration, or content queries.

The repair output after post-content card failure must contain or retain an
exact bounded authority sufficient to recreate the approved generated passage
bank without reacquiring the source. It must not falsely report readiness. If
apply has already established exact-v3 card absence or revision before a later
failure, it MAY emit the corresponding bound repair directly. If missing, old,
or unreadable catalog state prevented a safe binding, it MUST instead emit an
opaque retained-plan `catalog repair-apply --inspect-current` command with no
approval, absence assumption, or expected revision.

Inspection MUST acquire the normal namespace apply lock, revalidate the
retained plan against committed plan/apply state under that lock, strongly read
exact-v3 catalog state, and emit an opaque approved follow-up bound to observed
card absence or the exact current card revision. It MUST load no routing model,
perform no schema/card/content write or delete, and retain the plan. Bound
repair MUST keep the lock through registration, verification, and cleanup. A
card already matching the exact retained plan/apply system authority after an
ambiguous provider outcome is verified as successful without a second write;
other precondition drift fails closed and requires fresh inspection.

Generated routing passages are bounded but verbatim-derived source excerpts
persisted as ordinary attributes on catalog card rows. Public CLI and routing
output MUST redact passages and vectors. A principal authorized to query raw
provider rows in the catalog namespace can nevertheless read the excerpts, so
catalog credentials and raw-row ACLs MUST be governed as source-content access,
not metadata-only access.

## Catalog lifecycle

New readers accept exact remote schemas v1, v2, and v3. Existing plan lineage
values 1 and 2 remain compatible beside 3; local plan-reader compatibility is
independent. Exact remote schema v3 is a one-time reader-first prerequisite for
schema-v3 plan registration. Neither first nor ordinary apply creates a missing
catalog or migrates v1/v2. Provisioning and live migration/backfill are
separately reviewed operational tasks after compatible-reader deployment. If
the prerequisite is absent after content and local state commit, apply MUST
return nonzero partial success, perform no catalog schema or card write, retain
the exact plan as repair authority, and emit the retained-plan-backed read-only
inspection command. The operator completes the prerequisite or resolves the
read failure, runs inspection, reviews its absence/revision binding, and only
then runs the emitted bound repair. Successful verified repair may perform
exact plan cleanup; inspection and failed repair retain it, while cleanup
failure warns and leaves successful registration intact.

Only valid enabled compatible cards define automatic candidates. Missing-card
live namespaces are diagnostics rather than a global availability stop; the
apply that failed to register one already returned nonzero. Stale, disabled,
incompatible, malformed, reserved, or duplicate cards remain excluded or
fail according to their existing safety contracts.

## Certified and provisional routing

Descriptor-free shortlist scoring uses the maximum query cosine across each
card's base and individual evidence vectors, collapses to one score per
namespace, and only then takes the best twelve namespaces into MiniLM. Legacy
v1/v2 cards without the individual bank retain their existing aggregate-vector
fallback. A passage-bearing card without its complete bank is malformed. This
prevents a relevant passage in a deliberately diverse new card from being
diluted out of the shortlist by its centroid.

The confidence artifact identifies the exact certified namespace set and its
semantic projection. Validation returns one of two usable states:

- `certified`: the eligible namespace set and its projection exactly match the
  artifact's certified set and projection;
- `provisional`: the current eligible cards are internally valid but their set
  or projection differs from that exact certified state.

Invalid artifact, malformed card, stale stored hash/vector, and unstable read
state fail. Added, changed, missing, disabled, or incompatible members are
valid drift and force provisional mode; at least one eligible card is still
required. In certified state, current exact-name, score/margin, and
singleton/top-three behavior is unchanged. In provisional state, exact
title/alias matches retain their current authority; descriptor-free routing
scores all eligible cards through the same bounded BGE shortlist and MiniLM
reranker but forces `high_confidence=false`, applies no singleton thresholds,
and starts with the best three.

Output reports `routing_confidence_mode=certified|provisional`, whether
singleton thresholds were applied, and the provisional namespace count. It
does not expose source passage text or vectors. Explicit namespace retrieval
continues to bypass every automatic component.

## Performance and acceptance

- Prototype count is at most eight and text is bounded by the existing safe
  routing-evidence limit.
- The flattened evidence bank is at most `8 * 384` float32 values per card;
  no extra row, ANN index, or provider request is introduced.
- Apply adds at most one bounded routing embedding batch, no generative model,
  no reranker/evaluation, and no corpus-sized routing work.
- Catalog registration timing is reported through completion; same-harness
  median and p95 must not regress materially from the current registration
  path beyond the bounded embedding batch.
- Existing certified-catalog route outputs and thresholds are unchanged.
- A no-change plan still carries verified prototypes selected from the full
  desired corpus; tamper/reorder/dangling/over-limit state fails early.
- Every supported source kind produces deterministic source-grounded
  prototypes.
- A fake-provider end-to-end case proves plan -> approved apply -> immediate
  descriptor-free retrieve selects content that generic source metadata does
  not describe.
- Any valid certified-projection drift forces top three rather than failure or
  singleton; malformed state still stops before content access.
- Manual fields/examples and disabled state survive generated refreshes; total
  non-base evidence never exceeds eight.
- Focused and full Python 3.11/3.13, package/build/install, privacy, artifact,
  diff, independent-review, and activation-source-receipt checks pass.

## External effects and rollout

Local implementation and validation perform no live source, Turbopuffer,
catalog, schema, card, content, deployment, release, or publication mutation.
The task produces the compatible reader/writer, migration implementation, and
reviewed evidence. Shared live schema migration, corpus re-plans/backfills,
deployment, and release remain separately authorized operations after the
compatible reader is integrated.
