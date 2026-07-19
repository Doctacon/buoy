---
name: turbopuffer-site-rag
description: Build, operate, or query turbopuffer-backed RAG indexes for websites. Use for Scrapling crawls, local plan/apply validation, namespace planning, retrieval with citations, incremental updates, and cost-safe guardrails around turbopuffer writes.
---

# Turbopuffer Site RAG

This skill captures the generic Scrapling-based website-to-turbopuffer RAG workflow.

## Repository location

Run `uv run buoy ...` commands from the repository root.

If this skill is installed globally by symlink, resolve the symlink target to find the repository clone. Otherwise, ask the user for the local clone path before running repo commands from another directory.

## Credentials from `.env`

`buoy` deliberately reads `TURBOPUFFER_API_KEY` from the process environment; it does not parse `.env` itself. When the repository `.env` is the intended credential source, load it only into the command subshell so an inherited key cannot silently override it:

```bash
(
  set -a
  . ./.env
  set +a
  uv run buoy <command>
)
```

Do not print, persist, or copy the key. `TURBOPUFFER_REGION`, `TURBOPUFFER_NAMESPACE`, `BUOY_EMBEDDING_MODEL`, and `BUOY_EMBEDDING_PRECISION` remain optional non-secret environment overrides; CLI flags can override them for retrieval/evals. Apply always uses the precision recorded in its reviewed plan.

## Compact applied state

Each `(site_id, namespace)` has an embedded local DuckDB ledger at:

```text
.buoy/state/<site-id>/<namespace>/state.duckdb
```

Existing projects with only `.turbo-search` use that root in place with a warning; see `docs/migrating-to-buoy.md` for the bounded 0.2 compatibility contract.

- The ledger stores current row state plus compact apply summaries, not full row snapshots.
- DuckDB is the only applied-state authority. Obsolete JSON applied-state files are ignored and left unchanged; without `state.duckdb`, the next approved apply uses first-apply behavior and re-upserts the reviewed corpus.
- `apply --approve` takes a non-blocking lock for that namespace before embeddings or Turbopuffer writes. A same-namespace contender fails with a busy error; different namespaces have independent databases and can apply concurrently.
- This is embedded local state: do not add or depend on Quack, a listener, or shared cross-machine state.

## Non-negotiable guardrails

- Do **not** persist API keys, Proton Pass output, tokens, private vault names, private item titles, or share IDs to disk.
- Do **not** run live turbopuffer writes, namespace deletion, namespace replacement, or live evals unless the user explicitly approves that action in the current conversation.
- Default crawl/plan/apply-preflight commands to dry-run with respect to turbopuffer; crawling a public source may still use the network.
- Use open-source/local components where practical:
  - local embeddings: `BAAI/bge-small-en-v1.5`
  - scraper/crawler: Scrapling
  - package manager: `uv`
- Respect crawl ethics by default: same-site only, `robots_txt_obey = True`, conservative concurrency, crawl delay, and no paywall/auth/protection bypass unless explicitly authorized.
- When answering from a site index, retrieve context first and cite retrieved page titles/URLs.

## Generic Scrapling site workflow

Use this when building or testing the “base URL → crawl → chunks → namespace → search” workflow.

The polished workflow is Terraform-like:

1. `buoy plan`: turbopuffer-local preview. It may fetch the public source, then extracts Markdown, chunks, compares with local applied state, and writes review artifacts. It does not read turbopuffer credentials, load embeddings, create namespaces, or call turbopuffer. Interactive text-mode runs show default one-line stderr progress; use `--no-progress` to disable it. Versioned docs sites stop before page crawling by default with `--docs-version-policy warn`; use `latest`, `stable-latest`, `latest-nightly`, or `all` to make the policy explicit.
2. `buoy apply` without `--approve`: local-only preflight. Re-read the saved plan, verify artifacts, recompute the local diff, and report what would happen. No credentials, embeddings, or turbopuffer calls.
3. `buoy apply --approve`: explicit live path. Require `TURBOPUFFER_API_KEY` in the environment, embed/upsert only new or changed chunks using the plan-recorded precision, and update local applied state after success. Float16 is opt-in at plan time and requires CUDA or Apple MPS.
4. `--delete-stale`: extra delete guardrail. Stale rows are retained by default; live stale deletion requires both `--approve` and `--delete-stale`.

Plan artifacts are Markdown/JSON-first: `plan.json`, `summary.json`, `manifest.json`, `chunks.jsonl`, and `pages/*.md`. Pending, failed, and preflight plans remain for review/retry; successful approved apply removes its exact plan directory, and a new verified plan removes older same-namespace sibling plans. Copy artifacts elsewhere before approved apply when long-term audit/source retention is needed. Local applied state lives under `.buoy/state/.../state.duckdb` and is gitignored.

See [Scrapling site workflow](references/scrapling-site-workflow.md) for commands and design notes.

## Dry-run Scrapling crawler

Use the first-class CLI from the repository root:

```bash
uv run buoy crawl \
  --base-url "https://scrapling.readthedocs.io/en/latest/" \
  --max-pages 10 \
  --max-chunks 100 \
  --css-selector ".md-content__inner" \
  --json
```

This command must report `dry_run: true` and `turbopuffer_api_calls: false`.

## Live apply checklist

Only proceed if the user explicitly asks for a live generic site apply.

1. Run `buoy plan` first and inspect `summary.json`, `plan.json`, `manifest.json`, `chunks.jsonl`, and generated `pages/*.md`. Use `--include-path` / `--exclude-path` before apply when the crawl contains duplicate or unwanted paths such as `/llms-full.txt`.
2. Run apply preflight without approval:

```bash
uv run buoy apply
```

`apply` defaults to the newest `artifacts/site-crawls/**/plan.json` and the namespace recorded in that plan. Use `--json` for scripts/automation. Use `--plan` or `--namespace` only when overriding those defaults.

3. Confirm the namespace, rows to upsert, embeddings to generate, stale row counts, and whether stale deletion is desired. Default: retain stale rows; never delete namespaces here.
4. When the repository `.env` is the approved credential source, load it only in the command subshell; the CLI reads the resulting process environment and never prints or stores the key:

```bash
(
  set -a
  . ./.env
  set +a
  uv run buoy apply --approve
)
```

   Otherwise, set `TURBOPUFFER_API_KEY` only in the active shell and run the same approved command. Pass `--region` and `--namespace` when the reviewed plan requires non-default values.

5. Delete stale rows only when explicitly requested with both `--approve` and `--delete-stale`.
6. Record evidence with counts and command shape, never secret values, private vault names, item titles, share IDs, or token/API-key values.
