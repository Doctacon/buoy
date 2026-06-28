Status: recorded
Created: 2026-06-20
Updated: 2026-06-20
Relates-To: .loom/tickets/2026-06-20-plan-cli-artifact-workflow.md, .loom/specs/generic-site-rag-incremental-plan-apply.md

# Plan CLI Artifact Workflow Validation

## What was observed

Implemented the local-only `turbo-search plan` CLI workflow for generic site RAG planning.

Changed implementation/test/doc files:

- `src/turbo_search/cli.py`
- `src/turbo_search/plan_artifacts.py`
- `tests/test_cli.py`
- `README.md`
- `.loom/tickets/2026-06-20-plan-cli-artifact-workflow.md`

Key behavior added:

- `turbo-search plan --base-url <url>` command exists.
- It reuses the existing Scrapling crawl/extract/chunk path via `crawl_site()`.
- It writes generated Markdown pages plus `summary.json`, `plan.json`, `manifest.json`, and `chunks.jsonl`.
- It loads local applied state from `.turbo-search` by default, or `--state-root` when supplied.
- It computes incremental diff output using `diff_manifest_against_state()`.
- It supports `--namespace` for stable namespace override.
- It prints JSON or text summaries.
- It reports local-only safety fields: `dry_run=true`, `credentials_required=false`, `turbopuffer_api_calls=false`, `api_calls_occurred=false`.

No credentials were accessed. No embedding model was loaded. No turbopuffer API calls or live writes/evals were run.

## Procedure

Targeted CLI validation with mocked/no-network crawl behavior:

```bash
PYTHONPATH=src python3 -m unittest tests.test_cli -v
```

Result: 11 tests ran OK.

Full local test suite:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Result: 58 tests ran OK.

Full uv test suite:

```bash
uv run python -m unittest discover -s tests -v
```

Result: 58 tests ran OK.

Compile check:

```bash
PYTHONPATH=src python3 -m compileall -q src tests
```

Result: passed with no output.

## What this supports

This supports the ticket acceptance criteria:

- plan CLI exists and validates base URLs;
- plan writes required review/apply artifacts;
- plan output includes local-only safety fields;
- plan output includes page/chunk counts and diff counts;
- plan uses first-apply state when local state is absent;
- plan loads existing local state and reports unchanged diff when rows match;
- existing crawl command behavior remains covered by tests;
- mocked CLI tests do not require network, credentials, embeddings, or turbopuffer access.

## Limits

This evidence does not prove live Scrapling network behavior for `plan`; it reuses `crawl_site()`, whose live dry-run behavior has separate evidence. This evidence also does not prove `apply`, embeddings, live writes, or stale deletes, which are out of scope for this ticket.
