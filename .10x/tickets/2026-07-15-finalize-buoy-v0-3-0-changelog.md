Status: active
Created: 2026-07-15
Updated: 2026-07-16
Parent: .10x/tickets/2026-07-15-buoy-v0-3-0-release-plan.md
Depends-On: .10x/tickets/done/2026-07-15-create-buoy-v0-3-0-github-release.md

# Finalize Buoy v0.3.0 Changelog

## Scope

After the hosted v0.3.0 Release and provenance are verified, replace the pending 0.3.0 changelog marker with the observed release date, add the exact v0.3.0 release link, and advance the Unreleased compare link to `v0.3.0...HEAD`. Land this source-only follow-up through a separately reviewed `work/* -> develop` pull request using squash merge.

## Acceptance criteria

- Hosted v0.3.0 exists and supplies the authoritative release date/link before edits.
- Changelog version/date/release link and Unreleased comparison are exact and internally consistent.
- No main/tag/release/workflow/asset mutation occurs in this child.
- Required CI and independent review pass before integration to develop.
- Parent release plan may close after this child and graph reconciliation.

## Explicit exclusions

Changing the already-published tag/Release/assets, promoting this follow-up to main before a later release, feature changes, PyPI, Turbopuffer.

## References

- `docs/releasing.md`
- `.10x/specs/buoy-ci-and-github-releases.md`

## Evidence expectations

Observed hosted release metadata, exact changelog diff, task PR/check URLs, and independent review.

## Blockers

None. Hosted v0.3.0 release completed and passed independent review.

## Progress and notes

- 2026-07-16: Verified existing release evidence and current public Git state: annotated `v0.3.0` object `21a8d122151711a863dfb63d356baebbddca8d45` peels to reviewed main `595d157177bd032c20cf6e6c0112ee6b43212a88`; the public release URL returned HTTP 200 and its page reports release time `2026-07-16T22:17:09Z`. GitHub's JSON release API was transiently unavailable with HTTP 503, so the change uses the already-reviewed release evidence plus the current public tag/page observations.
- 2026-07-16: Updated only the scoped changelog metadata: finalized v0.3.0 as `2026-07-16`, added its exact GitHub Release link, and advanced Unreleased comparison to `v0.3.0...HEAD` while preserving prior content/links. Evidence: `.10x/evidence/2026-07-16-buoy-v0-3-0-changelog-finalization.md`. Ticket remains active pending independent review and hosted PR checks.
- 2026-07-16: Restored an accidentally emptied release-automation test file from `HEAD`, then made only the required 6-addition/3-deletion changelog assertion update. Focused 10 tests and all 364 tests passed, along with release tag dry-check, compilation, documentation references, and diff hygiene. No hosted mutation occurred.
