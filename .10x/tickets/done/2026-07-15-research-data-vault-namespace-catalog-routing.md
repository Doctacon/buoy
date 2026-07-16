Status: done
Created: 2026-07-15
Updated: 2026-07-15
Parent: .10x/tickets/done/2026-07-15-semantic-retrieval-research-plan.md
Depends-On: None

# Research Data Vault Namespace Catalog and Routing

## Scope

Research the smallest governed catalog and query-routing layer for many Buoy/Turbopuffer namespaces, informed by Data Vault 2.0 identity, lineage, and history without treating a namespace or vector index as a Data Vault hub.

Execute in branch `work/research-data-vault-namespace-routing` in its own worktree based on current `develop`. Produce `.10x/research/2026-07-15-data-vault-namespace-catalog-routing.md`. Research only; do not implement.

## Questions

- What is the authoritative identity for a namespace, source, Data Vault business concept, and indexed revision?
- Which catalog fields are required for semantic routing, embedding/schema compatibility, ACLs, freshness, source lineage, and retrieval profiles?
- Should the canonical catalog be relational/Data Vault-backed with a derived searchable namespace-card index, or can Turbopuffer safely be canonical?
- How should a query select a bounded compatible namespace set without all-namespace fan-out?
- Which routing approaches—exact filters, taxonomy classification, semantic namespace cards, learned routing, or hybrids—deserve evaluation?
- How are rename, reindex, stale source, deletion, model migration, and access-policy changes represented historically?

## Acceptance criteria

- Inspect current namespace discovery, multi-namespace retrieval, plan artifacts, applied state, and relevant decisions/specifications.
- Use official Turbopuffer documentation and primary/open-source routing/catalog examples.
- Define at least two viable architectures, their authority boundaries, failure modes, and migration paths.
- Provide a candidate catalog model with Data Vault 2.0 mapping, provenance, ACL, version, and embedding-contract fields.
- Define routing flow, compatibility checks, fallback behavior, and explicit non-goals.
- Propose offline eval cases and metrics for namespace-selection recall, over-selection, latency, cost, ACL safety, and final answer quality.
- State what can be tested without live Turbopuffer access.
- Recommend the smallest experiment, not an implementation.

## Explicit exclusions

- Product code, schemas, migrations, CLI/UI changes, live retrieval, live writes, or namespace mutation.
- Selecting a proprietary managed catalog or graph service when an open-source/self-hostable alternative is viable.
- Assuming catalog metadata ratifies Data Vault business meaning.

## Evidence expectations

Record source URLs, versions/dates where available, inspected local paths, competing options, null findings, cost/scale limits, and confidence. Distinguish documented facts from recommendations.

## Blockers

None for research. Architecture selection and implementation remain blocked on synthesis and user ratification.

## Progress and notes

- 2026-07-15: Ticket opened from the ratified four-track research plan. Execution intentionally deferred from the ticket-authoring turn.
- 2026-07-15: Inspected the parent plan, broad preliminary research, active namespace/retrieval/state/artifact contracts, completed implementation records, and relevant Buoy source. The requested worktree-root `context.md` and `plan.md` were absent; durable ticket/parent records were available.
- 2026-07-15: Researched official Turbopuffer namespace/query/metadata/schema/permission/limit documentation, Data Vault 2.0 authority and lineage sources, and open-source/self-hostable catalog, lineage, and semantic-routing implementations. No live service call or mutation occurred.
- 2026-07-15: Produced `.10x/research/2026-07-15-data-vault-namespace-catalog-routing.md` with separated facts/recommendations, three competing architectures, candidate identity/catalog/history model, fail-closed routing and fallback design, offline evals, local implications, smallest experiment, limits, and unresolved semantic blockers. Ticket intentionally remains active for independent review.
- 2026-07-15: Repaired the independent review findings: corrected `semantic-router` licensing from its repository license, distinguished Turbopuffer atomic upsert/conditional-write guarantees from absent general and cross-namespace/relational transaction semantics, added explicit policy/concept/source-revision relationship shapes, replaced the dead Data Vault Alliance URL with accessible and qualified Alliance sources, and added a held-out evaluation protocol. Scope remains research-only and the ticket remains active pending review.

- 2026-07-15: Closure after independent pass re-review. Acceptance mapping: (1) local namespace discovery, multi-namespace retrieval, plan artifacts, applied state, decisions, and specifications are enumerated in the research's “Local authority inspected completely” section and were source-spot-checked by the prior review; (2) official Turbopuffer documentation plus primary/open-source catalog, lineage, routing, licensing, and qualified Data Vault sources are recorded under “External sources,” with corrected claims freshly reproduced by the re-review; (3) Architectures A–C each state authority boundaries, failure modes, migration paths, and assessments; (4) the candidate catalog model includes Data Vault mappings, provenance, ACL and effective relationship records, versions, and embedding contracts; (5) “Candidate routing and fallback design” defines deterministic authorization/compatibility gates, bounded selection, conservative fallback, and non-goals; (6) “Offline evaluation design” covers route recall, over-selection, latency, cost/load, ACL and compatibility safety, lifecycle safety, and final answer quality with a held-out protocol; (7) “What can be tested without live Turbopuffer access” separates reproducible offline tests from unmeasured live behavior; and (8) “Smallest proposed experiment” remains fixture-backed, offline, non-implementation work requiring separate authorization. Evidence: research commit `763107cab7165174e220b69c6ed1d88d69ee78c0`, review commit `ea6729675549dd2736da50dc607bd26be2e889e8`, repair commit `a4bfce8125aadf589e0373d2a75a8e82d630e47e`, and pass re-review commit `12a09a200b675f71384efa973e263dabf2400ba1`. No live service or product mutation occurred.
- 2026-07-15: Retrospective: independent primary-source review caught an incorrect license, overbroad transaction wording, missing relationship shapes, a dead authority URL, and an under-specified held-out protocol. The effective pattern was to keep recommendations explicitly provisional, reproduce disputed claims against primary sources, model relationships needed by the proposed predicates without inventing their business semantics, and reserve an untouched evaluation set. These lessons are captured in the repaired research and reviews; no additional knowledge, skill, implementation, or follow-up ticket is warranted because remaining architecture/product gates are already recorded as blockers in the research and parent plan.
