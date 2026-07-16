Status: blocked
Created: 2026-07-15
Updated: 2026-07-15
Parent: .10x/tickets/2026-07-15-production-semantic-routing-plan.md
Depends-On: .10x/tickets/done/2026-07-15-build-production-local-namespace-catalog.md

# Integrate Approved Apply Catalog Registration

## Outcome

Extend plan/apply with catalog preview, precomputed pending registration, post-success local commit, partial-success reporting, and idempotent reconciliation under `.10x/specs/approved-apply-catalog-registration.md`.

## Branch and worktree

Execute on `work/integrate-approved-apply-catalog-registration` in its own worktree after the catalog child is reviewed, closed, and integrated into current `develop`.

## Scope

- Preserve supported schema-v1 plan hashes/compatibility; add apply `--region`, derive only integrity-bound fields from plans, and bind apply-resolved region/current ranking defaults into pending/card state.
- Add non-mutating plan/apply-preflight catalog previews without adding a second manual-semantic input path.
- Acquire and retain the existing namespace lock before model/pending/credential/remote work; enforce namespace-before-catalog lock ordering.
- Detect every confirmed/unconfirmed pending collision before precompute so apply rerun cannot duplicate remote writes; add approved local-only abandonment for indeterminate unconfirmed state.
- Precompute/validate the prospective card, persisted vector, and catalog/state-bound hashed pending artifact before credential lookup or remote writes.
- Integrate pending confirmation and local catalog commit only after existing remote apply and applied-state success.
- Implement partial-success output and exact repair command for post-apply catalog commit failures.
- Wire `buoy catalog reconcile --pending PATH --catalog PATH` and preview/approved `abandon-pending` with trusted-root/non-symlink path checks, bound catalog/state identity, namespace lock, applied-state verification, and idempotency.
- Preserve manual semantics/enabled state and refresh generated/system fields correctly.
- Add focused tests with faked remote writers for namespace-lock contention/lifetime, lock ordering, old plans, confirmed/unconfirmed pending collisions, abandonment preview/approval, ordering, failure boundaries, no automatic duplicate remote writes, trusted-path/symlink/tamper checks, and reconciliation.
- Update plan/apply/catalog documentation.
- Record evidence and obtain independent review before closure.

## Acceptance criteria

- Plan/preflight remain local, non-mutating, no-model, no-credential, and no-Turbopuffer paths; old schema-v1 plan hashes remain valid.
- Approved apply holds the existing namespace lock across card embedding, pending lifecycle, credential/remote work, applied-state commit, and catalog commit; a busy lock fails before all such work.
- Remote failure cannot mutate the canonical catalog or create reconcilable state.
- Successful remote/apply-state execution commits one catalog card, preserves manual semantics/enabled state, and removes pending state.
- Rare post-apply catalog failure returns explicit partial success with a catalog/state-bound confirmed pending artifact and exact local repair command; every pending state blocks apply rerun, and only explicit approved abandonment of unconfirmed indeterminate state can permit later existing idempotent repeat-upsert behavior.
- Reconcile reads no credentials, contacts no remote service, verifies applied identity/hash, and is idempotent.
- Existing apply/stale-deletion/applied-state semantics remain unchanged outside the additive catalog lifecycle.
- Focused tests, full suite, and `git diff --check` pass.
- Independent review has no unresolved significant finding.

## Explicit exclusions

- catalog core/schema redesign;
- automatic routed retrieval;
- remote catalog or remote rollback;
- automatic registration of unrelated namespaces;
- ACL/taxonomy/graph/tag-filter behavior.

## Evidence expectations

Evidence must map each phase and failure scenario to tests, show credential/remote call ordering, verify pending artifacts contain no secret/chunk content, prove manual/disabled preservation, exercise post-success reconciliation without a second remote write, and record full validation.

## Blockers

Blocked until `.10x/tickets/done/2026-07-15-build-production-local-namespace-catalog.md` is reviewed, closed, and integrated into `develop`.

## Progress and notes

- 2026-07-15: Opened as the second sequential child; no implementation occurred.
