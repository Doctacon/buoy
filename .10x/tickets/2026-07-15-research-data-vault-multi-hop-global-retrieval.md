Status: active
Created: 2026-07-15
Updated: 2026-07-15
Parent: .10x/tickets/2026-07-15-data-vault-semantic-retrieval-research-plan.md
Depends-On: None

# Research Data Vault Multi-Hop and Global Retrieval

## Scope

Research retrieval and evaluation strategies for questions that need evidence across namespaces, multiple hops, entity relationships, or corpus-wide synthesis. Determine when metadata routing, iterative vector retrieval, concept indexes, or graph traversal are justified over current explicit multi-namespace RRF.

Execute in branch `work/research-data-vault-multihop` in its own worktree based on current `develop`. Produce `.10x/research/2026-07-15-data-vault-multi-hop-global-retrieval.md`. Research only; do not implement.

## Questions

- Which query classes are local factual, cross-namespace, multi-hop, entity-centric, temporal, or global/sensemaking?
- Which baselines should be compared: current RRF, metadata-filtered retrieval, query decomposition, iterative retrieval, RAPTOR-style summaries, GraphRAG local/global/DRIFT, and graph-path retrieval?
- Which public benchmarks transfer to Buoy, and which project-specific datasets must be authored?
- What evidence establishes that a graph improves retrieval rather than only answer fluency?
- How should citation completeness, hop coverage, retrieval recall, faithfulness, latency, index cost, query cost, and ACL correctness be measured?
- What cost/quality gate should stop graph construction when metadata or decomposition suffices?

## Acceptance criteria

- Inspect current Buoy retrieval/eval architecture, ranking defaults, multi-namespace RRF contract, and existing eval records.
- Review primary papers and official/open-source implementations for multi-hop metadata RAG, GraphRAG, RAPTOR or comparable hierarchical retrieval, and iterative/decomposed retrieval.
- Define a query taxonomy and candidate evaluation matrix with the current system as baseline.
- Separate retrieval metrics from generation metrics and include provenance/citation and ACL checks.
- Identify reusable public datasets and specify the smallest Buoy-specific seed dataset needed for cross-namespace/Data Vault scenarios.
- Estimate indexing/query cost categories and define promotion thresholds or decision gates without inventing numeric values unsupported by evidence.
- Recommend an experiment order that can reject unnecessary graph complexity early.

## Explicit exclusions

- Building a benchmark, running live evals, implementing retrievers, or constructing a graph.
- Treating paper-specific gains as universal.
- Comparing raw scores across namespaces without calibrated or rank-based fusion.

## Evidence expectations

Record paper/version links, task and dataset scope, reported metrics with limitations, local paths, baseline gaps, contradictory findings, and confidence. Distinguish peer-reviewed work, preprints, vendor claims, and project documentation.

## Blockers

None for research. Experiments and implementation remain blocked on completed research, synthesis, and user ratification.

## Progress and notes

- 2026-07-15: Ticket opened from the ratified four-track research plan. Execution intentionally deferred from the ticket-authoring turn.
- 2026-07-15: Activated the research ticket on `work/research-data-vault-multihop`. Inspected the parent plan, preliminary investigation, current retrieval/eval specifications, ranking decision, validation evidence, docs, retrieval/eval/autoresearch implementations, and focused tests. The task-referenced worktree-root `context.md` and `plan.md` were absent; durable records supplied sufficient bounded authority.
- 2026-07-15: Produced `.10x/research/2026-07-15-data-vault-multi-hop-global-retrieval.md` covering primary-paper and official/open-source evidence; query taxonomy; baseline/ablation matrix; public and Buoy-specific dataset options; separate retrieval, generation, citation, temporal, and ACL metrics; cost/lifecycle gates; staged experiments; recommendations; contradictions; and limits. No dataset, eval, retriever, graph, source/spec/decision, or live-system mutation was performed. Ticket intentionally remains active for independent review.
- 2026-07-15: Repaired the independent review concerns in `.10x/reviews/2026-07-15-data-vault-multi-hop-global-retrieval-review.md`: converted the bibliography into a source-specific evidence ledger with arXiv versions, supportable repository commits or retrieval dates, per-finding confidence, and bounded primary-paper metrics/settings; corrected MultiHop-RAG's COLM 2024 status and the Multi-Meta-RAG title; and bounded the Buoy pilot at 16 core cases plus no more than eight mechanically triggered challenge cases with complete adjudication and an explicit insufficient-pilot stop. No success threshold, dataset, implementation, or experiment was created. Ticket remains active for follow-up review.
