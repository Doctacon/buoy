Status: done
Created: 2026-07-15
Updated: 2026-07-20
Parent: None
Depends-On: None

# Buoy v0.3.0 Release Plan

## Outcome

Release the integrated production semantic-routing work as GitHub-only Buoy v0.3.0. The user explicitly selected v0.3.0 and retained deprecated `turbo-search` / `TURBO_SEARCH_*` compatibility through 0.3, moving the announced removal target to 0.4.

## Child sequence

1. `.10x/tickets/done/2026-07-15-prepare-buoy-v0-3-0.md`
2. `.10x/tickets/done/2026-07-15-promote-develop-to-main-for-v0-3-0.md`
3. `.10x/tickets/done/2026-07-15-create-buoy-v0-3-0-github-release.md`
4. `.10x/tickets/done/2026-07-15-finalize-buoy-v0-3-0-changelog.md`

Children are strictly sequential. The parent is not executable.

## Aggregate acceptance criteria

- Project/module/lock/build metadata consistently report 0.3.0.
- Changelog describes the catalog, apply registration/recovery, automatic routing, and state-root/deprecation posture without claiming unsupported behavior.
- `develop` incorporates current `main` ancestry before the release merge.
- A passing release PR merges `develop` into `main` with a merge commit, never squash/rebase.
- Annotated `v0.3.0` points to the reviewed main commit and authoritative remote metadata reports a tag object.
- The approval-gated GitHub workflow publishes wheel/sdist, generated notes, and provenance successfully.
- No PyPI, branch-protection change, tag overwrite, force push, or Turbopuffer operation occurs.
- The post-release changelog finalization lands through a separately reviewed task PR after hosted release verification.
- Evidence and independent reviews support every child before closure.

## Explicit exclusions

- Removing deprecated command/environment aliases or `.turbo-search` compatibility.
- New product behavior beyond release metadata/docs necessary for 0.3.0.
- PyPI or other registry publication.
- Turbopuffer reads/writes.

## Progress and notes

- 2026-07-15: User selected v0.3.0 rather than merge-only or v0.2.2, and selected retaining deprecated command/environment aliases through 0.3 with removal target moved to 0.4.
- 2026-07-15: Current remote divergence is one main-only release merge commit and sixteen develop-only integration commits; release preparation must preserve ancestry rather than flatten it.

- 2026-07-15: Preparation child completed after local, independent, and hosted validation and was integrated through PR #21.
- 2026-07-15: Protected promotion completed technically: ancestry-only sync PR #23 produced develop `5658fe4cc5c12b80d8fd64aa7963f5f1907133db`; release PR #22 produced main `595d157177bd032c20cf6e6c0112ee6b43212a88`; exact main push CI passed. Promotion child remains active pending parent durable review/closure before release publication is unblocked. Evidence: `.10x/evidence/2026-07-15-buoy-v0-3-0-main-promotion.md`.

- 2026-07-15: Main promotion completed through protected ancestry-sync PR #23 and merge-commit release PR #22. Main is `595d157`; release publication child is unblocked.

- 2026-07-16: Annotated v0.3.0 and GitHub Release completed with verified assets/provenance and passing independent review. Changelog finalization child is unblocked.

- 2026-07-16: Final changelog PR #26 passed review/checks and integrated to develop as `ef7b554`. All four children and aggregate acceptance criteria are technically satisfied; parent remains open pending final graph review and closure reconciliation.

- 2026-07-16: Holistic closure review passed after all four children integrated: `.10x/reviews/2026-07-16-buoy-v0-3-0-release-closure-review.md`.

## Closure mapping

- Preparation: 0.3.0 metadata, complete pending changelog, retained aliases through 0.3, local/hosted validation, and independent review.
- Promotion: protected ancestry-only PR #23 and merge-commit release PR #22 produced main `595d157177bd032c20cf6e6c0112ee6b43212a88` with required checks and reviews.
- Publication: annotated tag object `21a8d122151711a863dfb63d356baebbddca8d45`, approval-gated run `29538957482`, Release `355388511`, exact wheel/sdist digests, and verified SLSA provenance.
- Finalization: PR #26 integrated the authoritative release date/link and advanced the Unreleased comparison on develop.
- Boundaries: no PyPI, protection weakening, force push, tag overwrite, source mutation outside governed PRs, or Turbopuffer operation.

## Retrospective

Key durable lessons are already captured in child records: derive changelogs from the full prior-tag range; test compatibility schedule text precisely; use a protected ancestry-only merge PR when update-branch cannot mutate a protected head; durably record harness reviews with their actual pre-merge chronology; distinguish tag push from environment-gated publication; and date temporal evidence from authoritative hosted events. The Node 24 action warning already has owner `.10x/tickets/done/2026-07-14-update-node24-github-actions.md`. No additional follow-up is required.
