Status: pass
Created: 2026-08-15
Updated: 2026-08-15
Ticket: .10x/tickets/2026-08-15-migrate-routing-catalog-v2-and-examples.md
Evidence: .10x/evidence/2026-08-15-routing-catalog-v2-migration.md

# Routing Catalog V2 Migration Review

## Scope and closure boundary

The independent review compared the settled checkpoint-two task-worktree
candidate with its `develop` base and the governing decision, specification,
active ticket, provisional evidence, public documentation, and focused tests.
It covered exact schema-v1/v2 semantics, snapshot and projection binding,
optimistic concurrency, schema-only and one-card mutation postconditions,
model/provider failure redaction, request and operation accounting,
idempotency, field and base-vector preservation, ordinary-apply persistence,
CLI validation order, and JSON/text truth.

The settled candidate was reviewed in
`work/routing-catalog-v2-migration` against base commit
`9fd3f01a05392a08401296d3fdc99d0dd70ed5a1`, before its handoff commit. The
handoff commit must contain this exact source, test, documentation, governance,
evidence, and review set.

This PASS covers only the bounded source implementation. It does not claim a
live preview has run, authorize a provider mutation, close the active ticket,
approve reviewed examples, activate prototype routing, merge the task, publish
an artifact, or release Buoy.

## Findings closed during review

- Migration preview text now exposes the exact normalized schema fingerprint,
  four schema additions, every namespace/deterministic-row/card-revision
  binding, vector-inclusive projection hash, and explicit approval budget.
  Reviewed-example text similarly exposes the canonical questions,
  current/intended revisions, prototype hashes, performed operations, and the
  one-card/one-write approval budget.
- Operator namespaces and approval digests are validated before credentials,
  catalog reads, models, resources, or write methods. Invalid runtime
  configuration also returns the same structured zero-operation result rather
  than escaping the JSON contract. Regressions prove projection drift and a
  stale valid card revision stop before resource, model, or write access.
- The schema primitive requires exact `OK` status, zero affected rows, no
  remaining rows, no row-mutation counts, and no affected IDs. The example
  operator accepts only one changed deterministic row and the exact intended
  card; zero-row, multiple-row, wrong-ID, and wrong-card results fail closed.
- Preview revisions are not represented as verified. Exact-v2 migration and
  already-present canonical examples are truthful zero-write idempotent
  successes. Failure output records one attempted mutation when appropriate,
  distinguishes exact accounting from a known lower bound, and never emits
  raw provider/model exception text, questions, vectors, credentials, paths,
  or tracebacks.
- Both post-write catalog reads reuse the compatibility contract established
  before the initial strong read. Migration verification requires unchanged
  live inventory, counts, card revisions, complete cards, base vectors, and
  vector-inclusive projection. Example verification requires the exact target
  candidate and exact full projections for every unrelated card.
- Reviewed examples are now preserved by ordinary apply for existing manual
  and generated cards. Source generation cannot invent examples for a new card
  or clear operator-owned examples, while verified source, retrieval, plan,
  and apply-lineage fields retain their existing refresh behavior.

## Implementation and safety findings

- `catalog migrate-routing-v2` performs a zero-write preview after one complete
  strong catalog read. Approval requires the exact preview snapshot revision
  and projection SHA-256 before the schema resource is acquired. Exact schema
  v1 permits one request carrying the exact additive v2 schema and no rows;
  exact schema v2 is a zero-write success. Any uncertain post-write state
  requires a fresh preview and is never rolled back by schema deletion.
- `catalog set-routing-examples` accepts one through eight canonical reviewed
  questions for exactly one eligible or disabled non-stale schema-v2 card.
  Approval binds the freshly observed card revision before local BGE model work
  and performs one conditional update. The candidate may change only
  `updated_at`, `card_revision`, and the four-field prototype bundle; the
  legacy semantic hash, vector, vector hash, enablement, source, semantic,
  retrieval, and lineage fields remain fixed.
- Content resources and content mutation methods are not acquired. The
  implementation does not alter production routing, the confidence artifact,
  schema-v1 base-vector selection, content fanout, card enablement, aliases,
  tags, content rows, credentials, or deletion state.

## Validation

The implementation evidence records the following settled-worktree results:

- the focused remote primitive, catalog operator, and apply-persistence suite
  passed `61/61` under Python 3.11.5 and `61/61` under Python 3.13.0;
- the full non-packaging suite passed `750/750` under each Python version, and
  the isolated packaging suite passed `3/3` under each version;
- source validation, Python compilation, and `git diff --check` passed;
- a diagnostic `0.5.2.dev999` wheel and source archive passed distribution
  validation, isolated installation, exact-version inspection, and help smokes
  for both new commands; nothing was published.

The independent reviewer reread the settled implementation, governing records,
documentation, and negative-path regressions and independently confirmed a
clean `git diff --check`. The reviewer did not rerun provider-backed commands
or make any live observation.

## External effects

Checkpoint-two implementation and validation made no provider call and
performed no live catalog-schema write, catalog-row write, content query or
write, deletion, activation, credential change, publication, or release. The
independent reviewer made no provider call and did not commit, push, merge, or
publish. Diagnostic distributions were local and unpublished. The last
recorded live observation therefore remains the prior exact schema-v1 snapshot
documented in the provisional evidence; this review does not claim a new live
readback.

## Verdict and remaining gates

PASS for the bounded checkpoint-two source implementation. The candidate is
reader-first, preview-first, revision-bound, provider-failure-safe, and
compatible with the still-authoritative legacy production route.

Before any shared-catalog mutation, the exact reviewed source must produce a
fresh read-only live preview whose schema, snapshot revision, vector-inclusive
projection, card identities, and request budget are recorded and independently
reviewed. Any drift requires regeneration. A separate go/no-go must then bind
exactly that preview before the one schema-only approval request. The resulting
catalog must strong-read as exact schema v2 with the unchanged legacy
projection before any example operation begins.

Each later reviewed-example update still requires owner-frozen questions and
canary disjointness, a fresh per-card preview, exact revision-bound approval,
one-row readback, unchanged full-catalog invariants, and recorded external
effects. Final evidence must also show unchanged production-route behavior.
Prototype routing, confidence calibration, activation, cleanup deletion,
merge, publication, and release remain separate, unapproved gates.
