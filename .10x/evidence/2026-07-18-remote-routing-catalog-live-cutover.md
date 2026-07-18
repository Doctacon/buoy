Status: recorded
Created: 2026-07-18
Updated: 2026-07-18
Relates-To: .10x/tickets/done/2026-07-18-atomic-remote-catalog-cutover.md, .10x/tickets/done/2026-07-18-remote-semantic-routing-plan.md

# Remote Routing Catalog Live Cutover

## What was observed

Under an explicit mutation freeze, Buoy created `buoy-routing-catalog-v1` in `gcp-us-central1`, seeded exactly the validated Dagster Benchmark and Oscilar cards, integrated PR #32 as `eba8145bb12eb7a0749a96ee4088938060a9fb12`, verified remote routing from two directories, and deleted only the exact bound local `.buoy/catalog.json`.

Final stable state:

- listed namespaces: 5;
- control plane: 1 (`buoy-routing-catalog-v1`);
- content live: 4;
- cards/eligible: 2 (`site-dagster-io-benchmark-v1`, `site-oscilar-com-v1`);
- missing-card exclusions: 2 (`site-dagster-io-v1`, `site-www-thistle-co-v1`);
- disabled/incompatible/stale: 0;
- snapshot revision: `cd77c5ce97dd7f8df82b191b9e534d0c5535c7fa5224ef81edcbacb7732b01e6`;
- Dagster card revision: `6b063015a1864c449a31df15f61201903c631a63011801f06163e2d47292ba9c`;
- Oscilar card revision: `4213e01252e99a8b92829fd021933525666bd259a834191216d979739f456ff1`.

## Procedure and side effects

1. Revalidated source as regular non-symlink mode `0600`, size `26063`, SHA-256 `aafe3e6752671badef9da1aa0150903056bb856666289c271e0a67cef7a5ab1a`; lock and pending paths absent.
2. Read-only migration preview listed four content namespaces and classified catalog absent.
3. The first approved migration issued one conditional catalog write request containing exact schema and two rows. Both rows were created. Post-write verification failed on live SDK normalization differences; no content namespace was queried or mutated.
4. Catalog-only strong reads established the precise provider behavior:
   - absent nullable extras are omitted;
   - returned vector metadata omits `filterable:false` while preserving exact `[384]f32`/cosine ANN;
   - float vector decimal rendering differs by at most `1.47e-8`, while IEEE-754 f32 bytes and stored hashes are exact.
5. Each narrow normalization repair passed focused independent review and fresh hosted Python 3.11/3.13/build checks before retry. The next two retries failed before writes on schema/vector validation. No additional remote write occurred.
6. Final read-only preview and approved idempotent verification both classified exact. Approved verification reported `affected_ids=[]` and `write_requests=0`; 12 read requests, including six namespace-list, two metadata, and four catalog-page requests, completed.
7. Automatic branch previews from the worktree and `/tmp` were byte-identical. Explicit namespace preview without credentials reported `turbopuffer_api_calls=false`. Apply preflight without credentials/API reported `remote_catalog_state=unknown_until_approved`.
8. PR #32 hosted checks passed and a dedicated integration session squash-merged it as `eba8145bb12eb7a0749a96ee4088938060a9fb12`.
9. Integrated canonical and `/tmp` previews, catalog list, explicit preview, and local apply preflight matched branch evidence.
10. Through an open `.buoy` directory descriptor and `O_NOFOLLOW` source descriptor, final deletion revalidated device/inode/size/mode/hash/catalog/card revisions and absent lock immediately before unlink. Only `catalog.json` was unlinked; lock/pending remained absent.
11. Post-deletion automatic previews from canonical `develop` and `/tmp` were byte-identical to pre-deletion output. Catalog list retained exact snapshot/counts; explicit preview remained API-free.
12. After all post-deletion checks passed, the mutation freeze was explicitly released. No catalog/apply mutation occurred between freeze declaration and release except the single authorized initial catalog schema/two-row batch.

## Billing and request limits

Read outputs reported two strong catalog page queries per stable pass, each with `billable_logical_bytes_queried=256000000` and `billable_logical_bytes_returned=4387`. No content retrieval or live eval was run. The only live write request was the initial conditional schema/two-row batch; all later migration verifications reported zero writes.

## What this supports

This supports remote catalog authority, deterministic live-list/card intersection, cross-directory behavior, exact two-card migration, missing-card exclusion, safe local deletion, and no-content-operation claims.

## Limits

This did not execute live content retrieval, content writes/deletes, apply approval, recovery conflict flows, cross-region routing, or extra-card mutations. Those remain covered by fakes/specifications rather than this cutover observation.

Provider audit logs were not inspected. The no-content-operation boundary is a parent/operator attestation supported by command scope, outputs, and final namespace state rather than provider-side audit evidence. No follow-up is opened: provider audit-log access was not a requirement, and introducing it would add unrelated control-plane scope. Live apply/recovery validation is also intentionally not opened as follow-up; it was explicitly excluded from cutover, has complete fake coverage, and will be exercised when a real approved apply is independently requested.
