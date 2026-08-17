Status: accepted
Created: 2026-08-17
Updated: 2026-08-17

# One-Time User-Global-Home Main Promotion and Tool Replacement

## Context

The repository owner first requested the user-global `~/.buoy` default as a
forward-only task and reserved integration for later review. That implementation
has now passed independent review and exact-head CI and was squash-integrated by
PR #129 as
`D0 = cd3f1bef4c9c4856c727f4891512278eafd82841`, with sole parent
`e101690bc351d92cc6b24a46cb5bc30f00bd6df0` and tree
`8c6790ac8be55601b25c7b79aad17994b790a533`.

The owner subsequently and explicitly directed the agent to continue through
passing pull requests until the changes are on `main` and the global `uv` tool
is installed. Current `main` is
`M = 7f7ddfe245e1e5b57946eb6ac10dcc01358559fc`. The merge base of `M` and
`D0` is `B = e101690bc351d92cc6b24a46cb5bc30f00bd6df0`; `tree(M)` and `tree(B)`
are both `98cb3e56af4d867987d4e23f279f68fcf912e666`. Although divergence counts
two main-only commits, the cumulative main-side content is empty relative to
`B`. A read-only merge construction of `M` with `D0` yields exact `tree(D0)`
without conflict.

The active paused-publication decision still excludes protected-branch merges,
and the prior automatic-routing promotion exception is superseded and consumed.
The original global-home decision also excluded integration and tool install.
This decision records the owner's later instruction without reopening any of
those unrelated authorities.

## Decision

Authorize one normal records-only authority pull request into `develop`, then
exactly one same-repository `develop -> main` pull request and exactly one
merge-commit integration of that release pull request. This is a narrow,
single-use exception only to the protected-branch-merge exclusion in
`.10x/decisions/release-publication-is-paused.md`. Publication remains paused.

The authority records must first integrate through the ordinary reviewed
`work/* -> develop` squash flow. Only afterward may a dedicated release session
bind final exact `develop` as `D`. It must require unchanged `M`, exact merge
base `B`, `tree(M) == tree(B)`, and an empty `B..M` content diff. The release
pull request must have base `main@M`, same-repository head `develop@D`, and a
prospective merge `P` with ordered parents `[M, D]` and `tree(P) == tree(D)`.

All three exact-head CI checks and all four exact-head release-readiness checks
must succeed. Independent release review must pass on the exact refs, complete
diff, prospective topology, check identities, mergeability, discussion state,
and exclusions. Integration must use a merge commit, never squash or rebase.
The actual result `R` must have ordered parents `[M, D]`, preserve exact
`tree(D)`, leave `develop == D`, and have an empty `D..R` content diff. Exact-
main CI and `Release / Publication paused` must then succeed.

Only after those post-main gates pass, authorize exactly one replacement of the
user-global `buoy-search` uv tool with an artifact cryptographically bound to
exact `R`. Before the invocation, a separate install review must bind the
current tool baseline, exact-R source/tree, build inputs, artifact and runtime-
constraints digests, executable target, and isolated-home smoke results. The
replacement is consumed when its one `uv tool install --force` invocation
begins. A failed or uncertain invocation grants no retry, rollback, uninstall,
or second invocation under this decision.

Post-install verification must prove the global `buoy` executable and installed
distribution are bound to exact `R`, preserve the active routing source receipt,
report the expected dynamic version, and resolve implicit state/artifact paths
to `~/.buoy` from unrelated working directories. Verification must not execute
`plan`, `apply`, or `retrieve` against live inputs and must not create the real
application home.

## Fail-closed and consumption boundary

Any ref, tree, merge-base, candidate, path scope, check, discussion, review,
artifact, installed-baseline, or path-behavior drift stops the relevant phase.
No phase may silently rebind an identity or substitute a merge/install method.
The main-merge authority is consumed when exact `R` is created; the install
authority is consumed when the one replacement invocation begins. Neither may
be reused for a retry, a second promotion, a later build, or recurring release
or installation automation.

## External effects and exclusions

Permitted effects are limited to the authority task branch and ordinary PR,
one same-repository release PR and merge commit, read-only checks/reviews, one
exact-main local build, one `buoy-search` uv-tool replacement, its bounded
temporary/cache files, verification, and one later records-only closure branch
and ordinary PR to `develop`.

No direct or force push to `develop` or `main`, branch deletion, protection or
ruleset change, tag, GitHub Release, package publication, deployment, provider
request/write, catalog migration, indexed-content mutation, model inference,
credential access/change, old project-asset scan/move/copy/backfill/delete,
real `~/.buoy` state/plan creation, other uv-tool mutation, or unrelated change
is authorized. Publication remains paused before, during, and after execution.
