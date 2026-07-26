Status: recorded
Created: 2026-07-25
Updated: 2026-07-25
Relates-To: .10x/tickets/done/2026-07-24-integrate-compact-delta-command-center.md, .10x/reviews/2026-07-25-compact-delta-command-center.md, .10x/specs/compact-delta-plan-artifacts.md

# Compact Delta Command Center Evidence

## What was observed

Command Center inventory now summary-qualifies only bounded schema-v2 `plan.json` files with regular sibling `delta.duckdb` files. Summary qualification validates the complete plan-only schema, source/baseline/delta/diff relationships, exact artifact projection/hash, and derived plan ID without opening the payload. Exact schema 1 is silently inert; malformed/unsupported versions such as schema 3 become isolated item errors without payload reads. Dashboard, plan list, and namespace inventory report payload verification `not_checked` and do not invoke the full verifier, connect to DuckDB, or open a delta file. A selected plan binds the captured directory/plan/delta regular-file identities plus expected plan ID/artifact hash/namespace through full verification; deterministic replacement and A→B→A tests fail safely for detail, chunk, and stale routes rather than returning B under A.

The existing `/api/v1/plans/{plan_id}/chunks` route returns only bounded changed/new/reactivated upserts. `/api/v1/plans/{plan_id}/stale-rows` returns bounded stale identities. Both schema-v1 page routes and all page-preview UI/API types were removed. The frontend states that unchanged content is omitted, shows the verified applied-state baseline, changed content, stale identities, and retains escaped-text/read-only boundaries.

Managed-job regressions prove successful publication contains exactly `plan.json` and `delta.duckdb`. Existing descriptor-relative/no-follow publication, durable lifecycle, interruption, one-active, and job identity checks remain passing. The packaged static frontend and installed wheel contain the rebuilt compact-delta review UI.

## Deterministic structural bounds

`tests.test_command_center_local` creates 1,000 schema-valid `plan.json` files padded to exactly 131,072 bytes plus delta sentinels. Its inventory spy rejects any delta `os.open`, full verifier call, or DuckDB connection. List and dashboard still return 1,000 total summaries with API pages bounded to 100.

A separate selected delta contains 100,000 valid stale rows. The production `LocalInventoryService.list_plan_stale_rows` path requests only offset 99,990 / limit 10 and observes exactly rows 99,990 through 99,999. A forwarding connection proxy instruments the actual verifier/query connection and proves exactly one `read_only=True` connection to that selected delta, production execution of `SELECT * FROM stale_rows ORDER BY ordinal LIMIT ? OFFSET ?` with `[10, 99990]`, and exactly ten rows materialized by that window query. Full verification streams all rows to validate logical identity and integrity without retaining the full table.

On macOS 26.5.1 build 25F80, Apple arm64, CPython 3.13.0, uv 0.11.7, the original combined structural measurement was 6.57 seconds real / 228,638,720 bytes maximum RSS. Reviewer reruns observed 5.717 seconds / 228,392,960 bytes, demonstrating ordinary host variance. After the review repairs, the summary, production-query, and replacement/ABA tests ran under `/usr/bin/time -l` in 5.80 seconds real with 212,959,232 bytes maximum RSS (about 203.1 MiB). These host measurements are observational; the identity, open/connection/query/materialization assertions are deterministic.

## Commands and results

- UI-extra focused Python basket across planning, jobs, local/remote inventory, API, CLI, and release automation: 149 tests passed in 19.728 seconds before review; post-review local/API/jobs basket passed 88 tests in 15.333 seconds.
- Frontend: `npm test -- --run` passed 37 tests; `npm run build` passed with 42 transformed modules and produced `index-D34KCjuB.js` plus the existing `index-Amu9gKyT.css`.
- Default-environment full Python discovery before review: 764 tests passed in 84.013 seconds with 31 expected optional-dependency skips. After review repairs and with the UI extra present, full Python discovery passed 766 tests in 84.024 seconds. This includes summary mapping and source-activity assertions for website, GitHub, local Markdown/PDF, DuckDB, BigQuery, and Snowflake without adapter imports. Two established state-root cleanup warnings, expected hostile-host diagnostics, safe fake-provider failures, and one upstream lxml deprecation warning were non-failing.
- The full run initially exposed a stale experimental-baseline fixture missing the schema-v2 `VerifiedApplyPlan` delta/directory binding fields. The fixture was updated mechanically; its 32 tests then passed before the successful full rerun.
- Ranking contract validation passed: 13 datasets, 13 folds, 369 judgments; the existing Buoy insufficiency/pending-baseline result is unchanged.
- C6 forecast validation passed with hash `d5199276c19ae89779287eaa90824ce1e1cc684a3f060899f02f65d976016243`.
- `uv build` produced wheel and sdist in a temporary directory. A fresh temporary Python 3.13 environment installed the wheel with `[ui]`; packaged resource inspection found the expected hashed JS/CSS and `buoy serve --help` passed.
- `uv sync --locked` restored the default environment. FastAPI and Uvicorn were absent, core package/CLI imports loaded no FastAPI, Uvicorn, turbopuffer, BigQuery, or Snowflake modules, and `uv lock --check` passed.
- `buoy plan --help` and `buoy apply --help` passed and contained no legacy artifact filenames.
- `python -m compileall -q src/buoy_search tests`, static-asset synchronization inspection, and repeated `git diff --check` passed. Final no-staged-files state is recorded after the bounded commit.

## Limits

No real plan/apply, source reacquisition, embedding/model load, turbopuffer credential read/call/write, remote catalog mutation, namespace mutation, cleanup of user legacy artifacts, browser mutation workflow, push, PR, merge, publish, or release occurred. Validation is native macOS only. Review blockers were repaired and independent final rereview passed at `.10x/reviews/2026-07-25-compact-delta-command-center.md`; aggregate closure review passed at `.10x/reviews/2026-07-25-compact-delta-hard-cutover.md`.
