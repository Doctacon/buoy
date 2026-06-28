Status: blocked
Created: 2026-06-20
Updated: 2026-06-20
Parent: .loom/tickets/2026-06-20-minimize-turbopuffer-rag-cost-plan.md
Depends-On: .loom/evidence/2026-06-20-turbopuffer-billing-cost-signal.md

# Immediate turbopuffer cost containment

## Scope

Decide and, if explicitly approved, execute the immediate action for the existing namespace `jellyfish-site-docs-v1` in `gcp-us-central1`.

Options to present to the user:

1. Delete the namespace now to stop ongoing storage charges.
2. Keep it temporarily until a cheaper replacement is designed and verified.
3. Keep it indefinitely as an MVP reference, accepting continuing storage charges.

In scope after approval:

- Retrieve the API key into shell memory only.
- Run only the minimum non-secret metadata/list/delete calls needed for the approved option.
- Record evidence of the final namespace state without secret values.

Out of scope unless separately approved:

- Reindexing.
- Live retrieval/evals.
- Copying the namespace.
- Persisting credentials.

## Acceptance criteria

- The ticket records the user's explicit choice.
- If deletion is approved, evidence confirms the namespace was deleted or no longer listed.
- If retention is chosen, evidence records that retention was intentional and why.
- No secrets are written to disk or Loom records.

## Progress and notes

- 2026-06-20: Ticket opened blocked because namespace deletion/retention is an authority decision.

## Blockers

- Waiting for user authority decision: delete now, keep until replacement, or keep indefinitely.
