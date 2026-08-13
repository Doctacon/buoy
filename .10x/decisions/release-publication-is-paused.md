Status: active
Created: 2026-07-30
Updated: 2026-08-13

# Release Publication Is Paused

## Decision

GitHub tag and Release publication is paused after v0.4.0. Buoy retains
Hatch-VCS tag-derived development versions and read-only source/build
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

## One-time exception

`.10x/decisions/v0-5-1-one-time-manual-security-release.md` authorizes only the
reviewed v0.5.1 containment release. Automatic publication remains paused
before and after that release.
