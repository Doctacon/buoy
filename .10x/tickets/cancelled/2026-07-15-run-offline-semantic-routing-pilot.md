Status: cancelled
Created: 2026-07-15
Updated: 2026-07-15
Parent: .10x/tickets/cancelled/2026-07-15-semantic-routing-offline-pilot-plan.md
Depends-On: .10x/tickets/cancelled/2026-07-15-freeze-offline-semantic-routing-fixture.md

# Run Offline Semantic Routing Pilot

## Scope

Run the independently reviewed frozen fixture exactly once on the pinned implementation, rerun for deterministic digest confirmation, and record durable plumbing evidence and bounded synthesis.

Execute on `work/run-offline-semantic-routing-pilot` after freeze integration.

## Acceptance criteria

- Verify implementation/input manifest before execution; make no fixture/parameter edits.
- Run oracle, exact, semantic, and hybrid with identical frozen gates/limits/evidence.
- Record canonical per-case, split, aggregate, safety-count, and downstream evidence metrics.
- Repeat and prove byte-identical output/SHA-256 digest.
- Describe results only as synthetic deterministic plumbing evidence.
- Create durable evidence/research synthesis with findings, contradictions, limits, and smallest next action.
- Do not promote architecture or close parent without user review.
- Run focused/full tests, diff checks, and independent review.

## Assumption provenance

Execution of the local pilot is user-ratified. Frozen fixture semantics/metrics are pilot-only. Real quality, ACLs, models, thresholds, and architecture remain unresolved.

## Explicit exclusions

Editing frozen inputs, real namespaces/ACLs, network/credentials, Turbopuffer/model/hosted calls, live evals/writes, answer generation, production infrastructure, Data Vault, concepts, ontology, or graphs.

## References

- `.10x/specs/superseded/offline-semantic-routing-evaluation.md`
- `.10x/tickets/cancelled/2026-07-15-semantic-routing-offline-pilot-plan.md`

## Evidence expectations

Manifest verification, commands, canonical output/digests, metrics, deterministic rerun, tests, independent review, no-network/external-side-effect confirmation, and limits.

## Blockers

Depends on `.10x/tickets/cancelled/2026-07-15-freeze-offline-semantic-routing-fixture.md` closing and integrating into current `develop`. Repaired shaping passed independent re-review.

## Progress and notes

- 2026-07-15: Split from fixture authoring after shaping review. This executor may not change frozen inputs or tune held-out cases.
- 2026-07-15: Repaired shaping passed `.10x/reviews/2026-07-15-semantic-routing-offline-pilot-shaping-rereview.md`; dependency remains the only execution blocker.

- 2026-07-15: Cancelled before implementation after the user accepted `.10x/reviews/2026-07-15-holistic-semantic-routing-workstream-review.md`. The five-stage synthetic framework could prove plumbing but not representative routing value; it is replaced by one bounded representative experiment. No implementation from this ticket occurred.
