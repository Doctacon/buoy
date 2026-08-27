Status: active
Created: 2026-08-27
Updated: 2026-08-27
Supersedes: .10x/decisions/superseded/buoy-refreshes-repo-eval-corpus-identity-for-subpackage-layout.md
Amends: .10x/decisions/repo-ranking-promotion-policy.md

# Buoy Versions Repository Evaluations and Gates Only Default Promotion

## Context

The frozen ranking contract currently serves both as immutable historical evidence and as a current-checkout regression fixture. That coupling requires historical paths and corpus identities to match `HEAD`, so ordinary file moves cascade through frozen manifests, dataset hashes, tests, and approval records.

The project still needs reproducible benchmark claims, preserved judgments, and distribution-aware promotion evidence. It does not need every implementation PR to reproduce or rewrite historical benchmarks.

## Decision

Repository evaluation datasets, corpus manifests, and benchmark results will be immutable versioned artifacts. Historical versions are validated against their recorded source snapshot, never against the current checkout. Current development uses an explicit successor dataset/corpus version with lineage to its predecessor.

The reorganized Buoy dataset MAY carry forward existing judgment semantics through an explicit old-to-new path mapping and remain `baseline_pending`. Historical scores stay attached to the historical corpus; no current score is claimed until a new benchmark runs.

Every PR runs the same fast deterministic integrity and behavior suite. Full ranking benchmarks are required only to promote active ranking defaults. A PR is mechanically a promotion PR exactly when it changes the single packaged ranking-default authority file. Such a change must reference a complete immutable same-corpus baseline/candidate benchmark artifact that passes `.10x/decisions/repo-ranking-promotion-policy.md`. Adding or changing experimental ranking implementation without changing the authority file is not a promotion.

Runtime routing calibration and repository ranking evaluation remain separate authority surfaces. No provider/model/retrieval operation is required merely to version a dataset, migrate paths, or merge a `baseline_pending` current eval.

## Alternatives considered

### Keep one frozen dataset coupled to `HEAD`

Rejected because it rewrites history or blocks ordinary refactors.

### Run the full benchmark for every ranking-related source change

Rejected because source-path classification is broad and ranking implementation may remain inactive indefinitely.

### Identify promotion PRs by labels or contributor intent

Rejected because manual classification is easy to omit. Changing one authority file is mechanically checkable.

## Consequences

Historical benchmark evidence remains reproducible and immutable. Current evaluation data can evolve honestly. Normal PRs stay fast. Expensive evidence is paid for at the moment it matters: changing defaults. A current dataset with no benchmark is visibly `baseline_pending` and cannot support promotion claims.
