Status: active
Created: 2026-07-29
Updated: 2026-07-29

# Remote Evidence Snapshots

## Purpose and scope

Phase 3A freezes the exact evidence membership of one to 64 explicitly selected, already-applied Buoy turbopuffer namespaces without copying their full corpus to the operator machine. A snapshot consists of one immutable-by-Buoy turbopuffer branch per source namespace, one compact remote membership ledger, one completed row in a fixed region-local evidence catalog, and one bounded local `snapshot.json` manifest.

This specification supersedes any design that stores the full evidence corpus in local DuckDB, JSONL, Markdown, a duplicate evidence-content namespace, or the ledger. It does not implement concept/mention extraction, assertions, edges, graph storage, graph UI, taxonomy, ontology, scheduling, retention, deletion, garbage collection, sharded-copy fallback, cross-region copy, source mutation, plan, or apply behavior.

## Authority and provider contract

The implementation MUST use the installed official turbopuffer Python SDK. The implementation baseline is SDK 2.4.0. It MUST use `Namespace.branch_from(source_namespace=...)`, metadata fields `approx_logical_bytes`, `approx_row_count`, `created_at`, `branching.parent`, and `sharding.num_shards`, strong queries, and ordered export pagination (`rank_by=("id", "asc")`, an advancing `id > last_id` filter, and `limit=10_000`). Branch drift detection MUST use official `last_write_at` when exposed and SDK 2.4.0's documented `updated_at` last-modified-by-write value as the conservative canonical fallback; a branch with neither usable marker MUST fail closed. Namespace IDs MUST satisfy `[A-Za-z0-9-_.]{1,128}` and document IDs MUST be at most 64 bytes. Writes MUST be bounded well below the 512 MiB payload limit.

Official current documentation states that branching is unsupported for sharded namespaces. A selected namespace with `sharding` metadata MUST fail before branch creation. No fallback copy is permitted.

## Explicit selection and eligibility

The operator MUST provide at least one and at most 64 namespace IDs. Selection MUST reject duplicates, wildcards, prefixes, automatic/all routing, invalid IDs, the routing-catalog namespace, and every ID beginning `buoy-evidence-`. Processing order MUST be deterministic lexical order.

Every source MUST have exactly one unambiguous local applied-state identity, a non-first-apply state containing at least one ledger row, an eligible compatible remote routing card, matching namespace/site/embedding/region/schema expectations, and branch-capable remote metadata. A zero-row state MUST fail before remote creation because turbopuffer cannot create an absent schema-only namespace and a sentinel would violate the exact ledger contract. All sources MUST share one region.

## Apply locking and local streaming

Snapshot creation MUST acquire the existing namespace apply lock for every source in sorted order and hold all locks through state fingerprinting, branch creation/reconciliation, ledger publication/verification, and catalog finalization. Lock contention MUST fail before remote creation. Locks MUST always release. Unrelated namespaces remain independent. Documentation MUST warn that snapshots can temporarily block apply on selected namespaces.

Applied state MUST be read through a read-only, exact-schema, descriptor-bound/no-follow streaming reader ordered by `row_id`, using bounded `fetchmany()` batches with pre/post replacement checks and no checkpoint or mutation. It exposes only row ID, canonical URL, page/chunk/embedding-text hashes, plan ID, applied timestamp, and status. The complete ledger MUST NOT be materialized as `AppliedStateRow` objects or another unbounded collection.

## Identity and remote names

Snapshot identity MUST be computed before remote creation as `evidence_<first-16-hex>` from a stable canonical hash of schema version, sorted source namespaces, common region, each ordered local logical state fingerprint, site ID, last plan/apply IDs, routing-card revision, and compatible schema/embedding contract. It MUST exclude time, provider request/latency/approximate metrics, paths, and credentials.

Names MUST be deterministic and remain within 128 bytes:

- branch: `buoy-evidence-branch-<snapshot-short-id>-<source-hash>`
- ledger: `buoy-evidence-ledger-<snapshot-short-id>`
- fixed catalog: `buoy-evidence-catalog-v1`

Evidence-internal namespaces MUST never enter ordinary retrieval routing or be presented as user source content.

## Estimate

`buoy evidence estimate --namespace ...` MUST validate local state and routing compatibility, read remote metadata, enforce limits, and report per-source and total approximate rows/logical bytes. It MUST make no remote write, branch, ledger, catalog row, or local artifact and MUST download no content.

Defaults are `--maximum-rows 1000000` and `--maximum-remote-logical-bytes 5368709120`. Exact local ledger rows and summed approximate source logical bytes MUST fail closed before branches when over limit. Limits never truncate; operators may explicitly increase them. Output MUST state that logical bytes are approximate and branch storage may be billed by full logical namespace size.

## Snapshot lifecycle

Snapshot creation MUST execute in this order:

1. Validate explicit inputs, local state identities, routing compatibility, region, and limits without writes.
2. Acquire sorted apply locks.
3. Stream local rows to compute exact total/status counts and ordered fingerprints.
4. Read and validate source metadata, including no sharding, common region, and budgets.
5. Derive deterministic identity and names.
6. Check the evidence catalog for the exact ID. A matching complete row is remotely verified and reused; a conflicting row fails closed.
7. Create or safely reuse one deterministic branch per source. A reused incomplete branch must have the exact parent and reconcile fully; an unknown/wrong-parent collision fails.
8. Stream local rows again into bounded, idempotent full-row ledger upserts with explicit schema and exact affected-count checks. An identical retry MAY reuse an existing deterministic ledger only after exact schema, snapshot/source/branch/document identity, complete row/hash/status-count, locked local-fingerprint, and branch reconciliation; partial or mismatched ledgers MUST fail without overwrite or deletion.
9. Reconcile each branch through one ordered, bounded strong scan requesting only `canonical_url`, `page_hash`, `chunk_hash`, `embedding_text_hash`, `plan_id`, and `applied_at`; never vectors, content, title, tags, or unused metadata.
10. Strong-scan and verify the ledger, exact counts, status counts, ledger logical hash, and snapshot logical hash.
11. Re-read branch metadata and fail if parent or the canonical write marker (`last_write_at`, otherwise SDK `updated_at`) changed. Write the complete evidence-catalog row last with insert-if-absent/idempotent semantics.
12. Atomically write the bounded local manifest after remote completion.

Buoy MUST never write to a branch after `branch_from`. The operational contract is: **Buoy treats evidence branches as immutable and detects later writes through metadata and complete reconciliation.** External writes are not technically prevented.

## Ledger contract

The ledger contains one row per local applied-state row and no vectors/content/title. Its deterministic document ID is derived from snapshot ID, source namespace, and source row ID and remains within 64 bytes. Exact attributes are:

`snapshot_id`, `source_namespace`, `branch_namespace`, `source_row_id`, `site_id`, `status`, `canonical_url`, `page_hash`, `chunk_hash`, `embedding_text_hash`, `plan_id`, `applied_at`, `ordinal`.

Allowed statuses are `active`, `retained_stale`, and `deleted`. Only `status`, `source_namespace`, and `branch_namespace` (plus ID) need remain filterable; large identity/provenance strings MUST be explicitly non-filterable when supported.

## Reconciliation

For `active` and `retained_stale`, the branch MUST contain the exact same ID and matching URL, hashes, plan provenance, and applied timestamp where present. `retained_stale` remains in the ledger but is not active graph evidence. A `deleted` row MUST be absent from the branch but remain in the ledger. Missing expected rows, unexpected branch rows, deleted rows present remotely, mismatches, duplicate/out-of-order IDs, and non-advancing pages MUST fail with sanitized namespace/category/safe-row-ID diagnostics only.

## Evidence catalog

The fixed catalog stores one row per completed snapshot with safe metadata: snapshot/schema/state/time/region, source and branch namespaces, ledger, source/status counts, source-state hashes, last plan/apply IDs, card revisions, approximate logical bytes, exact ledger count, branch parent/created/last-write/approximate metrics, snapshot logical hash, and manifest hash. Visible state MUST be `complete`. No complete row may be written before all branches and ledger pass verification. No secrets, environment values, local roots/paths, clients, or raw responses may be serialized.

## Local artifact

The only persistent local snapshot artifact is `<out-root>/<snapshot-id>/snapshot.json`, defaulting under `artifacts/evidence-snapshots`. It contains bounded summary metadata, counts, namespace IDs, logical hash, manifest hash, and activity—never row membership or content. It MUST be at most 256 KiB and written atomically. Manifest failure after remote completion does not invalidate the remote snapshot; an identical invocation can reconstruct it from the catalog.

## Verification

`buoy evidence verify --snapshot-id ...` requires credentials and remote reads, performs no writes, and MUST NOT depend on current local applied state or original source databases. It reads the complete catalog row, optionally validates a present/supplied manifest, validates every branch parent and recorded metadata, validates ledger schema/rows/hash/counts, ordered-merges every branch against the ledger, recomputes logical hashes/counts, and rejects later writes or any drift. A local-manifest-only check is not complete verification.

## Cleanup

Before catalog finalization, best-effort cleanup may delete only namespaces proven absent before this invocation, created by it, exactly named as expected, identity/parent validated, and unreferenced by a completed catalog row. Source, preexisting, unknown, routing-catalog, and completed resources MUST never be deleted. Cleanup failure MUST report leaked internal IDs and state that no valid snapshot finalized. No general deletion/GC command exists.

## Activity and performance

Estimate, snapshot, and verify MUST report the requested credential/API/source-write/internal-write/local-corpus/local-manifest flags and provider billing/query metrics only when actually exposed—never invented. Snapshot additionally reports branch create/reuse and ledger/catalog write counts.

Working memory MUST remain bounded by one remote page, one local batch, one ledger write batch, and hashing state. A 100,000-row fake fixture MUST demonstrate bounded `fetchmany`, 10,000-row remote pages, bounded ledger writes, no content/vector request, exact hashes/counts, only a bounded manifest locally, and measured peak RSS/local bytes/call counts/reconciliation elapsed time without brittle latency thresholds.

## Namespace visibility and roadmap

Automatic routing and ordinary namespace discovery/Command Center tables MUST exclude `buoy-evidence-` namespaces. Remote refresh may report bounded `internal_evidence_namespace_count`. No graph UI is added.

Roadmap status:

- Phase 3A — remote evidence snapshots: implemented by this specification
- Phase 3B — autonomous local concepts, mentions, and lightweight taxonomy: implemented
- Phase 3C — evidence-backed typed assertions: future
- Phase 4 — graph review and visualization: future
- Phase 5 — incremental semantic maintenance: future

## Acceptance criteria

All behaviors above are covered by provider-free fake-client tests, including estimate validation/no-write, deterministic identity, branch safety/drift, ledger strictness/batches/mutation, ordered reconciliation edge cases and 10,001-row paging, multi-source cleanup/finalization/lock release, verification without local state/zero writes, 100,000-row bounded processing, import laziness/provider inertness, CLI JSON/text behavior, namespace filtering, documentation, and package contents. Full repository validation and distribution builds MUST pass. Live provider smoke MUST remain opt-in and MUST NOT run for this phase without explicit separate authorization.
