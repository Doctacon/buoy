Status: active
Created: 2026-07-18
Updated: 2026-07-18

# Atomic Remote Catalog Cutover

## Purpose and scope

Stage remote backend primitives without changing authority, then switch catalog CLI, approved apply, and automatic retrieval together only after reviewed remote seed state exists. Prevent local/remote split-brain and bind deletion to the exact canonical file.

## Two-phase rollout

### Phase 1: inert backend

The first child may integrate remote schema/serializer/read/write primitives and tests. It MUST NOT change public catalog CLI, apply, retrieval, help/docs, local catalog reads/writes, or create a live remote namespace.

### Phase 2: one authority cutover

One cutover child owns public catalog CLI, approved apply, automatic retrieval, live seed, integration, and local-file deletion. No intermediate public authority is merged.

## Mutation freeze

From live seed preflight until the cutover PR merges and post-merge verification completes:

- no `buoy catalog` mutation;
- no approved apply;
- no edits to `.buoy/catalog.json`;
- ordinary local-catalog retrieval MAY continue before merge because seed is byte-equivalent, but no card mutation may occur;
- any local catalog hash/revision drift, remote card drift, target namespace drift, or competing PR/ref change aborts cutover.

The freeze and release are explicitly reported.

## Exact local deletion binding

Canonical path: `/Users/crlough/Code/personal/turbo-search/.buoy/catalog.json`.

Expected pre-cutover identity:

- regular non-symlink file;
- size 26,063 bytes;
- SHA-256 `aafe3e6752671badef9da1aa0150903056bb856666289c271e0a67cef7a5ab1a`;
- catalog revision `cd77c5ce97dd7f8df82b191b9e534d0c5535c7fa5224ef81edcbacb7732b01e6`;
- Dagster card revision `6b063015a1864c449a31df15f61201903c631a63011801f06163e2d47292ba9c`;
- Oscilar card revision `4213e01252e99a8b92829fd021933525666bd259a834191216d979739f456ff1`.

Expected lock path: `/Users/crlough/Code/personal/turbo-search/.buoy/catalog.json.lock`; inspection found it absent. If present at cutover it MUST be a regular non-symlink file and acquired non-blocking before deletion. No catalog pending registration may exist. Any mismatch blocks deletion.

Delete neither `.buoy` nor any other state. If no lock exists, delete only the exact catalog after all post-merge remote validations. If a lock exists, hold it while revalidating and deleting catalog/lock.

## Seed and cutover sequence

1. Complete implementation and independent review on task branch; required PR checks pass.
2. Enter freeze and revalidate exact local identity, exact remote main/develop/PR head, four content-live namespaces, and reserved namespace state.
3. Seed according to remote catalog migration preconditions. Final strong proof: exactly two intended cards, no extras/conflicts; five listed total including control plane; two missing-card content targets.
4. With branch code, perform authenticated read-only automatic previews from canonical checkout and unrelated temporary directory; both select the same route/intersection. Make no content query.
5. Revalidate local hash/revision and remote stable card set immediately before integration.
6. Integrate the exact reviewed PR into develop through required checks.
7. From integrated develop, repeat two-directory remote previews and explicit local dry preview; verify catalog CLI and approved-apply preflight contracts.
8. Revalidate exact local file/lock/pending state, then delete only the bound local catalog/lock.
9. Prove default remote operation no longer reads local state and release freeze.
10. Record live reads/writes, affected IDs, checks, deletion identity, and limits; close only after independent review.

If integration fails after seed, retain the local catalog and freeze; remote seed is idempotent. If post-merge verification fails, retain the local catalog for evidence even though integrated code ignores it, open a blocker, and do not claim cutover complete.

## External side effects authorized

The user authorized:

- create/update only `buoy-routing-catalog-v1` in `gcp-us-central1` with exactly two card rows;
- read namespace inventory/catalog metadata/cards for verification;
- delete only the exact bound local catalog/lock after success.

Not authorized: content namespace queries/writes/deletes, extra cards, cross-region operations, remote catalog deletion, live content retrieval/evals, protection changes, or other filesystem deletion.

## Acceptance scenarios

Absent, one-card partial, exact complete, and conflict/extra remote states follow the remote catalog spec. Every drift aborts. Successful cutover has one integrated public authority, two remote cards, two missing-card exclusions, identical cross-directory previews, no local catalog, and untouched content namespaces.
