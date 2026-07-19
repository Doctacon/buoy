Status: recorded
Created: 2026-07-19
Updated: 2026-07-19
Relates-To: .10x/tickets/done/2026-07-18-remove-unreachable-local-catalog-persistence.md

# Unreachable Local-Catalog Persistence Removal

## What was observed

The nine ticket-scoped local JSON catalog persistence definitions were production-unreachable before deletion and are absent afterward:

- `document_to_dict`
- `empty_catalog`
- `resolve_catalog_path`
- `load_catalog`
- `catalog_lock`
- `_atomic_write` in `src/buoy_search/catalog.py` (the independent pending-recovery writer in `catalog_pending.py` is preserved)
- `save_catalog`
- `commit_system_card`
- `mutate_catalog`

The implementation diff changes only `src/buoy_search/catalog.py`. AST comparison against task base `25aafee398f78761d3638becd7bd452d00e14927` proves all 38 remaining top-level function/class definitions in that module are structurally identical. `routing.py`, `remote_catalog.py`, `catalog_pending.py`, `catalog_cli.py`, `apply.py`, and their protective tests are unchanged.

Ten tests that existed only for dead local persistence were deleted from `tests/test_catalog.py`:

1. `test_save_load_is_canonical_sorted_and_revision_validated`
2. `test_save_rejects_duplicate_namespaces_before_writing`
3. `test_missing_catalog_is_empty_without_creating_files`
4. `test_json_nan_and_malformed_file_report_path_and_recovery`
5. `test_atomic_save_fsyncs_file_and_best_effort_directory`
6. `test_failed_atomic_replace_preserves_previous_bytes`
7. `test_lock_contention_fails_fast_and_preserves_catalog`
8. `test_commit_api_validates_merges_and_is_idempotent`
9. `test_catalog_path_precedence_and_empty_values`
10. `test_default_and_legacy_path_resolution_and_ambiguity`

Two mixed tests were narrowed without losing production-reachable assertions: prospective/persisted lineage validation no longer calls removed `save_catalog`, and generated-card disable preservation now exercises production-reachable `merge_system_card` directly. Parser tests now construct schema-v1 payloads directly, preserving unknown-field, hash, ordering, duplicate, integer-type, and integer-vector validation coverage without recreating persistence helpers.

## Procedure and results

### Base incorporation

```text
git fetch origin develop
git merge --ff-only origin/develop
HEAD=25aafee398f78761d3638becd7bd452d00e14927
origin/develop=25aafee398f78761d3638becd7bd452d00e14927
Already up to date.
```

### Before-deletion production reachability

A Python AST scan parsed every `src/**/*.py`, resolved direct imports from `buoy_search.catalog`, resolved qualified module references, and attributed same-module name loads to their owning top-level definition. It found no external production reference for any candidate. The only candidate-to-candidate edges were:

```text
save_catalog -> document_to_dict, _atomic_write
load_catalog -> empty_catalog
commit_system_card -> catalog_lock, load_catalog, save_catalog
mutate_catalog -> catalog_lock, load_catalog, save_catalog
```

`resolve_catalog_path`, `commit_system_card`, and `mutate_catalog` had no caller. The scan intentionally distinguished `catalog.py::_atomic_write` from the separate production-reachable `catalog_pending.py::_atomic_write`.

### After-deletion AST and source checks

A second Python AST scan compared `git show HEAD:src/buoy_search/catalog.py` with the worktree file and asserted the removed definition set equals the exact ticket set, no new definition exists, every retained definition has identical attribute-free AST, and no production module imports a removed symbol:

```text
REMOVED_DEFINITIONS=['_atomic_write', 'catalog_lock', 'commit_system_card', 'document_to_dict', 'empty_catalog', 'load_catalog', 'mutate_catalog', 'resolve_catalog_path', 'save_catalog']
UNEXPECTED_NEW_DEFINITIONS=[]
PRESERVED_DEFINITIONS_WITH_AST_CHANGES=none
PRESERVED_DEFINITIONS_AST_IDENTICAL=38
EXTERNAL_PRODUCTION_IMPORTS_OF_REMOVED_SYMBOLS=none
```

Bounded source searches found no scoped symbol in `src/buoy_search/catalog.py` and no test reference to a removed catalog symbol. The only remaining `BUOY_CATALOG_PATH` occurrence is the pre-existing `CATALOG_ENV` compatibility constant; no code reads it, and the exact nine-symbol scope did not authorize removing it. Applied-state locking and pending-recovery atomic persistence remain present and unchanged.

### Focused behavior

```text
PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 --locked python -m unittest -q \
  tests.test_catalog tests.test_catalog_cli tests.test_catalog_pending \
  tests.test_remote_catalog tests.test_automatic_routing tests.test_apply_cli \
  tests.test_cutover_isolation
Ran 151 tests in 17.539s — OK

PYTHONDONTWRITEBYTECODE=1 uv run --python 3.13 --locked python -m unittest -q \
  tests.test_catalog tests.test_catalog_cli tests.test_catalog_pending \
  tests.test_remote_catalog tests.test_automatic_routing tests.test_apply_cli \
  tests.test_cutover_isolation
Ran 151 tests in 15.585s — OK
```

These injected-client suites cover schema/card/parser/generated semantics, `catalog migrate-local`, remote list/mutation/reconcile/abandon, approved apply registration and pending recovery, automatic routing, and cutover isolation. They prohibit accidental construction of real remote clients.

### Full suites

```text
PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 --locked python -m unittest discover -s tests -p 'test_*.py' -q
Ran 414 tests in 29.049s — OK

PYTHONDONTWRITEBYTECODE=1 uv run --python 3.13 --locked python -m unittest discover -s tests -p 'test_*.py' -q
Ran 414 tests in 27.602s — OK
```

Each run emitted two expected test-fixture cleanup warnings for intentionally simulated plan-artifact deletion failures; both suites completed successfully. The 414 count is exactly the prior 424-test baseline minus the ten obsolete persistence tests.

### Distribution build

```text
out=$(mktemp -d /tmp/buoy-catalog-build.XXXXXX)
uv build --out-dir "$out"
Successfully built buoy_search-0.3.0.tar.gz
Successfully built buoy_search-0.3.0-py3-none-any.whl
wheel sha256 6b6a754d9cf30c5873889b24ec31acc68325fbab0e6e4144998a530ff54053af
sdist sha256 c96f70b0946ddd79858d0015ca24620b34ed4d0061e56e579db38b1d6ba36b5c
```

The build output was directed to `/tmp/buoy-catalog-build.pxtM96`; no distribution artifact was written into the repository.

An initial `python -m pytest` attempt was not a validation failure: the locked project has no `pytest` dependency, so it exited with `No module named pytest`. Validation then used the repository/hosted workflow's canonical `unittest` command.

## What this supports

- Only the source-proven dead local persistence cluster and its obsolete tests were removed.
- `catalog migrate-local` retains direct JSON decoding plus `parse_catalog` validation in `catalog_cli.py`; it does not depend on any removed persistence helper.
- Card/schema/parser/generated-semantics/routing/remote/pending behavior is preserved by identical retained AST plus focused and full tests.
- The branch performed no Buoy live operation, no Turbopuffer operation, no live crawl, no user catalog/data deletion, and no file deletion outside the obsolete source test bodies. All remote behavior tests used injected clients; only the explicitly required Git fetch/push/PR workflow contacts Git hosting.

## Hosted checks

Pull request [#43](https://github.com/Doctacon/buoy-search/pull/43) ran GitHub Actions workflow `CI`, run `29700312134`, against implementation commit `c13bbcc`:

```text
Python 3.11 — pass (44s)
Python 3.13 — pass (1m3s)
Build distributions — pass (10s)
```

The subsequent record-only commit adds this hosted observation and ticket progress; it does not change source or tests. Current-head hosted status is reported separately at handoff so the record update does not recursively claim its own checks.

## Limits

This is implementation evidence, not independent review and not ticket closure.
