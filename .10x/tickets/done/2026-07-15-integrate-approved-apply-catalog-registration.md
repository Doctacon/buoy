Status: done
Created: 2026-07-15
Updated: 2026-07-15
Parent: .10x/tickets/done/2026-07-15-production-semantic-routing-plan.md
Depends-On: .10x/tickets/done/2026-07-15-build-production-local-namespace-catalog.md

# Integrate Approved Apply Catalog Registration

## Outcome

Extend plan/apply with catalog preview, precomputed pending registration, post-success local commit, partial-success reporting, and idempotent reconciliation under `.10x/specs/superseded/approved-apply-catalog-registration.md`.

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

None. Dependency `.10x/tickets/done/2026-07-15-build-production-local-namespace-catalog.md` is reviewed, closed, and integrated at develop commit `9dcdecb`.

## Progress and notes

- 2026-07-15: Opened as the second sequential child; no implementation occurred.
- 2026-07-15: Marked active after dependency integration at develop commit `9dcdecb`; implementation started on `work/integrate-approved-apply-catalog-registration`.
- 2026-07-15: Implemented apply/plan catalog previews, apply `--region`/`--catalog`, namespace-lock lifetime and under-lock diff refresh, integrity-bound pending precompute/collision handling, post-state confirmation/catalog commit, truthful partial success, local reconcile/approved abandonment, manual/disabled preservation, and schema-v1 compatibility. Source inspection exposed current supported PDF plans using canonical `pdf://<source-id>`; the governing specs were narrowly corrected to preserve that source-backed compatibility without deriving filenames from opaque IDs.
- 2026-07-15: Added fake/sentinel coverage including lock ordering/lifetime, no early credential/remote work, confirmed/unconfirmed collision behavior, secret/chunk exclusion, remote and catalog failures, confirmation-write failure recovery from exact applied-state identity, no duplicate remote writes, reconcile idempotency, abandon preview/approval, tamper/symlink/out-of-root rejection, manual/disabled preservation, and legacy plan/source behavior. Focused tests passed (127), full suite passed (340), compilation and `git diff --check` passed. Evidence: `.10x/evidence/2026-07-15-approved-apply-catalog-registration-implementation.md`. Ticket remains active pending independent review.
- 2026-07-15: Applied only independent-review fixes: truthful catalog-success/pending-cleanup partial output and idempotent cleanup, enabled-state preservation for concurrent generated disables, post-lock and pre-unlink pending identity revalidation for reconcile/abandon, no-follow canonical pending-root creation, and missing-credential pending/abandon coverage. Focused tests passed (133), full suite passed (346), compilation and `git diff --check` passed. Evidence record updated; ticket remains active and unclosed.

- 2026-07-15: Corrective commit `e7a8170` resolved all review findings; two fresh re-reviewers passed. Review: `.10x/reviews/2026-07-15-approved-apply-catalog-registration-review.md`.

## Closure mapping

- Apply lock/pending/remote/state/catalog phases, previews, partial success, reconcile/abandon, source compatibility, manual preservation, and CLI output map to focused tests and evidence.
- 133 focused and 346 full-suite tests, compilation, and diff checks passed.
- No automatic routing or excluded architecture was added.

## Retrospective

Post-commit cleanup must report committed state truthfully, and recovery artifacts require identity revalidation immediately before deletion. These invariants are now captured in the active spec and regression tests. Automatic routing remains owned by the final child.
