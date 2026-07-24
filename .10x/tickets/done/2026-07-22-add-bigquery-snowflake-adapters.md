Status: done
Created: 2026-07-22
Updated: 2026-07-22
Parent: .10x/tickets/done/2026-07-22-add-database-relation-sources.md
Depends-On: .10x/tickets/done/2026-07-22-refactor-shared-database-relation-core.md

# Add BigQuery and Snowflake adapters

## Scope

Implement lazy official BigQuery and Snowflake readers, identifier/schema safety, global aggregate validation, deterministic limited acquisition, dry-run/cost labels/timeout diagnostics, named Snowflake connections/query tags/timeouts/batched fetch/cleanup, backend models, plan/crawl CLI dispatch and validation, truthful source-vs-turbopuffer summaries, optional dependencies and fake-backed tests.

## Exclusions

Live calls, credential CLI fields, arbitrary SQL, catalog/ranking/docs, new apply source logic, non-goal databases/features.

## Acceptance criteria

Both remote table/view paths implement the shared contract; invalid combinations/identifiers fail; SDKs remain optional/lazy; no secret/connection leakage; saved-plan apply neither imports nor connects; focused fake-backed adapter and CLI tests pass.

## Evidence expectations

Run adapter/CLI/apply tests without optional SDKs or credentials and record exact results.

## Progress and notes

- 2026-07-22: Opened from ratified specs.
- 2026-07-22: Implemented lazy official-client BigQuery and Snowflake relation sources over the shared database materialization core. BigQuery now uses ADC-style client construction, schema inspection, strict three-part identifier validation, dry runs for all generated read-only queries, aggregate cost-cap enforcement plus actual job caps, operation labels, result timeouts, deterministic limited acquisition, and non-secret job statistics. Snowflake now uses named connections only, canonical uppercase identifiers, read-only schema/aggregate/limited queries, query tags, session and execute timeouts, bounded `fetchmany()`, and reliable rollback/cursor/connection cleanup.
- 2026-07-22: Added `--database-backend`, BigQuery billing/location/bytes controls, Snowflake named connection, remote query timeout, conditional local path rules, exact backend-flag validation, explicit-empty mapping rejection, lazy dispatch for both `plan` and `crawl`, remote source-vs-turbopuffer activity summaries, and source-independent logical plan metadata. Existing implicit and explicit DuckDB paths remain compatible. Extended internal database URI handling so BigQuery/Snowflake plans use stable site/namespace identities without changing apply source logic.
- 2026-07-22: Added optional `bigquery` and `snowflake` project extras and updated `uv.lock` through normal `uv run` resolution. Added fake-backed adapter and CLI tests for identities, safety, tables/views via schema inspection, mappings/title fallback, generated SQL, dry-run cap, labels/timeouts, query statistics, global failures, resource cleanup, missing dependencies, plan/crawl dispatch, invalid combinations, artifact leakage, truthful summaries, and verified saved-plan loading without source access.
- 2026-07-22: Final focused command `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests.test_bigquery_relation tests.test_snowflake_relation tests.test_database_relation_cli -q` passed 22 tests in 0.057s. Final expanded command `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests.test_database_relation tests.test_bigquery_relation tests.test_snowflake_relation tests.test_database_relation_cli tests.test_duckdb_relation tests.test_duckdb_relation_cli tests.test_cli tests.test_crawler tests.test_apply_cli -q` passed 192 tests in 8.753s with two pre-existing best-effort cleanup warnings. Targeted `py_compile`, `git diff --check`, and the no-staged-files check passed. The fake-backed BigQuery plan also verifies and completes `apply --dry-run` while both source loaders are configured to fail on access. Implementation is complete within this child scope; catalog/ranking/docs/full regression were completed by child 3. Parent evidence and passing re-review are recorded at `.10x/evidence/2026-07-23-database-relation-sources-validation.md` and `.10x/reviews/2026-07-23-database-relation-sources-review.md`; closed.

- 2026-07-22: Closure repair after independent review added BigQuery's official `job_timeout_ms` server-side job configuration plus client timeout cancellation, explicit client cleanup, and redacted SDK diagnostics; removed eager adapter imports from CLI/crawler so apply CLI import does not load any database adapter; made timeout validation finite; aligned Snowflake with the shared strict identifier subset, rejected quoted mixed-case schema columns, used explicit Python-strip-equivalent whitespace characters, and redacted SDK diagnostics. Focused fake-backed regressions cover each boundary.
- 2026-07-22: Repair validation passed 52 focused tests in 1.830s and full default discovery passed 600 tests in 70.008s after `uv sync --locked`; only two established cleanup warnings and one upstream lxml deprecation warning were emitted.

- 2026-07-23: Reopened after post-merge review identified bounded adapter-hardening regressions: BigQuery dry-run cap ordering and query-count cost, cloud selected-row revalidation under mutation, Snowflake query-tag length, and shared CLI help wording. The user ratified exact failure behavior, compatibility constraints, tests, documentation, and validation commands. This is regression repair within the original adapter scope; no new product surface or specification is required.

## Reopened acceptance criteria

- BigQuery dry runs omit provider bytes caps; Buoy aggregates exact-query estimates and fails before actual submission with estimate and cap; actual jobs retain provider caps.
- BigQuery source-query count is reduced where safe without weakening global validation/counts, deterministic bounded acquisition, timeout/cancellation, or read-only behavior.
- BigQuery and Snowflake acquisition SQL filters valid IDs and nonblank content; shared bounded Python revalidation rejects null/blank/duplicate selected IDs and null/blank content before materialization.
- Snowflake query tags remain readable when short and become deterministic, collision-resistant, and within the documented limit when long.
- Shared CLI help names all database relations; detailed indexing docs describe cost and mutation hardening.
- Existing identities, URLs, page filenames, plan schema/saved plans, catalog/ranking, DuckDB behavior, lazy imports, and apply isolation remain compatible.
- Focused tests, complete unittest discovery, validators, locked sync, build, optional-extra resolution, and diff checks pass without live service calls.

## Progress and notes (reopened hardening)

- 2026-07-23: Replaced BigQuery's three dry-run/three-actual-query flow with one generated read-only statement that emits one summary row, an optional global duplicate diagnostic, and bounded ordered document rows. Planning now submits exactly one uncapped dry run, compares its aggregate estimate with Buoy's configured cap, and only then submits one actual job carrying `maximum_bytes_billed`, labels, server/client timeouts, cancellation, and existing diagnostics. Fake coverage proves a provider that rejects capped dry runs is no longer triggered and aggregate cap failure submits no actual query.
- 2026-07-23: Added shared bounded selected-row validation in `database_relation.py`. BigQuery and Snowflake now reject selected null/blank IDs, duplicate text IDs, null/blank content, and apply title fallback before materialization. Both acquisition queries filter valid IDs and nonblank content; fake mutation regressions prove failure before a `pages/` directory is written while complex Unicode/slash/quote/backslash IDs remain unchanged.
- 2026-07-23: Bounded Snowflake query tags to the documented 2,000-character maximum. Short tags are unchanged; oversized source IDs retain the readable Buoy/operation prefix and receive a full SHA-256 collision-resistant suffix. Updated both `--max-pages` help surfaces and detailed indexing cost/mutation/tag documentation.
- 2026-07-23: Focused command `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests.test_database_relation tests.test_bigquery_relation tests.test_snowflake_relation tests.test_database_relation_cli -q` passed 43 tests in 0.413s. Expanded database/DuckDB/apply/catalog/retriever command passed 159 tests in 11.936s. Targeted `py_compile` and `git diff --check` passed.
- 2026-07-23: Required full validation passed after `uv sync --locked` resolved 154 and checked 106 packages. Ranking contract emitted 13 datasets/369 judgments and bundle SHA `5a79f58aaca87a2d4f7cbec68fdcfbbcbf041131821587f8aba74a86daca99d9`; C6 forecast SHA was `d5199276c19ae89779287eaa90824ce1e1cc684a3f060899f02f65d976016243`; full discovery passed 609 tests in 75.408s with two established cleanup warnings and one upstream lxml deprecation warning; `uv build --out-dir dist` built both artifacts. Optional resolution succeeded for `google-cloud-bigquery==3.42.2` and `snowflake-connector-python==4.7.1`; final `uv sync --locked` restored the default environment. No live warehouse or turbopuffer calls were made.
- 2026-07-23: Parent reran the complete required suite: 609 tests passed in 65.813s, both validators and package build passed, both optional extras resolved, and the locked default was restored. Independent review found no critical, significant, or minor findings. Evidence: `.10x/evidence/2026-07-23-database-relation-adapter-hardening-validation.md`. Review: `.10x/reviews/2026-07-23-database-relation-adapter-hardening-review.md`. Reopened acceptance criteria are supported; closed.

## Blockers

None.
