Status: done
Created: 2026-07-21
Updated: 2026-07-21
Parent: None
Depends-On: None

# Shape Simple Main Release Automation

## Outcome

Replace the repository's release ceremony with an independently reviewed, user-ratified contract for mechanically checked `develop -> main` readiness and fully automatic GitHub-only publication on a successful main push.

## Scope

- Identify the user's requested removal target precisely: supersede/remove active ancestry-sync, manual tag-push, release-environment approval, and post-hoc conversational preflight procedure; no release skill file exists.
- Define exact PR readiness checks, names, commands, branch protection transition, failure behavior, and no-live boundaries.
- Define exact main-push trigger, validation/build order, SemVer/tag/release state machine, automatic tag/attestation/Release behavior, idempotent no-op, fail-closed collisions, and environment deletion boundary.
- Preserve open-source-first portability by keeping logic repository-local and actions full-SHA pinned while documenting the explicit GitHub requirement.
- Obtain independent review and exact user ratification before implementation tickets open.

## User-ratified upstream choices

On 2026-07-21 the user explicitly selected:

1. **Release ceremony:** remove/supersede ancestry-sync, manual approval, and tag-push procedure; replace release docs/governance with the simple workflow.
2. **Existing version:** no-op only when tag and Release already match exact HEAD; otherwise fail without overwrite; a new release requires a version bump.
3. **Release gate:** fully automatic build, attestation, tag, and publication after checks, with no manual environment approval.

The remaining workflow/check mechanics are drafted for exact review rather than silently inferred.

## Acceptance criteria

- Two focused draft specifications are regeneration-grade and do not conflict.
- Develop-to-main checks make version bump, branch identity, tests, artifact clean-install behavior, and collision state mechanical.
- Main-push automation builds once and has an exact mutation/no-op/failure state machine.
- Existing v0.4.0 state and the first future version-bump requirement are explicit.
- Supersession/deletion scope names old workflow/docs/spec/decision/environment behavior without deleting historical evidence.
- Independent review passes and an exact confirm-or-correct checkpoint is presented before activation or implementation.

## Explicit exclusions

Workflow/source/test implementation; branch protection/environment mutation; PR merge; version bump; tag/Release mutation; deleting historical evidence; PyPI; Turbopuffer.

## References

- `.10x/specs/develop-to-main-release-readiness.md`
- `.10x/specs/main-push-automatic-github-release.md`
- `.github/workflows/ci.yml`
- `.github/workflows/release.yml`
- `docs/releasing.md`
- `.10x/specs/protected-github-branches.md`
- `.10x/specs/superseded/buoy-ci-and-github-releases.md`
- `.10x/decisions/simple-main-release-governance.md`
- `.10x/reviews/2026-07-21-simple-main-release-automation-shaping-review.md`
- `.10x/evidence/2026-07-21-simple-main-release-automation-ratification.md`
- `.10x/tickets/done/2026-07-21-simple-main-release-automation-plan.md`

## Evidence expectations

Current workflow/governance inventory; user choices; independent review findings; exact checkpoint; explicit no-implementation/no-external-mutation attestation.

## Blockers

None. Independent review concerns were repaired through the exact reviewer checkpoint and the user ratified `Confirm simplest flow (Recommended)`.

## Progress and notes

- 2026-07-21: User rejected the existing merge/deploy ceremony and requested a simpler model: CI checks representing whether develop can reasonably merge to main, then automatic release on main commit. Repository inspection found no release skill file; the removable surface is active governance/procedure plus the tag-triggered workflow. User selected removal of ceremony, exact-head no-op/otherwise-fail collision behavior, and fully automatic publication. Drafted two focused specs only. No workflow, docs, tests, branch protection, environment, tag, Release, PyPI, Turbopuffer, or product state changed.
- 2026-07-21: Independent review identified ancestry, partial-state, determinism/race/REST, protection transition, supersession/record graph, environment deletion, external semantics, and portability blockers. The exact recommended repaired checkpoint dropped main strict freshness/last-push approval, validated prospective merge results, required stable SemVer/deterministic serialized builds/exact REST and provenance, made every partial state permanently fail, mandated environment deletion/supersession, and added self-hosted migration. The user confirmed `Confirm simplest flow (Recommended)`. Activated both focused specs, superseded the v2 decision and old release spec, updated branch protection authority, opened one non-executable implementation plan with repository and hosted-configuration children, and closed shaping. No implementation or external mutation occurred.

## Closure mapping

- Current inventory and upstream choices: `.10x/evidence/2026-07-21-simple-main-release-automation-shaping.md`.
- Independent concerns: `.10x/reviews/2026-07-21-simple-main-release-automation-shaping-review.md`.
- Exact ratification: `.10x/evidence/2026-07-21-simple-main-release-automation-ratification.md`.
- Active behavior: `.10x/specs/develop-to-main-release-readiness.md`, `.10x/specs/main-push-automatic-github-release.md`, and `.10x/decisions/simple-main-release-governance.md`.
- Execution ownership: `.10x/tickets/done/2026-07-21-simple-main-release-automation-plan.md` and its two children.

## Retrospective

Strict base freshness is not free: when release commits advance only main, it creates recurring ancestry work. Validating the prospective merge result and revalidating exact main shifts that safety property into CI without preserving the ceremony.
