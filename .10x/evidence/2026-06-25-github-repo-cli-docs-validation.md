Status: recorded
Created: 2026-06-25
Updated: 2026-06-25
Relates-To: .loom/tickets/2026-06-25-github-repo-cli-docs-validation.md

# GitHub Repo CLI Docs Validation

## What was observed

Completed CLI routing and documentation for automatic public GitHub repository URL ingestion.

Changed files:

- `src/turbo_search/github_repo.py`
  - Added `crawl_github_repo(source, options)` and summary construction for source kind, repo metadata, acquisition strategy, selected/skipped file counts, commit SHA, and chunks.
- `src/turbo_search/cli.py`
  - `crawl` and `plan` now call `detect_source`.
  - GitHub repository sources route to `crawl_github_repo`; ordinary websites still route to `crawl_site`.
  - Help/description text now mentions website or public GitHub repository planning.
  - Text summaries include source kind and GitHub repo/file counts when applicable.
- `tests/test_cli.py`
  - Added tests proving GitHub `crawl` and `plan` route to the repo crawler, not the Scrapling website crawler.
  - Added plan-artifact assertions for repo-specific namespace/site ID/state path and GitHub chunk source metadata.
- `README.md`
  - Added a public GitHub repository indexing section with `https://github.com/Doctacon/open-streaming-lab`, repo-specific namespace example, path filters, and non-goals.
- `docs/generic-site-rag-plan-apply.md`
  - Updated workflow docs to cover public GitHub repository sources and repo-relative include/exclude filters.

Validation commands:

```bash
uv run python -m unittest discover tests
uv run turbo-search --help | head -40
```

Outputs:

```text
.......................................................................................................
----------------------------------------------------------------------
Ran 103 tests in 1.580s

OK
```

```text
usage: turbo-search [-h] [--version] {crawl,plan,apply,retrieve,evals} ...

Local site/repository RAG utilities. Planning is local-only by default unless
explicitly documented otherwise.

positional arguments:
  {crawl,plan,apply,retrieve,evals}
    crawl               crawl a website or public GitHub repo and chunk
                        locally; always dry-run
    plan                crawl a website or public GitHub repo and write local
                        review/apply plan artifacts; no live writes
    apply               verify and optionally apply a saved generic site RAG
                        plan
    retrieve            retrieve relevant chunks; dry-run plan by default
                        unless --live is passed
    evals               list or run retrieval smoke evals for a namespace
```

After a minor cleanup, the full test suite was run again:

```bash
uv run python -m unittest discover tests
```

Output:

```text
.......................................................................................................
----------------------------------------------------------------------
Ran 103 tests in 1.586s

OK
```

After increasing source-specific GitHub defaults to `5000` repo files and `100000` chunks, validation was rerun:

```bash
uv run python -m unittest tests.test_cli tests.test_crawler tests.test_github_repo tests.test_plan_artifacts tests.test_apply_cli
uv run python -m unittest discover tests
uv run turbo-search plan --help | rg -n "max-pages|max-chunks|GitHub" -C 1
```

Outputs:

```text
...........................................................................
----------------------------------------------------------------------
Ran 75 tests in 1.750s

OK
.......................................................................................................
----------------------------------------------------------------------
Ran 103 tests in 1.711s

OK
```

```text
35:  --max-pages MAX_PAGES
36-                        Maximum pages/files to scrape. Defaults: websites=250,
37:                        GitHub repos=5000.
38:  --max-chunks MAX_CHUNKS
39-                        Maximum chunks to generate. Defaults: websites=10000,
40:                        GitHub repos=100000.
```

Live public GitHub URL smoke test:

```bash
SMOKE_ROOT=$(mktemp -d /tmp/turbo-search-github-smoke.XXXXXX)
uv run turbo-search plan https://github.com/Doctacon/open-streaming-lab \
  --out-dir "$SMOKE_ROOT/plan" \
  --state-root "$SMOKE_ROOT/state" \
  --max-pages 30 \
  --max-chunks 100 \
  --json
```

Key output fields:

```json
{
  "source_kind": "github_repo",
  "base_url": "https://github.com/Doctacon/open-streaming-lab",
  "namespace": "github-doctacon-open-streaming-lab-v1",
  "site_id": "github-doctacon-open-streaming-lab",
  "acquisition_strategy": "git-shallow-clone",
  "repo_full_name": "Doctacon/open-streaming-lab",
  "repo_ref": "main",
  "commit_sha": "fa5894b0711bdad49e6d6b6637bf844e7a524173",
  "files_discovered": 49,
  "files_selected": 30,
  "chunks_generated": 100,
  "rows_to_upsert": 100,
  "limit_reached": true,
  "credentials_required": false,
  "turbopuffer_api_calls": false
}
```

## Procedure

1. Wired CLI source detection for `crawl` and `plan`.
2. Added a GitHub repo crawl summary wrapper over acquisition/corpus/chunking.
3. Added mocked CLI tests that avoid live GitHub/turbopuffer calls.
4. Updated README and workflow docs.
5. Ran full unit tests and CLI help inspection.
6. Ran a live public GitHub URL smoke test against `https://github.com/Doctacon/open-streaming-lab` with low page/chunk caps and temporary output/state directories.

## What this supports or challenges

Supports the ticket acceptance criteria that:

- CLI help mentions public GitHub repositories.
- JSON summary fields include source kind/repo metadata/file counts through tests.
- End-to-end dry-run behavior is covered with mocks/local fixtures and a live public GitHub URL smoke test.
- Ordinary website tests still pass.
- Documentation includes the GitHub repo example and repo-relative filters.

## Limits

This evidence does not include live turbopuffer apply, which remains guarded by explicit approval. The live GitHub smoke used temporary directories and low caps (`--max-pages 30`, `--max-chunks 100`), so it validates the one-command path without exhaustively indexing the full repository.
