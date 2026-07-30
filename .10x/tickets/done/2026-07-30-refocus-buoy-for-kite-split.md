Status: done
Created: 2026-07-30
Updated: 2026-07-30
Parent: None
Depends-On: None

# Refocus Buoy for the Kite Split

## Scope

Implement `.10x/specs/focused-buoy-boundary.md` on `work/refocus-buoy`, based on
fetched `origin/develop` commit
`7d359f344348289fef75e8a53c9bfc258c5d9c17`.

Remove account-wide routing, catalog, multi-namespace, Command Center, evidence,
and experimental orchestration surfaces. Retain the mature source adapters,
compact plan/apply implementation, applied-state safeguards, retrieval ranking,
evaluation, and explicit single-namespace handoff. Repair release validation for
the repository's active Hatch VCS version authority.

## Explicit exclusions

No force-push, history rewrite, tag mutation, release, merge to `develop` or
`main`, provider call, turbopuffer mutation, evidence-resource cleanup, Kite
implementation, or personal-site change.

Kite repository creation and bootstrap are governed separately in Kite's own
records.

## Acceptance criteria

1. The active decision and specification are implemented.
2. Focused CLI, source, plan/apply, retrieval, eval, and release tests pass.
3. Full remaining unittest discovery passes without removed-surface imports.
4. The wheel and sdist contain only focused Buoy product surfaces.
5. Documentation states the Buoy/Kite boundary and migration impact.
6. Evidence and review records map observed validation to the specification.
7. One bounded commit is pushed and a draft PR targets `develop`; no merge is
   performed.

## Evidence expectations

Record base/final commits, removed and retained surfaces, exact validation
commands/results, package inventories, release-validator behavior, provider
inertness, and confirmation that no remote data or protected branch changed.

## Progress and notes

- 2026-07-30: User ratified the default split and draft-PR finish line.
- 2026-07-30: Created clean worktree `work/refocus-buoy` from fetched
  `origin/develop`.
- 2026-07-30: Historical audit identified `d9ca6db` as the last pure Buoy
  product boundary and confirmed no clean historical tree also contains the
  later database adapters.

## Closure

The focused decision and specification are implemented. The remaining suite
passes 462/462 on Python 3.13 and 462/462 on Python 3.11. Final source,
distribution, ranking, syntax-forecast, lock, diff, link, and clean-wheel
checks pass. Evidence and independent review records map the result to the
active boundary.

The implementation is delivered as one forward commit on
`work/refocus-buoy`, preserving history and tags. Its draft pull request targets
`develop`; no merge, release, provider mutation, legacy-evidence cleanup,
protected-branch change, or personal-site change occurred.
