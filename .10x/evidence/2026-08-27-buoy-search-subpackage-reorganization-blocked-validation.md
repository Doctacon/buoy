Status: recorded
Created: 2026-08-27
Updated: 2026-08-27
Relates-To: .10x/tickets/done/2026-08-27-reorganize-buoy-search-subpackages.md, .10x/specs/buoy-search-subpackage-layout.md, .10x/decisions/buoy-activates-certified-bounded-prototype-routing.md, .10x/decisions/superseded/buoy-recertifies-final-reviewed-cli-receipt.md

# Buoy Search subpackage reorganization blocked validation

## What was observed

The structural migration was implemented according to the specified module map, including import-path updates in `src/`, `tests/`, executable scripts, the console-script declaration, and package-data repository-path judgments. No compatibility forwarding modules were added.

The migration cannot currently satisfy the full-suite acceptance criterion without authority beyond the structural-only specification. The packaged active routing artifact at `src/buoy_search/data/automatic_routing_confidence_calibration.json` binds exact SHA-256 identities for these formerly flat production modules:

- `routing_quality.py`
- `routing.py`
- `cli.py`
- `evidence.py`

Those files now live at:

- `src/buoy_search/evals/routing_quality.py`
- `src/buoy_search/retrieval/routing.py`
- `src/buoy_search/cli/main.py`
- `src/buoy_search/retrieval/evidence.py`

Their imports and package-data/source lookup paths necessarily changed as part of relocation, so their byte hashes changed. The active loader correctly rejects the stale artifact before automatic routing. The governing decision `.10x/decisions/buoy-activates-certified-bounded-prototype-routing.md` requires exact installed-byte matching and rejection on mismatch. `.10x/decisions/superseded/buoy-recertifies-final-reviewed-cli-receipt.md` grants only a prior, narrowly scoped CLI telemetry recertification and does not authorize this migration to rebind the four receipts.

Supervisor direction on 2026-08-27 confirmed that rebinding/recertification is not authorized by the current structural-only spec. The artifact hashes were not changed, and compatibility copies were not created.

## Procedure and command results

### Tree inventory

Command:

```sh
find src/buoy_search -mindepth 1 -maxdepth 1 ! -name '__pycache__' -print | sort
```

Observed root entries:

```text
src/buoy_search/__init__.py
src/buoy_search/__main__.py
src/buoy_search/_version.py
src/buoy_search/catalog
src/buoy_search/cli
src/buoy_search/config.py
src/buoy_search/data
src/buoy_search/evals
src/buoy_search/indexing
src/buoy_search/local_paths.py
src/buoy_search/model_progress.py
src/buoy_search/planning
src/buoy_search/relations
src/buoy_search/retrieval
src/buoy_search/source_url.py
src/buoy_search/telemetry
```

This matches the required concern directories and allowed root modules.

### Old-import search

Commands:

```sh
rg -n --glob '*.py' '(^|[^A-Za-z0-9_])(from|import) buoy_search\.(entrypoint|catalog_cli|telemetry_cli|crawler|chunker|github_repo|repo_syntax_chunking|treatment_token_budget|retriever|cross_encoder|evidence|routing|_provider_invocation_receipt|applied_state|apply|plan_artifacts|plan_cleanup|plan_diff|plan_validation|planning_service|telemetry_envelope|telemetry_queue|telemetry_store|telemetry_writer|multi_corpus_evals|evidence_evals|routing_quality|database_relation|bigquery_relation|duckdb_relation|snowflake_relation|remote_catalog)([^A-Za-z0-9_]|$)' src tests scripts
rg -n --glob '*.py' 'from buoy_search import (cli|telemetry|telemetry_store|telemetry_writer|telemetry_queue|routing_quality|plan_cleanup|multi_corpus_evals|autoresearch|_provider_invocation_receipt)' src tests scripts
```

Result: both searches returned no matches.

### Compilation and import smoke test

Commands:

```sh
uv run python -m compileall -q src tests
uv run python - <<'PY'
# Imported every new module path named by the specification.
PY
```

Result: compilation passed. All 37 moved implementation module paths imported successfully across `cli`, `indexing`, `retrieval`, `planning`, `telemetry`, `evals`, `relations`, and `catalog`.

### Full test suite

Initial command:

```sh
uv run --with pytest pytest -q
```

Result: collection failed because this environment required the repository root on `PYTHONPATH` for the existing `tests` and `scripts` namespace imports. This was a test invocation/environment issue, not a source failure.

Repository-aware command:

```sh
PYTHONPATH=.:src uv run --with pytest pytest -q
```

Observed result at that point: `83 failed, 1127 passed, 57 warnings, 1120 subtests passed`. The failures exposed two relocation follow-ups and the governed artifact blocker. Test/source lookup helpers and repository-eval dataset paths were subsequently updated for the specified new locations.

Focused post-fix command:

```sh
PYTHONPATH=.:src uv run --with pytest pytest -q \
  tests/test_automatic_routing.py \
  tests/test_routing_quality.py \
  tests/test_routing_quality_runner.py \
  tests/test_routing_activation_cli.py \
  tests/test_evals.py
```

Result: `6 failed, 129 passed, 148 subtests passed`. All six failures were duplicate collection of three automatic-routing CLI tests, each stopping early with:

```text
Automatic routing failed: routing confidence artifact is invalid.
```

This is the expected stale exact-byte receipt rejection. A final full-suite rerun was not performed after supervisor direction to stop rather than recertify.

### CLI check

Command:

```sh
uv run python -m buoy_search --help
```

Result: passed and printed the expected `buoy` command help with `catalog`, `crawl`, `plan`, `apply`, `retrieve`, and `evals` subcommands.

### Wheel build and inventory

Commands:

```sh
rm -rf dist
uv build --wheel
# Inspect the resulting wheel with zipfile for all subpackage __init__.py files and package data.
```

Result: wheel built successfully as `dist/buoy_search-0.5.2.dev122+g097aff416.d20260827-py3-none-any.whl`. Inventory found all eight required concern subpackage initializers, 45 nested Python files, and 29 files under `buoy_search/data/`; no required entry was missing.

### Repository state

Commands:

```sh
git diff --cached --name-only
git status --short
git diff --stat
```

Result: `git diff --cached --name-only` returned no output; no files are staged. The worktree contains the requested structural moves, import/test/script/data-path updates, the governing spec/ticket, and this evidence record.

## What this supports or challenges

This evidence supports that the directory layout, new imports, module importability, CLI entrypoint, wheel recursion, package data, and no-forwarder requirements were implemented. It challenges acceptance criterion 4: the existing suite cannot pass while both the current exact-byte routing artifact and the moved production bytes are retained.

## Limits

- The full suite is not passing and was not rerun after the final relocation-path fixes because receipt recertification was explicitly denied and execution was directed to stop.
- Import smoke checks prove importability, not all runtime paths.
- Wheel inventory proves inclusion, not installed-wheel runtime behavior.
- No claim is made that the active routing artifact may safely be rebound. That requires separate authority and its mandated validation/review process.
