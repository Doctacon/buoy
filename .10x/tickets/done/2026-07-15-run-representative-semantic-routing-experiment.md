Status: done
Created: 2026-07-15
Updated: 2026-07-19
Parent: None
Depends-On: None

# Run Representative Semantic Routing Experiment

## Outcome

Implement and run one bounded, read-only source-attribution experiment over the existing 13-repository/90-question basket. Compare oracle, lexical card aliases, semantic namespace cards, and equal-weight hybrid route RRF without adding production routing architecture.

## Governing records

- `.10x/specs/representative-semantic-namespace-routing-experiment.md`
- `.10x/reviews/2026-07-15-holistic-semantic-routing-workstream-review.md`
- `.10x/decisions/data-vault-is-analogy-not-architecture.md`
- `.10x/specs/repo-search-eval-autoresearch.md`
- `.10x/evidence/2026-06-28-cross-corpus-seed-eval-datasets.md`
- `.10x/decisions/namespace-ranking-defaults.md`
- the 13 tracked `src/buoy_search/data/*_repo_search_seed_evals.json` files enumerated by the active specification
- `src/buoy_search/retriever.py` for the established `RRF_K` constant and the boundary around downstream hit fusion

## Cold-start context

The superseded plan would have built five synthetic taxonomy/catalog/evaluator stages before any representative value evidence or product consumer existed. The user accepted the holistic review's smaller path on 2026-07-15.

The 13 tracked seed datasets enumerated by the active specification provide 90 source-backed, assistant-drafted questions. They are not human-approved product ground truth and do not contain the same question run against every other namespace. Use only case ID, question text, and the specification's home-namespace mapping for descriptive source attribution. Do not manufacture downstream cross-namespace results from missing data.

A read-only inspection on 2026-07-15 found open-source `BAAI/bge-small-en-v1.5` revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a` in the local Hugging Face cache. Execution must use that exact revision with the specification's offline/local-only environment, socket, credential, and path-write guards; fail rather than download, mutate cache, or substitute if loading fails.

## Scope

1. Narrow `.gitignore` so only `autoresearch/runs/semantic-routing-representative-20260715/` is newly tracked while unrelated run contents remain ignored.
2. Create that run directory with one experiment-specific evaluator and reviewed 13-card configuration.
3. Load the 13 tracked seed datasets and validate the exact dataset/mapping/card/90-question contract.
4. Implement the four routing strategies and exact offline/local-only guards as specified.
5. Add focused tests for validation, normalization, descriptor deduplication/frequency, deterministic ranking, injected-vector semantic ranking, RRF, metrics, overwrite safety, exact model revision/offline controls, socket/credential/write guards, and the narrow ignore exception.
6. Run the real semantic experiment with the pinned cached model and guards.
7. Commit `plan.json`, `result.json`, and `report.md` with explicit limitations and the model snapshot SHA-256 manifest.
8. Record reproducible evidence and obtain independent adversarial review before closure.

## Acceptance criteria

- The diff adds no production taxonomy, catalog, router, command, public API, persistence, graph, dependency, or behavior under `src/buoy_search/`.
- The experiment consumes exactly the 13 tracked dataset/mapping entries and all 90 questions enumerated by the active specification.
- Card validation is fail-closed and card text contains project-level descriptions rather than benchmark-question or expected-file leakage.
- Independent review inspects benchmark provenance and names materially ambiguous home-source questions rather than treating the assistant-drafted basket as product ground truth.
- Oracle, lexical, semantic, and hybrid route rankings follow the active specification exactly.
- Semantic execution uses `BAAI/bge-small-en-v1.5` revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, exact offline/local-only controls, a recorded model-file SHA-256 manifest, and fail-fast socket/credential/path-write guards.
- A narrow `.gitignore` exception makes this experiment's script/config/final artifacts reviewable while all unrelated untracked run directories remain ignored.
- Hybrid route fusion uses `RRF_K = 60` consistently with the existing runtime constant.
- Results include per-question rankings and aggregate/per-repository MRR, recall@1/3/5, unranked counts, and evaluated counts.
- The report distinguishes source-attribution evidence from unlabeled alternative relevance, downstream retrieval quality, and production readiness.
- The implementation does not misuse cached home-namespace hits as comparable cross-namespace results.
- Focused tests, the full test suite, and `git diff --check` pass.
- Independent review finds no unresolved significant issue and verifies the reported metrics from `result.json`.

## Explicit exclusions

- any production source change;
- live Turbopuffer access;
- downloads, hosted APIs, or credentials;
- production ACL, lifecycle, freshness, or compatibility policy;
- downstream same-query multi-namespace retrieval or `cross_namespace_rrf` execution without comparable hits;
- tag output changes owned by `.10x/tickets/2026-07-19-return-retrieval-tags.md` (shaping history: `.10x/tickets/done/2026-07-15-reconcile-retrieval-tag-output.md`); tag filtering remains excluded;
- promotion thresholds or production integration choice;
- query decomposition, concepts, relationships, ontology, or graphs.

## Evidence expectations

Evidence must record:

- implementation commit and exact tracked input paths/mappings;
- model identifier, immutable revision, snapshot-file SHA-256 manifest, offline environment controls, and guard behavior;
- focused and full validation commands with exit status;
- machine-readable aggregate metrics checked against the committed result;
- confirmation that no network, Turbopuffer, credential, model-download, production-state, or external-write path ran;
- limitations caused by home-source-only labels and absent same-query cross-namespace hits.

## Dependencies

None. The model revision cache and all 13 tracked source datasets were inspected before opening this ticket. If the cached model cannot load under the offline and write guards, mark this ticket blocked; do not download, mutate cache, or substitute.

## Blockers

None.

## Progress and notes

- 2026-07-15: Opened after the user accepted the smaller representative-experiment path. This ticket replaces the cancelled five-stage synthetic pilot and is the only executable implementation owner for the first routing-value slice.
- 2026-07-15: Implemented and ran the bounded evaluator in commit `a15bc686a645d1081f78272058a8da02751ff479`. The guarded cached-model run evaluated all 90 questions across 13 cards. Aggregate MRR / recall@1 / recall@3 / recall@5 were lexical `0.864815 / 0.822222 / 0.911111 / 0.911111`, semantic `0.913246 / 0.877778 / 0.933333 / 0.944444`, and hybrid RRF `0.933153 / 0.900000 / 0.955556 / 0.955556`. Focused tests (14), full suite (288), and `git diff --check` passed. Reproducible inputs, guards, model manifest, commands, side-effect confirmation, and limitations are recorded in `.10x/evidence/2026-07-15-representative-semantic-routing-experiment.md`. Ticket remains active pending the explicitly separate independent adversarial review and metric/provenance inspection; it is not closed or moved.
- 2026-07-15: Independent review found that the initial semantic/hybrid artifacts did not enforce the specified route fan-out, used hard-coded zero counters instead of factual guard completion, under-covered escape APIs, and omitted source-revealing bias. Corrective commit `d4bef7873c0f281aa1b4d5cc693464234ecf44fa` applies only the accepted fixes and regenerates the pinned guarded run. Every recorded ranking is now top-five before scoring. Corrected MRR / recall@1 / recall@3 / recall@5 / unranked are lexical `0.864815 / 0.822222 / 0.911111 / 0.911111 / 8`, semantic `0.906481 / 0.877778 / 0.933333 / 0.944444 / 5`, and hybrid RRF `0.927778 / 0.900000 / 0.955556 / 0.955556 / 4`; the earlier semantic/hybrid MRR and zero-unranked values are superseded. The artifacts record `79/90` questions with an explicit home title/alias and 11 descriptor-free, cross-home-ambiguous cases. Guards now cover socket sends, process launch/spawn, and additional path mutation; hard-coded counters were replaced with exact coverage, credential/module checks, successful no-violation completion, and equal before/after model manifests. Focused tests (18), full suite (292), independent metric recalculation, and `git diff --check` passed. Ticket remains active and unclosed pending independent re-review.

- 2026-07-15: Two fresh independent re-reviewers passed the corrected implementation. They independently reproduced aggregate and per-repository metrics, verified top-five storage/scoring, inspected hardened guards and benchmark-bias reporting, and found no blocker. Durable review: `.10x/reviews/2026-07-15-representative-semantic-routing-experiment-review.md`.

## Closure mapping

- The bounded evaluator, cards, tracked plan/result/report, and focused tests are committed under the specified experimental boundary.
- All 13 mapped datasets and 90 questions are present; card/input validation and composite case identity are verified.
- Oracle, lexical, semantic, and hybrid behavior map to focused tests and independent result recalculation.
- Pinned offline model identity, input/model manifests, guard configuration/completion, and no-production-change limits are recorded in `.10x/evidence/2026-07-15-representative-semantic-routing-experiment.md`.
- Eighteen focused and 292 full-suite tests passed; `git diff --check` passed.
- Initial fan-out and evidence-overclaim findings were corrected and explicitly superseded in evidence rather than hidden.
- Independent final review verdict is pass with only bounded residual risks.
- The active specification still matches the implemented route-only experiment and explicitly excludes production routing and graph work.

## Retrospective

Three reusable lessons were extracted to `.10x/knowledge/semantic-routing-evaluation-lessons.md`: apply route limits before every rank-derived metric, distinguish configured guards from observed activity, and quantify source-name exposure before interpreting semantic-routing results.

No production or benchmark follow-up is opened automatically. The result has no ratified promotion threshold, 79/90 questions reveal the home source, alternatives are unlabeled, and no product integration seam is approved. Any human-reviewed benchmark or production-routing slice requires new user ratification rather than widening this completed experiment.
