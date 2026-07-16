Status: done
Created: 2026-07-15
Updated: 2026-07-15
Parent: .10x/tickets/2026-07-15-buoy-v0-3-0-release-plan.md
Depends-On: .10x/tickets/done/2026-07-15-prepare-buoy-v0-3-0.md

# Promote Develop to Main for v0.3.0

## Scope

- Verify release-prepared `develop`, current `main`, protection, no conflicting open release PR, and exact divergence.
- Open the release pull request `develop -> main` against exact current refs. The originally ratified expected-head-bound update-branch endpoint was attempted and failed without ref mutation; preserve that evidence.
- Under the user-ratified replacement mechanism, create `release/v0.3.0-sync` from exact release-ready develop, merge exact current main into it with a merge commit, verify content neutrality and exact ancestry, and open a protected PR to develop. Require Python 3.11, Python 3.13, Build distributions, strict freshness, and independent review. Merge that sync PR only with a merge commit; never direct-push, rebase, squash, or weaken protection.
- After the sync merge, verify develop contains both the prior release-ready develop and exact current main, then require release PR #22 to rerun strict-freshness checks at the updated develop head.
- Independently review the complete release diff and release metadata.
- Merge with a merge commit, never squash/rebase.
- Verify resulting `main` has `develop` as an ancestor and observe successful push CI.

## Acceptance criteria

- The failed expected-head-bound update-branch operation and unchanged refs remain durably recorded.
- The replacement sync branch begins at exact release-ready develop and contains a merge commit whose exact other parent is current main, with no content change from release-ready develop.
- Its protected PR to develop passes all required checks and independent review before a merge-commit-only integration.
- Current main ancestry is contained by release-ready develop before promotion.
- Release PR contains exactly reviewed develop changes and reports mergeable/clean.
- All required checks and independent review pass.
- GitHub records a merge commit on main with both prior main and release-ready develop ancestry.
- Local/remote main and develop refs plus release commit are recorded without source mutation after review.

## Explicit exclusions

Tag/release creation, version changes, branch-protection changes, force push, squash/rebase, PyPI, Turbopuffer.

## References

- `.10x/specs/protected-github-branches.md`
- `.10x/decisions/protected-development-and-github-release-governance.md`

## Evidence expectations

Pre/post commit graph, PR/check URLs, merge method/parents, main push CI, diff summary, and independent review.

## Blockers

None. Protected sync PR #23 and release PR #22 were merged with verified merge commits; main push CI, durable independent review, closure mapping, and dependent-child unblocking are complete. The prior failed update-branch evidence remains authoritative history.

## Progress and notes

- 2026-07-15: Promotion pre-merge execution started from release-prepared develop `1441c14`; no main merge is authorized in this phase.
- 2026-07-15: Preflight passed and release PR #22 was opened at exact head `1441c142dae2f501fd8d7306ab3bf1a9db1532d2` against exact main `1fa99431de85b9de435250f273919bf2d247d1fc`. The expected-head-bound update request failed HTTP 422 without moving either ref. Execution stopped per contract. Evidence: `.10x/evidence/2026-07-15-buoy-v0-3-0-promotion-update-branch-blocker.md`.
- 2026-07-15: User explicitly ratified a dedicated protected sync-PR mechanism. Fresh remote preflight confirmed the required exact refs and no existing sync branch/PR; execution resumed only through sync PR readiness, not merge.
- 2026-07-15: Created ancestry-only merge commit `e32061ea33f4efe41cd4288e85083748fd0102fc` with exact parents develop `1441c142dae2f501fd8d7306ab3bf1a9db1532d2` and main `1fa99431de85b9de435250f273919bf2d247d1fc`; its tree equals release-prepared develop and remains version 0.3.0. Sync PR #23 became exact, `MERGEABLE`/`CLEAN`, with all three required checks passing. Readiness evidence: `.10x/evidence/2026-07-15-buoy-v0-3-0-sync-pr-readiness.md`.
- 2026-07-15: Post-merge verification passed. PR #23 merge commit `5658fe4cc5c12b80d8fd64aa7963f5f1907133db` has exact base/sync parents; PR #22 release merge `595d157177bd032c20cf6e6c0112ee6b43212a88` has exact prior-main/synced-develop parents. All release-prepared/sync/develop/main trees are identical, develop is an ancestor of main, fresh release PR checks passed, and exact main push CI run `29537732717` passed all three required jobs. Evidence: `.10x/evidence/2026-07-15-buoy-v0-3-0-main-promotion.md`. Ticket remains active pending parent durable review/closure; no tag/Release action occurred.

- 2026-07-15: Durable review confirms the two independent pass reviews occurred before PR #23 and PR #22 merges, with exact session timestamps and reviewed heads. Review: `.10x/reviews/2026-07-15-buoy-v0-3-0-main-promotion-review.md`.

## Closure mapping

- Protected ancestry: user-ratified PR #23 preserved exact main/develop ancestry with zero content change and merge-commit integration.
- Release promotion: PR #22 merged with merge commit `595d157177bd032c20cf6e6c0112ee6b43212a88`, exact prior-main/develop parents, and identical release-ready tree.
- Required PR, develop-push, and main-push checks passed; version is 0.3.0.
- Independent reviews passed before each merge and post-merge evidence verified hosted state.
- No tag, GitHub Release, PyPI, source change, or Turbopuffer operation occurred in this child.

## Retrospective

Protected update-branch can be rejected when head-branch protection requires PRs. A dedicated ancestry-only release-sync PR with a reviewed merge commit preserves both histories without weakening protection. Review-harness results must be durably recorded before closure even when GitHub requires zero hosted approvals.
