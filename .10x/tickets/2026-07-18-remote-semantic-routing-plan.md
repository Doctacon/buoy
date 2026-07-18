Status: open
Created: 2026-07-18
Updated: 2026-07-18
Parent: None
Depends-On: None

# Remote Semantic Routing Plan

## Outcome

Replace working-directory local routing-card authority with live Turbopuffer namespace discovery intersected against cards in `buoy-routing-catalog-v1`, migrate the two validated cards, update apply recovery, cut retrieval over, and delete `.buoy/catalog.json`.

## Child sequence

1. `.10x/tickets/2026-07-18-build-remote-routing-catalog.md`
2. `.10x/tickets/2026-07-18-seed-remote-routing-catalog.md`
3. `.10x/tickets/2026-07-18-integrate-apply-remote-catalog.md`
4. `.10x/tickets/2026-07-18-cut-over-remote-routing.md`

Children are strictly sequential. The parent is not executable.

## Aggregate acceptance criteria

- Remote catalog schema/conditional card lifecycle and authenticated CLI are production-tested without local catalog authority.
- Actual paginated Turbopuffer namespace listing is intersected with valid remote cards; missing/stale targets are excluded/counted and IDs never become semantics.
- Oscilar and Dagster Benchmark cards are migrated to the reserved namespace; uncarded live Dagster/Thistle remain excluded.
- Approved apply registers/reconciles remote cards without duplicate content writes or concurrent overwrite.
- Default automatic retrieval works from unrelated directories using only credentials/region and remote authority; explicit CLI namespace remains the manual bypass.
- Automatic preview truthfully reports credential/read-only remote activity.
- `.buoy/catalog.json`, lock, local path flags/environment, and obsolete local catalog implementation are removed after cutover verification.
- No content namespace mutation occurs except the already authorized card migration in the reserved catalog namespace; no deletion of content namespaces/rows.
- Focused/full/hosted validation, evidence, and independent reviews pass for every child.

## Explicit exclusions

ID-only routing; per-content-namespace card rows; local/disk card cache; cross-region fan-out; remote distributed locks; content-namespace deletion; ACL/taxonomy/graph/telemetry/online learning; concurrency changes to content retrieval.

## References

- `.10x/decisions/production-routing-remote-catalog.md`
- `.10x/research/2026-07-18-turbopuffer-remote-routing-catalog.md`
- `.10x/specs/remote-turbopuffer-routing-catalog.md`
- `.10x/specs/approved-apply-remote-catalog-registration.md`
- `.10x/specs/default-remote-namespace-routing.md`

## Progress and notes

- 2026-07-18: User rejected working-directory catalog authority, approved the dedicated remote catalog plus live-list intersection and authenticated remote preview, selected exclusion for live namespaces lacking cards, and explicitly approved migrating Oscilar/Dagster cards then deleting the local catalog.
- 2026-07-18: The unimplemented local-default ticket was cancelled and its authorities superseded before runtime changes.
