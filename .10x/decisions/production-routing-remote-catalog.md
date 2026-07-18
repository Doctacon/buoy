Status: active
Created: 2026-07-18
Updated: 2026-07-18

# Production Routing Uses a Remote Turbopuffer Catalog

## Context

The released local catalog made routing deterministic but tied authority to a working-directory `.buoy/catalog.json`. The user runs Buoy from unrelated directories and explicitly rejected that locality. Turbopuffer namespace listing is the desired availability authority, but it returns IDs only and namespace metadata cannot hold custom semantic cards.

Research in `.10x/research/2026-07-18-turbopuffer-remote-routing-catalog.md` established that a dedicated document namespace can hold cards while the namespace list remains actual-existence authority.

## Decision

- Canonical routing-card authority is a reserved Turbopuffer namespace named `buoy-routing-catalog-v1` in the resolved region.
- Automatic routing lists live Turbopuffer namespaces and reads validated cards from that reserved namespace on every invocation. It intersects both sets before relevance scoring.
- The reserved catalog namespace is never a retrieval candidate.
- A live target namespace without a valid card is excluded and counted. A card whose target is not live is stale, excluded, and counted. If no valid live cards remain, routing fails clearly.
- Namespace IDs alone never supply fallback semantics or compatibility values.
- Automatic preview requires credentials and performs read-only Turbopuffer listing/catalog queries. No local/offline automatic preview or on-disk card cache remains.
- Explicit CLI `--namespace` remains the sole manual bypass and retains local dry preview behavior. `TURBOPUFFER_NAMESPACE` does not influence retrieval.
- `--auto-route` remains an accepted compatibility affirmation, while routing is default when no CLI namespace is supplied.
- Card documents preserve the established semantic/retrieval/vector/hash/lineage contract and use optimistic conditional writes instead of local file locks.
- Approved apply stages a remote card update and preserves manual semantics/enabled state with revision-bound conflict detection and recoverable pending state. The user explicitly approved recovery that can safely rebase newer manual/enabled-only edits or explicitly accept a strictly newer remote apply without replaying content.
- Catalog CLI operations become authenticated remote operations; local path options/environment variables are removed. The user accepted that preview/list/show require list+query permission and expose complete card metadata to query-capable keys, while mutations/apply additionally require write permission.
- Remote backend code may stage inertly, but catalog CLI, apply, and retrieval authority switch together under a mutation freeze and exact migration/deletion checks; no split-brain public rollout is allowed.
- The two validated Oscilar and Dagster Benchmark cards are migrated remotely. After remote routing verification, `.buoy/catalog.json` and its lock are deleted. Unregistered live Dagster/Thistle namespaces remain excluded.
- No remote namespace inference, ACL system, taxonomy, graph, telemetry, online learning, or cross-region fan-out is introduced.

This decision supersedes `.10x/decisions/superseded/production-routing-default-local-catalog.md` and the earlier local-catalog decisions it had preserved.

## Alternatives considered

### Keep local catalog in a global OS directory

Rejected because it remains machine-local and can drift across computers/accounts.

### Store a card inside every content namespace

Rejected because routing would require one additional query per listed namespace and reserved card rows would need universal exclusion from content retrieval.

### Route from namespace IDs

Rejected because identifiers do not provide reliable semantics, enabled state, compatibility contracts, or ranking settings.

### Dedicated remote catalog without live-list intersection

Rejected because stale cards could route to deleted namespaces and the user explicitly selected Turbopuffer's actual namespace list as availability authority.

## Consequences

This is an explicit user-required extension of the existing Turbopuffer managed-service dependency, not a new provider choice. Buoy keeps canonical card serialization/export and embedding local/provider-neutral and introduces no hosted embedding dependency.

Automatic retrieval now depends on Turbopuffer availability and a key with list/query permission even for preview. Catalog/apply mutations require write permission. Remote catalog reads add two control-plane request families before content retrieval. The architecture works from any directory and machine with the same account/region. Cross-system apply failures remain recoverable through local pending artifacts, but card concurrency is optimistic rather than filesystem-locked.
