Status: done
Created: 2026-07-15
Updated: 2026-07-15

# Data Vault Multi-Hop and Global Retrieval

## Scope correction — no Data Vault architecture

The user clarified after this research closed that Data Vault was only an analogy for stable concepts and relationships. `.10x/decisions/data-vault-is-analogy-not-architecture.md` governs: Buoy will not build or require hubs, links, satellites, warehouse authority, or Data Vault loading.

Retain this record's query taxonomy, current-RRF baseline, metadata/decomposition/iteration/hierarchy/graph experiment order, citation and ACL gates, source-ledger findings, and bounded pilot design. Reinterpret Data Vault temporal-authority examples as generic versioned concept/relationship truth fixtures; recommendations requiring an actual Data Vault are withdrawn.

## Question

Which retrieval and evaluation strategies are justified for Buoy questions that require evidence across namespaces, multiple hops, entity relationships, historical state, or corpus-wide synthesis, and what evidence should be required before adding graph or hierarchical indexing beyond current explicit multi-namespace reciprocal-rank fusion (RRF)?

This investigation is research only. It does not select an architecture, ratify query semantics, build a dataset, run an evaluation, construct a graph, or change retrieval.

## Executive conclusion

Buoy should not begin with a general knowledge graph. The evidence supports a staged comparison in which the current explicit multi-namespace hybrid retrieval plus RRF remains the control, then progressively more expensive mechanisms are admitted only for the query class they can plausibly solve:

1. improve and measure explicit namespace selection and current RRF;
2. add metadata routing/filtering where the discriminating facts already exist as governed attributes;
3. test query decomposition and iterative retrieval for compositional questions;
4. test hierarchical summaries only for long-document or corpus-level synthesis;
5. test graph-local or graph-path retrieval only where stable entities/relations and gold hop paths exist;
6. test GraphRAG global or DRIFT-style search only for corpus-wide sensemaking, not as a default factual retriever.

The strongest finding is methodological: an answer-quality improvement does **not** establish a retrieval improvement. A graph is promoted only if it increases retrieval of the complete, authorized gold evidence set (including hop coverage and citations) over metadata/decomposition controls, with acceptable index/query cost and deletion/correction behavior. Graph-produced fluent summaries without better evidence recall, citation support, and ACL correctness are not a win.

Public multi-hop benchmarks are useful for mechanism screening but do not model Buoy's namespace boundaries, embedding compatibility, Data Vault authority, source lineage, or ACLs. A small reviewed Buoy dataset with namespace-qualified chunk judgments, hop dependencies, temporal validity, answerability, and per-principal access expectations is therefore required before any architecture decision.

## Sources and methods

Research was performed 2026-07-15 from the current Buoy source and durable project records, primary papers, paper repositories, and official/open-source implementation documentation. No live Turbopuffer request, index construction, benchmark run, or product-data mutation occurred.

### Local authority inspected

- `.10x/tickets/2026-07-15-semantic-retrieval-research-plan.md`
- `.10x/tickets/done/2026-07-15-research-data-vault-multi-hop-global-retrieval.md`
- `.10x/research/2026-07-15-metadata-tagging-graphs-and-data-vault.md`
- `.10x/specs/explicit-multi-namespace-retrieval.md`
- `.10x/specs/repo-search-eval-autoresearch.md`
- `.10x/decisions/namespace-ranking-defaults.md`
- `.10x/evidence/2026-06-28-cross-corpus-live-retrieval-evals.md`
- `.10x/evidence/2026-06-28-cross-corpus-seed-eval-datasets.md`
- `.10x/evidence/2026-06-28-graded-repo-eval-metric-validation.md`
- `.10x/evidence/2026-06-28-live-turbo-search-repo-index-and-eval.md`
- `.10x/evidence/2026-07-14-explicit-multi-namespace-retrieval.md`
- `.10x/reviews/2026-07-14-explicit-multi-namespace-retrieval-review.md`
- `.10x/tickets/done/2026-07-14-add-explicit-multi-namespace-retrieval.md`
- `docs/retrieval.md`
- `docs/evaluation.md`
- `src/buoy_search/retriever.py`
- `src/buoy_search/evals.py`
- `src/buoy_search/autoresearch.py`
- `tests/test_multi_namespace_retrieval.py`
- `tests/test_evals.py`

The task referred to worktree-root `context.md` and `plan.md`; neither path existed in this worktree. The executable ticket, parent plan, broad preliminary research, governing records, and source provided sufficient bounded authority for this research-only execution. This missing handoff material is recorded as a limit rather than silently reconstructed.

### Primary research and official/open-source sources

All web sources below were retrieved on 2026-07-15. An arXiv version or repository commit is recorded when the primary source exposed one; a retrieval date is the pin for mutable documentation pages. Confidence applies to the narrow finding in the final column, not to transfer into Buoy.

| Topic | Source and evidence class | Version/revision | Finding, limitation, and confidence |
|---|---|---|---|
| Multi-hop benchmark | Tang and Yang, **MultiHop-RAG: Benchmarking Retrieval-Augmented Generation for Multi-Hop Queries**, arXiv:2401.15391; official dataset/code: `https://github.com/yixuantt/MultiHop-RAG` | arXiv v1; repository `3dd4d4e79fc9843008b8f832da99086a82f1a805` | **COLM 2024-accepted paper** plus open-source artifacts. Provides multi-document query types and separate retrieval/generation evaluation. **Confidence: high** that the paper/repository report this benchmark shape and publication status; **low transfer confidence** because its curated news corpus is not a namespace/ACL benchmark. |
| Metadata-filtered multi-hop RAG | **Multi-Meta-RAG: Improving RAG for Multi-Hop Queries using Database Filtering with LLM-Extracted Metadata**, arXiv:2406.13213 | arXiv v2 | Primary preprint showing query-derived domain metadata narrowing retrieval on MultiHop-RAG. **Confidence: medium** because this is a non-peer-reviewed source result; useful as a cheaper-control hypothesis, not proof that inferred metadata is safe or universal. |
| Decomposition with retrieval | Press et al., **Measuring and Narrowing the Compositionality Gap in Language Models**, arXiv:2210.03350 (Self-Ask); `https://github.com/ofirpress/self-ask` | arXiv v3; repository `559e56ec1ba8dc93cf63c4148ec1f4717caf4b60` | Explicit follow-up questions expose decomposition. **Confidence: high** in the peer-reviewed mechanism description; **low transfer confidence** because search snippets/answers are not Buoy evidence with provenance. |
| Interleaved reasoning/retrieval | Trivedi et al., **Interleaving Retrieval with Chain-of-Thought Reasoning for Knowledge-Intensive Multi-Step Questions**, arXiv:2212.10509 / ACL 2023 (IRCoT); `https://github.com/StonyBrookNLP/ircot` | arXiv v2; repository `3c1820f698eea5eeddb4fba3c56b64c961e063e4` | Supports retrieval conditioned on partial reasoning. **Confidence: high** in the peer-reviewed mechanism; transfer remains unproven and reasoning traces may amplify a wrong hop. |
| Iterative retrieval/generation | Shao et al., **Enhancing Retrieval-Augmented Large Language Models with Iterative Retrieval-Generation Synergy**, arXiv:2305.15294 / EMNLP 2023 (ITER-RETGEN) | arXiv v2 | Generated context can guide another retrieval round. **Confidence: high** in the peer-reviewed mechanism; it does not settle Buoy stopping, provenance, or ACL behavior. |
| Hierarchical retrieval | Sarthi et al., **RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval**, arXiv:2401.18059 / ICLR 2024; `https://github.com/parthsarthi03/raptor` | arXiv v1; repository `7da1d48a7e1d7dec61a63c9d9aae84e2dfaa5767` | Clusters and recursively summarizes chunks into a tree. **Confidence: high** in the peer-reviewed long-document QA result; **low transfer confidence** because summary nodes add Buoy citation-lineage and lifecycle obligations. |
| GraphRAG global search | Edge et al., **From Local to Global: A Graph RAG Approach to Query-Focused Summarization**, arXiv:2404.16130; Microsoft Research publication; `https://github.com/microsoft/graphrag` | arXiv v2; repository `dac4f721ddc14adae9d3183cdc99e7c6ad7d9fca` | Evidence is for global sensemaking with entity/community summaries, judged mainly for comprehensiveness/diversity. **Confidence: medium** because this is a primary research report dominated by LLM pairwise judging, not an independent replication or universal factual-retrieval result. |
| GraphRAG local/global/DRIFT | Microsoft GraphRAG official query docs: `https://microsoft.github.io/graphrag/query/overview/`, `.../local_search/`, `.../global_search/`, and `.../drift_search/` | Mutable docs retrieved 2026-07-15 | Local expands from entities; global map-reduces community reports; DRIFT combines broad entry with local follow-ups. **Confidence: high** for documented behavior, **none** as independent comparative-quality evidence. |
| Graph-guided chunk expansion | Zhu et al., **Knowledge Graph-Guided Retrieval Augmented Generation (KG²RAG)**, arXiv:2502.06864 / NAACL 2025; `https://arxiv.org/abs/2502.06864v1`; `https://aclanthology.org/2025.naacl-long.449/` | arXiv v1; NAACL 2025 long-paper publication; no implementation pin recorded | Starts with semantic chunk seeds, expands through KG relations, then organizes chunks. **Confidence: high** in the peer-reviewed mechanism description; transfer to Buoy derived graphs remains untested. |
| Graph retrieval | He et al., **G-Retriever: Retrieval-Augmented Generation for Textual Graph Understanding and Question Answering**, arXiv:2402.07630 / NeurIPS 2024; `https://github.com/XiaoxinHe/G-Retriever` | arXiv v3; repository `315b0ff8a206536067602fb97e77c10f4d646d5d` | Retrieves a query-relevant subgraph using a prize-collecting Steiner-tree formulation. **Confidence: high** in the peer-reviewed graph-QA mechanism; **low transfer confidence** for a derived document/entity graph. |
| Memory/graph traversal | Gutierrez et al., **HippoRAG: Neurobiologically Inspired Long-Term Memory for Large Language Models**, arXiv:2405.14831 / NeurIPS 2024; `https://github.com/OSU-NLP-Group/HippoRAG` | arXiv v3; repository `1e8f60981bf760b64003aa5bf5668126d0c106b3` | Uses an extracted knowledge graph and Personalized PageRank for associative retrieval. **Confidence: high** in the peer-reviewed mechanism; extraction/entity-resolution remains a Buoy confounder. |
| Citation evaluation | Gao et al., **Enabling Large Language Models to Generate Text with Citations**, arXiv:2305.14627 / EMNLP 2023 (ALCE); `https://github.com/princeton-nlp/ALCE` | arXiv v2; repository `246c476a4edfc564266b7346b6e29ef4861ae937` | Separates citation correctness and completeness from answer quality. **Confidence: high** in the peer-reviewed evaluation separation; automated citation judging still needs human calibration. |
| Public multi-hop QA | HotpotQA (`https://hotpotqa.github.io/`), 2WikiMultiHopQA (`https://github.com/Alab-NII/2wikimultihop`), MuSiQue (`https://github.com/StonyBrookNLP/musique`), IIRC (`https://allenai.org/data/iirc`) | HotpotQA page retrieved 2026-07-15; 2Wiki commit `13800e5be57df1b4040b9b1588c6c811779e69e9`; MuSiQue commit `922ac98f19a201998dbdae6d7f2887a5258dbdeb`; IIRC page retrieved 2026-07-15 | Official sources expose supporting facts, decompositions, linked paragraphs, or incomplete-information cases. **Confidence: high** in available supervision, **low transfer confidence** for namespace routing/ACL semantics. |
| Vector/filter baseline | Turbopuffer query/filter/multi-query documentation: `https://turbopuffer.com/docs/query`, `https://turbopuffer.com/docs/metadata`, `https://turbopuffer.com/docs/permissions` | Mutable docs retrieved 2026-07-15 | Documents namespace-local ANN/BM25, filters, multi-query/RRF, and filter-based access enforcement. **Confidence: high** for documented service behavior, **none** as independent benchmark evidence. |

### Primary-source reported settings and results

These values are transcribed only where the primary paper supplies the task, metric, and setting. They are author-reported results, were not reproduced here, and are not Buoy success thresholds. No numeric result from the other ledger entries is used to motivate a Buoy arm.

| Source | Reported setting and result | Confidence and limitation |
|---|---|---|
| MultiHop-RAG arXiv v1, Tables 4-6 | 2,556 benchmark queries: 1,078 require two evidence items, 779 require three, 398 require four, and 301 are null. With 256-token chunks, voyage-02 retrieval followed by bge-reranker-large over 20 candidates reports Hits@10 `0.7467` and Hits@4 `0.6625`; GPT-4 generation from the top six retrieved chunks reports accuracy `0.56` versus `0.89` from gold evidence. | **High confidence that the primary paper reports these values; low transfer confidence.** Hits measures evidence occurrence on its news benchmark, and generation accuracy uses its answer protocol and model/API versions. |
| Multi-Meta-RAG arXiv v2, Table 2 | On non-null MultiHop-RAG queries, 256-token chunks with 32-token overlap, metadata filtering plus similarity top-20 and bge-reranker-large top-10: voyage-02 baseline versus Multi-Meta-RAG reports MRR@10 `0.6016`→`0.6748`, MAP@10 `0.2619`→`0.3388`, Hits@10 `0.7419`→`0.9042`, and Hits@4 `0.6630`→`0.7920`. | **Medium confidence:** exact primary-preprint table values, not peer-reviewed or reproduced. The benchmark metadata is curated and the result does not establish safety for noisy, temporal, or ACL-bearing Buoy metadata. |
| RAPTOR arXiv v1, Tables 3-4 | On QASPER with GPT-4, reported answer F1 is RAPTOR `55.7`, DPR `53.0`, BM25 `50.2`; on QuALITY dev with GPT-3, reported accuracy is RAPTOR `62.4`, DPR `60.4`, BM25 `57.3`. | **High confidence that the ICLR paper reports these values; low transfer confidence.** These are generated-answer results on long-document QA, not leaf-evidence recall, citations, ACLs, or Data Vault history. |
| GraphRAG arXiv v2, Experiment 1 / Figure 2 | Two corpora (podcast transcripts and news), 125 generated questions per corpus, each pairwise comparison repeated five times. Global graph conditions versus vector RAG report LLM-judged comprehensiveness win-rate ranges of `72–83%` (podcasts) and `72–80%` (news), and diversity ranges of `75–82%` and `62–71%`, respectively. | **Medium confidence:** exact primary-report ranges, but questions and judgments are LLM-generated, directness favors vector RAG, and no human-calibrated Buoy retrieval/citation result follows. |

### Evidence-quality rules used

- Peer-reviewed papers establish results only on their stated task, corpus, models, metrics, and implementation.
- Preprints are useful hypotheses, not settled universal results.
- Official project documentation establishes intended behavior and operational shape, not comparative quality.
- Repository READMEs establish reproducibility affordances and licensing only to the extent the inspected revision supports them.
- Vendor or project claims are not promoted to Buoy requirements.
- LLM-as-judge results are directional until prompts, models, repetitions, order effects, and human agreement are reported.
- No raw paper score is compared with a Buoy score; corpus, judgment, k, model, and answer protocol differ.

## Current Buoy baseline and gaps

### What exists

Current live retrieval is namespace-local hybrid ANN plus boosted BM25, fused by server RRF or deterministic client RRF. Final ranking is namespace-aware:

- `site-*`, `pdf-*`, and `file-*`: page grouping, no profile, pool 20, max aggregation;
- repository/general: file grouping, `repo_code`, pool 100, `adaptive_sum_3`.

Explicit multi-namespace retrieval:

- requires an operator-selected namespace list;
- normalizes and embeds once;
- queries namespaces sequentially with one region/model/precision contract;
- preserves each namespace's final ranked list;
- fuses those lists with equal-weight RRF using `RRF_K = 60`;
- retains `(namespace, row ID)` identity and namespace citation;
- fails whole on a namespace failure.

This is the correct control because it avoids comparing uncalibrated raw scores across namespaces.

Current graded evals measure per-query NDCG@10, Recall@10, MRR@10, Precision@5, and a weighted repository score. Existing datasets are source-locator judgments within one namespace; current live eval execution accepts one namespace and does not score multi-hop dependencies, complete evidence sets, citations, generation, temporal validity, routing, or ACLs. Seed labels are assistant-drafted and not human-approved.

### Material baseline gaps

1. No semantic namespace catalog or automatic router is current authority.
2. No multi-namespace eval runner exists.
3. No query decomposition, iterative retrieval, summary hierarchy, entity index, or graph retriever exists.
4. Current retrieval filters only `doc_kind`; governed metadata/tag filtering is not implemented by this ticket.
5. Retrieval output has chunk/source provenance, but no end-answer/citation evaluator.
6. No gold representation says which evidence items satisfy hop 1, hop 2, their dependency, or the complete answer.
7. No principal/ACL test fixture proves that routing, summaries, or shared entities cannot leak inaccessible evidence.
8. No catalog validates per-namespace embedding/schema compatibility before selection.

These gaps mean public benchmark reproduction and Buoy product evaluation are distinct phases.

## Query taxonomy

A query may occupy more than one class. Evaluation must label all applicable axes instead of forcing one mutually exclusive bucket.

| Class | Operational definition | Example shape | Smallest plausible mechanism | Failure to detect |
|---|---|---|---|---|
| Local factual | One chunk/page/file in one known namespace directly supports the answer. | “What flag prevents stale deletion?” | Current namespace-local hybrid retrieval. | Unnecessary decomposition/graph cost; answer drift away from primary text. |
| Cross-namespace parallel | Independent evidence from two or more explicitly known namespaces must be compared or combined; no later hop depends on an earlier answer. | “Compare the documented retry policy with the implementation.” | Current explicit multi-namespace RRF, with complete-evidence scoring. | Returning only one side while appearing plausible. |
| Multi-hop compositional | Evidence B can be located or interpreted only after resolving evidence/entity A. | “Which component owns the setting used by the workflow described in another source?” | Query decomposition or iterative retrieval; metadata if the bridge is explicit. | One-shot similarity retrieves topical but non-bridging chunks. |
| Entity-centric consolidation | Evidence about one stable business entity/key is distributed across sources or time. | “What do contracts, incidents, and account notes establish about customer X?” | Governed entity/business-key metadata; graph only for typed relationships. | Name collision, alias split, cross-tenant entity leakage. |
| Temporal/historical | Correct answer depends on event/valid-time ordering or an “as of” boundary. | “Which policy applied when the incident occurred?” | Authoritative Data Vault Hub/Link/Satellite history plus filtered retrieval. | Using current summaries/edges for historical truth; temporal leakage. |
| Relationship/path | The requested object is a relationship or constrained path among entities, potentially with several supporting assertions. | “Which vendor is connected to this control through the affected system?” | Graph-path retrieval if relations are stable and cited; otherwise decomposition. | Unsupported shortcut edges, fan-out, circular evidence. |
| Global/sensemaking | The question asks for themes, trends, coverage, contrasts, or aggregate characterization over much of a corpus; no small gold chunk set is sufficient. | “What recurring risks and counterexamples appear across all incident reviews?” | Hierarchical/community summaries, with drill-down citations. | Nearest-neighbor sampling misses corpus coverage; summaries hallucinate consensus. |
| Mixed local-to-global | Broad exploration must be followed by focused evidence gathering. | “What are the main themes, and what source evidence best supports the surprising one?” | DRIFT-like broad entry plus local follow-ups. | A global summary without evidence or local retrieval without breadth. |
| Unanswerable/negative | Authorized corpus lacks sufficient evidence, contains contradictions, or the premise is false. | “Which approved exception permits this?” when none exists. | Any arm must abstain and expose searched scope. | Fluent fabrication; graph path treated as proof. |
| ACL-bound | Any class where some relevant-looking namespaces/chunks are inaccessible to the requesting principal. | Same question under two principals with different access. | Authorization before routing/retrieval plus mandatory filters at every derived layer. | Existence, entity, summary, count, or citation leakage. |

Additional labels needed for analysis: number of required namespaces, number of gold evidence items, minimum hop depth, bridge-entity ambiguity, temporal constraint, conflict/contradiction, answerability, and whether the query names the namespace/entity explicitly.

## Candidate systems and what each tests

### B0 — current explicit multi-namespace hybrid plus RRF

The non-negotiable control. Use current namespace-local defaults and equal-weight cross-namespace rank fusion. Do not compare raw scores across namespaces. For an automatic-routing study, first run an oracle-selection version with the gold namespace set; this separates routing failure from retrieval failure.

### B1 — metadata routing/filtering

Route or filter using governed fields such as source kind, domain, entity/business key, valid time, security scope, and document kind. Evaluate separately:

- oracle/gold metadata filters, which measure the mechanism's ceiling;
- deterministic query-to-filter rules;
- inferred query metadata, which adds a classification failure surface.

Multi-Meta-RAG makes this a required cheap control: if metadata identifies the right evidence domain, a graph may add extraction/index cost without adding useful recall. Metadata results do not transfer if labels are noisy, missing, stale, or ACL-bearing fields are probabilistic.

### B2 — decomposed one-pass retrieval

Generate or author atomic subquestions, retrieve each independently, and union/fuse cited evidence. Compare oracle decomposition with model decomposition to separate retrieval capability from decomposition quality. Preserve the parent question, subquestion ID, and evidence-to-hop mapping. Do not use generated subanswers as citations.

### B3 — iterative/interleaved retrieval

Retrieve, form an intermediate hypothesis or query, retrieve again, and stop under a declared rule. IRCoT and ITER-RETGEN show why later queries can resolve bridges missed by a single query, but an early false premise can steer every later hop. Record every query, retrieved set, authorized scope, and stopping reason. Cap rounds in each declared experiment; choose the cap from pilot saturation/cost evidence rather than a product default invented here.

### B4 — hierarchical/RAPTOR-style retrieval

Index leaf chunks plus recursively clustered summaries. Test leaf-only, summary-only, and mixed-level retrieval. This arm is justified for long-document or broad thematic questions, not assumed for local facts. Every summary node must retain descendant chunk IDs and namespace/source hashes; generation must cite leaves or clearly identify summary-derived claims. Re-clustering/re-summarization after source deletion or correction is part of index cost.

### B5 — GraphRAG local search

Map query entities to graph nodes, expand through entity/relationship/community/text-unit context, then answer from the bounded neighborhood. Compare against entity metadata filters and vector-seed-plus-neighbor expansion. GraphRAG local search is an entity-centric mechanism, not a global-search substitute. Entity ambiguity, relationship provenance, and ACL-safe neighborhood expansion are first-order evaluation dimensions.

### B6 — GraphRAG global search

Map-reduce community reports or comparable hierarchical summaries across the corpus. Use only global/sensemaking cases. Measure coverage, diversity, contradiction representation, and leaf-citation completeness. The original GraphRAG evidence relies substantially on LLM-judged comprehensiveness/diversity over large corpora; it does not prove better local factual retrieval and should not be averaged with local QA as if they were the same task.

### B7 — DRIFT-style search

Use an initial broad/community answer to generate follow-up questions and retrieve local evidence iteratively. This targets mixed local-to-global queries. Its value must be isolated from simply spending more retrieval/generation calls: compare at matched or reported budgets against B3 and B6.

### B8 — graph-path retrieval

Use vector/BM25 seeds, then retrieve constrained paths/subgraphs connecting query entities or hop evidence. KG²RAG is the closest chunk-evidence pattern; G-Retriever and HippoRAG provide alternative subgraph/PPR mechanisms. Evaluate extracted-graph and oracle-graph variants separately. A derived edge is a routing hint, not authoritative evidence: answer claims must cite source chunks or authoritative Data Vault observations supporting each path edge.

## Baseline and evaluation matrix

Every arm must report results by query class; a single macro average can hide a global-query improvement purchased by local-query regressions.

| Arm | Local | Cross-namespace | Multi-hop | Entity/path | Temporal | Global | Primary comparison question |
|---|---:|---:|---:|---:|---:|---:|---|
| B0 current RRF, explicit/oracle namespaces | required | required | required | required | required | required | What does current retrieval already solve? |
| B1 governed metadata route/filter | optional | required | required | required | required | optional | Does known structure remove distractors cheaply? |
| B2 decomposition | control | required | required | optional | optional | no | Does splitting the question recover complete evidence? |
| B3 iterative retrieval | control | optional | required | required | optional | no | Does later-hop conditioning add evidence beyond decomposition? |
| B4 RAPTOR/hierarchy | control | optional | optional | no | risky | required | Do summaries improve long/global coverage while retaining leaf support? |
| B5 GraphRAG local | control | optional | required | required | risky | no | Does graph neighborhood expansion beat entity metadata/decomposition? |
| B6 GraphRAG global | no | no | no | no | risky | required | Does community synthesis improve breadth and supported claims? |
| B7 DRIFT | no | optional | required | required | risky | required | Does broad-to-local iteration beat matched-budget B3/B6? |
| B8 graph-path | control | optional | required | required | optional only with temporal edges | no | Do paths recover required bridges rather than only improve fluency? |

For each applicable cell, run these ablations where feasible:

1. oracle namespace selection versus predicted selection;
2. oracle metadata/decomposition/entity links versus inferred values;
3. retrieval-only context versus answer generation from the same context;
4. equal retrieved-token or reported-cost comparison;
5. leaf evidence with and without summary/graph expansion;
6. authorized full corpus versus principal-restricted corpus;
7. fresh index versus source correction/deletion fixture.

This factorial separation locates failure in routing, indexing, retrieval, or generation instead of crediting an entire pipeline.

## Dataset options

### Public mechanism-screening datasets

| Dataset | Best use | Reusable supervision | Transfer limits |
|---|---|---|---|
| MultiHop-RAG | Multi-document retrieval plus answer generation; comparison, inference, temporal, and unanswerable-style behavior represented in the benchmark taxonomy. | Queries, corpus, evidence/answer annotations and official evaluation artifacts. | Curated news domains and benchmark metadata are unlike independently governed Buoy namespaces; no product ACL or Data Vault history. |
| HotpotQA full-wiki/distractor | Bridge and comparison QA; supporting-fact retrieval. | Answer and supporting sentences/pages. | Wikipedia links and entities make a cleaner graph than enterprise sources; answer leakage and mature benchmark tuning are risks. |
| 2WikiMultiHopQA | Multi-hop reasoning with explicit evidence/decomposition structure. | Supporting evidence and reasoning paths/decompositions. | Template/Wikipedia construction can reward benchmark-specific shortcuts. |
| MuSiQue | Composition designed to reduce shortcut solutions. | Multi-hop questions, answers, paragraphs, decomposition/support. | Still paragraph QA, not cross-namespace routing, ACL, or historical authority. |
| IIRC | Questions needing linked information and sometimes insufficient information. | Linked context and answerability signals. | Wikipedia link-following differs from an extracted enterprise graph. |
| QASPER | Long scientific-document QA, including unanswerable questions. | Evidence spans and answers. | Better for hierarchy/long-document retrieval than cross-namespace or entity graph evaluation. |
| NarrativeQA / QuALITY | Long-document comprehension used in hierarchical-retrieval work. | Long texts and answers/multiple choice depending on dataset. | Generation/comprehension gains can occur without precise chunk/citation retrieval. |

Public screening should use each dataset's official split and metric, then add retrieval diagnostics only when gold evidence permits. It should not be mixed into one “Buoy score.” Contamination, licensing, corpus redistribution, and current official revisions must be checked before dataset acquisition; this record does not authorize downloading them.

### Smallest useful Buoy-specific seed

The minimum useful seed is not merely a list of questions and answers. It is a reviewed evidence graph over an immutable snapshot of selected test sources. The bounded pilot contains **16 distinct query cases: exactly two cases assigned to each of these eight primary strata** (a case may carry additional taxonomy labels, but counts toward only one minimum stratum):

1. local factual controls;
2. cross-namespace parallel/comparison;
3. true dependent multi-hop with a named bridge;
4. entity/path consolidation, with at least one alias or collision fixture;
5. temporal behavior, with one “as of” and one changed-fact fixture grounded in authoritative history;
6. global/sensemaking, each with an explicit theme/coverage rubric;
7. unanswerable or contradictory behavior, including at least one insufficient-evidence case;
8. ACL counterfactuals: two base queries, each executed under at least two principals with different authorized evidence (four principal-query evaluations).

Before retrieval, map each B0-B8 arm that the pilot proposes to evaluate to at least two applicable cases. Two reviewers independently complete every required case field and label against the frozen snapshot, then adjudicate every disagreement. Label calibration is complete only when every required field is populated, every evidence locator resolves to the snapshot, and every disagreement has a recorded resolution; this is a completeness rule, not an agreement-rate success threshold.

Expansion is finite: after adjudicating the 16 cases, add **at most one challenge case per primary stratum** (at most eight additional cases) only where a mechanical deficiency exists—an unresolved required field or evidence locator, both stratum cases exercise the same source/fixture pattern, or a proposed arm has fewer than two applicable cases. Independently review and adjudicate those additions once, then stop. If any deficiency remains, record the pilot as insufficient and block comparative conclusions rather than adding cases indefinitely. This pilot is descriptive and is too small for promotion inference; do not bootstrap it or set architecture success thresholds from it. Final sample size, statistical power, and numeric promotion thresholds require a later design informed by pilot variance, label friction, and ratified operator budgets.

Each case should contain:

```text
id
query
query_classes[]
principal / policy fixture
authorized_namespace_set[]
forbidden_namespace_set[]
answerability
reference_answer or global coverage rubric
gold_evidence[]:
  namespace_id
  row/chunk_id
  source locator and source hash
  relevance grade
  hop_id(s)
  valid-time / observed-time bounds when applicable
hop_dependencies[]
gold_entities/business_keys[] (when applicable)
gold_relations/path[] with supporting chunk IDs (when applicable)
required and optional claims[]
known contradictions[]
reviewers, adjudication status, snapshot/version
```

Use public, synthetic, or deliberately permissioned fixtures—not private production text—for the first ACL suite. Namespace IDs, row IDs, and source hashes are needed because URL-only matching cannot distinguish duplicated or versioned evidence across namespaces. Gold hop dependencies distinguish “retrieved two topical passages” from “retrieved the evidence chain.”

### Data Vault-specific fixtures

Formal Data Vault 2.0 authority must remain separate from derived semantic indexes:

- Hub fixtures define stable business keys and aliases.
- Link fixtures define authoritative business relationships.
- Satellite fixtures define changing descriptions and load/effective history.
- Unstructured chunks provide evidence about Hub/Link/Satellite assertions but do not silently become warehouse truth.
- Derived entity nodes, edges, concepts, summaries, and embeddings retain source `(namespace, chunk, source hash)`, extraction version, confidence, and time.

Temporal cases should include current-versus-historical answers, late-arriving observations, conflicting sources, and a correction/deletion. This reveals whether a graph or summary has flattened history.

## Retrieval metrics (before generation)

Report per query class and distribution, not only means.

1. **Namespace routing recall/precision and authorized routing recall** — whether all gold authorized namespaces were selected and irrelevant namespaces avoided.
2. **Evidence Recall@k** — fraction of relevant namespace-qualified evidence items retrieved. Preserve existing graded judgments where applicable.
3. **NDCG@k / MRR@k / Precision@k** — ranking diagnostics compatible in spirit with current Buoy evals, while reporting the exact judgment unit and k.
4. **Complete-evidence-set recall / success** — whether all required evidence items for an answer are present. This catches one-hop partial success hidden by ordinary recall.
5. **Hop recall and hop coverage** — fraction of required hops with at least one valid supporting item; report all-hop success separately.
6. **Bridge retrieval success** — whether the entity/fact needed to formulate the dependent hop was retrieved before or at that hop.
7. **Path precision/recall** — for graph arms, whether retrieved nodes/edges match gold relationships and whether each edge has source support.
8. **Entity resolution accuracy** — alias merge, collision avoidance, and correct business-key mapping.
9. **Temporal retrieval accuracy** — evidence is valid for the requested time and does not substitute a later/current fact.
10. **Global coverage** — coverage of human-defined themes/claims and representation of material counterevidence; use rubric plus source-grounded claim inventory rather than nearest-chunk relevance alone.
11. **Retrieval redundancy and context efficiency** — unique relevant evidence per retrieved token, duplicate-source rate, and irrelevant context share.
12. **Round/path diagnostics** — query and evidence by iteration, marginal new gold evidence per round, stopping reason, path length, and expansion fan-out.

A graph has improved retrieval only if graph-enabled arms beat the strongest non-graph control on complete authorized evidence, hop/path coverage, or global source coverage—not merely on generated-answer ratings.

## Generation and citation metrics

Generation is evaluated from a frozen retrieved context so retrieval and generation effects remain separable.

1. **Claim correctness / answer correctness** — exact match/F1 where appropriate; rubric or human adjudication for synthesis.
2. **Faithfulness/groundedness** — each verifiable answer claim entailed by supplied evidence; report unsupported-claim rate.
3. **Citation precision (correctness)** — cited sources actually support the associated claim.
4. **Citation completeness/recall** — supported citations exist for every externally verifiable claim, not only for some answer sentences.
5. **Citation provenance validity** — citation resolves to the exact authorized namespace/chunk/source revision used.
6. **Multi-source completeness** — citations cover every required hop/source, not several citations to one hop.
7. **Temporal citation correctness** — cited evidence was valid at the requested time.
8. **Abstention accuracy** — unanswerable/insufficient/conflicting cases produce a calibrated refusal or qualified answer.
9. **Global synthesis quality** — rubric dimensions such as comprehensiveness, diversity/non-redundancy, balance/counterevidence, and usefulness, each accompanied by cited source coverage.

Automated entailment or LLM judges may triage citation scoring, but the evaluation must publish judge model/version, prompt, ordering/randomization, repeated-run variance, and agreement with a blinded human calibration subset. Do not use the same model/configuration to generate graph summaries, answers, and unreviewed quality labels without disclosing the dependence.

## ACL, isolation, and provenance checks

ACL correctness is a safety invariant, not an average relevance metric.

For every relevant query class, run counterfactual principal pairs and check:

- unauthorized namespaces are not routed to or queried;
- mandatory chunk filters apply before ranking and generation;
- graph traversal cannot cross from an authorized node into an unauthorized supporting edge/chunk;
- shared entity names do not reveal the existence, count, relationship, title, summary, or freshness of restricted sources;
- community/hierarchical summaries are either principal-specific, computed only from a safely shareable corpus, or filtered/reconstructed so restricted contributions cannot influence output;
- caches, intermediate subqueries, logs, and citations do not leak forbidden text or identifiers;
- removal of access retracts derived searchability and cached context;
- failures and partial retrieval emit no unauthorized partial answer.

Report unauthorized retrieved items, unauthorized cited items, and unauthorized answer claims separately. Promotion requires zero observed unauthorized disclosure in the declared adversarial suite; a passing finite suite does not prove universal absence, so residual risk remains explicit.

Provenance checks require every returned leaf and every derived summary/edge to resolve to current source coordinates. A graph path is not itself a citation. If an edge has no supporting authorized leaf evidence, it may aid exploration but must not support an answer claim.

## Cost, lifecycle, and operational evaluation

### Cost categories

| Stage | Vector/metadata baseline | Hierarchical/RAPTOR | GraphRAG/graph path | Iterative/DRIFT |
|---|---|---|---|---|
| Index compute | existing chunk embedding/schema | clustering plus recursive summary generation/embedding | entity/relation/claim extraction, resolution, graph/community construction, summaries/embeddings | usually baseline index; optional graph/global index inherited |
| Storage | chunks, vectors, attributes | leaf plus summary nodes, tree memberships, lineage | nodes, edges, community reports, embeddings, provenance/history | query traces/caches; inherited indexes |
| Query work | one embedding, selected namespace ANN/BM25 and RRF | multi-level retrieval | entity mapping, neighborhood/path/PPR/subgraph retrieval | multiple retrieval and generation rounds |
| Update/delete | existing row/state reconciliation | affected ancestors may need reclustering/resummarization | entity/edge/community invalidation, dedupe and summary rebuild | cache/trace expiry plus inherited-index update |
| Human governance | source judgments, metadata | summary review policy | entity resolution, relation schema, corrections, ACL review | decomposition/stopping/failure review |

Measure wall-clock p50/p95, model and embedding calls, input/output tokens, retrieved tokens, namespaces queried, graph nodes/edges visited, storage growth, index duration, incremental update duration, deletion-to-retraction time, and failed/retry work. Use normalized units such as cost per indexed source token, cost per query, and cost per fully supported answer. Dollar cost may be added for the declared deployment, but open-source/self-hosted compute and operations are still costs.

### Promotion/stop gates

Numeric quality/cost thresholds are intentionally not invented before pilot variance and operator budgets exist. Use these evidence-backed gates in order:

1. **Baseline sufficiency gate:** if B0 meets reviewed complete-evidence and answer needs for a class, stop; added machinery has no demonstrated requirement.
2. **Metadata gate:** if B1 closes the material gap with governed attributes and passes ACL/provenance checks, do not build a graph for that class.
3. **Decomposition gate:** if B2/B3 recover the evidence chain at lower index/lifecycle burden, prefer them unless query cost or reliability violates a ratified budget.
4. **Retrieval-not-fluency gate:** reject a graph/hierarchy that improves only answer style or LLM-judge preference without better evidence/hop/global coverage and citation support.
5. **Oracle-gap gate:** if an oracle graph/decomposition/filter does not materially beat B0/B1, stop work on the inferred production version. If oracle wins but inferred does not, the blocker is extraction/routing quality, not generator quality.
6. **ACL gate:** any observed unauthorized disclosure blocks promotion regardless of average quality.
7. **Provenance gate:** derived claims/paths that cannot resolve to authorized source chunks cannot support generated answers.
8. **Lifecycle gate:** if correction, deletion, access revocation, or temporal history cannot be reconciled and verified, do not promote the derived index.
9. **Cost-matched gate:** compare quality at matched/reported token, latency, and query budgets; do not credit a method merely for making more calls or supplying more context.
10. **Robustness gate:** promote only after predeclared query-class slices and a held-out reviewed set show the benefit is not one dataset, source, model, or judge artifact. Ratify numeric thresholds after the seed establishes variance and practical budgets.

## Experiment order

This order is designed to reject unnecessary complexity early.

1. **Harden labels without running retrieval.** Review the Buoy query taxonomy, immutable source snapshot, namespace-qualified gold evidence, hop dependencies, temporal truth, and ACL counterfactuals. Calibrate human agreement.
2. **Measure B0.** Add an evaluation design for current single/explicit multi-namespace RRF. Run explicit/oracle namespace selection first; only later score a router so routing and retrieval are not confounded.
3. **Metadata ceiling then realistic metadata.** Compare oracle filters, governed fields, deterministic parsing, then inferred metadata. Stop if the cheap arm satisfies the class.
4. **Decomposition ceiling then realistic decomposition.** Compare gold subquestions, model subquestions, and iterative retrieval. Log each round and perform matched-budget ablations.
5. **Hierarchy on only long/global slices.** Test leaf-only, summary-only, and mixed RAPTOR-style retrieval, requiring descendant-leaf citation completeness and update/delete measurement.
6. **Oracle graph feasibility.** Build no production graph. On a bounded fixture, use gold entities/relations/paths to test whether graph expansion has a ceiling above metadata/decomposition. If not, reject graph complexity.
7. **Extracted graph comparison.** Only if the oracle graph wins, compare KG²RAG-style seed expansion, GraphRAG local, and a path/PPR arm. Attribute loss separately to extraction, resolution, traversal, and generation.
8. **Global/DRIFT comparison.** Only for global and mixed local-to-global cases, compare hierarchical summaries, GraphRAG global, DRIFT, and iterative non-graph retrieval at reported/matched budgets.
9. **ACL and lifecycle adversarial phase.** Exercise correction, deletion, historical “as of,” access revocation, entity collision, shared communities, caches, and summary/path retraction.
10. **Held-out replication and architecture synthesis.** Repeat across source families/models and present quality/cost/risk intervals. Architecture selection and numeric promotion thresholds require user ratification in a later record.

No stage here authorizes building datasets or running live evals; each would need its own governed spec/ticket and any live mutation approval.

## Recommendations for Buoy

1. Keep current explicit multi-namespace RRF as the reference baseline and preserve namespace-local rank fusion; never compare raw cross-namespace scores without calibration.
2. Treat namespace routing and retrieval as separate systems with separate oracle controls and metrics.
3. Require governed metadata filtering as the cheapest serious multi-hop baseline before graph work.
4. Prefer decomposition/iteration for dependent questions when stable entity relationships are absent or expensive to govern.
5. Restrict RAPTOR/GraphRAG global/DRIFT experiments to long-document, global, and mixed sensemaking classes; do not average them into a universal retriever claim.
6. If graph experiments are reached, start from vector/BM25 seeds and preserve leaf chunk provenance. Compare graph expansion to entity metadata and decomposition at equal/reported budgets.
7. Keep formal Data Vault Hubs/Links/Satellites authoritative. Semantic entities, relationships, concepts, and summaries are derived indexes with extraction version, confidence, history, and source coordinates.
8. Make ACL boundaries part of routing, traversal, summary construction, caching, and citation—not a post-retrieval filter.
9. Extend evaluation conceptually from path relevance to namespace-qualified evidence sets, hop dependencies, citations, temporal validity, and principals before selecting technology.
10. Prefer open-source/self-hostable reference implementations, but independently verify current licenses, optional model/service dependencies, and reproducibility before adoption. Microsoft GraphRAG, RAPTOR, IRCoT, KG²RAG, G-Retriever, and HippoRAG are research references, not endorsed dependencies by this record.

## Contradictions and interpretation

- Multi-Meta-RAG indicates metadata can substantially improve a multi-hop benchmark, while graph approaches argue relations/community structure are needed. These are not mutually exclusive: metadata is the required cheaper control, and a graph is justified only on residual classes.
- RAPTOR and GraphRAG report stronger answers on long/global tasks, but their generated summary indexes can improve generation context without proving leaf-evidence retrieval. Buoy must measure both.
- GraphRAG global search optimizes comprehensiveness/diversity; current Buoy evals optimize ranked source relevance. Neither metric can substitute for the other.
- IRCoT/ITER-RETGEN avoid graph indexing but spend repeated query/generation work. The architecture trade is index/lifecycle cost versus per-query cost and error propagation, not “graph versus no graph” in isolation.
- Data Vault relationship/history modeling resembles a graph structurally, but warehouse authority must not be conflated with probabilistically extracted semantic edges.

## Limits and blockers

- The task-referenced worktree-root `context.md` and `plan.md` were absent. Their intended content could not be inspected; the durable ticket graph and records were used instead.
- No paper implementation was installed or reproduced, and no public dataset was downloaded. Reported paper results remain source claims bounded to their experimental settings.
- The ledger pins the inspected arXiv versions and supportable repository commits or records a 2026-07-15 retrieval date for mutable pages. Those sources can still evolve; any experiment ticket must revalidate and pin its exact licenses, model dependencies, datasets, and benchmark scripts.
- The inspected GraphRAG global evidence relies heavily on model-based qualitative judging; independent human calibration is required.
- Public benchmarks do not establish Buoy namespace routing, ACL isolation, temporal Data Vault correctness, or source-deletion behavior.
- Existing Buoy graded labels are assistant-drafted and single-namespace. They cannot ratify multi-hop/global promotion thresholds.
- No user-ratified numeric latency, token, storage, quality, or operations budget exists. This record therefore defines gates and required measurements, not invented numeric promotion values.
- Graph extraction, entity resolution, correction authority, summary ACL strategy, and operational ownership remain architecture blockers for implementation.
- Building datasets, running fixture/live evals, constructing derived indexes, or implementing retrieval requires later specifications/tickets and user ratification after all four research tracks are synthesized.
