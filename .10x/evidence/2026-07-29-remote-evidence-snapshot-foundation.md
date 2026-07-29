Status: recorded
Created: 2026-07-29
Updated: 2026-07-29
Relates-To: .10x/tickets/2026-07-29-implement-remote-evidence-snapshot-foundation.md, .10x/specs/remote-evidence-snapshots.md

# Remote Evidence Snapshot Foundation

## What was observed

Graph Phase 3A is implemented on `work/remote-evidence-snapshot-foundation` from base commit `606c168389e28b09105e8eb139f2cde063994a83` (`origin/main` fetched 2026-07-29). Initial implementation commit `cf37f5fff20cc05ffe561cbf3010165e779e74eb` received two independent fail reviews; the follow-up repair commit is the commit containing this updated record.

The installed and locked official provider SDK is `turbopuffer==2.4.0`. The implementation uses `client.namespace(destination).branch_from(source_namespace=source)`, explicit strong ordered queries, `limit=10_000`, metadata reads, conditional ledger ownership/catalog completion writes, and no provider import during ordinary module import/help. No live provider call was made.

### Remote architecture and naming

- Branch per source: `buoy-evidence-branch-<16-hash>-<16-source-hash>`.
- Compact ledger per snapshot: `buoy-evidence-ledger-<16-hash>`.
- Fixed region-local completed catalog: `buoy-evidence-catalog-v1`.
- Snapshot ID: `evidence_<first-16-hex>` from schema, sorted source namespaces, region, locked local row fingerprints, site/plan/apply identity, routing-card revision, and embedding/schema contract.
- Identity excludes creation time, provider metrics/latency/request IDs, paths, and credentials.

Ledger schema has no vector/content/title. `status`, `source_namespace`, and `branch_namespace` are filterable; `source_row_id` is additionally filterable for ordered per-source remote verification. URL, hashes, site, plan/apply provenance, snapshot identity, and ordinal are non-filterable. Allowed membership is exactly `active`, `retained_stale`, or `deleted`.

Catalog schema stores safe scalar/list metadata, canonical source identity JSON, source hashes, plan/apply IDs, card revisions, branch observations, approximate logical bytes, exact ledger counts/hash, snapshot hash, and manifest hash. The full deterministic source identity is rebound to the snapshot-ID digest during verify. `state=complete` is inserted last with insert-if-absent semantics.

### Limits and eligibility

Defaults are 1,000,000 exact local ledger rows and 5,368,709,120 approximate remote logical bytes. Estimate returns `would_pass_limits=false` and a safe limit diagnostic while making no write/artifact; snapshot fails before branches. Explicitly larger limits are supported and never truncate.

Selection requires one to 64 unique sorted valid explicit namespace IDs. Routing catalog, `buoy-evidence-` internal IDs, wildcards/prefix/all/automatic selection, missing/ambiguous/first-apply/zero-row state, disabled/incompatible cards, mismatched site/plan/apply/region/embedding/schema, and sharded metadata fail closed. Zero-row state is user-ratified as ineligible because SDK/API 2.4.0 cannot create an absent schema-only ledger and a sentinel would violate ledger membership.

Every selected apply lock is acquired in namespace order and held through fingerprinting, branch reconciliation, ledger verification, and catalog finalization. Lock tests observed fail-before-branch behavior and release after success/failure.

### Reconciliation, verification, and failure handling

Active and retained-stale local rows must exist in a branch and match ID, canonical URL, page/chunk/embedding hashes, plan ID, and applied timestamp. Deleted rows must be absent but remain in the ledger. Missing, extra, present-deleted, mismatched, duplicate/out-of-order, non-advancing, changed-parent, changed-last-write, and changed-count/byte metadata fail.

Verification uses only the completed remote catalog, remote ledger, and branches; a test deleted current local applied state before successful verify. It performs zero writes. It recomputes each ordered source fingerprint and source/status counts from ledger rows, validates deterministic ledger document IDs/ordinals/site/source/branch identity, checks deterministic branch/ledger names and the source-identity-derived snapshot ID, compares actual branch observations, and recomputes ledger/snapshot/manifest hashes. Tests alter source hashes, plan IDs, branch names, approximate bytes, branch rows, ledger rows, timestamps, and manifests and observe rejection.

Branches are operationally immutable only: Buoy never writes them after `branch_from`, performs a final metadata check after ledger verification immediately before catalog publication, and verification detects later metadata or row drift.

The independent review found that deterministic namespace names cannot prove exclusive cleanup ownership across hosts. The repair marks creation only after definite success, uses conditional first-ledger inserts and exact affected IDs, tracks transport/count ambiguity separately, and issues no automatic namespace deletion. Failures report all definite/possible incomplete internal IDs. This preserves concurrent, preexisting, unknown, source, routing-catalog, and completed evidence and leaves retention/deletion for a separately ratified lifecycle. Tests observe zero `delete_all()` calls on branch, ledger, reconciliation, and catalog failures.

SDK-shaped metadata tests return Python `datetime` values from `to_dict`-like objects; the implementation normalizes them to ISO strings and completes catalog serialization.

## 100,000-row structural measurement

A provider-free 100,000-row DuckDB state plus matching lean fake branch was run in a temporary directory after the independent-review repairs. DuckDB uses `fetchmany(1_000)`, remote scans use 10,000-row strong pages, and ledger writes use at most 1,000 rows and 16 MiB encoded payload. The global O(total rows) verification ID set was removed. No content/vector attribute was requested. The fake retains 100,000 branch and ledger rows in-process, so RSS includes fake remote state and is an upper-bound harness measurement, not solely Buoy buffer memory.

Observed JSON:

```json
{"approximate_remote_logical_bytes":50000000,"billable_logical_bytes_queried":2200,"billable_logical_bytes_returned":2000000,"branch_calls":1,"catalog_write_calls":1,"elapsed_reconciliation_seconds":6.336577,"ledger_write_calls":100,"local_manifest_bytes":1018,"manifest_files":["snapshot.json"],"peak_rss_delta_bytes":204177408,"remote_query_calls":22,"remote_query_metric":30,"rows":100000,"wall_elapsed_seconds":6.352428}
```

`/usr/bin/time -l` reported 447,184,896 bytes maximum process RSS for the complete fake-provider test process. No latency pass/fail threshold is asserted.

The suite also contains a separate 100,000-row local stream/fingerprint test, a 10,001-row two-page scan, a 2,501-row `[1000, 1000, 501]` count-batching test, and a forced-small-cap encoded-byte batching test.

## Validation procedure and exact results

All commands ran from the task worktree after the repair:

- `git diff --check` — pass, no output.
- `uv sync --locked` — pass; 157 packages resolved, 106 checked.
- `uv lock --check` — pass; 157 packages resolved.
- `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/validate_ranking_contract.py` — pass; 13 datasets, 369 judgments, dataset bundle `5a79f58aaca87a2d4f7cbec68fdcfbbcbf041131821587f8aba74a86daca99d9`.
- `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/c6_syntax_forecast.py validate` — pass; forecast `d5199276c19ae89779287eaa90824ce1e1cc684a3f060899f02f65d976016243`.
- Focused evidence/applied-state/apply/remote-catalog/release/Command Center suite — 237 tests passed in 27.156s.
- Full `unittest discover` — 848 tests passed in 103.760s; 39 skipped. Existing expected warning/argparse/log lines appeared; no failure.
- `uv build --out-dir dist` — pass; wheel and sdist built.
- Package inspection — wheel 72 files, sdist 168 files; wheel contains all three evidence modules; sdist contains evidence modules, `docs/evidence-snapshots.md`, and all three focused test modules; no `state.duckdb`, `snapshot.json`, `evidence.duckdb`, or `node_modules` packaged.
- Provider-blocked ordinary/evidence imports — pass; `turbopuffer` absent from `sys.modules`.
- `buoy evidence estimate|snapshot|verify --help` — pass without credentials/provider import.
- Restore `rm -rf dist web/node_modules; uv sync --locked; uv lock --check` — pass.
- Final `git diff --check` — pass.

Frontend source was unchanged, so packaged assets were not rebuilt and `npm ci/test/build` was not run, following the explicit unchanged-frontend boundary.

## What this supports

This supports that full evidence remains in turbopuffer branches, only bounded membership/summary metadata is duplicated remotely, only `snapshot.json` persists locally, source namespaces and branches are never written by ledger/catalog paths, verification is independent of current local state, provider model timestamps serialize, limits and sharding fail before branches, identical completed snapshots reuse deterministic identities with factual current activity, and internal evidence namespaces are excluded from routing, discovery, local inventory, and combined Command Center source rows.

## Limits

- No live smoke ran; ambient credentials were not used. Provider permissions, billing-account behavior, and production latency remain unobserved.
- Approximate logical bytes are provider metadata, not exact storage or price.
- Branch immutability is detected, not access-controlled against external writers.
- Strong consistency has the documented provider operational limits.
- The authoritative catalog is not cryptographically signed against a privileged coherent rewrite.
- Conservative failure handling reports and retains incomplete internals rather than risking unsafe cross-host deletion; no deletion/GC command exists.
- The 100,000-row RSS includes in-process fake remote storage and is not a provider-backed client-only measurement.
- No push, merge, PR, publish, release, source apply, source namespace write, LLM call, graph extraction, taxonomy/ontology creation, or UI build occurred.
