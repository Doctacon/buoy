Status: recorded
Created: 2026-07-16
Updated: 2026-07-16
Target: commits `0fdccbd` and `e6efa3c`
Verdict: pass

# Default Automatic Routing Shaping Review

## Findings

Initial review found two blockers: active catalog/apply specs still referenced the superseded opt-in decision, and query/argument error precedence was underspecified.

The repaired shaping:

- explicitly preserves every non-activation catalog/apply choice in the new active decision and limits supersession to retrieval activation/environment precedence;
- points active catalog and approved-apply specs at active authority;
- specifies live/dry-plan, contradictory-mode, namespace-list, and whitespace-query error precedence with acceptance scenarios;
- requires corresponding argument-matrix and sentinel evidence in the executable ticket.

The ratified contract is coherent: retrieval auto-routes when no CLI namespace is written; explicit CLI namespaces remain the sole manual override; `TURBOPUFFER_NAMESPACE` has no retrieve effect or warning; `--auto-route` remains compatible; no opt-out is added; algorithms, fan-out, catalog, fail-closed behavior, and remote boundaries remain unchanged.

## Verdict

Pass. The bounded implementation ticket is executable with no unresolved semantic assumption.

## Residual risk

Changing the default is intentionally behaviorally incompatible for scripts that relied only on `TURBOPUFFER_NAMESPACE`; they must add CLI `--namespace` or accept automatic routing. Existing explicit CLI and `--auto-route` scripts remain supported.
