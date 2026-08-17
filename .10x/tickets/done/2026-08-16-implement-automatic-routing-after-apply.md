Status: completed
Created: 2026-08-16
Updated: 2026-08-16
Decision: .10x/decisions/buoy-derives-routing-prototypes-from-reviewed-plans.md
Specification: .10x/specs/automatic-routing-after-apply.md

# Implement Automatic Routing after Apply

## Outcome

Make the ordinary user workflow `buoy plan` -> reviewed `buoy apply` ->
namespace-free retrieval work immediately and well for a new source. Derive
bounded routing evidence from actual indexed content without a generative LLM,
publish it during apply, and treat certification as singleton optimization
rather than basic routing availability.

## Scope

- Advance compact plans to schema v3/delta v2 with exact reviewed routing
  prototypes selected from the complete desired corpus.
- Add a system-owned content-passage bank to the one-card remote catalog
  contract, retaining individual shortlist vectors while preserving operator
  examples and a shared eight-slot budget.
- Embed and register the approved bank during apply with truthful readiness,
  partial-success repair, and timing output.
- Add exact v1/v2/v3 remote readers, explicit reader-first schema-v3 migration,
  no ordinary-apply bootstrap, and plan-lineage compatibility.
- Replace additive catalog projection failure with provisional descriptor-free
  top-three routing while preserving the certified anchor and all malformed-
  state fail-closed boundaries.
- Update focused docs, tests, package artifacts, confidence authority,
  evidence, and independent review.

## Acceptance

- `plan` uses no generative model, routing model, Turbopuffer credential, or
  provider write and deterministically persists at most eight real passages.
- No-change plans retain those passages although unchanged content remains
  absent from content upserts.
- Apply embeds at most one bounded routing batch, runs no MiniLM/canaries, and
  performs no source reacquisition or catalog-wide evaluation.
- A successful card verification reports automatic retrieval ready; any card
  failure reports nonzero partial success and exact repair authority.
- Exact remote schema v3 is a one-time prerequisite. Missing/older state after
  content commit triggers no catalog mutation, retains the plan, and emits an
  opaque plan-backed `repair-apply --inspect-current` command after separate
  setup/migration. Inspection is lock-held and read-only, revalidates committed
  authority, and emits an absence/revision-bound repair; read failure follows
  the same path after recovery.
- Existing manual semantics/examples and enabled state remain authoritative;
  the combined non-base evidence budget is always at most eight.
- Generic `catalog upsert` cannot set, clear, or replace the system-owned
  routing-passage bank and preserves existing passages.
- Any one reviewed source passage can nominate its card into the unique-card
  top-12 shortlist; a diverse passage bank is not reduced to centroid-only
  authority.
- Exact certified routing is behaviorally unchanged. Any valid projection
  drift, including an added or content-refreshed card, participates
  immediately but descriptor-free routing always starts with up to three and
  never claims calibrated singleton confidence.
- Exact-name and explicit-namespace paths remain unchanged. Malformed
  artifacts, cards, or vector/hash state still fail before content work;
  internally valid catalog drift remains provisional and usable.
- A complete fake-provider workflow proves plan -> apply -> automatic search
  selects the new namespace from content-derived evidence.
- Focused/full supported-Python tests, build/install/package, locked
  dependency, privacy, diff, performance, and independent review gates pass.

## Owned paths

- `src/buoy_search/{plan_artifacts,plan_validation,planning_service,apply,catalog,remote_catalog,catalog_cli,routing,routing_quality,cli}.py`
- focused plan/apply/catalog/routing/activation tests and fixtures
- indexing/retrieval/migration documentation and confidence package data
- this ticket's decision, specification, evidence, and review records

## External effects

The owner's “execute all of that” direction authorizes this bounded local
implementation, validation, review, commits, and PR handoff. Tests use local
fixtures/fake providers. No live provider/schema/card/content mutation,
deployment, release, package publication, or self-merge is authorized.

## Progress

- 2026-08-16: User approved the content-derived passage-bank plan, immediate
  conservative routing, certification-as-optimization boundary, and full
  implementation. Created isolated branch `work/automatic-routing-after-apply`
  from current local `develop` at `8a979562`.
- 2026-08-16: Independent review rejected non-atomic apply-time catalog
  bootstrap and passage-bearing shell repair output. Hardened the design to a
  reader-first exact-v3 prerequisite plus retained-plan repair, without raw
  source text in diagnostics.
- 2026-08-16: Follow-up review rejected generic passage mutation, unknown-state
  `catalog show` fallback, non-idempotent ambiguous repair, and repair/apply
  races. Removed passage controls from generic upsert and added lock-held,
  state-revalidated `repair-apply --inspect-current` followed by an exact
  absence/revision-bound, idempotent repair.
- 2026-08-16: Final independent review passed with no remaining correctness,
  security/privacy, migration, atomicity, repair, or authority blocker. The
  frozen implementation passed 848 tests on Python 3.11 and 3.13, a 331-test
  focused basket, validators, benchmark, distribution validation, and isolated
  wheel smoke.

## Closure

- Evidence: `.10x/evidence/2026-08-16-automatic-routing-after-apply.md`
- Independent review:
  `.10x/reviews/2026-08-16-automatic-routing-after-apply-review.md`
- Compatibility: local plan artifacts hard-cut to exact schema v3/delta v2;
  remote readers accept v1/v2/v3, but passage writes require explicit
  reader-first schema v3. Existing corpora need a fresh reviewed plan/apply or
  separately governed backfill for truthful content-derived passages.
- External effects: none beyond local dependency/build cache activity. No live
  source/provider read, catalog/content/schema write, deployment, publication,
  release, merge, or pull request occurred.
