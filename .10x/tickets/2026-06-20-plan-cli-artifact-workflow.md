Status: done
Created: 2026-06-20
Updated: 2026-06-20
Parent: .loom/tickets/2026-06-20-generic-site-rag-incremental-plan-apply.md
Depends-On: .loom/tickets/2026-06-20-plan-artifact-manifest-model.md, .loom/tickets/2026-06-20-incremental-plan-diff-engine.md, .loom/specs/generic-site-rag-incremental-plan-apply.md, .loom/specs/generic-website-rag-dry-run-crawl.md

# Plan CLI Artifact Workflow

## Scope

Add the polished local-only plan command for generic website RAG indexing.

In scope:

- Add `turbo-search plan` or a clearly documented plan mode using the existing `crawl` implementation.
- Reuse Scrapling crawl/extract/chunk behavior from `turbo-search crawl`.
- Write `plan.json`, `manifest.json`, `chunks.jsonl`, `summary.json`, and `pages/*.md`.
- Load local state if present and include incremental diff output.
- Print JSON and text summaries.
- Keep all plan behavior credential-free and turbopuffer-free.
- Preserve existing `turbo-search crawl` behavior or provide a backwards-compatible alias.
- Tests for CLI validation, no credentials, no live calls, and artifact creation.

Out of scope:

- Live apply.
- Embeddings.
- Turbopuffer writes/deletes.
- Remote state.
- Browser-rendered crawling.

## Command sketch

```bash
turbo-search plan \
  --base-url "https://scrapling.readthedocs.io/en/latest/" \
  --out-dir artifacts/site-crawls/scrapling-readthedocs-io-plan \
  --max-pages 1000 \
  --max-chunks 10000 \
  --css-selector ".md-content__inner" \
  --json
```

Optional namespace override:

```bash
turbo-search plan --base-url <url> --namespace site-example-com-v1 --json
```

## Acceptance criteria

- `turbo-search plan --base-url <url> --json` exists.
- Invalid base URL exits with code 2 and a clear message.
- Plan writes all required artifacts.
- Plan output includes safety fields:
  - `dry_run: true`
  - `credentials_required: false`
  - `turbopuffer_api_calls: false`
  - `api_calls_occurred: false`
- Plan output includes page/chunk/diff counts.
- Plan uses local state if present and first-apply state if absent.
- Plan does not load embedding model or read `TURBOPUFFER_API_KEY`.
- Existing crawl tests continue to pass.
- Add mocked/no-network CLI tests for artifact mode.

## Progress and notes

- 2026-06-20: Ticket opened for Phase 2 CLI surface.
- 2026-06-20: Implemented `turbo-search plan` in `src/turbo_search/cli.py` with the same crawl options as `crawl`, plus `--namespace` and `--state-root`.
- 2026-06-20: Plan reuses `crawl_site()`, re-processes generated pages into an indexing plan, builds `plan.json`/`manifest.json`/`chunks.jsonl`, loads local applied state, computes incremental diff output, and overwrites `summary.json` with plan-specific local-only summary fields.
- 2026-06-20: Updated `src/turbo_search/plan_artifacts.py` so plan artifact state paths honor a supplied state root.
- 2026-06-20: Added mocked/no-network CLI tests for first-apply artifact creation, existing-state unchanged diff, and invalid URL validation while preserving existing crawl behavior tests.
- 2026-06-20: Updated README with plan command usage and artifact list.
- 2026-06-20: Validation passed. Evidence: `.loom/evidence/2026-06-20-plan-cli-artifact-workflow-validation.md`.

## Blockers

None.
