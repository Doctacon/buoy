Status: superseded
Created: 2026-07-18
Updated: 2026-07-18

# Remote Routing Catalog CLI

## Purpose and scope

Define the public authenticated catalog lifecycle after atomic cutover. All commands operate on exact `buoy-routing-catalog-v1` in the resolved region. No local catalog authority/path remains.

## Common configuration and output

Every command accepts `--region REGION` with precedence CLI, non-empty `TURBOPUFFER_REGION`, then existing default. It reads `TURBOPUFFER_API_KEY` from process environment. `BUOY_CATALOG_PATH` is not read or warned about. `--catalog` is removed and rejected by argument parsing.

All commands use remote stable read/mutation protocols. Expected validation, permission, not-found, conflict, or API failures return exit 2 with stderr diagnostics; unexpected internal failures retain existing nonzero behavior. JSON stdout remains clean.

Every JSON payload includes `command`, `catalog_namespace`, `region`, stable `snapshot_revision`, request/page/billing summaries when available, and no credentials. Vectors appear only under explicit include option. Text output names remote authority and classifications.

## Read commands

### `buoy catalog list [SEARCH] [--all] [--json] [--region REGION]`

- lists enabled live carded targets by default;
- `--all` also returns disabled and stale cards but never synthesizes missing-card rows;
- SEARCH uses canonical matching over namespace/title/summary/aliases/tags;
- reports listed/control-plane/content-live/card/stale/missing/disabled/incompatible/eligible counts;
- sorted by target namespace.

### `buoy catalog show NAMESPACE [--include-vector] [--json] [--region REGION]`

- requires exact card target, even if stale;
- validates live/stale status;
- redacts vector by default; explicit include returns vector only in JSON;
- fails when absent without ID inference.

## Manual mutation

### `upsert`

`buoy catalog upsert NAMESPACE` retains complete source/semantic/retrieval options from the established CLI, uses resolved `--region` both for API/card region, optional repeated alias/tag, and optional `--disabled`. It builds/reuses the local cached routing vector, sets manual origin, and performs conditional create/update. Existing created time/lineage are preserved unless the complete validated input explicitly and lawfully updates system fields. Namespace must be live; reserved target forbidden.

### `enable` / `disable`

`buoy catalog enable|disable NAMESPACE [--json] [--region]` strongly reads exact revision, is idempotent, and conditionally changes only enabled/timestamps/revision while preserving vector/card fields.

### `remove`

`buoy catalog remove NAMESPACE [--approve] [--json] [--region]` is preview-only without approval. Approved remove conditionally deletes only the remote card at the previewed/current exact revision, strongly proves absence, and states that target content namespace/rows/applied state are untouched. Revision drift conflicts.

## Legacy migration entrypoint

`buoy catalog migrate-local --source PATH [--approve] [--json] [--region REGION]`

- is the exact operator entrypoint for schema-v1 local catalog import;
- source must normalize to a regular non-symlink file; mutation never deletes/changes it;
- validates complete document/card hashes/vectors and requires every card region equal resolved region;
- preview requires credentials and performs namespace list plus remote catalog state/schema reads, then reports absent/empty/partial/exact/conflicting/extra state and intended affected IDs;
- without `--approve`, performs zero writes and succeeds only when state is migratable/idempotent;
- with approval, creates exact schema if absent and follows the remote migration-state rules with `return_affected_ids` validation;
- final two-pass proof reports exact rows/revisions and live intersection;
- conflicting schema/card/extra row, unsupported source, drift, or unexpected affected IDs fail without cleanup/deletion.

The cutover ticket binds this command to the exact two-card source and authorized writes. The command remains available for explicit legacy migration but never restores local authority.

## Apply recovery commands

### `reconcile`

`buoy catalog reconcile --pending PATH [--rebase | --accept-remote] [--approve] [--expected-remote-revision REV] [--json] [--region]`

- ordinary reconcile requires no approval and attempts original idempotent conditional commit;
- `--rebase` and `--accept-remote` are mutually exclusive and require `--approve`;
- `--accept-remote` additionally requires exact `--expected-remote-revision` matching both stable reads immediately before pending removal; it displays pending/remote plan/apply/revision identities and explicitly records operator acceptance. It never infers causal ordering from timestamps;
- outputs action `committed`, `already_committed`, `rebased`, `accepted_remote`, or conflict;
- all paths obey trusted pending/ledger/inode/revision rules and never replay content.

### `abandon-pending`

`buoy catalog abandon-pending --pending PATH [--approve] [--json] [--region]` is preview-only without approval, API-free where remote proof is unnecessary, and removes only genuinely unconfirmed/non-promotable revalidated state. It cannot remove confirmed/promotable pending.

## Exact first-apply manual race

When pending base is absent and a manual card appears before commit, approved rebase is allowed only if the new card is valid/manual, target/source/retrieval contract exactly equals the pending verified candidate, lineage remains null, and differences are limited to manual semantics/enabled plus derived fields. It preserves those fields and conditionally commits pending apply/system lineage. Otherwise conflict remains for explicit accept-remote or external correction.

## Security and side effects

Read and permission matrix follows the remote catalog spec. Cards must contain no secrets. Mutation outputs include exact affected IDs/revisions, never vectors by default. No command deletes or writes content namespaces. All public behavior changes land atomically with apply/retrieval cutover.

## Acceptance scenarios

Complete parser/help/JSON/text/error matrices; path/env removal; read classifications; conditional mutation races; migration absent/partial/exact/conflict; remove preview/revision conflict; ordinary/rebase/first-apply-race/accept-remote/abandon recovery; redaction/credential/permission/billing behavior are tested with injected clients.
