Status: done
Created: 2026-07-15
Updated: 2026-07-15
Parent: .10x/tickets/2026-07-15-semantic-retrieval-research-plan.md
Depends-On: None

# Research Data Vault Governed Tagging and Filtering

## Scope

Research governed tagging for namespaces, sources, documents, and chunks, including exact metadata filtering and relevance boosts. Distinguish Data Vault 2.0 business metadata from structural tags and probabilistic inferred labels.

Execute in branch `work/research-data-vault-tagging` in its own worktree based on current `develop`. Produce `.10x/research/2026-07-15-data-vault-governed-tagging-filtering.md`. Research only; do not implement.

## Questions

- Which tags are authoritative, human-defined, rule-derived, closed-set similarity assignments, or open-set LLM extractions?
- How should tag identity, hierarchy/synonyms, taxonomy version, assignment source, confidence, reviewer state, and effective history be modeled?
- Which fields should be materialized onto Turbopuffer chunks for filtering/ranking, and which provenance belongs in an external authoritative store?
- How do Chief Labels/Collections, RAGFlow tag sets, Cognee NodeSets, and comparable open-source tools apply, update, remove, and query tags?
- What should AND/OR/exclusion, namespace-level versus chunk-level, and filter-versus-boost semantics be?
- How are ACL tags kept separate from topical relevance tags so retrieval cannot bypass authorization?

## Acceptance criteria

- Inspect Buoy's current deterministic tags, Turbopuffer schema, retrieval filters/output, plan artifacts, and the blocked tag-output drift ticket.
- Build a taxonomy of tagging modes and identify which are safe as authority versus derived hints.
- Define at least two candidate tagging architectures with update/deletion/reprocessing behavior.
- Provide a candidate assignment/provenance model and a minimal materialized Turbopuffer attribute model consistent with documented limits.
- Define query semantics and compatibility impacts for single- and multi-namespace retrieval without turning examples into requirements.
- Propose evals for tag precision/recall, routing/retrieval quality, false exclusion, ACL safety, taxonomy drift, and operating cost.
- Recommend the smallest controlled-tag experiment, not an implementation.

## Explicit exclusions

- Implementing retrieval tag output/filtering, resolving `.10x/tickets/2026-07-15-reconcile-retrieval-tag-output.md`, or changing public behavior.
- Treating LLM-inferred tags as Data Vault authority.
- Live Turbopuffer operations or proprietary-only taxonomy services.

## Evidence expectations

Record official documentation, open-source implementation evidence where available, inspected local paths, taxonomy/version tradeoffs, failure cases, and confidence. Separate product claims from measured evidence.

## Blockers

None for research. Tag semantics and implementation remain blocked on findings, synthesis, and user ratification.

## Progress and notes

- 2026-07-15: Ticket opened from the ratified four-track research plan. Execution intentionally deferred from the ticket-authoring turn.
- 2026-07-15: Inspected the parent plan, preliminary research, blocked tag-output drift ticket, referenced active records, and Buoy tagging/schema/retrieval/applied-state source. Reviewed official Chief, RAGFlow, Cognee, and Turbopuffer documentation plus Data Vault and open taxonomy/catalog comparisons. Drafted `.10x/research/2026-07-15-data-vault-governed-tagging-filtering.md`; ticket remains active pending independent review.
- 2026-07-15: Addressed only the independent review's evidence-depth concerns. Added fixed RAGFlow/Cognee source spot-check permalinks and bounded what they corroborate; classified evidence and confidence explicitly; narrowed Data Vault claims to non-primary vocabulary pending enterprise methodology validation; and replaced the broad DataHub link with specific official tag/term documentation. Record-only repair; ticket remains active for reviewer verification.
- 2026-07-15: Closure criterion mapping after the pass re-review in `.10x/reviews/2026-07-15-data-vault-governed-tagging-filtering-rereview.md`:
  - Current deterministic tags, Turbopuffer schema, retrieval/output drift, plan artifacts, and the blocked public tag-output owner were inspected and documented in the research's local findings.
  - The research classifies structural, human-governed, source-authoritative, rule-derived, similarity-derived, open-set LLM, concept, and ACL modes and states which may serve as authority.
  - Architectures A, B, and C cover update, deletion, correction, and reprocessing behavior.
  - Candidate term/assignment/projection provenance and a minimal Turbopuffer attribute projection are documented with evidence limits.
  - Candidate ANY/ALL/exclusion, filter/boost, single-namespace, multi-namespace, missing-value, and ACL-conjunction semantics are recommendations only; public compatibility remains blocked.
  - Evals cover assignment precision/recall, retrieval/routing quality, false exclusion, ACL safety, taxonomy/lifecycle drift, and operating cost.
  - The recommended experiment remains a bounded offline 10–30-term, one-namespace comparison with no live writes or public behavior change.
  - The pass re-review confirms all ticket criteria and evidence expectations are satisfied; its residual risks are disclosed research limits or intentionally unresolved implementation decisions, not closure blockers.
- 2026-07-15: Retrospective — The durable lesson is to classify evidence strength explicitly and bind open-source implementation claims to fixed source snapshots; that learning is incorporated directly into the completed research record. No implementation semantics were ratified by closure. The blocked public tag-output/filtering ticket remains the owner for that behavior, while taxonomy ownership, ACL policy, stale-row handling, thresholds, and Data Vault operational semantics remain unresolved prerequisites for any future implementation. No additional skill, knowledge record, or follow-up ticket is warranted beyond those existing owners and blockers.
