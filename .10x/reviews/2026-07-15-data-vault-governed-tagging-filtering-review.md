Status: recorded
Created: 2026-07-15
Updated: 2026-07-15
Target: commit `a1680819583a8d3e0a0ed7dabcbfa9350875bfe7`; `.10x/research/2026-07-15-data-vault-governed-tagging-filtering.md`
Verdict: concerns

# Data Vault Governed Tagging and Filtering Review

## Target and method

Independently reviewed commit `a168081` against:

- `.10x/tickets/done/2026-07-15-research-data-vault-governed-tagging-filtering.md`
- `.10x/tickets/done/2026-07-15-semantic-retrieval-research-plan.md`
- `.10x/tickets/2026-07-15-reconcile-retrieval-tag-output.md`
- the active retrieval specification, preliminary research, current Buoy tagging/schema/retrieval/diff/apply source, and relevant tests
- official Chief, RAGFlow, Cognee, Turbopuffer, SKOS, DataHub, OpenMetadata, and Databricks/Data Vault comparison pages cited by the research

The requested worktree-root `plan.md` and `progress.md` were absent at review time. The executable ticket and its parent supplied the available governing plan. No live Turbopuffer query, product-data access, or external mutation was performed.

Primary-source spot checks included Turbopuffer's official Markdown documentation for permissions, query consistency, writes, and limits; Cognee's official NodeSets Markdown page; Chief's official Collection and Concept help pages; and the official RAGFlow tag-set page. Local claims were checked against commit `a168081` source rather than accepted from the research prose.

## Findings

### Correct

1. **Authority classes and ACLs are separated clearly.** The tagging taxonomy distinguishes structural, steward-controlled, source-authoritative, rule-derived, similarity-derived, open-set LLM, first-class concept, and authorization classes (`.10x/research/2026-07-15-data-vault-governed-tagging-filtering.md:99`). The proposed projection keeps `governed_tag_ids`, `derived_tag_ids`, user/group ACLs, explicit public state, and ACL revision separate (`:276`), and the query/lifecycle rules make ACL filtering mandatory and fail-closed (`:298`, `:355`). This directly satisfies the ticket's central authority/derived/ACL boundary and does not treat confidence or topical affinity as authorization.

2. **Local-source claims are supported.** Buoy declares `tags` as `[]string` (`src/buoy_search/chunker.py:60-71`), copies page-level derived tags to every chunk (`src/buoy_search/chunker.py:255-295`), preserves them in plan records and writes them to rows (`src/buoy_search/plan_artifacts.py:347-380`, `:444-482`), but does not request or expose them during retrieval (`src/buoy_search/retriever.py:33-43`, `:106-140`). The documentation drift is real (`docs/retrieval.md:54`) and remains assigned to the blocked ticket rather than being silently resolved. Row identity and incremental comparison omit tags (`src/buoy_search/plan_artifacts.py:176-195`, `src/buoy_search/plan_diff.py:137-163`), supporting the warning that an external assignment-only change needs a deliberate metadata update path.

3. **Lifecycle and retained-stale-row analysis identifies the material local hazard.** Applied state distinguishes active, retained-stale, and deleted rows (`src/buoy_search/applied_state.py:32-37`); apply retains stale rows unless deletion is explicitly selected (`src/buoy_search/apply.py:377-425`); and tests confirm retained stale rows remain tracked and may reactivate (`tests/test_plan_diff.py:205-232`). The research therefore correctly warns that updating only active rows does not retract old remote searchable projections (`.10x/research/2026-07-15-data-vault-governed-tagging-filtering.md:344`). It also covers rename, deprecation, split/merge, complete-run replacement, partial reprocessing, source deletion, and projection reconciliation (`:328-363`, `:392-407`).

4. **Chief, RAGFlow, Cognee, and Turbopuffer claims are appropriately bounded.** Chief's official Collection page confirms saved label-based scopes with the stated group/global include/exclude operators; its Concept pages describe automatic/manual concepts and source-backed navigation. RAGFlow's official tag-set documentation supports the closed-set similarity versus open-set keyword distinction and reparsing lifecycle. Cognee's official NodeSets Markdown confirms propagation to documents/chunks/entities, first-class `NodeSet`/`belongs_to_set` graph materialization, OR-by-default/AND filtering, and the named unsupported search types. Turbopuffer's official docs confirm filter-based permissions rather than built-in row RBAC, explicit `is_public`, empty permission arrays meaning no access, single-namespace queries, multi-query/RRF, strong/eventual consistency behavior, whole upsert and patch/delete operations, and the quoted current limits. The research consistently labels these as documented behavior rather than measured quality (`.10x/research/2026-07-15-data-vault-governed-tagging-filtering.md:67-85`, `:116-152`).

5. **Data Vault treatment is cautious rather than authority-laundering.** The record limits its source confidence because it did not inspect the licensed methodology, calls the proposed Hub/Link/Satellite mapping a recommendation rather than a normative standard mapping, and keeps inferred observations from overwriting approved assignments (`.10x/research/2026-07-15-data-vault-governed-tagging-filtering.md:154-172`). Architecture B is conditional on an existing governed Data Vault and explicitly names durable-history/privacy-erasure tension (`:252-260`). That is proportionate to the available evidence.

6. **Filter/boost semantics are testable and do not become accidental requirements.** ANY, ALL, EXCLUDE ANY, EXCLUDE ALL, missing-value, hierarchy-expansion, and namespace-compatibility behavior are stated as candidate semantics (`.10x/research/2026-07-15-data-vault-governed-tagging-filtering.md:294-326`). Hard filters are reserved for explicit/authoritative constraints after false-exclusion measurement; probabilistic tags remain bounded boosts. ACL conjunction is invariant across ANN, BM25, fallback, reranking, aggregation, and fusion paths.

7. **The eval plan is unusually complete for a research ticket.** It covers assignment precision/recall/F1 and calibration, propagation, retrieval and routing quality, false exclusion, single/multi-namespace behavior, ACL non-exposure and revocation, taxonomy drift, stale/reprocessing reconciliation, latency/write/storage/steward cost, ablations, and promotion gates (`.10x/research/2026-07-15-data-vault-governed-tagging-filtering.md:365-419`). Thresholds are intentionally left for ratification rather than invented.

8. **Recommendation scope is proportional.** Although Architecture A is the preferred governed end state, the actual first step is a 10–30-term, one-namespace, non-sensitive, offline fixture experiment with a no-tag/structural baseline and no public behavior or live write (`.10x/research/2026-07-15-data-vault-governed-tagging-filtering.md:422-434`). Architecture C is retained as the smallest metadata-only comparator, and enterprise Data Vault/catalog/graph adoption is deferred. This meets the request for a controlled experiment rather than implementation.

### Concern

1. **Minor — open-source implementation evidence is not independently established.** The ticket asks for open-source implementation evidence where available, but the record explicitly relies on official RAGFlow and Cognee documentation and says their source paths were not audited (`.10x/research/2026-07-15-data-vault-governed-tagging-filtering.md:67-85`, `:462-471`). The spot-checked documentation supports the claims, so this does not undermine the proposed boundaries; however, future architecture synthesis should not treat those documented mechanics as source-verified implementation or production-quality evidence.

2. **Minor — Data Vault history support is explanatory, not primary-methodology evidence.** The only Data Vault-specific external source is a Databricks explainer, which the record correctly identifies as less than the full Data Vault 2.0 standard (`.10x/research/2026-07-15-data-vault-governed-tagging-filtering.md:35-65`, `:67-85`). The basic Hub/Link/Satellite/history framing is reasonable and the proposed mapping is explicitly non-normative, but retention, physical erasure, effectivity, and loading semantics must be revalidated against the actual enterprise Data Vault authority before implementation.

3. **Minor — the DataHub citation is broad.** The cited generic metadata-model page does not by itself strongly substantiate the specific lightweight-tag versus governed-glossary comparison at `.10x/research/2026-07-15-data-vault-governed-tagging-filtering.md:174-180`. OpenMetadata and SKOS provide stronger direct support, and the comparison is only vocabulary guidance, so the recommendation remains sound. A synthesis record should cite DataHub's specific tag and glossary-term documentation if that comparison becomes decision-bearing.

No blocker was found.

## Criterion assessment

| Ticket criterion | Assessment | Evidence |
|---|---|---|
| Inspect current deterministic tags, schema, retrieval/output, plan artifacts, and blocked drift | Satisfied | Research `:89-97`; verified against the local paths cited above and the blocked ticket. |
| Taxonomy of modes and authority safety | Satisfied | Research `:99-114`; authority, derivation, concept, and ACL classes remain distinct. |
| At least two architectures with update/deletion/reprocessing | Satisfied | Research `:236-274`; three architectures are compared with lifecycle and cost. |
| Assignment/provenance model and minimal Turbopuffer projection | Satisfied | Research `:182-234`, `:276-292`; documented limits and repairable projection are addressed. |
| Single/multi-namespace query and compatibility semantics | Satisfied | Research `:294-326`; explicitly recommendations, with blocked public behavior preserved. |
| Precision/recall, retrieval, false exclusion, ACL, drift, and cost evals | Satisfied | Research `:365-419`; all requested eval families and promotion gates are present. |
| Smallest controlled-tag experiment, not implementation | Satisfied | Research `:422-434`; offline and bounded, with no live/public change. |
| Evidence expectations | Satisfied with concerns | Official documentation, local evidence, confidence, limits, and failure cases are recorded; open-source source implementation evidence and primary Data Vault methodology remain explicitly unverified. |
| Parent shared invariants | Satisfied | Authority/projection separation, provenance, ACLs, open/self-hostable options, metadata-only baseline, lifecycle/cost, and measurable evals are all covered. |

## Verdict

**Concerns.** Commit `a168081` is factually careful, locally well-supported, complete against the executable ticket, and proportionate. The concerns are evidence-depth limits already substantially disclosed by the research; they do not block integration of this research record, but they prevent treating product internals, open-source implementation quality, or detailed Data Vault loading/retention behavior as verified architecture authority.

## Residual risk

- No live corpus or Turbopuffer namespace was measured, so quality, latency, cost, tag distribution, projection lag, and remote stale-row prevalence remain unknown.
- Chief internals and ACL/scoring behavior are private and were not inferred.
- RAGFlow and Cognee source/dependency behavior was not audited beyond official documentation.
- Data Vault effectivity, retention/erasure, and stewardship semantics require confirmation from the actual enterprise authority before implementation.
- Public tag output/filter behavior, exact grammar/boost weights, missing-schema compatibility, taxonomy ownership, ACL source of truth, revocation SLO, and numerical gates remain intentionally blocked for user ratification.
