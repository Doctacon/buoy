Status: superseded
Created: 2026-08-27
Updated: 2026-08-27
Supersedes: .10x/decisions/superseded/buoy-recertifies-routing-receipts-for-subpackage-migration.md
Amends: .10x/decisions/buoy-activates-certified-bounded-prototype-routing.md

# Buoy Recertifies Routing Receipts for the Subpackage Migration — Field Correction

## Context

The superseded decision correctly authorized narrow recertification of the four source files moved by `.10x/specs/buoy-search-subpackage-layout.md`, but it named the routing-quality artifact field `routing_quality_module_sha256`. Inspection of the active artifact and production loader proves that no such field exists. The existing receipt for `src/buoy_search/evals/routing_quality.py` is `receipts.evaluator_scorer_sha256`. The other three authorized field names were correct.

The owner authorized recertifying the four explained source hashes, not creating a new artifact field. This correction makes that authorization executable without changing its semantic or operational boundary.

## Decision

Buoy MAY recertify exactly these four existing receipt fields against the final reviewed relocated source bytes:

- `receipts.evaluator_scorer_sha256` for `src/buoy_search/evals/routing_quality.py`
- `receipts.routing_module_sha256` for `src/buoy_search/retrieval/routing.py`
- `receipts.cli_module_sha256` for `src/buoy_search/cli/main.py`
- `receipts.evidence_module_sha256` for `src/buoy_search/retrieval/evidence.py`

No new field may be added. Before and after comparison MUST prove that exactly these four string values changed and every other parsed field and text line remained unchanged except those value lines.

All validation, review, exclusion, and authorization boundaries from the superseded decision remain unchanged: source deltas must be relocation-only; routing semantics, thresholds, calibration/certification data, reports, projections, evaluator identities, revisions, policies, and other receipts remain frozen; no live, provider, credential, catalog, release, publication, or deployment operation is authorized.

## Alternatives considered

### Add `routing_quality_module_sha256`

Rejected because it would change the artifact schema and would not match the production loader.

### Treat the mismatch as implicit

Rejected because receipt authority is fail-closed and must name the exact existing field before mutation.

## Consequences

The recertification ticket can proceed against the actual artifact schema. This correction grants no additional source, artifact, semantic, or operational scope.
