Status: blocked
Created: 2026-07-15
Updated: 2026-07-15
Parent: .10x/tickets/2026-07-15-buoy-v0-3-0-release-plan.md
Depends-On: .10x/tickets/2026-07-15-promote-develop-to-main-for-v0-3-0.md

# Create Buoy v0.3.0 GitHub Release

## Scope

- Preflight reviewed main/version/CI, preserved v0.2.0/v0.2.1 history, absent v0.3.0 conflicts, and the existing release-environment approval gate.
- Create and push annotated `v0.3.0` from the exact reviewed main commit.
- Verify authoritative remote metadata reports object type `tag` and the expected peeled commit.
- Treat annotated-tag creation/push as the first external mutation. Then observe validation/build completion and the release environment wait; approve only the expected commit/version/artifacts. Approval gates provenance attestation and GitHub Release/assets creation, not the earlier tag push.
- Verify terminal workflow success, GitHub Release, wheel/sdist identities and digests, generated notes, and provenance attestation.
- Confirm no PyPI publication and record durable evidence/review.

## Acceptance criteria

- Existing tags/releases remain immutable and no v0.3.0 conflict exists before mutation.
- Annotated v0.3.0 points to exact reviewed main and remote object type is `tag`.
- Tag push occurs only after preflight and is recorded as an external mutation; the later environment approval gates attestation and GitHub Release/assets mutation, and only the expected run is approved.
- GitHub Release contains `buoy_search-0.3.0-py3-none-any.whl` and `buoy_search-0.3.0.tar.gz` with verifiable provenance.
- No PyPI, branch mutation, tag overwrite, source mutation, or Turbopuffer operation occurs.
- Independent review passes before closure.

## Explicit exclusions

Additional source changes, changelog final-link follow-up, PyPI, replacing tags/releases, branch protection, Turbopuffer.

## References

- `.10x/specs/buoy-ci-and-github-releases.md`
- `docs/releasing.md`
- `.10x/tickets/done/2026-07-14-create-buoy-v0-2-1-github-release.md`

## Evidence expectations

Preflight observations; tag object/peeled commit; workflow/run/job/deployment identity; approval boundary; release/assets/checksums/attestation; no-PyPI observation; independent review.

## Blockers

Main-promotion dependency only.

## Progress and notes
