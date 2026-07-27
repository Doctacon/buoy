Status: active
Created: 2026-07-27
Updated: 2026-07-27

# Command Center Summary Inventory Performance

## Purpose and scope

Define the performance and integrity contract for Command Center local summary inventory over schema-v2 plans and compact DuckDB applied state. This specification narrows implementation behavior without changing plan/state schemas, product authority, selected-plan verification, or the active contracts in `.10x/specs/command-center-local-inventory.md`, `.10x/specs/compact-delta-plan-artifacts.md`, and `.10x/specs/compact-duckdb-applied-state.md`.

It governs artifact traversal boundaries, summary-only applied-state inspection, a short process-local snapshot cache, direct-lookup refresh behavior, and structural/performance evidence. Selected plan detail, changed chunks, and stale rows remain fully verified on every request.

## Artifact traversal boundary

- Inventory MUST recursively search the configured artifacts root without following symlinks.
- Any directory whose current file list contains `plan.json` MUST be treated as a plan-artifact leaf. The current `os.walk()` directory list MUST be emptied before any descendant traversal or current-plan parsing outcome is known.
- The boundary applies equally to schema 1, schema 2, malformed, unsupported, missing-delta, unsafe, and otherwise invalid plans.
- The current `plan.json` MUST still be processed by the existing bounded summary path: schema 1 remains silently inert; malformed/unsupported current plans remain isolated item errors; valid siblings remain discoverable.
- Inventory MUST NOT descend into legacy pages, checkouts, staging/payload directories, or nested plans below an existing plan boundary.
- No broad global directory-name exclusion may replace this rule. Symlink rejection, configured-root containment, no deletion/migration, and zero delta-payload opens during summary discovery remain mandatory.

## Applied-state summary projection

A separate summary reader MUST inspect one selected `state.duckdb` without calling or weakening `load_applied_state()`.

The summary projection exposes only metadata and counts needed by Command Center: current schema version, site ID, namespace, normalized base URL, updated timestamp, last plan/apply IDs, and active, retained-stale, deleted, and total row counts.

For each database the reader MUST:

1. bind the expected regular no-follow database and configured-root identity before opening;
2. open exactly one read-only DuckDB connection and close it reliably;
3. validate the current exact state schema using the existing validator;
4. require exactly one metadata row and validate schema, site, namespace, base URL, expected database location, and normal state identity invariants;
5. use aggregate SQL to count every allowed status and total rows;
6. reject unknown statuses and contradictory totals;
7. avoid the full ordered applied-row query and construct no `AppliedStateRow` objects;
8. perform no write, checkpoint, or mutation; and
9. recheck selected database identity after inspection so replacement or symlink substitution fails closed.

One malformed/unsafe database MUST remain an isolated inventory error and MUST NOT hide valid sibling namespaces. Database bytes MUST remain unchanged.

## Process-local summary snapshot cache

Each `LocalInventoryService` instance MUST own one in-memory summary cache containing only summary-qualified plan records, applied-state summaries, and isolated local artifact errors.

- Default TTL is exactly 1.0 second. The clock and TTL MUST be injectable for deterministic tests; TTL MUST be finite and bounded from 0.5 through 2.0 seconds.
- A lock MUST protect the cache and snapshot rebuild so concurrent requests cannot stampede or observe a partial snapshot.
- Successful summaries and isolated errors are cached. The cache MUST never be serialized or shared across processes.
- `invalidate()` MUST safely clear the cache and MUST NOT raise to callers.
- After TTL expiry or invalidation, the next summary request rebuilds once.
- External CLI plan/apply/cleanup changes may remain invisible for no longer than the TTL.
- Direct `get_plan(plan_id)` and `get_namespace(namespace)` misses MUST force exactly one refresh and retry before returning not-found. They MUST NOT loop.
- Cache entries MUST NOT authorize or bypass selected-record identity checks. A cached selected record whose plan/delta/directory is replaced MUST still fail safely during full verification.

The cache MUST NOT contain verified artifacts, delta rows, chunk/stale windows, preflight/apply authority, remote snapshots, search results, or provider/model/source-adapter objects.

## Selected-plan invariant

`get_plan`, `list_plan_chunks`, and `list_plan_stale_rows` MUST retain exact directory/plan/delta identity binding, complete schema/logical/artifact/source/baseline verification, pre/post replacement checks, and bounded SQL materialization on every request. No process-local verified-forever token is allowed. Full verification remains intentionally linear in selected delta rows and MUST be measured separately from summary latency.

## Structural acceptance scenarios

- A schema-v1 plan with arbitrarily many/deep descendants causes one plan-boundary inspection and no descendant traversal.
- Valid schema-v2, malformed, unsupported, and missing-delta plan directories are leaves; nested plans below them are not discovered; valid siblings remain visible.
- Summary inventory opens no delta payload.
- A 100,000-row applied state produces exact active/retained/deleted/total counts through one read-only connection and aggregate result, without `load_applied_state`, the ordered row query, or row-object construction.
- Dashboard → Namespaces → Plans within one TTL performs one plan scan and one state scan. Concurrent summary requests do not stampede. Expiry and explicit invalidation each trigger exactly one new scan.
- Direct plan and namespace misses refresh once and can discover newly published local records.
- Repaired artifacts/errors become visible after refresh.
- Cache construction/reuse imports no remote client, provider SDK, model, or source adapter.

## Observational performance evidence

Before implementation, current `main` MUST be measured with a disposable fixture; after implementation, the exact fixture and commands MUST be rerun. The fixture contains 1,000 near-limit schema-v2 summaries with unopened delta sentinels, a high/deep schema-v1 legacy tree, one applied state with at least 100,000 rows plus smaller states, and one fully valid selected delta.

Record host OS/architecture, Python and DuckDB versions, fixture counts, cold and at least five warm repetitions (median/p50), and peak RSS when practical for Dashboard, Plans, Namespaces, namespace detail, plan detail, first/later changed pages, and near-end stale page. Summary and selected verification timings MUST be reported separately. On the measured host, warm Dashboard/Plans/Namespaces SHOULD be below 250 ms or at least 5× faster than baseline; this observation MUST NOT become a brittle cross-platform CI limit.

## Exclusions

No schema change, plan migration/deletion, persistent index, watcher, external cache/queue, cached apply authority, cached verified delta rows, selected-verification bypass, cancellation, browser apply, namespace/catalog mutation, source-provider call, graph/taxonomy/ontology work, or turbopuffer operation.
