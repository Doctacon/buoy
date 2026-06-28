Status: active
Created: 2026-06-20
Updated: 2026-06-20

# Generic Site RAG Incremental State Strategy

## Context

The project now has a working dry-run website preview command using Scrapling:

```bash
turbo-search crawl --base-url <url> --json
```

It can crawl a site, extract Markdown, generate chunks, and produce local artifacts without credentials or turbopuffer calls. The next product step is a Terraform-like `plan` / `apply` workflow for generic website RAG indexing.

The user specifically wants incremental behavior before a polished `apply` exists. If yesterday's crawl already embedded 1,268 chunks and tomorrow's crawl changes only 20 chunks, the system should not re-embed or re-upsert all 1,268 chunks. It should detect added, changed, unchanged, and stale rows.

Open questions considered:

- Should applied state live locally, in the repository, in turbopuffer, or in a remote state backend?
- Should stale rows be deleted automatically?
- Should namespaces be stable or versioned?
- Should chunk text live in turbopuffer or be hydrated locally?

Relevant research: `.loom/research/2026-06-20-incremental-rag-state-backend-research.md`.

## Decision

Build the first polished generic site RAG workflow around a **local applied-state manifest** with a backend abstraction for future remote state.

Specific decisions:

1. **State backend:** local applied-state manifest first.
   - Store current state at `.turbo-search/state/<site-id>/<namespace>/last-applied.json`.
   - Store historical applied manifests under `.turbo-search/state/<site-id>/<namespace>/history/`.
   - Treat this as local machine state, similar to Terraform local state for a solo/dev workflow.
   - Design the state store behind a small interface so remote or turbopuffer-backed state can be added later.

2. **Namespace strategy:** stable namespace per site.
   - Default namespace candidate remains `site-<host-slug>-v1`.
   - Repeated applies update the same namespace incrementally.

3. **Deletes:** stale rows require an explicit delete flag.
   - A plan must report stale rows.
   - Apply must not delete stale rows unless an explicit flag such as `--delete-stale` is passed.
   - If stale rows are retained, local state must continue tracking them as retained stale rows so they can be deleted in a future apply.

4. **Content storage:** store chunk text in turbopuffer for the first polished version.
   - This keeps retrieval and citation behavior simple.
   - Cost optimization via local hydration remains a separate future concern.

5. **Recovery metadata:** turbopuffer rows should include enough state metadata to inspect or reconstruct state later.
   - Include `site_id`, `canonical_url`, `page_hash`, `chunk_hash`, `embedding_text_hash`, `plan_id`, and `applied_at` in row attributes where supported.

## Alternatives considered

### Store state only in turbopuffer

Rejected for the first implementation.

Pros:

- Any machine with credentials could theoretically inspect current row metadata.
- State travels with the vector rows.

Cons:

- Plan generation would require live turbopuffer reads, violating the local-only preview model.
- Recovery/diff logic would depend on provider-specific query/filter/delete semantics.
- It makes safe review harder because the plan cannot be fully generated offline.

Turbopuffer metadata remains useful as a recovery/debugging layer, but not as the primary state backend yet.

### Commit state to the repository

Rejected as the default.

Pros:

- State is versioned and reviewable.
- Other machines can reproduce diff behavior after pulling.

Cons:

- Crawl artifacts and site metadata can be noisy.
- Committing applied state may expose public-site metadata that users do not expect in source control.
- It complicates quick local experimentation.

A future `--state-dir` or documented committed-state option may be useful, but it should not be the MVP default.

### Implement remote state immediately

Rejected for MVP scope.

Pros:

- Better team/CI semantics, locking, backup, and shared state.

Cons:

- Requires choosing and implementing storage/locking semantics before the CLI contract is proven.
- Adds operational complexity outside the immediate local prototype.

The local state store should be designed so a remote backend can be added later.

### Versioned namespaces per apply

Rejected for the first polished workflow.

Pros:

- Easy rollback/cutover model.
- Avoids in-place mutation risk.

Cons:

- Higher storage cost.
- Namespace lifecycle becomes more complex.
- Retrieval clients must know which namespace is current.

A stable namespace with explicit stale-delete planning is simpler and cheaper for the current product direction.

## Consequences

### Enables

- Terraform-like local plan/apply behavior.
- Efficient incremental embedding and upsert behavior.
- Reproducible review artifacts before live writes.
- Explicit delete safety.
- Future remote state without changing the user-facing model.

### Restricts

- The first version is not inherently multi-machine safe. If another machine applies to the same namespace without sharing state, local diffing can be wrong.
- CI/team workflows will need a remote or committed state backend later.
- Losing local state means the next plan may need a conservative full-sync/recovery mode.

### Accepted tradeoffs

- Keep MVP state local for simplicity and local-only planning.
- Store full chunk content in turbopuffer for retrieval ergonomics despite higher storage/query cost.
- Require explicit `--delete-stale` instead of automatic convergence to avoid accidental destructive writes.
