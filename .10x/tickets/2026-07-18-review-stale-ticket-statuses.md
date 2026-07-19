Status: blocked
Created: 2026-07-18
Updated: 2026-07-18
Parent: .10x/tickets/2026-07-18-repository-cleanup-plan.md
Depends-On: .10x/tickets/2026-07-18-normalize-terminal-ticket-placement.md

# Review Stale Ticket Statuses

## Scope

Perform closure review—not implementation repair—of stale open/active/blocked tickets identified in `.10x/research/2026-07-18-repository-dead-end-inventory.md`:

- float16 embedding inference;
- single-pass plan and stage timing;
- cross-corpus validation basket;
- repo oversize source indexing;
- website capped aggregation default review;
- repo searchable path/symbol metadata;
- repo search heavy ranking experiments;
- conditional website replanning.

For each ticket, map existing acceptance criteria to existing evidence/reviews/source and choose only an evidence-supported disposition: close, cancel with durable no-action rationale, remain open/active, or block with a precise closure note. Do not create new verification evidence or repair implementation in this ticket.

## Acceptance criteria

- Read each ticket and every referenced governing/evidence/review record needed for closure.
- Check active spec coherence and material test/source assertions where semantic authority is relevant.
- Move only supported terminal tickets to terminal directories and repair references.
- Unsupported closure leaves the ticket open/blocked with exact missing evidence, review, retrospective, or spec-coherence requirements.
- Preserve unfinished work with a durable owner; do not conflate rejected hypotheses with failed implementation.
- Record one adversarial aggregate review with verdict and residual risk.

## Evidence expectations

Per-ticket acceptance mapping, disposition table, moved/reference map, unsupported-closure notes, and aggregate review.

## Blockers

Terminal placement normalization must integrate first.

## Explicit exclusions

Running new tests/benchmarks/live operations; fixing code; accepting residual risk; changing ranking or precision defaults; closing Node.js-action or retrieval-tag tickets.

## References

- `.10x/tickets/2026-07-18-repository-cleanup-plan.md`
- `.10x/research/2026-07-18-repository-dead-end-inventory.md`

## Progress and notes
