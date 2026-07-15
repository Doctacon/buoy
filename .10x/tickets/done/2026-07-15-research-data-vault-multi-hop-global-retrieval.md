Status: done
Created: 2026-07-15
Updated: 2026-07-15
Parent: .10x/tickets/2026-07-15-semantic-retrieval-research-plan.md
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
- 2026-07-15: Resolved the sole remaining re-review blocker by verifying KG²RAG's exact title and arXiv v1 submission against its primary arXiv page and recording the version-pinned arXiv link plus the NAACL 2025 ACL Anthology publication link in the source ledger. Preserved the finding's confidence and Buoy transfer limitation. Ticket remains active for final review.
- 2026-07-15: Closure assessment after the final pass review (`.10x/reviews/2026-07-15-data-vault-multi-hop-global-retrieval-final-review.md`): all acceptance criteria are supported. Current Buoy retrieval/eval architecture and governing records were inspected; primary papers and official/open-source implementations are recorded in a versioned evidence ledger with bounded metrics, confidence, and limitations; the query taxonomy and B0-B8 baseline/ablation matrix are defined; retrieval, generation, citation/provenance, temporal, and ACL metrics are separated; public datasets and the finite 16-case Buoy pilot (with at most eight mechanically triggered challenge cases) are specified; cost/lifecycle categories and non-numeric promotion gates are defined; and the experiment sequence rejects graph complexity behind baseline, metadata, decomposition, and oracle gates. The initial review concerns were repaired, the sole re-review blocker was repaired, and the final review verdict is `pass`. Research-only exclusions were preserved: no dataset, eval, retriever, graph, threshold, specification, decision, implementation, or live-system mutation was created.
- 2026-07-15: Retrospective: the most reusable lesson is that a broad bibliography is not a reproducible evidence ledger; source-specific versions or retrieval dates, evidence class, bounded reported settings/results, confidence, and transfer limits must be recorded from the outset. A “smallest” pilot also needs a finite count, mechanical expansion triggers, adjudication completeness, and a hard insufficient-data stop rather than an open-ended sampling instruction. No new knowledge or skill record is warranted because these lessons are already concretely captured in the completed research record and review chain. Downstream architecture synthesis, datasets/evals, numeric promotion thresholds, experiments, and implementation remain blocked on completion/reconciliation of all four research tracks and user ratification; closure does not authorize them.
