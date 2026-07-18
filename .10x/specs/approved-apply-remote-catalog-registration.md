Status: active
Created: 2026-07-18
Updated: 2026-07-18

# Approved Apply Remote Catalog Registration

## Purpose and scope

Replace local JSON card commit with revision-bound remote card registration in `buoy-routing-catalog-v1` while preserving approved content-write ordering, manual semantics/enabled state, crash truthfulness, collision blocking, and recoverability.

## Lock and precompute order

Approved apply MUST retain one local namespace lock across the entire operation. Before credentials or remote work it MUST:

1. verify plan/artifacts/diff and current applied state;
2. derive and validate generated source/retrieval card fields;
3. compute the candidate semantic projection/vector using the cached pinned local model;
4. validate remote-catalog target namespace/region and deterministic card ID;
5. reject any pending collision.

Because manual/enabled state is remote, the final merged card cannot be bound until an authenticated read.

## Authenticated preparation

After local precompute and before content writes, apply MUST:

1. read credentials;
2. list/verify that the reserved catalog namespace exists and validate its schema;
3. fetch the exact existing card, if any;
4. preserve manual semantic fields and every existing enabled state;
5. bind the observed card revision or expected absence;
6. construct, hash, and atomically persist a local pending artifact containing the final card, expected revision/absence, target catalog namespace/region, plan/artifact/state identities, and intended content apply identity.

No content write may start if this phase fails. Remote card reads are allowed; remote card writes are not.

## Content and card commit sequence

With pending state durable and the namespace lock held:

1. execute the existing ordered depth-one content upsert/delete pipeline;
2. commit compact local applied state;
3. confirm pending state with exact apply identity/ledger;
4. conditionally upsert the remote card against expected revision/absence;
5. re-read and validate the committed card;
6. remove the exact validated pending artifact.

The remote card commit is idempotent for an identical card/apply identity. Zero affected rows under the condition is a concurrency conflict and leaves confirmed pending state for reconciliation.

## Failure truthfulness and replay

- Failure before any content write leaves unconfirmed pending state only when enough remote-bound intent exists; it blocks rerun until explicitly approved abandonment.
- Content failure leaves unconfirmed pending and must never claim card registration.
- Applied-state success followed by confirmation failure remains recoverable when ledger identity proves completion.
- Confirmed pending means content/state succeeded and automatic apply replay is forbidden.
- Remote card failure after state success reports partial success with `content_applied=true`, `catalog_updated=false`, exact pending path, observed conflict/error, and reconcile command.
- Card success followed by pending cleanup failure reports `catalog_updated=true`, exact card revision, `pending_cleanup=false`, and idempotent reconcile guidance.
- No failure may automatically repeat content writes or silently overwrite a newer remote card.

## Reconcile and abandonment

`buoy catalog reconcile --pending PATH` requires credentials/region, validates trusted pending path/payload/inode after namespace lock, proves confirmed state against applied ledger, and conditionally commits/revalidates the remote card. If the intended identical card is already present, it removes pending idempotently. A different newer revision is a conflict requiring explicit operator resolution; reconcile never overwrites it.

`abandon-pending` applies only to unconfirmed state, requires `--approve`, performs no remote mutation, and removes only the revalidated exact artifact. Confirmed state cannot be abandoned.

Local `--catalog` binding disappears; pending binds exact reserved namespace and region instead.

## CLI/output

Approved apply preview remains local/model-free where currently guaranteed. Approved execution reports remote catalog namespace, expected/committed card revisions, pending state, and remote read/write phases without vectors or credentials. Catalog preview reads/writes follow the remote catalog spec.

## Acceptance scenarios

- First apply precomputes locally, verifies remote absence, writes pending, applies content/state, conditionally creates card, verifies, and cleans up.
- Existing manual/disabled card remains manual/disabled while system fields/lineage refresh.
- Concurrent remote disable changes revision and causes apply card conflict rather than overwrite.
- Content succeeds but card write fails; rerun cannot repeat content and reconcile completes the card later.
- Card already committed but cleanup failed; reconcile verifies identical state and only removes pending.
- Missing credentials/catalog/schema/conflicting existing card fails before content writes.
- No local catalog JSON is read or written.

## Explicit exclusions

Remote distributed locks, automatic conflict merge after pending creation, content replay, remote namespace deletion, cross-region card writes, card inference from IDs, ACLs, telemetry, or live operations outside the separately approved migration.
