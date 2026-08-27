Status: active
Created: 2026-08-27
Updated: 2026-08-27
Supersedes: .10x/decisions/superseded/buoy-recertifies-final-reviewed-cli-receipt.md, .10x/decisions/superseded/buoy-recertifies-routing-receipts-for-subpackage-migration-field-correction.md
Amends: .10x/decisions/buoy-activates-certified-bounded-prototype-routing.md

# Buoy Validates Routing Semantics, Not Python Bytes

## Context

Buoy's active routing calibration currently binds exact SHA-256 values of evaluator, routing, CLI, and evidence Python files. This detects semantic drift, but also rejects comments, imports, package paths, telemetry instrumentation, and structural refactors. The subpackage reorganization demonstrated that the mechanism turns behavior-preserving maintenance into repeated recertification without increasing confidence in routing quality.

The actual safety requirement is narrower: calibrated thresholds must run only with compatible routing algorithms, features, models, schemas, and selection semantics. Raw implementation bytes are an overly broad proxy for that contract and do not constitute a security boundary when the package's Python code itself can be replaced.

## Decision

Buoy will validate a strict semantic routing compatibility descriptor rather than exact Python-file hashes. The descriptor binds behavior-affecting schema, algorithm, feature, projection, model/revision, shortlist, selection, and output-field identities. The active calibration artifact remains strict and fail-closed when that descriptor, its calibrated thresholds, its certification state, or its catalog projection is incompatible.

Evaluator, routing, CLI, and evidence source hashes will be removed from runtime activation requirements and package-installed-byte tests. Historical reports and evidence retain their original source hashes as provenance; they are not rewritten.

Behavioral and mutation tests MUST prove that each semantic descriptor mismatch fails before content access. A semantic change requires an explicit descriptor revision and new calibration/promotion evidence. A behavior-preserving refactor, import update, file move, formatting change, or telemetry instrumentation does not.

Existing routing thresholds, models, canary data, catalog projection, selection behavior, explicit-namespace bypass, fail-closed ordering, privacy boundaries, and provider/content mutation limits remain unchanged.

## Alternatives considered

### Continue hashing source files

Rejected because it has a high false-positive rate and materially slows ordinary repository maintenance.

### Validate only one integer version

Rejected because it makes accidental model, schema, feature, or selection mismatches easier to miss.

### Remove runtime compatibility validation

Rejected because calibrated thresholds still need a mechanically enforced semantic boundary.

## Consequences

Structural refactors no longer require routing receipt recertification. Review must focus on whether a change affects the semantic descriptor. Historical source identities remain available for reproducing old certification claims, while active runtime compatibility becomes smaller and user-legible.
