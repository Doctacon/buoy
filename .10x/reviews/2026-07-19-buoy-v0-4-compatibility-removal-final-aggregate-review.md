Status: recorded
Created: 2026-07-19
Updated: 2026-07-19
Target: .10x/tickets/done/2026-07-19-buoy-v0-4-compatibility-removal-plan.md
Verdict: concerns

# Buoy 0.4 Compatibility Removal Final Aggregate Review

## Target

PR #49 at exact reviewed head `9e7ec237d31d9fb4ef79209df1d45fcc2b0dd6cf`, including the console-alias removal, environment-alias removal, repository-root `.10x/**` artifact exclusion, aggregate evidence, and exact-head hosted checks.

## Findings

### Implementation passes

The bounded implementation has no identified source, test, build, or packaging defect at the reviewed head. The exact Hatch configuration excludes only repository-root `.10x/**`; the focused assertion requires that exact configuration. Controlled builds across a single staged `.10x/**` evidence-record delta produced byte-identical 45-member wheels and 95-member sdists with zero `.10x` members and matching before/after SHA-256 digests. Repository records remain tracked.

Aggregate Python 3.11 and 3.13 suites each passed 422 tests; 75 focused packaging, environment-gate, CLI, autoresearch, and release tests passed. Clean candidate installation and the digest-verified released-0.3.0 same-environment upgrade passed, including removal of the package-owned `turbo-search` launcher. Exact pushed head `9e7ec237d31d9fb4ef79209df1d45fcc2b0dd6cf` passed hosted Python 3.11, Python 3.13, and distribution jobs in workflow `29709578755`.

### Significant record-coherence concern

The implementation evidence contradicts two current Blockers sections: the parent still says aggregate acceptance is blocked by `.10x/**` in the sdist, and the packaging child says `None` before immediately saying the same defect still blocks acceptance until implementation. Those present-tense statements are stale. They make the active ticket graph claim that an exact-head-proven repair remains unimplemented even though later progress and `.10x/evidence/2026-07-19-exclude-internal-records-from-buoy-v0-4-artifacts.md` prove otherwise.

The pre-repair observations in `.10x/evidence/2026-07-19-buoy-v0-4-compatibility-removal-candidate.md` and `.10x/reviews/2026-07-19-buoy-v0-4-aggregate-packaging-blocker-review.md` remain valid historical snapshots of their older targets; they do not describe the current implementation state. Current ticket Blockers must explicitly mark that packaging defect resolved by the later exact-head evidence. Parent and all three children must remain active/open pending a final bounded re-review; that pending review is an acceptance step, not evidence that the packaging implementation is absent.

## Verdict

Concerns raised on record coherence only. Implementation passes at exact reviewed head `9e7ec237d31d9fb4ef79209df1d45fcc2b0dd6cf`. Reconcile the parent and packaging-child Blockers and progress against the final packaging evidence, then perform one bounded re-review. Do not close or move the parent or any child based on this review.

## Residual risk

- Local deterministic build, install, and upgrade validation used macOS arm64 and CPython 3.13; source suites and hosted Linux checks cover Python 3.11 and 3.13, but hosted clean-install and released-wheel upgrade were not separately exercised.
- No live remote product behavior was exercised; pre-dispatch and no-side-effect behavior is supported by sentinel tests, installed-wheel validation, and existing non-live suites.
- Upgrade evidence proves removal of the package-owned launcher only, not arbitrary user-owned aliases, wrappers, copies, or caches.
- No publication, tag, GitHub Release, state/data mutation, or live product-service operation occurred. PR #49 remains open and unmerged.
