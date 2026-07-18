Status: blocked
Created: 2026-07-18
Updated: 2026-07-18
Parent: .10x/tickets/2026-07-18-remote-semantic-routing-plan.md
Depends-On: .10x/tickets/2026-07-18-integrate-apply-remote-catalog.md

# Cut Over Retrieval to Remote Routing

## Scope

Implement `.10x/specs/default-remote-namespace-routing.md`, remove obsolete local catalog routing/path behavior and tests/docs, verify default automatic routing through remote fakes and the seeded live remote catalog, then delete the canonical user's `.buoy/catalog.json` and lock only after successful remote dry/live-read validation.

This child includes the explicitly authorized read-only live route preview needed to prove cutover. It does not authorize content retrieval or writes beyond deleting the superseded local catalog files.

## Acceptance criteria

- Default automatic and compatibility-flag retrieval use live-list/remote-card intersection with exact diagnostics and retained ranking algorithm.
- Explicit CLI namespace bypass remains local for dry preview and compatible for live retrieval.
- Automatic previews require credentials, truthfully report read-only calls, and never write/query content namespaces.
- Missing-card, stale-card, corruption, pagination, permission, offline, query precedence, and credential boundaries are covered.
- Local catalog module/path flags/environment/docs are removed where no longer used; no `.buoy/catalog.json` read/write path remains.
- Read-only live preview from the canonical checkout and an unrelated temporary directory yields the same two-card route/intersection.
- After verification, `.buoy/catalog.json` and lock are deleted; other `.buoy` state is untouched.
- Focused/full/hosted checks, durable evidence, independent review, and parent graph coherence pass.

## Explicit exclusions

Live content retrieval/evals, content writes/deletes, additional card migration, local card cache, ID fallback, cross-region work, routing algorithm/model/fan-out changes.

## References

- `.10x/specs/default-remote-namespace-routing.md`
- `.10x/specs/remote-turbopuffer-routing-catalog.md`

## Evidence expectations

Argument/credential/API call matrix, pagination/intersection/ranking fakes, exact live read-only commands/output from two directories, pre/post local file state, no-content-query/write attestation, full/hosted checks, independent review.

## Blockers

Remote catalog, seed, and apply integration dependencies.

## Progress and notes
