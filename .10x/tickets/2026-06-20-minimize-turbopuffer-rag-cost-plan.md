Status: open
Created: 2026-06-20
Updated: 2026-06-20
Parent: none
Depends-On: .loom/specs/cost-minimized-turbopuffer-jellyfish-rag.md, .loom/knowledge/turbopuffer-cost-model.md, .loom/evidence/2026-06-20-turbopuffer-billing-cost-signal.md

# Plan: minimize turbopuffer cost for Jellyfish RAG

## Scope

Create a cost-first follow-up plan for the Jellyfish docs RAG prototype after the initial turbopuffer bill was higher than expected.

In scope:

- Explain and quantify likely cost drivers from the current implementation.
- Add local-only cost estimation before future live operations.
- Redesign the index/retrieval path to minimize storage, write, query, and returned-byte charges.
- Add stronger CLI/docs guardrails around live writes, live retrieval, and live evals.
- Decide what to do with the current `jellyfish-site-docs-v1` namespace.

Out of scope until explicitly approved:

- Deleting the current namespace.
- Running additional live turbopuffer queries.
- Running live evals.
- Writing a replacement namespace.
- Persisting or printing secrets.

## Child tickets and dependency order

1. `.loom/tickets/2026-06-20-turbopuffer-cost-audit-estimator.md`
   - Local-only audit of current cost drivers and estimator for alternate shapes.
   - No dependencies beyond current repo and cost evidence.

2. `.loom/tickets/2026-06-20-turbopuffer-immediate-cost-containment.md`
   - Authority decision and optional execution path for deleting or retaining the current namespace.
   - Blocked until user approval for any live/destructive action.

3. `.loom/tickets/2026-06-20-cost-optimized-index-design.md`
   - Choose the target cost-first architecture: local-first hybrid vs compact turbopuffer hybrid vs other variants.
   - Depends on ticket 1; must resolve spec open decisions before implementation tickets proceed.

4. `.loom/tickets/2026-06-20-cost-optimized-local-chunk-store.md`
   - Implement deterministic local content/citation hydration so turbopuffer does not need to return full chunk content.
   - Depends on ticket 3.

5. `.loom/tickets/2026-06-20-cost-optimized-turbopuffer-schema-and-retrieval.md`
   - Implement minimized schema, explicit filterability, minimal include attributes, smaller live defaults, and write batch sizing.
   - Depends on tickets 3 and 4.

6. `.loom/tickets/2026-06-20-query-and-eval-cost-guardrails.md`
   - Update CLI/docs/tests so live evals and live queries are cost-visible and hard to run accidentally.
   - Can start after ticket 1; should be reconciled after tickets 4 and 5.

7. `.loom/tickets/2026-06-20-cost-optimized-live-reindex-cutover.md`
   - Optional live reindex/cutover into a cheaper namespace and optional deletion of old namespace.
   - Blocked until user approves estimated cost, target namespace, and validation query count.

8. `.loom/tickets/2026-06-20-cost-optimized-rag-review.md`
   - Review cost estimates, schema, query behavior, and docs before closing the plan.
   - Depends on whichever implementation/cutover tickets are executed.

## Execution policy

- Parent agent coordinates only. Executable child tickets should be run by subagents when the user says to execute.
- No child ticket may perform live turbopuffer operations unless its ticket explicitly says it is approved and records the exact approved operation.
- Local-only tickets may inspect code, run unit tests, and run dry-run/index-size analysis without credentials.
- Every live operation must produce evidence with command shape, non-secret config, row/query counts, and limits.

## Acceptance criteria

- The user has a clear explanation of why the MVP bill moved.
- A cost-first target architecture is selected and recorded.
- The code no longer defaults to expensive retrieval/eval settings.
- The retrieval path can answer using locally hydrated content so returned bytes from turbopuffer are minimized.
- Any future live write has a preflight estimate and uses better batch sizing.
- The current namespace is either intentionally retained or deleted with explicit evidence.

## Progress and notes

- 2026-06-20: Opened plan based on user billing screenshots and pricing notes. No live turbopuffer calls or credential access performed.

## Blockers

Authority decisions required before any live/destructive work:

- Delete, retain, or replace `jellyfish-site-docs-v1`.
- Approve/reject local-first hybrid retrieval.
- Approve a maximum live reindex/query validation budget.
