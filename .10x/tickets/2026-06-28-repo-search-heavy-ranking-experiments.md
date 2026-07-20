Status: active
Created: 2026-06-28
Updated: 2026-07-20
Depends-On: .10x/evidence/2026-06-28-repo-search-file-ranking-promotion-validation.md, .10x/research/2026-06-28-repo-search-precision-state-of-art.md

# Repo Search Heavy Ranking Experiments

## Outcome

Complete or explicitly disposition the genuinely unfinished heavy repo-ranking outcomes without reopening completed ranking, reranker, metadata, aggregation, or indexing-ablation history:

1. code-aware embedding feasibility and paired evaluation;
2. isolated syntax-aware chunking;
3. repository-held-out lightweight learning to rank;
4. routed-profile reproduction/generalization and, only if later ratified, productization.

This is a non-executable parent plan. Execution belongs only to the bounded C1-C9 children below.

## Completed history preserved

The existing progress log and evidence remain authoritative for completed local rerankers, file/page grouping and aggregation, current `repo_code` scoring, opt-in searchable path/symbol metadata and regex breadcrumbs, metadata/file-card/oversize ablations, 13-repo ranking grids, and distribution-safe promoted ranking changes. None are reopened by this graph.

The known broad basket is 13 repositories and 90 unique composite `repo_key:case_id` identities: 10 each for Buoy, Requests, Click, pytest, and Typer; 5 each for Black, Ruff, Flask, Django, Pydantic, HTTPX, MkDocs, and Rich. Each dataset-local `case_id` and every label remain unchanged; local IDs need not be globally unique. The labels support calibration/experiment evidence, not a production-ground-truth claim.

## Child graph and sequence

1. **C1 — executable local contract freeze:** `.10x/tickets/2026-07-19-freeze-repo-ranking-experiment-contract.md`
2. **C2 — executable read-only model research, parallel with C1:** `.10x/tickets/2026-07-19-research-code-aware-embedding-candidate.md`
3. **C3 — blocked live retrieval-only shared capture after C1:** `.10x/tickets/2026-07-19-capture-current-repo-candidates-and-baselines.md`
4. **C4 — blocked model/download/new-namespace pilot after C1+C2:** `.10x/tickets/2026-07-19-evaluate-code-aware-embedding-pilot.md`
5. **C5 — local syntax implementation, blocked pending C1 and a ratified active focused syntax spec:** `.10x/tickets/2026-07-19-implement-opt-in-python-syntax-chunking.md`
6. **C6 — blocked live syntax evaluation after C5 and exact write approval:** `.10x/tickets/2026-07-19-evaluate-python-syntax-chunking.md`
7. **C7 — blocked offline held-out ranker after C1+C3 and user-ratified material-weight/sign/order thresholds:** `.10x/tickets/2026-07-19-evaluate-lightweight-learning-to-rank.md`
8. **C8 — blocked offline routed-profile reproduction/generalization after C1+C3 and a user-ratified oracle-gap measure/threshold:** `.10x/tickets/2026-07-19-reproduce-and-generalize-routed-profile-selection.md`
9. **C9 — blocked productization after C8 and product ratification:** `.10x/tickets/2026-07-19-productize-routed-ranking-profile.md`

C1 and C2 may run in parallel. C4 and eventual local C5 may proceed independently after their gates. C7 and C8 share the exact immutable C3 cache and MUST NOT issue duplicate retrieval calls, but both remain blocked after C1/C3 until their distinct experiment thresholds are pre-registered and user-ratified. C1 may freeze the shared contract but MUST NOT invent those thresholds or make C7/C8 executable. C9 remains blocked and has no active product spec until C8 plus the user checkpoint.

## Aggregate acceptance criteria

- Every comparative child uses C1's frozen datasets, all 90 composite `repo_key:case_id` identities, source snapshots, namespace/commit/model mapping, folds, metrics, and artifact schema while preserving dataset-local `case_id` values and labels.
- Index-changing comparisons use paired current promoted defaults on the same source commit/corpus. `80.316` / P@5 `0.517` remains only a secondary routed-portfolio reference.
- Proprietary model APIs are excluded. No model identity, revision, license conclusion, prefix contract, dimension exception, download/resource budget, or public surface is inferred before C2 and the exact checkpoint.
- Every indexing experiment uses new namespaces only. Baseline namespaces are never mutated; stale/namespace deletes are forbidden; catalog/default changes require separate owners and approval.
- C3 performs at most one approved raw retrieval pass per frozen composite identity and exports separate ANN/BM25 candidates. Its schema and cache keys MUST carry `repo_key`, the unchanged dataset-local `case_id`, and the composite `repo_key:case_id`; C7/C8 are offline consumers of the same hash-addressed cache.
- General-default candidates apply `.10x/decisions/repo-ranking-promotion-policy.md`: no repo score regression; no repo P@5 regression; positive score on at least 3 repos; largest gain share at most 70%; improved all-repo average score.
- The three-repo no-regression/positive-average/two-improving-repo rule is only an experiment escalation gate for deciding whether to request a separately approved full-basket run. It is not active promotion policy and cannot authorize promotion.
- Passing an experiment means promotion-candidate evidence only. Label confidence, product surface, default promotion, and catalog mutation remain separate checkpoints.
- Any source implementation has focused/full tests, evidence, and independent review; no child is closed from plausible prose or a passing aggregate alone.

## Safety boundaries and stop conditions

- Stop affected repositories if C1 cannot reproduce checked-in judgments from pinned manifests; never rewrite labels silently.
- Stop C4 if no credible 384-dimensional local candidate fits current contracts; dynamic dimensions/routing/catalog migration need a separate decision.
- Stop C3/C7/C8 if separate raw lists are unavailable or default replay mismatches C1 tolerance; do not recapture candidates for each child.
- Stop C4/C6 on absent exact approval, failed pilot gate, incompatible contracts, or resource use beyond the approved bound.
- Stop C5 before implementation/spec activation until exact syntax arms, AST boundaries, line coverage/citations, and fallback behavior are ratified.
- Stop C7 before execution until the definition of material weights and exact sign/order stability thresholds are pre-registered and user-ratified; afterward stop on leakage, repository identity, incomplete folds, regressions, or failure of those thresholds.
- Stop C8 before execution until the oracle-gap measure and exact minimum materially-closed threshold are pre-registered and user-ratified. Stop C8/C9 automatic selection if evidence supports only oracle/static per-repo mapping. Never ship a benchmark lookup table as generalization.

## Exact user checkpoints

1. C3: approve one retrieval-only pass for all 90 frozen composite `repo_key:case_id` identities under the exact C1 namespace/commit map and reported request/cost bound, with preserved dataset-local IDs/labels, separate ANN/BM25 lists, and zero writes/deletes/catalog changes.
2. C4: approve the exact pinned model download bytes/RAM/device estimate and exact three-repo paired namespace rows/writes, with zero deletes and no catalog/default change. Passing the pilot gate permits only a request for separately approved full-basket experimentation.
3. C5: confirm or correct exact syntax arms, AST ownership, long-symbol subdivision, coverage/citation semantics, and syntax-error/non-Python fallback before an active spec is created.
4. C6: approve exact per-arm rows/namespaces/writes/storage multiplier from passing local C5 plans.
5. C7: pre-register and user-ratify the definition of material weights and exact allowed sign/order stability thresholds before fitting.
6. C8: pre-register and user-ratify the oracle-gap measure and exact minimum materially-closed threshold before selector evaluation.
7. C9: after C8, confirm the recommended versioned explicit opt-in profile with `repo_code` unchanged, or explicitly authorize shaping an automatic selector from held-out evidence.
8. Promotion: only for a learned/embedding default candidate, decide whether assistant-drafted labels suffice or whether bounded independent review is required.

## Parent closure requirements

C4, C6, C7, and C8 must each have evidence-backed terminal disposition or explicit no action. C9 must either complete under a ratified focused product spec or record no action consistent with C8. Closure also requires aggregate evidence mapping, independent review, retrospective extraction, coherent active specs/decisions/defaults, and separate owners for any promotion or label-review work.

## Blockers

The parent is intentionally non-executable. Current child blockers are recorded on C3, C4, C5, C6, C7, C8, and C9. C1 and C2 are the only immediately executable children. C7/C8 are blocked both on dependencies and on distinct pre-registered user-ratified thresholds; C1 cannot supply or infer those thresholds.

## Explicit exclusions

Reopening completed reranker/metadata/aggregation/ranking-grid work; source/tests/models/downloads/live calls during decomposition; label edits or ground-truth claims; existing namespace mutation/deletion; catalog/default promotion; hidden/static per-repo product routing; speculative syntax or product specs.

## References

- `.10x/research/2026-07-19-repo-search-heavy-ranking-experiment-decomposition.md`
- `.10x/research/2026-06-28-repo-search-precision-state-of-art.md`
- `.10x/research/2026-06-28-expanded-validation-ranking-hypotheses.md`
- `.10x/decisions/repo-ranking-promotion-policy.md`
- `.10x/decisions/namespace-ranking-defaults.md`
- `.10x/specs/repo-search-eval-autoresearch.md`
- `.10x/evidence/2026-07-01-repo-portfolio-routing-validation.md`
- `.10x/evidence/2026-07-02-repo-routed-profile-portfolio-validation.md`
- `.10x/reviews/2026-07-19-stale-ticket-status-closure-review.md`

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
- 2026-06-28: After explicit user approval for writes/evals to new namespaces, live-applied and evaluated metadata-only, oversize-only, and oversize+metadata ablations on pytest/Typer. Metadata-only improved both seed datasets and became the next promotion candidate. Oversize fixed authority-file recall but regressed existing seed datasets, so it remains opt-in/query-routed. Evidence: `.10x/evidence/2026-06-28-repo-oversize-metadata-live-eval.md`. Follow-up: `.10x/tickets/done/2026-06-28-repo-search-metadata-cross-repo-validation.md`.
- 2026-06-28: Metadata-only cross-repo validation on turbo-search, Requests, and Click showed better five-repo average score/P@5 but regressions on turbo-search and Requests. Do not promote metadata-only default under no-regression policy. Future work should test metadata placement/scoring rather than a universal preamble. Evidence: `.10x/evidence/2026-06-28-repo-search-metadata-cross-repo-validation.md`.
- 2026-06-28: Implemented and validated opt-in file-card metadata pages. File cards improved four of five repos and average score/P@5, but turbo-search still regressed, so no default promotion. Evidence: `.10x/evidence/2026-06-28-repo-file-card-metadata-validation.md`.
- 2026-06-28: Continued hypotheses until a no-regression improvement passed. File-card multiplier tuning, candidate/pool grids, and broad profile-weight changes did not pass. Conditional example/demo path demotion in `repo_code` improved Click, pytest, and Typer while leaving turbo-search and Requests unchanged, so it was promoted. Evidence: `.10x/evidence/2026-06-28-repo-example-path-demotion-validation.md`.
- 2026-06-28: Continued from the example-demotion baseline. Tested source-like boosts, `testing/` boosts, singular `doc/` demotion, `docs/tutorial/` demotion, dunder/internal typing demotions, and combinations. Query-aware `doc/` plus `docs/tutorial/` demotion passed the five-repo no-regression policy and was promoted. Evidence: `.10x/evidence/2026-06-28-repo-documentation-path-demotion-validation.md`.
- 2026-06-28: Continued from the documentation-demotion baseline. Tested root package source boosts, top-level source-like boosts, filename/path overlap boosts, test/docs query boosts, dunder/internal file demotions, and nested-private path demotion. Nested private path-segment demotion passed the five-repo no-regression policy and was promoted. Evidence: `.10x/evidence/2026-06-28-repo-nested-private-path-demotion-validation.md`.
- 2026-06-28: Continued from the nested-private baseline toward the user's +2.0 average-score target. Tested embedded agent-artifact path demotion alongside the prior root/source/path/dunder hypotheses. Embedded agent-artifact path-segment demotion passed the five-repo no-regression policy, improved Typer, and brought cumulative average score from `77.765` to `79.785` (`+2.020`). Evidence: `.10x/evidence/2026-06-28-repo-embedded-agent-artifact-demotion-validation.md`.
- 2026-06-28: Continued from the embedded-agent-artifact baseline after the user reset the next +2.0 target. Tested `docs_src/` example-source demotion, `tests/test_tutorial/` demotion, and combinations. Example scaffold demotion passed the five-repo no-regression policy, improving Typer from `64.734` to `66.121` and average score from `79.785` to `80.063`. Evidence: `.10x/evidence/2026-06-28-repo-example-scaffold-demotion-validation.md`.
- 2026-06-28: Tested opt-in oversize-file-card indexing in five new namespaces. It improved Click but regressed turbo-search, Requests, pytest, and Typer, so it remains opt-in and is not default-safe. Evidence: `.10x/evidence/2026-06-28-repo-oversize-file-card-indexing-validation.md`.
- 2026-06-28: Continued ranking hypotheses until the reset +2.0 average-score target was reached. Private/vendored `_click` routing, conventional `core.py`/`models.py` boosts, parameter-query `utils.py` demotion, non-CLI `cli.py` demotion, `_click/termui.py` terminal boost, and `index.md` parent-directory matching passed the five-repo no-regression policy. Average score reached `81.793`, up `+2.007` from the reset baseline `79.785`. Evidence: `.10x/evidence/2026-06-28-repo-private-module-routing-validation.md`.
- 2026-06-28: After user concern that the `+2.007` gain was too Typer-concentrated, created eight more repo eval datasets (`black`, `ruff`, `flask`, `django`, `pydantic`, `httpx`, `mkdocs`, `rich`) and live-applied eight new namespaces with no deletes. Added distribution-aware promotion policy. Full private-module candidate failed that policy because 81.8% of gain came from one repo. Reverted the over-concentrated pieces and kept only the passing `cli.py`/`_click/termui.py`/`index.*` subset. Evidence: `.10x/evidence/2026-06-28-expanded-repo-ranking-basket-validation.md`; decision: `.10x/decisions/repo-ranking-promotion-policy.md`.
- 2026-06-28: Continued hypotheses toward the user's next `+2.0` distributed target. Tested broad package-root source recognition, fixture/snapshot scaffold demotion, multiple demotion factors, stronger path/symbol boosts, broad docs demotion, and broad tests demotion. Promoted the smallest passing combination: package-root source recognition plus `0.80x` fixture/snapshot scaffold demotion for non-fixture/test queries. Live 13-repo evals improved average score `70.545 -> 72.762` (`+2.216`), P@5 unchanged, positive gains on 8 repos, no regressions, largest gain share 23.5%. Evidence: `.10x/evidence/2026-06-28-repo-source-fixture-routing-validation.md`.
- 2026-07-01: Continued hypotheses toward the user's next `+2.0` distributed target. Tested source-stem boosts, path-component boosts, generic test demotion, Rust crate-root routing, query-matched `_internal` exemption, conventional `core.py`/`models.py`/`utils.py` routing, `__init__.py` demotion, and `docs/source/` demotion. Promoted the passing combined conventional entrypoint routing set. Live 13-repo evals improved average score `72.762 -> 74.874` (`+2.112`), P@5 `0.452 -> 0.478`, positive gains on 10 repos, no score/P@5 regressions, largest gain share 35.2%. Evidence: `.10x/evidence/2026-07-01-repo-conventional-entrypoint-routing-validation.md`.
- 2026-07-01: Continued hypotheses toward the user's next `+2.0` target with explicit permission to create new namespaces. Tested candidate-depth configs, expanded file-card namespaces, existing metadata/file-card/oversize-card namespaces, oversize-source namespaces, and aggregation routing. The passing portfolio improved average score `74.874 -> 77.761` (`+2.887`) and P@5 `0.478 -> 0.500`, with positive gains on all 13 repos, no score/P@5 regressions, and largest gain share 21.2%. This is a portfolio/routing candidate, not a universal default. Evidence: `.10x/evidence/2026-07-01-repo-portfolio-routing-validation.md`.
- 2026-07-02: Continued hypotheses toward another `+2.0` target from the `77.761` portfolio baseline. Tested production-source boosts, path-overlap boosts, filename-stem boosts, nested-test demotion, snapshot demotion, Rust crate-root boosts, and routed combinations. Universal variants caused regressions and were rejected. The passing routed-profile portfolio improved average score `77.761 -> 80.316` (`+2.555`) and P@5 `0.500 -> 0.517`, with positive gains on 11 repos, no score/P@5 regressions, and largest gain share 31.3%. No new namespaces were required for the passing result. Evidence: `.10x/evidence/2026-07-02-repo-routed-profile-portfolio-validation.md`.
- 2026-07-19: Closure review confirmed that the extensive completed experiments are well evidenced and current promoted defaults remain coherent with `.10x/decisions/namespace-ranking-defaults.md` and `.10x/decisions/repo-ranking-promotion-policy.md`. Closure is nevertheless unsupported because named heavy hypotheses remain unevaluated and the latest routed portfolio is not productized. The ticket remains active; no completed experiment was reclassified as failed implementation. Review: `.10x/reviews/2026-07-19-stale-ticket-status-closure-review.md`.
- 2026-07-19: Decomposed this umbrella into the non-executable C1-C9 graph. Only C1 local contract freeze and C2 read-only research are immediately executable; C3/C4/C5/C6/C9 retain explicit gates, and C7/C8 share one dependency-gated offline cache. No completed history, labels, model, budget, syntax/product semantics, live operation, write, default, or promotion was changed. Research: `.10x/research/2026-07-19-repo-search-heavy-ranking-experiment-decomposition.md`.
- 2026-07-20: Repaired PR #56 review blockers: case uniqueness is composite `repo_key:case_id` while local IDs/labels remain intact; the three-repo rule is experiment escalation only; and C7/C8 are explicitly blocked on user-ratified pre-registered thresholds that C1 cannot invent.

## Closure note

Existing evidence supports isolation from defaults, open-source/local-only model use, new-namespace/no-delete safety, baseline comparisons, tests for source changes, live retrieval validation, promoted no-regression ranking subsets, and explicit rejection of regressions. It does not support terminal disposition of the umbrella scope. Closure requires either bounded evidence for the remaining named hypotheses and routed-selector/profile work, or an explicit durable no-action decision that narrows/cancels those outcomes, followed by retrospective extraction.
