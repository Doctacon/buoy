Status: recorded
Created: 2026-06-28
Updated: 2026-06-28
Relates-To: .10x/tickets/2026-06-28-repo-file-card-metadata-indexing.md, .10x/evidence/2026-06-28-repo-search-metadata-cross-repo-validation.md, .10x/tickets/2026-06-28-repo-search-heavy-ranking-experiments.md

# Repo File-Card Metadata Validation

## What was observed

Implemented and validated an opt-in repository indexing mode, `--repo-file-cards`, that adds separate file metadata pages for selected repository files while keeping ordinary code chunks clean.

The file-card pages include:

- repository path;
- path tokens;
- file stem;
- language;
- Python def/class symbols and split symbol tokens when available.

A small file-card-aware ranking adjustment was also added for `repo_code` ranking: generic file-card-only groups are demoted unless the query has a precise path/stem match, preventing generic metadata cards from too easily outranking source chunks.

No default indexing behavior was changed.

## Procedure

Unit validation:

```bash
uv run python -m unittest tests.test_retriever tests.test_github_repo tests.test_cli
# 54 tests OK

uv run python -m unittest discover tests
# 144 tests OK

git diff --check
# OK
```

Live plan/apply/eval, after user approval:

```bash
uv run turbo-search plan https://github.com/<owner>/<repo> \
  --namespace <new-file-card-namespace> \
  --out-dir artifacts/site-crawls/<repo>-file-cards-plan-20260628 \
  --repo-file-cards \
  --json

uv run turbo-search apply --plan artifacts/site-crawls/<repo>-file-cards-plan-20260628/plan.json \
  --namespace <new-file-card-namespace> \
  --approve --json

uv run turbo-search evals --live --dataset <repo-seed-dataset> \
  --namespace <new-file-card-namespace> \
  --top-k 10 --candidates 200 --json
```

No `--repo-search-metadata`, no oversize flag, no `--delete-stale`, and no namespace deletion were used.

Artifacts:

- `autoresearch/runs/repo-file-cards-20260628/file-card-summary.json`
- `autoresearch/runs/repo-file-cards-20260628/file-card-report.md`
- plan/apply/eval JSON under `autoresearch/runs/repo-file-cards-20260628/`

## Apply counts

| Repo | Namespace | Files | File cards | Rows | Deleted |
|---|---|---:|---:|---:|---:|
| turbo-search | `github-doctacon-turbo-search-v4-file-cards` | 29 | 29 | 567 | 0 |
| requests | `github-psf-requests-v3-file-cards` | 117 | 117 | 853 | 0 |
| click | `github-pallets-click-v3-file-cards` | 140 | 140 | 1364 | 0 |
| pytest | `github-pytest-dev-pytest-v3-file-cards` | 573 | 573 | 4144 | 0 |
| Typer | `github-fastapi-typer-v3-file-cards` | 644 | 644 | 3165 | 0 |

## Eval results

| Repo | Baseline score | File-card score | Δ score | Baseline P@5 | File-card P@5 | Δ P@5 | Result |
|---|---:|---:|---:|---:|---:|---:|---|
| turbo-search | 87.760 | 85.874 | -1.886 | 0.540 | 0.540 | +0.000 | regression |
| requests | 84.426 | 84.457 | +0.031 | 0.420 | 0.440 | +0.020 | pass |
| click | 72.474 | 77.485 | +5.011 | 0.400 | 0.440 | +0.040 | pass |
| pytest | 84.742 | 86.171 | +1.429 | 0.640 | 0.660 | +0.020 | pass |
| Typer | 59.423 | 64.728 | +5.305 | 0.380 | 0.420 | +0.040 | pass |

Averages across the five repo basket:

- Score: `77.765 -> 79.743` (`+1.978`)
- P@5: `0.476 -> 0.500` (`+0.024`)

## What this supports or challenges

Supports:

- File cards are more promising than metadata preambles:
  - metadata preambles regressed turbo-search and Requests;
  - file cards still regress turbo-search, but Requests no longer regresses and Click improves more.
- File cards improve four of five repos and improve average score/P@5.

Challenges:

- File cards fail the no-regression promotion policy because turbo-search regresses by composite score (`87.760 -> 85.874`).
- Turbo-search regressions are concentrated in cases where metadata cards alter NDCG/MRR ordering, especially `evals-composite-metrics`, `plan-artifacts-github-metadata`, and `chunking-code-and-markdown`.

## Conclusion

Do not promote `--repo-file-cards` as a default. Keep it opt-in. The next ranking work should target turbo-search file-card regressions before reconsidering default promotion.
