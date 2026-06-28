Status: draft
Created: 2026-06-20
Updated: 2026-06-20

# Cost-minimized turbopuffer Jellyfish RAG

## Purpose and scope

Define the desired cost-first behavior for the Jellyfish docs RAG prototype after the initial MVP produced a higher-than-expected bill.

This spec covers:

- Cost-aware indexing schema choices.
- Cost-aware retrieval defaults.
- Local content hydration and/or local BM25 options.
- Cost-estimation and guardrails before live turbopuffer operations.
- Safe namespace cutover/deletion behavior.

This spec does not cover:

- Building a production chatbot UI.
- Proprietary embedding or reranking services.
- Any live turbopuffer mutation without explicit user approval.

## Background

The MVP indexed `12,721` chunks into `jellyfish-site-docs-v1`. The observed dashboard showed `24.94MB` storage, `24.01MB` data written, `30` queries, `7.68GB` queried, and a `$5.87` current invoice. Evidence: `.loom/evidence/2026-06-20-turbopuffer-billing-cost-signal.md`.

The project needs a revised design that optimizes for the smallest practical bill over maximum recall.

## Cost-first behavior contract

### Live operation guardrail

Given any CLI command that may call turbopuffer, when the command is run without an explicit live flag, then it must not contact turbopuffer.

Given a command that may write to turbopuffer, when an estimated cost/size report has not been shown, then it should refuse to write unless an explicit override is passed.

Given the user has not explicitly approved a live delete/reindex/query, then agents must not run it.

### Index footprint

A cost-first index should minimize logical size by default:

- Use the smallest acceptable vector type (`[384]f16` baseline; evaluate `[384]i8` if quality remains acceptable).
- Avoid storing full chunk `content` in turbopuffer if a local chunk store can hydrate answers.
- If turbopuffer BM25 is kept, use a single compact `search_text` attribute instead of three separate full-text attributes.
- Explicitly mark citation/debug metadata as not filterable unless there is an actual query path that filters on it.
- Avoid `tags` and `source_hash` in the live namespace unless needed for sync/cutover.
- Reduce chunk count with larger target chunks, stronger boilerplate stripping, and duplicate suppression before any live write.

### Retrieval footprint

A cost-first retrieval should minimize returned bytes and query count:

- Return only `id` plus minimal citation metadata from turbopuffer.
- Do not return `content` from turbopuffer by default.
- Hydrate full content from a local artifact keyed by chunk ID.
- Default live retrieval should use small limits suitable for one-question exploration, not eval-scale defaults.
- Live evals must remain opt-in and should print the number of billable queries before running.

### Hybrid search options

The recommended direction is local-first hybrid:

1. Turbopuffer performs vector ANN over compact vectors and returns candidate IDs.
2. Local open-source BM25/FTS over the chunk store returns lexical candidates.
3. The CLI fuses local BM25 and turbopuffer ANN results with local RRF.
4. The answer workflow hydrates final chunks locally and cites `title`/`url`.

A second acceptable direction, if local BM25 is rejected, is compact turbopuffer hybrid:

1. Turbopuffer stores vector plus one compact full-text `search_text` field.
2. Turbopuffer multi-query performs ANN + BM25/RRF.
3. Turbopuffer returns only IDs/small metadata.
4. Full chunk content is still hydrated locally.

## Acceptance criteria

- A local cost audit can explain the observed cost drivers without additional live turbopuffer calls.
- A cost estimate command/report compares current MVP shape to at least two cheaper alternatives.
- The chosen replacement schema explicitly sets filterability for every non-vector attribute.
- Retrieval no longer requests full `content` from turbopuffer by default.
- Full answer context is available from a local chunk store with deterministic IDs and citation metadata.
- Any live reindex/cutover ticket is blocked until the user approves the target namespace, estimated write size, delete/cutover behavior, and maximum number of live query validations.
- README and agent workflow warn that live evals and writes are billable and should not be used as casual smoke checks.

## Open authority decisions

These must be answered before execution moves beyond local-only audit/design work:

1. Should the current `jellyfish-site-docs-v1` namespace be deleted now to stop ongoing storage charges, retained as evidence, or retained until a cheaper replacement is verified?
2. Is local-first hybrid acceptable, even though BM25 would run locally rather than inside turbopuffer?
3. If a replacement namespace is approved, what is the maximum acceptable live write/query budget for validation?
