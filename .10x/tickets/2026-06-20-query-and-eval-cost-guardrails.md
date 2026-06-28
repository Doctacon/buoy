Status: open
Created: 2026-06-20
Updated: 2026-06-20
Parent: .loom/tickets/2026-06-20-minimize-turbopuffer-rag-cost-plan.md
Depends-On: .loom/tickets/2026-06-20-turbopuffer-cost-audit-estimator.md, .loom/knowledge/turbopuffer-cost-model.md

# Query and eval cost guardrails

## Scope

Make it hard to accidentally run expensive live turbopuffer operations from the CLI or docs.

In scope:

- Update README and `docs/agent-answering-workflow.md` to put cost warnings before live commands.
- Change examples to one-query, tiny-limit commands when the goal is observing bill changes.
- Make live evals print the number of queries and require an explicit confirmation flag if appropriate.
- Consider lowering `DEFAULT_CANDIDATES` and/or making live defaults different from dry-run/eval defaults.
- Add a `--cost-plan` or similar dry-run output that shows whether a command will call turbopuffer and what it will request/return.
- Ensure docs say not to rerun `index --write` against the old MVP namespace unless intentionally replacing data.

Out of scope:

- Live query execution.
- Live eval execution.
- Reindexing.

## Acceptance criteria

- The default documented live query example uses minimal limits and explains that it is one billable request.
- The docs clearly warn that `evals --live` runs multiple billable queries.
- CLI output for dry-run plans includes enough cost-shape information to avoid accidental misuse.
- Tests cover any new confirmation/guardrail behavior.

## Progress and notes

- 2026-06-20: Ticket opened only.

## Blockers

- Cost audit should inform the exact wording and defaults.
