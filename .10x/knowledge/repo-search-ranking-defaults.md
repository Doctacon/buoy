Status: active
Created: 2026-06-28
Updated: 2026-06-28

# Repo and Website Ranking Defaults

`turbo-search` retrieval defaults to hybrid ANN + BM25 + RRF followed by namespace-aware final ranking. GitHub repo planning also excludes generated/vendor directories plus local agent memory/run artifacts (`.10x/`, `.loom/`, `.pi/`, `.turbo-search/`, `artifacts/`, `autoresearch/`) and eval fixture JSON under `/data/` by default so repository search stays focused on source, tests, and user-facing docs. Repo planning skips text files above 51200 bytes by default; experiments can opt into larger files with `--repo-max-file-bytes` and searchable path/Python-symbol text with `--repo-search-metadata`.

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

- process/project-agent and run-artifact paths such as `.pi/`, `.10x/`, `.loom/`, `.claude/`, `.cursor/`, `.turbo-search/`, `artifacts/`, and `autoresearch/` are demoted strongly;
- eval/fixture/dataset JSON under `/data/` is demoted strongly so answer-key-like files do not dominate implementation queries;
- `docs/`, README/CHANGELOG, and other Markdown files are demoted gently, with a partial recovery for exact documentation filename matches such as `docs/api.rst` on API queries;
- example/demo paths such as `examples/`, `docs_src/`, `example_scripts/`, `/example/`, and `/examples/` are demoted for non-example queries;
- `tests/` files get a light boost because repository evals often ask where behavior is validated;
- source/config files are mostly neutral, with conservative query-aware boosts for exact source filename matches and Python `def`/`class` declarations already present in retrieved chunks;
- when top five lacks docs/tests and rank 1 is an implementation file, one strong docs/tests companion may be promoted into slot five without replacing the top implementation hit.

Generic website rows without `repo_path` remain chunk-keyed and are not collapsed by file ranking.

Use capped URL/page-level aggregation for website experiments with:

```bash
turbo-search retrieve "..." --ranking-aggregation capped-sum-3
```

`ranking_mode=page` groups website chunks by canonical URL while repository rows still group by `repo_path`. Page ranking improved assistant-drafted website evals on `site-turbopuffer-com-v1`, `site-sqlmesh-readthedocs-io-v1`, and `site-pi-dev-v1`, so page/max/pool20 was promoted as the `site-*` default on 2026-06-28. Website capped aggregation remains opt-in because it was not uniformly better than max at the precision-oriented pool. Expanded validation on Ruff and Typer docs showed capped_sum_3 improved both new site seed datasets, but prior Pi-site evidence had a tiny capped-score regression at pool 20 while P@5 was unchanged; see `.10x/tickets/2026-06-28-website-capped-aggregation-default-review.md`. Use raw chunk order for debugging with:

```bash
turbo-search retrieve "..." --ranking-mode chunk --ranking-profile none
```

The repo default was first promoted after live retrieval-only experiments improved the `turbo-search` seed repo eval from `Precision@5 = 0.300` and `repo_search_score = 59.967` to `Precision@5 = 0.500` and `repo_search_score = 87.251` on namespace `github-doctacon-turbo-search-v1`. A follow-up capped aggregation experiment improved `turbo-search` further, but cross-repo validation on `psf/requests` showed full capped aggregation was not a safe universal default. After current `main` shipped project-memory/eval artifacts, a clean current-main namespace plus query-intent, path/symbol, role-diversification, and adaptive aggregation profile validates `turbo-search` at `Precision@5 = 0.540`, `Recall@10 = 0.833`, `NDCG@10 = 0.922`, and `repo_search_score = 87.760`. Cross-repo validation on `psf/requests` improved from the pre-profile `repo_search_score = 81.809` to `84.426` and `Precision@5 = 0.360` to `0.420`. Third-repo validation on `pallets/click` challenged the strict max aggregation default; adaptive aggregation improved Click max from `67.150` to `72.474` without regressing turbo-search or Requests. Across three repos, adaptive aggregation scored `81.553` average versus `79.457` for max and `81.411` for capped_sum_3.

Expanded validation on `pytest-dev/pytest` and `fastapi/typer` kept the repo default unchanged. Adaptive aggregation beat strict max on both new repos (`pytest: 84.742 vs 83.585`, `Typer: 59.423 vs 56.139`) and raw chunk by a large margin. Full `capped_sum_3` improved pytest (`88.278`) but regressed Typer (`52.663`), so capped remains opt-in under the no-regression policy. The Typer repo score is lower than other repo corpora partly because the current 50 KiB repo file cap skips central files such as `typer/main.py` and `typer/params.py`; see `.10x/tickets/2026-06-28-repo-oversize-source-indexing.md`.

Live ablations on pytest and Typer showed metadata-only indexing is promising while oversize indexing is not default-safe. `--repo-search-metadata` with the default file-size cap improved existing seed scores (`pytest: 84.742 -> 85.971`, `Typer: 59.423 -> 62.062`). `--repo-max-file-bytes 200000` recovered authority-file queries targeting previously skipped central files (`pytest: 23.136 -> 78.622`, `Typer: 27.002 -> 69.619`) but regressed existing seed scores, so oversize remains opt-in or future query-routed behavior.

Metadata-only cross-repo validation improved the five-repo average score/P@5 and improved pytest, Typer, and Click, but regressed turbo-search (`87.760 -> 85.568`) and Requests (`84.426 -> 84.000`) by composite score. Under the no-regression policy, do not promote metadata-only as a default. Keep `--repo-search-metadata` opt-in until metadata placement/scoring is retuned. Evidence: `.10x/evidence/2026-06-28-repo-search-metadata-cross-repo-validation.md`.

File-card metadata indexing (`--repo-file-cards`) is a better opt-in metadata shape than universal preambles, but still not default-safe. It adds separate metadata pages per selected file while keeping code chunks clean. Five-repo validation improved average score/P@5 and improved Requests, Click, pytest, and Typer, but turbo-search regressed (`87.760 -> 85.874`), so default promotion remains blocked. Evidence: `.10x/evidence/2026-06-28-repo-file-card-metadata-validation.md`.

Conditional example/demo path demotion is now part of the default `repo_code` profile. It improved Click (`72.474 -> 72.816`), pytest (`84.742 -> 86.042`), and Typer (`59.423 -> 59.710`) while leaving turbo-search and Requests unchanged. Evidence: `.10x/evidence/2026-06-28-repo-example-path-demotion-validation.md`.

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
