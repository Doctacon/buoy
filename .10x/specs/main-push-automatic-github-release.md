Status: active
Created: 2026-07-21
Updated: 2026-07-21

# Main-Push Automatic GitHub Release

## Purpose and authority

Replace manual tag creation and release-environment approval with a fully automatic workflow on every push to `main`. The user ratified stable-SemVer, exact-state no-op/otherwise-permanent-failure, and no manual approval after independent review.

## Trigger, serialization, and permissions

`.github/workflows/release.yml` MUST trigger only on pushes to `main`, never tags or manual dispatch. Concurrency group is one repository-wide `release-main` with `cancel-in-progress: false`.

Validation/build jobs use `contents: read`, no secrets. The final publication job receives only `contents: write`, `id-token: write`, `attestations: write`, and `actions: read` if artifact download requires it. It MUST NOT install dependencies or execute repository code after receiving write permission; it consumes immutable build artifacts and deterministic state-machine output only.

## Validation and deterministic build

Before mutation the workflow MUST:

1. require stable `MAJOR.MINOR.PATCH` agreement across project/module/lock, with no leading zero in any multi-digit core numeric identifier;
2. require empty Unreleased, current pending section, and older sections whose `YYYY-MM-DD` values are real ISO calendar dates;
3. run the same locked 3.11/3.13 validation as readiness;
4. build wheel/sdist exactly once with `SOURCE_DATE_EPOCH=GITHUB_SHA commit timestamp`, `PYTHONHASHSEED=0`, `TZ=UTC`, `LC_ALL=C`, and locked backend;
5. verify assets, metadata, inventory, clean install, CLI, and mandatory tokenizer smoke;
6. produce a hash-addressed immutable state plan from authoritative GitHub tag/Release/provenance inspection.

## Exact state machine

For `TAG=v<version>` and exact `SHA=GITHUB_SHA`:

### Create

Only when both tag ref and Release are absent:

- REST-create an annotated tag object with tag `TAG`, message `Buoy <version>`, fixed tagger `github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>`, and object `SHA` type `commit`;
- REST-create `refs/tags/TAG` pointing to that tag object;
- if ref creation returns 422, authoritatively reinspect tag, Release, downloaded assets, and provenance once: exact complete state becomes a no-op without attestation or Release mutation; every partial or mismatched observation permanently fails;
- attest exact wheel/sdist digests with subject names, repository `Doctacon/buoy-search`, workflow `release.yml`, source ref `refs/heads/main`, and source commit `SHA`;
- REST-create non-draft/non-prerelease Release `Buoy <version>` for `TAG`, target identity `TAG`, generated notes, and exactly the two already-built assets;
- for both create and no-op outcomes, freshly reinspect tag object/peel and Release/tag identity, download the published assets and compare their exact names/digests, and verify provenance fields before success.

### No-op

Only when annotated tag and Release both exist and all of these match exact `SHA`: tag peel, Release tag/name/non-draft/non-prerelease identity, exact two asset names/digests, and provenance subject names/digests/repository/workflow/source ref/source commit. Then succeed without mutation.

### Permanent fail

Every other state—including lightweight tag, tag-only, Release-only, wrong peel, partial assets, digest/provenance mismatch, or conflicting target—fails without automated completion, overwrite, move, deletion, cleanup, or retry repair. Recovery requires a separately authorized operator decision or abandoning that version.

## Race behavior

Serialization prevents workflow-owned overlap. A concurrent external creator between inspection and mutation is handled only by the single 422 reinspection above. It can convert to exact continuation/no-op only when every authoritative identity matches; otherwise fail. No loop or repeated mutation attempt is permitted.

## Existing v0.4.0 transition

Published v0.4.0 is the sole legacy no-op exception. It MUST be accepted only when every normal exact-state field matches and all of these legacy pins match simultaneously:

- tag `v0.4.0`, annotated and peeled to `c49dc0582bf3f06a16eafdcca0707d1e64e1c58d`;
- Release name `Buoy v0.4.0`, tag/target `v0.4.0`, non-draft, non-prerelease, and exactly two assets;
- wheel `buoy_search-0.4.0-py3-none-any.whl` SHA-256 `89b84c6beba2979ab6ffd0d244d1d0f5c1af938cfbec021a89094a7109e5c4c8`;
- sdist `buoy_search-0.4.0.tar.gz` SHA-256 `9c0469d2fc03b8e03780b06793537736391c21f0ed07c43adab9e674988ffd3a`;
- provenance repository `Doctacon/buoy-search`, workflow `release.yml`, source ref `refs/tags/v0.4.0`, source commit `c49dc0582bf3f06a16eafdcca0707d1e64e1c58d`, and the exact corresponding subject names/digests.

This exception exists only because the already-published v0.4.0 provenance predates main-push automation. Any mismatch permanently fails. Every future version MUST require provenance source ref `refs/heads/main`; the legacy source-ref exception MUST NOT generalize. Any different main commit retaining 0.4.0 fails readiness and automatic release. The next release requires an explicit stable version bump; this spec does not choose it.

## Environment removal and supersession

After repository workflow integration proves zero `environment: release` references and GitHub reports zero active/pending deployments, implementation MUST delete the unused `release` environment and verify 404/readback absence. It MUST supersede old tag-trigger/manual-approval release specs/decision, replace `docs/releasing.md`, close obsolete/open v0.4 release records truthfully, and preserve historical evidence.

## Tests

Repository-local dry tests cover triggers, job permissions, action pins, strict stable version/real-date changelog rules, deterministic build variables, create/no-op/all mismatch states, annotated/lightweight tags, executable deterministic 422 full-reinspection behavior, executable final published-asset/provenance verification, generated-note/tag target, asset/provenance fields, serialization, no environment/tag trigger/manual dispatch, and forbidden overwrite/delete/move/force-push commands. Readiness Policy scans the bounded repository-wide release-behavior surface (all workflows and release helpers) and rejects PyPI or Turbopuffer behavior.

## Portability

GitHub is the user-required existing host. The state machine, version checks, build, hashes, and validation live in standard Python/shell. `docs/releasing.md` MUST map GitHub REST operations to portable Git operations plus generic forge release/attestation APIs so migration to self-hosted Git/CI reuses the same scripts and artifacts. GitHub integration is limited to a thin API adapter and pinned open-source actions; no proprietary registry or artifact format is introduced.

## Explicit exclusions

Choosing next version; product changes; PyPI; Turbopuffer; environment approval; manual tag push; tag-trigger/manual workflow; tag/Release replacement; force push; ancestry sync.
