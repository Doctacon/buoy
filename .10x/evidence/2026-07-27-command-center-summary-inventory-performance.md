Status: recorded
Created: 2026-07-27
Updated: 2026-07-27
Relates-To: .10x/tickets/2026-07-27-implement-summary-inventory-performance.md, .10x/specs/command-center-summary-inventory-performance.md

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

```bash
uv run python -m compileall -q src/buoy_search/applied_state.py src/buoy_search/command_center_local.py scripts/benchmark_command_center_inventory.py tests/test_applied_state.py tests/test_command_center_local.py tests/test_command_center_inventory_benchmark.py
git diff --check
```

Both passed.

```bash
uv run python - <<'PY'
# Build the default fixture in TemporaryDirectory and print structural_observations(fixture).
PY
```

Passed with the exact structural result recorded above; the temporary fixture was deleted automatically.

## Design evidence

- Traversal empties the current `os.walk()` directory list immediately when `plan.json` is present, then applies the existing schema-1 inert/current-plan error isolation path.
- `load_applied_state_summary` binds the exact lexical `state/<site>/<namespace>/state.duckdb` path with regular-directory checks and `O_NOFOLLOW`, retains the descriptor identity, opens one read-only DuckDB connection, invokes the existing schema validator, reads exactly one metadata row, and executes one aggregate SQL statement using `count(*) FILTER` for all three allowed statuses plus total. It validates path/metadata/base URL/schema identity, rejects unknown statuses by count reconciliation, closes reliably, and rechecks descriptor/path identity after inspection.
- The service cache is instance-local, guarded across lookup and rebuild by one `threading.Lock`, uses injectable monotonic clock and bounded 0.5–2.0-second TTL (default 1.0), stores the complete summary snapshot including isolated errors, and clears non-raising through `invalidate()`. Direct misses force once; concurrent miss refreshes reuse a newer snapshot rather than rebuilding again.
- Selected plan detail/chunk/stale calls still pass cached records through `_verify_record`, including exact pre/post directory, plan, and delta identity plus full `verify_plan_artifacts` payload validation. Summary discovery still opens zero delta payloads.

## Limits

This child intentionally did not rerun or alter the frozen baseline timing numbers, perform full-suite/package/frontend validation, thread API routes, or wire managed-job invalidation. Exact before/after timing and downstream integration review remain owned by `.10x/tickets/2026-07-27-validate-command-center-inventory-performance.md` and the sibling integration tickets. Filesystem identity checks detect ordinary replacement/symlink substitution through bound pre/post device/inode identity; as with existing selected-plan checks, a hostile same-inode concurrent byte rewrite is outside the guarantee of inode binding and must still be rejected by the relevant schema/identity validation when observed.
