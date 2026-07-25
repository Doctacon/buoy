Status: recorded
Created: 2026-07-24
Updated: 2026-07-25
Relates-To: .10x/tickets/done/2026-07-24-implement-compact-delta-planning.md, .10x/reviews/2026-07-25-compact-delta-planning.md, .10x/specs/compact-delta-plan-artifacts.md

# Compact Delta Planning Evidence

## What was observed

Schema-v2 planning now constructs the complete desired manifest only in process, diffs it against the presence-bound local applied state, and persists exactly `plan.json` plus `delta.duckdb`. The DuckDB has the exact three fixed tables, changed/new/reactivated upserts, stale/retained-stale identities, and plan/source/baseline binding. Canonical logical hashing uses the exact SQL column field names (`tags_json` and `source_metadata_json` remain the logical keys while their values are parsed JSON). Full verification now enforces exact application tables/views/macros, SQL schema/constraints, canonical JSON, ordinal/sort order, count relationships, row/hash/embedding identity, safe relative paths, source invariants, stale correspondence, logical/artifact identity, and credential/path privacy. The schema-v1 writer path is gone.

The shared planning service loads applied state before artifact finalization, derives all source variants from stable crawl/source metadata, records the baseline presence bit and canonical state hash, removes known source staging, rejects any unexpected retained output, verifies the compact delta before success, and copies only the two files for managed jobs. Source planning remains turbopuffer/model inert.

## Focused validation

- `tests.test_compact_delta_planning`, `tests.test_plan_artifacts`, and `tests.test_planning_service`: 33 passed.
- `tests.test_plan_diff` and `tests.test_plan_cleanup`: 14 passed.
- `tests.test_github_repo`: 25 passed.
- `tests.test_cli`: 41 passed.
- `tests.test_database_relation_cli`: 10 passed.
- `tests.test_duckdb_relation_cli`: 5 passed.
- Combined planning/source basket across compact artifacts, diff, cleanup, shared service, CLI, GitHub, shared database relations, DuckDB, BigQuery, and Snowflake: 179 passed in 12.602 seconds.
- Python compilation of `plan_artifacts.py` and `planning_service.py`: passed.

Tests cover first apply, no change, changed rows, reactivation, active and retained stale rows, duplicate row identity, output/time/job-independent artifact identity, baseline presence hash, all exact source variants with zero upserts, source metadata agreement, schema/table/count/logical/identity tampering, no legacy path fields, two-file managed publication, staging removal, source-path privacy, and planning credential/model isolation.

## Post-review repair validation

Independent review found that the original logical hash renamed the SQL contract keys and that full verification did not independently enforce several spec invariants. The repair retained exact logical keys, added a direct golden hash, and added re-signed tamper tests for content/hash, row formula, absolute source path, empty required field, credential metadata, diff counts, stale correspondence, and canonical ordering, plus direct noncanonical JSON, unexpected view/macro, and credential-bearing source URI tests.

- Expanded compact planning/source basket across compact artifacts, plan artifacts/diff/cleanup, shared planning, CLI, GitHub, shared database relations, DuckDB, BigQuery, and Snowflake: 183 passed in 13.687 seconds.
- Compact-delta focused module: 10 passed.
- Python compilation and `git diff --check`: passed.

The initial 179-test result above records the pre-review implementation state; it is not evidence for the repaired verifier. The 183-test first post-review basket was subsequently superseded by the second repair below.

## Second post-review repair validation

Second rereview found four remaining verifier gaps. The repaired verifier now rejects extra non-internal tables/views/macros in every DuckDB schema; recursively rejects credential-bearing URI userinfo in plan options, source attributes, and row metadata; requires local/PDF filename basenames and exact document URI/source-ID authority; validates website/GitHub/document/database source variant consistency; reconciles only independently derivable delta operation counts while accepting a one-page zero-chunk first plan; enforces first-apply structural zeros; and requires lexicographically sorted unique tags. The schema's diff wording was narrowed accordingly because omitted unchanged content cannot independently reconstruct later page/unchanged counts.

Re-signed tamper tests cover cross-schema table/view/macro objects, metadata URI userinfo, unsafe filename, source-ID/extension mismatch, every operation count, first-apply structural counts, noncanonical/unsorted/duplicate tags, and valid zero-chunk page behavior. Sorting tags changes the schema-v2 identity golden to `d6b5e13bbbfdbbdeacef69ec5f154e9340038f88b28b40160135e7d9ed1014e0` without changing row identity.

- `tests.test_compact_delta_planning`: 13 passed, including resigned contradictions for website, GitHub, local file, PDF, DuckDB, BigQuery, and Snowflake source variants.
- Expanded basket across compact artifacts, plan artifacts/diff/cleanup, shared planning, CLI, GitHub, shared database relations, DuckDB, BigQuery, and Snowflake: 186 passed in 13.908 seconds.
- `python -m py_compile` for `plan_artifacts.py` and `planning_service.py`: passed.
- `git diff --check`: passed.

The 186-test result above was superseded by the final authority/privacy repair below.

## Final authority and privacy repair validation

Final rereview found that a fully re-signed delta could move valid row content to a foreign source URL, omit plan-derived identity recomputation, preserve contradictory metadata aliases, or introduce additional credential/provider connection markers. The final verifier now binds every upsert and stale canonical URL to the exact plan source authority: website exact hostname, GitHub repository/blob plus row path/ref, opaque local/PDF document URL, or backend/source database document URI. It enforces every present PDF file alias and DuckDB legacy alias, exact source-derived `site_id` and `namespace_candidate`, exact current applied-state schema, expanded recursive privacy markers, and all plan/source/delta identity consistency.

All seven source variants now write and fully verify zero-upsert artifacts. Re-signed tests move valid rows to foreign website, GitHub, local-file, PDF, DuckDB, BigQuery, and Snowflake authorities while recomputing row/logical/artifact identities; all are rejected by source authority. Additional tests reject a foreign stale URL, contradictions in all four PDF file aliases and all three DuckDB legacy aliases, site/candidate/schema tampering, profile/connection plan options, and token/profile/connection/authorization/cookie/API-key/secret metadata keys. Safe `ranking_profile` and token-budget/tokenizer fields remain allowed.

Exact final commands:

- `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests.test_compact_delta_planning -q` — 15 tests passed in 3.424 seconds.
- `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests.test_compact_delta_planning tests.test_plan_artifacts tests.test_plan_diff tests.test_plan_cleanup tests.test_planning_service tests.test_cli tests.test_github_repo tests.test_database_relation tests.test_database_relation_cli tests.test_duckdb_relation tests.test_duckdb_relation_cli tests.test_bigquery_relation tests.test_snowflake_relation -q` — 188 tests passed in 15.112 seconds. Two expected cleanup-safety warning lines were emitted by existing failure fixtures.
- `PYTHONDONTWRITEBYTECODE=1 uv run python -m py_compile src/buoy_search/plan_artifacts.py src/buoy_search/planning_service.py` — passed.
- `git diff --check` — passed.

The 188-test result above was superseded by the strict metadata/privacy repair below.

## Strict metadata and URI privacy repair validation

Final privacy review found that open-ended row metadata still permitted unknown custom/provider fields and credential material in URI query/fragment components. The repaired verifier uses exact per-source-kind allowlists derived from current generated frontmatter: common safe metadata plus only the GitHub, local-file, PDF, DuckDB, BigQuery, or Snowflake fields owned by that source. Every unknown custom/provider key and every cross-kind invariant/variant key is rejected; `duckdb_document_id` and all other legacy aliases are classified and accepted only for their owning source kind.

URI validation now rejects userinfo, secret-bearing query/fragment names or values, and unapproved provider connection schemes in plan sources, row canonical URLs, plan options/attributes, and row metadata. Stored website source URI must equal current canonical normalization: legitimate nonsecret query is retained, while an input fragment remains permitted but is removed by existing base normalization; legitimate row query/fragment citations remain intact. Re-signed adversarial tests cover source `access_token`, row `api_key`, private/secret fragments, a PostgreSQL endpoint, `snowflake_account`, cross-kind `duckdb_document_id`, and positive `lang=en`/section cases.

- `tests.test_compact_delta_planning`: 17 passed in 3.841 seconds.
- Expanded planning/source basket: 190 passed in 15.638 seconds; two expected cleanup-safety warnings were emitted by existing failure fixtures.
- Python compilation of `plan_artifacts.py` and `planning_service.py`: passed.
- `git diff --check`: passed.

The 190-test result was superseded by the bounded recursive privacy repair below.

## Recursive nested-URI privacy repair validation

Final nested-URI review found that a safe-looking outer public URL could hide a percent-encoded credential-bearing or provider connection URI inside repeated query/fragment encoding. The repaired verifier uses one bounded recursive JSON/string validator across plan options, source values, tags, row metadata, and canonical URLs. It bounds JSON depth/nodes, string bytes, and URL decode rounds; repeatedly decodes nested values; scans embedded absolute URI substrings; rejects userinfo and non-authorized schemes; and restricts opaque/database schemes to their exact source URI, canonical row URL, and `url` metadata contexts. Legitimate nested public HTTP(S) URLs remain accepted.

Fully re-signed regressions cover double-encoded nested HTTP userinfo and PostgreSQL URIs in plan options and allowed `fetcher` metadata, plus a positive double-encoded nested public URL in both surfaces.

- Focused new regression: 1 passed.
- Compact artifact/diff/service basket: 54 passed.
- Expanded planning/source basket: 191 passed in 16.017 seconds; two expected cleanup-safety warnings were emitted by existing failure fixtures.
- Python compilation of `plan_artifacts.py` and `planning_service.py`: passed.
- `git diff --check`: passed.

The 191-test result was superseded by the final fail-closed decode/path-boundary repair below.

## Final URL-decode and absolute-path privacy repair

Final rereview found two bounded fail-open edges. Recursive percent-decoding previously stopped after its configured rounds even when another decode would still change the value, and absolute POSIX path detection covered selected prefixes rather than all rooted paths. The repaired validator now raises when URL decoding has not stabilized after five rounds and uses platform-independent `PurePosixPath`/`PureWindowsPath` authority to reject all absolute POSIX, drive-qualified Windows, and UNC paths. The exact `include_paths`/`exclude_paths` option keys retain their validated source-relative URL-pattern semantics; validated source URI paths remain accepted.

New regressions reject a seven-times encoded credential URI, `/var/lib/buoy/private.db`, `C:\\Users\\operator\\private.db`, and `\\\\server\\share\\private.db` in plan options and allowed row metadata. A website source URI containing `/var/lib/docs` remains valid, proving URI path components are not confused with filesystem paths.

- Focused compact-delta planning suite: 20 passed in 4.221 seconds.
- Expanded planning/source basket: 193 passed in 16.304 seconds; two expected cleanup-safety warnings were emitted by existing failure fixtures.
- Python compilation of `plan_artifacts.py` and `planning_service.py`: passed.
- `git diff --check`: passed.

The 193-test result is the current planning-child evidence.

## Representative artifact measurements

A temporary one-row fixture produced:

- first apply: files `delta.duckdb,plan.json`; `plan.json` 1,248 bytes; delta 1,585,152 bytes; 1 upsert, 0 stale;
- no change: files `delta.duckdb,plan.json`; `plan.json` 1,248 bytes; delta 798,720 bytes; 0 upserts, 0 stale;
- incremental changed content: files `delta.duckdb,plan.json`; `plan.json` 1,248 bytes; delta 2,371,584 bytes; 1 upsert, 1 stale.

The no-change delta contains no content rows. No state database was created for first-apply planning. Measurements are host/DuckDB-version observations, not portable size guarantees.

## Limits and dependency handoff

The dependent apply ticket still reads schema-v1 manifest/chunks artifacts and therefore is not expected to pass until `.10x/tickets/2026-07-24-implement-compact-delta-apply.md` replaces that reader. Command Center/managed-job contract consumers beyond the shared publication seam remain for the final integration ticket. Full repository tests were not claimed at this intermediate dependency boundary.

No live source provider, embedding model, turbopuffer credential/call/write, real apply, user artifact deletion, push, PR, merge, publish, or release occurred.
