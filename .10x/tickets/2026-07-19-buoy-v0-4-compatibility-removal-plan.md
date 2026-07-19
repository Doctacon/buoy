Status: open
Created: 2026-07-19
Updated: 2026-07-19
Parent: None
Depends-On: .10x/tickets/done/2026-07-18-shape-v0-4-compatibility-removal.md

# Buoy 0.4 Compatibility Removal Plan

## Outcome

Deliver the user-ratified Buoy 0.4.0 hard removal of exactly one installed console alias and two deprecated embedding environment aliases, with coherent package/runtime/docs/tests and reproducible clean-install plus released-0.3.0 upgrade evidence. Preserve all other compatibility and perform no state, data, remote, publication, tag, or release operation.

This parent is an aggregate plan and is not executable.

## Child graph

- `.10x/tickets/2026-07-19-remove-buoy-v0-4-console-alias.md` owns the package entry point, dedicated legacy hook, candidate version metadata needed for the 0.4.0 wheel, console migration guidance, and clean/upgrade wheel validation.
- `.10x/tickets/2026-07-19-remove-buoy-v0-4-environment-aliases.md` owns the pre-dispatch environment gate, exact diagnostics, complete command/help/version matrix, configuration migration guidance, and no-side-effect validation.

The children have no semantic dependency and their implementation/review work may proceed in parallel in separate task worktrees. They intentionally share the 0.4.0 boundary and MUST be reconciled into one aggregate candidate before integration: neither removal may land on `develop` without the other, and the 0.4.0 version metadata MUST agree across package/module/lock artifacts. Documentation/changelog conflicts are reconciled without broadening either child's behavior.

## Aggregate acceptance criteria

- A candidate 0.4.0 distribution exposes only `buoy`; `pyproject.toml` has no `turbo-search` script and `buoy_search.cli` has no `legacy_main` hook.
- Every successfully parsed actual primary or autoresearch command rejects either removed variable before handler dispatch with exit 2, empty stdout even under `--json`, and one exact value-redacted diagnostic ordered model then precision.
- Help/version and parsed no-handler help remain available with removed variables present; parser failures remain parser failures.
- Clean candidate installation and same-environment upgrade from the immutable, digest-verified released GitHub 0.3.0 wheel prove primary-launcher continuity and old package-owned launcher removal.
- Focused/full supported-Python tests, wheel/sdist build and inspection, docs/changelog/reference checks, independent child reviews, aggregate review, and hosted checks pass.
- `.turbo-search` state fallback, old plans, flags, source aliases, migration commands, current `BUOY_*`/`TURBOPUFFER_*`, direct-command defaults, IDs, artifacts, local data, and remote identity/behavior remain unchanged.
- No validation publishes packages, creates tags/releases, uses live Turbopuffer, or mutates user state/data.

## Integration and evidence expectations

Each child records exact commands, focused/full results, changed paths, stream/exit assertions, package or sentinel observations, and explicit side-effect limits. Aggregate integration verifies both active specifications against the combined diff, candidate 0.4.0 metadata, distribution artifacts, hosted checks, and independent reviews before either child or this plan closes.

The two stale retrieval-mode and apply-namespace statements in `.pi/skills/turbopuffer-site-rag/references/scrapling-site-workflow.md` are separately owned by `.10x/tickets/2026-07-19-reconcile-scrapling-site-workflow-direct-command-guidance.md`; neither is implementation scope or evidence for this plan.

## Blockers

None. The user ratified all execution-critical semantics on 2026-07-19.

## Explicit exclusions

Any compatibility beyond the three named aliases; arbitrary user-owned launchers; state/data migration or deletion; remote reads/writes; PyPI publication; Git tags; GitHub Release creation; stale skill-reference corrections; unrelated parser/config/refactoring work.

## References

- `.10x/specs/buoy-v0-4-console-alias-removal.md`
- `.10x/specs/buoy-v0-4-environment-alias-removal.md`
- `.10x/decisions/buoy-product-identity-and-compatibility-v0-3.md`
- `.10x/research/2026-07-19-v0-4-compatibility-removal-inventory.md`
- `.10x/reviews/2026-07-19-v0-4-compatibility-removal-shaping-review-response.md`
- `.10x/tickets/done/2026-07-18-shape-v0-4-compatibility-removal.md`

## Progress and notes

- 2026-07-19: User ratified the reviewer's exact recommended command boundary, diagnostics, console deletion, upgrade procedure, retained compatibility, and no-side-effect contract. Opened two bounded implementation children; no implementation began.
