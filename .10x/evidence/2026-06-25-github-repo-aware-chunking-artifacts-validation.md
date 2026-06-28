Status: recorded
Created: 2026-06-25
Updated: 2026-06-25
Relates-To: .loom/tickets/2026-06-25-github-repo-aware-chunking-and-artifacts.md

# GitHub Repo-Aware Chunking and Artifacts Validation

## What was observed

Validated repository-aware corpus chunking, source metadata propagation into plan artifacts/rows, incremental diff behavior, and apply preflight compatibility.

Changed files:

- `src/turbo_search/github_repo.py`
  - Repository code/config corpus rendering already writes line-range sections and fenced code blocks to avoid arbitrary sentence/word splitting for ordinary-sized code blocks.
- `src/turbo_search/plan_artifacts.py`
  - Added `source_metadata` to chunk manifest records.
  - Propagated page source metadata into chunk records.
  - Added row/schema fields for `source_kind`, `repo_full_name`, `repo_owner`, `repo_name`, `repo_ref`, `commit_sha`, `repo_path`, and `language`.
- `src/turbo_search/apply.py`
  - Updated manifest chunk parsing to preserve `source_metadata` during apply preflight verification.
- `tests/test_github_repo.py`
  - Added tests for GitHub source metadata in chunks and rows.
  - Added tests for no-change, changed, and stale diff behavior using local applied state.
  - Added apply preflight verification of a generated GitHub plan.

Validation commands:

```bash
uv run python -m unittest tests.test_github_repo tests.test_plan_artifacts tests.test_apply_cli tests.test_cli tests.test_crawler
uv run python -m unittest discover tests
```

Outputs:

```text
.........................................................................
----------------------------------------------------------------------
Ran 73 tests in 1.564s

OK
```

```text
.....................................................................................................
----------------------------------------------------------------------
Ran 101 tests in 1.590s

OK
```

## Procedure

1. Read repo-aware chunking/artifacts ticket.
2. Propagated GitHub source metadata through plan artifacts and live row construction.
3. Added artifact/diff/preflight tests using generated local repository corpora.
4. Ran focused and full `unittest` suites.

## What this supports or challenges

Supports the ticket acceptance criteria that:

- Markdown docs still flow through existing heading chunking.
- Code files are represented through line-range fenced sections with path/language context.
- No-change plans report unchanged chunks against local state.
- Changed/removed repository content reports rows to upsert and stale rows.
- Apply preflight accepts and verifies a generated GitHub plan.
- Existing website and apply tests continue to pass.

## Limits

This evidence does not prove final CLI documentation/help or the one-command GitHub `plan` user flow. That is covered by the remaining CLI/docs validation ticket.
