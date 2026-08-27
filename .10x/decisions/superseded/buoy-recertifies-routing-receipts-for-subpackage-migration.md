Status: superseded
Created: 2026-08-27
Updated: 2026-08-27
Amends: .10x/decisions/buoy-activates-certified-bounded-prototype-routing.md

# Buoy Recertifies Routing Receipts for the Subpackage Migration

## Context

The approved structural migration governed by `.10x/specs/buoy-search-subpackage-layout.md` moved four source files whose exact bytes are bound by the active packaged routing-confidence artifact. Import and package-relative lookup changes altered those bytes, so the active loader correctly rejects the old receipts even though no routing semantics, thresholds, calibration cases, catalog projection, or eligibility rules were intentionally changed.

The prior recertification authority in `.10x/decisions/superseded/buoy-recertifies-final-reviewed-cli-receipt.md` applies only to command-telemetry CLI repairs and cannot authorize rebinding all four migrated files. The migration is therefore blocked as recorded in `.10x/evidence/2026-08-27-buoy-search-subpackage-reorganization-blocked-validation.md`.

On 2026-08-27 the owner approved a narrow recertification after receiving an explanation that the hashes are tamper-detection receipts and that recertification would verify path/import-only diffs without changing routing thresholds or calibration data.

## Decision

Buoy MAY recertify exactly these four artifact receipt fields against the final reviewed subpackage-migration bytes:

- `routing_quality_module_sha256` for `src/buoy_search/evals/routing_quality.py`
- `routing_module_sha256` for `src/buoy_search/retrieval/routing.py`
- `cli_module_sha256` for `src/buoy_search/cli/main.py`
- `evidence_module_sha256` for `src/buoy_search/retrieval/evidence.py`

Before updating the artifact, execution MUST verify that changes to these four modules are limited to relocation-required imports, package-relative paths, and repository-source path judgments. It MUST compare the parsed artifact before and after and prove that exactly the four receipt values changed. All thresholds, calibration/certification cases and digests, semantic catalog projection, evaluator identities, reports, revisions, policy fields, and other receipts MUST remain unchanged.

After rebinding, execution MUST run the routing certification/validation checks, the full repository suite, CLI validation, wheel build and inventory, and installed-wheel validation needed to prove that the packaged loader accepts the new exact bytes. Independent review MUST confirm both the structural migration and narrow artifact delta before either ticket can close.

Any semantic routing change, calibration-data regeneration, threshold change, live collection/evaluation, provider operation, catalog/card/content mutation, credential access, release, publication, deployment, or compatibility forwarding module remains unauthorized.

## Alternatives considered

### Leave the migration blocked

Rejected. It would preserve stale receipts and leave the approved package reorganization unable to pass its test suite or automatic-routing validation.

### Restore compatibility copies at old paths

Rejected. The owner explicitly selected a breaking cleanup, and duplicate production modules would undermine the intended concern boundaries.

### Recalibrate routing semantics

Rejected. No semantic routing change is requested or supported by evidence; recalibration would unnecessarily widen scope and operational risk.

## Consequences

The active artifact's byte identity will change only because four certified source receipts advance to the reviewed relocated files. Routing behavior and semantic authority remain frozen. The exact comparison, validation outputs, package checks, and independent review become required closure evidence for both the recertification ticket and the blocked structural-migration ticket.
