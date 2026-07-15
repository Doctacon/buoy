Status: open
Created: 2026-07-15
Updated: 2026-07-15
Parent: None
Depends-On: None

# Semantic Retrieval Research Plan

## Plan outcome

Produce four focused, evidence-backed investigations for semantic organization and retrieval over many Buoy/Turbopuffer namespaces:

1. namespace catalog and routing;
2. governed tagging and metadata filtering;
3. cross-namespace concept/entity graphs;
4. multi-hop and global retrieval.

This is a parent plan, not an executable ticket. It does not authorize product implementation, live Turbopuffer operations, or an architecture decision. Each child is research-only and must run in its own `work/*` branch and worktree based on current `develop`.

## Ratified context

- “Chief AI” means Chief at `chief.bot`.
- Data Vault was an analogy for stable concepts and relationships, not an architecture requirement. Buoy MUST NOT build or require Data Vault 2.0 for this workstream; `.10x/decisions/data-vault-is-analogy-not-architecture.md` governs.
- The intended surfaces are semantic catalog, taxonomy, ontology, concepts, typed relationships, provenance, and retrieval.
- All four capability families matter and must be investigated independently rather than collapsed into one broad implementation.
- The broad preliminary investigation is `.10x/research/2026-07-15-metadata-tagging-graphs-and-data-vault.md`; its Data Vault-specific interpretation is superseded by the active decision above.

## Child investigations

1. `.10x/tickets/done/2026-07-15-research-data-vault-namespace-catalog-routing.md`
2. `.10x/tickets/done/2026-07-15-research-data-vault-governed-tagging-filtering.md`
3. `.10x/tickets/done/2026-07-15-research-data-vault-concept-graph.md`
4. `.10x/tickets/done/2026-07-15-research-data-vault-multi-hop-global-retrieval.md`

The investigations may run in parallel because each owns a separate worktree and research question. Their findings must remain independently reviewable. Architecture synthesis happens only after all four findings are available and reconciled against shared invariants.

## Shared research invariants

Every child must:

- treat Data Vault hub/link/satellite language only as historical analogy and introduce no warehouse requirements;
- preserve source provenance to namespace and chunk identity;
- cover ACL/isolation implications rather than assuming all namespaces may be joined;
- prefer open-source/self-hostable components and name licensing or operational caveats;
- compare the proposed layer with the smallest metadata/vector-only alternative;
- identify costs, stale-data/deletion behavior, entity/tag correction, and reprocessing needs;
- define measurable evals rather than asserting that graphs or tags improve retrieval;
- inspect current Buoy records/source before recommending new behavior;
- perform no live Turbopuffer writes, namespace changes, tags, releases, secrets, or product-data mutation.

## Aggregate acceptance criteria

- Four focused research records exist, each with question, sources/methods, findings, conclusions, limits, and explicit local implications.
- Each child branch/worktree started from the then-current protected `develop` and contains only its bounded research/record changes.
- The namespace study defines catalog authority, routing compatibility, and model/schema/ACL metadata.
- The tagging study distinguishes structural labels, controlled taxonomies, inferred terms, provenance, and filtering/ranking semantics.
- The concept-graph study defines candidate node/edge/provenance/history models and evaluates open-source storage choices without prematurely selecting one.
- The multi-hop/global study defines query classes, baselines, datasets/evals, quality measures, and cost gates.
- Contradictions among findings are named; none are silently converted into active product behavior.
- No active specification or executable implementation ticket is created until the user reviews the combined findings and ratifies an architecture.

## Integration points

- Current namespace discovery and explicit multi-namespace retrieval contracts.
- Turbopuffer document attributes, namespace isolation, and filtering.
- taxonomy/ontology identity, typed relationships, provenance, and historical observations without Data Vault machinery.
- Buoy plan artifacts, source hashes, row IDs, embedding contracts, applied state, and retrieval evals.
- Chief Labels/Collections/Concepts as a product comparison, not implementation authority.

## Blockers

None for the four completed research investigations. Architecture synthesis remains blocked on reconciling the findings under `.10x/decisions/data-vault-is-analogy-not-architecture.md`; implementation remains blocked on focused specifications, user ratification, and executable tickets.

## Progress and notes

- 2026-07-15: Preliminary internet and codebase research confirmed per-chunk Turbopuffer attributes and separated structural metadata, controlled tags, concepts, and first-class graphs.
- 2026-07-15: User confirmed Chief at `chief.bot`, formal Data Vault 2.0, and all four investigation tracks, each in its own worktree based on `develop`.
- 2026-07-15: Concept-graph child research completed and passed independent re-review; closed child: `.10x/tickets/done/2026-07-15-research-data-vault-concept-graph.md`. Architecture synthesis and implementation remain blocked on completion/reconciliation of all four tracks and user ratification.
- 2026-07-15: Governed tagging/filtering research passed re-review and closed at `.10x/tickets/done/2026-07-15-research-data-vault-governed-tagging-filtering.md`. Its implementation semantics remain unratified and the public tag-output/filtering drift remains blocked in its existing owner.
- 2026-07-15: The multi-hop/global retrieval child research completed after a final pass review; its ticket is `.10x/tickets/done/2026-07-15-research-data-vault-multi-hop-global-retrieval.md` and its research record is `.10x/research/2026-07-15-data-vault-multi-hop-global-retrieval.md`. Aggregate architecture synthesis and implementation remain blocked until all four findings are available, reconciled, and user-ratified.
- 2026-07-15: User corrected the workstream premise: Data Vault was only an analogy for concepts and relationships. Renamed this active parent plan, repaired graph references, and adopted `.10x/decisions/data-vault-is-analogy-not-architecture.md`. No Data Vault implementation, schema, warehouse, or loading process is in scope.
