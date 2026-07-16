Status: cancelled
Created: 2026-07-15
Updated: 2026-07-15
Parent: .10x/tickets/cancelled/2026-07-15-semantic-routing-offline-pilot-plan.md
Depends-On: .10x/tickets/cancelled/2026-07-15-build-offline-semantic-router-evaluator.md

# Freeze Offline Semantic Routing Fixture

## Scope

Create the synthetic catalog, taxonomy, cards, vectors, source-grouped development/held-out cases, cached namespace evidence, labels, configuration, preregistration, and SHA-256 manifest required for one auditable deterministic plumbing run.

Execute on `work/freeze-offline-semantic-routing-fixture` after evaluator integration.

## Acceptance criteria

- Cover every required catalog/taxonomy/evaluator scenario, including adversarial ACL canaries.
- Record source-grouped split assignments and ensure near-duplicate source groups do not cross splits.
- Freeze route/evidence limits, metric definitions, implementation commit, all input files, and canonical card text.
- Generate a SHA-256 manifest over every frozen input.
- State explicitly that synthetic visible labels support plumbing evidence only.
- Receive independent review before the run child starts.
- Run fixture validation, focused/full tests, and diff checks.

## Assumption provenance

The local synthetic pilot is user-ratified. Freeze mechanics and fixture meanings are pilot-only. No real semantic quality or ACL policy is claimed.

## Explicit exclusions

Running the final held-out report, tuning after freeze, real data/users, network/live services, production architecture, or graph work.

## References

- `.10x/specs/superseded/offline-semantic-routing-evaluation.md`
- `.10x/tickets/cancelled/2026-07-15-semantic-routing-offline-pilot-plan.md`

## Evidence expectations

Frozen inventory, split/group rationale, preregistration, manifest, validator/test results, independent review, and no-external-side-effect proof.

## Blockers

Depends on `.10x/tickets/cancelled/2026-07-15-build-offline-semantic-router-evaluator.md` closing and integrating into current `develop`. Repaired shaping passed independent re-review.

## Progress and notes

- 2026-07-15: Added after shaping review found that one executor could otherwise author and tune the held-out fixture. No fixture created.
- 2026-07-15: Repaired shaping passed `.10x/reviews/2026-07-15-semantic-routing-offline-pilot-shaping-rereview.md`; dependency remains the only execution blocker.

- 2026-07-15: Cancelled before implementation after the user accepted `.10x/reviews/2026-07-15-holistic-semantic-routing-workstream-review.md`. The five-stage synthetic framework could prove plumbing but not representative routing value; it is replaced by one bounded representative experiment. No implementation from this ticket occurred.
