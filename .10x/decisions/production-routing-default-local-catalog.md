Status: active
Created: 2026-07-16
Updated: 2026-07-16

# Production Retrieval Routes by Default

## Context

`.10x/decisions/superseded/production-routing-local-catalog.md` introduced catalog routing behind `--auto-route` so the first production release could preserve explicit namespace behavior while routing quality was judged live. Buoy v0.3.0 now has a validated local catalog, apply registration/recovery, default-state migration, and released routing implementation. Requiring the flag on every ordinary retrieval is unnecessary friction.

The user explicitly selected this contract on 2026-07-16: ordinary retrieval always uses catalog routing; environment namespace selection must not influence retrieval; a namespace written directly in the command remains available as the deliberate manual override. Existing scripts that pass `--auto-route` must continue to work.

## Decision

- `buoy retrieve QUERY` MUST route through the canonical local catalog when no CLI `--namespace` is supplied.
- One or more repeatable CLI `--namespace ID` arguments remain the sole manual namespace-selection override and retain existing explicit retrieval behavior.
- `TURBOPUFFER_NAMESPACE` MUST NOT be read, selected, or warned about by `buoy retrieve`. Other vendor variables keep their existing contracts.
- `--auto-route` remains accepted as an idempotent compatibility affirmation for existing scripts. It does not change default behavior.
- `--auto-route` combined with CLI `--namespace` remains an error because the command requests contradictory selection modes.
- `--route-top-k` and `--catalog` apply to the default automatic mode without requiring `--auto-route`; they remain invalid with explicit CLI namespaces.
- No `--no-auto-route` is added. A deliberate CLI namespace is the manual escape hatch.
- Automatic routing retains eligibility-before-relevance, fixed persisted-vector contracts, local-only preview, default top-three fan-out, fail-closed errors, all-or-nothing live retrieval, and no remote discovery/fallback.
- Every non-activation choice from the superseded decision remains active: canonical local JSON catalog authority; enabled compatible-card eligibility; hybrid lexical/semantic RRF; persisted vectors refreshed only on semantic/model-contract change; manual semantic and enabled-state preservation; apply precomputation before remote writes; namespace locking; exact pending-state reconciliation/approved abandonment; and no remote catalog, ACL groups, taxonomy, graph, telemetry, or online learning.

This decision supersedes `.10x/decisions/superseded/production-routing-local-catalog.md` only by changing retrieval activation and namespace-environment precedence; it explicitly restates and preserves the remaining catalog/apply architecture.

## Alternatives considered

### Keep opt-in routing

Rejected by the user as unnecessary friction after the released catalog/routing workflow proved operational.

### Let `TURBOPUFFER_NAMESPACE` override routing

Rejected. Hidden shell state should not silently disable the normal routing behavior.

### Remove manual namespace selection

Rejected. A namespace explicitly written in a command remains useful for diagnosis, comparison, and controlled retrieval.

### Add `--no-auto-route`

Rejected as redundant. Without an explicit namespace it would only turn a useful default into an error; explicit `--namespace` already expresses the intended override.

## Consequences

Ordinary retrieval becomes simpler and catalog availability becomes part of the default retrieval contract. Missing, corrupt, empty, or incompatible catalog state fails before credentials or remote calls. Existing explicit commands and `--auto-route` scripts remain compatible. Existing scripts that relied only on `TURBOPUFFER_NAMESPACE` must add `--namespace` or accept automatic routing.
