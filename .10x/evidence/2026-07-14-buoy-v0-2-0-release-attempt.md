Status: recorded
Created: 2026-07-14
Updated: 2026-07-14
Relates-To: .10x/tickets/cancelled/2026-07-14-create-buoy-v0-2-0-github-release.md, .10x/tickets/2026-07-14-buoy-public-ci-release-plan.md

# Buoy v0.2.0 GitHub Release Attempt

## Raw evidence

Sanitized repository, environment, tag, workflow, jobs, artifacts, deployment, release, branch-protection, and PyPI observations are retained at `.10x/evidence/.storage/2026-07-14-buoy-v0-2-0-release-attempt.json`. No credentials are stored.

## Preflight

Preflight confirmed:

- canonical public repository `Doctacon/buoy-search`, default branch `main`;
- canonical main and local HEAD at reviewed commit `d846d2b2e965e7f62ff180442724d02705688a1a`;
- main CI run `29359814276` completed successfully;
- project and module version `0.2.0`;
- no pre-existing `v0.2.0` tag or GitHub Release;
- PyPI JSON endpoint for `buoy-search` returned 404;
- `main` remained unprotected as ratified.

## Environment and tag mutation

The GitHub `release` environment was created with one required reviewer, GitHub user `Doctacon` (ID recorded in raw evidence), and `prevent_self_review: false`. This explicitly permits the initiating account to approve its own pending release deployment while still requiring an approval action.

Exactly one annotated tag was created and pushed:

```text
v0.2.0
annotated tag object: 7eef05d045cc7e59000e2e8ae9abd268e2c21c5f
peeled commit: d846d2b2e965e7f62ff180442724d02705688a1a
message: Buoy v0.2.0
```

GitHub's tag API confirms the ref points to an object of type `tag`.

## Hosted workflow failure

Tag push started Release workflow run `29360369610` at the expected commit. The `Validate and build` job failed in its first validation step before dependency sync, tests, build, artifact upload, environment deployment, attestation, or release mutation.

The runner reported:

```text
release tag 'v0.2.0' must be annotated; found Git object type 'commit'
```

The remote tag is annotated, but `actions/checkout` materialized `refs/tags/v0.2.0` as a commit object in that runner checkout. `scripts/release_checks.py tag-object` therefore rejected the checkout. The workflow never reached the `release` environment, so no pending deployment existed and no approval was performed.

## Preserved state

After failure:

- annotated remote/local `v0.2.0` tag remains unchanged;
- workflow run is terminal `failure`;
- zero workflow artifacts exist;
- no GitHub Release exists;
- no attestation was created;
- PyPI still returns 404;
- branch protection remains absent;
- no source, branch, package registry, or Turbopuffer mutation occurred after the tag push.

The supervisor directed preservation: do not delete/move the tag, change source, or create another release until the user explicitly ratifies a recovery contract.

## Recovery decision required

The current ticket cannot complete without one newly ratified option:

1. Fix workflow checkout/tag validation in a new commit, then explicitly delete and recreate `v0.2.0` at that reviewed commit before releasing 0.2.0.
2. Preserve failed `v0.2.0` permanently, fix/version-bump, and release `v0.2.1` from a new commit.
3. Leave v0.2.0 unreleased and the release plan blocked.

## Limits

This evidence proves observed GitHub state and the failure boundary, not which recovery choice is preferable. No independent review has yet occurred.
