Status: recorded
Created: 2026-07-15
Updated: 2026-07-15
Target: commits `e823aba` and `ab2d89f`; integrated catalog/apply commits through `ac6a3ca`
Verdict: pass

# Automatic Production Semantic Routing Review

## Target

Independent algorithm/runtime, CLI/safety, and holistic cross-slice review of the completed production semantic routing stack.

## Findings and resolution

Initial child review passed all substantive routing behavior and found two minor gaps: explicit retrieval error precedence had shifted, and fail-closed catalog/model tests did not sentinel credential reads. Corrective commit `ab2d89f` restored explicit namespace-before-empty-query precedence while keeping auto-route query validation, and added credential-read sentinels for missing/corrupt catalog and missing route model. Final re-review passed.

A separate holistic review checked catalog → apply card → router compatibility and the parent acceptance criteria.

## Correct

- Auto-route is explicitly opt-in; explicit retrieval bypasses catalog/model routing and retains existing output paths.
- Enabled/region/model/precision/dimension/schema/ranking eligibility gates run before relevance scoring.
- Lexical phrase ranking, persisted-vector semantic ranking, deterministic ties, equal imported `RRF_K=60` hybrid fusion, and top-three default truncation match the active spec.
- Apply-generated cards provide the exact contracts consumed by routing.
- Dry preview is local-only and vector-redacted; failure occurs before credential/live-client work.
- Live routing preserves route order, per-card ranking values plus independent CLI overrides, one retrieval embedding, sequential all-or-nothing namespace calls, namespace-qualified evidence, and existing downstream RRF/global top-k.
- Routed output remains explicit even for one selected namespace; no vectors, telemetry, query persistence, remote discovery/catalog, ACL, taxonomy, or graph was added.
- Documentation matches activation, environment/path precedence, overrides, failure behavior, and local-model requirements.
- 125 focused and 363 full-suite tests, compilation, and `git diff --check` passed.
- Prior catalog and apply children retain passing durable reviews.

## Verdict

Pass. No blocker remains. Child 3 and the production parent satisfy closure gates.

## Residual risk

No live Turbopuffer call was performed during validation. Actual account namespaces, latency, and user-perceived routing quality remain intentionally user-judged in live use. Explicit namespace retrieval remains the fail-closed fallback.
