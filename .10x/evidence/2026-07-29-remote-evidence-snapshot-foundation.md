Status: recorded
Created: 2026-07-29
Updated: 2026-07-29
Relates-To: .10x/tickets/2026-07-29-implement-remote-evidence-snapshot-foundation.md, .10x/specs/remote-evidence-snapshots.md

# Remote Evidence Snapshot Foundation

## What was observed

Graph Phase 3A is implemented on `work/remote-evidence-snapshot-foundation` from base commit `606c168389e28b09105e8eb139f2cde063994a83` (`origin/main` fetched 2026-07-29). The final implementation commit is the commit containing this evidence record; resolve it with `git rev-parse HEAD` after commit creation.

The installed and locked official provider SDK is `turbopuffer==2.4.0`. The implementation uses `client.namespace(destination).branch_from(source_namespace=source)`, explicit strong ordered queries, `limit=10_000`, metadata reads, conditional catalog upsert, and guarded `delete_all()` only for current-invocation incomplete internal resources. No live provider call was made.

### Remote architecture and naming

- Branch per source: `buoy-evidence-branch-<16-hash>-<16-source-hash>`.
- Compact ledger per snapshot: `buoy-evidence-ledger-<16-hash>`.
- Fixed region-local completed catalog: `buoy-evidence-catalog-v1`.
- Snapshot ID: `evidence_<first-16-hex>` from schema, sorted source namespaces, region, locked local row fingerprints, site/plan/apply identity, routing-card revision, and embedding/schema contract.
- Identity excludes creation time, provider metrics/latency/request IDs, paths, and credentials.

Ledger schema has no vector/content/title. `status`, `source_namespace`, and `branch_namespace` are filterable; `source_row_id` is additionally filterable to support bounded ordered remote-ledger/branch verification. URL, hashes, site, plan/apply provenance, snapshot identity, and ordinal are non-filterable. Allowed membership is exactly `active`, `retained_stale`, or `deleted`.

Catalog schema stores safe scalar/list metadata and canonical JSON strings for keyed source hashes, plan/apply IDs, card revisions, and branch observations. It stores branch parent/created/last-write/approximate metrics, exact ledger counts/hash, snapshot hash, and manifest hash. `state=complete` is inserted last with insert-if-absent semantics.

### Limits and eligibility

Defaults are 1,000,000 exact local ledger rows and 5,368,709,120 approximate remote logical bytes. Estimate returns `would_pass_limits=false` and a safe limit diagnostic while making no write/artifact; snapshot fails before branches. Explicitly larger limits are supported and never truncate.

Selection requires one to 64 unique sorted valid explicit namespace IDs. Routing catalog, `buoy-evidence-` internal IDs, wildcards/prefix/all/automatic selection, missing/ambiguous/first-apply/zero-row state, disabled/incompatible cards, mismatched site/plan/apply/region/embedding/schema, and sharded metadata fail closed. Zero-row state is rejected because SDK/API 2.4.0 cannot create an absent schema-only ledger namespace and a sentinel would violate ledger membership.

Every selected apply lock is acquired in namespace order and held through fingerprinting, branch reconciliation, ledger verification, and catalog finalization. Lock tests observed fail-before-branch behavior and release after success/failure.

### Reconciliation and cleanup

Active and retained-stale local rows must exist in a branch and match ID, canonical URL, page/chunk/embedding hashes, plan ID, and applied timestamp. Deleted rows must be absent but remain in the ledger. Missing, extra, present-deleted, mismatched, duplicate/out-of-order, non-advancing, changed-parent, changed-last-write, and changed-count/byte metadata fail.

Verification uses only the completed remote catalog, remote ledger, and branches; a test deleted current local applied state before a successful verify. It performs zero writes. Branches are operationally immutable only: Buoy never writes them after `branch_from`, and verification detects later metadata or row drift.

Before completion, tests observed cleanup of only exact branches/ledger created by the failing invocation. Preexisting/wrong-parent branches and unrelated namespaces were not deleted. Catalog-finalization and reconciliation failures removed current incomplete resources; completed-marker uncertainty skips deletion. A forced local manifest failure left the completed remote row and internal resources intact for later reconstruction.

## 100,000-row structural measurement

A provider-free 100,000-row DuckDB state plus matching lean fake branch was run in a temporary directory. The implementation used DuckDB `fetchmany(1_000)`, 10,000-row strong remote pages, and 1,000-row ledger write batches. No content/vector attribute was requested. The fake retained remote provider state in-process, so peak RSS includes the fake's 100,000-row ledger and is an upper-bound harness measurement, not solely Buoy buffer memory.

Observed JSON:

```json
{"approximate_remote_logical_bytes":50000000,"branch_calls":1,"branch_create_count":1,"catalog_write_calls":1,"content_or_vector_requested":false,"elapsed_reconciliation_seconds":5.58458,"ledger_rows_written":100000,"ledger_write_calls":100,"local_manifest_bytes":1018,"manifest_files":["evidence_ef0dd74964a7f9c0/snapshot.json"],"peak_rss_delta_bytes":202080256,"remote_query_calls":29,"rows":100000,"wall_elapsed_seconds":5.599794}
```

The normal suite also contains this 100,000-row full fake snapshot, a separate 100,000-row local stream/fingerprint test, a 10,001-row two-page scan, and a 2,501-row `[1000, 1000, 501]` ledger batching test. No latency pass/fail threshold is asserted.

## Validation procedure and exact results

All commands ran from the task worktree after final source changes:

- `git diff --check` — pass, no output.
- `uv sync --locked` — pass; 157 packages resolved, 106 checked.
- `uv lock --check` — pass; 157 packages resolved.
- `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/validate_ranking_contract.py` — pass; 13 datasets, 369 judgments, dataset bundle `5a79f58aaca87a2d4f7cbec68fdcfbbcbf041131821587f8aba74a86daca99d9`.
- `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/c6_syntax_forecast.py validate` — pass; forecast `d5199276c19ae89779287eaa90824ce1e1cc684a3f060899f02f65d976016243`.
- Focused evidence/applied-state/apply/remote-catalog/release suite — 182 tests passed in 18.781s.
- Full `unittest discover` — 839 tests passed in 102.506s; 39 skipped. Existing expected warning/argparse/log lines appeared; no failure.
- `uv build --out-dir dist` — pass; wheel and sdist built.
- Package inspection — wheel 72 files, sdist 168 files; wheel contains all three evidence modules; sdist contains evidence modules, `docs/evidence-snapshots.md`, and all three focused test modules; no `state.duckdb`, `snapshot.json`, or `node_modules` packaged.
- Provider-blocked ordinary/evidence imports — pass; `turbopuffer` absent from `sys.modules`.
- `buoy evidence estimate|snapshot|verify --help` — pass without credentials/provider import.
- Restore `rm -rf dist web/node_modules; uv sync --locked; uv lock --check` — pass.
- Final `git diff --check` — pass.

Frontend source was unchanged, so packaged assets were not rebuilt and `npm ci/test/build` was not run, following the explicit unchanged-frontend boundary.

## What this supports

This supports that full evidence remains in turbopuffer branches, only bounded membership/summary metadata is duplicated remotely, only `snapshot.json` persists locally, source namespaces and branches are never written by ledger/catalog paths, verification is independent of current local state, limits and sharding fail before branches, identical completed snapshots reuse deterministic identities, and internal evidence namespaces are excluded from ordinary discovery/routing/Command Center source classification.

## Limits

- No live smoke ran; ambient credentials were not used. Provider permissions, billing-account behavior, and production latency remain unobserved.
- Approximate logical bytes are provider metadata and are not exact storage or price.
- Branch immutability is detected, not access-controlled against external writers.
- Strong consistency has the documented provider operational limits.
- The 100,000-row peak RSS includes in-process fake remote storage and is not a provider-backed client-only measurement.
- No push, merge, PR, publish, release, source apply, source namespace write, LLM call, graph extraction, taxonomy/ontology creation, or UI build occurred.
