Status: provisional
Created: 2026-08-20
Updated: 2026-08-20
Ticket: .10x/tickets/2026-08-20-ship-buoy-v0-6-1.md
Decision: .10x/decisions/annotated-tag-triggered-github-releases.md
Specification: .10x/specs/annotated-tag-triggered-github-release.md
Relates-To: .10x/evidence/2026-08-19-buoy-v0-6-0-github-release.md

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

## Evidence required to complete

- Exact changed-path/blob scope, focused and full locked validation, workflow
  lint, distribution smoke, link/status/diff hygiene, and independent review.
- Exact-head task PR and CI, develop squash integration, release PR with all
  four readiness jobs, ordered main merge, and exact-main CI identities.
- Fresh readback that the v0.6.0 tag object/run remain exact, immutable
  Releases remain enabled, and all local/remote v0.6.1 tag and complete
  authenticated Release surfaces including drafts are absent before tagging.
- Annotated v0.6.1 tag-object SHA, exact tagger/message/peel/current-main
  identity, and the successful normal Release workflow run/jobs.
- Published immutable/latest Release ID/URL and exact two asset IDs, names,
  sizes, API digests, numeric-ID downloaded hashes, and build attestations.
- Isolated downloaded-wheel version, CLI/module/telemetry/import/tokenizer
  smoke with a fresh empty home and no credential/provider/model activity.
- Separately reviewed records-only closure identities and explicit proof that
  closure performs no hosted Release mutation.

## Effect log

At this provisional checkpoint no v0.6.1 tag, Release, draft, asset,
attestation, registry publication, provider/model/data operation, application
behavior change, global installation, real Buoy-home inspection, protection
change, force push, or unrelated hosted mutation has occurred.

The preserved v0.6.0 tag has not moved or been deleted, and no v0.6.0 Release
has been created. This evidence grants no recovery, manual-dispatch, PyPI, or
application authority.
