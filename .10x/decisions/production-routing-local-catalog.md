Status: active
Created: 2026-07-15
Updated: 2026-07-15

# Production Routing Uses an Opt-In Local Catalog

## Context

Buoy requires explicit namespace selection and can merge explicitly selected namespaces, but remote namespace discovery exposes only identifiers. The representative routing experiment showed that semantic cards plus lexical routing can select source namespaces, while also showing that the benchmark is too source-revealing to serve as a production promotion gate.

The user nevertheless explicitly authorized a full production implementation for frequent personal use and chose the operational behavior directly on 2026-07-15.

## Decision

Production routing will use:

- explicit `buoy retrieve --auto-route` activation; existing explicit namespace behavior remains the default;
- a canonical local catalog under Buoy state, not a managed or remote catalog service;
- every enabled, compatible catalog card as eligible in a single-user/account-scoped model; no group ACL system in this release;
- hybrid lexical plus semantic namespace-card routing;
- three routed namespaces by default, with an explicit bounded CLI override;
- persisted semantic card vectors refreshed when card semantics or the routing model contract changes;
- local-only route preview when `--auto-route` is used without `--live`;
- successful approved apply integration that preserves manually edited semantic fields and enabled state;
- catalog precomputation before remote writes, with an exact reconciliation path if the rare post-apply catalog commit fails.

Explicit CLI namespaces remain authoritative and do not invoke automatic routing. Routing and catalog errors fail closed; Buoy does not silently search every visible remote namespace.

The first implementation uses atomic canonical JSON plus the existing `portalocker` dependency because the catalog is small local control-plane state and no relational query requirement exists.

## Alternatives considered

### Automatic routing whenever namespace is omitted

Rejected for the first production release because it would silently replace the current explicit-selection safety contract. The opt-in flag is reversible and lets the user judge live behavior without changing unrelated calls.

### Turbopuffer-hosted catalog

Rejected because it adds live control-plane writes, cross-device synchronization semantics, and a remote authority that are not required for one frequent user. A future decision may add a disposable remote projection while keeping local authority.

### Public-only eligibility

Rejected because the user selected enabled-card eligibility in a single-user/account context. This does not authorize multi-user access control or make catalog metadata an authorization system.

### Group ACLs now

Rejected as unnecessary complexity for the selected single-user scope. Any shared/multi-user deployment requires a new security specification before catalog routing is enabled.

### Re-embed every card on every route

Rejected because persisted vectors provide faster repeated routing and a clear hash/model revision contract.

### Top-one or top-five default

Rejected in favor of top three as the user-selected balance of coverage, latency, and Turbopuffer query cost. The bounded override preserves experimentation.

## Consequences

- Local catalog loss or corruption disables automatic routing but does not affect explicit retrieval or remote namespace contents.
- Catalog cards must carry enough retrieval compatibility metadata to gate before ranking.
- Existing remote namespaces are not automatically inferred from IDs; they require manual catalog registration or a future successful apply.
- Approved apply gains a local catalog staging/commit/reconciliation lifecycle.
- Dry-run automatic routing loads the local routing model but does not contact Turbopuffer or read credentials.
- Live automatic routing queries only selected catalog namespaces and retains existing all-or-nothing multi-namespace retrieval behavior.
- The production feature is intentionally user-judged after deployment; experiment metrics are context, not a launch threshold.
- This decision does not authorize taxonomy, graph, concepts, relationship extraction, or public retrieval-tag semantics.
