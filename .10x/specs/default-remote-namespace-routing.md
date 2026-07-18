Status: active
Created: 2026-07-18
Updated: 2026-07-18

# Default Remote Namespace Routing

## Purpose and scope

Define default automatic retrieval using live Turbopuffer namespace discovery intersected with remote cards from `.10x/specs/remote-turbopuffer-routing-catalog.md`. Preserve explicit CLI namespace retrieval as the sole manual bypass.

## Activation

- Without CLI `--namespace`, `buoy retrieve QUERY` MUST automatically route remotely whether or not compatibility flag `--auto-route` is present.
- Repeatable CLI `--namespace` MUST bypass namespace listing, remote catalog, and routing-model work; explicit dry preview remains credential-free and local.
- `TURBOPUFFER_NAMESPACE` MUST NOT be read, selected, or warned about by retrieve.
- `--auto-route` remains accepted and is contradictory with CLI namespaces.
- `--route-top-k` (default 3, maximum 10) is valid in automatic mode without the flag and invalid with explicit namespaces.
- Local retrieve `--catalog` and `BUOY_CATALOG_PATH` no longer exist. The remote catalog namespace is fixed, not configurable.
- No `--no-auto-route` exists.

Existing validation precedence remains: live/dry-plan conflict first; contradictory explicit/automatic options next; explicit namespace-list validation before explicit query; automatic whitespace-only query before configuration/credentials/API work.

## Automatic read sequence

After argument and non-empty-query validation, automatic dry or live retrieval MUST:

1. resolve region/model/precision and read `TURBOPUFFER_API_KEY`;
2. list all live namespaces in that region and read/paginate/validate remote cards;
3. intersect and classify missing/stale targets;
4. apply enabled/region/model/precision/dimension/schema/ranking eligibility before relevance;
5. load the exact cached pinned routing model locally;
6. execute the established lexical, semantic, and equal-weight RRF algorithm using persisted card vectors;
7. deterministically truncate to top three or `--route-top-k` before content retrieval.

No remote namespace discovery or remote catalog call may occur before credential lookup, and no routing-model load may occur before the remote catalog has produced at least one valid compatible card. No read path may mutate or repair remote/local state.

## Ranking algorithm retained

Canonical descriptor normalization, exact phrase lexical scoring, BGE query prefix/model/revision, normalized dot-product semantic ranking, namespace tie-breaks, imported `RRF_K=60`, and top-k truncation remain byte-for-byte compatible where practical. Namespace IDs never become fallback descriptors.

## Preview

Automatic retrieval without `--live` is a read-only remote preview, not a local dry run. It MUST:

- require credentials and list/query Turbopuffer;
- make zero writes and zero content-namespace queries;
- show remote catalog namespace, snapshot revision, live/card/eligible counts, missing/stale/incompatible counts, selected route, ranking components, and per-namespace retrieval plans;
- report `credentials_required=true`, read-only API calls occurred, and content retrieval did not occur;
- never print vectors or credentials.

Explicit CLI namespace preview retains the existing local, credential-free retrieval plan and output shape.

## Live retrieval

Automatic `--live` MUST use the exact route produced by the same remote read/routing sequence, then hand ordered per-card configurations to existing `MultiNamespaceRetriever` and downstream cross-namespace RRF. Content query embedding remains once per live retrieval, namespace calls remain sequential/all-or-nothing, and final top-k/namespace-qualified identity remain unchanged.

A failure during listing/catalog/routing emits no content result. A failure in any selected content namespace emits no partial result. No fallback to all live namespaces, IDs, stale cards, environment namespace, or explicit mode is allowed.

## Output compatibility

Routed output always uses the multi-namespace shape, even for one selected card. Replace local catalog path fields with:

- `catalog_namespace=buoy-routing-catalog-v1`;
- region and remote snapshot revision;
- read-only namespace-list/catalog-query call counts or booleans;
- live/card/missing/stale/eligible/excluded counts.

Existing selected-card score/rank components and retrieval plans remain. Explicit namespace outputs remain compatible.

## Acceptance scenarios

- From two unrelated directories with the same key/region, automatic preview discovers the same live/card intersection and route without local catalog files.
- Four live namespaces, two valid cards, and no stale cards route only the two carded targets while reporting two missing cards.
- Zero live valid cards fail before routing model or content query.
- Whitespace query fails before credentials/API/model.
- Missing key fails before client construction.
- Missing list permission, missing catalog namespace, corrupt schema/card, pagination loop, and API errors fail closed.
- Explicit CLI namespace dry preview makes no credential/API/catalog/model call.
- Compatibility `--auto-route` produces the same result as default automatic mode.
- Automatic preview makes read-only list/catalog calls and no writes/content queries.
- Automatic live route order and downstream retrieval/RRF remain unchanged.

## Explicit exclusions

Offline automatic preview, local/disk card cache, remote card repair during read, ID-only fallback, all-visible fan-out, cross-region discovery, concurrent content retrieval, ACLs, taxonomy, graph, telemetry, online learning, or query persistence.
