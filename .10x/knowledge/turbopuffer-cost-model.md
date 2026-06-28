Status: active
Created: 2026-06-20
Updated: 2026-06-20

# Turbopuffer cost model and project guardrails

## Scope

Reusable project knowledge for keeping turbopuffer-backed Jellyfish RAG costs as low as possible. Source evidence: `.loom/evidence/2026-06-20-turbopuffer-billing-cost-signal.md`, current implementation evidence, and the current schema in `src/turbo_search/indexer.py`.

## Pricing concepts to remember

- **Launch has a monthly minimum.** The observed `$5.87` invoice for an ~11-day `Jun 20-Jul 1` period matches `$16/mo` prorated almost exactly (`$16 / 30 * 11 = $5.87`). This means the first visible bill was probably dominated by the plan minimum, not by the RAG workload's raw usage. Evidence: `.loom/evidence/2026-06-20-turbopuffer-launch-minimum-billing-analysis.md`.
- **Storage is logical-size and index-sensitive.** Attributes are billed at full logical size per index, and unindexed attributes are discounted.
- **Vectors should stay compact.** Current implementation already uses `[384]f16`, which is cheaper than f32. `i8` may reduce vector storage further if supported and relevance remains acceptable.
- **Filterability is not free.** Filterable attributes are billed per vector column. In the observed namespace, default filterability made `url`, `path`, `chunk_index`, `doc_kind`, `tags`, and `source_hash` filterable unless explicitly disabled.
- **Full-text indexes duplicate cost surface.** The MVP indexed `content`, `title`, and `section_path` for BM25. A cost-first design should avoid separate full-text indexes unless the query quality benefit is proven.
- **Writes have minimums and batch discounts.** The MVP wrote with batch size `128`, which was safe but probably below the batch size needed to maximize the documented write discount that maxes near `3.2MB` per write.
- **Queries have a minimum queried-byte threshold.** Small namespaces can still incur the per-query minimum. Reducing query count is usually more important than micro-tuning candidate counts once below the threshold.
- **Returned bytes matter.** Returning full chunk `content` from turbopuffer for every candidate is cost-hostile. Prefer returning tiny identifiers/metadata and hydrating content locally.
- **Namespaces matter.** Smaller targeted namespaces can reduce queried bytes when above the minimum and can improve latency, but duplicating data across namespaces can increase storage/write cost.

## Current MVP cost risks

Important correction: the current invoice appears to be mostly the prorated Launch-plan minimum. The risks below are still worth fixing for future usage and scale, but they are probably not why the invoice already reached `$5.87`.

Current namespace: `jellyfish-site-docs-v1` in `gcp-us-central1`.

Current row count: `12,721` chunk rows.

Current schema from `src/turbo_search/indexer.py`:

- ANN vector: `vector [384]f16`
- Full-text: `content`, `title`, `section_path`
- Metadata: `url`, `path`, `chunk_index`, `doc_kind`, `tags`, `source_hash`

Observed live schema made metadata fields filterable by default unless disabled. That is probably unnecessary for citation/debug attributes and conflicts with the cost notes.

Current retrieval asks turbopuffer to include these attributes:

- `title`
- `url`
- `section_path`
- `content`
- `path`
- `doc_kind`
- `chunk_index`

For bill-sensitive usage, `content` should not be returned from turbopuffer unless there is no local chunk store.

## Cost-first design rules for future work

1. **No additional live write/query/eval runs without explicit user approval.** Dry-runs and local file analysis are safe.
2. **Default to local/open-source hydration.** Store full chunk text locally in a JSONL or SQLite artifact; turbopuffer should return IDs and small metadata only.
3. **Minimize indexed attributes.** Make every metadata field explicitly `filterable: False` unless a live query requires filtering by that field.
4. **Avoid multiple full-text attributes.** If BM25 stays in turbopuffer, use one compact `search_text` attribute rather than indexing `content`, `title`, and `section_path` separately.
5. **Consider local BM25.** For a small local corpus, SQLite FTS/Tantivy-style local BM25 plus turbopuffer vector search may be cheaper than storing full content for turbopuffer BM25.
6. **Tune chunk count before writing.** Larger chunks, boilerplate removal, and deduplication can reduce rows and metadata overhead.
7. **Batch writes for discounts.** Compute estimated batch logical size and target the documented discount knee near `3.2MB`, subject to SDK/request limits.
8. **Make cost visible in CLI output.** Any command that can call turbopuffer should print estimated query/write shape before execution and should expose bill-sensitive defaults.
9. **Do not run live evals casually.** A five-question eval is multiple billable queries; dry-run/local eval should be the default.
10. **Treat namespace deletion as an authority decision.** Deleting the current namespace may stop ongoing storage costs, but it is destructive and requires explicit user approval.
