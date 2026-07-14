Status: active
Created: 2026-07-14
Updated: 2026-07-14
Parent: None
Depends-On: .10x/tickets/done/2026-07-14-buoy-rebrand-plan.md

# Buoy Public CI and Release Plan

## Aggregate outcome

Ship truthful public-project badges/governance, reproducible CI, and an approval-gated GitHub-only v0.2.1 release while preserving the failed v0.2.0 tag as immutable history. This is a parent plan and is not executable.

## Governing records

- `.10x/decisions/github-only-release-automation-v0-2-1.md`
- `.10x/specs/buoy-ci-and-github-releases.md`
- `.10x/specs/buoy-public-project-surface.md`
- `.10x/knowledge/documentation-details-on-demand.md`
- `.10x/research/2026-07-14-buoy-github-release-automation.md`

## Child sequence

1. `.10x/tickets/done/2026-07-14-add-buoy-ci-release-and-public-files.md` — workflows, badges, changelog, contributor/security/release docs, metadata.
2. `.10x/tickets/done/2026-07-14-validate-buoy-ci-release-automation.md` — static/local workflow and package validation.
3. `.10x/tickets/done/2026-07-14-publish-buoy-rebrand-commit.md` — reconcile inherited index, commit, push, and observe main CI.
4. `.10x/tickets/cancelled/2026-07-14-create-buoy-v0-2-0-github-release.md` — preserved failed annotated-tag attempt; cancelled without Release.
5. `.10x/tickets/done/2026-07-14-repair-release-workflow-and-bump-v0-2-1.md` — validate remote tag metadata, bump patch version, commit/push, pass CI.
6. `.10x/tickets/done/2026-07-14-create-buoy-v0-2-1-github-release.md` — approval-gated first GitHub Release.
7. `.10x/tickets/2026-07-14-finalize-v0-2-1-release-docs.md` — post-release changelog and graph finalization.

## Aggregate acceptance criteria

- CI is real, passing, least-privilege, pinned, and linked by a truthful badge.
- Public governance/release docs remain concise and accurate.
- Complete rebrand plus automation is committed and pushed without losing inherited staged work.
- Public `v0.2.0` remains an immutable failed-attempt tag without a Release; `v0.2.1` exists as the first GitHub Release with wheel/sdist and provenance after explicit environment approval.
- No PyPI publication/project, branch protection, long-lived release token, live Turbopuffer operation, or vanity badge is created.
- All child evidence/reviews and current records agree.

## Progress and notes

- 2026-07-14: User selected GitHub-only publication, tag-triggered release with approval, and CI without a `main` protection rule.
- 2026-07-14: Full plan execution authorized; child 1 assigned.
- 2026-07-14: Hosted v0.2.0 run failed before release mutation because checkout dereferenced the annotated tag. User ratified immutable-tag recovery through v0.2.1; decision/spec/children superseded accordingly.
- 2026-07-14: CI/public files, validation, commit/push, and main CI completed. Release child created the exact annotated v0.2.0 tag but hosted tag-object validation failed before build or approval; external state was preserved.
- 2026-07-14: User ratified immutable-tag v0.2.1 recovery. The workflow fix/version bump passed main CI, and approval-gated v0.2.1 release completed with verified wheel/sdist provenance. Final changelog/record commit is in progress.

## Blockers

- `.10x/tickets/2026-07-14-finalize-v0-2-1-release-docs.md` must pass review, commit/push, and CI before aggregate closure.
