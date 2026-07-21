Status: open
Created: 2026-07-21
Updated: 2026-07-21
Parent: .10x/tickets/2026-07-21-buoy-v0-4-0-release-plan.md
Depends-On: .10x/tickets/done/2026-07-21-validate-buoy-v0-4-0-release-candidate.md

# Promote Develop to Main for v0.4.0

## Scope

- Verify release-ready `develop`, current `main`, branch protection, historical PR #80, exact divergence, and no conflicting release operation; because PR #80 is closed at a stale conflicting head, open one replacement `develop -> main` release PR after the ancestry/governance records integrate.
- Create a dedicated ancestry-sync branch from exact release-ready `develop`, merge exact current `main` with a merge commit, and prove the resulting tree is content-identical to release-ready `develop` except for this ticket's already-reviewed release records where applicable.
- Open the ancestry-only sync PR to `develop`; require strict freshness, all three checks, exact-parent/tree evidence, and independent review; merge using a merge commit only.
- Revalidate updated `develop` and the replacement release PR, require all checks, any mechanically required last-push approval, and independent complete release-diff review, then merge it to `main` with a merge commit only.
- Verify exact parents/ancestry/tree and passing `main` push CI.

## Acceptance criteria

- Current `main` ancestry reaches `develop` through a protected PR without direct push, squash, rebase, force push, or protection change.
- The sync merge introduces no content from stale `main` over release-ready develop.
- The replacement release PR contains the exact reviewed release candidate, is clean/current, and passes Python 3.11, Python 3.13, and Build distributions.
- The replacement release PR merges with a merge commit whose parents preserve prior main and exact synced develop.
- Resulting `main` tree equals reviewed release-ready develop and main push CI passes.
- Durable evidence and independent review pass; no tag/Release/PyPI/Turbopuffer operation occurs.

## Explicit exclusions

Candidate source changes after review; tag or Release creation; publication; branch protection changes; direct push; squash/rebase; Turbopuffer.

## References

- `.10x/specs/protected-github-branches.md`
- `.10x/decisions/protected-development-and-github-release-governance-v2.md`
- PR #80: `https://github.com/Doctacon/buoy-search/pull/80`
- `.10x/tickets/done/2026-07-15-promote-develop-to-main-for-v0-3-0.md`
- `.10x/evidence/2026-07-21-buoy-v0-4-0-ancestry-sync-readiness.md`
- `.10x/reviews/2026-07-21-buoy-v0-4-0-main-promotion-readiness-review.md`

## Evidence expectations

Exact pre/post refs, divergence, sync commit parents/tree, PR/check URLs, merge methods and parents, reviewed candidate tree identity, main push CI, independent review, and explicit no-publication/no-product-state boundary.

## Blockers

Replacement release PR #85 is content-, ancestry-, and CI-ready but mechanically blocked by retained main `require_last_push_approval=true`. After this record-only citation/review follow-up integrates and PR #85 reruns final-head CI, an eligible reviewer other than latest pusher `Doctacon` must approve that final head. No bypass or self-approval is permitted.

## Progress and notes

- 2026-07-21: Opened after PR #80 reported conflicts between `main` `820b8ab` and `develop` `ce262d4`. The established protected ancestry-only sync mechanism is record-backed from v0.3.0. No branch, PR, ancestry, tag, release, or product state changed.
- 2026-07-21: Reviewed candidate PR #82 integrated as exact release-ready develop `47a0c33c412062f6467b1858e411179bfca60dcf`. Dedicated ancestry merge `1abd9f587d3e188fa19be11755c786d81df3d455` has exact second parent current main `820b8abba4308481eace728203d98f3365154956` and exact tree equality `4c6395c330bb14ab75012d4b82c78f8b9a739aa8` with release-ready develop. Evidence: `.10x/evidence/2026-07-21-buoy-v0-4-0-ancestry-sync-readiness.md`. Independent review passed exact PR #83 head `cf08383f4c62559a29369b33b7d87f38919ad507`; GitHub merged it with merge commit `3dd1c72f5e75785c11530dc24f34067c6983b1c6`, exact parents release-ready develop and reviewed sync head. No direct protected-branch mutation, tag, Release, PyPI, Turbopuffer, or user-state operation occurred.
- 2026-07-21: Hosted inspection found main protection allowed force pushes and required last-push approval, differing from the superseded governance contract. The user explicitly selected `Keep current rules` and then directed release execution. `.10x/decisions/protected-development-and-github-release-governance-v2.md` and `.10x/specs/protected-github-branches.md` retain the exact settings without changing hosted protection and continue to prohibit using force push or bypass. Hosted state also proves PR #80 is closed, conflicting, and pinned to stale head `a2142205cae8ccfce9ed5f4d3b4785413621812b`; replacement PR #85 was opened from current develop.
- 2026-07-21: Independent readiness review passed PR #85 content, ancestry, version, exact-head CI, and merge-commit topology at develop `35cf2d6e4da48a5e84c7f97d9e81e8f13950b504`; review: `.10x/reviews/2026-07-21-buoy-v0-4-0-main-promotion-readiness-review.md`. It remains mechanically blocked on eligible last-push approval. The review also found and this follow-up repairs three non-existent PR #82 SHA citations to actual `278400909596b5644431bd03fe526e600153f152`. No product source, main merge, tag, Release, protection, PyPI, Turbopuffer, or user-state mutation occurred.
