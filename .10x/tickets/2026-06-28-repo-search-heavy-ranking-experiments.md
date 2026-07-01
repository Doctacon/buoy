Status: active
Created: 2026-06-28
Updated: 2026-06-28
Depends-On: .10x/evidence/2026-06-28-repo-search-file-ranking-promotion-validation.md, .10x/research/2026-06-28-repo-search-precision-state-of-art.md

# Repo Search Heavy Ranking Experiments

## Scope

Evaluate the heavier remaining precision hypotheses after the default file-level ranking promotion:

- open-source/local rerankers over top candidates;
- code-aware embedding model candidates;
- symbol/path/identifier metadata enrichment;
- syntax-aware or symbol-breadcrumb chunking;
- lightweight learning-to-rank after labels are expanded/reviewed.

## Acceptance criteria

- Each experiment is isolated from production defaults until evidence supports promotion.
- Proprietary model APIs are not used.
- New namespaces are used for re-indexing experiments; existing baseline namespaces are not deleted or mutated without a separate approval.
- Results compare against the post-promotion default baseline from `.10x/evidence/2026-06-28-repo-search-file-ranking-promotion-validation.md`.
- Any source changes have tests and live retrieval-only eval evidence.

## Blockers

- None for retrieval-only ranking experiments.
- Larger cross-repo labels remain recommended before learning-to-rank or embedding-model default promotion.

## References

- `.10x/research/2026-06-28-repo-search-precision-state-of-art.md`
- `.10x/evidence/2026-06-28-repo-search-file-ranking-promotion-validation.md`

## Progress and notes

- 2026-06-28: Opened as follow-up owner for heavier hypotheses not included in the file-ranking/H9/H4 execution slice.
- 2026-06-28: Activated local reranker slice for existing GitHub repo namespace `github-doctacon-turbo-search-v1` and website namespace `site-turbopuffer-com-v1`.
- 2026-06-28: Added assistant-drafted website eval dataset `src/turbo_search/data/turbopuffer_site_search_seed_evals.json` for `site-turbopuffer-com-v1`.
- 2026-06-28: Fixed schema portability for website retrieval: retry live queries without `repo_path` when a namespace schema does not contain it.
- 2026-06-28: Tested `cross-encoder/ms-marco-MiniLM-L-6-v2` and `BAAI/bge-reranker-base` reranker variants across repo and website corpora. Evidence: `.10x/evidence/2026-06-28-local-reranker-repo-and-site-validation.md`.
- 2026-06-28: Result: local rerankers should not be promoted as default for repo search; website search improved slightly on Precision@5 when reranking was combined with URL/page collapse.
- 2026-06-28: Tested website page aggregation after user selected the hypothesis. `capped-sum-3` passed both targets on `site-turbopuffer-com-v1`; no defaults changed. Evidence: `.10x/evidence/2026-06-28-website-page-aggregation-experiments.md`.
- 2026-06-28: Implemented opt-in `--ranking-aggregation capped-sum-3` for page ranking and validated it live on `site-turbopuffer-com-v1`; no defaults changed. Evidence: `.10x/evidence/2026-06-28-opt-in-page-aggregation-ranking-validation.md`.
- 2026-06-28: Cross-site validated page ranking on existing `site-sqlmesh-readthedocs-io-v1` namespace. Page mode pool 20 improved Precision@5 from `0.260` to `0.473`; default promotion remains separate. Evidence: `.10x/evidence/2026-06-28-cross-site-page-aggregation-sqlmesh-validation.md`.
- 2026-06-28: Promoted namespace-aware website defaults for `site-*`: page/none/pool20/max. GitHub repo defaults preserved. Evidence: `.10x/evidence/2026-06-28-website-page-ranking-default-promotion-validation.md`.
- 2026-06-28: Hardened evidence on third website namespace `site-pi-dev-v1`; promoted default improved Precision@5 from `0.220` to `0.333`. Evidence: `.10x/evidence/2026-06-28-website-ranking-evidence-hardening.md`.
- 2026-06-28: User explicitly cancelled the human-review prerequisite preference and requested more hypotheses/tests focused on repo search score improvements.
- 2026-06-28: Tested repo file aggregation grid. `file/repo_code/pool100/capped_sum_3` improved repo score from `87.251` to `89.629`, Precision@5 from `0.500` to `0.520`, Recall@10 from `0.833` to `0.900`, and NDCG@10 from `0.920` to `0.935`.
- 2026-06-28: Promoted repo `ranking_aggregation` default from `max` to `capped_sum_3`; website default remains `page/none/pool20/max`. Evidence: `.10x/evidence/2026-06-28-repo-capped-aggregation-default-promotion.md`.
- 2026-06-28: Re-indexed current shipped `main` into existing `github-doctacon-turbo-search-v1` without stale deletion; unfiltered memory/eval artifacts degraded score to `71.346`, exposing index-hygiene as the next strongest hypothesis.
- 2026-06-28: Added default GitHub repo planning exclusions for local agent memory/run artifacts and eval fixture JSON; updated `repo_code` profile to demote artifact/eval paths and lightly boost `tests/`.
- 2026-06-28: Applied clean new namespace `github-doctacon-turbo-search-v2-clean`; default repo score recovered to `88.125` on current `main`. Evidence: `.10x/evidence/2026-06-28-repo-index-hygiene-and-profile-validation.md`.
- 2026-06-28: Implemented query-aware implementation-vs-experiment reranking in the `repo_code` profile. Clean `turbo-search` with opt-in capped aggregation reached `repo_search_score = 89.197`; cross-repo-safe max default scored `86.697`. Evidence: `.10x/evidence/2026-06-28-repo-query-intent-profile-validation.md`.
- 2026-06-28: Cross-repo validated `psf/requests` in new namespace `github-psf-requests-v1`. `max` aggregation beat `capped_sum_3` (`81.809` vs `78.229`), so the active repo default was reverted to `max` and capped aggregation remains opt-in. Evidence: `.10x/evidence/2026-06-28-cross-repo-requests-validation.md`.
- 2026-06-28: User selected universal default, path/symbol ranking, leave polluted namespace alone, scoring-only scope. Implemented conservative path/symbol boosts inside `repo_code` using existing `repo_path` and retrieved Python def/class chunk content. Live retrieval-only evals improved both validation repos: `turbo-search` `86.697 -> 87.126`, `psf/requests` `81.809 -> 82.547`. Evidence: `.10x/evidence/2026-06-28-repo-path-symbol-ranking-validation.md`.
- 2026-06-28: Implemented scoring-only module-role diversification. The rule preserves the top implementation hit and promotes at most one strong docs/tests companion into slot five when top five lacks a companion role. Live retrieval-only evals improved `psf/requests` from `82.547 -> 84.093` without changing `turbo-search` (`87.126`). Evidence: `.10x/evidence/2026-06-28-repo-role-diversification-validation.md`.
- 2026-06-28: Added third public repo validation on `pallets/click` in new namespace `github-pallets-click-v1`. Planned 150 files / 1196 chunks locally; approved apply upserted 1196 rows with no deletes. Click default max scored `67.150`; opt-in capped_sum_3 scored `72.550`; raw chunk scored `42.769`. Three-repo current-profile average now favors capped_sum_3 (`81.411`) over max (`79.457`) but capped still regresses `psf/requests`, so default aggregation remains a decision point rather than silently changed. Evidence: `.10x/evidence/2026-06-28-cross-repo-click-validation.md`.
- 2026-06-28: Implemented `adaptive_sum_3`, a scoring-only close-evidence aggregation that starts from max and adds 5% per extra same-file chunk when the extra chunk score is at least 80% of the best chunk score. Three-repo live evals improved every repo versus max (`turbo-search 87.126 -> 87.760`, `psf/requests 84.093 -> 84.426`, `pallets/click 67.150 -> 72.474`) and beat capped_sum_3 on average (`81.553` vs `81.411`), so repository default was promoted to `adaptive_sum_3`. Evidence: `.10x/evidence/2026-06-28-repo-adaptive-aggregation-validation.md`.
- 2026-06-28: Created ten additional post-expanded-validation hypotheses covering oversize source indexing, role-aware query classification, path/symbol metadata, website adaptive aggregation, representative section choice, site heading/slug expansion, candidate-depth tuning, and a tiny feature-based ranker. Research: `.10x/research/2026-06-28-expanded-validation-ranking-hypotheses.md`.
- 2026-06-28: Executed the next three recommended hypotheses to local/retrieval-only limits. Website adaptive aggregation failed no-regression due turbopuffer regression; website default unchanged. Repo oversize/source metadata now has opt-in CLI support and local pytest/Typer plans/preflights. Evidence: `.10x/evidence/2026-06-28-website-adaptive-aggregation-review.md`, `.10x/evidence/2026-06-28-repo-oversize-metadata-local-validation.md`.
- 2026-06-28: After explicit user approval for writes/evals to new namespaces, live-applied and evaluated metadata-only, oversize-only, and oversize+metadata ablations on pytest/Typer. Metadata-only improved both seed datasets and became the next promotion candidate. Oversize fixed authority-file recall but regressed existing seed datasets, so it remains opt-in/query-routed. Evidence: `.10x/evidence/2026-06-28-repo-oversize-metadata-live-eval.md`. Follow-up: `.10x/tickets/2026-06-28-repo-search-metadata-cross-repo-validation.md`.
- 2026-06-28: Metadata-only cross-repo validation on turbo-search, Requests, and Click showed better five-repo average score/P@5 but regressions on turbo-search and Requests. Do not promote metadata-only default under no-regression policy. Future work should test metadata placement/scoring rather than a universal preamble. Evidence: `.10x/evidence/2026-06-28-repo-search-metadata-cross-repo-validation.md`.
- 2026-06-28: Implemented and validated opt-in file-card metadata pages. File cards improved four of five repos and average score/P@5, but turbo-search still regressed, so no default promotion. Evidence: `.10x/evidence/2026-06-28-repo-file-card-metadata-validation.md`.
- 2026-06-28: Continued hypotheses until a no-regression improvement passed. File-card multiplier tuning, candidate/pool grids, and broad profile-weight changes did not pass. Conditional example/demo path demotion in `repo_code` improved Click, pytest, and Typer while leaving turbo-search and Requests unchanged, so it was promoted. Evidence: `.10x/evidence/2026-06-28-repo-example-path-demotion-validation.md`.
