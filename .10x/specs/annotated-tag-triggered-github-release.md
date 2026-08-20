Status: active
Created: 2026-08-19
Updated: 2026-08-19
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

An exact completed rerun is a read-only no-op. An exact complete draft may
continue to publication. Any mismatched, ambiguous, duplicated, corrupt, or
partial state fails without deletion, replacement, force, or blind retry.

After a successful or stopped run, the ordinary task closes its ticket and
evidence through a separately reviewed records-only change. That closure may
record hosted facts and statuses only; it performs no tag, Release, asset,
attestation, registry, provider, or user-home mutation.

## First invocation

The first invocation is v0.6.0. Before its tag push, the exact workflow must be
reviewed and integrated, exact-main CI must pass, v0.6.0 tag/Release state must
be absent, and repository immutable Releases must be enabled. Publication is
GitHub-only and contains exactly `buoy_search-0.6.0-py3-none-any.whl` and
`buoy_search-0.6.0.tar.gz`.

## Acceptance

- Focused workflow/validator tests and the full locked 3.11/3.13 suites pass.
- Release readiness retains its four read-only check names and validates the
  exact prospective version.
- The public v0.6.0 tag is annotated and the Release is immutable/latest with
  exactly two verified assets and build attestations.
- A clean downloaded-wheel smoke reports 0.6.0.
- No PyPI, provider, model, user-home, or unrelated repository effect occurs.
