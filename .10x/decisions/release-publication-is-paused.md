Status: superseded
Created: 2026-07-30
Updated: 2026-08-19

# Release Publication Is Paused

## Supersession

The repository owner explicitly authorized a persistent, narrowly scoped,
write-capable GitHub Release workflow and immutable Releases on 2026-08-19.
`.10x/decisions/annotated-tag-triggered-github-releases.md` supersedes this
pause when its reviewed implementation reaches `main`. Historical paused and
one-time release records remain preserved; they grant no current authority.

## Decision

Automatic GitHub tag and Release publication remains paused. The completed
one-time manual v0.5.1 security release does not resume the publisher. Buoy
retains Hatch-VCS tag-derived development versions and read-only source/build
validation.

All release-related workflows declare only `contents: read`. The existing four
release-readiness job names remain for branch-protection continuity. The
legacy static-version publication commands fail cleanly and are unreachable
from workflows. Diagnostic wheel and sdist builds are inspected and
clean-installed inside their workflow job, then discarded; they are not
uploaded or retained as workflow artifacts.

## Supersedes

This decision supersedes
`label-driven-tag-derived-automatic-releases.md`,
`develop-to-main-release-readiness.md`,
`main-push-automatic-github-release.md`, and
`buoy-release-validation.md` as active publication authority until a new
reviewed release design explicitly resumes writes.

## Exclusions

No static-version rollback, target version selection, tag, Release, artifact
publication, or protected-branch merge is authorized.

## One-time exceptions

`.10x/decisions/v0-5-1-one-time-manual-security-release.md` authorizes only the
reviewed v0.5.1 containment release. That exception was consumed on 2026-08-13;
it grants no authority for another tag, asset, or Release. Automatic
publication remains paused.

`.10x/decisions/v0-6-0-one-time-manual-github-release.md` was superseded before
use. It created no tag, Release, asset, or attestation and grants no current
authority. The reusable design is governed by
`.10x/decisions/annotated-tag-triggered-github-releases.md`.
