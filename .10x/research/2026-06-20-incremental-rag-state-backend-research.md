Status: done
Created: 2026-06-20
Updated: 2026-06-20

# Incremental RAG State Backend Research

## Question

For a Terraform-like website-to-RAG workflow, where should incremental indexing state live so repeated applies avoid re-embedding unchanged content while still supporting safe deletes and reproducible plans?

The specific decision needed was whether the first polished implementation should store applied state locally, commit it to the repository, store it in turbopuffer, or design for a remote backend immediately.

## Sources and methods

A short web research pass was run on 2026-06-20 using these queries:

- `RAG incremental indexing state manifest document hashes vector database best practice`
- `LlamaIndex incremental indexing document management vector store docstore hashes`
- `LangChain indexing API RecordManager incremental vectorstore cleanup source_id`
- `Terraform state remote backend standard practice local vs remote state`

Sources surfaced and consulted:

- LangChain RecordManager reference: https://reference.langchain.com/python/langchain-core/indexing/base/RecordManager
- LangChain indexing API reference: https://reference.langchain.com/python/langchain-core/indexing/api/index
- LangChain blog, "Syncing data sources to vector stores": https://www.langchain.com/blog/syncing-data-sources-to-vector-stores
- LlamaIndex ingestion/document-management examples: https://docs.llamaindex.ai/en/stable/examples/ingestion/ingestion_gdrive/
- LlamaIndex document-management documentation: https://developers.llamaindex.ai/python/framework/module_guides/indexing/document_management/
- HashiCorp Terraform remote state documentation: https://developer.hashicorp.com/terraform/language/state/remote
- HashiCorp Terraform backend overview: https://developer.hashicorp.com/terraform/language/backend
- AWS Terraform backend best-practices overview: https://docs.aws.amazon.com/prescriptive-guidance/latest/terraform-aws-provider-best-practices/backend.html
- Spacelift Terraform backends overview: https://spacelift.io/blog/terraform-backends

## Findings

### Incremental RAG needs an explicit ledger

The recurring pattern across RAG indexing systems is that stateless pipelines cannot do efficient incremental updates. They need a ledger/docstore/record-manager that can answer:

- what source documents were previously indexed;
- which content hashes were written;
- which vector rows correspond to which source IDs;
- which rows are stale when sources disappear or chunks change.

LangChain's indexing API uses a `RecordManager` that tracks hashes, source IDs, and write times separately from the vector store. It supports cleanup modes and warns that source IDs matter for incremental cleanup. LlamaIndex uses a docstore alongside the vector store to manage duplicate and changed documents.

### Chunk-level hashes are better than page-only hashes

Page-level hashes are useful for quickly detecting whether a page changed, but they are too coarse for embedding reuse. A tiny page edit should not force re-embedding every unchanged chunk on that page.

The state model should track at least:

- page/content hash for changed-page detection;
- chunk hash for embedding/upsert reuse;
- embedding text hash because embeddings are generated from title/section/content, not only content;
- row ID so stale turbopuffer rows can be deleted later.

### Vector stores can hold recovery metadata but should not be the first source of truth

Several sources recommend or imply separate state/docstore abstractions because vector-store metadata behavior varies by provider and client. Storing metadata in vector rows is still valuable for recovery/debugging, but using the vector database as the only state backend makes diffing, locking, and local plan review harder.

For this project, turbopuffer rows should include enough metadata to reconstruct intent later (`site_id`, `canonical_url`, `page_hash`, `chunk_hash`, `plan_id`, `applied_at`), but the initial incremental diff should be driven by a local applied-state manifest.

### Terraform's local vs remote state pattern maps well

Terraform stores state locally by default, but remote state/backends are standard for teams, CI/CD, locking, durability, and shared collaboration.

For this project, the analogous path is:

1. Start with a local state backend because the current workflow is a local CLI prototype.
2. Design the state store behind a small abstraction so remote state can be added later.
3. Do not require committed state for the MVP because generated crawl/site metadata can be noisy and may not belong in source control.
4. Do not require turbopuffer as the only state backend because state reads should not be required for local plan generation.

## Conclusions

Recommended first implementation:

- Use a local applied-state manifest first.
- Store it under a dedicated local state directory, not inside the reviewed plan artifacts.
- Keep historical applied manifests for audit/debugging.
- Include recovery metadata in turbopuffer rows so future tools can inspect or reconstruct state if local state is lost.
- Design an interface that can later support remote state, committed state, or turbopuffer-backed state without changing the plan/apply contract.

Recommended state path shape:

```text
.turbo-search/state/<site-id>/<namespace>/last-applied.json
.turbo-search/state/<site-id>/<namespace>/history/<apply-id>.json
```

Recommended row metadata additions:

```text
site_id
canonical_url
page_hash
chunk_hash
embedding_text_hash
plan_id
applied_at
```

This supports the user's chosen product defaults:

- stable namespace per site;
- explicit delete flag for stale rows;
- chunk text stored in turbopuffer for MVP retrieval ergonomics;
- Markdown/JSON review before live writes.

## Limits

This was a lightweight research pass, not a full implementation audit. It did not test turbopuffer delete/query APIs directly. The exact turbopuffer delete mechanics and metadata filter capabilities must be verified during implementation before any generic live apply is run.
