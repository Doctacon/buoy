Status: active
Created: 2026-08-27
Updated: 2026-08-27
Decision: .10x/decisions/buoy-validates-routing-semantics-not-python-bytes.md
Amends: .10x/specs/bounded-prototype-routing-activation.md, .10x/specs/retrieve-command-telemetry.md

# Routing Semantic Compatibility

## Purpose and scope

Define the behavior-affecting compatibility boundary between Buoy's active automatic-routing implementation and packaged calibration artifact. This specification replaces runtime and distribution validation of evaluator/routing/CLI/evidence Python-file hashes. It does not change calibrated routing behavior.

## Semantic descriptor

Production code MUST expose one canonical semantic descriptor. The active calibration artifact MUST contain an exactly equal descriptor. It has these required fields:

```text
contract_revision = bounded-prototype-routing-v1
artifact_schema = automatic-routing-confidence-v4
routing_algorithm = bounded-prototype-singleton-or-top3-v1
schema_contract = remote-routing-card-schema-v1-v2
projection = separate_prototype_vector_normalized_mean_v1
feature_contract = max_prototype_score_and_margin_v1
score_field = reranker_score
margin_field = reranker_margin
routing_model = BAAI/bge-small-en-v1.5
routing_model_revision = 5c38ec7c405ec4b44b94cc5a9bb96e735b38267a
routing_reranker_model = cross-encoder/ms-marco-MiniLM-L-6-v2
routing_reranker_revision = c5ee24cb16019beea0893ab7796b1df96625c6b8
shortlist_limit = 12
max_examples = 8
confident_selection = singleton_when_score_and_margin_meet_floors
fallback_selection = top3_or_all_when_fewer
explicit_namespace_behavior = bypass_automatic_routing
catalog_policy = certified-exact-otherwise-provisional-v1
```

The representation MUST be strict JSON-compatible data with exact keys, types, and values. Unknown, missing, duplicate, or mismatched fields MUST fail before model construction or content access.

## Artifact migration

The active artifact schema MUST advance to version 4. It MUST preserve current thresholds, certification/calibration fields, canary suite, catalog projection, certified namespace anchor, approval state, historical report identities, and non-source provenance.

Runtime source receipt fields for evaluator runner/scorer, routing, CLI, and evidence Python files MUST be removed from the active schema. Their prior values remain only in immutable historical decisions, evidence, reports, and superseded artifacts. `collect_artifact_sha256` MAY remain as historical artifact provenance but MUST NOT bind current Python implementation bytes.

The artifact's full raw-byte SHA-256 MUST be recorded in durable evidence for releases or promotions that use it. Runtime MUST NOT depend on a separately hand-maintained copy of that full-file hash.

## Behavior

- The loader MUST validate strict artifact schema, semantic descriptor equality, finite thresholds, owner approval, passing certification, canary/catalog identities, and existing provisional catalog policy.
- Any descriptor mismatch MUST fail closed before content access.
- Explicit namespace retrieval MUST retain its established bypass.
- Current score/margin threshold and singleton-versus-top-three behavior MUST remain unchanged.
- File moves, import changes, comments, formatting, and instrumentation MUST NOT require artifact changes unless they alter a descriptor field or tested routing behavior.
- A semantic implementation change MUST update `contract_revision` or a more specific descriptor field and MUST obtain new calibration/promotion evidence before activation.

## Acceptance scenarios

1. Given the current implementation and migrated schema-v4 artifact, automatic routing validates and produces the same focused routing outcomes as before migration.
2. Given any single descriptor field mismatch, automatic routing fails before routing-model construction and content access.
3. Given arbitrary changes to non-semantic source bytes with descriptor and behavior unchanged, loader validation remains valid.
4. Given a modified threshold, certification field, catalog projection, or owner approval, existing fail-closed validation remains effective.
5. Given an explicit namespace request, automatic compatibility loading remains bypassed exactly as before.

## Acceptance criteria

- No runtime, source-tree, wheel, sdist, or installed-package check compares current Python-file hashes to calibration receipts.
- The active artifact has exact schema version 4 and the canonical descriptor above.
- Mutation coverage rejects each descriptor field independently.
- Focused routing, CLI, artifact, telemetry-compatibility, distribution, and full-suite tests pass.
- Semantic before/after tests prove current routing selections, fanout, thresholds, errors, provider/content ordering, and explicit bypass unchanged.

## Explicit exclusions

- Threshold, model, canary, label, catalog, routing-selection, or provisional-policy changes.
- Live collection/evaluation or provider/catalog/content mutation.
- Release, publication, deployment, or integration operations.
