Status: recorded
Created: 2026-07-21
Updated: 2026-07-21
Relates-To: .10x/tickets/done/2026-07-21-create-buoy-v0-4-0-github-release.md, .10x/tickets/done/2026-07-21-buoy-v0-4-0-release-plan.md

# Buoy v0.4.0 GitHub Release

## Preflight

Exact reviewed/accepted main was `c49dc0582bf3f06a16eafdcca0707d1e64e1c58d`, tree `7de04d70c442de5fb5051cd6ceafda5b4c39c285`. Project/module/lock reported 0.4.0, exact-main CI run `29851219914` passed, no local/remote `v0.4.0` tag or GitHub Release existed, the `release` environment required reviewer `Doctacon` with self-review allowed, tag/assets dry checks passed, and PyPI returned HTTP 404 for `buoy-search` 0.4.0.

## Annotated tag

Created and pushed annotated tag `v0.4.0`:

- tag object: `1a527da870a1b6d8acedee8b93dbf85d24dac8b9`;
- authoritative remote object type: `tag`;
- peeled object type: `commit`;
- peeled commit: `c49dc0582bf3f06a16eafdcca0707d1e64e1c58d`.

No prior tag or Release was replaced or deleted.

## Workflow and approval

Unique Release workflow run `29851435791` targeted exact commit `c49dc0582bf3f06a16eafdcca0707d1e64e1c58d`.

`Validate and build` job `88705013738` passed remote annotated-tag/version verification, locked sync, complete release validation, one wheel/sdist build, exact asset verification, and artifact retention before publication.

The run then waited on exactly one pending deployment for environment ID `18151168858`. Pre-approval revalidation confirmed the exact run/commit/tag, successful validation/build, absent Release, and current-user approval eligibility. The exact deployment was approved with comment naming the reviewed commit. `Publish GitHub release` job `88705440328` passed artifact download, conflicting-state refusal, SLSA provenance attestation, and Release creation. The complete run succeeded.

Hosted warnings noted that several pinned upstream actions target Node.js 20 but were forced by GitHub to run on Node.js 24. The actions remain full-SHA pinned; publication succeeded. This warning is an upstream action-runtime migration signal, not evidence of release failure.

## Release and assets

GitHub Release:

- database ID: `357504706`;
- URL: `https://github.com/Doctacon/buoy-search/releases/tag/v0.4.0`;
- name: `Buoy v0.4.0`;
- published: `2026-07-21T17:07:47Z`;
- draft: false;
- prerelease: false.

Downloaded assets matched GitHub API digests exactly:

- wheel asset ID `484935331`, 523,079 bytes, SHA-256 `89b84c6beba2979ab6ffd0d244d1d0f5c1af938cfbec021a89094a7109e5c4c8`;
- sdist asset ID `484935332`, 932,895 bytes, SHA-256 `9c0469d2fc03b8e03780b06793537736391c21f0ed07c43adab9e674988ffd3a`.

`gh attestation verify --repo Doctacon/buoy-search` succeeded independently for both downloaded assets.

## No-PyPI and safety boundary

After publication, PyPI still returned HTTP 404 for `https://pypi.org/pypi/buoy-search/0.4.0/json`. No package registry publication, branch/protection mutation, tag overwrite, Release replacement, Turbopuffer/provider operation, namespace operation, live retrieval/apply/eval, user-state discovery/mutation, or user-owned cleanup occurred.

## What this supports

This supports completion of the GitHub-only v0.4.0 publication child. Post-release changelog finalization remains separately owned and must not alter the tagged commit or Release.
