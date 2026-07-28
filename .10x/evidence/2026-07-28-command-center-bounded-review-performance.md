Status: recorded
Created: 2026-07-28
Updated: 2026-07-28
Relates-To: .10x/tickets/done/2026-07-28-validate-bounded-review-performance.md, .10x/tickets/done/2026-07-28-command-center-bounded-review-performance-plan.md, .10x/specs/command-center-bounded-inventory-transport.md, .10x/specs/command-center-coalesced-plan-review.md

# Command Center Bounded Review Performance Aggregate Validation

## Handoff and scope

Integrated validation ran on branch `work/command-center-bounded-review-performance` from hosted-main base `4a4af8c1db8464893ea97ce2395842e25d861ed0`. Three independent aggregate reviewers subsequently passed backend correctness/security/integrity, frontend/performance/accessibility, and docs/package/static/scope hygiene; the third reviewer identified only the closure mechanics now reconciled in the terminal ticket graph and final review record. The exact final bounded commit hash is necessarily supplied by the execution handoff: a commit cannot contain its own hash. No push, merge, PR, publish, release, or external product operation occurred.

The integrated diff implements server-filtered bounded plan/namespace transport, bounded namespace history, one-verification combined review, focused plan pagination, browser race/history handling, synchronized static assets, benchmark/test updates, and canonical documentation. README remained materially accurate and was not changed.

## Diagnosis and final semantics

The unchanged-base benchmark established that Plans and Namespaces each fetched all ten 100-row API pages and implied 1,000 React rows. Initial review, changed-page navigation, and stale-page navigation each issued detail/chunks/stale together, causing three concurrent complete verifications.

The final implementation requests one 50-row server-filtered inventory page and renders those 50 current React rows. Initial selected-plan review issues one combined request and invokes the complete verifier once with both 10-row windows. Changed or stale pagination issues only its focused endpoint and performs one fresh complete verification for that section. No verification result, rows, token, cache entry, or apply authority persists between payload requests. Summary snapshot cache behavior remains unchanged. Complete verification remains linear and took about 2.61–2.71 seconds in the verifier, and 2.61–3.06 seconds wall time, for this 100 changed/100,000 stale fixture.

`docs/command-center.md` now states browser/server pagination, server-side local filters, separate accurate remote-only presentation, bounded namespace history, one-verification initial review, one fresh complete verification per focused payload page, no persisted authority, unchanged summary cache, and the residual several-second linear cost without a constant-time or universal-subsecond claim.

## Host and fixture

- OS: `macOS-26.5.1-arm64-arm-64bit-Mach-O`
- Architecture/logical CPUs: arm64 / 10
- Python: 3.13.0
- DuckDB: 1.5.4
- FastAPI / Starlette / httpx: 0.139.2 / 1.3.1 / 0.28.1
- Node / npm: v24.6.0 / 11.5.1
- Fixture: 1,000 near-limit 131,072-byte schema-v2 plan summaries across 1,000 namespaces; selected delta 100 changed plus 100,000 stale rows; 999 unopened delta sentinels; one applied-state row.
- Fixture and raw benchmark JSON lived under system temporary paths and were removed.

## Before/after transport

JSON bytes are exact UTF-8 response-body bytes excluding headers/framing. React rows are bound to the request shape by the focused 1,000-record RTL regression.

| Surface | Before requests / records / JSON bytes / React rows | After requests / records / JSON bytes / React rows | After wall / cumulative peak RSS |
|---|---|---|---|
| Plans initial | 10 / 1,000 / 710,603 / 1,000 | 1 / 50 / 35,558 / 50 | 436.358 ms / 248,020,992 bytes |
| Namespaces initial | 10 / 1,000 / 575,605 / 1,000 | 1 / 50 / 28,808 / 50 | 4.605 ms / 248,119,296 bytes |

The 20× baseline record/row multiplication is removed. Plans timing includes the initial cached-snapshot build; Namespaces reuses that process-local snapshot. These timings are observational, not portable thresholds.

## Before/after selected review

| Transition | Before requests / verifier calls | After requests / verifier calls | After response bytes / materialized rows | After verifier / wall / peak RSS |
|---|---|---|---|---|
| Initial | 3 / 3 | 1 / 1 | 5,953 / 20 (10 changed + 10 stale) | 2,609.953 ms / 2,612.343 ms / 280,395,776 bytes |
| Changed page | 3 / 3 | 1 / 1 | 2,646 / 10 changed | 2,707.862 ms / 3,063.165 ms / 280,395,776 bytes |
| Stale page | 3 / 3 | 1 / 1 | 1,989 / 10 stale | 2,662.493 ms / 3,023.422 ms / 280,395,776 bytes |

All three final verifier calls used `materialize=False`, ran on one `AnyIO worker thread` off the benchmark main thread, and materialized only their requested verifier windows: combined `(10 upsert, 10 stale)`, chunks `(10, 0)`, stale `(0, 10)`. The initial request used both `(0, 10)` windows; focused requests used upsert `(10, 10)` or stale `(10, 10)` only.

## Commands and results

1. `git diff --check`; `uv sync --locked`; `uv lock --check` — passed. Core sync resolved 157 lock entries and removed FastAPI, Starlette, and Uvicorn.
2. `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/validate_ranking_contract.py` — passed: 13 datasets/folds, 90 composite identities, 369 judgments, dataset bundle SHA-256 `5a79f58aaca87a2d4f7cbec68fdcfbbcbf041131821587f8aba74a86daca99d9`.
3. `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/c6_syntax_forecast.py validate` — passed at forecast SHA-256 `d5199276c19ae89779287eaa90824ce1e1cc684a3f060899f02f65d976016243`; established tokenizer readiness remained false.
4. `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover -s tests -p 'test_*.py' -q` — passed 806 tests in 100.532 seconds with 38 expected core-environment skips. Existing mocked cleanup, hostile-host argparse, fake-provider, and lxml diagnostics were non-failing.
5. `uv sync --locked --extra ui` — passed; installed locked FastAPI 0.139.2, Starlette 1.3.1, and Uvicorn 0.51.0.
6. `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests.test_applied_state tests.test_command_center_local tests.test_command_center_api tests.test_command_center_jobs tests.test_planning_service tests.test_plan_artifacts tests.test_command_center_inventory_benchmark tests.test_command_center_bounded_review_benchmark tests.test_release_automation -q` — passed 205 focused tests in 23.131 seconds.
7. `cd web && npm ci` — passed: 214 packages installed and 215 audited. The separately documented React Router advisory still reports two high findings; no dependency scope changed.
8. `cd web && npm test -- --run` — passed all 45 tests in 2.86 seconds, including exact 1,000-record bounded inventories and combined/focused review request shapes.
9. `cd web && npm run build` — passed TypeScript and Vite 7.3.6, 42 modules. Output: 632-byte HTML, 285,744-byte JS, 11,191-byte CSS.
10. Static reference/orphan/hash check — passed. References are `/buoy.svg`, `/assets/index-DAM_87xf.js`, `/assets/index-0ugYq-Qa.css`; no orphan asset exists. SHA-256 values: HTML `6e7501489318c5dab74c11908904dfc1cbc06ebab6412a858757b65704793e0a`, SVG `f791c77f25e202a0556d2688ec9180e7d78c983f220f84b097c1fdc8894edcef`, JS `9d0985edf337986886ffd79bbe3dccdfbdee4c3c81944a80f4c35fe36391fc20`, CSS `8aa90744893ad97ca4fcfd03fc1fec818967a36e6bff22c8e894663959f39be3`.
11. `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/benchmark_command_center_bounded_review.py` — passed on the exact 1,000-plan/namespace plus 100/100,000 selected-delta fixture; results are recorded above. Raw JSON was removed.
12. `rm -rf dist && uv build --out-dir dist` — passed, building `buoy_search-0.4.1.dev118+g4a4af8c1d.d20260728-py3-none-any.whl` and matching sdist.
13. Standard-library wheel/sdist inventory — passed. Wheel has 69 entries with exactly one hashed JS and CSS asset. Sdist has 161 entries and contains `docs/command-center.md`, both inventory/bounded-review benchmark drivers, the bounded-review benchmark test, frontend source/test, and lockfile. Both archives contain zero `node_modules`, `.10x`, DuckDB/database/log/profile files.
14. Isolated installed-wheel smoke — passed from `/private/tmp/buoy-bounded-wheel-target.CEGdbq`: Dashboard, Plans, Namespaces, namespace detail, combined review, and static root all returned HTTP 200; dashboard found three plans, bounded namespace history found one plan, combined review returned 10 changed and 10 stale rows, and no apply/remote/provider/model/source-specific adapter module loaded.
15. Final restoration command `rm -rf dist web/node_modules && uv sync --locked && uv lock --check`, temporary-shim core import isolation, generated-target cleanup/inventory, `git diff --check`, empty staged-name check, and status inspection — passed. FastAPI/Uvicorn and optional API/jobs/provider/model modules were absent from ordinary core imports; final worktree has no `dist`, `web/node_modules`, source version shim, non-venv bytecode/cache, staged file, or tracked private/generated artifact.

## Validation repairs and deviations

The asynchronous validation runner reported an `ENOENT` while persisting its output because completed work/validation cleanup removed the runner artifact directory before output persistence. The validation work itself completed, its results were recovered from the completed run context, and no product, test, package, or external-operation failure occurred; the deviation is limited to runner-output persistence.

The first focused benchmark-test run failed because the finalized test expected ten changed rows from a 12-row fixture at offset 10; the real bounded result was correctly two. The assertion was repaired to prove exact window materialization, then the complete focused and full gates passed.

Two preliminary installed-wheel harness attempts were rejected without source changes. The first checked generic `crawler`/`database_relation` modules after complete artifact verification even though the governing inertness contract excludes provider/model/source-specific adapters; the accepted rerun uses the existing tested forbidden-module set. The second fixture-builder retry lacked this worktree's ignored Hatch-generated `_version.py`; the accepted command used a temporary validation shim only for fixture construction and removed it before installed-wheel execution. These were harness/environment corrections, not product defects.

## Changed implementation and test surface

- Backend: `src/buoy_search/command_center_local.py`, `src/buoy_search/command_center_api.py`.
- Frontend: `web/src/App.tsx`, `web/src/api.ts`, `web/src/types.ts`, `web/src/styles.css`.
- Tests/benchmark: `tests/test_command_center_local.py`, `tests/test_command_center_api.py`, `web/src/App.test.tsx`, `tests/test_command_center_bounded_review_benchmark.py`, `scripts/benchmark_command_center_bounded_review.py`, `scripts/benchmark_command_center_inventory.py`.
- Docs/static: `docs/command-center.md`, packaged `index.html`, `index-DAM_87xf.js`, `index-0ugYq-Qa.css`, and removal of the two superseded hashed assets.
- Durable records: the two active specs; terminal parent and children; baseline/backend/frontend/aggregate evidence; three completed-child reviews; and `.10x/reviews/2026-07-28-command-center-bounded-review-performance-final-review.md`.

## Limits and residual risk

- TestClient and RTL do not constitute a live graphical-browser run.
- JSON bytes depend on response fields and deterministic fixture metadata; they exclude HTTP framing.
- Filesystem caches were not dropped. RSS is cumulative whole-process peak, not operation-attributed incremental memory.
- Timing is one host observation. Complete selected-delta verification remains intentionally linear and several seconds for 100,100 rows.
- The summary cache remains process-local, nonpersistent, non-authorizing, and unchanged by this work.
- The installed wheel was smoke-tested with a small valid selected delta; the full benchmark used the checkout production code and exact large fixture.
- Independent review found no implementation defect. Residuals are limited to TestClient/RTL not being a graphical-browser run, filesystem race coverage not exhausting every platform timing, reviewer reliance on recorded complete validation after the environment was restored, and intentionally linear several-second complete verification.

## Side-effect attestation

No live crawl, clone, document/database source adapter, database provider, remote refresh/search, embedding/model load, apply, approved apply, catalog/namespace mutation, turbopuffer operation, push, merge, PR, publish, release, or credential operation ran. Tests used fakes and disposable local artifacts. Benchmark, build, install target, fixture, and raw output paths were temporary and removed. No external service or product state was read or mutated.
