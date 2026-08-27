Status: done
Created: 2026-08-27
Updated: 2026-08-27
Parent: .10x/tickets/done/2026-08-27-decouple-evidence-from-source-layout-plan.md
Depends-On: None

# Implement routing semantic compatibility

## Scope

Implement `.10x/specs/routing-semantic-compatibility.md`: introduce the canonical semantic descriptor, migrate the active calibration artifact to strict schema v4, remove current Python-file receipts from runtime/package validation, and preserve established routing behavior.

## Acceptance criteria

- Exact descriptor and schema-v4 artifact match the governing spec.
- Current evaluator/routing/CLI/evidence file hashes are absent from active runtime and package validation.
- Prior source hashes remain untouched in historical evidence/records.
- Mutation tests fail closed for each descriptor field before content/model access.
- Focused routing, artifact, CLI, telemetry compatibility, full tests, wheel/sdist, and installed-package checks pass.
- Semantic before/after evidence proves unchanged thresholds, selections, fanout, explicit bypass, errors, privacy, and provider/content ordering.

## Explicit exclusions

Any threshold, model, canary, catalog, selection, telemetry, live operation, release, or unrelated refactor change.

## Evidence expectations

Artifact semantic comparison, removed-receipt inventory, descriptor mutation matrix, focused/full/package outputs, behavior parity evidence, diff summary, and residual risks.

## Blockers

None.

## Progress and notes

- 2026-08-27: Opened from the ratified semantic-compatibility specification. No implementation occurred in this record-authoring turn.
- 2026-08-27: Implemented strict schema-v4 semantic compatibility with the exact 18-field descriptor, removed five Python-byte receipts and installed-byte hashing, preserved routing thresholds/bindings/calibration/certification/non-source provenance, and migrated evaluator serialization/readiness checks.
- 2026-08-27: Added/updated strict schema, all-18-field mutation, before-model mismatch, evaluator-gate, production behavior, and provenance tests. Focused routing passed `117 + 135 subtests`; broad routing/CLI/telemetry/provider compatibility passed `271 + 345 subtests`.
- 2026-08-27: Full suite reached `1167 passed, 1222 subtests passed` with exactly ten known historical eval-path failures owned by the next child. Wheel/sdist build and inventory passed; isolated wheel semantic loading and explicit bypass passed. Artifact SHA-256 is `448e46d9522b6267b5db46a5f38e635f41c68e54514cc0b0e12c4d47bdb7a4b4`. No files staged and no external/live operations. Evidence: `.10x/evidence/2026-08-27-routing-semantic-compatibility-implementation.md`.
- 2026-08-27: Aggregate integration after all dependencies passed 1176 tests on Python 3.11 and 3.13, package/isolated semantic validation, CLI/import/shim audits, and diff hygiene. Evidence: `.10x/evidence/2026-08-27-buoy-search-subpackage-final-integration.md`. Ticket remains active pending independent review.
- 2026-08-27: Addressed the routing P2/minor finding from `.10x/reviews/2026-08-27-evidence-layout-aggregate-review.md`. Renamed seven stale current-active schema-v2/v3 test methods and the schema-mode fixture/label to truthful schema-v4 terminology while preserving `test_obsolete_schema_v2_active_artifact_is_rejected`. Focused routing validation passed `117 tests, 135 subtests`; collection audit found no stale current-active schema-v2/schema-v3 names; diff hygiene passed and no files are staged. Updated `.10x/evidence/2026-08-27-routing-semantic-compatibility-implementation.md`.
- 2026-08-27: Final aggregate repair passed exact Python 3.11/3.13 suites, routing semantic package/isolated checks, hosted workflow smoke, and complete layout/hygiene validation. Evidence: `.10x/evidence/2026-08-27-buoy-search-subpackage-final-integration.md`.
- 2026-08-27: Fresh independent aggregate review passed with no findings: `.10x/reviews/2026-08-27-evidence-layout-final-review.md`. Closed after acceptance criteria, evidence, specification coherence, and exclusions were rechecked.

## Closure mapping

The schema-v4 descriptor/artifact, removal of runtime Python-byte receipts, all-field fail-closed mutation coverage, behavior parity, full dual-runtime suites, distributions, and isolated package checks are supported by `.10x/evidence/2026-08-27-routing-semantic-compatibility-implementation.md` and aggregate integration evidence. Final review passed.

## Retrospective

Raw source hashes are too sensitive for semantic compatibility. A small explicit descriptor plus behavior/mutation tests preserves the fail-closed boundary while allowing structural maintenance.
