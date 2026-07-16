Status: done
Created: 2026-07-15
Updated: 2026-07-15
Parent: None
Depends-On: None

# Production Semantic Routing Plan

## Outcome

Deliver the user-authorized production routing path through three bounded, sequentially integrated children:

1. canonical local namespace catalog and management CLI;
2. approved apply registration and reconciliation;
3. opt-in automatic routed retrieval.

This is a parent plan, not an executable ticket.

## Governing records

- `.10x/decisions/production-routing-local-catalog.md`
- `.10x/specs/production-local-namespace-catalog.md`
- `.10x/specs/approved-apply-catalog-registration.md`
- `.10x/specs/automatic-production-namespace-routing.md`
- `.10x/specs/explicit-multi-namespace-retrieval.md`
- `.10x/specs/turbopuffer-namespace-discovery.md`
- `.10x/specs/compact-duckdb-applied-state.md`
- `.10x/specs/depth-one-approved-apply-pipeline.md`
- `.10x/specs/embedding-inference-precision.md`
- `.10x/specs/buoy-local-compatibility.md`
- `.10x/reviews/2026-07-15-representative-semantic-routing-experiment-review.md`
- `.10x/knowledge/semantic-routing-evaluation-lessons.md`

## User-ratified production behavior

On 2026-07-15 the user explicitly requested full production implementation despite the limited benchmark and chose:

- explicit `--auto-route` activation;
- local catalog authority;
- enabled-card single-user eligibility;
- default route fan-out three;
- preservation of manual semantic fields during apply;
- precompute-before-remote plus explicit reconciliation for post-apply catalog failure;
- local-only dry route preview;
- persisted card vectors.

The user intends to judge quality through frequent live personal use. This authorizes the production path but not ACL groups, remote catalog, automatic default routing, graph work, or hidden fallback behavior.

## Child sequence

1. `.10x/tickets/done/2026-07-15-build-production-local-namespace-catalog.md`
2. `.10x/tickets/done/2026-07-15-integrate-approved-apply-catalog-registration.md`
3. `.10x/tickets/done/2026-07-15-add-automatic-production-namespace-routing.md`

The sequence is intentionally linear. All three touch CLI/state contracts, and later children must build on the integrated reviewed API rather than duplicate it across parallel worktrees.

## Integration points

- `.buoy`/legacy state-root resolution and local atomic state mechanics;
- plan artifacts/source metadata, old-plan compatibility, namespace lock lifetime, and approved apply sequencing;
- runtime model/precision/region configuration;
- explicit multi-namespace retrieval and namespace-qualified downstream RRF;
- namespace-aware ranking defaults;
- CLI text/JSON safety conventions and full test suite.

## Aggregate acceptance criteria

- Catalog state is local, atomic, lock-protected, validated, manually manageable, and carries persisted pinned routing vectors.
- Manual card semantics and enabled state survive apply; system/retrieval/apply fields refresh.
- Approved apply precomputes card registration before remote writes and provides idempotent local reconciliation after rare post-apply catalog failure.
- `retrieve --auto-route` performs local hybrid routing over enabled compatible cards, defaults to three, and reuses existing multi-namespace retrieval/RRF.
- Dry auto-route performs no credential or Turbopuffer work; explicit retrieval remains unchanged.
- Every child has focused tests, full-suite validation, durable evidence, independent review, and coherent closure before the next child begins.
- No remote catalog, ACL group system, taxonomy, tag filtering, graph, telemetry, or online learning is introduced.

## Blockers

None for the first child after this specification set passes independent shaping review and integrates into `develop`. Later children remain blocked on their named dependency.

## Progress and notes

- 2026-07-15: User explicitly authorized production implementation and ratified activation, authority, eligibility, fan-out, card ownership, apply failure/reconciliation, preview, and vector persistence semantics. Created focused production specifications and three sequential bounded child tickets. Implementation is intentionally deferred from this specification/ticket-authoring turn.

- 2026-07-15: Local catalog child completed with passing independent review; implementation commits `f8a89dd` and `e13d3e1`. Apply registration remains blocked until this branch integrates into `develop`.

- 2026-07-15: Approved apply catalog registration child completed with passing independent review; commits `0ea4571` and `e7a8170`. Automatic routing remains blocked until integration.

- 2026-07-15: Automatic production routing completed in `e823aba` and `ab2d89f`; holistic review passed and confirmed all aggregate acceptance criteria.

## Closure mapping

- Local catalog child: done, independently reviewed, integrated via PR #15.
- Approved apply registration child: done, independently reviewed, integrated via PR #16.
- Automatic routing child: done with final holistic pass review in this branch.
- Catalog authority, persisted vectors, apply staging/recovery, opt-in local preview, live top-three routing, explicit fallback, tests, docs, evidence, and review are coherent.
- No remote catalog, ACL groups, taxonomy, graph, telemetry, or automatic-default activation was introduced.

## Retrospective

Production delivery required strict persisted types/lineage, source-kind-aware URI handling, namespace-lock lifetime across local/remote phases, truthful partial-success state, identity revalidation before recovery deletion, and explicit legacy CLI/credential regression tests. These lessons are encoded in active specs and tests. No additional follow-up is opened automatically; the user explicitly chose live personal use as the quality judgment path.
