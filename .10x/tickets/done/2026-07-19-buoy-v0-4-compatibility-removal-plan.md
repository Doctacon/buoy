Status: done
Created: 2026-07-19
Updated: 2026-07-19
Parent: None
Depends-On: .10x/tickets/done/2026-07-18-shape-v0-4-compatibility-removal.md

# Buoy 0.4 Compatibility Removal Plan

## Outcome

Deliver the user-ratified Buoy 0.4.0 hard removal of exactly one installed console alias and two deprecated embedding environment aliases, with coherent package/runtime/docs/tests and reproducible clean-install plus released-0.3.0 upgrade evidence. Preserve all other compatibility and perform no state, data, remote, publication, tag, or release operation.

This parent is an aggregate plan and is not executable.

## Child graph

- `.10x/tickets/done/2026-07-19-remove-buoy-v0-4-console-alias.md` owns the package entry point, dedicated legacy hook, candidate version metadata needed for the 0.4.0 wheel, console migration guidance, and clean/upgrade wheel validation.
- `.10x/tickets/done/2026-07-19-remove-buoy-v0-4-environment-aliases.md` owns the pre-dispatch environment gate, exact diagnostics, complete command/help/version matrix, configuration migration guidance, and no-side-effect validation.
- `.10x/tickets/done/2026-07-19-exclude-internal-records-from-buoy-v0-4-artifacts.md` owns the post-assembly packaging repair that retains repository `.10x/**` records while excluding exactly those records from both artifacts, proving controlled record-only artifact stability, and rerunning aggregate install/upgrade validation.

The compatibility-removal children have no semantic dependency and their implementation/review work proceeded in parallel in separate task worktrees. They intentionally share the 0.4.0 boundary and MUST be reconciled into one aggregate candidate before integration: neither removal may land on `develop` without the other, and the 0.4.0 version metadata MUST agree across package/module/lock artifacts. Documentation/changelog conflicts are reconciled without broadening either child's behavior. The packaging child depends on the assembled candidate evidence and now blocks aggregate acceptance.

## Aggregate acceptance criteria

- A candidate 0.4.0 distribution exposes only `buoy`; `pyproject.toml` has no `turbo-search` script and `buoy_search.cli` has no `legacy_main` hook.
- Every successfully parsed actual primary or autoresearch command rejects either removed variable before handler dispatch with exit 2, empty stdout even under `--json`, and one exact value-redacted diagnostic ordered model then precision.
- Help/version and parsed no-handler help remain available with removed variables present; parser failures remain parser failures.
- Clean candidate installation and same-environment upgrade from the immutable, digest-verified released GitHub 0.3.0 wheel prove primary-launcher continuity and old package-owned launcher removal.
- Focused/full supported-Python tests, wheel/sdist build and inspection, docs/changelog/reference checks, independent child reviews, aggregate review, and hosted checks pass.
- Repository `.10x/**` records remain tracked but neither wheel nor sdist contains a `.10x` entry; under controlled deterministic conditions, adding only `.10x/**` evidence leaves corresponding wheel and sdist bytes and SHA-256 digests unchanged.
- `.turbo-search` state fallback, old plans, flags, source aliases, migration commands, current `BUOY_*`/`TURBOPUFFER_*`, direct-command defaults, IDs, artifacts, local data, and remote identity/behavior remain unchanged.
- No validation publishes packages, creates tags/releases, uses live Turbopuffer, or mutates user state/data.

## Integration and evidence expectations

Each child records exact commands, focused/full results, changed paths, stream/exit assertions, package or sentinel observations, and explicit side-effect limits. Aggregate integration verifies all three active specifications against the combined diff, candidate 0.4.0 metadata, distribution artifacts, hosted checks, and independent reviews before either child or this plan closes.

The two stale retrieval-mode and apply-namespace statements in `.pi/skills/turbopuffer-site-rag/references/scrapling-site-workflow.md` are separately owned by `.10x/tickets/2026-07-19-reconcile-scrapling-site-workflow-direct-command-guidance.md`; neither is implementation scope or evidence for this plan.

## Blockers

None. The previously observed `.10x/**` sdist defect is resolved at exact reviewed head `9e7ec237d31d9fb4ef79209df1d45fcc2b0dd6cf`: `.10x/evidence/2026-07-19-exclude-internal-records-from-buoy-v0-4-artifacts.md` records the exact repository-root exclusion, zero `.10x` members in both artifacts, byte-identical controlled record-only builds, refreshed aggregate install/upgrade validation, and passing exact-head hosted checks. The parent and all three children remain active/open pending final bounded re-review; that acceptance step is not a current implementation blocker.

## Explicit exclusions

Any compatibility beyond the three named aliases; any artifact exclusion beyond repository-root `.10x/**`; removal or relocation of repository records; runtime/package-code, bundled-data, or user-documentation changes for the packaging repair; arbitrary user-owned launchers; state/data migration or deletion; live product-service reads/writes (authorized GitHub PR/check delivery operations are allowed); PyPI publication; Git tags; GitHub Release creation; stale skill-reference corrections; unrelated parser/config/refactoring work.

## References

- `.10x/specs/buoy-v0-4-console-alias-removal.md`
- `.10x/specs/buoy-v0-4-environment-alias-removal.md`
- `.10x/specs/buoy-v0-4-internal-record-artifact-exclusion.md`
- `.10x/decisions/buoy-product-identity-and-compatibility-v0-3.md`
- `.10x/research/2026-07-19-v0-4-compatibility-removal-inventory.md`
- `.10x/reviews/2026-07-19-v0-4-compatibility-removal-shaping-review-response.md`
- `.10x/reviews/2026-07-19-buoy-v0-4-aggregate-packaging-blocker-review.md`
- `.10x/reviews/2026-07-19-buoy-v0-4-compatibility-removal-final-aggregate-review.md`
- `.10x/tickets/done/2026-07-18-shape-v0-4-compatibility-removal.md`

## Progress and notes

- 2026-07-19: User ratified the reviewer's exact recommended command boundary, diagnostics, console deletion, upgrade procedure, retained compatibility, and no-side-effect contract. Opened two bounded implementation children; no implementation began.
- 2026-07-19: Aggregate candidate commit `68477fdca5a5b5f7b890d059c484739f02fc1dd8` non-fast-forward merged both full reviewed child tips onto `31b355a`. Resolved only the shared changelog and CLI-test conflict by retaining both active-spec contracts; automatic shared docs/CLI/release-test reconciliation also retained both child diffs. Local Python 3.11/3.13 suites, exhaustive gate tests, wheel/sdist inspection, clean install, digest-verified released-0.3.0 same-environment upgrade, launcher absence, and diff/reference/history checks passed. Evidence: `.10x/evidence/2026-07-19-buoy-v0-4-compatibility-removal-candidate.md`. Independent aggregate review remains pending; this non-executable plan stays active.
- 2026-07-19: Opened aggregate PR #49 against `develop` without merging. Hosted workflow `29708550897` passed Python 3.11 (`88249318152`), Python 3.13 (`88249318150`), and distribution (`88249388732`) jobs on pushed evidence head `6d4a24c27c215cc40ddcb9e8d4d66211ed2d445d`. A record-only follow-up documents hosted results; exact final-head checks remain visible on PR #49.
- 2026-07-19: Aggregate packaging review found that the recorded 536-entry candidate sdist contains 441 `.10x` entries while the 45-entry wheel contains none. The user ratified excluding exactly repository-root `.10x/**` from both artifacts while retaining the records, plus a controlled record-only determinism proof and aggregate clean-install/upgrade rerun. Opened the focused active spec and executable packaging child; no exclusion was implemented. Parent and all children remain active and aggregate acceptance is blocked pending that child.
- 2026-07-19: Packaging child implementation now excludes only repository-root `.10x/**`; controlled before/after builds across one staged evidence-record delta were byte-identical with zero `.10x` members, and aggregate Python 3.11/3.13, exact gate/no-side-effect, clean-install, and digest-verified same-environment upgrade validation passed. Evidence: `.10x/evidence/2026-07-19-exclude-internal-records-from-buoy-v0-4-artifacts.md`. Parent and all children remain active pending independent bounded/final aggregate review and exact-head hosted checks; no merge, publication, tag, release, state/data mutation, or live product-service operation occurred.
- 2026-07-19: Final aggregate review of exact head `9e7ec237d31d9fb4ef79209df1d45fcc2b0dd6cf` passed the implementation and raised one record-coherence concern: this plan and the packaging child still described the already-proven exclusion as unimplemented/currently blocking. Reconciled both current Blockers sections against the final packaging evidence and review `.10x/reviews/2026-07-19-buoy-v0-4-compatibility-removal-final-aggregate-review.md`.
- 2026-07-19: Final bounded re-review confirmed record coherence. Parent-observed exact-head Python 3.11, Python 3.13, and distribution checks passed at `3e35c77df0d3a3c6109807203d58e3e0380dbdae`; PR #49 was clean and mergeable. All three children and aggregate criteria are supported by evidence and review. Review: `.10x/reviews/2026-07-19-buoy-v0-4-compatibility-removal-closure-review.md`.

## Closure mapping

- Console removal and upgrade behavior: child evidence and independent child review.
- Environment rejection and no-side-effect boundary: exhaustive child/aggregate tests, evidence, and review.
- Internal-record artifact boundary: controlled deterministic artifacts, zero-member inventories, aggregate install/upgrade evidence, and review.
- Integration coherence: both reviewed child tips preserved, shared conflicts reconciled, 0.4.0 metadata coherent, full suites and exact-head hosted checks passed.
- Side effects: no publication, tag, release, state/data mutation, or live product-service operation.

## Retrospective

Artifact evidence cannot self-attest exact heads when project records are shipped inside the artifact whose hash they record. Excluding repository-internal `.10x/**` records from distributions creates a stable evidence boundary while preserving durable repository memory. Aggregate version cutovers should establish that boundary before final artifact hashing.
