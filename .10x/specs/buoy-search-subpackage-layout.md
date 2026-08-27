Status: active
Created: 2026-08-27
Updated: 2026-08-27

# Buoy Search Subpackage Layout

## Purpose and scope

Reorganize the flat `src/buoy_search/` Python package into concern-oriented subpackages so contributors can locate related implementation by domain. This is an intentional breaking cleanup: old flat module import paths are not retained through forwarding modules.

This specification governs module placement and import-path migration only. It does not authorize behavioral changes, API redesign within modules, file splitting, symbol renaming, or opportunistic cleanup.

## Required layout

The package MUST use these concern directories:

- `cli/`: command entrypoints and command-specific presentation/parsing
- `indexing/`: source acquisition, crawling, chunking, and indexing preparation
- `retrieval/`: retrieval, reranking, routing, and retrieval evidence
- `planning/`: plan construction, validation, diffing, lifecycle, apply, and applied state
- `telemetry/`: telemetry production, envelopes, queues, storage, and writing
- `evals/`: evaluation contracts, runners, quality measurement, and autoresearch
- `relations/`: database-relation abstractions and backend adapters
- `catalog/`: local and remote routing-catalog implementation
- `data/`: packaged datasets and model assets; unchanged

Cross-cutting configuration, paths, URL validation, package versioning, and package launch files MAY remain at the package root.

## Module mapping

### `cli/`

- `cli.py` -> `cli/main.py`
- `entrypoint.py` -> `cli/entrypoint.py`
- `catalog_cli.py` -> `cli/catalog.py`
- `telemetry_cli.py` -> `cli/telemetry.py`

### `indexing/`

- `crawler.py`
- `chunker.py`
- `github_repo.py`
- `repo_syntax_chunking.py`
- `treatment_token_budget.py`

### `retrieval/`

- `retriever.py`
- `cross_encoder.py`
- `evidence.py`
- `routing.py`
- `_provider_invocation_receipt.py`

### `planning/`

- `applied_state.py`
- `apply.py`
- `plan_artifacts.py`
- `plan_cleanup.py`
- `plan_diff.py`
- `plan_validation.py`
- `planning_service.py`

### `telemetry/`

- `telemetry.py` -> `telemetry/producer.py`
- `telemetry_envelope.py` -> `telemetry/envelope.py`
- `telemetry_queue.py` -> `telemetry/queue.py`
- `telemetry_store.py` -> `telemetry/store.py`
- `telemetry_writer.py` -> `telemetry/writer.py`

### `evals/`

- `evals.py` -> `evals/core.py`
- `autoresearch.py`
- `evidence_evals.py` -> `evals/evidence.py`
- `multi_corpus_evals.py` -> `evals/multi_corpus.py`
- `routing_quality.py`

### `relations/`

- `database_relation.py` -> `relations/base.py`
- `bigquery_relation.py` -> `relations/bigquery.py`
- `duckdb_relation.py` -> `relations/duckdb.py`
- `snowflake_relation.py` -> `relations/snowflake.py`

### `catalog/`

- `catalog.py` -> `catalog/local.py`
- `remote_catalog.py` -> `catalog/remote.py`

### Package root

These modules remain at the root in this pass:

- `__init__.py`
- `__main__.py`
- `_version.py`
- `config.py`
- `local_paths.py`
- `model_progress.py`
- `source_url.py`

## Behavior

1. All source and test imports MUST use the new module paths.
2. Every new subpackage MUST contain `__init__.py`.
3. Old flat implementation modules MUST be removed rather than retained as compatibility shims.
4. `python -m buoy_search` and installed console-script behavior MUST remain unchanged from a user's perspective.
5. Package data under `buoy_search/data/` MUST remain discoverable in built distributions.
6. The migration MUST preserve existing runtime behavior and test assertions except where tests inspect the old import path itself.

## Acceptance criteria

- The root `src/buoy_search/` contains only the listed root modules plus the nine named subdirectories.
- No tracked Python source or test imports an old flat path for a moved module.
- Import smoke checks succeed for every new module path.
- The full existing test suite passes after import-path updates.
- A built wheel contains all new subpackages and existing packaged data.
- `python -m buoy_search --help` succeeds.

## Constraints and exclusions

- No compatibility forwarding modules.
- No symbol renames or public call-signature changes.
- No module decomposition beyond the specified moves.
- No new runtime dependencies.
- No unrelated formatting or cleanup.
