Status: active
Created: 2026-08-27
Updated: 2026-08-27
Decision: .10x/decisions/buoy-advances-repo-eval-for-test-layout.md

# Buoy Test Suite Layout

## Purpose and scope

Reorganize the flat `tests/` directory into concern-oriented Python test packages that mirror the production package's major boundaries. This is a structural pass only: existing test modules move as whole files, with only import, discovery, workflow, documentation, and path-reference changes required by relocation.

The pass MUST NOT split large test modules, redesign fixtures, rename test methods/classes, change assertions, weaken coverage, or refactor test behavior.

## Required layout

`tests/` MUST contain an empty `__init__.py`, the existing `fixtures/` support directory, and these concern packages:

- `core/`
- `cli/`
- `catalog/`
- `indexing/`
- `planning/`
- `relations/`
- `retrieval/`
- `telemetry/`
- `evals/`
- `provider_receipts/`
- `benchmarks/`

Every concern package MUST contain an empty `__init__.py`. No test implementation module or benchmark remains directly under `tests/`.

## Exact module mapping

### `tests/core/`

- `test_ci_workflow.py`
- `test_config.py`
- `test_dynamic_version.py`
- `test_environment_alias_removal.py`
- `test_local_paths.py`
- `test_model_progress.py`

### `tests/cli/`

- `test_apply_cli.py`
- `test_catalog_cli.py`
- `test_cli.py`

### `tests/catalog/`

- `test_catalog.py`
- `test_remote_catalog.py`

### `tests/indexing/`

- `test_chunker.py`
- `test_crawler.py`
- `test_crawler_exact_host.py`
- `test_github_repo.py`
- `test_repo_syntax_chunking.py`
- `test_treatment_token_budget.py`

### `tests/planning/`

- `test_applied_state.py`
- `test_apply_catalog_registration.py`
- `test_compact_delta_planning.py`
- `test_plan_artifacts.py`
- `test_plan_cleanup.py`
- `test_plan_diff.py`
- `test_planning_service.py`

### `tests/relations/`

- `test_bigquery_relation.py`
- `test_database_relation.py`
- `test_database_relation_cli.py`
- `test_duckdb_relation.py`
- `test_duckdb_relation_cli.py`
- `test_snowflake_relation.py`

### `tests/retrieval/`

- `routing_confidence_fixtures.py`
- `test_automatic_routing.py`
- `test_automatic_routing_after_apply.py`
- `test_multi_namespace_retrieval.py`
- `test_retrieval_evidence.py`
- `test_retriever.py`
- `test_routing_activation_cli.py`
- `test_routing_quality.py`
- `test_routing_quality_runner.py`
- `test_evidence.py`

### `tests/telemetry/`

- `test_local_retrieval_telemetry.py`
- `test_retrieve_command_telemetry.py`
- `test_telemetry_cli.py`
- `test_telemetry_envelope.py`
- `test_telemetry_producer.py`
- `test_telemetry_queue.py`
- `test_telemetry_store.py`
- `test_telemetry_v2_storage.py`
- `test_telemetry_writer.py`

### `tests/evals/`

- `test_autoresearch.py`
- `test_c6_syntax_forecast.py`
- `test_evals.py`
- `test_evidence_evals.py`
- `test_multi_corpus_eval_runner.py`
- `test_multi_corpus_evals.py`
- `test_ranking_contract.py`
- `test_ranking_promotion.py`

### `tests/provider_receipts/`

- `test_provider_invocation_receipt_catalog.py`
- `test_provider_invocation_receipt_content.py`
- `test_provider_invocation_receipt_core.py`
- `test_provider_invocation_receipt_integration.py`

### `tests/benchmarks/`

- `benchmark_apply_catalog_registration.py`

### `tests/fixtures/`

- `retrieve_command_timing_probe.py` remains at its existing path.

## Behavior

1. All cross-test imports MUST use the new package paths.
2. Pytest and standard-library unittest discovery MUST recursively discover the same tests under Python 3.11 and 3.13.
3. Workflow, script, documentation, and record references that execute/import active tests MUST use the new paths.
4. Historical evidence prose MAY retain historical paths when it explicitly describes a past checkout; durable pointers to moved active files MUST be repaired.
5. Old root test modules MUST be removed rather than retained as forwarding modules.
6. Test contents MUST remain byte-equivalent after normalizing only relocation-required import/path-reference lines.
7. The benchmark remains outside ordinary `test_*.py` discovery.
8. Because five moved test paths are active repo-eval judgments, implementation MUST preserve immutable v2 and create a path-only v3 successor with unchanged judgment semantics, `baseline_status=pending`, and `promotion_eligible=false`.

## Acceptance criteria

- The final tree exactly matches this mapping.
- No active Python, workflow, script, or documentation command imports a moved root test module.
- Cross-test import cycles and helper imports resolve from the new packages.
- Pytest reports the same 1,191 tests and 1,292 subtests as the pre-move baseline.
- Standard-library discovery reports 1,191 tests on Python 3.11 and 3.13.
- Ranking, routing, promotion, CI-workflow, package, wheel/sdist, and isolated-install checks remain green.
- Repo-eval v2 remains byte-identical; v3 changes only version/lineage, the five approved test paths, and mechanically derived path-membership identities.
- A semantic diff audit finds no assertion, fixture value, test method/class name, or behavior change beyond relocation requirements.
- No compatibility forwarding modules or unrelated cleanup are introduced.

## Explicit exclusions

- Splitting large test modules.
- Extracting shared helpers from existing test modules.
- Renaming tests or changing collection semantics.
- Adding or removing coverage.
- Reorganizing production source, `.10x` history, or non-test fixtures beyond path-pointer repair.
