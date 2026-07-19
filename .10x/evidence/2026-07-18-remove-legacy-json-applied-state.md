Status: recorded
Created: 2026-07-18
Updated: 2026-07-18
Relates-To: .10x/tickets/done/2026-07-18-remove-legacy-json-applied-state.md, .10x/decisions/duckdb-only-applied-state-hard-cutover.md, .10x/specs/compact-duckdb-applied-state.md

# DuckDB-Only Applied-State Hard Cutover Validation

## What was observed

- Applied-state production code no longer names, discovers, parses, migrates, archives, deletes, or warns about obsolete JSON applied state. `AppliedStatePaths` contains only the namespace directory, `state.duckdb`, and the apply lock.
- Focused regressions exercise obsolete direct and prior-archive JSON paths with invalid/binary contents. Missing DuckDB and valid initialized-empty DuckDB remain first apply; valid populated DuckDB remains authoritative; invalid schema and identity still fail closed.
- Plan, existing apply preflight, successful confirmed apply, and failed confirmed apply fixtures preserve obsolete-file bytes, device/inode identity, size, and modification time. Apply preflight output is byte-identical with the files absent or present; confirmed apply produces the same state classification, content-write IDs, committed current rows, summary counts, catalog result, and plan cleanup behavior.
- The `.turbo-search` root fallback tests, namespace lock tests, compact summary tests, content-failure preservation tests, successful state commit tests, and catalog pending/recovery tests remain in the passing full suite.
- Active indexing documentation and the project skill now describe obsolete JSON applied state as ignored and unchanged rather than migrated or deleted.

## Procedure and results

Run from the repository root on branch `work/remove-legacy-json-applied-state` after incorporating `origin/develop` at `6f2812313396943bc0aa0a6b095a1affd466a539`:

```bash
uv run --python 3.11 python -m unittest tests.test_applied_state tests.test_cli tests.test_apply_cli
# Ran 99 tests in 18.564s — OK

uv run --python 3.13 python -m unittest tests.test_applied_state tests.test_cli tests.test_apply_cli
# Ran 99 tests in 17.988s — OK

uv run --python 3.11 python -m unittest discover -s tests
# Ran 407 tests in 25.300s — OK

uv run --python 3.13 python -m unittest discover -s tests
# Ran 407 tests in 24.973s — OK

rm -rf dist && uv build --out-dir dist
# Successfully built dist/buoy_search-0.3.0.tar.gz
# Successfully built dist/buoy_search-0.3.0-py3-none-any.whl

uv run --python 3.13 python scripts/release_checks.py assets --dist dist
# exit 0

if rg -n 'last-applied\.json|legacy-json|applied_state_(from|to)_json|_migrate_legacy_state|_delete_legacy_archive' src; then exit 1; else echo 'production_source_obsolete_json_references=0'; fi
# production_source_obsolete_json_references=0

if rg -n 'legacy `last-applied\.json` is (removed|deleted)|legacy JSON.*(removed|deleted)' README.md docs .pi/skills; then exit 1; else echo 'active_doc_json_migration_promises=0'; fi
# active_doc_json_migration_promises=0

git diff --check
# exit 0

gh pr checks 36 --watch --interval 10
# Actions run 29691090597
# Python 3.11 — pass (58s), job 88203840298
# Python 3.13 — pass (41s), job 88203840297
# Build distributions — pass (10s), job 88203930341
```

## What this supports or challenges

This supports the ticket's hard-cutover, inert-file, first-apply, DuckDB-authority, fail-closed, lock, content/state sequencing, pending-recovery, documentation, focused/full Python, distribution-build, and hosted-check acceptance claims. Pull request `#36` passed both versioned test jobs and the dependent distribution build in Actions run `29691090597`. Independent review remains a separate required gate and this evidence does not close the ticket.

## Parent-observed invalid-DuckDB fail-closed probe

After independent review, the parent ran a temporary-directory Python 3.13 probe through the public `load_applied_state` path. One existing `state.duckdb` contained invalid bytes; another contained invalid bytes and mode `000`. Both raised `AppliedStateError` rather than returning first-apply state:

```text
corrupt=fail_closed:AppliedStateError:could not load DuckDB applied state: ... not a valid DuckDB database file
unreadable=fail_closed:AppliedStateError:could not load DuckDB applied state: ... Permission denied
```

The probe restored permissions in `finally`, used no project state path, and made no credential or remote call. Together with committed schema-version and identity-mismatch regressions, this covers the specification's corrupt, unreadable, schema-incompatible, and identity-invalid fail-closed classes.

## Limits

All remote content and catalog behavior used injected fakes; no live Turbopuffer operation, credential use, release, interactive apply confirmation, or merge occurred.
