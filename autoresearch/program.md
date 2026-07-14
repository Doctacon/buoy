# buoy-search Repo Search Autoresearch Program

This is the human-owned program for config-only repository search eval research.
Autoresearch agents read it before proposing or running experiments. Do not edit
this file during a research run unless a human explicitly asks for a program
change.

The Python runner is intentionally small: it runs exactly one registered
experiment and writes artifacts. The LLM/human researcher owns hypotheses,
iteration, keep/discard decisions, and durable interpretation.

## Goal

Improve repository search quality for `buoy-search` by comparing retrieval
configurations against a fixed graded eval dataset.

The primary metric is the composite repo search score:

```text
100 * (0.55 * NDCG@10 + 0.20 * Recall@10 + 0.15 * MRR@10 + 0.10 * Precision@5)
```

Component metrics are as important as the aggregate. Do not keep a config solely
because the aggregate improved if it hides a major component regression or an
obvious relevance failure.

## Editable Surfaces

During config-only autoresearch, you may edit or create:

- experiment JSON files under `autoresearch/experiments/`;
- result notes and reports under explicit run output directories;
- durable `.10x/` evidence/review records that interpret runs.

You must not edit during a config-only run:

- source code under `src/`;
- tests under `tests/`;
- `autoresearch/program.md`;
- eval metric implementation;
- seed dataset labels unless the run is explicitly a dataset-calibration task;
- local applied state;
- turbopuffer namespaces or rows.

## Experiment Definition

Run one experiment with:

```bash
uv run python -m buoy_search.autoresearch \
  --experiment autoresearch/experiments/<experiment-id>.json \
  --out autoresearch/runs/<experiment-id>
```

A safe fixture-mode sample is checked in at
`autoresearch/experiments/repo-search-fixture-baseline.json`. Run it with an
output directory outside the repo, or under an intentionally ignored/temporary
path, when you only want to validate runner plumbing:

```bash
uv run python -m buoy_search.autoresearch \
  --experiment autoresearch/experiments/repo-search-fixture-baseline.json \
  --out /tmp/buoy-search-repo-search-fixture-baseline \
  --json
```

Minimal fixture-mode example:

```json
{
  "experiment_id": "repo-search-fixture-baseline",
  "question": "Does the baseline config retrieve expected implementation files?",
  "hypothesis": "The baseline top_k/candidates config should rank direct source files highly.",
  "mode": "fixture",
  "dataset_path": "src/buoy_search/data/buoy_search_repo_search_seed_evals.json",
  "config": {
    "namespace": "github-owner-buoy-search-v1",
    "region": "gcp-us-central1",
    "embedding_model": "BAAI/bge-small-en-v1.5"
  },
  "retrieval_options": {
    "top_k": 5,
    "candidates": 100,
    "doc_kind": null
  },
  "fixture_hits": {
    "github-url-routing": [
      {"path": "src/buoy_search/crawler.py", "title": "crawler.py"}
    ]
  }
}
```

Live mode is retrieval-only and requires current human authorization plus
`TURBOPUFFER_API_KEY` in the environment:

```json
{
  "experiment_id": "repo-search-live-baseline",
  "question": "How does the baseline live namespace score?",
  "hypothesis": "The indexed repo namespace should retrieve grade-3 source files in the top results.",
  "mode": "live",
  "dataset_path": "src/buoy_search/data/buoy_search_repo_search_seed_evals.json",
  "config": {
    "namespace": "github-owner-buoy-search-v1",
    "region": "gcp-us-central1",
    "embedding_model": "BAAI/bge-small-en-v1.5"
  },
  "retrieval_options": {
    "top_k": 10,
    "candidates": 100,
    "doc_kind": null
  }
}
```

## Single Iteration

1. State one hypothesis in the experiment JSON.
2. Choose one config change only: `top_k`, `candidates`, `doc_kind`, or another
   already exposed retrieval option.
3. Run exactly one experiment with `python -m buoy_search.autoresearch`.
4. Inspect `plan.json`, `result.json`, and `report.md`.
5. Compare composite and component metrics against the current baseline.
6. Record verdict and limits in durable evidence/review when the result matters.
7. Keep, discard, mutate, or ask for human review.

## Keep / Discard Guidance

Keep a candidate config when:

- repo search score improves meaningfully;
- no component metric regresses enough to matter;
- top failed cases are understood;
- complexity stays zero or near-zero because the change is configuration only.

Discard when:

- improvement is noise or fixture overfitting;
- NDCG improves but recall or MRR regresses materially;
- it depends on source mutation, live writes, namespace changes, or unapproved
  dataset edits;
- the result cannot be reproduced from saved artifacts.

## Safety Boundaries

The runner rejects experiment fields that imply writes, applies, deletes,
namespace management, patches, or source mutation. Do not work around that guard.

Fixture mode is the default for local/test validation and performs no credential
reads or turbopuffer calls. Live mode is retrieval-only. Never run apply,
`--approve`, stale deletion, namespace deletion, or namespace creation as part
of this autoresearch program.
