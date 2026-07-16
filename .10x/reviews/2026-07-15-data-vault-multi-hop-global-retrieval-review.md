Status: recorded
Created: 2026-07-15
Updated: 2026-07-15
Target: 34cab2f716d9ec13192928ce24fe335d884dd586
Verdict: concerns

# Data Vault Multi-Hop and Global Retrieval Review

## Target and method

Independently reviewed commit `34cab2f716d9ec13192928ce24fe335d884dd586` against:

- `.10x/tickets/done/2026-07-15-research-data-vault-multi-hop-global-retrieval.md`;
- `.10x/tickets/done/2026-07-15-semantic-retrieval-research-plan.md`;
- current retrieval/eval specifications, decisions, evidence, docs, implementation, and focused tests named by the research record;
- primary-paper pages, ACL Anthology entries, official project repositories, and current Microsoft GraphRAG query documentation.

The requested worktree-root `plan.md` and `progress.md` were absent, consistent with the implementation record's stated handoff limitation. No live retrieval, dataset download, index construction, benchmark, or external mutation was performed.

## Findings

### Significant — primary-source traceability does not fully meet the ticket's evidence expectations

The source table is broad and generally careful, but it remains a qualitative bibliography rather than a reproducible evidence ledger. `.10x/research/2026-07-15-data-vault-multi-hop-global-retrieval.md:57-74` does not pin repository/documentation revisions, record source-specific access dates, reproduce any paper-reported metric with its task/model/setting, or assign confidence to individual findings. The ticket explicitly requires paper/version links, reported metrics with limitations, and confidence at `.10x/tickets/done/2026-07-15-research-data-vault-multi-hop-global-retrieval.md:40-42`.

Two spot-check details also need correction or clarification:

- The official MultiHop-RAG repository identifies the paper as accepted by COLM 2024, while line 61 classifies it only as a paper/preprint. The arXiv identifier is correct and the record's transfer limitation is sound, but the evidence class is stale/incomplete.
- The title at line 62 is not the primary source's title. arXiv:2406.13213 is titled “Multi-Meta-RAG: Improving RAG for Multi-Hop Queries using Database Filtering with LLM-Extracted Metadata.” The identifier still makes the source findable, and the record correctly bounds inferred metadata as a fallible cheap control.

This gap does not overturn the recommendation because the record avoids importing paper scores as Buoy claims and explicitly limits transfer. It does prevent a cold reviewer from independently checking which reported gains motivated each arm without repeating the literature review.

### Minor — the “smallest” Buoy seed is structurally defined but not operationally bounded

Lines 229-270 correctly require namespace-qualified evidence, hop dependencies, temporal truth, ACL counterfactuals, adjudication, and immutable snapshots. However, “at least one” case per combination followed by adding cases until each arm has more than an anecdote and bootstrap uncertainty is reportable does not define a finite minimum or a label-calibration stopping rule. This only partially satisfies the ticket's request to specify the smallest Buoy-specific seed. Deferring final sample size and promotion thresholds is correct; the missing piece is a bounded pilot design whose insufficiency can be determined mechanically without inventing a product threshold.

### Correct — current Buoy baseline and baseline gaps are accurately represented

The current-source claims at lines 86-120 match the governing records and implementation: namespace-aware website/document versus repository ranking defaults, `RRF_K = 60`, one embedding with sequential explicit namespace queries, namespace-qualified result identity, whole-command failure, `doc_kind` as the only current query filter, and a single-namespace source-locator eval harness reporting NDCG@10, Recall@10, MRR@10, and Precision@5. The record correctly treats oracle namespace selection as an evaluation control rather than a current automatic router.

The B0-B8 matrix at lines 185-211 keeps current explicit multi-namespace retrieval as the control, includes metadata and decomposition before graph arms, isolates oracle versus inferred structure, requires query-class slices instead of a misleading universal average, and includes matched-context/cost and authorization ablations.

### Correct — taxonomy is useful and avoids false exclusivity

Lines 122-139 distinguish local, parallel cross-namespace, dependent multi-hop, entity, temporal, path, global, mixed local-to-global, unanswerable, and ACL-bound behavior. Treating these as overlapping labels plus hop depth, ambiguity, answerability, and temporal axes is more defensible than forcing one category per query. The taxonomy also maps each class to the smallest plausible mechanism and a concrete failure mode.

### Correct — retrieval, generation, citation, and ACL evaluation are separated

Lines 284-336 establish retrieval-only evidence recall, complete-set success, hop/bridge/path coverage, temporal correctness, global coverage, iteration diagnostics, and context efficiency before generation. Generation is then evaluated from frozen context with claim correctness, groundedness, citation precision and completeness, exact provenance, multi-source/hop coverage, temporal validity, abstention, and synthesis rubrics. LLM judges are explicitly subject to disclosed model/prompt/order/repetition and blinded human calibration.

ACL treatment is appropriately an invariant rather than an averaged metric: counterfactual principals, pre-routing/pre-ranking enforcement, derived-summary and graph-traversal leakage, cache/log/citation leakage, revocation, and separate unauthorized retrieval/citation/claim counts are covered. Zero observed disclosure blocks promotion while finite-suite residual risk remains explicit.

### Correct — cost gates and experiment order reject graph complexity early

Lines 338-365 cover index, storage, query, update/delete, governance, latency, token, storage-growth, retry, and retraction costs. The record correctly declines to invent numeric thresholds before pilot variance and operator budgets exist, while still defining baseline, metadata, decomposition, oracle, ACL, provenance, lifecycle, cost-matched, and held-out robustness gates.

The experiment order at lines 367-382 hardens labels first, measures B0, tests metadata and decomposition ceilings, limits hierarchy to long/global slices, and requires an oracle graph win before extracted-graph work. ACL/restricted-corpus ablations are present throughout the matrix, with a later dedicated adversarial lifecycle phase before promotion.

### Correct — GraphRAG claims are materially bounded

Lines 169-183 and 397-403 distinguish local entity-neighborhood search, global community-report map/reduce, DRIFT broad-to-local iteration, and graph-path retrieval. The original GraphRAG claim is limited to global sensemaking and LLM-judged comprehensiveness/diversity rather than generalized factual retrieval. Spot checks of the paper and current official query docs support that characterization. The review also confirmed RAPTOR's long-document QA framing, IRCoT/ITER-RETGEN's iterative retrieval framing, and ALCE's separate citation-quality evaluation direction.

Most importantly, lines 24 and 301 require graph arms to improve complete authorized evidence, hop/path coverage, or global source coverage over the strongest non-graph control—not merely answer fluency or judge preference. Derived edges remain routing hints, not citations or Data Vault authority.

## Criterion assessment

| Ticket criterion | Assessment | Evidence |
|---|---|---|
| Inspect current Buoy retrieval/eval architecture and records | Met | Research lines 32-55 and 86-120; verified against active specs, decision, evidence, docs, `retriever.py`, `evals.py`, and `autoresearch.py`. |
| Review primary papers and official/open-source implementations | Partially met | Broad relevant coverage at lines 57-74, but missing pinned revisions, reported metrics/settings, per-finding confidence, and two bibliographic/evidence-class corrections. |
| Define query taxonomy and baseline/evaluation matrix | Met | Lines 122-139 and 141-211. |
| Separate retrieval/generation metrics and cover citation/provenance/ACL | Met | Lines 284-336. |
| Identify public datasets and smallest Buoy seed | Partially met | Public dataset transfer matrix is strong at lines 215-227; seed schema is strong at lines 229-270 but minimum/stopping rule is not operationally bounded. |
| Define cost categories and promotion gates without unsupported numbers | Met | Lines 338-365. |
| Order experiments to reject unnecessary graph work early | Met | Lines 367-382. |
| Keep paper and GraphRAG claims bounded | Met | Lines 76-84, 169-183, 397-411. |

## Verdict

**Concerns.** The research direction, baseline matrix, metric separation, ACL/citation gates, cost controls, staged experiment order, and GraphRAG boundaries are technically sound and suitable for later synthesis. No blocker was found in the core recommendation. Before treating the child research ticket as fully evidenced, the source ledger should satisfy its explicit reproducibility contract and the Buoy pilot seed should have an operational minimum/stopping rule.

## Residual risk

- Primary implementations and docs evolve; this review spot-checked current pages but did not pin or reproduce any implementation.
- No paper benchmark or Buoy retrieval experiment was run, so all comparative benefit remains a bounded hypothesis.
- Existing Buoy labels remain assistant-drafted and single-namespace; no promotion threshold, statistical power, or human agreement is established.
- ACL, deletion/retraction, temporal correctness, entity resolution, and graph extraction remain unobserved experimentally.
