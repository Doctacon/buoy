Status: recorded
Created: 2026-07-15
Updated: 2026-07-15
Target: repair commit `fc16b4aad1a23c5e7aa0c97cd0dfb0da6ea183f4`; `.10x/research/2026-07-15-data-vault-governed-tagging-filtering.md`
Verdict: pass

# Data Vault Governed Tagging and Filtering Re-review

## Target and method

Re-reviewed repair commit `fc16b4a` against:

- `.10x/tickets/2026-07-15-research-data-vault-governed-tagging-filtering.md`
- `.10x/research/2026-07-15-data-vault-governed-tagging-filtering.md`
- `.10x/reviews/2026-07-15-data-vault-governed-tagging-filtering-review.md`
- the exact `a5729e9..fc16b4a` repair diff
- the fixed RAGFlow and Cognee source permalinks and the specific DataHub tag/term documentation added by the repair

The requested worktree-root `plan.md` and `progress.md` were absent. The executable ticket and its parent remain the available governing plan, consistent with the prior review and the research's disclosed limit. No live product, corpus, Turbopuffer namespace, or external service was mutated.

## Findings

### Correct

1. **The repair is bounded to the prior evidence-depth concerns.** Commit `fc16b4a` changes only the research record and its ticket progress note. It adds fixed implementation references, refines evidence classifications, narrows Data Vault claims, replaces the broad DataHub citation, and updates limits. It does not alter recommendations, public behavior, source, tests, or the ticket's research-only scope.

2. **The RAGFlow source claim is supported and appropriately narrow.** The fixed executor snapshot invokes per-chunk tag calculation, falls back to content tagging when needed, stores the resulting tag field, and records applied tags (`task_executor.py` at the cited snapshot, lines 559–624). The fixed search snapshot calculates both content and query tag features from `tag_kwd` (`search.py`, lines 813–837). The research claims only ingestion/query-path wiring and explicitly excludes conclusions about exact end-to-end scoring, reparsing completeness, dependencies, scale, or production quality (`.10x/research/2026-07-15-data-vault-governed-tagging-filtering.md:131-139`, `:475`).

3. **The Cognee source claim is supported and appropriately narrow.** The fixed classification snapshot creates stable `NodeSet` objects from document metadata (`classify_documents.py`, lines 64–99); chunk extraction copies `belongs_to_set` (`extract_chunks_from_documents.py`, lines 50–58); and the fixed repository tests exercise OR/AND filtering through the vector adapter and retriever (`test_pgvector.py`, lines 92–206). The research explicitly leaves unsupported-search-type behavior documentation-only and does not claim those tests were executed or that all retrievers, entity propagation, scale, or production quality were independently verified (`.10x/research/2026-07-15-data-vault-governed-tagging-filtering.md:141-149`, `:475`).

4. **The Data Vault evidence limitation is now explicit enough to prevent authority laundering.** The evidence table classifies the Databricks explainer as non-primary, low-to-medium-confidence, vocabulary-only evidence (`.10x/research/2026-07-15-data-vault-governed-tagging-filtering.md:71-81`). The findings make no normative loading, effectivity, retention, erasure, or physical-design claim and require validation against the enterprise methodology and owners before implementation (`:163-181`, `:476`). The candidate Hub/Link/Satellite mapping therefore remains clearly architectural synthesis rather than a standards claim.

5. **The DataHub comparison now has direct documentation support.** The specific official Tags tutorial describes tags as informal, loosely controlled labels, while the Terms tutorial describes a standardized shared vocabulary associated with physical assets. This directly supports the limited label-versus-glossary distinction at `.10x/research/2026-07-15-data-vault-governed-tagging-filtering.md:183-189`; the record still disclaims workflow, governance, scale, and fitness equivalence.

6. **Ticket acceptance remains fully supported.** The repair does not weaken the previously verified taxonomy, three candidate architectures and lifecycle behavior, assignment/provenance model, minimal Turbopuffer projection, single/multi-namespace filter and boost semantics, ACL separation, eval design, or bounded offline experiment. Those satisfy `.10x/tickets/2026-07-15-research-data-vault-governed-tagging-filtering.md:24-42`. The newly added implementation evidence closes the only acceptance concern about open-source source evidence where available.

### Fixed

1. **Prior concern: open-source implementation evidence was not independently established.** Resolved by fixed RAGFlow and Cognee commit permalinks plus claims limited to the exact code and tests inspected (`.10x/research/2026-07-15-data-vault-governed-tagging-filtering.md:45-50`, `:76-77`, `:131-149`).

2. **Prior concern: Data Vault support was explanatory rather than primary.** Explicitly bounded rather than overclaimed. The record now treats the source as vocabulary-only and carries enterprise-methodology revalidation as an implementation prerequisite (`.10x/research/2026-07-15-data-vault-governed-tagging-filtering.md:62-67`, `:78`, `:163-181`, `:476`). This is the correct resolution because no primary methodology source was available.

3. **Prior concern: the DataHub citation was too broad.** Resolved with specific official tag and glossary-term tutorials and a claim no broader than those pages support (`.10x/research/2026-07-15-data-vault-governed-tagging-filtering.md:64`, `:80`, `:183-189`).

### Blocker

None for accepting the research ticket's deliverable.

### Note

The research's implementation decisions at `.10x/research/2026-07-15-data-vault-governed-tagging-filtering.md:457-469` remain intentionally unratified. They are correctly bounded implementation blockers, not deficiencies in this research deliverable.

## Criterion assessment

| Ticket criterion | Assessment | Evidence |
|---|---|---|
| Inspect current tagging, schema, retrieval/output, plans, and drift owner | Satisfied | Research `:94-102`; unchanged from the prior verified review. |
| Classify tagging modes and authority safety | Satisfied | Research `:104-119`; authority, derivation, concepts, and ACLs remain separate. |
| Compare at least two architectures with lifecycle behavior | Satisfied | Research architecture section provides three candidates and update/deletion/reprocessing behavior. |
| Provide provenance and minimal Turbopuffer models | Satisfied | Candidate term/assignment/projection models and minimal materialized attributes remain explicit and bounded. |
| Define single/multi-namespace filter and boost semantics | Satisfied | Candidate semantics remain recommendations and preserve ACL and compatibility boundaries. |
| Propose required evaluation families | Satisfied | Assignment, retrieval, false-exclusion, ACL, drift, lifecycle, and cost evals remain covered. |
| Recommend the smallest experiment, not implementation | Satisfied | One-namespace, 10–30-term, offline, no-live-write experiment remains the recommended first step. |
| Meet evidence expectations | Satisfied | Official docs, local evidence, fixed open-source source snapshots, confidence classes, limits, and failure cases are recorded. |

## Verdict

**Pass.** Repair commit `fc16b4a` resolves the prior review concerns or explicitly bounds them at the strength the available evidence permits. The governed-tagging research satisfies the executable ticket and is ready for parent synthesis. No blocker was found.

## Residual risk

- No live corpus, Turbopuffer namespace, or end-to-end RAGFlow/Cognee system was exercised; quality, latency, cost, and operational behavior remain unmeasured as disclosed.
- Detailed Data Vault loading, effectivity, retention, erasure, and physical-design semantics still require the actual enterprise methodology and owner before implementation.
- Product semantics, thresholds, ACL ownership/SLOs, stale-row policy, and public retrieval compatibility remain intentionally unratified and must not be inferred from this research.
