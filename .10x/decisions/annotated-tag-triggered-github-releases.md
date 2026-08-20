Status: accepted
Created: 2026-08-19
Updated: 2026-08-19
Specification: .10x/specs/annotated-tag-triggered-github-release.md

# Annotated-Tag-Triggered GitHub Releases

## Decision

Buoy uses one reusable GitHub-only release workflow. A reviewed release-prep
change reaches `main`, exact-main CI passes, and a maintainer's annotated
`vMAJOR.MINOR.PATCH` tag push is the publication approval. The workflow then
runs complete locked tests, builds and clean-smokes one wheel/sdist pair,
attests them, creates a draft Release, verifies downloaded bytes, and publishes
that same Release.

All jobs default to `contents: read`. Only the publication job receives exact
`contents: write`, `id-token: write`, and `attestations: write`. Published
Releases must be immutable. Repository owners enable and verify that persistent
administrative setting outside the workflow because its deliberately narrow
token cannot read repository-administration settings; the workflow verifies
the resulting published Release is immutable. The workflow may neither
publish to PyPI nor delete, replace, clobber, force-move, or repair public
objects.

Future releases reuse this standing design. They need the repository's normal
bounded release-prep ticket/change/review and passing CI, but not a new release
decision, version-specific specification, independent artifact ceremony, or
prepublication GO ceremony. After publication, the ordinary ticket/evidence
closure is a small records-only change and performs no hosted Release mutation.

## Rationale

The prior process repeatedly encoded the same safety properties as bespoke
records and manual commands. The durable controls belong in a pinned,
least-privilege workflow. The annotated tag provides a clear human approval
boundary while Hatch-VCS keeps the public version derived from Git.

## Exclusions

No PyPI or other registry, provider/model/data operation, real Buoy-home
inspection, global tool replacement, branch-protection weakening, force push,
tag movement, release deletion, or unrelated product change is authorized.
