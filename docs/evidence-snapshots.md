# Remote evidence snapshots

Graph Phase 3A freezes applied Buoy evidence without making a second full copy on the laptop. Full content and vectors remain in turbopuffer.

```text
applied source namespace A ──branch──> immutable-by-Buoy evidence branch A
applied source namespace B ──branch──> immutable-by-Buoy evidence branch B
                                      + compact remote membership ledger
                                      + one completed remote catalog row
                                      + one small local snapshot.json
```

Phase 3A itself creates no concept, mention, assertion, edge, taxonomy, ontology, graph database, or graph UI. A completed snapshot is the immutable input to implemented Phase 3B [autonomous local semantics](semantics.md); only active ledger rows are eligible there.

## Estimate first

Branch storage may be billed from the full logical size of every branched source namespace even though branch creation is copy-on-write. Always inspect the estimate before creating a snapshot:

```bash
uv run buoy evidence estimate \
  --namespace docs-one \
  --namespace calls-one
```

Estimate requires turbopuffer credentials because it reads the routing catalog and namespace metadata. It reports exact local ledger counts plus approximate remote row and logical-byte metadata. It creates no branch, remote row, or local artifact and downloads no content.

The fail-closed defaults are:

- `--maximum-rows 1000000`
- `--maximum-remote-logical-bytes 5368709120` (5 GiB)

Neither limit truncates. Increase a limit explicitly only after reviewing the estimate. Logical bytes are approximate provider metadata, not a price calculation.

## Create

```bash
uv run buoy evidence snapshot \
  --namespace docs-one \
  --namespace calls-one
```

Selection is explicit: provide one to 64 unique, valid namespace IDs. There is no wildcard, prefix, automatic-routing, or all-namespaces mode. Routing-catalog and `buoy-evidence-` internal namespaces are rejected.

Each source must have exactly one local applied-state database with at least one membership row, a completed non-first apply, a matching enabled routing card, a compatible region/embedding/schema contract, and branch-capable turbopuffer metadata. Zero-row state fails before remote creation because turbopuffer cannot create an absent schema-only ledger namespace without adding a contract-breaking sentinel. All selected sources must share one region. Sharded namespaces fail before any branch because current turbopuffer branching does not support them; Buoy never falls back to a full copy.

Buoy acquires every selected namespace's existing apply lock in sorted order and holds the locks through fingerprinting, branch reconciliation, ledger verification, and catalog finalization. A snapshot can therefore temporarily block apply for selected namespaces. Unrelated namespace applies are unaffected, and every lock releases on success or failure.

### Remote layout

A deterministic snapshot creates or safely reuses:

- `buoy-evidence-branch-<snapshot-short-id>-<source-hash>` per source;
- `buoy-evidence-ledger-<snapshot-short-id>` once;
- one `complete` row in region-local `buoy-evidence-catalog-v1`.

Branches retain the source content and vectors. Buoy never patches or upserts an evidence branch after `branch_from`. This is an operational contract, not provider access control:

> Buoy treats evidence branches as immutable and detects later writes through metadata and complete reconciliation.

The compact ledger has one identity/provenance row for every local applied-state row. It contains `active`, `retained_stale`, and `deleted` membership, URL and hashes, plan/apply provenance, source/branch identity, and ordinal. It contains no content, title, vector, credential, provider response, local path, or connection setting. Active rows are future graph evidence. Retained-stale rows stay reproducible but are not active evidence. Deleted rows remain in the ledger and must be absent from the branch.

Creation scans every branch in strong, deterministic ID order while requesting only URL, hash, plan, and applied-time reconciliation attributes. Missing active/stale rows, present deleted rows, extra rows, mismatches, duplicate/out-of-order pages, and branch metadata changes fail. Write drift uses turbopuffer's `last_write_at` when available and SDK 2.4.0's documented `updated_at` as a conservative fallback; if neither marker is available, snapshot creation and verification fail closed. The remote ledger is then scanned and hashed. The completed catalog row is written last and is the authoritative validity marker.

An identical retry after a failure may reuse a deterministic incomplete branch and ledger only when their parent, schema, identity, every row, status count, hashes, locked local fingerprint, and branch reconciliation match exactly. Partial or altered ledgers are never patched, overwritten, or deleted; they fail as reported collisions.

Before completion, failures report every definitely or possibly created internal namespace. Buoy does not automatically delete these deterministic names in Phase 3A: without a remote ownership lease, another host could begin reusing or complete the same snapshot between a catalog check and deletion. Preserving and reporting an incomplete internal namespace is safer than deleting concurrent, preexisting, unknown, routing-catalog, source, or completed evidence. This phase deliberately has no snapshot delete, branch delete, retention, or garbage-collection command.

### Local artifact

The only local snapshot artifact is:

```text
artifacts/evidence-snapshots/<snapshot-id>/snapshot.json
```

It is atomically written after remote completion and capped at 256 KiB. It stores IDs, counts, approximate bytes, logical hash, and activity—never membership arrays or content. There is no `evidence.duckdb`, evidence JSONL, pages directory, manifest database, or content cache. A local write failure cannot invalidate a completed remote snapshot; an identical command can recreate the manifest.

Snapshot identity is deterministic from sorted source identities, locked applied-state fingerprints, routing-card revisions, region, and embedding/schema compatibility. Creation time, provider metrics, output paths, and credentials are excluded. Repeating an unchanged request produces the same snapshot/branch/ledger IDs. A matching completed snapshot is fully verified and reused rather than duplicated.

Snapshots are explicit operator actions. Nothing schedules them automatically.

## Verify

```bash
uv run buoy evidence verify --snapshot-id evidence_<id>
```

Complete verification requires credentials and remote reads. It does not use current applied state or original sources. It reads the completed catalog row, checks an available or explicitly supplied local manifest, validates ledger schema/rows/hash/counts, checks every branch parent and recorded metadata, and ordered-merges every branch against its remote ledger membership. Later writes, missing/extra/mutated rows, ledger mutation, catalog hash drift, and manifest mismatch fail. Verification performs no remote or local mutation.

A local-manifest-only check is not complete evidence verification because full evidence lives remotely.

## Activity reporting

All commands report credential/API/source-write/internal-write/local-corpus/local-manifest activity. Provider logical-byte billing counters are reported only when the SDK response exposes them; Buoy does not invent metrics. Snapshot output also reports branch create/reuse counts and ledger/catalog writes. Remote query verification is billable provider work even though it performs no mutation.

## Roadmap

- **Phase 3A — remote evidence snapshots: implemented**
- **Phase 3B — autonomous local concepts, mentions, and taxonomy: implemented**
- **Phase 3C — evidence-backed typed assertions: future**
- **Phase 4 — graph review and visualization: future**
- **Phase 5 — incremental semantic maintenance: future**

Phase 3B is a lightweight evidence-linked taxonomy, not a complete ontology. No arbitrary assertions or graph visualization currently exists.
