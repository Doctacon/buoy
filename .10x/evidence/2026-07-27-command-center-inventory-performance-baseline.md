Status: recorded
Created: 2026-07-27
Updated: 2026-07-27
Relates-To: .10x/tickets/2026-07-27-baseline-command-center-inventory-performance.md, .10x/specs/command-center-summary-inventory-performance.md

# Command Center Inventory Performance Baseline

## What was observed

Unchanged runtime source from base commit `01f2d19432c4bc77e9d6bd7ab8a657b5f4583521` was measured with the disposable fixture produced by `scripts/benchmark_command_center_inventory.py`. No file under `src/` was changed. The fixture lived only in a system temporary directory, was reused by isolated measurement workers, and was deleted automatically after the run.

Host:

- OS: macOS 26.5.1 (`macOS-26.5.1-arm64-arm-64bit-Mach-O`)
- Architecture: arm64
- Logical CPUs: 10
- Python: 3.13.0
- DuckDB: 1.5.4

Fixture:

- 1,000 summary-qualified schema-v2 plans, each exactly 131,072 bytes.
- One plan had a fully valid selected `delta.duckdb` containing 100 changed upsert rows and 100,000 stale rows; 999 siblings contained a fixed sentinel, not a DuckDB database.
- One schema-v1 plan boundary contained a `pages` tree 32 levels deep, 100 bucket directories, and 5,000 page files.
- One large applied-state database contained 100,003 rows.
- Four smaller applied-state databases contained 257 rows each.
- Total applied-state rows were 101,031 across five databases.

## Procedure

Run from the repository root:

```bash
uv run python scripts/benchmark_command_center_inventory.py
```

The driver:

1. constructs and verifies the fixture without invoking a provider, source adapter, plan operation, or apply operation;
2. starts a fresh worker process for each measured surface;
3. creates one `LocalInventoryService` in that worker;
4. records the first service call as process-cold, without attempting to drop OS filesystem caches;
5. records the next five calls against the same service and fixture as warm repetitions;
6. computes warm p50 with `statistics.median` over those five values;
7. measures wall time with `time.perf_counter`; and
8. records process `ru_maxrss`, including interpreter/import/runtime memory, normalized to bytes.

The exact default fixture parameters are constants/default arguments in the committed driver. Its stdout is the complete machine-readable JSON result. The measurement used no private artifacts and retained no fixture, database, legacy tree, browser profile, or raw JSON log.

## Results

### Summary inventory

| Surface | Cold (ms) | Five warm repetitions (ms) | Warm p50 (ms) | Peak RSS (bytes) |
|---|---:|---|---:|---:|
| Dashboard | 704.402 | 686.041, 694.687, 677.469, 676.771, 678.291 | 678.291 | 264,306,688 |
| Plans | 696.778 | 692.411, 688.501, 690.231, 676.684, 685.421 | 688.501 | 295,845,888 |
| Namespaces | 698.993 | 690.446, 677.361, 673.250, 685.911, 709.920 | 685.911 | 296,517,632 |
| Namespace detail | 693.740 | 674.002, 668.422, 671.639, 668.571, 677.227 | 671.639 | 253,181,952 |

### Selected-plan full verification

These timings are intentionally separate from summary inventory. Every call performed the current selected-plan full-verification path.

| Surface | Cold (ms) | Five warm repetitions (ms) | Warm p50 (ms) | Peak RSS (bytes) |
|---|---:|---|---:|---:|
| Plan detail | 3,347.904 | 3,329.753, 3,338.324, 3,323.781, 3,317.235, 3,321.163 | 3,323.781 | 304,627,712 |
| Changed page 1 (`offset=0`, `limit=50`) | 4,085.209 | 3,338.170, 3,355.035, 3,331.466, 3,350.765, 3,305.817 | 3,338.170 | 358,858,752 |
| Changed later page (`offset=50`, `limit=50`) | 4,067.524 | 3,335.544, 3,368.601, 3,320.289, 3,334.753, 3,348.582 | 3,335.544 | 355,991,552 |
| Near-end stale page (`offset=99,950`, `limit=50`) | 4,165.951 | 3,405.128, 3,385.210, 3,363.135, 3,374.436, 3,374.122 | 3,374.436 | 359,104,512 |

## Structural observations

A traced `Dashboard → Namespaces → Plans` sequence against one service produced:

- 3 plan scans and 3 state scans: every summary request rebuilt the snapshot.
- 3,405 artifact-walk directory yields, or 1,135 per scan. The current walker descended through the schema-v1 `pages` descendants after seeing its `plan.json`.
- 33 state-walk directory yields.
- 30 state DuckDB connections, or two connections per database per scan.
- 303,093 `AppliedStateRow` constructions, exactly `101,031 rows × 3 scans`.
- 0 delta DuckDB connections, 0 Python `os.open` calls for any `delta.duckdb`, and 0 summary delta payload opens; the focused driver test separately confirmed sentinel bytes remained unchanged.

Source and focused-test inspection additionally show:

- `_snapshot()` calls `_discover_plans()` and `_discover_states()` on every invocation.
- State discovery first reads metadata, then calls `load_applied_state()`, which executes the full ordered applied-row query and constructs one `AppliedStateRow` per row.
- Each selected plan detail/chunk/stale request first performs the same summary snapshot, then `_verify_record()` opens exactly the selected delta read-only and fully streams/verifies it before returning the requested bounded window.
- The eight measured FastAPI inventory handlers are `async def` handlers that directly invoke these synchronous filesystem/DuckDB methods. The blocking work is therefore executed on the endpoint event-loop thread in this baseline (`src/buoy_search/command_center_api.py:712-760`).

## What this supports or challenges

This supports the child ticket's pre-change baseline and a reproducible before/after comparison. It shows that current warm summary navigation is approximately 672–689 ms p50 on this host, repeated summary navigation does not reuse inventory work, schema-v1 descendants are traversed, applied state is fully materialized, and selected full verification remains a separate approximately 3.32–3.37 second p50 cost.

The run recorded exactly zero provider, source, plan, and apply operations.

## Limits

- "Cold" means the first call in a fresh Python worker, not a machine reboot or privileged filesystem-cache drop.
- `ru_maxrss` is whole-process peak memory, not operation-attributed incremental RSS, and includes interpreter/import overhead.
- Results are observational for this host and fixture, not portable CI thresholds.
- The selected fixture has 100 changed rows and 100,000 stale rows. It exercises early/later changed windows and a near-end stale window but is not a distribution model of production content sizes.
- Runtime tracing used Python-level spies; it establishes calls/materialization, not physical disk-block reads below DuckDB or the OS cache.
- Event-loop behavior is established by route/source structure, not a concurrent-load latency experiment.
