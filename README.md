# turbo-search
<img src="images/puffin.png" height="120" alt="turbo-search puffin" />
Tiny CLI for turning public websites into turbopuffer-backed hybrid RAG indexes.

The main workflow is intentionally Terraform-like:

1. **plan**: crawl and chunk locally; no credentials or turbopuffer calls.
2. **apply**: preflight the latest plan; still local-only.
3. **apply --approve**: embed and upsert only the approved diff.

It uses Scrapling for crawling/extraction, local `BAAI/bge-small-en-v1.5` embeddings, and turbopuffer hybrid retrieval with ANN + BM25 + RRF.

## Setup

```bash
uv sync
```

Optional but recommended for fewer Hugging Face download warnings:

```bash
uv run hf auth login
```

Do **not** commit API keys. Live apply/retrieval read `TURBOPUFFER_API_KEY` from the environment only.

## Optional global command

Install the CLI so `turbo-search` works from any directory:

```bash
# from the repo root
uv tool install --editable . --force

# or from anywhere
uv tool install --editable /path/to/turbo-search --force
```

Verify:

```bash
turbo-search --help
```

When run outside this repo, generated `artifacts/` and `.turbo-search/` state are created in the current directory.

## Index a new website

```bash
# 1. Create a local plan. No credentials, embeddings, or live writes.
uv run turbo-search plan https://example.com/

# 2. Review what would be applied. Still no credentials or live calls.
uv run turbo-search apply

# 3. If the plan looks good, explicitly upsert to turbopuffer.
export TURBOPUFFER_API_KEY="..."
uv run turbo-search apply --approve
```

The namespace is derived from the site, for example:

```text
https://example.com/ -> site-example-com-v1
```

Plan artifacts are written under `artifacts/site-crawls/...` and local applied state is written under `.turbo-search/state/...`. Both are local/generated paths and are gitignored.

## Shape the crawl

Defaults are source-aware:

```text
crawl_strategy: hybrid
website max_pages: 3000
website max_chunks: 120000
website docs_version_policy: warn
GitHub repo max_files: 5000
GitHub repo max_chunks: 100000
GitHub repo max_file_bytes: 51200
strip_trailing_slash: true
```

GitHub repo planning excludes generated/vendor directories plus local agent memory/run artifacts such as `.10x/`, `.loom/`, `.pi/`, `.turbo-search/`, `artifacts/`, `autoresearch/`, and eval fixture JSON under `/data/` by default. For repo-ranking experiments, use `--repo-max-file-bytes` to include larger text files, `--repo-search-metadata` to add searchable path/Python-symbol metadata to generated code pages, or `--repo-file-cards` to add separate searchable metadata card pages per file while keeping code chunks clean; these are opt-in and do not change the default plan.

Useful filters:

```bash
# Only crawl docs pages
uv run turbo-search plan https://example.com/ --include-path /docs/**

# Exclude noisy paths
uv run turbo-search plan https://example.com/ --exclude-path /blog/**

# Bigger site
uv run turbo-search plan https://example.com/ --max-pages 1000 --max-chunks 50000

# Versioned docs site: keep current docs and exclude old version folders
uv run turbo-search plan https://example.com/ --docs-version-policy latest
```

For sites with repeated `/docs/{version}/...` pages, the default `warn` policy stops before page crawling and asks you to choose. Use `--docs-version-policy latest`, `stable-latest`, or `latest-nightly` to add effective excludes for older docs versions while keeping non-versioned pages like blogs/specs eligible. Use `--docs-version-policy all` to keep every version.

Other crawl strategies:

```bash
uv run turbo-search plan https://example.com/ --crawl-strategy sitemap
uv run turbo-search plan https://example.com/ --crawl-strategy link
```

## Incremental updates

Run the same sequence later:

```bash
uv run turbo-search plan https://example.com/
uv run turbo-search apply
uv run turbo-search apply --approve
```

`plan` compares the new crawl against local applied state and reports:

```text
upsert=<new or changed chunks>
unchanged=<already indexed chunks>
stale=<previously indexed chunks missing from the new crawl>
```

Approved apply embeds/upserts only new or changed chunks. Stale rows are retained by default. Delete them only with an extra explicit flag:

```bash
uv run turbo-search apply --approve --delete-stale
```

## Search an indexed site

```bash
uv run turbo-search retrieve \
  "How does this feature work?" \
  --live \
  --namespace site-example-com-v1 \
  --top-k 5
```

Retrieval defaults to hybrid ANN + BM25 + RRF, then namespace-aware final ranking. `site-*` namespaces default to page-level website ranking (`--ranking-mode page --ranking-profile none --ranking-pool 20 --ranking-aggregation max`). Repository namespaces default to file-level ranking (`--ranking-mode file --ranking-profile repo-code --ranking-pool 100 --ranking-aggregation adaptive-sum-3`), which deduplicates chunks by `repo_path`, uses the best chunk per file plus a small close-chunk evidence bonus, gently demotes repository process/docs/eval-artifact paths such as `.pi/`, `.10x/`, `.loom/`, `autoresearch/`, `docs/`, Markdown files, and eval fixture JSON, lightly boosts `tests/` files, applies conservative query-aware path/symbol boosts for exact source/doc filename or Python def/class matches, and may promote one strong doc/test companion into the top five without replacing the top implementation hit. Use `--ranking-aggregation max` for strict single-best-chunk file ranking, `--ranking-aggregation capped-sum-3` to fully reward up to three matching chunks from the same file, or `--ranking-mode chunk --ranking-profile none` to inspect raw chunk-level fused order.

Dry-run retrieval is the default and does not contact turbopuffer:

```bash
uv run turbo-search retrieve "How does this feature work?" --namespace site-example-com-v1
```

## Evaluate repository search quality

Repository search evals use graded source judgments and report a composite score
from 0 to 100:

```text
repo_search_score = 100 * (
  0.55 * NDCG@10
+ 0.20 * Recall@10
+ 0.15 * MRR@10
+ 0.10 * Precision@5
)
```

The seed dataset for this repo lives at:

```text
src/turbo_search/data/turbo_search_repo_search_seed_evals.json
```

Dataset cases contain a natural-language `question` and `judgments` with
repo-relative `repo_path`, optional `url`/`section_path`, integer `grade` from
0 to 3, and a reviewer-facing `reason`. The seed labels are assistant-drafted
and marked `human_approved_ground_truth: false`; use them for calibration until
reviewed.

Run the safe fixture autoresearch sample without credentials or turbopuffer
calls:

```bash
uv run python -m turbo_search.autoresearch \
  --experiment autoresearch/experiments/repo-search-fixture-baseline.json \
  --out /tmp/turbo-search-repo-search-fixture-baseline \
  --json
```

The autoresearch runner executes exactly one config-only trial and writes
`plan.json`, `result.json`, and `report.md`. Live autoresearch mode is
retrieval-only and must target an already-applied namespace; it never performs
apply, writes, deletes, or namespace management.
