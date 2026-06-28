Status: active
Created: 2026-06-20
Updated: 2026-06-20

# Generic Site RAG Incremental Plan/Apply

## Purpose and scope

This spec defines the polished Terraform-like workflow for generic website-to-RAG indexing.

It extends the existing dry-run crawl behavior from `.loom/specs/generic-website-rag-dry-run-crawl.md` into two explicit phases:

1. `plan`: local-only crawl/extract/chunk/diff review.
2. `apply`: explicitly approved live embedding/upsert/delete against turbopuffer.

The core product requirement is incremental behavior: repeated applies for the same site/namespace should embed and write only new or changed chunks, while reporting stale rows and deleting them only with explicit approval.

Related records:

- Decision: `.loom/decisions/generic-site-rag-incremental-state.md`
- Research: `.loom/research/2026-06-20-incremental-rag-state-backend-research.md`
- Vocabulary: `.loom/knowledge/generic-site-rag-plan-apply-vocabulary.md`
- Existing dry-run spec: `.loom/specs/generic-website-rag-dry-run-crawl.md`

## Out of scope

This spec does not cover:

- remote/team state backend implementation;
- scheduled crawls;
- browser-rendered or stealth crawling;
- anti-bot bypass behavior;
- namespace deletion/replacement;
- local-content hydration cost optimization;
- a graphical review UI;
- proprietary embedding or reranking services.

## Behavior

### Plan command

The CLI should expose a local-only plan command, either as a new command or as a clear alias/evolution of the current crawl preview:

```bash
turbo-search plan \
  --base-url "https://scrapling.readthedocs.io/en/latest/" \
  --out-dir artifacts/site-crawls/scrapling-readthedocs-io-plan \
  --max-pages 1000 \
  --max-chunks 10000 \
  --css-selector ".md-content__inner" \
  --json
```

The plan command must:

- validate `--base-url` as absolute HTTP(S);
- crawl with Scrapling using the existing sitemap-first/same-site behavior;
- obey robots.txt;
- write generated Markdown pages;
- chunk generated pages locally;
- calculate page, chunk, embedding-text, and artifact hashes;
- read local applied state if present;
- compute an incremental diff;
- write reviewable plan artifacts;
- make no turbopuffer API calls;
- read no credentials;
- report `dry_run: true`, `credentials_required: false`, `turbopuffer_api_calls: false`, and `api_calls_occurred: false`.

Plan can accept a namespace candidate/target for diffing state:

```bash
turbo-search plan --base-url <url> --namespace site-example-com-v1
```

If no namespace is supplied, it uses the deterministic candidate `site-<host-slug>-v1`.

### Plan artifacts

A plan directory should contain at least:

```text
plan.json
summary.json
manifest.json
chunks.jsonl
pages/*.md
```

`plan.json` is the primary artifact passed to apply. It should include:

```json
{
  "schema_version": 1,
  "command": "plan",
  "plan_id": "...",
  "created_at": "...",
  "base_url": "...",
  "site_id": "...",
  "namespace": "site-scrapling-readthedocs-io-v1",
  "namespace_candidate": "site-scrapling-readthedocs-io-v1",
  "state_backend": "local",
  "state_path": ".turbo-search/state/.../last-applied.json",
  "crawl_options": {},
  "chunk_options": {},
  "embedding_model": "BAAI/bge-small-en-v1.5",
  "artifact_hash": "...",
  "diff": {
    "first_apply": false,
    "pages_added": 0,
    "pages_changed": 0,
    "pages_unchanged": 0,
    "pages_removed": 0,
    "chunks_unchanged": 0,
    "chunks_to_embed": 0,
    "rows_to_upsert": 0,
    "stale_rows": 0
  }
}
```

`manifest.json` should contain page and chunk details used for hashing and state comparison. `chunks.jsonl` should be easy to inspect without loading one large JSON file.

### Artifact hash verification

Apply must verify that the reviewed plan artifacts have not changed since the plan was created.

At minimum, `plan.json` should record a deterministic hash over the generated content needed for apply:

- generated Markdown page file paths and contents, excluding volatile crawl timestamps where possible;
- chunk records and embedding text hashes;
- manifest metadata needed for row construction.

If the hash does not match at apply time, apply must fail before credentials are read or live writes are attempted.

### Applied state

The first implementation uses a local state backend.

Default state path:

```text
.turbo-search/state/<site-id>/<namespace>/last-applied.json
.turbo-search/state/<site-id>/<namespace>/history/<apply-id>.json
```

State must include the row ledger for all rows the tool believes are present in the namespace, including retained stale rows.

Minimum state fields:

```json
{
  "schema_version": 1,
  "site_id": "...",
  "namespace": "...",
  "base_url": "...",
  "updated_at": "...",
  "last_plan_id": "...",
  "last_apply_id": "...",
  "rows": [
    {
      "row_id": "...",
      "canonical_url": "...",
      "page_hash": "...",
      "chunk_hash": "...",
      "embedding_text_hash": "...",
      "plan_id": "...",
      "applied_at": "...",
      "status": "active"
    }
  ]
}
```

If stale rows are not deleted, their `status` should remain trackable as retained stale or equivalent. Future plans must still surface them as stale until deleted.

### Incremental diff semantics

A plan compares the desired manifest against the local applied-state row ledger.

Diff categories:

- **unchanged chunk:** same row identity and same embedding text hash already active in state; no embedding or upsert needed.
- **new chunk:** desired chunk not present in state; needs embedding and upsert.
- **changed chunk:** desired canonical URL/section lineage exists but embedding text hash changed; needs embedding and upsert. The previous row becomes stale unless it has the same row ID.
- **removed page/chunk:** previously applied row no longer appears in desired manifest; report as stale.
- **retained stale row:** stale row intentionally left in namespace because apply was run without delete approval.

### Row identity

Generic site rows need IDs that are stable enough for incremental behavior and short enough for turbopuffer.

Recommended row ID input:

```text
site_id + canonical_url + section_path + chunk_hash
```

Recommended display shape:

```text
ts_<32 hex chars>
```

This differs from the original Jellyfish prototype chunk ID shape, which included full page source hash. The generic workflow should avoid page-hash-based IDs that cause every chunk on a changed page to receive a new ID.

### Row schema additions

Generic site rows should store chunk content in turbopuffer and include metadata for recovery/debugging.

Required or recommended row attributes:

```text
id
vector
content
title
url
path
section_path
chunk_index
doc_kind
tags
source_hash
site_id
canonical_url
page_hash
chunk_hash
embedding_text_hash
plan_id
applied_at
```

The exact turbopuffer schema syntax must be verified during implementation. Existing read paths should continue to avoid returning vectors by default.

### Apply command

The CLI should expose an explicit live apply command:

```bash
turbo-search apply \
  --plan artifacts/site-crawls/scrapling-readthedocs-io-plan/plan.json \
  --namespace site-scrapling-readthedocs-io-v1
```

Without `--approve`, apply must act as a preflight only:

- read and verify the plan;
- print the diff summary;
- say whether credentials would be required;
- make no turbopuffer calls;
- do not load the embedding model.

Live apply requires explicit approval:

```bash
turbo-search apply \
  --plan artifacts/site-crawls/scrapling-readthedocs-io-plan/plan.json \
  --namespace site-scrapling-readthedocs-io-v1 \
  --approve
```

With `--approve`, apply must:

1. verify artifact hash;
2. verify namespace matches the plan/argument;
3. require `TURBOPUFFER_API_KEY` from the environment;
4. load the configured local embedding model;
5. embed only chunks classified as new/changed;
6. upsert only those rows;
7. delete stale rows only if `--delete-stale` is also supplied;
8. write local state only after successful live operations;
9. write history state atomically before or together with updating `last-applied.json`;
10. report row counts, embedding counts, stale counts, and safety flags.

### Delete behavior

Plan always reports stale rows.

Apply behavior:

- Without `--delete-stale`: do not delete stale rows. Preserve them in local state as retained stale rows.
- With `--delete-stale`: delete stale row IDs from turbopuffer after explicit approval and update state to remove them or mark them deleted.

Delete operations must never run from plan and must never run from apply preflight.

### Failure behavior

Apply must fail before live work when:

- plan file does not exist;
- plan schema version is unsupported;
- artifact hash verification fails;
- namespace argument conflicts with plan namespace;
- base URL/site ID in state conflicts with plan;
- `--approve` is supplied but required credentials are absent;
- delete is requested but the plan does not include stale rows or delete semantics are unsupported by the current turbopuffer writer.

If live work starts and fails partway through, the tool must not silently overwrite `last-applied.json` as if the apply fully succeeded. It should record/print a partial failure summary and leave prior state intact unless a safe partial-state design is implemented deliberately.

## Acceptance criteria

- `turbo-search plan` exists or the existing `crawl` command gains an explicitly documented plan artifact mode.
- Plan is local-only and does not require credentials or turbopuffer access.
- Plan writes `plan.json`, `manifest.json`, `chunks.jsonl`, `summary.json`, and generated Markdown pages.
- Plan compares desired chunks to local applied state and reports first-apply/add/change/unchanged/stale counts.
- Apply without `--approve` is a no-write preflight.
- Apply with `--approve` embeds/upserts only new/changed chunks.
- Apply deletes stale rows only with `--delete-stale`.
- Apply updates local applied state atomically after successful operations.
- Tests cover first apply, no-change second plan, changed page/chunk, removed page/stale row, stale retained without delete, and stale deleted with explicit flag using fakes/mocks rather than live turbopuffer.
- Documentation shows the Scrapling docs example workflow from plan to apply.
- No private credential identifiers or secret values are persisted in code, docs, plans, state, tests, or Loom records.

## Constraints

- Use Python/uv and local open-source `BAAI/bge-small-en-v1.5` embeddings by default.
- Keep Scrapling as the crawler/fetch/extraction layer.
- Keep live writes behind explicit approval.
- Do not implement proprietary managed services as core dependencies.
- Keep generated artifacts and local state out of default commits unless the user deliberately chooses otherwise.
