Status: accepted
Created: 2026-08-16
Updated: 2026-08-16

# One-Time Automatic-Routing Main Promotion

## Context

The user explicitly requested that the completed automatic-routing work be
integrated through `develop` and then delivered to `main`. The routing feature
reached `main` through accidental squash PR #117, while the reviewed remote
reader fix and governance closure remained on `develop`. The one-time,
content-empty ancestry repair is now complete and consumed. Fresh local
readback binds current `main` as
`M = 0db802ec1a895f289c7600b19c80603986839873` and the base for this authority
task as `D0 = 4abb931e9a6bd15040287e84dc68bf502e0fea9e`.

`M` is an ancestor of `D0`, so the history is ready for the repository's normal
same-repository `develop -> main` release flow. However,
`.10x/decisions/release-publication-is-paused.md` currently excludes any
protected-branch merge as well as publication. The active
`.10x/specs/protected-github-branches.md` separately defines the required
same-repository release PR, exact checks, independent review, and merge-commit
method as behavioral gates while hosted protection remains absent by owner
choice.

## Decision

Authorize exactly one same-repository pull request from branch `develop` to
branch `main` in `Doctacon/buoy` and exactly one merge-commit integration of
that pull request. This is a narrow exception only to the paused-publication
decision's protected-branch-merge exclusion. It does not resume or alter any
publication mechanism or any other exclusion in that decision.

This ordinary authority-record task must first integrate into `develop`
through the normal reviewed squash flow. Only afterward may a dedicated release
session freshly bind exact `origin/develop` as `D`. The session must require
`origin/main == M`; it must not infer or predeclare `D` before the authority
records integrate.

The release pull request must have exact same-repository base/head branches
`main` and `develop`, unchanged bound commits `M` and `D`, and a GitHub
prospective merge result `P` whose ordered parents are `[M, D]` and whose tree
equals `tree(D)`. All seven checks on that exact candidate must succeed:

- `CI / Python 3.11`;
- `CI / Python 3.13`;
- `CI / Build distributions`;
- `Release readiness / Policy`;
- `Release readiness / Python 3.11`;
- `Release readiness / Python 3.13`;
- `Release readiness / Distribution`.

An independent release review must pass on the exact refs, complete release
diff, candidate topology, hosted check identities, merge method, and exclusion
boundary. A dedicated release session must then use merge-commit integration,
never squash or rebase. Result `R` must have ordered parents `[M, D]`, satisfy
`tree(R) == tree(D)`, and leave `origin/develop == D`.

After integration, exact-main `CI` and the read-only
`Release / Publication paused` job must pass. Fresh readback must prove the
expected refs, parents, trees, ancestry, and empty `D..R` content diff, plus
unchanged branch-protection/ruleset, tag, and GitHub Release inventories.

## Fail-closed and consumption boundary

Stop without opening or merging the release pull request if `main` differs
from exact `M`, bound `D` changes, `M` is not an ancestor of `D`, the
prospective merge result cannot be constructed with the exact parents/tree,
any of the seven checks is missing, stale, ambiguous, or unsuccessful,
independent review does not pass, or the host cannot perform the exact merge
method. Drift requires an updated reviewed record; it may not be silently
rebound.

The authority is consumed immediately when the one qualifying merge commit
`R` is created. It cannot authorize a retry, second main merge, recurring
release ceremony, or later closure promotion. Durable closure must record the
actual result and mark this decision superseded.

## External effects and exclusions

Permitted hosted effects are limited to the ordinary authority branch and PR,
one same-repository `develop -> main` PR, read-only hosted checks/review, its
one merge-commit integration, and a later ordinary records-only closure branch
and PR to `develop`.

No direct or force push to a long-lived branch, branch-protection or ruleset
change, tag, GitHub Release, retained workflow artifact, package publication,
deployment, provider request/write, routing-catalog migration, indexed-content
mutation, model inference, credential change, or other release/publication
action is authorized. Publication remains paused before, during, and after the
main merge.
