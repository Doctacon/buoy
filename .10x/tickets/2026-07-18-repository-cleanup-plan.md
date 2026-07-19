Status: open
Created: 2026-07-18
Updated: 2026-07-18
Parent: None
Depends-On: .10x/tickets/done/2026-07-18-direct-command-defaults-plan.md

# Repository Cleanup Plan

## Outcome

After the direct-command-defaults plan integrates, remove source-proven dead code and record debris, preserve valuable work from the abandoned Qdrant branch before retiring it, and shape the separately governed 0.4 compatibility removal without deleting active evidence or intentional compatibility.

The already authorized clean merged-worktree cleanup is complete and recorded at `.10x/evidence/2026-07-18-merged-worktree-cleanup.md`.

## Child sequence

1. `.10x/tickets/done/2026-07-18-triage-thistle-qdrant-dead-end.md`
2. `.10x/tickets/2026-07-18-remove-unreachable-local-catalog-persistence.md`
3. `.10x/tickets/2026-07-18-normalize-terminal-ticket-placement.md`
4. `.10x/tickets/2026-07-18-review-stale-ticket-statuses.md`
5. `.10x/tickets/2026-07-18-shape-v0-4-compatibility-removal.md`

Thistle triage must complete before deleting its dirty worktree. Source cleanup follows the direct-command integration to avoid parallel changes against moving CLI/catalog contracts. Record placement precedes status review so closure checks use the canonical graph. Compatibility shaping is last so it builds on the cleaned current state. The parent is not executable.

## Aggregate acceptance criteria

- Dirty/unmerged work is never deleted before durable classification and salvage/disposition.
- Product-neutral Thistle exact-host crawler safety receives a durable repair owner; exact-chunk dedup is retired/no-action with only historical non-authoritative provenance preserved; Qdrant-specific work is retired only with preserved inventory evidence and coherent ticket statuses.
- Only production-unreachable local-catalog persistence code/tests are removed; active card/schema/remote/migrate-local behavior remains.
- All already-terminal tickets live in terminal directories with repaired references.
- Stale open/active/blocked tickets receive evidence-backed closure, cancellation/no-action rationale, or explicit remaining blockers; no closure evidence is invented.
- 0.4 compatibility removal is shaped as an explicit contract and bounded tickets, not implemented opportunistically.
- Ignored artifacts, active local state, remote namespaces, release branches/tags, and the two current dirty worktrees remain untouched unless a child explicitly governs them.

## Explicit exclusions

Deleting ignored `artifacts/`, `.buoy/`, credentials, remote namespaces, local/remote branches, release tags, the current direct-command worktree, or the Thistle worktree before triage; changing retrieval tags; implementing Node.js action upgrades; broad refactoring.

## References

- `.10x/research/2026-07-18-repository-dead-end-inventory.md`
- `.10x/evidence/2026-07-18-merged-worktree-cleanup.md`
- `.10x/tickets/done/2026-07-18-direct-command-defaults-plan.md`

## Progress and notes

- 2026-07-18: User authorized the recommended cleanup sequence. Removed 28 clean worktrees tied to merged PRs, preserved both dirty/unmerged worktrees, and recovered approximately 13.4 GB.
- 2026-07-18: Independent shaping review passed with no blockers. Review: `.10x/reviews/2026-07-18-repository-cleanup-shaping-review.md`.
- 2026-07-18: Thistle/Qdrant triage integrated at `f9fd5b3` with preservation/disposition review pass. After exact HEAD/status-manifest revalidation, removed the retired dirty worktree and local `thistle-site-test` branch under the merged deletion manifest. No external provider/container or unrelated repository state was touched. Evidence: `.10x/evidence/2026-07-18-thistle-worktree-deletion.md`.
- 2026-07-18: Post-merge audit found the exact-host spec cited an original untracked ticket as if it were addressable at commit `d7a37d7`. Repaired the provenance paragraph to cite the merged disposition research and exact path/hash inventories while stating that the retired untracked files are historical provenance, not current authority. Review: `.10x/reviews/2026-07-18-thistle-provenance-reference-repair-review.md`.
- 2026-07-18: User superseded the earlier dedup-reconciliation direction: retire exact-chunk dedup, preserve it only as historical non-authority, and salvage only the exact-host behavior from the dirty implementation.
