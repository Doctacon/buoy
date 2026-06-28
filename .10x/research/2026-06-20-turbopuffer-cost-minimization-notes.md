Status: active
Created: 2026-06-20
Updated: 2026-06-20

# Turbopuffer cost minimization notes

## Question

Why did the Jellyfish docs turbopuffer prototype produce a visible bill despite being a small website, and what should be researched or validated before rebuilding it more cheaply?

## Sources and methods

- User-supplied turbopuffer billing screenshots and pricing-calculator text.
- Existing implementation schema and retrieval code in `src/turbo_search/indexer.py` and `src/turbo_search/retriever.py`.
- Existing live indexing/retrieval evidence under `.loom/evidence/`.

No new live turbopuffer calls, writes, or credential access were performed for this note.

## Preliminary findings

Current MVP choices that likely increased cost:

1. **Multiple indexed text attributes.** `content`, `title`, and `section_path` all have full-text search enabled.
2. **Filterable metadata by default.** Observed live schema shows `url`, `path`, `chunk_index`, `doc_kind`, `tags`, and `source_hash` are filterable unless explicitly disabled.
3. **Full content returned from retrieval.** Retrieval includes `content` in `include_attributes`, so full chunks may be returned from turbopuffer for candidates.
4. **Live eval/query count.** Dashboard shows `30` queries. The eval harness and live validation commands intentionally ran multiple queries for smoke validation, but those should not be casual defaults when bill-sensitive.
5. **Write batch size.** The live write used batch size `128`; the pricing notes say write batch discounts max out near `3.2MB`, so larger batches may have reduced write cost.
6. **Row count.** `12,721` chunks from `1,124` files is reasonable for RAG quality, but cost-first mode may need larger chunks/fewer rows.

## Conclusions to validate

- The cheapest viable path is probably to keep full chunk content local and have turbopuffer return only IDs/small metadata.
- Local open-source BM25/FTS plus turbopuffer vector search is likely cheaper than storing full text for turbopuffer BM25, but the quality/cost tradeoff needs explicit approval.
- If turbopuffer BM25 is retained, it should probably be over one compact `search_text` field, not three separate text fields.
- Future live writes need preflight estimates and larger batch sizing.
- The current namespace may continue to accrue storage charges until deleted; deleting it is destructive and requires user approval.

## Open research items

- Verify exact turbopuffer syntax and support for explicit non-filterable fields, i8 vectors, by-ID reads, and namespace deletion with the installed SDK/API.
- Verify whether `multi_query` with server RRF returns only final rows or candidates from each subquery, and how `include_attributes` affects returned-byte billing.
- Verify whether any cheaper read-by-ID path exists that avoids normal query minimums.
- Compare local-first hybrid quality against the current MVP smoke evals without running live turbopuffer evals unless approved.
