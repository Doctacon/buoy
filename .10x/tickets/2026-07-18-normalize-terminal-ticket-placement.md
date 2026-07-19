Status: blocked
Created: 2026-07-18
Updated: 2026-07-18
Parent: .10x/tickets/2026-07-18-repository-cleanup-plan.md
Depends-On: .10x/tickets/2026-07-18-remove-unreachable-local-catalog-persistence.md

# Normalize Terminal Ticket Placement

## Scope

Mechanically move the 19 `done` and one `cancelled` ticket currently stored directly under `.10x/tickets/` into `.10x/tickets/done/` and `.10x/tickets/cancelled/`, then repair every affected `.10x/` reference.

## Acceptance criteria

- Enumerate exact source/destination paths and refuse collisions.
- Move only tickets whose existing status is already terminal; do not alter status, semantics, progress history, or closure claims.
- Repair all Markdown path references across `.10x/` while preserving historical meaning.
- No top-level ticket has `done` or `cancelled` status afterward.
- No `.10x/` Markdown reference points to a missing path; `git diff --check` passes.
- Independent record review confirms no active authority was changed.

## Evidence expectations

Before/after terminal inventory, move map, reference validation count, diff check, and no source/runtime changes.

## Blockers

Run after source cleanup integration under the selected sequence.

## Explicit exclusions

Closing, cancelling, rewriting, or deleting any ticket; changing source/tests/docs outside reference repair; moving evidence/reviews/research.

## References

- `.10x/tickets/2026-07-18-repository-cleanup-plan.md`
- `.10x/research/2026-07-18-repository-dead-end-inventory.md`

## Progress and notes
