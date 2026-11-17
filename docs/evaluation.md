# Evaluate search quality

Use hand-authored datasets to make retrieval changes measurable. Eval listing is local-only by default; live evaluation is an explicit retrieval operation against an already-applied namespace.

## Inspect an eval dataset

```bash
uv run buoy evals \
  --dry-run \
  --dataset src/buoy_search/data/scrapling_retrieval_smoke_evals.json \
  --namespace site-scrapling-readthedocs-io-v1 \
  --json
```

Dry-run mode lists questions and expected source hints without credentials, embeddings, or turbopuffer calls.

## Run live evals

```bash
export TURBOPUFFER_API_KEY="..."
uv run buoy evals \
  --live \
  --dataset src/buoy_search/data/scrapling_retrieval_smoke_evals.json \
  --namespace site-scrapling-readthedocs-io-v1 \
  --json
```

Live evals retrieve only. They never apply rows, delete stale rows, delete namespaces, or update local applied state.

The ranking flags accepted by `retrieve` are also available to `evals`, which makes controlled ranking comparisons possible.

## Dataset shape

Repository datasets use a natural-language `question` and graded `judgments`. Each judgment contains:

- repo-relative `repo_path`;
- optional `url` or `section_path`;
- integer relevance `grade` from 0 to 3;
- reviewer-facing `reason`.

The seed dataset for this codebase is:

```text
src/buoy_search/data/buoy_search_repo_search_v3.json
```

Its labels are assistant-drafted and marked `human_approved_ground_truth: false`; treat them as calibration data until a person reviews them. Version 2 carries the version-1 judgments forward through an explicit path map for the subpackage layout and remains `baseline_status: pending`. Its path-membership manifest proves only that current judged paths exist; it is not a corpus identity or source snapshot and cannot support promotion. Historical version-1 bytes remain immutable evidence and are validated against their recorded manifest rather than against the current checkout.

## Repository score

Repository evals report component metrics and a composite score from 0 to 100:

```text
repo_search_score = 100 * (
  0.55 * NDCG@10
+ 0.20 * Recall@10
+ 0.15 * MRR@10
+ 0.10 * Precision@5
)
```

NDCG rewards correct graded ordering, recall checks whether relevant files were found, MRR rewards an early first relevant result, and precision limits noise in the first five results.

## One-shot autoresearch

Autoresearch runs one declared retrieval configuration and writes a reproducible report. The fixture baseline is safe and requires no credentials:

```bash
uv run python -m buoy_search.evals.autoresearch \
  --experiment autoresearch/experiments/repo-search-fixture-baseline.json \
  --out /tmp/buoy-repo-search-fixture-baseline \
  --json
```

A run writes:

```text
plan.json
result.json
report.md
```

The runner is config-only and one-shot. Live mode is retrieval-only against an existing namespace; it never performs apply, deletion, or namespace management.

## A useful comparison loop

1. Keep the source namespace and eval dataset fixed.
2. Record the current retrieval configuration and score.
3. Change one ranking parameter.
4. Re-run the same dataset.
5. Inspect both aggregate metrics and per-question regressions before promoting a default.

## Default promotion gate

Active repository and website defaults have one packaged authority:

```text
src/buoy_search/data/ranking_defaults.json
```

Changing ranking implementation or adding an experimental option does not promote it. Every pull request runs the same fast local checks; the full promotion gate applies only when this authority file differs from the pull request's merge base.

A promotion must check in one matching immutable artifact under `.10x/evidence/.storage/ranking-promotions/` and reference a basket in `src/buoy_search/data/repo_ranking_promotion_baskets.json`. Every registered basket has exactly 13 repositories. Each recorded member names actual versioned dataset, corpus-manifest, and baseline-benchmark files whose raw hashes are reproduced by CI. CI also validates dataset identity and cases/judgments plus corpus repository/source identity and its nonempty canonical path/content-hash inventory; consistently rehashing unrelated or malformed JSON does not make it valid evidence. Missing, tampered, path-only, or self-declared files are categorically ineligible. The production registry remains empty while current Buoy v2 is pending.

The artifact also binds the old and proposed authority bytes and requires exactly equal non-authority baseline/candidate inputs. Retrieval options use only the closed `top_k`, `candidates`, `use_ann`, and `use_bm25` schema. URLs, headers, arbitrary objects, credentials, and credential-like values are rejected. CI recomputes basket, benchmark, and distribution-aware policy identities offline; it does not run retrieval or load a model.

Pull requests compare against their merge base. Protected-branch pushes compare against the event's previous SHA. A missing comparison base fails closed. The one-time authority introduction is explicit and accepted only when its exact bytes match the reviewed pre-file defaults hash.

See [Retrieve and rank results](retrieval.md) for ranking controls.
