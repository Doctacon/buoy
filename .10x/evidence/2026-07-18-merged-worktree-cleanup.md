Status: recorded
Created: 2026-07-18
Updated: 2026-07-18
Relates-To: .10x/tickets/2026-07-18-repository-cleanup-plan.md

# Merged Worktree Cleanup

## What was observed

Before cleanup, `git worktree list` showed the primary `develop` worktree, 28 clean worktrees whose branch names matched merged GitHub PR heads, and two dirty/unmerged worktrees: `work/shape-direct-command-defaults` and `thistle-site-test`.

The containing `turbo-search.worktrees` directory measured 16 GB.

After cleanup:

- all 28 clean merged-PR worktrees were removed with `git worktree remove`;
- `git worktree prune` completed;
- the primary repository and both dirty worktrees remained;
- the worktree directory measured 2.6 GB;
- no local or remote branch was deleted.

Removed branches/worktrees:

- `work/add-automatic-production-namespace-routing`
- `work/atomic-remote-catalog-cutover`
- `work/backfill-live-namespace-catalog`
- `work/build-production-local-namespace-catalog`
- `work/build-remote-routing-backend`
- `work/close-buoy-v0-3-0-release`
- `work/close-remote-catalog-cutover`
- `work/create-buoy-v0-3-0-release`
- `work/finalize-buoy-v0-3-0-changelog`
- `work/integrate-approved-apply-catalog-registration`
- `work/migrate-local-state-root`
- `work/prepare-buoy-v0-3-0`
- `work/promote-develop-main-v0-3-0`
- `work/reconcile-data-vault-analogy`
- `release/v0.3.0-sync`
- `work/research-data-vault-concept-graph`
- `work/research-data-vault-multihop`
- `work/research-data-vault-namespace-routing`
- `work/research-data-vault-tagging`
- `work/research-metadata-tagging-data-vault`
- `work/reshape-semantic-routing-experiment`
- `work/review-semantic-routing-workstream`
- `work/run-representative-semantic-routing-experiment`
- `work/shape-default-auto-route`
- `work/shape-production-semantic-routing`
- `work/shape-remote-routing-catalog`
- `work/shape-semantic-routing-pilot`
- `work/shape-v0-3-0-release`

## Procedure

1. Re-ran `git status --short --branch` and `git worktree list`.
2. Loaded merged PR head names with `gh pr list --state merged --limit 200 --json headRefName`.
3. For each linked worktree, required exact branch membership in that merged-head set and an empty `git status --porcelain`.
4. Removed only matches with `git worktree remove`.
5. Ran `git worktree prune`, listed survivors, and remeasured disk.

## What this supports

The cleanup removed only clean linked checkouts whose work had durable merged PR history, while preserving all dirty/unmerged work. It recovered approximately 13.4 GB of local disk.

## Limits

This evidence does not prove the corresponding local/remote branch refs are unnecessary; none were deleted. It does not classify ignored artifacts inside surviving worktrees or the main repository.
