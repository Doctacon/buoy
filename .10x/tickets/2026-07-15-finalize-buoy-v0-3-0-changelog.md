Status: blocked
Created: 2026-07-15
Updated: 2026-07-15
Parent: .10x/tickets/2026-07-15-buoy-v0-3-0-release-plan.md
Depends-On: .10x/tickets/2026-07-15-create-buoy-v0-3-0-github-release.md

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

Hosted v0.3.0 release dependency only.

## Progress and notes
