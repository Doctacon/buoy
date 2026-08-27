Status: recorded
Created: 2026-08-27
Updated: 2026-08-27
Target: .10x/tickets/done/2026-08-27-decouple-evidence-from-source-layout-plan.md
Verdict: fail

# Evidence/layout aggregate implementation review

## Target

Complete working-tree implementation for the parent plan and its routing semantic compatibility, versioned repository evaluation, ranking promotion gate, and subpackage integration children.

Independent reviewer runs:

- routing: `b0beb102-586a-4373-8910-82b03cd2fe2f`
- eval versioning: `7cc6c617-a0f8-4599-8297-39c0023d5d46`
- promotion gate: `84cc8f59-dc40-4c2b-a78a-3525459bba12`
- aggregate: `000bc35b-b4ba-40a9-b8cd-9f61a6a19b7e`

## Findings

### Significant: hosted distribution CI imports removed flat modules

`.github/workflows/ci.yml` clean-wheel smoke imports `buoy_search.treatment_token_budget` and `buoy_search.routing_quality`. Those paths were intentionally removed. Local package checks did not execute these workflow-embedded imports, so hosted distribution CI would fail.

### Significant: pending evaluation data can authorize promotion

The promotion validator matches active v2 identity fields but does not reject `baseline_status=pending` or require a recorded immutable benchmark/corpus identity. The passing fixture therefore contradicts the governing rule that pending v2 cannot support promotion.

### Significant: pending path membership is represented as a corpus manifest

The v2 manifest records paths and a path-set hash but no repository/source snapshot or content identity. Calling it a corpus manifest overstates its authority. Pending versions may use explicit path-membership manifests, but promotion requires a recorded content-addressed corpus identity.

### Significant: promotion evidence does not bind the full 13-repository basket

The validator requires 13 result rows but binds only the Buoy dataset/corpus fields. All repositories used by the promotion policy need one versioned basket identity containing each dataset and corpus identity.

### Significant: baseline and candidate configurations may differ

The validator requires non-empty retrieval option objects but not equality. Candidate gains could therefore come from unrelated `top_k`, model, corpus, or retrieval-setting differences instead of the proposed authority change.

### Significant: credential exclusion is key-name-only

Free-form retrieval options can contain headers, URLs, or credentials under innocuous keys/values. Promotion artifacts require a strict allowlisted safe schema and value validation.

### Significant: push CI can bypass promotion comparison

The workflow supplies a merge base only for pull requests. Pushes to protected branches can classify as `base-unavailable` and pass. Push events must use their previous SHA, and CI must fail closed when a required comparison base is unavailable outside explicit one-time introduction.

### Minor: stale schema names in routing tests

Several tests exercise schema v4 under schema-v2/v3 names. Rename them to current schema terminology while retaining explicit obsolete-schema rejection coverage.

## Verdict

Fail. Core architecture and local validation are promising, but the promotion authority and hosted CI gaps are significant and must be repaired before closure.

## Residual risk

No reviewer independently ran commands, and no GitHub-hosted workflow has run. Repair requires a fresh independent aggregate review and complete validation.
