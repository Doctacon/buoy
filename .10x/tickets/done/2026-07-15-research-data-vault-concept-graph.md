Status: done
Created: 2026-07-15
Updated: 2026-07-15
Parent: .10x/tickets/done/2026-07-15-semantic-retrieval-research-plan.md
Depends-On: None

# Research Data Vault Cross-Namespace Concept Graph

## Scope

Research a provenance-preserving concept/entity graph derived from chunks across many namespaces while keeping Data Vault 2.0 hubs, links, satellites, business keys, and history authoritative.

Execute in branch `work/research-data-vault-concept-graph` in its own worktree based on current `develop`. Produce `.10x/research/2026-07-15-data-vault-concept-graph.md`. Research only; do not implement.

## Questions

- Which nodes and edges are needed for source, namespace, chunk, business entity, concept, relationship, assertion, taxonomy term, and time?
- How should stable Data Vault identities map to derived entities without merging unratified LLM guesses into hubs or links?
- How should every concept, relationship, and summary retain chunk/source provenance, extraction version, confidence, validity, and retraction state?
- How do Chief Concepts, Cognee NodeSets, Graphiti, Microsoft GraphRAG, LlamaIndex PropertyGraphIndex, and RAGFlow handle graph construction, retrieval, updates, and deletion?
- Which open-source/self-hostable storage choices are viable, and when is a relational edge model sufficient before a graph database?
- How are cross-namespace ACLs enforced during graph traversal and concept aggregation?

## Acceptance criteria

- Inspect current Buoy identity/hash/provenance fields and active Data Vault/tagging preliminary research.
- Compare at least three open-source graph/concept approaches using source-backed behavior, licensing, operational cost, update semantics, and retrieval integration.
- Define candidate node/edge schemas with explicit authority and provenance classification.
- Analyze entity resolution, aliases, contradictory facts, temporal validity, deletion, model/taxonomy migration, and ACL leakage.
- Compare a full graph with smaller alternatives: concept cards, inverted entity assignments, or relational adjacency tables.
- Propose evals for entity resolution, edge precision, provenance completeness, deletion correctness, traversal usefulness, latency, and cost.
- Recommend a bounded concept-layer experiment, not an implementation or graph-store selection.

## Explicit exclusions

- Creating Data Vault hubs/links from LLM output.
- Choosing or deploying a graph database, changing schemas, extracting live entities, or mutating Turbopuffer.
- Assuming graph visualization improves retrieval.

## Evidence expectations

Record official docs and source links, licenses, local paths, model/graph lifecycle behavior, contradictions, null findings, and confidence. Name where product internals are undocumented.

## Blockers

None for research. Concept/edge semantics, storage, and implementation remain blocked on synthesis and user ratification.

## Progress and notes

- 2026-07-15: Ticket opened from the ratified four-track research plan. Execution intentionally deferred from the ticket-authoring turn.
- 2026-07-15: Activated the ticket and completed the bounded research record at `.10x/research/2026-07-15-data-vault-concept-graph.md`. Inspected current Buoy identity/provenance source and compared Chief Concepts, Cognee, Graphiti, Microsoft GraphRAG, LlamaIndex property graphs, RAGFlow, Data Vault authority boundaries, and open-source relational/graph storage. The record proposes a reified assertion/evidence model, ACL/temporal/deletion controls, smaller alternatives, and a synthetic offline eval; it makes no store selection or live/source/spec/decision change. Ticket intentionally remains active for independent review.
- 2026-07-15: Repaired the significant finding in `.10x/reviews/2026-07-15-data-vault-concept-graph-review.md`. The research now defines a common `DerivedAssertion` contract and coherent `MentionAssertion`, `TaxonomyAssignmentAssertion`, and `VaultResolutionAssertion` identities, typed endpoints, provenance/run links, temporal and ACL fields, authority boundaries, and correction/deletion behavior. It explicitly states that approved or retracted Vault mappings affect only derived projections and never ratify or mutate warehouse Hubs, Links, Observations, keys, or relationships. Scope remains research-only; ticket remains active for required review.
- 2026-07-15: Independent re-review passed at `.10x/reviews/2026-07-15-data-vault-concept-graph-rereview.md`; the prior assertion-model finding is resolved with no blocker. Closed the research ticket after mapping every criterion to the completed record and pass re-review. Research status remains `done`; implementation and architecture/product decisions remain blocked as recorded below.

## Closure

- Current Buoy identity/hash/provenance and preliminary research inspection: satisfied by the local authority inventory and identity analysis in `.10x/research/2026-07-15-data-vault-concept-graph.md` sections 1 and Sources and methods.
- Open-source approach comparison: satisfied by the source-backed comparison of Cognee, Graphiti, Microsoft GraphRAG, LlamaIndex, and RAGFlow, with Chief as a proprietary behavior reference, including licensing, lifecycle, retrieval, and operational limits.
- Candidate node/edge authority and provenance: satisfied by the reified `DerivedAssertion` model, typed assertion subtypes, exact evidence/run links, imported read-only Vault references, lifecycle, and policy controls; the pass re-review confirms the prior gap is resolved.
- Resolution, aliases, contradictions, time, deletion, migration, and ACL leakage: satisfied by research sections 6–8 and the pass re-review's temporal, lifecycle, and ACL assessment.
- Smaller alternatives: satisfied by concept cards, inverted entity assignments, relational assertion/adjacency tables, and batch community-summary comparisons.
- Evals: satisfied by the synthetic dataset, compared arms, safety gates, and entity, assertion, provenance, deletion, traversal, retrieval, latency, cost, ACL, and operational metrics.
- Bounded recommendation: satisfied by the offline synthetic storage-neutral experiment recommendation, with no implementation, live mutation, or store selection.
- Evidence expectations: satisfied by dated official/source links, licenses, local paths, lifecycle findings, null findings, undocumented internals, limits, and confidence boundaries in the research record.

The pass re-review establishes that the repaired research satisfies the ticket without widening scope. No product source, schema, specification, architecture decision, live service, or Turbopuffer state changed.

## Retrospective

The material review lesson is that saying assertions are “reified” is insufficient unless every subtype has an explicit logical home for identity, typed endpoints, evidence, extraction run, policy, temporal state, review, and retraction. The repaired common assertion contract now preserves that lesson in the research model itself. No separate knowledge or skill record is warranted because this is a bounded candidate-model finding, not an adopted project convention or operational procedure.
