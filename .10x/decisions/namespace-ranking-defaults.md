Status: active
Created: 2026-06-28
Updated: 2026-06-28

# Namespace Ranking Defaults

## Context

`turbo-search` uses namespace-aware final ranking after hybrid ANN + BM25 + RRF. Website and repository indexes have different duplicate patterns:

- website rows need page-level deduplication by canonical URL;
- GitHub repository rows need file-level grouping by `repo_path`;
- repository files may have multiple matching chunks, but repeated evidence can also over-rank broad core files;
- current `repo_code` scoring also applies artifact demotion, conditional example/demo path demotion, query-intent handling, path/symbol boosts, and one-companion docs/tests role diversification.

Earlier evidence rejected universal `capped_sum_3` because it improved `turbo-search` but regressed `psf/requests`. Third-repo validation on `pallets/click` reopened the aggregation question: `capped_sum_3` was average-better across three repos, but still regressed `psf/requests`.

A conservative adaptive aggregation rule was then tested: start with `max`, and add a 5% bonus for each of up to two additional chunks from the same file only when those chunks are close to the best file chunk (`score >= 0.80 * best_chunk_score`). This keeps single-best-file behavior as the base, rewards repeated same-file evidence lightly, and avoids the large full-sum jumps that caused Requests regressions.

Three-repo live retrieval-only validation with the current scoring profile:

```text
max average:             Score = 79.457, P@5 = 0.440
capped_sum_3 average:    Score = 81.411, P@5 = 0.460
adaptive_sum_3 average:  Score = 81.553, P@5 = 0.453
```

`adaptive_sum_3` improved every validation repo versus `max`:

```text
turbo-search: 87.126 -> 87.760
psf/requests: 84.093 -> 84.426
pallets/click: 67.150 -> 72.474
```

This decision supersedes `.10x/decisions/superseded/namespace-ranking-defaults-max-aggregation.md`. The older universal capped-sum decision remains superseded at `.10x/decisions/superseded/namespace-ranking-defaults-capped-sum-3.md`.

## Decision

Use namespace-aware defaults:

Website namespaces (`site-*`):

```text
candidates = 200
ranking_mode = page
ranking_profile = none
ranking_pool = 20
ranking_aggregation = max
```

Repository/general namespaces, including GitHub namespaces:

```text
candidates = 200
ranking_mode = file
ranking_profile = repo_code
ranking_pool = 100
ranking_aggregation = adaptive_sum_3
```

`adaptive_sum_3` uses the best chunk per file plus a small close-evidence bonus:

```text
score = best_chunk_score * (1 + 0.05 * close_extra_chunk_count)
close_extra_chunk_count = count of chunks 2..3 where chunk_score >= 0.80 * best_chunk_score
```

User-supplied CLI/config ranking options continue to override namespace defaults. `--ranking-aggregation max` remains available for strict single-best-chunk file/page ranking, and `--ranking-aggregation capped-sum-3` remains available for opt-in repo or website experiments.

Within `ranking_profile=repo_code`, example/demo paths such as `examples/`, `docs_src/`, `example_scripts/`, `/example/`, and `/examples/` are demoted for queries that are not explicitly asking for examples/tutorials/samples/demos. This is part of the default repository profile rather than a separate CLI knob.

## Alternatives considered

- Keep repo `max`: rejected after adaptive aggregation improved all three validation repos and preserved the no-regression property that made `max` attractive.
- Promote `capped_sum_3` for all repo namespaces: rejected because it still regresses `psf/requests` versus `max` and `adaptive_sum_3` despite strong Click and turbo-search results.
- Use learned/adaptive source-specific aggregation: deferred until there are more labels and repositories.

## Consequences

- Repository retrieval/evals without explicit ranking flags now use a conservative repeated-file evidence bonus.
- Website defaults remain unchanged at page/max/pool20.
- Strict `max` and full `capped_sum_3` remain inspectable CLI/config options.
- Further repo score improvements should target index hygiene, richer path/symbol metadata, example-aware query routing, or learned/adaptive ranking after more labeled repos.

## Evidence

- `.10x/evidence/2026-06-28-repo-capped-aggregation-default-promotion.md`
- `.10x/evidence/2026-06-28-repo-index-hygiene-and-profile-validation.md`
- `.10x/evidence/2026-06-28-cross-repo-requests-validation.md`
- `.10x/evidence/2026-06-28-repo-query-intent-profile-validation.md`
- `.10x/evidence/2026-06-28-repo-path-symbol-ranking-validation.md`
- `.10x/evidence/2026-06-28-repo-role-diversification-validation.md`
- `.10x/evidence/2026-06-28-cross-repo-click-validation.md`
- `.10x/evidence/2026-06-28-repo-adaptive-aggregation-validation.md`
- `.10x/evidence/2026-06-28-website-ranking-evidence-hardening.md`
- `.10x/evidence/2026-06-28-repo-example-path-demotion-validation.md`
