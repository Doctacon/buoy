Status: recorded
Created: 2026-07-27
Updated: 2026-07-27
Relates-To: .10x/tickets/2026-07-27-validate-command-center-inventory-performance.md, .10x/tickets/2026-07-27-command-center-inventory-performance-plan.md, .10x/specs/command-center-summary-inventory-performance.md, .10x/specs/command-center-managed-plan-cache-invalidation.md, .10x/specs/command-center-blocking-route-threading.md

# Command Center Inventory Performance Aggregate Validation

## What was observed

The final integrated implementation from branch `work/command-center-inventory-performance` was validated against base `01f2d19432c4bc77e9d6bd7ab8a657b5f4583521`. The exact committed default benchmark driver ran from clean implementation commit `607bae7ec55766acf46eb1c3cd42a0162e4236b3` with no tracked changes. The documentation/evidence/package-contract repair commit that contains this record is necessarily identified by the execution handoff because a commit cannot contain its own hash.

On the same host and exact fixture as the baseline, warm summary p50 fell from 671.639–688.501 ms to 0.018–0.141 ms. Dashboard, Plans, and Namespaces exceeded the required 5× observational improvement by 4,844.9×, 38,250.1×, and 6,532.5× respectively. Process-cold summaries still rebuild the snapshot and measured 365.065–371.328 ms. Selected-plan routes retained complete per-call verification and remain linear in the selected 100,100-row delta; their warm p50 was 2,899.825–2,937.950 ms, about 12.0–13.2% below baseline but intentionally not cached or claimed subsecond.

The final structural sequence `Dashboard → Namespaces → Plans` performed one plan scan, one state scan, five read-only state connections, zero applied-row object constructions, no legacy descendant traversal, and zero delta payload opens. The default 1.0-second locked process-local summary cache is nonpersistent and non-authorizing; successful managed publication invalidates it in-process, while external changes may remain invisible until TTL expiry. Direct misses refresh once. Selected detail/chunk/stale access continues complete identity/schema/logical/source/baseline/payload verification on every request.

## Exact host and fixture

Host:

- OS: macOS 26.5.1 (`macOS-26.5.1-arm64-arm-64bit-Mach-O`)
- Architecture: arm64
- Logical CPUs: 10
- Python: 3.13.0
- DuckDB: 1.5.4

Fixture:

- 1,000 summary-qualified schema-v2 plans, each exactly 131,072 bytes.
- 999 fixed delta sentinels plus one valid selected delta with 100 changed upserts and 100,000 stale rows.
- One schema-v1 boundary with 32 levels, 100 bucket directories, and 5,000 page files.
- One 100,003-row applied state and four 257-row states: 101,031 total state rows across five databases.
- One process-cold call and five same-service warm calls per surface, each in its own fresh worker; OS filesystem caches were not dropped.
- Wall time used `time.perf_counter`; warm p50 is the median of five; peak RSS is process-wide `ru_maxrss` normalized to bytes.
- The fixture lived under a system temporary directory and was removed automatically. No raw benchmark output was retained in the repository.

## Before/after measurements

### Summary inventory

| Surface | Baseline cold (ms) | Baseline warm ×5 (ms) | Baseline p50 (ms) / RSS (bytes) | Final cold (ms) | Final warm ×5 (ms) | Final p50 (ms) / RSS (bytes) | Warm speedup |
|---|---:|---|---:|---:|---|---:|---:|
| Dashboard | 704.402 | 686.041, 694.687, 677.469, 676.771, 678.291 | 678.291 / 264,306,688 | 371.328 | 0.144, 0.131, 0.126, 0.192, 0.140 | 0.140 / 75,366,400 | 4,844.9× |
| Plans | 696.778 | 692.411, 688.501, 690.231, 676.684, 685.421 | 688.501 / 295,845,888 | 365.065 | 0.035, 0.018, 0.016, 0.020, 0.015 | 0.018 / 74,809,344 | 38,250.1× |
| Namespaces | 698.993 | 690.446, 677.361, 673.250, 685.911, 709.920 | 685.911 / 296,517,632 | 366.690 | 0.114, 0.102, 0.099, 0.106, 0.105 | 0.105 / 74,629,120 | 6,532.5× |
| Namespace detail | 693.740 | 674.002, 668.422, 671.639, 668.571, 677.227 | 671.639 / 253,181,952 | 365.771 | 0.154, 0.143, 0.140, 0.141, 0.140 | 0.141 / 74,842,112 | 4,763.4× |

### Selected full verification

These calls are deliberately separate from summary performance. Each call completely verifies the selected delta before returning a bounded result window.

| Surface | Baseline cold (ms) | Baseline warm ×5 (ms) | Baseline p50 (ms) / RSS (bytes) | Final cold (ms) | Final warm ×5 (ms) | Final p50 (ms) / RSS (bytes) | Warm change |
|---|---:|---|---:|---:|---|---:|---:|
| Plan detail | 3,347.904 | 3,329.753, 3,338.324, 3,323.781, 3,317.235, 3,321.163 | 3,323.781 / 304,627,712 | 2,936.719 | 2,883.040, 2,899.899, 2,899.825, 2,907.812, 2,899.063 | 2,899.825 / 196,427,776 | 12.8% lower |
| Changed page 1 (`offset=0`, `limit=50`) | 4,085.209 | 3,338.170, 3,355.035, 3,331.466, 3,350.765, 3,305.817 | 3,338.170 / 358,858,752 | 3,582.395 | 2,967.214, 2,947.569, 2,909.537, 2,937.950, 2,883.611 | 2,937.950 / 259,588,096 | 12.0% lower |
| Changed later (`offset=50`, `limit=50`) | 4,067.524 | 3,335.544, 3,368.601, 3,320.289, 3,334.753, 3,348.582 | 3,335.544 / 355,991,552 | 3,610.365 | 2,966.664, 2,926.716, 2,929.290, 2,936.512, 2,957.944 | 2,936.512 / 261,423,104 | 12.0% lower |
| Near-end stale (`offset=99,950`, `limit=50`) | 4,165.951 | 3,405.128, 3,385.210, 3,363.135, 3,374.436, 3,374.122 | 3,374.436 / 359,104,512 | 3,682.128 | 2,929.302, 2,961.312, 2,913.244, 2,943.179, 2,911.750 | 2,929.302 / 259,735,552 | 13.2% lower |

## Structural result

```json
{"applied_row_objects":0,"artifact_walk_directories":1002,"delta_builtin_opens":0,"delta_duckdb_connections":0,"delta_io_opens":0,"delta_os_opens":0,"legacy_descendants_traversed":false,"plan_scans":1,"state_connections":5,"state_scans":1,"state_walk_directories":11,"summary_delta_payload_open_count":0,"summary_delta_payload_opened":false,"summary_sequence":["dashboard","namespaces","plans"]}
```

## Required commands and exact results

1. `uv run python scripts/benchmark_command_center_inventory.py`
   - Passed from clean commit `607bae7e`. All eight post-timing result validators passed; fixture and timing values are recorded above. Side-effect counters were exactly zero provider, source, plan, and apply operations.
2. `git diff --check && uv sync --locked && uv lock --check`
   - Passed before validation. Core sync resolved 157 lock entries and removed optional FastAPI/Starlette/Uvicorn.
3. `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/validate_ranking_contract.py`
   - Passed in 0.08s: 13 datasets/folds, 90 composite identities, 369 judgments, dataset bundle SHA-256 `5a79f58aaca87a2d4f7cbec68fdcfbbcbf041131821587f8aba74a86daca99d9`.
4. `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/c6_syntax_forecast.py validate`
   - Passed in 0.23s at forecast SHA-256 `d5199276c19ae89779287eaa90824ce1e1cc684a3f060899f02f65d976016243`; tokenizer readiness remained false at the established checkpoint.
5. `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover -s tests -p 'test_*.py' -q`
   - The first run executed 791 tests in 92.902s and failed one release/public-surface test because latest `main` had removed `images/buoy.svg` while the active brand/package contract, `pyproject.toml`, CI archive inventory, and test still required it. The bounded repair restored `images/buoy.svg` byte-for-byte from `src/buoy_search/command_center_static/buoy.svg`; both SHA-256 values are `f791c77f25e202a0556d2688ec9180e7d78c983f220f84b097c1fdc8894edcef`.
   - The complete rerun passed all 791 tests in 83.887s with 35 skips. Expected safe cleanup, hostile-host argparse, fake-provider, and upstream lxml diagnostics were non-failing.
6. `uv sync --locked --extra ui`
   - Passed; installed locked FastAPI 0.139.2, Starlette 1.3.1, and Uvicorn 0.51.0.
7. `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests/test_applied_state.py tests/test_command_center_local.py tests/test_command_center_api.py tests/test_command_center_jobs.py tests/test_planning_service.py tests/test_release_automation.py -q`
   - Passed all 169 focused applied-state/local/API/jobs/planning/release tests in 19.144s. The known Starlette TestClient/httpx deprecation warning was non-failing.
8. `cd web && npm ci`
   - Passed under available Node 24.6.0/npm 11.5.1: 214 packages installed, 215 audited. The established React Router advisory reported two high findings; its applicability/no-action disposition remains owned by `.10x/evidence/2026-07-24-react-router-advisory-no-action.md`.
9. `cd web && npm test -- --run`
   - Passed one Vitest file and all 37 tests in 2.11s.
10. `cd web && npm run build`
    - Passed TypeScript and Vite 7.3.6: 42 modules; `index.html` 0.63 kB, CSS 10.66 kB, JavaScript 278.77 kB.
11. `git diff --exit-code -- src/buoy_search/command_center_static` plus a standard-library HTML reference/hash check
    - Passed. Build output was byte-synchronized. References `/buoy.svg`, `/assets/index-D34KCjuB.js`, and `/assets/index-Amu9gKyT.css` all resolve. SHA-256: index `c4129e00430f8378c89ae550bf72c860bd170d64158d1b78e13dd472a9855833`; JavaScript `734e5bb9acbeb0cc98e9da4e53c6fba81b15be1df34b59bbdfc98d3bbd63a74c`; CSS `fd57c4f2b1319313451571398931ad5b20c8707cdc3f931cd88d993d3c1bd815`; SVG `f791c77f25e202a0556d2688ec9180e7d78c983f220f84b097c1fdc8894edcef`.
12. `uv build --out-dir dist`
    - Passed in 1.99s; built `buoy_search-0.4.1.dev112+g607bae7ec.d20260728-py3-none-any.whl` and matching sdist.
13. Standard-library wheel/sdist inventory assertions
    - Passed. Wheel: 69 entries, including index, Buoy SVG, and exactly one hashed JavaScript/CSS asset. Sdist: 159 entries, including docs, benchmark driver, restored public SVG, and all intended frontend source/build inputs. Both archives contained zero `node_modules` entries.
14. `uv pip install --no-deps --target /tmp/buoy-command-center-wheel-target dist/*.whl` plus isolated installed-wheel TestClient smoke
    - Install passed. The accepted resolved-temporary-root run imported the package and static root from `/private/tmp/buoy-command-center-wheel-target`, then received HTTP 200 from `/api/v1/health`, `/api/v1/dashboard`, `/api/v1/plans`, `/api/v1/namespaces`, and `/`. Empty local summary counts/lists were exact and the packaged HTML loaded.
15. Safari WebDriver availability/browser smoke probe
    - `/usr/bin/safaridriver --version` reported Safari 26.5 and `/status` was ready, so a real-engine session was attempted without installing dependencies. Session creation returned the explicit platform error that Safari's user-level “Allow remote automation” setting was disabled. The setting was not mutated. No product/browser assertion was accepted, and all temporary server/driver roots/logs were removed.
16. `rm -rf dist web/node_modules /tmp/buoy-command-center-wheel-target && uv sync --locked && uv lock --check`
    - Passed. Optional UI packages were removed and the default locked core environment was restored.
17. Isolated core import check using `.venv/bin/python -I`
    - Passed. Ordinary `buoy_search` and `buoy_search.cli` imports found neither FastAPI nor Uvicorn and loaded no Command Center API/job module, BigQuery/Snowflake adapter, turbopuffer, sentence-transformers, or transformers.
18. Final `git diff --check`, lock check, staged-file, generated-directory, and tracked-artifact inventory checks
    - Passed. No files were staged; `dist` and `web/node_modules` were absent; no tracked database/profile/log/private-state/generated-artifact path was found.

## Documentation and changed files

`docs/command-center.md` now states the `plan.json` traversal leaf, aggregate read-only state summaries, locked 1.0-second process-local TTL, immediate managed invalidation, bounded external visibility, one-refresh misses, nonpersistent/non-authorizing cache scope, and continued complete selected verification with explicit linear-cost/no-universal-subsecond limits. README already links the canonical packaged SVG and accurately describes Command Center installation/scope, so no README change was needed.

Final-child files are:

- `docs/command-center.md`
- `images/buoy.svg` (mechanical restoration of a pre-existing latest-main package/public-surface defect)
- `.10x/evidence/2026-07-27-command-center-inventory-performance.md`
- `.10x/tickets/2026-07-27-validate-command-center-inventory-performance.md`
- `.10x/tickets/2026-07-27-command-center-inventory-performance-plan.md`

No new or changed test file was needed in this final child; the existing release-automation regression detected the missing required SVG and the existing 791-test suite plus focused 169-test basket exercised the integrated behavior.

## Deviations, defects, and limits

- Pre-existing defect repaired: hosted-main commit `7dbf0feb` removed `images/buoy.svg` but did not update the still-active brand/package/CI/test contract. The final child restored only an identical copy; no spec, package configuration, CI workflow, or other asset changed.
- Installed-wheel exploratory deviation: the first smoke used Darwin's lexical `/tmp` path and correctly failed the managed-root identity guard because the physical root is `/private/tmp`. The accepted rerun resolved the temporary root first and all installed-wheel endpoints passed. No source repair was needed.
- Browser deviation: Safari was installed, but a real WebDriver session was unavailable without changing the operator's disabled “Allow remote automation” setting. The setting was left untouched; jsdom frontend tests and real installed-wheel FastAPI/static smoke passed, but no graphical browser claim is made.
- The available local Node was 24.6.0, not CI's pinned 24.18.0. The immutable CI convention remains pinned to 24.18.0; local install/test/build passed.
- Selected verification is intentionally linear in selected delta rows and remains about 2.90–2.94 seconds warm p50 for this 100,100-row fixture. This is the principal residual performance cost and is not hidden by summary caching.
- The summary cache is process-local, nonpersistent, non-authorizing, and may remain stale for at most the TTL after external-process changes. A crash after durable managed success but before callback execution has the same bounded stale window.
- Worker-pool exhaustion under many simultaneous blocking calls remains outside the one-blocked-call threading contract.
- Cold means process-cold, not OS-cache-cold. RSS is process-wide. Five warm calls are a small observational sample and are not portable CI thresholds.
- The npm React Router advisory and Starlette/lxml warnings are pre-existing and separately documented; no dependency or product scope was widened here.

## External-side-effect attestation

No live crawl, clone, source adapter, database provider, remote refresh/search, turbopuffer, embedding/model, apply, catalog/namespace mutation, push, merge, PR, publish, or release operation ran. The benchmark reported zero provider/source/plan/apply operations. API/provider/source tests used fakes or temporary local artifacts. Package, benchmark, installed-wheel, local server, and attempted browser-driver files lived only in system temporary directories and were removed. No generated benchmark database/tree/profile/raw log, distribution, `node_modules`, credential, private path, or local state is committed.
