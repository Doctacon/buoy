Status: superseded
Created: 2026-08-13
Updated: 2026-08-13

# v0.5.1 One-Time Manual Security Release

## 2026-08-13 disposition

This one-time publication authority was consumed and no longer grants release
or ref-write authority. Automatic publication remains paused under
`.10x/decisions/release-publication-is-paused.md`; the decision below is
retained as the historical release contract.

## Decision

Authorize one manual GitHub-only v0.5.1 release containing the GitHub
repository containment fix and minimum installation/first-index onboarding.
The write-capable workflow remains disabled.

The release must come from the separately reviewed and promoted `main` commit,
after the complete Python 3.11/3.13 and distribution checks pass. It creates an
annotated `v0.5.1` tag and a non-draft GitHub Release containing exactly the
`buoy_search-0.5.1-py3-none-any.whl` and `buoy_search-0.5.1.tar.gz` assets. The
downloaded assets must match the locally recorded SHA-256 digests, and the
published wheel must pass a clean install and offline CLI/tokenizer smoke test
before the draft security advisory is published. GitHub artifact attestations
for both assets are verified if the available authenticated tooling can produce
them without changing the assets. The local manual path has no Actions OIDC
issuer, so an exact annotated tag, source commit, and downloaded SHA-256
evidence are the required one-time authority and the limitation is recorded.
Before tag creation, the artifacts are built with exact
`SETUPTOOLS_SCM_PRETEND_VERSION=0.5.1` and the deterministic environment in
`docs/releasing.md`; the release evidence binds that command and both digests
to the exact promoted commit. A separate reviewed post-release documentation
PR dates v0.5.1 and moves the read-only validator's published-history baseline
through v0.5.1.

## Fail-closed boundary

The existing v0.5.0 lightweight tag and asset-less Release are immutable
history. If any v0.5.1 tag, Release, or asset exists before creation, or if a
write leaves partial hosted state, stop without moving, overwriting, or
deleting it and require a new reviewed recovery decision.

## Exclusions

No PyPI publication, Turbopuffer operation, namespace or stale-row mutation,
branch-protection change, direct or force push, reusable release automation,
or unrelated product work is authorized. Automatic publication remains paused
after v0.5.1.

The one annotated `v0.5.1` tag-ref push described in `docs/releasing.md` is the
only direct ref creation authorized here. “No direct push” continues to apply
to `main` and `develop`; task branches still use ordinary reviewed PRs.

## Execution record

The one-time authority was consumed on 2026-08-13. PR #101 integrated the
reviewed change to `develop` as
`f68dcf5f0a4352df59e14ca1d78bef1ea1b7f6ee`; PR #102 merge-committed that tree
to `main` as `284b309a02546b13a63e709d9afe7f72c557b474`. Annotated tag v0.5.1
(tag object `081b128c9f02761342e473e4faf7d034c7097627`) and GitHub Release
369682440 were published and verified before GHSA-q6rp-r8g8-5xgh was
published. Exact asset evidence is in
`.10x/evidence/2026-08-13-buoy-v0-5-1-github-release.md`.

This completed exception grants no future publication authority. Automatic
publication remains paused, and the exclusions above remain in force.
