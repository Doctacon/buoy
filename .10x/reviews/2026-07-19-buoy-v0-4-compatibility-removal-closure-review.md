Status: recorded
Created: 2026-07-19
Updated: 2026-07-19
Target: .10x/tickets/done/2026-07-19-buoy-v0-4-compatibility-removal-plan.md
Verdict: pass

# Buoy 0.4 Compatibility Removal Closure Review

## Target

PR #49 at exact final pre-closure head `3e35c77df0d3a3c6109807203d58e3e0380dbdae`.

## Findings

Independent aggregate review confirmed the implementation and artifact evidence satisfy all three active specifications. It initially raised only stale blocker text; a bounded re-review confirmed that record-coherence issue resolved and found no remaining content blocker.

Parent-observed exact-head GitHub checks then passed:

- Python 3.11: workflow `29709772643`, job `88252016214`;
- Python 3.13: workflow `29709772643`, job `88252016218`;
- Build distributions: workflow `29709772643`, job `88252056880`.

GitHub reported PR #49 clean and mergeable at the same head. Because `.10x/**` is excluded from both artifacts, closure-only record changes do not change the validated wheel or sdist payload/hashes.

Acceptance is supported for:

- coherent 0.4.0 package/module/lock metadata;
- sole `buoy` package launcher and removal of `legacy_main`;
- exact post-parse/pre-dispatch old-environment rejection contract;
- retained unrelated compatibility;
- zero `.10x` entries in wheel/sdist and byte-identical deterministic artifacts across a record-only delta;
- clean installation and digest-verified released-0.3.0 same-environment upgrade;
- complete Python 3.11/3.13 suites, focused checks, hosted checks, and bounded side-effect attestations.

## Verdict

Pass. The three children and aggregate parent are closure-eligible.

## Residual risk

Local deterministic build/install/upgrade validation was macOS arm64/Python 3.13; hosted Linux CI covered Python 3.11/3.13 source and distribution construction but not a second full upgrade exercise. Live product-service behavior was intentionally not exercised; side-effect safety is supported by source inspection and sentinel/non-dispatch tests. Package-owned launchers are removed; arbitrary user-created aliases are outside scope.
