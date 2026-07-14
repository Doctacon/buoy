Status: recorded
Created: 2026-07-14
Updated: 2026-07-14
Relates-To: .10x/tickets/done/2026-07-14-buoy-local-compatibility.md, .10x/specs/buoy-local-compatibility.md

# Buoy Local Compatibility Validation

## What was observed

- New low-level/default plan state is `.buoy`.
- Implicit plan/apply resolution uses `.buoy` when it exists or neither root exists; uses an existing lone `.turbo-search` root in place with a stderr warning; and refuses dual roots before crawl, plan discovery, model construction, writer construction, local mutation, or remote work.
- Explicit `--state-root` bypasses implicit resolution even when both branded roots exist.
- Resolution never copies, moves, merges, deletes, or creates a root. A marker-based filesystem comparison remained byte/path identical after legacy fallback.
- An existing schema-supported plan recording `.turbo-search` preflighted successfully through implicit legacy fallback. Its artifact hash remained unchanged, `.buoy` was not created, JSON stdout remained parseable, and the warning appeared only on stderr.
- `BUOY_EMBEDDING_MODEL` is primary. `TURBO_SEARCH_EMBEDDING_MODEL` works only as the 0.2 fallback with one stderr warning; different simultaneous values fail with a user-friendly conflict. Matching simultaneous values use the new variable without warning. `TURBOPUFFER_REGION` and `TURBOPUFFER_NAMESPACE` remain unchanged.
- Both `.buoy` and `.turbo-search` are gitignored, excluded from GitHub repository ingestion, and treated as retrieval artifact paths.
- A committed pre-rebrand golden regression for the standard plan-artifact fixture preserves artifact hash `aa7faed6db9f353d87a959cc575a408e3278963610eacec1ef7f2aca0f71f7c8`, remote row ID `ts_2fd4695f91b79df01d0f8b1d47587127`, and namespace `site-example-com-v1`. `jf_*` values are intermediate chunk IDs, not the remote generic-site row identity, and are not used as evidence for this compatibility contract.

## Procedure and results

```text
PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest \
  tests.test_config tests.test_applied_state tests.test_cli tests.test_apply_cli \
  tests.test_github_repo tests.test_plan_artifacts tests.test_retriever -q
Ran 142 tests; OK

PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover -s tests -p 'test_*.py' -q
Ran 226 tests; OK

uv lock --check
git diff --check
OK
```

Focused tests use temporary directories, cleared/patched environments, mocked crawls, and model/writer constructors that fail if called. No credential, model, network, or Turbopuffer operation ran.

A standalone temporary marker check reported:

```text
warning=True
filesystem_unchanged=True
new_root_created=False
```

A standalone environment check reported the legacy selected model and one warning, then the exact conflicting-variable error. The committed standard-fixture golden test produced and asserted the exact artifact hash, `ts_*` remote row ID, and namespace recorded above.

## Changed files

- `.gitignore`
- `src/buoy_search/applied_state.py`
- `src/buoy_search/cli.py`
- `src/buoy_search/config.py`
- `src/buoy_search/github_repo.py`
- `src/buoy_search/plan_artifacts.py`
- `src/buoy_search/retriever.py`
- `tests/test_config.py`
- `tests/test_applied_state.py`
- `tests/test_apply_cli.py`
- `tests/test_cli.py`
- `tests/test_github_repo.py`
- `tests/test_plan_artifacts.py`

## Preservation of pre-existing work

Eleven staged documentation/record paths predated this ticket and remain the same staged path set. This worker did not stage, unstage, reset, or overwrite that work. The repository therefore is not globally free of staged files, but this ticket added no staged files.

## What this supports or challenges

Supports every state-root and environment scenario in the governing specification, old-plan/hash compatibility, JSON/stderr separation, no migration side effects, unchanged remote `ts_*` row and namespace identity, and no-live execution.

## Limits

- The 0.2 fallback warns but intentionally does not provide an automatic state migration.
- Documentation/logo migration is owned by the dependent branding child and remains outside this ticket.
- Independent re-review is required before ticket closure.
