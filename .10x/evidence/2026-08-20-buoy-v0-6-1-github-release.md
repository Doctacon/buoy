Status: recorded
Created: 2026-08-20
Updated: 2026-08-20
Ticket: .10x/tickets/done/2026-08-20-ship-buoy-v0-6-1.md
Decision: .10x/decisions/annotated-tag-triggered-github-releases.md
Specification: .10x/specs/annotated-tag-triggered-github-release.md
Relates-To: .10x/evidence/2026-08-19-buoy-v0-6-0-github-release.md
Preparation-Review: .10x/reviews/2026-08-20-buoy-v0-6-1-release-preparation-review.md
Closure-Review: .10x/reviews/2026-08-20-buoy-v0-6-1-release-closure-review.md

# Buoy v0.6.1 GitHub Release Evidence

## Starting state

- Current release-preparation base is exact
  `develop@788c377c57bc1b4f1bfd4aba05d39ad67fe48ead`, tree
  `cc619214f5eff4585e6a4df2394d6f45a37a9d5f`.
- Current remote release source is exact
  `main@701d73ebbf6a8c3b2c664a0295374dcb4283283c`, the v0.6.0
  release-preparation merge with the same tree and ordered parents
  `caed68fdce3ef91e41c11f5d586a6166837d0392` and
  `788c377c57bc1b4f1bfd4aba05d39ad67fe48ead`.
- Annotated tag object `1ffb70f5656f48c782defbe252dab44426134343`
  names `v0.6.0`, has message `Buoy v0.6.0`, and peels to that exact main
  commit. It is permanent and outside v0.6.1 mutation authority.
- Release run `32329737394` failed both locked test jobs solely in
  `DynamicVersionTests.test_clean_editable_install_derives_development_version_from_vcs`
  because the fixture did not construct post-tag history. Build and publish
  were skipped, the run retained zero artifacts, and no v0.6.0 Release,
  draft, asset, or attestation exists.
- Repository immutable Releases are enabled and stay enabled. The reusable
  publisher remains the accepted publication path.

## Authorized successor

The owner selected v0.6.1 rather than a temporary recovery publisher. The
successor uses an ordinary task PR, a merge-commit release PR, exact-main CI,
one annotated v0.6.1 tag, and the normal reusable workflow. It adds no
recovery workflow and no `workflow_dispatch` entry point.

Only an exact rerun against an already successfully published matching
Release is verification-only. Any failed v0.6.1 run or partial hosted state is
a stop for read-only inspection; it receives no blind-rerun authority from
this ticket, and the owner must choose the next separately reviewed action
from the exact observed state.

The bounded source change advances the public changelog, README asset URL,
supported-version row, and validator expectation to v0.6.1 and makes the
development-version test hermetic with controlled post-tag history. It does
not change application behavior, release-workflow permissions/state
transitions, dependencies, the lockfile, or dynamic Hatch-VCS version
authority.

## Preparation and develop integration

The bounded preparation candidate was exact commit
`2e8e305908f704c01763d6cad071182294eb99e4` on
`work/ship-buoy-v0-6-1`. Task PR
[\#140](https://github.com/Doctacon/buoy/pull/140) targeted `develop` from
that exact head. CI run
[32378163294](https://github.com/Doctacon/buoy/actions/runs/32378163294)
passed Python 3.11 job `96454494281`, Python 3.13 job `96454493792`, and
Build distributions job `96455240673`.

A separate integration role squash-merged the task PR as
`cb718d747db582d05f52bbea436b6ee737ed5bfa`, sole parent
`788c377c57bc1b4f1bfd4aba05d39ad67fe48ead`, with exact tree
`eee7e36424dea2a80e77f35c7a6bf793541790bc`. The integration preserved the
reviewed public release surfaces, hermetic dynamic-version test fixture, and
unchanged reusable publisher.

## Main promotion and exact-main CI

Release PR [\#141](https://github.com/Doctacon/buoy/pull/141) promoted exact
`develop@cb718d747db582d05f52bbea436b6ee737ed5bfa` to still-current `main`.
Release readiness run
[32379410852](https://github.com/Doctacon/buoy/actions/runs/32379410852)
attempt 1 passed all four jobs, and ordinary PR CI run
[32379410871](https://github.com/Doctacon/buoy/actions/runs/32379410871)
attempt 1 passed.

A separate release role merge-committed the PR as
`0d6f414f9f258b4f7025f95c97ba5cb58d16b8d3`, with ordered parents
`701d73ebbf6a8c3b2c664a0295374dcb4283283c` and
`cb718d747db582d05f52bbea436b6ee737ed5bfa` and exact tree
`eee7e36424dea2a80e77f35c7a6bf793541790bc`. Exact-main CI run
[32379909011](https://github.com/Doctacon/buoy/actions/runs/32379909011)
attempt 1 passed at that exact main commit.

## Fresh tag boundary and annotated tag

Immediately before the one tag push, read-only inspection reverified that:

- v0.6.0 tag object `1ffb70f5656f48c782defbe252dab44426134343`
  remained unchanged at its failed release-preparation main commit;
- no v0.6.0 GitHub Release had appeared;
- local and remote v0.6.1 tags and every authenticated v0.6.1 Release surface,
  including drafts, were absent;
- repository immutable Releases remained enabled; and
- no Release workflow was active.

One annotated `v0.6.1` tag was then created and pushed at exact current main:

- tag object: `bbd3824985d1b9778def284156313a27dca6526f`;
- peeled commit: `0d6f414f9f258b4f7025f95c97ba5cb58d16b8d3`;
- tagger: `Doctacon <61797492+Doctacon@users.noreply.github.com>`; and
- message: `Buoy v0.6.1`.

The public v0.6.0 tag was not moved, deleted, recreated, or repurposed.

## Normal reusable workflow

The tag push started unique Release workflow run
[32380801652](https://github.com/Doctacon/buoy/actions/runs/32380801652)
at exact tagged main. Attempt 1 completed successfully:

- Python 3.13 job `96463245408`: success;
- Python 3.11 job `96463245831`: success;
- Build distributions job `96463977009`: success; and
- Publish immutable GitHub release job `96464271856`: success.

The build retained artifact `9411013181`, named `buoy-search-v0.6.1`, from
the same run and exact head. The publisher attested the two distributions,
created one frozen draft, verified its exact notes/assets, verified build
provenance for both distributions, published that draft, and passed its final
immutable/latest readback. No manual dispatch or recovery publisher was used.

## Published immutable Release and assets

GitHub Release
[v0.6.1](https://github.com/Doctacon/buoy/releases/tag/v0.6.1) is database
ID `373806097`, name `Buoy v0.6.1`, target
`0d6f414f9f258b4f7025f95c97ba5cb58d16b8d3`, and was published at
`2026-08-20T14:36:33Z`. It is non-draft, non-prerelease, immutable, and the
repository's latest Release.

It contains exactly two uploaded assets:

- wheel asset ID `522371846`,
  `buoy_search-0.6.1-py3-none-any.whl`, 697,772 bytes, SHA-256
  `3c1b8805d39f67194dcd29c05545266356092f28cd7fd545213cfd08465d1d3a`;
- source asset ID `522371845`, `buoy_search-0.6.1.tar.gz`, 1,227,623 bytes,
  SHA-256
  `d1fc71cfdf9968594251b8d08661a462ffa9898859847ebcc9b569de8f2fd60d`.

API-reported sizes and digests matched the retained build inputs. Fresh
downloads through each numeric asset-ID endpoint matched those same SHA-256
digests, and build-attestation verification passed for both exact files.

## Isolated downloaded-wheel smoke

The published wheel installed successfully into a clean isolated environment
with a fresh empty home. `buoy --version` returned `buoy 0.6.1`; CLI help,
module help, telemetry help, import, and packaged-tokenizer smoke all passed.
The smoke made no credential, provider, model, data, namespace, or real
Buoy-home access.

## Final effect and closure boundary

The accepted public effect is exactly one new annotated v0.6.1 tag, one
successful normal Release workflow, build-attestation verification for both
assets, and immutable GitHub Release `373806097` with the two assets above. No
PyPI publication,
application/provider/model/data operation, global installation, real
Buoy-home inspection, branch-protection change, force push, v0.6.0 recovery,
tag movement, or unrelated hosted mutation occurred.

The terminal closure candidate only advances this evidence to `recorded`,
moves its ticket to `tickets/done`, repairs direct record backlinks, and
names the separately authored closure review. It performs no tag, Release,
asset, attestation, workflow, registry, application, or provider write. This
evidence grants no recovery, manual-dispatch, PyPI, or application authority.
