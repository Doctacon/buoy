Status: cancelled
Created: 2026-07-15
Updated: 2026-07-15
Parent: .10x/tickets/cancelled/2026-07-15-semantic-routing-offline-pilot-plan.md
Depends-On: .10x/tickets/cancelled/2026-07-15-build-controlled-taxonomy-fixture.md

# Build Offline Namespace Catalog Fixture

## Scope

Implement the catalog model/loader, integrated taxonomy references, synthetic eligibility/ACL/compatibility gates, deterministic cards, leakage protections, and focused tests governed by `.10x/specs/superseded/semantic-namespace-catalog-pilot.md`.

Execute on `work/build-offline-namespace-catalog-fixture` in its own worktree after taxonomy integration.

## Acceptance criteria

- Reuse the integrated taxonomy model for revision/reference/card labels.
- Validate every catalog field/domain, group rule, compatibility tuple, and enabled state.
- Generate deterministic revision-bound cards.
- Add adversarial no-leak canaries and no-network/external-construction sentinels.
- Add focused tests for every catalog acceptance scenario.
- Run focused tests, full suite, and `git diff --check`.

## Assumption provenance

Broad catalog-card/compatibility/access direction is user-ratified. Current precision/profile/source-kind domains and RRF compatibility are source-backed. Fixture schema and synthetic ACL mechanics are pilot-only. Production authority/ACL/freshness remain unresolved and excluded.

## Explicit exclusions

Routing/scoring/metrics, production persistence, real ACLs, CLI/API, live Turbopuffer, model loading, Data Vault, ontology, concepts, or graphs.

## References

- `.10x/specs/superseded/semantic-namespace-catalog-pilot.md`
- `.10x/specs/superseded/controlled-taxonomy-pilot.md`
- `.10x/tickets/cancelled/2026-07-15-semantic-routing-offline-pilot-plan.md`

## Evidence expectations

Changed files, field/validation contract, scenario and sentinel tests, full-suite result, diff hygiene, and limits.

## Blockers

Depends on `.10x/tickets/cancelled/2026-07-15-build-controlled-taxonomy-fixture.md` closing and integrating into current `develop`. Repaired shaping passed independent re-review.

## Progress and notes

- 2026-07-15: Initially declared independent; shaping review found a real taxonomy dependency. Ticket now depends on integrated taxonomy and remains unimplemented.
- 2026-07-15: Repaired shaping passed `.10x/reviews/2026-07-15-semantic-routing-offline-pilot-shaping-rereview.md`; dependency remains the only execution blocker.

- 2026-07-15: Cancelled before implementation after the user accepted `.10x/reviews/2026-07-15-holistic-semantic-routing-workstream-review.md`. The five-stage synthetic framework could prove plumbing but not representative routing value; it is replaced by one bounded representative experiment. No implementation from this ticket occurred.
