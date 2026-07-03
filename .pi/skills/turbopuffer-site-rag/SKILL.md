---
name: turbopuffer-site-rag
description: Build, operate, or query turbopuffer-backed RAG indexes for websites. Use for Scrapling crawls, local plan/apply validation, namespace planning, retrieval with citations, incremental updates, and cost-safe guardrails around turbopuffer writes.
---

# Turbopuffer Site RAG

This skill captures the generic Scrapling-based website-to-turbopuffer RAG workflow.

## Repository location

Run `uv run turbo-search ...` commands from the `turbo-search` repository root.

If this skill is installed globally by symlink, resolve the symlink target to find the repository clone. Otherwise, ask the user for the local clone path before running repo commands from another directory.

## Non-negotiable guardrails

- Do **not** persist API keys, Proton Pass output, tokens, private vault names, private item titles, or share IDs to disk.
- Do **not** run live turbopuffer writes, namespace deletion, namespace replacement, or live evals unless the user explicitly approves that action in the current conversation.
- Default crawl/plan/apply-preflight commands to dry-run/local-only.
- Use open-source/local components where practical:
  - local embeddings: `BAAI/bge-small-en-v1.5`
  - scraper/crawler: Scrapling
  - package manager: `uv`
- Respect crawl ethics by default: same-site only, `robots_txt_obey = True`, conservative concurrency, crawl delay, and no paywall/auth/protection bypass unless explicitly authorized.
- When answering from a site index, retrieve context first and cite retrieved page titles/URLs.

## Generic Scrapling site workflow

Use this when building or testing the “base URL → crawl → chunks → namespace → search” workflow.

The polished workflow is Terraform-like:

1. `turbo-search plan`: local-only preview. Crawl with Scrapling, extract Markdown, chunk, compare with local applied state, and write review artifacts. No credentials, embeddings, namespace creation, or turbopuffer calls. Interactive text-mode runs show default one-line stderr progress; use `--no-progress` to disable it. Versioned docs sites stop before page crawling by default with `--docs-version-policy warn`; use `latest`, `stable-latest`, `latest-nightly`, or `all` to make the policy explicit.
2. `turbo-search apply` without `--approve`: local-only preflight. Re-read the saved plan, verify artifacts, recompute the local diff, and report what would happen. No credentials, embeddings, or turbopuffer calls.
3. `turbo-search apply --approve`: explicit live path. Require `TURBOPUFFER_API_KEY` in the environment, embed/upsert only new or changed chunks, and update local applied state after success.
4. `--delete-stale`: extra delete guardrail. Stale rows are retained by default; live stale deletion requires both `--approve` and `--delete-stale`.

Plan artifacts are Markdown/JSON-first: `plan.json`, `summary.json`, `manifest.json`, `chunks.jsonl`, and `pages/*.md`. Local applied state lives under `.turbo-search/state/...` and is gitignored.

See [Scrapling site workflow](references/scrapling-site-workflow.md) for commands and design notes.

## Dry-run Scrapling crawler

Use the first-class CLI from the repository root:

```bash
uv run turbo-search crawl \
  --base-url "https://scrapling.readthedocs.io/en/latest/" \
  --max-pages 10 \
  --max-chunks 100 \
  --css-selector ".md-content__inner" \
  --json
```

This command must report `dry_run: true` and `turbopuffer_api_calls: false`.

## Live apply checklist

Only proceed if the user explicitly asks for a live generic site apply.

1. Run `turbo-search plan` first and inspect `summary.json`, `plan.json`, `manifest.json`, `chunks.jsonl`, and generated `pages/*.md`. Use `--include-path` / `--exclude-path` before apply when the crawl contains duplicate or unwanted paths such as `/llms-full.txt`.
2. Run apply preflight without approval:

```bash
uv run turbo-search apply
```

`apply` defaults to the newest `artifacts/site-crawls/**/plan.json` and the namespace recorded in that plan. Use `--json` for scripts/automation. Use `--plan` or `--namespace` only when overriding those defaults.

3. Confirm the namespace, rows to upsert, embeddings to generate, stale row counts, and whether stale deletion is desired. Default: retain stale rows; never delete namespaces here.
4. Retrieve the turbopuffer API key into shell memory only and set environment variables only in the active shell:

```bash
export TURBOPUFFER_REGION=gcp-us-central1
export TURBOPUFFER_NAMESPACE=<approved-namespace>
export TURBOPUFFER_API_KEY=<retrieved into shell memory only>
```

5. Run approved apply only after explicit approval:

```bash
uv run turbo-search apply --approve
```

6. Delete stale rows only when explicitly requested with both `--approve` and `--delete-stale`.
7. Record evidence with counts and command shape, never secret values, private vault names, item titles, share IDs, or token/API-key values.
