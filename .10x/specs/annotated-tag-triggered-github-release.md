Status: active
Created: 2026-08-19
Updated: 2026-08-20
Decision: .10x/decisions/annotated-tag-triggered-github-releases.md

# Annotated-Tag-Triggered GitHub Release

## Source and approval

Release preparation must leave an empty Unreleased section, place the latest
notes under one dated stable SemVer heading, add the canonical previous-tag
comparison link, update the README wheel URL, and mark the latest version
supported. The exact release source must be on `main` with passing CI.

One annotated `vX.Y.Z` tag, whose message is `Buoy vX.Y.Z` and whose peel is
the exact reviewed main commit, is the sole human publication action.
Lightweight, moved, malformed, or version-mismatched tags fail before release
creation.

## Workflow

The tag workflow must:

1. default to `contents: read`, use non-cancelling per-tag concurrency, and pin
   every third-party Action to a full commit SHA;
2. independently run the locked Python 3.11 and 3.13 suites plus source,
   ranking, C6, and lock validation;
3. build exactly one wheel and one sdist on Python 3.13, require tag-derived
   version/filenames/metadata, and clean-install/smoke the wheel;
4. retain the exact pair and reviewed changelog notes as one short-lived
   Actions artifact;
5. give write, OIDC, and attestation permissions only to the final publication
   job and attest both distributions; repository-admin preflight separately
   requires immutable Releases enabled because the workflow token has no
   administration permission;
6. create a draft non-prerelease GitHub Release with exactly those two assets,
   verify its numeric-ID asset downloads byte-for-byte, and publish the same
   Release as latest; and
7. read back the immutable published Release, exact annotated tag, two asset
   names/digests, latest identity, and downloaded bytes.

An exact rerun after the matching Release is already successfully published
is a read-only verification no-op. Any failed run or unpublished hosted state
is a stop for read-only inspection and may not be blindly rerun; the owner
must choose the next separately reviewed action from the exact observed state.
An exact complete draft is the only unpublished state this standing workflow
can resume after that inspection and choice. Any mismatched, ambiguous,
duplicated, or corrupt state fails without deletion, replacement, force, or
blind retry.

After a successful or stopped run, the ordinary task closes its ticket and
evidence through a separately reviewed records-only change. That closure may
record hosted facts and statuses only; it performs no tag, Release, asset,
attestation, registry, provider, or user-home mutation.

## Invocation history and first successful publication

The first invocation was v0.6.0. Its exact annotated tag remains fixed at
`701d73ebbf6a8c3b2c664a0295374dcb4283283c`, but both locked test jobs stopped
on a non-hermetic fixture that assumed an editable checkout always has a
development version. Build and publication were skipped, leaving zero workflow
artifacts and no v0.6.0 Release, asset, or attestation. That tag must never be
deleted, recreated, overwritten, moved, or used by a recovery/manual-dispatch
path.

The first eligible successful publication is v0.6.1. Its ordinary reviewed
release-preparation task must correct the public version surfaces and make the
VCS-version fixture hermetic by constructing controlled post-tag history. The
fix reaches `develop` through an ordinary task PR and `main` through the normal
release PR merge commit. Exact-main CI must pass; the v0.6.1 tag and Release
must be absent; immutable Releases must remain enabled; and the normal
annotated `v0.6.1` tag push is the sole publication action. Publication is
GitHub-only and contains exactly
`buoy_search-0.6.1-py3-none-any.whl` and
`buoy_search-0.6.1.tar.gz`.

## Acceptance

- Focused workflow/validator tests and the full locked 3.11/3.13 suites pass.
- Release readiness retains its four read-only check names and validates the
  exact prospective version.
- The public v0.6.1 tag is annotated and the Release is immutable/latest with
  exactly two verified assets and build attestations.
- A clean downloaded-wheel smoke reports 0.6.1.
- No PyPI, provider, model, user-home, or unrelated repository effect occurs.
