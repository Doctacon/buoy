Status: recorded
Created: 2026-07-23
Updated: 2026-07-23
Relates-To: .10x/tickets/done/2026-07-23-command-center-local-inventory-services.md, .10x/specs/command-center-local-inventory.md

# Command Center Local Inventory Services Validation

## What was observed

The framework-independent local inventory service implements typed dashboard, plan, namespace, applied-state, page-preview, chunk-preview, warning, and safe-error models. It discovers recursive plan artifacts, isolates malformed items, deduplicates stable plan IDs, orders valid timestamps newest-first, aggregates plan and applied-state inventory, maps every persisted Phase 1 source kind, redacts private/provider details, and enforces safe lookup, traversal, pagination, and preview bounds.

A clean subprocess import loaded none of the BigQuery/Snowflake adapters, remote catalog/client packages, turbopuffer, sentence-transformers, transformers, Google BigQuery, or Snowflake connector modules.

## Procedure and results

1. `uv run python -m unittest discover -s tests -p 'test_command_center_local.py' -v`
   - Result: passed.
   - Output: 14 tests ran in 1.199s; `OK`.
   - Coverage included discovery, recursive ordering, deduplication, malformed isolation, unknown counts, current plan-artifact compatibility, all six supported source mappings, path/provider redaction, plan/state namespace aggregation, safe errors, symlink/traversal rejection, bounded page/chunk previews, pagination bounds, and clean-import isolation.
2. `uv run python -m unittest tests/test_plan_artifacts.py tests/test_applied_state.py tests/test_plan_diff.py -q`
   - Result: passed.
   - Output: 45 tests ran in 1.386s; `OK`.
   - This confirms compatibility with the current persisted plan, DuckDB applied-state, and incremental-diff models.
3. `uv run python -m py_compile src/buoy_search/command_center_local.py tests/test_command_center_local.py && git diff --check && test -z "$(git diff --cached --name-only)"`
   - Result: passed.
   - Output: compilation and diff check passed; no staged files.
4. `uv run pytest -q tests/test_command_center_local.py`
   - Result: not used for acceptance because the repository environment does not install a `pytest` executable; uv reported `Failed to spawn: pytest`. The repository's existing tests use `unittest`, and the equivalent focused unittest commands above passed.

## Inspected compatibility points

- Current plans persist identity, timestamps, source/diff/embedding fields in `plan.json`, page and chunk records in `manifest.json`, Markdown below the plan's `pages/` directory, and optional source activity/ranking data in `summary.json`.
- Current local applied state is one read-only DuckDB ledger per `state/<site_id>/<namespace>/state.duckdb`; the service reuses `load_applied_state` after verifying the discovered ledger path matches persisted identity.
- Current source provenance fields are `repo_full_name`; `file_*`/`pdf_*`; generic `database_backend`, `database_source_id`, and `database_relation`; and legacy DuckDB provenance where generic fields are absent.
- Current missing `embedding_precision` semantics remain the established legacy `float32` compatibility default. Missing counts remain `None` rather than being fabricated.

## What this supports or challenges

This supports every acceptance criterion in `.10x/tickets/done/2026-07-23-command-center-local-inventory-services.md` and the local-inventory acceptance scenarios in `.10x/specs/command-center-local-inventory.md`.

## Limits

- No remote provider/source operation, credential access, model load, browser, API/server/CLI, frontend, mutation, or live database/source connection was exercised or added.
- The service reports malformed or incompatible local artifacts as safe item-level errors; it does not repair them.
- Global applied row totals are unknown when any applied-state artifact is malformed or unsafe.
