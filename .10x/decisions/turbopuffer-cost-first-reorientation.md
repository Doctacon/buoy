Status: active
Created: 2026-06-20
Updated: 2026-06-20

# ADR: Reorient Jellyfish RAG work around minimum turbopuffer cost

## Context

The initial Jellyfish docs RAG MVP successfully indexed and queried `jellyfish-site-docs/` in turbopuffer, but the user observed a `$5.87` current invoice after a small amount of live validation. The billing dashboard showed storage, writes, queried-byte, and returned-byte charges all contributing materially. Evidence: `.loom/evidence/2026-06-20-turbopuffer-billing-cost-signal.md`.

The user explicitly wants future plans to take turbopuffer pricing and best practices into account so the bill is as small as possible.

## Decision

Future Jellyfish RAG work must prioritize minimum turbopuffer bill over maximum retrieval quality until the user explicitly changes that priority.

This means:

- Do not run additional live turbopuffer writes, queries, or evals without explicit user approval.
- Treat namespace deletion/reindexing as authority decisions.
- Prefer local/open-source storage, BM25, hydration, and evaluation when they reduce turbopuffer storage/returned-byte/query costs.
- Add cost estimation and guardrails before any replacement live index is written.
- Revise the MVP schema/retrieval defaults before considering the prototype cost-acceptable.

## Alternatives considered

- **Keep MVP as-is and just use smaller `top_k`/`candidates`.** Rejected because it does not address storage, filterability, full-text indexes, write batch size, or returned content bytes.
- **Stop using turbopuffer entirely.** Not chosen yet because the project goal remains testing turbopuffer-backed retrieval, but local/offloaded components should be used where they reduce cost.
- **Immediately delete the namespace.** Not decided here because deletion is destructive and requires explicit user approval.

## Consequences

- Some retrieval quality experiments may wait until after local cost modeling.
- The next implementation should likely add local chunk hydration and possibly local BM25.
- The old namespace may continue to cost money until the user chooses to delete it.
- The previous baseline decision remains useful history, but cost-first constraints now govern follow-up work.
