Status: recorded
Created: 2026-07-15
Updated: 2026-07-15
Target: f2538f001820bd3cf9c4596ab54092e3094844de
Verdict: concerns

# Data Vault Multi-Hop and Global Retrieval Re-review

## Target and method

Re-reviewed repair commit `f2538f001820bd3cf9c4596ab54092e3094844de` against:

- `.10x/tickets/done/2026-07-15-research-data-vault-multi-hop-global-retrieval.md`;
- `.10x/tickets/done/2026-07-15-semantic-retrieval-research-plan.md`;
- `.10x/research/2026-07-15-data-vault-multi-hop-global-retrieval.md`;
- `.10x/reviews/2026-07-15-data-vault-multi-hop-global-retrieval-review.md`; and
- the exact repair diff from `e5538ec` to `f2538f0`.

The requested worktree-root `plan.md` and `progress.md` are absent. The durable parent plan, child ticket, research record, prior review, and repair diff provided the governing material for this bounded re-review.

Validation was read-only except for this review record. I fetched the explicitly pinned arXiv PDFs for MultiHop-RAG v1, Multi-Meta-RAG v2, RAPTOR v1, and GraphRAG v2 and checked the quoted tables/settings. I also used `git ls-remote` to confirm that all ten repository commits newly recorded in the ledger resolve in their named repositories. No benchmark, dataset, implementation, live retrieval, or external write was performed.

## Findings

### Significant — one graph-source ledger entry still lacks the required paper/version link

The repair materially improves the ledger, but the KG²RAG row at `.10x/research/2026-07-15-data-vault-multi-hop-global-retrieval.md:71` identifies only “cited publication page”; it records no URL, publication venue/revision, paper identifier, or implementation revision. That is not independently refindable from the record and does not satisfy the ticket's explicit requirement to record paper/version links at `.10x/tickets/done/2026-07-15-research-data-vault-multi-hop-global-retrieval.md:40-42`. It also conflicts with the ledger's own pinning description at research line 59 and the blanket claim at line 424 that inspected sources are pinned.

This is relevant rather than incidental: KG²RAG is used as the closest chunk-evidence pattern for B8 and remains a named research reference at research lines 206 and 410. The repaired record should supply the exact primary publication URL/identifier and revision or explicitly remove the unsupported source-specific reliance. This does not overturn the staged recommendation, because other pinned graph sources and the oracle-first gate independently support evaluating graph expansion only after cheaper controls. It does block treating the ticket's evidence expectations as fully met.

### Correct — the two requested bibliographic corrections are repaired

The MultiHop-RAG entry now records the official title, arXiv identifier/version, repository revision, and COLM 2024 acceptance status at research line 63. The Multi-Meta-RAG entry now uses the primary source title, “Multi-Meta-RAG: Improving RAG for Multi-Hop Queries using Database Filtering with LLM-Extracted Metadata,” and identifies arXiv v2 at line 64. These directly resolve the two spot-check errors in the prior review.

### Correct — versions and confidence are substantially reproducible and properly bounded

Research lines 63-76 now distinguish paper/preprint, official documentation, repository, and vendor/project-documentation evidence. Each finding has narrow confidence and a separate transfer limitation. Mutable documentation is dated, and pinned repositories are attached to full commit hashes. `git ls-remote` confirmed all ten newly named commits for MultiHop-RAG, Self-Ask, IRCoT, RAPTOR, GraphRAG, G-Retriever, HippoRAG, ALCE, 2WikiMultiHopQA, and MuSiQue.

The G-Retriever repository correction at line 72 is internally coherent: the recorded commit resolves in the newly named `XiaoxinHe/G-Retriever` repository. Confidence is not laundered into Buoy applicability; for example, GraphRAG remains medium-confidence primary research dominated by model judging, and official documentation is assigned no independent comparative-quality confidence.

### Correct — reported metrics/settings match the pinned primary papers and remain non-ratifying

Spot checks support research lines 84-87:

- MultiHop-RAG v1 Table 4 reports 2,556 queries split into 1,078 two-evidence, 779 three-evidence, 398 four-evidence, and 301 null cases; Table 5 reports voyage-02 plus reranking Hits@10 `0.7467` and Hits@4 `0.6625`. The record appropriately rounds and bounds the Table 6 generation comparison.
- Multi-Meta-RAG v2 Table 2 reports the recorded voyage-02 baseline-to-method values: MRR@10 `0.6016`→`0.6748`, MAP@10 `0.2619`→`0.3388`, Hits@10 `0.7419`→`0.9042`, and Hits@4 `0.6630`→`0.7920`.
- RAPTOR v1 Tables 3-4 report the recorded QASPER F1 and QuALITY development accuracy values.
- GraphRAG v2 describes two 125-question corpus evaluations, five repeated comparisons, and the recorded comprehensiveness/diversity win-rate ranges.

Research lines 80 and 84-87 clearly label these as author-reported, unreproduced, setting-specific values rather than Buoy thresholds. The limitations preserve the ticket's prohibition on universalizing paper gains.

### Correct — the pilot seed and stopping rule are finite and mechanically assessable

Research lines 244-257 now define exactly 16 core cases, two assigned to each of eight primary strata. They preserve overlapping taxonomy labels while preventing one case from satisfying multiple minimum stratum counts. ACL cases also state the principal-query evaluation count.

Label calibration has a deterministic completeness condition: required fields are populated, locators resolve against the frozen snapshot, and all reviewer disagreements are adjudicated. Expansion is capped at one mechanically triggered challenge case per stratum (eight maximum), followed by one review/adjudication pass and a hard stop. Remaining deficiencies produce an “insufficient” pilot and block comparison rather than causing indefinite expansion. The explicit prohibition on bootstrap/promotion inference from this pilot correctly avoids inventing statistical confidence from 16-24 cases.

### Correct — no repair regression or scope widening found

The repair changes only the research record and the child ticket's append-only progress note. It does not alter source, tests, specifications, decisions, datasets, thresholds, architecture, or live state. `git diff --check f7eeb01..f2538f0` passed. The query taxonomy, B0-B8 matrix, metric separation, ACL invariant, provenance/lifecycle gates, and cheapest-control-first experiment order accepted by the prior review remain intact.

## Ticket criterion assessment

| Ticket criterion | Assessment | Evidence |
|---|---|---|
| Inspect current Buoy retrieval/eval architecture and records | Met | Prior review verified research lines 32-55 and 99-120 against governing source/records; repair did not alter this material. |
| Review primary papers and official/open-source implementations | Partially met | Most sources now have versions/revisions and per-finding confidence at lines 63-76, and the reported primary-paper results at lines 84-87 spot-check correctly. KG²RAG at line 71 remains without an exact paper/version link. |
| Define query taxonomy and baseline/evaluation matrix | Met | Prior review accepted research lines 122-211; repair caused no regression. |
| Separate retrieval/generation metrics and cover citation/provenance/ACL | Met | Prior review accepted research lines 284-336; repair caused no regression. |
| Identify public datasets and smallest Buoy seed | Met | Research lines 229-257 now provide both transfer limits and a finite 16-case seed with at most eight triggered additions and an explicit stop. |
| Define cost categories and promotion gates without unsupported numbers | Met | Research lines 338-365 remain bounded; the new pilot language expressly disclaims promotion inference. |
| Order experiments to reject unnecessary graph work early | Met | Research lines 367-382 remain unchanged and accepted. |
| Meet ticket evidence expectations | Partially met | Versions, confidence, settings, and metrics are substantially repaired, but research line 71 still lacks the required refindable paper/version link. |

## Verdict

**Concerns.** Repair commit `f2538f0` resolves the prior bibliographic errors, the broad version/confidence/metrics gap, and the unbounded seed/stopping-rule gap without regressing the technical recommendation. One narrow but material evidence-ledger defect remains: KG²RAG is still relied upon without an exact paper/version link. The core recommendation has no technical blocker, but the child ticket's acceptance is not fully supported until that source is made independently refindable or its source-specific reliance is removed.

## Residual risk

- The literature metrics were source-checked but not experimentally reproduced; they remain author-reported evidence only.
- Mutable documentation and repository heads can evolve even though the inspected revisions/dates are recorded.
- No Buoy multi-hop/global dataset, statistical-power design, ACL test, temporal test, or retrieval experiment exists; the record correctly leaves implementation and promotion blocked on later ratification and tickets.
- The absent worktree-root `plan.md` and `progress.md` could not be reviewed; durable records supplied the available authority.
