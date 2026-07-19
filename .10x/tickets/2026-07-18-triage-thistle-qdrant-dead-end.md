Status: blocked
Created: 2026-07-18
Updated: 2026-07-18
Parent: .10x/tickets/2026-07-18-repository-cleanup-plan.md
Depends-On: .10x/tickets/2026-07-18-direct-command-defaults-plan.md

# Triage Thistle/Qdrant Dead End

## Scope

Inspect the complete dirty `thistle-site-test` worktree before deletion and classify every tracked/untracked change as:

- product-neutral behavior still absent from current Buoy;
- historical evidence/record worth preserving;
- Qdrant/Tantivy/superseded-package-specific work to retire;
- generated/ignored state safe to delete only after all preservation owners close.

For product-neutral behavior, compare the current Turbopuffer architecture and active specifications, then create focused draft/active specs and bounded child tickets only where semantics are already record-backed or user-ratified. Exact-host redirect safety is a safety candidate; exact-chunk deduplication/citation aliases require explicit reconciliation with current row/citation contracts rather than mechanical copying.

This ticket is investigation and disposition only. It MUST NOT modify current source, run live crawls, start Qdrant, mutate remote services, or delete the dirty worktree.

## Acceptance criteria

- Inventory all modified/untracked paths and unique commits in `thistle-site-test` against current `develop`.
- Preserve or index unique evidence/reviews/specs/tickets with provenance and current authority status; do not activate superseded Qdrant behavior.
- Establish whether current Buoy still lacks final-response exact-host enforcement and record the smallest current-architecture repair owner if needed.
- Reconcile the old dedup/alias contract against current Turbopuffer row IDs, retrieval output, and citation behavior; unresolved semantics remain blocked/draft.
- Cancel or supersede old Qdrant smoke tickets with explicit no-action rationale once valuable findings have owners.
- Produce a deletion manifest proving no unique durable work remains only if deletion becomes safe.

## Evidence expectations

Path/commit inventory, current-vs-branch behavior matrix, record provenance map, source references, and exact remaining/deletable paths.

## Blockers

The direct-command-defaults plan must integrate first under the user-selected sequence. Deduplication/citation semantics may require a separate user checkpoint after source comparison.

## Explicit exclusions

Porting the Qdrant backend; running Thistle/Mercury crawls; deleting Qdrant volumes/collections, remote Turbopuffer data, ignored artifacts, branches, or worktrees; silently activating old specs.

## References

- `.10x/tickets/2026-07-18-repository-cleanup-plan.md`
- `.10x/research/2026-07-18-repository-dead-end-inventory.md`

## Progress and notes
