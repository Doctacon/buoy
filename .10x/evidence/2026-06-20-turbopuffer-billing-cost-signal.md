Status: recorded
Created: 2026-06-20
Updated: 2026-06-20
Relates-To: .loom/tickets/2026-06-20-minimize-turbopuffer-rag-cost-plan.md, .loom/specs/cost-minimized-turbopuffer-jellyfish-rag.md

# Turbopuffer billing and pricing signal

## What was observed

The user reported that the turbopuffer bill is already materially higher than expected for the small Jellyfish site-docs prototype and supplied screenshots plus pricing-calculator notes.

Stored screenshots:

- `.loom/evidence/.storage/2026-06-20-turbopuffer-billing-invoice.png`
- `.loom/evidence/.storage/2026-06-20-turbopuffer-dev-overview.png`
- `.loom/evidence/.storage/2026-06-20-turbopuffer-pricing-calculator.png`

Observed dashboard values from the supplied screenshots:

- Current invoice: `$5.87`
- Billing period shown: `Jun 20-Jul 1`, with `10 days left`
- Breakdown shown in pie chart:
  - Storage: `$1.45` (`24.7%`)
  - Pinned namespace: `$0.00`
  - Writes: `$1.50` (`25.6%`)
  - Queries, queried bytes category: `$1.46` (`24.9%`)
  - Queries, returned bytes category: `$1.46` (`24.9%`)
- Dev overview:
  - Namespaces: `1`
  - Documents/rows: `12.72K`
  - Storage: `24.94MB`
  - Rows written: `12.72K`
  - Data written: `24.01MB`
  - Queries: `30`
  - Queried: `7.68GB`

The user also supplied these turbopuffer pricing notes:

Storage:

```text
Attributes are billed at 100% of their logical size per-index (50% if unindexed). See docs
f16 vectors cost 50% less than f32
i8 vectors cost 75% less than f32
Filterable attributes are billed per vector column
```

Writes:

```text
50% discount on unindexed attributes
Minimum billing threshold of 10kB per write
50% write discount for namespace copies
≤ 50% write batch discounts (maxes out at 3.2MB)
min((log10(kb)-1)*0.2, 0.5)*100% discount
Patch writes are billed for the size of the patched attributes
Patch and conditional writes add the cost of one query per request
i8, f16, f32 charged as 4 bytes/dimension as indexing time is similar.
Filterable attributes are billed per vector column
```

Queries:

```text
$0.05/GB returned
$1.00/PB queried
50% discount on unindexed attributes
f16 vectors cost 50% less than f32
i8 vectors cost 75% less than f32
80% discount on marginal bytes queried between 32GB–128GB, per query
96% discount on marginal bytes queried over 128GB, per query
Minimum billing threshold of 1.28GB queried, per query
```

Namespaces:

```text
A namespace is an isolated set of documents. Queries are cheaper and faster on smaller namespaces. We recommend putting each tenant or isolated workload in its own namespace.
```

## Procedure

The screenshots were read from the temporary clipboard paths supplied by the user and copied into `.loom/evidence/.storage/` so the cost signal remains durable after temp files are cleaned up.

The pricing notes were copied from the user's message verbatim.

## What this supports or challenges

This challenges the previous MVP schema and live-validation defaults as cost-unsafe for exploratory usage:

- The namespace is small in absolute data terms (`24.94MB`) but still produced a visible invoice during initial indexing and validation.
- The current schema indexes several attributes and leaves multiple metadata attributes filterable by default, which conflicts with the supplied best-practice emphasis on indexed/filterable logical size.
- Live retrieval/eval defaults used candidate counts that were reasonable for quality smoke testing but too expensive as defaults for bill-sensitive exploration.
- Returning `content` from turbopuffer on retrieval likely contributes to returned-byte charges; full chunk content can instead be hydrated locally from an open-source/local store.

This evidence supports opening a cost-minimization plan before any additional live indexing, queries, or evals are run.

## Limits

The screenshots show aggregate billing and usage, not per-request line items. They do not prove which exact request produced which cost component. The pricing notes are user-supplied extracts and should be verified against current turbopuffer docs before implementing a final cost model.
