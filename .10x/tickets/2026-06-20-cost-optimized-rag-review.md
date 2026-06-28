Status: open
Created: 2026-06-20
Updated: 2026-06-20
Parent: .loom/tickets/2026-06-20-minimize-turbopuffer-rag-cost-plan.md
Depends-On: .loom/tickets/2026-06-20-query-and-eval-cost-guardrails.md

# Review cost-optimized RAG changes

## Scope

Perform an adversarial review of the cost-minimized plan and any implementation before closing the parent plan.

In scope:

- Review schema for unnecessary indexed/filterable attributes.
- Review retrieval for accidental full-content/vector returns from turbopuffer.
- Review CLI/docs for live-cost warnings and accidental eval/write paths.
- Review estimator assumptions against observed dashboard values.
- Confirm no secrets or temp credential artifacts were written.
- Confirm evidence exists for local tests and any approved live operations.

Out of scope:

- Implementing fixes directly; findings should open or update tickets.

## Acceptance criteria

- A review record is written under `.loom/reviews/`.
- Findings are categorized by severity.
- Any significant finding has a follow-up ticket or is explicitly accepted as residual risk.
- Parent plan is not closed until the review verdict is pass or concerns are deliberately accepted.

## Progress and notes

- 2026-06-20: Ticket opened only.

## Blockers

- Meaningful review depends on whichever design/implementation tickets are executed.
