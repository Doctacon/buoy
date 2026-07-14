Status: active
Created: 2026-06-28
Updated: 2026-07-14

# Repo Search Composite Eval and Config Autoresearch

## Purpose and scope

Define a deterministic retrieval-quality evaluation surface for GitHub repository search and a first-pass autoresearch loop that can compare retrieval configurations without mutating indexing code or live turbopuffer state.

The first target corpus was this repository under its pre-rebrand `turbo-search` identity. Current fixture/data paths use the Buoy technical identity `buoy-search`; already-applied remote namespaces retain their original semantic names. The dataset uses graded source labels drafted from repository inspection. Live validation may run retrieval/eval commands against an already-applied turbopuffer namespace, but MUST NOT run live writes, deletes, namespace creation, namespace deletion, or state mutation.

## Behavior

### Graded eval cases

An eval dataset MUST be a JSON document containing hand-authored cases. Each case MUST include:

- stable `id`;
- natural-language `question`;
- one or more graded judgments over expected source targets.

Each judgment MUST identify at least one source locator:

- `repo_path` for GitHub repository files;
- `url` for canonical source URL;
- optional `section_path` when a specific section matters.

Each judgment MUST include integer `grade` in `[0, 3]`:

- `3`: source directly answers the question;
- `2`: source is useful supporting context;
- `1`: source is tangential but plausibly useful;
- `0`: source is explicitly irrelevant/noisy when included as a negative example.

Judgment reasons SHOULD be recorded for reviewer calibration.

### Composite score

The repo search score MUST be reported on a `0.0` to `100.0` scale:

```text
repo_search_score = 100 * (
  0.55 * ndcg_at_10
+ 0.20 * recall_at_10
+ 0.15 * mrr_at_10
+ 0.10 * precision_at_5
)
```

Metric definitions:

- `NDCG@10`: graded ranking quality using `2^grade - 1` gain and ideal DCG over the same case judgments.
- `Recall@10`: fraction of relevant judged targets with `grade > 0` retrieved in the top 10.
- `MRR@10`: reciprocal rank of the first hit matching a judgment with `grade > 0`; `0` when none match.
- `Precision@5`: fraction of the top 5 hits matching any judgment with `grade > 0`.

The report MUST include per-case component metrics and aggregate component means. A composite score without component metrics is insufficient.

### Matching

A retrieved hit matches a judgment when any available locator matches:

- exact or normalized substring URL match;
- exact repo path match against hit `path`, source metadata `repo_path`, URL path suffix, or displayed path;
- optional section-path containment when provided by the judgment.

Matching MUST be deterministic and local. LLM judging is out of scope for the first implementation slice.

### Config-only autoresearch

The first autoresearch loop MUST be config-only. It MAY compare retrieval configurations such as:

- `top_k`;
- candidate count;
- ANN/BM25 enabled/disabled arms only if existing retrieval code already supports the mode;
- BM25 field weights only if exposed as configuration rather than code edits;
- source/doc filters that are already represented as retrieval configuration.

It MUST NOT modify retrieval implementation code during a trial. It MUST NOT tune against held-out cases if a split is present.

A one-shot runner MUST:

1. read one experiment definition;
2. run the fixed graded eval against one configured namespace or dry-run fixture;
3. write raw result JSON and a human-readable report;
4. append or emit a result row with score, component metrics, config, status, and notes.

The Python runner owns one trial only. The human/LLM research program owns hypothesis selection, keep/discard decisions, and iteration.

### Safety

- Dry-run/list modes MUST remain available without credentials and without turbopuffer calls.
- Live eval mode MAY read `TURBOPUFFER_API_KEY` and query turbopuffer only when explicitly requested.
- Live eval mode MUST NOT call apply, write, delete, create namespace, delete namespace, or update local applied state.
- Result artifacts MUST NOT persist secrets.

## Acceptance criteria

- The existing smoke eval dataset remains loadable and backward compatible.
- The graded Buoy repository eval dataset can be loaded and scored deterministically from mocked hits.
- The composite score reports NDCG@10, Recall@10, MRR@10, Precision@5, and `repo_search_score`.
- The CLI or runner can execute a dry-run/list mode without credentials.
- The config-only autoresearch one-shot runner can execute one registered experiment and write result artifacts without modifying source code.
- Tests cover metric math, matching, dataset validation, and runner dry-run behavior.

## Explicit exclusions

- LLM-as-judge grading.
- Reranker implementation.
- Query rewriting implementation.
- Live turbopuffer writes/deletes or namespace management.
- Infinite autonomous daemon loop.
- Private repository ingestion/evaluation.
