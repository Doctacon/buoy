Status: recorded
Created: 2026-07-27
Updated: 2026-07-27
Relates-To: .10x/tickets/done/2026-07-27-implement-summary-inventory-performance.md, .10x/specs/command-center-summary-inventory-performance.md

# Command Center Summary Inventory Performance Implementation

## What was observed

The bounded summary-core implementation now prunes every `plan.json` directory before parsing, reads applied-state inventory through a constant-size aggregate projection, and reuses one locked per-`LocalInventoryService` snapshot for the default 1.0-second TTL.

The default disposable benchmark fixture (1,000 maximum-size plan summaries, one schema-1 descendant tree, five applied-state databases totaling 101,031 rows, and unopened delta sentinels) produced this structural result for `Dashboard → Namespaces → Plans`:

```json
{"applied_row_objects":0,"artifact_walk_directories":1002,"delta_builtin_opens":0,"delta_duckdb_connections":0,"delta_io_opens":0,"delta_os_opens":0,"legacy_descendants_traversed":false,"plan_scans":1,"state_connections":5,"state_scans":1,"state_walk_directories":11,"summary_delta_payload_open_count":0,"summary_delta_payload_opened":false,"summary_sequence":["dashboard","namespaces","plans"]}
```

A focused 100,000-row state test observed one `duckdb.connect(path, read_only=True)` call, one schema-version row, one metadata row, one aggregate result row, zero `AppliedStateRow` constructions, and exact counts: 50,000 active, 25,000 retained stale, 25,000 deleted, 100,000 total. The database device/inode/size/mtime/bytes snapshot was unchanged.

## Procedure and results

```bash
uv run python -m unittest tests.test_applied_state tests.test_command_center_local tests.test_command_center_inventory_benchmark -v
```

Passed 43 focused tests. Coverage includes parse-outcome-independent traversal leaves and valid siblings; schema/metadata/path/status validation; no-follow symlink and replacement rejection; exact aggregate query structure; 100,000-row constant-size result materialization; error reuse and repair after expiry; TTL bounds; expiry/invalidation rebuild; concurrent no-stampede behavior; direct plan/namespace one-refresh discovery; selected plan replacement/ABA full-verification failures; zero summary delta opens; and fresh-process remote/provider/model/source-adapter import isolation.

Independent review then failed commit `700bd33b` on state-database A→B→A replacement, vacuous valid-plan import isolation, stale identity-excluded selected-detail metadata, and missing focused failure-path coverage. The repair basket now passes 86 tests. Added regressions prove deterministic state-database ABA rejection; root/intermediate symlink and lexical escape rejection; existing state-schema-version validator reuse plus zero/duplicate metadata rejection; connection and all held-descriptor close attempts on failures; fresh-process qualification of a real valid schema-v2 plan without source adapters; and reconstruction of rewritten `created_at`/`originating_job_id` after full verification on every selected-detail call.

```bash
uv run python -m compileall -q src/buoy_search/applied_state.py src/buoy_search/command_center_local.py scripts/benchmark_command_center_inventory.py tests/test_applied_state.py tests/test_command_center_local.py tests/test_command_center_inventory_benchmark.py
git diff --check
```

Both passed for the original implementation. Review-repair validation additionally ran:

```bash
uv run python -m unittest tests.test_applied_state tests.test_command_center_local tests.test_command_center_inventory_benchmark tests.test_compact_delta_planning tests.test_plan_artifacts -v
uv run python -m compileall -q src/buoy_search/applied_state.py src/buoy_search/plan_validation.py src/buoy_search/plan_artifacts.py src/buoy_search/command_center_local.py scripts/benchmark_command_center_inventory.py tests/test_applied_state.py tests/test_command_center_local.py tests/test_command_center_inventory_benchmark.py tests/test_compact_delta_planning.py tests/test_plan_artifacts.py
git diff --check
```

The combined repair basket passed 86 tests; compilation and diff checks passed.

```bash
uv run python - <<'PY'
# Build the default fixture in TemporaryDirectory and print structural_observations(fixture).
PY
```

Passed with the exact structural result recorded above; the temporary fixture was deleted automatically.

## Design evidence

- Traversal empties the current `os.walk()` directory list immediately when `plan.json` is present, then applies the existing schema-1 inert/current-plan error isolation path.
- `load_applied_state_summary` binds the exact lexical `state/<site>/<namespace>/state.duckdb` path by holding no-follow descriptors and mutation identities for the database and parent chain. It opens one read-only DuckDB connection, reuses the existing `_validate_database_schema` schema-version validator, requires exactly one metadata row, and executes one aggregate SQL statement using `count(*) FILTER` for all three allowed statuses plus total. This is validator reuse, not a new claim of independent physical table/constraint-schema proof. Post-read held-descriptor/path mutation checks reject ordinary replacement, symlink substitution, and deterministic A→B→A swaps; all descriptors and the connection are closed on success and failure.
- The service cache is instance-local, guarded across lookup and rebuild by one `threading.Lock`, uses injectable monotonic clock and bounded 0.5–2.0-second TTL (default 1.0), stores the complete summary snapshot including isolated errors, and clears non-raising through `invalidate()`. Direct misses force once; concurrent miss refreshes reuse a newer snapshot rather than rebuilding again.
- Selected plan detail/chunk/stale calls still pass cached records through `_verify_record`, including exact pre/post directory, plan, and delta identity plus full `verify_plan_artifacts` payload validation. Selected detail reconstructs every document-backed response field from the fully verified plan, so valid same-inode rewrites of identity-excluded `created_at` and `originating_job_id` cannot return cached stale values. Summary discovery still opens zero delta payloads.
- Summary qualification uses the narrow import-safe `plan_validation` boundary. Full artifact validation delegates its complete plan-document validation to the same boundary before retaining all existing delta schema/row/hash verification; fresh-process coverage parses a real generated schema-v2 plan and observes no crawler/database/local-source adapter imports.

## Limits

This child intentionally did not rerun or alter the frozen baseline timing numbers, perform full-suite/package/frontend validation, thread API routes, or wire managed-job invalidation. Exact before/after timing and downstream integration review remain owned by `.10x/tickets/2026-07-27-validate-command-center-inventory-performance.md` and the sibling integration tickets. State-summary pathname replacement is bound by held file/parent mutation identities; hostile mutation that preserves every observed inode, size, ctime, and mtime value is outside the tested guarantee. Selected-plan same-inode byte rewrites remain subject to complete per-call plan/delta validation, and identity-excluded response metadata is reconstructed only after that verification.
