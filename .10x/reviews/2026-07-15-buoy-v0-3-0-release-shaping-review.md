Status: recorded
Created: 2026-07-15
Updated: 2026-07-15
Target: commits `31707ff`, `76bbd90`, and `0871d9d`
Verdict: pass

# Buoy v0.3.0 Release Shaping Review

## Findings

Initial review found four blockers: active authorities still required alias removal in 0.3; main-ancestry incorporation was underspecified; release-environment approval was incorrectly described as the first mutation boundary; and post-release changelog finalization lacked an owner.

The repaired shaping:

- supersedes the prior identity decision with `.10x/decisions/buoy-product-identity-and-compatibility-v0-3.md` and aligns active specs on retention through 0.3/removal target 0.4;
- binds main-ancestry incorporation to GitHub's release-PR update-branch endpoint with expected-head SHA, ancestry verification, and fail-closed behavior;
- records annotated-tag push as the first external mutation and environment approval as the later attestation/Release-assets boundary;
- adds a fourth sequential child for separately reviewed post-release changelog finalization;
- repairs moved decision references and record metadata.

Child scopes, dependencies, statuses, external-side-effect limits, acceptance criteria, and evidence expectations are coherent. Current `main...develop` divergence is one main-only ancestry commit and sixteen develop-only commits; read-only merge-tree inspection found no content conflict.

## Verdict

Pass. The release plan is coherent and the preparation child is executable. Promotion, publication, and changelog finalization remain dependency-blocked.

## Residual risk

GitHub's protected update-branch endpoint and hosted release approval flow were not mutated during shaping review. Their execution tickets require fresh preflight and fail closed if observed behavior differs.
