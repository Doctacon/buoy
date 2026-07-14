Status: active
Created: 2026-06-28
Updated: 2026-07-14

# Repo and Website Ranking Defaults

Buoy retrieval defaults to hybrid ANN + BM25 + RRF followed by namespace-aware final ranking. GitHub repo planning also excludes generated/vendor directories plus local agent memory/run artifacts (`.10x/`, `.loom/`, `.pi/`, `.buoy/`, legacy `.turbo-search/`, `artifacts/`, `autoresearch/`) and eval fixture JSON under `/data/` by default so repository search stays focused on source, tests, and user-facing docs. Repo planning skips text files above 51200 bytes by default; experiments can opt into larger files with `--repo-max-file-bytes` and searchable path/Python-symbol text with `--repo-search-metadata`.

Website namespaces (`site-*`) default to:

```text
candidates = 200
ranking_mode = page
ranking_profile = none
ranking_pool = 20
ranking_aggregation = max
```

Repository namespaces default to repository-aware final ranking:

```text
candidates = 200
ranking_mode = file
ranking_profile = repo_code
ranking_pool = 100
ranking_aggregation = adaptive_sum_3
```

`ranking_mode=file` groups GitHub repository hits by `repo_path` so duplicate chunks from the same file do not consume the top-k result slots. The representative chunk is the earliest fused hit for that file. `ranking_aggregation=adaptive_sum_3` uses the best chunk per file plus a small close-evidence bonus: up to two additional same-file chunks add 5% each only when their rank-derived score is at least 80% of the best chunk score. Strict `max` and full `capped_sum_3` remain opt-in.

`ranking_profile=repo_code` is a gentle post-fusion path prior for repository rows only:

- process/project-agent artifact directory segments such as `.pi/`, `.10x/`, `.agents/`, `.loom/`, `.claude/`, `.cursor/`, `.buoy/`, and legacy `.turbo-search/` are demoted strongly even when embedded below another path segment; root-level run artifacts `artifacts/` and `autoresearch/` are also demoted strongly;
- eval/fixture/dataset JSON under `/data/` is demoted strongly so answer-key-like files do not dominate implementation queries;
- `docs/`, README/CHANGELOG, and other Markdown files are demoted gently, with a partial recovery for exact documentation filename matches such as `docs/api.rst` on API queries;
- singular `doc/` documentation roots are demoted for non-documentation/example queries;
- `docs/tutorial/` paths receive an extra demotion for non-documentation/tutorial/example queries;
- example/demo paths such as `examples/`, `docs_src/`, `example_scripts/`, `/example/`, and `/examples/` are demoted for non-example queries;
- example scaffold paths such as `docs_src/` and `tests/test_tutorial/` receive an extra demotion for non-example/tutorial queries;
- fixture/snapshot scaffold paths such as `/fixtures/`, `/snapshots/`, `/resources/test/`, and `/tests/data/` receive a conservative extra demotion for queries that are not asking for fixtures, snapshots, or tests;
- nested private path segments such as `typer/_click/` are demoted when the private segment is not query-related, while private package roots such as `src/_pytest/` are exempt; `_internal` package segments are not demoted when the full path has at least two query-token matches;
- `tests/` files get a light boost because repository evals often ask where behavior is validated;
- source/config files are mostly neutral, with conservative query-aware boosts for exact source filename matches and Python `def`/`class` declarations already present in retrieved chunks; source-path recognition includes ordinary top-level package files such as `django/http/request.py`, `httpx/_models.py`, `rich/text.py`, `mkdocs/commands/build.py`, and `pydantic/type_adapter.py`, not just `src/` and `lib/`;
- Rust crate root entrypoints `crates/<crate>/src/lib.rs` and `crates/<crate>/src/main.rs` are boosted when the query matches the crate name;
- conventional Python module names are query-aware: `core.py` is boosted for command/runtime queries, `models.py` is boosted for parameter/field/model metadata queries, and `utils.py` is demoted for parameter metadata queries that are not asking for utility helpers;
- non-public `__init__.py` files are demoted unless the query asks for public API, exports, module entrypoints, initialization, or top-level behavior;
- `docs/source/` paths receive an extra demotion for non-documentation queries;
- a small conventional-file subset is query-aware: non-CLI `cli.py` hits are gently demoted, nested `_click/termui.py` gets a terminal-UI boost, and `index.*` can match its parent directory name;
- when top five lacks docs/tests and rank 1 is an implementation file, one strong docs/tests companion may be promoted into slot five without replacing the top implementation hit.

Generic website rows without `repo_path` remain chunk-keyed and are not collapsed by file ranking.

Use capped URL/page-level aggregation for website experiments with:

```bash
buoy retrieve "..." --ranking-aggregation capped-sum-3
```

`ranking_mode=page` groups website chunks by canonical URL while repository rows still group by `repo_path`. Page ranking improved assistant-drafted website evals on `site-turbopuffer-com-v1`, `site-sqlmesh-readthedocs-io-v1`, and `site-pi-dev-v1`, so page/max/pool20 was promoted as the `site-*` default on 2026-06-28. Website capped aggregation remains opt-in because it was not uniformly better than max at the precision-oriented pool. Expanded validation on Ruff and Typer docs showed capped_sum_3 improved both new site seed datasets, but prior Pi-site evidence had a tiny capped-score regression at pool 20 while P@5 was unchanged; see `.10x/tickets/2026-06-28-website-capped-aggregation-default-review.md`. Use raw chunk order for debugging with:

```bash
buoy retrieve "..." --ranking-mode chunk --ranking-profile none
```

The repo default was first promoted after live retrieval-only experiments improved the `turbo-search` seed repo eval from `Precision@5 = 0.300` and `repo_search_score = 59.967` to `Precision@5 = 0.500` and `repo_search_score = 87.251` on namespace `github-doctacon-turbo-search-v1`. A follow-up capped aggregation experiment improved `turbo-search` further, but cross-repo validation on `psf/requests` showed full capped aggregation was not a safe universal default. After current `main` shipped project-memory/eval artifacts, a clean current-main namespace plus query-intent, path/symbol, role-diversification, and adaptive aggregation profile validates `turbo-search` at `Precision@5 = 0.540`, `Recall@10 = 0.833`, `NDCG@10 = 0.922`, and `repo_search_score = 87.760`. Cross-repo validation on `psf/requests` improved from the pre-profile `repo_search_score = 81.809` to `84.426` and `Precision@5 = 0.360` to `0.420`. Third-repo validation on `pallets/click` challenged the strict max aggregation default; adaptive aggregation improved Click max from `67.150` to `72.474` without regressing turbo-search or Requests. Across three repos, adaptive aggregation scored `81.553` average versus `79.457` for max and `81.411` for capped_sum_3.

Expanded validation on `pytest-dev/pytest` and `fastapi/typer` kept the repo default unchanged. Adaptive aggregation beat strict max on both new repos (`pytest: 84.742 vs 83.585`, `Typer: 59.423 vs 56.139`) and raw chunk by a large margin. Full `capped_sum_3` improved pytest (`88.278`) but regressed Typer (`52.663`), so capped remains opt-in under the no-regression policy. The Typer repo score is lower than other repo corpora partly because the current 50 KiB repo file cap skips central files such as `typer/main.py` and `typer/params.py`; see `.10x/tickets/2026-06-28-repo-oversize-source-indexing.md`.

Live ablations on pytest and Typer showed metadata-only indexing is promising while oversize indexing is not default-safe. `--repo-search-metadata` with the default file-size cap improved existing seed scores (`pytest: 84.742 -> 85.971`, `Typer: 59.423 -> 62.062`). `--repo-max-file-bytes 200000` recovered authority-file queries targeting previously skipped central files (`pytest: 23.136 -> 78.622`, `Typer: 27.002 -> 69.619`) but regressed existing seed scores, so oversize remains opt-in or future query-routed behavior.

Metadata-only cross-repo validation improved the five-repo average score/P@5 and improved pytest, Typer, and Click, but regressed turbo-search (`87.760 -> 85.568`) and Requests (`84.426 -> 84.000`) by composite score. Under the no-regression policy, do not promote metadata-only as a default. Keep `--repo-search-metadata` opt-in until metadata placement/scoring is retuned. Evidence: `.10x/evidence/2026-06-28-repo-search-metadata-cross-repo-validation.md`.

File-card metadata indexing (`--repo-file-cards`) is a better opt-in metadata shape than universal preambles, but still not default-safe. It adds separate metadata pages per selected file while keeping code chunks clean. Five-repo validation improved average score/P@5 and improved Requests, Click, pytest, and Typer, but turbo-search regressed (`87.760 -> 85.874`), so default promotion remains blocked. Evidence: `.10x/evidence/2026-06-28-repo-file-card-metadata-validation.md`.

Conditional example/demo path demotion is now part of the default `repo_code` profile. It improved Click (`72.474 -> 72.816`), pytest (`84.742 -> 86.042`), and Typer (`59.423 -> 59.710`) while leaving turbo-search and Requests unchanged. Evidence: `.10x/evidence/2026-06-28-repo-example-path-demotion-validation.md`.

Query-aware documentation path demotion is also part of the default `repo_code` profile. Against the example-demotion baseline, singular `doc/` plus `docs/tutorial/` demotion improved pytest (`86.042 -> 89.191`) and Typer (`59.710 -> 62.787`) while leaving turbo-search, Requests, and Click unchanged. Evidence: `.10x/evidence/2026-06-28-repo-documentation-path-demotion-validation.md`.

Nested private path-segment demotion is also part of the default `repo_code` profile. Against the documentation-demotion baseline, it improved Typer (`62.787 -> 64.411`) while leaving turbo-search, Requests, Click, and pytest unchanged. Evidence: `.10x/evidence/2026-06-28-repo-nested-private-path-demotion-validation.md`.

Embedded agent-artifact path-segment demotion is also part of the default `repo_code` profile. Against the nested-private baseline, it improved Typer (`64.411 -> 64.734`) while leaving turbo-search, Requests, Click, and pytest unchanged. The cumulative five-repo average-score gain from the pre-example baseline is now `77.765 -> 79.785` (`+2.020`). Evidence: `.10x/evidence/2026-06-28-repo-embedded-agent-artifact-demotion-validation.md`.

Example scaffold path demotion is also part of the default `repo_code` profile. Against the embedded-agent-artifact baseline, it improved Typer (`64.734 -> 66.121`) while leaving turbo-search, Requests, Click, and pytest unchanged. Evidence: `.10x/evidence/2026-06-28-repo-example-scaffold-demotion-validation.md`.

The full private-module routing candidate (`_click` special demotion, `core.py`/`models.py` boosts, and parameter-query `utils.py` demotion) reached the five-repo `+2.007` reset target but failed expanded distribution validation because 81.8% of positive gain came from one repo. It is not a general default. The smaller accepted subset (`cli.py` non-CLI demotion, `_click/termui.py` terminal boost, and `index.*` parent-directory matching) passed 13-repo distribution validation: all-repo average score `70.310 -> 70.545`, P@5 `0.448 -> 0.452`, positive gains on turbo-search, Typer, and Django, no repo-level score/P@5 regressions, and largest gain share 59.9%. Evidence: `.10x/evidence/2026-06-28-expanded-repo-ranking-basket-validation.md`.

Broad package-root source recognition plus conservative fixture/snapshot scaffold demotion passed the 13-repo distribution policy and met the user's next +2.0 target: average score `70.545 -> 72.762` (`+2.216`), P@5 unchanged, positive gains on 8 repos, no score/P@5 regressions, and largest gain share 23.5%. Evidence: `.10x/evidence/2026-06-28-repo-source-fixture-routing-validation.md`.

Conventional entrypoint routing passed the 13-repo distribution policy and met the user's next +2.0 target: average score `72.762 -> 74.874` (`+2.112`), P@5 `0.452 -> 0.478`, positive gains on 10 repos, no score/P@5 regressions, and largest gain share 35.2%. Evidence: `.10x/evidence/2026-07-01-repo-conventional-entrypoint-routing-validation.md`.

A per-repo portfolio/routing candidate passed the next +2.0 target but is not a universal default: average score `74.874 -> 77.761` (`+2.887`), P@5 `0.478 -> 0.500`, positive gains on all 13 repos, no score/P@5 regressions, and largest gain share 21.2%. It combines selected file-card/metadata/oversize-card namespaces, candidate-depth tuning, and aggregation routing. Treat it as evidence for a future automatic selector or explicit retrieval profile, not as the current default. Evidence: `.10x/evidence/2026-07-01-repo-portfolio-routing-validation.md`.

A routed profile portfolio passed the next +2.0 target from the `77.761` baseline but is not a universal default: average score `77.761 -> 80.316` (`+2.555`), P@5 `0.500 -> 0.517`, positive gains on 11 repos, no score/P@5 regressions, and largest gain share 31.3%. Universal source/path/stem/test/crate variants regressed some repos; the passing result depends on per-repo profile routing. Treat it as evidence for a future automatic selector or explicit retrieval profile, not as the current default. Evidence: `.10x/evidence/2026-07-02-repo-routed-profile-portfolio-validation.md`.

Oversize file-card indexing (`--repo-oversize-file-cards`) remains opt-in only. It improved Click but regressed turbo-search, Requests, pytest, and Typer in five-repo validation. Evidence: `.10x/evidence/2026-06-28-repo-oversize-file-card-indexing-validation.md`.

Evidence:

- `.10x/evidence/2026-06-28-repo-search-file-ranking-promotion-validation.md`
- `.10x/evidence/2026-06-28-repo-capped-aggregation-default-promotion.md`
- `.10x/evidence/2026-06-28-repo-index-hygiene-and-profile-validation.md`
- `.10x/evidence/2026-06-28-repo-path-symbol-ranking-validation.md`
- `.10x/evidence/2026-06-28-repo-role-diversification-validation.md`
- `.10x/evidence/2026-06-28-cross-repo-click-validation.md`
- `.10x/evidence/2026-06-28-repo-adaptive-aggregation-validation.md`
- `.10x/evidence/2026-06-28-cross-corpus-live-retrieval-evals.md`
- `.10x/evidence/2026-06-28-repo-oversize-metadata-live-eval.md`
- `.10x/evidence/2026-06-28-repo-search-metadata-cross-repo-validation.md`
- `.10x/evidence/2026-06-28-repo-file-card-metadata-validation.md`
- `.10x/evidence/2026-06-28-repo-example-path-demotion-validation.md`
- `.10x/evidence/2026-06-28-repo-documentation-path-demotion-validation.md`
- `.10x/evidence/2026-06-28-repo-nested-private-path-demotion-validation.md`
- `.10x/evidence/2026-06-28-repo-embedded-agent-artifact-demotion-validation.md`
- `.10x/evidence/2026-06-28-repo-example-scaffold-demotion-validation.md`
- `.10x/evidence/2026-06-28-repo-oversize-file-card-indexing-validation.md`
- `.10x/evidence/2026-06-28-repo-private-module-routing-validation.md`
- `.10x/evidence/2026-06-28-expanded-repo-ranking-basket-validation.md`
- `.10x/evidence/2026-06-28-repo-source-fixture-routing-validation.md`
- `.10x/evidence/2026-07-01-repo-conventional-entrypoint-routing-validation.md`
- `.10x/evidence/2026-07-01-repo-portfolio-routing-validation.md`
- `.10x/evidence/2026-07-02-repo-routed-profile-portfolio-validation.md`
