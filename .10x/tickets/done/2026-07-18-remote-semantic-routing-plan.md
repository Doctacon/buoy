Status: done
Created: 2026-07-18
Updated: 2026-07-18
Parent: None
Depends-On: None

# Remote Semantic Routing Plan

## Outcome

Replace working-directory routing-card authority with actual Turbopuffer namespace discovery intersected against cards in `buoy-routing-catalog-v1`; migrate the two validated cards; atomically switch catalog CLI, apply, and retrieval; then delete the exact local catalog.

## Child sequence

1. `.10x/tickets/done/2026-07-18-build-remote-routing-backend.md` — done
2. `.10x/tickets/done/2026-07-18-atomic-remote-catalog-cutover.md` — done

The backend child is intentionally inert. The cutover child is one cohesive authority transition because splitting public catalog/apply/retrieval changes would create a forbidden split-brain window. The parent is not executable.

## Aggregate acceptance criteria

- Exact remote schema/serializer, strong stable pagination, intersection counts, optimistic create/update/delete, permission/cost boundaries, and safe recovery primitives are tested without changing public authority.
- One reviewed cutover switches catalog CLI, approved apply, and default routing together.
- A mutation freeze prevents divergence from seed through post-integration verification.
- Exactly two validated cards are seeded; five listed IDs classify as one control plane, four content-live, two eligible carded targets, and two missing-card exclusions.
- Automatic preview works from unrelated directories using credentials/region and remote authority; explicit CLI namespace remains the local dry-preview/manual bypass.
- Confirmed apply conflicts have approved safe-rebase and exact operator-accepted stable remote revision recovery without content replay or clock-based ordering.
- Exact bound `.buoy/catalog.json` is deleted only after integrated remote verification; no other local state changes.
- No content namespace query/write/delete occurs during migration/cutover verification.
- Focused/full/hosted validation, durable evidence, and independent reviews pass.

## Explicit exclusions

ID-only routing; per-content-namespace card rows; local/disk cache; cross-region fan-out; remote distributed locks; content deletion/live retrieval/evals; ACL/taxonomy/graph/telemetry/online learning; protection changes.

## References

- `.10x/decisions/production-routing-remote-catalog.md`
- `.10x/research/2026-07-18-turbopuffer-remote-routing-catalog.md`
- `.10x/specs/namespace-routing-card-contract.md`
- `.10x/specs/remote-turbopuffer-routing-catalog.md`
- `.10x/specs/remote-routing-catalog-cli.md`
- `.10x/specs/approved-apply-remote-catalog-registration.md`
- `.10x/specs/default-remote-namespace-routing.md`
- `.10x/specs/atomic-remote-catalog-cutover.md`

## Progress and notes

- 2026-07-18: User rejected working-directory authority, approved dedicated remote catalog plus live-list intersection/authenticated preview, chose missing-card exclusion, authorized two-card migration/local deletion, and accepted safe-rebase/accept-remote recovery plus list/query versus write permission exposure.
- 2026-07-18: The unimplemented local-default ticket was cancelled. Initial four-child rollout was reshaped to inert backend plus atomic cutover after review identified split-brain risk.
- 2026-07-18: Inert backend passed independent review and hosted checks and was integrated through PR #31 as `bc8bdc30555e66837288d049c3c4885e3cf1df71`; atomic cutover dependency is satisfied.
- 2026-07-18: Atomic cutover merged through PR #32 as `eba8145bb12eb7a0749a96ee4088938060a9fb12`. Exact remote migration, two-directory branch/integrated/post-deletion proof, explicit bypass, local apply preflight, exact local deletion, freeze release, and retrospective evidence are recorded in `.10x/evidence/2026-07-18-remote-routing-catalog-live-cutover.md`.
- 2026-07-18: Child closure and aggregate closure review passed. Both children are done, all aggregate criteria are evidenced, residual risks have no-action rationale, and the parent plan is closed.
