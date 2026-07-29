Status: done
Created: 2026-07-29
Updated: 2026-07-29

# Turbopuffer Evidence Snapshot API

## Question

What exact official turbopuffer SDK/API contract bounds branch-backed evidence snapshots?

## Sources and methods

Inspected official documentation on 2026-07-29: https://turbopuffer.com/docs/branching, `/metadata`, `/query`, `/export`, `/limits`, `/write`, `/delete-namespace`, `/sharding`, and `/guarantees`. Inspected the installed SDK generated signatures/source through `uv run python`; `uv.lock` resolves `turbopuffer==2.4.0`.

## Findings

- SDK 2.4.0 exposes `client.namespace(destination).branch_from(source_namespace=source)` and equivalent `write(branch_from_namespace={"source_namespace": source})`.
- `metadata()` exposes `approx_logical_bytes`, `approx_row_count`, `created_at`, `last_write_at`, `updated_at`, optional `branching.parent`, optional `sharding.num_shards`, index state, and schema. Metadata reads are billed as zero-row queries.
- Official export pagination uses `query(rank_by=("id", "asc"), limit=10_000, filters=("id", "Gt", last_id))`. Strong consistency is the default; this work passes `consistency={"level": "strong"}` explicitly.
- Namespace names match `[A-Za-z0-9-_.]{1,128}`. IDs may be unsigned 64-bit integers, UUIDs, or strings up to 64 bytes. Attribute values are limited to 8 MiB, filterable values to 4 KiB, documents to 64 MiB, and write payloads to 512 MiB.
- Explicit schemas can mark attributes `filterable: false`, reducing indexing/billing; ID remains the ordering key.
- Conditional writes use `upsert_condition`, including insert-if-absent `("id", "Eq", None)`, and return actual affected counts. There is no general transaction.
- `delete_all()` deletes a namespace irreversibly. Cleanup therefore needs strict provenance/name/parent/identity guards.
- Official sharding documentation says branching is not supported for sharded namespaces. Metadata `sharding` presence is the preflight rejection signal.
- Branches are instant independent copy-on-write clones, not access-controlled immutable objects. Later branch writes must be detected through metadata and full reconciliation.
- Approximate logical bytes and row counts are coarse metadata and may lag when backpressure is disabled. They are suitable for conservative estimates, not exact identity.

## Conclusions

Use SDK 2.4.0 exact methods, explicit strong ordered 10,000-row scans, metadata-based sharding rejection and budget estimates, deterministic bounded IDs/names, conditional catalog publication, and guarded `delete_all()` only for current-invocation incomplete resources. Do not claim provider-enforced branch immutability or exact byte estimates.

## Limits

No live provider call was made. SDK shapes and official documentation were inspected; organization-specific permissions and server behavior remain covered only by fakes unless a separately authorized smoke test runs.
