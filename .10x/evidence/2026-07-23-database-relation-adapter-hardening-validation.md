Status: recorded
Created: 2026-07-23
Updated: 2026-07-23
Relates-To: .10x/tickets/done/2026-07-22-add-bigquery-snowflake-adapters.md

# Database relation adapter hardening validation

## What was observed

The post-merge adapter hardening passed parent-observed validation from `work/harden-database-relation-adapters`.

- `git diff --check`: passed.
- `uv sync --locked`: resolved 154 and checked 106 packages.
- Ranking contract validator: passed with 13 datasets, 369 judgments, bundle SHA `5a79f58aaca87a2d4f7cbec68fdcfbbcbf041131821587f8aba74a86daca99d9`.
- C6 syntax forecast validator: passed with forecast SHA `d5199276c19ae89779287eaa90824ce1e1cc684a3f060899f02f65d976016243`.
- Full unittest discovery: 609 tests passed in 65.813s; output contained two established best-effort cleanup warnings and one upstream lxml deprecation warning.
- `uv build --out-dir /tmp/buoy-hardening-build`: wheel and sdist built successfully.
- `uv sync --extra bigquery`: succeeded with `google-cloud-bigquery==3.42.2`.
- `uv sync --extra snowflake`: succeeded with `snowflake-connector-python==4.7.1`.
- Final `uv sync --locked`: restored the default environment.

Focused development runs recorded in the ticket passed 43 and 159 tests.

## Procedure

Commands matched the required validation workflow, except build output was directed to `/tmp/buoy-hardening-build` to avoid leaving generated artifacts in the worktree. Optional environments were installed independently, then removed by the final locked sync.

## What this supports

This supports BigQuery dry-run/actual cap ordering, the one-query acquisition design, cloud selected-row hardening, Snowflake query-tag bounds, CLI help, compatibility regression coverage, packaging, and optional dependency resolution.

## Limits

No live BigQuery, Snowflake, or turbopuffer call was made. Fake providers verify generated SQL/configuration and bounded Python validation but cannot prove provider optimizer behavior or live concurrent-mutation timing. BigQuery dry-run estimates remain provider estimates of its chosen query plan. Snowflake still uses multiple read statements; selected-row filters and Python revalidation prevent unsafe materialization but do not establish snapshot isolation.
