Status: active
Created: 2026-06-20
Updated: 2026-06-20

# Generic Site RAG Plan/Apply Vocabulary

## Plan

A local-only, reviewable artifact that describes what would be indexed for a website and how it differs from the last applied state.

A plan must not read credentials, create namespaces, embed text, or call turbopuffer.

Expected artifacts include:

```text
plan.json
summary.json
pages/*.md
chunks.jsonl
manifest.json
```

## Apply

A live, explicitly approved operation that takes a saved plan and mutates a turbopuffer namespace.

Apply may embed new/changed chunks and upsert rows. It may delete stale rows only when an explicit delete flag is supplied.

Apply is the generic-site equivalent of Terraform apply. It must verify that the saved plan still matches the reviewed artifacts before doing live work.

## Applied state

The local ledger of what rows the system believes are currently present in a namespace for a site.

MVP state path:

```text
.turbo-search/state/<site-id>/<namespace>/last-applied.json
.turbo-search/state/<site-id>/<namespace>/history/<apply-id>.json
```

Applied state is not the same as a plan. Plans are review artifacts; applied state is the diff baseline for future plans.

## Row ledger

The part of applied state that tracks row IDs and their source metadata:

```text
row_id
canonical_url
page_hash
chunk_hash
embedding_text_hash
plan_id
applied_at
status
```

If stale rows are retained because `--delete-stale` was not passed, they remain in the row ledger with a retained-stale status so a future plan can still report/delete them.

## Page hash

A hash of normalized extracted page Markdown after site chrome cleanup and before chunking. It detects whether the page changed since the last plan/apply.

Page hashes are useful for changed-page reporting but should not be the only incremental unit.

## Chunk hash

A hash of normalized chunk content. It is the main unit for deciding whether a chunk needs embedding/upsert.

## Embedding text hash

A hash of the exact text passed to the embedding model. This can differ from the chunk hash because embedding text includes title and section context.

If embedding text changes, the embedding should be recomputed even if the raw content is similar.

## Stable namespace

A namespace that is reused across recurring applies for the same site, rather than creating a new namespace for every version.

Default candidate pattern:

```text
site-<host-slug>-v1
```

## Stale row

A row believed to exist in turbopuffer from a previous apply but no longer present in the current desired plan.

Stale rows must be reported in the plan. They must not be deleted unless apply is run with an explicit delete flag such as `--delete-stale`.
