Status: open
Created: 2026-06-20
Updated: 2026-06-20
Parent: .loom/tickets/2026-06-20-minimize-turbopuffer-rag-cost-plan.md
Depends-On: .loom/tickets/2026-06-20-turbopuffer-cost-audit-estimator.md, .loom/specs/cost-minimized-turbopuffer-jellyfish-rag.md

# Cost-optimized index design

## Scope

Select the architecture for the cheaper Jellyfish RAG replacement before implementation.

Design variants to evaluate:

1. **Patch current shape:** keep turbopuffer hybrid but disable unnecessary filterability and reduce live defaults.
2. **Compact turbopuffer hybrid:** vector + one compact `search_text` BM25 field in turbopuffer; content hydrated locally.
3. **Local-first hybrid:** turbopuffer vector ANN only; local open-source BM25/FTS and local content hydration; local RRF fusion.
4. **Page-level or larger-chunk index:** fewer rows with lower metadata overhead, accepting potentially lower answer precision.
5. **Quantized vector variant:** evaluate `[384]i8` if turbopuffer supports it with acceptable retrieval quality.

In scope:

- Update `.loom/specs/cost-minimized-turbopuffer-jellyfish-rag.md` from draft to active when decisions are resolved.
- Create an ADR if a durable architecture choice is made.
- Define target namespace naming and cutover strategy.
- Define what quality loss is acceptable to reduce cost.

Out of scope:

- Code implementation.
- Live reindexing.
- Live queries.

## Acceptance criteria

- A single recommended target design is documented with tradeoffs.
- The recommendation explicitly addresses storage, writes, queried bytes, returned bytes, and namespace strategy.
- The recommendation states whether local-first hybrid is acceptable.
- The target schema/query shape is precise enough for implementation tickets to execute without guessing.
- Any unresolved user authority decisions are listed clearly.

## Progress and notes

- 2026-06-20: Ticket opened only. Recommended starting point is local-first hybrid because it minimizes turbopuffer returned bytes and avoids storing full chunk content in turbopuffer.

## Blockers

- Depends on local audit/estimator findings.
- User approval may be needed if moving BM25 out of turbopuffer changes the product intent.
