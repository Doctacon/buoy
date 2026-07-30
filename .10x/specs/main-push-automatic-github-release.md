Status: superseded
Created: 2026-07-21
Updated: 2026-07-21

# Label-Driven Main-Push Automatic GitHub Release

## Purpose and scope

Publish one deterministic stable GitHub Release automatically after a passing labeled `develop -> main` PR is merge-committed. No committed release version, changelog preparation, tag push, environment approval, PyPI, or Turbopuffer operation is involved.

This specification supersedes `.10x/specs/superseded/main-push-automatic-github-release-static-version.md` for future releases and restates every retained normative guarantee below.

## Trigger and merged-PR authority

The workflow triggers only on pushes to `main`, never tags or manual dispatch, with exact concurrency group `release-main` and `cancel-in-progress: false`.

Before mutation, exact `GITHUB_SHA` MUST:

- be a two-parent merge commit ordered `[prior main, exact develop head]`;
- resolve through GitHub's commit-associated-PR API to exactly one closed/merged same-repository PR with `merge_commit_sha=GITHUB_SHA`, base `main`, and head `develop` equal to the second parent;
- contain exactly one set of merge-time authority trailers produced by readiness:
  - `Buoy-Release-Label: release:patch|release:minor|release:major`
  - `Buoy-Release-Version: <stable target>`
  - `Buoy-Release-Base-Tag: <stable base tag>`
  - `Buoy-Release-PR: <associated PR number>`
  - `Buoy-Release-Head: <second-parent SHA>`;
- have no other stable tag ref—annotated or lightweight—and no other GitHub Release, including partial/mismatched state, whose exact peel/direct target/Release target commit is `GITHUB_SHA`.

Current mutable PR labels are diagnostic only after merge and MUST NOT determine release identity. Any duplicate/malformed/conflicting trailer, ambiguous PR, squash/rebase topology, different PR/head, or existing different stable release/tag for the same SHA fails before build publication or mutation.

## Version and notes

Using prior main as the base and the immutable merge trailer label, derive the target exactly as `.10x/specs/develop-to-main-release-readiness.md`. Recomputed base tag, label, target, PR number, and head MUST equal every trailer and associated-PR/topology field. A workflow rerun therefore reuses the immutable merge plan even if PR labels later change.

Project metadata MUST be dynamic through pinned `hatch-vcs==0.5.0`; build and install validation use exact `SETUPTOOLS_SCM_PRETEND_VERSION=<target>`. Source checkouts may expose a PEP 440 VCS development version; published wheel/sdist and `buoy --version` MUST expose exact stable target SemVer.

`CHANGELOG.md` remains frozen history through v0.4.0. The GitHub Release uses generated notes over the exact previous-tag-to-current range.

## Validation and deterministic build

Read-only jobs use exactly `contents: read`, `pull-requests: read`, and no secrets. They MUST:

1. validate merged PR/topology/label and tag authority;
2. validate dynamic metadata/frozen changelog/current repository policy;
3. run complete locked Python 3.11 and 3.13 validation;
4. build wheel/sdist exactly once with target override and deterministic environment;
5. verify exact names/metadata/inventory, clean install, CLI/help/version, and exact bundled tokenizer;
6. produce a hash-addressed immutable state plan from authoritative tag/Release/assets/provenance inspection.

The final publication job alone receives exactly `contents: write`, `id-token: write`, `attestations: write`, and `actions: read` for artifact download. It has no checkout, installs nothing, and executes no repository code.

## Exact state machine

For target `TAG=v<target>` and exact main `SHA`:

### Create

Only when tag ref and Release are both absent:

- REST-create annotated tag object `TAG`, message `Buoy <target>`, fixed tagger `github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>`, object `SHA` type commit;
- REST-create `refs/tags/TAG` to that object;
- on ref 422, perform one full authoritative reinspection; exact complete becomes no-op, every partial/mismatch fails;
- attest exact wheel/sdist subject names/digests for repository `Doctacon/buoy`, workflow `release.yml`, source ref `refs/heads/main`, and exact `SHA`;
- REST-create non-draft/non-prerelease Release `Buoy <target>` with generated notes and exactly those two built assets;
- unconditionally reinspect tag/Release, download and hash both assets, and verify provenance before success.

### No-op

Only exact complete matching tag peel, Release identity, two asset names/digests, and provenance succeeds without mutation.

### Permanent fail

Every lightweight, tag-only, Release-only, partial asset, wrong peel/identity/digest/provenance, conflicting target, or repeated mutation state fails without completion, overwrite, move, deletion, cleanup, or retry repair.

## Legacy v0.4.0

The sole immutable legacy no-op requires all normal exact-state fields plus:

- annotated tag `v0.4.0` peeled to `c49dc0582bf3f06a16eafdcca0707d1e64e1c58d`;
- Release ID `357504706`, name `Buoy v0.4.0`, tag/target `v0.4.0`, non-draft, non-prerelease, exactly two assets;
- wheel `buoy_search-0.4.0-py3-none-any.whl` SHA-256 `89b84c6beba2979ab6ffd0d244d1d0f5c1af938cfbec021a89094a7109e5c4c8`;
- sdist `buoy_search-0.4.0.tar.gz` SHA-256 `9c0469d2fc03b8e03780b06793537736391c21f0ed07c43adab9e674988ffd3a`;
- provenance repository `Doctacon/buoy-search`, workflow `release.yml`, source ref `refs/tags/v0.4.0`, source commit exact above, and exact corresponding subject names/digests.

No future target may use either legacy repository or source-ref exception. Any mismatch permanently fails.

## Tests

Repository-local executable tests MUST cover triggers, exact permissions, full-SHA action pins, label/SemVer/tag-authority vectors, duplicate/malformed trailers, PR association/topology, later label mutation, different stable release already on the same SHA, dynamic exact version, deterministic environment/build once, create/no-op/every mismatch, annotated/lightweight tags, 422 full reinspection, downloaded digest/provenance final verification, generated notes, serialization, v0.4 legacy exact pins, and absence of overwrite/delete/move/force-push/environment/PyPI/Turbopuffer behavior.

## Portability

Version/tag calculation, trailer parsing, artifact validation, hashes, and state planning MUST remain repository-local standard Python/shell. GitHub integration is a thin adapter over standard merge commits, annotated Git tags, release assets, and attestations. Documentation MUST map the same plan to a self-hosted forge/runner. GitHub Actions remains the explicit managed-platform exception; no proprietary package registry or artifact format is introduced.

## Acceptance scenarios

- Merge-committed patch plan over v0.4.0 computes/publishes exact v0.4.1 automatically.
- Later mutation of PR labels does not change rerun identity; immutable merge trailers still compute v0.4.1.
- A different stable tag/Release already associated with the same main SHA fails before creating another version.
- Main SHA without exact merged PR/trailers/topology fails before mutation.
- Build metadata and installed CLI equal target despite dynamic source metadata.
- Existing exact complete target no-ops; every partial/mismatch permanently fails.
- Published assets have exact digests and canonical future provenance.

## Explicit exclusions

Static project/module/lock release version; committed pending changelog; squash/rebase main promotion; manual tag/workflow/environment approval; PyPI; Turbopuffer; destructive repair; force push; product changes.
