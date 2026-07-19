Status: done
Created: 2026-07-18
Updated: 2026-07-18
Parent: .10x/tickets/2026-07-18-repository-cleanup-plan.md
Depends-On: .10x/tickets/done/2026-07-18-direct-command-defaults-plan.md

# Triage Thistle/Qdrant Dead End

## Scope

Inspect the complete dirty `thistle-site-test` worktree before deletion and classify every tracked/untracked change as:

- product-neutral behavior still absent from current Buoy;
- historical evidence/record worth preserving;
- Qdrant/Tantivy/superseded-package-specific work to retire;
- generated/ignored state safe to delete only after all preservation owners close.

For product-neutral behavior, compare the current Turbopuffer architecture and active specifications, then create focused draft/active specs and bounded child tickets only where semantics are already record-backed or user-ratified. Exact-host redirect safety is the only dirty implementation behavior to salvage. Exact-chunk deduplication/citation aliases are retired by final user direction; preserve their provenance only as historical non-authority and port no behavior.

This ticket is investigation and disposition only. It MUST NOT modify current source, run live crawls, start Qdrant, mutate remote services, or delete the dirty worktree.

## Acceptance criteria

- Inventory all modified/untracked paths and unique commits in `thistle-site-test` against current `develop`.
- Preserve or index unique evidence/reviews/specs/tickets with provenance and current authority status; do not activate superseded Qdrant behavior.
- Establish whether current Buoy still lacks final-response exact-host enforcement and record the smallest current-architecture repair owner if needed.
- Record explicit cancelled/no-action disposition for the old dedup/alias contract; retain no current active/draft spec or executable/blocked implementation ticket.
- Cancel or supersede old Qdrant smoke tickets with explicit no-action rationale once valuable findings have owners.
- Produce a deletion manifest proving no unique durable work remains only if deletion becomes safe.

## Evidence expectations

Path/commit inventory, current-vs-branch behavior matrix, record provenance map, source references, and exact remaining/deletable paths.

## Blockers

None. The deletion manifest becomes effective only after this preservation PR merges.

## Explicit exclusions

Porting the Qdrant backend; running Thistle/Mercury crawls; deleting Qdrant volumes/collections, remote Turbopuffer data, ignored artifacts, branches, or worktrees; silently activating old specs.

## References

- `.10x/tickets/2026-07-18-repository-cleanup-plan.md`
- `.10x/research/2026-07-18-repository-dead-end-inventory.md`
- `.10x/research/2026-07-18-thistle-qdrant-dead-end-disposition.md`
- `.10x/evidence/2026-07-18-thistle-qdrant-dead-end-disposition.md`
- `.10x/tickets/cancelled/2026-07-18-reconcile-website-exact-chunk-deduplication.md`

## Progress and notes

- 2026-07-18: Inventoried 17 tracked-modified and 91 untracked dirty paths plus 288 path entries across the two unique branch commits. Preserved exact status, content hashes, classifications, provenance, and current authority in the storage inventories and disposition research.
- 2026-07-18: Confirmed current Buoy lacks final-response/per-hop exact-host enforcement. Preserved the historical safety contract as active `.10x/specs/website-exact-host-crawl-boundary.md` and opened the bounded current repair ticket.
- 2026-07-18: Applied final user ratification: removed the drafted current dedup spec, cancelled/no-actioned its port, and retained the old implementation/spec/evidence/review only as historical path/hash provenance.
- 2026-07-18: Kept sitemap resource-limit and MarkItDown normalization owners because current source plus prior ratified records prove those gaps. Discarded speculative compact-plan and namespace-deletion drafts because no current measurement/request proves a need.
- 2026-07-18: Cancelled the two Qdrant smoke tickets only after their results and hashes were preserved. Produced an exact post-merge deletion manifest without touching the dirty worktree or external state.
- 2026-07-18: Record-only branch became ready for independent review; deletion remained forbidden pending review and merge.
- 2026-07-18: Independent review passed at commit `32b0d6e` with exact Thistle HEAD/status/content hashes unchanged. Review: `.10x/reviews/2026-07-18-thistle-qdrant-dead-end-disposition-review.md`.

## Closure mapping

- Complete dirty/unique-commit inventory: storage manifests and evidence counts/hashes.
- Durable preservation and authority classification: disposition research, active safety/robustness specs and tickets, cancelled historical Qdrant/dedup tickets.
- Exact-host current gap: current-source comparison, active focused spec, and bounded repair owner.
- Dedup retirement: explicit user decision, cancelled no-action ticket, and absence of active/draft implementation authority.
- Qdrant ticket retirement: preserved outcomes/provenance before cancellation.
- Deletion safety: exact post-merge manifest, excluded external state, and independent pass review.

## Retrospective

A dirty dead-end branch can contain both obsolete architecture and valuable product-neutral findings. Classifying every path before deletion preserved crawl safety and normalization contracts without importing Qdrant or dedup complexity. Future provider cutovers should separate behavioral evidence from provider-specific implementation earlier so retirement does not require forensic recovery.
